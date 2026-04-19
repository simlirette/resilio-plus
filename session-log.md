# Session Log — Resilio Plus

## 2026-04-17 [saved] — FE-HOME-FROM-DESIGN
Goal: Implement Home screen from Claude Design handoff. Pivot design system to warm minimalist (Apple Health / Whoop 5.0).
Decisions:
- Design handoff URL (api.anthropic.com) returned 404 → files provided locally in `docs/design/home/`.
- Font migration: Space Grotesk → Inter. Design explicitly uses Inter 300/400/500. Package `@expo-google-fonts/inter` added.
- Accent color: `#3B74C9` (Clinical Blue) replaces `#5b5fef` (indigo). Stored as `colors.accent`.
- Palette: warm off-white `#F7F4EE` (light) / `#131210` (dark). Not the old dark clinical `#08080e`.
- MetricRow: type-based colors (nutrition=warn, strain=ok, sleep=okStrong) — not state-based. Discusses with SO needed.
- Card.tsx: padding=0 + overflow:hidden (content controls padding). Card radius=22px, 0.5px border.
- Tab bar: NOT updated — floating liquid-glass bar from design is FE-MOBILE-3.
- Circle props: `strokeWidth` (explicit override) + `innerLabel` (ring interior label) added for readiness ring.
- CognitiveLoadDial: tick marks at 25/50/75%, accent color for fill, weight-300 number.
- SessionCard: side-by-side layout (left content + right chevron circle).
- Home: allostatic card has side-by-side (text left, dial right) with 0/50/100 legend.
Rejected:
- State-based metric colors — design hardcodes per-metric-type colors.
- backgroundColor on MetricRow — Card wrapping done at call site in Home screen.
Open:
- Tab bar: liquid-glass floating bar → FE-MOBILE-3
- MetricRow color strategy (type vs state) → discuss with Simon-Olivier
- Inter on real iOS device: not validated yet

## 2026-04-17 [saved] — FE-FIX-WEB-BUILD
Goal: Débloquer `npx expo export --platform web` pour preview visuel du Home screen FE-MOBILE-2.
Decisions:
- Cause: `react-native-web` et `react-dom` complètement absents — ni dans package.json ni dans pnpm store. Expo SDK 55 bundledNativeModules.json attend `~0.21.0`.
- `.npmrc` hoisting requis en plus de l'install dans apps/mobile: `@expo/router-server` Node.js SSR path cherche react-native-web depuis deep pnpm virtual store; ne le trouve qu'en root node_modules/.
- `pnpm install --no-frozen-lockfile` requis (lockfile outdated après ajout deps en non-CI mode).
- Version résolue: react-native-web@0.21.2 (compatible React 19.2.4).
Rejected:
- Hoisting global (`shamefully-hoist=true`) — trop agressif, préféré ciblé.
Open:
- Aucun — fix complet, 85 tests verts, web export 12 routes.

