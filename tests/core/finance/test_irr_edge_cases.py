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


def test_irr_deep_underwater_returns_valid_domain_root_not_spurious():
    """Regression: a deep-underwater single-sign-change deal must return the economically
    meaningful root r > -100% (1 + r > 0), NOT a spurious sub-(-100%) polynomial root.

    This exact cashflow (surfaced by a Mission 1 scenario corner) previously drove
    Newton-Raphson to converge on r ≈ -1.7911 (1 + r < 0, a non-economic root); the true
    IRR is ≈ -18.63%. Guards the domain-validity fix in irr.py.
    """
    cf = [-135000, 1641.5, 1422.3, 1160.4, 852.9, 497.0, 2152.2, 1689.9, 1169.3, 586.8, 12843.9]
    r = irr(cf)
    assert isinstance(r, float)
    assert r > -1.0  # valid domain: 1 + r > 0 (never a sub-(-100%) artifact)
    assert math.isclose(r, -0.18630, abs_tol=1e-4)  # the true economically meaningful root
    # and it genuinely zeroes NPV
    npv = sum(a / ((1.0 + r) ** t) for t, a in enumerate(cf))
    assert abs(npv) < 1e-3
