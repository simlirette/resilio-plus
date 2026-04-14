# Knowledge JSONs — Audit, Enrichment & Validation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich 9 JSON knowledge files to a standardized schema with 10–20 rules each, add JSON Schema validation, and add a pytest suite covering all files.

**Architecture:** Common envelope schema (schema_version, target_agent, language, last_updated, source_books, extracted_rules) applied to all 9 files. Each rule gets priority/confidence/source/applies_to fields. JSON Schemas enforce the contract. Pytest parametrizes over all 9 files. One commit per file.

**Tech Stack:** Python 3.13, jsonschema library, pytest, JSON. Pytest path: `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe`

---

## File Map

**Create:**
- `docs/knowledge/schemas/common_rule.schema.json` — shared rule schema
- `docs/knowledge/schemas/biking_coach_power_rules.schema.json`
- `docs/knowledge/schemas/head_coach_acwr_rules.schema.json`
- `docs/knowledge/schemas/head_coach_interference_rules.schema.json`
- `docs/knowledge/schemas/lifting_coach_volume_rules.schema.json`
- `docs/knowledge/schemas/nutrition_coach_fueling_rules.schema.json`
- `docs/knowledge/schemas/recovery_coach_hrv_rules.schema.json`
- `docs/knowledge/schemas/recovery_coach_sleep_cns_rules.schema.json`
- `docs/knowledge/schemas/running_coach_tid_rules.schema.json`
- `docs/knowledge/schemas/swimming_coach_biomechanics_rules.schema.json`
- `tests/backend/test_knowledge_jsons.py`
- `docs/backend/KNOWLEDGE-JSONS.md`

**Modify:**
- `docs/knowledge/biking_coach_power_rules.json`
- `docs/knowledge/head_coach_acwr_rules.json`
- `docs/knowledge/head_coach_interference_rules.json` (invalid — full rewrite)
- `docs/knowledge/lifting_coach_volume_rules.json`
- `docs/knowledge/nutrition_coach_fueling_rules.json`
- `docs/knowledge/recovery_coach_hrv_rules.json`
- `docs/knowledge/recovery_coach_sleep_cns_rules.json`
- `docs/knowledge/running_coach_tid_rules.json`
- `docs/knowledge/swimming_coach_biomechanics_rules.json`
- `.gitignore`

---

## Task 1: Install jsonschema + update .gitignore

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Install jsonschema**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pip.exe install jsonschema
```

Expected output contains: `Successfully installed jsonschema`

- [ ] **Step 2: Add *.backup to .gitignore**

Append to `.gitignore`:
```
# Knowledge JSON backups
*.json.backup
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: add *.json.backup to .gitignore"
```

---

## Task 2: Create JSON Schema files

**Files:**
- Create: `docs/knowledge/schemas/` (all 10 schema files)

- [ ] **Step 1: Create schemas directory and common schema**

Create `docs/knowledge/schemas/common_rule.schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "description": "Common schema for all Resilio knowledge JSON files",
  "type": "object",
  "required": ["schema_version", "target_agent", "language", "last_updated", "extracted_rules"],
  "additionalProperties": true,
  "properties": {
    "schema_version": { "type": "string", "const": "1.0" },
    "target_agent": {
      "type": "string",
      "enum": ["Head Coach", "Running Coach", "Lifting Coach", "Swimming Coach", "Biking Coach", "Nutrition Coach", "Recovery Coach"]
    },
    "language": { "type": "string", "enum": ["en"] },
    "last_updated": { "type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$" },
    "source_books": { "type": "array", "items": { "type": "string" } },
    "extracted_rules": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["rule_name", "category", "condition", "action", "formula_or_value", "priority", "confidence", "source", "applies_to"],
        "properties": {
          "rule_name":        { "type": "string", "minLength": 1 },
          "category":         { "type": "string", "minLength": 1 },
          "condition":        { "type": "string", "minLength": 1 },
          "action":           { "type": "string", "minLength": 1 },
          "formula_or_value": { "type": "string", "minLength": 1, "not": { "const": "N/A" } },
          "priority":         { "type": "string", "enum": ["high", "medium", "low"] },
          "confidence":       { "type": "string", "enum": ["strong", "moderate", "weak"] },
          "source":           { "type": "string", "minLength": 1 },
          "applies_to":       { "type": "array", "minItems": 1, "items": { "type": "string" } }
        }
      }
    }
  }
}
```

- [ ] **Step 2: Create per-file schemas (all reference common via $ref pattern)**

Each file gets an identical schema that references the same rules. Create these 9 files with identical content (just the description differs):

`docs/knowledge/schemas/running_coach_tid_rules.schema.json`:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "description": "Schema for running_coach_tid_rules.json",
  "$ref": "common_rule.schema.json"
}
```

Repeat for each of the 8 remaining files, changing only the `description` field:
- `biking_coach_power_rules.schema.json` → description: "Schema for biking_coach_power_rules.json"
- `head_coach_acwr_rules.schema.json` → description: "Schema for head_coach_acwr_rules.json"
- `head_coach_interference_rules.schema.json` → description: "Schema for head_coach_interference_rules.json"
- `lifting_coach_volume_rules.schema.json` → description: "Schema for lifting_coach_volume_rules.json"
- `nutrition_coach_fueling_rules.schema.json` → description: "Schema for nutrition_coach_fueling_rules.json"
- `recovery_coach_hrv_rules.schema.json` → description: "Schema for recovery_coach_hrv_rules.json"
- `recovery_coach_sleep_cns_rules.schema.json` → description: "Schema for recovery_coach_sleep_cns_rules.schema.json"
- `swimming_coach_biomechanics_rules.schema.json` → description: "Schema for swimming_coach_biomechanics_rules.json"

- [ ] **Step 3: Commit schemas**

```bash
git add docs/knowledge/schemas/
git commit -m "feat(knowledge): add JSON Schema files for all 9 knowledge JSONs"
```

---

## Task 3: Write failing tests

**Files:**
- Create: `tests/backend/test_knowledge_jsons.py`

- [ ] **Step 1: Write the test file**

Create `tests/backend/test_knowledge_jsons.py`:

```python
"""Validation tests for all 9 knowledge JSON files in docs/knowledge/."""
import json
import pytest
import jsonschema
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
KNOWLEDGE_DIR = REPO_ROOT / "docs" / "knowledge"
SCHEMA_DIR = KNOWLEDGE_DIR / "schemas"
COMMON_SCHEMA_PATH = SCHEMA_DIR / "common_rule.schema.json"

KNOWN_AGENTS = {
    "Head Coach", "Running Coach", "Lifting Coach",
    "Swimming Coach", "Biking Coach", "Nutrition Coach", "Recovery Coach",
}

JSON_FILES = [
    "biking_coach_power_rules.json",
    "head_coach_acwr_rules.json",
    "head_coach_interference_rules.json",
    "lifting_coach_volume_rules.json",
    "nutrition_coach_fueling_rules.json",
    "recovery_coach_hrv_rules.json",
    "recovery_coach_sleep_cns_rules.json",
    "running_coach_tid_rules.json",
    "swimming_coach_biomechanics_rules.json",
]


def load_json(filename: str) -> dict:
    path = KNOWLEDGE_DIR / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_schema() -> dict:
    with open(COMMON_SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize("filename", JSON_FILES)
def test_valid_json(filename):
    """File must parse as valid JSON without errors."""
    data = load_json(filename)
    assert isinstance(data, dict)


@pytest.mark.parametrize("filename", JSON_FILES)
def test_schema_version(filename):
    """schema_version must be '1.0'."""
    data = load_json(filename)
    assert data.get("schema_version") == "1.0", (
        f"{filename}: expected schema_version='1.0', got {data.get('schema_version')!r}"
    )


@pytest.mark.parametrize("filename", JSON_FILES)
def test_target_agent_valid(filename):
    """target_agent must be one of the 7 known agents."""
    data = load_json(filename)
    assert data.get("target_agent") in KNOWN_AGENTS, (
        f"{filename}: unknown target_agent {data.get('target_agent')!r}"
    )


@pytest.mark.parametrize("filename", JSON_FILES)
def test_language_is_english(filename):
    """language must be 'en'."""
    data = load_json(filename)
    assert data.get("language") == "en", (
        f"{filename}: expected language='en', got {data.get('language')!r}"
    )


@pytest.mark.parametrize("filename", JSON_FILES)
def test_rules_not_empty(filename):
    """extracted_rules must be a non-empty list."""
    data = load_json(filename)
    rules = data.get("extracted_rules", [])
    assert len(rules) > 0, f"{filename}: extracted_rules is empty"


@pytest.mark.parametrize("filename", JSON_FILES)
def test_no_na_formula(filename):
    """No rule may have formula_or_value == 'N/A'."""
    data = load_json(filename)
    for rule in data.get("extracted_rules", []):
        assert rule.get("formula_or_value", "") != "N/A", (
            f"{filename}: rule '{rule.get('rule_name')}' has formula_or_value='N/A'"
        )


@pytest.mark.parametrize("filename", JSON_FILES)
def test_all_rules_have_required_fields(filename):
    """Every rule must have priority, confidence, source, and applies_to."""
    data = load_json(filename)
    required = {"priority", "confidence", "source", "applies_to"}
    for rule in data.get("extracted_rules", []):
        missing = required - set(rule.keys())
        assert not missing, (
            f"{filename}: rule '{rule.get('rule_name')}' missing fields: {missing}"
        )


@pytest.mark.parametrize("filename", JSON_FILES)
def test_priority_enum(filename):
    """priority must be 'high', 'medium', or 'low'."""
    data = load_json(filename)
    valid = {"high", "medium", "low"}
    for rule in data.get("extracted_rules", []):
        assert rule.get("priority") in valid, (
            f"{filename}: rule '{rule.get('rule_name')}' has invalid priority={rule.get('priority')!r}"
        )


@pytest.mark.parametrize("filename", JSON_FILES)
def test_confidence_enum(filename):
    """confidence must be 'strong', 'moderate', or 'weak'."""
    data = load_json(filename)
    valid = {"strong", "moderate", "weak"}
    for rule in data.get("extracted_rules", []):
        assert rule.get("confidence") in valid, (
            f"{filename}: rule '{rule.get('rule_name')}' has invalid confidence={rule.get('confidence')!r}"
        )


@pytest.mark.parametrize("filename", JSON_FILES)
def test_schema_conformance(filename):
    """File must conform to the common JSON Schema."""
    data = load_json(filename)
    schema = load_schema()
    # Remove $ref for inline validation (jsonschema draft-07 resolver)
    schema.pop("$ref", None)
    jsonschema.validate(instance=data, schema=schema)
```

