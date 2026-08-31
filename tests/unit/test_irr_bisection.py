from src.core.finance.irr import irr


def test_irr_converges_on_simple_positive_cashflow():
    """
    A simple, well-behaved cash flow with a real positive IRR converges under the default
    (Mission 4, PV.5) bracketed-Brent solver.

    HISTORY: this test used to be named `test_irr_bisection_used_when_newton_disabled` and forced
    `max_iter=0` to make the (now-removed) Newton-Raphson stage give up and fall through to a
    separate bisection fallback. PV.5 replaced that two-stage Newton/bisection design with a
    single bracketed Brent solve (`irr.py::_brent_root`) -- there is no longer a "Newton disabled"
    switch to flip, so this test now just pins the ordinary convergent case.
    """
    cf = [-1000.0, 0.0, 0.0, 1200.0]
    r = irr(cf)
    assert r is not None
    assert 0.0 < r < 1.0  # between 0% and 100%


def test_irr_max_iter_zero_returns_none_cleanly():
    """
    `max_iter=0` now caps the (single) Brent solve directly: zero iterations means the solver
    never gets a chance to refine the bracket, so it must report `None` -- not crash, and not
    return an arbitrary point from inside the bracket. See `_brent_root`'s docstring: an empty
    iteration budget falls straight to the "exceeded max_iter without meeting tol" return.
    """
    cf = [-1000.0, 0.0, 0.0, 1200.0]
    assert irr(cf, max_iter=0) is None


def test_irr_all_same_sign_returns_none():
    # All positive -> no sign change -> no real IRR
    assert irr([100.0, 100.0, 100.0]) is None
    # All negative -> also no real IRR
    assert irr([-50.0, -10.0]) is None
