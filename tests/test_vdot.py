"""Tests pour core/vdot.py — lookup VDOT + formatters de pace."""


def test_vdot_exact_lookup():
    """VDOT 38 (entier) → threshold_sec_km = 318 (valeur confirmée table)."""
    from core.vdot import get_vdot_paces

    paces = get_vdot_paces(38.0)
    assert paces["threshold_sec_km"] == 318.0


def test_vdot_interpolation():
    """VDOT 38.5 → threshold interpolé entre 38 (318) et 39 (314)."""
    from core.vdot import get_vdot_paces

    paces = get_vdot_paces(38.5)
    assert paces["threshold_sec_km"] == 316.0  # 318 + 0.5*(314-318)


def test_vdot_clamp_low():
    """VDOT 10 → clampé à VDOT 20 (threshold_sec_km = 498)."""
    from core.vdot import get_vdot_paces

    paces = get_vdot_paces(10.0)
    assert paces["threshold_sec_km"] == 498.0


def test_vdot_clamp_high():
    """VDOT 100 → clampé à VDOT 85 (threshold_sec_km = 164)."""
    from core.vdot import get_vdot_paces

    paces = get_vdot_paces(100.0)
    assert paces["threshold_sec_km"] == 164.0


def test_format_pace():
    """318 sec/km → '5:18/km'."""
    from core.vdot import format_pace

    assert format_pace(318) == "5:18/km"


def test_format_pace_400m():
    """114 sec/400m → '1:54/400m'."""
    from core.vdot import format_pace_400m

    assert format_pace_400m(114) == "1:54/400m"
