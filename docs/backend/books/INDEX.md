# Running Coaching Books — Index

**Files:** 5 extracts in `docs/backend/books/`
**Purpose:** Cross-reference, conflict detection, and integration candidates

---

## 1. Coverage Matrix

| Concept | Daniels | Pfitz-Adv | Pfitz-FRR | 80/20 | FIRST |
|---|---|---|---|---|---|
| Training zones / intensity levels | ✅ E/M/T/I/R (5 pace zones) | ✅ Recovery/GA/MP/LT/VO₂max (effort-based) | ✅ Recovery/GA/LT/VO₂max/Speed (effort-based) | ✅ Z1–Z5 (%LTHR + RPE) | ✅ TR/TMP/LR (3 types, pace-table only) |
| Pace derivation from race performance | ✅ VDOT lookup (Table 5.1/5.2) | ✅ Race-pace direct mapping (5K→VO₂max, 15K/HM→LT) | ✅ Race-pace direct mapping (5K→VO₂max, 10K→LR, 15K/HM→LT) | ✅ Race-equivalency calculator | ✅ 5K time → official FIRST pace tables |
| 10% weekly volume progression cap | ✅ 10% hard cap | ✅ 10% hard cap (+1 mi/session secondary cap) | ✅ 10% hard cap | — (not specified) | — (not specified; volume not the primary variable) |
| Cutback / deload weeks | ✅ Hold 3–4 weeks before increase | ✅ Cutback every 3–4 weeks; −20–25% | ✅ Cutback every 3–4 weeks; −20–25% | — (not specified explicitly) | — (no cutback protocol; fixed 12–16 week plan) |
| Long run % of weekly mileage | ✅ 25–30%; 150 min cap | ✅ 22–29%; 22 mi / 210 min cap | ✅ 20–25% (FRR runners); distance-based | ⚠️ Not specified as % | ⚠️ 20 mi max (marathon); no % rule |
| Taper structure | ✅ Phase IV; compressed if season < 24 wk | ✅ 3 wk: −20–25% / −40% / −60%; intensity maintained | ✅ 1–2 wk (5K), 2 wk (10K), 2–3 wk (HM); −20–25%/−35–40%/−50–60% | ✅ 1–2 wk; reduce volume, maintain quality | ✅ Race week: skip XT, reduce 3 key runs |
| Return from break protocol | ✅ < 5 days → 100%; 6–28 days → 50%/75%; > 8 wk → 33–50% + VDOT decay | ✅ < 10 days → skip missed sessions; > 20 days → revise goal | — (not specified) | ✅ > 2 wk break → −50% first week | ✅ Post-marathon: 1 wk off + 1 wk easy + 1 wk 90% |
| Altitude adjustments | ✅ ≥ 7,000 ft: R unchanged, I/T by effort only | — | — | — | — |
| Warm-up / cool-down requirements | ✅ 10–15 min E warm-up + 4–6 strides + cool-down for T/I/R | ✅ 15–20 min warm-up + strides + 10–15 min cool-down for LT/VO₂max | ✅ 10–20 min easy + dynamic drills + 4–6 strides; 10–20 min cool-down | — (not specified per workout type) | ✅ TR: 10–15 min + 2–4 strides; TMP: 1 mi easy; mandatory cool-down |
| Race-distance specific rules | — (phase structure applies across distances) | ✅ Marathon-specific (MP runs, 22 mi long run, 3 wk taper) | ✅ 5K/10K/HM-specific rules per physiological hierarchy | ✅ Per-phase distribution; race counts toward 20% | ✅ Separate 5K/10K/HM/marathon pace tables and plan lengths |
| Cross-training guidance | — (not a focus) | ✅ Cycling × 1.5; water running HR −10% | ✅ Cycling × 1.5; injury substitution rules | ✅ Counts toward TID; min 3 actual runs/week | ✅ Non-weight-bearing mandatory; 2 XT sessions/week; elliptical NOT recommended |
| Quality session limits per week | ✅ ≤ 2–3 Q days; hard/easy required | ✅ Hard/Easy; back-to-back OK for advanced only | ✅ Hard/Easy; 1 easy day between hard sessions | ⚠️ ≤ 2 Z4-5 sessions; up to 3 any Z3+ (advanced) | ✅ Exactly 3 key runs; no flexibility |
| Recovery run guidelines | ✅ E-pace (conversational); no HR cap | ✅ < 76% MHR / < 70% HRR; strictly easy | ✅ Very easy; blood-flow only; no training stress | ✅ Zone 1; RPE ≤ 2 | — (no recovery runs; XT replaces them) |

### Conflict Notes (from matrix)

**⚠️ Long run % of weekly mileage:** Books give different ceilings.
- Daniels: 25–30% of weekly mileage (+ 150 min duration cap)
- Pfitz-Adv: 22–29% of weekly mileage (+ 22 mi / 210 min absolute caps)
- Pfitz-FRR: 20–25% (shorter-distance runners)
- 80/20: No % rule defined
- FIRST: Distance-based only (20 mi max for marathon); no % rule

