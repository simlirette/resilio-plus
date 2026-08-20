"""Two sport vocabularies exist; the readers must accept both.

Strava emits `"Run"`, `"TrailRun"`, `"Ride"`, `"Swim"`. `activity_mapper.
SPORT_MAP` normalises those to Resilio's internal words -- `"running"`,
`"biking"`, `"swimming"` -- before writing `strava_activities`. So the same
`StravaActivity` shape carries Strava's vocabulary when it comes from the API
and Resilio's when it is rebuilt from a table row.

`estimate_vdot` filtered on `sport_type == "Run"` and `SPORT_MUSCLE_MAP` keys
on `Run`/`Ride`/`Swim`/`TrailRun`, so any caller reading rows back got zero
matches: VDOT fell to its 35.0 beginner floor and cardio strain stayed flat.
Nothing raised -- both have a valid fallback.

Fixed by accepting either vocabulary at the read points rather than adding a
reverse map at one call site, which would leave the trap set for the next one.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from app.core.running_logic import estimate_vdot
from app.schemas.connector import StravaActivity

TODAY = date(2026, 8, 20)


def _run(sport_type: str, km: float = 10.0, minutes: float = 50.0) -> StravaActivity:
    return StravaActivity(
        id="a1",
        name="Run",
        sport_type=sport_type,
        date=TODAY - timedelta(days=3),
        duration_seconds=int(minutes * 60),
        distance_meters=km * 1000,
    )


class TestVdotAcceptsBothVocabularies:
    @pytest.mark.parametrize("sport_type", ["Run", "running", "TrailRun", "VirtualRun"])
    def test_a_run_is_a_run_however_it_is_spelled(self, sport_type: str) -> None:
        result = estimate_vdot([_run(sport_type)], reference_date=TODAY)

        assert result > 35.0, f"{sport_type!r} was not recognised as a run"

    def test_both_spellings_give_the_same_answer(self) -> None:
        strava = estimate_vdot([_run("Run")], reference_date=TODAY)
        internal = estimate_vdot([_run("running")], reference_date=TODAY)

        assert strava == internal


class TestVdotStillExcludesNonRuns:
    @pytest.mark.parametrize(
        "sport_type", ["Ride", "biking", "Swim", "swimming", "WeightTraining"]
    )
    def test_other_sports_do_not_produce_a_running_vdot(self, sport_type: str) -> None:
        """A cyclist must not be handed running paces."""
        assert estimate_vdot([_run(sport_type)], reference_date=TODAY) == 35.0


class TestStrainAcceptsBothVocabularies:
    """Exact-map equality, not `> 0`.

    `SPORT_MUSCLE_MAP["__unknown__"]` carries a non-zero coefficient for every
    muscle, so a `> 0` assertion would pass on the fallback and prove nothing.
    """

    @pytest.mark.parametrize(
        "spelling,canonical",
        [
            ("Run", "Run"),
            ("running", "Run"),
            ("VirtualRun", "Run"),
            ("TrailRun", "TrailRun"),
            ("Ride", "Ride"),
            ("biking", "Ride"),
            ("EBikeRide", "Ride"),
            ("Swim", "Swim"),
            ("swimming", "Swim"),
        ],
    )
    def test_each_spelling_resolves_to_its_canonical_map(
        self, spelling: str, canonical: str
    ) -> None:
        from app.core.strain import SPORT_MUSCLE_MAP, resolve_sport

        assert resolve_sport(spelling) == SPORT_MUSCLE_MAP[canonical]

    @pytest.mark.parametrize("name", ["Kitesurf", "WeightTraining", "", "  "])
    def test_an_unmapped_sport_falls_back(self, name: str) -> None:
        from app.core.strain import SPORT_MUSCLE_MAP, resolve_sport

        assert resolve_sport(name) == SPORT_MUSCLE_MAP["__unknown__"]

    def test_the_canonical_keys_are_untouched(self) -> None:
        from app.core.strain import SPORT_MUSCLE_MAP, resolve_sport

        for key in SPORT_MUSCLE_MAP:
            assert resolve_sport(key) == SPORT_MUSCLE_MAP[key]

    def test_a_run_row_read_back_from_the_table_loads_cardio(self) -> None:
        """The end-to-end shape of the bug: DB vocabulary into the strain index."""
        from app.core.strain import compute_muscle_strain

        scores = compute_muscle_strain(
            [_run("running", km=10.0, minutes=50.0)], [], reference_date=TODAY
        )

        assert scores is not None
        assert scores.calves > 0, "a run from the table loaded no calves"
        assert scores.quads > 0
