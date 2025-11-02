# src/core/intelligence/narrative_builder.py

from __future__ import annotations

from .deal_fusion import DealIntelligence


def _fmt_money(value: float | None) -> str:
    """Format currency without localization; deterministic and simple."""
    if value is None:
        return "N/A"
    try:
        return f"${int(round(float(value))):,}"
    except Exception:
        return "N/A"


def _score_from_flags(flags: dict[str, float], key: str) -> float:
    """Safely fetch a score in [0,1] from quality_flags, defaulting to 0.0."""
    try:
        return float(flags.get(key, 0.0))
    except Exception:
        return 0.0


def build_narrative_md(deal: DealIntelligence) -> str:
    """
    Produce a deterministic Markdown narrative for a fused deal.

    Sections:
      - Deal Overview (title, address)
      - Snapshot (beds/baths, price, composite score)
      - Media Insights (quality flags, detected defects)
      - Financials (IRR, monthly cashflow)
      - Risks (sorted)
      - Notes (sorted)

    Determinism:
      - All lists are sorted.
      - All floats are formatted with fixed precision (2 decimals).
      - Missing values are rendered as 'N/A' or omitted lines.
    """
    listing = deal.listing
    photos = deal.photos
    finance = deal.finance
    lines: list[str] = []

    # Title & Address
    title = listing.title or "Listing"
    lines.append(f"# Deal Overview — {title}")
    if listing.address:
        lines.append(f"**Address:** {listing.address}")
    lines.append("")

    # Snapshot
    lines.append("## Snapshot")
    beds = "?" if listing.bedrooms is None else f"{listing.bedrooms}"
    baths = "?" if listing.bathrooms is None else f"{listing.bathrooms}"
    lines.append(f"- **Beds/Baths:** {beds} / {baths}")

    # Price (prefer finance.purchase_price; fall back to listing.price)
    price_value = getattr(finance, "purchase_price", None) if finance is not None else None
    if price_value is None and listing.price is not None:
        price_value = listing.price
    lines.append(f"- **Price:** {_fmt_money(price_value)}")
    lines.append(f"- **Composite Score:** {deal.composite_score:.2f}")
    lines.append("")

    # Media Insights
    lines.append("## Media Insights")
    natural_light_score = _score_from_flags(photos.quality_flags, "natural_light_score")
    renovated_score = _score_from_flags(photos.quality_flags, "renovated_score")
    lines.append(f"- Natural light score: {natural_light_score:.2f}")
    lines.append(f"- Renovated score: {renovated_score:.2f}")
    if photos.defect_counts:
        detected_defects = ", ".join(sorted(photos.defect_counts.keys()))
        lines.append(f"- Detected defects: {detected_defects}")
    lines.append("")

    # Financials
    lines.append("## Financials")
    if hasattr(finance, "irr"):
        try:
            lines.append(f"- IRR: {float(finance.irr):.2f}")
        except Exception:
            lines.append("- IRR: N/A")
    if hasattr(finance, "cashflow_monthly"):
        try:
            lines.append(f"- Monthly cashflow: {float(finance.cashflow_monthly):.2f}")
        except Exception:
            lines.append("- Monthly cashflow: N/A")
    lines.append("")

    # Risks
    if deal.risk_flags:
        lines.append("## Risks")
        for risk in sorted(deal.risk_flags):
            lines.append(f"- {risk}")
        lines.append("")

    # Notes
    if deal.notes:
        lines.append("## Notes")
        for note in sorted(deal.notes):
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)
