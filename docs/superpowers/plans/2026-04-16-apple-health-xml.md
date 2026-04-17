# Apple Health XML Import (V3-X) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-optimized:subagent-driven-development (recommended) or superpowers-optimized:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add streaming Apple Health export.xml parser with daily aggregation, DB persistence, and feature-flagged endpoint.  
**Architecture:** New `integrations/apple_health/` module (parser → aggregator → importer), new `apple_health_daily` DB table, endpoint added to existing `routes/integrations.py`. Coexists with existing JSON connector at `connectors/apple_health.py` without overlap.  
**Tech Stack:** Python 3.13, lxml 5.x (streaming iterparse), SQLAlchemy Mapped[T], FastAPI, Alembic, pytest  
**Assumptions:** Assumes `alembic/` is at repo root (not `backend/alembic/`). Assumes existing pytest path `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe`. Assumes `pyproject.toml` at repo root controls dependencies. Will NOT work if lxml is missing — Task 1 adds it first.

---

## File map

| File | Action | Responsibility |
|------|--------|---------------|
| `pyproject.toml` | Modify | Add `lxml>=5.0,<6.0` dependency |
| `backend/app/integrations/apple_health/__init__.py` | Create | Package marker |
| `backend/app/integrations/apple_health/xml_parser.py` | Create | Streaming lxml.iterparse → `AppleHealthRecord` generator |
| `backend/app/integrations/apple_health/aggregator.py` | Create | `AppleHealthRecord` stream → `dict[date, AppleHealthDailySummary]` |
| `backend/app/integrations/apple_health/importer.py` | Create | Upsert summaries to DB; update ConnectorCredential + AthleteModel |
| `backend/app/db/models.py` | Modify | Add `AppleHealthDailyModel`; add relationship to `AthleteModel` |
| `alembic/versions/0010_apple_health_daily.py` | Create | Migration: `apple_health_daily` table |
| `backend/app/models/athlete_state.py` | Modify | Add `hrv_sdnn: Optional[float]` to `AthleteMetrics`; extend `SyncSourceName` |
| `backend/app/routes/integrations.py` | Modify | Add `POST /integrations/apple-health/import` endpoint |
| `.env.example` | Modify | Add `APPLE_HEALTH_ENABLED=false` |
| `tests/fixtures/apple_health/` | Create | 10 synthetic XML fixtures |
| `tests/backend/integrations/test_apple_health_parser.py` | Create | Parser unit tests |
| `tests/backend/integrations/test_apple_health_aggregator.py` | Create | Aggregator unit tests |
| `tests/backend/integrations/test_apple_health_importer.py` | Create | Importer unit tests |
| `tests/backend/api/test_apple_health_endpoint.py` | Create | Endpoint integration tests |
| `docs/backend/INTEGRATIONS.md` | Modify | Add Apple Health section with runtime warning |

---

### Task 1: Add lxml dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add lxml to dependencies**

In `pyproject.toml`, add `"lxml>=5.0,<6.0"` to the `dependencies` list after `httpx`:

```toml
    "httpx>=0.28.0,<1.0",
    "lxml>=5.0,<6.0",
```

- [ ] **Step 2: Install**

```bash
poetry add "lxml>=5.0,<6.0"
```

- [ ] **Step 3: Verify import**

```bash
poetry run python -c "from lxml import etree; print(etree.__version__)"
```

Expected: prints a version string like `5.3.0`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml poetry.lock
git commit -m "chore(deps): add lxml>=5.0 for Apple Health XML streaming parser"
```

---

### Task 2: Create synthetic XML fixtures

**Files:**
- Create: `tests/fixtures/apple_health/minimal_valid.xml`
- Create: `tests/fixtures/apple_health/sleep_ios15.xml`
- Create: `tests/fixtures/apple_health/sleep_ios16.xml`
- Create: `tests/fixtures/apple_health/sleep_with_inbed.xml`
- Create: `tests/fixtures/apple_health/multi_day_7d.xml`
- Create: `tests/fixtures/apple_health/body_mass_lbs.xml`
- Create: `tests/fixtures/apple_health/mixed_sources.xml`
- Create: `tests/fixtures/apple_health/truncated.xml`
- Create: `tests/fixtures/apple_health/large_range_90d.xml` (generated in step)
- Create: `tests/fixtures/apple_health/empty_target_types.xml`

- [ ] **Step 1: Create fixture directory and core fixtures**

Create `tests/fixtures/apple_health/minimal_valid.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_US">
 <ExportDate value="2026-04-16 10:00:00 +0000"/>
 <Record type="HKQuantityTypeIdentifierHeartRateVariabilitySDNN" sourceName="Apple Watch" unit="ms" creationDate="2026-04-15 08:00:00 +0000" startDate="2026-04-14 22:00:00 +0000" endDate="2026-04-15 06:00:00 +0000" value="45.3"/>
 <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch" unit="" creationDate="2026-04-15 08:00:00 +0000" startDate="2026-04-14 23:00:00 +0000" endDate="2026-04-15 07:00:00 +0000" value="HKCategoryValueSleepAnalysisAsleep"/>
 <Record type="HKQuantityTypeIdentifierRestingHeartRate" sourceName="Apple Watch" unit="count/min" creationDate="2026-04-15 08:00:00 +0000" startDate="2026-04-15 08:00:00 +0000" endDate="2026-04-15 08:00:00 +0000" value="52"/>
 <Record type="HKQuantityTypeIdentifierBodyMass" sourceName="Health" unit="kg" creationDate="2026-04-15 07:00:00 +0000" startDate="2026-04-15 07:00:00 +0000" endDate="2026-04-15 07:00:00 +0000" value="72.5"/>
 <Record type="HKQuantityTypeIdentifierActiveEnergyBurned" sourceName="Apple Watch" unit="kcal" creationDate="2026-04-15 22:00:00 +0000" startDate="2026-04-15 06:00:00 +0000" endDate="2026-04-15 22:00:00 +0000" value="450.0"/>
</HealthData>
```

Create `tests/fixtures/apple_health/sleep_ios15.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_US">
 <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch" unit="" creationDate="2026-04-15 07:00:00 +0000" startDate="2026-04-14 22:30:00 +0000" endDate="2026-04-15 06:30:00 +0000" value="HKCategoryValueSleepAnalysisAsleep"/>
 <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch" unit="" creationDate="2026-04-15 07:00:00 +0000" startDate="2026-04-14 22:00:00 +0000" endDate="2026-04-15 07:00:00 +0000" value="HKCategoryValueSleepAnalysisInBed"/>
</HealthData>
```

Create `tests/fixtures/apple_health/sleep_ios16.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_US">
 <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch" unit="" creationDate="2026-04-15 07:00:00 +0000" startDate="2026-04-14 23:00:00 +0000" endDate="2026-04-15 01:00:00 +0000" value="HKCategoryValueSleepAnalysisAsleepCore"/>
 <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch" unit="" creationDate="2026-04-15 07:00:00 +0000" startDate="2026-04-15 01:00:00 +0000" endDate="2026-04-15 02:30:00 +0000" value="HKCategoryValueSleepAnalysisAsleepDeep"/>
 <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch" unit="" creationDate="2026-04-15 07:00:00 +0000" startDate="2026-04-15 02:30:00 +0000" endDate="2026-04-15 04:30:00 +0000" value="HKCategoryValueSleepAnalysisAsleepREM"/>
 <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch" unit="" creationDate="2026-04-15 07:00:00 +0000" startDate="2026-04-15 04:30:00 +0000" endDate="2026-04-15 05:00:00 +0000" value="HKCategoryValueSleepAnalysisAwake"/>
</HealthData>
```
Expected: sleep_hours = 2.0 + 1.5 + 2.0 = 5.5h (Awake excluded)

Create `tests/fixtures/apple_health/sleep_with_inbed.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_US">
 <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch" unit="" creationDate="2026-04-15 07:00:00 +0000" startDate="2026-04-14 22:00:00 +0000" endDate="2026-04-15 07:00:00 +0000" value="HKCategoryValueSleepAnalysisInBed"/>
 <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch" unit="" creationDate="2026-04-15 07:00:00 +0000" startDate="2026-04-14 23:00:00 +0000" endDate="2026-04-15 06:00:00 +0000" value="HKCategoryValueSleepAnalysisAsleep"/>
