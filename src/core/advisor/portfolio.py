# src/core/advisor/portfolio.py

from __future__ import annotations

from src.core.intelligence.deal_fusion import DealIntelligence


def portfolio_summary(deals: list[DealIntelligence]) -> dict[str, float]:
    """Aggregate summary for dashboards."""
    if not deals:
        return {"avg_score": 0.0, "total_cashflow": 0.0, "risk_items": 0.0}
    avg_score = sum(d.composite_score for d in deals) / len(deals)
    total_cf = sum(float(getattr(d.finance, "cashflow_monthly", 0.0)) for d in deals)
    risks = sum(len(d.risk_flags) for d in deals)
    return {"avg_score": float(avg_score), "total_cashflow": float(total_cf), "risk_items": float(risks)}
