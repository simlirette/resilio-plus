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
