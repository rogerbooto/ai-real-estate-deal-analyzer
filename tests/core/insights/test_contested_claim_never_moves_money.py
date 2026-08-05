# tests/core/insights/test_contested_claim_never_moves_money.py
"""
Mission 2, task 3.4 — G2-N1 and G2-N2. **A claim a detector contradicted must move nothing, and
must never be attributed to that detector.**

The reproduction both halves come from
------------------------------------
A blank grey image named ``garage.jpg``, plus a provider that DECLARES ``parking_garage`` and
REPORTS NOTHING (the documented ``register_provider`` / ``register_onnx_provider`` action, which
R-6 deliberately makes a zero-code-change upgrade)::

    insights.amenities : ['parking']
    Y1 cash flow moved : +$1,105.80
    observation        : origin=cv_provider  provider_kind=model  conf=0.3

**G2-N1 — a contradicted claim moved money.** ``runner._augment_from_filename`` scored the claim
0.30 to say "something looked and disagreed". But ``_surface_key_for_detection`` maps every
``PARKING_SPECIFIC_AMENITIES`` member onto the ``parking`` surface, ``_amenities_from`` emits the
literal tag, and ``finance.engine._apply_insight_modifiers`` selects its income rule by MEMBERSHIP
in ``amenities`` — it never reads a confidence. So the score gated nothing on this route, and
0.30 was never a safety property. A tag that never arrives is the only thing that cannot select a
rule, which is why the guard is at ingest and the finance core is untouched.

**G2-N2 — the same laundering as M17, on the sibling producer.** ``DetectedLabelModel`` had no
``source`` field and ``extra="ignore"``, so the marker was silently DELETED at the schema
boundary. ``synthesis`` then had nothing left to branch on and stamped the record
``origin="cv_provider", provider_kind="model"`` — asserting a detector found what it had
explicitly reported it did not find. Carrying ``source`` onto the model is what makes refusing
that stamp possible at all; a consumer cannot decline to vouch for evidence it was never handed.

Defence in depth, deliberately
------------------------------
Two independent guards, because they fail in different circumstances:

* the PRODUCER guard (``photo_insights._split_measured_and_hints``) keeps contested entries out of
  ``amenity_counts`` / ``defect_counts`` / ``image_detections``;
* the CONSUMER guard (``synthesis._amenities_from``) refuses to ship a tag whose only support is a
  claim a detector rejected — which is what protects the pipeline from a THIRD producer that
  builds ``PhotoInsights`` itself and does not filter.

Each is exercised separately below, so reverting either one turns tests RED on its own.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from src.core.cv import amenities_defects as ad
from src.core.cv.photo_insights import build_photo_insights
from src.core.finance.engine import run_financial_model
from src.core.insights.synthesis import synthesize_listing_insights
from src.schemas.labels import AmenityLabel
from src.schemas.models import (
    DetectedLabelModel,
    FinancialInputs,
    ListingNormalized,
    PhotoInsights,
)

_GARAGE = AmenityLabel.parking_garage.value
_INPUTS = Path("data/sample_listings/36_kelly_moncton/inputs.json")


# ---------------------------------------------------------------------------------
# Fixtures — the reproduction, verbatim
# ---------------------------------------------------------------------------------


@pytest.fixture
def restore_providers() -> Iterator[None]:
    saved = dict(ad._PROVIDERS)
    yield
    ad._PROVIDERS.clear()
    ad._PROVIDERS.update(saved)


@pytest.fixture
def garage_photo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A visually blank grey photo named ``garage.jpg``.

    Blank on purpose: the whole point is that the FILE NAME, not the content, is the only thing
    claiming a garage. Faint deterministic dithering only, so ``_filter_photos`` (1 KiB minimum
    plus a low-entropy drop) does not discard it before anything gets to look.
    """
    monkeypatch.setenv("AIREDEAL_CACHE_DIR", str(tmp_path / "cache"))
    photos = tmp_path / "photos"
    photos.mkdir()
    img = Image.new("RGB", (900, 700), color=(128, 128, 128))
    px = img.load()
    assert px is not None
    for y in range(0, 700, 3):
        for x in range(0, 900, 3):
            px[x, y] = (127, 129, 128)
    img.save(photos / "garage.jpg", quality=95)
    return photos


