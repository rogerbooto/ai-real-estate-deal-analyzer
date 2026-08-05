# src/agents/chief_strategist.py
"""
Chief Strategist Agent (V1)

Purpose
-------
Convert a deterministic FinancialForecast into an InvestmentThesis:
  - Verdict: BUY | CONDITIONAL | DECLINE
  - Rationale: human-readable bullet points citing the key metrics
  - Levers: actionable suggestions to improve the deal

Design
------
- Fully deterministic rule-based scoring (no LLM calls).
- Conservative, easily-tunable guardrails exposed as constants.
- Reads Year 1 metrics and scan across years for risk (e.g., negative CF).

Tuning
------
Adjust the thresholds below to match your underwriting style.

Notes
-----
This is intentionally simple for V1. In V2+, you can:
  - Add scenario analysis (rent up/down, rate shocks, cap changes)
  - Make lever magnitudes quantitative (e.g., "raise rent +$85")
  - Let an LLM synthesize a narrative from structured rationale
"""

from __future__ import annotations

from src.schemas.models import FinancialForecast, InvestmentThesis, MarketAssumptions

# ----------------------------
# Underwriting guardrails (tunable)
# ----------------------------
MIN_DSCR_Y1 = 1.20  # Year 1 DSCR floor
#: Fallback cap-rate-spread target, used ONLY when the caller supplies no ``MarketAssumptions``.
#: When they do, the user's own ``market.cap_rate_spread_target`` wins — that is the same number
#: ``run_financial_model`` tests when it raises "cap-rate spread below target", so the thesis and
#: the report's Warnings section cannot disagree about whether the spread cleared the bar.
MIN_SPREAD = 0.015  # Cap rate - interest rate target (150 bps)
MIN_IRR_10YR = 0.12  # 10-year IRR target (12%)
#: Year-1 cash-on-cash floor (3%). Cash-on-cash is the standard first-year equity yield,
#: ``CoC = Year-1 cash flow / total cash invested`` — where the denominator is the acquisition
#: cash outlay (down payment + closing costs + upfront reserves). The number itself is computed
#: once, deterministically, by ``run_financial_model`` (``src/core/finance/engine.py``) and lands
#: on ``PurchaseMetrics.coc``; this module only reads it. DSCR asks whether the *lender* is
#: covered and Year-1 cash flow asks whether the deal is above water in dollars, but neither asks
#: what the *buyer's own cash* earns: a deal can clear both on a large down payment and still
#: return under 3% on the money it consumed.
MIN_COC_Y1 = 0.03
REQUIRE_POSITIVE_CF_ALL = False  # If True, require CF >= 0 for all years to be BUY
REQUIRE_POSITIVE_CF_Y1 = True  # Require CF >= 0 in Year 1 for BUY


def spread_target_for(market: MarketAssumptions | None) -> float:
    """
    Resolve the cap-rate-spread target this thesis is judged against.

    The engine warns on ``purchase.spread_vs_rate < market.cap_rate_spread_target``
    (``src/core/finance/engine.py``). The strategist must test the *same* number, or a report can
    print "cap-rate spread below target" under Warnings while its own Investment Thesis says the
    spread meets target — and on a deal that otherwise reads BUY the levers list is empty, so the
    warning is never explained.

    Args:
        market: The run's market guardrails, or None when the caller has none to give.

    Returns:
        ``market.cap_rate_spread_target`` when a market block is supplied, else ``MIN_SPREAD``.
    """
    if market is None:
        return MIN_SPREAD
    return market.cap_rate_spread_target


def _flag(condition: bool, msg: str, rationale: list[str]) -> None:
    """Append a rationale line if condition is True."""
    if condition:
        rationale.append(msg)


