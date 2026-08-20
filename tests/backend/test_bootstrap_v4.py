"""The first-run script is the only path to a usable install — pin its behaviour.

Getting this wrong is invisible until someone's real profile is silently
replaced by a leftover seed row, or a link code is minted for the wrong athlete.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "bootstrap_v4.py"


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location("bootstrap_v4", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["bootstrap_v4"] = module
    spec.loader.exec_module(module)
    return module


bootstrap = _load_module()


@pytest.fixture
def sqlite_db(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Point the script's lazy `app.db` imports at a throwaway SQLite file."""
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker

    import app.db.database as database
    from app.db import models  # noqa: F401 — registers ORM models

    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection: Any, _record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    database.Base.metadata.create_all(engine)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(engine))
    return database


def _args(**overrides: Any) -> argparse.Namespace:
    base: dict[str, Any] = {field: None for field in bootstrap.PROFILE_FIELDS}
    base["new"] = False
    base.update(overrides)
    return argparse.Namespace(**base)


class TestConfigReport:
    def test_placeholder_values_count_as_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("JWT_SECRET", "CHANGEME-run-openssl")
        assert bootstrap._is_set("JWT_SECRET") is False

    def test_blank_counts_as_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JWT_SECRET", "   ")
        assert bootstrap._is_set("JWT_SECRET") is False

    def test_a_real_value_counts_as_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JWT_SECRET", "0a1b2c3d")
        assert bootstrap._is_set("JWT_SECRET") is True

    def test_required_gaps_are_reported_as_blockers(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        for name, _required in (e for group in bootstrap.GROUPS.values() for e in group):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)

        blockers = bootstrap.check_config()

        assert "TELEGRAM_BOT_TOKEN" in blockers
        assert "ANTHROPIC_API_KEY" in blockers
        assert "GOOGLE_CLIENT_ID" not in blockers  # optional
        assert "MISSING" in capsys.readouterr().out

    def test_webhook_mode_demands_a_shared_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TELEGRAM_MODE", "webhook")
        monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)

        assert "TELEGRAM_WEBHOOK_SECRET" in bootstrap.check_config()

    def test_polling_mode_does_not(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TELEGRAM_MODE", "polling")
        monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)

        assert "TELEGRAM_WEBHOOK_SECRET" not in bootstrap.check_config()

    def test_the_report_never_prints_a_secret_value(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "1234:super-secret-token")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-do-not-print-me")

        bootstrap.check_config()

        out = capsys.readouterr().out
        assert "super-secret-token" not in out
        assert "sk-ant-do-not-print-me" not in out


