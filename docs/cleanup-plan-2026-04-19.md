# Cleanup Plan — 2026-04-19

Author: Claude Code (tech lead audit)
Status: DRAFT — awaiting user validation before Phase 3 execution

---

## 1. Branches

### 1A — Local branches to archive (tag + delete local)

These are merged or subsumed into main. Content preserved via git history and optional `archive/` tags.

| Branch | Last commit | Reason |
|---|---|---|
| `feat/phase10` | 2026-04-10 | Merged into main |
| `feat/phase11` | 2026-04-10 | Merged into main |
| `session/app-works` | 2026-04-12 | Merged into main |
| `session/fe-1b-expo-mobile` | 2026-04-12 | Merged into main |
| `session/fe-1d-api-client` | 2026-04-12 | Merged into main |
| `session/fe-vague1-postmortem` | 2026-04-12 | Merged into main |
| `session/frontend-s0-monorepo-setup` | 2026-04-12 | Merged into main |
| `session/s1-external-plan-clean` | 2026-04-12 | Merged into main |
| `session/s2-plan-import` | 2026-04-12 | Merged into main |
| `session/s3-weekly-review` | 2026-04-12 | Merged into main |
| `session/s4-energy-patterns` | 2026-04-12 | Merged into main |
| `session/s5-frontend-energy` | 2026-04-12 | Merged into main |
| `session/s6-frontend-tracking` | 2026-04-12 | Merged into main |
| `session/s7-e2e-finalisation` | 2026-04-12 | Merged into main |
| `session/s7b-finalisation-complete` | 2026-04-12 | Merged into main |
| `v3` | 2026-04-10 | Merged into main |
| `v3-athletestate` | 2026-04-10 | Merged into main |
| `v3-energy-coach` | 2026-04-10 | Merged into main |
| `v3-frontend` | 2026-04-10 | Merged into main |
| `v3-hormonal-ea` | 2026-04-10 | Merged into main |
| `v3-knowledge` | 2026-04-10 | Merged into main |
| `v3-recovery-coach` | 2026-04-10 | Merged into main |
| `feat/backend-finalize` | 2026-04-10 | Content fully in main (squash/cherry-pick, not git-merged) |
| `feat/connectors` | 2026-04-10 | Content fully in main (squash/cherry-pick, not git-merged) |
| `session/fe-home-polish-nativetabs` | 2026-04-18 | Superseded by chore/downgrade-sdk54 |
| `chore/color-purge-amber-canonical` | 2026-04-18 | Wave 1 ui-mobile primitives — superseded or blocked; archive for reference |
| `feat/ui-integration-v1` | 2026-04-18 | Design exports + UI integration pre-downgrade; design assets already in docs/design/ |
| `session/fe-1a-tauri-desktop` | 2026-04-12 | Desktop deferred; 1 scaffold commit not merged — archive |
| `session/fe-1c-eslint-hex-cleanup` | 2026-04-12 | ESLint/hex cleanup; content applied via sibling branches |

**Action**: `git tag archive/<branch>-2026-04-19 <branch>` then `git branch -d <branch>`.
For branches with unmerged content relative to main (color-purge, ui-integration-v1, fe-1a-tauri): use `git branch -D` after tagging.

### 1B — Branches to keep

| Branch | Reason |
|---|---|
| `chore/downgrade-sdk54` | Active — PR in progress |
| `main` | Source of truth |

### 1C — Remote branches (NO ACTION without further user confirmation)

Remote branches at `origin/` are left untouched. User to decide separately whether to prune stale remotes.

---

## 2. Root-level files to move to `resilio-archive/`

### 2A — Test output dumps → `resilio-archive/misc/test-logs/`

| File | Date |
|---|---|
| `full_suite_pass.txt` | 2026-04-06 |
| `fails.txt` | 2026-04-06 |
| `fails2_utf8.txt` | 2026-04-06 |
| `fails_utf8.txt` | 2026-04-06 |
| `specific_fails.txt` | 2026-04-06 |
| `specific_fails2.txt` | 2026-04-06 |
| `decoded_fails.txt` | 2026-04-06 |
| `pytest-debug.txt` | 2026-04-13 |
| `pytest-output.txt` | 2026-04-13 |
| `pytest-results.txt` | 2026-04-13 |
| `pytest_after_exclusion.log` | 2026-04-12 |
| `pytest_full.log` | 2026-04-12 |

### 2B — Session reports → `resilio-archive/misc/session-reports/`

| File | Date |
|---|---|
| `SESSION_PLAN.md` | 2026-04-12 |
| `SESSION_NOTES_APP_WORKS.md` | 2026-04-12 |
| `SESSION_REPORT.md` | 2026-04-12 |
| `SESSION_REPORT_APP_WORKS.md` | 2026-04-12 |
| `SESSION_REPORT_FE_1D.md` | 2026-04-12 |
| `SESSION_REPORT_BACKEND_FINAL_AUDIT.md` | 2026-04-17 |
| `SESSION_REPORT_FE_FIX_WEB_BUILD.md` | 2026-04-17 |
| `SESSION_REPORT_FE_HOME_FROM_DESIGN.md` | 2026-04-17 |
| `SESSION_REPORT_FE_HOME_POLISH_NATIVETABS.md` | 2026-04-19 |
| `SESSION_REPORT_FE_MOBILE_1.md` | 2026-04-17 |
| `SESSION_REPORT_FE_MOBILE_1B.md` | 2026-04-17 |
| `SESSION_REPORT_FE_MOBILE_2.md` | 2026-04-17 |

