"""Energy Availability (EA) calculation + RED-S detection.

Section 6 du resilio-v3-master.md.

EA = (Apport calorique − EAT) / kg FFM
  EAT = Énergie dépensée à l'entraînement (kcal)
  FFM = Fat-Free Mass — masse maigre en kg

Les seuils cliniques proviennent de data/ea_thresholds.json.
"""
from __future__ import annotations

import json
import pathlib
from typing import Literal

EaStatus = Literal["optimal", "suboptimal", "critical"]

# ---------------------------------------------------------------------------
# Chargement des seuils
# ---------------------------------------------------------------------------

_DATA_PATH = pathlib.Path(__file__).parents[3] / "data" / "ea_thresholds.json"

with _DATA_PATH.open(encoding="utf-8") as _f:
    _EA_DATA = json.load(_f)

# Seuils cliniques (section 6.2)
_OPTIMAL_MIN: float = float(_EA_DATA["female"]["optimal_min_kcal_per_kg_ffm"])      # 45 — identique M/F
_CRITICAL_F: float = float(_EA_DATA["female"]["critical_threshold_kcal_per_kg_ffm"]) # 30
_CRITICAL_M: float = float(_EA_DATA["male"]["critical_threshold_kcal_per_kg_ffm"])   # 25
_REDS_DAYS: int = int(_EA_DATA["female"]["reds_consecutive_days"])                   # 3


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def calculate_energy_availability(
    caloric_intake: float,
    exercise_energy: float,
    ffm_kg: float,
) -> float:
    """Calcule l'Energy Availability en kcal/kg de masse maigre.

    Paramètres
    ----------
    caloric_intake:
        Apport calorique total du jour (kcal).
    exercise_energy:
        Énergie dépensée à l'entraînement — EAT (kcal).
    ffm_kg:
        Fat-Free Mass, masse maigre en kg.

    Retourne
    --------
    EA en kcal/kg FFM. Peut être négatif si l'apport est inférieur à l'EAT.

    Lève
    ----
    ValueError si ffm_kg <= 0.
    """
    if ffm_kg <= 0.0:
        raise ValueError(f"ffm_kg must be > 0, got {ffm_kg}")
    return (caloric_intake - exercise_energy) / ffm_kg


def get_ea_status(ea_value: float, sex: str = "F") -> EaStatus:
    """Retourne le statut EA selon le sexe et les seuils cliniques.

    Seuils (section 6.2) :
      - >= 45 : optimal  (identique M/F)
      - >= seuil_critique : suboptimal
      - < seuil_critique  : critical   (< 30 femme / < 25 homme)

    Paramètres
    ----------
    ea_value : EA en kcal/kg FFM.
    sex      : "F" (femme) ou "M" (homme). Insensible à la casse.
    """
    if ea_value >= _OPTIMAL_MIN:
        return "optimal"
    critical_threshold = _CRITICAL_F if sex.upper() == "F" else _CRITICAL_M
    if ea_value < critical_threshold:
        return "critical"
    return "suboptimal"


def detect_reds_risk(ea_history: list[float], sex: str = "F") -> bool:
    """Détecte un signal RED-S : EA < seuil critique pendant N jours consécutifs.

    Évalue les valeurs depuis la fin de la liste (les plus récentes en dernier).
    Si la liste contient moins de _REDS_DAYS entrées, retourne False.

    Paramètres
    ----------
    ea_history : Liste des valeurs EA quotidiennes (ordre chronologique).
    sex        : "F" ou "M".
    """
    if len(ea_history) < _REDS_DAYS:
        return False
    critical_threshold = _CRITICAL_F if sex.upper() == "F" else _CRITICAL_M
    consecutive = 0
    for ea in reversed(ea_history):
        if ea < critical_threshold:
            consecutive += 1
            if consecutive >= _REDS_DAYS:
                return True
        else:
            break
    return False
