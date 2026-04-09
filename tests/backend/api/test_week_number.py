from datetime import date, timedelta


def _plan_payload(offset_weeks: int = 0):
    start = date.today() + timedelta(weeks=offset_weeks)
    return {"start_date": str(start), "end_date": str(start + timedelta(days=6))}


def test_first_plan_has_week_number_1(authed_client):
    c, athlete_id = authed_client
    # onboarding already created plan #1; get week-status to check week_number
    resp = c.get(f"/athletes/{athlete_id}/week-status")
    assert resp.status_code == 200
    assert resp.json()["week_number"] == 1


def test_second_plan_increments_week_number(authed_client):
    c, athlete_id = authed_client
    # Create a second plan
    resp2 = c.post(f"/athletes/{athlete_id}/plan", json=_plan_payload(offset_weeks=1))
    assert resp2.status_code == 201
    # week-status should now show week_number = 2
    resp = c.get(f"/athletes/{athlete_id}/week-status")
    assert resp.status_code == 200
    assert resp.json()["week_number"] == 2


def test_third_plan_has_week_number_3(authed_client):
    c, athlete_id = authed_client
    c.post(f"/athletes/{athlete_id}/plan", json=_plan_payload(offset_weeks=1))
    c.post(f"/athletes/{athlete_id}/plan", json=_plan_payload(offset_weeks=2))
    resp = c.get(f"/athletes/{athlete_id}/week-status")
    assert resp.status_code == 200
    assert resp.json()["week_number"] == 3
