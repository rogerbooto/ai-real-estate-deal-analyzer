# tests/core/cv/test_amenities_defects.py
from __future__ import annotations

from io import BytesIO

from PIL import Image

from src.core.cv import amenities_defects as mod  # to reach _PROVIDERS for monkeypatch
from src.core.cv.amenities_defects import detect_from_image
from src.core.cv.ontology import AMENITIES_DEFECTS_V1


def _img_from_bytes(png_bytes) -> Image.Image:
    """Build a tiny PIL image from the shared png_bytes() fixture (no disk IO)."""
    data = png_bytes(16, 16)  # small, deterministic
    return Image.open(BytesIO(data)).convert("RGB")


def test_ood_labels_rejected(monkeypatch, png_bytes):
    """Provider returns a mix of OOD and in-ontology names; only canonicals survive."""

    def fake_provider(_: Image.Image):
        return [
            {"name": "nonexistent_label", "confidence": 0.99},  # OOD → drop
            {"name": "garage", "confidence": 0.80},  # synonym → parking_garage
            {"name": "mold", "confidence": 0.75},  # synonym → mold_suspect
        ]

    monkeypatch.setitem(mod._PROVIDERS, "local", fake_provider)

    out = detect_from_image(_img_from_bytes(png_bytes), provider="local", ontology=AMENITIES_DEFECTS_V1)
    names = [d["name"] for d in out]
    cats = {d["category"] for d in out}

    assert "parking_garage" in names
    assert "mold_suspected" in names
    assert cats.issubset({"amenity", "defect"})


def test_duplicates_merge_with_max_confidence(monkeypatch, png_bytes):
    """If provider emits the same concept twice (synonyms), keep max confidence."""

    def fake_provider(_: Image.Image):
        return [
            {"name": "garage", "confidence": 0.40},  # lower confidence
            {"name": "parking_garage", "confidence": 0.85},  # higher confidence canonical
            "garage",  # string form — treated as 0.0 conf
        ]

    monkeypatch.setitem(mod._PROVIDERS, "vision", fake_provider)

    out = detect_from_image(_img_from_bytes(png_bytes), provider="vision", ontology=AMENITIES_DEFECTS_V1)
    assert len(out) == 1
    rec = out[0]
    assert rec["name"] == "parking_garage"
    assert abs(rec.get("confidence", 0.0) - 0.85) < 1e-9


def test_cutoff_gating_applied(monkeypatch, png_bytes):
    """
    Below-cutoff candidates are dropped; at-or-above cutoff are kept.
    - ev_charger has cutoff 0.65 (ontology)
    - dishwasher has cutoff 0.60 (ontology)
    """

    def fake_provider(_: Image.Image):
        return [
            {"name": "ev_charger", "confidence": 0.50},  # below cutoff → drop
            {"name": "dishwasher", "confidence": 0.60},  # meets cutoff → keep
        ]

    monkeypatch.setitem(mod._PROVIDERS, "vision", fake_provider)
    out = detect_from_image(_img_from_bytes(png_bytes), provider="vision", ontology=AMENITIES_DEFECTS_V1)
    names = [d["name"] for d in out]
    assert "ev_charger" not in names
    assert "dishwasher" in names


def test_local_provider_basic_heuristics():
    """
    A very bright image should trigger 'natural_light_high' from the local provider.
    """
    # Create a bright image (near-white) to satisfy luminance heuristic
    img = Image.new("RGB", (64, 64), color=(245, 245, 245))
    out = detect_from_image(img, provider="local", ontology=AMENITIES_DEFECTS_V1)
    names = [d["name"] for d in out]
    assert "natural_light_high" in names


def test_onnx_provider_closed_set_and_cutoffs(monkeypatch, png_bytes):
    """
    Simulate ONNX provider outputs with a fake provider and verify:
      - OOD labels are dropped
      - synonyms are canonicalized
      - per-label cutoffs enforced
    """

    def fake_onnx(_: Image.Image):
        return [
            {"name": "unknown_label", "confidence": 0.99},  # OOD → drop
            {"name": "garage", "confidence": 0.80},  # synonym → parking_garage (keep)
            {"name": "dishwasher", "confidence": 0.58},  # below 0.60 → drop
            {"name": "ev_charger", "confidence": 0.72},  # above 0.65 → keep
        ]

    monkeypatch.setitem(mod._PROVIDERS, "onnx", fake_onnx)

    out = detect_from_image(_img_from_bytes(png_bytes), provider="onnx", ontology=AMENITIES_DEFECTS_V1)
    names = [d["name"] for d in out]
    cats = {d["category"] for d in out}

    assert "parking_garage" in names
    assert "ev_charger" in names
    assert "dishwasher" not in names
    assert "unknown_label" not in names
    assert cats.issubset({"amenity", "defect"})


def test_onnx_provider_duplicate_resolution(monkeypatch, png_bytes):
    """
    If the provider emits multiple synonyms of the same concept, the highest confidence wins.
    """

    def fake_onnx(_: Image.Image):
        return [
            {"name": "parking_garage", "confidence": 0.70},
            {"name": "garage", "confidence": 0.82},  # synonym, higher confidence → should win
        ]

    monkeypatch.setitem(mod._PROVIDERS, "onnx", fake_onnx)

    out = detect_from_image(_img_from_bytes(png_bytes), provider="onnx", ontology=AMENITIES_DEFECTS_V1)
    assert len(out) == 1
    rec = out[0]
    assert rec["name"] == "parking_garage"
    assert abs(rec.get("confidence", 0.0) - 0.82) < 1e-9
