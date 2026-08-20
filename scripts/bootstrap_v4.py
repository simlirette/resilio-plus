#!/usr/bin/env python3
"""First-run setup for the V4 text coach.

The bot never auto-creates an athlete — that is a deliberate safety property,
but it means a fresh install has nothing for a Telegram chat to link to. This
script closes that gap: it checks the configuration, creates the athlete, and
mints the link code you send to the bot as your first message.

Safe to re-run: it reuses the existing athlete unless you pass ``--new``, and
every run mints a fresh link code.

    python scripts/bootstrap_v4.py --check
    python scripts/bootstrap_v4.py --keys
    python scripts/bootstrap_v4.py --name "Simon" --age 34 --sex M \\
        --weight-kg 75 --height-cm 180 --primary-sport running \\
        --hours-per-week 8 --timezone America/Montreal

Never prints a secret's value — only whether it is set.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "backend"))

EXIT_OK = 0
EXIT_BLOCKED = 1

OK = "  ok  "
MISSING = "MISSING"
OPTIONAL = " skip "

SPORTS = ("running", "lifting", "swimming", "biking")


# ─── Configuration ────────────────────────────────────────────────────────────


def _is_set(name: str) -> bool:
    value = os.getenv(name, "").strip()
    return bool(value) and not value.upper().startswith("CHANGEME")


def _load_dotenv() -> None:
    """Read .env into the process without printing any of it."""
    path = _REPO_ROOT / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


GROUPS: dict[str, tuple[tuple[str, bool], ...]] = {
    "Core (the app will not work without these)": (
        ("DATABASE_URL", True),
        ("ANTHROPIC_API_KEY", True),
        ("JWT_SECRET", True),
    ),
    "Telegram (the coach cannot reach you without these)": (
        ("TELEGRAM_BOT_TOKEN", True),
        ("TELEGRAM_MODE", False),
        ("PUBLIC_BASE_URL", False),
    ),
    "Google Calendar (approve writes nothing without these)": (
        ("GOOGLE_CLIENT_ID", False),
        ("GOOGLE_CLIENT_SECRET", False),
        ("GOOGLE_ENCRYPTION_KEY", False),
        ("GOOGLE_REDIRECT_URI", False),
    ),
    "Strava (optional — activities can also arrive via Hevy/Terra)": (
        ("STRAVA_CLIENT_ID", False),
        ("STRAVA_CLIENT_SECRET", False),
        ("STRAVA_ENCRYPTION_KEY", False),
        ("STRAVA_REDIRECT_URI", False),
    ),
}


def check_config() -> list[str]:
    """Print a config report; return the names of missing required settings."""
    blockers: list[str] = []
    print("Configuration")
    print("=" * 62)
    for group, entries in GROUPS.items():
        print(f"\n{group}")
        for name, required in entries:
            if _is_set(name):
                mark = OK
            elif required:
                mark = MISSING
                blockers.append(name)
            else:
                mark = OPTIONAL
            shown = ""
            if name in ("PUBLIC_BASE_URL", "TELEGRAM_MODE") and _is_set(name):
                shown = f"  → {os.environ[name]}"
            print(f"  [{mark}] {name}{shown}")

    mode = os.getenv("TELEGRAM_MODE", "polling").strip() or "polling"
    if mode == "webhook" and not _is_set("TELEGRAM_WEBHOOK_SECRET"):
        print("\n  [MISSING] TELEGRAM_WEBHOOK_SECRET (required in webhook mode)")
        blockers.append("TELEGRAM_WEBHOOK_SECRET")

    blockers.extend(_check_provider_pairs())
    return blockers


def _check_provider_pairs() -> list[str]:
    """Catch half-configured providers, which fail only at the OAuth bounce."""
    base = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    problems: list[str] = []
    notes: list[str] = []

    for provider, id_var, key_var, redirect_var in (
        ("Strava", "STRAVA_CLIENT_ID", "STRAVA_ENCRYPTION_KEY", "STRAVA_REDIRECT_URI"),
        ("Google", "GOOGLE_CLIENT_ID", "GOOGLE_ENCRYPTION_KEY", "GOOGLE_REDIRECT_URI"),
    ):
        if not _is_set(id_var):
            continue
        expected = f"{base}/integrations/link/callback/{provider.lower()}"
        if not _is_set(key_var):
            problems.append(key_var)
            notes.append(
                f"  [MISSING] {key_var} — {provider} is configured but its tokens "
                "have nowhere safe to live."
            )
        if not _is_set(redirect_var):
            problems.append(redirect_var)
            notes.append(
                f"  [MISSING] {redirect_var} — without it the OAuth callback "
                f"falls back to a route that no longer exists. Set:\n"
                f"            {redirect_var}={expected}"
            )
        elif os.environ[redirect_var].rstrip("/") != expected:
            notes.append(
                f"  [ warn ] {redirect_var} is not {expected}\n"
                f"            It must match the provider console exactly, and land "
                "on a route that exists."
            )

    if notes:
        print("\nProvider wiring")
        for note in notes:
            print(note)
    return problems


def print_keys() -> None:
    """Print freshly generated secrets for the operator to paste in."""
    from cryptography.fernet import Fernet

    print("Generated secrets — paste into .env, then never regenerate them:")
    print()
    print(f"JWT_SECRET={secrets.token_hex(32)}")
    print(f"STRAVA_ENCRYPTION_KEY={Fernet.generate_key().decode()}")
    print(f"GOOGLE_ENCRYPTION_KEY={Fernet.generate_key().decode()}")
    print(f"TELEGRAM_WEBHOOK_SECRET={secrets.token_urlsafe(32)}")
    print()
    print("Rotating an encryption key makes the tokens stored under it unreadable.")


# ─── Database ─────────────────────────────────────────────────────────────────


def check_database() -> bool:
    from sqlalchemy import text

    from app.db.database import SessionLocal

    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception as exc:
        print(f"\n[MISSING] Database unreachable: {type(exc).__name__}")
        print("          Start it with:  docker compose up -d db")
        print("          If it is already running, try 127.0.0.1 instead of")
        print("          localhost in DATABASE_URL — on Windows, WSL can own")
        print("          [::1]:5432 and localhost resolves there first.")
        print("          Then migrate:   alembic upgrade head")
        return False
    return True


def tables_ready() -> bool:
    from sqlalchemy import inspect

    from app.db.database import engine

    names = set(inspect(engine).get_table_names())
    needed = {"athletes", "messaging_identities", "messaging_link_codes"}
    missing = needed - names
    if missing:
        print(f"\n[MISSING] Tables not created: {', '.join(sorted(missing))}")
        print("          Run:  alembic upgrade head")
        return False
    return True


PROFILE_FIELDS = (
    "name",
    "age",
    "sex",
    "weight_kg",
    "height_cm",
    "primary_sport",
    "hours_per_week",
    "timezone",
    "weekly_cycle_day",
    "weekly_cycle_hour",
)

PROFILE_DEFAULTS: dict[str, object] = {
    "name": "Athlete",
    "age": 30,
    "sex": "other",
    "weight_kg": 70.0,
    "height_cm": 175.0,
    "primary_sport": "running",
    "hours_per_week": 6.0,
    "timezone": "America/Montreal",
    "weekly_cycle_day": 6,
    "weekly_cycle_hour": 18,
}


def _supplied(args: argparse.Namespace) -> dict[str, object]:
    """Only the profile fields the operator actually passed."""
    return {
        field: getattr(args, field)
        for field in PROFILE_FIELDS
        if getattr(args, field) is not None
    }


def ensure_athlete(args: argparse.Namespace) -> tuple[str, str, dict[str, object]]:
    """Return (athlete_id, action, profile).

    Reuses the single existing athlete by default and applies whatever profile
    fields were passed, so a leftover seed row cannot silently become the
    athlete the coach plans for. ``--new`` always creates a fresh one.
    """
    from app.db.database import SessionLocal
    from app.db.models import AthleteModel

    supplied = _supplied(args)

    with SessionLocal() as db:
        if not args.new:
            existing = db.query(AthleteModel).order_by(AthleteModel.id).first()
            if existing is not None:
                for field, value in supplied.items():
                    setattr(existing, field, value)
                if "primary_sport" in supplied:
                    existing.sports_json = json.dumps([supplied["primary_sport"]])
                db.commit()
                action = "updated" if supplied else "reused unchanged"
                profile = {f: getattr(existing, f) for f in PROFILE_FIELDS}
                return existing.id, action, profile

        values: dict[str, object] = {**PROFILE_DEFAULTS, **supplied}
        athlete_id = str(uuid.uuid4())
        db.add(
            AthleteModel(
                id=athlete_id,
                sports_json=json.dumps([values["primary_sport"]]),
                goals_json=json.dumps([]),
                available_days_json=json.dumps([0, 1, 2, 3, 4, 5, 6]),
                equipment_json=json.dumps([]),
                journey_phase="signup",
                preferred_session_hour_json=json.dumps({}),
                **values,  # type: ignore[arg-type]
            )
        )
        db.commit()
        return athlete_id, "created", values


def mint_link_code(athlete_id: str, hours: int) -> str:
    from app.db.database import SessionLocal
    from app.db.models import MessagingLinkCodeModel

    code = f"link-{secrets.token_hex(4)}"
    with SessionLocal() as db:
        db.add(
            MessagingLinkCodeModel(
                code=code,
                athlete_id=athlete_id,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=hours),
            )
        )
        db.commit()
    return code


def existing_identity(athlete_id: str) -> str | None:
    from app.db.database import SessionLocal
    from app.db.models import MessagingIdentityModel

    with SessionLocal() as db:
        row = (
            db.query(MessagingIdentityModel)
            .filter_by(athlete_id=athlete_id, channel="telegram")
            .first()
        )
        return row.external_id if row is not None else None


# ─── Main ─────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--check", action="store_true", help="Config report only.")
    parser.add_argument("--keys", action="store_true", help="Generate secrets and exit.")
    parser.add_argument("--new", action="store_true", help="Force a new athlete.")
    parser.add_argument("--name")
    parser.add_argument("--age", type=int)
    parser.add_argument("--sex", choices=("M", "F", "other"))
    parser.add_argument("--weight-kg", type=float)
    parser.add_argument("--height-cm", type=float)
    parser.add_argument("--primary-sport", choices=SPORTS)
    parser.add_argument("--hours-per-week", type=float)
    parser.add_argument("--timezone")
    parser.add_argument(
        "--weekly-cycle-day", type=int, help="0=Monday … 6=Sunday (default 6)."
    )
    parser.add_argument("--weekly-cycle-hour", type=int)
    parser.add_argument(
        "--code-hours", type=int, default=24, help="Link code lifetime (default 24h)."
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    _load_dotenv()

    if args.keys:
        print_keys()
        return EXIT_OK

    blockers = check_config()

    if args.check:
        print()
        if blockers:
            print(f"Blocked on: {', '.join(blockers)}")
            return EXIT_BLOCKED
        print("Configuration looks usable.")
        return EXIT_OK

    if not check_database() or not tables_ready():
        return EXIT_BLOCKED

    athlete_id, action, profile = ensure_athlete(args)
    linked_chat = existing_identity(athlete_id)

    print()
    print("Athlete")
    print("=" * 62)
    print(f"  id                {athlete_id}")
    print(f"  status            {action}")
    for field in PROFILE_FIELDS:
        print(f"  {field:<18}{profile[field]}")
    print("  (weekly_cycle_day: 0=Monday … 6=Sunday)")
    if action == "reused unchanged":
        print()
        print("  This is whatever athlete already existed in the database. If the")
        print("  profile above is not you, re-run with --name --age --sex and the")
        print("  rest to correct it, or --new to start a separate athlete. The")
        print("  coach plans from these numbers, so they matter.")

    print()
    print("Next steps")
    print("=" * 62)
    print(f"  1. Put this in .env:   ADMIN_ATHLETE_ID={athlete_id}")

    if linked_chat is not None:
        print(f"  2. Telegram already linked to chat {linked_chat} — nothing to do.")
        print("  3. Start the backend, then message the bot.")
    else:
        code = mint_link_code(athlete_id, args.code_hours)
        print("  2. Start the backend (see docs/backend/TELEGRAM-COACH.md §Quickstart).")
        print("  3. Message your bot on Telegram with exactly this, and nothing else:")
        print()
        print(f"         {code}")
        print()
        print(f"     (valid {args.code_hours}h, single use)")
        print("  4. Then send /connect and open the links to hook up your data.")

    if blockers:
        print()
        print(f"Still missing before it will run: {', '.join(blockers)}")
        return EXIT_BLOCKED
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
