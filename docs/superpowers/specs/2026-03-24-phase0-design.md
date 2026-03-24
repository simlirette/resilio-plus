# Phase 0 Design Spec — Resilio Plus Repo Setup

**Date**: 2026-03-24
**Project**: Resilio Plus — Hybrid Athlete Multi-Agent Coaching Platform
**Scope**: Phase 0 — Repository duplication, scaffold, and CLAUDE.md rewrite
**Approach**: Flat monorepo (Approach A)

---

## 1. Context

`resilio-app` is a mature Python running coach CLI (Typer + Poetry) with a functional Strava connector, VDOT calculator, training plan logic, and a rich set of Claude Code skills. Phase 0 transforms it into the starting point of a multi-agent hybrid coaching platform called **Resilio Plus**, without breaking existing functionality.

The target architecture (described in `resilio-hybrid-coach-blueprint.md`) requires:
- A FastAPI backend (new)
- A Next.js frontend (new)
- A BMAD-style multi-agent system (new)
- Preservation of the running CLI for development and debug

---

## 2. Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Repo location | `C:\Users\simon\resilio-plus` | Same level as resilio-app |
| Repo name | `resilio-plus` | Project brand name |
| CLI fate | Kept for dev/debug (Option C) | Zero regression, reuse core logic in FastAPI |
| .bmad-core/ in Phase 0 | Yes — empty scaffold with placeholders | Visible structure from day one |
| Structure | Flat monorepo (Approach A) | resilio/ untouched while backend/ built alongside |

---

## 3. Repository Structure

```
resilio-plus/
│
├── resilio/                        # Original Python CLI — read-only in Phase 0
│   ├── core/                       # Business logic (strava, vdot, plan, load, etc.)
│   ├── api/                        # CLI API layer
│   ├── cli/                        # Typer commands
│   ├── schemas/                    # Pydantic models (reused by backend/)
│   └── utils/
│
├── tests/                          # Existing tests — untouched
├── config/                         # Existing config — untouched
│
├── docs/
│   ├── coaching/                   # Running methodology docs (kept intact)
│   │   └── methodology.md          # 5 books synthesis — used by Running Coach agent
│   ├── training_books/             # [KEPT INTACT] 5 book summaries used by Running Coach agent
│   │   ├── daniel_running_formula.md
│   │   ├── advanced_marathoning_pete_pfitzinger.md
│   │   ├── faster_road_racing_pete_pfitzinger.md
│   │   ├── 80_20_matt_fitzgerald.md
│   │   └── run_less_run_faster_bill_pierce.md
│   ├── superpowers/
│   │   └── specs/                  # Superpowers design specs (this file lives here)
│   └── legacy/                     # CLI-specific docs to be migrated here once backend supersedes CLI in Phase 2+
│
├── backend/                        # [NEW] FastAPI application — Phase 2+
│   └── README.md                   # Placeholder: "FastAPI backend — implemented in Phase 2"
│
├── frontend/                       # [NEW] Next.js application — Phase 4+
│   └── README.md                   # Placeholder: "Next.js frontend — implemented in Phase 4"
│
├── .bmad-core/                     # [NEW] BMAD-style agent definitions
│   ├── agents/                     # .agent.md files (placeholders)
│   │   ├── head-coach.agent.md
│   │   ├── running-coach.agent.md
│   │   ├── lifting-coach.agent.md
│   │   ├── swimming-coach.agent.md
│   │   ├── biking-coach.agent.md
│   │   ├── nutrition-coach.agent.md
│   │   └── recovery-coach.agent.md
│   ├── tasks/
│   │   └── README.md               # Placeholder: tasks defined in Phase 1
│   ├── templates/
│   │   └── README.md               # Placeholder: templates defined in Phase 1
│   ├── data/
│   │   └── README.md               # Placeholder: JSON knowledge bases in Phase 1
│   └── workflows/
│       └── README.md               # Placeholder: workflows defined in Phase 1
│
├── .claude/                        # Existing Claude Code skills (kept intact)
├── .agents/                        # Existing agent skills (kept intact)
│
├── CLAUDE.md                       # [REWRITTEN] Hybrid coach instructions
├── AGENTS.md                       # [REWRITTEN] Hybrid coach instructions (Codex)
├── pyproject.toml                  # [UPDATED] FastAPI + uvicorn added
├── poetry.lock                     # Regenerated
├── .gitignore                      # Unchanged
└── README.md                       # [UPDATED] Describes Resilio Plus
```

---

## 4. CLAUDE.md Structure

The new `CLAUDE.md` replaces the running-coach-focused content with a hybrid multi-agent coaching context. It retains all running methodology references since they feed the Running Coach agent.

### Sections:

**1. Quick Start**
Role: Head Coach IA orchestrating 7 specialist agents. Backend FastAPI + Frontend Next.js. `resilio/` is the legacy CLI preserved for debug.

