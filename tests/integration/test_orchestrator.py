# tests/test_orchestrator.py
"""
CV Tagging Orchestrator Tests

Purpose
-------
Validate the high-level orchestrator behavior:
- Normalizes and preserves ordering of input paths.
- Scans folders (non-recursive and recursive) deterministically.
- Honors feature flags to route via PhotoTaggerAgent (which delegates
  to batch-aware cv_tagging) or directly to tag_photos.
- Flags unreadable inputs without raising.

Notes
-----
- Uses the mock vision provider when AI is enabled to avoid network calls.
- We only assert schema shape and key signals (amenities/defects/conditions).
"""

from src.orchestrators.cv_tagging_orchestrator import CvTaggingOrchestrator


def test_analyze_paths_preserves_order_and_flags_unreadable(tmp_path, monkeypatch):
    # Enable AI + mock to exercise the routed path; orchestrator picks agent via env.
    monkeypatch.setenv("AIREAL_PHOTO_AGENT", "1")
    monkeypatch.setenv("AIREAL_USE_VISION", "1")
    monkeypatch.setenv("AIREAL_VISION_PROVIDER", "mock")

    img1 = tmp_path / "kitchen_island.jpg"
    img2 = tmp_path / "bath_double_vanity.jpg"
    not_img = tmp_path / "notes.txt"

    img1.write_text("stub")
    img2.write_text("stub")
    not_img.write_text("text")

    # Duplicate path in list should be de-duplicated (first occurrence wins)
    orc = CvTaggingOrchestrator()
    out = orc.analyze_paths([str(img1), str(img2), str(not_img), str(img1)])

    assert "images" in out and "rollup" in out
    ids = [img["image_id"] for img in out["images"]]
    assert ids == [img1.name, img2.name, not_img.name]  # order preserved, duplicate removed

    by_id = {img["image_id"]: img for img in out["images"]}
    assert "unreadable" in by_id[not_img.name]["quality_flags"]

    # Minimal rollup sanity
    roll = out["rollup"]
    assert isinstance(roll.get("amenities", []), list)
    assert isinstance(roll.get("defects", []), list)
    assert isinstance(roll.get("condition_tags", []), list)


def test_analyze_folder_recursive_and_direct_flag_fallback(tmp_path, monkeypatch):
    # Disable agent to exercise direct orchestrator->tag_photos path
    monkeypatch.setenv("AIREAL_PHOTO_AGENT", "0")
    monkeypatch.setenv("AIREAL_USE_VISION", "1")
    monkeypatch.setenv("AIREAL_VISION_PROVIDER", "mock")

    # Create nested structure
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    f1 = tmp_path / "a" / "kitchen_stainless.jpg"
    f2 = tmp_path / "b" / "bath_mold.jpg"
    f3 = tmp_path / "readme.txt"
    f1.write_text("stub")
    f2.write_text("stub")
    f3.write_text("ignore")

    orc = CvTaggingOrchestrator()
    out = orc.analyze_folder(str(tmp_path), recursive=True)

    assert "images" in out and len(out["images"]) == 2  # only images included
    names = [img["image_id"] for img in out["images"]]
    assert set(names) == {f1.name, f2.name}

    # Mold should appear in defects via mock provider filename cue
    assert "mold_suspected" in out["rollup"]["defects"]
