# src/core/finance/dual.py
"""
Forward-mode dual numbers with a fixed-width tangent vector of 4 (Mission 5, IA.1a).

WHAT THIS IS. A `Dual4` carries a primal float (`re`) plus four tangent slots (`d0..d3`) --
d(value)/d(direction_j) for up to four caller-named directions -- through ordinary Python
arithmetic. One engine pass on `Dual4` inputs therefore yields the value AND all four partial
derivatives at once (the whole point: one pass = the full Jacobian, measured at ~4.1x a plain
float pass vs 8 engine passes for central finite differences; see
docs/plans/mission-5-discovery/D1_ad_design.md §1).

WHY UNROLLED FLOAT SLOTS AND NOT numpy / tuples / a tape:
  * numpy-backed tangents were MEASURED slower at this width -- 11.3x on the small-op-count
    shape (D.2), 2.0x vs this exact class on the full engine slice (D.1 §1) -- because per-op
    array allocation swamps a length-4 vector. Mission 4's "do not vectorise" verdict stands,
    re-measured twice. No dependency is added.
  * tuple tangents measured 6.5x an engine pass vs 4.1x for these unrolled slots (D.1 §1).
  * a reverse-mode tape measured 6.9x AND carries O(ops) live memory per probe; at 4 inputs x
    8 outputs, forward wins outright (D.1 §1). Only per-unit-rent differentiation (thousands of
    inputs) would justify reverse mode, and that is explicitly out of scope.

SEMANTICS -- "differentiate the program as written":
  * Comparisons (`<`, `<=`, `>`, `>=`, `==`, `!=`) and truthiness read the PRIMAL only, so a
    dual pass takes exactly the branches the float pass takes. At a kink (`max(0.0, x)` at
    x == 0, the amortization balance snap, the rate clamp) the tangent is the one-sided
    derivative of the branch the program actually executes. That is deliberate: the search
    layer safeguards against kinks; this layer must never invent smoothness.
  * The primal arithmetic inside every operator is the IDENTICAL IEEE-754 operation, in the
    identical order, that the float path performs -- so the primal of a dual pass is
    bit-identical to the float pass by construction (pinned by tests/core/finance/
    test_jacobian.py against the golden matrix).
  * `float(Dual4)` is NOT provided, on purpose: an implicit float() would silently truncate
    tangents (e.g. `bal = float(principal)` in amortization would have eaten the loan tangent).
    Anything that needs the primal must say so explicitly via `primal()`. Loud beats convenient.
  * `Dual4 ** Dual4` and `float ** Dual4` are NOT provided (nothing in the engine needs them;
    an unexpected use raises TypeError instead of guessing).

This class is core-private mechanics: it is deliberately NOT exported from
`src.core.finance.__init__`. The public seam is `src/core/finance/jacobian.py`.
"""

from __future__ import annotations

import math
from typing import cast


