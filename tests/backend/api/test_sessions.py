"""Tests for session detail, logging, and history endpoints."""
import json
from datetime import date

PLAN_BODY = {"start_date": "2026-04-13", "end_date": "2026-04-19"}


def _get_first_session_id(authed_client):
    """Helper: generate a plan and return its first session's id."""
    c, athlete_id = authed_client
    resp = c.post(f"/athletes/{athlete_id}/plan", json=PLAN_BODY)
    assert resp.status_code == 201
    sessions = resp.json()["sessions"]
    assert len(sessions) > 0
    return sessions[0]["id"], athlete_id


def test_session_detail_returns_200(authed_client):
    c, athlete_id = authed_client
    session_id, _ = _get_first_session_id((c, athlete_id))
    resp = c.get(f"/athletes/{athlete_id}/sessions/{session_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == session_id
    assert "sport" in body
    assert "duration_min" in body
    assert body["log"] is None  # not yet logged


def test_session_detail_wrong_athlete_returns_403(authed_client):
    c, _ = authed_client
    resp = c.get("/athletes/other-id/sessions/any-id")
    assert resp.status_code == 403


def test_session_detail_unknown_session_returns_404(authed_client):
    c, athlete_id = authed_client
    c.post(f"/athletes/{athlete_id}/plan", json=PLAN_BODY)
    resp = c.get(f"/athletes/{athlete_id}/sessions/nonexistent-session-id")
    assert resp.status_code == 404


def test_post_log_creates_log(authed_client):
    c, athlete_id = authed_client
    session_id, _ = _get_first_session_id((c, athlete_id))
    resp = c.post(
        f"/athletes/{athlete_id}/sessions/{session_id}/log",
        json={"actual_duration_min": 40, "rpe": 7, "notes": "Felt good"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["session_id"] == session_id
    assert body["actual_duration_min"] == 40
    assert body["rpe"] == 7
    assert body["skipped"] is False


def test_post_log_upserts(authed_client):
    """Posting twice updates instead of creating a duplicate."""
    c, athlete_id = authed_client
    session_id, _ = _get_first_session_id((c, athlete_id))
    c.post(f"/athletes/{athlete_id}/sessions/{session_id}/log",
           json={"actual_duration_min": 40, "rpe": 7})
    resp2 = c.post(f"/athletes/{athlete_id}/sessions/{session_id}/log",
                   json={"actual_duration_min": 35, "rpe": 8, "notes": "Updated"})
    assert resp2.status_code == 201
    assert resp2.json()["actual_duration_min"] == 35
    assert resp2.json()["notes"] == "Updated"


def test_post_log_skipped(authed_client):
    c, athlete_id = authed_client
    session_id, _ = _get_first_session_id((c, athlete_id))
    resp = c.post(
        f"/athletes/{athlete_id}/sessions/{session_id}/log",
        json={"skipped": True},
    )
    assert resp.status_code == 201
    assert resp.json()["skipped"] is True


def test_get_log_returns_log(authed_client):
    c, athlete_id = authed_client
    session_id, _ = _get_first_session_id((c, athlete_id))
    c.post(f"/athletes/{athlete_id}/sessions/{session_id}/log",
           json={"actual_duration_min": 40})
    resp = c.get(f"/athletes/{athlete_id}/sessions/{session_id}/log")
    assert resp.status_code == 200
    assert resp.json()["actual_duration_min"] == 40


def test_get_log_not_found_returns_404(authed_client):
    c, athlete_id = authed_client
    c.post(f"/athletes/{athlete_id}/plan", json=PLAN_BODY)
    resp = c.get(f"/athletes/{athlete_id}/sessions/no-log-yet/log")
    assert resp.status_code == 404


def test_session_detail_includes_log_after_logging(authed_client):
    c, athlete_id = authed_client
    session_id, _ = _get_first_session_id((c, athlete_id))
    c.post(f"/athletes/{athlete_id}/sessions/{session_id}/log",
           json={"actual_duration_min": 42, "rpe": 6})
    resp = c.get(f"/athletes/{athlete_id}/sessions/{session_id}")
    assert resp.status_code == 200
    assert resp.json()["log"] is not None
    assert resp.json()["log"]["actual_duration_min"] == 42


def test_history_returns_list(authed_client):
    c, athlete_id = authed_client
    resp = c.get(f"/athletes/{athlete_id}/history")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 1  # onboarding creates 1 plan
    assert body[0]["sessions_total"] > 0


def test_history_shows_logged_count(authed_client):
    c, athlete_id = authed_client
    session_id, _ = _get_first_session_id((c, athlete_id))
    c.post(f"/athletes/{athlete_id}/sessions/{session_id}/log",
           json={"actual_duration_min": 30})
    resp = c.get(f"/athletes/{athlete_id}/history")
    assert resp.status_code == 200
    # At least one week across all plans must show a logged session.
    # (Avoid max() by start_date: onboarding also creates a plan whose start_date
    # may be more recent than PLAN_BODY, so the logged session would be in a
    # different week than "most recent".)
    assert any(w["sessions_logged"] >= 1 for w in resp.json())
