"""The whole first-contact flow, driven only by inbound text messages."""
from __future__ import annotations

import uuid
from typing import Any

import pytest
from app.db.models import AthleteModel, DeepLinkTokenModel, MessagingIdentityModel
from app.messaging.approval_service import ApprovalService
from app.messaging.approvals import parse_callback
from app.messaging.base import Button
from app.messaging.commands import CommandRouter
from app.messaging.gateway import MessagingGateway
from app.services.graph_invoker import build_live_coordinator
from sqlalchemy.orm import Session

EXTERNAL_ID = "31337"

PROPOSED_PLAN = {
    "phase": "base",
    "sessions": [
        {
            "id": "slot-1",
            "date": "2031-06-02",
            "sport": "running",
            "workout_type": "easy",
            "duration_min": 45,
            "notes": "",
        }
    ],
}

_BLOCK_QUESTIONS = {
    1: "Tell me about yourself.",
    2: "Age, sex, weight, height?",
    3: "What is the goal and by when?",
    4: "Sport history?",
    5: "Training preferences?",
    6: "Here is the scope — confirm?",
}


class Channel:
    name = "telegram"

    def __init__(self) -> None:
        self.messages: list[tuple[str, list[Button] | None]] = []

    def send(self, external_id: str, text: str) -> str:
        self.messages.append((text, None))
        return f"msg-{len(self.messages)}"

    def send_with_buttons(
        self, external_id: str, text: str, buttons: list[Button]
    ) -> str:
        self.messages.append((text, buttons))
        return f"msg-{len(self.messages)}"

    def max_message_length(self) -> int:
        return 4096

    def format(self, text: str) -> str:
        return text


class Notifier:
    def __init__(self, channel: Channel) -> None:
        self._channel = channel

    def send(
        self, athlete_id: str, text: str, buttons: list[Button] | None = None
    ) -> object:
        if buttons:
            return [self._channel.send_with_buttons(EXTERNAL_ID, text, buttons)]
        return [self._channel.send(EXTERNAL_ID, text)]


class FakeCoaching:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def create_plan(
        self,
        athlete_id: str,
        athlete_dict: dict[str, Any],
        load_history: list[float],
        db: Session,
    ) -> tuple[str, dict[str, Any] | None]:
        self.calls.append(athlete_id)
        return "plan-thread", PROPOSED_PLAN

    def resume_plan(
        self,
        thread_id: str,
        approved: bool,
        feedback: str | None,
        db: Session,
    ) -> dict[str, Any] | None:
        return {**PROPOSED_PLAN, "db_plan_id": "plan-1"}


@pytest.fixture
def onboarding_athlete(db_session: Session) -> str:
    athlete_id = str(uuid.uuid4())
    db_session.add(
        AthleteModel(
            id=athlete_id,
            name="Text Athlete",
            age=34,
            sex="M",
            weight_kg=76.0,
            height_cm=181.0,
            primary_sport="running",
            hours_per_week=8.0,
            sports_json='["running"]',
            goals_json="[]",
            available_days_json="[]",
            equipment_json="[]",
            journey_phase="signup",
        )
    )
    db_session.add(
        MessagingIdentityModel(
            id=str(uuid.uuid4()),
            athlete_id=athlete_id,
            channel="telegram",
            external_id=EXTERNAL_ID,
        )
    )
    db_session.commit()
    return athlete_id


