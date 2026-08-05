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
from src.core.cv import amenities_defects as ad
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


@pytest.fixture
def detector_that_covers_dishwashers(tmp_path: Path, monkeypatch) -> object:
    """Bind a provider that CAN detect ``dishwasher`` and, on these images, reports none.

    Needed because the built-in providers declare a two-label vocabulary (light and grey), so
    ``dishwasher`` is normally a label NOTHING can look for -- and a filename claim nothing can
    check is not an observation at all, so it produces no provenance record to assert on (that
    case is covered in tests/core/cv/test_filename_corroboration.py). The tests below are about
    the OTHER case: something looked, disagreed, and the file name's claim survives as the file
    name's claim -- never as the detector's.
    """

    def _covers_dishwasher_reports_none(_img: object) -> list[object]:
        return []

    monkeypatch.setenv("AIREDEAL_CACHE_DIR", str(tmp_path / "cache"))
    original = ad._PROVIDERS["local"]
    ad.register_provider("local", _covers_dishwasher_reports_none, detects=["dishwasher"])
    yield _covers_dishwasher_reports_none
    ad._PROVIDERS["local"] = original


@pytest.fixture
def detector_that_confirms_dishwashers(tmp_path: Path, monkeypatch) -> object:
    """Bind a provider that CAN detect ``dishwasher`` and DOES report it on these images.

    Needed for ``test_same_tag_from_text_and_from_photos_keeps_both_records``: a *contested*
    filename claim (the sibling fixture above) never reaches the money-reading ``amenities`` list
    as of Mission 2 task 3.4's Task A, so it can no longer demonstrate "the copy and a photo both
    saw it" -- only a genuinely confirmed detection (the provider covers the label AND emits it)
    can produce two independent, tag-list-surviving records to compare.
    """

    def _confirms_dishwasher(_img: object) -> list[object]:
        return [{"name": "dishwasher", "confidence": 0.72, "evidence": ["stub_detector"]}]

    monkeypatch.setenv("AIREDEAL_CACHE_DIR", str(tmp_path / "cache_confirmed"))
    original = ad._PROVIDERS["local"]
    ad.register_provider("local", _confirms_dishwasher, detects=["dishwasher"])
    yield _confirms_dishwasher
    ad._PROVIDERS["local"] = original


