# tests/unit/test_recourse_perturb_bitexact.py
"""
BIT-EXACTNESS PROOF for the PV.4 performance rewrite of the rent-lever `_perturb` branch.

`src.market.recourse._fast_unit_income` builds a `UnitIncome` by writing the instance's state
directly instead of going through pydantic validation (the same technique
`src.core.finance.engine._year_row` uses for `YearBreakdown` -- see
`tests/core/finance/test_engine_bitexact_refactors.py`, whose shape this file follows).

Every comparison here is on raw IEEE-754 bytes (`struct.pack`) or on plain `==`/`is` over exact
values -- never `pytest.approx`. An 8th-decimal difference, or a `0.0` vs. `-0.0` mismatch, is a
FAILURE in this file, by design.

This file also proves the two things the mission brief flagged as needing direct proof rather
than assumption:
  1. Validation-free construction is INDISTINGUISHABLE from validated construction, field-by-
     field, on raw bytes, across many units and many awkward rent deltas.
  2. Bypassing validation at CONSTRUCTION time does not disturb `validate_assignment=True` on
     the resulting object, in either direction (fast-built object still validates on assignment;
     assigning an invalid value still raises).
And it separately proves the honest-math claim from the mission brief -- floating point addition
is not associative, so "add t to every unit, then sum" and "sum, then add N * t" are NOT
interchangeable -- which is the reason `_perturb` rebuilds every `UnitIncome` individually rather
than synthesising an aggregate.
"""

from __future__ import annotations

import math
import random
import struct

import pydantic
import pytest

from src.market.recourse import _fast_unit_income
from src.schemas.models import UnitIncome


def _bits(x: float) -> bytes:
    """Raw double bytes: distinguishes 0.0 from -0.0, and matches nan to nan."""
    return struct.pack("<d", x)


def _same_float(x: float, y: float) -> bool:
    if math.isnan(x) and math.isnan(y):
        return True
    return _bits(x) == _bits(y)


# ==================================================================================================
# 1. `_fast_unit_income` == `UnitIncome(**kwargs)`, bit for bit, field for field.
# ==================================================================================================

_NASTY: list[float] = [0.0, -0.0, 1e308, -1e308, 5e-324, -5e-324, 1e16, 0.1, -0.1, 1200.375, -1200.375]


def _cases() -> list[tuple[float, float]]:
    rng = random.Random(20260829)
    cases: list[tuple[float, float]] = []
    for rent in _NASTY:
        for other in _NASTY:
            cases.append((rent, other))
    for _ in range(2_000):
        rent = rng.uniform(-1e6, 1e6) * (10.0 ** rng.randint(-6, 9))
        other = rng.uniform(-1e6, 1e6) * (10.0 ** rng.randint(-6, 9))
        cases.append((rent, other))
    return cases


@pytest.mark.parametrize("rent_month,other_income_month", _cases())
def test_fast_unit_income_is_indistinguishable_from_validated_construction(rent_month: float, other_income_month: float) -> None:
    fast = _fast_unit_income(rent_month=rent_month, other_income_month=other_income_month)
    validated = UnitIncome(rent_month=rent_month, other_income_month=other_income_month)

    assert fast == validated
    assert fast.model_dump() == validated.model_dump()
    assert fast.model_dump(mode="json") == validated.model_dump(mode="json")
    assert fast.model_dump_json() == validated.model_dump_json()
    assert fast.model_dump(exclude_unset=True) == validated.model_dump(exclude_unset=True)
    assert fast.__pydantic_fields_set__ == validated.__pydantic_fields_set__
    assert fast.__pydantic_extra__ == validated.__pydantic_extra__
    assert fast.__pydantic_private__ == validated.__pydantic_private__
    # Bit-level, not just `==`: `model_dump` / `==` comparison would let 0.0 pass for -0.0.
    assert _same_float(fast.rent_month, validated.rent_month)
    assert _same_float(fast.other_income_month, validated.other_income_month)


def test_fast_unit_income_fields_set_is_not_shared_between_units():
    """`__pydantic_fields_set__` is mutated by pydantic on attribute assignment. Sharing one set
    across units would be a real aliasing bug across a 5,000-unit rent roll, so
    `_fast_unit_income` hands out a fresh copy each time."""
    a = _fast_unit_income(rent_month=1200.0, other_income_month=50.0)
    b = _fast_unit_income(rent_month=1200.0, other_income_month=50.0)
    assert a.__pydantic_fields_set__ is not b.__pydantic_fields_set__
    assert a.__pydantic_fields_set__ == b.__pydantic_fields_set__


# ==================================================================================================
# 2. `validate_assignment=True` is undisturbed by validation-free construction.
# ==================================================================================================


def test_fast_built_unit_still_validates_on_assignment_like_a_validated_one():
    """`validate_assignment` lives on the class's `__setattr__`, not on how the instance was
    built. A fast-built `UnitIncome` must still validate (and, here, coerce) on assignment
    exactly as a normally-constructed one does."""
    fast = _fast_unit_income(rent_month=1200.0, other_income_month=50.0)
    validated = UnitIncome(rent_month=1200.0, other_income_month=50.0)

    fast.rent_month = "1300"  # type: ignore[assignment]  # pydantic coerces the string to float
    validated.rent_month = "1300"  # type: ignore[assignment]

    assert fast.rent_month == validated.rent_month == 1300.0
    assert isinstance(fast.rent_month, float)


def test_fast_built_unit_still_rejects_invalid_assignment_like_a_validated_one():
    fast = _fast_unit_income(rent_month=1200.0, other_income_month=50.0)
    validated = UnitIncome(rent_month=1200.0, other_income_month=50.0)

    with pytest.raises(pydantic.ValidationError):
        fast.rent_month = "not-a-number"  # type: ignore[assignment]
    with pytest.raises(pydantic.ValidationError):
        validated.rent_month = "not-a-number"  # type: ignore[assignment]


# ==================================================================================================
# 3. THE FORBIDDEN SHORTCUT, pinned as an executable finding.
# ==================================================================================================
#
# The founder explicitly ruled out "sum the baseline rents once, then add N * t" as a replacement
# for "add t to each unit, then sum" -- floating point addition is not associative, so the two are
# different doubles, not just a stylistic preference. Kept as a test, not a comment, so it stays
# true rather than becoming folklore.


def test_honest_per_unit_add_then_sum_differs_from_shortcut_sum_then_add_n_times():
    rng = random.Random(4242)
    mismatches = 0
    trials = 20
    for _ in range(trials):
        n = rng.randint(500, 5_000)
        rents = [rng.uniform(200.0, 5_000.0) + rng.random() for _ in range(n)]
        t = rng.uniform(-500.0, 500.0) + rng.random() * 1e-6

        honest = sum(r + t for r in rents)
        shortcut = sum(rents) + n * t

        if _bits(honest) != _bits(shortcut):
            mismatches += 1

    assert mismatches > 0, (
        "expected floating-point non-associativity to produce at least one mismatch across "
        f"{trials} trials -- if this ever stops being true, re-derive the whole 'never synthesise "
        "an aggregate' argument before trusting it"
    )