- [ ] **Step 2: Run tests — expect most to fail**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_knowledge_jsons.py -v 2>&1 | head -60
```

Expected: majority FAILED (files lack schema_version, priority, confidence, etc.)

- [ ] **Step 3: Commit test file**

```bash
git add tests/backend/test_knowledge_jsons.py
git commit -m "test(knowledge): add parametrized validation suite for 9 knowledge JSONs"
```

---

## Task 4: Enrich running_coach_tid_rules.json (Priority 1)

**Files:**
- Modify: `docs/knowledge/running_coach_tid_rules.json`

- [ ] **Step 1: Backup**

```bash
cp docs/knowledge/running_coach_tid_rules.json docs/knowledge/running_coach_tid_rules.json.backup
```

- [ ] **Step 2: Write enriched file**

Write `docs/knowledge/running_coach_tid_rules.json`:

```json
{
  "schema_version": "1.0",
  "target_agent": "Running Coach",
  "language": "en",
  "last_updated": "2026-04-13",
  "source_books": [
    "daniels-running-formula",
    "pfitzinger-advanced-marathoning",
    "pfitzinger-faster-road-racing",
    "fitzgerald-8020",
    "pierce-first"
  ],
  "extracted_rules": [
    {
      "rule_name": "80/20 TID — polarized split default",
      "category": "Intensity Distribution",
      "condition": "If athlete trains for any endurance event and no specific methodology is prescribed",
      "action": "Distribute at least 80% of weekly training TIME at Zone 1-2 (below first ventilatory threshold) and no more than 20% at Zone 3+",
      "formula_or_value": "Z1-2: ≥80% of weekly training time; Z3+: ≤20%; measured in minutes, not distance or sessions",
      "priority": "high",
      "confidence": "strong",
      "source": "Fitzgerald 80/20 Running + Seiler 2010 polarized model meta-analysis",
      "applies_to": ["running", "cycling", "swimming"]
    },
    {
      "rule_name": "Polarized TID — VO2max and work economy",
      "category": "Intensity Distribution",
      "condition": "If objective is to improve VO2max and work economy in endurance runners",
      "action": "Apply polarized intensity distribution: 15-20% high-intensity, 75-80% low-intensity",
      "formula_or_value": "HIT: 15-20% of weekly volume; LIT: 75-80%; threshold work: remaining 5-10%",
      "priority": "high",
      "confidence": "strong",
      "source": "Systematic review: polarized TID vs threshold TID in endurance athletes (running_coach_tid_rules original)",
      "applies_to": ["running"]
    },
    {
      "rule_name": "VDOT — derive training paces from race performance",
      "category": "Pace Prescription",
      "condition": "If athlete has a recent race time (within 4-6 weeks) for any standard distance",
      "action": "Look up VDOT from Daniels Table 5.1 using race distance + time, then derive all training paces (E/M/T/I/R) from Table 5.2",
      "formula_or_value": "VDOT = lookup(race_distance, race_time) → E_pace, M_pace, T_pace, I_pace, R_pace from Table 5.2",
      "priority": "high",
      "confidence": "strong",
      "source": "Daniels' Running Formula, 3rd ed., Tables 5.1 and 5.2",
      "applies_to": ["running"]
    },
    {
      "rule_name": "6-Second Rule — pace zone spacing",
      "category": "Pace Prescription",
      "condition": "If athlete has a recent mile time but no full race time for VDOT lookup, and VDOT > 50",
      "action": "Use mile race pace as R-pace; each slower zone adds 6 sec/400m: R → I (+6s) → T (+12s)",
      "formula_or_value": "I_pace = R_pace + 6s per 400m; T_pace = I_pace + 6s per 400m; for VDOT 40-50 use 7-8s; R is fastest",
      "priority": "medium",
      "confidence": "strong",
      "source": "Daniels' Running Formula, 3rd ed., §2",
      "applies_to": ["running"]
    },
    {
      "rule_name": "Easy pace (E-pace) zone",
      "category": "Pace Zones",
      "condition": "If scheduling an easy or recovery run",
      "action": "Run at fully conversational effort; no HR cap specified; this forms 60-75% of weekly mileage",
      "formula_or_value": "Conversational pace; ~59-74% vVO2max; 60-75% of total weekly volume at this intensity",
      "priority": "high",
      "confidence": "strong",
      "source": "Daniels' Running Formula §2 E-Pace",
      "applies_to": ["running"]
    },
    {
      "rule_name": "Threshold pace (T-pace) zone and volume cap",
      "category": "Pace Zones",
      "condition": "If scheduling a tempo or lactate threshold session",
      "action": "Run at 'comfortably hard' controlled effort; cap T-pace volume at 10% of weekly mileage per session",
      "formula_or_value": "~83-88% vVO2max; max T-volume per session = weekly_mileage × 10%",
      "priority": "high",
      "confidence": "strong",
      "source": "Daniels' Running Formula §2 T-Pace",
      "applies_to": ["running"]
    },
    {
      "rule_name": "Interval pace (I-pace) zone and volume cap",
      "category": "Pace Zones",
      "condition": "If scheduling interval work targeting VO2max",
      "action": "Run 3-5 min work bouts at I-pace; recovery ≥ work duration; cap session volume",
      "formula_or_value": "~95-100% vVO2max; work bouts: 3-5 min; recovery: ≥ work duration; max I-volume = min(10 km, weekly_mileage × 8%)",
      "priority": "high",
      "confidence": "strong",
      "source": "Daniels' Running Formula §2 I-Pace",
      "applies_to": ["running"]
    },
    {
      "rule_name": "Repetition pace (R-pace) zone and volume cap",
      "category": "Pace Zones",
      "condition": "If scheduling speed and running economy work (200-400m reps)",
      "action": "Run 200-400m at R-pace; near-full recovery (2-3× work duration); cap session volume",
      "formula_or_value": "~105-120% vVO2max; work bouts: ≤2 min; recovery: 2-3× work duration; max R-volume = min(8 km, weekly_mileage × 5%)",
      "priority": "medium",
      "confidence": "strong",
      "source": "Daniels' Running Formula §2 R-Pace",
      "applies_to": ["running"]
    },
    {
      "rule_name": "10% weekly volume progression cap",
      "category": "Load Management",
      "condition": "Always — when increasing weekly mileage",
      "action": "Never increase weekly mileage by more than 10% over the previous week; hold new level 3-4 weeks before next increase",
      "formula_or_value": "new_weekly_mileage ≤ previous_week_mileage × 1.10; hold 3-4 weeks before next increase",
      "priority": "high",
      "confidence": "strong",
      "source": "Daniels' Running Formula §2; Pfitzinger Advanced Marathoning Ch.2; consensus across all 5 books",
      "applies_to": ["running"]
    },
    {
      "rule_name": "Long run ceiling — marathon plan",
      "category": "Load Management",
      "condition": "If athlete is on a marathon training plan",
      "action": "Cap long run distance and duration using the most conservative binding rule",
      "formula_or_value": "long_run ≤ min(weekly_mileage × 0.29, 22 miles) AND projected_duration ≤ 210 min (3.5 h); Pfitz-Adv rule is primary",
      "priority": "high",
      "confidence": "strong",
      "source": "Pfitzinger Advanced Marathoning; Daniels (25-30% + 150 min cap); INDEX.md conflict resolution",
      "applies_to": ["running"]
    },
    {
      "rule_name": "Long run ceiling — 5K to half-marathon plan",
      "category": "Load Management",
      "condition": "If athlete is on a 5K, 10K, or half-marathon training plan",
      "action": "Cap long run at 20-25% of weekly mileage; no absolute distance cap for these distances",
      "formula_or_value": "long_run ≤ weekly_mileage × 0.20-0.25; no absolute mi cap for sub-marathon",
      "priority": "high",
      "confidence": "strong",
      "source": "Pfitzinger Faster Road Racing; INDEX.md coverage matrix",
      "applies_to": ["running"]
    },
    {
      "rule_name": "Cutback week protocol",
      "category": "Load Management",
      "condition": "If athlete has trained at consistent volume for 3-4 weeks",
      "action": "Schedule a cutback week with 20-25% volume reduction; maintain intensity, reduce mileage only",
      "formula_or_value": "Every 3-4 weeks: volume reduction = 20-25%; intensity sessions unchanged",
      "priority": "high",
      "confidence": "strong",
      "source": "Pfitzinger Advanced Marathoning Ch.2; Pfitzinger Faster Road Racing",
      "applies_to": ["running"]
    },
    {
      "rule_name": "Quality session limits per week",
      "category": "Session Structure",
      "condition": "Always — when scheduling weekly training",
      "action": "Limit quality sessions (containing T/I/R pace work or Z4-5) to ≤3/week for all athletes; Z4-5 sessions hard-capped at 2/week regardless of level",
      "formula_or_value": "Q-days ≤ 3/week; Z4-5 sessions ≤ 2/week (all athletes); never schedule 2 consecutive hard days",
      "priority": "high",
      "confidence": "strong",
      "source": "Daniels' Running Formula §2; Fitzgerald 80/20 Ch.3; INDEX.md conflict resolution",
      "applies_to": ["running"]
    },
    {
      "rule_name": "Return-from-break — short break",
      "category": "Return to Training",
      "condition": "If athlete returns after a break of ≤5 days",
      "action": "Resume at 100% of previous training load; no adjustment needed",
      "formula_or_value": "Break ≤5 days → resume at 100% load; no VDOT adjustment",
      "priority": "high",
      "confidence": "strong",
      "source": "Daniels' Running Formula §3, Table 9.2",
      "applies_to": ["running"]
    },
    {
      "rule_name": "Return-from-break — medium break (6-28 days)",
      "category": "Return to Training",
      "condition": "If athlete returns after a break of 6-28 days",
      "action": "Resume at 50% load for first half of return period, then 75% for second half; adjust VDOT by -1 to -3 points",
      "formula_or_value": "Break 6-28 days → first half at 50%, second half at 75%; VDOT adjustment: ×0.93-0.99",
      "priority": "high",
      "confidence": "strong",
      "source": "Daniels' Running Formula §3, Table 9.2",
      "applies_to": ["running"]
    },
    {
      "rule_name": "Return-from-break — long break (>8 weeks)",
      "category": "Return to Training",
      "condition": "If athlete returns after a break of more than 8 weeks",
      "action": "Start at 33-50% of previous load; recalculate VDOT from a recent time trial; expect significant fitness decay",
      "formula_or_value": "Break >8 wk → start at 33-50% load; VDOT × 0.80-0.92; new race or time trial required to reset paces",
      "priority": "high",
      "confidence": "strong",
      "source": "Daniels' Running Formula §3, Table 9.2",
      "applies_to": ["running"]
    },
    {
      "rule_name": "Altitude adjustment",
      "category": "Environmental Adaptation",
      "condition": "If training at altitude ≥7,000 feet (2,133 m)",
      "action": "Keep R-pace unchanged; adjust I and T sessions by effort (not pace); expect paces to be 3-5% slower at same physiological cost",
      "formula_or_value": "Altitude ≥7,000 ft: R_pace unchanged; I and T → run by effort; expected pace slowing: 3-5%",
      "priority": "medium",
      "confidence": "strong",
      "source": "Daniels' Running Formula §3",
      "applies_to": ["running"]
    },
    {
      "rule_name": "Warm-up protocol for quality sessions",
      "category": "Session Structure",
      "condition": "Before any T, I, or R-pace session",
      "action": "Run 10-15 min at E-pace, then 4-6 strides (20-30 sec at R-pace effort); cool down 10-15 min E-pace after session",
      "formula_or_value": "Warm-up: 10-15 min E-pace + 4-6 strides × 20-30s at R-effort; cool-down: 10-15 min E-pace",
      "priority": "medium",
      "confidence": "strong",
      "source": "Daniels' Running Formula §2; Pfitzinger Advanced Marathoning Ch.3",
      "applies_to": ["running"]
    },
    {
      "rule_name": "Marathon taper structure",
      "category": "Taper",
      "condition": "If athlete is tapering for a marathon (A-race)",
      "action": "Apply 3-week taper: each week reduce volume by 20%, 40%, 60% from peak; maintain intensity throughout",
      "formula_or_value": "Week -3: volume × 0.80; Week -2: volume × 0.60; Week -1 (race week): volume × 0.40; intensity sessions maintained",
      "priority": "high",
      "confidence": "strong",
      "source": "Pfitzinger Advanced Marathoning Ch.9",
      "applies_to": ["running"]
    },
    {
      "rule_name": "Cross-training equivalency",
      "category": "Cross-Training",
      "condition": "If athlete substitutes cycling or pool running for road running sessions",
      "action": "Apply equivalency factor to compare aerobic load; maintain 80/20 TID across all modalities",
      "formula_or_value": "Cycling: 1.5× bike miles = 1 run mile (aerobic equivalency); pool running: target HR −10% vs equivalent road run HR",
      "priority": "medium",
      "confidence": "moderate",
      "source": "Pfitzinger Advanced Marathoning; Fitzgerald 80/20 Running",
      "applies_to": ["running", "cycling"]
    }
  ]
}
```

- [ ] **Step 3: Run tests for this file**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_knowledge_jsons.py -k "running" -v
```

Expected: all 10 parametrized tests for `running_coach_tid_rules.json` PASS.

- [ ] **Step 4: Commit**

```bash
git add docs/knowledge/running_coach_tid_rules.json
git commit -m "feat(knowledge): enrich running_coach_tid_rules — 2 to 20 rules, VDOT zones, taper, cutback"
```

