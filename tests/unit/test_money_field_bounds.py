# tests/unit/test_money_field_bounds.py
"""
Mission 5 OI.1 (Gate D, PD.1 §(c)): lower bounds on the 17 currency-denominated fields of
``FinancialInputs``.

DECISION (``docs/plans/mission-5-discovery/PD1_product_calls.md`` §(c)): ``purchase_price`` is
``gt=0`` (an all-cash deal is modelled as ``down_payment_rate=1.0``, never a zero price -- see the
``all_cash_deal`` golden case). Every other money field -- ``closing_costs``, all 12 ``opex`` line
items, ``UnitIncome.rent_month``/``other_income_month``, and ``capex_reserve_upfront`` -- is
``ge=0``: zero is legitimate (self-managed, vacant unit, absent expense, no upfront capex). No rate,
ratio or year-count field is touched in this pass.

This file pins the floor at exactly zero: a negative value is rejected, and -- because
over-tightening is the likelier defect in a pass like this one -- an exact ``0.0`` on every ``ge=0``
field is still ACCEPTED.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.schemas.models import FinancialInputs, OperatingExpenses, UnitIncome
from tests.utils import make_financial_inputs, make_financing_terms, make_income_model, make_opex

# ---------------------------------------------------------------------------------------
# purchase_price: gt=0 (the one field with a strictly-positive floor)
# ---------------------------------------------------------------------------------------


def test_purchase_price_negative_rejected() -> None:
    with pytest.raises(ValidationError):
        make_financing_terms(purchase_price=-1.0)


def test_purchase_price_zero_rejected() -> None:
    """THE PIN: unlike every other money field, zero is NOT legitimate here -- an all-cash
    purchase is modelled via down_payment_rate=1.0, never a zero price (all_cash_deal golden case)."""
    with pytest.raises(ValidationError):
        make_financing_terms(purchase_price=0.0)


def test_purchase_price_positive_accepted() -> None:
    f = make_financing_terms(purchase_price=1.0)
    assert f.purchase_price == 1.0


# ---------------------------------------------------------------------------------------
# closing_costs: ge=0
# ---------------------------------------------------------------------------------------


def test_closing_costs_negative_rejected() -> None:
    with pytest.raises(ValidationError):
        make_financing_terms(closing_costs=-1.0)


def test_closing_costs_zero_accepted() -> None:
    """Guards against over-tightening: zero closing costs (seller pays all) must still validate."""
    f = make_financing_terms(closing_costs=0.0)
    assert f.closing_costs == 0.0


# ---------------------------------------------------------------------------------------
# OperatingExpenses: all 12 line items are ge=0
# ---------------------------------------------------------------------------------------

_OPEX_FIELDS = (
    "insurance",
    "taxes",
    "utilities",
    "water_sewer",
    "property_management",
    "repairs_maintenance",
    "trash",
    "landscaping",
    "snow_removal",
    "hoa_fees",
    "reserves",
    "other",
)


@pytest.mark.parametrize("field", _OPEX_FIELDS)
def test_opex_field_negative_rejected(field: str) -> None:
    with pytest.raises(ValidationError):
        make_opex(**{field: -1.0})


@pytest.mark.parametrize("field", _OPEX_FIELDS)
def test_opex_field_zero_accepted(field: str) -> None:
    """Guards against over-tightening: zero means the expense is absent, which is common and
    correct (self-managed => property_management=0, no HOA => hoa_fees=0, ...)."""
    o = make_opex(**{field: 0.0})
    assert getattr(o, field) == 0.0


def test_all_opex_fields_zero_accepted_simultaneously() -> None:
    """The golden matrix anchors 30 exact zeros on nine of these paths -- confirm the whole
    all-zero shape (not just one field at a time) still validates."""
    zeros = dict.fromkeys(_OPEX_FIELDS, 0.0)
    o = OperatingExpenses(**zeros, expense_growth=0.0)
    for field in _OPEX_FIELDS:
        assert getattr(o, field) == 0.0


# ---------------------------------------------------------------------------------------
# UnitIncome.rent_month / other_income_month: ge=0
# ---------------------------------------------------------------------------------------


def test_rent_month_negative_rejected() -> None:
    with pytest.raises(ValidationError):
        UnitIncome(rent_month=-1.0)


def test_rent_month_zero_accepted() -> None:
    """Guards against over-tightening: a vacant unit, a unit under renovation, or the
    owner-occupied unit in a house-hack all have rent_month=0."""
    u = UnitIncome(rent_month=0.0)
    assert u.rent_month == 0.0


def test_other_income_month_negative_rejected() -> None:
    with pytest.raises(ValidationError):
        UnitIncome(rent_month=1000.0, other_income_month=-1.0)


def test_other_income_month_zero_accepted() -> None:
    u = UnitIncome(rent_month=1000.0, other_income_month=0.0)
    assert u.other_income_month == 0.0


# ---------------------------------------------------------------------------------------
# capex_reserve_upfront: ge=0
# ---------------------------------------------------------------------------------------


def test_capex_reserve_upfront_negative_rejected() -> None:
    with pytest.raises(ValidationError):
        FinancialInputs(
            financing=make_financing_terms(),
            opex=make_opex(),
            income=make_financial_inputs().income,
            capex_reserve_upfront=-1.0,
        )


def test_capex_reserve_upfront_zero_accepted() -> None:
    """Guards against over-tightening: zero is the default and the common case."""
    fi = FinancialInputs(
        financing=make_financing_terms(),
        opex=make_opex(),
        income=make_financial_inputs().income,
        capex_reserve_upfront=0.0,
    )
    assert fi.capex_reserve_upfront == 0.0


# ---------------------------------------------------------------------------------------
# Explicitly NOT bounded in this pass: rates, ratios, year-counts (a spot check, not full coverage)
# ---------------------------------------------------------------------------------------


def test_rent_growth_still_accepts_negative() -> None:
    """rent_growth is a rate, not a money field -- declining markets are real and this pass
    must not touch it. (Constructed, not assigned: IncomeModel is frozen since Gate V N3.)"""
    im = make_income_model(rent_growth=-0.05)
    assert im.rent_growth == -0.05


def test_amort_years_still_accepts_zero() -> None:
    """amort_years is explicitly out of scope for this pass (the all_cash_deal golden case ships
    amort_years=0 with down_payment_rate=1.0); a naive floor here would break a committed case."""
    f = make_financing_terms(amort_years=0)
    assert f.amort_years == 0