def _silent(_img: Image.Image) -> list[Any]:
    """A detector that CAN see garages and, on this image, saw nothing."""
    return []


def _sees_a_garage(_img: Image.Image) -> list[dict[str, Any]]:
    """A detector that CAN see garages and, on this image, did."""
    return [{"name": _GARAGE, "confidence": 0.80, "evidence": ["door_ratio=0.44"]}]


def _y1_delta(insights: Any) -> float:
    """How much Year-1 cash flow these insights move, in dollars.

    ``income_is_estimated=True`` is what unlocks the engine's amenity uplifts; with it False the
    engine honours the investor's income verbatim and NOTHING here could move a number, which
    would make every assertion below vacuous.
    """
    raw = json.loads(_INPUTS.read_text(encoding="utf-8"))["inputs"]
    raw["income_is_estimated"] = True
    fi = FinancialInputs.model_validate(raw)
    return run_financial_model(fi, insights=insights).years[0].cash_flow - run_financial_model(fi, insights=None).years[0].cash_flow


# ---------------------------------------------------------------------------------
# G2-N1 — the money
# ---------------------------------------------------------------------------------


def test_a_contradicted_filename_claim_moves_no_money(garage_photo: Path, restore_providers: None) -> None:
    """RED on revert. The headline reproduction: +$1,105.80 must become +$0.00.

    Not asserted as "smaller" or "below a threshold" — exactly zero. A contradicted claim is not
    entitled to a discounted influence on a number; it is entitled to none.
    """
    ad.register_provider("local", _silent, detects=[_GARAGE])

    photos = build_photo_insights(garage_photo)
    insights = synthesize_listing_insights(ListingNormalized(address="1 Test St"), photos)

    assert "parking" not in insights.amenities, f"a claim a detector rejected reached the money path: {insights.amenities}"
    assert _y1_delta(insights) == pytest.approx(0.0), "a contested claim still moved Year-1 cash flow"


def test_a_confirmed_claim_still_moves_money(garage_photo: Path, restore_providers: None) -> None:
    """The guard must be narrow, not a blanket refusal of filename-adjacent evidence.

    Same file name, same rule, one difference: the detector DID report a garage, so the name
    corroborates rather than contradicts. That is two agreeing signals and it is allowed to count.
    Without this test the previous one could be passed by breaking parking detection outright.
    """
    ad.register_provider("local", _sees_a_garage, detects=[_GARAGE])

    photos = build_photo_insights(garage_photo)
    insights = synthesize_listing_insights(ListingNormalized(address="1 Test St"), photos)

    assert "parking" in insights.amenities
    assert _y1_delta(insights) == pytest.approx(1105.80, abs=0.01), "the corroborated path stopped working"


def test_the_reader_is_still_told_about_the_disagreement(garage_photo: Path, restore_providers: None) -> None:
    """Keeping it out of the money must not mean hiding it.

    ``notes`` is the carrier because the report renders it and the finance core never reads it.
    The wording must distinguish this from the "nothing could look" case: a reader told that a
    detector disagreed must not come away believing nothing checked.
    """
    ad.register_provider("local", _silent, detects=[_GARAGE])

    insights = synthesize_listing_insights(ListingNormalized(address="1 Test St"), build_photo_insights(garage_photo))

    hits = [n for n in insights.notes if _GARAGE in n]
    assert hits, f"the disagreement vanished; the reader learns nothing: {insights.notes}"
    assert "did not report it" in hits[0]
    assert "does not affect any number" in hits[0]
    assert "no registered detector" not in hits[0], "reported as 'nothing could look', which is a different fact"


def test_the_amenities_rollup_note_does_not_re_assert_the_withheld_tag(garage_photo: Path, restore_providers: None) -> None:
    """The "Amenities present: ..." note reads the boolean map, which still says parking.

    Rendering it unfiltered would re-assert on one line what the line above just retracted — the
    same shape of defect as the report claiming a feature the code contradicts.
    """
    ad.register_provider("local", _silent, detects=[_GARAGE])

    insights = synthesize_listing_insights(ListingNormalized(address="1 Test St"), build_photo_insights(garage_photo))

    rollups = [n for n in insights.notes if n.startswith("Amenities present:")]
    assert not any("parking" in n for n in rollups), f"a withheld amenity was re-asserted in the roll-up: {rollups}"


