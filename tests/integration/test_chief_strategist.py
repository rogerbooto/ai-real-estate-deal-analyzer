# tests/test_chief_strategist.py
from src.agents.chief_strategist import synthesize_thesis
from src.agents.financial_forecaster import forecast_financials
from src.schemas.models import (
    FinancialInputs,
    FinancingTerms,
    IncomeModel,
    MarketAssumptions,
    OperatingExpenses,
    RefinancePlan,
    UnitIncome,
)


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
            units=[UnitIncome(rent_month=1300.0, other_income_month=100.0) for _ in range(6)],
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
            units=[UnitIncome(rent_month=1200.0, other_income_month=100.0) for _ in range(4)],
            occupancy=0.95,
            bad_debt_factor=0.97,
            rent_growth=0.04,
        ),
        refi=RefinancePlan(do_refi=False),
        market=MarketAssumptions(
            cap_rate_purchase=None,
            cap_rate_floor=None,  # let spread/coverage drive CONDITIONAL
            cap_rate_spread_target=0.015,
        ),
        capex_reserve_upfront=0.0,
    )


def _inputs_poor() -> FinancialInputs:
    # Weak income → likely DECLINE
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
            units=[UnitIncome(rent_month=900.0, other_income_month=50.0) for _ in range(3)],
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
        (_inputs_poor, "DECLINE"),
    ]:
        forecast = forecast_financials(builder())
        thesis = synthesize_thesis(forecast)

        assert thesis.verdict in {"BUY", "CONDITIONAL", "DECLINE"}
        assert thesis.verdict == expected
        assert isinstance(thesis.rationale, list) and len(thesis.rationale) > 0
        if thesis.verdict != "BUY":
            assert len(thesis.levers) > 0  # should suggest actions


# ---------------------------------------------------------------------------
# Cap-rate floor guardrail (Mission 2 / F1)
#
# The engine emits "cap rate below floor" when the purchase cap breaches
# `MarketAssumptions.cap_rate_floor`; the strategist consumes that warning as its
# sixth DECLINE input. These tests pin the end-to-end signal: engine warning ->
# `no_cap_floor_breach` -> rationale line -> lever. They turn RED if the engine
# stops emitting the warning or the strategist stops matching it.
# ---------------------------------------------------------------------------

RESPECTS_FLOOR = "Purchase cap rate respects the floor policy."
BREACHES_FLOOR = "Purchase cap rate breaches the configured floor."


def _inputs_with_floor(cap_rate_purchase: float | None, cap_rate_floor: float | None) -> FinancialInputs:
    """`_inputs_good()` (a clean BUY) with only the cap policy varied."""
    good = _inputs_good()
    return good.model_copy(
        update={
            "market": MarketAssumptions(
                cap_rate_purchase=cap_rate_purchase,
                cap_rate_floor=cap_rate_floor,
                cap_rate_spread_target=0.015,
            )
        }
    )


def test_cap_floor_breach_drives_breach_rationale_and_lever():
    """A purchase cap below an explicit floor must reach the thesis as a breach."""
    forecast = forecast_financials(_inputs_with_floor(cap_rate_purchase=0.04, cap_rate_floor=0.05))
    thesis = synthesize_thesis(forecast)

    assert "cap rate below floor" in forecast.warnings
    assert BREACHES_FLOOR in thesis.rationale
    assert RESPECTS_FLOOR not in thesis.rationale
    # The breach is a live verdict input, so this deal can no longer be a BUY.
    assert thesis.verdict != "BUY"
    assert "Address: cap rate below floor" in thesis.levers


def test_cap_floor_respected_keeps_the_positive_rationale():
    """At or above the floor, the reassuring line is a true claim, not a default."""
    forecast = forecast_financials(_inputs_with_floor(cap_rate_purchase=0.05, cap_rate_floor=0.05))
    thesis = synthesize_thesis(forecast)

    assert not any("below floor" in w.lower() for w in forecast.warnings)
    assert RESPECTS_FLOOR in thesis.rationale
    assert BREACHES_FLOOR not in thesis.rationale


def test_no_floor_policy_never_breaches():
    """`cap_rate_floor=None` means no policy configured — never a breach."""
    forecast = forecast_financials(_inputs_with_floor(cap_rate_purchase=0.01, cap_rate_floor=None))
    thesis = synthesize_thesis(forecast)

    assert not any("below floor" in w.lower() for w in forecast.warnings)
    assert RESPECTS_FLOOR in thesis.rationale


def test_cap_floor_breach_plus_weak_dscr_forces_decline():
    """
    The strategist's two-input DECLINE shortcut (`cap-floor breach AND DSCR fail`) was
    unreachable while the engine never emitted the warning. This pins it as live.
    """
    weak = _inputs_poor()  # DSCR well below 1.20, cap floor 0.055 breached
    forecast = forecast_financials(weak)
    thesis = synthesize_thesis(forecast)

    assert "cap rate below floor" in forecast.warnings
    assert forecast.years[0].dscr < 1.20
    assert thesis.verdict == "DECLINE"
    assert BREACHES_FLOOR in thesis.rationale