</HealthData>
```
Expected: sleep_hours = 7.0 (only Asleep; InBed 9h excluded)

Create `tests/fixtures/apple_health/multi_day_7d.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_US">
 <Record type="HKQuantityTypeIdentifierHeartRateVariabilitySDNN" sourceName="Apple Watch" unit="ms" creationDate="2026-04-10 08:00:00 +0000" startDate="2026-04-09 22:00:00 +0000" endDate="2026-04-10 06:00:00 +0000" value="40.0"/>
 <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch" unit="" creationDate="2026-04-10 08:00:00 +0000" startDate="2026-04-09 23:00:00 +0000" endDate="2026-04-10 07:00:00 +0000" value="HKCategoryValueSleepAnalysisAsleep"/>
 <Record type="HKQuantityTypeIdentifierRestingHeartRate" sourceName="Apple Watch" unit="count/min" creationDate="2026-04-10 08:00:00 +0000" startDate="2026-04-10 08:00:00 +0000" endDate="2026-04-10 08:00:00 +0000" value="55"/>
 <Record type="HKQuantityTypeIdentifierActiveEnergyBurned" sourceName="Apple Watch" unit="kcal" creationDate="2026-04-10 20:00:00 +0000" startDate="2026-04-10 08:00:00 +0000" endDate="2026-04-10 20:00:00 +0000" value="400.0"/>
 <Record type="HKQuantityTypeIdentifierHeartRateVariabilitySDNN" sourceName="Apple Watch" unit="ms" creationDate="2026-04-11 08:00:00 +0000" startDate="2026-04-10 22:00:00 +0000" endDate="2026-04-11 06:00:00 +0000" value="38.0"/>
 <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch" unit="" creationDate="2026-04-11 08:00:00 +0000" startDate="2026-04-10 23:00:00 +0000" endDate="2026-04-11 06:30:00 +0000" value="HKCategoryValueSleepAnalysisAsleep"/>
 <Record type="HKQuantityTypeIdentifierRestingHeartRate" sourceName="Apple Watch" unit="count/min" creationDate="2026-04-11 08:00:00 +0000" startDate="2026-04-11 08:00:00 +0000" endDate="2026-04-11 08:00:00 +0000" value="57"/>
 <Record type="HKQuantityTypeIdentifierActiveEnergyBurned" sourceName="Apple Watch" unit="kcal" creationDate="2026-04-11 20:00:00 +0000" startDate="2026-04-11 08:00:00 +0000" endDate="2026-04-11 20:00:00 +0000" value="320.0"/>
 <Record type="HKQuantityTypeIdentifierHeartRateVariabilitySDNN" sourceName="Apple Watch" unit="ms" creationDate="2026-04-12 08:00:00 +0000" startDate="2026-04-11 22:00:00 +0000" endDate="2026-04-12 06:00:00 +0000" value="50.0"/>
 <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch" unit="" creationDate="2026-04-12 08:00:00 +0000" startDate="2026-04-11 22:30:00 +0000" endDate="2026-04-12 07:00:00 +0000" value="HKCategoryValueSleepAnalysisAsleep"/>
 <Record type="HKQuantityTypeIdentifierRestingHeartRate" sourceName="Apple Watch" unit="count/min" creationDate="2026-04-12 08:00:00 +0000" startDate="2026-04-12 08:00:00 +0000" endDate="2026-04-12 08:00:00 +0000" value="51"/>
 <Record type="HKQuantityTypeIdentifierBodyMass" sourceName="Health" unit="kg" creationDate="2026-04-12 07:00:00 +0000" startDate="2026-04-12 07:00:00 +0000" endDate="2026-04-12 07:00:00 +0000" value="73.0"/>
 <Record type="HKQuantityTypeIdentifierActiveEnergyBurned" sourceName="Apple Watch" unit="kcal" creationDate="2026-04-12 20:00:00 +0000" startDate="2026-04-12 08:00:00 +0000" endDate="2026-04-12 20:00:00 +0000" value="510.0"/>
 <Record type="HKQuantityTypeIdentifierHeartRateVariabilitySDNN" sourceName="Apple Watch" unit="ms" creationDate="2026-04-13 08:00:00 +0000" startDate="2026-04-12 22:00:00 +0000" endDate="2026-04-13 06:00:00 +0000" value="42.0"/>
 <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch" unit="" creationDate="2026-04-13 08:00:00 +0000" startDate="2026-04-12 23:00:00 +0000" endDate="2026-04-13 07:30:00 +0000" value="HKCategoryValueSleepAnalysisAsleep"/>
 <Record type="HKQuantityTypeIdentifierRestingHeartRate" sourceName="Apple Watch" unit="count/min" creationDate="2026-04-13 08:00:00 +0000" startDate="2026-04-13 08:00:00 +0000" endDate="2026-04-13 08:00:00 +0000" value="53"/>
 <Record type="HKQuantityTypeIdentifierActiveEnergyBurned" sourceName="Apple Watch" unit="kcal" creationDate="2026-04-13 20:00:00 +0000" startDate="2026-04-13 08:00:00 +0000" endDate="2026-04-13 20:00:00 +0000" value="380.0"/>
 <Record type="HKQuantityTypeIdentifierHeartRateVariabilitySDNN" sourceName="Apple Watch" unit="ms" creationDate="2026-04-14 08:00:00 +0000" startDate="2026-04-13 22:00:00 +0000" endDate="2026-04-14 06:00:00 +0000" value="35.0"/>
 <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch" unit="" creationDate="2026-04-14 08:00:00 +0000" startDate="2026-04-13 23:30:00 +0000" endDate="2026-04-14 06:30:00 +0000" value="HKCategoryValueSleepAnalysisAsleep"/>
 <Record type="HKQuantityTypeIdentifierRestingHeartRate" sourceName="Apple Watch" unit="count/min" creationDate="2026-04-14 08:00:00 +0000" startDate="2026-04-14 08:00:00 +0000" endDate="2026-04-14 08:00:00 +0000" value="60"/>
 <Record type="HKQuantityTypeIdentifierActiveEnergyBurned" sourceName="Apple Watch" unit="kcal" creationDate="2026-04-14 20:00:00 +0000" startDate="2026-04-14 08:00:00 +0000" endDate="2026-04-14 20:00:00 +0000" value="290.0"/>
 <Record type="HKQuantityTypeIdentifierHeartRateVariabilitySDNN" sourceName="Apple Watch" unit="ms" creationDate="2026-04-15 08:00:00 +0000" startDate="2026-04-14 22:00:00 +0000" endDate="2026-04-15 06:00:00 +0000" value="45.0"/>
 <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch" unit="" creationDate="2026-04-15 08:00:00 +0000" startDate="2026-04-14 23:00:00 +0000" endDate="2026-04-15 07:00:00 +0000" value="HKCategoryValueSleepAnalysisAsleep"/>
 <Record type="HKQuantityTypeIdentifierRestingHeartRate" sourceName="Apple Watch" unit="count/min" creationDate="2026-04-15 08:00:00 +0000" startDate="2026-04-15 08:00:00 +0000" endDate="2026-04-15 08:00:00 +0000" value="54"/>
 <Record type="HKQuantityTypeIdentifierActiveEnergyBurned" sourceName="Apple Watch" unit="kcal" creationDate="2026-04-15 20:00:00 +0000" startDate="2026-04-15 08:00:00 +0000" endDate="2026-04-15 20:00:00 +0000" value="420.0"/>
 <Record type="HKQuantityTypeIdentifierHeartRateVariabilitySDNN" sourceName="Apple Watch" unit="ms" creationDate="2026-04-16 08:00:00 +0000" startDate="2026-04-15 22:00:00 +0000" endDate="2026-04-16 06:00:00 +0000" value="48.0"/>
 <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch" unit="" creationDate="2026-04-16 08:00:00 +0000" startDate="2026-04-15 23:00:00 +0000" endDate="2026-04-16 06:30:00 +0000" value="HKCategoryValueSleepAnalysisAsleep"/>
 <Record type="HKQuantityTypeIdentifierRestingHeartRate" sourceName="Apple Watch" unit="count/min" creationDate="2026-04-16 08:00:00 +0000" startDate="2026-04-16 08:00:00 +0000" endDate="2026-04-16 08:00:00 +0000" value="52"/>
 <Record type="HKQuantityTypeIdentifierActiveEnergyBurned" sourceName="Apple Watch" unit="kcal" creationDate="2026-04-16 20:00:00 +0000" startDate="2026-04-16 08:00:00 +0000" endDate="2026-04-16 20:00:00 +0000" value="350.0"/>
</HealthData>
```

Create `tests/fixtures/apple_health/body_mass_lbs.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_US">
 <Record type="HKQuantityTypeIdentifierBodyMass" sourceName="Health" unit="lb" creationDate="2026-04-15 07:00:00 +0000" startDate="2026-04-15 07:00:00 +0000" endDate="2026-04-15 07:00:00 +0000" value="159.83"/>
</HealthData>
```
Expected body_mass_kg ≈ 72.5 (159.83 × 0.453592 = 72.497... ≈ 72.5)

Create `tests/fixtures/apple_health/mixed_sources.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_US">
 <Record type="HKQuantityTypeIdentifierRestingHeartRate" sourceName="Apple Watch" unit="count/min" creationDate="2026-04-15 08:00:00 +0000" startDate="2026-04-15 08:00:00 +0000" endDate="2026-04-15 08:00:00 +0000" value="52"/>
 <Record type="HKQuantityTypeIdentifierRestingHeartRate" sourceName="iPhone" unit="count/min" creationDate="2026-04-15 09:00:00 +0000" startDate="2026-04-15 09:00:00 +0000" endDate="2026-04-15 09:00:00 +0000" value="56"/>
