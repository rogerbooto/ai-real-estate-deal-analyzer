# tests/unit/test_input_models_validate_assignment.py
"""
Defect 2 (Mission 4, PV.2): input-schema field constraints were only enforced at construction time.

Before the fix, none of ``FinancialInputs`` and its submodels (``FinancingTerms``,
``OperatingExpenses``, ``IncomeModel``, ``UnitIncome``, ``RefinancePlan``, ``MarketAssumptions``)
set ``model_config``, so they were neither frozen nor ``validate_assignment``-enabled -- in-place
attribute assignment silently bypassed every declared ``ge``/``le`` bound. Confirmed:
``FinancingTerms(...).down_payment_rate = 1.5`` (declared ``le=1``) used to succeed silently.

THE FIX: each of those seven models now sets ``model_config = ConfigDict(validate_assignment=True)``
(and only that -- the models remain unfrozen; legitimate in-place mutation patterns elsewhere in
the codebase, e.g. ``src/market/recourse.py``'s surgical ``model_copy``, are untouched because
``model_copy(update=...)`` does not validate even with this flag on).

This file pins that in-place assignment of an out-of-bound value on each of the seven affected
models now raises ``pydantic.ValidationError``, while legitimate in-bound assignment still works.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.schemas.models import FinancialInputs
from tests.utils import (
    make_financial_inputs,
    make_financing_terms,
    make_income_model,
    make_market_assumptions,
    make_opex,
    make_refi_plan,
)


def test_financing_terms_rejects_out_of_bound_assignment() -> None:
    f = make_financing_terms()
    with pytest.raises(ValidationError):
        f.down_payment_rate = 1.5  # declared le=1


def test_financing_terms_accepts_in_bound_assignment() -> None:
    f = make_financing_terms()
    f.down_payment_rate = 0.30
    assert f.down_payment_rate == 0.30


def test_income_model_rejects_out_of_bound_assignment() -> None:
    im = make_income_model()
    with pytest.raises(ValidationError):
        im.occupancy = 1.5  # declared le=1


def test_unit_income_rejects_out_of_bound_assignment() -> None:
    im = make_income_model()
    unit = im.units[0]
    # rent_month itself has no declared bound, but other_income_month must still validate type.
    with pytest.raises(ValidationError):
        unit.rent_month = "not-a-number"  # type: ignore[assignment]


def test_refinance_plan_rejects_out_of_bound_assignment() -> None:
    r = make_refi_plan()
    with pytest.raises(ValidationError):
        r.refi_ltv = 1.5  # declared le=1


def test_market_assumptions_accepts_in_bound_assignment() -> None:
    m = make_market_assumptions()
    m.cap_rate_spread_target = 0.02
    assert m.cap_rate_spread_target == 0.02


def test_opex_rejects_wrong_type_assignment() -> None:
    o = make_opex()
    with pytest.raises(ValidationError):
        o.insurance = "free"  # type: ignore[assignment]


def test_financial_inputs_rejects_wrong_type_assignment() -> None:
    inputs: FinancialInputs = make_financial_inputs()
    with pytest.raises(ValidationError):
        inputs.income_is_estimated = "not-a-bool"  # type: ignore[assignment]


def test_model_copy_update_still_bypasses_validation_by_design() -> None:
    """
    Pins the documented, deliberate asymmetry: ``model_copy(update=...)`` -- the surgical-copy
    pattern used throughout ``src/market/recourse.py`` and ``src/market/adapter.py`` for the
    recourse hot path -- does NOT re-run validators even with ``validate_assignment=True`` set.
    This is exactly why Defect 1 (``InputsLoader.with_overrides``) needed its own explicit
    re-validation step rather than relying on this flag.
    """
    f = make_financing_terms()
    copied = f.model_copy(update={"down_payment_rate": 1.5})
    assert copied.down_payment_rate == 1.5  # not rejected -- model_copy never validates
