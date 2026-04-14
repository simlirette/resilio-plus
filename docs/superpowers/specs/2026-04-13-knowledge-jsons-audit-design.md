# Knowledge JSONs — Audit, Enrichment & Validation Design

**Date:** 2026-04-13  
**Scope:** 9 JSON knowledge files in `docs/knowledge/`  
**Phase:** V3-N (proposed)

---

## 1. Context

9 JSON files store scientific rules consumed by the 7 coaching agents. Current state:

| File | Agent | Rules | Status |
|---|---|---|---|
| `biking_coach_power_rules.json` | Biking Coach | 10 | Valid — missing Coggan zones, FTP, CTL/ATL/TSB |
| `head_coach_acwr_rules.json` | Head Coach | 5 | Valid — missing ACWR thresholds, EWMA formula |
| `head_coach_interference_rules.json` | Head Coach | ~15 | **INVALID JSON** — UTF-8 encoding corruption |
| `lifting_coach_volume_rules.json` | Lifting Coach | 10 | Valid — missing MEV/MAV/MRV, DUP, RPE scale |
| `nutrition_coach_fueling_rules.json` | Nutrition Coach | 6 | Valid — missing g/kg targets, protein, intra-workout |
| `recovery_coach_hrv_rules.json` | Recovery Coach | 8 | Valid — missing RMSSD thresholds, readiness score |
| `recovery_coach_sleep_cns_rules.json` | Recovery Coach | 9 | Valid — CNS rules entirely absent despite title |
| `running_coach_tid_rules.json` | Running Coach | 2 | Valid — severely thin; 5 book extracts exist unused |
| `swimming_coach_biomechanics_rules.json` | Swimming Coach | 2 | Valid — CSS zones, SWOLF, stroke rate all missing |

Cross-cutting issues:
- Mixed French/English — no standard language
- No common schema: missing `version`, `priority`, `confidence`, `applies_to` fields
- `formula_or_value` often `"N/A"` or qualitative — not machine-actionable
- No JSON Schema files, no validation tests

---

## 2. Common Schema

### File Envelope (top-level)

```json
{
  "schema_version": "1.0",
  "target_agent": "<Agent Name>",
  "language": "en",
  "last_updated": "2026-04-13",
  "source_books": ["<book-slug>", ...],
  "extracted_rules": []
}
```

Fields:
- `schema_version` — string, must be `"1.0"` for this iteration
- `target_agent` — must match one of 7 known agent names
- `language` — `"en"` (all files normalized to English)
- `last_updated` — ISO date
- `source_books` — list of book slugs from `docs/backend/books/`

### Rule Shape

```json
{
  "rule_name": "Polarized TID — 80/20 split",
  "category": "Intensity Distribution",
  "condition": "If athlete trains for endurance and goal is VO2max improvement",
  "action": "Distribute 80% of weekly training time at Zone 1-2, 20% at Zone 3+",
  "formula_or_value": "Z1-2: ≥80% weekly time; Z3+: ≤20%",
  "priority": "high",
  "confidence": "strong",
  "source": "Fitzgerald 80/20 + Seiler 2010 meta-analysis",
  "applies_to": ["running", "cycling", "swimming"]
}
```

New fields:
- `priority`: `"high" | "medium" | "low"` — how critical for agent decisions
- `confidence`: `"strong" | "moderate" | "weak"` — evidence quality
- `source`: book title or article reference
- `applies_to`: list of sports this rule applies to

**Constraint:** `formula_or_value` must never be `"N/A"` — use a specific value, range, or formula. If truly qualitative, use a brief descriptive string that an agent can act on.

---

## 3. Enrichment Plan

### Priority 1 — `running_coach_tid_rules.json` (2 → ~20 rules)

Source: `docs/backend/books/` (all 5 extracts), existing `running_coach_tid_rules.json`

Rules to add:
- VDOT zone definitions: E / M / T / I / R pace formulas
- 10% weekly volume progression cap (Daniels + Pfitz consensus)
- Long run % ceiling: `min(weekly_mileage × 0.29, 22 miles)` AND `≤ 210 min`
- Cutback week protocol: every 3–4 weeks, −20–25% volume
- Quality session limits: ≤ 2–3 Q days/week, hard/easy required
- Return-from-break protocol: <5 days → 100%; 6–28 days → 50%/75%; >8 wk → 33–50%
- Altitude adjustment: ≥7,000 ft → R unchanged, I/T by effort only
- Warm-up requirement: 10–15 min E + 4–6 strides before T/I/R sessions
- Taper structure: 3 wk for marathon (−20% / −40% / −60%), intensity maintained
- Cross-training equivalency: cycling × 1.5 run miles; water running HR −10%
- FIRST compatibility: 3 key runs only; no 4th run; XT replaces easy runs
- 80/20 TID as universal default guardrail for non-quality sessions
- Conflict resolution: long run % — use Pfitz-Adv rule as primary

