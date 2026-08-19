from __future__ import annotations

import logging
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from threading import Event, Thread
from typing import Any, Protocol

from .client import TelegramAPIError
from .runtime import TelegramConfigurationError, get_telegram_runtime

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PollingHandle:
    thread: Thread
    stop_event: Event
    join_timeout: float = 16.0

    def stop(self, timeout: float | None = None) -> None:
        deadline = self.join_timeout if timeout is None else timeout
        self.stop_event.set()
        self.thread.join(timeout=deadline)
        if self.thread.is_alive():
            raise TimeoutError(
                f"Telegram polling thread did not stop within {deadline:g} seconds"
            )


class _PollingClient(Protocol):
    def get_updates(
        self,
        *,
        offset: int | None = None,
        timeout: int = 10,
        stop_event: Event | None = None,
    ) -> list[dict[str, Any]]: ...


def run_polling_loop(
    client: _PollingClient,
    process_update: Callable[[Mapping[str, Any]], None],
    *,
    stop_event: Event,
    poll_timeout: int = 10,
    waiter: Callable[[float], bool] | None = None,
) -> None:
    """Long-poll Telegram until shutdown, advancing after successful processing."""
    offset: int | None = None
    wait_for_stop = stop_event.wait if waiter is None else waiter
    while not stop_event.is_set():
        try:
            updates = client.get_updates(
                offset=offset,
                timeout=poll_timeout,
                stop_event=stop_event,
            )
        except TelegramAPIError:
            logger.warning("telegram_polling_request_failed")
            if wait_for_stop(1.0):
                return
            continue
        if stop_event.is_set():
            return
        for update in updates:
            if stop_event.is_set():
                return
            try:
                process_update(update)
            except Exception:
                # Update payloads and downstream exception strings can contain
                # athlete text, so keep this operational signal deliberately terse.
                logger.warning("telegram_update_processing_failed")
                if wait_for_stop(1.0):
                    return
                break
            update_id = update.get("update_id")
            if isinstance(update_id, int) and not isinstance(update_id, bool):
                next_offset = update_id + 1
                offset = next_offset if offset is None else max(offset, next_offset)


def start_polling_thread(
    client: _PollingClient,
    process_update: Callable[[Mapping[str, Any]], None],
    *,
    poll_timeout: int = 10,
) -> PollingHandle:
    stop_event = Event()
    thread = Thread(
        target=run_polling_loop,
        kwargs={
            "client": client,
            "process_update": process_update,
            "stop_event": stop_event,
            "poll_timeout": poll_timeout,
        },
        name="telegram-polling",
        daemon=True,
    )
    thread.start()
    return PollingHandle(thread=thread, stop_event=stop_event)


def start_polling_from_env() -> PollingHandle | None:
    mode = os.getenv("TELEGRAM_MODE", "").strip().lower()
    if not mode or mode == "webhook":
        return None
    if mode != "polling":
        raise TelegramConfigurationError(
            "TELEGRAM_MODE must be either polling or webhook"
        )
    runtime = get_telegram_runtime()
    return start_polling_thread(
        runtime.client,
        runtime.processor.process_update,
    )
