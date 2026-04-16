from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
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
) -> dict:
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
