"""Tests unitaires pour compute_ewma_acwr et acwr_zone."""

import pytest

from core.acwr import acwr_zone, compute_ewma_acwr


def test_ewma_acwr_empty_loads():
    """Liste vide → tout à zéro."""
    acute, chronic, acwr = compute_ewma_acwr([])
    assert acute == 0.0
    assert chronic == 0.0
    assert acwr == 0.0


def test_ewma_acwr_single_day():
    """Un seul jour → acute = chronic = la charge, ACWR = 1.0."""
    acute, chronic, acwr = compute_ewma_acwr([100.0])
    assert acute == pytest.approx(100.0)
    assert chronic == pytest.approx(100.0)
    assert acwr == pytest.approx(1.0)


def test_ewma_acwr_safe_zone():
    """28 jours de charge constante → ACWR ≈ 1.0, zone safe."""
    loads = [100.0] * 28
    acute, chronic, acwr = compute_ewma_acwr(loads)
    assert acwr == pytest.approx(1.0, rel=1e-3)
    assert acwr_zone(acwr) == "safe"


def test_ewma_acwr_danger_zone():
    """Pic de charge la dernière semaine → ACWR > 1.5, zone danger."""
    # 21 jours de faible charge, puis 7 jours de charge triple
    loads = [50.0] * 21 + [300.0] * 7
    _, _, acwr = compute_ewma_acwr(loads)
    assert acwr > 1.5
    assert acwr_zone(acwr) == "danger"


def test_ewma_acwr_underload():
    """Charge réduite à zéro la dernière semaine → ACWR < 0.8, zone underload."""
    # 21 jours de charge normale, puis 7 jours de repos complet
    loads = [100.0] * 21 + [0.0] * 7
    _, _, acwr = compute_ewma_acwr(loads)
    assert acwr < 0.8
    assert acwr_zone(acwr) == "underload"
