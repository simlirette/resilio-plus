# Apple Health XML Import — Design Spec

**Date:** 2026-04-16  
**Status:** Approved  
**Phase:** V3-X  
**Author:** Claude Sonnet 4.6

---

## Scope

### In

- Streaming parser for Apple Health `export.xml` (lxml.iterparse, memory-efficient, >100MB supported)
- 5 target HK record types: HRV SDNN, Sleep, RHR, Body Mass, Active Energy
- Daily aggregation (90-day window default)
- New DB table `apple_health_daily` + Alembic migration 0010
- `POST /integrations/apple-health/import` endpoint (multipart, JWT auth, feature flag)
- Feature flag `APPLE_HEALTH_ENABLED=false` (.env.example)
- `hrv_sdnn` field added to `AthleteMetrics` (separate from Terra `hrv_rmssd`)
- Body mass import updates `AthleteModel.weight_kg` when measurement < 7 days old
- Exhaustive synthetic XML fixtures (10 files) + unit tests
- `docs/backend/INTEGRATIONS.md` update with Apple Health section + runtime warning
- `SyncSourceName` extended to include `"apple_health"`

### Out

- Real-time webhook or HealthKit SDK integration
- Background/async job (synchronous streaming is fast enough; gunicorn timeout 120s)
- Parsing all HK types (only 5 target types)
- Historical data beyond 365 days
- Android Health Connect integration

---

## Architecture

```
backend/app/integrations/apple_health/
  __init__.py
  xml_parser.py    — streaming lxml.iterparse → Generator[AppleHealthRecord]
  aggregator.py    — Iterable[AppleHealthRecord] → dict[date, AppleHealthDailySummary]
  importer.py      — upsert apple_health_daily + update ConnectorCredential + update AthleteModel

backend/app/db/models.py
  AppleHealthDailyModel (new table: apple_health_daily)

backend/app/routes/integrations.py
  POST /integrations/apple-health/import

backend/app/models/athlete_state.py
  AthleteMetrics.hrv_sdnn: Optional[float] = None   (new field)

backend/app/models/athlete_state.py
  SyncSourceName: add "apple_health" to Literal

alembic/versions/0010_add_apple_health_daily.py

tests/fixtures/apple_health/          (10 synthetic XML fixtures)
tests/backend/integrations/
  test_apple_health_parser.py
  test_apple_health_importer.py
```

---

## Data flow

```
POST /integrations/apple-health/import
  └─ Feature flag check (APPLE_HEALTH_ENABLED)
  └─ file.file.read() → bytes
  └─ xml_parser.parse_records(bytes_io, TARGET_TYPES, since_date)
       └─ lxml.iterparse, resolve_entities=False
       └─ yields AppleHealthRecord (Generator, O(1) memory)
  └─ aggregator.aggregate(records)
       └─ dict[date, AppleHealthDailySummary]
  └─ importer.import_daily_summaries(athlete_id, summaries, db)
       └─ upsert apple_health_daily (UniqueConstraint athlete_id+date)
       └─ update ConnectorCredential.extra_json (last snapshot for JSON compat)
       └─ if body_mass recent (< 7d): update AthleteModel.weight_kg
  └─ return {days_imported, records_processed, date_range}
```

---

## Record types and parsing

### Target types

```python
TARGET_TYPES: set[str] = {
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN",
    "HKCategoryTypeIdentifierSleepAnalysis",
    "HKQuantityTypeIdentifierRestingHeartRate",
    "HKQuantityTypeIdentifierBodyMass",
    "HKQuantityTypeIdentifierActiveEnergyBurned",
}
```

### Apple Health XML record structure

```xml
<Record 
  type="HKQuantityTypeIdentifierRestingHeartRate"
  sourceName="Apple Watch"
  unit="count/min"
  creationDate="2024-01-15 08:00:00 -0500"
  startDate="2024-01-15 08:00:00 -0500"
  endDate="2024-01-15 08:00:00 -0500"
  value="52"
/>
```

Date format: `"%Y-%m-%d %H:%M:%S %z"` → parse as timezone-aware, convert to UTC.

### Sleep category values (critical — string, not float)

