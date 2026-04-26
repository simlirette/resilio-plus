"""Chat routes — Phase D (D4).

Endpoints:
  POST /chat/message                — send a free-form message, get Head Coach response
  GET  /chat/history/{athlete_id}   — last N chat messages for the athlete
"""
from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.models import ChatMessageModel
from ..dependencies import get_current_athlete_id, get_db
from ..graphs.chat_turn import run_chat_turn

router = APIRouter(prefix="/chat", tags=["chat"])

DB = Annotated[Session, Depends(get_db)]
AuthAthleteId = Annotated[str, Depends(get_current_athlete_id)]


# ─── Request / Response schemas ───────────────────────────────────────────────

class ChatMessageRequest(BaseModel):
    athlete_id: str
    user_message: str
    last_3_intents: list[str] = []
    session_log_context: dict[str, Any] | None = None


class ChatMessageResponse(BaseModel):
    final_response: str
    intent_decision: str
    specialists_consulted: list[str]


class ChatHistoryEntry(BaseModel):
    id: str
    role: str
    content: str
    intent_decision: str | None
    specialists_consulted: list[str]
    created_at: str


class ChatHistoryResponse(BaseModel):
    messages: list[ChatHistoryEntry]
    total: int


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/message", response_model=ChatMessageResponse)
def post_chat_message(
    body: ChatMessageRequest,
    db: DB,
    current_athlete_id: AuthAthleteId,
) -> ChatMessageResponse:
    """Send a free-form user message; returns Head Coach (or synthesized) response.

    Auth: only the authenticated athlete may send messages for their own athlete_id.
    """
    if body.athlete_id != current_athlete_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot send messages for another athlete",
        )

    result = run_chat_turn(
        athlete_id=body.athlete_id,
        user_message=body.user_message,
        db=db,
        last_3_intents=body.last_3_intents,
        session_log_context=body.session_log_context,
    )

    return ChatMessageResponse(
        final_response=result["final_response"],
        intent_decision=result["intent_decision"],
        specialists_consulted=result["specialists_consulted"],
    )


@router.get("/history/{target_athlete_id}", response_model=ChatHistoryResponse)
def get_chat_history(
    target_athlete_id: str,
    db: DB,
    current_athlete_id: AuthAthleteId,
    limit: int = Query(default=50, ge=1, le=200),
) -> ChatHistoryResponse:
    """Return the last N chat messages for the athlete (user + assistant pairs)."""
    if target_athlete_id != current_athlete_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot read chat history for another athlete",
        )

    rows = (
        db.query(ChatMessageModel)
        .filter(ChatMessageModel.athlete_id == target_athlete_id)
        .order_by(ChatMessageModel.created_at.desc())
        .limit(limit)
        .all()
    )

    entries = [
        ChatHistoryEntry(
            id=row.id,
            role=row.role,
            content=row.content,
            intent_decision=row.intent_decision,
            specialists_consulted=json.loads(row.specialists_consulted or "[]"),
            created_at=row.created_at.isoformat(),
        )
        for row in reversed(rows)  # oldest first in returned order
    ]

    return ChatHistoryResponse(messages=entries, total=len(entries))
