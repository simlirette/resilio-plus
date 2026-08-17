"""Builder for IntentClassificationRequest — Phase D (D3).

Constructs the structured input consumed by classify_intent_service from
an AthleteModel instance and conversation context.
"""
from __future__ import annotations

import json

from ..db.models import AthleteModel
from ..schemas.intent import (
    ConversationContextMinimal,
    IntentClassificationRequest,
    UserProfileMinimal,
)


def build_classify_intent_request(
    athlete: AthleteModel,
    user_message: str,
    last_3_intents: list[str],
    last_user_message: str | None = None,
) -> IntentClassificationRequest:
    """Build an IntentClassificationRequest from AthleteModel + conversation context.

    Args:
        athlete: ORM model with journey_phase, sports_json, clinical_context_flag (if set).
        user_message: The current user message to classify.
        last_3_intents: Up to 3 most recent classify_intent decision values (oldest first).
            Truncated to last 3 if longer.
        last_user_message: The previous user message, if available, for disambiguation.

    Returns:
        IntentClassificationRequest ready for classify_intent_service.
    """
    sports: list[str] = json.loads(athlete.sports_json or "[]")

    # clinical_context_flag is not yet stored on AthleteModel — default None.
    # Phase D will add this column when clinical flags are implemented.
    clinical_flag = getattr(athlete, "clinical_context_flag", None)

    profile = UserProfileMinimal(
        athlete_id=athlete.id,
        journey_phase=athlete.journey_phase,
        sports=sports,
        clinical_context_flag=clinical_flag,
    )

    context = ConversationContextMinimal(
        last_3_intents=last_3_intents[-3:],
        last_user_message=last_user_message,
    )

    return IntentClassificationRequest(
        user_message=user_message,
        conversation_context_minimal=context,
        user_profile_minimal=profile,
    )
