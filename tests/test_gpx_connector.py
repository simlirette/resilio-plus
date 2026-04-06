"""
Tests unitaires GpxConnector.
Parse le XML GPX et insère dans run_activities.
"""

from sqlalchemy import select

from connectors.gpx import GpxConnector
from models.database import RunActivity

# Minimal GPX avec 3 trackpoints — durée = 1200s, élévation = 5m de gain
GPX_SAMPLE = b"""<?xml version="1.0"?>
<gpx xmlns="http://www.topografix.com/GPX/1/1" version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="48.8566" lon="2.3522">
        <ele>30.0</ele>
        <time>2026-04-01T08:00:00Z</time>
      </trkpt>
      <trkpt lat="48.8570" lon="2.3530">
        <ele>32.0</ele>
        <time>2026-04-01T08:10:00Z</time>
      </trkpt>
      <trkpt lat="48.8580" lon="2.3545">
        <ele>35.0</ele>
        <time>2026-04-01T08:20:00Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""


# ── test_parse_gpx_extracts_distance ─────────────────────────────────────────

def test_parse_gpx_extracts_distance():
    connector = GpxConnector()
    result = connector.parse_gpx(GPX_SAMPLE)

    # 3 points in Paris — distance should be ~0.1-0.5 km
    assert result["distance_km"] is not None
    assert 0.05 < result["distance_km"] < 2.0


# ── test_parse_gpx_extracts_duration ─────────────────────────────────────────

def test_parse_gpx_extracts_duration():
    connector = GpxConnector()
    result = connector.parse_gpx(GPX_SAMPLE)

    # 08:20 - 08:00 = 1200 seconds
    assert result["duration_seconds"] == 1200
    assert result["activity_date"].isoformat() == "2026-04-01"


# ── test_ingest_gpx_creates_run_activity ─────────────────────────────────────

async def test_ingest_gpx_creates_run_activity(db_session, simon_athlete):
    connector = GpxConnector()
    run = await connector.ingest_gpx(simon_athlete.id, GPX_SAMPLE, db_session)

    assert run.athlete_id == simon_athlete.id
    assert run.activity_type == "Run"
    assert run.strava_raw == {"source": "gpx"}
    assert run.distance_km is not None
    assert run.duration_seconds == 1200

    # Verify stored in DB
    result = await db_session.execute(
        select(RunActivity).where(RunActivity.id == run.id)
    )
    stored = result.scalar_one()
    assert stored.activity_type == "Run"