def test_cv_detection_records_the_provider_its_kind_and_its_confidence(cv_photos: Path) -> None:
    """A genuinely PIXEL-derived detection carries the provider, its kind, and its confidence.

    Deliberately asserted on ``stainless_appliances`` (read off the pixels) rather than
    ``dishwasher``: an earlier version of this test used the dishwasher, whose tag comes from the
    *file name*, and so pinned a filename guess as a detector's finding -- certifying the exact
    fabrication the sibling test below forbids. See test_filename_contested_tag_is_never_promoted_to_an_amenity.
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


def test_filename_contested_tag_is_never_promoted_to_an_amenity(cv_photos: Path, detector_that_covers_dishwashers: object) -> None:
    """M17 closed the ATTRIBUTION half of this defect; Mission 2 task 3.4 (Task A) closes the MONEY half.

    ``runner._augment_from_filename`` splices filename-suggested labels into the provider's own
    detection list. Before M17, everything in that list was stamped ``origin="cv_provider"``, so a
    blank grey image named ``mold_basement.jpg`` produced a 0.90-confidence "mould suspected"
    finding attributed to a detector -- with ``evidence=None`` and ``rationale=None``, and the
    highest confidence in the ledger. M17 fixed the ATTRIBUTION (the record correctly said
    ``photo_filename``, not ``cv_provider``) but the tag still entered ``insights.amenities`` --
    the list ``finance.engine._apply_insight_modifiers`` reads by MEMBERSHIP, never confidence --
    so a claim a detector explicitly REJECTED could still select an income rule. This test used to
    assert exactly that ("the filename-derived amenity shipped with... provenance", i.e. it shipped
    as an amenity at all): the premise this mission's G2-N1/G2-N2 rows overturned on the sibling
    producer and this row (3.4 Task A) overturns here. A contested claim now stays out of
    ``amenities`` entirely -- it is not dropped, it still reaches the reader through ``notes``,
    worded to say a covering detector disagreed.
    """
    insights = analyze_listing(listing_txt_path=None, photos_folder=str(cv_photos), fallback_text="A home.")

    assert "dishwasher" not in insights.amenities, "a claim a detector CONTRADICTED reached the money-reading list"
    assert _by_tag(insights, "dishwasher") == [], "a withheld tag left a dangling provenance record"
    contested_notes = [n for n in insights.notes if "dishwasher" in n]
    assert contested_notes, f"the contested hint vanished entirely: {insights.notes}"
    # The disagreement itself is on the record: a reader must be able to tell "a detector looked
    # and said no" from "a file name said so and nothing checked".
    assert "did not report it" in contested_notes[0], f"the detector's disagreement was dropped: {contested_notes}"


def test_filename_promoted_material_stays_out_of_the_tag_lists_too(cv_photos: Path) -> None:
    """Task 3.5 (Mission 2): a filename-promoted material is the SAME class of claim as a
    filename-suggested amenity/defect, so it is withheld from ``amenities`` the same way.

    Re-adjudicated: this test used to assert ``kitchen_island`` shipped as a ``photo_filename``-
    origin observation ON ``insights.amenities``, i.e. that the promotion graduated into the list
    ``finance.engine._apply_insight_modifiers`` reads. That was consistent with the *pre-3.4* CV
    pipeline but not with the suggest-vs-confirm rule (R-6) this mission closed everywhere else:
    ``tag_images``'s material path (``core/cv/runner.py``) has no detector/provider concept at
    all, so nothing can ever CONFIRM or CONTEST a promoted material the way a covering CV provider
    can for a filename-suggested amenity. Structurally it is always the "nothing was able to look"
    case, so it is now an unconfirmed hint -- shown to the reader via ``notes``, not counted as an
    amenity, and (since ``retain_recorded_tags`` only keeps observations pointing at a tag that
    actually shipped) it carries no dangling ledger entry either.
    """
    insights = analyze_listing(listing_txt_path=None, photos_folder=str(cv_photos), fallback_text="A home.")

    assert "kitchen_island" not in insights.amenities, "a filename-only material claim reached the money-reading list"
    assert _by_tag(insights, "kitchen_island") == [], "a withdrawn tag left a dangling provenance record"
    assert any("kitchen_island" in n for n in insights.notes), "the filename hint vanished instead of being surfaced"


def test_same_tag_from_text_and_from_photos_keeps_both_records(cv_photos: Path, detector_that_confirms_dishwashers: object) -> None:
    """The repeated-tag case ACROSS sources -- the shape decision this field was designed around.

    The copy claims a dishwasher and a photo is tagged with one. Those are two independent
    sightings; collapsing them would erase the fact that the two sources agree, which is precisely
    the signal a reader wants.

    Re-adjudicated to use ``detector_that_confirms_dishwashers`` rather than the CONTESTED fixture:
    since Mission 2 task 3.4 (Task A), a contested photo-side claim never enters ``amenities`` at
    all (see ``test_filename_contested_tag_is_never_promoted_to_an_amenity``), so it can no longer
    demonstrate two sources agreeing -- only a genuinely CONFIRMED detection can produce a second,
    tag-list-surviving record to compare against the text-side one.
    """
    insights = analyze_listing(
        listing_txt_path=None,
        photos_folder=str(cv_photos),
        fallback_text="7 Pine Lane. Includes a dishwasher.",
    )

    dishwasher = _by_tag(insights, "dishwasher")
    origins = sorted(o.origin for o in dishwasher)
    assert "listing_text" in origins, f"the copy's own claim was dropped: {dishwasher}"
    # The photo side is `cv_provider`: a detector that covers "dishwasher" actually emitted it on
    # these pixels. The point of this test is that two independent sightings survive as two
    # records -- a reader can tell "the copy says so AND a photo agrees" from "only the copy says
    # so".
    assert "cv_provider" in origins, f"the photo-side sighting was dropped: {dishwasher}"
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
