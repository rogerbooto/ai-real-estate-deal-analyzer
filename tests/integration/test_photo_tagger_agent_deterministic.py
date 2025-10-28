# tests/integration/test_photo_tagger_agent_deterministic.py
"""
PhotoTaggerAgent — Deterministic Mode

Purpose
-------
Ensure the agent delegates to deterministic tagging when AI is disabled and
returns the strict schema with expected signals from filename heuristics.
"""

from src.agents.photo_tagger import PhotoTaggerAgent


def test_agent_deterministic_only(tmp_path, monkeypatch):
    # Force deterministic behavior
    monkeypatch.setenv("AIREAL_USE_VISION", "0")

    k = tmp_path / "kitchen_island.jpg"
    w = tmp_path / "notes.txt"
    k.write_text("stub")
    w.write_text("ignore")

    agent = PhotoTaggerAgent()
    out = agent.analyze([str(k), str(w)])

    assert "images" in out and "rollup" in out
    ids = [img["image_id"] for img in out["images"]]
    assert ids == [k.name, w.name]

    by_id = {img["image_id"]: img for img in out["images"]}

    # Kitchen island should be detected from filename
    k_labels = {(t["category"], t["label"]) for t in by_id[k.name]["tags"]}
    assert ("room_type", "kitchen") in k_labels
    assert ("material", "kitchen_island") in k_labels

    # Non-image flagged unreadable
    assert by_id[w.name]["readable"] is False

    # Amenities derived from feature
    roll = out["rollup"]
    assert "kitchen_island" in roll["amenities"]
