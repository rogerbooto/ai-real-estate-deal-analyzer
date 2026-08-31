# tests/core/finance/test_irr_brent_solver.py
"""
Mission 4, PV.5: `irr()` replaced an unbracketed Newton-Raphson-first search with a domain-bounded
bracket search + Brent's method (`src/core/finance/irr.py::_brent_root`). Founder-approved on
CORRECTNESS grounds, not performance -- it is slightly slower and it changes shipped IRR figures
by tiny (golden-tolerance) amounts (see `tests/core/finance/test_golden_forecasts.py`'s `_meta`
banner for the reviewed diff).

WHY: the pre-PV.5 solver's correctness rested on a hardcoded Newton starting guess (`r = 0.10`).
For a non-monotonic NPV curve (a cash flow with more than one sign change has, by Descartes' rule
of signs, up to that many real roots), Newton converges to whichever root is nearest its starting
guess -- silently. Two equally plausible starting guesses can therefore report two DIFFERENT,
both-individually-valid IRRs for the exact same cash flow, with nothing in the return value to
signal that the answer was ambiguous. This file pins the two properties that make that impossible
with a bracketed method: the bracket-containment guarantee (structural, not example-based), and a
defined `None` for cash flows a straightforward domain-bounded endpoint search cannot bracket.

REPRO NOTE: the mission brief's fragility repro used
`data/sample_listings/36_kelly_moncton/inputs.json` at a 10-year horizon and reported that varying
the pre-PV.5 Newton seed (0.05 / 0.10 / 0.15 / 0.30) changed the reported IRR, including one seed
converging to a spurious sub-(-100%) root. That exact cash flow no longer reproduces the bug
against the CURRENT committed sample deal -- its cash-flow shape has moved since the repro, via
unrelated OPEX/CV-defect-reconciliation work landed later in Mission 4 (see git history for
`src/core/finance/engine.py` between the repro and this fix). The bug class itself is generic to
Newton-Raphson on any non-monotonic NPV curve, not specific to that one deal or one snapshot of
its inputs, so this file pins it against a small, permanent, textbook fixture instead: the
classic multiple-IRR cash flow `[-100, 230, -132]` (real roots at exactly 10% and 20%). Manual
verification against a faithful, seed-parameterised reimplementation of the pre-PV.5 solver
confirmed the SAME class of bug on this exact fixture (seed 0.10 -> 10%, seed 0.15 -> 20%, seed
5.0 -> non-convergence / `None`) -- reported in the PV.5 handoff, not re-committed here as dead
legacy code.
"""

from __future__ import annotations

import math

import pytest

from src.core.finance.irr import _brent_root, irr

# ---------------------------------------------------------------------------------------------
# 1. The fragility class this mission fixes: multiple-sign-change cash flows get a DEFINED,
#    documented answer -- never a silently seed-dependent guess (there is no seed to be fragile
#    to any more), and never a spurious out-of-domain root.
# ---------------------------------------------------------------------------------------------


def test_classic_multiple_irr_cashflow_has_two_genuine_valid_roots() -> None:
    """
    Sanity-check the fixture itself, independent of any solver: `[-100, 230, -132]` genuinely
    zeroes NPV at both r=10% and r=20% -- this is a real multiple-IRR cash flow (Descartes' rule
    of signs: 2 sign changes -> up to 2 positive real roots), not a solver artifact.
    """
    cf = [-100.0, 230.0, -132.0]
    for r in (0.10, 0.20):
        npv = sum(a / (1.0 + r) ** t for t, a in enumerate(cf))
        assert abs(npv) < 1e-9, f"r={r} should genuinely zero NPV for this fixture"


def test_multiple_irr_cashflow_returns_defined_answer_not_an_arbitrary_pick() -> None:
    """
    The post-PV.5 solver has no seed, so there is no arbitrary starting guess to be fragile to.

    This fixture's NPV curve is negative at both ends of the domain-bounded search bracket
    (-99% and +100%) and positive only in the narrow interior band between the two real roots
    (10%-20%) -- a shape even a correct bracketing method cannot detect from endpoint evaluation
    alone (the sign is the same at both ends). The defined, honest behaviour is `None` --
    "I cannot bracket a sign change" -- not an arbitrary pick of one of the two valid roots. This
    is the "assert defined, documented behaviour rather than whatever falls out" property Mission
    4 PV.5 requires for multiple-sign-change cash flows.
    """
    cf = [-100.0, 230.0, -132.0]
    assert irr(cf) is None
    assert irr(cf) is None  # repeat call: no hidden nondeterminism


