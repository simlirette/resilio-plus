"""
VDOT Training Paces — core/vdot.py
Lookup linéaire dans data/vdot_paces.json avec interpolation fractionnaire.
"""
from __future__ import annotations

import json
from pathlib import Path

_TABLE: dict[str, dict] = {}
_PACE_KEYS = [
    "easy_fast_sec_km",
    "easy_slow_sec_km",
    "marathon_sec_km",
    "threshold_sec_km",
    "interval_sec_km",
    "repetition_sec_400m",
]


def _load_table() -> dict[str, dict]:
    global _TABLE
    if not _TABLE:
        path = Path(__file__).parent.parent / "data" / "vdot_paces.json"
        _TABLE = json.loads(path.read_text())["table"]
    return _TABLE


def get_vdot_paces(vdot: float) -> dict:
    """
    Retourne les 6 allures pour un VDOT donné (interpolation linéaire entre entiers).

    Args:
        vdot: VDOT de l'athlète (ex: 38.2). Clampé dans [20.0, 85.0].

    Returns:
        dict avec clés: easy_fast_sec_km, easy_slow_sec_km, marathon_sec_km,
        threshold_sec_km, interval_sec_km, repetition_sec_400m.
        Toutes les valeurs en secondes (float).
    """
    table = _load_table()
    vdot = max(20.0, min(85.0, float(vdot)))
    low = int(vdot)
    frac = vdot - low

    low_paces = table[str(low)]
    high_paces = table.get(str(low + 1), low_paces)

    return {k: low_paces[k] + frac * (high_paces[k] - low_paces[k]) for k in _PACE_KEYS}


def format_pace(sec_per_km: float) -> str:
    """Convertit secondes/km en 'M:SS/km'."""
    total = int(round(sec_per_km))
    m, s = divmod(total, 60)
    return f"{m}:{s:02d}/km"


def format_pace_400m(sec_per_400m: float) -> str:
    """Convertit secondes/400m en 'M:SS/400m'."""
    total = int(round(sec_per_400m))
    m, s = divmod(total, 60)
    return f"{m}:{s:02d}/400m"
