#!/usr/bin/env python3
"""First-run setup for the V4 text coach.

The bot never auto-creates an athlete - that is a deliberate safety property,
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

Never prints a secret's value - only whether it is set.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import uuid
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
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


# --- Configuration ---------------------------------------------------------


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
    "Ops (optional, but this is how you see whether the cron fired)": (
        ("ADMIN_ATHLETE_ID", False),
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
    "Strava (optional - activities can also arrive via Hevy/Terra)": (
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
            if (
                name in ("PUBLIC_BASE_URL", "TELEGRAM_MODE", "ADMIN_ATHLETE_ID")
                and _is_set(name)
            ):
                shown = f"  -> {os.environ[name]}"
            print(f"  [{mark}] {name}{shown}")

    mode = os.getenv("TELEGRAM_MODE", "polling").strip() or "polling"
    if mode == "webhook" and not _is_set("TELEGRAM_WEBHOOK_SECRET"):
        print("\n  [MISSING] TELEGRAM_WEBHOOK_SECRET (required in webhook mode)")
        blockers.append("TELEGRAM_WEBHOOK_SECRET")

    if not _is_set("ADMIN_ATHLETE_ID"):
        print()
        print("  ADMIN_ATHLETE_ID is unset. It is just your athlete's id - this")
        print("  script prints it, and it gates /admin/jobs and /admin/metrics.")

    blockers.extend(_check_fernet_keys())
    blockers.extend(_check_provider_pairs())
    return blockers


FERNET_KEYS = ("STRAVA_ENCRYPTION_KEY", "GOOGLE_ENCRYPTION_KEY")


def _accepts_fernet(value: str) -> bool:
    from cryptography.fernet import Fernet

    try:
        Fernet(value.encode())
    except Exception:
        return False
    return True


def _check_fernet_keys() -> list[str]:
    """A key of the wrong shape passes every other check and fails at use.

    It fails *after* the OAuth round trip succeeds, as a 500, with the
    authorization code already spent - so validate the shape up front.
    """
    problems: list[str] = []
    notes: list[str] = []
    for name in FERNET_KEYS:
        if not _is_set(name):
            continue
        value = os.environ[name].strip()
        if _accepts_fernet(value):
            continue
        problems.append(name)
        # A base64 key ends in '=' padding, the single easiest character to lose
        # when copying. Check that before saying anything more general.
        if _accepts_fernet(value + "="):
            notes.append(
                f"  [ BAD  ] {name} is missing its trailing '=' ({len(value)} "
                "chars, needs 44).\n"
                "            A Fernet key ends in '=' padding and it is easy "
                "to lose when copying.\n"
                f"            Add a single '=' to the end of the {name} line."
            )
        else:
            notes.append(
                f"  [ BAD  ] {name} is not a valid Fernet key ({len(value)} "
                "chars; it must be exactly 44 url-safe base64\n"
                "            characters, not a passphrase). Generate one with:\n"
                f"            poetry run python scripts/bootstrap_v4.py --keys {name}"
            )
    if notes:
        print("\nEncryption keys")
        for note in notes:
            print(note)
    return problems


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
                f"  [MISSING] {key_var} - {provider} is configured but its tokens "
                "have nowhere safe to live."
            )
        if not _is_set(redirect_var):
            problems.append(redirect_var)
            notes.append(
                f"  [MISSING] {redirect_var} - without it the OAuth callback "
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


def _generators() -> dict[str, Callable[[], str]]:
    from cryptography.fernet import Fernet

    return {
        "JWT_SECRET": lambda: secrets.token_hex(32),
        "STRAVA_ENCRYPTION_KEY": lambda: Fernet.generate_key().decode(),
        "GOOGLE_ENCRYPTION_KEY": lambda: Fernet.generate_key().decode(),
        "TELEGRAM_WEBHOOK_SECRET": lambda: secrets.token_urlsafe(32),
    }


def print_keys(names: list[str] | None = None) -> int:
    """Print freshly generated secrets for the operator to paste in.

    Takes explicit names so you can mint one without rotating the others -
    regenerating a key that already encrypted a stored token destroys it.
    """
    generators = _generators()
    wanted = names or list(generators)

    unknown = [n for n in wanted if n not in generators]
    if unknown:
        print(f"Unknown key name(s): {', '.join(unknown)}")
        print(f"Known: {', '.join(generators)}")
        return EXIT_BLOCKED

    already = [n for n in wanted if _is_set(n)]
    print("Generated secrets - paste into .env:")
    print()
    for name in wanted:
        print(f"{name}={generators[name]()}")
    print()
    if already:
        print("WARNING: these are already set in .env, and replacing an")
        print("encryption key makes every token stored under it unreadable:")
        for name in already:
            print(f"  - {name}")
        print("Keep the existing value unless you mean to start that")
        print("integration over.")
    else:
        print("Rotating an encryption key later makes the tokens stored")
        print("under it unreadable. Set these once.")
    return EXIT_OK


GOOGLE_VARS = (
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_ENCRYPTION_KEY",
    "GOOGLE_REDIRECT_URI",
)


def verify_google() -> int:
    """Report Google Calendar status, and hand over the consent URL if needed.

    Three outcomes: not configured (says which variables are missing), configured
    but not authorised (prints the URL to open), or connected (confirms the
    calendar exists by touching the API).
    """
    missing = [name for name in GOOGLE_VARS if not _is_set(name)]
    if missing:
        base = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
        print("[MISSING] Google Calendar is not configured yet:")
        for name in missing:
            print(f"  - {name}")
        print()
        print("  GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET come from the Google")
        print("  Cloud Console (OAuth client, type: Web application).")
        print("  GOOGLE_ENCRYPTION_KEY:")
        print("      poetry run python scripts/bootstrap_v4.py --keys GOOGLE_ENCRYPTION_KEY")
        print("  GOOGLE_REDIRECT_URI must be exactly:")
        print(f"      {base}/integrations/link/callback/google")
        return EXIT_BLOCKED

    if not check_database() or not tables_ready():
        return EXIT_BLOCKED

    from app.db.database import SessionLocal
    from app.db.models import AthleteModel
    from app.integrations.google_calendar import oauth_service

    with SessionLocal() as db:
        athlete = db.query(AthleteModel).order_by(AthleteModel.id).first()
        if athlete is None:
            print("[MISSING] No athlete yet - run this script with no flags first.")
            return EXIT_BLOCKED
        athlete_id = athlete.id

        if not oauth_service.is_connected(athlete_id, db):
            try:
                auth_url = oauth_service.connect(athlete_id, db)["auth_url"]
            except Exception as exc:
                print(f"[FAIL] Could not build the consent URL: {type(exc).__name__}")
                return EXIT_BLOCKED
            print("Google Calendar is configured but not authorised yet.")
            print()
            print("1. Make sure the backend is running (.\\scripts\\start_coach.ps1).")
            print("2. Open this URL in a browser ON THIS MACHINE - the callback")
            print("   comes back to a loopback address only this machine can reach:")
            print()
            print(f"   {auth_url}")
            print()
            print("3. Approve, land on the 'go back to Telegram' page, then re-run")
            print("   this command to confirm.")
            return EXIT_BLOCKED

    # Connected: prove it by touching the API.
    from app.integrations.google_calendar.calendar_sync_service import (
        CalendarSyncService,
    )

    with SessionLocal() as db:
        try:
            calendar_id = CalendarSyncService(db).ensure_calendar(athlete_id)
        except Exception as exc:
            print(f"[FAIL] Connected, but the calendar call failed: {exc}")
            print("       Re-authorise by deleting the row in")
            print("       google_calendar_credentials and re-running this.")
            return EXIT_BLOCKED

    print("[  ok  ] Google Calendar is connected and reachable.")
    print(f"         Calendar: 'Resilio Training' ({calendar_id})")
    print("         Approving a week will write its sessions there.")
    return EXIT_OK


def verify_telegram() -> int:
    """Confirm the bot token works and print who it belongs to."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token or token.upper().startswith("CHANGEME"):
        print("[MISSING] TELEGRAM_BOT_TOKEN is not set.")
        return EXIT_BLOCKED

    import httpx

    try:
        response = httpx.get(
            f"https://api.telegram.org/bot{token}/getMe", timeout=15.0
        )
    except Exception as exc:
        print(f"[FAIL] Could not reach Telegram: {type(exc).__name__}")
        return EXIT_BLOCKED

    if response.status_code == 401:
        print("[FAIL] Telegram rejected the token (401).")
        print("       Re-copy it from BotFather - it is the whole string,")
        print("       digits, colon and all.")
        return EXIT_BLOCKED
    if response.status_code != 200:
        print(f"[FAIL] Telegram answered {response.status_code}.")
        return EXIT_BLOCKED

    bot = response.json().get("result", {})
    username = bot.get("username", "?")
    print("[  ok  ] Telegram token works.")
    print(f"         Bot: @{username} ({bot.get('first_name', '')})")
    print(f"         Open https://t.me/{username} to start the chat.")
    return EXIT_OK


