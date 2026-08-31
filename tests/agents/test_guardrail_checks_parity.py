# tests/agents/test_guardrail_checks_parity.py
"""Golden/parity test for the Mission 4 Gate D `guardrail_checks` extraction ("Option B").

`synthesize_thesis` used to compute its seven guardrail booleans as local variables
(pre-Mission-4 `chief_strategist.py:172-179`). Gate D ruled (over Discovery's recommended
"Option A", duplicate-and-parity-test) that they must instead be extracted into a small, pure,
additive helper -- `guardrail_checks` -- that `synthesize_thesis` itself calls, so a second call
site (`src/market/recourse.py`) can never independently re-derive, and silently diverge from, the
same seven tests. The guardian's condition for accepting that refactor was a golden/parity test
asserting `synthesize_thesis`'s output is identical before and after.

This is that test. A REFERENCE reimplementation of the exact pre-refactor seven-boolean logic is
reproduced verbatim below -- copied, never imported from `src.agents.chief_strategist` -- so this
test cannot pass merely because both sides call the same (possibly-buggy) helper. If a future
change to `guardrail_checks` (or to the verdict fail-count arithmetic) ever silently diverges from
this reference, this test goes RED immediately.
"""

from __future__ import annotations

import pytest

from src.agents.chief_strategist import (
    MIN_COC_Y1,
    MIN_DSCR_Y1,
    MIN_IRR_10YR,
    REQUIRE_POSITIVE_CF_ALL,
    REQUIRE_POSITIVE_CF_Y1,
    _levers_for,
    spread_target_for,
    synthesize_thesis,
)
from src.agents.financial_forecaster import forecast_financials
from src.schemas.models import FinancialForecast, FinancialInputs, InvestmentThesis, MarketAssumptions
from tests.utils import make_financial_inputs, make_market_assumptions


def _reference_thesis(forecast: FinancialForecast, market: MarketAssumptions | None) -> InvestmentThesis:
    """Verbatim reimplementation of the PRE-Mission-4 `synthesize_thesis` guardrail logic --
    the exact seven local-variable computations this refactor extracted into `guardrail_checks`,
    and the exact verdict/rationale assembly around them. Deliberately duplicated (not imported)."""
    y1 = forecast.years[0]
    purchase = forecast.purchase
    spread_target = spread_target_for(market)

    rationale: list[str] = []

    dscr_ok = y1.dscr >= MIN_DSCR_Y1
    spread_ok = purchase.spread_vs_rate >= spread_target
    irr_ok = forecast.irr_10yr >= MIN_IRR_10YR
    coc_ok = purchase.coc >= MIN_COC_Y1
    cf_y1_ok = (y1.cash_flow >= 0.0) if REQUIRE_POSITIVE_CF_Y1 else True
    cf_all_ok = all(y.cash_flow >= 0.0 for y in forecast.years) if REQUIRE_POSITIVE_CF_ALL else True
    no_cap_floor_breach = not any("cap rate" in w.lower() and "below floor" in w.lower() for w in forecast.warnings)

    def _flag(condition: bool, msg: str) -> None:
        if condition:
            rationale.append(msg)

    _flag(dscr_ok, f"DSCR (Y1) is healthy at {y1.dscr:.2f} (≥ {MIN_DSCR_Y1:.2f}).")
    _flag(not dscr_ok, f"DSCR (Y1) is weak at {y1.dscr:.2f} (< {MIN_DSCR_Y1:.2f}).")

    _flag(spread_ok, f"Cap-rate spread meets target at {purchase.spread_vs_rate:.2%} (≥ {spread_target:.2%}).")
    _flag(not spread_ok, f"Cap-rate spread is thin at {purchase.spread_vs_rate:.2%} (< {spread_target:.2%}).")

    _flag(irr_ok, f"Projected IRR (10y) is {forecast.irr_10yr:.2%} (≥ {MIN_IRR_10YR:.2%}).")
    _flag(not irr_ok, f"Projected IRR (10y) is {forecast.irr_10yr:.2%} (< {MIN_IRR_10YR:.2%}).")

    _flag(coc_ok, f"Cash-on-cash (Y1) is healthy at {purchase.coc:.2%} (≥ {MIN_COC_Y1:.2%}).")
    _flag(not coc_ok, f"Cash-on-cash (Y1) is weak at {purchase.coc:.2%} (< {MIN_COC_Y1:.2%}).")

    if REQUIRE_POSITIVE_CF_Y1:
        _flag(cf_y1_ok, f"Year-1 cash flow is positive at ${y1.cash_flow:,.0f}.")
        _flag(not cf_y1_ok, f"Year-1 cash flow is negative at ${y1.cash_flow:,.0f}.")

    if REQUIRE_POSITIVE_CF_ALL:
        _flag(cf_all_ok, "Cash flow is non-negative across the hold period.")
        _flag(not cf_all_ok, "Cash flow turns negative in some years.")

    cap_floor = market.cap_rate_floor if market is not None else None
    if cap_floor is not None:
        cap = purchase.cap_rate
        _flag(no_cap_floor_breach, f"Purchase cap rate is {cap:.2%} (≥ the {cap_floor:.2%} floor you set).")
        _flag(not no_cap_floor_breach, f"Purchase cap rate is {cap:.2%} (< the {cap_floor:.2%} floor you set).")
    else:
        _flag(not no_cap_floor_breach, "Purchase cap rate breaches the configured floor.")

    fails = [not dscr_ok, not spread_ok, not irr_ok, not coc_ok, not cf_y1_ok, not cf_all_ok, not no_cap_floor_breach]
    num_fails = sum(1 for f in fails if f)
    pass_condition = num_fails >= 3 or ((not no_cap_floor_breach) and (not dscr_ok))

    if not any(fails):
        verdict = "BUY"
        levers: list[str] = []
    elif pass_condition:
        verdict = "DECLINE"
        levers = _levers_for(forecast, spread_target)
    else:
        verdict = "CONDITIONAL"
        levers = _levers_for(forecast, spread_target)

    return InvestmentThesis(verdict=verdict, rationale=rationale, levers=levers)


