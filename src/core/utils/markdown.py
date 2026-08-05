# src/core/utils/markdown.py
from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def _kv(label: str, value: Any) -> str:
    if value is None or value == "":
        return ""
    return f"- **{label}:** {value}"


def deal_card(d: Any, score: float, rank: int | None = None) -> str:
    """One deal as a Markdown block.

    ``rank`` is optional and defaults to ``None`` so existing callers keep working, but
    :func:`render_markdown` always passes it: the section is titled "Ranked Deals", and a ranked
    list whose entries carry no rank leaves the reader to infer the ordering from document order
    alone. The retired inline block in ``cli/advisor_cli.py`` numbered its headings; adopting this
    shared renderer must not cost the reader that.
    """
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
    summary_fn = getattr(L, "summary", None)
    summary = summary_fn() if callable(summary_fn) else None

    parts = [
        f"### {rank}. {title}" if rank is not None else f"### {title}",
        _kv("Address", addr),
        _kv("Composite score", f"{score:.2f}"),
        _kv("Cashflow (monthly)", f"{cash:,.0f}" if cash is not None else None),
        # `price` is genuinely optional on a listing, and this module was unreachable until task
        # 3.1b wired it, so nothing had ever exercised the None path: `f"{None:,.0f}"` raises
        # TypeError, taking the whole report down over one missing field.
        _kv("Price", f"{price:,.0f}" if price is not None else None),
        _kv("Price / sqft", f"{ppsf:,.2f}" if ppsf is not None else None),
        _kv("Beds", bd),
        _kv("Baths", ba),
        _kv("Sqft", sqft),
        _kv("Title source", tsrc),
        _kv("Title confidence", f"{tconf:.2f}" if tconf is not None else None),
        _kv("Summary", summary),
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
    lines = ["# Deal Advisor Report", ""]
    lines.append(portfolio_block(portfolio))
    lines.append("")
    lines.append("## Ranked Deals")
    for position, (d, score) in enumerate(ranked, start=1):
        lines.append("")
        lines.append(deal_card(d, score, rank=position))
    lines.append("")
    return "\n".join(lines)
