from __future__ import annotations

import asyncio
from threading import Event, Thread
from typing import Any

import pytest
from app.integrations.telegram import polling as polling_module
from app.integrations.telegram.client import TelegramAPIError
from app.integrations.telegram.polling import (
    run_polling_loop,
    start_polling_from_env,
    start_polling_thread,
)
from app.integrations.telegram.runtime import TelegramConfigurationError


class SequencedPollingClient:
    def __init__(self, stop_event: Event) -> None:
        self._stop_event = stop_event
        self.offsets: list[int | None] = []

    def get_updates(
        self,
        *,
        offset: int | None = None,
        timeout: int = 10,
        stop_event: Event | None = None,
    ) -> list[dict[str, Any]]:
        self.offsets.append(offset)
        if len(self.offsets) == 1:
            return [
                {"update_id": 4, "message": {"text": "first"}},
                {"update_id": 6, "message": {"text": "second"}},
            ]
        self._stop_event.set()
        return []


def test_polling_processes_updates_and_advances_offset_past_highest_id() -> None:
    stop_event = Event()
    client = SequencedPollingClient(stop_event)
    processed: list[dict[str, Any]] = []

    run_polling_loop(
        client,
        processed.append,
        stop_event=stop_event,
    )

    assert [update["update_id"] for update in processed] == [4, 6]
    assert client.offsets == [None, 7]


def test_polling_backs_off_and_recovers_after_bot_api_failure() -> None:
    stop_event = Event()
    processed: list[dict[str, Any]] = []
    delays: list[float] = []

    class RecoveringClient:
        def __init__(self) -> None:
            self.calls = 0

        def get_updates(
            self,
            *,
            offset: int | None = None,
            timeout: int = 10,
            stop_event: Event | None = None,
        ) -> list[dict[str, Any]]:
            self.calls += 1
            if self.calls == 1:
                raise TelegramAPIError("Telegram getUpdates transport failed")
            return [{"update_id": 8, "message": {"text": "recovered"}}]

    def process_recovered(update: dict[str, Any]) -> None:
        processed.append(update)
        stop_event.set()

    run_polling_loop(
        RecoveringClient(),
        process_recovered,
        stop_event=stop_event,
        waiter=lambda delay: delays.append(delay) or False,
    )

    assert [update["update_id"] for update in processed] == [8]
    assert delays == [1.0]


def test_polling_retries_failed_update_before_advancing_offset() -> None:
    stop_event = Event()
    processed: list[int] = []
    offsets: list[int | None] = []
    delays: list[float] = []
    attempts = 0

    class OneBatchClient:
        def get_updates(
            self,
            *,
            offset: int | None = None,
            timeout: int = 10,
            stop_event: Event | None = None,
        ) -> list[dict[str, Any]]:
            offsets.append(offset)
            return [{"update_id": 9}, {"update_id": 10}]

    def process(update: dict[str, Any]) -> None:
        nonlocal attempts
        update_id = update["update_id"]
        attempts += 1
        if update_id == 9 and attempts == 1:
            raise RuntimeError("poison update")
        processed.append(update_id)
        if update_id == 10:
            stop_event.set()

    run_polling_loop(
        OneBatchClient(),
        process,
        stop_event=stop_event,
        waiter=lambda delay: delays.append(delay) or False,
    )

    assert processed == [9, 10]
    assert offsets == [None, None]
    assert delays == [1.0]


def test_polling_does_not_process_batch_returned_after_stop() -> None:
    stop_event = Event()
    processed: list[dict[str, Any]] = []
    supplied_stop_events: list[Event | None] = []

    class StoppingLongPollClient:
        def get_updates(
            self,
            *,
            offset: int | None = None,
            timeout: int = 10,
            stop_event: Event | None = None,
        ) -> list[dict[str, Any]]:
            supplied_stop_events.append(stop_event)
            assert stop_event is not None
            stop_event.set()
            return [{"update_id": 12, "message": {"text": "too late"}}]

    run_polling_loop(
        StoppingLongPollClient(),
        processed.append,
        stop_event=stop_event,
    )

    assert supplied_stop_events == [stop_event]
    assert processed == []


def test_polling_stops_before_next_update_in_returned_batch() -> None:
    stop_event = Event()
    processed: list[int] = []

    class BatchClient:
        def get_updates(
            self,
            *,
            offset: int | None = None,
            timeout: int = 10,
            stop_event: Event | None = None,
        ) -> list[dict[str, Any]]:
            return [{"update_id": 20}, {"update_id": 21}]

    def process(update: dict[str, Any]) -> None:
        processed.append(update["update_id"])
        stop_event.set()

    run_polling_loop(BatchClient(), process, stop_event=stop_event)

    assert processed == [20]


def test_polling_api_failure_backoff_is_interrupted_by_stop() -> None:
    stop_event = Event()
    waits: list[float] = []

    class FailingClient:
        calls = 0

        def get_updates(
            self,
            *,
            offset: int | None = None,
            timeout: int = 10,
            stop_event: Event | None = None,
        ) -> list[dict[str, Any]]:
            self.calls += 1
            raise TelegramAPIError("polling failure")

    client = FailingClient()

    def stop_during_wait(delay: float) -> bool:
        waits.append(delay)
        stop_event.set()
        return True

    run_polling_loop(
        client,
        lambda _update: None,
        stop_event=stop_event,
        waiter=stop_during_wait,
    )

    assert client.calls == 1
    assert waits == [1.0]


