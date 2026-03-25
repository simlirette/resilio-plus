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