class TestEnsureAthlete:
    def test_creates_one_with_the_supplied_profile(self, sqlite_db: Any) -> None:
        athlete_id, action, profile = bootstrap.ensure_athlete(
            _args(name="Simon", age=34, sex="M", weight_kg=75.0)
        )

        assert action == "created"
        assert profile["name"] == "Simon"
        assert profile["age"] == 34
        from app.db.models import AthleteModel

        with sqlite_db.SessionLocal() as db:
            row = db.get(AthleteModel, athlete_id)
            assert row is not None
            assert row.journey_phase == "signup"
            assert row.sports_json == '["running"]'

    def test_defaults_fill_the_gaps(self, sqlite_db: Any) -> None:
        _id, _action, profile = bootstrap.ensure_athlete(_args(name="Simon"))

        assert profile["timezone"] == "America/Montreal"
        assert profile["weekly_cycle_day"] == 6
        assert profile["weekly_cycle_hour"] == 18

    def test_a_leftover_row_is_updated_not_silently_adopted(
        self, sqlite_db: Any
    ) -> None:
        from app.db.models import AthleteModel

        with sqlite_db.SessionLocal() as db:
            db.add(
                AthleteModel(
                    id="seed-row",
                    name="Test User",
                    age=30,
                    sex="M",
                    weight_kg=70.0,
                    height_cm=175.0,
                    primary_sport="running",
                    hours_per_week=6.0,
                    sports_json='["running"]',
                    goals_json="[]",
                    available_days_json="[]",
                    equipment_json="[]",
                )
            )
            db.commit()

        athlete_id, action, profile = bootstrap.ensure_athlete(
            _args(name="Simon", age=34, weight_kg=75.0)
        )

        assert athlete_id == "seed-row"
        assert action == "updated"
        assert profile["name"] == "Simon"
        assert profile["age"] == 34
        assert profile["height_cm"] == 175.0  # untouched — not supplied

    def test_reuse_without_flags_is_called_out(self, sqlite_db: Any) -> None:
        bootstrap.ensure_athlete(_args(name="Simon"))

        _id, action, profile = bootstrap.ensure_athlete(_args())

        assert action == "reused unchanged"
        assert profile["name"] == "Simon"

    def test_new_forces_a_second_athlete(self, sqlite_db: Any) -> None:
        first, _, _ = bootstrap.ensure_athlete(_args(name="Simon"))
        second, action, _ = bootstrap.ensure_athlete(_args(name="Other", new=True))

        assert action == "created"
        assert second != first

    def test_changing_the_primary_sport_rewrites_the_sports_list(
        self, sqlite_db: Any
    ) -> None:
        athlete_id, _, _ = bootstrap.ensure_athlete(_args(name="Simon"))
        bootstrap.ensure_athlete(_args(primary_sport="swimming"))

        from app.db.models import AthleteModel

        with sqlite_db.SessionLocal() as db:
            row = db.get(AthleteModel, athlete_id)
            assert row is not None
            assert row.sports_json == '["swimming"]'


class TestLinkCode:
    def test_mints_a_single_use_code_for_the_athlete(self, sqlite_db: Any) -> None:
        athlete_id, _, _ = bootstrap.ensure_athlete(_args(name="Simon"))

        code = bootstrap.mint_link_code(athlete_id, hours=24)

        from app.db.models import MessagingLinkCodeModel

        with sqlite_db.SessionLocal() as db:
            row = db.get(MessagingLinkCodeModel, code)
            assert row is not None
            assert row.athlete_id == athlete_id
            assert row.consumed_at is None
            expires = row.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            assert expires > datetime.now(timezone.utc)

    def test_every_run_mints_a_fresh_code(self, sqlite_db: Any) -> None:
        athlete_id, _, _ = bootstrap.ensure_athlete(_args(name="Simon"))

        codes = {bootstrap.mint_link_code(athlete_id, hours=1) for _ in range(5)}

        assert len(codes) == 5

    def test_an_already_linked_chat_is_reported(self, sqlite_db: Any) -> None:
        import uuid

        from app.db.models import MessagingIdentityModel

        athlete_id, _, _ = bootstrap.ensure_athlete(_args(name="Simon"))
        assert bootstrap.existing_identity(athlete_id) is None

        with sqlite_db.SessionLocal() as db:
            db.add(
                MessagingIdentityModel(
                    id=str(uuid.uuid4()),
                    athlete_id=athlete_id,
                    channel="telegram",
                    external_id="9001",
                )
            )
            db.commit()

        assert bootstrap.existing_identity(athlete_id) == "9001"


class TestKeys:
    def test_generated_secrets_are_distinct_and_usable(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from cryptography.fernet import Fernet

        bootstrap.print_keys()
        lines = [
            line for line in capsys.readouterr().out.splitlines() if "=" in line
        ]
        values = {line.split("=", 1)[0]: line.split("=", 1)[1] for line in lines}

        assert set(values) == {
            "JWT_SECRET",
            "STRAVA_ENCRYPTION_KEY",
            "GOOGLE_ENCRYPTION_KEY",
            "TELEGRAM_WEBHOOK_SECRET",
        }
        assert len(set(values.values())) == 4
        # The Fernet keys must actually be Fernet keys.
        for name in ("STRAVA_ENCRYPTION_KEY", "GOOGLE_ENCRYPTION_KEY"):
            Fernet(values[name].encode())