# --- Database --------------------------------------------------------------


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
        print("          localhost in DATABASE_URL - on Windows, WSL can own")
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
    "target_race_date",
)

# Stored as JSON text on the athlete row, so handled separately from the
# scalar fields above.
JSON_LIST_FIELDS = {"sports": "sports_json", "goals": "goals_json"}

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
    "target_race_date": None,
}


def _supplied(args: argparse.Namespace) -> dict[str, object]:
    """Only the profile fields the operator actually passed."""
    return {
        field: getattr(args, field)
        for field in PROFILE_FIELDS
        if getattr(args, field) is not None
    }


def _supplied_lists(args: argparse.Namespace) -> dict[str, str]:
    """JSON-list columns the operator passed, already serialised."""
    out: dict[str, str] = {}
    for field, column in JSON_LIST_FIELDS.items():
        value = getattr(args, field, None)
        if value:
            out[column] = json.dumps(list(value))
    return out


def _parse_race_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"--target-race-date must be YYYY-MM-DD, got {value!r}"
        ) from None


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
                lists = _supplied_lists(args)
                # An explicit --sports wins; otherwise a new primary sport at
                # least keeps the list consistent with it.
                if "sports_json" not in lists and "primary_sport" in supplied:
                    lists["sports_json"] = json.dumps([supplied["primary_sport"]])
                for column, payload in lists.items():
                    setattr(existing, column, payload)
                db.commit()
                action = "updated" if (supplied or lists) else "reused unchanged"
                profile = {f: getattr(existing, f) for f in PROFILE_FIELDS}
                profile["sports"] = json.loads(existing.sports_json or "[]")
                profile["goals"] = json.loads(existing.goals_json or "[]")
                return existing.id, action, profile

        values: dict[str, object] = {**PROFILE_DEFAULTS, **supplied}
        lists = _supplied_lists(args)
        lists.setdefault("sports_json", json.dumps([values["primary_sport"]]))
        lists.setdefault("goals_json", json.dumps([]))
        athlete_id = str(uuid.uuid4())
        db.add(
            AthleteModel(
                id=athlete_id,
                available_days_json=json.dumps([0, 1, 2, 3, 4, 5, 6]),
                equipment_json=json.dumps([]),
                journey_phase="signup",
                preferred_session_hour_json=json.dumps({}),
                **lists,
                **values,  # type: ignore[arg-type]
            )
        )
        db.commit()
        reported = dict(values)
        reported["sports"] = json.loads(lists["sports_json"])
        reported["goals"] = json.loads(lists["goals_json"])
        return athlete_id, "created", reported


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


