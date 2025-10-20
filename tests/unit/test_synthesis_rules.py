# tests/unit/test_synthesis_rules.py
from src.core.insights import synthesize_listing_insights
from src.schemas.models import ListingNormalized, PhotoInsights


def test_synthesis_adds_notes_on_flags():
    listing = ListingNormalized(price=1000.0, bedrooms=2.0, bathrooms=1.0, sqft=800)
    photos = PhotoInsights(
        room_counts={"kitchen": 1}, amenities={"dishwasher": True}, quality_flags={"renovated_score": 0.7}, provider="det", version="1"
    )
    out = synthesize_listing_insights(listing, photos)
    assert out is not None
    assert any("dishwasher" in (n.lower()) for n in out.notes)
