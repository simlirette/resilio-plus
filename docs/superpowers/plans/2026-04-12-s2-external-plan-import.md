# S-2 External Plan Import (Claude Haiku) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two endpoints — POST /import (Haiku parses uploaded file → ExternalPlanDraft) and POST /import/confirm (persists draft as ExternalPlan + sessions) — both guarded by require_tracking_mode.

**Architecture:** A new `PlanImportService` calls the Anthropic Messages API (Claude Haiku) to parse file content into a structured draft. The confirm step reuses the existing `ExternalPlanService` CRUD methods. No DB writes happen during parsing. All file types are decoded as UTF-8 text — Haiku records quality issues in `parse_warnings`.

**Tech Stack:** FastAPI (multipart upload via `python-multipart`), Anthropic SDK (`anthropic>=0.25`, `claude-haiku-4-5-20251001`), SQLAlchemy + SQLite in-memory (tests), pytest + `unittest.mock.patch`.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `pyproject.toml` | Modify | Add `anthropic>=0.25` dependency |
| `backend/app/schemas/external_plan.py` | Modify | Add `ExternalPlanDraftSession` + `ExternalPlanDraft` |
| `backend/app/services/plan_import_service.py` | Create | Haiku parsing + confirm logic |
| `backend/app/routes/external_plan.py` | Modify | Add `/import` and `/import/confirm` routes |
| `tests/backend/services/test_plan_import_service.py` | Create | Unit tests for service (Anthropic client mocked) |
| `tests/backend/api/test_external_plan_import.py` | Create | API integration tests (service mocked) |

---

### Task 1: Add anthropic dependency + new Pydantic schemas

**Files:**
- Modify: `pyproject.toml`
- Modify: `backend/app/schemas/external_plan.py`

- [ ] **Step 1: Add anthropic to pyproject.toml**

In `pyproject.toml`, under `dependencies`, add after `"langgraph..."`:

```toml
    "anthropic>=0.25,<1.0",
```

- [ ] **Step 2: Install the dependency**

```bash
cd C:/Users/simon/resilio-plus
poetry add anthropic
```

Expected: resolves and installs `anthropic` package, lockfile updated.

- [ ] **Step 3: Add schemas to external_plan.py**

In `backend/app/schemas/external_plan.py`, after the existing imports, add at the bottom of the file:

```python
class ExternalPlanDraftSession(BaseModel):
    session_date: date | None = None
    sport: str
    title: str
    description: str | None = None
    duration_min: int | None = None


class ExternalPlanDraft(BaseModel):
    title: str
    sessions_parsed: int
    sessions: list[ExternalPlanDraftSession]
    parse_warnings: list[str]
```

- [ ] **Step 4: Verify import works**

```bash
cd C:/Users/simon/resilio-plus
poetry run python -c "from app.schemas.external_plan import ExternalPlanDraft, ExternalPlanDraftSession; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml poetry.lock backend/app/schemas/external_plan.py
git commit -m "feat(s2): add anthropic dep + ExternalPlanDraft schemas"
```

---

### Task 2: Create PlanImportService (TDD — red phase)

**Files:**
- Create: `tests/backend/services/test_plan_import_service.py`
- Create: `backend/app/services/plan_import_service.py` (stub — just enough to fail)

- [ ] **Step 1: Write failing tests**

Create `tests/backend/services/test_plan_import_service.py`:

```python
"""Unit tests for PlanImportService — Anthropic client is always mocked."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.external_plan import ExternalPlanDraft
from app.services.plan_import_service import PlanImportService


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
            {"session_date": None, "sport": "running", "title": "Run", "description": None, "duration_min": None}
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
# confirm_import — integrates with ExternalPlanService
# ---------------------------------------------------------------------------

def test_confirm_import_creates_plan_and_sessions():
    from datetime import date
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.db.database import Base
    from app.db import models  # noqa: registers ORM models
    from app.schemas.external_plan import ExternalPlanDraftSession, ExternalPlanDraft

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    TestSession = sessionmaker(engine)

    # Create athlete
    import uuid
    from app.models.schemas import AthleteModel
    athlete_id = str(uuid.uuid4())
    with TestSession() as db:
        athlete = AthleteModel(
            id=athlete_id,
            name="Bob",
            age=28,
            sex="M",
            weight_kg=75.0,
            height_cm=180.0,
            sports=["running"],
            primary_sport="running",
            goals=["race"],
            available_days=[0, 2, 4],
            hours_per_week=8.0,
            email="bob@test.com",
            hashed_password="x",
            coaching_mode="tracking_only",
        )
        db.add(athlete)
        db.commit()

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
                    session_date=None,
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

    assert plan.title == "Coach Plan"
    assert plan.source == "file"
    assert plan.status == "active"
    assert len(plan.sessions) == 2
    sports = {s.sport for s in plan.sessions}
    assert sports == {"running", "lifting"}
```

