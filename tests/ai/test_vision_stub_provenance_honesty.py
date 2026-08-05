# tests/ai/test_vision_stub_provenance_honesty.py
"""The `vision` provider slot holds a stub, and its artifacts must say so.

Two defects are pinned here:

1. `build_photo_insights(use_ai=True)` stamped `version="ai"`, making a hand-written
   threshold's output indistinguishable from a future real classifier's.
2. `_provider_vision_stub` asserted `"street parking"` for any landscape image at
   luminance >= 0.50 -- a property claim derived from a photo being wide and bright.
   On the committed demo listing that fired on 8 of 12 photos and produced
   `parking_type="street", parking_spots=1` plus `amenities["parking"]=True`.

Both turn RED if reverted. The provider seam itself (`_PROVIDERS`,
`register_onnx_provider`, `provider_kind`) is explicitly exercised, not removed.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pytest
from PIL import Image

from src.core.cv import amenities_defects as ad
from src.core.cv.amenities_defects import RawCandidate, detect_from_image, provider_kind
from src.core.cv.ontology import AMENITIES_DEFECTS_V1
from src.core.cv.photo_insights import DETERMINISTIC_VERSION, VISION_STUB_VERSION, build_photo_insights


@pytest.fixture(autouse=True)
def _isolated_cv_cache(tmp_path, monkeypatch):
    """`tag_amenities_and_defects` caches per (provider, sha256); isolate so stale
    pre-fix cache entries can never mask a regression."""
    monkeypatch.setenv("AIREDEAL_CACHE_DIR", str(tmp_path / "cvcache"))


def _bright_landscape() -> Image.Image:
    """Wide and bright -- exactly the input that used to fabricate "street parking"."""
    return Image.new("RGB", (96, 64), color=(245, 245, 245))


# --------------------------------------------------------------------------------------
# Defect 2: no fabricated parking claim
# --------------------------------------------------------------------------------------


def test_vision_stub_emits_no_parking_label_for_a_wide_bright_image() -> None:
    """RED on revert: 'wide and not dark' must not become a parking claim."""
    out = detect_from_image(_bright_landscape(), provider="vision", ontology=AMENITIES_DEFECTS_V1)
    names = {d["name"] for d in out}

    assert "street_parking" not in names, "the vision stub is asserting street parking from aspect+brightness again"
    assert not any("parking" in n for n in names), f"vision stub emitted a parking label: {sorted(names)}"


@pytest.mark.parametrize("size", [(96, 64), (320, 200), (1024, 576)])
def test_no_landscape_geometry_produces_parking(size: tuple[int, int]) -> None:
    """The old rule keyed on aspect alone; sweep landscape geometries to be sure it is gone."""
    img = Image.new("RGB", size, color=(200, 200, 200))
    names = {d["name"] for d in detect_from_image(img, provider="vision", ontology=AMENITIES_DEFECTS_V1)}
    assert not any("parking" in n for n in names)


def test_demo_listing_parking_is_identical_with_and_without_ai(tmp_path, monkeypatch) -> None:
    """RED on revert: on the real committed listing, --ai must not invent parking.

    Pre-fix this asserted parking_type='street', parking_spots=1 and amenities['parking']=True
    on the AI path while the default path said 'none'.
    """
    photos = Path("data/sample_listings/36_kelly_moncton/photos")
    if not photos.is_dir():
        pytest.skip("demo photo bundle not present")

    default = build_photo_insights(photos, use_ai=False)
    ai = build_photo_insights(photos, use_ai=True)

    assert ai.parking == default.parking
    assert ai.parking is not None and ai.parking.parking_type == "none"
    assert ai.parking.parking_spots is None
    assert ai.amenities["parking"] is False
    assert "street_parking" not in ai.amenity_counts


def test_street_parking_remains_consumable_from_a_real_provider() -> None:
    """The fix removes a bogus *emission*, not the seam: a provider that genuinely detects
    street parking still flows through the ontology and the parking roll-up."""

    def _fake_model(img: Image.Image) -> Iterable[RawCandidate]:
        return [{"name": "street parking", "confidence": 0.9, "rationale": "fake model"}]

    original = ad._PROVIDERS["onnx"] if "onnx" in ad._PROVIDERS else None
    ad._PROVIDERS["onnx"] = _fake_model
    try:
        out = detect_from_image(_bright_landscape(), provider="onnx", ontology=AMENITIES_DEFECTS_V1)
        assert [d["name"] for d in out] == ["street_parking"]
    finally:
        if original is None:
            ad._PROVIDERS.pop("onnx", None)
        else:
            ad._PROVIDERS["onnx"] = original


# --------------------------------------------------------------------------------------
# Defect 1: the stub's artifacts are identifiable as the stub's
# --------------------------------------------------------------------------------------


def test_ai_path_is_not_labelled_ai(tmp_path) -> None:
    """RED on revert: `version="ai"` overclaims; the label must name the actual producer."""
    photos = tmp_path / "photos"
    photos.mkdir()
    Image.new("RGB", (800, 600), "white").save(photos / "kitchen.jpg")

    ai = build_photo_insights(photos, use_ai=True)

    assert ai.version != "ai", "stub output is stamped 'ai' again; it is not a model"
    assert ai.version == VISION_STUB_VERSION
    assert "stub" in ai.version


def test_provenance_marks_the_provider_as_a_stub(tmp_path) -> None:
    """A user (and a future maintainer) can tell stub output from a real classifier's."""
    photos = tmp_path / "photos"
    photos.mkdir()
    Image.new("RGB", (800, 600), "white").save(photos / "kitchen.jpg")

    ai = build_photo_insights(photos, use_ai=True)
    default = build_photo_insights(photos, use_ai=False)

    assert ai.provenance["selected_provider"] == "vision"
    assert ai.provenance["provider_kind"] == "heuristic_stub"
    assert default.provenance["provider_kind"] == "heuristic_stub"
    assert default.version == DETERMINISTIC_VERSION  # default path label is unchanged


def test_empty_folder_provenance_agrees_with_the_populated_path(tmp_path) -> None:
    """The early return used to duplicate the provider/version logic; it must not drift."""
    empty = tmp_path / "empty"
    empty.mkdir()

    ai = build_photo_insights(empty, use_ai=True)
    assert ai.version == VISION_STUB_VERSION
    assert ai.provenance["selected_provider"] == "vision"
    assert ai.provenance["provider_kind"] == "heuristic_stub"

    default = build_photo_insights(empty, use_ai=False)
    assert default.version == DETERMINISTIC_VERSION
    assert default.provenance["selected_provider"] == "local"


def test_provider_kind_reports_model_once_a_real_provider_is_registered() -> None:
    """RED on revert: `provider_kind` must track the *current* binding, so registering a
    real classifier (the seam Roger wants) flips the label without a code edit."""

    def _fake_model(img: Image.Image) -> Iterable[RawCandidate]:
        return []

    assert provider_kind("vision") == "heuristic_stub"
    assert provider_kind("local") == "heuristic_stub"
    assert provider_kind("llm") == "heuristic_stub"

    ad._PROVIDERS["onnx"] = _fake_model
    try:
        assert provider_kind("onnx") == "model"
    finally:
        ad._PROVIDERS.pop("onnx", None)

    with pytest.raises(ValueError):
        provider_kind("onnx")  # unregistered again


def test_register_onnx_provider_still_exists() -> None:
    """The seam must survive the honesty fix."""
    assert callable(ad.register_onnx_provider)
    assert callable(ad.make_onnx_provider)
    assert set(ad._PROVIDERS) >= {"local", "vision", "llm"}