@pytest.fixture
def scripted_onboarding(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> dict[str, int]:
    """Emulate the coach's turns without calling an LLM.

    Rewritten 2026-08-21. This used to script the six-block walk; there are no
    blocks. The coach answers each message through the agentic loop and decides
    for itself when the profile can support a plan, so the fake counts turns and
    flips the phase where the real loop would call `generate_plan`.
    """
    state = {"block": 0}

    class FakeTurn:
        def __init__(self, reply: str) -> None:
            self.reply = reply
            self.ok = True
            self.tools_used: list[str] = []

    def turn(*, athlete_id: str, user_message: str, db: Session) -> FakeTurn:
        state["block"] += 1
        if state["block"] > 6:
            athlete = db.get(AthleteModel, athlete_id)
            assert athlete is not None
            athlete.journey_phase = "baseline_pending_confirmation"
            db.commit()
            result = FakeTurn("Profil complet — voici ta semaine.")
            # Where the real loop would call the tool, which is what chains the
            # approval buttons.
            result.tools_used = ["generate_plan"]
            return result
        return FakeTurn(_BLOCK_QUESTIONS[min(state["block"], 6)])

    monkeypatch.setattr("app.services.graph_invoker.run_coach_turn", turn)
    return state


def _phase(db_session: Session, athlete_id: str) -> str:
    """Read journey_phase and leave the session clean for the next inbound."""
    db_session.expire_all()
    athlete = db_session.get(AthleteModel, athlete_id)
    assert athlete is not None
    phase = athlete.journey_phase
    db_session.rollback()
    return phase


def build_gateway(
    db_session: Session,
    channel: Channel,
    coaching: FakeCoaching,
) -> MessagingGateway:
    notifier = Notifier(channel)
    return MessagingGateway(
        db_session,
        {channel.name: channel},
        coordinator=build_live_coordinator(coaching=coaching),
        notifier=notifier,
        approvals=ApprovalService(
            db_session, notifier=notifier, coaching=coaching
        ),
        commands=CommandRouter(db_session, notifier=notifier),
    )


def test_first_message_starts_onboarding_and_the_last_one_proposes_a_plan(
    db_session: Session,
    onboarding_athlete: str,
    scripted_onboarding: dict[str, int],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channel = Channel()
    coaching = FakeCoaching()
    gateway = build_gateway(db_session, channel, coaching)

    gateway.handle_inbound("telegram", EXTERNAL_ID, "hi")

    assert _phase(db_session, onboarding_athlete) == "onboarding"
    assert channel.messages[0][0] == _BLOCK_QUESTIONS[1]

    for answer in ["I run", "34 M 76 181", "sub-90 half in June", "5 years", "DUP"]:
        gateway.handle_inbound("telegram", EXTERNAL_ID, answer)

    assert channel.messages[-1][0] == _BLOCK_QUESTIONS[6]

    gateway.handle_inbound("telegram", EXTERNAL_ID, "confirmed")

    assert _phase(db_session, onboarding_athlete) == "baseline_pending_confirmation"
    assert coaching.calls == [onboarding_athlete]

    final_text, buttons = channel.messages[-1]
    assert buttons is not None and len(buttons) == 3
    assert "easy" in final_text
    tokens = {parse_callback(b.token)[0] for b in buttons}  # type: ignore[index]
    assert len(tokens) == 1


def test_approving_the_proposed_week_resumes_the_plan_thread(
    db_session: Session,
    onboarding_athlete: str,
    scripted_onboarding: dict[str, int],
) -> None:
    channel = Channel()
    coaching = FakeCoaching()
    gateway = build_gateway(db_session, channel, coaching)

    gateway.handle_inbound("telegram", EXTERNAL_ID, "hi")
    for answer in ["a", "b", "c", "d", "e", "confirmed"]:
        gateway.handle_inbound("telegram", EXTERNAL_ID, answer)

    _, buttons = channel.messages[-1]
    assert buttons is not None
    token, resolution = parse_callback(buttons[0].token)  # type: ignore[misc]
    assert resolution == "approve"

    outcome = ApprovalService(
        db_session, notifier=Notifier(channel), coaching=coaching
    ).handle_button(
        athlete_id=onboarding_athlete,
        channel="telegram",
        external_id=EXTERNAL_ID,
        token=token,
        resolution="approve",
    )

    assert outcome.resolution == "approve"
    assert "approuvée" in channel.messages[-1][0].lower()


def test_connect_command_issues_provider_links_mid_onboarding(
    db_session: Session,
    onboarding_athlete: str,
    scripted_onboarding: dict[str, int],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://coach.example.com")
    channel = Channel()
    gateway = build_gateway(db_session, channel, FakeCoaching())

    gateway.handle_inbound("telegram", EXTERNAL_ID, "hi")
    gateway.handle_inbound("telegram", EXTERNAL_ID, "/connect")

    text = channel.messages[-1][0]
    assert text.count("https://coach.example.com/integrations/link/") == 3

    db_session.expire_all()
    rows = db_session.query(DeepLinkTokenModel).all()
    assert {row.provider for row in rows} == {"strava", "hevy", "google"}
    assert all(row.consumed_at is None for row in rows)
    db_session.rollback()


def test_a_command_does_not_advance_the_onboarding_block(
    db_session: Session,
    onboarding_athlete: str,
    scripted_onboarding: dict[str, int],
) -> None:
    channel = Channel()
    gateway = build_gateway(db_session, channel, FakeCoaching())

    gateway.handle_inbound("telegram", EXTERNAL_ID, "hi")
    gateway.handle_inbound("telegram", EXTERNAL_ID, "/help")

    assert scripted_onboarding["block"] == 1