- [ ] **Step 2: Create stub service so import doesn't fail at collection**

Create `backend/app/services/plan_import_service.py`:

```python
"""PlanImportService — parse uploaded plan files with Claude Haiku."""
from __future__ import annotations

import anthropic
from sqlalchemy.orm import Session

from ..schemas.external_plan import ExternalPlanDraft
from ..models.schemas import ExternalPlanModel


class PlanImportService:

    @staticmethod
    def parse_file(content: str, filename: str) -> ExternalPlanDraft:
        raise NotImplementedError

    @staticmethod
    def confirm_import(
        athlete_id: str,
        draft: ExternalPlanDraft,
        db: Session,
    ) -> ExternalPlanModel:
        raise NotImplementedError
```

- [ ] **Step 3: Run tests — verify red**

```bash
cd C:/Users/simon/resilio-plus
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/services/test_plan_import_service.py -v 2>&1 | tail -20
```

Expected: multiple FAILED with `NotImplementedError`.

---

### Task 3: Implement PlanImportService — green phase

**Files:**
- Modify: `backend/app/services/plan_import_service.py`

- [ ] **Step 1: Implement parse_file and confirm_import**

Replace `backend/app/services/plan_import_service.py` entirely:

```python
"""PlanImportService — parse uploaded plan files with Claude Haiku."""
from __future__ import annotations

import json
import os

import anthropic
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models.schemas import ExternalPlanModel
from ..schemas.external_plan import ExternalPlanDraft, ExternalPlanDraftSession
from .external_plan_service import ExternalPlanService

_SYSTEM_PROMPT = """You are a training plan parser. Extract all training sessions from the provided document.
Return ONLY a valid JSON object with this exact structure:
{
  "title": "<plan title or 'Imported Plan' if unknown>",
  "sessions": [
    {
      "session_date": "YYYY-MM-DD or null",
      "sport": "<one of: running, lifting, swimming, cycling, other>",
      "title": "<session title>",
      "description": "<detail or null>",
      "duration_min": <integer or null>
    }
  ],
  "parse_warnings": ["<any issues found>"]
}
Do not include any text outside the JSON object."""

_MODEL = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 4096
_MAX_CONTENT_CHARS = 40_000  # ~10k tokens — stay within Haiku context


class PlanImportService:

    @staticmethod
    def parse_file(content: str, filename: str) -> ExternalPlanDraft:
        """Call Claude Haiku to parse file text into an ExternalPlanDraft.

        Raises 400 if content is empty.
        Raises 422 if Haiku returns non-JSON.
        """
        if not content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty or could not be decoded",
            )

        # Truncate to protect against huge files
        truncated = content[:_MAX_CONTENT_CHARS]

        api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY", "")
        client = anthropic.Anthropic(api_key=api_key)

        message = client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Filename: {filename}\n\n{truncated}",
                }
            ],
        )

        raw_text = message.content[0].text

        try:
            data = json.loads(raw_text)
        except (json.JSONDecodeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not parse Haiku response as JSON: {exc}",
            ) from exc

        sessions = [ExternalPlanDraftSession(**s) for s in data.get("sessions", [])]

        return ExternalPlanDraft(
            title=data.get("title", "Imported Plan"),
            sessions_parsed=len(sessions),
            sessions=sessions,
            parse_warnings=data.get("parse_warnings", []),
        )

    @staticmethod
    def confirm_import(
        athlete_id: str,
        draft: ExternalPlanDraft,
        db: Session,
    ) -> ExternalPlanModel:
        """Persist a reviewed ExternalPlanDraft as an active ExternalPlan with sessions.

        Archives any existing active plan (via ExternalPlanService.create_plan).
        Source is set to 'file' to distinguish from manual creation.
        """
        plan = ExternalPlanService.create_plan(
            athlete_id=athlete_id,
            title=draft.title,
            db=db,
        )
        # Override source to 'file'
        plan.source = "file"
        db.commit()
        db.refresh(plan)

        for s in draft.sessions:
            ExternalPlanService.add_session(
                plan_id=plan.id,
                athlete_id=athlete_id,
                session_date=s.session_date,
                sport=s.sport,
                title=s.title,
                description=s.description,
                duration_min=s.duration_min,
                db=db,
            )

        db.refresh(plan)
        return plan
```