# ---------------------------------------------------------------------------------
# G2-N1 — the PRODUCER guard, on its own
# ---------------------------------------------------------------------------------


def test_photo_insights_keeps_contested_entries_out_of_every_counted_rollup(garage_photo: Path, restore_providers: None) -> None:
    """``amenity_counts``/``defect_counts`` are what become tags. ``image_detections`` is what
    the provenance ledger explains. None of them may hold a claim a detector rejected — that is
    what makes ``image_detections`` mean "what a detector reported" rather than "what was said"."""
    ad.register_provider("local", _silent, detects=[_GARAGE])

    photos = build_photo_insights(garage_photo)

    assert photos.amenity_counts == {}, f"a contested claim was counted as a detection: {photos.amenity_counts}"
    assert photos.defect_counts == {}
    assert not any(photos.amenities.values()), f"a contested claim set an amenity boolean: {photos.amenities}"
    assert all(not dets for dets in photos.image_detections.values())
    assert photos.contested_hint_counts.get(_GARAGE) == 1, "the fact was dropped instead of rerouted"
    assert photos.unconfirmed_hint_counts == {}, "a contested claim was mislabelled as unmeasurable"


def test_parking_summary_is_not_set_by_a_contradicted_claim(garage_photo: Path, restore_providers: None) -> None:
    """``_parking_summary`` has its own 0.6 bar, which a 0.30 contested entry already failed.

    Pinned anyway: the bar is a confidence test, and the point of this whole task is that a
    confidence test is not what keeps a rejected claim out. If the blend is ever recalibrated
    above 0.6 this stays RED-worthy rather than silently flipping.
    """
    ad.register_provider("local", _silent, detects=[_GARAGE])

    parking = build_photo_insights(garage_photo).parking

    assert parking is not None
    assert parking.parking_type == "none"
    assert parking.parking_spots is None


# ---------------------------------------------------------------------------------
# G2-N1 — the CONSUMER guard, on its own (the third-producer case)
# ---------------------------------------------------------------------------------


def _hand_built(source: str, *, boolean: bool = True) -> PhotoInsights:
    """A ``PhotoInsights`` assembled by something OTHER than ``build_photo_insights``.

    This is the scenario the consumer guard exists for: a producer that sets the amenity boolean
    and hands over the detection record without filtering it. ``synthesis`` must reach the safe
    answer from the record alone.
    """
    return PhotoInsights(
        provider="third_party",
        version="v9",
        amenities={AmenityLabel.parking.value: boolean},
        image_detections={
            "sha0": [
                DetectedLabelModel(
                    name=_GARAGE,
                    category="amenity",
                    confidence=0.30,
                    evidence=["file name contains 'garage'"],
                    source=source,  # type: ignore[arg-type]
                )
            ]
        },
        provenance={"selected_provider": "third_party", "provider_kind": "model"},
    )


def test_synthesis_withholds_a_tag_whose_only_support_a_detector_rejected() -> None:
    """RED on revert of the consumer guard alone. ``build_photo_insights`` is not involved."""
    insights = synthesize_listing_insights(ListingNormalized(address="1 Test St"), _hand_built("filename_contested"))

    assert "parking" not in insights.amenities
    assert _y1_delta(insights) == pytest.approx(0.0)
    assert any(_GARAGE in n and "did not report it" in n for n in insights.notes)


def test_synthesis_still_trusts_a_boolean_it_has_no_evidence_against() -> None:
    """The guard is scoped to CONTRADICTED, not to "unattributed", and that distinction is the
    whole design. A caller who hand-builds ``amenities`` with no detections at all has asserted
    something this module has no grounds to overrule; silently deleting it would be a different
    dishonesty, and would break every legitimate caller that supplies booleans directly."""
    photos = PhotoInsights(provider="third_party", version="v9", amenities={AmenityLabel.parking.value: True})

    insights = synthesize_listing_insights(ListingNormalized(address="1 Test St"), photos)

    assert "parking" in insights.amenities
    assert [o for o in insights.observations if o.tag == "parking"][0].origin == "unknown"


