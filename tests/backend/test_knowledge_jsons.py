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
