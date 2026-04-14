import io
from pathlib import Path

FIXTURE = (Path(__file__).parents[2] / "fixtures" / "hevy_export_sample.csv").read_bytes()


def test_hevy_csv_import_returns_200(api_client, auth_state):
    resp = api_client.post(
        "/integrations/hevy/import",
        files={"file": ("hevy_export.csv", io.BytesIO(FIXTURE), "text/csv")},
        headers=auth_state["headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_workouts"] == 2
    assert body["matched"] + body["standalone"] == 2
    assert len(body["workouts"]) == 2


def test_hevy_csv_import_response_shape(api_client, auth_state):
    resp = api_client.post(
        "/integrations/hevy/import",
        files={"file": ("hevy_export.csv", io.BytesIO(FIXTURE), "text/csv")},
        headers=auth_state["headers"],
    )
    body = resp.json()
    assert "total_workouts" in body
    assert "matched" in body
    assert "standalone" in body
    assert "skipped" in body
    assert "workouts" in body
    w = body["workouts"][0]
    assert "date" in w
    assert "workout_name" in w
    assert "session_id" in w
    assert "matched" in w
    assert "sets_imported" in w


def test_hevy_csv_import_upsert_no_duplicate(api_client, auth_state):
    """Re-importing same file must not duplicate rows — idempotent."""
    for _ in range(2):
        resp = api_client.post(
            "/integrations/hevy/import",
            files={"file": ("hevy_export.csv", io.BytesIO(FIXTURE), "text/csv")},
            headers=auth_state["headers"],
        )
        assert resp.status_code == 200
    assert resp.json()["total_workouts"] == 2


def test_hevy_csv_import_lbs_unit(api_client, auth_state):
    resp = api_client.post(
        "/integrations/hevy/import?unit=lbs",
        files={"file": ("hevy_export.csv", io.BytesIO(FIXTURE), "text/csv")},
        headers=auth_state["headers"],
    )
    assert resp.status_code == 200


def test_hevy_csv_import_empty_file_returns_422(api_client, auth_state):
    header = b"Date,Workout Name,Exercise Name,Set Order,Weight,Reps,Distance,Seconds,Notes,Workout Notes,RPE\n"
    resp = api_client.post(
        "/integrations/hevy/import",
        files={"file": ("empty.csv", io.BytesIO(header), "text/csv")},
        headers=auth_state["headers"],
    )
    assert resp.status_code == 422


def test_hevy_csv_import_unauthenticated_returns_401(api_client):
    resp = api_client.post(
        "/integrations/hevy/import",
        files={"file": ("hevy_export.csv", io.BytesIO(FIXTURE), "text/csv")},
    )
    assert resp.status_code == 401