`HKCategoryTypeIdentifierSleepAnalysis` stores `value` as a named constant:

```python
_SLEEP_ASLEEP_VALUES: frozenset[str] = frozenset({
    "HKCategoryValueSleepAnalysisAsleep",       # iOS ≤ 15
    "HKCategoryValueSleepAnalysisAsleepCore",   # iOS 16+
    "HKCategoryValueSleepAnalysisAsleepDeep",   # iOS 16+
    "HKCategoryValueSleepAnalysisAsleepREM",    # iOS 16+
})
# Excluded: HKCategoryValueSleepAnalysisInBed, HKCategoryValueSleepAnalysisAwake
```

Sleep duration = `(end_date - start_date).total_seconds() / 3600` for records in `_SLEEP_ASLEEP_VALUES`.

### Body mass unit conversion

```python
if record.unit in ("lb", "lbs"):
    value_kg = float(record.value) * 0.453592
else:
    value_kg = float(record.value)  # unit == "kg"
```

### Aggregation rules

| Metric | Rule |
|--------|------|
| `hrv_sdnn_avg` | Mean of all SDNN values for the day |
| `sleep_hours` | Sum of asleep durations; sleep record attributed to `end_date.date()` (wake-up day) |
| `rhr_bpm` | Mean of all RHR readings for the day |
| `body_mass_kg` | Last reading of the day (chronological) |
| `active_energy_kcal` | Sum of all active energy readings for the day |

---

## DB Model

```python
class AppleHealthDailyModel(Base):
    __tablename__ = "apple_health_daily"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"), nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    hrv_sdnn_avg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sleep_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rhr_bpm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    body_mass_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    active_energy_kcal: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    athlete: Mapped[AthleteModel] = relationship("AthleteModel", back_populates="apple_health_daily")

    __table_args__ = (UniqueConstraint("athlete_id", "record_date"),)
```

Alembic migration 0010. Also adds `apple_health_daily` relationship to `AthleteModel`.

---

## AthleteMetrics extension

```python
class AthleteMetrics(BaseModel):
    # ... existing fields ...
    hrv_rmssd: Optional[float] = None            # Terra — RMSSD (ms)
    hrv_sdnn: Optional[float] = None             # Apple Health — SDNN (ms); NOT comparable to hrv_rmssd
    hrv_history_7d: list[float] = Field(default_factory=list)
    sleep_hours: Optional[float] = None
    resting_hr: Optional[float] = None
```

**Recovery Coach priority**: when both sources present, Terra `hrv_rmssd` takes priority. Apple `hrv_sdnn` used as fallback only. Never compare SDNN to RMSSD absolute values.

---

## SyncSourceName extension

```python
SyncSourceName = Literal["strava", "hevy", "terra", "apple_health", "manual"]
```

---

## Endpoint

```python
@router.post("/apple-health/import")
def apple_health_xml_import(
    db: DB,
    athlete_id: Annotated[str, Depends(get_current_athlete_id)],
    file: UploadFile = File(...),
    days_back: int = Query(default=90, ge=1, le=365),
) -> dict[str, Any]:
```

**Feature flag check:**
```python
if not os.getenv("APPLE_HEALTH_ENABLED", "false").lower() == "true":
    raise HTTPException(status_code=503, detail="Apple Health integration disabled (APPLE_HEALTH_ENABLED=false)")
```

**Response:**
```json
{
  "days_imported": 42,
  "records_processed": 387,
  "date_range": {"from": "2024-03-01", "to": "2024-04-15"},
  "summaries": {
    "hrv_days": 38,
    "sleep_days": 42,
    "rhr_days": 41,
    "body_mass_days": 5,
    "active_energy_days": 42
  },
  "weight_updated": true
}
```

**HTTP errors:**
| Status | Cause |
|--------|-------|
| 503 | Feature flag disabled |
| 422 | Invalid/truncated XML, malformed records |
| 404 | Athlete not found |
| 413 | File too large (>50MB content-length check) — note: no hard limit enforced, gunicorn timeout=120s is the practical limit |

---

## Synthetic XML fixtures

