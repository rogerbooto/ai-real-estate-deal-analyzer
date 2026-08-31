# tests/core/finance/test_engine_bitexact_refactors.py
"""
BIT-EXACTNESS PROOFS for the PV.3 performance rewrite of the finance engine.

The golden harness (`test_golden_forecasts.py`) pins the engine's OUTPUT on 34 fixed inputs. This
file pins the REASONING that made each rewrite safe -- the specific claim each optimisation rests
on, tested directly and over a far wider value range than 34 cases can cover. The two are
complements: golden catches "a shipped number moved"; this catches "the argument for why it
couldn't have moved was wrong", which is the thing that would let a future edit reintroduce the
same class of bug somewhere the goldens do not reach.

Every comparison here is on raw IEEE-754 bytes (`struct.pack`) or on plain `==` over exact
values -- never `pytest.approx`. An 8th-decimal difference is a FAILURE in this file, by design.
"""

from __future__ import annotations

import math
import random
import struct
from dataclasses import dataclass

import pytest

from src.core.finance.amortization import YearDebt, amortization_payment, amortization_schedule
from src.core.finance.engine import _year_row
from src.schemas.models import YearBreakdown


def _bits(x: float) -> bytes:
    """Raw double bytes: distinguishes 0.0 from -0.0, and matches nan to nan."""
    return struct.pack("<d", x)


# ==================================================================================================
# 1. The unrolled `total_opex` chain == `sum([...])`
# ==================================================================================================
#
# The year loop used to build a 12-element list and call `sum()` on it. It now evaluates
# `0.0 + a + b + ... + l` directly. The claim: CPython's `sum` seeds with int 0 and switches to a
# float accumulator on the first float, so it computes exactly that chain, in that order.


def _unrolled(v: list[float]) -> float:
    a, b, c, d, e, f, g, h, i, j, k, m = v
    return 0.0 + a + b + c + d + e + f + g + h + i + j + k + m


_NASTY = [0.0, -0.0, 1e308, -1e308, 5e-324, -5e-324, 1e16, 0.1, -0.1, math.inf, -math.inf]


def _same_float(x: float, y: float) -> bool:
    if math.isnan(x) and math.isnan(y):
        return True
    return _bits(x) == _bits(y)


def test_unrolled_total_opex_equals_builtin_sum_over_random_vectors() -> None:
    """20,000 twelve-term vectors spanning the full exponent range, plus signed zeros, infinities
    and subnormals. Zero tolerance: the raw bytes must match, so `0.0` vs `-0.0` is a failure."""
    rng = random.Random(20260829)
    for _ in range(20_000):
        v = [rng.choice(_NASTY) if rng.random() < 0.25 else rng.uniform(-1e6, 1e6) * (10.0 ** rng.randint(-300, 300)) for _ in range(12)]
        assert _same_float(_unrolled(v), sum(v)), v


def test_unrolled_total_opex_equals_builtin_sum_on_signed_zero_corner() -> None:
    """The one corner where a naive unroll would have been wrong: `sum` seeds with 0.0, so an
    all-negative-zero vector sums to +0.0, not -0.0. The chain must agree, bit for bit."""
    v = [-0.0] * 12
    assert _bits(sum(v)) == _bits(0.0)
    assert _bits(_unrolled(v)) == _bits(sum(v))


# ==================================================================================================
# 2. `_year_row` == `YearBreakdown(**kwargs)`
# ==================================================================================================
#
# The year loop builds `YearBreakdown` rows by writing the instance state directly instead of
# going through pydantic validation (~3.1 us -> ~0.8 us each; `model_construct` was measured
# SLOWER than validation, at ~5.1 us, and is not used). The claim: for a model with no validators,
# no aliases, no computed fields and no private attributes, the two produce indistinguishable
# objects.

_ROW_VALUE_SETS: list[dict[str, float]] = [
    {"scale": 1.0, "sign": 1.0},
    {"scale": 1e12, "sign": 1.0},
    {"scale": 1e-9, "sign": -1.0},
    {"scale": 0.0, "sign": 1.0},
]


