from __future__ import annotations

import math
import sys
from collections.abc import Callable, Iterable
from datetime import date, datetime
from operator import truediv
from typing import cast

CashFlowItem = float | tuple[float, date | datetime | float]
CashFlows = Iterable[CashFlowItem]


def _discount_base(rate: float, t: float) -> float:
    """
    ``(1 + rate) ** t`` — the present-value discount base used by every NPV term — computed
    without ever raising ``OverflowError``.

    Long horizons combined with a trial ``rate`` that has temporarily wandered far from the true
    root (a normal, transient part of the search, not a sign anything is wrong) can push
    ``1 + rate`` to a magnitude where CPython's float ``**`` raises
    ``OverflowError: (34, 'Numerical result out of range')`` instead of saturating, unlike ``/``
    and ``*`` which saturate to ``inf`` per IEEE-754. This helper restores that saturating
    behaviour: mathematically, ``lim (1+rate)**t -> inf`` as ``rate -> inf`` for any fixed ``t``
    from this module's actual domain (``t >= 0``, and ``1 + rate > 0`` is enforced by the
    domain-bounded bracket search below, which never evaluates a rate at or below -100%), so
    returning ``math.inf`` on overflow is the correct limit, not an approximation. A discount base
    of ``inf`` makes the corresponding cash flow's contribution to NPV correctly vanish (``a / inf
    == 0.0``) instead of crashing — exactly the economically-correct statement that a cash flow
    infinitely discounted is worth nothing today.
    """
    try:
        return float((1.0 + rate) ** t)
    except OverflowError:
        return math.inf


def _safe_div(a: float, b: float) -> float:
    """
    ``a / b``, but returns a signed (or zero) infinity instead of raising ``ZeroDivisionError``
    when ``b`` has underflowed to exactly ``0.0``.

    Mirror image of ``_discount_base``'s saturating-overflow fix, in the opposite direction: a
    discount base can underflow to ``0.0`` (rather than overflow to ``inf``) when ``rate`` is deep
    in the domain-floor bracket bound (close to -100%) and ``t`` is large -- e.g.
    ``(1e-6) ** 100 == 1e-600``, far below the smallest representable double (~4.9e-324). As the
    discount rate approaches -100%, the discount base correctly vanishes, so a nonzero cash flow
    divided by it correctly diverges to a signed infinity -- an infinitely-negative rate makes any
    future dollar worth an unbounded amount today. A zero cash flow contributes ``0.0`` regardless
    of the (vanishing) discount base.
    """
    if b == 0.0:
        return 0.0 if a == 0.0 else math.copysign(math.inf, a)
    return a / b


def _to_years(t0: date | datetime | float, t: date | datetime | float) -> float:
    """Convert two time markers into a year fraction."""
    # numeric → already a year offset
    if isinstance(t0, int | float) and isinstance(t, int | float):
        return float(t) - float(t0)

    # date/datetime → day count / 365.0
    if isinstance(t0, datetime):
        base = t0
    elif isinstance(t0, date):
        base = datetime(t0.year, t0.month, t0.day)
    else:
        # fallback: treat as zero and return numeric t as-is
        return float(t) if isinstance(t, int | float) else 0.0

    if isinstance(t, datetime):
        other = t
    elif isinstance(t, date):
        other = datetime(t.year, t.month, t.day)
    else:
        # fallback for mixed types
        return float(t) if isinstance(t, int | float) else 0.0

    return (other - base).days / 365.0


