import json
import pytest
from datetime import date
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker


def make_test_engine():
    """Create a fresh in-memory SQLite engine with FK enforcement for testing."""
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def test_base_is_importable():
    from app.db.database import Base
    assert Base is not None


def test_database_url_is_absolute():
    from app.db.database import DATABASE_URL
    # After migrating to PostgreSQL, DATABASE_URL must use postgresql or sqlite scheme
    assert DATABASE_URL.startswith("postgresql") or DATABASE_URL.startswith("sqlite:///"), (
        f"DATABASE_URL must use postgresql or sqlite:/// scheme, got: {DATABASE_URL}"
    )


def test_session_local_is_importable():
    from app.db.database import SessionLocal
    assert SessionLocal is not None


def test_in_memory_engine_fk_enforcement():
    """SQLite FK constraints are OFF by default — verify our pragma enables them."""
    engine = make_test_engine()
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA foreign_keys"))
        value = result.scalar()
    assert value == 1, "PRAGMA foreign_keys must be ON"


def setup_db(engine):
    """Create all tables. Call at start of each DB test."""
    from app.db.database import Base
    from app.db import models  # noqa: F401 — registers ORM models with Base
    Base.metadata.create_all(engine)
    return sessionmaker(engine)


def teardown_db(engine):
    """Drop all tables. Call at end of each DB test."""
    from app.db.database import Base
    Base.metadata.drop_all(engine)


def make_athlete_row():
    import uuid
    return {
        "id": str(uuid.uuid4()),
        "name": "Alice",
        "age": 30,
        "sex": "F",
        "weight_kg": 60.0,
        "height_cm": 168.0,
        "primary_sport": "running",
        "hours_per_week": 10.0,
        "sports_json": '["running","lifting"]',
        "goals_json": '["run a marathon sub-4h"]',
        "available_days_json": '[0,2,4,6]',
        "equipment_json": '[]',
    }


def test_all_seven_tables_created():
    from sqlalchemy import inspect
    engine = make_test_engine()
    setup_db(engine)
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    assert "users" in table_names
    assert "athletes" in table_names
    assert "training_plans" in table_names
    assert "nutrition_plans" in table_names
    assert "weekly_reviews" in table_names
    assert "connector_credentials" in table_names
    assert "session_logs" in table_names
    teardown_db(engine)


def test_athlete_crud_round_trip():
    from app.db.models import AthleteModel
    engine = make_test_engine()
    Session = setup_db(engine)
    row = make_athlete_row()
    with Session() as session:
        athlete = AthleteModel(**row)
        session.add(athlete)
        session.commit()
        fetched = session.get(AthleteModel, row["id"])
        assert fetched.name == "Alice"
        assert fetched.age == 30
        assert fetched.sex == "F"
        assert fetched.sports_json == '["running","lifting"]'
    teardown_db(engine)


def test_athlete_json_fields_stored_as_strings():
    from app.db.models import AthleteModel
    engine = make_test_engine()
    Session = setup_db(engine)
    row = make_athlete_row()
    with Session() as session:
        session.add(AthleteModel(**row))
        session.commit()
        fetched = session.get(AthleteModel, row["id"])
        # JSON fields must be strings (not already parsed)
        assert isinstance(fetched.sports_json, str)
        # And parseable back to list
        assert json.loads(fetched.sports_json) == ["running", "lifting"]
        assert json.loads(fetched.goals_json) == ["run a marathon sub-4h"]
        assert json.loads(fetched.available_days_json) == [0, 2, 4, 6]
        assert json.loads(fetched.equipment_json) == []
    teardown_db(engine)


def test_training_plan_fk_constraint_enforced():
    from app.db.models import TrainingPlanModel
    from sqlalchemy.exc import IntegrityError
    import uuid
    engine = make_test_engine()
    Session = setup_db(engine)
    with Session() as session:
        plan = TrainingPlanModel(
            id=str(uuid.uuid4()),
            athlete_id="does-not-exist",  # FK violation
            start_date=date(2026, 4, 7),
            end_date=date(2026, 5, 4),
            phase="base",
            total_weekly_hours=8.0,
            acwr=1.0,
            weekly_slots_json="{}",
        )
        session.add(plan)
        with pytest.raises(IntegrityError):
            session.commit()
    teardown_db(engine)