</HealthData>
```
Expected rhr_bpm = (52 + 56) / 2 = 54.0

Create `tests/fixtures/apple_health/truncated.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_US">
 <Record type="HKQuantityTypeIdentifierRestingHeartRate" sourceName="Apple Watch" unit="count/min" creationDate="2026-04-15 08:00:00 +0000" startDate="2026-04-15 08:0
```

Create `tests/fixtures/apple_health/empty_target_types.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_US">
 <ExportDate value="2026-04-16 10:00:00 +0000"/>
 <Record type="HKQuantityTypeIdentifierHeartRate" sourceName="Apple Watch" unit="count/min" creationDate="2026-04-15 10:00:00 +0000" startDate="2026-04-15 10:00:00 +0000" endDate="2026-04-15 10:00:00 +0000" value="142"/>
 <Record type="HKQuantityTypeIdentifierStepCount" sourceName="iPhone" unit="count" creationDate="2026-04-15 20:00:00 +0000" startDate="2026-04-15 06:00:00 +0000" endDate="2026-04-15 20:00:00 +0000" value="8432"/>
</HealthData>
```

- [ ] **Step 2: Generate large_range_90d.xml via script**

Create a Python script `scripts/gen_apple_health_fixture.py` and run it once:

```python
"""Generate large_range_90d.xml with 90 days of all 5 metric types (~450 records)."""
from datetime import date, timedelta
import random

lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<HealthData locale="en_US">']
base = date(2026, 1, 16)
for i in range(90):
    d = base + timedelta(days=i)
    prev = d - timedelta(days=1)
    ds = d.isoformat()
    ps = prev.isoformat()
    lines.append(
        f' <Record type="HKQuantityTypeIdentifierHeartRateVariabilitySDNN" '
        f'sourceName="Apple Watch" unit="ms" '
        f'creationDate="{ds} 08:00:00 +0000" startDate="{ps} 22:00:00 +0000" '
        f'endDate="{ds} 06:00:00 +0000" value="{random.uniform(30,70):.1f}"/>'
    )
    lines.append(
        f' <Record type="HKCategoryTypeIdentifierSleepAnalysis" '
        f'sourceName="Apple Watch" unit="" '
        f'creationDate="{ds} 08:00:00 +0000" startDate="{ps} 23:00:00 +0000" '
        f'endDate="{ds} 07:00:00 +0000" value="HKCategoryValueSleepAnalysisAsleep"/>'
    )
    lines.append(
        f' <Record type="HKQuantityTypeIdentifierRestingHeartRate" '
        f'sourceName="Apple Watch" unit="count/min" '
        f'creationDate="{ds} 08:00:00 +0000" startDate="{ds} 08:00:00 +0000" '
        f'endDate="{ds} 08:00:00 +0000" value="{random.randint(48,65)}"/>'
    )
    lines.append(
        f' <Record type="HKQuantityTypeIdentifierActiveEnergyBurned" '
        f'sourceName="Apple Watch" unit="kcal" '
        f'creationDate="{ds} 20:00:00 +0000" startDate="{ds} 06:00:00 +0000" '
        f'endDate="{ds} 20:00:00 +0000" value="{random.uniform(200,600):.1f}"/>'
    )
lines.append('</HealthData>')

with open("tests/fixtures/apple_health/large_range_90d.xml", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"Generated {len(lines)-2} record lines")
```

Run: `poetry run python scripts/gen_apple_health_fixture.py`
Expected: prints "Generated 360 record lines"

- [ ] **Step 3: Commit fixtures**

```bash
git add tests/fixtures/apple_health/ scripts/gen_apple_health_fixture.py
git commit -m "test(fixtures): add 10 synthetic Apple Health XML fixtures for V3-X"
```

---

### Task 3: Create xml_parser.py (TDD)

**Files:**
- Create: `tests/backend/integrations/test_apple_health_parser.py`
- Create: `backend/app/integrations/apple_health/__init__.py`
- Create: `backend/app/integrations/apple_health/xml_parser.py`

**Does NOT cover:** Parsing of HK types outside `TARGET_TYPES` (ignored silently). Records with unparseable dates are skipped, not raised. Files without any `<Record>` elements yield 0 records without error.

- [ ] **Step 1: Write failing tests**

Create `tests/backend/integrations/test_apple_health_parser.py`:

```python
"""Tests for Apple Health XML streaming parser."""
from __future__ import annotations

import io
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from lxml import etree

from backend.app.integrations.apple_health.xml_parser import (
    TARGET_TYPES,
    AppleHealthRecord,
    parse_records,
)

FIXTURE_DIR = Path(__file__).parents[3] / "fixtures" / "apple_health"


def _parse(filename: str, **kwargs) -> list[AppleHealthRecord]:
    path = FIXTURE_DIR / filename
    with open(path, "rb") as f:
        return list(parse_records(f, **kwargs))


class TestMinimalValid:
    def test_yields_five_records(self):
        records = _parse("minimal_valid.xml")
        assert len(records) == 5

    def test_record_types_are_target_types(self):
        records = _parse("minimal_valid.xml")
        for r in records:
            assert r.record_type in TARGET_TYPES

    def test_dates_are_utc_aware(self):
        records = _parse("minimal_valid.xml")
        for r in records:
            assert r.start_date.tzinfo is not None
            assert r.end_date.tzinfo is not None
            assert r.start_date.tzinfo == timezone.utc

    def test_hrv_record_value_is_numeric_string(self):
        records = _parse("minimal_valid.xml")
        hrv = next(r for r in records if "HeartRateVariability" in r.record_type)
        assert float(hrv.value) == pytest.approx(45.3)

    def test_sleep_record_value_is_category_string(self):
        records = _parse("minimal_valid.xml")
        sleep = next(r for r in records if "SleepAnalysis" in r.record_type)
        assert sleep.value == "HKCategoryValueSleepAnalysisAsleep"

    def test_body_mass_unit_is_kg(self):
        records = _parse("minimal_valid.xml")
        mass = next(r for r in records if "BodyMass" in r.record_type)
        assert mass.unit == "kg"
        assert float(mass.value) == pytest.approx(72.5)


class TestSinceDate:
    def test_since_date_filters_older_records(self):
        """Records with end_date before since_date must be excluded."""
        records = _parse("minimal_valid.xml", since_date=date(2026, 4, 16))
        # All records in minimal_valid.xml end on 2026-04-15 → all filtered out
        assert len(records) == 0

    def test_since_date_includes_matching_records(self):
        records = _parse("minimal_valid.xml", since_date=date(2026, 4, 15))
        assert len(records) == 5


class TestSleepCategories:
    def test_ios15_sleep_record_included(self):
        records = _parse("sleep_ios15.xml")
        sleep_records = [r for r in records if "SleepAnalysis" in r.record_type]
        # Only the Asleep record, not InBed (InBed is still yielded by parser — filtering is aggregator's job)
        assert len(sleep_records) == 2  # parser yields ALL sleep records; aggregator filters

    def test_ios16_sleep_records_all_yielded(self):
        records = _parse("sleep_ios16.xml")
        sleep_records = [r for r in records if "SleepAnalysis" in r.record_type]
        assert len(sleep_records) == 4  # Core + Deep + REM + Awake all yielded by parser


class TestTruncatedXML:
    def test_raises_on_truncated_xml(self):
        with pytest.raises(etree.XMLSyntaxError):
            _parse("truncated.xml")


class TestEmptyTargetTypes:
    def test_no_records_yielded_for_non_target_types(self):
        records = _parse("empty_target_types.xml")
        assert len(records) == 0


class TestLargeRange:
    def test_90d_fixture_yields_expected_count(self):
        records = _parse("large_range_90d.xml")
        # 90 days × 4 records (HRV + sleep + RHR + energy) = 360
        assert len(records) == 360

    def test_no_memory_error(self):
        """Verify streaming works — no MemoryError on large fixture."""
        records = _parse("large_range_90d.xml")
        assert len(records) > 0


class TestBodyMassLbs:
    def test_yields_body_mass_record(self):
        records = _parse("body_mass_lbs.xml")
        assert len(records) == 1
        assert records[0].unit == "lb"
        # Parser yields raw value — unit conversion is aggregator's job
        assert float(records[0].value) == pytest.approx(159.83)
```

- [ ] **Step 2: Run tests — expect FAIL (module not found)**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/integrations/test_apple_health_parser.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'backend.app.integrations.apple_health'`

- [ ] **Step 3: Implement xml_parser.py**

Create `backend/app/integrations/apple_health/__init__.py` (empty):
```python
```

Create `backend/app/integrations/apple_health/xml_parser.py`:

