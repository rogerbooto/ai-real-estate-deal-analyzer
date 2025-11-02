# tests/core/intelligence/test_narrative_builder.py

from __future__ import annotations

from src.core.intelligence.deal_fusion import fuse_deal_intelligence
from src.core.intelligence.narrative_builder import build_narrative_md


def test_build_narrative_md_baseline(listing_fixture, photos_fixture, finance_fixture) -> None:
    """
    Validate that the narrative contains the expected sections and key values
    with deterministic formatting.
    """
    deal = fuse_deal_intelligence(listing_fixture, photos_fixture, finance_fixture)
    md = build_narrative_md(deal)

    # Headline and address
    assert "# Deal Overview — Charming 2BR Near River" in md
    assert "**Address:** 123 Main St, Moncton, NB" in md

    # Snapshot with fixed formatting
    assert "## Snapshot" in md
    assert "- **Beds/Baths:** 2.0" in md
    assert "- **Price:** $350,000" in md
    assert "- **Composite Score:** 0.53" in md

    # Media insights & defects line is sorted
    assert "## Media Insights" in md
    assert "- Natural light score: 0.80" in md
    assert "- Renovated score: 0.60" in md
    assert "- Detected defects: crack, paint_peel" in md

    # Financials
    assert "## Financials" in md
    assert "- IRR: 0.55" in md
    assert "- Monthly cashflow: 125.00" in md

    # Risks (sorted) and Notes (sorted)
    assert "## Risks" in md
    assert "- parking:none" in md

    assert "## Notes" in md
    # Notes sorted alphabetically
    assert "- South-facing windows" in md
    assert "- Walkable to trails" in md
