from app.messaging.plan_renderer import SPORT_EMOJI, render_session_line, render_week

PLAN = {
    "phase": "build",
    "acwr": {
        "ratio": 1.12,
        "status": "safe",
        "acute_7d": 420.0,
        "chronic_28d": 375.0,
        "max_safe_weekly_load": 487.5,
    },
    "global_fatigue": {
        "local_muscular": 48.0,
        "cns_load": 33.0,
        "metabolic_cost": 41.0,
        "recovery_hours": 26.0,
        "affected_muscles": ["quads", "calves"],
    },
    "conflicts": [
        {
            "severity": "warning",
            "rule": "heavy_legs_before_intervals",
            "agents": ["lifting", "running"],
            "message": "Squats Tuesday compress Wednesday's intervals.",
        }
    ],
    "sessions": [
        {
            "id": "slot-1",
            "date": "2031-05-05",
            "sport": "running",
            "workout_type": "tempo",
            "duration_min": 60,
            "fatigue_score": {
                "local_muscular": 40.0,
                "cns_load": 30.0,
                "metabolic_cost": 55.0,
                "recovery_hours": 20.0,
                "affected_muscles": ["quads"],
            },
            "notes": "8 km @ 4:35/km",
        },
        {
            "id": "slot-2",
            "date": "2031-05-07",
            "sport": "lifting",
            "workout_type": "lower_strength",
            "duration_min": 75,
            "fatigue_score": {
                "local_muscular": 65.0,
                "cns_load": 55.0,
                "metabolic_cost": 25.0,
                "recovery_hours": 40.0,
                "affected_muscles": ["quads", "glutes"],
            },
            "notes": "",
        },
    ],
    "readiness_level": "green",
    "notes": ["Volume held flat — ACWR near the top of the safe band."],
}


class TestRenderWeek:
    def test_lists_every_session_grouped_by_day(self) -> None:
        text = render_week(PLAN)

        assert "Monday 05 May" in text
        assert "Wednesday 07 May" in text
        assert "tempo" in text
        assert "lower_strength" in text
        assert "60 min" in text
        assert "75 min" in text

    def test_includes_sport_emoji(self) -> None:
        text = render_week(PLAN)
        assert SPORT_EMOJI["running"] in text
        assert SPORT_EMOJI["lifting"] in text

    def test_includes_reasoning_not_only_sessions(self) -> None:
        text = render_week(PLAN)

        assert "1.12" in text
        assert "build" in text
        assert "Squats Tuesday compress Wednesday's intervals." in text
        assert "Volume held flat" in text

    def test_reports_weekly_totals(self) -> None:
        text = render_week(PLAN)
        assert "2 sessions" in text
        assert "2h15" in text

    def test_notes_render_when_present(self) -> None:
        text = render_week(PLAN)
        assert "8 km @ 4:35/km" in text

    def test_empty_plan_states_rest_week(self) -> None:
        text = render_week({"phase": "recovery", "sessions": []})
        assert "No sessions" in text

    def test_handles_missing_optional_blocks(self) -> None:
        text = render_week({"sessions": PLAN["sessions"]})
        assert "tempo" in text

    def test_none_plan_is_reported_not_crashed(self) -> None:
        assert "No plan" in render_week(None)

    def test_degraded_sources_are_surfaced(self) -> None:
        text = render_week(PLAN, degraded_sources=["hevy"])
        assert "hevy" in text.lower()


class TestRenderSessionLine:
    def test_unknown_sport_falls_back_to_a_neutral_marker(self) -> None:
        line = render_session_line(
            {
                "sport": "rowing",
                "workout_type": "steady",
                "duration_min": 30,
                "notes": "",
            }
        )
        assert "steady" in line
        assert "30 min" in line


class TestMultiLineNotes:
    """Agent notes are sometimes several lines — they must stay one bullet.

    The nutrition coach emits per-day-type targets as a multi-line block; a live
    plan on 2026-08-20 rendered it as orphan lines under a stray bullet.
    """

    MULTI = (
        "rest: carbs=3.5g/kg protein=1.8g/kg\n"
        "strength: carbs=4.5g/kg protein=1.8g/kg\n"
        "race: carbs=7.0g/kg protein=1.8g/kg"
    )

    def test_extra_lines_are_indented_under_their_bullet(self) -> None:
        text = render_week({**PLAN, "notes": [self.MULTI]})

        assert "- rest: carbs=3.5g/kg protein=1.8g/kg" in text
        assert "  strength: carbs=4.5g/kg protein=1.8g/kg" in text
        assert "\nstrength:" not in text

    def test_only_one_bullet_is_opened_per_note(self) -> None:
        text = render_week({**PLAN, "notes": [self.MULTI]})

        why = text.split("**Why this week**", 1)[1]
        assert why.count("- rest:") == 1
        assert "- strength:" not in why

    def test_a_single_line_note_is_unchanged(self) -> None:
        text = render_week({**PLAN, "notes": ["Volume held flat."]})
        assert "- Volume held flat." in text

    def test_blank_lines_inside_a_note_are_dropped(self) -> None:
        text = render_week({**PLAN, "notes": ["first\n\n\nsecond"]})

        assert "- first" in text
        assert "  second" in text
        assert "\n\n  second" not in text

    def test_an_all_whitespace_note_produces_no_bullet(self) -> None:
        text = render_week({**PLAN, "notes": ["   \n  \n"]})
        assert "-  " not in text