```python
"""Streaming Apple Health export.xml parser.

Uses lxml.etree.iterparse for memory-efficient processing of large files (>100MB).
Only yields records for target HK types. Clears parsed elements to maintain O(1) memory.

WARNING: NOT VALIDATED ON REAL DEVICE — tested with synthetic fixtures only.
Validate against a real iPhone export before enabling APPLE_HEALTH_ENABLED=true in prod.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import BinaryIO, Generator

from lxml import etree

_DATE_FMT = "%Y-%m-%d %H:%M:%S %z"

TARGET_TYPES: frozenset[str] = frozenset({
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN",
    "HKCategoryTypeIdentifierSleepAnalysis",
    "HKQuantityTypeIdentifierRestingHeartRate",
    "HKQuantityTypeIdentifierBodyMass",
    "HKQuantityTypeIdentifierActiveEnergyBurned",
})


@dataclass
class AppleHealthRecord:
    """A single parsed Apple Health record."""

    record_type: str
    start_date: datetime   # timezone-aware, UTC
    end_date: datetime     # timezone-aware, UTC
    value: str             # Raw string. Quantity types: numeric. Category types: HKCategory* constant.
    unit: str
    source_name: str


def _parse_date(s: str) -> datetime:
    """Parse Apple Health date string to UTC-aware datetime.
    
    Format: "YYYY-MM-DD HH:MM:SS ±HHMM"
    """
    dt = datetime.strptime(s, _DATE_FMT)
    return dt.astimezone(timezone.utc)


def parse_records(
    file_obj: BinaryIO,
    target_types: frozenset[str] = TARGET_TYPES,
    since_date: date | None = None,
) -> Generator[AppleHealthRecord, None, None]:
    """Stream Apple Health XML, yielding records for target types only.

    Memory usage: O(1) per record. Clears each element after processing.
    Raises lxml.etree.XMLSyntaxError for malformed or truncated XML.

    Args:
        file_obj: Binary file-like object (UploadFile.file, open(..., "rb"), BytesIO)
        target_types: HK record type identifiers to include
        since_date: If given, skip records whose end_date.date() < since_date
    """
    context = etree.iterparse(
        file_obj,
        events=("end",),
        tag="Record",
        resolve_entities=False,
        huge_tree=True,
    )

    for _event, elem in context:
        record_type = elem.get("type", "")

        if record_type not in target_types:
            # Free memory immediately for non-target records
            parent = elem.getparent()
            elem.clear()
            if parent is not None:
                while parent and len(parent) and parent[0] is not elem:
                    del parent[0]
            continue

        start_str = elem.get("startDate")
        end_str = elem.get("endDate")
        value = elem.get("value", "")
        unit = elem.get("unit", "")
        source_name = elem.get("sourceName", "")

        # Free element memory before yielding
        parent = elem.getparent()
        elem.clear()
        if parent is not None:
            while parent and len(parent) and parent[0] is not elem:
                del parent[0]

        if not start_str or not end_str:
            continue

        try:
            start_dt = _parse_date(start_str)
            end_dt = _parse_date(end_str)
        except ValueError:
            continue  # skip records with unparseable dates

        if since_date is not None and end_dt.date() < since_date:
            continue

        yield AppleHealthRecord(
            record_type=record_type,
            start_date=start_dt,
            end_date=end_dt,
            value=value,
            unit=unit,
            source_name=source_name,
        )
```

- [ ] **Step 4: Run tests — expect PASS**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/integrations/test_apple_health_parser.py -v
```

Expected: all tests pass (green)

- [ ] **Step 5: Commit**

```bash
git add backend/app/integrations/apple_health/ tests/backend/integrations/test_apple_health_parser.py
git commit -m "feat(apple-health): streaming XML parser — lxml.iterparse, TARGET_TYPES, O(1) memory"
```

---

### Task 4: Create aggregator.py (TDD)

**Files:**
- Create: `tests/backend/integrations/test_apple_health_aggregator.py`
- Create: `backend/app/integrations/apple_health/aggregator.py`

**Does NOT cover:** Records with unparseable numeric values (silently skipped). Multiple HRV readings same night averaged (by design). Deduplication across sources (all sources included in aggregation).

- [ ] **Step 1: Write failing tests**

Create `tests/backend/integrations/test_apple_health_aggregator.py`:

```python
"""Tests for Apple Health daily aggregator."""
from __future__ import annotations

import io
from datetime import date
from pathlib import Path

import pytest

from backend.app.integrations.apple_health.aggregator import (
    AppleHealthDailySummary,
    aggregate,
)
from backend.app.integrations.apple_health.xml_parser import parse_records

FIXTURE_DIR = Path(__file__).parents[3] / "fixtures" / "apple_health"


def _agg(filename: str, **parse_kwargs) -> dict[date, AppleHealthDailySummary]:
    path = FIXTURE_DIR / filename
    with open(path, "rb") as f:
        records = parse_records(f, **parse_kwargs)
        return aggregate(records)


class TestMinimalValid:
    def test_returns_one_day(self):
        result = _agg("minimal_valid.xml")
        assert len(result) == 1

    def test_hrv_sdnn_avg(self):
        result = _agg("minimal_valid.xml")
        day = result[date(2026, 4, 15)]
        assert day.hrv_sdnn_avg == pytest.approx(45.3)

    def test_sleep_hours(self):
        # startDate=2026-04-14 23:00 UTC, endDate=2026-04-15 07:00 UTC → 8h, attributed to 2026-04-15
        result = _agg("minimal_valid.xml")
        day = result[date(2026, 4, 15)]
        assert day.sleep_hours == pytest.approx(8.0)

    def test_rhr_bpm(self):
        result = _agg("minimal_valid.xml")
        day = result[date(2026, 4, 15)]
        assert day.rhr_bpm == pytest.approx(52.0)

    def test_body_mass_kg(self):
        result = _agg("minimal_valid.xml")
        day = result[date(2026, 4, 15)]
        assert day.body_mass_kg == pytest.approx(72.5)

    def test_active_energy_kcal(self):
        result = _agg("minimal_valid.xml")
        day = result[date(2026, 4, 15)]
        assert day.active_energy_kcal == pytest.approx(450.0)


class TestSleepIOS15:
    def test_inbed_excluded_asleep_included(self):
        # Asleep: 23:00→06:30 = 7.5h; InBed: 22:00→07:00 = 9h (excluded)
        result = _agg("sleep_ios15.xml")
        day = result[date(2026, 4, 15)]
        assert day.sleep_hours == pytest.approx(7.5)

    def test_inbed_only_sleep_hours_is_none(self):
        # If only InBed records, no asleep records → sleep_hours = None
        # Use sleep_with_inbed.xml which has InBed (9h) + Asleep (7h)
        result = _agg("sleep_with_inbed.xml")
        day = result[date(2026, 4, 15)]
        assert day.sleep_hours == pytest.approx(7.0)  # only Asleep counted


class TestSleepIOS16:
    def test_core_deep_rem_summed_awake_excluded(self):
        # Core: 01:00-01:00 startDate=23:00→01:00 = 2h; Deep: 01:00→02:30 = 1.5h; REM: 02:30→04:30 = 2h; Awake: excluded
        result = _agg("sleep_ios16.xml")
        day = result[date(2026, 4, 15)]
        assert day.sleep_hours == pytest.approx(5.5)


class TestSleepAttributedToEndDate:
    def test_sleep_spanning_midnight_attributed_to_wakeup_day(self):
        # Record startDate=2026-04-14 23:00, endDate=2026-04-15 07:00 → day=2026-04-15
        result = _agg("minimal_valid.xml")
        assert date(2026, 4, 15) in result
        assert date(2026, 4, 14) not in result


class TestBodyMassLbs:
    def test_lbs_converted_to_kg(self):
        result = _agg("body_mass_lbs.xml")
        day = result[date(2026, 4, 15)]
        # 159.83 lb × 0.453592 ≈ 72.498 kg
        assert day.body_mass_kg == pytest.approx(72.5, abs=0.05)


class TestMixedSources:
    def test_rhr_averaged_across_sources(self):
        # Apple Watch: 52, iPhone: 56 → mean=54.0
        result = _agg("mixed_sources.xml")
        day = result[date(2026, 4, 15)]
        assert day.rhr_bpm == pytest.approx(54.0)


class TestMultiDay7d:
    def test_returns_seven_days(self):
        result = _agg("multi_day_7d.xml")
        assert len(result) == 7

    def test_day_with_body_mass(self):
        result = _agg("multi_day_7d.xml")
        day = result[date(2026, 4, 12)]
        assert day.body_mass_kg == pytest.approx(73.0)

    def test_days_without_body_mass_are_none(self):
        result = _agg("multi_day_7d.xml")
        for d, summary in result.items():
            if d != date(2026, 4, 12):
                assert summary.body_mass_kg is None


class TestEmptyTargetTypes:
    def test_empty_result_for_no_target_records(self):
        result = _agg("empty_target_types.xml")
        assert len(result) == 0
