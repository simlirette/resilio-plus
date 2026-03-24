# Phase 0 — Resilio Plus Repo Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Duplicate `resilio-app` into a new `resilio-plus` repo at `C:\Users\simon\resilio-plus`, scaffold the flat monorepo structure (backend/, frontend/, .bmad-core/), rewrite CLAUDE.md and AGENTS.md for the hybrid coach project, and update pyproject.toml — without breaking any existing CLI functionality.

**Architecture:** Flat monorepo. The original `resilio/` package stays untouched (read-only in Phase 0). New directories (`backend/`, `frontend/`, `.bmad-core/`) are created alongside it with README placeholders. CLAUDE.md and AGENTS.md are fully rewritten to reflect the 7-agent hybrid coaching architecture.

**Tech Stack:** Python 3.11+, Poetry, FastAPI 0.115+, uvicorn 0.32+, httpx 0.28+ (replacing existing 0.25), existing Typer CLI.

**Spec:** `docs/superpowers/specs/2026-03-24-phase0-design.md`

---

## File Map

| Action | Path | Notes |
|---|---|---|
| Create | `C:\Users\simon\resilio-plus\` | Full copy of resilio-app |
| Modify | `pyproject.toml` | Replace httpx, add fastapi + uvicorn |
| Rewrite | `CLAUDE.md` | Hybrid coach context |
| Rewrite | `AGENTS.md` | Hybrid coach context (Codex) |
| Update | `README.md` | Describe Resilio Plus |
| Create | `backend/README.md` | Placeholder |
| Create | `frontend/README.md` | Placeholder |
| Create | `.bmad-core/agents/head-coach.agent.md` | Stub |
| Create | `.bmad-core/agents/running-coach.agent.md` | Stub |
| Create | `.bmad-core/agents/lifting-coach.agent.md` | Stub |
| Create | `.bmad-core/agents/swimming-coach.agent.md` | Stub |
| Create | `.bmad-core/agents/biking-coach.agent.md` | Stub |
| Create | `.bmad-core/agents/nutrition-coach.agent.md` | Stub |
| Create | `.bmad-core/agents/recovery-coach.agent.md` | Stub |
| Create | `.bmad-core/tasks/README.md` | Placeholder |
| Create | `.bmad-core/templates/README.md` | Placeholder |
| Create | `.bmad-core/data/README.md` | Placeholder |
| Create | `.bmad-core/workflows/README.md` | Placeholder |
| Create | `docs/superpowers/plans/` | Directory (copy from resilio-app) |

---

## Task 1: Duplicate repo and initialize git branch

**Files:**
- Create: `C:\Users\simon\resilio-plus\` (full copy of `C:\Users\simon\resilio-app\`)

- [ ] **Step 1: Copy the entire resilio-app directory to resilio-plus**

Run (in PowerShell or bash):
```bash
cp -r /c/Users/simon/resilio-app /c/Users/simon/resilio-plus
```

Expected: No errors. `C:\Users\simon\resilio-plus\` now exists with all files.

- [ ] **Step 2: Verify the copy succeeded**

```bash
ls /c/Users/simon/resilio-plus/
```

Expected output includes: `resilio/`, `tests/`, `CLAUDE.md`, `AGENTS.md`, `pyproject.toml`, `poetry.lock`, `.git/`

- [ ] **Step 3: Move into resilio-plus and create the feature branch**

```bash
cd /c/Users/simon/resilio-plus
git checkout -b feat/phase0-restructure
```

Expected: `Switched to a new branch 'feat/phase0-restructure'`

- [ ] **Step 4: Set git identity for this repo**

```bash
git config user.email "simon@resilio-plus.dev"
git config user.name "Simon"
```

Expected: No errors.

- [ ] **Step 5: Verify existing tests still pass on the fresh copy**

```bash
cd /c/Users/simon/resilio-plus
poetry install
poetry run pytest --tb=short -q
```

Expected: All tests pass. Zero failures. This is the baseline — if tests fail here, stop and investigate before proceeding.

---

## Task 2: Scaffold backend/, frontend/, and .bmad-core/ directories

**Files:**
- Create: `backend/README.md`
- Create: `frontend/README.md`
- Create: `.bmad-core/tasks/README.md`
- Create: `.bmad-core/templates/README.md`
- Create: `.bmad-core/data/README.md`
- Create: `.bmad-core/workflows/README.md`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p /c/Users/simon/resilio-plus/backend
mkdir -p /c/Users/simon/resilio-plus/frontend
mkdir -p /c/Users/simon/resilio-plus/.bmad-core/agents
mkdir -p /c/Users/simon/resilio-plus/.bmad-core/tasks
mkdir -p /c/Users/simon/resilio-plus/.bmad-core/templates
mkdir -p /c/Users/simon/resilio-plus/.bmad-core/data
mkdir -p /c/Users/simon/resilio-plus/.bmad-core/workflows
mkdir -p /c/Users/simon/resilio-plus/docs/superpowers/plans
mkdir -p /c/Users/simon/resilio-plus/docs/legacy
```

- [ ] **Step 2: Create backend/README.md**

Create file `backend/README.md` with this exact content:
```markdown
# Backend — FastAPI

> **Status**: Placeholder — implemented in Phase 2.

This directory will contain the FastAPI application for Resilio Plus.

## Planned structure (Phase 2+)

```
backend/
├── resilio/
│   ├── agents/          # AI agent implementations
│   ├── api/             # FastAPI routes
│   ├── connectors/      # Strava, Hevy, FatSecret, Apple Health
│   ├── core/            # Business logic (fatigue, periodization, conflict)
│   ├── schemas/         # Pydantic models
│   └── db/              # SQLAlchemy + SQLite
└── Dockerfile
```

## Running (Phase 2+)

```bash
poetry run uvicorn backend.resilio.main:app --reload
```
```

