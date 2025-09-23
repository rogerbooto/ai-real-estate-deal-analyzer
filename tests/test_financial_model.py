from src.schemas.models import (
    FinancialInputs,
    FinancingTerms,
    IncomeModel,
    MarketAssumptions,
    OperatingExpenses,
    RefinancePlan,
    UnitIncome,
)
from src.tools.financial_model import run


def _baseline_inputs(do_refi: bool = False) -> FinancialInputs:
    financing = FinancingTerms(
        purchase_price=500_000.0,
        closing_costs=10_000.0,
        down_payment_rate=0.25,
        interest_rate=0.055,
        amort_years=30,
        io_years=0,
    )
    opex = OperatingExpenses(
        insurance=2_400.0,
        taxes=6_000.0,
        utilities=3_600.0,
        water_sewer=1_800.0,
        property_management=4_800.0,
        repairs_maintenance=2_400.0,
        trash=1_200.0,
        landscaping=800.0,
        snow_removal=600.0,
        hoa_fees=0.0,
        reserves=1_500.0,
        other=500.0,
        expense_growth=0.02,
    )
    income = IncomeModel(
        units=[UnitIncome(rent_month=1200.0, other_income_month=100.0) for _ in range(4)],
        occupancy=0.95,
        bad_debt_factor=0.97,
        rent_growth=0.03,
    )
    refi = RefinancePlan(
        do_refi=do_refi,
        year_to_refi=5,
        refi_ltv=0.75,
        exit_cap_rate=None,
        market_cap_rate=None,
    )
    market = MarketAssumptions(
        cap_rate_purchase=None,
        cap_rate_floor=0.05,
        cap_rate_spread_target=0.015,
    )
    return FinancialInputs(
        financing=financing,
        opex=opex,
        income=income,
        refi=refi,
        market=market,
        capex_reserve_upfront=0.0,
    )


def _inputs_low_units_negative_cf() -> FinancialInputs:
    financing = FinancingTerms(
        purchase_price=450_000.0,
        closing_costs=8_000.0,
        down_payment_rate=0.20,
        interest_rate=0.065,
        amort_years=30,
        io_years=0,
    )
    opex = OperatingExpenses(
        insurance=3_000.0,
        taxes=7_500.0,
        utilities=4_200.0,
        water_sewer=2_100.0,
        property_management=5_000.0,
        repairs_maintenance=2_500.0,
        trash=1_200.0,
        landscaping=1_000.0,
        snow_removal=800.0,
        hoa_fees=0.0,
        reserves=1_800.0,
        other=600.0,
        expense_growth=0.03,
    )
    income = IncomeModel(
        units=[UnitIncome(rent_month=1200.0, other_income_month=0.0) for _ in range(2)],  # subscale on purpose
        occupancy=0.90,
        bad_debt_factor=0.92,
        rent_growth=0.02,
    )
    refi = RefinancePlan(
        do_refi=False,
        year_to_refi=5,
        refi_ltv=0.7,
        exit_cap_rate=None,
        market_cap_rate=None,
    )
    market = MarketAssumptions(
        cap_rate_purchase=None,
        cap_rate_floor=0.055,
        cap_rate_spread_target=0.015,
    )
    return FinancialInputs(
        financing=financing,
        opex=opex,
        income=income,
        refi=refi,
        market=market,
        capex_reserve_upfront=0.0,
    )


def test_run_no_refi_10yr_smoke():
    inputs = _baseline_inputs(do_refi=False)
    forecast = run(inputs, insights=None, horizon_years=10)

    # Structure checks
    assert len(forecast.years) == 10
    assert forecast.purchase.cap_rate >= 0.0
    assert forecast.purchase.annual_debt_service > 0.0
    assert forecast.purchase.acquisition_cash > 0.0

    # Monotonic sanity: with positive rent growth & expense growth, GSI should weakly increase
    gsi_values = [y.gsi for y in forecast.years]
    assert all(b >= a for a, b in zip(gsi_values, gsi_values[1:], strict=False))

    # DSCR should be finite and non-negative
    assert all(y.dscr >= 0.0 for y in forecast.years)

    # IRR/EM should compute (don’t assert specific number, just finiteness)
    assert forecast.irr_10yr == forecast.irr_10yr  # not NaN
    assert forecast.equity_multiple_10yr > 0.0

    # No refi event expected
    assert forecast.refi is None


def test_run_with_refi_creates_event_and_cash_out_applies():
    inputs = _baseline_inputs(do_refi=True)
    forecast = run(inputs, insights=None, horizon_years=10)

    # Structure
    assert len(forecast.years) == 10
    assert forecast.refi is not None
    assert forecast.refi.year == inputs.refi.year_to_refi
    assert forecast.refi.value >= 0.0
    assert forecast.refi.new_loan >= 0.0
    # If value supports it, cash_out should be >= 0 (zero acceptable if not enough value)
    assert forecast.refi.cash_out >= 0.0

    # Post-refi years should still have valid debt service and balances
    post = [y for y in forecast.years if y.year > inputs.refi.year_to_refi]
    assert all(y.debt_service >= 0.0 for y in post)
    assert post[-1].ending_balance >= 0.0

    # IRR/EM compute
    assert forecast.irr_10yr == forecast.irr_10yr
    assert forecast.equity_multiple_10yr > 0.0


def test_warnings_for_subscale_and_negative_cf():
    inputs = _inputs_low_units_negative_cf()
    forecast = run(inputs, insights=None, horizon_years=10)

    # Expect at least the subscale warning
    assert any("Subscale risk" in w for w in forecast.warnings)

    # Likely negative cash flow at some point given parameters
    assert any("Negative cash flow" in w for w in forecast.warnings)
