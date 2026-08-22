"""Resilio must not send an athlete shopping for a paid API it does not need.

Simon, live on 2026-08-22: "Pourquoi le bot me demande la Terra connection?"

`pending_providers` returns every entry of `SUPPORTED_PROVIDERS` the athlete
has not connected. He had Strava, Hevy and Google — so the one name left was
Terra, and the invitation contained that single line. Tapping it lands on a
form asking for "the Terra user id from the Terra dashboard", which requires a
paid Terra account he has no reason to open.

Terra supplies exactly two signals: `hrv_rmssd` and `sleep_duration_hours`.
Apple Health supplies both from the athlete's own phone, for free, and since
2026-08-21 `compute_jobs._recovery_records` reads it. Terra is also absent from
the athlete's own goal document, which names "Strava, Hevy, Apple Health".

So the recovery source that works was never offered, and the one that costs
money and does not apply was the only thing offered. The connector code stays —
it works, and a future athlete may arrive with Terra already set up — but
nothing proposes it unprompted any more.
"""
from __future__ import annotations

import pytest

from app.services.deep_link_service import (
    SUPPORTED_PROVIDERS,
    UnsupportedProviderError,
    issue_link,
)


class TestWhatIsOffered:
    def test_terra_is_not_in_the_offered_providers(self) -> None:
        assert "terra" not in SUPPORTED_PROVIDERS

    def test_the_three_the_athlete_actually_uses_are(self) -> None:
        assert set(SUPPORTED_PROVIDERS) == {"strava", "hevy", "google"}

    def test_a_terra_link_can_no_longer_be_minted(self) -> None:
        """Not offering it but still minting it would be the same trap, quieter."""
        with pytest.raises(UnsupportedProviderError):
            issue_link(object(), athlete_id="a1", provider="terra")


class TestTheGapIsStillNamed:
    """Removing Terra without naming Apple Health leaves recovery unreachable.

    Stated as a fact about how the system works, not as an instruction to go
    ask for it — the same rule the rest of the facts block follows.
    """

    def _run(self, invitation: str | None) -> str:
        from unittest.mock import patch

        from app.services.coach_tools import ToolContext, run_tool

        with patch(
            "app.services.deep_link_service.connector_links_message",
            return_value=invitation,
        ):
            return run_tool(
                "offer_connector_links", {}, ToolContext(athlete_id="a1", db=object())
            ).content

    def test_it_is_named_alongside_the_links(self) -> None:
        assert "Apple Health" in self._run("**Connecte tes données**\n\n- Strava: http://x")

    def test_it_is_named_when_there_is_nothing_left_to_link(self) -> None:
        """The case Simon was in: everything linkable already connected."""
        assert "Apple Health" in self._run(None)

    def test_the_links_are_not_dropped(self) -> None:
        assert "http://x" in self._run("**Connecte tes données**\n\n- Strava: http://x")