class Dual4:
    """A scalar `re` plus a fixed 4-wide tangent vector `(d0, d1, d2, d3)`.

    Subclassing is unsupported: operators dispatch on ``o.__class__ is Dual4`` (measured
    meaningfully faster than ``isinstance`` in the hot pass, and there is no legitimate
    subclass).
    """

    __slots__ = ("re", "d0", "d1", "d2", "d3")

    def __init__(self, re: float, d0: float = 0.0, d1: float = 0.0, d2: float = 0.0, d3: float = 0.0) -> None:
        self.re = re
        self.d0 = d0
        self.d1 = d1
        self.d2 = d2
        self.d3 = d3

    # -- arithmetic -------------------------------------------------------------------------

    def __add__(self, o: float | Dual4) -> Dual4:
        if o.__class__ is Dual4:
            od = cast(Dual4, o)
            return Dual4(self.re + od.re, self.d0 + od.d0, self.d1 + od.d1, self.d2 + od.d2, self.d3 + od.d3)
        of = cast(float, o)
        return Dual4(self.re + of, self.d0, self.d1, self.d2, self.d3)

    def __radd__(self, o: float) -> Dual4:
        # o is never a Dual4 here (Python only calls the reflected op for a foreign left operand)
        return Dual4(o + self.re, self.d0, self.d1, self.d2, self.d3)

    def __sub__(self, o: float | Dual4) -> Dual4:
        if o.__class__ is Dual4:
            od = cast(Dual4, o)
            return Dual4(self.re - od.re, self.d0 - od.d0, self.d1 - od.d1, self.d2 - od.d2, self.d3 - od.d3)
        of = cast(float, o)
        return Dual4(self.re - of, self.d0, self.d1, self.d2, self.d3)

    def __rsub__(self, o: float) -> Dual4:
        return Dual4(o - self.re, -self.d0, -self.d1, -self.d2, -self.d3)

    def __mul__(self, o: float | Dual4) -> Dual4:
        if o.__class__ is Dual4:
            od = cast(Dual4, o)
            a, b = self.re, od.re
            return Dual4(
                a * b,
                self.d0 * b + a * od.d0,
                self.d1 * b + a * od.d1,
                self.d2 * b + a * od.d2,
                self.d3 * b + a * od.d3,
            )
        of = cast(float, o)
        return Dual4(self.re * of, self.d0 * of, self.d1 * of, self.d2 * of, self.d3 * of)

    def __rmul__(self, o: float) -> Dual4:
        return Dual4(o * self.re, self.d0 * o, self.d1 * o, self.d2 * o, self.d3 * o)

    def __truediv__(self, o: float | Dual4) -> Dual4:
        if o.__class__ is Dual4:
            od = cast(Dual4, o)
            b = od.re
            q = self.re / b  # the float path's own division, same operands, same order
            return Dual4(
                q,
                (self.d0 - q * od.d0) / b,
                (self.d1 - q * od.d1) / b,
                (self.d2 - q * od.d2) / b,
                (self.d3 - q * od.d3) / b,
            )
        of = cast(float, o)
        return Dual4(self.re / of, self.d0 / of, self.d1 / of, self.d2 / of, self.d3 / of)

    def __rtruediv__(self, o: float) -> Dual4:
        b = self.re
        q = o / b
        k = -q / b  # d(o/x)/dx = -o/x**2
        return Dual4(q, k * self.d0, k * self.d1, k * self.d2, k * self.d3)

    def __pow__(self, o: float | Dual4) -> Dual4:
        if o.__class__ is Dual4:
            return NotImplemented  # dual exponent: nothing in the engine needs it -> TypeError
        of = cast(float, o)
        p = self.re**of  # identical primal op (raises exactly where the float path raises)
        if self.re != 0.0 or of >= 1.0:
            k = of * self.re ** (of - 1.0)
        else:
            # d(x**n)/dx at x == 0 with n < 1 is unbounded; nan (not a made-up 0.0) so the
            # Jacobian layer's isfinite packing degrades the row to None with a reason.
            k = math.nan
        return Dual4(p, k * self.d0, k * self.d1, k * self.d2, k * self.d3)

    def __neg__(self) -> Dual4:
        return Dual4(-self.re, -self.d0, -self.d1, -self.d2, -self.d3)

    # -- primal-branch comparisons / truthiness ---------------------------------------------

    def __lt__(self, o: float | Dual4) -> bool:
        return self.re < (cast(Dual4, o).re if o.__class__ is Dual4 else cast(float, o))

    def __le__(self, o: float | Dual4) -> bool:
        return self.re <= (cast(Dual4, o).re if o.__class__ is Dual4 else cast(float, o))

    def __gt__(self, o: float | Dual4) -> bool:
        return self.re > (cast(Dual4, o).re if o.__class__ is Dual4 else cast(float, o))

    def __ge__(self, o: float | Dual4) -> bool:
        return self.re >= (cast(Dual4, o).re if o.__class__ is Dual4 else cast(float, o))

    def __eq__(self, o: object) -> bool:
        if o.__class__ is Dual4:
            return self.re == cast(Dual4, o).re
        if isinstance(o, int | float):
            return self.re == o
        return NotImplemented

    def __ne__(self, o: object) -> bool:
        result = self.__eq__(o)
        if result is NotImplemented:
            return result
        return not result

    # Defining __eq__ clears the default __hash__; Dual4 is mutable-slotted and primal-equality
    # based, so being unhashable is correct, not an accident.

    def __bool__(self) -> bool:
        return self.re != 0.0

    def __repr__(self) -> str:
        return f"Dual4(re={self.re!r}, d=({self.d0!r}, {self.d1!r}, {self.d2!r}, {self.d3!r}))"