| File | Purpose |
|------|---------|
| `minimal_valid.xml` | 1 record per type, single day, correct format |
| `sleep_ios15.xml` | HKCategoryValueSleepAnalysisAsleep only |
| `sleep_ios16.xml` | Core + Deep + REM sleep records |
| `sleep_with_inbed.xml` | Mix of InBed + Asleep — InBed must be excluded |
| `multi_day_7d.xml` | 7 days all metrics, used for aggregation tests |
| `body_mass_lbs.xml` | unit="lb" records — conversion must yield correct kg |
| `mixed_sources.xml` | Apple Watch + iPhone same day (both included in mean) |
| `truncated.xml` | XML cut mid-element — parser must raise, endpoint returns 422 |
| `large_range_90d.xml` | 90 days, ~500 records — performance + memory test |
| `empty_target_types.xml` | Only HKQuantityTypeIdentifierHeartRate (excluded) — 0 imports |

---

## Security

- `lxml.etree.iterparse(..., resolve_entities=False)` — prevents XXE injection
- No external entity resolution
- File size practical limit: gunicorn 120s timeout + memory-efficient streaming

---

## Feature flag

`.env.example` addition:
```
# --- Apple Health (experimental — not validated on real device) ---
# WARNING: V1 — tested with synthetic fixtures only. Validate on iPhone before enabling in prod.
APPLE_HEALTH_ENABLED=false
```

---

## SDNN vs RMSSD documentation

- **RMSSD** (Terra): Root Mean Square of Successive Differences. Reflects parasympathetic activity. Typical range: 20–80ms. Used by Recovery Coach as primary HRV metric.
- **SDNN** (Apple Health): Standard Deviation of NN intervals. Reflects overall autonomic variability. Typically 30–120ms (always higher than RMSSD for same measurement session).
- **Do not compare absolute values.** Both move in the same direction (fatigue ↓ both, recovery ↑ both) but cannot be substituted in formulas that use absolute thresholds.
- Stored separately in AthleteMetrics. Recovery Coach uses RMSSD when available; falls back to SDNN trend only.

---

## Testing strategy

### Parser unit tests (`test_apple_health_parser.py`)

- Each fixture → expected record count + types
- Truncated XML → `ValueError` or `lxml.etree.XMLSyntaxError` raised
- Sleep values: iOS 15 vs iOS 16 fixture → same `sleep_hours` result
- InBed records excluded from sleep calculation
- Date parsing: timezone-aware, UTC conversion
- `days_back` filter: records older than `since_date` ignored
- `empty_target_types.xml` → 0 records yielded

### Aggregator unit tests

- multi_day_7d → 7 `AppleHealthDailySummary` objects
- sleep spanning midnight (end on next day) → attributed to correct date
- Multiple HRV readings same day → averaged
- body_mass_lbs → value in kg correct (tolerance ±0.01)
- mixed_sources → both readings included in mean

### Importer unit tests (`test_apple_health_importer.py`)

- Upsert: same day re-import updates row, no duplicate
- `AthleteModel.weight_kg` updated when body mass < 7 days old
- `AthleteModel.weight_kg` NOT updated when body mass > 7 days old
- `ConnectorCredentialModel.extra_json` updated with latest values
- Returns correct counts (days_imported, records_processed)

### Endpoint integration tests

- Feature flag disabled → 503
- Valid XML + enabled → 200 + correct response shape
- Truncated XML → 422

---

## Failure modes (resolved)

| Mode | Severity | Resolution |
|------|----------|------------|
| lxml missing from pyproject.toml | Critical | Add before implementation |
| Sleep value is string not float | Critical | Separate parsing path for HKCategory* types |
| SDNN/RMSSD confusion | Critical | Separate fields (hrv_sdnn vs hrv_rmssd) |
| Timezone offset parsing | Minor | `%z` format; tested in fixtures |
| DOCTYPE XXE | Minor | `resolve_entities=False` |
| Files >500MB timeout | Minor | Document as V1 limit; streaming handles memory |

---

## Non-goals (documented)

- No validation on real iPhone data in V1 — `WARNING: NOT VALIDATED ON REAL DEVICE` in endpoint docstring and INTEGRATIONS.md
- No deduplication between Apple Health and Terra for same day (separate fields, no conflict)
- No real-time sync (manual upload only in V1)
