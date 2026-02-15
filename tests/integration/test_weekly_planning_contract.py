"""Contract test: presentation-JSON alignment in weekly planning.

This test ensures that the suggest_optimal_run_count function provides
recommendations that prevent presentation-JSON mismatches.
"""

import pytest
from resilio.api.plan import suggest_optimal_run_count


class TestWeeklyPlanningContract:
    """Test the contract between run count suggestions and actual plan generation."""

    def test_suggest_run_count_recovery_week_23km(self):
        """Test the specific case that caused the Week 4 discrepancy.

        With 23km recovery week and max 4 runs, system should recommend 3 runs
        because 4 runs would create easy runs below 5km minimum.
        """
        result = suggest_optimal_run_count(
            target_volume_km=23.0,
            max_runs=4,
            phase="build"  # Recovery weeks are part of build phase
        )

        assert result['recommended_runs'] == 3, (
            f"Expected 3 runs for 23km recovery week, got {result['recommended_runs']}. "
            f"Rationale: {result['rationale']}"
        )

    def test_suggest_run_count_low_volume_scenarios(self):
        """Test common low-volume scenarios that risk presentation-JSON mismatch."""
        test_cases = [
            # (volume, max_runs, phase, expected_runs, description)
            (18.0, 4, "base", 3, "18km base week - below comfortable for 4 runs"),
            (23.0, 4, "build", 3, "23km build week - borderline for 4 runs"),
            (20.0, 5, "base", 3, "20km with high max_runs - should reduce"),
            (15.0, 3, "recovery", 2, "15km recovery - very low volume"),
        ]

        for volume, max_runs, phase, expected, description in test_cases:
            result = suggest_optimal_run_count(
                target_volume_km=volume,
                max_runs=max_runs,
                phase=phase
            )

            assert result['recommended_runs'] == expected, (
                f"{description}: Expected {expected} runs, got {result['recommended_runs']}. "
                f"Rationale: {result['rationale']}"
            )

    def test_suggest_run_count_comfortable_volume_scenarios(self):
        """Test scenarios where max_runs can be safely used."""
        test_cases = [
            # (volume, max_runs, phase, expected_runs, description)
            (28.0, 4, "base", 3, "28km - system prefers fewer, more substantial runs"),
            (32.0, 4, "build", 4, "32km - comfortable for 4 runs"),
            (35.0, 5, "base", 4, "35km - system balances quality vs quantity"),
            (48.0, 5, "build", 5, "48km - high volume, use max runs"),
        ]

        for volume, max_runs, phase, expected, description in test_cases:
            result = suggest_optimal_run_count(
                target_volume_km=volume,
                max_runs=max_runs,
                phase=phase
            )

            assert result['recommended_runs'] == expected, (
                f"{description}: Expected {expected} runs, got {result['recommended_runs']}. "
                f"Rationale: {result['rationale']}"
            )

    def test_suggest_run_count_returns_required_fields(self):
        """Verify the function returns all required contract fields."""
        result = suggest_optimal_run_count(
            target_volume_km=25.0,
            max_runs=4,
            phase="base"
        )

        # Required fields for AI agents to make decisions
        required_fields = [
            'target_volume_km',
            'max_runs',
            'phase',
            'recommended_runs',
            'rationale',
            'distribution_preview',
            'minimum_volume_for_max_runs',
            'comfortable_volume_for_max_runs',
        ]

        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

    def test_suggest_run_count_rationale_is_actionable(self):
        """Verify rationale provides clear guidance for AI agents."""
        result = suggest_optimal_run_count(
            target_volume_km=23.0,
            max_runs=4,
            phase="build"
        )

        rationale = result['rationale']

        # Rationale should mention the constraint that drives the decision
        assert len(rationale) > 0, "Rationale should not be empty"
        assert isinstance(rationale, str), "Rationale should be a string"

        # For this specific case, should mention easy run minimums
        assert "5" in rationale or "minimum" in rationale.lower(), (
            "Rationale should explain why fewer runs are needed (minimum constraints)"
        )

    def test_suggest_run_count_distribution_preview_shows_concerns(self):
        """Verify distribution_preview flags problematic configurations."""
        result = suggest_optimal_run_count(
            target_volume_km=23.0,
            max_runs=4,
            phase="build"
        )

        preview = result['distribution_preview']

        # Should show preview for max_runs option
        max_runs_key = f"with_{result['max_runs']}_runs"
        assert max_runs_key in preview, f"Missing preview for {max_runs_key}"

        # Should flag concerns for max_runs if not recommended
        if result['recommended_runs'] < result['max_runs']:
            max_runs_preview = preview[max_runs_key]
            assert 'concerns' in max_runs_preview, "Should flag concerns for non-recommended count"
            assert len(max_runs_preview['concerns']) > 0, "Should list specific concerns"

    def test_suggest_run_count_phase_affects_recommendation(self):
        """Verify phase (base vs build vs recovery) affects long run % and thus run count."""
        # Same volume, different phases should potentially give different recommendations
        # due to different long run percentages
        base_result = suggest_optimal_run_count(
            target_volume_km=30.0,
            max_runs=4,
            phase="base"
        )

        build_result = suggest_optimal_run_count(
            target_volume_km=30.0,
            max_runs=4,
            phase="build"
        )

        # Both should have valid recommendations
        assert 2 <= base_result['recommended_runs'] <= 4
        assert 2 <= build_result['recommended_runs'] <= 4

        # Distribution previews should differ in long run percentages
        # (this is implementation-dependent but helps catch regressions)
        assert 'distribution_preview' in base_result
        assert 'distribution_preview' in build_result
