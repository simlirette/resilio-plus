"""Allostatic load scoring — section 5.2 du resilio-v3-master.md.

Calcule le score de charge allostatique normalisé (0-100) à partir de six
composantes pondérées :  HRV, sommeil, travail, stress, cycle, EA.

Les poids et mappings de scores proviennent de data/allostatic_weights.json.
"""
from __future__ import annotations

import json
import pathlib
from typing import Optional

# ---------------------------------------------------------------------------
# Chargement des poids depuis le fichier de données
# ---------------------------------------------------------------------------

_DATA_PATH = pathlib.Path(__file__).parents[3] / "data" / "allostatic_weights.json"

with _DATA_PATH.open(encoding="utf-8") as _f:
    _WEIGHTS_DATA = json.load(_f)

_WEIGHTS: dict[str, float] = _WEIGHTS_DATA["component_weights"]
_WORK_SCORES: dict[str, float] = _WEIGHTS_DATA["work_intensity_scores"]
_STRESS_SCORES: dict[str, float] = _WEIGHTS_DATA["stress_level_scores"]
_CYCLE_SCORES: dict[str, float] = _WEIGHTS_DATA["cycle_phase_scores"]
_EA_SCORES: dict[str, float] = _WEIGHTS_DATA["ea_status_scores"]


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------


def calculate_allostatic_score(
    hrv_deviation: float,
    sleep_quality: float,
    work_intensity: str,
    stress_level: str,
    cycle_phase: Optional[str],
    ea_status: str,
) -> float:
    """Calcule le score de charge allostatique (0-100).

    Paramètres
    ----------
    hrv_deviation:
        % de déviation du HRV vs baseline. Négatif = dégradation.
        Exemple : -15 → le HRV est 15% sous la baseline.
    sleep_quality:
        Score de qualité du sommeil 0-100. 100 = parfait.
    work_intensity:
        "light" | "normal" | "heavy" | "exhausting"
    stress_level:
        "none" | "mild" | "significant"
    cycle_phase:
        "menstrual" | "follicular" | "ovulation" | "luteal" | None
    ea_status:
        "optimal" | "suboptimal" | "critical"

    Retourne
    --------
    float entre 0.0 et 100.0 inclus.
    """
    # Composante HRV : déviation négative = charge haute
    # -15% → score 30 ;  positif (meilleur que baseline) → 0
    hrv_score = min(100.0, max(0.0, -hrv_deviation * 2.0))

    # Composante sommeil : inverse de la qualité
    sleep_score = 100.0 - sleep_quality

    # Composantes via lookup
    work_score = float(_WORK_SCORES[work_intensity])
    stress_score = float(_STRESS_SCORES[stress_level])
    cycle_key = cycle_phase if cycle_phase is not None else "null"
    cycle_score = float(_CYCLE_SCORES.get(cycle_key, _CYCLE_SCORES["null"]))
    ea_score = float(_EA_SCORES[ea_status])

    scores = {
        "hrv_deviation": hrv_score,
        "sleep_quality": sleep_score,
        "work_intensity": work_score,
        "stress_level": stress_score,
        "cycle_phase": cycle_score,
        "ea_status": ea_score,
    }

    total = sum(_WEIGHTS[k] * scores[k] for k in _WEIGHTS)
    return min(100.0, max(0.0, total))


def intensity_cap_from_score(allostatic_score: float) -> float:
    """Retourne le cap d'intensité recommandé (0.0–1.0) selon le score.

    Plages (agent.md section 3.4 / master doc section 5.3) :
      0–40  → 1.00  (plan normal)
      41–60 → 1.00  (avertissement, pas de réduction)
      61–80 → 0.85  (–15%)
      81–100→ 0.70  (séance légère seulement)
    """
    if allostatic_score <= 60.0:
        return 1.0
    if allostatic_score <= 80.0:
        return 0.85
    return 0.70