**2. Architecture Overview**
- 7 agents: Head Coach, Running, Lifting, Swimming, Biking, Nutrition, Recovery
- FatigueScore unified language (section 6 of blueprint)
- 4 API connectors: Strava (active), Hevy, FatSecret, Apple Health via Terra
- Phase map: which code lives where per phase

**3. Repository Map**
Table: folder → purpose → phase when built

**4. Agent Slash Commands** (placeholders, active in Phase 1+)
`/head-coach`, `/run-coach`, `/lift-coach`, `/swim-coach`, `/bike-coach`, `/nutrition-coach`, `/recovery-coach`

**5. Running Coach Knowledge Base**
Books (5) — summaries in `docs/training_books/`, synthesis in `docs/coaching/methodology.md`:
- Daniels' Running Formula — VDOT, zones, paces → `resilio/core/vdot/`
- Pfitzinger's Advanced Marathoning — volume, periodization
- Pfitzinger's Faster Road Racing — 5K to half-marathon specific
- Fitzgerald's 80/20 Running — TID 80/20
- FIRST's Run Less, Run Faster — intensity over volume

Blueprint sources (Section 5.3 — referenced by ID, no local summary):
- Durability of Running Economy (PubMed 40878015)
- Biomechanical risk factors for running injuries (PMC 11532757)
- Running Biomechanics and Running Economy (PMC 12913831)
- Training volume on marathon performance (blueprint reference)
- Advanced footwear technology (blueprint reference)

Supplement v2 sources (Section 2 — with expanded treatment):
- Seiler — TID best practices (IJSPP 2010)
- Pyramidal→Polarized transition (PMC 9299127)
- ML-personalized marathon training (Scientific Reports 2025)

Key workout protocols: long run, tempo, VO2max intervals, repetitions, progression run, tapering
Full methodology: `docs/coaching/methodology.md` (kept intact)

**6. Development Rules**
- `resilio/` is read-only in Phase 0 (do not modify)
- New logic goes in `backend/`
- TDD mandatory (Superpowers workflow)
- CLI kept for internal debug only

**7. Key References**
- Blueprint: `C:\Users\simon\RESILIO PLUS\resilio-hybrid-coach-blueprint.md`
- Supplement v2: `C:\Users\simon\RESILIO PLUS\resilio-knowledge-supplement-v2.md`
- Execution plan: `C:\Users\simon\RESILIO PLUS\resilio-plan-execution-superpowers.md`

---

## 5. .bmad-core/agents/ Placeholder Format

Each `.agent.md` file created in Phase 0 follows this stub format:

```markdown
---
name: <Agent Name>
role: <one-line role>
status: placeholder — implemented in Phase 3
---

# <Agent Name>

> Full implementation in Phase 3. See resilio-hybrid-coach-blueprint.md section 5.x
> and resilio-knowledge-supplement-v2.md for knowledge base.

## Knowledge Sources
- [listed per agent from blueprint + supplement v2]

## Slash Command
/<command-name>
```

---

## 6. pyproject.toml Changes

The `pyproject.toml` has two sections: `[project]` (PEP 517 standard) and `[tool.poetry]`. The existing httpx constraint in `[project].dependencies` is `"httpx>=0.25.0,<0.26.0"`. This must be **replaced** (not appended) with the updated constraint.

Changes to `[project].dependencies`:
```toml
# REPLACE this existing line:
"httpx>=0.25.0,<0.26.0",
# WITH:
"httpx>=0.28.0,<1.0",
"fastapi>=0.115.0,<1.0",
"uvicorn[standard]>=0.32.0,<1.0",
```

No changes to `[tool.poetry]`, `[tool.poetry.group.dev.dependencies]`, or any other section. `resilio` CLI entry point unchanged. `poetry install` must pass after these changes.

---

## 7. Git Workflow

**Starting point**: Duplicate `resilio-app` → `resilio-plus` at `C:\Users\simon\resilio-plus`
**Branch**: `feat/phase0-restructure`

**Commits** (in order):
1. `chore: init resilio-plus from resilio-app` — initial duplicate, all files as-is
2. `feat: scaffold backend/, frontend/, .bmad-core/ directories` — new folders + placeholders
3. `feat: rewrite CLAUDE.md and AGENTS.md for hybrid coach` — new AI instructions
4. `chore: add FastAPI and uvicorn to pyproject.toml` — dependency additions
5. `docs: update README.md for Resilio Plus`

**Invariants** (must hold after Phase 0):
- `poetry install` succeeds
- All existing tests pass (`poetry run pytest`)
- `resilio` CLI remains functional

---

## 8. Out of Scope for Phase 0

- Any code in `backend/` or `frontend/`
- Full `.agent.md` content (only stubs)
- `.bmad-core/data/` JSON files (volume-landmarks, exercise-sfr, etc.)
- `.bmad-core/tasks/`, `templates/`, `workflows/` content
- Database setup
- Any API route implementation
