"""
SCÉNARIO A — Test 1RM planifié + Veto ROUGE du Recovery Coach
Principe : le Head Coach présente la situation, sa recommandation,
et attend une décision humaine. Le veto ROUGE sur le test 1RM
ne peut pas être overridé — seule la séance de remplacement est négociable.
"""

from datetime import date

from langgraph.types import interrupt

from models.athlete_state import AthleteState

CONFLICT_ID = "A_1RM_RED_VETO"


def detect(state: AthleteState) -> bool:
    """Retourne True si le scénario A est actif."""
    hrv_today = state.fatigue.hrv_rmssd_today
    hrv_baseline = state.fatigue.hrv_rmssd_baseline
    hrv_drop = (hrv_baseline - hrv_today) / hrv_baseline if hrv_baseline else 0

    return (
        state.fatigue.recovery_score_today < 50
        and hrv_drop > 0.20
        and _has_scheduled_1rm_today(state)
    )


def _has_scheduled_1rm_today(state: AthleteState) -> bool:
    today = date.today().strftime("%A").lower()
    session = state.constraint_matrix.schedule.get(today, {})
    assigned = session.get("assigned", [])
    return any("1rm" in s.lower() or "test" in s.lower() for s in assigned)


def run(state: AthleteState) -> AthleteState:
    """Nœud LangGraph — interrompt le graph et présente la décision."""
    hrv_today = state.fatigue.hrv_rmssd_today
    hrv_baseline = state.fatigue.hrv_rmssd_baseline
    hrv_drop = (hrv_baseline - hrv_today) / hrv_baseline
    sleep = state.fatigue.sleep_hours_last_night
    recovery = state.fatigue.recovery_score_today
    hr_delta = state.fatigue.get("hr_rest_delta", "N/A")

    situation = (
        f"ALERTE HEAD COACH — Conflit Récupération / Test 1RM\n\n"
        f"Données biométriques ce matin :\n"
        f"  HRV RMSSD   : {hrv_today}ms (baseline {hrv_baseline}ms, -{hrv_drop:.0%})\n"
        f"  FC repos     : +{hr_delta} bpm vs baseline\n"
        f"  Sommeil      : {sleep}h\n"
        f"  Recovery Score : {recovery}/100 → ROUGE\n\n"
        f"Votre Test 1RM Squat est prévu aujourd'hui.\n"
        f"Un test 1RM dans cet état produit un résultat non représentatif "
        f"et présente un risque élevé de blessure."
    )

    recommendation = (
        "RECOMMANDATION : Reporter le Test 1RM à J+7.\n"
        "Séance de remplacement aujourd'hui : Technique Squat à 60% 1RM estimé, "
        "4×3, RPE 5 — maintien du pattern moteur sans stress systémique.\n"
        "Mésocycle décalé d'une semaine en conséquence."
    )

    state.pending_decision = {
        "conflict_id": CONFLICT_ID,
        "situation": situation,
        "recommendation": recommendation,
        "alternatives": [],
        "hard_rule_override_possible": False,
        "status": "awaiting_user_input",
    }

    return interrupt(state)


def get_alternatives(state: AthleteState) -> list[str]:
    return [
        "Option B : Repos complet aujourd'hui. Test 1RM conditionnel à J+4 "
        "(déclenché seulement si Recovery Score > 70 à J+4).",

        "Option C : Séance Upper Body Tier 1 uniquement aujourd'hui "
        "(membres inférieurs au repos complet). Test 1RM reporté à J+7.",
    ]


def handle_custom_override(state: AthleteState) -> AthleteState:
    """L'utilisateur insiste pour faire le test — refus protocole."""
    state.pending_decision["warning"] = (
        "REFUS SYSTÈME : Recovery Score < 50 est une limite absolue. "
        "Le Test 1RM ne peut pas être effectué dans cet état. "
        "Choisissez parmi les options proposées ou l'Option B/C."
    )
    return interrupt(state)
