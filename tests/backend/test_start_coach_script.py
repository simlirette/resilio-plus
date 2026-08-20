"""Regression guards for the launcher, which broke twice in ways CI cannot see.

`start_coach.ps1` is the first thing an operator runs, and both of its failures
were invisible until execution:

1. Em dashes in a `.ps1` with no BOM. PowerShell 5.1 reads the file as ANSI,
   mangles the multi-byte characters, and reports "the string is missing the
   terminator" pointing at an unrelated line.
2. `$ErrorActionPreference = "Stop"`. Docker writes progress to stderr, which
   PowerShell wraps in an ErrorRecord, so the script aborted on a healthy
   `docker compose up`.

These are cheap to assert and expensive to rediscover.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "start_coach.ps1"


@pytest.fixture(scope="module")
def source() -> str:
    # Deliberately lenient: a non-ASCII byte is its own test's problem, and a
    # strict read here would error out every other check in this module.
    return _SCRIPT.read_text(encoding="ascii", errors="replace")


def test_the_launcher_exists_and_is_tracked() -> None:
    assert _SCRIPT.is_file(), f"{_SCRIPT} is missing"


def test_it_is_pure_ascii() -> None:
    raw = _SCRIPT.read_bytes()
    offenders = [(i, b) for i, b in enumerate(raw) if b > 127]
    assert not offenders, (
        "PowerShell 5.1 reads a BOM-less .ps1 as ANSI; non-ASCII bytes break the "
        f"parser. First offender at byte {offenders[0][0] if offenders else '-'}."
    )


def test_it_does_not_make_stderr_fatal(source: str) -> None:
    assert not re.search(
        r'\$ErrorActionPreference\s*=\s*["\']Stop["\']', source
    ), "docker and alembic write progress to stderr; Stop turns that into a crash"


def test_it_checks_exit_codes_instead(source: str) -> None:
    # Whatever replaces ErrorActionPreference must still notice failures.
    assert source.count("$LASTEXITCODE") >= 4


def test_it_pins_the_ipv4_loopback(source: str) -> None:
    assert "127.0.0.1" in source
    assert "@localhost:" in source, "the localhost rewrite guard is gone"


def test_it_runs_the_preflight_before_starting_the_backend(source: str) -> None:
    preflight = source.index("bootstrap_v4.py --check")
    uvicorn = source.index("uvicorn app.main:app")
    assert preflight < uvicorn, "starting the app before the preflight hides the cause"


def test_it_hands_the_env_file_to_uvicorn(source: str) -> None:
    """Without --env-file the server is blind to everything the preflight saw.

    The preflight reads .env itself, so a launcher that omits this starts a
    backend with no API key, no bot token and no Google settings while every
    check reports green - which is exactly how it failed on 2026-08-20.
    """
    uvicorn_line = next(
        line for line in source.splitlines() if "uvicorn app.main:app" in line
    )
    assert "--env-file" in uvicorn_line


@pytest.mark.skipif(sys.platform != "win32", reason="needs powershell.exe")
def test_powershell_can_parse_it() -> None:
    command = (
        "$errors = $null; "
        "$null = [System.Management.Automation.Language.Parser]::ParseFile("
        f"'{_SCRIPT}', [ref]$null, [ref]$errors); "
        "if ($errors) { $errors | ForEach-Object { $_.Message }; exit 1 }; exit 0"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, f"parse errors:\n{result.stdout}\n{result.stderr}"