- [ ] **Step 3: Create frontend/README.md**

Create file `frontend/README.md` with this exact content:
```markdown
# Frontend — Next.js

> **Status**: Placeholder — implemented in Phase 4.

This directory will contain the Next.js web application for Resilio Plus.

## Planned structure (Phase 4+)

```
frontend/
├── src/
│   ├── app/             # App Router pages
│   │   ├── page.tsx     # Dashboard
│   │   ├── onboarding/  # Onboarding flow
│   │   ├── plan/        # Training plan view
│   │   ├── review/      # Weekly review
│   │   └── chat/        # Head Coach chat interface
│   ├── components/      # React components
│   └── lib/
│       └── api.ts       # Backend API client
└── package.json
```

## Running (Phase 4+)

```bash
cd frontend && npm run dev
```
```

- [ ] **Step 4: Create .bmad-core placeholder READMEs**

Create `.bmad-core/tasks/README.md`:
```markdown
# Tasks — Placeholder

> **Status**: Placeholder — implemented in Phase 1.

BMAD-style task definitions for each coaching workflow step.
See `resilio-hybrid-coach-blueprint.md` section 2 for planned tasks.
```

Create `.bmad-core/templates/README.md`:
```markdown
# Templates — Placeholder

> **Status**: Placeholder — implemented in Phase 1.

YAML templates for training plans, nutrition plans, weekly reports, and athlete profiles.
See `resilio-hybrid-coach-blueprint.md` section 2 for planned templates.
```

Create `.bmad-core/data/README.md`:
```markdown
# Data — Placeholder

> **Status**: Placeholder — implemented in Phase 1.

JSON knowledge bases for agent decision-making:
- `volume-landmarks.json` — MEV/MAV/MRV per muscle group
- `exercise-database.json` — exercises by SFR profile (Tier 1/2/3)
- `running-zones.json` — Daniels/Seiler training zones
- `cycling-zones.json` — Coggan power zones (Z1-Z7)
- `swimming-benchmarks.json` — SWOLF, DPS, CSS zones
- `nutrition-targets.json` — macros by day type

See `resilio-hybrid-coach-blueprint.md` section 9 for data tables.
See `resilio-knowledge-supplement-v2.md` for zone definitions.
```

Create `.bmad-core/workflows/README.md`:
```markdown
# Workflows — Placeholder

> **Status**: Placeholder — implemented in Phase 4.

BMAD-style workflow definitions:
- `workflow-new-athlete.md` — Onboarding steps 1-6
- `workflow-weekly-review.md` — Weekly loop steps 7-8-9
- `workflow-plan-renewal.md` — Post-objective plan renewal

See `resilio-hybrid-coach-blueprint.md` section 2 for planned workflows.
```

- [ ] **Step 5: Commit scaffold**

```bash
cd /c/Users/simon/resilio-plus
git add backend/ frontend/ .bmad-core/ docs/superpowers/plans/ docs/legacy/
git commit -m "feat: scaffold backend/, frontend/, .bmad-core/ directories"
```

Expected: Commit succeeds. `git log --oneline` shows this as the newest commit.

---

## Task 3: Create .bmad-core/agents/ stubs (7 files)

**Files:**
- Create: `.bmad-core/agents/head-coach.agent.md`
- Create: `.bmad-core/agents/running-coach.agent.md`
- Create: `.bmad-core/agents/lifting-coach.agent.md`
- Create: `.bmad-core/agents/swimming-coach.agent.md`
- Create: `.bmad-core/agents/biking-coach.agent.md`
- Create: `.bmad-core/agents/nutrition-coach.agent.md`
- Create: `.bmad-core/agents/recovery-coach.agent.md`

- [ ] **Step 1: Create head-coach.agent.md**

```markdown
---
name: Head Coach
role: Orchestrator — synchronizes all specialist agents, manages global load, resolves conflicts
status: placeholder — implemented in Phase 3
---

# Head Coach

> Full implementation in Phase 3. See `resilio-hybrid-coach-blueprint.md` section 5.1
> and `resilio-knowledge-supplement-v2.md` section 1 for knowledge base.

## Slash Command
/head-coach

## Responsibilities
- Receive FatigueScore from each specialist agent
- Calculate global fatigue budget for the week
- Detect inter-agent conflicts (e.g., heavy legs + speed session next day)
- Arbitrate and produce a unified, coherent weekly plan
- Coordinate with Nutrition Coach to adapt macros per activity day

## Key Concepts
- Concurrent training interference (mTOR vs AMPK): separate force/endurance stimuli 6-24h
- Training Intensity Distribution (TID): pyramidal in prep, polarized in competition
- ACWR (Acute:Chronic Workload Ratio): keep between 0.8-1.3; >1.5 = danger zone
- FatigueScore unified language: local_muscular, cns_load, metabolic_cost, recovery_hours

## Knowledge Sources
- Blueprint §5.1: Head Coach concepts (HIFT, ACWR, TID, Masters athletes)
- Supplement v2 §1.1: ACWR detailed rules (EWMA, sweet spot, danger zone)
- Supplement v2 §1.2: Force/endurance sequencing rules
- Supplement v2 §1.3: Macro-annual periodization for multisport
```

- [ ] **Step 2: Create running-coach.agent.md**