```

- [ ] **Step 2: Run tests — expect FAIL**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/integrations/test_apple_health_aggregator.py -v 2>&1 | head -15
```

Expected: `ModuleNotFoundError: No module named '...aggregator'`

- [ ] **Step 3: Implement aggregator.py**

Create `backend/app/integrations/apple_health/aggregator.py`:

```python
"""Aggregate AppleHealthRecord stream into per-day summaries.

WARNING: NOT VALIDATED ON REAL DEVICE — tested with synthetic fixtures only.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

from .xml_parser import AppleHealthRecord

# Sleep values that count as "asleep" time (InBed and Awake excluded)
_SLEEP_ASLEEP_VALUES: frozenset[str] = frozenset({
    "HKCategoryValueSleepAnalysisAsleep",       # iOS ≤ 15
    "HKCategoryValueSleepAnalysisAsleepCore",   # iOS 16+
    "HKCategoryValueSleepAnalysisAsleepDeep",   # iOS 16+
    "HKCategoryValueSleepAnalysisAsleepREM",    # iOS 16+
    # Excluded: HKCategoryValueSleepAnalysisInBed, HKCategoryValueSleepAnalysisAwake
})


@dataclass
class AppleHealthDailySummary:
    """Aggregated daily metrics from Apple Health records."""

    date: date
    hrv_sdnn_avg: float | None = None       # Mean SDNN (ms). NOTE: SDNN ≠ RMSSD; see INTEGRATIONS.md
    sleep_hours: float | None = None         # Sum of asleep durations; None if no asleep records
    rhr_bpm: float | None = None            # Mean resting heart rate (bpm)
    body_mass_kg: float | None = None       # Last body mass reading of the day (kg)
    active_energy_kcal: float | None = None  # Sum of active energy burned (kcal)


def aggregate(records: Iterable[AppleHealthRecord]) -> dict[date, AppleHealthDailySummary]:
    """Aggregate Apple Health records into per-day summaries.

    Returns a dict keyed by date. Dates with no target records are absent.

    Rules:
    - HRV SDNN: mean of all values for the day (by end_date)
    - Sleep: sum of asleep durations (InBed + Awake excluded); attributed to end_date (wake-up day)
    - RHR: mean of all readings for the day
    - Body mass: last reading of the day (latest end_date wins); lbs converted to kg
    - Active energy: sum of all readings for the day
    """
    _hrv: dict[date, list[float]] = defaultdict(list)
    _sleep: dict[date, float] = defaultdict(float)
    _sleep_seen: set[date] = set()  # tracks days with at least one asleep record
    _rhr: dict[date, list[float]] = defaultdict(list)
    _mass: dict[date, tuple[datetime, float]] = {}   # (end_datetime, value_kg)
    _energy: dict[date, float] = defaultdict(float)
    all_dates: set[date] = set()

    for r in records:
        rtype = r.record_type

        if rtype == "HKQuantityTypeIdentifierHeartRateVariabilitySDNN":
            try:
                d = r.end_date.date()
                all_dates.add(d)
                _hrv[d].append(float(r.value))
            except ValueError:
                pass

        elif rtype == "HKCategoryTypeIdentifierSleepAnalysis":
            d = r.end_date.date()  # attribute to wake-up day
            all_dates.add(d)
            if r.value in _SLEEP_ASLEEP_VALUES:
                duration_h = (r.end_date - r.start_date).total_seconds() / 3600
                _sleep[d] += duration_h
                _sleep_seen.add(d)

        elif rtype == "HKQuantityTypeIdentifierRestingHeartRate":
            try:
                d = r.end_date.date()
                all_dates.add(d)
                _rhr[d].append(float(r.value))
            except ValueError:
                pass

        elif rtype == "HKQuantityTypeIdentifierBodyMass":
            try:
                d = r.end_date.date()
                all_dates.add(d)
                raw = float(r.value)
                kg = raw * 0.453592 if r.unit in ("lb", "lbs") else raw
                existing = _mass.get(d)
                if existing is None or r.end_date > existing[0]:
                    _mass[d] = (r.end_date, kg)
            except ValueError:
                pass

        elif rtype == "HKQuantityTypeIdentifierActiveEnergyBurned":
            try:
                d = r.end_date.date()
                all_dates.add(d)
                _energy[d] += float(r.value)
            except ValueError:
                pass

    result: dict[date, AppleHealthDailySummary] = {}
    for d in all_dates:
        hrv_vals = _hrv.get(d, [])
        rhr_vals = _rhr.get(d, [])
        mass_entry = _mass.get(d)
        result[d] = AppleHealthDailySummary(
            date=d,
            hrv_sdnn_avg=sum(hrv_vals) / len(hrv_vals) if hrv_vals else None,
            sleep_hours=_sleep[d] if d in _sleep_seen else None,
            rhr_bpm=sum(rhr_vals) / len(rhr_vals) if rhr_vals else None,
            body_mass_kg=mass_entry[1] if mass_entry else None,
            active_energy_kcal=_energy[d] if d in _energy else None,
        )
    return result
```

- [ ] **Step 4: Run tests — expect PASS**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/integrations/test_apple_health_aggregator.py -v
```

Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add backend/app/integrations/apple_health/aggregator.py tests/backend/integrations/test_apple_health_aggregator.py
git commit -m "feat(apple-health): daily aggregator — SDNN/sleep/RHR/body-mass/energy"
```

---

### Task 5: Add DB model + Alembic migration 0010

**Files:**
- Modify: `backend/app/db/models.py`
- Create: `alembic/versions/0010_apple_health_daily.py`

**Does NOT cover:** Backfilling existing data. Rolling back migration (down() removes table).

- [ ] **Step 1: Add AppleHealthDailyModel to db/models.py**

In `backend/app/db/models.py`, after the `HeadCoachMessageModel` class, add:

```python
class AppleHealthDailyModel(Base):
    """Daily aggregated Apple Health metrics per athlete."""

    __tablename__ = "apple_health_daily"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"), nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    hrv_sdnn_avg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sleep_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rhr_bpm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    body_mass_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    active_energy_kcal: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    athlete: Mapped["AthleteModel"] = relationship("AthleteModel", back_populates="apple_health_daily")

    __table_args__ = (UniqueConstraint("athlete_id", "record_date"),)
```

Also add the relationship to `AthleteModel`:

```python
    apple_health_daily: Mapped[list["AppleHealthDailyModel"]] = relationship(
        "AppleHealthDailyModel", back_populates="athlete", cascade="all, delete-orphan"
    )
```

(Add this after the `head_coach_messages` relationship in `AthleteModel`)

- [ ] **Step 2: Create Alembic migration**

Create `alembic/versions/0010_apple_health_daily.py`:

```python
"""Apple Health daily metrics table

Revision ID: 0010
Revises: 0009
Create Date: 2026-04-16 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "apple_health_daily",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("athlete_id", sa.String(), sa.ForeignKey("athletes.id"), nullable=False),
        sa.Column("record_date", sa.Date(), nullable=False),
        sa.Column("hrv_sdnn_avg", sa.Float(), nullable=True),
        sa.Column("sleep_hours", sa.Float(), nullable=True),
        sa.Column("rhr_bpm", sa.Float(), nullable=True),
        sa.Column("body_mass_kg", sa.Float(), nullable=True),
        sa.Column("active_energy_kcal", sa.Float(), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("athlete_id", "record_date"),
    )
    op.create_index("ix_apple_health_daily_athlete_date", "apple_health_daily", ["athlete_id", "record_date"])


def downgrade() -> None:
    op.drop_index("ix_apple_health_daily_athlete_date", table_name="apple_health_daily")
    op.drop_table("apple_health_daily")
```

- [ ] **Step 3: Run migration**

```bash
poetry run alembic upgrade head
```

Expected: `Running upgrade 0009 -> 0010, Apple Health daily metrics table`

- [ ] **Step 4: Verify table exists**

```bash
poetry run python -c "
from backend.app.db.database import engine
from sqlalchemy import inspect
inspector = inspect(engine)
cols = [c['name'] for c in inspector.get_columns('apple_health_daily')]
print('columns:', cols)
"
```

