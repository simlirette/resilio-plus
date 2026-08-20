#!/usr/bin/env python3
"""Manual smoke test for the V4 text coach against a RUNNING instance.

Checks the transport and automation layer end to end on a live box:

    1.  the app is up and ready
    2.  a link code redeems into a messaging identity
    3.  an inbound message reaches the coordinator and produces a reply
    4.  a weekly cycle can be forced and sends a plan with three buttons
    5.  approving that plan lands events in the Resilio Training calendar

Usage::

    PYTHONPATH=backend python scripts/smoke_test_v4.py \\
        --base-url http://localhost:8000 \\
        --athlete-id <uuid> \\
        --external-id <telegram chat id>

Talks to the database directly for the parts Telegram would normally do
(minting a link code, reading what went out), and over HTTP for the parts a
deploy must actually serve. Nothing here is mocked — it sends real messages if
TELEGRAM_BOT_TOKEN is set, so run it against a bot you own.

NOT for CI: needs a live instance, real credentials, and it writes to a real
calendar.
"""
from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime, timedelta, timezone

EXIT_OK = 0
EXIT_FAIL = 1


def _print(step: str, ok: bool, detail: str = "") -> bool:
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {step}" + (f" — {detail}" if detail else ""))
    return ok


def check_health(base_url: str) -> bool:
    import httpx

    try:
        health = httpx.get(f"{base_url}/health", timeout=10.0)
        ready = httpx.get(f"{base_url}/ready", timeout=10.0)
    except Exception as exc:
        return _print("service reachable", False, str(exc))
    return _print(
        "service reachable",
        health.status_code == 200 and ready.status_code == 200,
        f"/health {health.status_code}, /ready {ready.status_code}",
    )


def check_link_flow(athlete_id: str, external_id: str) -> bool:
    from app.db.database import SessionLocal
    from app.db.models import MessagingIdentityModel, MessagingLinkCodeModel
    from app.messaging.gateway import MessagingGateway
    from app.messaging.notification_service import NotificationService

    code = f"smoke-{uuid.uuid4().hex[:8]}"
    with SessionLocal() as db:
        existing = (
            db.query(MessagingIdentityModel)
            .filter_by(channel="telegram", external_id=external_id)
            .first()
        )
        if existing is not None:
            return _print(
                "identity linked",
                existing.athlete_id == athlete_id,
                f"already linked to {existing.athlete_id}",
            )

        db.add(
            MessagingLinkCodeModel(
                code=code,
                athlete_id=athlete_id,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            )
        )
        db.commit()

    from app.integrations.telegram.runtime import get_telegram_runtime

    runtime = get_telegram_runtime()
    channels = {runtime.channel.name: runtime.channel}
    with SessionLocal() as db:
        gateway = MessagingGateway(
            db, channels, notifier=NotificationService(db, channels)
        )
        try:
            linked = gateway.link_identity("telegram", external_id, code)
        except Exception as exc:
            return _print("identity linked", False, str(exc))
    return _print("identity linked", linked == athlete_id, linked)


def check_inbound(athlete_id: str, external_id: str) -> bool:
    from app.db.database import SessionLocal
    from app.db.models import OutboundMessageModel
    from app.integrations.telegram.runtime import get_telegram_runtime

    runtime = get_telegram_runtime()
    with SessionLocal() as db:
        before = (
            db.query(OutboundMessageModel).filter_by(athlete_id=athlete_id).count()
        )

    runtime.processor.process_update(
        {
            "update_id": int(datetime.now(timezone.utc).timestamp()),
            "message": {
                "chat": {"id": int(external_id), "type": "private"},
                "text": "/status",
            },
        }
    )

    with SessionLocal() as db:
        after = db.query(OutboundMessageModel).filter_by(athlete_id=athlete_id).count()
    return _print("inbound message answered", after > before, f"{before} -> {after}")


def check_weekly_cycle(athlete_id: str) -> str | None:
    from app.db.database import SessionLocal
    from app.jobs.weekly_jobs import run_weekly_cycle_now

    with SessionLocal() as db:
        try:
            result = run_weekly_cycle_now(athlete_id, db)
        except Exception as exc:
            _print("weekly cycle sent a plan", False, str(exc))
            return None

    _print(
        "weekly cycle sent a plan",
        result.plan_sent,
        f"degraded={result.degraded_sources or 'none'} reason={result.reason or '-'}",
    )
    return result.approval_token if result.plan_sent else None


def check_approval(athlete_id: str, external_id: str, token: str) -> bool:
    from app.db.database import SessionLocal
    from app.messaging.approval_service import ApprovalService
    from app.messaging.calendar_hook import get_calendar_pusher
    from app.messaging.notification_service import NotificationService
    from app.messaging.outbound import configured_channels

    with SessionLocal() as db:
        channels = configured_channels()
        service = ApprovalService(
            db,
            notifier=NotificationService(db, channels),
            calendar_pusher=get_calendar_pusher(),
        )
        try:
            outcome = service.handle_button(
                athlete_id=athlete_id,
                channel="telegram",
                external_id=external_id,
                token=token,
                resolution="approve",
            )
        except Exception as exc:
            return _print("approve wrote the calendar", False, str(exc))

    if outcome.calendar is None:
        return _print(
            "approve wrote the calendar",
            False,
            "no calendar configured — connect Google Calendar first",
        )
    return _print("approve wrote the calendar", True, str(outcome.calendar))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--athlete-id", required=True)
    parser.add_argument("--external-id", required=True, help="Telegram chat id")
    parser.add_argument(
        "--skip-calendar",
        action="store_true",
        help="Stop after the plan is sent; do not approve or write events.",
    )
    args = parser.parse_args()

    results = [
        check_health(args.base_url),
        check_link_flow(args.athlete_id, args.external_id),
        check_inbound(args.athlete_id, args.external_id),
    ]

    token = check_weekly_cycle(args.athlete_id)
    results.append(token is not None)

    if token is not None and not args.skip_calendar:
        results.append(check_approval(args.athlete_id, args.external_id, token))

    passed = all(results)
    print()
    print("V4 smoke test:", "PASS" if passed else "FAIL")
    return EXIT_OK if passed else EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
