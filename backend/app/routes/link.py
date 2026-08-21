"""Tap-to-connect links for an athlete who only has a phone.

These endpoints are **unauthenticated by design**: the athlete is never logged
into a web session, so the single-use deep-link token *is* the credential. It is
opaque, short-lived, and burned on first use — the same trust model as the
Telegram webhook secret.

Routes:
  GET  /integrations/link/{token}            → provider auth (redirect or form)
  POST /integrations/link/{token}            → store a pasted API key
  GET  /integrations/link/callback/strava    → OAuth return, then back to chat
"""
from __future__ import annotations

import html
import json
import logging
import os
import uuid
from typing import Annotated, Any

import httpx as _httpx
from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..db.models import ConnectorCredentialModel
from ..dependencies import get_db
from ..integrations.google_calendar.oauth_service import (
    GoogleCalendarConfigurationError,
    InvalidOAuthStateError,
)
from ..integrations.google_calendar.oauth_service import callback as google_oauth_callback
from ..integrations.google_calendar.oauth_service import connect as google_oauth_connect
from ..integrations.strava.oauth_service import callback as strava_oauth_callback
from ..integrations.strava.oauth_service import connect as strava_oauth_connect
from ..jobs.registry import register_athlete_jobs
from ..jobs.scheduler import get_scheduler
from ..messaging.outbound import notify_athlete
from ..services.coordinator_service import coordinator_service
from ..services.deep_link_service import (
    InvalidDeepLinkError,
    consume_link,
    consume_pending,
    resolve_link,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations/link", tags=["link"])

DB = Annotated[Session, Depends(get_db)]

_PROVIDER_LABEL = {
    "strava": "Strava",
    "hevy": "Hevy",
    "terra": "Terra",
    "google": "Google Calendar",
}

_KEY_FIELD = {"hevy": "api_key", "terra": "terra_user_id"}

_KEY_PROMPT = {
    "hevy": (
        "Open Hevy → Settings → Developer → generate an API key, then paste it here."
    ),
    "terra": (
        "Paste the Terra user id from the Terra dashboard for the wearable you "
        "want Resilio to read."
    ),
}


# ─── HTML ─────────────────────────────────────────────────────────────────────


def _page(title: str, body: str, status_code: int = 200) -> HTMLResponse:
    return HTMLResponse(
        content=(
            "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(title)}</title>"
            "<style>body{font-family:system-ui,-apple-system,sans-serif;"
            "margin:0;padding:2rem;line-height:1.5;max-width:32rem}"
            "h1{font-size:1.35rem;margin:0 0 .75rem}"
            "input{width:100%;padding:.7rem;font-size:1rem;margin:.5rem 0 1rem;"
            "box-sizing:border-box}"
            "button{padding:.7rem 1.2rem;font-size:1rem;width:100%}</style>"
            f"</head><body>{body}</body></html>"
        ),
        status_code=status_code,
    )


def _done_page(provider: str) -> HTMLResponse:
    label = _PROVIDER_LABEL.get(provider, provider)
    return _page(
        f"{label} connected",
        f"<h1>{html.escape(label)} connected</h1>"
        "<p>Done — go back to Telegram, the coach has the rest.</p>",
    )


def _dead_link_page() -> HTMLResponse:
    return _page(
        "Link expired",
        "<h1>This link is no longer valid</h1>"
        "<p>Links are single-use and expire. Ask the coach for a fresh one in "
        "Telegram.</p>",
        status_code=410,
    )


def _key_form_page(token: str, provider: str) -> HTMLResponse:
    label = _PROVIDER_LABEL.get(provider, provider)
    field = _KEY_FIELD[provider]
    prompt = _KEY_PROMPT[provider]
    return _page(
        f"Connect {label}",
        f"<h1>Connect {html.escape(label)}</h1>"
        f"<p>{html.escape(prompt)}</p>"
        f"<form method='post' action='/integrations/link/{html.escape(token)}'>"
        f"<input name='{field}' autocomplete='off' autocapitalize='off' "
        f"spellcheck='false' required>"
        "<button type='submit'>Connect</button></form>",
    )


# ─── Credentials ──────────────────────────────────────────────────────────────


def _store_key_credential(
    db: Session,
    *,
    athlete_id: str,
    provider: str,
    secret: str,
) -> None:
    """Persist a pasted key the same way the existing connector routes do."""
    extra_json = json.dumps({_KEY_FIELD[provider]: secret})
    row = (
        db.query(ConnectorCredentialModel)
        .filter_by(athlete_id=athlete_id, provider=provider)
        .first()
    )
    if row is None:
        row = ConnectorCredentialModel(
            id=str(uuid.uuid4()),
            athlete_id=athlete_id,
            provider=provider,
        )
        db.add(row)
    row.extra_json = extra_json
    db.commit()


def _after_connect(db: Session, athlete_id: str, provider: str) -> None:
    """Burn the link, register sync jobs, tell the coach, tell the athlete."""
    try:
        consume_pending(db, athlete_id=athlete_id, provider=provider)
    except Exception:
        logger.warning(
            "deep_link_consume_failed",
            extra={"athlete_id": athlete_id, "provider": provider},
            exc_info=True,
        )

    try:
        register_athlete_jobs(athlete_id, provider, get_scheduler())
    except RuntimeError:
        logger.debug("scheduler_not_running", extra={"provider": provider})

    try:
        coordinator_service.dispatch(
            athlete_id,
            "system_silent",
            {"connector_connected": provider},
            db,
        )
    except Exception:
        logger.warning("connector_dispatch_failed", exc_info=True)

    # Reads above autobegin a transaction; outbound delivery needs a clean one.
    if db.in_transaction():
        db.commit()

    label = _PROVIDER_LABEL.get(provider, provider)
    notify_athlete(
        db,
        athlete_id,
        f"{label} connected. I will pull your data from here on.",
        kind="connector_connected",
    )


# ─── Routes ───────────────────────────────────────────────────────────────────


@router.get("/callback/strava", response_class=HTMLResponse)
def strava_callback(code: str, state: str, db: DB) -> HTMLResponse:
    """Strava OAuth return leg — finish the exchange, then send them back."""
    try:
        result = strava_oauth_callback(code=code, state=state, db=db)
    except ValueError:
        return _dead_link_page()
    except _httpx.HTTPStatusError:
        raise HTTPException(status_code=502, detail="Strava token exchange failed")

    _after_connect(db, result["athlete_id"], "strava")
    return _done_page("strava")


@router.get("/callback/google", response_class=HTMLResponse)
def google_callback(code: str, state: str, db: DB) -> HTMLResponse:
    """Google OAuth return leg — finish the exchange, then send them back."""
    try:
        result = google_oauth_callback(code=code, state=state, db=db)
    except InvalidOAuthStateError:
        return _dead_link_page()
    except GoogleCalendarConfigurationError:
        raise HTTPException(status_code=503, detail="Google Calendar is not configured")
    except _httpx.HTTPStatusError:
        raise HTTPException(status_code=502, detail="Google token exchange failed")

    _after_connect(db, result["athlete_id"], "google")
    return _done_page("google")


@router.get("/{token}")
def open_link(token: str, db: DB) -> Any:
    """Resolve a deep link and hand the athlete to the provider."""
    try:
        link = resolve_link(db, token=token)
    except InvalidDeepLinkError:
        return _dead_link_page()

    if link.provider == "strava":
        # Not consumed here: the token burns in the callback, once the athlete
        # has actually connected. See deep_link_service.consume_pending.
        auth_url = strava_oauth_connect(link.athlete_id, db)["auth_url"]
        return RedirectResponse(auth_url, status_code=302)

    if link.provider == "google":
        try:
            auth_url = google_oauth_connect(link.athlete_id, db)["auth_url"]
        except GoogleCalendarConfigurationError:
            raise HTTPException(
                status_code=503, detail="Google Calendar is not configured"
            )
        return RedirectResponse(auth_url, status_code=302)

    if link.provider == "terra":
        widget_url = os.getenv("TERRA_WIDGET_URL", "").strip()
        if widget_url:
            return RedirectResponse(widget_url, status_code=302)

    return _key_form_page(token, link.provider)


@router.post("/{token}", response_class=HTMLResponse)
def submit_link(
    token: str,
    db: DB,
    api_key: Annotated[str, Form()] = "",
    terra_user_id: Annotated[str, Form()] = "",
) -> HTMLResponse:
    """Accept a pasted provider key and burn the token."""
    try:
        link = resolve_link(db, token=token)
    except InvalidDeepLinkError:
        return _dead_link_page()

    if link.provider not in _KEY_FIELD:
        return _dead_link_page()

    secret = (api_key if link.provider == "hevy" else terra_user_id).strip()
    if not secret:
        return _key_form_page(token, link.provider)

    try:
        consume_link(db, token=token)
    except InvalidDeepLinkError:
        return _dead_link_page()

    _store_key_credential(
        db,
        athlete_id=link.athlete_id,
        provider=link.provider,
        secret=secret,
    )
    _after_connect(db, link.athlete_id, link.provider)
    return _done_page(link.provider)
