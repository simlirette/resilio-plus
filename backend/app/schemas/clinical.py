"""Clinical context flag — Phase D (D2).

ClinicalContextFlag is a Literal union representing active clinical sensitivity modes.
Used by classify_intent to propagate clinical framing to specialist agents.

DEP-C10-003 / D2.
"""
from __future__ import annotations

from typing import Literal

# ClinicalContextFlag — injected into IntentClassificationRequest and specialist payloads
# when an active clinical frame is in effect for the athlete.
#
#   tca     — troubles du comportement alimentaire (declared or suspected)
#   red_s   — Relative Energy Deficiency in Sport
#   ots_nfor — overtraining syndrome / non-functional overreaching
#
# None = no active clinical context.

ClinicalContextFlag = Literal["tca", "red_s", "ots_nfor"] | None