---

## Task 5: Enrich head_coach_acwr_rules.json (Priority 2)

**Files:**
- Modify: `docs/knowledge/head_coach_acwr_rules.json`

- [ ] **Step 1: Backup**

```bash
cp docs/knowledge/head_coach_acwr_rules.json docs/knowledge/head_coach_acwr_rules.json.backup
```

- [ ] **Step 2: Write enriched file**

Write `docs/knowledge/head_coach_acwr_rules.json`:

```json
{
  "schema_version": "1.0",
  "target_agent": "Head Coach",
  "language": "en",
  "last_updated": "2026-04-13",
  "source_books": [],
  "extracted_rules": [
    {
      "rule_name": "ACWR safe zone — no action",
      "category": "Load Management",
      "condition": "If athlete's ACWR is between 0.8 and 1.3",
      "action": "Training load is in the safe zone; proceed with planned sessions; no modification required",
      "formula_or_value": "ACWR 0.8–1.3: safe zone; no intervention",
      "priority": "high",
      "confidence": "strong",
      "source": "ACWR meta-analysis (head_coach_acwr_rules original); Gabbett 2016; CLAUDE.md ACWR section",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "ACWR caution zone — flag and reduce",
      "category": "Load Management",
      "condition": "If athlete's ACWR is between 1.3 and 1.5",
      "action": "Flag elevated injury risk to athlete; reduce the next planned session load by 10-15%; do not increase load until ACWR returns to safe zone",
      "formula_or_value": "ACWR 1.3–1.5: caution zone; reduce next session load by 10-15%; flag athlete",
      "priority": "high",
      "confidence": "strong",
      "source": "Gabbett 2016 ACWR injury risk meta-analysis; CLAUDE.md ACWR section",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "ACWR danger zone — mandatory load reduction",
      "category": "Load Management",
      "condition": "If athlete's ACWR exceeds 1.5",
      "action": "Mandatory significant load reduction; notify athlete of high injury risk; replace planned hard sessions with easy/recovery sessions until ACWR drops below 1.3",
      "formula_or_value": "ACWR >1.5: danger zone; mandatory load reduction; replace hard sessions with easy/recovery",
      "priority": "high",
      "confidence": "strong",
      "source": "Gabbett 2016 ACWR injury risk meta-analysis; CLAUDE.md ACWR section",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "ACWR formula — EWMA-based",
      "category": "Load Calculation",
      "condition": "When computing ACWR for any athlete",
      "action": "Use EWMA (not simple rolling average) for both acute (7-day) and chronic (28-day) load windows",
      "formula_or_value": "ACWR = EWMA_7d_load / EWMA_28d_load; EWMA_n = load_n × λ + EWMA_{n-1} × (1 − λ); λ_acute = 2/(7+1)=0.25; λ_chronic = 2/(28+1)=0.067",
      "priority": "high",
      "confidence": "strong",
      "source": "Hulin et al. 2016; CLAUDE.md ACWR section",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "Multi-sport combined load for ACWR",
      "category": "Load Calculation",
      "condition": "If athlete trains across multiple sports (hybrid athlete)",
      "action": "Sum TSS-equivalent load across all sports before computing ACWR; do not compute separate ACWRs per sport",
      "formula_or_value": "total_daily_load = Σ(sport_TSS_equivalent); ACWR computed on total_daily_load; run TSS: hours × IF² × 100; cycling TSS: standard",
      "priority": "high",
      "confidence": "strong",
      "source": "CLAUDE.md ACWR section; strain.py EWMA implementation",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "10% weekly total load cap — all sports combined",
      "category": "Load Management",
      "condition": "Always — when planning the next training week for any athlete",
      "action": "Never increase total weekly load (across all sports) by more than 10% from the previous week",
      "formula_or_value": "next_week_total_load ≤ current_week_total_load × 1.10",
      "priority": "high",
      "confidence": "strong",
      "source": "CLAUDE.md Development Rules; consensus across Daniels, Pfitzinger",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "Trail running eccentric load multiplier",
      "category": "Load Calculation",
      "condition": "If athlete performs trail running, especially with significant elevation change",
      "action": "Apply eccentric load multiplier to TSS; monitor biochemical and neuromuscular markers post-session",
      "formula_or_value": "Trail run TSS multiplier: 1.1–1.3× road equivalent (higher on steep descents); monitor CK and RPE next morning",
      "priority": "medium",
      "confidence": "moderate",
      "source": "Systematic review: muscle damage in trail running (head_coach_acwr_rules original)",
      "applies_to": ["running"]
    },
    {
      "rule_name": "Kinetic variables for lower limb injury monitoring",
      "category": "Injury Prevention",
      "condition": "If athlete shows ACWR >1.3 AND reports lower limb fatigue or asymmetry",
      "action": "Flag for kinetic variable assessment; specifically monitor eccentric hamstring strength and concentric quad torque; integrate with wellness scores",
      "formula_or_value": "Flag: ACWR >1.3 + lower limb fatigue report → request kinetic assessment; eccentric hamstring / concentric quad ratio <0.6 = elevated risk",
      "priority": "medium",
      "confidence": "moderate",
      "source": "Systematic review: kinetic variables and lower limb injury in soccer (head_coach_acwr_rules original)",
      "applies_to": ["running", "lifting"]
    },
    {
      "rule_name": "Strength training adherence reduces injury risk",
      "category": "Injury Prevention",
      "condition": "If athlete participates in contact or high-impact sports",
      "action": "Prescribe and monitor adherence to strength training; consistent strength training reduces sports injury rate",
      "formula_or_value": "Consistent strength training adherence: reduces injury rate (meta-analysis effect; RR reduction significant in contact sports)",
      "priority": "high",
      "confidence": "strong",
      "source": "Meta-analysis: strength training adherence and injury rates in contact sports (head_coach_acwr_rules original)",
      "applies_to": ["running", "lifting", "cycling"]
    },
    {
      "rule_name": "Integrated injury risk assessment",
      "category": "Injury Prevention",
      "condition": "When evaluating overall injury risk for any athlete",
      "action": "Integrate ACWR data with contextual indicators: wellness score, RPE trend, sleep quality, and training monotony",
      "formula_or_value": "Risk score = f(ACWR, wellness_score, RPE_trend, sleep_hours, training_monotony); flag if ≥2 indicators are elevated simultaneously",
      "priority": "high",
      "confidence": "moderate",
      "source": "Systematic review: integrated injury risk assessment (head_coach_acwr_rules original)",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    }
  ]
}
```

- [ ] **Step 3: Run tests for this file**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_knowledge_jsons.py -k "acwr" -v
```

Expected: all tests PASS for `head_coach_acwr_rules.json`.

- [ ] **Step 4: Commit**

```bash
git add docs/knowledge/head_coach_acwr_rules.json
git commit -m "feat(knowledge): enrich head_coach_acwr_rules — add ACWR thresholds, EWMA formula, multi-sport load"
```

---

## Task 6: Fix and enrich head_coach_interference_rules.json (Priority 3)

**Files:**
- Modify: `docs/knowledge/head_coach_interference_rules.json` (full rewrite — file is invalid JSON)

- [ ] **Step 1: Backup the broken file**

```bash
cp docs/knowledge/head_coach_interference_rules.json docs/knowledge/head_coach_interference_rules.json.backup
```

- [ ] **Step 2: Write valid enriched file**

The original file has UTF-8 encoding corruption making it invalid JSON. Rewrite completely in English, preserving the scientific content from the source articles plus new rules.

Write `docs/knowledge/head_coach_interference_rules.json`:

```json
{
  "schema_version": "1.0",
  "target_agent": "Head Coach",
  "language": "en",
  "last_updated": "2026-04-13",
  "source_books": [],
  "extracted_rules": [
    {
      "rule_name": "Concurrent HIIT + resistance — preserve musculoskeletal function",
      "category": "Concurrent Training",
      "condition": "If program combines HIIT and resistance training over 8-12 weeks",
      "action": "Design the program to improve or maintain maximal strength, explosive performance, neuromuscular activation, and muscle size simultaneously",
      "formula_or_value": "Program duration: 8-12 weeks; resistance sessions: 2-3/week; HIIT sessions: 2-3/week; interference minimal when structured correctly",
      "priority": "high",
      "confidence": "strong",
      "source": "Systematic review: concurrent HIIT and resistance training for musculoskeletal function",
      "applies_to": ["running", "cycling", "lifting"]
    },
    {
      "rule_name": "Sprint interval training (SIT) — no interference on strength or power",
      "category": "Concurrent Training",
      "condition": "If SIT (sprint intervals) is integrated into a concurrent training program with resistance training",
      "action": "Do not expect reduction in strength or power gains; SIT improves cardiorespiratory fitness without compromising resistance training adaptations",
      "formula_or_value": "SIT + RT: no significant difference in strength/power vs RT alone; cardiorespiratory fitness improves with SIT addition",
      "priority": "high",
      "confidence": "strong",
      "source": "Meta-analysis: does SIT cause interference in concurrent training (lifting_coach_volume_rules + head_coach_interference original)",
      "applies_to": ["lifting", "running", "cycling"]
    },
    {
      "rule_name": "Short sprint protocols preserve jump performance",
      "category": "Concurrent Training",
      "condition": "If goal is to maintain or improve jump performance (vertical/horizontal power) in a concurrent training program",
      "action": "Include sprint protocols of ≤10 seconds duration; longer sprint protocols may impair jump performance adaptations",
      "formula_or_value": "Sprint duration ≤10 seconds: jump performance maintained or improved; >10s sprints: potential interference with power adaptations",
      "priority": "medium",
      "confidence": "moderate",
      "source": "Meta-analysis: SIT and interference in concurrent training (original source articles)",
      "applies_to": ["running", "lifting"]
    },
    {
      "rule_name": "Heavy strength training improves endurance cycling economy",
      "category": "Concurrent Training",
      "condition": "If an endurance cyclist (or triathlete) adds heavy resistance training to their program",
      "action": "Expect improvement in cycling economy and endurance performance; heavy strength training does not cause interference in trained cyclists",
      "formula_or_value": "Heavy RT (≥85% 1RM, 3-5 sets, 2-4 reps) 2-3×/week: improves economy; no significant VO2max or LT interference in trained cyclists",
      "priority": "high",
      "confidence": "strong",
      "source": "Systematic review with meta-analysis: heavy strength training effects on endurance cyclist performance (original source articles)",
      "applies_to": ["cycling", "lifting"]
    },
    {
      "rule_name": "Session order — strength before endurance (same day)",
      "category": "Session Scheduling",
      "condition": "If strength and endurance sessions must be performed on the same day",
      "action": "Schedule strength session first, followed by the endurance session; this order minimizes interference with strength adaptations",
      "formula_or_value": "Same-day ordering: Strength → Endurance; reverse order (Endurance → Strength) reduces maximal strength adaptation by ~10-15%",
      "priority": "high",
      "confidence": "strong",
      "source": "Coffey & Hawley 2017; concurrent training interference research consensus",
      "applies_to": ["lifting", "running", "cycling"]
    },
    {
      "rule_name": "Minimum interference gap between sessions",
      "category": "Session Scheduling",
      "condition": "If strength and endurance sessions are on the same day and session order matters",
      "action": "Separate strength and endurance sessions by at least 6 hours to allow partial recovery and minimize interference",
      "formula_or_value": "Minimum gap: 6 hours between strength and endurance sessions; 8 hours preferred for high-intensity sessions",
      "priority": "high",
      "confidence": "strong",
      "source": "Coffey & Hawley 2017; Baar 2014 molecular interference review",
      "applies_to": ["lifting", "running", "cycling"]
    },
    {
      "rule_name": "Interference classification by endurance modality",
      "category": "Concurrent Training",
      "condition": "When selecting the endurance modality for a concurrent training day",
      "action": "Prefer cycling over running for same-day combination with heavy lifting; running causes greater leg-muscle interference than cycling",
      "formula_or_value": "Interference severity (on hypertrophy/strength): running > cycling > swimming; cycling preferred when combining with lower-body lifting",
      "priority": "medium",
      "confidence": "moderate",
      "source": "Wilson et al. 2012 meta-analysis on concurrent training interference; modality-specific interference research",
      "applies_to": ["lifting", "running", "cycling"]
    },
    {
      "rule_name": "Endurance-first ordering when gap is <6 hours",
      "category": "Session Scheduling",
      "condition": "If strength and endurance sessions must be separated by less than 6 hours AND the priority goal is hypertrophy",
      "action": "When gap is unavoidably <6h and hypertrophy is priority, consider endurance first to have fresher muscles for the strength session",
      "formula_or_value": "Gap <6h + hypertrophy priority: Endurance → Strength preferred; otherwise default to Strength → Endurance",
      "priority": "medium",
      "confidence": "weak",
      "source": "Baar 2014 molecular signaling review; emerging concurrent training literature",
      "applies_to": ["lifting", "running", "cycling"]
    },
    {
      "rule_name": "Concurrent training frequency — resistance sessions",
      "category": "Session Scheduling",
      "condition": "If designing a concurrent training program for an endurance athlete",
      "action": "Prescribe 2-3 resistance training sessions per week; more than 3 increases interference risk without additional adaptation benefit",
      "formula_or_value": "Resistance sessions: 2-3/week; endurance sessions: 3-6/week depending on sport; total sessions: ≤9-10/week to manage fatigue",
      "priority": "high",
      "confidence": "strong",
      "source": "Systematic review: concurrent HIIT and resistance for musculoskeletal function (original source articles)",
      "applies_to": ["lifting", "running", "cycling"]
    },
    {
      "rule_name": "AMPK/mTOR molecular interference window",
      "category": "Physiology",
      "condition": "If explaining why same-day session ordering and gaps matter",
      "action": "Note that endurance exercise activates AMPK (catabolic signaling) which suppresses mTOR (anabolic signaling) for 3-6 hours; this is the molecular basis for the 6h gap rule",
      "formula_or_value": "AMPK activation post-endurance: peak 0-2h, resolves 3-6h; mTOR suppression window: 0-6h post-endurance; strength first avoids this suppression during the critical 2-3h post-strength window",
      "priority": "medium",
      "confidence": "strong",
      "source": "Baar 2014 molecular review; Hawley et al. 2016 concurrent training signaling",
      "applies_to": ["lifting", "running", "cycling"]
    }
  ]
}
```

- [ ] **Step 3: Run tests for this file**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_knowledge_jsons.py -k "interference" -v
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add docs/knowledge/head_coach_interference_rules.json
git commit -m "fix(knowledge): rebuild head_coach_interference_rules — fix invalid JSON, translate to English, enrich to 10 rules"
```

