import json
from datetime import date, datetime, timezone

from app.db.models import StravaActivityModel, ConnectorCredentialModel
from app.schemas.connector import StravaActivity
from app.integrations.strava.activity_mapper import SPORT_MAP, to_model


def test_strava_activity_model_has_enc_columns():
    cols = {c.key for c in StravaActivityModel.__table__.columns}
    assert "access_token_enc" not in cols  # belongs to ConnectorCredentialModel
    assert "strava_id" in cols
    assert "sport_type" in cols
    assert "raw_json" in cols


def test_connector_credential_has_enc_columns():
    cols = {c.key for c in ConnectorCredentialModel.__table__.columns}
    assert "access_token_enc" in cols
    assert "refresh_token_enc" in cols
    assert "last_sync_at" in cols
    assert "access_token" not in cols
    assert "refresh_token" not in cols


_ATHLETE_ID = "athlete-123"


def _make_activity(**overrides) -> StravaActivity:
    defaults = dict(
        id="strava_999",
        name="Morning Run",
        sport_type="Run",
        date=date(2026, 4, 10),
        duration_seconds=3600,
        distance_meters=10000.0,
        elevation_gain_meters=150.0,
        average_hr=145,
        max_hr=175,
        avg_watts=None,
        perceived_exertion=7,
    )
    defaults.update(overrides)
    return StravaActivity(**defaults)


def test_run_maps_to_running():
    model = to_model(_make_activity(sport_type="Run"), _ATHLETE_ID)
    assert model.sport_type == "running"


def test_trail_run_maps_to_running():
    model = to_model(_make_activity(sport_type="TrailRun"), _ATHLETE_ID)
    assert model.sport_type == "running"


def test_virtual_ride_maps_to_biking():
    model = to_model(_make_activity(sport_type="VirtualRide"), _ATHLETE_ID)
    assert model.sport_type == "biking"


def test_ride_maps_to_biking():
    model = to_model(_make_activity(sport_type="Ride"), _ATHLETE_ID)
    assert model.sport_type == "biking"


def test_swim_maps_to_swimming():
    model = to_model(_make_activity(sport_type="Swim"), _ATHLETE_ID)
    assert model.sport_type == "swimming"


def test_unknown_sport_type_lowercased():
    model = to_model(_make_activity(sport_type="Yoga"), _ATHLETE_ID)
    assert model.sport_type == "yoga"


def test_strava_id_extracted_from_id_field():
    model = to_model(_make_activity(id="strava_12345"), _ATHLETE_ID)
    assert model.strava_id == 12345


def test_optional_fields_none_when_absent():
    activity = _make_activity(
        distance_meters=None,
        elevation_gain_meters=None,
        average_hr=None,
        max_hr=None,
        avg_watts=None,
        perceived_exertion=None,
    )
    model = to_model(activity, _ATHLETE_ID)
    assert model.distance_m is None
    assert model.elevation_m is None
    assert model.avg_hr is None
    assert model.max_hr is None
    assert model.avg_watts is None
    assert model.perceived_exertion is None


def test_raw_json_stored():
    model = to_model(_make_activity(), _ATHLETE_ID)
    raw = json.loads(model.raw_json)
    assert "sport_type" in raw
    assert raw["name"] == "Morning Run"


def test_model_id_is_strava_prefixed():
    model = to_model(_make_activity(id="strava_999"), _ATHLETE_ID)
    assert model.id == "strava_999"


def test_athlete_id_set_correctly():
    model = to_model(_make_activity(), _ATHLETE_ID)
    assert model.athlete_id == _ATHLETE_ID