- [ ] **Step 2: Run service tests — verify green**

```bash
cd C:/Users/simon/resilio-plus
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/services/test_plan_import_service.py -v 2>&1 | tail -20
```

Expected: all PASSED.

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/plan_import_service.py tests/backend/services/test_plan_import_service.py
git commit -m "feat(s2): PlanImportService — Haiku parse + confirm (TDD green)"
```

---

### Task 4: Add import routes to external_plan router (TDD — red phase)

**Files:**
- Create: `tests/backend/api/test_external_plan_import.py`
- Modify: `backend/app/routes/external_plan.py`

- [ ] **Step 1: Write API tests**

Create `tests/backend/api/test_external_plan_import.py`:

```python
"""API integration tests for External Plan Import endpoints."""
from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db import models  # noqa: registers ORM models
from app.dependencies import get_db
from app.main import app
from app.schemas.external_plan import ExternalPlanDraft, ExternalPlanDraftSession


def _make_test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


@pytest.fixture()
def client():
    engine = _make_test_engine()
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(engine)

    def override_get_db():
        with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def _base_onboarding(**overrides):
    from datetime import date
    base = {
        "name": "Alice",
        "age": 30,
        "sex": "F",
        "weight_kg": 60.0,
        "height_cm": 168.0,
        "sports": ["running"],
        "primary_sport": "running",
        "goals": ["stay fit"],
        "available_days": [0, 2, 4],
        "hours_per_week": 8.0,
        "email": "alice@test.com",
        "password": "password123",
        "plan_start_date": str(date.today()),
    }
    return {**base, **overrides}


