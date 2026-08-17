"""D7 TDD — onboarding graph (blocs 1-3 with HITL interrupts)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


def _make_athlete(
    athlete_id: str = "a1",
    thread_id: str | None = None,
) -> MagicMock:
    m = MagicMock()
    m.id = athlete_id
    m.journey_phase = "onboarding"
    m.sports_json = '["running"]'
    m.primary_sport = "running"
    m.hours_per_week = 8.0
    m.coaching_mode = "full"
    m.clinical_context_flag = None
    m.active_onboarding_thread_id = thread_id
    return m


def _mock_llm(text: str = "question") -> MagicMock:
    block = MagicMock()
    block.text = text
    msg = MagicMock()
    msg.content = [block]
    return msg


def _make_db(athlete: MagicMock) -> MagicMock:
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = athlete
    return db


class TestOnboardingStart:
    def test_start_creates_thread_block1(self):
        """run_onboarding_start returns current_block=1 for new athlete."""
        from app.graphs.onboarding import run_onboarding_start

        athlete = _make_athlete()
        db = _make_db(athlete)

        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm("Bienvenue!")
            result = run_onboarding_start(athlete_id="a1", db=db)

        assert result["current_block"] == 1
        assert result["thread_id"] is not None
        assert "a1:onboarding:" in result["thread_id"]
        assert result["status"] == "in_progress"
        assert result["question"] == "Bienvenue!"

    def test_thread_id_stored_on_athlete(self):
        """After start, athlete.active_onboarding_thread_id is set."""
        from app.graphs.onboarding import run_onboarding_start

        athlete = _make_athlete()
        db = _make_db(athlete)

        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            result = run_onboarding_start(athlete_id="a1", db=db)

        assert athlete.active_onboarding_thread_id == result["thread_id"]

    def test_start_without_existing_thread_goes_bloc1(self):
        """Athlete with no active thread → new thread at block 1."""
        from app.graphs.onboarding import run_onboarding_start

        athlete = _make_athlete(thread_id=None)
        db = _make_db(athlete)

        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            result = run_onboarding_start(athlete_id="a1", db=db)

        assert result["current_block"] == 1


class TestOnboardingRespond:
    def test_respond_to_bloc1_advances_to_bloc2(self):
        """Responding to block 1 → current_block becomes 2."""
        from app.graphs.onboarding import run_onboarding_respond, run_onboarding_start

        athlete = _make_athlete()
        db = _make_db(athlete)

        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm("Présentation faite")
            start = run_onboarding_start(athlete_id="a1", db=db)

        thread_id = start["thread_id"]

        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm("Profil collecté?")
            result = run_onboarding_respond(
                thread_id=thread_id,
                user_response="Je suis un coureur de niveau intermédiaire",
                db=db,
            )

        assert result["current_block"] == 2
        assert result["status"] == "in_progress"
        assert result["question"] == "Profil collecté?"

    def test_respond_stores_collected_data(self):
        """User response stored in collected_data under block key."""
        from app.graphs.onboarding import run_onboarding_respond, run_onboarding_start

        athlete = _make_athlete()
        db = _make_db(athlete)

        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            start = run_onboarding_start(athlete_id="a1", db=db)

        thread_id = start["thread_id"]

        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            result = run_onboarding_respond(
                thread_id=thread_id,
                user_response="coureur débutant",
                db=db,
            )

        assert "intro_response" in result["collected_data"]
        assert result["collected_data"]["intro_response"] == "coureur débutant"

    def test_respond_to_bloc3_is_still_in_progress(self):
        """Completing blocks 1-3 → still in_progress (blocs 4-6 remain)."""
        from app.graphs.onboarding import run_onboarding_respond, run_onboarding_start

        athlete = _make_athlete()
        db = _make_db(athlete)

        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            start = run_onboarding_start(athlete_id="a1", db=db)

        thread_id = start["thread_id"]

        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            run_onboarding_respond(thread_id, "intro", db=db)

        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            run_onboarding_respond(thread_id, "25 ans, 70kg", db=db)

        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            result = run_onboarding_respond(thread_id, "finir un semi en 6 mois", db=db)

        assert result["status"] == "in_progress"
        assert result["current_block"] == 4

    def test_invalid_thread_raises(self):
        """Unknown thread_id raises ValueError."""
        from app.graphs.onboarding import run_onboarding_respond

        import pytest

        with pytest.raises(ValueError, match="not found"):
            run_onboarding_respond(
                thread_id="invalid-thread-id",
                user_response="...",
                db=MagicMock(),
            )


class TestOnboardingResume:
    def test_resume_after_abandon_at_bloc2(self):
        """Abandon after advancing to bloc 2 → start again returns bloc 2, not bloc 1."""
        from app.graphs.onboarding import run_onboarding_respond, run_onboarding_start

        athlete = _make_athlete()
        db = _make_db(athlete)

        # Start → block 1
        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm("Bloc 1 question")
            start = run_onboarding_start(athlete_id="a1", db=db)

        thread_id = start["thread_id"]

        # Respond → advances to block 2
        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm("Bloc 2 question")
            run_onboarding_respond(thread_id, "intro response", db=db)

        # "Abandon" — athlete already has thread_id set from first start call
        # athlete.active_onboarding_thread_id was set to thread_id during start

        # Resume via start again — athlete.active_onboarding_thread_id is set
        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm("Bloc 2 resume")
            resumed = run_onboarding_start(athlete_id="a1", db=db)

        # Should resume at block 2, not start at block 1
        assert resumed["current_block"] == 2
        assert resumed["thread_id"] == thread_id
