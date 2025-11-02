# src/core/utils/markdown.py
from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def _kv(label: str, value: Any) -> str:
    if value is None or value == "":
        return ""
    return f"- **{label}:** {value}"


def deal_card(d: Any, score: float) -> str:
    L = getattr(d, "listing", None)
    F = getattr(d, "finance", None)
    title = getattr(L, "title", None) or getattr(d, "shortname", None) or "(untitled)"
    addr = getattr(L, "address", None)
    bd = getattr(L, "bedrooms", None)
    ba = getattr(L, "bathrooms", None)
    sqft = getattr(L, "sqft", None)
    price = getattr(L, "price", None)
    ppsf = getattr(F, "price_per_sqft", None)
    cash = getattr(F, "cashflow_monthly", None)
    tconf = getattr(L, "title_confidence", None)
    tsrc = getattr(L, "title_source", None)

    parts = [
        f"### {title}",
        _kv("Address", addr),
        _kv("Composite score", f"{score:.2f}"),
        _kv("Cashflow (monthly)", f"{cash:,.0f}" if cash is not None else None),
        _kv("Price", f"{price:,.0f}"),
        _kv("Price / sqft", f"{ppsf:,.2f}" if ppsf is not None else None),
        _kv("Beds", bd),
        _kv("Baths", ba),
        _kv("Sqft", sqft),
        _kv("Title source", tsrc),
        _kv("Title confidence", f"{tconf:.2f}" if tconf is not None else None),
    ]
    return "\n".join(p for p in parts if p)


def portfolio_block(portfolio: dict[str, Any]) -> str:
    return "\n".join(
        [
            "## Portfolio",
            f"- **Average score:** {portfolio.get('avg_score', 0):.2f}",
            f"- **Total monthly cashflow:** {portfolio.get('total_cashflow', 0):,.0f}",
            f"- **Risk items:** {portfolio.get('risk_items', 0)}",
        ]
    )


def render_markdown(ranked: Iterable[tuple[Any, float]], portfolio: dict[str, Any]) -> str:
    lines = ["# Deal Advisor Results", ""]
    lines.append(portfolio_block(portfolio))
    lines.append("")
    lines.append("## Ranked Deals")
    for d, score in ranked:
        lines.append("")
        lines.append(deal_card(d, score))
    lines.append("")
    return "\n".join(lines)
