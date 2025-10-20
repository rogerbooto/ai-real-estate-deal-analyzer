from src.core.finance.irr import irr


def test_irr_bisection_used_when_newton_disabled():
    # Newton is disabled -> must use bisection path
    # Simple CF that has a real positive IRR
    cf = [-1000.0, 0.0, 0.0, 1200.0]
    r = irr(cf, max_iter=0)  # force bisection fallback
    assert r is not None
    assert 0.0 < r < 1.0  # between 0% and 100%


def test_irr_all_same_sign_returns_none():
    # All positive -> no sign change -> no real IRR
    assert irr([100.0, 100.0, 100.0]) is None
    # All negative -> also no real IRR
    assert irr([-50.0, -10.0]) is None
