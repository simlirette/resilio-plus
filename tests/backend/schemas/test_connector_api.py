from app.schemas.connector_api import ConnectorStatus, HevyConnectRequest, ConnectorListResponse


def test_connector_status_connected():
    s = ConnectorStatus(provider="strava", connected=True, expires_at=9999999999)
    assert s.provider == "strava"
    assert s.connected is True
    assert s.expires_at == 9999999999


def test_connector_status_api_key_provider_has_no_expiry():
    s = ConnectorStatus(provider="hevy", connected=True, expires_at=None)
    assert s.expires_at is None


def test_hevy_connect_request():
    r = HevyConnectRequest(api_key="abc123")
    assert r.api_key == "abc123"


def test_connector_list_response_empty():
    r = ConnectorListResponse(connectors=[])
    assert r.connectors == []


def test_connector_list_response_with_items():
    r = ConnectorListResponse(connectors=[
        ConnectorStatus(provider="strava", connected=True, expires_at=9999999999),
        ConnectorStatus(provider="hevy", connected=True, expires_at=None),
    ])
    assert len(r.connectors) == 2