def test_start_polling_thread_creates_stoppable_named_daemon() -> None:
    calls: list[int | None] = []
    called = Event()

    class StoppingClient:
        def get_updates(
            self,
            *,
            offset: int | None = None,
            timeout: int = 10,
            stop_event: Event | None = None,
        ) -> list[dict[str, Any]]:
            calls.append(offset)
            called.set()
            return []

    handle = start_polling_thread(StoppingClient(), lambda _update: None)
    assert called.wait(timeout=1.0)
    handle.stop(timeout=1.0)

    assert handle.thread.name == "telegram-polling"
    assert handle.thread.daemon is True
    assert handle.thread.is_alive() is False
    assert handle.join_timeout == 16.0
    assert calls


def test_polling_handle_stop_raises_when_thread_misses_deadline() -> None:
    stop_event = Event()
    release = Event()
    thread = Thread(target=release.wait, daemon=True)
    thread.start()
    handle = polling_module.PollingHandle(thread=thread, stop_event=stop_event)

    try:
        with pytest.raises(TimeoutError, match="did not stop"):
            handle.stop(timeout=0.01)
    finally:
        release.set()
        thread.join(timeout=1.0)

    assert stop_event.is_set()


def test_polling_mode_starts_shared_runtime_in_daemon(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_MODE", "polling")
    runtime = object()
    expected_handle = object()
    captured: list[tuple[object, object]] = []

    class Processor:
        def process_update(self, update: dict[str, Any]) -> None:
            return None

    runtime = type(
        "Runtime",
        (),
        {"client": object(), "processor": Processor()},
    )()
    monkeypatch.setattr(polling_module, "get_telegram_runtime", lambda: runtime)

    def fake_start(client: object, process_update: object):
        captured.append((client, process_update))
        return expected_handle

    monkeypatch.setattr(polling_module, "start_polling_thread", fake_start)

    handle = start_polling_from_env()

    assert handle is expected_handle
    assert captured == [(runtime.client, runtime.processor.process_update)]


@pytest.mark.parametrize("mode", [None, "webhook"])
def test_non_polling_mode_does_not_create_runtime(monkeypatch, mode: str | None) -> None:
    if mode is None:
        monkeypatch.delenv("TELEGRAM_MODE", raising=False)
    else:
        monkeypatch.setenv("TELEGRAM_MODE", mode)
    monkeypatch.setattr(
        polling_module,
        "get_telegram_runtime",
        lambda: (_ for _ in ()).throw(AssertionError("runtime must stay lazy")),
    )

    assert start_polling_from_env() is None


def test_invalid_telegram_mode_fails_fast(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_MODE", "invalid")

    with pytest.raises(TelegramConfigurationError, match="polling or webhook"):
        start_polling_from_env()


def test_fastapi_lifespan_starts_and_stops_telegram_polling(monkeypatch) -> None:
    from app import main as main_module

    events: list[str] = []

    class Scheduler:
        def shutdown(self, *, wait: bool) -> None:
            assert wait is False
            events.append("scheduler_stop")

    class Handle:
        def stop(self) -> None:
            events.append("polling_stop")

    monkeypatch.setattr(
        main_module,
        "setup_scheduler",
        lambda: events.append("scheduler_start") or Scheduler(),
    )
    monkeypatch.setattr(
        main_module,
        "start_polling_from_env",
        lambda: events.append("polling_start") or Handle(),
    )
    monkeypatch.setattr(
        main_module,
        "close_telegram_runtime",
        lambda: events.append("runtime_close"),
    )

    async def exercise_lifespan() -> None:
        async with main_module.lifespan(main_module.app):
            events.append("inside")

    asyncio.run(exercise_lifespan())

    assert events == [
        "scheduler_start",
        "polling_start",
        "inside",
        "polling_stop",
        "runtime_close",
        "scheduler_stop",
    ]


def test_fastapi_lifespan_leaves_runtime_open_when_polling_stop_times_out(
    monkeypatch,
) -> None:
    from app import main as main_module

    events: list[str] = []

    class Scheduler:
        def shutdown(self, *, wait: bool) -> None:
            assert wait is False
            events.append("scheduler_stop")

    class Handle:
        def stop(self) -> None:
            events.append("polling_stop")
            raise TimeoutError("polling thread did not stop")

    monkeypatch.setattr(
        main_module,
        "setup_scheduler",
        lambda: events.append("scheduler_start") or Scheduler(),
    )
    monkeypatch.setattr(
        main_module,
        "start_polling_from_env",
        lambda: events.append("polling_start") or Handle(),
    )
    monkeypatch.setattr(
        main_module,
        "close_telegram_runtime",
        lambda: events.append("runtime_close"),
    )

    async def exercise_lifespan() -> None:
        async with main_module.lifespan(main_module.app):
            events.append("inside")

    with pytest.raises(TimeoutError, match="did not stop"):
        asyncio.run(exercise_lifespan())

    assert events == [
        "scheduler_start",
        "polling_start",
        "inside",
        "polling_stop",
        "scheduler_stop",
    ]
