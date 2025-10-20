from src.core.insights.synthesis import synthesize_listing_insights
from src.schemas.models import ListingNormalized, PhotoInsights


def test_synthesis_includes_multiple_notes_and_handles_empty_address():
    listing = ListingNormalized(
        # intentionally omit address fields to exercise address fallback + notes
        price=1900.0,
        bedrooms=3.0,
        bathrooms=2.0,
        sqft=1100,
    )
    photos = PhotoInsights(
        room_counts={"kitchen": 1, "bath": 1},
        amenities={"dishwasher": True, "parking": True},
        quality_flags={"renovated_score": 0.8},  # should trigger “renovated” tag/note
        provider="det",
        version="1",
    )
    out = synthesize_listing_insights(listing, photos)
    joined = " ".join(out.notes).lower()
    assert "dishwasher" in joined
    assert "parking" in joined
    assert any("renovat" in t.lower() for t in out.condition_tags)
    # notes exist and are strings
    assert out.notes and all(isinstance(n, str) for n in out.notes)


def test_synthesis_no_signals_produces_structured_output():
    listing = ListingNormalized(price=1200.0, bedrooms=1.0, bathrooms=1.0, sqft=600)
    photos = PhotoInsights(room_counts={}, amenities={}, quality_flags={}, provider="det", version="1")
    out = synthesize_listing_insights(listing, photos)
    assert isinstance(out.amenities, list)
    assert isinstance(out.condition_tags, list)
    assert isinstance(out.notes, list)