**⚠️ Quality session limits per week:** Mostly agreement but FIRST is structurally stricter.
- FIRST: Exactly 3 key runs; rigid
- Pfitzinger: 2–3 hard sessions; hard/easy rule
- Daniels: 2–3 Q days; hard/easy required
- 80/20: ≤ 2 Z4-5 sessions; up to 3 any Z3+ for advanced athletes only

---

## 2. Conflict Notes

### Conflict 1 — Long Run % of Weekly Mileage

**Books in conflict:** Daniels vs. Pfitz-Adv vs. Pfitz-FRR vs. FIRST

| Book | Rule |
|---|---|
| Daniels | Long run ≤ 25–30% of weekly mileage AND ≤ 150 min (2.5 h) |
| Pfitz-Adv | Long run ≤ 29% of weekly mileage AND ≤ 22 miles AND ≤ 210 min |
| Pfitz-FRR | Long run ≤ 20–25% of weekly mileage (no absolute distance cap stated for FRR distances) |
| 80/20 | No % rule; governed purely by TID and phase structure |
| FIRST | 20 miles maximum for marathon plans; no % rule; up to 5 × 20-mile runs prescribed |

**Resolution recommendation:** Apply the most conservative binding rule. For marathon training, use Pfitz-Adv's compound rule: `long_run_distance ≤ min(weekly_mileage × 0.29, 22 miles)` AND `projected_duration ≤ 210 min`. For 5K–HM plans, use Pfitz-FRR's 20–25% guideline. For FIRST plans, respect the 20-mile absolute cap. Daniels' 25–30% is the most permissive; use it only when no race-distance-specific cap applies.

---

### Conflict 2 — Quality Sessions Per Week (FIRST strictness)

**Books in conflict:** FIRST vs. all others

| Book | Rule |
|---|---|
| FIRST | Exactly 3 key runs per week — rigid structural constraint; adding a 4th run defeats the method |
| Daniels | 2–3 Q days; hard/easy alternation; never 2 consecutive hard days without compensation |
| Pfitz-Adv | Hard/Easy principle; typically 2–3 hard sessions; back-to-back allowed for advanced athletes |
| Pfitz-FRR | 1 easy day between all hard sessions; race-distance-specific session counts |
| 80/20 | ≤ 2 Z4-5 sessions for ALL athletes; up to 3 any-Z3+ sessions for advanced only |

**Resolution recommendation:** FIRST's "3 hard sessions" and 80/20's "≤ 2 Z4-5 hard sessions" are not directly contradictory — FIRST's Tempo Run occupies 80/20's Zone 3, not Zone 4-5. For a FIRST athlete, the 80/20 rule is technically satisfied (2 Z4-5 runs = TR + LR; TMP ≈ Zone 3). When integrating, apply 80/20's 2 Z4-5 cap as the universal floor and let race-distance logic from Pfitz-FRR govern session type allocation.

---

### Conflict 3 — Easy Run Intensity / Role

**Books in conflict:** 80/20 vs. FIRST

| Book | Rule |
|---|---|
| 80/20 | 80% of weekly training TIME at Zone 1-2; easy runs are the foundational building block |
| FIRST | No easy runs exist in the program; cross-training replaces them entirely |
| Daniels | E-pace runs are foundational; 60–75% of weekly volume at E-pace |
| Pfitz-Adv | GA runs at MP + 15–25% fill majority of weekly mileage; recovery runs < 76% MHR |
| Pfitz-FRR | GA runs at conversational effort; HR 70–81% MHR; same role as Pfitz-Adv |

**Resolution recommendation:** FIRST is a structurally different model, not a "conflict" per se — it replaces easy runs with XT. When the agent is operating under a FIRST plan, suppress easy-run prescriptions and substitute XT. Under all other models, 80/20's Zone 1-2 discipline applies as the default guardrail for non-quality sessions.

---

### Conflict 4 — Pace Zone Reference Anchor

**Books in conflict:** Daniels (VDOT) vs. 80/20 (%LTHR) vs. Pfitzinger (race pace direct) vs. FIRST (5K pace tables)

| Book | Anchor |
|---|---|
| Daniels | VDOT integer derived from recent race time → all paces from Table 5.2 |
| Pfitz-Adv | Race pace direct: 5K → VO₂max pace; 15K/HM → LT pace; goal MP → long run pace |
| Pfitz-FRR | Same as Pfitz-Adv; 10K pace additionally used for long run derivation |
| 80/20 | %LTHR (derived from 30-min field test); pace zones are secondary from race equivalency |
| FIRST | 5K race time → official FIRST pace tables (opaque formula; not derivable from other models) |

**Resolution recommendation:** These are four parallel zone derivation systems, not strict numeric conflicts — a 5K time fed into each will produce similar but not identical pace targets. Daniels VDOT is the most comprehensive (covers all 5 intensities); use it as the primary derivation engine. 80/20's LTHR zones should be used for HR-monitored sessions. FIRST pace tables are only applicable within FIRST plans. Flag when the user switches models mid-training block.