### Priority 2 — `head_coach_acwr_rules.json` (5 → ~12 rules)

Source: CLAUDE.md, existing source articles

Rules to add:
- ACWR safe zone: 0.8–1.3 (no action)
- ACWR caution zone: 1.3–1.5 (flag to athlete, reduce next session by 10–15%)
- ACWR danger zone: >1.5 (mandatory load reduction, notify athlete)
- ACWR formula: `ACWR = 7-day EWMA load / 28-day EWMA load`
- EWMA formula: `EWMA_n = load_n × λ + EWMA_{n-1} × (1 − λ)`; λ = 2/(N+1)
- Multi-sport combined load: sum TSS-equivalent across all sports before computing ACWR
- 10% weekly load cap: never increase total weekly load >10% in one step (all sports combined)
- Trail running flag: eccentric load multiplier → monitor biochemical markers

### Priority 3 — `head_coach_interference_rules.json` (invalid → ~15 rules)

Step 1 — Fix encoding: re-read raw bytes, decode as UTF-8 with `errors='replace'`, reconstruct valid JSON.  
Step 2 — Enrich with:
- Concurrent training order: strength before cardio same day
- Minimum interference gap: ≥6h between strength and cardio sessions
- SIT (sprint intervals) — no significant interference on strength/power gains
- HIIT + resistance: 8–12 week program, 2–3 resistance sessions/week
- Heavy strength for endurance cyclists: improves economy without interference
- Endurance-first ordering: when gap <6h, endurance before strength preferred for hypertrophy

### Priority 4 — `swimming_coach_biomechanics_rules.json` (2 → ~10 rules)

Source: CSS physiology standards, SWOLF definition

Rules to add:
- CSS (Critical Swim Speed) zone definitions: Z1–Z4 relative to CSS pace
- SWOLF calculation: `SWOLF = stroke_count + split_seconds` (lower = more efficient)
- Target SWOLF ranges by distance/level
- Stroke rate targets: freestyle 50–60 strokes/min (recreational), 80–100 (elite)
- Open-water drafting: position 0–50cm behind lead swimmer's feet
- Triathlon swim exit: reduce intensity last 200m to manage HR before T1
- Breaststroke energy cost: 40% higher than freestyle at same speed; use for recovery swims only
- CSS derivation: from 400m and 200m time trial: `CSS = (D400 - D200) / (T400 - T200)`

### Priority 5 — `recovery_coach_sleep_cns_rules.json` (9 → ~16 rules)

CNS rules to add (entirely missing):
- CNS fatigue indicators: RPE inflation (same pace feels harder), reaction time degradation, mood disturbance
- CNS recovery window post-heavy strength: 48–72h before next CNS-demanding session
- Stimulant timing: caffeine ≥6h before sleep; avoid post-4pm if sleep-sensitive
- Sleep duration target for athletes: 8–9h/night; minimum 7h for recovery
- Sleep debt protocol: 1h extra sleep for each 2h deficit accumulated during week
- Pre-competition sleep extension: add 1–2h for 3–5 nights before event

### Priority 6 — `biking_coach_power_rules.json` (10 → ~15 rules)

Rules to add:
- Coggan power zones Z1–Z7: Z1 <55% FTP, Z2 55–74%, Z3 75–89%, Z4 90–104%, Z5 105–120%, Z6 121–150%, Z7 >150% FTP
- FTP test protocol: 20-min all-out × 0.95, or ramp test (last completed minute × 0.75)
- CTL formula: 42-day EWMA of daily TSS
- ATL formula: 7-day EWMA of daily TSS
- TSB = CTL − ATL (form; negative = fatigued, positive = fresh)
- Target TSB before A-race: +5 to +25
- Optimal cadence: 85–100 rpm for endurance; 60–80 rpm for strength intervals

### Priority 7 — `lifting_coach_volume_rules.json` (10 → ~15 rules)

Rules to add:
- MEV (Minimum Effective Volume): ~10 sets/week per muscle group to maintain
- MAV (Maximum Adaptive Volume): ~15–20 sets/week per muscle group for growth
- MRV (Maximum Recoverable Volume): ~25+ sets/week — diminishing returns + injury risk
- DUP weekly structure: vary rep ranges across sessions (e.g., 3–5 / 8–12 / 15–20)
- RPE scale: RPE 6 = 4 reps in reserve; RPE 8 = 2 RIR; RPE 9 = 1 RIR; RPE 10 = max
- Progressive overload: add load only when top set RPE ≤ 7 for 2 consecutive sessions

### Priority 8 — `nutrition_coach_fueling_rules.json` (6 → ~14 rules)

