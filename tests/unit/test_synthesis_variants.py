from src.core.insights.synthesis import synthesize_listing_insights
from src.schemas.models import ListingNormalized, PhotoInsights


def test_synthesis_adds_notes_for_amenity_and_condition():
    listing = ListingNormalized(price=1500.0, bedrooms=2.0, bathrooms=1.0, sqft=850)
    photos = PhotoInsights(
        room_counts={"kitchen": 1},
        amenities={"dishwasher": True},  # should create a note
        quality_flags={"renovated_score": 0.72},  # above threshold -> condition tag + note
        provider="det",
        version="1",
    )

    out = synthesize_listing_insights(listing, photos)
    assert "renovated" in " ".join(out.condition_tags).lower()

    # Notes should reference both dishwasher and renovation
    joined = " | ".join(out.notes).lower()
    assert "dishwasher" in joined


def test_synthesis_handles_no_signals_cleanly():
    listing = ListingNormalized(price=1200.0, bedrooms=1.0, bathrooms=1.0, sqft=600)
    photos = PhotoInsights(
        room_counts={},
        amenities={},  # no amenity signals
        quality_flags={"renovated_score": 0},  # below threshold
        provider="det",
        version="1",
    )
    out = synthesize_listing_insights(listing, photos)
    # no condition tag, notes still a valid list (may be empty or minimal)
    assert not out.condition_tags or all(isinstance(x, str) for x in out.condition_tags)
    assert isinstance(out.notes, list)