```markdown
---
name: Running Coach
role: Specialist — running economy, biomechanical durability, injury prevention
status: placeholder — implemented in Phase 3
---

# Running Coach

> Full implementation in Phase 3. See `resilio-hybrid-coach-blueprint.md` section 5.3
> and `resilio-knowledge-supplement-v2.md` section 2 for knowledge base.

## Slash Command
/run-coach

## Responsibilities
- Evaluate aerobic level (via Strava history if available)
- Design running sessions across training zones
- Apply 80/20 TID discipline (80% easy, 20% hard)
- Monitor biomechanical durability (long runs ≥90min)
- Prescribe mandatory hip external rotator strengthening (injury prevention)
- Calculate VDOT and zone paces using `resilio/core/vdot/`

## Key Concepts
- VDOT: running fitness score → paces for E/M/T/I/R zones (Daniels)
- Durability: running economy degrades +3.1% after 90min — target this adaptation
- Zone distribution: Z1 easy (75-80% volume), Z2 tempo (5-10%), Z3 VO2max (5-8%)
- Biomechanical risk: hip drop, cadence, footstrike pattern monitoring
- Tapering: -40-60% volume over 2-3 weeks, maintain 1-2 intensity sessions

## Books (summaries in docs/training_books/)
- Daniels' Running Formula — VDOT, zones, paces → `resilio/core/vdot/`
- Pfitzinger's Advanced Marathoning — volume, marathon periodization
- Pfitzinger's Faster Road Racing — 5K to half-marathon
- Fitzgerald's 80/20 Running — TID 80/20
- FIRST's Run Less, Run Faster — intensity over volume

## Blueprint Sources (§5.3 — paper IDs only)
- Durability of Running Economy (PubMed 40878015)
- Biomechanical risk factors (PMC 11532757)
- Running Biomechanics and Economy (PMC 12913831)

## Supplement v2 Sources (§2 — with expanded treatment)
- Seiler — TID best practices (IJSPP 2010)
- Pyramidal→Polarized transition (PMC 9299127)
- ML-personalized marathon training (Scientific Reports 2025)

## Key Workout Protocols
- Long run: 20-33% weekly volume, Z1, 90-150min
- Tempo run: 20-40min at T-pace, or 3×10min cruise intervals
- VO2max intervals: 5-6 × 3-5min at I-pace, rest = interval duration
- Repetitions: 8-12 × 200-400m at R-pace, full rest
- Progression run: Z1 → Z2 in final 20-30min
- Tapering: 40-60% volume reduction, keep intensity sessions short
```

- [ ] **Step 3: Create lifting-coach.agent.md**

```markdown
---
name: Lifting Coach
role: Specialist — neuromuscular optimization, hypertrophy, progressive overload
status: placeholder — implemented in Phase 3
---

# Lifting Coach

> Full implementation in Phase 3. See `resilio-hybrid-coach-blueprint.md` section 5.2
> and `resilio-knowledge-supplement-v2.md` section 3 for knowledge base.

## Slash Command
/lift-coach

## Responsibilities
- Evaluate strength level (via Hevy history if available)
- Design resistance training respecting MEV/MAV/MRV per muscle group
- Reduce leg volume 30-50% when running load is high
- Select exercises by SFR profile (Tier 1 stable machines > Tier 3 barbell when fatigued)
- Apply DUP (Daily Undulating Periodization) for hybrid flexibility

## Key Concepts
- MEV/MAV/MRV: minimum/maximum adaptive/maximum recoverable volume (per muscle group)
- RIR 1-3: never train to failure for hybrid athletes
- SFR (Stimulus-to-Fatigue Ratio): prefer high-SFR, stable exercises (machines/cables)
- MRV legs reduced 30-50% when running volume is high
- DUP: alternate force (3-5 reps) / hypertrophy (8-12 reps) days by readiness

## Knowledge Sources
- Blueprint §5.2: Lifting rules (Schoenfeld, Israetel, Helms, Beardsley)
- Supplement v2 §3.1: DUP for hybrid athletes
- Supplement v2 §3.2: Velocity-Based Training (20% velocity loss = stop set)
- Supplement v2 §3.3: Exercise tier table (Tier 1/2/3)
- Data: `.bmad-core/data/volume-landmarks.json`, `.bmad-core/data/exercise-database.json`
```

- [ ] **Step 4: Create swimming-coach.agent.md**

```markdown
---
name: Swimming Coach
role: Specialist — hydrodynamics, propulsive efficiency, technique
status: placeholder — implemented in Phase 3
---

# Swimming Coach

> Full implementation in Phase 3. See `resilio-hybrid-coach-blueprint.md` section 5.5
> and `resilio-knowledge-supplement-v2.md` section 5 for knowledge base.

## Slash Command
/swim-coach

## Responsibilities
- Evaluate swimming level (open water vs pool technique)
- Optimize DPS (distance per stroke) and SWOLF score — not raw volume
- Apply CSS-based training zones
- Prescribe dry-land strength 2-4x/week at 80-90% 1RM

## Key Concepts
- Propulsive efficiency: triathletes 44% vs competitive swimmers 61% — gap to close
- SWOLF = time per length + stroke count (primary metric)
- CSS (Critical Swim Speed): swim lactate threshold (from 200m+400m test)
- Open water: higher stroke frequency, lower cycle length vs pool
- Drafting: -11% O2 cost in open water

## Knowledge Sources
- Blueprint §5.5: Swimming rules (SWOLF, DPS, dry-land)
- Supplement v2 §5.1: CSS zones (Z1-Z5)
- Supplement v2 §5.2: Key session types (pull, kick, drill, threshold, VO2max)
- Data: `.bmad-core/data/swimming-benchmarks.json`
```

