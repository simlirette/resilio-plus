"""
SwimmingPrescriber — calcul déterministe des séances natation CSS.

Basé sur la CSS (Critical Swim Speed) et les zones d'intensité associées.
Aucun appel réseau — pur calcul, entièrement testable hors LLM.
"""


class SwimmingPrescriber:
    """Prescrit des séances natation à partir du profil natation de l'athlète."""

    # CSS par défaut selon niveau technique (s/100m)
    _CSS_DEFAULTS = {
        "beginner": 150.0,
        "intermediate": 110.0,
        "advanced": 90.0,
    }

    # Distance de base par niveau technique (m par session)
    _BASE_DISTANCE = {
        "beginner": 1000,
        "intermediate": 1800,
        "advanced": 2500,
    }

    # Multiplicateurs intermédiaire/avancé (rapportés au beginner)
    _DISTANCE_MULTIPLIERS = {
        "beginner": 1.0,
        "intermediate": 1.8,
        "advanced": 2.5,
    }

    # Types de session (cyclés pour les semaines multi-sessions)
    _SESSION_TYPES = ["technique", "aerobic_endurance", "threshold"]

    # Coaching cues par type de session et niveau
    _COACHING_CUES = {
        "technique": [
            "Doigts joints, pouce vers le bas à l'entrée",
            "Rotation hanches 45° sur chaque traction",
        ],
        "aerobic_endurance": [
            "Expiration continue sous l'eau",
            "Tête basse, regard vers le fond",
        ],
        "threshold": [
            "Tempo de nage régulier",
            "Tempo bras à maintenir malgré la fatigue",
        ],
    }

    def prescribe(self, view: dict) -> dict:
        """
        Prescrit un plan natation hebdomadaire.

        Args:
            view: vue filtrée Swimming Coach (retournée par _swimming_view).

        Returns:
            {
              "agent": "swimming_coach",
              "technique_level": str,
              "css_sec_per_100m": float,
              "weekly_volume_km": float,
              "sessions": list,
              "coaching_notes": [],
              "notes": "",   # rempli par SwimmingCoachAgent
            }
        """
        profile = view.get("swimming_profile", {})
        reference_times = profile.get("reference_times", {})
        technique_level = profile.get("technique_level", "beginner")
        weekly_volume_km = profile.get("weekly_volume_km", 0.0)

        css = self._calculate_css(reference_times, technique_level)
        session_count = self._session_count(weekly_volume_km)
        sessions = self._build_sessions(session_count, technique_level, css)

        return {
            "agent": "swimming_coach",
            "technique_level": technique_level,
            "css_sec_per_100m": css,
            "weekly_volume_km": weekly_volume_km,
            "sessions": sessions,
            "coaching_notes": [],
            "notes": "",
        }

    # ── CSS Calculation ──────────────────────────────────────────────────────

    def _calculate_css(self, reference_times: dict, technique_level: str) -> float:
        """
        Calcule la CSS en s/100m.

        Si reference_times contient '200m' et '400m' (en minutes), utilise la formule :
            css_m_per_s = (400 - 200) / ((t400_min - t200_min) * 60)
            css_sec_per_100m = 100 / css_m_per_s

        Sinon, utilise les valeurs par défaut selon le niveau technique.
        """
        if "200m" in reference_times and "400m" in reference_times:
            t200_min = reference_times["200m"]
            t400_min = reference_times["400m"]
            delta_seconds = (t400_min - t200_min) * 60.0
            if delta_seconds > 0:
                css_m_per_s = (400 - 200) / delta_seconds
                css_sec_per_100m = 100.0 / css_m_per_s
                return round(css_sec_per_100m, 2)

        return self._CSS_DEFAULTS.get(technique_level, 150.0)

    # ── Session Count ────────────────────────────────────────────────────────

    def _session_count(self, weekly_volume_km: float) -> int:
        """Détermine le nombre de sessions selon le volume hebdomadaire."""
        if weekly_volume_km <= 0:
            return 0
        if weekly_volume_km <= 1.5:
            return 1
        if weekly_volume_km <= 3.0:
            return 2
        if weekly_volume_km <= 5.0:
            return 3
        return 4

    # ── Session Building ─────────────────────────────────────────────────────

    def _build_sessions(
        self, count: int, technique_level: str, css: float
    ) -> list:
        """Construit la liste de sessions selon le nombre et le niveau."""
        sessions = []
        for i in range(count):
            session_type = self._SESSION_TYPES[i % len(self._SESSION_TYPES)]
            session = self._build_session(i + 1, session_type, technique_level, css)
            sessions.append(session)
        return sessions

    def _build_session(
        self, session_number: int, session_type: str, technique_level: str, css: float
    ) -> dict:
        """Construit une session avec ses sets."""
        multiplier = self._DISTANCE_MULTIPLIERS.get(technique_level, 1.0)
        sets = self._build_sets(session_type, technique_level, css, multiplier)
        total_distance = sum(
            s["distance_m"] * (s["reps"] if s["reps"] else 1) for s in sets
        )
        return {
            "session_number": session_number,
            "session_type": session_type,
            "total_distance_m": total_distance,
            "css_target_sec_per_100m": css,
            "sets": sets,
            "coaching_cues": self._COACHING_CUES[session_type],
        }

    def _round_to_50(self, value: float) -> int:
        """Arrondit à la dizaine de 50m la plus proche."""
        return max(50, round(value / 50) * 50)

    def _build_sets(
        self, session_type: str, technique_level: str, css: float, multiplier: float
    ) -> list:
        """Construit les sets selon le type de session."""
        if session_type == "technique":
            return self._technique_sets(css, multiplier)
        if session_type == "aerobic_endurance":
            return self._aerobic_sets(css, multiplier)
        # threshold
        return self._threshold_sets(css, multiplier)

    def _technique_sets(self, css: float, multiplier: float) -> list:
        """
        Session technique :
        - warmup: 200m, Z1
        - drill: 4×50m, Z2, rest=30s
        - main: 4×100m, Z3 (CSS +5s/100m), rest=20s
        - cooldown: 200m, Z1
        """
        base_warmup = 200
        base_drill = 50
        base_main = 100
        base_cooldown = 200
        base_drill_reps = 4
        base_main_reps = 4

        warmup_m = self._round_to_50(base_warmup * multiplier) if multiplier != 1.0 else base_warmup
        drill_m = self._round_to_50(base_drill * multiplier) if multiplier != 1.0 else base_drill
        main_m = self._round_to_50(base_main * multiplier) if multiplier != 1.0 else base_main
        cooldown_m = self._round_to_50(base_cooldown * multiplier) if multiplier != 1.0 else base_cooldown

        drill_reps = round(base_drill_reps * multiplier) if multiplier != 1.0 else base_drill_reps
        main_reps = round(base_main_reps * multiplier) if multiplier != 1.0 else base_main_reps

        return [
            {
                "type": "warmup",
                "distance_m": warmup_m,
                "pace_zone": "Z1",
                "reps": None,
                "rest_seconds": None,
                "description": "Crawl, respiration tous les 3 temps",
            },
            {
                "type": "drill",
                "distance_m": drill_m,
                "pace_zone": "Z2",
                "reps": drill_reps,
                "rest_seconds": 30,
                "description": "Catch-up drill — bras en extension avant traction",
            },
            {
                "type": "main",
                "distance_m": main_m,
                "pace_zone": "Z3",
                "reps": main_reps,
                "rest_seconds": 20,
                "description": "Technique crawl — focus allongement",
            },
            {
                "type": "cooldown",
                "distance_m": cooldown_m,
                "pace_zone": "Z1",
                "reps": None,
                "rest_seconds": None,
                "description": "Dos crawlé souple",
            },
        ]

    def _aerobic_sets(self, css: float, multiplier: float) -> list:
        """
        Session aérobie endurance :
        - warmup: 200m, Z1
        - main: 4×150m, Z2 (CSS +10s/100m), rest=30s
        - cooldown: 200m, Z1
        """
        base_warmup = 200
        base_main = 150
        base_cooldown = 200
        base_main_reps = 4

        warmup_m = self._round_to_50(base_warmup * multiplier) if multiplier != 1.0 else base_warmup
        main_m = self._round_to_50(base_main * multiplier) if multiplier != 1.0 else base_main
        cooldown_m = self._round_to_50(base_cooldown * multiplier) if multiplier != 1.0 else base_cooldown
        main_reps = round(base_main_reps * multiplier) if multiplier != 1.0 else base_main_reps

        return [
            {
                "type": "warmup",
                "distance_m": warmup_m,
                "pace_zone": "Z1",
                "reps": None,
                "rest_seconds": None,
                "description": "Crawl souple, réveil musculaire",
            },
            {
                "type": "main",
                "distance_m": main_m,
                "pace_zone": "Z2",
                "reps": main_reps,
                "rest_seconds": 30,
                "description": "Pace aérobie — confort absolu",
            },
            {
                "type": "cooldown",
                "distance_m": cooldown_m,
                "pace_zone": "Z1",
                "reps": None,
                "rest_seconds": None,
                "description": "Retour au calme",
            },
        ]

    def _threshold_sets(self, css: float, multiplier: float) -> list:
        """
        Session threshold :
        - warmup: 200m, Z1
        - main: 3×200m, Z3 (CSS ±3s/100m), rest=45s
        - cooldown: 200m, Z1
        """
        base_warmup = 200
        base_main = 200
        base_cooldown = 200
        base_main_reps = 3

        warmup_m = self._round_to_50(base_warmup * multiplier) if multiplier != 1.0 else base_warmup
        main_m = self._round_to_50(base_main * multiplier) if multiplier != 1.0 else base_main
        cooldown_m = self._round_to_50(base_cooldown * multiplier) if multiplier != 1.0 else base_cooldown
        main_reps = round(base_main_reps * multiplier) if multiplier != 1.0 else base_main_reps

        return [
            {
                "type": "warmup",
                "distance_m": warmup_m,
                "pace_zone": "Z1",
                "reps": None,
                "rest_seconds": None,
                "description": "Crawl souple, activation progressive",
            },
            {
                "type": "main",
                "distance_m": main_m,
                "pace_zone": "Z3",
                "reps": main_reps,
                "rest_seconds": 45,
                "description": "Pace CSS — effort soutenu",
            },
            {
                "type": "cooldown",
                "distance_m": cooldown_m,
                "pace_zone": "Z1",
                "reps": None,
                "rest_seconds": None,
                "description": "Récupération active",
            },
        ]