---

## Task 7: Enrich swimming_coach_biomechanics_rules.json (Priority 4)

**Files:**
- Modify: `docs/knowledge/swimming_coach_biomechanics_rules.json`

- [ ] **Step 1: Backup**

```bash
cp docs/knowledge/swimming_coach_biomechanics_rules.json docs/knowledge/swimming_coach_biomechanics_rules.json.backup
```

- [ ] **Step 2: Write enriched file**

Write `docs/knowledge/swimming_coach_biomechanics_rules.json`:

```json
{
  "schema_version": "1.0",
  "target_agent": "Swimming Coach",
  "language": "en",
  "last_updated": "2026-04-13",
  "source_books": [],
  "extracted_rules": [
    {
      "rule_name": "CSS derivation — 400m and 200m time trial",
      "category": "Pace Prescription",
      "condition": "When establishing swim training zones for any athlete without prior CSS data",
      "action": "Derive CSS from 400m and 200m all-out time trials on the same day; this pace is the aerobic threshold for swimming",
      "formula_or_value": "CSS (m/s) = (D400 - D200) / (T400 - T200) where D=distance in meters, T=time in seconds; CSS pace = 100m split at that speed",
      "priority": "high",
      "confidence": "strong",
      "source": "Wakayoshi et al. 1992 (original CSS derivation); swimming physiology consensus",
      "applies_to": ["swimming"]
    },
    {
      "rule_name": "CSS Zone 1 — Recovery",
      "category": "Training Zones",
      "condition": "If scheduling a recovery or warm-up swim",
      "action": "Swim at below 80% of CSS pace; fully aerobic, minimal lactate accumulation",
      "formula_or_value": "<80% CSS pace; RPE ≤ 3; conversational breathing pattern; used for warm-up, cool-down, and active recovery",
      "priority": "high",
      "confidence": "strong",
      "source": "CSS zone framework derived from Wakayoshi 1992 + swimming physiology standards",
      "applies_to": ["swimming"]
    },
    {
      "rule_name": "CSS Zone 2 — Aerobic Development",
      "category": "Training Zones",
      "condition": "If scheduling an aerobic base or endurance swim",
      "action": "Swim at 80-94% of CSS pace; primary zone for aerobic base building; forms 70-80% of total swim volume",
      "formula_or_value": "80-94% CSS pace; RPE 4-6; sustainable for long sets; main aerobic development zone",
      "priority": "high",
      "confidence": "strong",
      "source": "CSS zone framework derived from Wakayoshi 1992 + swimming physiology standards",
      "applies_to": ["swimming"]
    },
    {
      "rule_name": "CSS Zone 3 — Threshold (at CSS)",
      "category": "Training Zones",
      "condition": "If scheduling threshold or CSS-pace sets",
      "action": "Swim at 95-100% of CSS pace; this is the maximal lactate steady-state; limit to ≤15% of weekly swim volume",
      "formula_or_value": "95-100% CSS pace; RPE 7-8; maximal lactate steady state; volume cap ≤15% of weekly swim time",
      "priority": "high",
      "confidence": "strong",
      "source": "CSS zone framework; analogous to Daniels T-pace principle applied to swimming",
      "applies_to": ["swimming"]
    },
    {
      "rule_name": "CSS Zone 4 — Speed/VO2swim",
      "category": "Training Zones",
      "condition": "If scheduling high-intensity interval swim sets targeting VO2max",
      "action": "Swim at >100% CSS pace (race pace or faster); use short intervals with adequate rest; limit to ≤10% of weekly swim volume",
      "formula_or_value": ">100% CSS pace (105-115% for VO2 sets); work:rest ratio 1:3 to 1:4; volume ≤10% weekly swim time",
      "priority": "medium",
      "confidence": "strong",
      "source": "CSS zone framework; VO2swim interval research",
      "applies_to": ["swimming"]
    },
    {
      "rule_name": "SWOLF — efficiency metric",
      "category": "Technique Monitoring",
      "condition": "When monitoring swimming technique efficiency",
      "action": "Calculate SWOLF for each set; lower SWOLF indicates better efficiency; track trends over weeks",
      "formula_or_value": "SWOLF = stroke_count_per_length + split_seconds_per_length; lower = more efficient; elite freestyle 25m: SWOLF ~30-35; recreational: 40-50",
      "priority": "medium",
      "confidence": "strong",
      "source": "Swimming efficiency research; SWOLF standardized metric",
      "applies_to": ["swimming"]
    },
    {
      "rule_name": "Freestyle stroke rate by distance",
      "category": "Technique Prescription",
      "condition": "When prescribing stroke rate targets for freestyle training",
      "action": "Set stroke rate targets based on distance; lower stroke rate with longer stroke for distance events, higher rate for sprint",
      "formula_or_value": "Distance freestyle (1500m+): 50-60 strokes/min; middle distance (200-400m): 65-75 strokes/min; sprint (50-100m): 80-100 strokes/min",
      "priority": "medium",
      "confidence": "moderate",
      "source": "Toussaint & Hollander 1994; competitive swimming stroke rate research",
      "applies_to": ["swimming"]
    },
    {
      "rule_name": "Open-water drafting — position and energy savings",
      "category": "Race Tactics",
      "condition": "If athlete races in open-water or triathlon swim",
      "action": "Position 0-50cm directly behind the lead swimmer's feet; hip-draft position (beside lead swimmer's hips) offers partial benefit",
      "formula_or_value": "Feet-draft (0-50cm behind): energy cost reduction ~11-38%; hip-draft (beside hips): ~5-15% reduction; position must be maintained actively",
      "priority": "high",
      "confidence": "strong",
      "source": "Systematic review: aerodynamic drafting in mass-start non-motorized sports (original swimming_coach_biomechanics source)",
      "applies_to": ["swimming"]
    },
    {
      "rule_name": "Triathlon swim exit — reduce intensity pre-T1",
      "category": "Race Tactics",
      "condition": "If athlete is approaching the swim exit in a triathlon",
      "action": "Reduce swim intensity in the final 150-200m to allow HR and breathing to stabilize before T1; prioritize a strong exit kick and breathing control",
      "formula_or_value": "Final 150-200m: reduce effort to CSS Zone 2 (~85% CSS); allows HR to drop 5-10 bpm before transition; improves early bike output",
      "priority": "medium",
      "confidence": "moderate",
      "source": "Triathlon physiology research; transition optimization consensus",
      "applies_to": ["swimming"]
    },
    {
      "rule_name": "Breaststroke energy cost — use for recovery only",
      "category": "Technique Economics",
      "condition": "If scheduling a breaststroke set for a swimmer who primarily uses freestyle",
      "action": "Treat breaststroke as a recovery stroke only; its energy cost is 40% higher than freestyle at the same speed",
      "formula_or_value": "Breaststroke energy cost: ~40% higher than freestyle at matched speed; active frontal drag: highest of all 4 strokes; prescribe at Zone 1 effort only",
      "priority": "medium",
      "confidence": "strong",
      "source": "Systematic review: variability of energy cost in breaststroke (original swimming_coach_biomechanics source)",
      "applies_to": ["swimming"]
    }
  ]
}
```

