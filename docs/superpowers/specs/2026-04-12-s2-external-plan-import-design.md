# S-2 — External Plan Import (Claude Haiku) — Design Spec

**Date:** 2026-04-12  
**Branch:** `session/s2-plan-import`  
**Depends on:** S-1 (ExternalPlan CRUD — merged on main)

---

## Overview

Athletes in `tracking_only` mode need to upload an external training plan file and have
Claude Haiku parse it into structured sessions. A two-phase approach (parse → confirm)
lets the athlete review and adjust the draft before it is committed to the database.

---

## Endpoints

| Method | Path | Guard | Description |
|--------|------|-------|-------------|
| POST | `/athletes/{id}/external-plan/import` | `require_tracking_mode` | Upload file, returns `ExternalPlanDraft` |
| POST | `/athletes/{id}/external-plan/import/confirm` | `require_tracking_mode` | Persist draft, returns `ExternalPlanOut` |

### POST /import — multipart upload

- **Body:** `UploadFile` field named `file`
- **Accepted types:** `.txt`, `.csv`, `.ics`, `.pdf` (all decoded as UTF-8 with error replacement)
- **Returns:** `ExternalPlanDraft` (HTTP 200) — no DB write
- **Errors:** 400 if file is empty or unreadable; 422 if Haiku returns unparseable JSON

### POST /import/confirm — persist draft

- **Body:** `ExternalPlanDraft` JSON
- **Returns:** `ExternalPlanOut` (HTTP 201) — creates ExternalPlan + all sessions
- **Behavior:** archives any existing active ExternalPlan (reuses `ExternalPlanService.create_plan`)

---

## Schemas (new additions to `schemas/external_plan.py`)

```python
class ExternalPlanDraftSession(BaseModel):
    session_date: date | None = None
    sport: str
    title: str
    description: str | None = None
    duration_min: int | None = None

class ExternalPlanDraft(BaseModel):
    title: str
    sessions_parsed: int       # count Haiku found
    sessions: list[ExternalPlanDraftSession]
    parse_warnings: list[str]
```

---

## Service: `PlanImportService` (`services/plan_import_service.py`)

### `parse_file(content: str, filename: str) -> ExternalPlanDraft`

1. Build a structured system prompt asking Haiku to extract sessions as JSON
2. Call `anthropic.Anthropic(api_key=...).messages.create(model="claude-haiku-4-5-20251001", ...)`
3. Parse the JSON response into `ExternalPlanDraft`
4. If Haiku returns malformed JSON → raise 422 with parse error in `parse_warnings`

API key sourced from env var `ANTHROPIC_API_KEY` (or `CLAUDE_API_KEY` fallback).

### `confirm_import(athlete_id, draft, db) -> ExternalPlanModel`

1. Call `ExternalPlanService.create_plan(...)` — archives old plan, creates new
2. For each session in `draft.sessions`: call `ExternalPlanService.add_session(...)`
3. Return the refreshed plan model

---

## Haiku Prompt Design

**System prompt:**
> You are a training plan parser. Extract all training sessions from the provided document.
> Return ONLY a JSON object with this exact structure:
> `{"title": str, "sessions": [...], "parse_warnings": [...]}`
> Each session: `{"session_date": "YYYY-MM-DD" | null, "sport": str, "title": str, "description": str | null, "duration_min": int | null}`
> Sport must be one of: running, lifting, swimming, cycling, other.

---

## File Handling

All file types decoded as `content.decode("utf-8", errors="replace")`.
For PDF files this produces lossy text; Haiku will note quality issues in `parse_warnings`.
No additional PDF parsing library (only `anthropic>=0.25` is the authorized new dependency).

---

## Testing Strategy

- **Unit tests** (`tests/backend/services/test_plan_import_service.py`):
  - Mock `anthropic.Anthropic` — test happy path, malformed JSON, empty content
- **API tests** (`tests/backend/api/test_external_plan_import.py`):
  - Mock `PlanImportService.parse_file` — test 200 response, mode guard, unauthenticated
  - Mock `PlanImportService.confirm_import` — test 201 response, session creation
  - Real DB (SQLite in-memory) for confirm endpoint integration tests

---

## Files Changed

| File | Action |
|------|--------|
| `pyproject.toml` | Add `anthropic>=0.25` |
| `backend/app/schemas/external_plan.py` | Add `ExternalPlanDraftSession`, `ExternalPlanDraft` |
| `backend/app/services/plan_import_service.py` | Create |
| `backend/app/routes/external_plan.py` | Add 2 routes |
| `tests/backend/services/test_plan_import_service.py` | Create |
| `tests/backend/api/test_external_plan_import.py` | Create |
