"""Energy Coach Agent V3.

Modélise la charge de vie totale — cognitive, professionnelle, hormonale — et
la traduit en un EnergySnapshot normalisé attaché à l'AthleteState.

Ne prescrit jamais de workouts. Produit uniquement un EnergySnapshot.

Section 3.4 du resilio-v3-master.md — 5 skills :
  1. calculate_allostatic_score
  2. assess_cognitive_load
  3. calculate_energy_availability
  4. predict_recovery_capacity
  5. generate_energy_report

+ create_snapshot() : orchestre les 5 skills et retourne un EnergySnapshot.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from ...core.allostatic import (
    calculate_allostatic_score as _core_allostatic,
)
from ...core.allostatic import (
    intensity_cap_from_score,
)
from ...core.energy_availability import (
    calculate_energy_availability as _core_ea,
)
from ...core.energy_availability import (
    detect_reds_risk,
    get_ea_status,
)
from ...models.athlete_state import EnergyCheckIn, EnergySnapshot, StressLevel, WorkIntensity
from ..prompts import ENERGY_COACH_PROMPT

_SYSTEM_PROMPT = ENERGY_COACH_PROMPT


# ---------------------------------------------------------------------------
# Structures de données d'entrée
# ---------------------------------------------------------------------------


@dataclass
class EnergyInput:
    """Toutes les données nécessaires à l'Energy Coach pour une journée."""

    hrv_deviation: float  # % déviation vs baseline (négatif = pire)
    sleep_quality: float  # 0-100
    caloric_intake: float  # kcal totaux du jour
    exercise_energy: float  # EAT — énergie dépensée à l'entraînement
    ffm_kg: float  # Fat-Free Mass en kg
    check_in: EnergyCheckIn
    sex: str = "M"  # "M" ou "F"
    ea_history: list[float] = field(default_factory=list)  # EA des jours précédents


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class EnergyCoach:
    """Spécialiste de la charge de vie totale.

    Produit un EnergySnapshot quotidien que le Head Coach et le Recovery Coach
    utilisent pour calibrer leurs décisions.
    """

    @property
    def name(self) -> str:
        return "energy"

    # ------------------------------------------------------------------
    # Skill 1 — Allostatic score
    # ------------------------------------------------------------------

    def calculate_allostatic_score(
        self,
        hrv_deviation: float,
        sleep_quality: float,
        work_intensity: WorkIntensity,
        stress_level: StressLevel,
        cycle_phase: Optional[str],
        ea_status: str,
    ) -> float:
        """Délègue à core/allostatic.py — retourne un score 0-100."""
        return _core_allostatic(
            hrv_deviation=hrv_deviation,
            sleep_quality=sleep_quality,
            work_intensity=work_intensity,
            stress_level=stress_level,
            cycle_phase=cycle_phase,
            ea_status=ea_status,
        )

    # ------------------------------------------------------------------
    # Skill 2 — Cognitive load
    # ------------------------------------------------------------------

    def assess_cognitive_load(
        self,
        work_intensity: WorkIntensity,
        stress_level: StressLevel,
    ) -> float:
        """Évalue la charge cognitive normalisée 0-100.

        Formule : 60% journée de travail + 40% stress déclaré.
        Utilise les mêmes mappings que le score allostatic.
        """
        _work_scores = {"light": 10.0, "normal": 30.0, "heavy": 65.0, "exhausting": 90.0}
        _stress_scores = {"none": 0.0, "mild": 30.0, "significant": 70.0}
        work_score = _work_scores.get(work_intensity, 30.0)
        stress_score = _stress_scores.get(stress_level, 0.0)
        return min(100.0, 0.60 * work_score + 0.40 * stress_score)

    # ------------------------------------------------------------------
    # Skill 3 — Energy Availability
    # ------------------------------------------------------------------

    def calculate_energy_availability(
        self,
        caloric_intake: float,
        exercise_energy: float,
        ffm_kg: float,
    ) -> float:
        """Délègue à core/energy_availability.py — retourne EA en kcal/kg FFM."""
        return _core_ea(
            caloric_intake=caloric_intake,
            exercise_energy=exercise_energy,
            ffm_kg=ffm_kg,
        )

    # ------------------------------------------------------------------
    # Skill 4 — Recovery capacity
    # ------------------------------------------------------------------

    def predict_recovery_capacity(
        self,
        allostatic_score: float,
        allostatic_history: Optional[list[float]] = None,
    ) -> float:
        """Prédit la capacité de récupération (0-100) à partir du score allostatic.

        Formule simple : 100 - allostatic_score.
        L'historique peut être utilisé pour détecter une tendance (réservé V3.1).
        """
        return max(0.0, min(100.0, 100.0 - allostatic_score))

    # ------------------------------------------------------------------
    # Skill 5 — Energy report
    # ------------------------------------------------------------------

    def generate_energy_report(
        self,
        allostatic_score: float,
        energy_availability: float,
        cognitive_load: float,
        recovery_capacity: float,
        flags: list[str],
        sex: str = "M",
    ) -> dict:
        """Génère le rapport synthétique pour le Head Coach.

        Le veto est déclenché si :
        - EA < seuil critique (< 30 femme / < 25 homme)
        - OU allostatic_score > 80

        Retourne un dict avec les clés :
          allostatic_score, energy_availability, cognitive_load,
          recovery_capacity, intensity_cap, veto_triggered, veto_reason, flags
        """
        ea_status = get_ea_status(energy_availability, sex=sex)
        cap = intensity_cap_from_score(allostatic_score)
        veto_triggered = False
        veto_reasons: list[str] = []

        if ea_status == "critical":
            veto_triggered = True
            threshold = 30.0 if sex.upper() == "F" else 25.0
            veto_reasons.append(
                f"EA critique ({energy_availability:.1f} < {threshold} kcal/kg FFM)"
            )

        if allostatic_score > 80.0:
            veto_triggered = True
            veto_reasons.append(f"Score allostatic critique ({allostatic_score:.1f} > 80)")

        return {
            "allostatic_score": allostatic_score,
            "energy_availability": energy_availability,
            "cognitive_load": cognitive_load,
            "recovery_capacity": recovery_capacity,
            "intensity_cap": cap,
            "veto_triggered": veto_triggered,
            "veto_reason": " | ".join(veto_reasons) if veto_reasons else None,
            "flags": flags,
        }

    # ------------------------------------------------------------------
    # create_snapshot — orchestre les 5 skills
    # ------------------------------------------------------------------

    def create_snapshot(self, inp: EnergyInput) -> EnergySnapshot:
        """Orchestre les 5 skills et retourne un EnergySnapshot structuré.

        Logique de veto :
        - EA critique (selon sexe) → veto
        - Allostatic score > 80 → veto
        - RED-S (EA < seuil 3 jours consécutifs) → veto + flag
        """
        # Skill 3 — EA
        ea = self.calculate_energy_availability(
            caloric_intake=inp.caloric_intake,
            exercise_energy=inp.exercise_energy,
            ffm_kg=inp.ffm_kg,
        )
        ea_status = get_ea_status(ea, sex=inp.sex)

        # Skill 1 — Allostatic
        allostatic = self.calculate_allostatic_score(
            hrv_deviation=inp.hrv_deviation,
            sleep_quality=inp.sleep_quality,
            work_intensity=inp.check_in.work_intensity,
            stress_level=inp.check_in.stress_level,
            cycle_phase=inp.check_in.cycle_phase,
            ea_status=ea_status,
        )

        # Skill 2 — Cognitive load
        cognitive = self.assess_cognitive_load(
            work_intensity=inp.check_in.work_intensity,
            stress_level=inp.check_in.stress_level,
        )

        # Skill 4 — Recovery capacity
        recovery = self.predict_recovery_capacity(allostatic_score=allostatic)

        # Flags
        flags: list[str] = []
        full_ea_history = inp.ea_history + [ea]
        if detect_reds_risk(full_ea_history, sex=inp.sex):
            flags.append("red_s_risk")
        if ea_status == "critical":
            flags.append("ea_critical")

        # Skill 5 — Report → veto logic
        report = self.generate_energy_report(
            allostatic_score=allostatic,
            energy_availability=ea,
            cognitive_load=cognitive,
            recovery_capacity=recovery,
            flags=flags,
            sex=inp.sex,
        )

        # Intensity cap — pire cas entre allostatic et cycle
        cap = report["intensity_cap"]

        return EnergySnapshot(
            timestamp=datetime.now(tz=timezone.utc),
            allostatic_score=allostatic,
            cognitive_load=cognitive,
            energy_availability=ea,
            cycle_phase=inp.check_in.cycle_phase,  # type: ignore[arg-type]
            sleep_quality=min(100.0, max(0.0, inp.sleep_quality)),
            recommended_intensity_cap=cap,
            veto_triggered=report["veto_triggered"],
            veto_reason=report["veto_reason"],
        )
