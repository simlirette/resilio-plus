"""
RecoveryPrescriber — calcul déterministe du Readiness Score.

Formule complète définie dans recovery_coach_system_prompt.md.
Aucun appel réseau — pur calcul, entièrement testable hors LLM.
"""


class RecoveryPrescriber:
    """Calcule le Readiness Score (0–100) à partir de 5 facteurs biométriques pondérés."""

    _HRV_W = 0.30
    _SLEEP_W = 0.25
    _ACWR_W = 0.25
    _HR_W = 0.10
    _SUBJ_W = 0.10

    def evaluate(self, view: dict) -> dict:
        """
        Calcule le Readiness Score et émet le verdict gate keeper.

        Args:
            view: vue filtrée Recovery Coach (retournée par _recovery_view).

        Returns:
            {
              "agent": "recovery_coach",
              "readiness_score": float (0-100),
              "color": "green" | "yellow" | "red",
              "factors": {hrv_score, sleep_score, acwr_score, hr_rest_score, subjective_score},
              "modification_params": {intensity_reduction_pct, tier_max, volume_reduction_pct},
              "overtraining_alert": bool,
              "notes": "",   # rempli par RecoveryCoachAgent
            }
        """
        fatigue = view.get("fatigue", {})
        identity = view.get("identity", {})

        hrv_score = self._hrv_score(
            fatigue.get("hrv_rmssd_today"),
            fatigue.get("hrv_rmssd_baseline"),
        )
        sleep_score = self._sleep_score(
            fatigue.get("sleep_hours_last_night"),
            fatigue.get("sleep_quality_subjective"),
        )
        acwr_score = self._acwr_score(fatigue.get("acwr"))
        hr_rest_score = self._hr_rest_score(
            fatigue.get("hr_rest_today"),
            identity.get("resting_hr"),
        )
        subjective_score = self._subjective_score(fatigue.get("fatigue_subjective"))

        readiness_score = round(
            self._HRV_W * hrv_score
            + self._SLEEP_W * sleep_score
            + self._ACWR_W * acwr_score
            + self._HR_W * hr_rest_score
            + self._SUBJ_W * subjective_score,
            1,
        )

        color = self._color(readiness_score)

        return {
            "agent": "recovery_coach",
            "readiness_score": readiness_score,
            "color": color,
            "factors": {
                "hrv_score": hrv_score,
                "sleep_score": sleep_score,
                "acwr_score": acwr_score,
                "hr_rest_score": hr_rest_score,
                "subjective_score": subjective_score,
            },
            "modification_params": self._modification_params(color),
            "overtraining_alert": self._overtraining_alert(
                fatigue.get("acwr"),
                fatigue.get("hrv_rmssd_today"),
                fatigue.get("hrv_rmssd_baseline"),
            ),
            "notes": "",
        }

    # ── Facteurs ────────────────────────────────────────────────────────────

    def _hrv_score(self, today: float | None, baseline: float | None) -> float:
        """HRV Score (30%) — RMSSD aujourd'hui vs baseline 7 jours."""
        if today is None or baseline is None or baseline == 0:
            return 50.0
        ratio = today / baseline
        if ratio >= 1.0:
            return 100.0
        if ratio >= 0.85:
            return 75.0
        if ratio >= 0.70:
            return 50.0
        return 25.0

    def _sleep_score(self, hours: float | None, quality: int | None) -> float:
        """Sleep Score (25%) — durée + qualité subjective (1-10)."""
        if hours is None or quality is None:
            return 50.0
        if hours >= 8 and quality >= 8:
            return 100.0
        if hours >= 7 and quality >= 7:
            return 80.0
        # 6-7h OU qualité 5-6 : évaluation top-down, premier match
        if (6 <= hours < 7) or (5 <= quality <= 6):
            return 50.0
        return 20.0

    def _acwr_score(self, acwr: float | None) -> float:
        """ACWR Score (25%) — ratio charge aiguë / chronique global."""
        if acwr is None:
            return 70.0
        if 0.8 <= acwr <= 1.3:
            return 100.0
        if (0.7 <= acwr < 0.8) or (1.3 < acwr <= 1.4):
            return 70.0
        if acwr > 1.5:
            return 0.0
        # acwr < 0.7 OU 1.4 < acwr <= 1.5
        return 40.0

    def _hr_rest_score(self, today: int | None, baseline: int | None) -> float:
        """HR Rest Score (10%) — FC repos aujourd'hui vs baseline profil."""
        if today is None or baseline is None:
            return 100.0  # neutre — pas de pénalité sans données
        diff = today - baseline
        if diff <= 0:
            return 100.0
        if diff <= 3:
            return 70.0
        if diff <= 6:
            return 40.0
        return 10.0

    def _subjective_score(self, value: int | None) -> float:
        """Subjective Fatigue Score (10%) — échelle 1-10."""
        if value is None:
            return 70.0
        if value <= 3:
            return 100.0
        if value <= 5:
            return 70.0
        if value <= 7:
            return 40.0
        return 10.0

    # ── Verdict ─────────────────────────────────────────────────────────────

    def _color(self, score: float) -> str:
        if score >= 75:
            return "green"
        if score >= 50:
            return "yellow"
        return "red"

    def _modification_params(self, color: str) -> dict:
        if color == "green":
            return {"intensity_reduction_pct": 0, "tier_max": 3, "volume_reduction_pct": 0}
        if color == "yellow":
            return {"intensity_reduction_pct": 15, "tier_max": 1, "volume_reduction_pct": 0}
        return {"intensity_reduction_pct": 100, "tier_max": 0, "volume_reduction_pct": 100}

    def _overtraining_alert(
        self,
        acwr: float | None,
        hrv_today: float | None,
        hrv_baseline: float | None,
    ) -> bool:
        """Détecte signaux de surentraînement point-in-time (sans historique multi-jours)."""
        if acwr is not None and acwr > 1.5:
            return True
        if (
            hrv_today is not None
            and hrv_baseline is not None
            and hrv_baseline > 0
            and hrv_today / hrv_baseline < 0.70
        ):
            return True
        return False
