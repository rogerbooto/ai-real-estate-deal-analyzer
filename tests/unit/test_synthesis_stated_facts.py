# tests/unit/test_synthesis_stated_facts.py
"""Regression for F4: stated listing facts must survive `synthesize_listing_insights`.

Before this fix, `synthesize_listing_insights` hand-built `ListingInsights` and never
copied `title/price/sqft/bedrooms/bathrooms/year_built` from the normalized listing, so
stated facts parsed from the source were silently dropped before reaching the report.
"""

from __future__ import annotations

from src.core.finance import run_financial_model
from src.core.insights.synthesis import synthesize_listing_insights
from src.core.reports.generator import generate_report
from src.schemas.models import ListingNormalized, PhotoInsights
from tests.utils import make_financial_inputs


def _listing_with_all_stated_facts() -> ListingNormalized:
    return ListingNormalized(
        address="36 Kelly St",
        title="36 Kelly St, Moncton",
        price=449_900.0,
        sqft=2100,
        bedrooms=4.0,
        bathrooms=2.5,
        year_built=1998,
    )


def _empty_photos() -> PhotoInsights:
    return PhotoInsights(room_counts={}, amenities={}, quality_flags={}, provider="det", version="1")


def test_stated_facts_survive_synthesis() -> None:
    listing = _listing_with_all_stated_facts()
    out = synthesize_listing_insights(listing, _empty_photos())

    assert out.title == "36 Kelly St, Moncton"
    assert out.price == 449_900.0
    assert out.sqft == 2100
    assert out.bedrooms == 4.0
    assert out.bathrooms == 2.5
    assert out.year_built == 1998


def test_absent_stated_facts_stay_none_not_fabricated() -> None:
    listing = ListingNormalized(address="123 Test Ave")
    out = synthesize_listing_insights(listing, _empty_photos())

    assert out.title is None
    assert out.price is None
    assert out.sqft is None
    assert out.bedrooms is None
    assert out.bathrooms is None
    assert out.year_built is None


def test_stated_facts_reach_the_rendered_report() -> None:
    listing = _listing_with_all_stated_facts()
    insights = synthesize_listing_insights(listing, _empty_photos())
    forecast = run_financial_model(make_financial_inputs())

    report = generate_report(insights, forecast, None)

    assert "449,900" in report
    assert "2,100 sq ft" in report
    assert "built 1998" in report
