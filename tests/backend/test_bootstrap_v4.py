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
    base.update({field: None for field in bootstrap.JSON_LIST_FIELDS})
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


class TestProviderWiring:
    def _clear(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for name in (
            "STRAVA_CLIENT_ID",
            "STRAVA_ENCRYPTION_KEY",
            "STRAVA_REDIRECT_URI",
            "GOOGLE_CLIENT_ID",
            "GOOGLE_ENCRYPTION_KEY",
            "GOOGLE_REDIRECT_URI",
        ):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000")

    def test_an_unconfigured_provider_is_not_nagged_about(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._clear(monkeypatch)
        assert bootstrap._check_provider_pairs() == []

    def test_a_client_id_without_its_key_or_redirect_blocks(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._clear(monkeypatch)
        monkeypatch.setenv("STRAVA_CLIENT_ID", "12345")

        problems = bootstrap._check_provider_pairs()

        assert set(problems) == {"STRAVA_ENCRYPTION_KEY", "STRAVA_REDIRECT_URI"}
        out = capsys.readouterr().out
        assert "/integrations/link/callback/strava" in out

    def test_a_fully_wired_provider_passes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._clear(monkeypatch)
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "abc.apps.googleusercontent.com")
        monkeypatch.setenv("GOOGLE_ENCRYPTION_KEY", "a-key")
        monkeypatch.setenv(
            "GOOGLE_REDIRECT_URI",
            "http://127.0.0.1:8000/integrations/link/callback/google",
        )

        assert bootstrap._check_provider_pairs() == []

    def test_a_redirect_pointing_somewhere_else_warns_without_blocking(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._clear(monkeypatch)
        monkeypatch.setenv("STRAVA_CLIENT_ID", "12345")
        monkeypatch.setenv("STRAVA_ENCRYPTION_KEY", "a-key")
        monkeypatch.setenv(
            "STRAVA_REDIRECT_URI", "http://localhost:8000/auth/strava/callback"
        )

        problems = bootstrap._check_provider_pairs()

        assert problems == []
        assert "warn" in capsys.readouterr().out

    def test_the_expected_redirect_follows_the_public_base(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._clear(monkeypatch)
        monkeypatch.setenv("PUBLIC_BASE_URL", "https://coach.example.com/")
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "abc")

        bootstrap._check_provider_pairs()

        assert (
            "https://coach.example.com/integrations/link/callback/google"
            in capsys.readouterr().out
        )


class TestSelectiveKeys:
    def test_a_single_name_mints_only_that_key(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.delenv("GOOGLE_ENCRYPTION_KEY", raising=False)

        assert bootstrap.print_keys(["GOOGLE_ENCRYPTION_KEY"]) == 0

        out = capsys.readouterr().out
        assert "GOOGLE_ENCRYPTION_KEY=" in out
        assert "JWT_SECRET=" not in out
        assert "STRAVA_ENCRYPTION_KEY=" not in out

    def test_no_names_mints_all_of_them(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        for name in (
            "JWT_SECRET",
            "STRAVA_ENCRYPTION_KEY",
            "GOOGLE_ENCRYPTION_KEY",
            "TELEGRAM_WEBHOOK_SECRET",
        ):
            monkeypatch.delenv(name, raising=False)

        assert bootstrap.print_keys(None) == 0

        out = capsys.readouterr().out
        assert out.count("=") >= 4

    def test_an_unknown_name_is_refused(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert bootstrap.print_keys(["NOPE"]) == 1
        assert "Unknown key name" in capsys.readouterr().out

    def test_overwriting_a_key_already_in_use_is_flagged(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("STRAVA_ENCRYPTION_KEY", "already-in-use")

        bootstrap.print_keys(["STRAVA_ENCRYPTION_KEY"])

        out = capsys.readouterr().out
        assert "WARNING" in out
        assert "unreadable" in out

    def test_a_fresh_key_carries_no_warning(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.delenv("GOOGLE_ENCRYPTION_KEY", raising=False)

        bootstrap.print_keys(["GOOGLE_ENCRYPTION_KEY"])

        assert "WARNING" not in capsys.readouterr().out


class TestVerifyTelegram:
    def test_missing_token_is_reported(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

        assert bootstrap.verify_telegram() == 1
        assert "MISSING" in capsys.readouterr().out

    def test_a_placeholder_counts_as_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "CHANGEME")
        assert bootstrap.verify_telegram() == 1

    def test_a_working_token_names_the_bot(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        import httpx
        import respx

        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
        with respx.mock(base_url="https://api.telegram.org") as mock:
            mock.get("/bot123:abc/getMe").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "ok": True,
                        "result": {"username": "resilioplusbot", "first_name": "resilio+"},
                    },
                )
            )
            assert bootstrap.verify_telegram() == 0

        out = capsys.readouterr().out
        assert "@resilioplusbot" in out
        assert "t.me/resilioplusbot" in out

    def test_a_rejected_token_says_so(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        import httpx
        import respx

        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:bad")
        with respx.mock(base_url="https://api.telegram.org") as mock:
            mock.get("/bot123:bad/getMe").mock(return_value=httpx.Response(401))
            assert bootstrap.verify_telegram() == 1

        assert "rejected the token" in capsys.readouterr().out

    def test_the_token_is_never_printed(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        import httpx
        import respx

        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:super-secret")
        with respx.mock(base_url="https://api.telegram.org") as mock:
            mock.get("/bot123:super-secret/getMe").mock(
                return_value=httpx.Response(
                    200, json={"ok": True, "result": {"username": "b", "first_name": "b"}}
                )
            )
            bootstrap.verify_telegram()

        assert "super-secret" not in capsys.readouterr().out


class TestVerifyGoogle:
    def _clear(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for name in bootstrap.GOOGLE_VARS:
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000")

    def test_unconfigured_lists_every_missing_variable(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._clear(monkeypatch)

        assert bootstrap.verify_google() == 1

        out = capsys.readouterr().out
        for name in bootstrap.GOOGLE_VARS:
            assert name in out
        assert "/integrations/link/callback/google" in out

    def test_it_names_the_exact_redirect_to_register(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._clear(monkeypatch)
        monkeypatch.setenv("PUBLIC_BASE_URL", "https://coach.example.com")

        bootstrap.verify_google()

        assert (
            "https://coach.example.com/integrations/link/callback/google"
            in capsys.readouterr().out
        )

    def test_configured_but_unauthorised_hands_over_the_consent_url(
        self,
        sqlite_db: Any,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from cryptography.fernet import Fernet

        self._clear(monkeypatch)
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "abc.apps.googleusercontent.com")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "shh")
        monkeypatch.setenv("GOOGLE_ENCRYPTION_KEY", Fernet.generate_key().decode())
        monkeypatch.setenv(
            "GOOGLE_REDIRECT_URI",
            "http://127.0.0.1:8000/integrations/link/callback/google",
        )
        bootstrap.ensure_athlete(_args(name="Simon"))

        assert bootstrap.verify_google() == 1

        out = capsys.readouterr().out
        assert "accounts.google.com" in out
        assert "calendar.app.created" in out
        assert "ON THIS MACHINE" in out

    def test_no_athlete_is_reported_before_anything_else(
        self, sqlite_db: Any, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from cryptography.fernet import Fernet

        self._clear(monkeypatch)
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "abc")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "shh")
        monkeypatch.setenv("GOOGLE_ENCRYPTION_KEY", Fernet.generate_key().decode())
        monkeypatch.setenv(
            "GOOGLE_REDIRECT_URI",
            "http://127.0.0.1:8000/integrations/link/callback/google",
        )

        assert bootstrap.verify_google() == 1
        assert "No athlete yet" in capsys.readouterr().out


class TestAdminAthleteId:
    def test_it_appears_in_the_report(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("ADMIN_ATHLETE_ID", "1a2d73d5-0000-0000-0000-000000000000")

        bootstrap.check_config()

        assert "ADMIN_ATHLETE_ID" in capsys.readouterr().out

    def test_its_value_is_shown_because_it_is_not_a_secret(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("ADMIN_ATHLETE_ID", "1a2d73d5-0000-0000-0000-000000000000")

        bootstrap.check_config()

        assert "-> 1a2d73d5-0000-0000-0000-000000000000" in capsys.readouterr().out

    def test_unset_explains_what_it_is_instead_of_blocking(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.delenv("ADMIN_ATHLETE_ID", raising=False)

        blockers = bootstrap.check_config()

        out = capsys.readouterr().out
        assert "ADMIN_ATHLETE_ID is unset" in out
        assert "athlete's id" in out
        assert "ADMIN_ATHLETE_ID" not in blockers

    def test_no_hint_once_it_is_set(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("ADMIN_ATHLETE_ID", "any-value")

        bootstrap.check_config()

        assert "is unset" not in capsys.readouterr().out


class TestFernetKeyValidation:
    """A key of the wrong shape passes every other check and fails at use.

    Seen live on 2026-08-20: a 19-character passphrase in GOOGLE_ENCRYPTION_KEY
    survived the whole OAuth round trip and then 500'd while storing the token,
    with the authorization code already spent.
    """

    def test_a_passphrase_is_rejected(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("GOOGLE_ENCRYPTION_KEY", "my-secret-key-1234")
        monkeypatch.delenv("STRAVA_ENCRYPTION_KEY", raising=False)

        problems = bootstrap._check_fernet_keys()

        assert problems == ["GOOGLE_ENCRYPTION_KEY"]
        out = capsys.readouterr().out
        assert "not a valid Fernet key" in out
        assert "44" in out

    def test_a_real_key_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from cryptography.fernet import Fernet

        monkeypatch.setenv("GOOGLE_ENCRYPTION_KEY", Fernet.generate_key().decode())
        monkeypatch.setenv("STRAVA_ENCRYPTION_KEY", Fernet.generate_key().decode())

        assert bootstrap._check_fernet_keys() == []

    def test_an_unset_key_is_not_a_shape_problem(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for name in bootstrap.FERNET_KEYS:
            monkeypatch.delenv(name, raising=False)

        assert bootstrap._check_fernet_keys() == []

    def test_both_keys_are_checked(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GOOGLE_ENCRYPTION_KEY", "too-short")
        monkeypatch.setenv("STRAVA_ENCRYPTION_KEY", "also-too-short")

        assert set(bootstrap._check_fernet_keys()) == set(bootstrap.FERNET_KEYS)

    def test_a_hex_secret_is_rejected(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # token_hex(32) is 64 chars - a plausible mistake, still not Fernet.
        monkeypatch.setenv("GOOGLE_ENCRYPTION_KEY", "a" * 64)
        monkeypatch.delenv("STRAVA_ENCRYPTION_KEY", raising=False)

        assert bootstrap._check_fernet_keys() == ["GOOGLE_ENCRYPTION_KEY"]

    def test_it_blocks_the_overall_check(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GOOGLE_ENCRYPTION_KEY", "nope")

        assert "GOOGLE_ENCRYPTION_KEY" in bootstrap.check_config()


class TestMissingBase64Padding:
    """The trailing '=' is the easiest character to lose when copying a key.

    Seen live on 2026-08-20: a correct key pasted 43 characters long. The
    generic "not a valid Fernet key" message sent the operator off to
    regenerate a key that was already right.
    """

    def _valid(self) -> str:
        from cryptography.fernet import Fernet

        return Fernet.generate_key().decode()

    def test_a_key_missing_only_its_padding_says_exactly_that(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.delenv("STRAVA_ENCRYPTION_KEY", raising=False)
        truncated = self._valid().rstrip("=")
        monkeypatch.setenv("GOOGLE_ENCRYPTION_KEY", truncated)

        problems = bootstrap._check_fernet_keys()

        assert problems == ["GOOGLE_ENCRYPTION_KEY"]
        out = capsys.readouterr().out
        assert "missing its trailing '='" in out
        assert "Add a single '='" in out
        assert "not a passphrase" not in out

    def test_a_genuinely_wrong_key_still_gets_the_general_advice(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.delenv("STRAVA_ENCRYPTION_KEY", raising=False)
        monkeypatch.setenv("GOOGLE_ENCRYPTION_KEY", "my-passphrase")

        bootstrap._check_fernet_keys()

        out = capsys.readouterr().out
        assert "not a passphrase" in out
        assert "missing its trailing" not in out

    def test_the_padded_key_itself_passes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("STRAVA_ENCRYPTION_KEY", raising=False)
        monkeypatch.setenv("GOOGLE_ENCRYPTION_KEY", self._valid())

        assert bootstrap._check_fernet_keys() == []

    def test_accepts_fernet_helper_is_honest(self) -> None:
        assert bootstrap._accepts_fernet(self._valid()) is True
        assert bootstrap._accepts_fernet("nope") is False
        assert bootstrap._accepts_fernet("") is False


class TestSportsGoalsAndRaceDate:
    """These three drive the plan, so the setup script has to be able to set them.

    Without a race date the periodization phase is always general_prep; with one
    30 days out it is competition. Without goals, analyze_goals has nothing to
    allocate sport budgets from.
    """

    def test_multiple_sports_are_stored(self, sqlite_db: Any) -> None:
        from app.db.models import AthleteModel

        athlete_id, _, profile = bootstrap.ensure_athlete(
            _args(name="Simon", primary_sport="running", sports=["running", "lifting"])
        )

        assert profile["sports"] == ["running", "lifting"]
        with sqlite_db.SessionLocal() as db:
            row = db.get(AthleteModel, athlete_id)
            assert row is not None
            assert row.sports_json == '["running", "lifting"]'

    def test_goals_are_stored(self, sqlite_db: Any) -> None:
        _id, _action, profile = bootstrap.ensure_athlete(
            _args(name="Simon", goals=["half marathon Usti nad Labem"])
        )

        assert profile["goals"] == ["half marathon Usti nad Labem"]

    def test_race_date_is_stored(self, sqlite_db: Any) -> None:
        from datetime import date

        _id, _action, profile = bootstrap.ensure_athlete(
            _args(name="Simon", target_race_date=date(2026, 9, 19))
        )

        assert profile["target_race_date"] == date(2026, 9, 19)

    def test_explicit_sports_beat_the_primary_sport_default(
        self, sqlite_db: Any
    ) -> None:
        _id, _action, profile = bootstrap.ensure_athlete(
            _args(name="Simon", primary_sport="running", sports=["running", "lifting"])
        )
        assert profile["sports"] == ["running", "lifting"]

    def test_changing_only_the_primary_sport_still_syncs_the_list(
        self, sqlite_db: Any
    ) -> None:
        bootstrap.ensure_athlete(_args(name="Simon", sports=["running", "lifting"]))

        _id, _action, profile = bootstrap.ensure_athlete(
            _args(primary_sport="swimming")
        )

        assert profile["sports"] == ["swimming"]

    def test_an_update_preserves_lists_it_was_not_given(
        self, sqlite_db: Any
    ) -> None:
        bootstrap.ensure_athlete(
            _args(name="Simon", sports=["running", "lifting"], goals=["half"])
        )

        _id, _action, profile = bootstrap.ensure_athlete(_args(age=24))

        assert profile["sports"] == ["running", "lifting"]
        assert profile["goals"] == ["half"]
        assert profile["age"] == 24

    def test_the_race_date_parser_rejects_junk(self) -> None:
        import argparse as _argparse

        with pytest.raises(_argparse.ArgumentTypeError):
            bootstrap._parse_race_date("19 septembre")

    def test_the_race_date_parser_accepts_iso(self) -> None:
        from datetime import date

        assert bootstrap._parse_race_date("2026-09-19") == date(2026, 9, 19)
