"""CLI error paths must never print secrets (OAuth client secrets, Strava tokens)."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import textwrap
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from oauthlib.oauth2.rfc6749.errors import InvalidClientError
from typer.testing import CliRunner

from resilio.cli import app as resilio_app
from resilio.cli.commands import calendar as calendar_commands
from resilio.core.google_calendar import GoogleCalendarAuthError, GoogleCalendarClient
from resilio.schemas.config import GoogleCalendarSettings

REPO_ROOT = Path(__file__).resolve().parents[2]
FAKE_CLIENT_SECRET = "GOCSPX-fakeSecretValue0123456789abcd"
FAKE_STRAVA_REFRESH = "f00dfacecafebabe0123456789abcdef01234567"
SECRET_PATTERNS = [
    re.compile(r"GOCSPX-[A-Za-z0-9_-]{8,}"),
    re.compile(r"\b[0-9a-f]{32,}\b"),
    re.compile(re.escape(FAKE_CLIENT_SECRET[:16])),
    re.compile(re.escape(FAKE_STRAVA_REFRESH[:12])),
]


def _assert_no_secret(text: str) -> None:
    for pattern in SECRET_PATTERNS:
        assert not pattern.search(text), f"secret-looking value leaked: {pattern.pattern}"


@pytest.fixture
def isolated_root(tmp_path, monkeypatch):
    """Work from a tmp repo root (with .git marker), never the real repository."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "credentials.json").write_text(
        json.dumps(
            {
                "installed": {
                    "client_id": "1234-fake.apps.googleusercontent.com",
                    "client_secret": FAKE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost"],
                }
            }
        )
    )
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _fail_token_exchange(monkeypatch) -> None:
    def _raise(self, *args, **kwargs):
        raise InvalidClientError(
            description=f"Unauthorized client_secret={FAKE_CLIENT_SECRET}"
        )

    monkeypatch.setattr(
        "google_auth_oauthlib.flow.InstalledAppFlow.run_local_server", _raise
    )


def test_invalid_client_maps_to_auth_error_without_secret(isolated_root, monkeypatch):
    _fail_token_exchange(monkeypatch)
    client = GoogleCalendarClient(
        isolated_root / "credentials.json", isolated_root / "token.json"
    )

    with pytest.raises(GoogleCalendarAuthError) as excinfo:
        client.authenticate()

    message = str(excinfo.value)
    assert "client secret is invalid" in message
    assert "resilio calendar auth" in message
    _assert_no_secret(message)
    # The library exception (which may carry the secret) is not chained.
    assert excinfo.value.__cause__ is None
    assert excinfo.value.__suppress_context__ is True


def test_calendar_sync_token_exchange_failure_returns_auth_envelope(
    isolated_root, monkeypatch
):
    _fail_token_exchange(monkeypatch)
    start = date.today() + timedelta(days=7)
    plan = SimpleNamespace(
        weeks=[
            SimpleNamespace(
                week_number=1, start_date=start, end_date=start + timedelta(days=6)
            )
        ]
    )
    secrets = SimpleNamespace(
        strava=SimpleNamespace(refresh_token=FAKE_STRAVA_REFRESH)
    )
    monkeypatch.setattr(
        calendar_commands,
        "load_config",
        lambda _root: SimpleNamespace(
            settings=SimpleNamespace(google_calendar=GoogleCalendarSettings()),
            secrets=secrets,
        ),
    )
    monkeypatch.setattr("resilio.api.plan.get_current_plan", lambda: plan)

    result = CliRunner().invoke(resilio_app, ["calendar", "sync"])

    assert result.exit_code != 0
    assert isinstance(result.exception, SystemExit)
    assert "Traceback" not in result.output
    envelope = json.loads(result.stdout)
    assert envelope["ok"] is False
    assert envelope["error_type"] == "auth"
    assert "client secret is invalid" in envelope["message"]
    _assert_no_secret(result.output)


_CRASH_SCRIPT = textwrap.dedent(
    """
    import os
    import sys
    from resilio.cli import app

    if sys.argv[1] == "locals-on":
        app.pretty_exceptions_show_locals = True

    @app.command(name="boom")
    def boom() -> None:
        # Loaded at runtime like real config, so only locals could expose it.
        client_secret = os.environ["FAKE_CLIENT_SECRET"]
        strava_refresh_token = os.environ["FAKE_STRAVA_REFRESH"]
        raise RuntimeError("token exchange failed")

    app(["boom"])
    """
)


def _run_crash(tmp_path: Path, mode: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / ".git").mkdir(exist_ok=True)
    script = tmp_path / "crash.py"
    script.write_text(_CRASH_SCRIPT)
    env = dict(os.environ)
    env.pop("_TYPER_STANDARD_TRACEBACK", None)
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONIOENCODING"] = "utf-8"
    env["COLUMNS"] = "200"
    env["FAKE_CLIENT_SECRET"] = FAKE_CLIENT_SECRET
    env["FAKE_STRAVA_REFRESH"] = FAKE_STRAVA_REFRESH
    return subprocess.run(
        [sys.executable, str(script), mode],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )


def test_resilio_app_disables_traceback_locals():
    assert resilio_app.pretty_exceptions_show_locals is False


def test_unhandled_cli_crash_does_not_print_locals(tmp_path):
    # Control: with locals on, the same crash leaks — proves the check is meaningful.
    leaky = _run_crash(tmp_path, "locals-on")
    assert leaky.returncode != 0
    assert FAKE_CLIENT_SECRET[:16] in leaky.stderr

    result = _run_crash(tmp_path, "default")
    assert result.returncode != 0
    assert "token exchange failed" in result.stderr
    _assert_no_secret(result.stdout + result.stderr)