# --- Main ------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--check", action="store_true", help="Config report only.")
    parser.add_argument(
        "--keys",
        nargs="*",
        metavar="NAME",
        help=(
            "Generate secrets and exit. Give names to mint only those, e.g. "
            "--keys GOOGLE_ENCRYPTION_KEY."
        ),
    )
    parser.add_argument(
        "--verify-telegram",
        action="store_true",
        help="Ask Telegram whether the bot token works, and print the bot name.",
    )
    parser.add_argument(
        "--verify-google",
        action="store_true",
        help="Report Google Calendar status and hand over the consent URL.",
    )
    parser.add_argument("--new", action="store_true", help="Force a new athlete.")
    parser.add_argument("--name")
    parser.add_argument("--age", type=int)
    parser.add_argument("--sex", choices=("M", "F", "other"))
    parser.add_argument("--weight-kg", type=float)
    parser.add_argument("--height-cm", type=float)
    parser.add_argument("--primary-sport", choices=SPORTS)
    parser.add_argument(
        "--sports",
        nargs="+",
        choices=SPORTS,
        help="Every sport the athlete trains, e.g. --sports running lifting.",
    )
    parser.add_argument(
        "--goal",
        dest="goals",
        action="append",
        help="Repeatable, e.g. --goal 'half marathon Usti nad Labem'.",
    )
    parser.add_argument(
        "--target-race-date",
        type=_parse_race_date,
        help="YYYY-MM-DD. Drives the periodization phase and weeks remaining.",
    )
    parser.add_argument("--hours-per-week", type=float)
    parser.add_argument("--timezone")
    parser.add_argument(
        "--weekly-cycle-day", type=int, help="0=Monday ... 6=Sunday (default 6)."
    )
    parser.add_argument("--weekly-cycle-hour", type=int)
    parser.add_argument(
        "--code-hours", type=int, default=24, help="Link code lifetime (default 24h)."
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    _load_dotenv()

    if args.keys is not None:
        return print_keys(args.keys or None)

    if args.verify_telegram:
        return verify_telegram()

    if args.verify_google:
        return verify_google()

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
    for extra in ("sports", "goals"):
        if extra in profile:
            print(f"  {extra:<18}{profile[extra]}")
    print("  (weekly_cycle_day: 0=Monday ... 6=Sunday)")
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
        print(f"  2. Telegram already linked to chat {linked_chat} - nothing to do.")
        print("  3. Start the backend, then message the bot.")
    else:
        code = mint_link_code(athlete_id, args.code_hours)
        print("  2. Start the backend (see docs/backend/TELEGRAM-COACH.md Quickstart).")
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
