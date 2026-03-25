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