- [ ] **Step 3: Run tests**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_knowledge_jsons.py -k "swimming" -v
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add docs/knowledge/swimming_coach_biomechanics_rules.json
git commit -m "feat(knowledge): enrich swimming_coach_biomechanics — 2 to 10 rules, CSS zones, SWOLF, drafting"
```

---

## Task 8: Enrich recovery_coach_sleep_cns_rules.json (Priority 5)

**Files:**
- Modify: `docs/knowledge/recovery_coach_sleep_cns_rules.json`

- [ ] **Step 1: Backup**

```bash
cp docs/knowledge/recovery_coach_sleep_cns_rules.json docs/knowledge/recovery_coach_sleep_cns_rules.json.backup
```

- [ ] **Step 2: Write enriched file**

Write `docs/knowledge/recovery_coach_sleep_cns_rules.json`:

```json
{
  "schema_version": "1.0",
  "target_agent": "Recovery Coach",
  "language": "en",
  "last_updated": "2026-04-13",
  "source_books": [],
  "extracted_rules": [
    {
      "rule_name": "Sleep duration target for athletes",
      "category": "Sleep",
      "condition": "When prescribing sleep for any athlete in active training",
      "action": "Target 8-9 hours of sleep per night; minimum 7 hours; below 6 hours triggers mandatory training modification",
      "formula_or_value": "Target: 8-9h/night; minimum: 7h; <6h: flag as critical — reduce session intensity by 20%, no high-intensity sessions",
      "priority": "high",
      "confidence": "strong",
      "source": "Sleep review: circadian rhythm and sleep in young adult athletes (original source)",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "Sleep debt accumulation protocol",
      "category": "Sleep",
      "condition": "If athlete has accumulated sleep debt during a training week",
      "action": "Prescribe 1 hour of additional sleep for each 2 hours of weekly sleep deficit; do not attempt to recover >3h of sleep debt in a single night",
      "formula_or_value": "Compensation rate: 1h extra sleep per 2h deficit; weekly deficit cap for single-night recovery: ≤3h; multi-night recovery preferred",
      "priority": "medium",
      "confidence": "moderate",
      "source": "Sleep debt research consensus; circadian rhythm and performance literature",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "Pre-competition sleep extension",
      "category": "Sleep",
      "condition": "If athlete has a major race or competition within 3-5 days",
      "action": "Extend sleep by 1-2 hours per night for 3-5 nights before the event; bank sleep in advance of potential pre-race night disruption",
      "formula_or_value": "Pre-competition: +1 to +2h sleep/night for 3-5 nights before event; race-night sleep quality matters less than pre-race banking",
      "priority": "high",
      "confidence": "strong",
      "source": "Systematic review: sleep and ultra-endurance performance (original source); pre-competition sleep banking research",
      "applies_to": ["running", "cycling", "swimming"]
    },
    {
      "rule_name": "Intra-competition napping for cognitive performance",
      "category": "Sleep",
      "condition": "If athlete experiences cognitive fatigue during ultra-endurance competition (>6h event)",
      "action": "Permit and schedule mid-race naps of 20-30 minutes at planned aid stations; napping improves subsequent decision-making and reduces error rate",
      "formula_or_value": "Nap duration: 20-30 min (avoid >30 min to prevent sleep inertia); improvement in cognitive performance: significant vs. no nap",
      "priority": "medium",
      "confidence": "moderate",
      "source": "Systematic review: sleep role in ultra-endurance performance (original source)",
      "applies_to": ["running", "cycling"]
    },
    {
      "rule_name": "Early morning practice — sleep mitigation",
      "category": "Sleep",
      "condition": "If athlete's schedule includes early morning practice sessions (before 6am)",
      "action": "Flag as a risk factor for sleep disturbance; recommend earlier bedtime, not reduced wake time; monitor weekly sleep totals",
      "formula_or_value": "Early practice (pre-6am): flag circadian risk; bedtime advance: shift bedtime by 30-60 min to compensate; monitor total weekly sleep hours",
      "priority": "high",
      "confidence": "strong",
      "source": "Review: circadian rhythm and sleep disturbances in young adult athletes (original source)",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "Sleep quality consequences — performance and mental health",
      "category": "Sleep",
      "condition": "If athlete reports or shows signs of inadequate sleep",
      "action": "Assess for reduced reaction times and mental health indicators (depressive symptoms, anxiety); modify training load and escalate if mental health signs present",
      "formula_or_value": "Inadequate sleep → reduced reaction time, anxiety, depressive symptoms; training load reduction: 15-20% until sleep normalizes",
      "priority": "high",
      "confidence": "strong",
      "source": "Review: circadian rhythm and sleep disturbances in young adult athletes (original source)",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "Yoga and meditation for melatonin and sleep quality",
      "category": "Sleep",
      "condition": "If athlete seeks a non-pharmacological approach to improve sleep onset and quality",
      "action": "Prescribe 20-30 min of yoga or meditation in the evening; proven to elevate melatonin and improve sleep quality",
      "formula_or_value": "Yogic techniques (meditation + mantra): pooled SMD = 0.37 (95% CI: 0.09-0.66) on melatonin levels; practice ≥3×/week",
      "priority": "low",
      "confidence": "moderate",
      "source": "Meta-analysis: yogic techniques and melatonin levels (original source)",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "Aerobic exercise improves sleep quality",
      "category": "Sleep",
      "condition": "If athlete or individual experiences general sleep disturbances (not from overtraining)",
      "action": "Regular moderate aerobic exercise improves sleep quality; schedule exercise ≥4 hours before bedtime to avoid sleep disruption",
      "formula_or_value": "Aerobic exercise: widely supported for sleep quality improvement; timing: ≥4h before bedtime; morning or afternoon preferred",
      "priority": "medium",
      "confidence": "strong",
      "source": "Systematic review: aerobic exercise and sleep quality (original source)",
      "applies_to": ["running", "cycling", "swimming"]
    },
    {
      "rule_name": "CNS fatigue indicators",
      "category": "CNS Recovery",
      "condition": "If athlete shows any of the following signs after a heavy training block: RPE inflation, mood disturbance, or reduced motivation",
      "action": "Assess for CNS fatigue; reduce CNS-demanding sessions; increase recovery days until indicators resolve",
      "formula_or_value": "CNS fatigue signs: RPE +2 or more vs. expected at given pace/load; reaction time increase >10%; mood disturbance; motivation loss; if ≥2 signs: mandatory 48-72h CNS recovery",
      "priority": "high",
      "confidence": "moderate",
      "source": "Overreaching and CNS fatigue research; Meeusen et al. 2013 overtraining consensus statement",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "CNS recovery window post-heavy strength",
      "category": "CNS Recovery",
      "condition": "After a heavy maximal strength session (≥85% 1RM, compound lifts, CNS-intensive)",
      "action": "Do not schedule another CNS-demanding session within 48-72 hours; this includes maximal sprint efforts, heavy Olympic lifts, and high-intensity intervals",
      "formula_or_value": "Post-maximal strength CNS recovery: 48-72h before next CNS-demanding session; aerobic Z1-Z2 work permitted within 24h",
      "priority": "high",
      "confidence": "strong",
      "source": "Neuromuscular fatigue research; Aagaard 2003; Häkkinen et al. CNS recovery studies",
      "applies_to": ["lifting", "running", "cycling"]
    },
    {
      "rule_name": "Caffeine timing — avoid CNS disruption to sleep",
      "category": "CNS Recovery",
      "condition": "If athlete uses caffeine for performance enhancement",
      "action": "Schedule last caffeine dose ≥6 hours before planned bedtime; athletes sensitive to caffeine should avoid post-2pm consumption",
      "formula_or_value": "Caffeine half-life: ~5-6h; last dose: ≥6h pre-sleep; for sensitive athletes: cut-off at 2pm; avoid late training sessions with pre-workout caffeine",
      "priority": "medium",
      "confidence": "strong",
      "source": "Caffeine pharmacokinetics research; sleep-caffeine interaction consensus",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    }
  ]
}
```

- [ ] **Step 3: Run tests**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_knowledge_jsons.py -k "sleep" -v
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add docs/knowledge/recovery_coach_sleep_cns_rules.json
git commit -m "feat(knowledge): enrich recovery_coach_sleep_cns — add CNS rules, sleep targets, pre-race banking"
```

---

## Task 9: Enrich biking_coach_power_rules.json (Priority 6)

**Files:**
- Modify: `docs/knowledge/biking_coach_power_rules.json`

- [ ] **Step 1: Backup**

```bash
cp docs/knowledge/biking_coach_power_rules.json docs/knowledge/biking_coach_power_rules.json.backup
```

- [ ] **Step 2: Write enriched file**

Write `docs/knowledge/biking_coach_power_rules.json`:

```json
{
  "schema_version": "1.0",
  "target_agent": "Biking Coach",
  "language": "en",
  "last_updated": "2026-04-13",
  "source_books": [],
  "extracted_rules": [
    {
      "rule_name": "FTP test protocol — 20-minute field test",
      "category": "Fitness Assessment",
      "condition": "When establishing FTP for a new athlete or after a training block of 6+ weeks",
      "action": "Perform a 20-minute all-out time trial; multiply average power by 0.95 to estimate FTP",
      "formula_or_value": "FTP = 20min_avg_power × 0.95; alternatively ramp test: last completed 1-min stage × 0.75; retest every 6-8 weeks",
      "priority": "high",
      "confidence": "strong",
      "source": "Coggan & Allen, Training and Racing with a Power Meter; ramp test Borszcz et al. 2020",
      "applies_to": ["cycling"]
    },
    {
      "rule_name": "Coggan Zone 1 — Active Recovery",
      "category": "Training Zones",
      "condition": "If scheduling an active recovery ride",
      "action": "Ride at <55% FTP; minimal physiological stress; used for recovery between hard sessions",
      "formula_or_value": "<55% FTP; HR typically <68% HRmax; RPE 1-2; no training adaptation targeted",
      "priority": "high",
      "confidence": "strong",
      "source": "Coggan & Allen, Training and Racing with a Power Meter (Coggan power zones)",
      "applies_to": ["cycling"]
    },
    {
      "rule_name": "Coggan Zone 2 — Endurance",
      "category": "Training Zones",
      "condition": "If scheduling an aerobic endurance ride",
      "action": "Ride at 55-74% FTP; primary zone for aerobic base building; forms 60-70% of total cycling volume in base phase",
      "formula_or_value": "55-74% FTP; HR ~69-83% HRmax; RPE 2-3; lactate <2 mmol/L",
      "priority": "high",
      "confidence": "strong",
      "source": "Coggan & Allen, Training and Racing with a Power Meter",
      "applies_to": ["cycling"]
    },
    {
      "rule_name": "Coggan Zone 3 — Tempo",
      "category": "Training Zones",
      "condition": "If scheduling a tempo ride for aerobic threshold development",
      "action": "Ride at 75-89% FTP; sustainable for 60-120 minutes in trained cyclists; limit to ≤20% of weekly volume",
      "formula_or_value": "75-89% FTP; HR ~84-94% HRmax; RPE 4-5; lactate 2-4 mmol/L; volume cap ≤20% weekly",
      "priority": "high",
      "confidence": "strong",
      "source": "Coggan & Allen, Training and Racing with a Power Meter",
      "applies_to": ["cycling"]
    },
    {
      "rule_name": "Coggan Zone 4 — Lactate Threshold",
      "category": "Training Zones",
      "condition": "If scheduling FTP/threshold intervals",
      "action": "Ride at 90-104% FTP; typical interval duration 8-20 minutes; total Z4 volume ≤10% of weekly volume",
      "formula_or_value": "90-104% FTP; HR ~94-100% LTHR; RPE 6-7; sustainable for 60 min at FTP; interval duration 8-20 min",
      "priority": "high",
      "confidence": "strong",
      "source": "Coggan & Allen, Training and Racing with a Power Meter",
      "applies_to": ["cycling"]
    },
    {
      "rule_name": "Coggan Zone 5 — VO2max",
      "category": "Training Zones",
      "condition": "If scheduling VO2max intervals on the bike",
      "action": "Ride at 105-120% FTP; intervals of 3-8 minutes; rest:work ratio 1:1; limit to ≤8% of weekly volume",
      "formula_or_value": "105-120% FTP; HR >100% LTHR; RPE 8; interval duration 3-8 min; rest = work duration; volume ≤8% weekly",
      "priority": "medium",
      "confidence": "strong",
      "source": "Coggan & Allen, Training and Racing with a Power Meter",
      "applies_to": ["cycling"]
    },
    {
      "rule_name": "Coggan Zone 6 — Anaerobic Capacity",
      "category": "Training Zones",
      "condition": "If scheduling anaerobic capacity or sprint preparation intervals",
      "action": "Ride at 121-150% FTP; very short intervals (30 sec to 2 min); long recovery (1:4 to 1:6 work:rest); limit to ≤5% of weekly volume",
      "formula_or_value": "121-150% FTP; RPE 9-10; interval duration 30s-2min; work:rest 1:4 to 1:6; volume ≤5% weekly",
      "priority": "medium",
      "confidence": "strong",
      "source": "Coggan & Allen, Training and Racing with a Power Meter",
      "applies_to": ["cycling"]
    },
    {
      "rule_name": "CTL — Chronic Training Load formula",
      "category": "Load Monitoring",
      "condition": "When tracking long-term aerobic fitness and training load for a cyclist",
      "action": "Calculate CTL as 42-day EWMA of daily TSS; this represents aerobic fitness baseline",
      "formula_or_value": "CTL = 42-day EWMA of daily TSS; λ = 2/(42+1) ≈ 0.046; typical competitive cyclist CTL: 60-100 TSS/day",
      "priority": "high",
      "confidence": "strong",
      "source": "Coggan & Allen, Training and Racing with a Power Meter; Banister 1991 impulse-response model",
      "applies_to": ["cycling"]
    },
    {
      "rule_name": "ATL — Acute Training Load formula",
      "category": "Load Monitoring",
      "condition": "When tracking short-term fatigue accumulation for a cyclist",
      "action": "Calculate ATL as 7-day EWMA of daily TSS; represents current fatigue state",
      "formula_or_value": "ATL = 7-day EWMA of daily TSS; λ = 2/(7+1) = 0.25; ATL > CTL indicates accumulated fatigue",
      "priority": "high",
      "confidence": "strong",
      "source": "Coggan & Allen, Training and Racing with a Power Meter; Banister 1991",
      "applies_to": ["cycling"]
    },
    {
      "rule_name": "TSB — Training Stress Balance (Form)",
      "category": "Load Monitoring",
      "condition": "When assessing athlete readiness for racing or peak performance",
      "action": "Compute TSB = CTL − ATL; positive TSB indicates freshness; target +5 to +25 for A-race day",
      "formula_or_value": "TSB = CTL − ATL; target for A-race: +5 to +25; <−20: significant fatigue; >+25: risk of detraining",
      "priority": "high",
      "confidence": "strong",
      "source": "Coggan & Allen, Training and Racing with a Power Meter",
      "applies_to": ["cycling"]
    },
    {
      "rule_name": "HIIT superiority for VO2max in cycling",
      "category": "Training",
      "condition": "If the goal is to improve VO2max or maximal aerobic power in cyclists",
      "action": "Prioritize HIIT over moderate-to-vigorous continuous training (MVICT); HIIT produces larger gains in relative VO2max and maximal aerobic power",
      "formula_or_value": "HIIT vs MVICT: VO2max relative g=0.39; VO2max absolute g=0.29; maximal aerobic power g=0.31; anaerobic power g=0.47",
      "priority": "high",
      "confidence": "strong",
      "source": "Meta-analysis: HIIT vs MVICT across 115 trials (original biking_coach_power_rules source)",
      "applies_to": ["cycling"]
    },
    {
      "rule_name": "Caffeine dose for general cycling performance",
      "category": "Ergogenic Aids",
      "condition": "If a cyclist uses caffeine to improve general cycling performance (time-to-completion reduction)",
      "action": "Use a low dose of caffeine (~1h before effort); low dose more effective than high dose for completion-time performance",
      "formula_or_value": "Dose: ≤3 mg/kg body weight; timing: ~60 min pre-exercise; effect: SMD=-0.36 on time-to-completion, SMD=+0.29 on mean power",
      "priority": "medium",
      "confidence": "strong",
      "source": "Meta-analysis: caffeine and cycling performance (original biking_coach_power_rules source)",
      "applies_to": ["cycling"]
    },
    {
      "rule_name": "Caffeine dose for sprint repeat performance (RSA)",
      "category": "Ergogenic Aids",
      "condition": "If a cyclist targets repeated sprint ability (RSA) improvement with caffeine",
      "action": "Use a higher caffeine dose for RSA; effect is larger in cycling than running RSA protocols",
      "formula_or_value": "Dose: ≥6 mg/kg body weight; RSA peak power improvement: WMD +6.67 (cycling) vs +4.56 (running); timing: 60 min pre-effort",
      "priority": "medium",
      "confidence": "strong",
      "source": "Meta-analysis: caffeine and repeated sprint ability (original biking_coach_power_rules source)",
      "applies_to": ["cycling"]
    },
    {
      "rule_name": "Optimal cadence by session type",
      "category": "Technique",
      "condition": "When prescribing cadence targets for cycling sessions",
      "action": "Vary target cadence by session type; higher cadence for endurance, lower for strength intervals",
      "formula_or_value": "Endurance/Z2-Z3: 85-100 rpm; threshold/Z4: 85-95 rpm; strength intervals/Z6: 60-80 rpm; sprint: 100-120 rpm",
      "priority": "medium",
      "confidence": "moderate",
      "source": "Cycling biomechanics research; Abbiss et al. 2009 cadence optimization",
      "applies_to": ["cycling"]
    },
    {
      "rule_name": "Bike fit — lower back pain prevention",
      "category": "Injury Prevention",
      "condition": "If a cyclist reports lower back pain or discomfort",
      "action": "Perform a personalized dynamic bike fit adjusted to workload demands; static fits are insufficient for preventing LBP under varied training loads",
      "formula_or_value": "Dynamic bike fit (workload-adapted): significant LBP reduction vs. no fit; saddle height, fore-aft position, and handlebar drop are primary adjustment vectors",
      "priority": "medium",
      "confidence": "moderate",
      "source": "Systematic review: bike fitting and lower back pain in cyclists (original biking_coach_power_rules source)",
      "applies_to": ["cycling"]
    }
  ]
}
```

