"""
Google Calendar integration — auth, token management, event CRUD.

Only file in the codebase that imports google-api-python-client /
google-auth-oauthlib.  All calendar operations go through GoogleCalendarClient.

Auth flow (desktop OAuth2):
1. First run: InstalledAppFlow opens browser → athlete authorises → token
   persisted to data/google_calendar/token.json.
2. Later runs: load token, silent refresh when expired.

Scope: calendar.events only (read/write events in a calendar we own).
Creating the dedicated "Resilio Training" calendar requires the broader
`calendar` scope — included so the first-run setup can create it once.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/calendar",  # needed once to create calendar
]


# ============================================================
# ERROR TYPES
# ============================================================


class GoogleCalendarError(Exception):
    """Base exception for Google Calendar errors."""


class GoogleCalendarAuthError(GoogleCalendarError):
    """OAuth / token error."""


class GoogleCalendarAPIError(GoogleCalendarError):
    """API request failed."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


# ============================================================
# CLIENT
# ============================================================


class GoogleCalendarClient:
    """
    Thin wrapper around the Google Calendar REST API.

    Encapsulates auth, token refresh, and raw CRUD operations.
    Higher-level sync logic lives in calendar_sync.py.
    """

    def __init__(self, credentials_path: Path, token_path: Path) -> None:
        self._credentials_path = credentials_path
        self._token_path = token_path
        self._service: object = None  # googleapiclient.discovery.Resource

    # ----------------------------------------------------------
    # AUTH
    # ----------------------------------------------------------

    def authenticate(self) -> None:
        """
        Load or obtain OAuth2 credentials and build the service object.

        First call: opens browser for user consent, persists token.
        Subsequent calls: loads token, refreshes silently if expired.

        Raises:
            GoogleCalendarAuthError: If auth fails.
        """
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise GoogleCalendarAuthError(
                "Google client libraries not installed. Run: "
                "poetry add google-api-python-client google-auth google-auth-oauthlib"
            ) from exc

        creds: Optional[Credentials] = None

        if self._token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self._token_path), SCOPES)
            except Exception as exc:
                logger.warning("Failed to load token file, re-authenticating: %s", exc)
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Google Calendar token refreshed")
                except Exception as exc:
                    logger.warning("Token refresh failed, re-authenticating: %s", exc)
                    creds = None

            if not creds:
                if not self._credentials_path.exists():
                    raise GoogleCalendarAuthError(
                        f"credentials.json not found at {self._credentials_path}. "
                        "Download it from Google Cloud Console (OAuth 2.0 Desktop app)."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self._credentials_path), SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info("Google Calendar: new token obtained via browser flow")

            # Persist token
            self._token_path.parent.mkdir(parents=True, exist_ok=True)
            self._token_path.write_text(creds.to_json())

        self._service = build("calendar", "v3", credentials=creds)
        logger.info("Google Calendar service ready")

    def _svc(self) -> object:
        if self._service is None:
            raise GoogleCalendarAuthError("Not authenticated. Call authenticate() first.")
        return self._service

    # ----------------------------------------------------------
    # CALENDAR MANAGEMENT
    # ----------------------------------------------------------

    def ensure_calendar(self, name: str) -> str:
        """
        Return the calendar_id for a calendar named *name*.

        If no calendar with that name exists, creates it and returns the new id.

        Args:
            name: Display name of the calendar (e.g. "Resilio Training").

        Returns:
            calendar_id string.
        """
        svc = self._svc()
        # List all calendars
        result = svc.calendarList().list().execute()  # type: ignore[attr-defined]
        for item in result.get("items", []):
            if item.get("summary") == name:
                logger.debug("Found existing calendar '%s': %s", name, item["id"])
                return str(item["id"])

        # Create new
        body = {
            "summary": name,
            "timeZone": "America/Toronto",
        }
        created = svc.calendars().insert(body=body).execute()  # type: ignore[attr-defined]
        calendar_id: str = created["id"]
        logger.info("Created calendar '%s': %s", name, calendar_id)
        return calendar_id

    # ----------------------------------------------------------
    # EVENT CRUD
    # ----------------------------------------------------------

    def list_managed_events(self, calendar_id: str, time_min: str, time_max: str) -> list[dict]:
        """
        List Resilio-managed events in [time_min, time_max].

        Filters by extendedProperties.private.resilio_managed=1.

        Args:
            calendar_id: Target calendar.
            time_min: RFC3339 string (inclusive).
            time_max: RFC3339 string (exclusive).

        Returns:
            List of event resource dicts.
        """
        svc = self._svc()
        events: list[dict] = []
        page_token: Optional[str] = None

        while True:
            kwargs: dict = dict(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                privateExtendedProperty="resilio_managed=1",
                singleEvents=True,
                orderBy="startTime",
                maxResults=250,
            )
            if page_token:
                kwargs["pageToken"] = page_token

            result = svc.events().list(**kwargs).execute()  # type: ignore[attr-defined]
            events.extend(result.get("items", []))
            page_token = result.get("nextPageToken")
            if not page_token:
                break

        return events

    def create_event(self, calendar_id: str, event: dict) -> dict:
        """
        Insert event into calendar.

        Args:
            calendar_id: Target calendar.
            event: Event resource dict (must include extendedProperties).

        Returns:
            Created event resource dict.
        """
        svc = self._svc()
        result: dict = (
            svc.events()  # type: ignore[attr-defined]
            .insert(calendarId=calendar_id, body=event)
            .execute()
        )
        logger.debug("Created event %s: %s", result.get("id"), result.get("summary"))
        return result

    def patch_event(self, calendar_id: str, event_id: str, patch: dict) -> dict:
        """
        Patch an existing event (partial update).

        Args:
            calendar_id: Target calendar.
            event_id: Google event id.
            patch: Fields to update.

        Returns:
            Updated event resource dict.
        """
        svc = self._svc()
        result: dict = (
            svc.events()  # type: ignore[attr-defined]
            .patch(calendarId=calendar_id, eventId=event_id, body=patch)
            .execute()
        )
        logger.debug("Patched event %s", event_id)
        return result

    def delete_event(self, calendar_id: str, event_id: str) -> None:
        """
        Delete event.

        Args:
            calendar_id: Target calendar.
            event_id: Google event id.
        """
        svc = self._svc()
        svc.events().delete(  # type: ignore[attr-defined]
            calendarId=calendar_id, eventId=event_id
        ).execute()
        logger.debug("Deleted event %s", event_id)
