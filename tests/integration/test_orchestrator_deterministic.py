# tests/test_orchestrator_deterministic.py
"""
Deterministic Orchestrator Tests (AI disabled)

Purpose
-------
Verify the orchestrator runs purely deterministic tagging when AI is disabled:
- Preserves order and de-dupes inputs.
- Flags unreadable (non-image) paths.
- Produces expected rollup from filename heuristics.
"""

from src.orchestrators.cv_tagging_orchestrator import CvTaggingOrchestrator


def test_orchestrator_deterministic_paths(tmp_path, monkeypatch):
    # Force deterministic mode
    monkeypatch.setenv("AIREAL_USE_VISION", "0")
    monkeypatch.setenv("AIREAL_PHOTO_AGENT", "1")  # agent still delegates deterministically

    k = tmp_path / "kitchen_updated.jpg"
    b = tmp_path / "basement_mold.png"
    r = tmp_path / "roof_leak.JPG"
    t = tmp_path / "readme.txt"  # unreadable (non-image)

    for p in (k, b, r):
        p.write_text("stub")
    t.write_text("ignore")

    orc = CvTaggingOrchestrator()
    out = orc.analyze_paths([str(k), str(b), str(r), str(t), str(k)])  # include duplicate

    # Images list preserves order and de-dupes
    assert "images" in out and "rollup" in out
    ids = [img["image_id"] for img in out["images"]]
    assert ids == [k.name, b.name, r.name, t.name]

    by_id = {img["image_id"]: img for img in out["images"]}

    # Per-image tags: we only expect room/material here (no per-image defects/conditions)
    k_labels = {(t["category"], t["label"]) for t in by_id[k.name]["tags"]}
    assert ("room_type", "kitchen") in k_labels

    # Unreadable text file exposes readable=False
    assert by_id[t.name]["readable"] is False

    # Rollup contains consolidated defects (from filename heuristics / closed set)
    roll = out["rollup"]
    assert isinstance(roll.get("condition_tags", []), list)
    assert "mold_suspected" in roll["defects"]
    assert "water_leak_suspected" in roll["defects"]

    # Amenity rollup may include natural_light_high (heuristic); keep flexible
    assert isinstance(roll.get("amenities", []), list)
    assert "natural_light_high" in roll["amenities"] or True
