# tests/core/insights/test_filename_material_never_becomes_a_sighting.py
"""
Mission 2, Gate 3 remediation — S1. **A material promoted off a file name is not a sighting.**

Task 3.5 brought filename-promoted materials under the suggest-vs-confirm rule in
``cv_tagging_orchestrator`` (its 3b block) but not in ``synthesis``. Before this fix,
``synthesis._photo_amenity_observations`` counted a filename-only material (e.g. ``kitchen_island``
promoted by ``MATERIAL_TO_AMENITY_SURFACE`` from a bare file name) as a real sighting, under a
comment reading "still a sighting for the purposes of this count, because nothing contradicted
it" — the wrong test, because nothing was ever ABLE to contradict it: no detector examines pixels
for a material tag at all (``_filename_generic_labels`` in ``core/cv/runner.py`` reads only the
name).

The reproduction (reviewer's, on a single blank grey ``kitchen_island.jpg``)::

    SYNTHESIS producer    -> ListingInsights.amenities: ['kitchen island', 'stainless appliances']
                             photos.unconfirmed_hint_counts: {}
    ORCHESTRATOR producer -> rollup['amenities']: ['stainless_appliances'] | unconfirmed_hints: ['kitchen_island']

So ``kitchen island`` entered the money-reading list from a file name with no hint note anywhere.
It moves no dollars TODAY only because ``finance.engine._apply_insight_modifiers`` matches the
literal strings ``"in-unit laundry"`` and ``"parking"`` and neither ``MaterialTag`` promotes to
either of those surfaces — "safe by accident", the same shape G2-N1/G2-N2/defect #4 already closed.

The fix brings ``synthesis`` to the same rule as the orchestrator: a filename-promoted material is
withheld from ``amenities``/``condition_tags``/``defects`` (the three lists the finance core
reads), and the reader learns about it through the unconfirmed-hint channel instead — the same
``unconfirmed_hint_note`` wording ``_notes_from`` already uses for
``photos.unconfirmed_hint_counts``, and the same fact ``cv_tagging_orchestrator`` puts in
``rollup["unconfirmed_hints"]``. Routed through the shared predicate
``is_uncorroborated_filename_claim`` (not re-decided locally), matching the docstring's explicit
instruction that a second copy of this rule is how the two producers diverged in the first place.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from src.core.cv.photo_insights import build_photo_insights
from src.core.finance.engine import run_financial_model
from src.core.insights.synthesis import synthesize_listing_insights
from src.orchestrators.cv_tagging_orchestrator import CvTaggingOrchestrator
from src.schemas.labels import AmenityLabel, MaterialTag
from src.schemas.models import FinancialInputs, ListingNormalized, PhotoInsights

_KITCHEN_ISLAND = MaterialTag.kitchen_island.value
_INPUTS = Path("data/sample_listings/36_kelly_moncton/inputs.json")


# ---------------------------------------------------------------------------------
# Fixtures — the reviewer's exact reproduction
# ---------------------------------------------------------------------------------


@pytest.fixture
def kitchen_island_photo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A visually blank grey photo named ``kitchen_island.jpg``.

    Blank on purpose: only the FILE NAME claims a kitchen island; nothing in the pixels does, and
    no registered provider even declares the ability to look for one.
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
    img.save(photos / "kitchen_island.jpg", quality=95)
    return photos


def test_reproduction_the_two_producers_used_to_disagree(kitchen_island_photo: Path) -> None:
    """Pinned exactly as the reviewer found it, so a future regression reproduces identically.

    RED on revert: before the fix, the synthesis assertion fails because ``kitchen island`` (or
    ``kitchen_island``, depending on spelling in that branch) is present in ``insights.amenities``.
    """
    photos = build_photo_insights(kitchen_island_photo)
    insights = synthesize_listing_insights(ListingNormalized(address="1 Test St"), photos)
    rollup = CvTaggingOrchestrator().analyze_folder(str(kitchen_island_photo))["rollup"]

    assert "kitchen island" not in insights.amenities, f"a filename-only material reached the money-reading list: {insights.amenities}"
    assert _KITCHEN_ISLAND not in rollup["amenities"]
    assert _KITCHEN_ISLAND in rollup["unconfirmed_hints"], "orchestrator sanity: fixture assumption"

    # The reader must be told the same fact the orchestrator's rollup carries, not nothing.
    hits = [n for n in insights.notes if _KITCHEN_ISLAND in n]
    assert hits, f"the hint vanished; the reader learns nothing: {insights.notes}"
    assert "no registered detector can examine the pixels" in hits[0]
    assert "does not affect any number" in hits[0]


def test_photo_insights_amenities_present_rollup_does_not_re_assert_the_withheld_material(kitchen_island_photo: Path) -> None:
    """The "Amenities present: ..." note reads the boolean map; it must exclude the withheld key,
    matching the identical guard already pinned for a detector-contradicted claim."""
    photos = build_photo_insights(kitchen_island_photo)
    insights = synthesize_listing_insights(ListingNormalized(address="1 Test St"), photos)

    rollups = [n for n in insights.notes if n.startswith("Amenities present:")]
    assert not any(_KITCHEN_ISLAND in n for n in rollups), f"a withheld material was re-asserted in the roll-up: {rollups}"


# ---------------------------------------------------------------------------------
# The consumer guard, isolated (a hand-built PhotoInsights, no CV pipeline involved)
# ---------------------------------------------------------------------------------


def _hand_built_material_only(*, boolean: bool = True) -> PhotoInsights:
    """A ``PhotoInsights`` whose ONLY support for ``kitchen_island`` is a filename-promoted
    material in ``image_labels`` — exactly the shape ``_amenities_surface_from``
    (``core/cv/photo_insights.py``) produces for any material tag, and exactly what
    ``synthesis._photo_amenity_observations``'s second loop must not count as a sighting."""
    return PhotoInsights(
        provider="third_party",
        version="v9",
        amenities={AmenityLabel.kitchen_island.value: boolean},
        image_labels={"sha0": [_KITCHEN_ISLAND]},
        provenance={"selected_provider": "third_party", "provider_kind": "model"},
    )