Rules to add:
- Carb target by day type: rest day 3–4g/kg; moderate training 5–7g/kg; hard/long 7–10g/kg
- Protein target: 1.6–2.2g/kg/day; 0.4g/kg per meal, 4× daily
- Intra-workout fueling: 30–60g carbs/h for sessions >60 min; up to 90g/h (glucose:fructose 2:1) for >2.5h
- Pre-workout meal: 1–4g/kg carbs, 1–4h before; avoid high-fat/fiber <2h before
- Post-workout window: 0.3g/kg protein + 1g/kg carb within 30–45 min of session end
- Hydration: 500ml water 2h before; 400–800ml/h during; 1.5L per kg lost after
- Race-day carb loading: 8–12g/kg/day for 24–48h before marathon/long event

### Priority 9 — `recovery_coach_hrv_rules.json` (8 → ~13 rules)

Rules to add:
- RMSSD threshold — low concern: >20ms (normal recovery)
- RMSSD threshold — flag: <15ms on consecutive mornings → reduce session intensity by 20%
- RMSSD threshold — veto: <10ms → recovery day only, no training load
- 7-day HRV trending rule: if 7-day average drops >8% from baseline → flag overreaching
- HRV + sleep interaction: RMSSD <15ms AND sleep <6h → mandatory rest day
- Morning measurement protocol: supine, 5-min RMSSD, consistent timing ±30 min

---

## 4. JSON Schema Files

Location: `docs/knowledge/schemas/`  
One schema per JSON file, named `<source_filename>.schema.json`.

Schema validates:
- Required envelope fields: `schema_version`, `target_agent`, `language`, `last_updated`, `extracted_rules`
- `extracted_rules` is a non-empty array
- Each rule has: `rule_name`, `category`, `condition`, `action`, `formula_or_value`, `priority`, `confidence`, `source`, `applies_to`
- `priority` enum: `["high", "medium", "low"]`
- `confidence` enum: `["strong", "moderate", "weak"]`
- `formula_or_value` is a non-empty string (not `"N/A"`)
- `applies_to` is a non-empty array of sport strings

---

## 5. Testing

**File:** `tests/backend/test_knowledge_jsons.py`

Tests (parametrized over all 9 files):
1. File parses as valid JSON
2. File conforms to its JSON Schema (`jsonschema.validate`)
3. No rule has `formula_or_value == "N/A"`
4. No rule is missing `priority` or `confidence`
5. `target_agent` is one of: Head Coach, Running Coach, Lifting Coach, Swimming Coach, Biking Coach, Nutrition Coach, Recovery Coach
6. `schema_version == "1.0"`
7. `extracted_rules` is non-empty

---

## 6. Backup Convention

Before editing any JSON file:
1. Copy `<file>.json` → `<file>.json.backup` in same directory
2. `.backup` extension added to `.gitignore`
3. Never commit `.backup` files

---

## 7. Deliverables

1. **9 enriched JSON files** in `docs/knowledge/`
2. **9 JSON Schema files** in `docs/knowledge/schemas/`
3. **`tests/backend/test_knowledge_jsons.py`** — 7 test types × 9 files = 63 parametrized tests
4. **`docs/backend/KNOWLEDGE-JSONS.md`** — coverage table (file, agent, rule count, source books, key formulas)
5. **`.gitignore` update** — add `*.json.backup`

---

## 8. Commit Order

One commit per logical unit:
1. Fix `head_coach_interference_rules.json` encoding (unblocks all other work)
2. Enrich `running_coach_tid_rules.json` (P1)
3. Enrich `head_coach_acwr_rules.json` (P2)
4. Enrich `head_coach_interference_rules.json` (P3)
5. Enrich `swimming_coach_biomechanics_rules.json` (P4)
6. Enrich `recovery_coach_sleep_cns_rules.json` (P5)
7. Enrich `biking_coach_power_rules.json` (P6)
8. Enrich `lifting_coach_volume_rules.json` (P7)
9. Enrich `nutrition_coach_fueling_rules.json` (P8)
10. Enrich `recovery_coach_hrv_rules.json` (P9)
11. Add JSON Schema files
12. Add `tests/backend/test_knowledge_jsons.py`
13. Add `docs/backend/KNOWLEDGE-JSONS.md`
14. Update `.gitignore`

---

## 9. Source References

- Book extracts: `docs/backend/books/` (5 files — Daniels, Pfitz-Adv, Pfitz-FRR, 80/20, FIRST)
- CLAUDE.md ACWR section
- Coggan power zones: original Coggan & Allen "Training and Racing with a Power Meter"
- MEV/MAV/MRV: Israetel et al. "Scientific Principles of Hypertrophy Training"
- CSS derivation: Wakayoshi 1992 original CSS formula
- RMSSD thresholds: Plews et al. 2013 HRV4Training guidelines
- Nutrition g/kg: Jeukendrup 2011 carbohydrate oxidation rates; Phillips & Van Loon 2011 protein
