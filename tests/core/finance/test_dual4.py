# tests/core/finance/test_dual4.py
"""
Unit tests for `src/core/finance/dual.py` -- the forward-mode dual scalar (Mission 5, IA.1a).

Two properties carry the whole AD design and are pinned here at the operator level:

  1. PRIMAL EXACTNESS: the primal inside every operator is the IDENTICAL IEEE-754 operation the
     float path performs -- compared on raw bytes, not with `approx`. This is what makes the
     engine's dual pass bit-identical to its float pass by construction.
  2. TANGENT CORRECTNESS: each operator's tangent is the analytic derivative, checked against
     tight central finite differences of the same scalar function.

Plus the loud-failure contract: no `__float__` (silent tangent truncation is the one bug class
this type must make impossible), no dual exponents, primal-branch comparisons/truthiness.
"""

from __future__ import annotations

import math
import struct
from collections.abc import Callable

import pytest

from src.core.finance.dual import Dual4, coerce_like_float, primal, tangents


def _bits(x: float) -> bytes:
    return struct.pack("<d", x)


def _d(v: float, slot: int = 0) -> Dual4:
    seeds = [0.0, 0.0, 0.0, 0.0]
    seeds[slot] = 1.0
    return Dual4(v, *seeds)


# ---------------------------------------------------------------------------------------------
# 1. Primal exactness, on raw bytes
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "a,b",
    [
        (3.1415926535, 2.718281828),
        (1e-8, 7.7),
        (-0.0, 4.25),
        (555000.0, 0.06),
        (1.0553, 9.0),
    ],
)
def test_primal_is_bitwise_identical_to_float_arithmetic(a: float, b: float) -> None:
    ops: list[tuple[str, Callable[[float, float], float]]] = [
        ("add", lambda x, y: x + y),
        ("radd", lambda x, y: y + x),
        ("sub", lambda x, y: x - y),
        ("rsub", lambda x, y: y - x),
        ("mul", lambda x, y: x * y),
        ("rmul", lambda x, y: y * x),
        ("div", lambda x, y: x / y),
        ("rdiv", lambda x, y: y / x),
        ("pow", lambda x, y: x**y),
        ("neg", lambda x, y: -x),
    ]
    for name, op in ops:
        try:
            expect = op(a, b)
        except ZeroDivisionError:
            # the float path raises here (e.g. 4.25 / -0.0); the dual path must raise the same
            with pytest.raises(ZeroDivisionError):
                op(_d(a), b)  # type: ignore[arg-type]
            continue
        got = op(_d(a), b)  # type: ignore[arg-type]
        assert isinstance(got, Dual4), name
        assert _bits(got.re) == _bits(expect), f"{name}: primal drifted"
    # dual-dual variants for the symmetric ops
    for name, op in ops[:8:2]:  # add, sub, mul, div
        try:
            expect = op(a, b)
        except ZeroDivisionError:
            with pytest.raises(ZeroDivisionError):
                op(_d(a), _d(b, 1))  # type: ignore[arg-type]
            continue
        got = op(_d(a), _d(b, 1))  # type: ignore[arg-type]
        assert _bits(got.re) == _bits(expect), f"dual-dual {name}: primal drifted"


def test_primal_exactness_through_a_composed_expression() -> None:
    """The amortization payment formula, float vs dual, byte-for-byte on the primal."""

    def pay(r: float) -> float:
        return r * 555000.0 / (1.0 - (1.0 + r) ** (-30))

    r = 0.06
    assert _bits(primal(pay(_d(r)))) == _bits(pay(r))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------------------------
# 2. Tangent correctness vs central finite differences
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fn",
    [
        lambda x: x * x * x + 2.0 * x - 7.0,
        lambda x: 1.0 / (x + 3.0),
        lambda x: (x * 5.5 - 2.0) / (x * x + 1.0),
        lambda x: (1.0 + x) ** (-30),
        lambda x: x**2.5,
        lambda x: -(x * 3.0) + (4.0 - x) * (x / 7.0),
    ],
)
@pytest.mark.parametrize("x0", [0.06, 1.7, 42.0])
def test_tangent_matches_central_fd(fn: Callable[[float], float], x0: float) -> None:
    h = 1e-6 * max(1.0, abs(x0))
    fd = (fn(x0 + h) - fn(x0 - h)) / (2 * h)
    ad = fn(_d(x0))  # type: ignore[arg-type]
    got = ad.d0 if isinstance(ad, Dual4) else 0.0
    assert got == pytest.approx(fd, rel=1e-6, abs=1e-9)