### 2C — Review files → `resilio-archive/misc/review-reports/`

| File | Date |
|---|---|
| `REVIEW_FRONTEND_S0.md` | 2026-04-12 |
| `REVIEW_VAGUE1.md` | 2026-04-12 |
| `REVIEW_VAGUE2.md` | 2026-04-12 |
| `REVIEW_VAGUE3.md` | 2026-04-12 |
| `FIX_REPORT_FRONTEND_S0.md` | 2026-04-12 |

### 2D — Old audit / status files → `resilio-archive/docs-obsolete/`

| File | Date | Reason |
|---|---|---|
| `AUDIT-RESILIO.md` | 2026-04-10 | Superseded by `docs/backend-audit-2026-04-17.md` |
| `BACKEND_V3_COMPLETE.md` | 2026-04-12 | Superseded by `BACKEND_FROZEN.md` |

### 2E — Deletion candidates (require explicit user confirmation)

| File | Reason |
|---|---|
| `context-snapshot.json` | Ephemeral Claude Code artifact — content stale |

---

## 3. Backup files to delete (17 files)

These are `.backup`, `.backup-sdk55`, `.backup-polish*`, `.backup-p6` files. Source files have been committed; backups are noise.

**All 17 files listed in Phase 1 report.** Deletions via `git rm`.

---

## 4. Root-level directories

### 4A — Archive → `resilio-archive/`

| Dir | Reason |
|---|---|
| `artefacts/` | 4 v2 architecture docs (2026-03-29). Pre-V3. Not referenced in active code or CLAUDE.md. |
| `.coaching/` | Pre-V3 coaching reference (2026-03-29). Content superseded by `docs/coaching/`. |

### 4B — Investigate then decide (need to check if referenced)

| Dir | Status |
|---|---|
| `skill builder/` | Likely superpowers tooling artifact. Check for references before touching. |
| `.worktrees/` | Stale worktree state. Can be removed if no active worktrees. |

### 4C — Keep

| Dir | Reason |
|---|---|
| `.agents/` | Active agents config |
| `.bmad-core/` | Active knowledge JSONs source |
| `.superpowers/` | Active Claude superpowers config |

---

## 5. docs/ files to archive → `docs/archive/` or `resilio-archive/docs-obsolete/`

| File | Destination | Reason |
|---|---|---|
| `docs/p6-home-plan.md` | `docs/archive/` | P6 completed |
| `docs/p6-polish-diagnostic.md` | `docs/archive/` | P6 completed |
| `docs/p6-polish-plan.md` | `docs/archive/` | P6 completed |
| `docs/sdk54-downgrade-plan.md` | `docs/archive/` | Completed (pending PR merge) |
| `docs/ui-audit-2026-04-12.md` | `docs/archive/` | Historical, keep accessible |
| `docs/ui-audit-mobile-2026-04-17.md` | `docs/archive/` | Historical |
| `docs/ui-rework-diagnostic.md` | `docs/archive/` | Completed |
| `docs/ui-rework-plan.md` | `docs/archive/` | Completed |
| `docs/ui-docs-preparation-report.md` | `docs/archive/` | Completed |
| `docs/plan-sessions-paralleles.md` | `docs/archive/` | Old planning doc |
| `docs/agents-validation-report.md` | `docs/archive/` | Historical validation |

---

## 6. frontend/UI-RULES.md changes

1. Add golden rule header (first line after title): *"Relis UI-RULES.md avant chaque modification frontend."*
2. Add section **Anti-patterns formels** with good/bad example for each:
   - `@import url()` for fonts → use `next/font/google`
   - Gradients on cards
   - Semantic colors (green/yellow/red) outside physiological context
   - Landscape photo background (Bevel style)
   - Serif display fonts
   - Pastel-heavy palettes
   - `#08080e` pure clinical dark (rejected with Whoop/Apple Health pivot)
   - Hardcoded token values (use `design-tokens` references)
3. Fix `apps/web/src/app/globals.css`: remove `@import url()`, use `next/font/google` in layout.

---

## 7. CLAUDE.md changes

1. Section Frontend: add explicit pointer to `frontend/UI-RULES.md` with instruction to read before any frontend work.
2. Add subsection "Anti-patterns récents" with link to UI-RULES.md anti-patterns section.
3. Confirm canonical path: `C:\Users\simon\resilio-plus` on `main`.
4. Confirm backend test command: `poetry run pytest tests/ -v --tb=short` (currently the pytest path is documented but the poetry command is not prominent enough).

---

## 8. Execution order

1. Create `resilio-archive/` structure + `README.md`
2. Archive branches (tag + delete) — 27 branches
3. Move root-level files (test logs, session reports, reviews, old audits) — `git mv`
4. Delete backup files — `git rm`
5. Archive `artefacts/` and `.coaching/` dirs
6. Archive `docs/` operational files to `docs/archive/`
7. Update `frontend/UI-RULES.md`
8. Fix `apps/web/src/app/globals.css` (`@import url()` → `next/font/google`)
9. Update `CLAUDE.md`
10. Write `docs/cleanup-2026-04-19.md` changelog
11. Validate: `git status`, `pytest`, `pnpm install`

---

**STOP — awaiting user validation.**