def test_weekly_review_fk_to_both_athlete_and_plan():
    from app.db.models import AthleteModel, TrainingPlanModel, WeeklyReviewModel
    import uuid
    engine = make_test_engine()
    Session = setup_db(engine)
    athlete_id = str(uuid.uuid4())
    plan_id = str(uuid.uuid4())
    review_id = str(uuid.uuid4())
    with Session() as session:
        session.add(AthleteModel(**{**make_athlete_row(), "id": athlete_id}))
        session.add(TrainingPlanModel(
            id=plan_id,
            athlete_id=athlete_id,
            start_date=date(2026, 4, 7),
            end_date=date(2026, 5, 4),
            phase="base",
            total_weekly_hours=8.0,
            acwr=1.0,
            weekly_slots_json="{}",
        ))
        session.add(WeeklyReviewModel(
            id=review_id,
            athlete_id=athlete_id,
            plan_id=plan_id,
            week_start=date(2026, 4, 7),
            results_json="[]",
        ))
        session.commit()
        review = session.get(WeeklyReviewModel, review_id)
        assert review.athlete_id == athlete_id
        assert review.plan_id == plan_id
        assert review.results_json == "[]"
    teardown_db(engine)


def test_nutrition_plan_targets_json_round_trip():
    from app.db.models import AthleteModel, NutritionPlanModel
    import uuid
    engine = make_test_engine()
    Session = setup_db(engine)
    athlete_id = str(uuid.uuid4())
    plan_id = str(uuid.uuid4())
    targets = {"rest": {"day_type": "rest", "macro_target": {"carbs_g_per_kg": 3.0, "protein_g_per_kg": 2.0, "fat_g_per_kg": 1.0, "calories_total": 1800}, "intra_effort_carbs_g_per_h": None, "sodium_mg_per_h": None}}
    with Session() as session:
        session.add(AthleteModel(**{**make_athlete_row(), "id": athlete_id}))
        session.add(NutritionPlanModel(
            id=plan_id,
            athlete_id=athlete_id,
            weight_kg=75.0,
            targets_json=json.dumps(targets),
        ))
        session.commit()
        fetched = session.get(NutritionPlanModel, plan_id)
        assert isinstance(fetched.targets_json, str)
        parsed = json.loads(fetched.targets_json)
        assert "rest" in parsed
        assert parsed["rest"]["macro_target"]["carbs_g_per_kg"] == 3.0
    teardown_db(engine)


def test_connector_credentials_table_created():
    from sqlalchemy import inspect
    engine = make_test_engine()
    setup_db(engine)
    inspector = inspect(engine)
    assert "connector_credentials" in inspector.get_table_names()
    teardown_db(engine)


def test_connector_credential_crud_round_trip():
    from app.db.models import AthleteModel, ConnectorCredentialModel
    import uuid
    engine = make_test_engine()
    Session = setup_db(engine)
    athlete_id = str(uuid.uuid4())
    cred_id = str(uuid.uuid4())
    with Session() as session:
        session.add(AthleteModel(**{**make_athlete_row(), "id": athlete_id}))
        session.add(ConnectorCredentialModel(
            id=cred_id,
            athlete_id=athlete_id,
            provider="strava",
            access_token_enc="tok",
            refresh_token_enc="ref",
            expires_at=9999999999,
            extra_json="{}",
        ))
        session.commit()
        fetched = session.get(ConnectorCredentialModel, cred_id)
        assert fetched.provider == "strava"
        assert fetched.access_token_enc == "tok"
        assert fetched.athlete_id == athlete_id
    teardown_db(engine)


def test_connector_credential_unique_constraint():
    from app.db.models import AthleteModel, ConnectorCredentialModel
    from sqlalchemy.exc import IntegrityError
    import uuid
    engine = make_test_engine()
    Session = setup_db(engine)
    athlete_id = str(uuid.uuid4())
    with Session() as session:
        session.add(AthleteModel(**{**make_athlete_row(), "id": athlete_id}))
        session.add(ConnectorCredentialModel(
            id=str(uuid.uuid4()),
            athlete_id=athlete_id,
            provider="strava",
            extra_json="{}",
        ))
        session.flush()
        session.add(ConnectorCredentialModel(
            id=str(uuid.uuid4()),
            athlete_id=athlete_id,
            provider="strava",  # duplicate (athlete_id, provider)
            extra_json="{}",
        ))
        with pytest.raises(IntegrityError):
            session.commit()
    teardown_db(engine)


