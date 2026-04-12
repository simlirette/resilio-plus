"""Unit tests for PlanImportService — Anthropic client is always mocked."""
from __future__ import annotations

import json
import uuid
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import models as _models  # noqa: registers all ORM models
from app.db.database import Base
from app.db.models import AthleteModel
from app.schemas.external_plan import ExternalPlanDraft, ExternalPlanDraftSession
from app.services.plan_import_service import PlanImportService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_pragma(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    return engine


def _make_athlete(db, mode: str = "tracking_only") -> str:
    athlete_id = str(uuid.uuid4())
    athlete = AthleteModel(
        id=athlete_id,
        name="Test",
        age=30,
        sex="M",
        weight_kg=70.0,
        height_cm=175.0,
        primary_sport="running",
        hours_per_week=8.0,
        sports_json='["running"]',
        goals_json='["fitness"]',
        available_days_json='[0,2,4]',
        equipment_json='[]',
        coaching_mode=mode,
    )
    db.add(athlete)
    db.commit()
    return athlete_id


def _mock_haiku_response(payload: dict) -> MagicMock:
    """Return a mock that looks like anthropic.types.Message with text content."""
    content_block = MagicMock()
    content_block.text = json.dumps(payload)
    message = MagicMock()
    message.content = [content_block]
    return message


# ---------------------------------------------------------------------------
# parse_file — happy path
# ---------------------------------------------------------------------------

def test_parse_file_returns_draft_with_sessions():
    haiku_payload = {
        "title": "Spring Marathon Block",
        "sessions": [
            {
                "session_date": "2026-05-01",
                "sport": "running",
                "title": "Easy 8k",
                "description": "Recovery run",
                "duration_min": 45,
            },
            {
                "session_date": "2026-05-03",
                "sport": "lifting",
                "title": "Strength A",
                "description": None,
                "duration_min": 60,
            },
        ],
        "parse_warnings": [],
    }
    with patch("app.services.plan_import_service.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _mock_haiku_response(haiku_payload)
        draft = PlanImportService.parse_file("Day 1: Easy 8k...", "plan.txt")

    assert isinstance(draft, ExternalPlanDraft)
    assert draft.title == "Spring Marathon Block"
    assert draft.sessions_parsed == 2
    assert len(draft.sessions) == 2
    assert draft.sessions[0].sport == "running"
    assert draft.sessions[1].title == "Strength A"
    assert draft.parse_warnings == []


def test_parse_file_returns_warnings_from_haiku():
    haiku_payload = {
        "title": "Unknown Plan",
        "sessions": [],
        "parse_warnings": ["Could not determine session dates"],
    }
    with patch("app.services.plan_import_service.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _mock_haiku_response(haiku_payload)
        draft = PlanImportService.parse_file("some unstructured text", "notes.txt")

    assert draft.sessions_parsed == 0
    assert "Could not determine session dates" in draft.parse_warnings


def test_parse_file_session_date_can_be_null():
    haiku_payload = {
        "title": "Undated Plan",
        "sessions": [
            {
                "session_date": None,
                "sport": "running",
                "title": "Run",
                "description": None,
                "duration_min": None,
            }
        ],
        "parse_warnings": [],
    }
    with patch("app.services.plan_import_service.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _mock_haiku_response(haiku_payload)
        draft = PlanImportService.parse_file("Run sometime", "plan.txt")

    assert draft.sessions[0].session_date is None


# ---------------------------------------------------------------------------
# parse_file — error handling
# ---------------------------------------------------------------------------

def test_parse_file_malformed_json_raises_422():
    from fastapi import HTTPException

    with patch("app.services.plan_import_service.anthropic.Anthropic") as MockClient:
        content_block = MagicMock()
        content_block.text = "This is not JSON"
        message = MagicMock()
        message.content = [content_block]
        MockClient.return_value.messages.create.return_value = message

        with pytest.raises(HTTPException) as exc_info:
            PlanImportService.parse_file("some content", "plan.txt")

    assert exc_info.value.status_code == 422
    assert "parse" in exc_info.value.detail.lower()


def test_parse_file_empty_content_raises_400():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        PlanImportService.parse_file("", "plan.txt")
    assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# confirm_import — integrates with ExternalPlanService via real SQLite DB
# ---------------------------------------------------------------------------

def test_confirm_import_creates_plan_and_sessions():
    engine = _make_engine()
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(engine)

    with TestSession() as db:
        athlete_id = _make_athlete(db)

        draft = ExternalPlanDraft(
            title="Coach Plan",
            sessions_parsed=2,
            sessions=[
                ExternalPlanDraftSession(
                    session_date=date(2026, 5, 1),
                    sport="running",
                    title="Easy 5k",
                    description=None,
                    duration_min=30,
                ),
                ExternalPlanDraftSession(
                    session_date=None,  # None → defaults to today
                    sport="lifting",
                    title="Strength",
                    description="Upper body",
                    duration_min=None,
                ),
            ],
            parse_warnings=[],
        )

        plan = PlanImportService.confirm_import(
            athlete_id=athlete_id,
            draft=draft,
            db=db,
        )

        # Access lazy-loaded attributes inside session context
        assert plan.title == "Coach Plan"
        assert plan.source == "file_import"
        assert plan.status == "active"
        assert len(plan.sessions) == 2
        sports = {s.sport for s in plan.sessions}
        assert sports == {"running", "lifting"}


def test_confirm_import_source_is_file_import():
    """Source must be 'file_import' to distinguish from manual creation."""
    engine = _make_engine()
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(engine)

    with TestSession() as db:
        athlete_id = _make_athlete(db)

        draft = ExternalPlanDraft(
            title="My Plan",
            sessions_parsed=0,
            sessions=[],
            parse_warnings=[],
        )

        plan = PlanImportService.confirm_import(
            athlete_id=athlete_id,
            draft=draft,
            db=db,
        )

        assert plan.source == "file_import"


def test_confirm_import_null_session_date_defaults_to_today():
    """Sessions with no date get session_date = date.today()."""
    engine = _make_engine()
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(engine)

    with TestSession() as db:
        athlete_id = _make_athlete(db)

        draft = ExternalPlanDraft(
            title="Dateless Plan",
            sessions_parsed=1,
            sessions=[
                ExternalPlanDraftSession(
                    session_date=None,
                    sport="running",
                    title="Run",
                ),
            ],
            parse_warnings=[],
        )

        plan = PlanImportService.confirm_import(
            athlete_id=athlete_id,
            draft=draft,
            db=db,
        )

        # Access lazy-loaded attributes inside session context
        assert len(plan.sessions) == 1
        assert plan.sessions[0].session_date == date.today()