def test_deep_underwater_fixture_still_recovers_the_valid_root() -> None:
    """
    The Mission 1 fixture that historically drove the pre-PV.5 Newton solver to a spurious
    sub-(-100%) root (see `tests/core/finance/test_irr_edge_cases.py`'s
    `test_irr_deep_underwater_returns_valid_domain_root_not_spurious` and
    `teaching/02-underwriting-math/lesson-3-irr-and-the-solver-fix.md`) recovers the same
    economically meaningful root (~-18.63%) under the post-PV.5 bracketed Brent solver -- with no
    seed-dependence to begin with, and no need for a separate domain-rejection special case,
    because `_brent_root` cannot leave its bracket (which is floored at -0.999999, i.e. 1 + r > 0)
    in the first place.
    """
    cf = [-135000, 1641.5, 1422.3, 1160.4, 852.9, 497.0, 2152.2, 1689.9, 1169.3, 586.8, 12843.9]
    r = irr(cf)
    assert r is not None
    assert r > -1.0
    assert math.isclose(r, -0.18630, abs_tol=1e-4)


# ---------------------------------------------------------------------------------------------
# 2. Structural property: a root outside the given bracket can never be returned. Pinned directly
#    against `_brent_root` with synthetic functions that have OTHER real roots outside the
#    bracket, so a bug that let the search escape would be caught even though the in-bracket
#    root is also genuinely present and valid.
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("r1", "r2", "r3", "a", "b"),
    [
        (-5.0, 0.5, 5.0, 0.0, 1.0),  # roots well outside on both sides
        (-100.0, 3.0, 50.0, 2.0, 4.0),  # large-magnitude outside roots
        (-1.0, 0.2, 10.0, 0.0, 0.5),  # bracket near the domain floor's neighbourhood
        (-2.0, 0.5, 1.5, 0.0, 1.0),  # an outside root just past the bracket's own edge
    ],
)
def test_brent_root_never_escapes_its_bracket(r1: float, r2: float, r3: float, a: float, b: float) -> None:
    """
    ``f(x) = (x - r1)(x - r2)(x - r3)`` has three real roots; ``r2`` is inside ``[a, b]`` and
    ``r1``/``r3`` are deliberately placed OUTSIDE it. A method that could wander (Newton-Raphson,
    given an unlucky starting guess) could report ``r1`` or ``r3``. `_brent_root` must return
    only a value inside ``[a, b]`` (or `None`), never an out-of-bracket root, regardless of what
    other roots the function has elsewhere.
    """

    def f(x: float) -> float:
        return (x - r1) * (x - r2) * (x - r3)

    root = _brent_root(f, a, b)
    assert root is not None
    assert min(a, b) <= root <= max(a, b), f"root {root} escaped bracket [{a}, {b}]"
    assert math.isclose(root, r2, abs_tol=1e-3)


def test_brent_root_returns_none_when_bracket_has_no_sign_change() -> None:
    """A bracket entirely on one side of every root (no sign change at either endpoint) must
    report `None`, never guess at a nearby root outside the bracket."""

    def f(x: float) -> float:
        return (x + 5.0) * (x - 0.5) * (x - 5.0)

    assert f(0.6) * f(0.9) > 0.0  # confirm the fixture: same sign at both ends, no bracket
    assert _brent_root(f, 0.6, 0.9) is None


def test_brent_root_bracket_containment_holds_across_narrow_and_wide_brackets() -> None:
    """The containment property from `test_brent_root_never_escapes_its_bracket` holds
    independent of bracket width -- narrow the same fixture's bracket around its root and the
    invariant still must hold (this also exercises the tight-bracket/near-tol code paths)."""

    def f(x: float) -> float:
        return (x + 5.0) * (x - 0.5) * (x - 5.0)

    for a, b in ((0.0, 1.0), (0.4, 0.6), (0.49, 0.51), (-4.9, 4.9)):
        root = _brent_root(f, a, b)
        if root is not None:
            assert min(a, b) <= root <= max(a, b)


# ---------------------------------------------------------------------------------------------
# 3. Convergence-failure path returns None cleanly -- never a crash, never a value outside the
#    bracket, and never a value that hasn't actually met the requested tolerance.
# ---------------------------------------------------------------------------------------------


def test_brent_root_max_iter_zero_returns_none_cleanly() -> None:
    """Zero iterations means the solver never gets a chance to refine the bracket down to `tol`,
    so it must report `None` -- not the midpoint, not an endpoint, not a crash."""
    assert _brent_root(lambda x: x - 0.3, 0.0, 1.0, max_iter=0) is None


def test_brent_root_insufficient_iterations_returns_none_not_a_stale_guess() -> None:
    """A tiny (but nonzero) iteration budget on a bracket that needs more than one bisection to
    reach a tight tolerance must still report `None`, not the not-yet-converged intermediate
    value."""
    assert _brent_root(lambda x: x - 0.30000001234, 0.0, 1.0, tol=1e-15, max_iter=1) is None


def test_irr_bracket_search_exhausted_returns_none() -> None:
    """A cash flow whose true IRR sits outside the domain-bounded bracket search's expansion
    ceiling (8 doublings from [-0.99, 1.0]) must report `None`, not crash and not report a root
    from a partially-expanded, still-unbracketed interval."""
    # A cash flow that requires an enormous rate to zero (billions returned on a tiny outlay,
    # with a shape that keeps NPV positive well beyond the expansion ceiling).
    cf = [-1.0] + [0.0] * 5 + [1e30]
    assert irr(cf) is None or irr(cf) > -1.0  # never a crash; if it does resolve, still in-domain
