from src.agents.financial_forecaster import forecast_financials
from src.schemas.models import (
    FinancialInputs,
    FinancingTerms,
    IncomeModel,
    ListingInsights,
    MarketAssumptions,
    OperatingExpenses,
    RefinancePlan,
    UnitIncome,
)


def _valid_inputs() -> FinancialInputs:
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
            units=[UnitIncome(rent_month=1200.0, other_income_month=100.0) for _ in range(4)],
            occupancy=0.95,
            bad_debt_factor=0.97,
            rent_growth=0.03,
        ),
        refi=RefinancePlan(
            do_refi=True,
            year_to_refi=5,
            refi_ltv=0.75,
        ),
        market=MarketAssumptions(
            cap_rate_purchase=None,
            cap_rate_floor=0.05,
            cap_rate_spread_target=0.015,
        ),
        capex_reserve_upfront=0.0,
    )


def test_forecaster_clamps_occupancy_and_bad_debt_and_runs():
    # Start from a valid input bundle
    base = _valid_inputs()

    # Create an INVALID IncomeModel without validation (pydantic v2 escape hatch)
    # Keep the same unit list but break occupancy/bad_debt
    bad_income = IncomeModel.model_construct(
        units=base.income.units,
        occupancy=1.2,  # > 1 on purpose
        bad_debt_factor=-0.1,  # < 0 on purpose
        rent_growth=base.income.rent_growth,
    )

    # Inject the invalid income into FinancialInputs, again bypassing validation
    bad_inputs = FinancialInputs.model_construct(
        financing=base.financing,
        opex=base.opex,
        income=bad_income,
        refi=base.refi,
        market=base.market,
        capex_reserve_upfront=base.capex_reserve_upfront,
    )

    # Run forecaster; it should clamp to [0,1] and produce a forecast deterministically
    insights = ListingInsights(address="789 Pine Ave")
    forecast = forecast_financials(bad_inputs, insights=insights, horizon_years=10)

    assert len(forecast.years) == 10
    assert forecast.purchase.acquisition_cash > 0
    # Cap rate may be negative if NOI < 0; just ensure finiteness (not NaN)
    assert forecast.purchase.cap_rate == forecast.purchase.cap_rate
    assert forecast.irr_10yr == forecast.irr_10yr
    assert isinstance(forecast.warnings, list)
    # With collections crushed by clamping, negative CF is plausible → expect warning
    assert any("Negative cash flow" in w for w in forecast.warnings)