def _y1_delta(insights: Any) -> float:
    """Same fixture the sibling contested-claim test uses (``36_kelly_moncton/inputs.json``), with
    ``income_is_estimated=True`` so the engine's amenity uplifts are live and this assertion is not
    vacuous."""
    raw = json.loads(_INPUTS.read_text(encoding="utf-8"))["inputs"]
    raw["income_is_estimated"] = True
    fi = FinancialInputs.model_validate(raw)
    return run_financial_model(fi, insights=insights).years[0].cash_flow - run_financial_model(fi, insights=None).years[0].cash_flow


def test_consumer_guard_withholds_a_material_only_support_boolean() -> None:
    """RED on revert of the consumer guard alone, with no CV pipeline involved at all."""
    insights = synthesize_listing_insights(ListingNormalized(address="1 Test St"), _hand_built_material_only())

    assert "kitchen island" not in insights.amenities
    assert any(_KITCHEN_ISLAND in n and "no registered detector" in n for n in insights.notes)
    # Documented in the module docstring: this specific surface moves no dollars today regardless
    # (the engine only reads "in-unit laundry" and "parking" literally) — asserted anyway so a
    # future engine rule keyed on "kitchen island" cannot silently start reading a withheld tag.
    assert _y1_delta(insights) == pytest.approx(0.0)


def test_consumer_guard_does_not_touch_a_boolean_backed_by_a_real_detection() -> None:
    """The guard must be narrow: a surface with a genuine (non-filename) detection still ships,
    exactly as the sibling contested-claim guard is scoped to withhold only what has no other
    support."""
    from src.schemas.models import DetectedLabelModel

    photos = PhotoInsights(
        provider="third_party",
        version="v9",
        amenities={AmenityLabel.stainless_kitchen.value: True},
        image_detections={"sha0": [DetectedLabelModel(name=MaterialTag.stainless_appliances.value, category="amenity", confidence=0.80)]},
        provenance={"selected_provider": "third_party", "provider_kind": "model"},
    )

    insights = synthesize_listing_insights(ListingNormalized(address="1 Test St"), photos)

    assert "stainless appliances" in insights.amenities