- [ ] **Step 5: Create biking-coach.agent.md**

```markdown
---
name: Biking Coach
role: Specialist — power-based training, aerodynamics, cycling economy
status: placeholder — implemented in Phase 3
---

# Biking Coach

> Full implementation in Phase 3. See `resilio-hybrid-coach-blueprint.md` section 5.4
> and `resilio-knowledge-supplement-v2.md` section 4 for knowledge base.

## Slash Command
/bike-coach

## Responsibilities
- Evaluate cycling level (FTP test required)
- Design workouts using Coggan power zones (Z1-Z7)
- Track TSS/CTL/ATL/TSB via Strava data
- Use PPi (Power Profile Index) for supramaximal efforts
- Monitor fatigue via power:HR ratio (submaximal test)

## Key Concepts
- FTP: Functional Threshold Power — 60min sustainable effort
- Coggan zones: Z1 (<55% FTP) to Z7 (>150% FTP, neuromuscular)
- TSS: Training Stress Score = (duration × NP × IF) / (FTP × 3600) × 100
- CTL/ATL/TSB: chronic fitness / acute load / form (CTL - ATL)
- PPi: Power Profile Index — superior to TSS for supramaximal efforts

## Knowledge Sources
- Blueprint §5.4: PPi, submaximal monitoring
- Supplement v2 §4.1: Coggan zones table
- Supplement v2 §4.2: FTP test protocols (20min test, ramp test)
- Supplement v2 §4.3: NP, IF, TSS, CTL, ATL, TSB formulas
- Data: `.bmad-core/data/cycling-zones.json`
```

- [ ] **Step 6: Create nutrition-coach.agent.md**

```markdown
---
name: Nutrition Coach
role: Specialist — nutritional periodization, macros, supplementation, fueling
status: placeholder — implemented in Phase 3
---

# Nutrition Coach

> Full implementation in Phase 3. See `resilio-hybrid-coach-blueprint.md` section 5.6
> and `resilio-knowledge-supplement-v2.md` section 6 for knowledge base.

## Slash Command
/nutrition-coach

## Responsibilities
- Calculate TDEE and adapt macros by day type
- Synchronize nutrition with training plan from Head Coach
- Prescribe intra-effort fueling (gels, sodium, fluids)
- Recommend evidence-based supplementation (Level A only)

## Key Concepts
- Carb periodization by day type:
  - Strength day: 4-5 g/kg/day
  - Long endurance: 6-7 g/kg/day
  - Rest: 3-4 g/kg/day
  - Intra-effort >75min: 30-60 g/h (up to 90g/h glucose:fructose 2:1)
- Protein: ~1.8 g/kg/day, 20-40g doses every 3-4h, 30-40g casein pre-sleep
- Recovery <4h: 3:1 carbs:protein ratio

## Supplementation (ISSN Level A evidence only)
- Creatine monohydrate: 3-5g/day
- Caffeine: 3-6mg/kg 30-60min pre-effort
- Beta-alanine: 3.2-6.4g/day (split doses)
- Nitrate (beetroot): 6-8mmol 2-3h pre-effort (+1-3% running economy)
- Omega-3: 2-4g EPA+DHA/day (reduces concurrent training inflammation)

## Knowledge Sources
- Blueprint §5.6: Macro rules, intra-effort fueling
- Supplement v2 §6.1: Hydration protocols
- Supplement v2 §6.2: Full supplementation table with doses
- Supplement v2 §6.3: Peri-competition nutrition (carb loading, race day)
- Data: `.bmad-core/data/nutrition-targets.json`
```

- [ ] **Step 7: Create recovery-coach.agent.md**

```markdown
---
name: Recovery Coach
role: Specialist — autonomic recovery, sleep optimization, overtraining prevention
status: placeholder — implemented in Phase 3
---

# Recovery Coach

> Full implementation in Phase 3. See `resilio-hybrid-coach-blueprint.md` section 5.7
> and `resilio-knowledge-supplement-v2.md` section 7 for knowledge base.

## Slash Command
/recovery-coach

## Responsibilities
- Calculate daily Readiness Score from HRV, sleep, RPE, mood
- Guide training intensity based on HRV-guided protocol (green/yellow/red)
- Prescribe sleep extension strategies pre-competition
- Recommend active recovery modalities

## Key Concepts
- HRV: RMSSD morning measurement (60s) is the gold standard
- Readiness Score: composite of HRV, sleep quality/duration, prior-day RPE, subjective mood
  - Green (>75%): proceed as planned, can intensify
  - Yellow (50-75%): reduce intensity 10-20%
  - Red (<50%): recovery day or Z1 only
- Sleep banking: extend 6.8h → 8.4h in the week before competition
- Baseline: 3-5 recordings needed to calibrate personal HRV range

## Active Recovery Modalities
- CWI (Cold Water Immersion): 10-15°C, 10-15min — competition phase only (blunts hypertrophy)
- Foam rolling/massage: 10-15min pre/post
- Yoga/dynamic stretching: rest days
- Tactical naps: when allostatic load is high

## Knowledge Sources
- Blueprint §5.7: HRV, sleep, readiness
- Supplement v2 §7.1: Active recovery protocols
- Supplement v2 §7.2: Readiness Score formula
```

- [ ] **Step 8: Commit agent stubs**

```bash
cd /c/Users/simon/resilio-plus
git add .bmad-core/agents/
git commit -m "feat: add .bmad-core agent stubs for 7 coaching agents"
```

