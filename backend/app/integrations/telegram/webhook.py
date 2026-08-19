from __future__ import annotations

import os
import secrets
from collections import OrderedDict
from threading import Lock
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, status

from .runtime import get_telegram_runtime

router = APIRouter(prefix="/integrations/telegram", tags=["telegram"])


class UpdateDeduplicator:
    """Thread-safe, process-local LRU of accepted Telegram update ids."""

    def __init__(self, capacity: int = 1000) -> None:
        if capacity <= 0:
            raise ValueError("Update deduplicator capacity must be positive")
        self._capacity = capacity
        self._seen: OrderedDict[int, None] = OrderedDict()
        self._lock = Lock()

    def accept(self, update_id: int) -> bool:
        with self._lock:
            if update_id in self._seen:
                self._seen.move_to_end(update_id)
                return False
            self._seen[update_id] = None
            if len(self._seen) > self._capacity:
                self._seen.popitem(last=False)
            return True


_update_deduplicator = UpdateDeduplicator()


@router.post("/webhook")
def telegram_webhook(
    update: dict[str, Any],
    background_tasks: BackgroundTasks,
    secret_token: Annotated[
        str | None,
        Header(alias="X-Telegram-Bot-Api-Secret-Token"),
    ] = None,
) -> dict[str, bool]:
    expected_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    if (
        not expected_secret
        or secret_token is None
        or not secrets.compare_digest(
            secret_token.encode("utf-8"),
            expected_secret.encode("utf-8"),
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Telegram webhook secret",
        )
    update_id = update.get("update_id")
    if isinstance(update_id, bool) or not isinstance(update_id, int):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Telegram update_id must be an integer",
        )

    runtime = get_telegram_runtime()
    if not _update_deduplicator.accept(update_id):
        return {"ok": True}
    background_tasks.add_task(runtime.processor.process_update, update)
    return {"ok": True}
