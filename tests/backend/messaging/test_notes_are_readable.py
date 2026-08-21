"""Agent notes are working data. The athlete gets prose.

The first live plan ended with this, sent to Telegram verbatim:

    • rest: carbs=3.5g/kg protein=1.8g/kg kcal≈2467
      strength: carbs=4.5g/kg protein=1.8g/kg kcal≈2775
      endurance_short: carbs=5.5g/kg protein=1.8g/kg kcal≈3083
      endurance_long: carbs=6.5g/kg protein=1.8g/kg kcal≈3392 | intra: 45.0g/h
      race: carbs=7.0g/kg protein=1.8g/kg kcal≈3546 | intra: 75.0g/h

`_reasoning_lines` copies every agent note into the message unchanged. That
table is how NutritionCoach hands numbers to the Head Coach; it is not
something a person reads on their phone on a Sunday evening.

A coach says "glucides autour des séances de qualité". It does not read out a
spreadsheet. Notes that look like machine output are summarised; notes written
in prose pass through untouched, because those are the ones worth reading.
"""
from __future__ import annotations

import pytest
from app.messaging.plan_renderer import render_week

MACROS = (
    "rest: carbs=3.5g/kg protein=1.8g/kg kcal≈2467\n"
    "strength: carbs=4.5g/kg protein=1.8g/kg kcal≈2775\n"
    "endurance_short: carbs=5.5g/kg protein=1.8g/kg kcal≈3083\n"
    "endurance_long: carbs=6.5g/kg protein=1.8g/kg kcal≈3392 | intra: 45.0g/h\n"
    "race: carbs=7.0g/kg protein=1.8g/kg kcal≈3546 | intra: 75.0g/h"
)

PROSE = "Volume maintenu à plat — l'ACWR est en haut de la zone sûre."


def _plan(notes) -> dict:
    return {
        "phase": "competition",
        "sessions": [
            {
                "date": "2026-08-24",
                "sport": "running",
                "workout_type": "tempo",
                "duration_min": 45,
                # The renderer reads per-session detail from `notes`, not
                # `description` -- checked against render_session_line.
                "notes": "8 km @ 5:10/km",
            }
        ],
        "notes": notes,
    }


class TestMachineOutputIsNotSent:
    def test_the_macro_table_does_not_reach_the_athlete(self) -> None:
        text = render_week(_plan(MACROS))

        assert "carbs=" not in text
        assert "kcal≈" not in text
        assert "g/kg" not in text

    def test_something_useful_is_said_instead(self) -> None:
        """Dropping it silently would lose a real coaching point."""
        text = render_week(_plan(MACROS))

        assert "nutrition" in text.lower() or "glucides" in text.lower()

    @pytest.mark.parametrize(
        "note",
        [
            "acwr=1.24 status=safe",
            "vdot=43 | phase: competition | week: 1",
            "quads=88.0 calves=79.0 glutes=61.0",
        ],
    )
    def test_other_key_value_dumps_are_caught_too(self, note: str) -> None:
        text = render_week(_plan(note))

        assert "=" not in text.split("**Pourquoi cette semaine**")[-1]


class TestProseSurvives:
    def test_a_written_note_is_passed_through(self) -> None:
        text = render_week(_plan(PROSE))

        assert PROSE in text

    def test_a_mixed_list_keeps_the_prose_and_drops_the_table(self) -> None:
        text = render_week(_plan([PROSE, MACROS]))

        assert PROSE in text
        assert "carbs=" not in text

    def test_a_note_with_a_pace_is_not_mistaken_for_machine_output(self) -> None:
        """Paces and dates contain digits and colons; they are the point."""
        note = "Mercredi : 6 x 800 m @ 4:09/km, récupération 2:00."
        text = render_week(_plan(note))

        assert "4:09/km" in text

    def test_a_note_naming_a_number_in_a_sentence_survives(self) -> None:
        note = "L'ACWR est à 1.54, donc la charge ne monte pas cette semaine."
        text = render_week(_plan(note))

        assert note in text


class TestNothingBreaks:
    def test_no_notes_renders_fine(self) -> None:
        assert render_week(_plan(None))

    def test_empty_notes_render_fine(self) -> None:
        assert render_week(_plan(""))

    def test_the_sessions_are_still_there(self) -> None:
        text = render_week(_plan(MACROS))

        assert "8 km @ 5:10/km" in text
