from app.db.models import StravaActivityModel, ConnectorCredentialModel


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
