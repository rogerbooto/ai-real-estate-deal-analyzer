# tests/unit/test_financial_model.py

from src.core.finance import run_financial_model
from src.schemas.models import FinancialForecast
from tests.utils import (
    make_financial_inputs,
    make_financing_terms,
    make_income_model,
    make_market_assumptions,
    make_opex,
    make_refi_plan,
)


def test_run_financials_baseline_no_refi():
    fin = make_financial_inputs(do_refi=False, num_units=4)
    out = run_financial_model(fin)
    assert isinstance(out, FinancialForecast)
    # Stable fields in the model
    assert hasattr(out, "purchase") and out.purchase is not None
    assert out.refi is None  # no-refi path
    assert hasattr(out, "irr_10yr")
    assert hasattr(out, "equity_multiple_10yr")
    assert isinstance(out.warnings, list)


def test_run_financials_with_refi():
    fin = make_financial_inputs(do_refi=True, num_units=4)
    out = run_financial_model(fin)
    assert out.refi is not None
    assert getattr(out.refi, "year", None) == 5  # default from factory


def test_variations_override_specific_fields():
    fin = make_financial_inputs(do_refi=False)
    fin = fin.model_copy(
        update={
            "financing": make_financing_terms(interest_rate=0.05, amort_years=25),
            "opex": make_opex(property_management=4800.0, reserves=1500.0),
            "income": make_income_model(num_units=3, rent_month=1400.0),
            "refi": make_refi_plan(do_refi=True, year_to_refi=7, refi_ltv=0.70),
            "market": make_market_assumptions(cap_rate_floor=0.045),
        }
    )
    out = run_financial_model(fin)
    assert isinstance(out, FinancialForecast)
    assert out.refi is not None and getattr(out.refi, "year", None) == 7
