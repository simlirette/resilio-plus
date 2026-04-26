# Phase D Audit — Conversational Coaching Layer

_Generated: 2026-04-26 | Branch: feat/phase-d-d1-coordinator_

## Overview

Phase D adds a full conversational coaching layer on top of the frozen V1 backend.
All LLM orchestration is additive — zero V1 backend modifications.

---

## Deliverables

### D1 — CoordinatorService skeleton

| Item | Status | File |
|---|---|---|
| `CoordinatorService` class | ✅ | `backend/app/services/coordinator_service.py` |
| `plan_generation_state` extension (AgentState) | ✅ | `backend/app/graphs/chat_turn.py` |
| Route event → handler dispatch | ✅ | `coordinator_service.py` |

### D2 — Schemas + intent types

| Item | Status | File |
|---|---|---|
| `IntentClassification` (Pydantic) | ✅ | `backend/app/schemas/intent.py` |
| `IntentClassificationRequest` | ✅ | `backend/app/schemas/intent.py` |
| `ClinicalContextFlag` enum | ✅ | `backend/app/schemas/clinical.py` |
| `SpecialistTarget`, `ConversationContextMinimal`, `UserProfileMinimal` | ✅ | `backend/app/schemas/intent.py` |

### D3 — classify_intent service

| Item | Status | File |
|---|---|---|
| `classify_intent()` — Haiku 4.5 gateway | ✅ | `backend/app/services/classify_intent_service.py` |
| XML `<contract_payload>` parser | ✅ | `classify_intent_service.py` |
| `track_agent_call("classify_intent")` observability | ✅ | `classify_intent_service.py` |
| `build_classify_intent_request()` builder | ✅ | `backend/app/core/classify_intent_builder.py` |
| Latency target: < 500ms (800ms hard limit) | ✅ | `_TIMEOUT_SECONDS = 0.8` |
| System prompt | ✅ | `docs/prompts/classify-intent.md` |

### D4 — chat_turn graph (HEAD_COACH_DIRECT + SPECIALIST_TECHNICAL)

| Item | Status | File |
|---|---|---|
| `run_chat_turn()` entry point | ✅ | `backend/app/graphs/chat_turn.py` |
| `HEAD_COACH_DIRECT` path (1 LLM call) | ✅ | `chat_turn.py` |
| `SPECIALIST_TECHNICAL` single-specialist path (2 LLM calls) | ✅ | `chat_turn.py` |
| `handle_session_log()` — RPE deviation → Lifting (DEP-C4-001) | ✅ | `chat_turn.py` |
| `POST /chat/message` endpoint | ✅ | `backend/app/routes/chat.py` |
| `GET /chat/history/{athlete_id}` endpoint | ✅ | `backend/app/routes/chat.py` |
| `ChatMessageModel` persistence | ✅ | `backend/app/db/models.py` |

### D5 — Specialist chain + clinical escalation

| Item | Status | File |
|---|---|---|
| Specialist chain (max 3, parallel consultation) | ✅ | `chat_turn.py` |
| `CLINICAL_ESCALATION_IMMEDIATE` routing | ✅ | `chat_turn.py` |
| `OUT_OF_SCOPE` guard response | ✅ | `chat_turn.py` |
| `CLARIFICATION_NEEDED` + `clarification_axes` in response | ✅ | `chat_turn.py` |
| `CrossDisciplineInterferenceService` (DEP-C4-004) | ✅ | `backend/app/services/cross_discipline_service.py` |

### D6 — Injury report (DEP-C3-001)

| Item | Status | File |
|---|---|---|
| `run_injury_report()` — Recovery consulted | ✅ | `chat_turn.py` |
| `escalate_to_takeover` detection (RA7) | ✅ | `chat_turn.py` |
| `ValueError` when payload missing on escalate | ✅ | `chat_turn.py` |
| `RecoveryCoachView` schema | ✅ | `backend/app/schemas/recovery_view.py` |
| `build_recovery_view()` builder | ✅ | `backend/app/core/recovery_view_builder.py` |

### D7 — Onboarding graph, blocs 1-3

