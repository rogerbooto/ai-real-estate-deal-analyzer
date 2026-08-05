# tests/test_chief_strategist.py
import math

import pytest

from src.agents.chief_strategist import MIN_COC_Y1, MIN_SPREAD, synthesize_thesis
from src.agents.financial_forecaster import forecast_financials
from src.schemas.models import (
    FinancialForecast,
    FinancialInputs,
    FinancingTerms,
    IncomeModel,
    InvestmentThesis,
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
    # The breach is a live verdict input, so this deal can no longer be a BUY.
    assert thesis.verdict != "BUY"
    assert "Address: cap rate below floor" in thesis.levers


def test_cap_floor_respected_is_not_a_breach():
    """A cap exactly at the floor clears it: no warning, no breach claim."""
    forecast = forecast_financials(_inputs_with_floor(cap_rate_purchase=0.05, cap_rate_floor=0.05))
    thesis = synthesize_thesis(forecast)

    assert not any("below floor" in w.lower() for w in forecast.warnings)
    assert BREACHES_FLOOR not in thesis.rationale
    # The numbered positive claim returns in Wave 3 with OPD-4, once the strategist can see
    # the floor value and can name it ("... is 6.35% (>= the 5.00% floor you set).").


def test_no_floor_policy_makes_no_floor_claim():
    """
    No floor configured means no claim to make, in either direction.

    Asserts *silence about the floor*, not the absence of one particular string: the
    strategist infers the breach from the absence of the engine warning, which cannot
    distinguish "no policy" from "policy cleared". Claiming the floor is respected when
    none was ever set is the exact false-report shape Mission 2 exists to remove.
    """
    forecast = forecast_financials(_inputs_with_floor(cap_rate_purchase=0.01, cap_rate_floor=None))
    thesis = synthesize_thesis(forecast)

    assert not any("below floor" in w.lower() for w in forecast.warnings)
    assert not any("floor" in line.lower() for line in thesis.rationale)


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


# ---------------------------------------------------------------------------
# Cap-rate SPREAD guardrail (Mission 2 / Wave 3 task 3.1a — guardian M4)
#
# `run_financial_model` warns "cap-rate spread below target" against the user's
# `MarketAssumptions.cap_rate_spread_target`. The strategist used to judge the same
# spread against a hardcoded 0.015, so the two could reach opposite conclusions about
# one number: the report's Warnings section said the spread missed, its own Investment
# Thesis said it met target, and because that deal still read BUY the levers list was
# empty — so the warning appeared with nothing explaining it.
#
# These tests pin the fix. Reverting `synthesize_thesis` to the hardcoded constant, or
# dropping `market=inputs.market` at either orchestrator, turns them RED.
# ---------------------------------------------------------------------------

SPREAD_BELOW_TARGET = "cap-rate spread below target"


def _spread_lines(thesis) -> list[str]:  # type: ignore[no-untyped-def]
    """The thesis' own claim about the spread — exactly one line, either way."""
    return [line for line in thesis.rationale if "Cap-rate spread" in line]


def _with_spread_target(inputs: FinancialInputs, target: float) -> FinancialInputs:
    """`inputs` with only `cap_rate_spread_target` varied — nothing else moves."""
    return inputs.model_copy(update={"market": inputs.market.model_copy(update={"cap_rate_spread_target": target})})


def test_stricter_configured_target_is_honoured_over_the_fallback():
    """
    A deal that clears 150 bps but misses the target the user actually set must be judged
    against the user's number.

    `_inputs_good()` earns a 11.50% spread and is a clean BUY at the 1.50% fallback. An
    investor who requires 15.00% has not been served by that answer. Before the fix this
    deal returned BUY with an empty levers list while the engine warned that the spread
    missed target — the M4 contradiction, verbatim.
    """
    inputs = _with_spread_target(_inputs_good(), 0.15)
    forecast = forecast_financials(inputs)
    thesis = synthesize_thesis(forecast, market=inputs.market)

    assert forecast.purchase.spread_vs_rate > MIN_SPREAD  # would clear the old hardcoded bar
    assert SPREAD_BELOW_TARGET in forecast.warnings  # engine judged it against 15.00%
    assert _spread_lines(thesis) == ["Cap-rate spread is thin at 11.50% (< 15.00%)."]
    assert thesis.verdict != "BUY"
    # A BUY has no levers, so the engine's warning had nowhere to be explained. Now it is.
    assert "Address: cap-rate spread below target" in thesis.levers
    assert "Negotiate lower price to improve cap-rate spread to ≥ 1500 bps." in thesis.levers


def test_looser_configured_target_is_honoured_over_the_fallback():
    """
    The mirror case: a target *below* 150 bps must also be respected.

    `_inputs_mixed()` earns 0.88%. At a configured 0.50% the engine raises no warning at
    all, yet the pre-fix thesis still called the spread "thin (< 1.50%)" and spent a
    guardrail failure on it — holding the deal at CONDITIONAL on a bar the user never set.
    """
    inputs = _with_spread_target(_inputs_mixed(), 0.005)
    forecast = forecast_financials(inputs)
    thesis = synthesize_thesis(forecast, market=inputs.market)

    assert forecast.purchase.spread_vs_rate < MIN_SPREAD  # would have failed the old hardcoded bar
    assert SPREAD_BELOW_TARGET not in forecast.warnings
    assert _spread_lines(thesis) == ["Cap-rate spread meets target at 0.88% (≥ 0.50%)."]
    assert thesis.verdict == "BUY"


def test_no_market_supplied_falls_back_to_min_spread():
    """
    Callers that pass no market block keep the documented fallback, unchanged.

    This is what keeps the kwarg additive: `MIN_SPREAD` is still the bar when there is no
    configured target to honour, so no existing caller's verdict moves.
    """
    inputs = _with_spread_target(_inputs_mixed(), 0.005)
    forecast = forecast_financials(inputs)

    thesis = synthesize_thesis(forecast)  # no market=

    assert MIN_SPREAD == 0.015
    assert _spread_lines(thesis) == ["Cap-rate spread is thin at 0.88% (< 1.50%)."]


@pytest.mark.parametrize("target", [0.0, 0.005, 0.0088, 0.015, 0.05, 0.115, 0.15, 0.30])
def test_warnings_can_never_contradict_the_thesis_about_the_spread(target: float):
    """
    The invariant behind the fix: one number, one verdict about it.

    For every configured target and both fixture deals, the engine's warning and the
    thesis' own spread line must agree. This is the property that makes "Warnings says
    missed / Thesis says met" unreachable, rather than merely absent from a fixture.
    """
    for builder in (_inputs_good, _inputs_mixed, _inputs_poor):
        inputs = _with_spread_target(builder(), target)
        forecast = forecast_financials(inputs)
        thesis = synthesize_thesis(forecast, market=inputs.market)

        engine_says_missed = SPREAD_BELOW_TARGET in forecast.warnings
        lines = _spread_lines(thesis)
        assert len(lines) == 1, "the thesis states its spread verdict exactly once"
        thesis_says_missed = "is thin" in lines[0]

        assert engine_says_missed == thesis_says_missed, f"target={target!r} deal={builder.__name__}: {forecast.warnings} vs {lines[0]}"


# ---------------------------------------------------------------------------
# Year-1 CASH-ON-CASH guardrail (Mission 2 / Wave 3 task 3.1a — OPD-1 port)
#
# `PurchaseMetrics.coc` (`CoC = Year-1 cash flow / acquisition cash`) was computed by
# the engine on every run and consulted by no verdict. The deleted
# `core/strategy/strategist.py` carried a `coc < 0.03` floor that never reached
# production; `MIN_COC_Y1` is that threshold ported into the live strategist.
#
# What it adds that the siblings cannot see: DSCR asks whether the lender is covered
# and the Year-1 cash-flow rule asks whether the deal is above water in dollars. A
# deal can clear both — DSCR 1.31, +$5,527 in the first year — while the buyer's own
# cash earns 2.94%. Nothing in the thesis used to say so.
#
# Reverting the `coc_ok` guardrail, its rationale lines, its `fails` entry or its
# levers turns these RED.
# ---------------------------------------------------------------------------


def _inputs_thin_equity_yield(rent_month: float) -> FinancialInputs:
    """
    `_inputs_good()` re-let at `rent_month` on a 40% down payment.

    One knob. At 40% down the equity base is large enough that a modest rent moves the
    Year-1 equity yield across 3% while DSCR stays comfortable and Year-1 cash flow stays
    positive — which is the only shape in which this guardrail says something new.
    """
    good = _inputs_good()
    return good.model_copy(
        update={
            "financing": good.financing.model_copy(update={"down_payment_rate": 0.40}),
            "income": good.income.model_copy(
                update={"units": [u.model_copy(update={"rent_month": rent_month}) for u in good.income.units]}
            ),
        }
    )


def _coc_lines(thesis: InvestmentThesis) -> list[str]:
    """The thesis' own claim about cash-on-cash — exactly one line, either way."""
    return [line for line in thesis.rationale if "Cash-on-cash" in line]


def test_weak_cash_on_cash_is_named_with_both_numbers():
    """
    Below the floor, the thesis says so and names the deal's CoC *and* the bar.

    House style: every guardrail line quotes its own number and the threshold it was
    judged against, so a reader can check the call without re-running the model.
    """
    inputs = _inputs_thin_equity_yield(545.0)
    forecast = forecast_financials(inputs)
    thesis = synthesize_thesis(forecast, market=inputs.market)

    assert forecast.purchase.coc < MIN_COC_Y1
    assert _coc_lines(thesis) == ["Cash-on-cash (Y1) is weak at 2.94% (< 3.00%)."]

    # The blind spot this closes: the two nearest guardrails both pass on this deal.
    assert "DSCR (Y1) is healthy at 1.31 (≥ 1.20)." in thesis.rationale
    assert "Year-1 cash flow is positive at $5,527." in thesis.rationale


def test_healthy_cash_on_cash_is_named_with_both_numbers():
    """The mirror: at or above the floor the thesis makes the positive claim, also numbered."""
    inputs = _inputs_thin_equity_yield(550.0)
    forecast = forecast_financials(inputs)
    thesis = synthesize_thesis(forecast, market=inputs.market)

    assert forecast.purchase.coc >= MIN_COC_Y1
    assert _coc_lines(thesis) == ["Cash-on-cash (Y1) is healthy at 3.12% (≥ 3.00%)."]
    assert not any("cash-on-cash" in lever.lower() for lever in thesis.levers)


def test_weak_cash_on_cash_is_a_live_verdict_input():
    """
    The floor is a *verdict* input, not decoration — it is the third failure that declines.

    Same property, same financing, $5/unit/month apart. At $545 the equity yield is 2.94%
    and joins the thin spread and the short IRR to make three failures (DECLINE); at $550
    it is 3.12% and only two guardrails fail (CONDITIONAL). Before the port both deals
    read CONDITIONAL and neither mentioned the yield on the cash.
    """
    weak_inputs = _inputs_thin_equity_yield(545.0)
    weak = synthesize_thesis(forecast_financials(weak_inputs), market=weak_inputs.market)

    ok_inputs = _inputs_thin_equity_yield(550.0)
    ok = synthesize_thesis(forecast_financials(ok_inputs), market=ok_inputs.market)

    assert weak.verdict == "DECLINE"
    assert ok.verdict == "CONDITIONAL"


def test_weak_cash_on_cash_offers_levers_on_both_sides_of_the_ratio():
    """A named weakness with no suggested fix is just a complaint — CoC gets levers like its siblings."""
    inputs = _inputs_thin_equity_yield(545.0)
    thesis = synthesize_thesis(forecast_financials(inputs), market=inputs.market)

    assert "Lift Year-1 net cash flow (rents, ancillary income, OPEX bids) to reach cash-on-cash ≥ 3%." in thesis.levers
    assert "Reduce the cash outlay (seller credits, lower closing costs, smaller upfront reserves) to raise cash-on-cash." in thesis.levers


@pytest.mark.parametrize(
    ("coc", "expected_line"),
    [
        (MIN_COC_Y1, "Cash-on-cash (Y1) is healthy at 3.00% (≥ 3.00%)."),
        (math.nextafter(MIN_COC_Y1, 0.0), "Cash-on-cash (Y1) is weak at 3.00% (< 3.00%)."),
    ],
    ids=["exactly-at-the-floor-clears", "one-ulp-below-the-floor-fails"],
)
def test_cash_on_cash_floor_is_inclusive_at_the_bar(coc: float, expected_line: str):
    """
    Exactly 3.00% PASSES.

    Justified by consistency, not by taste: every sibling guardrail in this module is
    inclusive at its bar (`dscr >= MIN_DSCR_Y1`, `spread >= target`, `irr >= MIN_IRR_10YR`,
    `cash_flow >= 0`), the engine's cap-rate floor clears a cap sitting exactly on it, and
    the ported `strategist.py` rule was `coc < 0.03` — which also passed at 0.03. An
    exclusive bar here would make 3% mean "3%" in five places and "above 3%" in one.

    The boundary is set on `PurchaseMetrics.coc` directly rather than steered there through
    the engine: landing a rent-and-financing combination exactly on the float `0.03` is luck,
    and this test is about the comparison operator, not about the engine's arithmetic. The
    second case is one unit-in-the-last-place below the constant — it still *prints* 3.00%,
    so the pair also pins that the rendered line follows the comparison and not the rounding.
    """
    inputs = _inputs_thin_equity_yield(545.0)
    forecast = forecast_financials(inputs)
    on_the_bar: FinancialForecast = forecast.model_copy(update={"purchase": forecast.purchase.model_copy(update={"coc": coc})})

    thesis = synthesize_thesis(on_the_bar, market=inputs.market)

    assert _coc_lines(thesis) == [expected_line]
