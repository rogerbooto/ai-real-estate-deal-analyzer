# tests/test_cv_tagging_ai_mock.py
"""
AI Path Integration (Mock Provider) — tag_photos()

Purpose
-------
Validate ontology mapping, thresholding, merge behavior, amenity derivation,
and rollup when AI path is enabled with the MockVisionProvider.
"""
import os
from pathlib import Path
from src.tools.cv_tagging import tag_photos


def test_ai_path_with_mock_provider(tmp_path: Path, monkeypatch):
    # Arrange
    kitchen = tmp_path / "kitchen_island_stainless_updated.jpg"
    bath = tmp_path / "bath_double_vanity_mold.jpg"
    kitchen.write_text("stub")
    bath.write_text("stub")

    # Enable AI path with mock provider
    monkeypatch.setenv("AIREAL_USE_VISION", "1")
    monkeypatch.setenv("AIREAL_VISION_PROVIDER", "mock")

    out = tag_photos([str(kitchen), str(bath)], use_ai=None)

    # Schema
    assert "images" in out and "rollup" in out
    imgs = {img["image_id"]: img for img in out["images"]}
    kimg, bimg = imgs[kitchen.name], imgs[bath.name]

    # Kitchen: room, features, condition
    klabels = {(t["category"], t["label"]) for t in kimg["tags"]}
    assert ("room_type", "kitchen") in klabels
    assert ("feature", "kitchen_island") in klabels
    assert ("feature", "stainless_appliances") in klabels
    assert any(t["category"] == "condition" for t in kimg["tags"])

    # Bath: room, feature, issue
    blabels = {(t["category"], t["label"]) for t in bimg["tags"]}
    assert ("room_type", "bathroom") in blabels
    assert ("feature", "double_vanity") in blabels
    assert ("issue", "mold_suspected") in blabels

    # Rollup aggregation
    roll = out["rollup"]
    assert "kitchen_island" in roll["amenities"]
    assert "stainless_kitchen" in roll["amenities"]
    assert "mold_suspected" in roll["defects"]
