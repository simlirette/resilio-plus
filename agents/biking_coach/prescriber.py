"""
BikingPrescriber — calcul déterministe des séances vélo (Coggan FTP zones).

Aucun appel réseau — pur calcul, entièrement testable hors LLM.
"""


class BikingPrescriber:
    """Prescrit des séances vélo à partir du profil cycliste de l'athlète."""

    # Zones Coggan 7 — bornes en % FTP
    _ZONES = {
        "Z1": (0.0,   0.55),   # Active Recovery
        "Z2": (0.55,  0.75),   # Endurance
        "Z3": (0.75,  0.90),   # Tempo
        "Z4": (0.90,  1.05),   # Lactate Threshold
        "Z5": (1.05,  1.20),   # VO2max
        "Z6": (1.20,  1.50),   # Anaerobic
        "Z7": (1.50,  9.99),   # Neuromuscular
    }

    # RPE par zone (si FTP inconnu)
    _RPE = {
        "Z1": "RPE 2-3/10",
        "Z2": "RPE 4-5/10",
        "Z3": "RPE 6-7/10",
        "Z4": "RPE 7-8/10",
        "Z5": "RPE 8-9/10",
        "Z6": "RPE 9-10/10",
        "Z7": "RPE 10/10",
    }

    # TSS/h par zone dominante
    _TSS_PER_HOUR = {
        "Z1": 30,
        "Z2": 50,
        "Z3": 70,
        "Z4": 90,
        "Z5": 110,
        "Z6": 130,
        "Z7": 150,
    }

    # Cycle de types de sessions
    _SESSION_TYPES = ["endurance", "tempo", "vo2max"]

    def prescribe(self, view: dict) -> dict:
        """
        Prescrit un plan vélo hebdomadaire.

        Args:
            view: vue filtrée Biking Coach (retournée par _biking_view).

        Returns:
            {
              "agent": "biking_coach",
              "ftp_watts": float | None,
              "weekly_volume_km": float,
              "sessions": list,
              "coaching_notes": [],
              "notes": "",   # rempli par BikingCoachAgent
            }
        """
        profile = view.get("biking_profile", {})
        ftp_watts = profile.get("ftp_watts", None)
        weekly_volume_km = float(profile.get("weekly_volume_km", 0.0))

        session_count = self._session_count(weekly_volume_km)
        sessions = self._build_sessions(session_count, ftp_watts, weekly_volume_km)

        return {
            "agent": "biking_coach",
            "ftp_watts": ftp_watts,
            "weekly_volume_km": weekly_volume_km,
            "sessions": sessions,
            "coaching_notes": [],
            "notes": "",
        }

    # ── Zone target ──────────────────────────────────────────────────────────

    def _zone_target(self, zone: str, ftp_watts: float | None) -> str:
        """
        Retourne la cible de puissance (watts ou RPE) pour une zone donnée.

        Si ftp_watts est None : retourne le label RPE.
        Sinon : calcule la plage en watts avec int() (floor) pour éviter
                le banker's rounding de Python.
        """
        if ftp_watts is None:
            return self._RPE.get(zone, "RPE N/A")

        lower_pct, upper_pct = self._ZONES.get(zone, (0.0, 1.0))
        low_w = int(ftp_watts * lower_pct)
        high_w = int(ftp_watts * upper_pct)
        return f"{low_w}–{high_w} W"

    # ── Session count ────────────────────────────────────────────────────────

    def _session_count(self, weekly_volume_km: float) -> int:
        """Détermine le nombre de sessions selon le volume hebdomadaire (km)."""
        if weekly_volume_km <= 0:
            return 0
        if weekly_volume_km <= 30:
            return 1
        if weekly_volume_km <= 80:
            return 2
        if weekly_volume_km <= 150:
            return 3
        return 4

    # ── Session building ─────────────────────────────────────────────────────

    def _build_sessions(
        self, count: int, ftp_watts: float | None, weekly_volume_km: float
    ) -> list:
        """Construit la liste de sessions (cycle endurance → tempo → vo2max)."""
        sessions = []
        for i in range(count):
            session_type = self._SESSION_TYPES[i % len(self._SESSION_TYPES)]
            session = self._build_session(i + 1, session_type, ftp_watts, weekly_volume_km)
            sessions.append(session)
        return sessions

    def _build_session(
        self,
        session_number: int,
        session_type: str,
        ftp_watts: float | None,
        weekly_volume_km: float,
    ) -> dict:
        """Construit une session selon son type."""
        if session_type == "endurance":
            return self._endurance_session(session_number, ftp_watts, weekly_volume_km)
        if session_type == "tempo":
            return self._tempo_session(session_number, ftp_watts)
        # vo2max
        return self._vo2max_session(session_number, ftp_watts)

    # ── Session templates ────────────────────────────────────────────────────

    def _endurance_session(
        self, session_number: int, ftp_watts: float | None, weekly_volume_km: float
    ) -> dict:
        """
        Session endurance :
        - 60 min si volume < 30 km, 90 min sinon
        - Z1 warmup 10min → Z2 body → Z1 cooldown 10min
        """
        short = weekly_volume_km < 30
        z2_minutes = 45 if short else 70

        blocks = [
            {
                "zone": "Z1",
                "duration_minutes": 10,
                "watts_or_rpe": self._zone_target("Z1", ftp_watts),
                "description": "Échauffement progressif",
            },
            {
                "zone": "Z2",
                "duration_minutes": z2_minutes,
                "watts_or_rpe": self._zone_target("Z2", ftp_watts),
                "description": "Endurance aérobie, cadence régulière",
            },
            {
                "zone": "Z1",
                "duration_minutes": 10,
                "watts_or_rpe": self._zone_target("Z1", ftp_watts),
                "description": "Récupération active",
            },
        ]

        total_minutes = sum(b["duration_minutes"] for b in blocks)

        return {
            "session_number": session_number,
            "session_type": "endurance",
            "duration_minutes": total_minutes,
            "tss_estimated": self._compute_tss(blocks),
            "blocks": blocks,
            "coaching_notes_session": (
                "Maintenir cadence 85-95 rpm. Pas de pointe de puissance."
            ),
        }

    def _tempo_session(self, session_number: int, ftp_watts: float | None) -> dict:
        """
        Session tempo :
        Z1 10min → Z3 15min → Z2 5min → Z3 15min → Z2 5min → Z3 15min → Z1 10min
        Total : 75 min
        """
        blocks = [
            {
                "zone": "Z1",
                "duration_minutes": 10,
                "watts_or_rpe": self._zone_target("Z1", ftp_watts),
                "description": "Échauffement",
            },
            {
                "zone": "Z3",
                "duration_minutes": 15,
                "watts_or_rpe": self._zone_target("Z3", ftp_watts),
                "description": "Bloc tempo 1",
            },
            {
                "zone": "Z2",
                "duration_minutes": 5,
                "watts_or_rpe": self._zone_target("Z2", ftp_watts),
                "description": "Récupération active",
            },
            {
                "zone": "Z3",
                "duration_minutes": 15,
                "watts_or_rpe": self._zone_target("Z3", ftp_watts),
                "description": "Bloc tempo 2",
            },
            {
                "zone": "Z2",
                "duration_minutes": 5,
                "watts_or_rpe": self._zone_target("Z2", ftp_watts),
                "description": "Récupération active",
            },
            {
                "zone": "Z3",
                "duration_minutes": 15,
                "watts_or_rpe": self._zone_target("Z3", ftp_watts),
                "description": "Bloc tempo 3",
            },
            {
                "zone": "Z1",
                "duration_minutes": 10,
                "watts_or_rpe": self._zone_target("Z1", ftp_watts),
                "description": "Retour au calme",
            },
        ]

        return {
            "session_number": session_number,
            "session_type": "tempo",
            "duration_minutes": 75,
            "tss_estimated": self._compute_tss(blocks),
            "blocks": blocks,
            "coaching_notes_session": (
                "3×15min tempo. Récupération active Z2 entre les blocs."
            ),
        }

    def _vo2max_session(self, session_number: int, ftp_watts: float | None) -> dict:
        """
        Session VO2max :
        Z1 10min warmup → 5×(Z5 3min + Z2 3min) → Z1 10min cooldown
        Total : 10 + 5*(3+3) + 10 = 50 min.
        duration_minutes is computed as sum(b["duration_minutes"] for b in blocks),
        which is the arithmetically correct value (50 min).
        """
        blocks = [
            {
                "zone": "Z1",
                "duration_minutes": 10,
                "watts_or_rpe": self._zone_target("Z1", ftp_watts),
                "description": "Échauffement",
            },
        ]

        # 5 intervals alternating Z5/Z2
        for rep in range(1, 6):
            blocks.append({
                "zone": "Z5",
                "duration_minutes": 3,
                "watts_or_rpe": self._zone_target("Z5", ftp_watts),
                "description": f"Intervalle VO2max {rep}/5",
            })
            blocks.append({
                "zone": "Z2",
                "duration_minutes": 3,
                "watts_or_rpe": self._zone_target("Z2", ftp_watts),
                "description": f"Récupération {rep}/5",
            })

        blocks.append({
            "zone": "Z1",
            "duration_minutes": 10,
            "watts_or_rpe": self._zone_target("Z1", ftp_watts),
            "description": "Retour au calme",
        })

        total_minutes = sum(b["duration_minutes"] for b in blocks)

        return {
            "session_number": session_number,
            "session_type": "vo2max",
            "duration_minutes": total_minutes,
            "tss_estimated": self._compute_tss(blocks),
            "blocks": blocks,
            "coaching_notes_session": (
                "5×3min VO2max (rapport 1:1). Cadence libre sur les intervalles."
            ),
        }

    # ── TSS computation ──────────────────────────────────────────────────────

    def _compute_tss(self, blocks: list) -> int:
        """
        Calcule le TSS estimé à partir des blocs.

        TSS = Σ (duration_minutes / 60) × tss_per_hour_for_zone
        """
        total = 0.0
        for block in blocks:
            zone = block["zone"]
            duration_h = block["duration_minutes"] / 60.0
            tss_rate = self._TSS_PER_HOUR.get(zone, 50)
            total += duration_h * tss_rate
        return round(total)