- [ ] **Step 3: Run tests**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_knowledge_jsons.py -k "biking" -v
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add docs/knowledge/biking_coach_power_rules.json
git commit -m "feat(knowledge): enrich biking_coach_power — add Coggan zones Z1-Z7, FTP, CTL/ATL/TSB, cadence"
```

---

## Task 10: Enrich lifting_coach_volume_rules.json (Priority 7)

**Files:**
- Modify: `docs/knowledge/lifting_coach_volume_rules.json`

- [ ] **Step 1: Backup**

```bash
cp docs/knowledge/lifting_coach_volume_rules.json docs/knowledge/lifting_coach_volume_rules.json.backup
```

- [ ] **Step 2: Write enriched file**

Write `docs/knowledge/lifting_coach_volume_rules.json`:

```json
{
  "schema_version": "1.0",
  "target_agent": "Lifting Coach",
  "language": "en",
  "last_updated": "2026-04-13",
  "source_books": [],
  "extracted_rules": [
    {
      "rule_name": "MEV — Minimum Effective Volume per muscle group",
      "category": "Volume Landmarks",
      "condition": "If the goal is to maintain muscle mass and strength during a period of reduced training",
      "action": "Prescribe at least MEV sets per muscle group per week; below MEV, detraining occurs",
      "formula_or_value": "MEV: ~8-10 sets/week per muscle group (maintenance threshold); individual range: 6-12 sets depending on training history",
      "priority": "high",
      "confidence": "strong",
      "source": "Israetel et al., Scientific Principles of Hypertrophy Training; meta-regression: weekly volume and hypertrophy",
      "applies_to": ["lifting"]
    },
    {
      "rule_name": "MAV — Maximum Adaptive Volume per muscle group",
      "category": "Volume Landmarks",
      "condition": "If the goal is hypertrophy and athlete is in an accumulation block",
      "action": "Target MAV range for primary muscle groups; volume within MAV produces the best hypertrophy return-on-investment",
      "formula_or_value": "MAV: ~15-20 sets/week per muscle group; individual range: 12-22 sets; peak hypertrophy response in this window",
      "priority": "high",
      "confidence": "strong",
      "source": "Israetel et al., Scientific Principles of Hypertrophy Training; Schoenfeld et al. 2017 dose-response",
      "applies_to": ["lifting"]
    },
    {
      "rule_name": "MRV — Maximum Recoverable Volume per muscle group",
      "category": "Volume Landmarks",
      "condition": "When an athlete approaches or exceeds MRV for any muscle group",
      "action": "Reduce volume back to MAV or MEV; above MRV, fatigue exceeds adaptation and injury risk rises significantly",
      "formula_or_value": "MRV: ~25+ sets/week per muscle group (highly individual); at MRV: diminishing returns; above MRV: detraining + injury risk",
      "priority": "high",
      "confidence": "strong",
      "source": "Israetel et al., Scientific Principles of Hypertrophy Training",
      "applies_to": ["lifting"]
    },
    {
      "rule_name": "DUP — Daily Undulating Periodization weekly structure",
      "category": "Periodization",
      "condition": "If athlete trains the same muscle group ≥3 times per week",
      "action": "Vary rep ranges across sessions (DUP); do not repeat same rep range within the same muscle group on consecutive sessions",
      "formula_or_value": "DUP weekly template: Session 1 = 3-5 reps (strength); Session 2 = 8-12 reps (hypertrophy); Session 3 = 15-20 reps (endurance/metabolic); rotate weekly",
      "priority": "high",
      "confidence": "strong",
      "source": "DUP research: Zourdos et al. 2016; Colquhoun et al. 2017",
      "applies_to": ["lifting"]
    },
    {
      "rule_name": "RPE scale — Reps In Reserve (RIR) method",
      "category": "Intensity Prescription",
      "condition": "When prescribing training intensity using RPE",
      "action": "Use RIR-based RPE scale; prescribe sets at RPE 7-9 for hypertrophy work; RPE 9-10 reserved for strength testing or AMRAP sets",
      "formula_or_value": "RPE 6 = 4 RIR; RPE 7 = 3 RIR; RPE 8 = 2 RIR; RPE 9 = 1 RIR; RPE 10 = maximal (0 RIR); hypertrophy target: RPE 7-9",
      "priority": "high",
      "confidence": "strong",
      "source": "Zourdos et al. 2016 RIR-based RPE validation; Helms et al. 2016",
      "applies_to": ["lifting"]
    },
    {
      "rule_name": "Progressive overload — when to add load",
      "category": "Progression",
      "condition": "When deciding whether to increase load on a given exercise",
      "action": "Add load only when the top working set is completed at RPE ≤7 for 2 consecutive sessions; do not increase load if RPE is ≥8",
      "formula_or_value": "Load increase trigger: top set RPE ≤7 for 2 consecutive sessions; load increment: 2.5-5 kg for upper body, 5-10 kg for lower body",
      "priority": "high",
      "confidence": "strong",
      "source": "Progressive overload consensus; RIR-based progression (Helms et al. 2016)",
      "applies_to": ["lifting"]
    },
    {
      "rule_name": "Drop-set training for hypertrophy and time efficiency",
      "category": "Advanced Techniques",
      "condition": "If hypertrophy is the goal and training time is limited",
      "action": "Use drop-sets to achieve equivalent hypertrophic stimulus in less time than traditional sets",
      "formula_or_value": "Drop-sets: 2-3 drops of 20-25% load per set; equivalent or superior hypertrophy vs. traditional sets at matched volume; time reduction: ~40%",
      "priority": "medium",
      "confidence": "strong",
      "source": "Meta-analysis: acute and chronic effects of drop-set training (original lifting_coach_volume_rules source)",
      "applies_to": ["lifting"]
    },
    {
      "rule_name": "Blood Flow Restriction (BFR) — low-load hypertrophy",
      "category": "Advanced Techniques",
      "condition": "If heavy loading is contraindicated (injury, post-surgery) and hypertrophy or strength maintenance is needed",
      "action": "Apply BFR with 20-30% 1RM; produces hypertrophy and strength gains comparable to high-intensity training",
      "formula_or_value": "BFR load: 20-30% 1RM; cuff pressure: 50-80% arterial occlusion pressure; sets: 4-5 per exercise; reps: 15-30; rest: 30-60s",
      "priority": "medium",
      "confidence": "strong",
      "source": "Meta-analysis: BFR interval training on hypertrophy and strength (original lifting_coach_volume_rules source)",
      "applies_to": ["lifting"]
    },
    {
      "rule_name": "Weekly volume dose-response for hypertrophy",
      "category": "Volume Programming",
      "condition": "When designing weekly volume for a hypertrophy block",
      "action": "Higher weekly set volume produces greater hypertrophy up to MRV; increase sets gradually across a mesocycle",
      "formula_or_value": "Dose-response: each additional set/week up to MRV adds measurable hypertrophy; recommended progression: +2 sets/week per muscle group across 4-week mesocycle",
      "priority": "high",
      "confidence": "strong",
      "source": "Meta-regression: weekly volume and muscle hypertrophy/strength (original lifting_coach_volume_rules source)",
      "applies_to": ["lifting"]
    },
    {
      "rule_name": "Creatine supplementation for hypertrophy",
      "category": "Supplementation",
      "condition": "If athlete is performing resistance training and targeting lean mass gain",
      "action": "Recommend creatine monohydrate supplementation; well-established for lean mass improvement; benefits are greater in novice to intermediate lifters",
      "formula_or_value": "Dose: 3-5g/day creatine monohydrate; loading phase optional (20g/day × 5 days); no significant difference between novice and experienced for lean mass; timing flexible",
      "priority": "medium",
      "confidence": "strong",
      "source": "Dose-response meta-analysis: creatine and resistance training in novice vs experienced lifters (original source)",
      "applies_to": ["lifting"]
    },
    {
      "rule_name": "Velocity-based training and eccentric overload for maximal strength",
      "category": "Strength Development",
      "condition": "If the primary goal is maximal strength (1RM) improvement",
      "action": "Include velocity-based training (VBT) or eccentric overload methods; these provide greater strength gains than traditional loading alone",
      "formula_or_value": "VBT: target bar velocity 0.5-0.8 m/s for strength; eccentric overload: 120-130% concentric 1RM; g=0.351 strength benefit vs traditional",
      "priority": "medium",
      "confidence": "moderate",
      "source": "Meta-analysis: advanced resistance training systems for strength (original lifting_coach_volume_rules source)",
      "applies_to": ["lifting"]
    },
    {
      "rule_name": "Rest-pause for hypertrophy",
      "category": "Advanced Techniques",
      "condition": "If athlete wants an alternative to drop-sets for hypertrophy",
      "action": "Use rest-pause training as a time-efficient hypertrophy method; modest advantage over traditional sets",
      "formula_or_value": "Rest-pause: perform set to near-failure, rest 15-30s, extend set for additional reps; repeat 2-3 times; modest hypertrophy advantage vs. traditional sets",
      "priority": "low",
      "confidence": "moderate",
      "source": "Meta-analysis: advanced resistance training systems (original lifting_coach_volume_rules source)",
      "applies_to": ["lifting"]
    }
  ]
}
```

- [ ] **Step 3: Run tests**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_knowledge_jsons.py -k "lifting" -v
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add docs/knowledge/lifting_coach_volume_rules.json
git commit -m "feat(knowledge): enrich lifting_coach_volume — add MEV/MAV/MRV, DUP, RPE/RIR scale, progressive overload"
```

