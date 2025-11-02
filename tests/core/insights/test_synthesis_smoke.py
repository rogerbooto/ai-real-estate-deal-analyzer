from src.core.insights.synthesis import synthesize_listing_insights
from src.schemas.models import ListingNormalized, PhotoInsights


def _minimal_listing():
    return ListingNormalized(
        title="Test Property",
        source_url="https://example.com/1",
        address="123 Test Ave",
    )


def test_synthesize_no_images_no_crash():
    listing = _minimal_listing()
    photos = PhotoInsights(
        room_counts={},
        amenities={},
        quality_flags={},
        defect_counts={},
        parking=None,
        image_index={},
        image_labels={},
        image_detections={},
        provider="local",
        version="v1",
        ontology_version="amenities_defects_v1",
        provenance={},
        images_total=0,
        detections_total=0,
    )
    out = synthesize_listing_insights(listing, photos)
    assert out.address is not None
    assert out.amenities == []
    assert isinstance(out.notes, list)


def test_synthesize_no_amenities_returns_empty_list():
    listing = _minimal_listing()
    photos = PhotoInsights(
        room_counts={},
        amenities={},
        quality_flags={},
        defect_counts={},
        parking=None,
        image_index={},
        image_labels={},
        image_detections={},
        provider="local",
        version="v1",
        ontology_version="amenities_defects_v1",
        provenance={},
        images_total=1,
        detections_total=0,
    )
    out = synthesize_listing_insights(listing, photos)
    assert out.amenities == []


def test_synthesize_bad_scores_yield_sparse_condition_tags():
    listing = _minimal_listing()
    photos = PhotoInsights(
        room_counts={},
        amenities={},
        quality_flags={"renovated_score": 0.2, "natural_light_score": 0.1, "curb_appeal_score": 0.1},
        defect_counts={},
        parking=None,
        image_index={},
        image_labels={},
        image_detections={},
        provider="local",
        version="v1",
        ontology_version="amenities_defects_v1",
        provenance={},
        images_total=2,
        detections_total=0,
    )
    out = synthesize_listing_insights(listing, photos)
    # Low scores shouldn't trigger positive tags like 'renovated' or 'good natural light'
    assert out.condition_tags == []
