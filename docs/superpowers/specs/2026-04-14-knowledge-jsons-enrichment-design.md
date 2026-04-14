# Knowledge JSONs Enrichment — V3-N2 Design Spec

**Date:** 2026-04-14  
**Status:** Approved  
**Scope:** Second enrichment pass on all 9 knowledge JSON files using book extractions as primary source. V3-N (2026-04-13) established the schema and initial rules. V3-N2 deepens content and adds book provenance.

---

## Context

9 knowledge JSON files live in `docs/knowledge/`. They are consumed by coaching agents via prompt injection or tool retrieval. V3-N enriched them to 111 rules total using peer-reviewed papers as primary source. The 5 book extractions (`docs/backend/books/`) were produced in V3-M (2026-04-13) but were not used as a source in V3-N.

**V3-N2 goal:** Use book extracts as primary source where applicable, external science as secondary. Target ~175–185 total rules (+60–70%). Populate `source_books` fields across all files.

---

## File Tiers

### Tier 1 — Book-rich (direct book content)

| File | Agent | Current Rules | Target |
|---|---|---|---|
| `running_coach_tid_rules.json` | Running Coach | 20 | 28–32 |

Books used: all 5 (`daniels-running-formula`, `pfitzinger-advanced-marathoning`, `pfitzinger-faster-road-racing`, `fitzgerald-8020`, `pierce-first`)

**Rules to add:**
- `Marathon-pace (M-pace) zone` — Daniels §2: 75–84% vVO2max / HRmax; marathon-race effort; unlimited volume if embedded in long run; comfortably hard but not threshold; `[ref: daniels-running-formula §2 M-Pace]`
- `Phase structure — 4-phase Daniels model` — Phase I (Foundation/E+L), II (Repetition/R), III (Interval/I), IV (Threshold/T); ideal 6 weeks/phase; compress proportionally if season <24 weeks; `[ref: daniels-running-formula §5]`
- `FIRST 3-run model — structural constraint` — Track Repeats (TR) + Tempo Run (TMP) + Long Run (LR) only; 2 XT sessions/week mandatory; adding a 4th run breaks the model; zone map: TR=Z4-5, TMP=Z3, LR=Z1-2; `[ref: pierce-first]`
- `Pfitz-FRR VO2max reps — 5K/10K specificity` — 600m–1 mile repeats at 5K race pace; full recovery; 4–6 reps; only in 5K/10K-specific plan weeks; `[ref: pfitzinger-faster-road-racing]`
- `Pfitz-Adv GA run definition` — General Aerobic run: MP+15–25% effort (approx 73–84% HRmax); fills majority of non-quality weekly mileage; never slower than E-pace; `[ref: pfitzinger-advanced-marathoning]`
- `Adverse weather quality session substitution` — Swap Q-day with scheduled E-day; acceptable substitutes: fartlek, hard hill repeats; goal = similar physiological stimulus; `[ref: daniels-running-formula §3]`
- `Pfitz-FRR taper structure — sub-marathon races` — 5K: 1–2 week taper (−20–25% / −35–40%); 10K: 2 weeks (−20–25% / −35–40%); HM: 2–3 weeks (−20–25% / −35–40% / −50–60%); intensity maintained; `[ref: pfitzinger-faster-road-racing]`
- `Pfitz return from break — >20 days` — Skip missed sessions entirely; revise goal race; do not try to make up lost volume; `[ref: pfitzinger-advanced-marathoning]`
- `80/20 post-break protocol` — Break >2 weeks: first week at 50% volume; counts toward 80/20 TID; `[ref: fitzgerald-8020]`

---

### Tier 2 — Book-indirect (books have relevant content)

#### `head_coach_acwr_rules.json` (10 → ~18)