---

## Task 11: Enrich nutrition_coach_fueling_rules.json (Priority 8)

**Files:**
- Modify: `docs/knowledge/nutrition_coach_fueling_rules.json`

- [ ] **Step 1: Backup**

```bash
cp docs/knowledge/nutrition_coach_fueling_rules.json docs/knowledge/nutrition_coach_fueling_rules.json.backup
```

- [ ] **Step 2: Write enriched file**

Write `docs/knowledge/nutrition_coach_fueling_rules.json`:

```json
{
  "schema_version": "1.0",
  "target_agent": "Nutrition Coach",
  "language": "en",
  "last_updated": "2026-04-13",
  "source_books": [],
  "extracted_rules": [
    {
      "rule_name": "Carbohydrate targets by training day type",
      "category": "Macronutrient Targets",
      "condition": "When prescribing daily carbohydrate intake based on training load",
      "action": "Set carbohydrate targets in g/kg body weight based on the day's training type",
      "formula_or_value": "Rest day: 3-4 g/kg; light training day: 4-5 g/kg; moderate training day: 5-7 g/kg; hard/long training day: 7-10 g/kg; >2.5h endurance event: 10-12 g/kg",
      "priority": "high",
      "confidence": "strong",
      "source": "Jeukendrup 2011; Burke et al. 2011; IOC nutrition consensus 2011",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "Daily protein target for athletes",
      "category": "Macronutrient Targets",
      "condition": "When prescribing daily protein intake for any athlete in active training",
      "action": "Target 1.6-2.2g protein per kg body weight per day; distribute across 4 meals at ~0.4g/kg per meal",
      "formula_or_value": "Daily protein: 1.6-2.2 g/kg/day; per meal: 0.4 g/kg (optimal for MPS); minimum 4 meals/day; upper benefit ceiling: ~2.2 g/kg beyond which no additional MPS",
      "priority": "high",
      "confidence": "strong",
      "source": "Phillips & Van Loon 2011; Morton et al. 2018 meta-analysis; Stokes et al. 2018",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "Intra-workout carbohydrate — sessions 60-150 min",
      "category": "Intra-Workout Nutrition",
      "condition": "If session duration is 60-150 minutes at moderate-to-high intensity",
      "action": "Consume 30-60g of carbohydrate per hour during exercise; glucose or maltodextrin sources preferred",
      "formula_or_value": "30-60 g carbs/hour; intestinal absorption rate: ~60g glucose/hour max; sources: glucose, maltodextrin, sports drinks, gels",
      "priority": "high",
      "confidence": "strong",
      "source": "Jeukendrup 2011 carbohydrate oxidation rates; meta-analysis: carb supplementation and endurance performance (original source)",
      "applies_to": ["running", "cycling", "swimming"]
    },
    {
      "rule_name": "Intra-workout carbohydrate — sessions >150 min",
      "category": "Intra-Workout Nutrition",
      "condition": "If session duration exceeds 150 minutes (2.5 hours) at sustained intensity",
      "action": "Increase carbohydrate intake to 60-90g per hour using a glucose:fructose 2:1 ratio blend to maximize absorption via dual-transporter pathway",
      "formula_or_value": "60-90 g carbs/hour; glucose:fructose ratio 2:1; dual-transporter ceiling: 90g/h; trained gut required for >80g/h without GI distress",
      "priority": "high",
      "confidence": "strong",
      "source": "Jeukendrup 2011; Currell & Jeukendrup 2008 dual-transporter research",
      "applies_to": ["running", "cycling"]
    },
    {
      "rule_name": "Pre-workout meal timing and composition",
      "category": "Pre-Workout Nutrition",
      "condition": "Before any training session of moderate-to-high intensity",
      "action": "Consume a carbohydrate-rich meal 1-4 hours before exercise; reduce portion size as timing approaches session start",
      "formula_or_value": "3-4h before: 1-4 g/kg carbs + moderate protein; 1-2h before: 1-2 g/kg carbs, low fat, low fiber; <1h: 0.5-1 g/kg simple carbs only; avoid high-fat/fiber <2h before",
      "priority": "high",
      "confidence": "strong",
      "source": "Burke et al. 2011; pre-exercise nutrition consensus (original nutrition source)",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "Post-workout recovery nutrition window",
      "category": "Post-Workout Nutrition",
      "condition": "After any training session exceeding 60 minutes or high-intensity effort",
      "action": "Consume protein + carbohydrate within 30-45 minutes of session end to maximize glycogen resynthesis and muscle protein synthesis",
      "formula_or_value": "Within 30-45 min post-session: 0.3 g/kg protein + 1 g/kg carbohydrate; glycogen resynthesis rate: 5-10% higher with immediate vs delayed intake",
      "priority": "high",
      "confidence": "strong",
      "source": "Ivy et al. 1988; post-exercise nutrition consensus; Burke et al. 2011",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "Race-day carbohydrate loading — marathon and long events",
      "category": "Pre-Race Nutrition",
      "condition": "If athlete is preparing for a marathon or endurance event lasting >90 minutes",
      "action": "Carbohydrate load in the 24-48 hours before the event; this maximizes muscle glycogen stores",
      "formula_or_value": "Carbohydrate loading: 8-12 g/kg/day for 24-48h pre-race; reduce training volume during loading period; muscle glycogen can increase 20-40% above normal",
      "priority": "high",
      "confidence": "strong",
      "source": "Burke et al. 2011; carbohydrate loading meta-analysis (original nutrition source)",
      "applies_to": ["running", "cycling"]
    },
    {
      "rule_name": "Hydration — pre, during, and post exercise",
      "category": "Hydration",
      "condition": "During any training session or race",
      "action": "Follow evidence-based hydration protocol across all three phases of exercise",
      "formula_or_value": "Pre: 500 ml water 2h before + 250-500 ml 15-30 min before; During: 400-800 ml/h (adjust by sweat rate and heat); Post: 1.5 L fluid per 1 kg body weight lost",
      "priority": "high",
      "confidence": "strong",
      "source": "ACSM hydration guidelines; Sawka et al. 2007",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "Glycogen sparing during prolonged exercise with carb intake",
      "category": "Performance Nutrition",
      "condition": "If athlete ingests carbohydrates during a prolonged endurance effort (≥100 min)",
      "action": "Expect reduced net muscle glycogen utilization; this delays fatigue onset and extends sustainable effort duration",
      "formula_or_value": "Glycogen sparing: ~24 mmol·kg⁻¹ dry weight during ~100 min exercise with carb ingestion vs. placebo",
      "priority": "high",
      "confidence": "strong",
      "source": "Meta-analysis: carbohydrate ingestion and net glycogen utilization (original nutrition source)",
      "applies_to": ["running", "cycling"]
    },
    {
      "rule_name": "Low-carbohydrate and ketogenic diet — metabolic adaptation",
      "category": "Dietary Strategy",
      "condition": "If a trained athlete adopts a low-carbohydrate (<130 g/day) or ketogenic (<50 g/day) diet",
      "action": "Expect metabolic fat-oxidation adaptation with maintained or improved aerobic performance outcomes; warn athlete of possible acute performance reduction during 2-4 week adaptation phase",
      "formula_or_value": "Low-carb: ≤130 g/day or ≤25% total energy; keto: <50 g/day or <10% total energy; adaptation phase: 2-4 weeks; aerobic performance: maintained or improved after adaptation",
      "priority": "medium",
      "confidence": "moderate",
      "source": "Meta-analysis: low-carb and ketogenic diets and aerobic performance (original nutrition source)",
      "applies_to": ["running", "cycling"]
    },
    {
      "rule_name": "GI distress prevention — intra-exercise nutrition",
      "category": "GI Health",
      "condition": "If athlete has a history of GI distress during endurance exercise",
      "action": "Implement gut training protocol; avoid high-fiber, high-fat, and high-fructose foods within 2-3h before and during exercise; gradually increase intra-workout carb intake across training weeks",
      "formula_or_value": "Gut training: gradually increase intra-workout carb intake from 30g/h → 60g/h → 90g/h over 4-8 weeks; avoid: high-fiber/fat pre-exercise; trial race nutrition in training",
      "priority": "high",
      "confidence": "moderate",
      "source": "Systematic review: nutritional strategies for minimizing GI symptoms during endurance exercise (original source)",
      "applies_to": ["running", "cycling"]
    },
    {
      "rule_name": "Omega-3 and cardiovascular health for endurance athletes",
      "category": "Supplementation",
      "condition": "If athlete seeks to optimize cardiovascular health markers alongside endurance performance",
      "action": "Include omega-3 fatty acid supplementation; combined with carbohydrate loading, protein optimization, and hydration it produces measurable cardiovascular and performance benefits",
      "formula_or_value": "Omega-3 supplementation: reduces resting HR by ~3 bpm, lowers LDL cholesterol; dose: 1-3g EPA+DHA/day; combined nutritional strategy improves endurance by 8-12%",
      "priority": "low",
      "confidence": "moderate",
      "source": "Forensic perspective on nutrition in competitive sports (original nutrition source)",
      "applies_to": ["running", "cycling", "swimming"]
    }
  ]
}
```

