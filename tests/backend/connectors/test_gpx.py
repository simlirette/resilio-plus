import pytest
from app.connectors.gpx import GpxConnector

MINIMAL_GPX = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <trkseg>
      <trkpt lat="48.8566" lon="2.3522">
        <ele>35.0</ele>
        <time>2026-04-10T08:00:00Z</time>
      </trkpt>
      <trkpt lat="48.8600" lon="2.3600">
        <ele>38.0</ele>
        <time>2026-04-10T08:30:00Z</time>
      </trkpt>
      <trkpt lat="48.8650" lon="2.3700">
        <ele>42.0</ele>
        <time>2026-04-10T09:00:00Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""

NO_TIMESTAMP_GPX = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
  <trk><trkseg>
    <trkpt lat="48.8566" lon="2.3522"><ele>35.0</ele></trkpt>
    <trkpt lat="48.8600" lon="2.3600"><ele>38.0</ele></trkpt>
  </trkseg></trk>
</gpx>"""

EMPTY_GPX = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
  <trk><trkseg></trkseg></trk>
</gpx>"""


def test_parse_valid_gpx():
    connector = GpxConnector()
    result = connector.parse(MINIMAL_GPX)
    assert result["activity_date"].isoformat() == "2026-04-10"
    assert result["duration_seconds"] == 3600
    assert result["distance_km"] is not None
    assert result["distance_km"] > 0


def test_parse_gpx_elevation_gain():
    connector = GpxConnector()
    result = connector.parse(MINIMAL_GPX)
    # Elevation: 35 → 38 (+3), 38 → 42 (+4) = 7m gain
    assert result["elevation_gain_m"] == pytest.approx(7.0, abs=0.1)


def test_parse_gpx_no_timestamps_raises():
    connector = GpxConnector()
    with pytest.raises(ValueError, match="timestamps"):
        connector.parse(NO_TIMESTAMP_GPX)


def test_parse_gpx_no_trackpoints_raises():
    connector = GpxConnector()
    with pytest.raises(ValueError, match="trackpoints"):
        connector.parse(EMPTY_GPX)


def test_parse_gpx_avg_pace():
    connector = GpxConnector()
    result = connector.parse(MINIMAL_GPX)
    if result["distance_km"] and result["duration_seconds"]:
        expected_pace = result["duration_seconds"] / result["distance_km"]
        assert result["avg_pace_sec_per_km"] == pytest.approx(expected_pace, rel=0.01)