Expected: Commit succeeds with 7 new files.

---

## Task 4: Update pyproject.toml

**Files:**
- Modify: `pyproject.toml` (lines 9-17, `[project].dependencies` section)

> **IMPORTANT**: The existing `"httpx>=0.25.0,<0.26.0"` in `[project].dependencies` must be **replaced**, not appended to. Adding a second httpx entry will cause `poetry install` to fail with a dependency conflict.

- [ ] **Step 1: View current pyproject.toml dependencies**

```bash
cd /c/Users/simon/resilio-plus
cat pyproject.toml
```

Verify you see: `"httpx>=0.25.0,<0.26.0",` in the `[project]` dependencies block.

- [ ] **Step 2: Edit pyproject.toml**

In the `[project]` section, replace the dependencies block so it reads:

```toml
dependencies = [
    "pydantic>=2.5,<3.0",
    "pyyaml>=6.0,<7.0",
    "requests>=2.31,<3.0",
    "python-dateutil>=2.8,<3.0",
    "httpx>=0.28.0,<1.0",
    "tenacity>=8.0.0,<9.0.0",
    "typer>=0.21.1,<0.22.0",
    "fastapi>=0.115.0,<1.0",
    "uvicorn[standard]>=0.32.0,<1.0",
]
```

The only changes are:
- `httpx>=0.25.0,<0.26.0` → `httpx>=0.28.0,<1.0`
- Added: `fastapi>=0.115.0,<1.0`
- Added: `uvicorn[standard]>=0.32.0,<1.0`

All other sections (`[tool.poetry]`, `[tool.poetry.group.dev.dependencies]`, `[build-system]`, etc.) remain unchanged.

- [ ] **Step 3: Run poetry install**

```bash
cd /c/Users/simon/resilio-plus
poetry install
```

Expected: Resolves dependencies successfully. No version conflict errors. `poetry.lock` is updated.

- [ ] **Step 4: Verify CLI still works**

```bash
poetry run resilio --help
```

Expected: Shows resilio CLI help menu. If this fails, the httpx update broke something — check the error and pin to a compatible version.

- [ ] **Step 5: Run existing tests**

```bash
poetry run pytest --tb=short -q
```

Expected: All tests pass. Zero failures.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml poetry.lock
git commit -m "chore: replace httpx 0.25 with 0.28, add fastapi and uvicorn"
```

---

## Task 5: Rewrite CLAUDE.md

**Files:**
- Rewrite: `CLAUDE.md` (full replacement)

- [ ] **Step 1: Replace CLAUDE.md with the new hybrid coach content**

Write the following content to `CLAUDE.md` (replacing all existing content):

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the Resilio Plus codebase.

## Quick Start

**What is this?** Resilio Plus is a multi-agent hybrid coaching platform for athletes who combine running, strength training, swimming, and cycling. A Head Coach AI orchestrates 7 specialist agents to create personalized, science-backed training and nutrition plans.

**Your Role**: You are the Head Coach AI. You orchestrate specialist agents (Running, Lifting, Swimming, Biking, Nutrition, Recovery) and use computational tools to make coaching decisions. The legacy CLI in `resilio/` provides running coaching tools you can reuse directly.

**Tech Stack**: Python 3.11 (FastAPI backend), Next.js (frontend), SQLite (persistence), Poetry (dependency management).

**Key Principle**: Tools provide quantitative data; you provide qualitative coaching judgment. The agents provide domain expertise; the Head Coach provides integration and conflict resolution.

---

## Architecture

### 7 Coaching Agents

| Agent | Slash Command | Status | Knowledge Base |
|---|---|---|---|
| Head Coach | /head-coach | Phase 3 | Blueprint §5.1, Supplement v2 §1 |
| Running Coach | /run-coach | Phase 3 | See Running Coach section below |
| Lifting Coach | /lift-coach | Phase 3 | Blueprint §5.2, Supplement v2 §3 |
| Swimming Coach | /swim-coach | Phase 3 | Blueprint §5.5, Supplement v2 §5 |
| Biking Coach | /bike-coach | Phase 3 | Blueprint §5.4, Supplement v2 §4 |
| Nutrition Coach | /nutrition-coach | Phase 3 | Blueprint §5.6, Supplement v2 §6 |
| Recovery Coach | /recovery-coach | Phase 3 | Blueprint §5.7, Supplement v2 §7 |

Agent definitions live in `.bmad-core/agents/`. Each `.agent.md` file contains the slash command, responsibilities, key concepts, and knowledge sources for that agent.

### Unified Fatigue Score (Head Coach Language)

All agents communicate via a shared `FatigueScore` (Blueprint §6):

```python
class FatigueScore:
    local_muscular: float    # Local muscle impact (0-100)
    cns_load: float          # Central nervous system cost (0-100)
    metabolic_cost: float    # Metabolic cost (0-100)
    recovery_hours: float    # Estimated recovery time
    affected_muscles: list   # Impacted muscle groups