## 2026-04-17 [saved] — FE-MOBILE-2
Goal: FE-MOBILE-2 — Home screen implementation: 4 new ui-mobile components, useHomeData hook, home screen layout, jest harness for apps/mobile component tests.
Decisions:
- pnpm dual react-native instances: apps/mobile → `_0e81f392...`, packages/ui-mobile → `_392dc7d...`. jest preset only mocks one. Fix: moduleNameMapper `'^react-native$'` → apps/mobile's instance. All components use same mocked instance.
- Do NOT mock TurboModuleRegistry in setupFilesAfterEnv: preset already provides `NativeModules.DeviceInfo.getConstants() → { Dimensions: {...} }`. Naive mock returns `{ window, screen }` (wrong shape → Dimensions crash).
- `IconComponent` (typed wrapper) instead of `Icon.*` direct JSX in ui-mobile components — avoids TS2786 (ForwardRefExoticComponent in package context).
- French clinical term "Charge allostatique" (not "Cognitive Load") — matches backend `allostatic_score`.
- Readiness < 50 → show rest banner AND still show session (clinical: inform, don't decide).
- jest-expo + react-test-renderer + @testing-library/react-native added to apps/mobile devDeps — required for `preset: 'jest-expo'` to find setup files.
Rejected:
- TurboModuleRegistry moduleNameMapper for logical path — does not intercept relative requires from within react-native own code.
- jest.mock in setup.ts for TurboModuleRegistry — overrides correct preset mock with wrong shape.
Open:
- Check-in screen (FE-MOBILE-3)
- Real API wiring (FE-MOBILE-BACKEND-WIRING)

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
Goal: Session FE-MOBILE-1 — Expo SDK 55 + NativeWind v5 + Expo Router + ui-mobile base.
Decisions:
- NativeWind v5 babel: NO `jsxImportSource: "nativewind"` — v4 pattern, removed in v5 (task spec was outdated).
- `withNativeWind(config)` no `{ input }` option — doesn't exist in v5 API.
- `useSafeAreaInsets` hook instead of `SafeAreaView` component — React 19 JSX type incompatibility.
- `Icon.tsx` is sole lucide-react-native importer; dual API: `Icon.Heart` (object) + `<IconComponent name>`.
- SDK 53 = RN 0.79.6 / React 19.0; SDK 54 = RN 0.81.5; SDK 55 = RN 0.83.4 / React 19.2.4.
Rejected:
- `@types/react-native` — deprecated since RN 0.73, built-in types; remove from all packages.
- `jsxImportSource: "nativewind"` in babel — NativeWind v5 breaks with it.
Open:
- Web build `@ts-expect-error ReactNode` fail (pre-existing on main — ThemeProvider web).
- NativeWind v5 preview untested on real device — validate in FE-MOBILE-2.

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

## 2026-04-17 [saved] [superseded by 2026-04-18 — NativeTabs replaced, SDK 54 compat]
Goal: FE-HOME-POLISH-NATIVETABS — 4 visual fixes + NativeTabs liquid glass migration
Decisions:
- MetricRow colors are now state-based (green→ok, yellow→warn, red→zoneRed) not hardcoded per metric type
- Label 'Récup.' renamed to 'Strain' — technical sport science term preserved in English per design decision
- SessionCard: removed blue sport label row (separate accent-colored text), merged duration+zone into one meta line, zone badge now extracts 'Z1' from 'Zone 1 (60–74%)'
- Mock stubs French titles: 'Easy Run Z1' → 'Course facile', 'Muscu — Upper Pull' → 'Musculation haut du corps'
- NativeTabs migration: expo-router/unstable-native-tabs with SF Symbols + built-in web Radix UI fallback — no Platform.OS branch needed
- Fix 4 (light mode) SKIPPED: ThemeProvider already uses useColorScheme() correctly
- SF Symbols for tab bar: house/house.fill, heart/heart.fill, bolt/bolt.fill, person/person.fill
Rejected:
- Platform.OS fallback for web — not needed, NativeTabsView.web.js handles this inside expo-router
Open:
- NativeTabs not validated on physical iOS device — liquid glass blur effect untested on real hardware

## 2026-04-18 [saved]
Goal: COLOR-PURGE — amber canonical replaces blue+mauve in packages/ and apps/mobile/
Decisions:
- design-tokens/colors.ts: top-level accent/primary = #B8552E; shadcn.dark primary/ring = #D97A52; shadcn.light = #B8552E; RGB channels updated
- brand/logo.tsx PRIMARY and BRAND.md: all #5b5fef refs → #B8552E; dark bg corrected #08080e → #131210
- app.json splash backgroundColor → #131210 (warm near-black), not amber — surface not accent
- UI-RULES-MOBILE.md deleted; frontend/UI-RULES.md is sole source of truth for design rules
Rejected:
- amber splash backgroundColor (#B8552E) — flash de marque incohérent, transition douce vers dark UI préférée
Open:
- apps/web/ still has #5b5fef (globals.css + energy/cycle) — hors scope, traitement séparé

## 2026-04-18 [saved]
Goal: UI mobile rework — Wave 1 primitives livréss, gate Expo Go en attente
Decisions:
- Lime (#C8FF4D) supprimé définitivement — amber (#B8552E/#D97A52) pour tous les CTAs y compris session
- Space Grotesk 400/500/600/700 remplace Inter — _layout.tsx + typography.ts corrigés
- Dark bg unifié #131210 pour V1 — variations contextuelles (#17171A, #161412, etc.) abandonnées
- Tab bar 4 onglets: Accueil|Entraînement|Coach|Profil. Check-in hors tab → /check-in
- zoneRed: #B64536 (terracotta, cohérent amber) remplace #ef4444 (rouge froid)
- physio tokens ajoutés: physio.green/yellow/red light+dark — sémantique physiologique stricte
Rejected:
- 5e tab Métriques (V1) — drill-down depuis Home via tap anneau
- Fond dark multi-valeurs — trop de complexité tokens pour V1
Open:
- Tests Wave 1 non écrits (Button/FloatingLabelInput/HeroNumber/ProgressSegments/SegmentedControl)
- Gate Expo Go Wave 1 non encore validé — continuer Wave 2 après "OK"

## 2026-04-18 [saved]
Goal: Downgrade Expo SDK 55→54 for Expo Go physical device compat.
Decisions:
- SDK 54 uses same react@19.2, react-native@0.83.4, reanimated@4.2.1 as SDK 55 — no ecosystem downgrade needed.
- expo-constants@~17.0.0 pinned explicitly — expo-router v4 peerDep not auto-resolved by expo install --fix.
- NativeTabs (expo-router/unstable-native-tabs) replaced with standard Tabs + IconComponent — API is SDK 55 only, doesn't exist in expo-router v4. [CORRECTED 2026-04-19: NativeTabs IS available in expo-router v6 SDK 54 via unstable-native-tabs — see commit 3b02531]
Rejected:
- React 18 downgrade — unnecessary, SDK 54 uses React 19.
- reanimated 3.x downgrade — unnecessary, SDK 54 supports reanimated 4.x.
Open:
- Gate Expo Go Wave 1: user must test /_debug/text-showcase + /_debug/inputs-showcase on device.

## 2026-04-19 [saved]
Goal: P1 Auth screens (login/signup/forgot-password) using Wave 1 primitives.
Decisions:
- FloatingLabelInput has no `style` prop — wrap in View for spacing (it extends TextInputProps with style omitted).
- expo install --fix must run AFTER pnpm install with target SDK — running with old CLI version fixes for wrong SDK.
- @types/react kept at ~19.2.0; expo wants ~19.1.x but 19.1 breaks react-native-svg class component types.
- SDK 54 actual versions: react-native@0.81.5, expo-router@~6.0.23 (not v4 as initially assumed).
Rejected:
- Running expo install --fix before pnpm install — produces wrong version alignment.
- NativeTabs for tab bar — SDK 55 only, not in expo-router v6. [CORRECTED 2026-04-19: this is wrong — NativeTabs available in SDK 54 expo-router v6 via unstable-native-tabs]
Open:
- P2 Onboarding or P3 Home Dashboard — next to implement.
- Apple Sign In stub needs expo-apple-authentication integration.

## 2026-04-19 [saved]
Goal: P2 Onboarding — 5-step flow with slide animation.
Decisions:
- SlideInRight/SlideOutLeft reanimated layout animations on Animated.View key={step} — direction state drives forward/back variant.
- SegmentedControl variant="accent" added for level selector (step 3) — accent bg on active pill.
- CTA enabled logic per step: step1=firstName, step2=sports≥1, step3=all levels set, step4=objective≠-1.
- /onboarding typed route not in generated types until expo start runs — use `as any` cast.
Rejected:
- Absolute positioning for CTA — flex layout + useSafeAreaInsets().bottom cleaner.
- Fade instead of slide — SPEC explicitly says slide horizontal.
Open:
- P3 Home Dashboard rework next.

## 2026-04-19 [saved]
Goal: P6 polish — 6 bugs fixed post-iPhone test.
Decisions:
- NativeTabs IS available SDK 54 via expo-router/unstable-native-tabs — prior "SDK 55 only" notes were wrong. Confirmed by build dir + commit e2d1810. `Label` + `Icon` are separate imports, children of `NativeTabs.Trigger` (not sub-components).
- `calendar.fill` invalid in sf-symbols 2.2 — use `calendar.circle` / `calendar.circle.fill`.
- Rank drag: PanResponder + Animated.Value translateY (native driver). Swap = Math.round(dy / ROW_HEIGHT). Haptics.Light pickup, Haptics.Medium drop (only on swap). Spring reset to 0 after release.
- Ring value 52px (first iteration) — confirmed too large at 72px on device; 52-60px range auto-allowed without new plan.
Rejected:
- draggable-flatlist v4 for rank drag — depends on reanimated worklets, same crash pattern as P2 onboarding.
- `NativeTabs.Trigger.Label` / `.Icon` as sub-components — doesn't exist in the type.
Open:
- Expo Go test: 6 polish bugs to validate on iPhone.
- Suppression candidats: MetricRow, SessionCard, CognitiveLoadDial, ReadinessStatusBadge.

## 2026-04-19 [saved]
Goal: Write merge-prep plan for chore/downgrade-sdk54 → main.
Decisions:
- Plan at docs/superpowers-optimized/plans/2026-04-19-merge-prep-chore-downgrade-sdk54.md — 5 tasks, user awaits GO.
- Workspace `pnpm -w typecheck` covers web only — mobile check: `cd apps/mobile ; pnpm typecheck` (separate step).
- .backup-* files are untracked, not committed — Step 3 adds them to .gitignore, no deletion needed.
- state.md had uncommitted changes — plan commits it in Task 1 Step 2 before any audit.
Rejected:
- gh pr create execution — display only, user merges manually on GitHub.
- Auto-merge or squash — explicitly forbidden.
Open:
- User GO pending — no execution started yet.
- Expo Go iPhone test for P6 Polish #3 not yet confirmed.

## 2026-04-19 [saved]
Goal: Execute merge-prep plan — paused at Task 3 Step 6 awaiting user GO.
Decisions:
- Health checks: mobile typecheck ✅, web typecheck ⚠️ pré-existant (ThemeProvider.tsx L25, not touched by branch), lint 37 warnings 0 errors (pré-existants), pytest unit 790 passed ✅.
- 0 backend files in diff → pytest non-blocking per plan rule.
- Cleanup scan CLEAN: 0 console.log, 6 TODO all legitimate (backend wiring stubs), 0 backup committed, 0 secrets.
- Only proposal: add *.backup-* and .expo/ to .gitignore.
Rejected:
- Removing any TODO comments — all are legitimate backend-wiring stubs.
- Blocking on web typecheck error — pre-existing on main, file not touched by branch.
Open:
- Awaiting user GO for .gitignore update → then Task 4 (CHANGELOG) → Task 5 (PR template + push).
- Today's Session confirmed placeholder: route /session/live does not exist.

## 2026-04-19 [saved]
Goal: Merge prep chore/downgrade-sdk54 — all 5 tasks complete.
Decisions:
- Merge prep complete: .gitignore updated, CHANGELOG created, CLAUDE.md updated, PR template created, branch pushed.
- web typecheck error (ThemeProvider.tsx L25 @ts-expect-error) = pre-existing on main, non-blocking.
- pytest 2430 passed — confirmed frozen backend untouched by branch.
- 6 TODO comments kept — all legitimate backend-wiring stubs, not debug artifacts.
Rejected:
- Removing TODO comments — backend wiring stubs are expected and documented.
Open:
- PR not yet created — user runs: gh pr create --base main --head chore/downgrade-sdk54 --title "feat(mobile): UI rework P1-P6 — 5 pages Expo SDK 54 (mocks only)" --body-file .github/pull_request_templates/ui-mobile-rework.md
