"""
Calcul ACWR (Acute:Chronic Workload Ratio) via EWMA.
Fonction utilitaire pure — pas de dépendances DB/FastAPI.
"""


def compute_ewma_acwr(
    daily_loads: list[float],
    acute_days: int = 7,
    chronic_days: int = 28,
) -> tuple[float, float, float]:
    """
    Calcule l'ACWR via EWMA (Exponentially Weighted Moving Average).

    Args:
        daily_loads: charges quotidiennes du plus ancien au plus récent.
                     Idéalement >= 28 valeurs. Valeurs manquantes = 0.0.
        acute_days:  fenêtre aiguë (défaut 7j)
        chronic_days: fenêtre chronique (défaut 28j)

    Returns:
        (ewma_acute, ewma_chronic, acwr)
        acwr = 0.0 si chronic == 0

    Formule:
        λ = 2 / (N + 1)
        ewma_t = ewma_{t-1} + λ * (load_t - ewma_{t-1})
    """
    if not daily_loads:
        return 0.0, 0.0, 0.0

    lambda_acute = 2 / (acute_days + 1)
    lambda_chronic = 2 / (chronic_days + 1)

    ewma_acute = daily_loads[0]
    ewma_chronic = daily_loads[0]

    for load in daily_loads[1:]:
        ewma_acute = ewma_acute + lambda_acute * (load - ewma_acute)
        ewma_chronic = ewma_chronic + lambda_chronic * (load - ewma_chronic)

    acwr = ewma_acute / ewma_chronic if ewma_chronic > 0 else 0.0
    return ewma_acute, ewma_chronic, acwr


def acwr_zone(acwr: float) -> str:
    """
    Classifie l'ACWR en zone de charge.

    Returns:
        'underload' : < 0.8
        'safe'      : 0.8 – 1.3
        'caution'   : 1.3 – 1.5
        'danger'    : > 1.5
    """
    if acwr < 0.8:
        return "underload"
    if acwr <= 1.3:
        return "safe"
    if acwr <= 1.5:
        return "caution"
    return "danger"