```

Examples:
- Easy 60min run (Z1): local=20, cns=10, metabolic=30
- 10×400m intervals: local=50, cns=40, metabolic=60
- Heavy squat 5×5: local=70, cns=60, metabolic=20

### API Connectors

| Connector | Status | Location |
|---|---|---|
| Strava | Active | `resilio/core/strava.py` |
| Hevy | Phase 3 | `backend/resilio/connectors/hevy.py` |
| FatSecret | Phase 3 | `backend/resilio/connectors/fatsecret.py` |
| Apple Health | Phase 3 | `backend/resilio/connectors/apple_health.py` (via Terra API) |

---

## Repository Map

| Folder | Purpose | Phase |
|---|---|---|
| `resilio/` | Legacy Python CLI — read-only in Phase 0 | Existing |
| `resilio/core/vdot/` | VDOT calculator — reused by Running Coach | Existing |
| `resilio/core/strava.py` | Strava OAuth + sync — reused by backend | Existing |
| `resilio/schemas/` | Pydantic models — reused by backend | Existing |
| `resilio/core/load.py` | CTL/ATL/TSB/ACWR logic — reused by Head Coach | Existing |
| `backend/` | FastAPI application | Phase 2+ |
| `frontend/` | Next.js application | Phase 4+ |
| `.bmad-core/agents/` | Agent definitions (.agent.md stubs) | Phase 0 (stubs), Phase 1 (full) |
| `.bmad-core/data/` | JSON knowledge bases | Phase 1 |
| `docs/coaching/` | Running methodology docs | Existing |
| `docs/training_books/` | 5 book summaries | Existing |
| `docs/superpowers/specs/` | Design specs | Phase 0+ |
| `docs/superpowers/plans/` | Implementation plans | Phase 0+ |

---

## Running Coach Knowledge Base

The Running Coach has the richest existing knowledge base, inherited from resilio-app.

### Books (5) — summaries in `docs/training_books/`, synthesis in `docs/coaching/methodology.md`

- **Daniels' Running Formula** — VDOT, training zones (E/M/T/I/R paces) → `resilio/core/vdot/`
- **Pfitzinger's Advanced Marathoning** — volume periodization, marathon-specific blocks
- **Pfitzinger's Faster Road Racing** — 5K to half-marathon training
- **Fitzgerald's 80/20 Running** — TID: 80% easy / 20% hard
- **FIRST's Run Less, Run Faster** — 3 quality sessions per week, intensity over volume

### Blueprint Sources (§5.3 — referenced by paper ID, no local summary file)

- Durability of Running Economy (PubMed 40878015)
- Biomechanical risk factors for running injuries (PMC 11532757)
- Running Biomechanics and Running Economy (PMC 12913831)
- Training volume on marathon performance
- Advanced footwear technology (carbon plate shoes: ~2% economy gain)

### Supplement v2 Sources (§2 — with expanded rules and zone tables)

- Seiler — TID best practices (IJSPP 2010)
- Pyramidal→Polarized transition (PMC 9299127): PYR→POL = +3% VO2max, +1.5% 5K perf
- ML-personalized marathon training (Scientific Reports 2025)

### Training Zones (Daniels/Seiler hybrid — from Supplement v2 §2.1)

| Zone | %HRmax | Weekly Volume | Purpose |
|---|---|---|---|
| Z1 Easy | 60-74% | 75-80% | Base aerobic, mitochondrial adaptation |
| Z2 Tempo | 80-88% | 5-10% | Lactate threshold, economy |
| Z3 VO2max | 95-100% | 5-8% | Maximal aerobic capacity |
| Z4 Repetition | N/A (too short) | 2-5% | Running economy, fast-twitch recruitment |

### Key Workout Protocols (Supplement v2 §2.2)

- **Long run**: 20-33% weekly volume, Z1, 90-150min
- **Tempo run**: 20-40min at T-pace, or cruise intervals (3×10min at T-pace, 2min rest)
- **VO2max intervals**: 5-6 × 3-5min at I-pace, rest = interval duration
- **Repetitions**: 8-12 × 200-400m at R-pace, full rest (jog recovery)
- **Progression run**: Z1 start → Z2 in final 20-30min
- **Tapering**: -40-60% volume over 2-3 weeks, maintain 1-2 short intensity sessions

### Progression Rules (Supplement v2 §2.3)

- Never increase weekly volume >10% week-over-week
- Deload every 3-4 weeks: -20-30% volume
- Increase in order: frequency → duration → intensity

---

## Development Rules

1. **`resilio/` is read-only in Phase 0** — do not modify existing CLI code
2. **New logic goes in `backend/`** — starting Phase 2
3. **TDD mandatory** — red → green → refactor on every feature
4. **CLI kept for debug** — `poetry run resilio --help` must always succeed
5. **Frequent atomic commits** — one commit per logical task
6. **Verify invariants after every task**:
   - `poetry install` must succeed
   - `poetry run pytest` must pass
   - `poetry run resilio --help` must respond

---

## ACWR Rule (applies to coaching logic AND load planning)

ACWR (Acute:Chronic Workload Ratio) = 7-day load / 28-day rolling average:
- **0.8–1.3**: Safe zone
- **1.3–1.5**: Caution — flag to athlete
- **>1.5**: Danger zone — significant injury risk, must reduce load

Use EWMA (Exponentially Weighted Moving Average) rather than simple rolling average.
Never increase total weekly load >10% in one step (applies across ALL sports combined).

---

## Key References

- **Blueprint**: `C:\Users\simon\RESILIO PLUS\resilio-hybrid-coach-blueprint.md`
- **Supplement v2**: `C:\Users\simon\RESILIO PLUS\resilio-knowledge-supplement-v2.md`
- **Execution Plan**: `C:\Users\simon\RESILIO PLUS\resilio-plan-execution-superpowers.md`
- **Phase 0 Spec**: `docs/superpowers/specs/2026-03-24-phase0-design.md`
- **Coaching Methodology**: `docs/coaching/methodology.md`
- **CLI Reference**: `docs/coaching/cli/index.md`

---

**Agents provide domain expertise. The Head Coach provides integration. Tools provide data. You provide judgment.**
```