- [ ] **Step 3: Run tests**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_knowledge_jsons.py -k "nutrition" -v
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add docs/knowledge/nutrition_coach_fueling_rules.json
git commit -m "feat(knowledge): enrich nutrition_coach_fueling — add g/kg targets, intra-workout protocol, race-day loading"
```

---

## Task 12: Enrich recovery_coach_hrv_rules.json (Priority 9)

**Files:**
- Modify: `docs/knowledge/recovery_coach_hrv_rules.json`

- [ ] **Step 1: Backup**

```bash
cp docs/knowledge/recovery_coach_hrv_rules.json docs/knowledge/recovery_coach_hrv_rules.json.backup
```

- [ ] **Step 2: Write enriched file**

Write `docs/knowledge/recovery_coach_hrv_rules.json`:

```json
{
  "schema_version": "1.0",
  "target_agent": "Recovery Coach",
  "language": "en",
  "last_updated": "2026-04-13",
  "source_books": [],
  "extracted_rules": [
    {
      "rule_name": "HRV morning measurement protocol",
      "category": "Measurement Protocol",
      "condition": "Always — when collecting HRV data for training readiness assessment",
      "action": "Measure RMSSD each morning: supine position, 5-minute recording, consistent timing within ±30 minutes",
      "formula_or_value": "Protocol: supine, 5-min recording, ±30 min consistent timing; use RMSSD (ln-RMSSD or raw ms); avoid measurement after alcohol, illness, or travel on the same morning",
      "priority": "high",
      "confidence": "strong",
      "source": "Plews et al. 2013 HRV4Training guidelines; HRV monitoring consensus",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "RMSSD — low concern threshold",
      "category": "Readiness Assessment",
      "condition": "If morning RMSSD is above 20ms (or within 8% of athlete's baseline)",
      "action": "Training readiness is normal; proceed with planned session; no modification required",
      "formula_or_value": "RMSSD >20ms (absolute) OR within ±8% of athlete's 7-day rolling baseline → no modification",
      "priority": "high",
      "confidence": "strong",
      "source": "Plews et al. 2013; HRV4Training longitudinal research",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "RMSSD — caution threshold (single morning)",
      "category": "Readiness Assessment",
      "condition": "If morning RMSSD is 15-20ms OR drops >8% below athlete's rolling baseline on a single morning",
      "action": "Flag reduced readiness; reduce planned session intensity by 15-20%; avoid new intensity PRs; reassess next morning",
      "formula_or_value": "RMSSD 15-20ms OR >8% below baseline (single day): reduce intensity 15-20%; no new intensity records; reassess day+1",
      "priority": "high",
      "confidence": "strong",
      "source": "Plews et al. 2013; Flatt et al. 2017 HRV-guided training",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "RMSSD — red flag threshold (consecutive mornings)",
      "category": "Readiness Assessment",
      "condition": "If morning RMSSD is <15ms OR drops >8% below baseline for 2+ consecutive mornings",
      "action": "Mandatory recovery day; replace planned session with active recovery only (Z1 effort, ≤30 min); do not prescribe intensity work until RMSSD returns to baseline",
      "formula_or_value": "RMSSD <15ms OR >8% below baseline for ≥2 consecutive days: mandatory rest/recovery day; Z1 only ≤30 min; no threshold or interval work",
      "priority": "high",
      "confidence": "strong",
      "source": "Plews et al. 2013; Flatt et al. 2017; overtraining syndrome prevention research",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "RMSSD — veto threshold (very low)",
      "category": "Readiness Assessment",
      "condition": "If morning RMSSD is <10ms",
      "action": "Apply veto: complete rest day; no training of any kind; assess for illness, overtraining, or acute stressor; escalate if pattern persists >3 days",
      "formula_or_value": "RMSSD <10ms: complete rest (no training); check for illness/OTS indicators; if <10ms for ≥3 consecutive days: refer for medical assessment",
      "priority": "high",
      "confidence": "strong",
      "source": "HRV thresholds from clinical and sports science research; overtraining syndrome criteria",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "7-day HRV trend — overreaching flag",
      "category": "Trend Monitoring",
      "condition": "If athlete's 7-day average HRV drops more than 8% from their longer-term (21-28 day) baseline",
      "action": "Flag potential overreaching; reduce total training load by 15-20% for the current week; monitor closely",
      "formula_or_value": "7-day avg HRV drop >8% vs. 21-28 day baseline → overreaching flag; reduce weekly load 15-20%; reassess after 5-7 days of reduced load",
      "priority": "high",
      "confidence": "strong",
      "source": "Plews et al. 2013; Flatt & Esco 2016 HRV trending in athletes",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "HRV + sleep interaction — compound flag",
      "category": "Readiness Assessment",
      "condition": "If RMSSD is <15ms AND sleep duration was <6h the same night",
      "action": "Apply compound recovery flag: mandatory rest or active recovery only; both signals together indicate significantly elevated injury and illness risk",
      "formula_or_value": "RMSSD <15ms + sleep <6h = compound flag: rest day mandatory; no training; prioritize sleep before reassessment",
      "priority": "high",
      "confidence": "moderate",
      "source": "Combined HRV and sleep research; Fullagar et al. 2015 sleep and athletic performance",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "HRV as parasympathetic recovery indicator",
      "category": "Physiology",
      "condition": "If explaining the physiological basis of HRV monitoring to an athlete or coach",
      "action": "Note that elevated vagally-mediated HRV (RMSSD) reflects parasympathetic dominance and indicates physiological recovery readiness",
      "formula_or_value": "High RMSSD = parasympathetic dominance = recovery; low RMSSD = sympathetic dominance = stress/fatigue; RMSSD is the most robust short-term HRV metric",
      "priority": "medium",
      "confidence": "strong",
      "source": "Systematic review: HRV monitoring, stress and recovery (original recovery_coach_hrv_rules source)",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "Cold water immersion for HRV and PNS reactivation",
      "category": "Recovery Technique",
      "condition": "After a high-intensity or high-volume training session where rapid recovery is prioritized",
      "action": "Apply cold water immersion (CWI) as the recovery technique; produces a moderate-to-large positive effect on RMSSD recovery speed",
      "formula_or_value": "CWI: 10-15°C water, 10-15 min immersion; RMSSD effect: Hedges' g = 0.75 (moderate-to-large); most effective after resistance exercise (g = 0.69)",
      "priority": "medium",
      "confidence": "strong",
      "source": "Meta-analysis: physical recovery techniques and vagally-mediated HRV (original recovery_coach_hrv_rules source)",
      "applies_to": ["running", "cycling", "lifting"]
    },
    {
      "rule_name": "Recovery techniques effectiveness after resistance exercise",
      "category": "Recovery Technique",
      "condition": "After a resistance training session",
      "action": "Apply active physical recovery techniques (CWI, massage, compression, active cool-down); these show larger HRV recovery effects after resistance than after continuous cardio",
      "formula_or_value": "Post-resistance recovery techniques: RMSSD effect g = 0.69; post-cardiovascular intermittent: g = 0.52; post-continuous cardio: no significant effect",
      "priority": "medium",
      "confidence": "strong",
      "source": "Meta-analysis: physical recovery techniques and vagally-mediated HRV (original recovery_coach_hrv_rules source)",
      "applies_to": ["lifting", "running", "cycling"]
    },
    {
      "rule_name": "HRV and overtraining symptom monitoring",
      "category": "Overtraining Detection",
      "condition": "If athlete shows chronic HRV depression (>2 weeks of below-baseline RMSSD) combined with performance decline",
      "action": "Assess for overtraining syndrome (OTS); systematic HRV alteration + performance decline + fatigue = OTS criteria; prescribe extended recovery block",
      "formula_or_value": "OTS indicators: chronic RMSSD depression >2 weeks + performance decline >5% + RPE inflation; if ≥2 criteria met: 2-4 week recovery block with ≤MEV training loads",
      "priority": "high",
      "confidence": "strong",
      "source": "Systematic review: HRV and overtraining in soccer (original recovery_coach_hrv_rules source); Meeusen et al. 2013",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    }
  ]
}
```

- [ ] **Step 3: Run tests**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_knowledge_jsons.py -k "hrv" -v
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add docs/knowledge/recovery_coach_hrv_rules.json
git commit -m "feat(knowledge): enrich recovery_coach_hrv — add RMSSD thresholds, trending rule, compound sleep+HRV flag"
```

---

## Task 13: Run full test suite

- [ ] **Step 1: Run all knowledge JSON tests**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_knowledge_jsons.py -v
```

Expected: 90 tests (10 test types × 9 files) PASS.

- [ ] **Step 2: Run full backend test suite to verify no regressions**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -x --timeout=60 -q 2>&1 | tail -20
```

Expected: all existing tests still pass (≥2021 passing per CLAUDE.md baseline).

---

## Task 14: Write KNOWLEDGE-JSONS.md

**Files:**
- Create: `docs/backend/KNOWLEDGE-JSONS.md`

- [ ] **Step 1: Write the doc**

Create `docs/backend/KNOWLEDGE-JSONS.md`:

```markdown
# Knowledge JSON Files — Reference

All files in `docs/knowledge/`. Consumed by coaching agents via prompt injection or tool retrieval.
Schema version: 1.0. Validated by `tests/backend/test_knowledge_jsons.py`.

---

## Coverage Table

| File | Agent | Rules | Last Updated | Source Books | Key Formulas |
|---|---|---|---|---|---|
| `biking_coach_power_rules.json` | Biking Coach | 15 | 2026-04-13 | Coggan & Allen | FTP×0.95; CTL=EWMA42; ATL=EWMA7; TSB=CTL-ATL; Z1-Z7 %FTP |
| `head_coach_acwr_rules.json` | Head Coach | 10 | 2026-04-13 | — | ACWR=EWMA7/EWMA28; safe 0.8-1.3; caution 1.3-1.5; danger >1.5 |
| `head_coach_interference_rules.json` | Head Coach | 10 | 2026-04-13 | — | Strength→Endurance order; 6h gap; AMPK/mTOR window 0-6h |
| `lifting_coach_volume_rules.json` | Lifting Coach | 12 | 2026-04-13 | Israetel et al. | MEV 8-10 sets/wk; MAV 15-20; MRV 25+; DUP 3/8/15 rep rotation |
| `nutrition_coach_fueling_rules.json` | Nutrition Coach | 12 | 2026-04-13 | Jeukendrup 2011 | 1.6-2.2g protein/kg; 3-12g carbs/kg by day type; 30-90g carbs/h intra |
| `recovery_coach_hrv_rules.json` | Recovery Coach | 11 | 2026-04-13 | — | RMSSD: >20ms=OK; 15-20ms=reduce 15%; <15ms×2=rest; <10ms=veto |
| `recovery_coach_sleep_cns_rules.json` | Recovery Coach | 11 | 2026-04-13 | — | 8-9h target; <6h=modify; CNS window 48-72h post-heavy lift |
| `running_coach_tid_rules.json` | Running Coach | 20 | 2026-04-13 | All 5 books | VDOT→paces; 80/20 TID; 10% volume cap; long run ≤29% or 22mi |
| `swimming_coach_biomechanics_rules.json` | Swimming Coach | 10 | 2026-04-13 | Wakayoshi 1992 | CSS=(D400-D200)/(T400-T200); SWOLF=strokes+seconds; Z1-Z4 |

---

## Schema

All files conform to `docs/knowledge/schemas/common_rule.schema.json`.

Required envelope fields: `schema_version`, `target_agent`, `language`, `last_updated`, `extracted_rules`

Required rule fields: `rule_name`, `category`, `condition`, `action`, `formula_or_value`, `priority`, `confidence`, `source`, `applies_to`

- `priority`: `high | medium | low`
- `confidence`: `strong | moderate | weak`
- `formula_or_value`: never `"N/A"` — must be specific

---

## Validation

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_knowledge_jsons.py -v
```

90 parametrized tests (10 types × 9 files). All must pass before merging any knowledge JSON change.

---

## Adding a New Rule

1. Open the target file in `docs/knowledge/`
2. Add rule with all required fields (use existing rules as template)
3. Ensure `formula_or_value` is not `"N/A"` — use a specific value, range, or formula
4. Run `pytest tests/backend/test_knowledge_jsons.py -k "<filename_fragment>" -v`
5. Commit: `feat(knowledge): add <rule_name> to <filename>`

## Adding a New Knowledge JSON File

1. Create file in `docs/knowledge/` following the common schema envelope
2. Create matching schema in `docs/knowledge/schemas/`
3. Add filename to `JSON_FILES` list in `tests/backend/test_knowledge_jsons.py`
4. Add row to coverage table above
5. Run full test suite
```

- [ ] **Step 2: Commit**

```bash
git add docs/backend/KNOWLEDGE-JSONS.md
git commit -m "docs(knowledge): add KNOWLEDGE-JSONS.md coverage table and usage guide"
```

---

## Task 15: Final verification

- [ ] **Step 1: Run full test suite one final time**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ --timeout=60 -q 2>&1 | tail -10
```

Expected: ≥2111 passing (2021 baseline + 90 new knowledge JSON tests), 0 failures.

- [ ] **Step 2: Verify all 9 JSON files parse cleanly**

```bash
python -c "
import json, glob
files = glob.glob('docs/knowledge/*.json')
for f in sorted(files):
    with open(f) as fp:
        data = json.load(fp)
    print(f'OK: {f} — {len(data[\"extracted_rules\"])} rules')
"
```

Expected: 9 lines, each `OK`, rule counts between 10-20.

- [ ] **Step 3: Confirm no .backup files committed**

```bash
git status docs/knowledge/
```

Expected: no `*.backup` files in git status (should be gitignored).