def _row_kwargs(scale: float, sign: float, *, cap: float | None) -> dict[str, object]:
    names = [n for n in YearBreakdown.model_fields if n not in ("year", "notes", "cap_rate_applied")]
    kwargs: dict[str, object] = {n: sign * scale * (idx + 1) * 1.0000001 for idx, n in enumerate(names)}
    kwargs["year"] = 7
    kwargs["cap_rate_applied"] = cap
    kwargs["notes"] = ["a note", "another"]
    return kwargs


@pytest.mark.parametrize("values", _ROW_VALUE_SETS)
@pytest.mark.parametrize("cap", [0.055, None])
def test_year_row_is_indistinguishable_from_validated_construction(values: dict[str, float], cap: float | None) -> None:
    kwargs = _row_kwargs(values["scale"], values["sign"], cap=cap)
    fast = _year_row(**kwargs)  # type: ignore[arg-type]
    validated = YearBreakdown(**kwargs)  # type: ignore[arg-type]

    assert fast == validated
    assert fast.model_dump() == validated.model_dump()
    assert fast.model_dump(mode="json") == validated.model_dump(mode="json")
    assert fast.model_dump_json() == validated.model_dump_json()
    assert fast.model_dump(exclude_unset=True) == validated.model_dump(exclude_unset=True)
    assert fast.__pydantic_fields_set__ == validated.__pydantic_fields_set__
    assert fast.__pydantic_extra__ == validated.__pydantic_extra__
    assert fast.__pydantic_private__ == validated.__pydantic_private__
    # Bit-level, not just `==`: `model_dump` comparison would let 0.0 pass for -0.0.
    for name in YearBreakdown.model_fields:
        a, b = getattr(fast, name), getattr(validated, name)
        if isinstance(a, float) and isinstance(b, float):
            assert _bits(a) == _bits(b), name
        else:
            assert a == b, name


def test_year_row_fields_set_is_not_shared_between_rows() -> None:
    """`__pydantic_fields_set__` is mutated by pydantic on attribute assignment. Sharing one set
    across rows would be a real aliasing bug, so `_year_row` hands out a fresh copy each time."""
    a = _year_row(**_row_kwargs(1.0, 1.0, cap=0.05))  # type: ignore[arg-type]
    b = _year_row(**_row_kwargs(1.0, 1.0, cap=0.05))  # type: ignore[arg-type]
    assert a.__pydantic_fields_set__ is not b.__pydantic_fields_set__
    assert a.__pydantic_fields_set__ == b.__pydantic_fields_set__


# ==================================================================================================
# 3. The column-oriented amortization core == the original row-oriented one
# ==================================================================================================
#
# `amortization_schedule` now delegates to `schedule_columns` (four float lists) so the engine can
# read the schedule without materialising a `YearDebt` per year. The claim: identical arithmetic,
# statement for statement. Checked against the ORIGINAL implementation, reproduced verbatim below
# so this test compares against history rather than against itself.

_EPS = 1e-6


@dataclass(frozen=True)
class _LegacyYearDebt:
    year: int
    interest: float
    principal: float
    payment: float
    ending_balance: float


def _legacy_amortization_schedule(principal: float, rate: float, amort_years: int, io_years: int, horizon_years: int):
    """VERBATIM copy of the pre-PV.3 implementation. Do not "improve" it -- its whole value is
    being a frozen record of what the numbers used to be."""
    if principal < 0:
        raise ValueError("principal must be >= 0")
    if any(x < 0 for x in (amort_years, io_years, horizon_years)):
        raise ValueError("amort_years, io_years, and horizon_years must be >= 0")
    out: list[_LegacyYearDebt] = []
    bal = float(principal)
    for y in range(1, io_years + 1):
        interest = bal * max(rate, 0.0)
        out.append(_LegacyYearDebt(y, interest=interest, principal=0.0, payment=interest, ending_balance=bal))
    if amort_years > 0:
        pay = amortization_payment(bal, rate, amort_years)
        for i in range(1, amort_years + 1):
            y = io_years + i
            interest = bal * max(rate, 0.0)
            principal_pay = max(0.0, pay - interest)
            bal = max(0.0, bal - principal_pay)
            if bal < _EPS:
                bal = 0.0
            out.append(_LegacyYearDebt(y, interest=interest, principal=principal_pay, payment=pay, ending_balance=bal))
    last_bal = out[-1].ending_balance if out else 0.0
    for y in range(len(out) + 1, horizon_years + 1):
        out.append(_LegacyYearDebt(y, interest=0.0, principal=0.0, payment=0.0, ending_balance=last_bal))
    return out[:horizon_years]


