import math

from src.core.finance.irr import irr


def test_irr_empty_cashflows_returns_none():
    assert irr([]) is None
    assert irr([0.0, 0.0, 0.0]) is None


def test_irr_all_negative_returns_none():
    assert irr([-100, -50, -25]) is None


def test_irr_non_monotonic_cashflows_valid_result():
    # Typical single-root profile
    cf = [-1000, 390, 390, 390]
    r = irr(cf)
    assert isinstance(r, float)
    # Roughly ~9–11%
    assert 0.05 < r < 0.15


def test_irr_tolerance_stable_under_small_perturbations():
    base = [-1000, 500, 600]
    perturbed = [-1000, 500.0001, 599.9999]
    r1 = irr(base)
    r2 = irr(perturbed)
    assert isinstance(r1, float) and isinstance(r2, float)
    assert abs(r1 - r2) < 1e-6 or math.isclose(r1, r2, rel_tol=1e-6, abs_tol=1e-6)


def test_irr_multiple_sign_changes_returns_some_root():
    # Two sign changes; implementation may still find a root if bracketable.
    cf = [-100, 230, -132]
    r = irr(cf)
    # Accept "no root" or any reasonable root in (-90%, 100%)
    assert r is None or (-0.9 < r < 1.0)