def _brent_root(
    f: Callable[[float], float],
    a: float,
    b: float,
    *,
    fa: float | None = None,
    fb: float | None = None,
    tol: float = 1e-6,
    max_iter: int = 100,
) -> float | None:
    """
    Brent's method — bisection + secant + inverse quadratic interpolation — for a real root of
    ``f`` bracketed by ``[a, b]`` (Mission 4, PV.5; replaces this module's former unbracketed
    Newton-Raphson search).

    Reference: R. P. Brent, *Algorithms for Minimization without Derivatives* (1973), ch. 4;
    equivalently Numerical Recipes in C, 2nd ed., §9.3 ("zbrent"), which this implementation
    follows step for step. At each iteration it tries inverse quadratic interpolation (three
    distinct function values) or, failing that, the secant method (two), and falls back to plain
    bisection whenever the interpolated step would land outside the current bracket, would not
    shrink it fast enough, or the bracket is already at the edge of the requested tolerance.

    THE PROPERTY THIS BUYS: every candidate point this function ever evaluates is either the
    bracket midpoint ``0.5 * (c - b)`` (by construction inside ``[b, c]``) or an interpolated step
    explicitly checked to fall strictly inside ``[b, c]`` before being accepted (`min1`/`min2`
    guard above) — and ``b``/``c`` always straddle the root (``fb`` and ``fc`` are kept opposite
    in sign, or one of them is exactly zero). Because the bracket only ever shrinks and its
    endpoints are always drawn from the ORIGINAL ``[a, b]``, ``min(a, b) <= root <= max(a, b)``
    holds for every value this function can return. This is the guarantee an unbracketed method
    (Newton-Raphson) cannot give: Newton can converge to any real root of ``f``, in or out of the
    caller's domain of interest, which is exactly the failure mode this replaces (see `irr()`'s
    docstring and ``tests/core/finance/test_irr_edge_cases.py``).

    Returns the root, or ``None`` if ``a``/``b`` do not bracket a sign change (and neither is
    itself an exact root), or if ``max_iter`` iterations elapse without meeting ``tol``.
    """
    fa = f(a) if fa is None else fa
    fb = f(b) if fb is None else fb
    if fa == 0.0:
        return a
    if fb == 0.0:
        return b
    if fa * fb > 0.0:
        return None  # not bracketed: no sign change between a and b

    c, fc = a, fa
    d = e = b - a
    eps = sys.float_info.epsilon

    for _ in range(max_iter):
        if fb * fc > 0.0:
            # b and c no longer straddle the root -- re-anchor c to the previous a
            c, fc = a, fa
            d = e = b - a
        if abs(fc) < abs(fb):
            # keep b as the best current estimate (smallest |f|)
            a, fa = b, fb
            b, fb = c, fc
            c, fc = a, fa

        tol1 = 2.0 * eps * abs(b) + 0.5 * tol
        xm = 0.5 * (c - b)
        if abs(xm) <= tol1 or fb == 0.0:
            return b

        if abs(e) >= tol1 and abs(fa) > abs(fb):
            s = fb / fa
            if a == c:
                # secant method (only two distinct points so far)
                p = 2.0 * xm * s
                q = 1.0 - s
            else:
                # inverse quadratic interpolation
                q = fa / fc
                r = fb / fc
                p = s * (2.0 * xm * q * (q - r) - (b - a) * (r - 1.0))
                q = (q - 1.0) * (r - 1.0) * (s - 1.0)
            if p > 0.0:
                q = -q
            p = abs(p)
            min1 = 3.0 * xm * q - abs(tol1 * q)
            min2 = abs(e * q)
            if 2.0 * p < min(min1, min2):
                # interpolated step accepted -- verified above to stay inside the bracket
                e = d
                d = p / q
            else:
                # interpolation rejected -- bisect instead
                d = xm
                e = d
        else:
            # not enough progress for interpolation -- bisect
            d = xm
            e = d

        a, fa = b, fb
        if abs(d) > tol1:
            b += d
        else:
            b += tol1 if xm > 0.0 else -tol1
        fb = f(b)

    return None  # exceeded max_iter without meeting tol