- [ ] **Step 2: Verify CLAUDE.md was written**

```bash
wc -l /c/Users/simon/resilio-plus/CLAUDE.md
```

Expected: >100 lines.

- [ ] **Step 3: Commit**

```bash
cd /c/Users/simon/resilio-plus
git add CLAUDE.md
git commit -m "feat: rewrite CLAUDE.md for hybrid coach multi-agent project"
```

---

## Task 6: Rewrite AGENTS.md

**Files:**
- Rewrite: `AGENTS.md` (full replacement — mirrors CLAUDE.md for Codex)

- [ ] **Step 1: Replace AGENTS.md with hybrid coach content**

Write the following content to `AGENTS.md`:

```markdown
# AGENTS.md

This file provides guidance to Codex (CLI/IDE) when working with the Resilio Plus codebase.

## Quick Start

**What is this?** Resilio Plus is a multi-agent hybrid coaching platform for athletes who combine running, strength training, swimming, and cycling. A Head Coach AI orchestrates 7 specialist agents to create personalized, science-backed training and nutrition plans.

**Your Role**: You are the Head Coach AI. You orchestrate specialist agents and use computational tools to make coaching decisions. The legacy CLI in `resilio/` provides running coaching tools you can reuse directly.

**Tech Stack**: Python 3.11 (FastAPI backend), Next.js (frontend), SQLite (persistence), Poetry (dependency management).

**Key Principle**: Tools provide quantitative data; you provide qualitative coaching judgment.

---

## Architecture

### 7 Coaching Agents

| Agent | Status | Knowledge Base |
|---|---|---|
| Head Coach | Phase 3 | Blueprint §5.1, Supplement v2 §1 |
| Running Coach | Phase 3 | docs/training_books/ + Supplement v2 §2 |
| Lifting Coach | Phase 3 | Blueprint §5.2, Supplement v2 §3 |
| Swimming Coach | Phase 3 | Blueprint §5.5, Supplement v2 §5 |
| Biking Coach | Phase 3 | Blueprint §5.4, Supplement v2 §4 |
| Nutrition Coach | Phase 3 | Blueprint §5.6, Supplement v2 §6 |
| Recovery Coach | Phase 3 | Blueprint §5.7, Supplement v2 §7 |

Agent definitions: `.bmad-core/agents/`

### Unified Fatigue Score

```python
class FatigueScore:
    local_muscular: float    # 0-100
    cns_load: float          # 0-100
    metabolic_cost: float    # 0-100
    recovery_hours: float
    affected_muscles: list
```

---

## Repository Map

| Folder | Purpose | Phase |
|---|---|---|
| `resilio/` | Legacy Python CLI — read-only in Phase 0 | Existing |
| `resilio/core/vdot/` | VDOT calculator | Existing |
| `resilio/core/strava.py` | Strava connector | Existing |
| `resilio/core/load.py` | CTL/ATL/TSB/ACWR | Existing |
| `backend/` | FastAPI application | Phase 2+ |
| `frontend/` | Next.js application | Phase 4+ |
| `.bmad-core/agents/` | Agent definitions | Phase 0 (stubs) |
| `.bmad-core/data/` | JSON knowledge bases | Phase 1 |
| `docs/coaching/` | Running methodology | Existing |
| `docs/training_books/` | 5 book summaries | Existing |

---

## Running Coach Knowledge Base

### Books (5) — summaries in `docs/training_books/`

- Daniels' Running Formula — VDOT, zones → `resilio/core/vdot/`
- Pfitzinger's Advanced Marathoning — volume, marathon periodization
- Pfitzinger's Faster Road Racing — 5K to half-marathon
- Fitzgerald's 80/20 Running — TID 80/20
- FIRST's Run Less, Run Faster — intensity over volume

Synthesis: `docs/coaching/methodology.md`

### Supplement v2 Sources (§2)

- Seiler — TID best practices (IJSPP 2010)
- Pyramidal→Polarized (PMC 9299127)
- ML marathon training (Scientific Reports 2025)

### Zone Table

| Zone | %HRmax | Weekly Volume | Purpose |
|---|---|---|---|
| Z1 Easy | 60-74% | 75-80% | Base aerobic |
| Z2 Tempo | 80-88% | 5-10% | Lactate threshold |
| Z3 VO2max | 95-100% | 5-8% | Maximal aerobic |
| Z4 Repetition | N/A | 2-5% | Running economy |

---

## Development Rules

1. `resilio/` is read-only in Phase 0
2. New logic goes in `backend/` (Phase 2+)
3. TDD mandatory: red → green → refactor
4. CLI must always work: `poetry run resilio --help`
5. Verify after every task: `poetry install` + `poetry run pytest`

---

## Key References

- **Blueprint**: `C:\Users\simon\RESILIO PLUS\resilio-hybrid-coach-blueprint.md`
- **Supplement v2**: `C:\Users\simon\RESILIO PLUS\resilio-knowledge-supplement-v2.md`
- **Phase 0 Spec**: `docs/superpowers/specs/2026-03-24-phase0-design.md`
- **Coaching Methodology**: `docs/coaching/methodology.md`
- **Claude Code guidance**: `CLAUDE.md`
```

- [ ] **Step 2: Commit**

```bash
cd /c/Users/simon/resilio-plus
git add AGENTS.md
git commit -m "feat: rewrite AGENTS.md for hybrid coach multi-agent project"
```

---

## Task 7: Update README.md

**Files:**
- Modify: `README.md` (full replacement of header section)

- [ ] **Step 1: Replace README.md**

Write the following content to `README.md`:

