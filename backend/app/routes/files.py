"""
File upload routes — Hevy CSV and Apple Health XML.

POST /files/hevy-csv          → parse Hevy export, return workouts
POST /files/apple-health-xml  → parse Apple Health export.xml, return summary
"""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..connectors.hevy import parse_hevy_csv
from ..connectors.apple_health import parse_apple_health_xml

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/hevy-csv")
def upload_hevy_csv(file: UploadFile = File(...)) -> dict:
    """
    Upload a Hevy CSV export → parse → return list of workouts.

    Accepts the standard Hevy CSV export (2026 format).
    Weights are converted from lbs to kg automatically.
    """
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Empty file")

    try:
        workouts = parse_hevy_csv(content)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"CSV parse error: {exc}")

    return {
        "parsed": len(workouts),
        "workouts": [w.model_dump(mode="json") for w in workouts],
    }


@router.post("/apple-health-xml")
async def upload_apple_health_xml(file: UploadFile = File(...)) -> dict:
    """
    Upload an Apple Health export.xml → parse in streaming mode → return summary.

    Extracts: HRV (SDNN/RMSSD), sleep hours, resting HR, body weight.
    Streaming parse handles files 500 MB+ without loading into memory.
    """
    try:
        summary = await parse_apple_health_xml(file)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"XML parse error: {exc}")

    return summary
