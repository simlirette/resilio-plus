import io
import os
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from lxml import etree
from sqlalchemy.orm import Session

from ..dependencies import get_current_athlete_id, get_db
from ..integrations.hevy.csv_parser import parse_hevy_csv
from ..integrations.hevy.importer import import_hevy_workouts

router = APIRouter(prefix="/integrations", tags=["integrations"])

DB = Annotated[Session, Depends(get_db)]


@router.post("/hevy/import")
def hevy_csv_import(
    db: DB,
    athlete_id: Annotated[str, Depends(get_current_athlete_id)],
    file: UploadFile = File(...),
    unit: Literal["kg", "lbs"] = Query(default="kg"),
) -> dict[str, Any]:
    """Import Hevy CSV export → parse → upsert to SessionLogModel.

    Matches workouts to active training plan lifting slots by date.
    Falls back to standalone session logs when no plan slot exists.
    """
    content = file.file.read()
    try:
        workouts = parse_hevy_csv(content, unit=unit)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return import_hevy_workouts(athlete_id, workouts, db)


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
            "active_energy_days": sum(
                1 for s in summaries.values() if s.active_energy_kcal is not None
            ),
        },
    }
