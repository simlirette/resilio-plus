from __future__ import annotations

from types import SimpleNamespace

import pytest
from app.integrations.telegram import webhook as webhook_module
from fastapi import BackgroundTasks, HTTPException


def test_webhook_rejects_bad_secret_token(api_client, monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "expected-secret")

    response = api_client.post(
        "/integrations/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
        json={"update_id": 1, "message": {"chat": {"id": 123}, "text": "Hi"}},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid Telegram webhook secret"}


def test_webhook_rejects_non_ascii_secret_as_403(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "expected-secret")

    with pytest.raises(HTTPException) as exc_info:
        webhook_module.telegram_webhook({}, BackgroundTasks(), "café")

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Invalid Telegram webhook secret"


def test_webhook_schedules_update_without_processing_inline(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "expected-secret")
    processed: list[dict[str, object]] = []

    class Processor:
        def process_update(self, update: dict[str, object]) -> None:
            processed.append(update)

    runtime = SimpleNamespace(processor=Processor())
    monkeypatch.setattr(webhook_module, "get_telegram_runtime", lambda: runtime)
    background_tasks = BackgroundTasks()
    update: dict[str, object] = {
        "update_id": 2,
        "message": {"chat": {"id": 123}, "text": "Hi"},
    }

    result = webhook_module.telegram_webhook(
        update,
        background_tasks,
        "expected-secret",
    )

    assert result == {"ok": True}
    assert processed == []
    assert len(background_tasks.tasks) == 1
    task = background_tasks.tasks[0]
    assert task.func == runtime.processor.process_update
    assert task.args == (update,)


def test_duplicate_update_id_is_ignored_before_background_scheduling(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "expected-secret")

    class Processor:
        def process_update(self, update: dict[str, object]) -> None:
            raise AssertionError("unit test does not execute background tasks")

    runtime = SimpleNamespace(processor=Processor())
    monkeypatch.setattr(webhook_module, "get_telegram_runtime", lambda: runtime)
    monkeypatch.setattr(
        webhook_module,
        "_update_deduplicator",
        webhook_module.UpdateDeduplicator(capacity=1000),
    )
    update: dict[str, object] = {
        "update_id": 77,
        "message": {"chat": {"id": 123}, "text": "Hi"},
    }
    first_tasks = BackgroundTasks()
    duplicate_tasks = BackgroundTasks()

    first = webhook_module.telegram_webhook(update, first_tasks, "expected-secret")
    duplicate = webhook_module.telegram_webhook(
        update,
        duplicate_tasks,
        "expected-secret",
    )

    assert first == {"ok": True}
    assert duplicate == {"ok": True}
    assert len(first_tasks.tasks) == 1
    assert duplicate_tasks.tasks == []


def test_runtime_configuration_failure_does_not_consume_update_id(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "expected-secret")
    monkeypatch.setattr(
        webhook_module,
        "_update_deduplicator",
        webhook_module.UpdateDeduplicator(capacity=1000),
    )
    update: dict[str, object] = {"update_id": 78, "message": {"text": "Hi"}}

    monkeypatch.setattr(
        webhook_module,
        "get_telegram_runtime",
        lambda: (_ for _ in ()).throw(RuntimeError("not configured")),
    )
    with pytest.raises(RuntimeError, match="not configured"):
        webhook_module.telegram_webhook(
            update,
            BackgroundTasks(),
            "expected-secret",
        )

    runtime = SimpleNamespace(processor=SimpleNamespace(process_update=lambda _update: None))
    monkeypatch.setattr(webhook_module, "get_telegram_runtime", lambda: runtime)
    retry_tasks = BackgroundTasks()

    assert webhook_module.telegram_webhook(
        update,
        retry_tasks,
        "expected-secret",
    ) == {"ok": True}
    assert len(retry_tasks.tasks) == 1


@pytest.mark.parametrize("update", [{}, {"update_id": True}, {"update_id": "1"}])
def test_webhook_rejects_update_without_integer_update_id(
    api_client,
    monkeypatch,
    update: dict[str, object],
) -> None:
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "expected-secret")

    response = api_client.post(
        "/integrations/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "expected-secret"},
        json=update,
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Telegram update_id must be an integer"}


def test_update_deduplicator_evicts_least_recently_used_id() -> None:
    deduplicator = webhook_module.UpdateDeduplicator(capacity=2)

    assert deduplicator.accept(1) is True
    assert deduplicator.accept(2) is True
    assert deduplicator.accept(1) is False  # refresh 1; 2 is now least recent
    assert deduplicator.accept(3) is True
    assert deduplicator.accept(2) is True
