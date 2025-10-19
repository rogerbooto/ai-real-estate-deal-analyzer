# src/core/strategy/strategist.py

from __future__ import annotations

from src.schemas.models import FinancialForecast, InvestmentThesis, MarketAssumptions


def form_thesis(ff: FinancialForecast, mkt: MarketAssumptions) -> InvestmentThesis:
    reasons: list[str] = []
    levers: list[str] = []
    verdict = "BUY"

    # Guardrails
    if ff.purchase.spread_vs_rate < mkt.cap_rate_spread_target:
        reasons.append(f"Cap-rate spread shortfall ({ff.purchase.spread_vs_rate:.2%} < {mkt.cap_rate_spread_target:.2%})")
    if ff.purchase.dscr < 1.20:
        reasons.append(f"DSCR low at purchase ({ff.purchase.dscr:.2f} < 1.20)")
    if ff.purchase.coc < 0.03:
        reasons.append(f"Year-1 CoC low ({ff.purchase.coc:.2%} < 3%)")
    if any(y.cash_flow < 0 for y in ff.years):
        reasons.append("Negative cash flow in projection")

    if reasons:
        verdict = "CONDITIONAL"
        levers += [
            "Negotiate price to lift cap-rate and spread",
            "Buy down rate or seek IO period",
            "Increase rents and/or bill-backs to improve NOI",
        ]

    if ff.purchase.coc < 0 and ff.purchase.dscr < 1.0:
        verdict = "PASS"

    reasons += ff.warnings
    return InvestmentThesis(verdict=verdict, rationale=reasons, levers=levers)
