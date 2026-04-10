from app.connectors.apple_health import AppleHealthConnector, AppleHealthData
import pytest


def test_parse_full_payload():
    connector = AppleHealthConnector()
    data = {
        "snapshot_date": "2026-04-10",
        "hrv_rmssd": 48.5,
        "sleep_hours": 7.2,
        "hr_rest": 52,
    }
    parsed = connector.parse(data)
    assert isinstance(parsed, AppleHealthData)
    assert parsed.hrv_rmssd == 48.5
    assert parsed.sleep_hours == 7.2
    assert parsed.hr_rest == 52
    assert parsed.snapshot_date.isoformat() == "2026-04-10"


def test_parse_partial_payload():
    connector = AppleHealthConnector()
    data = {"snapshot_date": "2026-04-10", "hrv_rmssd": 52.0}
    parsed = connector.parse(data)
    assert parsed.sleep_hours is None
    assert parsed.hr_rest is None


def test_parse_missing_snapshot_date_raises():
    connector = AppleHealthConnector()
    with pytest.raises(ValueError, match="snapshot_date"):
        connector.parse({"hrv_rmssd": 55.0})


def test_to_extra_json():
    connector = AppleHealthConnector()
    data = connector.parse({
        "snapshot_date": "2026-04-10",
        "hrv_rmssd": 55.0,
        "sleep_hours": 8.0,
        "hr_rest": 50,
    })
    extra = connector.to_extra_dict(data)
    assert extra["last_hrv_rmssd"] == 55.0
    assert extra["last_sleep_hours"] == 8.0
    assert extra["last_hr_rest"] == 50
    assert "last_upload" in extra
