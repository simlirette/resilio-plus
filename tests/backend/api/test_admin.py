import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models as _models  # noqa: F401
from app.jobs import models as _job_models  # noqa: F401
from app.jobs.models import JobRunModel


def test_admin_jobs_returns_200_for_admin(api_client, auth_state, monkeypatch):
    monkeypatch.setenv("ADMIN_ATHLETE_ID", auth_state["athlete_id"])
    resp = api_client.get("/admin/jobs", headers=auth_state["headers"])
    assert resp.status_code == 200
    body = resp.json()
    assert "jobs" in body
    assert "summary" in body
    assert isinstance(body["jobs"], list)
    assert "total_jobs" in body["summary"]
    assert "errors_24h" in body["summary"]


def test_admin_jobs_returns_403_for_non_admin(api_client, auth_state, monkeypatch):
    monkeypatch.setenv("ADMIN_ATHLETE_ID", str(uuid.uuid4()))
    resp = api_client.get("/admin/jobs", headers=auth_state["headers"])
    assert resp.status_code == 403


def test_admin_jobs_returns_401_unauthenticated(api_client):
    resp = api_client.get("/admin/jobs")
    assert resp.status_code == 401
