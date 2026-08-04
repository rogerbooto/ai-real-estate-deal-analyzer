# tests/core/insights/test_observation_provenance.py
"""
Per-tag provenance (``ListingInsights.observations``) reaches the live paths.

Every test here turns RED if the provenance population is reverted -- i.e. if a producer goes
back to emitting bare tag strings. They assert the *distinguishability* property the field
exists for: given a tag, a reader must be able to tell whether the listing copy said it, a
filename implied it, a detector saw it (and whether that detector is a real model), or a
language model wrote it.

Deliberate negative assertions
------------------------------
A keyword match must NOT carry a confidence. The cheapest way to make provenance look rich is to
staple a made-up number onto a regex hit, which would make text and model output
indistinguishable again -- the exact defect this field closes. That is asserted, not assumed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from src.agents.listing_analyst import analyze_listing
from src.core.ingest.listing_parser import parse_listing_string
from src.core.insights.provenance import dedupe_and_sort
from src.core.insights.synthesis import synthesize_listing_insights
from src.schemas.models import ListingInsights, ListingNormalized, ObservationProvenance, PhotoInsights
from tests.utils import make_photo_insights, sha256_of

_TEXT = (
    "36 Kelly Street. Recently renovated throughout with a brand new dishwasher. "
    "In-unit laundry and a detached garage. Some mold in the basement."
)


def _by_tag(insights: ListingInsights, tag: str) -> list[ObservationProvenance]:
    return [o for o in insights.observations if o.tag == tag]


# ---------------------------------------------------------------------------------
# 1) Listing text
# ---------------------------------------------------------------------------------


def test_text_tag_records_a_listing_text_origin_with_the_phrase_that_fired() -> None:
    insights = parse_listing_string(_TEXT)

    assert insights.observations, "parse_listing_string emitted tags with no provenance at all"

    renovated = _by_tag(insights, "renovated")
    assert renovated, "condition tag 'renovated' shipped with no provenance record"
    assert [o.origin for o in renovated] == ["listing_text"]
    assert renovated[0].detail == "recently renovated", "the matched listing phrase was not recorded"
    assert renovated[0].kind == "condition"


def test_text_defect_and_amenity_tags_are_attributed_too() -> None:
    insights = parse_listing_string(_TEXT)

    mold = _by_tag(insights, "mold_suspected")
    assert mold and mold[0].origin == "listing_text" and mold[0].kind == "defect"
    assert mold[0].detail == "mold"

    laundry = _by_tag(insights, "in_unit_laundry")
    assert laundry and laundry[0].origin == "listing_text" and laundry[0].kind == "amenity"
    assert laundry[0].detail == "in-unit laundry"


def test_keyword_match_never_fabricates_a_confidence() -> None:
    """A regex hit has no confidence and must not pretend otherwise."""
    insights = parse_listing_string(_TEXT)
    text_records = [o for o in insights.observations if o.origin == "listing_text"]
    assert text_records, "sanity: the fixture must produce text-origin records"

    for obs in text_records:
        assert obs.detection is None, f"text-origin {obs.tag!r} carries a detection record it cannot have"
        assert obs.provider is None, f"text-origin {obs.tag!r} named a provider that never ran"
        assert obs.provider_kind is None, f"text-origin {obs.tag!r} claims a provider kind"


def test_one_surface_tag_backed_by_two_phrases_yields_two_records() -> None:
    """The repeated-tag case WITHIN one source.

    'parking' is a surface key several specific labels collapse onto, so a listing mentioning both
    a garage and a driveway has two independent justifications for the single emitted tag. A dict
    keyed by tag would have to throw one away; the list keeps both.
    """
    insights = parse_listing_string("42 Oak Road. Detached garage plus driveway parking.")

    parking = _by_tag(insights, "parking")
    details = sorted(o.detail or "" for o in parking)
    assert len(parking) >= 2, f"expected one record per matched phrase, got {parking}"
    assert "detached garage" in details and "driveway parking" in details


def test_every_recorded_tag_actually_shipped_in_its_list() -> None:
    """No dangling attributions: a record must point at a tag the reader can find."""
    insights = parse_listing_string(_TEXT)
    lists = {"amenity": insights.amenities, "condition": insights.condition_tags, "defect": insights.defects}
    for obs in insights.observations:
        assert obs.tag in lists[obs.kind], f"{obs.kind} record {obs.tag!r} attributes a tag that shipped nowhere"


# ---------------------------------------------------------------------------------
# 2) CV provider + filename, through the live analyst path (what main.py uses)
# ---------------------------------------------------------------------------------


@pytest.fixture
def cv_photos(tmp_path: Path, make_gradient_img) -> Path:
    """Photos covering BOTH provenance origins, so the two cannot be conflated.

    - ``flat_grey.png``        -> genuinely PIXEL-derived: the local provider reads low channel
      spread at mid brightness and emits ``stainless_appliances`` with real evidence. Its
      filename says nothing, so nothing can be attributed to the name.
    - ``kitchen_dishwasher.png`` -> FILENAME-derived: "dishwasher" in the name alone. No detector
      saw a dishwasher in these pixels.
    - ``kitchen_island_1.png`` -> a filename *material* promoted to the ``kitchen_island`` amenity
      surface, i.e. an assertion made from the file name, never from the pixels.
    """
    pdir = tmp_path / "cv_photos"
    pdir.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 64), (128, 128, 128)).save(pdir / "flat_grey.png")
    make_gradient_img(pdir / "kitchen_dishwasher.png", (64, 64), delta=7)
    make_gradient_img(pdir / "kitchen_island_1.png", (64, 64), delta=4242)
    return pdir


def test_cv_detection_records_the_provider_its_kind_and_its_confidence(cv_photos: Path) -> None:
    """A genuinely PIXEL-derived detection carries the provider, its kind, and its confidence.

    Deliberately asserted on ``stainless_appliances`` (read off the pixels) rather than
    ``dishwasher``: an earlier version of this test used the dishwasher, whose tag comes from the
    *file name*, and so pinned a filename guess as a detector's finding -- certifying the exact
    fabrication the sibling test below forbids. See test_filename_derived_tag_is_never_a_detection.
    """
    insights = analyze_listing(listing_txt_path=None, photos_folder=str(cv_photos), fallback_text="A home.")

    detected = [o for o in _by_tag(insights, "stainless_appliances") if o.origin == "cv_provider"]
    assert detected, f"no cv_provider record for a pixel-derived amenity; got {insights.observations}"

    obs = detected[0]
    assert obs.provider == "local", "the CV provider that produced the tag was not recorded"
    assert obs.provider_kind == "heuristic_stub", "the built-in providers are stubs; recording anything else would let the report claim AI"
    assert obs.provider_version, "the provider version was dropped"
    assert obs.source_image_sha, "the source image was dropped"
    assert obs.detection is not None and obs.detection.confidence > 0.0, "the detection's confidence was discarded"
    assert obs.detection.evidence, "a real detection carries the measurements it was based on; a fabricated one has none"


def test_filename_derived_tag_is_never_a_detection(cv_photos: Path) -> None:
    """M17: a label inferred from a FILE NAME must never be stamped as a detector's finding.

    ``runner._augment_from_filename`` splices filename-inferred labels into the provider's own
    detection list. Before this was fixed, everything in that list was stamped
    ``origin="cv_provider"``, so a blank grey image named ``mold_basement.jpg`` produced a
    0.90-confidence "mould suspected" finding attributed to a detector -- with ``evidence=None``
    and ``rationale=None``, and the highest confidence in the ledger.

    Per-tag provenance made that worse rather than better: before it, the filename guess was a bare
    string, dishonest only by omission. After it, it became an affirmative, structured, machine-
    readable claim with a confidence score attached.
    """
    insights = analyze_listing(listing_txt_path=None, photos_folder=str(cv_photos), fallback_text="A home.")

    dishwasher = _by_tag(insights, "dishwasher")
    assert dishwasher, "the filename-derived amenity shipped with no provenance at all"
    assert [o.origin for o in dishwasher] == [
        "photo_filename"
    ], f"a tag inferred from the file name is recorded as a detector's finding: {dishwasher}"
    assert all(o.detection is None for o in dishwasher), "a filename guess must carry no detection payload, and therefore no confidence"
    assert all(o.provider is None for o in dishwasher), "naming a provider implies that provider looked at the pixels"


def test_filename_derived_tag_is_not_reported_as_a_detector_seeing_it(cv_photos: Path) -> None:
    """``photo_filename`` is a distinct origin on purpose: no detector looked at these pixels."""
    insights = analyze_listing(listing_txt_path=None, photos_folder=str(cv_photos), fallback_text="A home.")

    island = _by_tag(insights, "kitchen_island")
    assert island, "the filename-promoted amenity shipped with no provenance"
    assert [o.origin for o in island] == ["photo_filename"]
    assert island[0].detection is None, "a filename token is not a detection"
    assert island[0].detail == "kitchen_island"


def test_same_tag_from_text_and_from_photos_keeps_both_records(cv_photos: Path) -> None:
    """The repeated-tag case ACROSS sources -- the shape decision this field was designed around.

    The copy claims a dishwasher and a photo is tagged with one. Those are two independent
    sightings; collapsing them would erase the fact that the two sources agree, which is precisely
    the signal a reader wants.
    """
    insights = analyze_listing(
        listing_txt_path=None,
        photos_folder=str(cv_photos),
        fallback_text="7 Pine Lane. Includes a dishwasher.",
    )

    dishwasher = _by_tag(insights, "dishwasher")
    origins = sorted(o.origin for o in dishwasher)
    assert "listing_text" in origins, f"the copy's own claim was dropped: {dishwasher}"
    # The photo side is `photo_filename`, not `cv_provider`: this tag comes from the file being
    # named "kitchen_dishwasher.png", and no detector saw a dishwasher in those pixels. The point
    # of this test is that two independent sightings survive as two records -- a reader can tell
    # "the copy says so AND a photo agrees" from "only the copy says so". That invariant is
    # unchanged; what changed is that the photo-side record no longer overstates how it was made.
    assert "photo_filename" in origins, f"the photo-side sighting was dropped: {dishwasher}"
    assert len(dishwasher) >= 2, "the two sources were collapsed into one record"


# ---------------------------------------------------------------------------------
# 3) The synthesis path (`ingest-listing` CLI)
# ---------------------------------------------------------------------------------


def _normalized(**kwargs: object) -> ListingNormalized:
    base: dict[str, object] = {"address": "9 Birch Ave", "parking": True, "laundry": "in-unit"}
    base.update(kwargs)
    return ListingNormalized(**base)  # type: ignore[arg-type]


def _photos_with_dishwasher(tmp_path: Path) -> PhotoInsights:
    img = tmp_path / "kitchen.png"
    img.write_bytes(b"not-a-real-image-but-hashable")
    return make_photo_insights(
        [img],
        amenities={"dishwasher": True},
        quality_flags={"renovated_score": 0.83},
        detections_by_sha={sha256_of(img): [{"name": "dishwasher", "category": "amenity", "confidence": 0.9}]},
        provenance={"selected_provider": "local", "provider_kind": "heuristic_stub", "use_ai": False},
    )


def test_synthesis_attributes_listing_facts_and_photo_detections_separately(tmp_path: Path) -> None:
    insights = synthesize_listing_insights(_normalized(), _photos_with_dishwasher(tmp_path))

    parking = _by_tag(insights, "parking")
    assert parking and parking[0].origin == "listing_text"
    assert parking[0].detail == "listing.parking=True"

    dishwasher = _by_tag(insights, "dishwasher")
    assert dishwasher and dishwasher[0].origin == "cv_provider"
    assert dishwasher[0].provider == "local"
    assert dishwasher[0].provider_kind == "heuristic_stub"
    assert dishwasher[0].detection is not None and dishwasher[0].detection.confidence == pytest.approx(0.9)


def test_synthesis_threshold_derived_condition_tag_records_the_threshold_not_a_detection(tmp_path: Path) -> None:
    insights = synthesize_listing_insights(_normalized(), _photos_with_dishwasher(tmp_path))

    renovated = _by_tag(insights, "renovated")
    assert renovated, "'renovated' shipped with no provenance"
    assert renovated[0].origin == "cv_provider"
    assert renovated[0].detection is None, "an aggregate-score tag has no single backing detection"
    assert renovated[0].detail == "renovated_score=0.83 >= 0.60", "the threshold that tripped was not recorded"


def test_unattributable_amenity_is_recorded_as_unknown_not_guessed(tmp_path: Path) -> None:
    """An amenity boolean with nothing behind it says so, rather than borrowing a provider."""
    img = tmp_path / "x.png"
    img.write_bytes(b"bytes")
    photos = make_photo_insights([img], amenities={"balcony": True}, provenance={"selected_provider": "local"})

    insights = synthesize_listing_insights(_normalized(parking=None, laundry=None), photos)

    balcony = _by_tag(insights, "balcony")
    assert balcony and balcony[0].origin == "unknown"
    assert balcony[0].provider is None, "an unattributable tag must not name a provider"


# ---------------------------------------------------------------------------------
# 4) Ledger mechanics
# ---------------------------------------------------------------------------------


def test_ledger_is_deterministically_ordered_and_deduped() -> None:
    a = ObservationProvenance(tag="parking", kind="amenity", origin="listing_text", detail="garage")
    b = ObservationProvenance(tag="parking", kind="amenity", origin="listing_text", detail="driveway")
    dup = ObservationProvenance(tag="parking", kind="amenity", origin="listing_text", detail="garage")

    assert dedupe_and_sort([b, a, dup]) == dedupe_and_sort([dup, a, b]) == [b, a]


def test_parsing_the_same_text_twice_yields_an_identical_ledger() -> None:
    first = parse_listing_string(_TEXT).observations
    second = parse_listing_string(_TEXT).observations
    assert first == second


def test_ledger_defaults_empty_so_existing_producers_keep_working() -> None:
    """Additive-only: a ListingInsights built the old way is still valid."""
    assert ListingInsights(amenities=["parking"]).observations == []