def test_training_plan_created_at_auto_populated():
    from app.db.models import AthleteModel, TrainingPlanModel
    from datetime import datetime, timedelta, timezone
    import uuid
    engine = make_test_engine()
    Session = setup_db(engine)
    athlete_id = str(uuid.uuid4())
    plan_id = str(uuid.uuid4())
    with Session() as session:
        session.add(AthleteModel(**{**make_athlete_row(), "id": athlete_id}))
        session.add(TrainingPlanModel(
            id=plan_id,
            athlete_id=athlete_id,
            start_date=date(2026, 4, 7),
            end_date=date(2026, 4, 13),
            phase="general_prep",
            total_weekly_hours=8.0,
            acwr=1.0,
            weekly_slots_json="[]",
            # created_at intentionally omitted — must auto-populate
        ))
        session.commit()
        fetched = session.get(TrainingPlanModel, plan_id)
        assert fetched.created_at is not None
        assert isinstance(fetched.created_at, datetime)
        # SQLite returns naive datetimes; interpret as UTC
        created_at_utc = fetched.created_at.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        assert now - timedelta(seconds=5) < created_at_utc <= now + timedelta(seconds=5)
    teardown_db(engine)


def test_athlete_credentials_relationship():
    from app.db.models import AthleteModel, ConnectorCredentialModel
    import uuid
    engine = make_test_engine()
    Session = setup_db(engine)
    athlete_id = str(uuid.uuid4())
    with Session() as session:
        session.add(AthleteModel(**{**make_athlete_row(), "id": athlete_id}))
        session.add(ConnectorCredentialModel(
            id=str(uuid.uuid4()), athlete_id=athlete_id, provider="strava", extra_json="{}",
        ))
        session.add(ConnectorCredentialModel(
            id=str(uuid.uuid4()), athlete_id=athlete_id, provider="hevy", extra_json="{}",
        ))
        session.commit()
        athlete = session.get(AthleteModel, athlete_id)
        assert len(athlete.credentials) == 2
        providers = {c.provider for c in athlete.credentials}
        assert providers == {"strava", "hevy"}
    teardown_db(engine)


def test_session_log_crud():
    from app.db.models import AthleteModel, SessionLogModel
    import json
    import uuid
    from datetime import datetime, timezone
    engine = make_test_engine()
    Session = setup_db(engine)
    athlete_id = str(uuid.uuid4())
    log_id = str(uuid.uuid4())
    with Session() as session:
        session.add(AthleteModel(**{**make_athlete_row(), "id": athlete_id}))
        session.commit()
        log = SessionLogModel(
            id=log_id,
            athlete_id=athlete_id,
            plan_id=None,
            session_id="sess-001",
            actual_duration_min=45,
            skipped=False,
            actual_data_json=json.dumps({"source": "manual"}),
            logged_at=datetime.now(timezone.utc),
        )
        session.add(log)
        session.commit()
        fetched = session.get(SessionLogModel, log_id)
        assert fetched is not None
        assert fetched.session_id == "sess-001"
        assert fetched.actual_duration_min == 45
    teardown_db(engine)


def test_session_log_athlete_relationship():
    from app.db.models import AthleteModel, SessionLogModel
    import json
    import uuid
    from datetime import datetime, timezone
    engine = make_test_engine()
    Session = setup_db(engine)
    athlete_id = str(uuid.uuid4())
    with Session() as session:
        session.add(AthleteModel(**{**make_athlete_row(), "id": athlete_id}))
        session.commit()
        session.add(SessionLogModel(
            id=str(uuid.uuid4()),
            athlete_id=athlete_id,
            plan_id=None,
            session_id="sess-rel-001",
            actual_duration_min=30,
            skipped=False,
            actual_data_json="{}",
            logged_at=datetime.now(timezone.utc),
        ))
        session.commit()
        athlete = session.get(AthleteModel, athlete_id)
        assert len(athlete.session_logs) == 1
        assert athlete.session_logs[0].session_id == "sess-rel-001"
    teardown_db(engine)
