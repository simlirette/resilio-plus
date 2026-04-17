# Session Log — Resilio Plus

## 2026-04-17 [saved] — FE-MOBILE-1B
Goal: FE-MOBILE-1B — Consolidation: audit, polish, unit tests, regression tests, docs, FE-MOBILE-2 prep.
Decisions:
- jest-expo preset for `@resilio/ui-mobile` tests (not bare jest). Matches app's test runner, handles RN transforms.
- pnpm transformIgnorePatterns: two-pattern approach (`.pnpm/` + flat). Character class `[-@+]` required — scoped pkgs use `+` (e.g., `@react-native+js-polyfills`), variants use `-` (e.g., `expo-modules-core@55.0.22_...`). Standard `[@]` fails silently.
- `renderWithTheme` helper in `packages/ui-mobile/src/__tests__/helpers.tsx` — all tests wrap in ThemeProvider.
- Regression tests: pure Node.js (`testEnvironment: 'node'`), fs/path grep — no RN runtime. Soft Rule 3 check (≤4 violations) not hard-fail: known #fff in index.tsx.
- `expo export` bundler failure in pnpm monorepo documented as pre-existing, not blocking. `expo start` (dev path) unaffected.
Rejected:
- Root jest.config.js (would conflict with apps/mobile config). Per-package config is correct isolation.
- Deleting 3 backup files — gitignored, deferred to FE-MOBILE-2 start.
Open:
- Web build: unused `@ts-expect-error` in `packages/ui-web/src/theme/ThemeProvider.tsx:25` → fix in F5.
- `expo export` EXPO_ROUTER_APP_ROOT unresolved in pnpm monorepo → upstream Expo/Metro issue.

## 2026-04-17 [saved] — BACKEND-FINAL-AUDIT
Goal: Backend V1 final audit + freeze — 0 flakes, clean quality, frozen governance.
Decisions:
- `test_history_shows_logged_count` fix: `any(sessions_logged >= 1)` over `max(by=start_date)` — onboarding plan had later start_date than PLAN_BODY plan.
- `test_high_continuity_no_breaks` fix: activities window extended to 2030-12-31 (not freeze_time — freeze_time conflicts with Pydantic v2 datetime.date schema generation).
- 9 files formatted (ruff format — scripts/ + apple_health/ + athlete_state.py + db/models.py); zero logic change.
- Security: no critical issues. JWT_SECRET dev default documented (not code-fixed — deployment concern).
- `get_agent_view()` documented as not-enforced-at-runtime (V2 feature, not V1 fix).
- CONTRACT.md placed in `backend/` (not `docs/`) — closer to governed code.
Rejected:
- Adding new tests for coverage-sake — 2430 tests already strong.
- `@pytest.mark.flaky` — root causes were deterministic and fixable.
- `freeze_time` for continuity test — Pydantic v2 breaks on frozen datetime.date.
Open:
- Third test run was in background at session end — expected to show 2430 passed (consistent with runs 1 and 2).

## 2026-04-16 [saved]
Goal: Implement V3-X Apple Health XML import — streaming parser + daily aggregation + endpoint.
Decisions:
- SDNN (Apple Health) and RMSSD (Terra) stored in separate fields — `hrv_sdnn` vs `hrv_rmssd` — not interchangeable numerically.
- Sleep attributed to `end_date` (wake-up day), not `start_date`; InBed/Awake excluded by aggregator, not parser.
- `FIXTURE_DIR` in tests: `Path(__file__).parents[3] / "tests" / "fixtures"` — not `parents[3] / "fixtures"` (would miss the `tests/` dir).
- `ConnectorCredentialModel.extra_json` updated on each import for backward compat with JSON connector at `routes/connectors.py`.
- Feature flag `APPLE_HEALTH_ENABLED=false` default — WARNING not validated on real iPhone.
Rejected:
- Reusing `hrv_rmssd` field for SDNN — absolute values not comparable.
- Parallel agent commits without `git pull --rebase` — causes non-fast-forward failures.
Open:
- Alembic migration 0010 not applied locally (no PostgreSQL) — run `poetry run alembic upgrade head` in Docker.
- No validation on real iPhone `export.xml` — V1 limit, must test before enabling flag in prod.

## 2026-04-16 23:30 [saved]
Goal: Fix ruff/test regressions introduced by Apple Health parallel session merge.
Decisions:
- `setup_scheduler()` wraps `restore_all_jobs` in try/except — DB unreachable at startup must not crash lifespan; jobs restore on next boot.
- `/ready` and `/ready/deep` health tests mock `engine.connect` — these routes bypass `get_db` dep, so SQLite override doesn't apply; mocking is correct.
- Apple Health E501 violations: add `"backend/app/integrations/apple_health/**" = ["E501"]` to ruff per-file-ignores, not inline noqa.
Rejected:
- Patching `get_db` to fix health tests — route uses `engine` directly, dep override irrelevant.
- Skipping health tests when PG unavailable — they should be self-contained.
Open:
- None.

## 2026-04-16 23:00 [saved]
Goal: Pre-launch audit V3-X — find and fix all critical issues before ship.
Decisions:
- 3 connector routes had no auth (`POST/GET/DELETE /connectors/*`) — fixed with `_require_own`; prior tests used bare `client` fixture so never caught this.
- Connector tests must use `authed_client` fixture — bare `client` bypasses auth dependency and produces false-green tests.
- `_require_own` pattern: FastAPI dependency injected as `_: Annotated[str, Depends(_require_own)]` — consistent across all athlete-scoped routes.
Rejected:
- Treating unauthed connector routes as acceptable — any caller could disconnect any athlete's Strava/Hevy.
- Bare `client` fixture for route tests that require ownership — masks auth bugs.
Open:
- `POST /athletes/` still public — intentional V1.1 design decision.

## 2026-04-16 20:30 [saved]
Goal: Design pre-launch audit for Resilio+ backend before V1 ship.
Decisions:
- Triage-first approach: all read-only checks before any fixes — report is accurate before code changes.
- `POST /athletes/` stays public by design — pre-auth onboarding, not a security gap; goes to V1.1 backlog.
- Docker optional: if unavailable, Axis E marked "manual verification required" rather than blocking.
- Fix scope: delete .backup files + patch .env.example only; fix wrong docs, not just incomplete ones.
Rejected:
- Parallel subagents per axis — harder to synthesize into coherent report.
- Fixing all doc gaps — only wrong docs fixed, missing docs go to V1.1 backlog.
Open:
- Next session: `writing-plans` on spec, then `execute-plan`.

## 2026-04-16 18:00 [saved]
Goal: Execute V3-W tech debt sprint — mypy --strict 0 errors, ruff 0 violations.
Decisions:
- N806 pattern: lazy-imported model classes → `_cls` suffix (`_plan_model_cls`); function-local dicts → lowercase (`_intensity`, `_z`).
- `redundant-cast` fix: use `var: Literal[...] = expr` annotation, not `cast()`, when assigning to a named variable.
- `getattr(block, "text", "")` over `isinstance(block, TextBlock)` — isinstance breaks MagicMock in tests.
- `Self` on `BaseConnector.__enter__` — fixes cascade of attr-defined errors in all connector subclasses.
- mypy `exclude = ["backend/scripts/"]` + ruff `per-file-ignores` for prompts.py (E501) and main.py (E402).
Rejected:
- `[[tool.mypy.overrides]]` per-file suppression — too broad (covered by design session).
- `isinstance(TextBlock)` for API response parsing — breaks mock-based tests.
Open:
- `analytics /performance` response shape `dict[str, Any]` — needs typing once stabilised.

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