| Item | Status | File |
|---|---|---|
| `run_onboarding_start()` — new or resume thread | ✅ | `backend/app/graphs/onboarding.py` |
| `run_onboarding_respond()` — advance bloc | ✅ | `onboarding.py` |
| In-memory `_thread_states` dict | ✅ | `onboarding.py` |
| `active_onboarding_thread_id` persistence | ✅ | `onboarding.py` |
| `POST /onboarding/start` endpoint | ✅ | `backend/app/routes/onboarding_d7.py` |
| `POST /onboarding/respond` endpoint | ✅ | `onboarding_d7.py` |

### D8 — Onboarding blocs 4-6 + injury mid-onboarding (DEP-C3-003)

| Item | Status | File |
|---|---|---|
| Blocs 4-6: sport_history, methodology_preferences, scope_confirmation | ✅ | `onboarding.py` |
| Bloc 6 completion → `journey_phase = "baseline_pending_confirmation"` | ✅ | `onboarding.py` |
| `suspend_onboarding_for_injury()` | ✅ | `onboarding.py` |
| `resume_onboarding_after_recovery()` | ✅ | `onboarding.py` |

### D9 — followup_transition graph

| Item | Status | File |
|---|---|---|
| `run_followup_start()` — present_baseline step | ✅ | `backend/app/graphs/followup_transition.py` |
| `run_followup_respond()` — 2-step HITL | ✅ | `followup_transition.py` |
| `adjust_objective` → `onboarding_reentry_active=True` | ✅ | `followup_transition.py` |
| Completion → `journey_phase = "steady_state"` | ✅ | `followup_transition.py` |
| `POST /followup/start`, `POST /followup/respond` | ✅ | `backend/app/routes/followup.py` |

### D10 — recovery_takeover graph (DEP-C3-002)

| Item | Status | File |
|---|---|---|
| `run_recovery_takeover_start()` — overlay activation | ✅ | `backend/app/graphs/recovery_takeover.py` |
| `recovery_takeover_active = True` + `previous_journey_phase` | ✅ | `recovery_takeover.py` |
| 3-step flow: assess → monitor → evaluate_and_return | ✅ | `recovery_takeover.py` |
| `previous_journey_phase == "onboarding"` routing | ✅ | `recovery_takeover.py` |
| `baseline_pending_confirmation` fallback | ✅ | `recovery_takeover.py` |

### D11 — MonitoringService

| Item | Status | File |
|---|---|---|
| `check_hrv_trend()` — strictly decreasing 3 values → flag | ✅ | `backend/app/services/monitoring_service.py` |
| `check_energy_patterns()` — delegates to `detect_energy_patterns()` | ✅ | `monitoring_service.py` |
| `check_proactive_message_allowed()` — ≤2/week cap | ✅ | `monitoring_service.py` |
| `check_baseline_exit_conditions()` → triggers followup | ✅ | `monitoring_service.py` |
| Zero LLM calls in monitoring checks | ✅ | All checks are pure flag evaluation |

### D12 — E2E integration tests

| Item | Status | File |
|---|---|---|
| 6 Phase D flow tests (HC direct, specialist chain, injury→takeover, onboarding 6 blocs, mid-injury suspend/resume, followup) | ✅ | `tests/e2e/test_phase_d_flows.py` |
| 3 clinical escalation tests | ✅ | `tests/e2e/test_phase_d_clinical.py` |

### D13 — Frontend chat UI

| Item | Status | File |
|---|---|---|
| `createChatClient()` — sendMessage + getHistory | ✅ | `packages/api-client/src/chat.ts` |
| `ChatBubble` component — role/content/specialists/timestamp | ✅ | `packages/ui-web/src/ChatBubble.tsx` |
| `TappableOptions` component — axes, disappears after selection | ✅ | `packages/ui-web/src/TappableOptions.tsx` |
| `/chat` page — ProtectedRoute, typing indicator, clarification axes | ✅ | `apps/web/src/app/chat/page.tsx` |
| 7 Vitest tests | ✅ | `apps/web/src/app/chat/__tests__/` |

### D14 — Frontend onboarding coach flow

| Item | Status | File |
|---|---|---|
| `createOnboardingClient()` — start + respond | ✅ | `packages/api-client/src/onboarding.ts` |
| `/onboarding/coach` page — 6-bloc stepper, resume detection, chat-style Q&A | ✅ | `apps/web/src/app/onboarding/coach/page.tsx` |
| Completion → redirect to dashboard | ✅ | `onboarding/coach/page.tsx` |
| 5 Vitest tests | ✅ | `apps/web/src/app/onboarding/__tests__/OnboardingCoach.test.tsx` |