**Rules to add:**
- `Training monotony index` — Foster 1998: monotony = weekly_avg_load / SD(daily_loads); monotony >2.0 = elevated illness/injury risk flag
- `Training strain composite` — strain = weekly_total_load × monotony; strain >6000 arbitrary units = high illness risk; flag to Head Coach
- `Pfitz/Daniels load-cap cross-reference` — tag existing 10% cap rule with `source_books: ["daniels-running-formula", "pfitzinger-advanced-marathoning"]`
- `Post-marathon mandatory recovery block` — Pfitz: 1 week complete rest + 1 week easy (Z1 only) + 1 week at 90% before any quality work; encode as ACWR floor rule
- `Back-to-back hard day rule — Pfitz advanced` — For advanced athletes only (>60 mi/wk): consecutive hard days permitted max 1×/month; must be followed by 2 easy days; `[ref: pfitzinger-advanced-marathoning]`
- `Monotony correction via session type variety` — Prevent monotony by varying session types daily; same session repeated >3 consecutive days = flag; `[ref: daniels-running-formula §2]`
- `ACWR + HRV compound danger flag` — ACWR >1.3 AND RMSSD <15ms same day: mandatory load reduction, no hard sessions; higher risk than either alone
- `10% single-session load spike cap` — Single session should not exceed 7-day average load × 1.5; even if weekly total is within 10%

#### `head_coach_interference_rules.json` (10 → ~18)

**Rules to add:**
- `Concurrent training AMPK/mTOR molecular window` — 0–6h post-endurance: AMPK elevated, mTOR suppressed; strength training in this window produces suboptimal hypertrophy; wait ≥6h; `[Coffey & Hawley 2007]`
- `Strength before long run — session ordering` — Pfitz: heavy strength BEFORE long run, not after; rationale: fatigue from long run degrades strength quality more than vice versa; `[ref: pfitzinger-advanced-marathoning]`
- `Endurance-first weekly scheduling default` — Head Coach default: endurance sessions AM, strength PM same day or next day when forced to combine; never strength AM then quality run PM
- `FIRST XT as interference buffer` — FIRST's cross-training days (non-weight-bearing) serve as active recovery without CNS demand; use this pattern for hybrid athletes on high-stress weeks; `[ref: pierce-first]`
- `Intra-day double session ordering` — If two sessions same day: endurance first if both aerobic; strength first if pairing strength + easy aerobic; never two hard sessions same day
- `Strength session frequency for interference minimization` — 2×/week strength at MEV maintains muscle without significant endurance interference; 3×/week at MAV requires careful scheduling; `[Hickson 1980 interference; Kraemer et al. 1995]`
- `Block periodization interference reduction` — Alternating strength-focused blocks (4 weeks) and endurance-focused blocks (4 weeks) reduces chronic interference vs concurrent year-round programming
- `Taper period strength protocol` — During race taper: reduce strength to MEV (maintenance); maintain intensity, cut volume 40–60%; avoid DOMS-inducing sessions within 7 days of A-race

#### `nutrition_coach_fueling_rules.json` (12 → ~18)

**Rules to add:**
- `Race-week carbohydrate loading protocol` — Pfitz Ch.9: reduce fiber/fat 48h pre-race; increase simple carbs to 8–12 g/kg/day; familiar foods only; no new foods race week; `[ref: pfitzinger-advanced-marathoning]`
- `Electrolytes and sodium intra-race` — 500–700 mg sodium/hour for efforts >90 min; prevents hyponatremia; combine with fluid intake; `[ACSM Position Stand 2007]`
- `Pre-long-run fueling — Pfitz protocol` — 1–4 g/kg carbs 2–3h before; consistent execution in training = gut training for race day; `[ref: pfitzinger-advanced-marathoning Ch.9]`
- `Caffeine as ergogenic aid` — 3–6 mg/kg body weight, 30–60 min pre-event; ~3% performance improvement; avoid if caffeine-naïve; trial in training first; `[Spriet 2014; IOC consensus]`
- `Protein synthesis window post-long-run` — Long runs >90 min: add 0.3–0.4 g/kg protein to post-run carb recovery meal to accelerate glycogen resynthesis + muscle repair; `[Ivy 1988; Berardi 2006]`
- `Altitude nutrition adjustment` — At altitude ≥2000m: increase carbohydrate intake by 10–15%; elevated energy expenditure at altitude; iron-rich foods to support hematological adaptation

