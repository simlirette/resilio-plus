"""Correlation ID + athlete ID ContextVars and middleware."""
from __future__ import annotations

import re
import uuid
from contextvars import ContextVar
from typing import Any, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="-")
athlete_id_ctx: ContextVar[Optional[str]] = ContextVar("athlete_id", default=None)

_VALID_CID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_HEADER = "X-Request-ID"


def get_correlation_id() -> str:
    return correlation_id_ctx.get()


def get_athlete_id() -> Optional[str]:
    return athlete_id_ctx.get()


def _coerce_cid(incoming: str | None) -> str:
    if incoming and _VALID_CID.match(incoming):
        return incoming
    return str(uuid.uuid4())


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Reads/generates X-Request-ID, sets ContextVar, echoes header back on response."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        cid = _coerce_cid(request.headers.get(_HEADER))
        token = correlation_id_ctx.set(cid)
        try:
            response: Response = await call_next(request)
        finally:
            correlation_id_ctx.reset(token)
        response.headers[_HEADER] = cid
        return response