def _battery() -> list[tuple[FinancialInputs, MarketAssumptions | None]]:
    """Representative deals spanning every branch: BUY, CONDITIONAL, DECLINE (both the >=3-fails
    path and the cap-floor+DSCR combo path is exercised across these), market=None (fallback
    thresholds / cap SILENCE case), and an explicit cap-rate floor cleared vs. breached."""
    battery: list[tuple[FinancialInputs, MarketAssumptions | None]] = []

    # 1) A healthy deal -- expect BUY.
    good = make_financial_inputs(num_units=6)
    good = good.model_copy(
        update={
            "financing": good.financing.model_copy(update={"purchase_price": 380_000.0, "down_payment_rate": 0.30}),
            "income": good.income.model_copy(update={"occupancy": 0.97, "bad_debt_factor": 0.98}),
        }
    )
    battery.append((good, good.market))

    # 2) The demo-deal shape -- a genuine multi-fail DECLINE (dscr/spread/coc/cf_y1 fail).
    demo = make_financial_inputs(num_units=2)
    demo = demo.model_copy(
        update={
            "financing": demo.financing.model_copy(
                update={"purchase_price": 399_900.0, "down_payment_rate": 0.05, "interest_rate": 0.055, "amort_years": 25}
            ),
            "income": demo.income.model_copy(update={"occupancy": 0.95, "bad_debt_factor": 0.97}),
            "market": make_market_assumptions(cap_rate_floor=0.05, cap_rate_spread_target=0.015, cap_rate_drift=0.0),
        }
    )
    battery.append((demo, demo.market))

    # 3) Same shape, no market block at all -- fallback thresholds + cap SILENCE branch.
    battery.append((demo, None))

    # 4) A CONDITIONAL: some guardrails soft (spread, irr), most pass.
    conditional = make_financial_inputs(num_units=4)
    conditional = conditional.model_copy(
        update={
            "financing": conditional.financing.model_copy(
                update={"purchase_price": 540_000.0, "down_payment_rate": 0.20, "interest_rate": 0.058}
            ),
        }
    )
    battery.append((conditional, conditional.market))

    return battery


@pytest.mark.parametrize("case_index", range(4))
def test_synthesize_thesis_matches_pre_refactor_reference(case_index: int) -> None:
    inputs, market = _battery()[case_index]
    forecast = forecast_financials(inputs=inputs, insights=None, horizon_years=10)

    expected = _reference_thesis(forecast, market)
    actual = synthesize_thesis(forecast, market=market)

    assert actual.verdict == expected.verdict
    assert actual.rationale == expected.rationale
    assert actual.levers == expected.levers


def test_battery_covers_buy_conditional_and_decline() -> None:
    """Sanity check that the battery above is not accidentally degenerate (all one verdict)."""
    verdicts = set()
    for inputs, market in _battery():
        forecast = forecast_financials(inputs=inputs, insights=None, horizon_years=10)
        verdicts.add(synthesize_thesis(forecast, market=market).verdict)
    assert verdicts == {"BUY", "CONDITIONAL", "DECLINE"}