#### `recovery_coach_sleep_cns_rules.json` (11 → ~17)

**Rules to add:**
- `Pfitz "rest is training" principle` — Explicit rule: unscheduled easy/rest day on poor-sleep or high-fatigue signal > forcing planned hard session; recovery IS the adaptation stimulus; `[ref: pfitzinger-advanced-marathoning]`
- `Post-marathon sleep debt` — Pfitz: expect 1–2 weeks of elevated sleep need (9–10h target) post-marathon due to systemic inflammation; flag in planning; `[ref: pfitzinger-advanced-marathoning]`
- `Daniels hold-3-4-weeks as CNS consolidation` — Holding volume constant 3–4 weeks before progressing = CNS and musculoskeletal consolidation; encode as explicit adaptation rule, not just mileage rule; `[ref: daniels-running-formula §2]`
- `Sleep deprivation and RPE inflation` — <6h sleep increases perceived exertion by ~10–15% at same pace/load; adjust session targets downward, not just skip; `[Fullagar et al. 2015]`
- `Screen/blue-light cutoff` — Avoid screens 60–90 min before bed; blue light suppresses melatonin by 50–60%; `[Harvard chronobiology; Chang et al. 2015]`
- `Napping timing and duration` — Power nap: 10–20 min, before 3pm; full sleep cycle nap: 90 min; avoid 20–90 min naps (sleep inertia zone)

---

### Tier 3 — Science-only

#### `recovery_coach_hrv_rules.json` (11 → ~17)

**Rules to add:**
- `Orthostatic HRV test protocol` — Measure RMSSD supine 2 min then standing 2 min; delta >15 bpm increase = sympathetic elevation flag; use when absolute RMSSD is ambiguous
- `HRV-guided periodization model` — Daily HRV-guided load outperforms fixed programming for VO2max gains; threshold: if within ±8% baseline = train as planned; `[Kiviniemi et al. 2010]`
- `Female athlete HRV baseline correction` — Menstrual cycle phase affects RMSSD; follicular phase: higher baseline; luteal: lower; use 28-day rolling baseline to normalize; flag only vs personal phase-adjusted baseline
- `ln-RMSSD vs raw RMSSD` — ln-RMSSD preferred for population comparisons; raw RMSSD acceptable for intra-athlete longitudinal monitoring; most apps report raw — acceptable
- `Dehydration effect on HRV` — Dehydration >2% body weight reduces RMSSD; ensure consistent hydration status before morning measurement; flag outliers on hot/travel days
- `Night HRV vs morning HRV` — Nocturnal HRV (during sleep) is a superior predictor vs morning measurement; if wearable provides nocturnal data, prefer it as primary signal

#### `lifting_coach_volume_rules.json` (12 → ~17)

**Rules to add:**
- `Frequency — 2×/week per muscle group` — Equal volume split across 2 sessions/week produces superior hypertrophy vs 1×/week; `[Schoenfeld et al. 2016 meta-analysis]`
- `Deload week protocol for strength blocks` — Every 4–6 weeks: reduce volume to MEV, maintain load intensity; full unloading not required; 1 week sufficient; `[Issurin 2010; Israetel et al.]`
- `Compound lifts priority for hybrid athletes` — Squat, deadlift, bench, row, pull-up: lower endurance interference per hypertrophy stimulus than isolation work; prioritize for hybrid athletes
- `Load progression method — double progression` — Increase reps within target range first (e.g., 3×8→3×12); then increase load by minimum increment and reset reps to lower bound; more systematic than pure RPE
- `Exercise selection for endurance-lifting hybrid` — Avoid excessive eccentric volume on legs before key endurance sessions; Bulgarian split squat, Nordic curls: high DOMS risk; schedule ≥72h before long run

#### `biking_coach_power_rules.json` (15 → ~18)

