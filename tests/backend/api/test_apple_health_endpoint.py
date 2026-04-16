"""Integration tests for POST /integrations/apple-health/import."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

FIXTURE_DIR = Path(__file__).parents[3] / "tests" / "fixtures" / "apple_health"


class TestFeatureFlag:
    def test_disabled_returns_503(self, api_client: TestClient, auth_state: dict):
        with patch.dict(os.environ, {"APPLE_HEALTH_ENABLED": "false"}):
            with open(FIXTURE_DIR / "minimal_valid.xml", "rb") as f:
                resp = api_client.post(
                    "/integrations/apple-health/import",
                    files={"file": ("export.xml", f, "application/xml")},
                    headers=auth_state["headers"],
                )
        assert resp.status_code == 503
        assert "APPLE_HEALTH_ENABLED" in resp.json()["detail"]

    def test_enabled_returns_200(self, api_client: TestClient, auth_state: dict):
        with patch.dict(os.environ, {"APPLE_HEALTH_ENABLED": "true"}):
            with open(FIXTURE_DIR / "minimal_valid.xml", "rb") as f:
                resp = api_client.post(
                    "/integrations/apple-health/import",
                    files={"file": ("export.xml", f, "application/xml")},
                    headers=auth_state["headers"],
                )
        assert resp.status_code == 200


class TestValidImport:
    def test_response_shape(self, api_client: TestClient, auth_state: dict):
        with patch.dict(os.environ, {"APPLE_HEALTH_ENABLED": "true"}):
            with open(FIXTURE_DIR / "minimal_valid.xml", "rb") as f:
                resp = api_client.post(
                    "/integrations/apple-health/import",
                    files={"file": ("export.xml", f, "application/xml")},
                    headers=auth_state["headers"],
                )
        data = resp.json()
        assert "days_imported" in data
        assert "date_range" in data
        assert "summaries" in data
        assert "weight_updated" in data
        assert "records_processed" in data

    def test_minimal_valid_imports_one_day(self, api_client: TestClient, auth_state: dict):
        with patch.dict(os.environ, {"APPLE_HEALTH_ENABLED": "true"}):
            with open(FIXTURE_DIR / "minimal_valid.xml", "rb") as f:
                resp = api_client.post(
                    "/integrations/apple-health/import",
                    files={"file": ("export.xml", f, "application/xml")},
                    headers=auth_state["headers"],
                )
        assert resp.json()["days_imported"] == 1

    def test_multi_day_imports_seven_days(self, api_client: TestClient, auth_state: dict):
        with patch.dict(os.environ, {"APPLE_HEALTH_ENABLED": "true"}):
            with open(FIXTURE_DIR / "multi_day_7d.xml", "rb") as f:
                resp = api_client.post(
                    "/integrations/apple-health/import",
                    files={"file": ("export.xml", f, "application/xml")},
                    headers=auth_state["headers"],
                )
        assert resp.json()["days_imported"] == 7

    def test_empty_target_types_returns_zero(self, api_client: TestClient, auth_state: dict):
        with patch.dict(os.environ, {"APPLE_HEALTH_ENABLED": "true"}):
            with open(FIXTURE_DIR / "empty_target_types.xml", "rb") as f:
                resp = api_client.post(
                    "/integrations/apple-health/import",
                    files={"file": ("export.xml", f, "application/xml")},
                    headers=auth_state["headers"],
                )
        assert resp.status_code == 200
        assert resp.json()["days_imported"] == 0


class TestErrorCases:
    def test_truncated_xml_returns_422(self, api_client: TestClient, auth_state: dict):
        with patch.dict(os.environ, {"APPLE_HEALTH_ENABLED": "true"}):
            with open(FIXTURE_DIR / "truncated.xml", "rb") as f:
                resp = api_client.post(
                    "/integrations/apple-health/import",
                    files={"file": ("export.xml", f, "application/xml")},
                    headers=auth_state["headers"],
                )
        assert resp.status_code == 422

    def test_unauthenticated_returns_401(self, api_client: TestClient):
        with patch.dict(os.environ, {"APPLE_HEALTH_ENABLED": "true"}):
            with open(FIXTURE_DIR / "minimal_valid.xml", "rb") as f:
                resp = api_client.post(
                    "/integrations/apple-health/import",
                    files={"file": ("export.xml", f, "application/xml")},
                )
        assert resp.status_code == 401