def _levers_for(forecast: FinancialForecast, spread_target: float) -> list[str]:
    """
    Produce actionable (but generic) levers based on observed weaknesses.
    This is V1 and intentionally qualitative.

    Args:
        forecast: The forecast being judged.
        spread_target: The cap-rate-spread target in force (see ``spread_target_for``). Quoted in
            the lever text so the suggested fix names the bar the reader actually configured.
    """
    y1 = forecast.years[0]
    levers: list[str] = []

    # If spread below target
    if forecast.purchase.spread_vs_rate < spread_target:
        levers.append(f"Negotiate lower price to improve cap-rate spread to ≥ {spread_target * 10_000:.0f} bps.")
        levers.append("Pursue lower interest rate or longer amortization to widen spread.")

    # If DSCR weak
    if y1.dscr < MIN_DSCR_Y1:
        levers.append("Increase down payment to reduce debt service and lift DSCR.")
        levers.append("Trim OPEX (e.g., utilities, PM fees) via vendor bids to lift NOI.")
        levers.append("Phase rent increases (e.g., renewal program) to strengthen DSCR.")

    # If Year-1 cash-on-cash below floor
    if forecast.purchase.coc < MIN_COC_Y1:
        levers.append(f"Lift Year-1 net cash flow (rents, ancillary income, OPEX bids) to reach cash-on-cash ≥ {MIN_COC_Y1:.0%}.")
        levers.append("Reduce the cash outlay (seller credits, lower closing costs, smaller upfront reserves) to raise cash-on-cash.")

    # If Year 1 cash flow negative
    if y1.cash_flow < 0:
        levers.append("Target rent optimization (ancillary income, fee schedule) to reach breakeven.")
        levers.append("Defer non-critical CapEx; build reserves gradually to improve Y1 cash flow.")

    # If 10-year IRR low
    if forecast.irr_10yr < MIN_IRR_10YR:
        levers.append(f"Refine exit assumptions (cap rate, value-add) or hold horizon to reach IRR ≥ {MIN_IRR_10YR:.0%}.")
        levers.append("Explore value-add scope (unit upgrades) to raise rents and exit value.")

    # Bubble up model-generated warnings as soft levers
    for w in forecast.warnings:
        levers.append(f"Address: {w}")

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for lever in levers:
        if lever not in seen:
            deduped.append(lever)
            seen.add(lever)
    return deduped


