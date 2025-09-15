# src/agents/chief_strategist.py
"""
Chief Strategist Agent (V1)

Purpose
-------
Convert a deterministic FinancialForecast into an InvestmentThesis:
  - Verdict: BUY | CONDITIONAL | PASS
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

from typing import List

from src.schemas.models import FinancialForecast, InvestmentThesis

# ----------------------------
# Underwriting guardrails (tunable)
# ----------------------------
MIN_DSCR_Y1 = 1.20            # Year 1 DSCR floor
MIN_SPREAD = 0.015            # Cap rate - interest rate target (150 bps)
MIN_IRR_10YR = 0.12           # 10-year IRR target (12%)
REQUIRE_POSITIVE_CF_ALL = False  # If True, require CF >= 0 for all years to be BUY
REQUIRE_POSITIVE_CF_Y1 = True    # Require CF >= 0 in Year 1 for BUY


def _flag(condition: bool, msg: str, rationale: List[str]) -> None:
    """Append a rationale line if condition is True."""
    if condition:
        rationale.append(msg)


def _levers_for(forecast: FinancialForecast) -> List[str]:
    """
    Produce actionable (but generic) levers based on observed weaknesses.
    This is V1 and intentionally qualitative.
    """
    y1 = forecast.years[0]
    levers: List[str] = []

    # If spread below target
    if forecast.purchase.spread_vs_rate < MIN_SPREAD:
        levers.append("Negotiate lower price to improve cap-rate spread to ≥ 150 bps.")
        levers.append("Pursue lower interest rate or longer amortization to widen spread.")

    # If DSCR weak
    if y1.dscr < MIN_DSCR_Y1:
        levers.append("Increase down payment to reduce debt service and lift DSCR.")
        levers.append("Trim OPEX (e.g., utilities, PM fees) via vendor bids to lift NOI.")
        levers.append("Phase rent increases (e.g., renewal program) to strengthen DSCR.")

    # If Year 1 cash flow negative
    if y1.cash_flow < 0:
        levers.append("Target rent optimization (ancillary income, fee schedule) to reach breakeven.")
        levers.append("Defer non-critical CapEx; build reserves gradually to improve Y1 cash flow.")

    # If 10-year IRR low
    if forecast.irr_10yr < MIN_IRR_10YR:
        levers.append("Refine exit assumptions (cap rate, value-add) or hold horizon to reach IRR ≥ 12%.")
        levers.append("Explore value-add scope (unit upgrades) to raise rents and exit value.")

    # Bubble up model-generated warnings as soft levers
    for w in forecast.warnings:
        levers.append(f"Address: {w}")

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for l in levers:
        if l not in seen:
            deduped.append(l)
            seen.add(l)
    return deduped


def synthesize_thesis(forecast: FinancialForecast) -> InvestmentThesis:
    """
    Convert a FinancialForecast into an InvestmentThesis via simple guardrails.

    Rules for BUY:
      - DSCR (Y1) ≥ MIN_DSCR_Y1
      - Cap-rate spread ≥ MIN_SPREAD
      - IRR_10yr ≥ MIN_IRR_10YR
      - If REQUIRE_POSITIVE_CF_Y1: Year-1 cash flow ≥ 0
      - If REQUIRE_POSITIVE_CF_ALL: All years have cash flow ≥ 0
      - No critical warnings (cap rate below explicit floor)

    Else if most but not all pass -> CONDITIONAL with suggested levers.
    Else -> PASS with levers.

    Returns:
        InvestmentThesis with verdict, rationale, and levers.
    """
    y1 = forecast.years[0]
    purchase = forecast.purchase

    rationale: List[str] = []

    # Evaluate guardrails
    dscr_ok = y1.dscr >= MIN_DSCR_Y1
    spread_ok = purchase.spread_vs_rate >= MIN_SPREAD
    irr_ok = forecast.irr_10yr >= MIN_IRR_10YR
    cf_y1_ok = (y1.cash_flow >= 0.0) if REQUIRE_POSITIVE_CF_Y1 else True
    cf_all_ok = all(y.cash_flow >= 0.0 for y in forecast.years) if REQUIRE_POSITIVE_CF_ALL else True
    no_cap_floor_breach = not any("cap rate" in w.lower() and "below floor" in w.lower() for w in forecast.warnings)

    # Rationale lines (pros/cons)
    _flag(dscr_ok, f"DSCR (Y1) is healthy at {y1.dscr:.2f} (≥ {MIN_DSCR_Y1:.2f}).", rationale)
    _flag(not dscr_ok, f"DSCR (Y1) is weak at {y1.dscr:.2f} (< {MIN_DSCR_Y1:.2f}).", rationale)

    _flag(spread_ok, f"Cap-rate spread meets target at {purchase.spread_vs_rate:.2%} (≥ {MIN_SPREAD:.2%}).", rationale)
    _flag(not spread_ok, f"Cap-rate spread is thin at {purchase.spread_vs_rate:.2%} (< {MIN_SPREAD:.2%}).", rationale)

    _flag(irr_ok, f"Projected IRR (10y) is {forecast.irr_10yr:.2%} (≥ {MIN_IRR_10YR:.2%}).", rationale)
    _flag(not irr_ok, f"Projected IRR (10y) is {forecast.irr_10yr:.2%} (< {MIN_IRR_10YR:.2%}).", rationale)

    if REQUIRE_POSITIVE_CF_Y1:
        _flag(cf_y1_ok, f"Year-1 cash flow is positive at ${y1.cash_flow:,.0f}.", rationale)
        _flag(not cf_y1_ok, f"Year-1 cash flow is negative at ${y1.cash_flow:,.0f}.", rationale)

    if REQUIRE_POSITIVE_CF_ALL:
        _flag(cf_all_ok, "Cash flow is non-negative across the hold period.", rationale)
        _flag(not cf_all_ok, "Cash flow turns negative in some years.", rationale)

    _flag(no_cap_floor_breach, "Purchase cap rate respects the floor policy.", rationale)
    _flag(not no_cap_floor_breach, "Purchase cap rate breaches the configured floor.", rationale)

    # Verdict logic (critical fail threshold)
    fails = [
        (not dscr_ok),                 # DSCR below floor
        (not spread_ok),               # spread below target
        (not irr_ok),                  # IRR below target
        (not cf_y1_ok),                # negative Y1 CF (if enforced)
        (not cf_all_ok),               # negative CF in hold (if enforced)
        (not no_cap_floor_breach),     # explicit cap floor breach
    ]
    num_fails = sum(1 for f in fails if f)

    # Heuristic thresholds (tunable):
    # - PASS if ≥3 critical items fail, OR cap-floor breach + DSCR fail together.
    pass_condition = (
        num_fails >= 3
        or ((not no_cap_floor_breach) and (not dscr_ok))
    )

    if not any(fails):            # all pass
        verdict = "BUY"
        levers: List[str] = []
    elif pass_condition:          # many critical fails
        verdict = "PASS"
        levers = _levers_for(forecast)
    else:                         # some fail, some pass
        verdict = "CONDITIONAL"
        levers = _levers_for(forecast)

    return InvestmentThesis(verdict=verdict, rationale=rationale, levers=levers)
