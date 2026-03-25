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

### Blueprint Sources (§5.3 — paper IDs, no local summary)

- Durability of Running Economy (PubMed 40878015)
- Biomechanical risk factors (PMC 11532757)
- Running Biomechanics and Economy (PMC 12913831)

### Supplement v2 Sources (§2 — with expanded treatment)

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