def primal(x: float) -> float:
    """The primal value of ``x``: ``x.re`` for a Dual4, ``x`` itself (untouched) for a float.

    Annotated ``float -> float`` because the engine's dual-generic paths keep their float
    annotations and duals flow through them duck-typed behind the one documented cast boundary
    in `jacobian.py` (the D.1 §4 mypy ruling: float annotations + a narrow, Any-free facade,
    rather than a constrained TypeVar that cannot express per-local heterogeneity).
    """
    if isinstance(x, Dual4):
        return x.re
    return x


def tangents(x: float, n: int) -> tuple[float, ...]:
    """The first ``n`` tangent slots of ``x`` (exact zeros for a plain float).

    A plain float is a theta-constant on this pass: its sensitivity to every direction is a
    true 0.0 -- which is a real derivative, never to be confused with the Jacobian layer's
    ``None`` ("no trustworthy derivative exists").
    """
    if isinstance(x, Dual4):
        return (x.d0, x.d1, x.d2, x.d3)[:n]
    return (0.0,) * n


def log1p(x: float) -> float:
    """``math.log1p`` extended to Dual4 -- the exact dual form of the stable primitive.

    For a float this IS ``math.log1p(x)``, bit for bit. For a Dual4 the primal is
    ``math.log1p(x.re)`` (the identical stable op the float pass performs, so the primal stays
    bit-identical by construction) and the tangent follows the exact chain rule::

        log1p(a + b*eps) = log1p(a) + (b / (1 + a)) * eps

    The tangent factor ``1/(1+a)`` is well-conditioned precisely where the stable branch lives
    (small ``a``: the factor is ~1.0), so extending the primitive costs no accuracy anywhere.
    Added for Mission 5 Gate V B1: `_amortization_payment_stable` sits on the engine's dual
    seam (`schedule_columns` receives the seeded rate), and a bare ``math.log1p`` raises
    ``TypeError`` on a Dual4 because Dual4 refuses ``__float__`` on purpose.
    """
    if isinstance(x, Dual4):
        p = math.log1p(x.re)
        k = 1.0 / (1.0 + x.re)
        return cast(float, Dual4(p, k * x.d0, k * x.d1, k * x.d2, k * x.d3))
    return math.log1p(x)


def expm1(x: float) -> float:
    """``math.expm1`` extended to Dual4 -- the exact dual form of the stable primitive.

    For a float this IS ``math.expm1(x)``, bit for bit. For a Dual4 the primal is
    ``math.expm1(x.re)`` (identical stable op, bit-identical primal by construction) and the
    tangent follows the exact chain rule::

        expm1(a + b*eps) = expm1(a) + (b * exp(a)) * eps

    ``math.exp(a)`` is fully stable for the small ``a`` the stable amortization branch feeds
    through here (~1.0), so no cancellation is introduced in the tangent. See `log1p` above
    for the B1 context.
    """
    if isinstance(x, Dual4):
        p = math.expm1(x.re)
        k = math.exp(x.re)
        return cast(float, Dual4(p, k * x.d0, k * x.d1, k * x.d2, k * x.d3))
    return math.expm1(x)


def coerce_like_float(x: float) -> float:
    """``float(x)`` for real numbers (the pre-existing behaviour, bit for bit), pass-through
    for a Dual4 -- for spots like ``bal = float(principal)`` where the float path's coercion
    must survive unchanged but an implicit ``float()`` on a dual would silently drop tangents
    (`Dual4` has no ``__float__`` for exactly that reason).
    """
    if isinstance(x, Dual4):
        return cast(float, x)
    return float(x)
