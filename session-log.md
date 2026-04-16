# Session Log — Resilio Plus

## 2026-04-16 [saved]
Goal: Design tech debt cleanup to reach mypy --strict + ruff clean before frontend freeze.
Decisions:
- SQLAlchemy `Mapped[T]` migration (not `# type: ignore`) — 246 errors fixed at source, cleaner long-term.
- Circular imports `schemas.py ↔ db/models.py` resolved via `schemas/base.py` extraction — one-way dep enforced.
- Pre-commit `.pre-commit-config.yaml` with ruff + mypy --strict — production-grade enforcement.
- Test gate: `pytest tests/backend/` after each SA model, full `pytest tests/` at end.
Rejected:
- `# type: ignore[assignment]` for SQLAlchemy columns — hides real bugs, accumulates debt.
- `[[tool.mypy.overrides]]` per-file suppression — too broad, masks future regressions.
- `TYPE_CHECKING` guard for circular imports — band-aid, doesn't fix the dependency direction.
Open:
- Next session: `writing-plans` on `docs/superpowers-optimized/specs/2026-04-16-tech-debt-cleanup-design.md`, then `execute-plan`.

## 2026-04-16 [saved]
Goal: Produce source-verified API + AthleteState reference docs for frontend weekend sprint
Decisions:
- API-CONTRACT.md + ATHLETE-STATE.md written from code only — types copied verbatim, no paraphrase
- 4 parallel subagents scanned routes+schemas simultaneously; faster than sequential + avoids drift
- AthleteState lives in `backend/app/models/athlete_state.py` (not schemas/) — distinct from API AthleteResponse
- AgentView matrix cross-verified line-by-line against `_AGENT_VIEWS` dict before commit
Rejected:
- Summarising schemas in prose — too much drift risk, use verbatim Pydantic copy
Open:
- analytics `/performance` response shape is `dict[str, Any]` — needs typing once stabilised

## 2026-04-16 [saved]
Goal: Source-verified AGENT-SPECS.md + HUMAN-IN-THE-LOOP.md for frontend coaching reference
Decisions:
- Agents run deterministically (pure functions) — prompts.py defines LLM format, not execution path
- AgentContext ≠ AgentView: Context is the execution input, View is the AthleteState filter; documented both
- _after_revise routes to "build" (not "present_to_athlete") on revision_count > 1 — proposed_plan_dict is None after revise_plan clears it
- Weekly review uses MemorySaver (ephemeral); coaching graph uses SqliteSaver (persistent) — different guarantees
Rejected:
- Summarising intensity weights in prose — verbatim copy only, drift risk too high
Open:
- Energy Coach agent file not found in agents/ — may be implemented differently (energy_patterns.py + graph node) [resolved 2026-04-16]

## 2026-04-16 [saved]
Goal: Source-verified STRAIN, ENERGY-COACH, INTEGRATIONS backend reference docs
Decisions:
- Energy Coach = 3 pure modules (energy_availability.py, allostatic.py, energy_patterns.py) — no BaseAgent subclass; confirmed via scan
- STRAIN-DEFINITION.md overwrites stub ADR — verbatim EXERCISE_MUSCLE_MAP (30 exercises) + λ constants preserved
- INTEGRATIONS.md rewritten: added Strava OAuth V2 full flow (Fernet encrypt, CSRF state, auto-refresh) + SPORT_MAP filter
- CLAUDE.md had duplicate Strain + Integrations entries — deduped, kept detailed versions only
Rejected:
- Prose summary of EXERCISE_MUSCLE_MAP — verbatim copy only (drift risk, same rule as previous sessions)
Open:
- `docs/backend/INTEGRATIONS.md.backup` still on disk — can delete once user confirms
