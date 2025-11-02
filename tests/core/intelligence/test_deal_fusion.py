# tests/core/intelligence/test_deal_fusion.py

from __future__ import annotations

from src.core.finance.adapters import FinanceSummary
from src.core.intelligence.deal_fusion import fuse_deal_intelligence
from src.core.intelligence.scoring import DEFAULT_WEIGHTS, compute_composite_score


def test_fuse_deal_intelligence_deterministic_components_and_score(
    listing_fixture,
    photos_fixture,
    finance_fixture,
) -> None:
    """
    Validate that fusion produces stable score components, a deterministic composite,
    sorted risks, and normalized notes for the baseline fixtures.

    Expected components:
      media_quality = avg(0.80, 0.60) = 0.70
      roi_index = 0.55
      neighborhood_safety = 0.70
      defect_penalty = 0.25 * distinct_defects = 0.25 * 2 = 0.50

    Composite with DEFAULT_WEIGHTS:
      s = 0.40*0.70 + 0.30*0.55 + 0.20*0.70 + (-0.10)*0.50
        = 0.28 + 0.165 + 0.14 - 0.05
        = 0.535
    """
    deal = fuse_deal_intelligence(listing_fixture, photos_fixture, finance_fixture)

    # Components
    assert abs(deal.score_components.media_quality - 0.70) < 1e-12
    assert abs(deal.score_components.roi_index - 0.55) < 1e-12
    assert abs(deal.score_components.neighborhood_safety - 0.70) < 1e-12
    assert abs(deal.score_components.defect_penalty - 0.50) < 1e-12

    # Composite score — check exact numeric target and parity with the scoring function
    expected_numeric = 0.535
    assert abs(deal.composite_score - expected_numeric) < 1e-12

    expected_via_fn = compute_composite_score(deal.score_components, DEFAULT_WEIGHTS)
    assert abs(deal.composite_score - expected_via_fn) < 1e-12

    # Risks: defects present; not negative cashflow; not above-market PPSF (210 <= 230)
    assert deal.risk_flags == ["parking:none"]

    # Notes normalized & sorted
    assert deal.notes == ["South-facing windows", "Walkable to trails"]


def test_above_market_ppsf_and_negative_cashflow_risks(
    listing_fixture,
    photos_fixture,
) -> None:
    """
    When PPSF is > 1.15 * market_ppsf and cashflow is negative,
    both risks should appear alongside the defect risk; list is sorted.
    """
    finance = FinanceSummary(
        irr=0.10,
        cashflow_monthly=-50.0,
        price_per_sqft=240.0,  # 240 > 1.15 * 200 = 230 → triggers above-market
        market_ppsf=200.0,
        purchase_price=300000.0,
        area_safety_index=0.40,
    )

    deal = fuse_deal_intelligence(listing_fixture, photos_fixture, finance)

    assert deal.risk_flags == ["parking:none", "neighborhood:low_safety_index"]