def _register(client, **overrides):
    payload = _base_onboarding(**overrides)
    resp = client.post("/athletes/onboarding", json=payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return body["access_token"], body["athlete"]["id"]


def _authed(client, token):
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def _make_draft(title="Coach Plan", num_sessions=1):
    from datetime import date
    sessions = [
        ExternalPlanDraftSession(
            session_date=date(2026, 5, 1),
            sport="running",
            title=f"Session {i+1}",
        )
        for i in range(num_sessions)
    ]
    return ExternalPlanDraft(
        title=title,
        sessions_parsed=num_sessions,
        sessions=sessions,
        parse_warnings=[],
    )


# ---------------------------------------------------------------------------
# POST /athletes/{id}/external-plan/import
# ---------------------------------------------------------------------------

def test_import_returns_draft_for_tracking_athlete(client):
    token, athlete_id = _register(
        client, email="importer@test.com", coaching_mode="tracking_only"
    )
    _authed(client, token)

    draft = _make_draft(num_sessions=2)
    with patch("app.routes.external_plan.PlanImportService.parse_file", return_value=draft):
        file_content = b"Day 1: Easy run 5k\nDay 3: Strength training"
        resp = client.post(
            f"/athletes/{athlete_id}/external-plan/import",
            files={"file": ("plan.txt", io.BytesIO(file_content), "text/plain")},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["title"] == "Coach Plan"
    assert body["sessions_parsed"] == 2
    assert len(body["sessions"]) == 2
    assert "parse_warnings" in body


def test_import_rejected_for_full_mode_athlete(client):
    token, athlete_id = _register(client, email="full@test.com")
    _authed(client, token)
    file_content = b"Some plan"
    resp = client.post(
        f"/athletes/{athlete_id}/external-plan/import",
        files={"file": ("plan.txt", io.BytesIO(file_content), "text/plain")},
    )
    assert resp.status_code == 403


def test_import_unauthenticated_rejected(client):
    file_content = b"Some plan"
    resp = client.post(
        "/athletes/some-id/external-plan/import",
        files={"file": ("plan.txt", io.BytesIO(file_content), "text/plain")},
    )
    assert resp.status_code == 401


def test_import_returns_warnings_from_service(client):
    token, athlete_id = _register(
        client, email="warn@test.com", coaching_mode="tracking_only"
    )
    _authed(client, token)

    draft = ExternalPlanDraft(
        title="Partial Plan",
        sessions_parsed=0,
        sessions=[],
        parse_warnings=["Could not detect dates"],
    )
    with patch("app.routes.external_plan.PlanImportService.parse_file", return_value=draft):
        resp = client.post(
            f"/athletes/{athlete_id}/external-plan/import",
            files={"file": ("plan.txt", io.BytesIO(b"vague text"), "text/plain")},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert "Could not detect dates" in body["parse_warnings"]


# ---------------------------------------------------------------------------
# POST /athletes/{id}/external-plan/import/confirm
# ---------------------------------------------------------------------------

def test_confirm_creates_plan_and_returns_plan_out(client):
    token, athlete_id = _register(
        client, email="confirm@test.com", coaching_mode="tracking_only"
    )
    _authed(client, token)

    draft = _make_draft(title="Confirmed Plan", num_sessions=2)

    with patch("app.routes.external_plan.PlanImportService.confirm_import") as mock_confirm:
        # Return a realistic ExternalPlanOut-compatible dict via the actual service
        # (we test real DB integration in test_plan_import_service.py)
        from app.schemas.external_plan import ExternalPlanOut, ExternalSessionOut
        from datetime import datetime, date

        mock_plan = MagicMock()
        mock_plan.id = "plan-123"
        mock_plan.athlete_id = athlete_id
        mock_plan.title = "Confirmed Plan"
        mock_plan.source = "file"
        mock_plan.status = "active"
        mock_plan.start_date = None
        mock_plan.end_date = None
        mock_plan.created_at = datetime(2026, 4, 12)
        mock_plan.sessions = []
        mock_confirm.return_value = mock_plan

        resp = client.post(
            f"/athletes/{athlete_id}/external-plan/import/confirm",
            json=draft.model_dump(mode="json"),
        )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["title"] == "Confirmed Plan"
    assert body["source"] == "file"
    assert body["status"] == "active"


def test_confirm_rejected_for_full_mode_athlete(client):
    token, athlete_id = _register(client, email="full2@test.com")
    _authed(client, token)
    draft = _make_draft()
    resp = client.post(
        f"/athletes/{athlete_id}/external-plan/import/confirm",
        json=draft.model_dump(mode="json"),
    )
    assert resp.status_code == 403


def test_confirm_unauthenticated_rejected(client):
    draft = _make_draft()
    resp = client.post(
        "/athletes/some-id/external-plan/import/confirm",
        json=draft.model_dump(mode="json"),
    )
    assert resp.status_code == 401
```

- [ ] **Step 2: Run tests — verify they fail (routes don't exist yet)**

```bash
cd C:/Users/simon/resilio-plus
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/api/test_external_plan_import.py -v 2>&1 | tail -20
```

Expected: FAILED with 404 or import errors.

---

### Task 5: Add import routes — green phase

**Files:**
- Modify: `backend/app/routes/external_plan.py`

- [ ] **Step 1: Add imports and two new routes**

At the top of `backend/app/routes/external_plan.py`, add to the existing imports:

```python
from fastapi import File, UploadFile
from ..schemas.external_plan import ExternalPlanDraft
from ..services.plan_import_service import PlanImportService
```

Then append these two routes at the bottom of the file:

```python

@router.post(
    "/{athlete_id}/external-plan/import",
    response_model=ExternalPlanDraft,
    status_code=200,
)
async def import_plan_file(
    athlete_id: str,
    athlete: TrackingAthlete,
    db: DB,
    file: UploadFile = File(...),
) -> ExternalPlanDraft:
    """Upload a plan file; Claude Haiku parses it into an ExternalPlanDraft.

    No DB write — the athlete reviews the draft and calls /import/confirm to persist.
    """
    raw = await file.read()
    content = raw.decode("utf-8", errors="replace")
    filename = file.filename or "upload"
    return PlanImportService.parse_file(content=content, filename=filename)


@router.post(
    "/{athlete_id}/external-plan/import/confirm",
    response_model=ExternalPlanOut,
    status_code=201,
)
def confirm_plan_import(
    athlete_id: str,
    body: ExternalPlanDraft,
    athlete: TrackingAthlete,
    db: DB,
) -> ExternalPlanOut:
    """Persist a reviewed ExternalPlanDraft as the athlete's active ExternalPlan."""
    plan = PlanImportService.confirm_import(
        athlete_id=athlete_id,
        draft=body,
        db=db,
    )
    db.refresh(plan)
    return ExternalPlanOut.model_validate(plan)
```

- [ ] **Step 2: Run API tests — verify green**

```bash
cd C:/Users/simon/resilio-plus
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/api/test_external_plan_import.py -v 2>&1 | tail -20
```

Expected: all PASSED.

- [ ] **Step 3: Run full test suite — verify no regressions**

```bash
cd C:/Users/simon/resilio-plus
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/ 2>&1 | tail -10
```

Expected: ≥ 1243 passed, 0 new failures.

- [ ] **Step 4: Commit**

```bash
git add backend/app/routes/external_plan.py tests/backend/api/test_external_plan_import.py
git commit -m "feat(s2): POST /import + /import/confirm routes with require_tracking_mode"
```

---

### Task 6: Branch setup, SESSION_REPORT, and push

**Files:**
- Modify: `SESSION_REPORT.md`

- [ ] **Step 1: Ensure branch exists**

```bash
git checkout main && git pull && git checkout -b session/s2-plan-import 2>/dev/null || git checkout session/s2-plan-import
```

(If you committed during earlier tasks while still on main, cherry-pick or reset as needed.)

- [ ] **Step 2: Append S-2 entry to SESSION_REPORT.md**

After the last `---` separator in SESSION_REPORT.md, append:

```markdown
---

## S-2 — External Plan Import (Claude Haiku) (2026-04-12)

**Branche :** `session/s2-plan-import`  
**Statut :** ✅ Terminé

### Ce qui a été fait

| Composant | Fichier | Tests |
|---|---|---|
| ExternalPlanDraft schemas | `backend/app/schemas/external_plan.py` | — |
| PlanImportService | `backend/app/services/plan_import_service.py` | unit tests ✅ |
| Routes FastAPI (2 endpoints) | `backend/app/routes/external_plan.py` | API tests ✅ |
| anthropic>=0.25 | `pyproject.toml` | — |

**Endpoints livrés :**
- `POST /athletes/{id}/external-plan/import` [require_tracking_mode] — multipart upload → ExternalPlanDraft
- `POST /athletes/{id}/external-plan/import/confirm` [require_tracking_mode] — ExternalPlanDraft → ExternalPlanOut

### Décisions notables

1. **Source="file"** : Les plans importés via fichier ont `source="file"` (vs `"manual"` pour la création manuelle).
2. **Pas d'écriture DB au parsing** : `/import` est non-destructif — l'athlète révise le draft avant de confirmer.
3. **Décodage UTF-8 universel** : Tous les types de fichier sont décodés en UTF-8 (errors='replace'). Pour les PDFs, Haiku note les problèmes dans `parse_warnings`.
4. **Truncation 40k chars** : Protection contre les fichiers très lourds — au-delà, Haiku ne verrait que le début.

### Invariants vérifiés

- `pytest tests/` → ≥ 1243 passed ✅
- Aucune régression sur les tests existants ✅
```

- [ ] **Step 3: Commit SESSION_REPORT**

```bash
git add SESSION_REPORT.md docs/superpowers/specs/2026-04-12-s2-external-plan-import-design.md docs/superpowers/plans/2026-04-12-s2-external-plan-import.md
git commit -m "docs(s2): SESSION_REPORT + design spec + implementation plan"
```

- [ ] **Step 4: Push branch**

```bash
git push -u origin session/s2-plan-import
```

Expected: branch pushed, tracking set.
