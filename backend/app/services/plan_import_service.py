"""PlanImportService — parse uploaded plan files with Claude Haiku."""
from __future__ import annotations

import json
import os
from datetime import date

import anthropic
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..db.models import ExternalPlanModel
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
                status_code=422,
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
        Source is set to 'file_import' to distinguish from manual creation.
        Sessions with no session_date default to date.today().
        """
        plan = ExternalPlanService.create_plan(
            athlete_id=athlete_id,
            title=draft.title,
            db=db,
        )
        # Override source — manual creation uses "manual"; file import uses "file_import"
        plan.source = "file_import"
        db.commit()
        db.refresh(plan)

        for s in draft.sessions:
            effective_date = s.session_date if s.session_date is not None else date.today()
            ExternalPlanService.add_session(
                plan_id=plan.id,
                athlete_id=athlete_id,
                session_date=effective_date,
                sport=s.sport,
                title=s.title,
                description=s.description,
                duration_min=s.duration_min,
                db=db,
            )

        db.refresh(plan)
        return plan