Expected: `columns: ['id', 'athlete_id', 'record_date', 'hrv_sdnn_avg', 'sleep_hours', 'rhr_bpm', 'body_mass_kg', 'active_energy_kcal', 'imported_at']`

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/models.py alembic/versions/0010_apple_health_daily.py
git commit -m "feat(db): add apple_health_daily table + Alembic migration 0010"
```

---

### Task 6: Extend AthleteMetrics and SyncSourceName

**Files:**
- Modify: `backend/app/models/athlete_state.py`

**Does NOT cover:** Changes to AgentView or `_AGENT_VIEWS` matrix (hrv_sdnn is a new metrics field, already in `metrics` section).

- [ ] **Step 1: Add hrv_sdnn to AthleteMetrics and extend SyncSourceName**

In `backend/app/models/athlete_state.py`:

**Change SyncSourceName** from:
```python
SyncSourceName = Literal["strava", "hevy", "terra", "manual"]
```
to:
```python
SyncSourceName = Literal["strava", "hevy", "terra", "apple_health", "manual"]
```

**Add hrv_sdnn to AthleteMetrics** after `hrv_rmssd`:
```python
class AthleteMetrics(BaseModel):
    """Raw connector values + derived metrics for today."""

    date: date
    # Raw Terra
    hrv_rmssd: Optional[float] = None        # RMSSD (ms) from Terra — primary HRV metric
    hrv_sdnn: Optional[float] = None         # SDNN (ms) from Apple Health — NOT comparable to hrv_rmssd
    hrv_history_7d: list[float] = Field(default_factory=list)
    sleep_hours: Optional[float] = None
    terra_sleep_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    resting_hr: Optional[float] = None
    # Computed
    acwr: Optional[float] = None
    acwr_status: Optional[Literal["safe", "caution", "danger"]] = None
    readiness_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    fatigue_score: Optional[FatigueScore] = None
    muscle_strain: Optional[MuscleStrainScore] = None
```

- [ ] **Step 2: Verify no type errors**

```bash
poetry run mypy backend/app/models/athlete_state.py --strict --no-error-summary
```

Expected: `Success: no issues found in 1 source file`

- [ ] **Step 3: Run existing tests to verify no regression**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/ -x -q 2>&1 | tail -5
```

Expected: all existing tests pass

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/athlete_state.py
git commit -m "feat(athlete-state): add hrv_sdnn field + apple_health to SyncSourceName"
```

---

### Task 7: Create importer.py (TDD)

**Files:**
- Create: `tests/backend/integrations/test_apple_health_importer.py`
- Create: `backend/app/integrations/apple_health/importer.py`

**Does NOT cover:** Re-importing with different aggregation (existing rows are overwritten on upsert). Partial rollback on DB error (DB session handles transaction).

- [ ] **Step 1: Write failing tests**

Create `tests/backend/integrations/test_apple_health_importer.py`:

```python
"""Tests for Apple Health importer — DB upsert + side effects."""
from __future__ import annotations

import json
import uuid
from datetime import date, timedelta, timezone
from datetime import datetime as dt

import pytest
from sqlalchemy.orm import Session

from backend.app.db.models import (
    AppleHealthDailyModel,
    AthleteModel,
    ConnectorCredentialModel,
)
from backend.app.integrations.apple_health.aggregator import AppleHealthDailySummary
from backend.app.integrations.apple_health.importer import import_daily_summaries


def _make_athlete(db: Session, weight_kg: float = 75.0) -> AthleteModel:
    athlete = AthleteModel(
        id=str(uuid.uuid4()),
        name="Test",
        age=30,
        sex="M",
        weight_kg=weight_kg,
        height_cm=180.0,
        primary_sport="running",
        hours_per_week=8.0,
        sports_json="[]",
        goals_json="[]",
        available_days_json="[]",
    )
    db.add(athlete)
    db.commit()
    return athlete


def _make_summaries(
    dates: list[date],
    hrv: float = 42.0,
    sleep: float = 7.5,
    rhr: float = 52.0,
    mass: float | None = None,
    energy: float = 400.0,
) -> dict[date, AppleHealthDailySummary]:
    return {
        d: AppleHealthDailySummary(
            date=d,
            hrv_sdnn_avg=hrv,
            sleep_hours=sleep,
            rhr_bpm=rhr,
            body_mass_kg=mass,
            active_energy_kcal=energy,
        )
        for d in dates
    }


class TestBasicImport:
    def test_imports_correct_day_count(self, db_session: Session):
        athlete = _make_athlete(db_session)
        today = date.today()
        summaries = _make_summaries([today - timedelta(days=i) for i in range(3)])
        result = import_daily_summaries(athlete.id, summaries, db_session)
        assert result["days_imported"] == 3

    def test_rows_created_in_db(self, db_session: Session):
        athlete = _make_athlete(db_session)
        today = date.today()
        summaries = _make_summaries([today])
        import_daily_summaries(athlete.id, summaries, db_session)
        row = db_session.query(AppleHealthDailyModel).filter_by(
            athlete_id=athlete.id, record_date=today
        ).first()
        assert row is not None
        assert row.hrv_sdnn_avg == pytest.approx(42.0)
        assert row.sleep_hours == pytest.approx(7.5)
        assert row.rhr_bpm == pytest.approx(52.0)

    def test_date_range_returned(self, db_session: Session):
        athlete = _make_athlete(db_session)
        d1, d2 = date(2026, 4, 10), date(2026, 4, 15)
        summaries = _make_summaries([d1, d2])
        result = import_daily_summaries(athlete.id, summaries, db_session)
        assert result["date_range"]["from"] == "2026-04-10"
        assert result["date_range"]["to"] == "2026-04-15"


class TestUpsert:
    def test_reimport_same_day_updates_row(self, db_session: Session):
        athlete = _make_athlete(db_session)
        today = date.today()
        import_daily_summaries(athlete.id, _make_summaries([today], hrv=40.0), db_session)
        import_daily_summaries(athlete.id, _make_summaries([today], hrv=55.0), db_session)
        rows = db_session.query(AppleHealthDailyModel).filter_by(athlete_id=athlete.id).all()
        assert len(rows) == 1
        assert rows[0].hrv_sdnn_avg == pytest.approx(55.0)


class TestBodyMassUpdate:
    def test_weight_updated_when_recent(self, db_session: Session):
        athlete = _make_athlete(db_session, weight_kg=75.0)
        today = date.today()
        summaries = _make_summaries([today], mass=72.5)
        result = import_daily_summaries(athlete.id, summaries, db_session)
        assert result["weight_updated"] is True
        db_session.refresh(athlete)
        assert athlete.weight_kg == pytest.approx(72.5)

    def test_weight_not_updated_when_old(self, db_session: Session):
        athlete = _make_athlete(db_session, weight_kg=75.0)
        old_date = date.today() - timedelta(days=8)  # 8 days ago, beyond 7-day cutoff
        summaries = _make_summaries([old_date], mass=72.5)
        result = import_daily_summaries(athlete.id, summaries, db_session)
        assert result["weight_updated"] is False
        db_session.refresh(athlete)
        assert athlete.weight_kg == pytest.approx(75.0)  # unchanged

    def test_weight_not_updated_when_no_body_mass(self, db_session: Session):
        athlete = _make_athlete(db_session, weight_kg=75.0)
        today = date.today()
        summaries = _make_summaries([today], mass=None)
        result = import_daily_summaries(athlete.id, summaries, db_session)
        assert result["weight_updated"] is False


class TestConnectorCredential:
    def test_connector_credential_created_with_latest_values(self, db_session: Session):
        athlete = _make_athlete(db_session)
        today = date.today()
        summaries = _make_summaries([today], hrv=44.0, sleep=7.0, rhr=53.0)
        import_daily_summaries(athlete.id, summaries, db_session)
        cred = db_session.query(ConnectorCredentialModel).filter_by(
            athlete_id=athlete.id, provider="apple_health"
        ).first()
        assert cred is not None
        extra = json.loads(cred.extra_json)
        assert extra["last_hrv_sdnn"] == pytest.approx(44.0)
        assert extra["last_sleep_hours"] == pytest.approx(7.0)
        assert extra["last_hr_rest"] == 53


class TestEmptySummaries:
    def test_empty_summaries_returns_zero(self, db_session: Session):
        athlete = _make_athlete(db_session)
        result = import_daily_summaries(athlete.id, {}, db_session)
        assert result["days_imported"] == 0
        assert result["date_range"]["from"] is None
        assert result["date_range"]["to"] is None
```

- [ ] **Step 2: Run — expect FAIL**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/integrations/test_apple_health_importer.py -v 2>&1 | head -15
```