@pytest.mark.parametrize("principal", [0.0, 1.0, 399_900.0, 475_000_000.0])
@pytest.mark.parametrize("rate", [0.0, -0.05, 0.001, 0.055, 0.18])
@pytest.mark.parametrize("amort_years,io_years,horizon_years", [(30, 0, 10), (30, 0, 100), (15, 5, 30), (0, 0, 5), (25, 10, 3), (5, 0, 5)])
def test_column_schedule_matches_the_original_row_schedule_bit_for_bit(
    principal: float, rate: float, amort_years: int, io_years: int, horizon_years: int
) -> None:
    new = amortization_schedule(principal, rate, amort_years, io_years, horizon_years)
    old = _legacy_amortization_schedule(principal, rate, amort_years, io_years, horizon_years)
    assert len(new) == len(old)
    for a, b in zip(new, old, strict=True):
        assert isinstance(a, YearDebt)
        assert a.year == b.year
        assert _bits(a.interest) == _bits(b.interest)
        assert _bits(a.principal) == _bits(b.principal)
        assert _bits(a.payment) == _bits(b.payment)
        assert _bits(a.ending_balance) == _bits(b.ending_balance)


# ==================================================================================================
# 4. THE NUMPY TRAP, pinned as an executable finding
# ==================================================================================================
#
# The one thing a future performance pass most needs to know before reaching for numpy in this
# module. Kept as a test, not a comment, so it stays true rather than becoming folklore.


def test_numpy_elementwise_power_is_bit_identical_but_numpy_summation_is_not() -> None:
    """ELEMENT-WISE operations are safe to vectorise; REDUCTIONS are not.

    `numpy` computes `x ** t` element by element through the same libm `pow` CPython uses, so the
    results are identical doubles. But `numpy.sum` accumulates PAIRWISE and `math.fsum` accumulates
    EXACTLY, while Python's `sum` accumulates strictly left to right -- so both return a different
    double from the one this engine has always shipped. `np.cumsum(x)[-1]` is sequential and does
    agree, which is why it is the only numpy reduction that could ever be substituted here.
    """
    np = pytest.importorskip("numpy")
    rng = random.Random(4242)

    pow_mismatches = 0
    for _ in range(300):
        n = rng.randint(2, 130)
        base = 1.0 + rng.uniform(-0.9, 4.0)
        exps = np.arange(0.0, float(n))
        if [base**t for t in exps.tolist()] != (base**exps).tolist():
            pow_mismatches += 1
    assert pow_mismatches == 0, "numpy element-wise ** diverged from CPython float **"

    npsum_mismatches = 0
    cumsum_mismatches = 0
    fsum_mismatches = 0
    for _ in range(2_000):
        n = rng.randint(8, 140)
        scale = 10.0 ** rng.randint(-8, 9)
        x = [rng.uniform(-1.0, 1.0) * scale for _ in range(n)]
        arr = np.array(x)
        sequential = sum(x)
        npsum_mismatches += float(arr.sum()) != sequential
        cumsum_mismatches += float(np.cumsum(arr)[-1]) != sequential
        fsum_mismatches += math.fsum(x) != sequential

    assert cumsum_mismatches == 0, "np.cumsum(x)[-1] is expected to reproduce sequential summation"
    assert npsum_mismatches > 0, (
        "np.sum was expected to DIFFER from Python's sequential sum on at least some vectors. "
        "If this ever stops being true, re-derive the whole reduction argument before trusting it."
    )
    assert fsum_mismatches > 0, "math.fsum was expected to differ from Python's sequential sum"
