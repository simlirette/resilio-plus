"""What the coach thinks is not what the athlete reads.

Verbatim from the first live conversation, sent to the athlete on Telegram:

    Profil reçu depuis l'onboarding :
    • Âge : 24 ans
    ...
    Ces données sont déjà enregistrées. Rien à collecter ici.
    ---
    Message à l'athlète :
    Ton profil de base est enregistré — 24 ans, 77,1 kg...

and, in a later message:

    Athlete #1a2d73d5 — Profil initial

The model produced its working notes and the reply, and everything was
forwarded. The athlete saw the machinery, an internal row identifier, and a
literal "Message à l'athlète:" label announcing where the real answer began.

Two layers here, on purpose. The *contract* asks the model to mark the part
meant for the athlete, which handles the common case. The *scrubber* runs
regardless, because a model that ignores the contract must not be able to leak
an identifier -- and a guard that only works when the model cooperates is not
a guard.
"""
from __future__ import annotations

import pytest
from app.services.reply import athlete_facing

UUID = "1a2d73d5-4f40-4201-a5b9-af19773206bf"


class TestTheContract:
    def test_the_marked_section_is_what_survives(self) -> None:
        raw = (
            "<reasoning>Le profil est complet, rien à collecter.</reasoning>\n"
            "<message>Ton profil est enregistré. On passe à la suite.</message>"
        )

        assert athlete_facing(raw) == "Ton profil est enregistré. On passe à la suite."

    def test_text_outside_the_marked_section_is_dropped(self) -> None:
        raw = (
            "Analyse interne : bloc 2 déjà rempli.\n"
            "<message>Quel est ton chrono récent ?</message>\n"
            "Note : relancer si pas de réponse."
        )

        assert athlete_facing(raw) == "Quel est ton chrono récent ?"

    def test_an_unmarked_reply_is_passed_through(self) -> None:
        """The contract is a hint, not a requirement -- most replies are clean."""
        raw = "Ta séance de jeudi passe en Z1."

        assert athlete_facing(raw) == "Ta séance de jeudi passe en Z1."

    def test_an_empty_marked_section_falls_back_to_the_whole_reply(self) -> None:
        raw = "Ta séance de jeudi passe en Z1.\n<message></message>"

        assert "Z1" in athlete_facing(raw)


class TestTheLegacySeparator:
    """The observed failure used a prose label, not tags."""

    @pytest.mark.parametrize(
        "label",
        [
            "Message à l'athlète :",
            "Message à l'athlète:",
            "message à l'athlete :",
            "Message to athlete:",
        ],
    )
    def test_everything_before_the_label_is_dropped(self, label: str) -> None:
        raw = (
            "Profil reçu depuis l'onboarding :\n"
            "Ces données sont déjà enregistrées. Rien à collecter ici.\n"
            "---\n"
            f"{label}\n"
            "Ton profil de base est enregistré."
        )

        result = athlete_facing(raw)

        assert result == "Ton profil de base est enregistré."
        assert "Rien à collecter" not in result


class TestTheScrubber:
    """Runs whether or not the model honoured the contract."""

    def test_an_athlete_row_identifier_never_reaches_the_athlete(self) -> None:
        raw = f"Athlete #{UUID} — Profil initial\n\nTa semaine est prête."

        result = athlete_facing(raw)

        assert UUID not in result
        assert "Athlete #" not in result
        assert "Ta semaine est prête." in result

    def test_a_short_id_form_is_caught_too(self) -> None:
        raw = "Athlete #1a2d73d5 — Profil initial\n\nTa semaine est prête."

        assert "1a2d73d5" not in athlete_facing(raw)

    def test_a_bare_uuid_anywhere_is_removed(self) -> None:
        raw = f"Analyse pour {UUID} terminée. Ta séance tient."

        result = athlete_facing(raw)

        assert UUID not in result
        assert "Ta séance tient." in result

    def test_a_thread_identifier_is_removed(self) -> None:
        raw = f"thread {UUID}:onboarding:abc\n\nOn continue."

        assert UUID not in athlete_facing(raw)

    def test_ordinary_numbers_are_untouched(self) -> None:
        """Paces, distances and dates must survive intact."""
        raw = "6 x 800 m @ 4:09/km, semi le 19 septembre 2026, VDOT 43."

        assert athlete_facing(raw) == raw


class TestDegradation:
    def test_an_empty_reply_stays_empty(self) -> None:
        assert athlete_facing("") == ""

    def test_a_reply_that_is_only_scaffolding_is_not_blanked(self) -> None:
        """Sending something imperfect beats sending nothing at all."""
        raw = f"Athlete #{UUID}"

        result = athlete_facing(raw)

        assert UUID not in result

    def test_whitespace_is_tidied(self) -> None:
        raw = "<message>\n\n  Ta séance tient.  \n\n</message>"

        assert athlete_facing(raw) == "Ta séance tient."
