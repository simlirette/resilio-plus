#!/usr/bin/env python3
"""Manual smoke test — runs full LangGraph coaching flow with REAL LLM calls.

Usage:
    cd backend
    python ../scripts/smoke_test_runtime.py --athlete-id smoke-test-001

Requires:
    OPENAI_API_KEY (or equivalent) in environment.
    NOT for CI — manual validation only.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import sys
import tempfile
import uuid
from datetime import date, timedelta

# Configure structured logging to see node transitions
logging.basicConfig(level=logging.INFO, format="%(message)s")


def main():
    parser = argparse.ArgumentParser(description="Smoke test: full LangGraph coaching flow")
    parser.add_argument("--athlete-id", default=f"smoke-{uuid.uuid4().hex[:8]}")
    args = parser.parse_args()

    # Lazy imports so --help works without full env
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from langgraph.checkpoint.sqlite import SqliteSaver

    from app.db.database import Base
    from app.db import models as _db_models  # noqa: F401
    from app.models import schemas as _v3  # noqa: F401
    from app.services.coaching_service import CoachingService

    # In-memory app DB (not checkpoint DB)
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def set_pragma(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)

    # SQLite checkpoint on disk (temp file)
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    conn = sqlite3.connect(tmp.name, check_same_thread=False)
    try:
        saver = SqliteSaver(conn)
        saver.setup()

        athlete_id = args.athlete_id
        target_race = date.today() + timedelta(weeks=20)

        with Session() as db:
            # Seed athlete
            athlete = _db_models.AthleteModel(
                id=athlete_id,
                name="SmokeTest",
                age=30,
                sex="M",
                weight_kg=75.0,
                height_cm=175.0,
                primary_sport="running",
                target_race_date=target_race,
                hours_per_week=6.0,
                sports_json=json.dumps(["running", "lifting"]),
                goals_json=json.dumps(["run sub-25min 5K"]),
                available_days_json=json.dumps([0, 2, 4]),
                equipment_json=json.dumps([]),
                coaching_mode="full",
                vdot=42.0,
                resting_hr=60,
                max_hr=185,
            )
            db.add(athlete)
            db.commit()

            profile = {
                "id": athlete_id,
                "name": "SmokeTest",
                "age": 30,
                "sex": "M",
                "weight_kg": 75.0,
                "height_cm": 175.0,
                "sports": ["running", "lifting"],
                "primary_sport": "running",
                "goals": ["run sub-25min 5K"],
                "target_race_date": target_race.isoformat(),
                "available_days": [0, 2, 4],
                "hours_per_week": 6.0,
                "equipment": [],
                "vdot": 42.0,
                "resting_hr": 60,
                "max_hr": 185,
                "sleep_hours_typical": 7.0,
                "stress_level": 5,
                "job_physical": False,
                "coaching_mode": "full",
                "ftp_watts": None,
                "css_per_100m": None,
            }

            svc = CoachingService(checkpointer=saver)

            print(f"\n{'='*60}")
            print(f"SMOKE TEST — athlete_id={athlete_id}")
            print(f"{'='*60}\n")

            # Step 1: Create plan
            print("[1/3] Creating plan (real LLM calls)...")
            try:
                thread_id, proposed = svc.create_plan(
                    athlete_id=athlete_id,
                    athlete_dict=profile,
                    load_history=[300.0] * 28,
                    db=db,
                )
            except Exception as exc:
                print(f"FAIL: create_plan raised {type(exc).__name__}: {exc}", file=sys.stderr)
                sys.exit(1)

            if proposed is None:
                print("FAIL: proposed_plan_dict is None", file=sys.stderr)
                sys.exit(1)

            sessions = proposed.get("sessions", [])
            print(f"  thread_id: {thread_id}")
            print(f"  sessions:  {len(sessions)}")
            print(f"  phase:     {proposed.get('phase')}")
            print(f"  readiness: {proposed.get('readiness_level')}")

            # Step 2: Inspect graph state
            print("\n[2/3] Inspecting graph state at interrupt...")
            snapshot = svc.get_graph_state(thread_id)
            print(f"  state keys: {list(snapshot.values.keys())}")
            print(f"  human_approved: {snapshot.values.get('human_approved')}")

            # Step 3: Approve
            print("\n[3/3] Approving plan...")
            try:
                final = svc.resume_plan(
                    thread_id=thread_id,
                    approved=True,
                    feedback=None,
                    db=db,
                )
            except Exception as exc:
                print(f"FAIL: resume_plan raised {type(exc).__name__}: {exc}", file=sys.stderr)
                sys.exit(1)

            if final is None:
                print("FAIL: final_plan_dict is None", file=sys.stderr)
                sys.exit(1)

            print(f"  db_plan_id: {final.get('db_plan_id')}")
            print(f"  sessions:   {len(final.get('sessions', []))}")

            print(f"\n{'='*60}")
            print("SMOKE TEST PASSED")
            print(f"{'='*60}\n")

        sys.exit(0)
    finally:
        conn.close()
        os.unlink(tmp.name)


if __name__ == "__main__":
    main()
