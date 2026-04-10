"""Recovery Coach V3 — Prescriber : calcul du veto 5 composantes.

Fonctions pures sans effet de bord. Chaque composante est classifiée
indépendamment, puis la synthèse détermine le statut global et le cap
d'intensité final (worst-component wins).

Référence : docs/resilio-v3-master.md — section 2.2
Seuils EA   : data/ea_thresholds.json
Cycle       : data/hormonal_adjustments.json
"""
from __future__ import annotations

from typing import Optional

from ...models.athlete_state import (
    EnergySnapshot,
    HormonalProfile,
    RecoveryVetoV3,
    TrafficLight,
)

# ---------------------------------------------------------------------------
# Seuils
# ---------------------------------------------------------------------------

# HRV (ratio current / baseline)
_HRV_GREEN_MIN = 0.80      # ratio >= 0.80 → vert
_HRV_YELLOW_MIN = 0.60     # ratio >= 0.60 → jaune ; < 0.60 → rouge

# ACWR
_ACWR_SAFE_LOW = 0.80      # en dessous → sous-entraînement, pas de risque
_ACWR_SAFE_HIGH = 1.30     # zone sûre [0.80 – 1.30]
_ACWR_CAUTION_HIGH = 1.50  # caution [1.30 – 1.50] ; > 1.50 → rouge

# EA (kcal/kg FFM)
_EA_OPTIMAL_MIN = 45.0
_EA_CRITICAL_FEMALE = 30.0
_EA_CRITICAL_MALE = 25.0

# Allostatic score
_ALLOSTATIC_GREEN_MAX = 60.0   # < 60 → vert
_ALLOSTATIC_YELLOW_MAX = 80.0  # 60–80 → jaune ; > 80 → rouge

# Caps d'intensité
_CAP_GREEN = 1.00
_CAP_YELLOW = 0.85   # −15 %
_CAP_RED = 0.00      # séance bloquée


# ---------------------------------------------------------------------------
# Classificateurs individuels
# ---------------------------------------------------------------------------

def classify_hrv(
    current_hrv: Optional[float],
    baseline_hrv: Optional[float],
) -> TrafficLight:
    """Classe la composante HRV d'après le ratio current / baseline.

    Sans données ou sans baseline → vert (cold start, pas de pénalité).
    """
    if current_hrv is None or baseline_hrv is None or baseline_hrv <= 0:
        return "green"
    ratio = current_hrv / baseline_hrv
    if ratio >= _HRV_GREEN_MIN:
        return "green"
    if ratio >= _HRV_YELLOW_MIN:
        return "yellow"
    return "red"


def classify_acwr(acwr: Optional[float]) -> TrafficLight:
    """Classe la composante ACWR.

    < 0.80 → sous-entraînement (pas un risque) → vert.
    """
    if acwr is None:
        return "green"
    if acwr > _ACWR_CAUTION_HIGH:
        return "red"
    if acwr > _ACWR_SAFE_HIGH:
        return "yellow"
    return "green"


def classify_ea(
    ea: Optional[float],
    sex: str = "female",
) -> TrafficLight:
    """Classe la disponibilité énergétique selon le sexe de l'athlète.

    Seuils (kcal/kg FFM) :
    - femme : critique < 30, sous-optimal 30–45, optimal >= 45
    - homme : critique < 25, sous-optimal 25–45, optimal >= 45
    """
    if ea is None:
        return "green"
    critical = _EA_CRITICAL_FEMALE if sex == "female" else _EA_CRITICAL_MALE
    if ea >= _EA_OPTIMAL_MIN:
        return "green"
    if ea >= critical:
        return "yellow"
    return "red"


def classify_allostatic(score: Optional[float]) -> TrafficLight:
    """Classe le score allostatic.

    < 60 → vert, 60–80 → jaune, > 80 → rouge.
    """
    if score is None:
        return "green"
    if score > _ALLOSTATIC_YELLOW_MAX:
        return "red"
    if score >= _ALLOSTATIC_GREEN_MAX:
        return "yellow"
    return "green"


def classify_cycle(profile: Optional[HormonalProfile]) -> Optional[TrafficLight]:
    """Classe la phase du cycle menstruel.

    Retourne None si le suivi est désactivé ou si aucune phase n'est définie.
    - folliculaire → vert (phase optimale)
    - menstruelle / ovulation / lutéale → jaune (ajustements requis)
    """
    if profile is None or not profile.enabled or profile.current_phase is None:
        return None
    if profile.current_phase == "follicular":
        return "green"
    return "yellow"


# ---------------------------------------------------------------------------
# Synthèse : compute_recovery_veto_v3
# ---------------------------------------------------------------------------

def _component_cap(light: TrafficLight) -> float:
    if light == "red":
        return _CAP_RED
    if light == "yellow":
        return _CAP_YELLOW
    return _CAP_GREEN


def compute_recovery_veto_v3(
    current_hrv: Optional[float],
    baseline_hrv: Optional[float],
    acwr: Optional[float],
    energy_snapshot: Optional[EnergySnapshot],
    hormonal_profile: Optional[HormonalProfile],
    sex: str = "female",
) -> RecoveryVetoV3:
    """Calcule le veto Recovery V3 en synthétisant les 5 composantes.

    Règles de synthèse (section 2.2) :
    - 0 indicateur hors zone → vert, cap 1.0
    - 1 indicateur hors zone → jaune, cap 0.85
    - 2+ indicateurs hors zone OU 1 indicateur rouge → rouge, cap 0.0
    La composante la plus dégradée détermine le cap final.
    """
    # --- Extraction des valeurs depuis le snapshot ---
    ea = energy_snapshot.energy_availability if energy_snapshot else None
    allostatic = energy_snapshot.allostatic_score if energy_snapshot else None

    # --- Classification de chaque composante ---
    hrv_comp = classify_hrv(current_hrv, baseline_hrv)
    acwr_comp = classify_acwr(acwr)
    ea_comp = classify_ea(ea, sex)
    allostatic_comp = classify_allostatic(allostatic)
    cycle_comp = classify_cycle(hormonal_profile)

    # --- Collecte des composantes actives (None = non comptabilisée) ---
    active: list[tuple[str, TrafficLight]] = [
        ("hrv", hrv_comp),
        ("acwr", acwr_comp),
        ("ea", ea_comp),
        ("allostatic", allostatic_comp),
    ]
    if cycle_comp is not None:
        active.append(("cycle", cycle_comp))

    # --- Comptage des indicateurs hors zone ---
    red_count = sum(1 for _, v in active if v == "red")
    yellow_count = sum(1 for _, v in active if v == "yellow")
    out_of_zone = red_count + yellow_count

    # --- Statut global ---
    if red_count > 0 or out_of_zone >= 2:
        status: TrafficLight = "red"
        final_cap = _CAP_RED
        veto_triggered = True
    elif out_of_zone == 1:
        status = "yellow"
        final_cap = _CAP_YELLOW
        veto_triggered = False
    else:
        status = "green"
        final_cap = _CAP_GREEN
        veto_triggered = False

    # --- Raisons ---
    veto_reasons: list[str] = [
        f"{name}: {value}" for name, value in active if value != "green"
    ]

    return RecoveryVetoV3(
        status=status,
        hrv_component=hrv_comp,
        acwr_component=acwr_comp,
        ea_component=ea_comp,
        allostatic_component=allostatic_comp,
        cycle_component=cycle_comp,
        final_intensity_cap=final_cap,
        veto_triggered=veto_triggered,
        veto_reasons=veto_reasons,
    )