### D15 — classify_intent eval dataset + audit

| Item | Status | File |
|---|---|---|
| 24-case JSONL eval dataset | ✅ | `data/classify_intent_eval.jsonl` |
| `eval_classify_intent.py` eval script | ✅ | `scripts/eval_classify_intent.py` |
| Phase D audit doc (this file) | ✅ | `docs/backend/PHASE-D-AUDIT.md` |

---

## Test Coverage

| Scope | Tests | Location |
|---|---|---|
| `classify_intent` service | ~8 | `tests/backend/services/test_classify_intent_service.py` |
| `chat_turn` graph | ~12 | `tests/backend/graphs/test_chat_turn*.py` |
| `onboarding` graph (D7+D8) | ~15 | `tests/backend/graphs/test_onboarding*.py` |
| `followup_transition` graph | ~8 | `tests/backend/graphs/test_followup_transition.py` |
| `recovery_takeover` graph | ~8 | `tests/backend/graphs/test_recovery_takeover.py` |
| `MonitoringService` | ~10 | `tests/backend/services/test_monitoring_service.py` |
| Phase D E2E flows | 9 | `tests/e2e/test_phase_d_flows.py`, `test_phase_d_clinical.py` |
| Frontend (Vitest) | 38 | `apps/web/src/app/**/` |

---

## Architecture Decisions

### No LLM calls in monitoring
`MonitoringService` computes flags only (HRV trend = 3 decreasing values, energy patterns via existing `detect_energy_patterns()`). No LLM inference in monitoring path — decisions are surfaced as flags for Head Coach to interpret on next `CHAT_FREE_MESSAGE`.

### In-memory thread state
Onboarding, followup, and recovery takeover graphs use module-level `_thread_states` dicts as a MemorySaver-equivalent. This is sufficient for development and single-process deployment. Production replacement: `SqliteSaver` or DB-backed table using the same thread_id → state mapping.

### `object.__setattr__()` for dynamic attributes
Attributes not in `AthleteModel`'s SQLAlchemy mapped columns (`previous_journey_phase`, `suspended_onboarding_block`, etc.) are set via `object.__setattr__(athlete, key, value)` to satisfy mypy --strict without adding migration-required columns.

### Additive-only backend changes
Phase D does not modify any V1-FROZEN files. All new logic is in:
- `backend/app/graphs/` — new graph modules
- `backend/app/services/` — new service modules  
- `backend/app/routes/` — new route modules
- `backend/app/schemas/` — new schema modules
- `backend/app/core/` — new builder modules

### Frontend dual onboarding
The existing `/onboarding` page handles account creation (static form). The new `/onboarding/coach` page handles the conversational coaching onboarding (6 Q&A blocs via D7/D8 backend API). Athletes go to `/onboarding/coach` after account creation.

---

## Eval Dataset Coverage

`data/classify_intent_eval.jsonl` (24 cases):

| Category | Count |
|---|---|
| HEAD_COACH_DIRECT | 3 |
| SPECIALIST_TECHNICAL (single) | 7 |
| SPECIALIST_TECHNICAL (multi-specialist chain) | 4 |
| CLINICAL_ESCALATION_IMMEDIATE | 3 |
| OUT_OF_SCOPE | 3 |
| CLARIFICATION_NEEDED | 3 |
| English / mixed-language | 3 |

Run eval: `python scripts/eval_classify_intent.py --verbose`
Pass threshold: ≥75% overall accuracy on `decision` field.

---

## Known Limitations

1. **Thread state not persistent across restarts** — In-memory `_thread_states` is reset on process restart. Production deployment requires `SqliteSaver` or DB persistence for onboarding/followup/recovery threads.
2. **Onboarding/followup routes not in API contract** — `docs/backend/API-CONTRACT.md` documents V1-FROZEN endpoints. Phase D routes are documented here and in route module docstrings.
3. **eval_classify_intent.py requires live API key** — Not run in CI. Run manually before major prompt changes to `docs/prompts/classify-intent.md`.