def test_an_unrecognised_filename_state_fails_safe() -> None:
    """``is_uncorroborated_filename_claim`` is written as "filename-derived AND NOT confirmed", so
    a value added to ``DetectionSource`` later lands in the cautious branch by default.

    Tested at the predicate rather than through the model, because the model's Literal correctly
    refuses an undeclared value — the predicate is what a future fifth state would flow through.
    """
    assert ad.is_uncorroborated_filename_claim("filename_contested")
    assert ad.is_uncorroborated_filename_claim("filename_unconfirmed")
    assert not ad.is_uncorroborated_filename_claim("filename_confirmed")
    assert not ad.is_uncorroborated_filename_claim("pixels")
    assert not ad.is_uncorroborated_filename_claim(None), "an absent marker means a detector emitted it"


# ---------------------------------------------------------------------------------
# G2-N2 — the attribution
# ---------------------------------------------------------------------------------


def test_the_source_marker_survives_schema_validation() -> None:
    """RED on revert of the additive field. ``extra="ignore"`` deleted it silently, which is why
    the consumer "structurally could not" decline the stamp: it was never handed the evidence."""
    det = DetectedLabelModel.model_validate({"name": _GARAGE, "category": "amenity", "confidence": 0.30, "source": "filename_contested"})

    assert det.source == "filename_contested"


def test_an_absent_marker_reads_as_a_detection() -> None:
    """The producer's documented contract: a record that never went through the filename pass IS
    a detection. A third-party provider that emits raw labels must not be demoted for it."""
    det = DetectedLabelModel.model_validate({"name": _GARAGE, "category": "amenity", "confidence": 0.80})

    assert det.source == "pixels"


def test_there_is_exactly_one_definition_of_detection_source() -> None:
    """The vocabulary crosses the schema boundary, so it is defined in ``schemas.models`` and
    re-exported by ``core.cv``. Pinned because two copies of a closed set is how the two halves of
    a safety rule drift apart — and ``src/schemas`` may not import ``src/core`` to fix it later."""
    from src.schemas.models import DetectionSource as SchemaSource

    assert ad.DetectionSource is SchemaSource


def test_a_contested_record_is_not_attributed_to_the_detector(garage_photo: Path, restore_providers: None) -> None:
    """The M17 laundering, on the sibling producer: ``origin=cv_provider, provider_kind=model``
    on a record the detector explicitly did not produce.

    Staged so the tag legitimately ships (a real garage detection on a second photo), because a
    withheld tag drops its ledger entries and would make this assertion vacuous — the failure mode
    where a test passes because the thing it inspects is absent.
    """
    # A second image the detector DOES fire on, so the `parking` surface is genuinely supported and
    # the tag ships. Distinguished by orientation, not by file name, so the file name plays no part.
    Image.new("RGB", (700, 900), color=(70, 90, 110)).save(garage_photo / "front.jpg", quality=95)
    ad.register_provider("local", lambda img: (_sees_a_garage(img) if img.height > img.width else []), detects=[_GARAGE])

    photos = build_photo_insights(garage_photo)
    assert photos.amenities[AmenityLabel.parking.value] is True, "fixture assumption: a real detection supports the surface"
    # Re-introduce the contested record the producer guard correctly removed, so that this test
    # exercises the CONSUMER's attribution rather than the producer's filtering.
    photos.image_detections["contested-sha"] = [
        DetectedLabelModel(name=_GARAGE, category="amenity", confidence=0.30, source="filename_contested")
    ]

    insights = synthesize_listing_insights(ListingNormalized(address="1 Test St"), photos)
    assert "parking" in insights.amenities, "fixture assumption: the tag ships, so its ledger entries survive"
    records = [o for o in insights.observations if o.tag == "parking" and o.source_image_sha == "contested-sha"]

    assert len(records) == 1, f"the contested sighting was not recorded at all: {insights.observations}"
    obs = records[0]
    assert obs.origin == "photo_filename", f"a detector was credited with a finding it rejected: origin={obs.origin}"
    assert obs.provider_kind is None, "a rejected claim was stamped with a producer kind"
    assert obs.detection is None, "a filename claim was given a detection payload"
    assert obs.detail is not None and "did not report it" in obs.detail