def irr(cash_flows: CashFlows, *, max_iter: int = 100, tol: float = 1e-6) -> float | None:
    """
    Compute annual IRR (Internal Rate of Return): the discount rate ``r`` that solves
    ``NPV(r) = sum_t CF_t / (1 + r) ** t = 0``.

    Uses a domain-bounded bracket search followed by Brent's method (bisection + secant + inverse
    quadratic interpolation; see ``_brent_root``) -- never an unbracketed method. (Mission 4,
    PV.5: this replaces a former Newton-Raphson-first design. Newton, seeded from a fixed guess,
    could converge to a mathematically real but economically meaningless root of the NPV
    polynomial -- or wander outside the valid domain and fail to converge at all -- depending
    entirely on cash-flow shape, with no way for a caller to know which happened short of
    inspecting the returned number. A bracketed method cannot do that: see `_brent_root`'s
    docstring for the structural guarantee.)

    Accepts either:
      - An iterable of cash amounts at integer periods, e.g. [-1000, 200, 200, ...]
      - An iterable of (amount, time) where time is a date/datetime or a numeric
        year offset, e.g. [(-1000, date(2024,1,1)), (1100, date(2025,1,1))]

    Returns:
      IRR as a decimal (0.12 for 12%), or None if undefined / not bracketing / no convergence.
    """
    # Normalize input
    try:
        raw: list[CashFlowItem] = list(cash_flows)
    except TypeError:
        return None

    if len(raw) < 2:
        return None

    # Detect format
    is_tuple = isinstance(raw[0], tuple | list) and len(raw[0]) == 2

    if is_tuple:
        # Dated cash flows: align times to the first timestamp
        amounts: list[float] = []
        times: list[float] = []
        t0 = cast(tuple[float, date | datetime | float], raw[0])[1]
        for item in raw:
            amt, current_t = cast(tuple[float, date | datetime | float], item)
            amounts.append(float(amt))
            times.append(_to_years(t0, current_t))
    else:
        # Simple periodic cash flows at integer periods 0..n
        amounts = [float(cast(float, x)) for x in raw]
        times = [float(i) for i in range(len(amounts))]

    # Must have sign change to have a real IRR
    has_pos = any(a > 0 for a in amounts)
    has_neg = any(a < 0 for a in amounts)
    if not (has_pos and has_neg):
        return None

    # ------------------------------------------------------------------------------------------
    # PERF (Mission 4, PV.3). `npv` is the hot loop of this module: the bracket search below calls
    # it up to 16 times and Brent's method calls it once per iteration, so on a 100-year forecast
    # this is still hundreds of discount-base evaluations per `irr()`. Two changes survive PV.5's
    # switch to Brent (a third, precomputing `dnpv`'s rate-independent numerator, does NOT: Brent
    # is derivative-free, so `dnpv` is gone -- there is nothing left to precompute it for):
    #
    #   1. The discount bases are built by a list comprehension instead of one call per term to
    #      `_discount_base`. `_discount_base` is `float((1.0 + rate) ** t)`; `1.0 + rate` is
    #      loop-invariant and `float()` on a `float` is the identity, so `base ** t` is the same
    #      double. The saturating `OverflowError -> math.inf` behaviour is preserved by catching
    #      the exception around the comprehension and rebuilding it element-wise through
    #      `_discount_base`, which yields exactly what the old per-element path yielded. (That
    #      fallback is live, not theoretical -- it is what
    #      tests/core/finance/test_irr_overflow_known_bug.py exercises.)
    #   2. The summation is `sum(map(truediv, ...))`, NOT `numpy.sum` and NOT `math.fsum`. Both of
    #      those reorder the accumulation (numpy sums pairwise, fsum is exact) and therefore return
    #      a DIFFERENT double from Python's strict left-to-right `sum` -- measured, not assumed:
    #      on this engine's own 101-term cash-flow vector, python-sequential 2105582636.5773134
    #      vs np.sum 2105582636.5773141 vs math.fsum 2105582636.577314. `map` preserves order and
    #      `sum` still accumulates left to right, so this is the same reduction, in the same order,
    #      over the same terms -- it merely removes the generator-frame overhead per term.
    #
    # NOTE on the `**` domain: a negative `base` with a fractional `t` would return a *complex* in
    # CPython, which `_discount_base`'s `float()` would have turned into a TypeError. Unreachable:
    # every `rate` this function evaluates satisfies `1 + rate > 0`, because the bracket search
    # below floors its lower bound at -0.999999 and Brent's method (see `_brent_root`) can never
    # evaluate a point outside the bracket it is given -- the same domain guarantee
    # `_discount_base`'s docstring already relies on.
    # ------------------------------------------------------------------------------------------

    def npv(rate: float) -> float:
        base = 1.0 + rate
        try:
            bases = [base**t for t in times]
        except OverflowError:
            bases = [_discount_base(rate, t) for t in times]
        try:
            return float(sum(map(truediv, amounts, bases)))
        except ZeroDivisionError:
            # A discount base underflowed to exactly 0.0 (the domain-floor bracket bound
            # -0.999999 raised to a large horizon `t` does this -- e.g. (1e-6) ** 100 == 1e-600,
            # far below the smallest representable double, ~4.9e-324). This is the mirror image
            # of `_discount_base`'s saturating-overflow fix: as `rate -> -100%` the discount base
            # correctly vanishes, so a nonzero cash flow divided by it correctly diverges to a
            # signed infinity (an infinitely-negative rate makes any future dollar worth an
            # unbounded amount today), not a crash. A zero cash flow contributes 0.0 regardless.
            return float(sum(map(_safe_div, amounts, bases)))

    # Domain-bounded bracket search.
    #
    # A valid IRR must satisfy 1 + r > 0 (r > -100%): (1 + r) ** t is the present-value base in
    # every NPV term, so at r = -100% it is a divide-by-zero and below -100% it is negative and
    # not a meaningful discount factor. Rather than seed an unbracketed search and reject whatever
    # root it happens to wander to (the former Newton-Raphson design's failure mode -- see irr.py's
    # module docstring), search only within (-1, inf) for a sign change and hand that bracket to
    # Brent's method, which is structurally incapable of returning a root outside it.
    # (Matches the `irr_10yr >= -1.0` invariant asserted in the engine tests.)
    lo, hi = -0.99, 1.0
    for _ in range(8):  # try a few expansions to find a sign change
        f_lo, f_hi = npv(lo), npv(hi)
        if f_lo == 0.0:
            return lo
        if f_hi == 0.0:
            return hi
        if f_lo * f_hi < 0.0:
            break
        # expand symmetrically
        hi *= 2.0
        lo = max(lo * 2.0, -0.999999)
    else:
        # never bracketed
        return None

    return _brent_root(npv, lo, hi, fa=f_lo, fb=f_hi, tol=tol, max_iter=max_iter)
