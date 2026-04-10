"""Recovery Coach Agent V3.

Point d'entrée public de l'agent Recovery V3.
Orchestre le prescriber pour produire un RecoveryVetoV3 complet.

Section 2.2 du resilio-v3-master.md.
"""
from __future__ import annotations

from typing import Optional

from ...models.athlete_state import (
    EnergySnapshot,
    HormonalProfile,
    RecoveryVetoV3,
)
from .prescriber import compute_recovery_veto_v3


class RecoveryCoachV3:
    """Agent Recovery V3 — veto élargi sur 5 composantes.

    Ne prescrit pas de workouts directement. Produit un RecoveryVetoV3
    que le Head Coach intègre dans ses décisions de prescription.
    """

    def assess(
        self,
        current_hrv: Optional[float],
        baseline_hrv: Optional[float],
        acwr: Optional[float],
        energy_snapshot: Optional[EnergySnapshot],
        hormonal_profile: Optional[HormonalProfile],
        sex: str = "female",
    ) -> RecoveryVetoV3:
        """Évalue l'état de récupération et retourne le veto V3.

        Args:
            current_hrv:       HRV RMSSD actuel (ms). None si non disponible.
            baseline_hrv:      HRV RMSSD de référence (moyenne long terme). None si non disponible.
            acwr:              Ratio charge aiguë/chronique. None si non disponible.
            energy_snapshot:   Snapshot Energy Coach (EA + allostatic). None si non disponible.
            hormonal_profile:  Profil cycle menstruel. None si non applicable.
            sex:               "female" | "male" (détermine les seuils EA).

        Returns:
            RecoveryVetoV3 avec statut, composantes et cap final.
        """
        return compute_recovery_veto_v3(
            current_hrv=current_hrv,
            baseline_hrv=baseline_hrv,
            acwr=acwr,
            energy_snapshot=energy_snapshot,
            hormonal_profile=hormonal_profile,
            sex=sex,
        )