**Rules to add:**
- `FTP test protocols — 20-min and ramp` — 20-min test: FTP = avg_power × 0.95; ramp test: FTP = last_completed_minute_avg_power × 0.75; both valid; ramp preferred for fatigued athletes
- `Weekly TSS load thresholds` — <300 TSS/wk: minimal aerobic load; 300–450: moderate; 450–600: high training stress; >600: very high, OTS risk if sustained >3 weeks
- `Coggan Zone 7 — neuromuscular power` — >150% FTP; sprint efforts <30s; not quantified by HR (HR lag); track as peak power in watts only; separate from aerobic TSS

#### `swimming_coach_biomechanics_rules.json` (10 → ~16)

**Rules to add:**
- `CSS derivation worked example` — CSS (m/s) = (400m distance − 200m distance) / (T400 − T200); example: 400m in 360s, 200m in 160s → CSS = 200/(360−160) = 1.0 m/s = 1:40/100m
- `Stroke rate vs DPS optimization` — SWOLF = stroke_count + time_per_length; optimal SWOLF is individual; higher DPS (fewer strokes) generally indicates better technique for distance events
- `CSS zone sets for aerobic development` — CSS ±3s/100m is the lactate threshold swim zone; key aerobic development set: 6–10 × 100m at CSS pace, 20s rest; `[Wakayoshi 1992; Pyne et al.]`
- `Flip turn and underwater dolphin kick` — 15m underwater dolphin kick post-turn = faster than surface swimming for most swimmers; train up to 15m breakout; `[biomechanics consensus]`
- `Open water vs pool adjustment` — Add 5–8% time for open water vs pool (no walls, wetsuit effect varies); adjust CSS-derived paces for open water racing accordingly
- `Bilateral breathing — aerobic sessions only` — Breathe every 3 strokes (bilateral) during aerobic sessions; every 2 strokes permitted during high-intensity reps; bilateral improves stroke balance

---

## Execution Rules

1. **Process order:** Tier 1 first, then Tier 2 (priority: acwr → interference → fueling → sleep), then Tier 3
2. **Before each file:** `.backup` copy committed alongside changes
3. **After each file:** run `pytest tests/backend/test_knowledge_jsons.py -v` — all 90 tests must pass
4. **Per-file commit:** `feat(knowledge): enrich <agent>_<domain> — <3-word summary>`
5. **`last_updated`:** bump to `2026-04-14` on every modified file
6. **`source_books` field:** populate with book IDs where rule traces to extract; `[]` for science-only rules
7. **No formula_or_value = "N/A"** — every new rule must have a specific value, range, or formula
8. **Cleanup commit:** remove all `.backup` files at end of session

---

## Files Modified

| File | Action |
|---|---|
| `docs/knowledge/running_coach_tid_rules.json` | Enrich — +8–12 rules |
| `docs/knowledge/head_coach_acwr_rules.json` | Enrich — +6–8 rules + source_books tags |
| `docs/knowledge/head_coach_interference_rules.json` | Enrich — +6–8 rules + source_books tags |
| `docs/knowledge/nutrition_coach_fueling_rules.json` | Enrich — +5–6 rules + source_books tags |
| `docs/knowledge/recovery_coach_sleep_cns_rules.json` | Enrich — +5–6 rules + source_books tags |
| `docs/knowledge/recovery_coach_hrv_rules.json` | Enrich — +5–6 rules |
| `docs/knowledge/lifting_coach_volume_rules.json` | Enrich — +4–5 rules |
| `docs/knowledge/biking_coach_power_rules.json` | Enrich — +3 rules |
| `docs/knowledge/swimming_coach_biomechanics_rules.json` | Enrich — +5–6 rules |
| `docs/backend/KNOWLEDGE-JSONS.md` | Update rule counts, last_updated dates |

---

## Out of Scope

- Schema changes — `common_rule.schema.json` v1.0 is frozen
- New test types — existing 90 parametrized tests are sufficient
- `.bmad-core/data/` JSON files — separate system, not in scope
- Agent code changes — knowledge JSON enrichment only
