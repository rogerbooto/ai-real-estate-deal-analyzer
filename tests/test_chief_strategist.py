# tests/test_chief_strategist.py
from src.schemas.models import (
    FinancingTerms,
    OperatingExpenses,
    IncomeModel,
    RefinancePlan,
    MarketAssumptions,
    FinancialInputs,
)
from src.agents.financial_forecaster import forecast_financials
from src.agents.chief_strategist import synthesize_thesis


def _inputs_good() -> FinancialInputs:
    # Healthier income → likely BUY under default guardrails
    return FinancialInputs(
        financing=FinancingTerms(
            purchase_price=450_000.0,
            closing_costs=8_000.0,
            down_payment_rate=0.30,
            interest_rate=0.05,
            amort_years=30,
            io_years=0,
        ),
        opex=OperatingExpenses(
            insurance=2000.0,
            taxes=5000.0,
            utilities=3000.0,
            water_sewer=1500.0,
            property_management=3600.0,
            repairs_maintenance=1800.0,
            trash=1000.0,
            landscaping=600.0,
            snow_removal=500.0,
            hoa_fees=0.0,
            reserves=1200.0,
            other=400.0,
            expense_growth=0.02,
        ),
        income=IncomeModel(
            units=6,
            rent_month=1300.0,
            other_income_month=100.0,
            occupancy=0.96,
            bad_debt_factor=0.98,
            rent_growth=0.03,
        ),
        refi=RefinancePlan(do_refi=False),
        market=MarketAssumptions(
            cap_rate_purchase=None,
            cap_rate_floor=0.05,
            cap_rate_spread_target=0.015,
        ),
        capex_reserve_upfront=0.0,
    )


def _inputs_mixed() -> FinancialInputs:
    # Thin spread or marginal DSCR → likely CONDITIONAL
    return FinancialInputs(
        financing=FinancingTerms(
            purchase_price=500_000.0,
            closing_costs=10_000.0,
            down_payment_rate=0.25,
            interest_rate=0.055,
            amort_years=30,
            io_years=0,
        ),
        opex=OperatingExpenses(
            insurance=2400.0,
            taxes=6000.0,
            utilities=3600.0,
            water_sewer=1800.0,
            property_management=4800.0,
            repairs_maintenance=2400.0,
            trash=1200.0,
            landscaping=800.0,
            snow_removal=600.0,
            hoa_fees=0.0,
            reserves=1500.0,
            other=500.0,
            expense_growth=0.02,
        ),
        income=IncomeModel(
            units=4,
            rent_month=1200.0,
            other_income_month=100.0,
            occupancy=0.95,
            bad_debt_factor=0.97,
            rent_growth=0.04,
        ),
        refi=RefinancePlan(do_refi=False),
        market=MarketAssumptions(
            cap_rate_purchase=None,
            cap_rate_floor=None,
            cap_rate_spread_target=0.015,
        ),
        capex_reserve_upfront=0.0,
    )


def _inputs_poor() -> FinancialInputs:
    # Weak income → likely PASS
    return FinancialInputs(
        financing=FinancingTerms(
            purchase_price=520_000.0,
            closing_costs=10_000.0,
            down_payment_rate=0.20,
            interest_rate=0.06,
            amort_years=30,
            io_years=0,
        ),
        opex=OperatingExpenses(
            insurance=3000.0,
            taxes=7500.0,
            utilities=4200.0,
            water_sewer=2100.0,
            property_management=5000.0,
            repairs_maintenance=2500.0,
            trash=1200.0,
            landscaping=1000.0,
            snow_removal=800.0,
            hoa_fees=0.0,
            reserves=1800.0,
            other=600.0,
            expense_growth=0.03,
        ),
        income=IncomeModel(
            units=3,
            rent_month=900.0,
            other_income_month=50.0,
            occupancy=0.90,
            bad_debt_factor=0.92,
            rent_growth=0.02,
        ),
        refi=RefinancePlan(do_refi=False),
        market=MarketAssumptions(
            cap_rate_purchase=None,
            cap_rate_floor=0.055,
            cap_rate_spread_target=0.015,
        ),
        capex_reserve_upfront=0.0,
    )


def test_thesis_buy_mixed_pass_buckets():
    for builder, expected in [
        (_inputs_good, "BUY"),
        (_inputs_mixed, "CONDITIONAL"),
        (_inputs_poor, "PASS"),
    ]:
        forecast = forecast_financials(builder())
        thesis = synthesize_thesis(forecast)

        assert thesis.verdict in {"BUY", "CONDITIONAL", "PASS"}
        assert thesis.verdict == expected
        assert isinstance(thesis.rationale, list) and len(thesis.rationale) > 0
        if thesis.verdict != "BUY":
            assert len(thesis.levers) > 0  # should suggest actions
