# tests/unit/test_recourse_negative_noi_precondition.py
"""
Mission 5 Gate V re-review, N5: `_derive_snapshot` feeds `base_forecast.purchase.cap_rate` (an
UNCONSTRAINED float -- a negative-NOI deal computes a negative purchase cap rate validly) into
`MarketSnapshot(cap_rate=...)`, which is `ge=0`. Before this fix, a negative-NOI deal raised a raw
`pydantic.ValidationError` from `MarketSnapshot`'s constructor, two layers below the public entry
points that reach it.

`compute_recourse` and `compute_combinations` are self-contained (each computes its OWN fresh
baseline) and do not check `is_genuinely_close` themselves -- the docstrings say so. At pipeline
level `is_genuinely_close` fails enough live guardrails on a negative-NOI deal to keep the gate
shut before either is reached, so this was never observed end-to-end -- but both are documented
public API (`src/market/README.md`), directly callable, and inherit the precondition regardless.

These tests exercise the direct-API path deliberately (bypassing `is_genuinely_close`, exactly
the shape of the 22-crash sweep the re-review measured) and pin: (1) a clean, named `ValueError`
in recourse's own vocabulary -- never a `pydantic.ValidationError` -- and (2) that an ordinary
positive-NOI deal is unaffected.
"""

from __future__ import annotations

import pydantic
import pytest

from src.market.recourse import compute_combinations, compute_recourse, is_genuinely_close
from src.schemas.models import FinancialInputs, FinancingTerms, IncomeModel, OperatingExpenses, UnitIncome


def _negative_noi_inputs() -> FinancialInputs:
    """Rent income (even before vacancy/bad-debt losses) nowhere near covering OPEX -> negative
    Year 1 NOI -> a negative purchase cap rate (NOI_Y1 / purchase_price), computed, not provided."""
    return FinancialInputs(
        financing=FinancingTerms(purchase_price=200_000.0, down_payment_rate=0.20, interest_rate=0.05),
        opex=OperatingExpenses(
            insurance=5_000.0,
            taxes=5_000.0,
            utilities=2_000.0,
            water_sewer=1_000.0,
            property_management=1_000.0,
        ),
        income=IncomeModel(units=[UnitIncome(rent_month=10.0, other_income_month=0.0)]),
    )


def _ordinary_positive_noi_inputs() -> FinancialInputs:
    """A deal with real, positive NOI -- the control case: neither entry point should raise."""
    return FinancialInputs(
        financing=FinancingTerms(purchase_price=300_000.0, down_payment_rate=0.20, interest_rate=0.05),
        opex=OperatingExpenses(
            insurance=1_500.0,
            taxes=3_000.0,
            utilities=800.0,
            water_sewer=600.0,
            property_management=1_200.0,
        ),
        income=IncomeModel(units=[UnitIncome(rent_month=1_800.0, other_income_month=50.0)]),
    )


def test_negative_noi_deal_fails_the_genuinely_close_gate() -> None:
    """Sanity check on the fixture: at pipeline level this deal never reaches either entry
    point, because `is_genuinely_close` shuts the gate first (the re-review's "zero crashes at
    pipeline level" finding) -- these tests exercise the direct-API path deliberately."""
    assert is_genuinely_close(_negative_noi_inputs()) is False


def test_compute_recourse_raises_named_value_error_on_negative_noi() -> None:
    """RED->GREEN: direct call, bypassing `is_genuinely_close`, on a negative-NOI deal. Must be a
    `ValueError` in recourse's own vocabulary (naming cap rate / NOI), never a raw
    `pydantic.ValidationError` surfacing from `MarketSnapshot` two layers down."""
    inputs = _negative_noi_inputs()
    with pytest.raises(ValueError) as excinfo:
        compute_recourse(inputs)
    assert not isinstance(excinfo.value, pydantic.ValidationError)
    message = str(excinfo.value)
    assert "cap rate" in message.lower()
    assert "negative" in message.lower()
    assert "noi" in message.lower()


def test_compute_combinations_raises_named_value_error_on_negative_noi() -> None:
    """Same precondition, same fix, the other newly-documented public entry point."""
    inputs = _negative_noi_inputs()
    with pytest.raises(ValueError) as excinfo:
        compute_combinations(inputs)
    assert not isinstance(excinfo.value, pydantic.ValidationError)
    message = str(excinfo.value)
    assert "cap rate" in message.lower()
    assert "negative" in message.lower()
    assert "noi" in message.lower()


def test_positive_noi_deal_is_unaffected_by_the_guard() -> None:
    """Control: the guard only trips on the actual precondition violation -- an ordinary deal
    with real NOI computes both analyses without raising."""
    inputs = _ordinary_positive_noi_inputs()
    recourse = compute_recourse(inputs)
    combos = compute_combinations(inputs)
    assert recourse is not None
    assert combos is not None