Expected: `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Implement importer.py**

Create `backend/app/integrations/apple_health/importer.py`:

```python
"""Upsert Apple Health daily summaries to DB.

Side effects:
- Creates/updates apple_health_daily rows (upsert by athlete_id + record_date)
- Updates AthleteModel.weight_kg when body_mass_kg is present and < 7 days old
- Creates/updates ConnectorCredentialModel for provider="apple_health" with latest snapshot

WARNING: NOT VALIDATED ON REAL DEVICE — tested with synthetic fixtures only.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ...db.models import AppleHealthDailyModel, AthleteModel, ConnectorCredentialModel
from .aggregator import AppleHealthDailySummary


def import_daily_summaries(
    athlete_id: str,
    summaries: dict[date, AppleHealthDailySummary],
    db: Session,
) -> dict:
    """Upsert daily Apple Health summaries into apple_health_daily.

    Returns:
        dict with keys: days_imported, weight_updated, date_range
    """
    now = datetime.now(timezone.utc)
    cutoff_for_weight = (now - timedelta(days=7)).date()

    days_imported = 0
    weight_updated = False
    latest_date: date | None = None
    latest_summary: AppleHealthDailySummary | None = None

    for d, summary in sorted(summaries.items()):
        row = (
            db.query(AppleHealthDailyModel)
            .filter_by(athlete_id=athlete_id, record_date=d)
            .first()
        )
        if row is None:
            row = AppleHealthDailyModel(
                id=str(uuid.uuid4()),
                athlete_id=athlete_id,
                record_date=d,
            )
            db.add(row)

        row.hrv_sdnn_avg = summary.hrv_sdnn_avg
        row.sleep_hours = summary.sleep_hours
        row.rhr_bpm = summary.rhr_bpm
        row.body_mass_kg = summary.body_mass_kg
        row.active_energy_kcal = summary.active_energy_kcal
        row.imported_at = now
        days_imported += 1

        # Track latest for ConnectorCredential
        if latest_date is None or d > latest_date:
            latest_date = d
            latest_summary = summary

        # Update weight if measurement is recent (< 7 days old)
        if summary.body_mass_kg is not None and d >= cutoff_for_weight:
            athlete = db.get(AthleteModel, athlete_id)
            if athlete is not None:
                athlete.weight_kg = summary.body_mass_kg
                weight_updated = True

    # Update ConnectorCredential snapshot (backward compat with JSON upload endpoint)
    if latest_summary is not None and latest_date is not None:
        _update_connector_credential(athlete_id, latest_date, latest_summary, now, db)

    db.commit()

    dates = list(summaries.keys())
    return {
        "days_imported": days_imported,
        "weight_updated": weight_updated,
        "date_range": {
            "from": min(dates).isoformat() if dates else None,
            "to": max(dates).isoformat() if dates else None,
        },
    }


def _update_connector_credential(
    athlete_id: str,
    latest_date: date,
    latest: AppleHealthDailySummary,
    now: datetime,
    db: Session,
) -> None:
    extra = {
        "last_snapshot_date": latest_date.isoformat(),
        "last_hrv_sdnn": latest.hrv_sdnn_avg,
        "last_sleep_hours": latest.sleep_hours,
        "last_hr_rest": int(latest.rhr_bpm) if latest.rhr_bpm is not None else None,
        "last_upload": now.isoformat(),
    }
    row = (
        db.query(ConnectorCredentialModel)
        .filter_by(athlete_id=athlete_id, provider="apple_health")
        .first()
    )
    if row is not None:
        existing = json.loads(row.extra_json or "{}")
        existing.update(extra)
        row.extra_json = json.dumps(existing)
    else:
        db.add(
            ConnectorCredentialModel(
                id=str(uuid.uuid4()),
                athlete_id=athlete_id,
                provider="apple_health",
                extra_json=json.dumps(extra),
            )
        )
```

- [ ] **Step 4: Run tests — expect PASS**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/integrations/test_apple_health_importer.py -v
```

Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add backend/app/integrations/apple_health/importer.py tests/backend/integrations/test_apple_health_importer.py
git commit -m "feat(apple-health): importer — upsert daily, update weight + ConnectorCredential"
```

---

### Task 8: Add endpoint + integration tests (TDD)

**Files:**
- Create: `tests/backend/api/test_apple_health_endpoint.py`
- Modify: `backend/app/routes/integrations.py`

**Does NOT cover:** Feature flag changes at runtime (checked once per request). File size limit (gunicorn 120s timeout is the practical limit). Content-type validation (FastAPI handles this).

- [ ] **Step 1: Write failing endpoint tests**

Create `tests/backend/api/test_apple_health_endpoint.py`:

```python
"""Integration tests for POST /integrations/apple-health/import."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

FIXTURE_DIR = Path(__file__).parents[3] / "fixtures" / "apple_health"


class TestFeatureFlag:
    def test_disabled_returns_503(self, client: TestClient, auth_headers: dict):
        with patch.dict(os.environ, {"APPLE_HEALTH_ENABLED": "false"}):
            with open(FIXTURE_DIR / "minimal_valid.xml", "rb") as f:
                resp = client.post(
                    "/integrations/apple-health/import",
                    files={"file": ("export.xml", f, "application/xml")},
                    headers=auth_headers,
                )
        assert resp.status_code == 503
        assert "APPLE_HEALTH_ENABLED" in resp.json()["detail"]

    def test_enabled_returns_200(self, client: TestClient, auth_headers: dict):
        with patch.dict(os.environ, {"APPLE_HEALTH_ENABLED": "true"}):
            with open(FIXTURE_DIR / "minimal_valid.xml", "rb") as f:
                resp = client.post(
                    "/integrations/apple-health/import",
                    files={"file": ("export.xml", f, "application/xml")},
                    headers=auth_headers,
                )
        assert resp.status_code == 200


class TestValidImport:
    def test_response_shape(self, client: TestClient, auth_headers: dict):
        with patch.dict(os.environ, {"APPLE_HEALTH_ENABLED": "true"}):
            with open(FIXTURE_DIR / "minimal_valid.xml", "rb") as f:
                resp = client.post(
                    "/integrations/apple-health/import",
                    files={"file": ("export.xml", f, "application/xml")},
                    headers=auth_headers,
                )
        data = resp.json()
        assert "days_imported" in data
        assert "date_range" in data
        assert "summaries" in data
        assert "weight_updated" in data

    def test_minimal_valid_imports_one_day(self, client: TestClient, auth_headers: dict):
        with patch.dict(os.environ, {"APPLE_HEALTH_ENABLED": "true"}):
            with open(FIXTURE_DIR / "minimal_valid.xml", "rb") as f:
                resp = client.post(
                    "/integrations/apple-health/import",
                    files={"file": ("export.xml", f, "application/xml")},
                    headers=auth_headers,
                )
        assert resp.json()["days_imported"] == 1

    def test_multi_day_imports_seven_days(self, client: TestClient, auth_headers: dict):
        with patch.dict(os.environ, {"APPLE_HEALTH_ENABLED": "true"}):
            with open(FIXTURE_DIR / "multi_day_7d.xml", "rb") as f:
                resp = client.post(
                    "/integrations/apple-health/import",
                    files={"file": ("export.xml", f, "application/xml")},
                    headers=auth_headers,
                )
        assert resp.json()["days_imported"] == 7


class TestErrorCases:
    def test_truncated_xml_returns_422(self, client: TestClient, auth_headers: dict):
        with patch.dict(os.environ, {"APPLE_HEALTH_ENABLED": "true"}):
            with open(FIXTURE_DIR / "truncated.xml", "rb") as f:
                resp = client.post(
                    "/integrations/apple-health/import",
                    files={"file": ("export.xml", f, "application/xml")},
                    headers=auth_headers,
                )
        assert resp.status_code == 422

    def test_unauthenticated_returns_401(self, client: TestClient):
        with patch.dict(os.environ, {"APPLE_HEALTH_ENABLED": "true"}):
            with open(FIXTURE_DIR / "minimal_valid.xml", "rb") as f:
                resp = client.post(
                    "/integrations/apple-health/import",
                    files={"file": ("export.xml", f, "application/xml")},
                )
        assert resp.status_code == 401

    def test_empty_target_types_returns_zero(self, client: TestClient, auth_headers: dict):
        with patch.dict(os.environ, {"APPLE_HEALTH_ENABLED": "true"}):
            with open(FIXTURE_DIR / "empty_target_types.xml", "rb") as f:
                resp = client.post(
                    "/integrations/apple-health/import",
                    files={"file": ("export.xml", f, "application/xml")},
                    headers=auth_headers,
                )
        assert resp.status_code == 200
        assert resp.json()["days_imported"] == 0
```

- [ ] **Step 2: Run — expect FAIL**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/api/test_apple_health_endpoint.py -v 2>&1 | head -20
```

Expected: 404 on route (route not yet added)

- [ ] **Step 3: Add endpoint to routes/integrations.py**

In `backend/app/routes/integrations.py`, add imports at top:

```python
import io
import os

from lxml import etree
```

Add after existing hevy import endpoint:

```python
@router.post("/apple-health/import")
def apple_health_xml_import(
    db: DB,
    athlete_id: Annotated[str, Depends(get_current_athlete_id)],
    file: UploadFile = File(...),
    days_back: int = Query(default=90, ge=1, le=365),
) -> dict[str, Any]:
    """Import Apple Health export.xml → aggregate daily summaries → upsert to DB.

    Streams the XML with lxml.iterparse (O(1) memory, handles >100MB files).
    Feature-flagged via APPLE_HEALTH_ENABLED env var (default: false).

    WARNING: NOT VALIDATED ON REAL DEVICE — tested with synthetic fixtures only.
    Enable APPLE_HEALTH_ENABLED=true only after validating against a real iPhone export.
    """
    if not os.getenv("APPLE_HEALTH_ENABLED", "false").lower() == "true":
        raise HTTPException(
            status_code=503,
            detail="Apple Health integration disabled (set APPLE_HEALTH_ENABLED=true to enable)",
        )

    from datetime import date, timedelta

    from ..integrations.apple_health.aggregator import aggregate
    from ..integrations.apple_health.importer import import_daily_summaries
    from ..integrations.apple_health.xml_parser import parse_records

    since_date = date.today() - timedelta(days=days_back)

    content = file.file.read()
    try:
        records = list(parse_records(io.BytesIO(content), since_date=since_date))
    except etree.XMLSyntaxError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid or truncated XML: {exc}")

    summaries = aggregate(iter(records))
    result = import_daily_summaries(athlete_id, summaries, db)

    return {
        "days_imported": result["days_imported"],
        "records_processed": len(records),
        "date_range": result["date_range"],
        "weight_updated": result["weight_updated"],
        "summaries": {
            "hrv_days": sum(1 for s in summaries.values() if s.hrv_sdnn_avg is not None),
            "sleep_days": sum(1 for s in summaries.values() if s.sleep_hours is not None),
            "rhr_days": sum(1 for s in summaries.values() if s.rhr_bpm is not None),
            "body_mass_days": sum(1 for s in summaries.values() if s.body_mass_kg is not None),
            "active_energy_days": sum(1 for s in summaries.values() if s.active_energy_kcal is not None),
        },
    }
```

- [ ] **Step 4: Run tests — expect PASS**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/api/test_apple_health_endpoint.py -v
```

Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/integrations.py tests/backend/api/test_apple_health_endpoint.py
git commit -m "feat(apple-health): POST /integrations/apple-health/import — feature-flagged endpoint"
```

---

### Task 9: Update .env.example and INTEGRATIONS.md

**Files:**
- Modify: `.env.example`
- Modify: `docs/backend/INTEGRATIONS.md`

- [ ] **Step 1: Add feature flag to .env.example**

Add after the `# --- Admin ---` section:

```
# --- Apple Health (experimental — NOT validated on real device) ---
# WARNING: V1 — tested with synthetic fixtures only.
# Validate against a real iPhone export before enabling in production.
# Enable only after runtime validation on a real device.
APPLE_HEALTH_ENABLED=false
```

- [ ] **Step 2: Update INTEGRATIONS.md Apple Health section**

Replace the existing `## 4. Apple Health — Placeholder` section with:

```markdown
## 4. Apple Health — XML Import

> ⚠️ **WARNING: NOT VALIDATED ON REAL DEVICE.** This integration was built and tested with
> synthetic XML fixtures only. Validate against a real iPhone export.xml before enabling
> `APPLE_HEALTH_ENABLED=true` in production.

**Endpoint:** `POST /integrations/apple-health/import`  
**Auth:** JWT Bearer  
**Content-Type:** `multipart/form-data`  
**Feature flag:** `APPLE_HEALTH_ENABLED=false` (default disabled)  
**Returns 503** if feature flag is false.

### 4.1 Parsed HK Record Types

| HK Record Type | DB Column | AthleteMetrics Field | Notes |
|----------------|-----------|----------------------|-------|
| `HKQuantityTypeIdentifierHeartRateVariabilitySDNN` | `hrv_sdnn_avg` | `hrv_sdnn` | SDNN (ms) — NOT the same as Terra's RMSSD |
| `HKCategoryTypeIdentifierSleepAnalysis` | `sleep_hours` | `sleep_hours` | Asleep only (InBed + Awake excluded) |
| `HKQuantityTypeIdentifierRestingHeartRate` | `rhr_bpm` | `resting_hr` | Mean daily |
| `HKQuantityTypeIdentifierBodyMass` | `body_mass_kg` | `AthleteModel.weight_kg` | Updated if < 7 days old; lbs→kg auto-converted |
| `HKQuantityTypeIdentifierActiveEnergyBurned` | `active_energy_kcal` | future EnergySnapshot | Sum daily |

### 4.2 SDNN vs RMSSD

**Do NOT compare absolute values between sources:**
- **RMSSD** (Terra): Root Mean Square of Successive Differences — parasympathetic HRV.
  Typical range: 20–80ms.
- **SDNN** (Apple Health): Standard Deviation of NN intervals — overall autonomic variability.
  Typically 30–120ms (always higher than RMSSD for same session).

Both trend in the same direction (fatigue ↓ both; recovery ↑ both) but absolute values differ.
Stored in separate fields: `AthleteMetrics.hrv_rmssd` (Terra) vs `AthleteMetrics.hrv_sdnn` (Apple Health).
Recovery Coach uses `hrv_rmssd` when available; falls back to `hrv_sdnn` for trend detection only.

### 4.3 Streaming

Apple Health `export.xml` can exceed 100MB. The parser uses `lxml.etree.iterparse` with element
clearing for O(1) memory usage. Gunicorn timeout (120s) is the practical size limit. Files
>500MB may timeout — document as V1 limitation.

### 4.4 Endpoint parameters

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `file` | File | required | Apple Health `export.xml` |
| `days_back` | int | 90 | How many days back to import (max 365) |

### 4.5 Response

```json
{
  "days_imported": 42,
  "records_processed": 387,
  "date_range": {"from": "2026-03-06", "to": "2026-04-15"},
  "weight_updated": false,
  "summaries": {
    "hrv_days": 38,
    "sleep_days": 42,
    "rhr_days": 41,
    "body_mass_days": 5,
    "active_energy_days": 42
  }
}
```

### 4.6 Module structure

```
backend/app/integrations/apple_health/
  xml_parser.py    — streaming lxml.iterparse → AppleHealthRecord generator
  aggregator.py    — records → dict[date, AppleHealthDailySummary]; iOS 15/16 sleep compat
  importer.py      — upsert apple_health_daily + update ConnectorCredential + AthleteModel

DB table: apple_health_daily (migration 0010)
  UniqueConstraint(athlete_id, record_date) — safe re-import
```

### 4.7 Coexistence with existing JSON connector

`POST /{athlete_id}/connectors/apple-health/upload` (existing, at `routes/connectors.py`) accepts
a simple JSON snapshot (single day, manual values). The XML import (this endpoint) writes to the
same `ConnectorCredentialModel.extra_json` for backward compatibility.
```

- [ ] **Step 3: Commit**

```bash
git add .env.example docs/backend/INTEGRATIONS.md
git commit -m "docs(apple-health): update INTEGRATIONS.md + .env.example feature flag"
```

---

### Task 10: Full test suite + CLAUDE.md update

**Files:**
- Modify: `CLAUDE.md`

**Does NOT cover:** Mypy strict check on new files (run separately if desired).

- [ ] **Step 1: Run full test suite**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -x -q 2>&1 | tail -10
```

Expected: ≥2378 tests + new Apple Health tests passing. Maximum 2 pre-existing failures (`test_history_shows_logged_count`, `test_high_continuity_no_breaks`).

- [ ] **Step 2: Run mypy on new files**

```bash
poetry run mypy backend/app/integrations/apple_health/ backend/app/routes/integrations.py --strict --no-error-summary
```

Expected: `Success: no issues found`

- [ ] **Step 3: Update CLAUDE.md**

In `CLAUDE.md`, update the pytest count to reflect new tests and add V3-X to phase status.

Add to Phase Status table after V3-W:
```
| V3-X | Apple Health XML Import — streaming lxml.iterparse, `apple_health_daily` table (Alembic 0010), `AthleteMetrics.hrv_sdnn`, `POST /integrations/apple-health/import` (feature-flagged), 10 synthetic fixtures, SDNN/RMSSD separation documented | ✅ Complete (2026-04-16) |
```

Update "Dernières phases complétées" block — add above V3-W:

```
**Dernières phases complétées (2026-04-16) :** V3-X livré — Apple Health XML import. Parser streaming lxml.iterparse O(1) mémoire (>100MB supporté). 5 types HK ciblés: HRV SDNN, Sleep (iOS 15/16 compat), RHR, Body Mass, Active Energy. Agrégation quotidienne; sleep attribuée à end_date (réveil); InBed/Awake exclus. Nouveau champ AthleteMetrics.hrv_sdnn (SDNN ≠ RMSSD Terra — champs séparés). Table apple_health_daily + Alembic 0010. Feature flag APPLE_HEALTH_ENABLED=false. 10 fixtures synthétiques. WARNING: non-validé sur device réel.
```

Update pytest count in Development Rules to reflect V3-X additions.

- [ ] **Step 4: Add Key Reference to CLAUDE.md**

Find the Key References section and add (after Integrations Reference):
```
- **Typing Conventions**: `docs/backend/TYPING-CONVENTIONS.md` — mypy --strict patterns (Mapped[T], Self, Literal, cast, getattr fallback)
```
(This should already be there from V3-W; skip if duplicate.)

- [ ] **Step 5: Final commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude): add V3-X Apple Health phase + update test count"
git push origin main
```

Expected: `git log --oneline -6` shows V3-X commit at HEAD.