```markdown
# Resilio Plus — Hybrid Athlete Coaching Platform

An AI-powered multi-agent coaching platform for hybrid athletes combining running, strength training, swimming, and cycling.

## What is Resilio Plus?

A **Head Coach AI** orchestrates 7 specialist agents to create personalized, periodized training and nutrition plans. Plans adapt weekly based on actual performance data from connected apps.

### Coaching Agents

| Agent | Specialty |
|---|---|
| Head Coach | Orchestration, conflict resolution, load management |
| Running Coach | Economy, biomechanics, injury prevention (Daniels/Pfitzinger/80-20/FIRST) |
| Lifting Coach | Hypertrophy, strength, MEV/MAV/MRV, SFR |
| Swimming Coach | SWOLF, CSS-based zones, propulsive efficiency |
| Biking Coach | FTP, Coggan zones, TSS/CTL/ATL/TSB |
| Nutrition Coach | Carb periodization, evidence-based supplementation |
| Recovery Coach | HRV-guided training, sleep banking, Readiness Score |

### Connected Apps

| App | Data | Status |
|---|---|---|
| Strava | Running, cycling, swimming (GPS, HR, power) | Active |
| Hevy | Strength training (sets, reps, load, volume) | Phase 3 |
| FatSecret | Nutrition (macros, micros, food journal) | Phase 3 |
| Apple Health | HRV, sleep, steps (via Terra API) | Phase 3 |

## Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLite, Poetry
- **Frontend**: Next.js, React, Tailwind CSS, shadcn/ui
- **AI**: Claude (Anthropic) via multi-agent architecture
- **Legacy CLI**: Typer (preserved for development and debug)

## Project Status

| Phase | Scope | Status |
|---|---|---|
| Phase 0 | Repo setup, scaffold, CLAUDE.md | ✅ Current |
| Phase 1 | Data schemas, agent definitions | Upcoming |
| Phase 2 | Agent implementations (backend) | Upcoming |
| Phase 3 | API connectors, FastAPI routes | Upcoming |
| Phase 4 | Next.js frontend | Upcoming |
| Phase 5 | Weekly review loop, E2E | Upcoming |

## Getting Started (Development)

```bash
# Install dependencies
poetry install

# Verify environment
poetry run resilio --help

# Run tests
poetry run pytest
```

## Origin

Based on [resilio-app](https://github.com/du-phan/resilio-app) by du-phan — a running coach CLI with Strava integration. The running methodology and VDOT calculator from resilio-app power the Running Coach agent.
```

- [ ] **Step 2: Commit**

```bash
cd /c/Users/simon/resilio-plus
git add README.md
git commit -m "docs: update README.md for Resilio Plus hybrid coach platform"
```

---

## Task 8: Copy spec and plan docs into resilio-plus

**Files:**
- Create: `docs/superpowers/specs/2026-03-24-phase0-design.md` (copy from resilio-app)
- Create: `docs/superpowers/plans/2026-03-24-phase0-setup.md` (this file)

- [ ] **Step 1: Copy the spec and plan from resilio-app**

```bash
cp /c/Users/simon/resilio-app/docs/superpowers/specs/2026-03-24-phase0-design.md \
   /c/Users/simon/resilio-plus/docs/superpowers/specs/

cp /c/Users/simon/resilio-app/docs/superpowers/plans/2026-03-24-phase0-setup.md \
   /c/Users/simon/resilio-plus/docs/superpowers/plans/
```

- [ ] **Step 2: Commit**

```bash
cd /c/Users/simon/resilio-plus
git add docs/superpowers/
git commit -m "docs: copy phase0 spec and plan from resilio-app"
```

---

## Task 9: Final invariant verification

- [ ] **Step 1: Full poetry install**

```bash
cd /c/Users/simon/resilio-plus
poetry install
```

Expected: Completes without errors.

- [ ] **Step 2: Run full test suite**

```bash
poetry run pytest --tb=short -q
```

Expected: All tests pass. Zero failures. If any test fails, investigate before declaring Phase 0 complete — do not skip.

- [ ] **Step 3: Verify CLI**

```bash
poetry run resilio --help
```

Expected: CLI help menu displays correctly.

- [ ] **Step 4: Verify new structure**

```bash
ls /c/Users/simon/resilio-plus/backend/
ls /c/Users/simon/resilio-plus/frontend/
ls /c/Users/simon/resilio-plus/.bmad-core/agents/
```

Expected:
- `backend/`: README.md
- `frontend/`: README.md
- `.bmad-core/agents/`: 7 `.agent.md` files

- [ ] **Step 5: Final git log check**

```bash
cd /c/Users/simon/resilio-plus
git log --oneline
```

Expected: See commits for each task in this plan on branch `feat/phase0-restructure`.

- [ ] **Step 6: Final commit marking Phase 0 complete**

```bash
git commit --allow-empty -m "chore: Phase 0 complete — resilio-plus scaffold ready"
```

---

## Phase 0 Complete ✓

**What now exists at `C:\Users\simon\resilio-plus\`:**
- Full copy of resilio-app with all existing CLI, tests, and methodology docs
- `backend/`, `frontend/`, `.bmad-core/` scaffold
- 7 agent stub files with knowledge source references
- New CLAUDE.md and AGENTS.md describing the hybrid coach architecture
- FastAPI + uvicorn dependencies added
- All existing tests passing, CLI functional

**Next: Phase 1** — Data schemas (Pydantic + SQLAlchemy) and full `.agent.md` content.
Start a new brainstorm session with: `/superpowers:brainstorm` in `C:\Users\simon\resilio-plus\`.