def test_all_four_slots_propagate_independently() -> None:
    x = Dual4(2.0, 1.0, 0.0, 0.0, 0.0)
    y = Dual4(5.0, 0.0, 1.0, 0.0, 0.0)
    z = Dual4(7.0, 0.0, 0.0, 1.0, 0.0)
    w = Dual4(3.0, 0.0, 0.0, 0.0, 1.0)
    out = x * y + z / w  # d/dx=y=5, d/dy=x=2, d/dz=1/w, d/dw=-z/w**2
    assert out.re == 2.0 * 5.0 + 7.0 / 3.0
    assert out.d0 == 5.0
    assert out.d1 == 2.0
    assert out.d2 == pytest.approx(1.0 / 3.0, rel=1e-15)
    assert out.d3 == pytest.approx(-7.0 / 9.0, rel=1e-15)


def test_pow_singular_tangent_is_nan_not_zero() -> None:
    """d(x**n)/dx at x=0 with n<1 is unbounded: the tangent must be nan (which the Jacobian
    layer degrades to None-with-reason), never a fabricated finite number."""
    out = _d(0.0) ** 0.5
    assert out.re == 0.0  # the primal float path's own result
    assert math.isnan(out.d0)


def test_dual_exponent_and_rpow_raise() -> None:
    with pytest.raises(TypeError):
        _ = _d(2.0) ** _d(3.0)
    with pytest.raises(TypeError):
        _ = 2.0 ** _d(3.0)  # type: ignore[operator]


# ---------------------------------------------------------------------------------------------
# 3. Primal-branch semantics and loud failures
# ---------------------------------------------------------------------------------------------


def test_comparisons_and_truthiness_read_the_primal() -> None:
    d = Dual4(1.5, d0=-99.0)  # wild tangent must not affect any branch decision
    assert d > 1.0 and d >= 1.5 and d < 2.0 and d <= 1.5
    assert d == 1.5 and d != 1.4
    assert 2.0 > d and 1.0 < d  # reflected paths
    assert bool(d) is True
    assert bool(Dual4(0.0, d0=123.0)) is False
    assert max(0.0, Dual4(-1.0, d0=1.0)) == 0.0  # clamped branch returns the float, as written
    picked = min([Dual4(3.0, d0=1.0), Dual4(2.0, d1=1.0), 2.5])
    assert isinstance(picked, Dual4) and picked.re == 2.0 and picked.d1 == 1.0


def test_no_implicit_float_conversion() -> None:
    """`float(dual)` must FAIL: an implicit conversion would silently truncate tangents (the
    exact bug `coerce_like_float` exists to make impossible at the one sanctioned site)."""
    with pytest.raises(TypeError):
        float(_d(1.0))  # type: ignore[arg-type]


def test_helpers() -> None:
    d = Dual4(4.0, 1.0, 2.0, 3.0, 4.0)
    assert primal(d) == 4.0  # type: ignore[arg-type]
    assert primal(4.0) == 4.0
    assert tangents(d, 2) == (1.0, 2.0)  # type: ignore[arg-type]
    assert tangents(7.0, 3) == (0.0, 0.0, 0.0)
    assert coerce_like_float(d) is d  # type: ignore[arg-type, comparison-overlap]
    assert _bits(coerce_like_float(-0.0)) == _bits(-0.0)
    assert coerce_like_float(5) == 5.0 and isinstance(coerce_like_float(5), float)
    assert "Dual4" in repr(d)


def test_unhashable_by_design() -> None:
    with pytest.raises(TypeError):
        hash(_d(1.0))


def test_equality_against_foreign_types_defers() -> None:
    """`==`/`!=` vs a non-numeric returns NotImplemented internally, so Python falls back to
    identity semantics instead of this class guessing an answer."""
    d = _d(1.0)
    assert (d == "1.0") is False
    assert (d != "1.0") is True
    assert (d == Dual4(1.0, d0=5.0)) is True  # dual-dual equality reads primals only