---

## 3. JSON Integration Candidates

### Zone HR Boundaries

- **Concept**: Recovery run HR ceiling (MHR)
- **Value**: < 76%
- **Source**: Pfitz-Adv `[§2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Confirmed by Pfitz-FRR ("very easy; blood flow only"); Daniels uses RPE not HR

- **Concept**: Recovery run HR ceiling (HRR)
- **Value**: < 70%
- **Source**: Pfitz-Adv `[§2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Pfitz-Adv only; other books do not specify HRR ceiling for recovery

- **Concept**: GA run HR range (MHR)
- **Value**: 70–81%
- **Source**: Pfitz-Adv `[§2]`, Pfitz-FRR `[§2]` (identical in both)
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Consistently defined across both Pfitzinger books

- **Concept**: GA run HR range (HRR)
- **Value**: 62–75%
- **Source**: Pfitz-Adv `[§2]`, Pfitz-FRR `[§2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Consistent across Pfitzinger sources

- **Concept**: LT run HR range (MHR)
- **Value**: 82–91%
- **Source**: Pfitz-Adv `[§2]`, Pfitz-FRR `[§2]` (identical)
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Both Pfitzinger books agree; corresponds to 80/20 Z3 upper boundary

- **Concept**: LT run HR range (HRR)
- **Value**: 77–88%
- **Source**: Pfitz-Adv `[§2]`, Pfitz-FRR `[§2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Consistent across Pfitzinger sources

- **Concept**: VO₂max interval HR range (MHR)
- **Value**: 93–95%
- **Source**: Pfitz-Adv `[§2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Pfitz-Adv only; Pfitz-FRR does not give absolute MHR for VO₂max intervals

- **Concept**: VO₂max interval HR range (HRR)
- **Value**: 91–94%
- **Source**: Pfitz-Adv `[§2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Pfitz-Adv only

- **Concept**: Long run HR range (MHR)
- **Value**: 74–84%
- **Source**: Pfitz-Adv `[§2]`, Pfitz-FRR `[§2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Consistent across Pfitzinger books

- **Concept**: MP run HR range (MHR)
- **Value**: 79–88%
- **Source**: Pfitz-Adv `[§2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Marathon-specific; Pfitz-Adv only

### 80/20 LTHR Zone Boundaries

- **Concept**: 80/20 Zone 1 upper boundary (%LTHR)
- **Value**: LTHR × 0.81
- **Source**: 80/20 `[§2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: All 80/20 HR zones use %LTHR, not %MHR; LTHR ≈ MHR × 0.88 typical

- **Concept**: 80/20 Zone 2 upper boundary (%LTHR)
- **Value**: LTHR × 0.89
- **Source**: 80/20 `[§2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Top of low-intensity range; Z1-2 combined = 80% minimum of weekly time

- **Concept**: 80/20 Zone 3 upper boundary (%LTHR)
- **Value**: LTHR × 0.93
- **Source**: 80/20 `[§2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Gray zone ceiling; must be < 5% of weekly training time

- **Concept**: 80/20 Zone 4 upper boundary (%LTHR)
- **Value**: LTHR × 1.02
- **Source**: 80/20 `[§2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Z4-5 combined ≤ 2 sessions/week hard cap

### Pace Multipliers

- **Concept**: Long run pace multiplier vs MP (fast bound)
- **Value**: MP × 1.10 (10% slower than MP)
- **Source**: Pfitz-Adv `[§2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Applies to marathon training long runs; do not go faster than this

- **Concept**: Long run pace multiplier vs MP (slow bound)
- **Value**: MP × 1.20 (20% slower than MP)
- **Source**: Pfitz-Adv `[§2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Applies to marathon training long runs

- **Concept**: Long run pace multiplier vs 10K (fast bound)
- **Value**: 10K_pace × 1.20 (20% slower than 10K pace)
- **Source**: Pfitz-FRR `[§2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: For 5K–HM runners; alternate derivation using 15K/HM pace × 1.17

- **Concept**: Long run pace multiplier vs 10K (slow bound)
- **Value**: 10K_pace × 1.33 (33% slower than 10K pace)
- **Source**: Pfitz-FRR `[§2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: For 5K–HM runners; alternate: HM_pace × 1.29

- **Concept**: GA run pace multiplier vs MP (fast bound)
- **Value**: MP × 1.15
- **Source**: Pfitz-Adv `[§2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Applies to marathon-phase GA runs

- **Concept**: GA run pace multiplier vs MP (slow bound)
- **Value**: MP × 1.25
- **Source**: Pfitz-Adv `[§2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Applies to marathon-phase GA runs

- **Concept**: Daniels 6-Second Rule (VDOT > 50)
- **Value**: 6 sec per 400m between R / I / T paces
- **Source**: Daniels `[§2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: VDOT 40-50: use 7–8 sec instead; R → I: −6 s/400m; I → T: −6 s/400m

### Volume Caps (%)

- **Concept**: Weekly volume progression hard cap
- **Value**: 10% per week
- **Source**: Daniels `[§2]`, Pfitz-Adv `[§3]`, Pfitz-FRR `[§3]` (all three agree)
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Pfitz-Adv adds secondary cap: ≤ 1 mile × number_of_sessions/week

- **Concept**: Long run % of weekly mileage cap (marathon)
- **Value**: 29% maximum
- **Source**: Pfitz-Adv `[§3]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Daniels allows 25–30%; use 29% as the shared conservative ceiling

- **Concept**: Long run % of weekly mileage cap (5K–HM)
- **Value**: 20–25% maximum
- **Source**: Pfitz-FRR `[§3]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Shorter-distance runners; lower than marathon equivalent

- **Concept**: T-pace total volume per session cap (Daniels)
- **Value**: weekly_mileage × 10%
- **Source**: Daniels `[§2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Single session cap; also applies to any continuous T run

- **Concept**: I-pace total volume per session cap (Daniels)
- **Value**: min(10 km, weekly_mileage × 8%)
- **Source**: Daniels `[§2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Per session; whichever is lower

- **Concept**: R-pace total volume per session cap (Daniels)
- **Value**: min(8 km, weekly_mileage × 5%)
- **Source**: Daniels `[§2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Per session; whichever is lower

- **Concept**: 80/20 Zone 3 (gray zone) time cap
- **Value**: < 5% of weekly training time
- **Source**: 80/20 `[§0]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Must reallocate excess Zone 3 time to Zone 1-2

- **Concept**: 80/20 low-intensity minimum (standard)
- **Value**: ≥ 80% of weekly training time
- **Source**: 80/20 `[§0]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Base Phase: 85–90%; Peak Phase: ~77% floor

### Session Count Limits

- **Concept**: Max Z4-5 sessions per week (80/20)
- **Value**: 2 sessions (ALL athletes, no exception)
- **Source**: 80/20 `[§5]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Advanced athletes may do up to 3 any-Z3+ sessions; Z4-5 always capped at 2

- **Concept**: Max quality sessions per week (standard athletes — 80/20)
- **Value**: 2 sessions
- **Source**: 80/20 `[§5]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Advanced athletes: max 3

- **Concept**: FIRST key runs per week
- **Value**: Exactly 3 (never 4)
- **Source**: FIRST `[Ch. 1]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Structural constraint; 4th run defeats injury-reduction logic

### Taper %

- **Concept**: Marathon taper week 1 volume reduction
- **Value**: 20–25% below peak
- **Source**: Pfitz-Adv `[§5]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Week 3 out from race; consistent with Pfitz-FRR week 1

- **Concept**: Marathon taper week 2 volume reduction
- **Value**: 40% below peak
- **Source**: Pfitz-Adv `[§5]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Week 2 out from race

- **Concept**: Marathon taper race week volume reduction
- **Value**: 60% below peak
- **Source**: Pfitz-Adv `[§5]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: 6 days before race

- **Concept**: HM taper week 2 volume reduction (Pfitz-FRR)
- **Value**: 35–40% below peak
- **Source**: Pfitz-FRR `[§4]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Half marathon only; second taper week

- **Concept**: Cutback week frequency
- **Value**: Every 3–4 weeks
- **Source**: Pfitz-Adv `[§2]`, Pfitz-FRR `[§3]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Both Pfitzinger books agree; Daniels uses a "hold 3–4 weeks" cadence (same effect)

- **Concept**: Cutback week volume reduction
- **Value**: 20–25%
- **Source**: Pfitz-Adv `[§2]`, Pfitz-FRR `[§3]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: CLAUDE.md also states 20–30% deload every 3–4 weeks

### Duration Caps

- **Concept**: Long run maximum duration (Daniels)
- **Value**: 150 min (2.5 h)
- **Source**: Daniels `[§2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Applies when distance cap (25–30% weekly mileage) would exceed 2.5 h

- **Concept**: Long run maximum duration (Pfitz-Adv)
- **Value**: 210 min (3.5 h)
- **Source**: Pfitz-Adv `[§3]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: For slow runners; applies when 22-mile cap would project beyond this duration

- **Concept**: Long run maximum distance (Pfitz-Adv)
- **Value**: 22 miles (35 km)
- **Source**: Pfitz-Adv `[§2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Hard ceiling regardless of weekly mileage

- **Concept**: Long run maximum distance (FIRST marathon)
- **Value**: 20 miles
- **Source**: FIRST `[Ch. 2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Up to 5 × 20-mile runs prescribed in peak weeks

- **Concept**: LT tempo segment duration (Pfitz-Adv)
- **Value**: 20–40 min continuous (≤ ~7 miles)
- **Source**: Pfitz-Adv `[§2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Hard cap; beyond 40 min shifts metabolic stimulus

- **Concept**: VO₂max interval duration per rep
- **Value**: 2–6 min per repetition
- **Source**: Pfitz-Adv `[§2]`, Pfitz-FRR `[§2]` (identical)
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: 600–1600 m at 5K pace; Daniels specifies 3–5 min for I-pace

- **Concept**: VO₂max total volume per session (Pfitz-Adv)
- **Value**: 5,000–10,000 m
- **Source**: Pfitz-Adv `[§2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Hard floor and ceiling; Pfitz-FRR does not specify a total volume bound

- **Concept**: Cross-training substitution multiplier (cycling)
- **Value**: bike_duration = run_duration × 1.5
- **Source**: Pfitz-Adv `[§3]`, Pfitz-FRR `[§2]` (identical)
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: For replacing a recovery or easy run with cycling

- **Concept**: VDOT break decay — short (6–28 days)
- **Value**: pre_break_VDOT × 0.93–0.99
- **Source**: Daniels `[Table 9.2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Lower bound (× 0.93) applies when no cross-training was maintained

- **Concept**: VDOT break decay — long (> 8 weeks)
- **Value**: pre_break_VDOT × 0.80–0.92
- **Source**: Daniels `[Table 9.2]`
- **Target file**: `.bmad-core/data/running-zones.json`
- **Notes**: Depends on whether cross-training was maintained during break

---

## 4. Agent Prompt Candidates

### Safety / Guardrail Rules (High Priority)

- **Agent**: Head Coach + Running Coach
- **Rule**: IF runner sick OR injured THEN pause ALL training immediately; do not modify and continue
- **Source**: Daniels `[§0, §1]`; Pfitz-Adv `[§4.10]`; Pfitz-FRR `[§4.11]`; FIRST `[§4.5]`
- **Priority**: High

- **Agent**: Head Coach
- **Rule**: IF athlete has fever OR symptoms below the chest THEN suspend ALL high-intensity and prolonged sessions for the duration of illness
- **Source**: Pfitz-Adv `[§4.10]`; Pfitz-FRR `[§4.6, §4.11]`
- **Priority**: High

- **Agent**: Head Coach + Running Coach
- **Rule**: IF athlete is limping OR reports pain that worsens during a run OR alters running biomechanics THEN stop the session immediately AND do not resume until pain-free
- **Source**: Pfitz-Adv `[§4.10]`; Pfitz-FRR `[§4.11]`
- **Priority**: High

- **Agent**: Head Coach
- **Rule**: IF ferritin < 25 ng/ml THEN pause training plan AND refer athlete to physician
- **Source**: Pfitz-Adv `[§4.10]`
- **Priority**: High

- **Agent**: Head Coach
- **Rule**: IF athlete shows persistent fatigue + elevated resting HR + disturbed sleep + performance decline despite training THEN flag as overtraining AND pause all hard sessions
- **Source**: Pfitz-Adv `[§4.10]`; Pfitz-FRR `[§4.11]`; FIRST `[§4.5]`
- **Priority**: High

- **Agent**: Running Coach
- **Rule**: IF heat distress symptoms occur during a run (headache, disorientation, muscle spasms, cessation of sweating) THEN stop workout immediately, seek shade, and hydrate
- **Source**: FIRST `[§4.5]`; Pfitz-FRR `[§4.6]`
- **Priority**: High

- **Agent**: Running Coach
- **Rule**: IF runner is new to running OR lacks required base (< 15 mi/week for 5K/10K plan; < 25 mi/week for marathon plan) THEN do not start FIRST plan; prescribe base-building phase of at least 3 months first
- **Source**: FIRST `[§4.5]`
- **Priority**: High

- **Agent**: Head Coach
- **Rule**: IF athlete is over 40 years of age AND beginning a new training plan THEN require physician clearance
- **Source**: FIRST `[§4.5]`
- **Priority**: High

---

### Volume Progression Rules (High Priority)

- **Agent**: Running Coach
- **Rule**: IF weekly_mileage_target > previous_week_mileage × 1.10 THEN cap weekly_mileage_target at previous_week_mileage × 1.10
- **Source**: Daniels `[§3]`; Pfitz-Adv `[§4.2]`; Pfitz-FRR `[§4.2]` (all three agree)
- **Priority**: High

- **Agent**: Running Coach
- **Rule**: IF increasing weekly mileage AND running ≥ 2 sessions/week THEN also cap increase at ≤ 1 mile × number_of_weekly_sessions (apply whichever cap is more restrictive)
- **Source**: Pfitz-Adv `[§4.2]`
- **Priority**: High

- **Agent**: Running Coach
- **Rule**: IF a mileage step-up has just been applied THEN hold at the new level for at least 2–3 weeks before the next increase
- **Source**: Pfitz-Adv `[§4.2]`; Pfitz-FRR `[§4.2]`
- **Priority**: High

- **Agent**: Running Coach
- **Rule**: IF athlete has trained for 3–4 consecutive weeks without a cutback week THEN schedule a cutback week at 75–80% of previous week's volume
- **Source**: Pfitz-Adv `[§4.2]`; Pfitz-FRR `[§4.2]`
- **Priority**: High

---

### Session Limit Rules (High Priority)

- **Agent**: Running Coach
- **Rule**: IF weekly plan contains > 2 sessions (standard athletes) or > 3 sessions (advanced athletes) with any Zone 3-5 content THEN revise plan to reduce quality sessions to the applicable limit
- **Source**: 80/20 `[§5]`
- **Priority**: High

- **Agent**: Running Coach
- **Rule**: IF Z4-5 sessions in the weekly plan exceed 2 THEN reduce to 2 regardless of athlete level
- **Source**: 80/20 `[§5]`
- **Priority**: High

- **Agent**: Running Coach
- **Rule**: IF two quality sessions appear on consecutive days THEN insert at least one low-intensity day between them
- **Source**: 80/20 `[§5]`; Daniels `[§2]`; Pfitz-Adv `[§1]`
- **Priority**: High

- **Agent**: Running Coach (FIRST plans only)
- **Rule**: IF runner is on a FIRST plan THEN key runs per week = exactly 3; adding a 4th run day defeats the program
- **Source**: FIRST `[Ch. 1]`
- **Priority**: High

---

### Pacing Rules (Medium Priority)

- **Agent**: Running Coach
- **Rule**: IF runner provides a recent race time THEN look up race distance and time in Daniels Table 5.1 to determine current VDOT AND use Table 5.2 to set all training paces (E, M, T, I, R)
- **Source**: Daniels `[§3]`
- **Priority**: Medium

- **Agent**: Running Coach
- **Rule**: IF workout_type = VO₂max interval THEN set pace = current 5K race pace; IF VO₂max interval pace is set faster than 5K race pace THEN reject and reset to 5K race pace
- **Source**: Pfitz-Adv `[§4.1]`; Pfitz-FRR `[§4.1]`
- **Priority**: Medium

- **Agent**: Running Coach
- **Rule**: IF workout_type = Lactate Threshold run THEN set pace = current 15K–HM race pace (effort equivalent to ~60-min race effort)
- **Source**: Pfitz-Adv `[§4.1]`; Pfitz-FRR `[§4.1]`
- **Priority**: Medium

- **Agent**: Running Coach
- **Rule**: IF workout_type = Long Run (marathon plan) THEN set pace between MP × 1.10 and MP × 1.20; NEVER set long run pace faster than MP × 1.10
- **Source**: Pfitz-Adv `[§4.1]`
- **Priority**: Medium

- **Agent**: Running Coach
- **Rule**: IF workout_type = Long Run (5K–HM plan) THEN set pace between 10K_pace × 1.20 and 10K_pace × 1.33
- **Source**: Pfitz-FRR `[§4.1]`
- **Priority**: Medium

- **Agent**: Running Coach
- **Rule**: IF VDOT is determined from race performance THEN do NOT update training paces again within 3–4 weeks even after a new race result
- **Source**: Daniels `[§3]`
- **Priority**: Medium

- **Agent**: Running Coach
- **Rule**: IF total_T_volume_in_session > weekly_mileage × 10% THEN reduce T volume to cap; IF I_pace_work_bout > 5 min THEN shorten to 5 min; IF R_pace_work_bout > 2 min THEN shorten to 2 min
- **Source**: Daniels `[§2]`
- **Priority**: Medium

- **Agent**: Running Coach
- **Rule**: IF total VO₂max interval volume for session > 10,000 m THEN reduce repetitions to stay ≤ 10,000 m
- **Source**: Pfitz-Adv `[§4.5]`
- **Priority**: Medium

---

### Workout Structure Rules (Medium Priority)

- **Agent**: Running Coach
- **Rule**: IF generating T, I, or R workout THEN prepend 10–15 min E-pace warm-up AND append 10–15 min E-pace cool-down; IF generating I or R workout THEN also include 4–6 strides at R-pace after warm-up and before first rep
- **Source**: Daniels `[§2]`
- **Priority**: Medium

- **Agent**: Running Coach
- **Rule**: IF workout_type = VO₂max interval THEN execute warm-up of 2–3 miles at easy aerobic pace + strides; cool-down of 2–3 miles at easy recovery pace
- **Source**: Pfitz-Adv `[§4.4]`; Pfitz-FRR `[§4.4]`
- **Priority**: Medium

- **Agent**: Running Coach
- **Rule**: IF workout_type is any quality session (LT, VO₂max, Speed) THEN add static stretching after cool-down (20–30 sec holds); do NOT perform prolonged static stretching before a workout
- **Source**: Pfitz-FRR `[§4.4]`
- **Priority**: Medium

---

### Taper Rules (Medium Priority)

- **Agent**: Running Coach
- **Rule**: IF marathon is 3 weeks away THEN begin taper: −20–25% from peak; IF 2 weeks away THEN −40%; IF race week (6 days) THEN −60%; maintain workout intensities at goal paces throughout taper
- **Source**: Pfitz-Adv `[§4.3]`
- **Priority**: Medium

- **Agent**: Running Coach
- **Rule**: IF goal race = half marathon THEN begin taper 2–3 weeks out; week 1 −20–25%, week 2 −35–40%, race week −50–60%; intensity maintained
- **Source**: Pfitz-FRR `[§4.3]`
- **Priority**: Medium

- **Agent**: Running Coach
- **Rule**: IF tapering THEN maintain workout intensities at race paces — reduce volume ONLY, not pace
- **Source**: Pfitz-Adv `[§4.3]`; Pfitz-FRR `[§4.3]`; 80/20 `[§5]`
- **Priority**: Medium

- **Agent**: Running Coach
- **Rule**: IF marathon is 10 days away THEN eliminate all strength training
- **Source**: Pfitz-Adv `[§4.3]`
- **Priority**: Medium

---

### Return from Break Rules (Medium Priority)

- **Agent**: Running Coach
- **Rule**: IF returning from a break of 5 days or fewer THEN resume training at 100% of previous workload and VDOT
- **Source**: Daniels `[§3]`
- **Priority**: Medium

- **Agent**: Running Coach
- **Rule**: IF returning from a break of 6–28 days THEN reduce training load to 50% for the first half of the return period AND 75% for the second half; adjust VDOT to 93–99% of pre-break VDOT
- **Source**: Daniels `[§3]`
- **Priority**: Medium

- **Agent**: Running Coach
- **Rule**: IF returning from a break > 8 weeks THEN follow structured return: 3 weeks at 33% load + 3 weeks at 50% load; reduce VDOT to 80–92% of pre-break value
- **Source**: Daniels `[§3]`
- **Priority**: Medium

- **Agent**: Running Coach
- **Rule**: IF athlete is returning from a training break > 2 weeks THEN reduce planned volume by at least 50% in the first week and rebuild gradually before re-entering the formal plan
- **Source**: 80/20 `[§3]`
- **Priority**: Medium

---

### Altitude Rules (Medium Priority)

- **Agent**: Running Coach
- **Rule**: IF training at altitude ≥ 7,000 ft THEN keep R-pace unchanged from sea-level AND increase recovery time; run I-pace and T-pace by effort only (not by target pace); run E and L runs by feel
- **Source**: Daniels `[§3]`
- **Priority**: Medium

---

### Long Run Guardrails (Medium Priority)

- **Agent**: Running Coach
- **Rule**: IF long_run_distance > weekly_mileage × 0.29 THEN reduce long_run_distance to weekly_mileage × 0.29; IF long_run_distance > 22 miles THEN cap at 22 miles; IF projected_long_run_duration > 210 min THEN reduce distance
- **Source**: Pfitz-Adv `[§4.6]`
- **Priority**: Medium

- **Agent**: Running Coach (FIRST plans only)
- **Rule**: IF plan_type = marathon THEN long_run_max_distance = 20 miles; up to 5 × 20-mile long runs may be prescribed in peak weeks
- **Source**: FIRST `[Ch. 2]`
- **Priority**: Medium

---

### 80/20 TID Compliance (Medium Priority)

- **Agent**: Running Coach
- **Rule**: IF total weekly training time is known THEN verify Zone 1-2 time ÷ total time ≥ 0.80 before approving the week's plan
- **Source**: 80/20 `[§0]`
- **Priority**: Medium

- **Agent**: Running Coach
- **Rule**: IF Zone 3 time exceeds 5% of weekly training time THEN reallocate that time to Zone 1-2 in the following week
- **Source**: 80/20 `[§0]`
- **Priority**: Medium

- **Agent**: Running Coach
- **Rule**: IF athlete reports that easy runs feel "somewhat hard" OR conversation requires effort THEN classify as gray-zone creep AND reduce pace/effort until Zone 1-2 RPE (≤ 6) is achieved
- **Source**: 80/20 `[§0, §2]`
- **Priority**: Medium

---

### Masters-Specific Rules (Medium Priority)

- **Agent**: Running Coach
- **Rule**: IF runner_age IN [36–45] THEN add 1 extra recovery day after each VO₂max session; IF runner_age IN [46–55] THEN add 2 extra recovery days after VO₂max + 1 day after tempo/long runs; IF runner_age IN [56–65] THEN add 2–3 extra recovery days after VO₂max
- **Source**: Pfitz-FRR `[§4.8]`
- **Priority**: Medium

- **Agent**: Running Coach
- **Rule**: IF runner_is_master AND approaching goal race THEN extend taper by several days beyond the standard duration
- **Source**: Pfitz-FRR `[§4.3]`
- **Priority**: Medium

---

### Race-Specific Session Count (Low Priority)

- **Agent**: Running Coach
- **Rule**: IF goal_race = 5K THEN schedule minimum 2 VO₂max sessions per week + 1 LT session during race-specific phase
- **Source**: Pfitz-FRR `[§4.10]`
- **Priority**: Low

- **Agent**: Running Coach
- **Rule**: IF goal_race = half_marathon THEN schedule 1 VO₂max session + 1–2 LT sessions per week + at least 1 HM-pace run per week in final 6 weeks
- **Source**: Pfitz-FRR `[§4.10]`
- **Priority**: Low

---

## 5. Cross-Book Compatibility Notes

**Volume progression (10% cap):** Daniels, Pfitz-Adv, and Pfitz-FRR all state the same 10% weekly volume cap as a hard, non-negotiable ceiling. There is no conflict here; this rule can be encoded as a universal guardrail in the Running Coach prompt. 80/20 and FIRST do not address volume progression explicitly in percentage terms (80/20 focuses on TID; FIRST fixes total volume via its 3-run structure), but neither contradicts the 10% rule. Pfitz-Adv adds a secondary cap of ≤ 1 mile per session per week (e.g., 6 sessions × 1 mile = 6 miles max increase), which acts as an additional binding constraint at lower mileage levels.

**Intensity distribution (80/20 vs. Daniels zones vs. FIRST):** All three models are compatible when mapped onto a common HR/effort framework. Daniels' E-pace corresponds closely to 80/20's Zone 1-2 (both are "conversational" below VT1). Daniels' T-pace maps to 80/20's Zone 3-4 boundary (comfortably hard, around LT). Daniels' I-pace corresponds to 80/20's Zone 5 (VO₂max effort). FIRST's Track Repeats operate at Zone 4-5, Tempo at Zone 3, and Long Run at Zone 1-2. The 80/20 rule (80% at Z1-2) is consistent with Daniels' typical session distribution and with both Pfitzinger books (majority of weekly mileage at GA or recovery pace). FIRST is the structural outlier — it has no easy runs — but a FIRST athlete's training time distribution still approximates a polarized model because 3+ days/week are XT at moderate effort, not high-intensity running.

**Long run (consensus on % of weekly mileage):** There is broad directional agreement that the long run should not dominate weekly mileage disproportionately, but the specific cap varies: Daniels (25–30%), Pfitz-Adv (22–29%), Pfitz-FRR (20–25%). The Pfitzinger books show a consistent pattern: the cap decreases as goal race distance decreases. Daniels is slightly more permissive, likely because his duration cap (150 min) acts as the binding constraint for slower runners. FIRST and 80/20 do not use percentage rules. A safe integration approach is to use the strictest applicable Pfitzinger cap (22–29% for marathon, 20–25% for FRR distances) and layer Daniels' 150-min duration cap on top for slow runners.

**Recovery / deload (consensus on cutback frequency):** Pfitz-Adv and Pfitz-FRR agree precisely: cutback week every 3–4 weeks, volume reduced by 20–25%. Daniels prescribes holding each new stress level for 3–4 weeks before increasing again, which is the same cadence expressed differently. CLAUDE.md's training rules also specify every 3–4 weeks at 20–30% reduction. 80/20 does not specify a cutback cadence but its base/peak/taper phase structure implicitly embeds volume variation. FIRST has no cutback protocol because its volume is fixed per the plan tables. Overall consensus: 3–4 weeks is the appropriate deload frequency for all volume-progressive plans.

**Quality sessions per week (FIRST=3, Pfitzinger=2–3, Daniels=2–3, 80/20=2 Z4-5):** These numbers are more compatible than they appear at first glance. FIRST's 3 sessions include one Tempo Run (roughly Zone 3 effort), which 80/20 does not count in its strict Z4-5 cap. Mapping FIRST to 80/20's framework: Track Repeats + Long Run = 2 Z4-5 sessions; Tempo Run = Zone 3 session. This satisfies 80/20's hard cap of 2 Z4-5 sessions per week. Pfitzinger (2–3 hard sessions) and Daniels (2–3 Q days) are directly compatible with FIRST's structure. The practical integration rule for the Running Coach agent: cap Z4-5 sessions at 2/week universally (80/20); allow up to one additional Zone 3 session (tempo/LT) per week (FIRST, Pfitzinger, Daniels all endorse this pattern).

---

## 6. Source File Map

| Extract file | Book |
|---|---|
| `daniels-running-formula-extract.md` | Daniels' Running Formula (Jack Daniels, 3rd ed., Human Kinetics) |
| `pfitzinger-advanced-marathoning-extract.md` | Advanced Marathoning (Pete Pfitzinger & Scott Douglas, 2nd ed., Human Kinetics) |
| `pfitzinger-faster-road-racing-extract.md` | Faster Road Racing (Pete Pfitzinger & Philip Latter, Human Kinetics, 2015) |
| `fitzgerald-8020-extract.md` | 80/20 Running (Matt Fitzgerald, New American Library, 2014) |
| `pierce-first-extract.md` | Run Less, Run Faster (Bill Pierce, Scott Murr & Ray Moss, 2nd ed., Rodale) |