def synthesize_thesis(forecast: FinancialForecast, *, market: MarketAssumptions | None = None) -> InvestmentThesis:
    """
    Convert a FinancialForecast into an InvestmentThesis via simple guardrails.

    Rules for BUY:
      - DSCR (Y1) ≥ MIN_DSCR_Y1
      - Cap-rate spread ≥ the configured ``market.cap_rate_spread_target`` (else MIN_SPREAD)
      - IRR_10yr ≥ MIN_IRR_10YR
      - Year-1 cash-on-cash ≥ MIN_COC_Y1
      - If REQUIRE_POSITIVE_CF_Y1: Year-1 cash flow ≥ 0
      - If REQUIRE_POSITIVE_CF_ALL: All years have cash flow ≥ 0
      - No critical warnings (cap rate below explicit floor)

    Else if most but not all pass -> CONDITIONAL with suggested levers.
    Else -> DECLINE with levers.

    Args:
        forecast: The deterministic forecast to judge. All money numbers come from here; this
            function computes none of them.
        market: The run's market guardrails, when the caller has them. Optional and additive so
            existing callers keep working — but every orchestrator passes ``inputs.market``,
            because the spread test must use the target the *user* configured, not a constant
            baked into this module. Omit it and the spread falls back to ``MIN_SPREAD``.

    Returns:
        InvestmentThesis with verdict, rationale, and levers.
    """
    y1 = forecast.years[0]
    purchase = forecast.purchase
    spread_target = spread_target_for(market)

    rationale: list[str] = []

    # Evaluate guardrails
    dscr_ok = y1.dscr >= MIN_DSCR_Y1
    spread_ok = purchase.spread_vs_rate >= spread_target
    irr_ok = forecast.irr_10yr >= MIN_IRR_10YR
    # Inclusive at the bar, exactly like every sibling above: a deal landing on 3.00% clears it.
    coc_ok = purchase.coc >= MIN_COC_Y1
    cf_y1_ok = (y1.cash_flow >= 0.0) if REQUIRE_POSITIVE_CF_Y1 else True
    cf_all_ok = all(y.cash_flow >= 0.0 for y in forecast.years) if REQUIRE_POSITIVE_CF_ALL else True
    no_cap_floor_breach = not any("cap rate" in w.lower() and "below floor" in w.lower() for w in forecast.warnings)

    # Rationale lines (pros/cons)
    _flag(dscr_ok, f"DSCR (Y1) is healthy at {y1.dscr:.2f} (≥ {MIN_DSCR_Y1:.2f}).", rationale)
    _flag(not dscr_ok, f"DSCR (Y1) is weak at {y1.dscr:.2f} (< {MIN_DSCR_Y1:.2f}).", rationale)

    _flag(spread_ok, f"Cap-rate spread meets target at {purchase.spread_vs_rate:.2%} (≥ {spread_target:.2%}).", rationale)
    _flag(not spread_ok, f"Cap-rate spread is thin at {purchase.spread_vs_rate:.2%} (< {spread_target:.2%}).", rationale)

    _flag(irr_ok, f"Projected IRR (10y) is {forecast.irr_10yr:.2%} (≥ {MIN_IRR_10YR:.2%}).", rationale)
    _flag(not irr_ok, f"Projected IRR (10y) is {forecast.irr_10yr:.2%} (< {MIN_IRR_10YR:.2%}).", rationale)

    _flag(coc_ok, f"Cash-on-cash (Y1) is healthy at {purchase.coc:.2%} (≥ {MIN_COC_Y1:.2%}).", rationale)
    _flag(not coc_ok, f"Cash-on-cash (Y1) is weak at {purchase.coc:.2%} (< {MIN_COC_Y1:.2%}).", rationale)

    if REQUIRE_POSITIVE_CF_Y1:
        _flag(cf_y1_ok, f"Year-1 cash flow is positive at ${y1.cash_flow:,.0f}.", rationale)
        _flag(not cf_y1_ok, f"Year-1 cash flow is negative at ${y1.cash_flow:,.0f}.", rationale)

    if REQUIRE_POSITIVE_CF_ALL:
        _flag(cf_all_ok, "Cash flow is non-negative across the hold period.", rationale)
        _flag(not cf_all_ok, "Cash flow turns negative in some years.", rationale)

    # Only the breach is claimable. `no_cap_floor_breach` is inferred from the *absence* of the
    # engine's warning, which is equally true when no floor was configured at all
    # (`cap_rate_floor` defaults to None) -- so a positive line here would assert compliance with
    # a policy that may not exist. Silence is the honest default until the strategist can see the
    # floor value itself; Wave 3 / OPD-4 restores the positive claim in the house style, naming
    # both numbers ("Purchase cap rate is 6.35% (>= the 5.00% floor you set).").
    _flag(not no_cap_floor_breach, "Purchase cap rate breaches the configured floor.", rationale)

    # Verdict logic (critical fail threshold)
    fails = [
        (not dscr_ok),  # DSCR below floor
        (not spread_ok),  # spread below target
        (not irr_ok),  # IRR below target
        (not coc_ok),  # Year-1 cash-on-cash below floor
        (not cf_y1_ok),  # negative Y1 CF (if enforced)
        (not cf_all_ok),  # negative CF in hold (if enforced)
        (not no_cap_floor_breach),  # explicit cap floor breach
    ]
    num_fails = sum(1 for f in fails if f)

    # Heuristic thresholds (tunable):
    # - DECLINE if ≥3 critical items fail, OR cap-floor breach + DSCR fail together.
    pass_condition = num_fails >= 3 or ((not no_cap_floor_breach) and (not dscr_ok))

    if not any(fails):  # all pass
        verdict = "BUY"
        levers: list[str] = []
    elif pass_condition:  # many critical fails
        verdict = "DECLINE"
        levers = _levers_for(forecast, spread_target)
    else:  # some fail, some pass
        verdict = "CONDITIONAL"
        levers = _levers_for(forecast, spread_target)

    return InvestmentThesis(verdict=verdict, rationale=rationale, levers=levers)
