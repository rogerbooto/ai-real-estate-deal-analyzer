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
    t = tmp_path / "readme.txt"  # unreadable

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

    # Deterministic filename heuristics: kitchen 'updated' => renovated_kitchen condition
    k_labels = {(t["category"], t["label"]) for t in by_id[k.name]["tags"]}
    assert ("room_type", "kitchen") in k_labels
    assert ("condition", "renovated_kitchen") in k_labels

    # Basement mold
    b_labels = {(t["category"], t["label"]) for t in by_id[b.name]["tags"]}
    assert ("room_type", "basement") in b_labels
    assert ("issue", "mold_suspected") in b_labels

    # Roof leak filename: at least leak_suspected (room may be absent)
    r_labels = {(t["category"], t["label"]) for t in by_id[r.name]["tags"]}
    assert ("issue", "leak_suspected") in r_labels

    # Unreadable flagged
    assert "unreadable" in by_id[t.name]["quality_flags"]

    # Rollup picks up condition/defects
    roll = out["rollup"]
    assert "renovated_kitchen" in roll["condition_tags"]
    assert "mold_suspected" in roll["defects"]
    assert "leak_suspected" in roll["defects"]
