# tests/test_photo_tagger_agent.py
"""
PhotoTaggerAgent Tests — Always-AI in AI mode

Purpose
-------
Validate that the agent delegates to the batch-aware orchestrator logic:
- When AI is enabled, all readable images go through AI (mock) and deterministic merge.
- Preserve input order and flag unreadable inputs.
- Surface expected features/amenities for typical filenames.

Notes
-----
- Uses MockVisionProvider (no network).
"""

from src.agents.photo_tagger import PhotoTaggerAgent


def test_agent_runs_ai_on_all_images_when_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv("AIREAL_USE_VISION", "1")
    monkeypatch.setenv("AIREAL_VISION_PROVIDER", "mock")

    kitchen = tmp_path / "kitchen_island_stainless.jpg"
    bath = tmp_path / "bath_double_vanity.jpg"
    other = tmp_path / "random.jpg"  # no room cue; still AI in AI mode
    bad = tmp_path / "notes.txt"  # unreadable

    kitchen.write_text("stub")
    bath.write_text("stub")
    other.write_text("stub")
    bad.write_text("ignore")

    agent = PhotoTaggerAgent()
    out = agent.analyze([str(kitchen), str(bath), str(other), str(bad)])

    assert "images" in out and "rollup" in out
    ids = [img["image_id"] for img in out["images"]]
    assert ids == [kitchen.name, bath.name, other.name, bad.name]  # order preserved

    by_id = {img["image_id"]: img for img in out["images"]}

    # Kitchen tags
    klabels = {(t["category"], t["label"]) for t in by_id[kitchen.name]["tags"]}
    assert ("room_type", "kitchen") in klabels
    assert ("feature", "kitchen_island") in klabels
    assert ("feature", "stainless_appliances") in klabels

    # Bath tags added by AI mock
    blabels = {(t["category"], t["label"]) for t in by_id[bath.name]["tags"]}
    assert ("room_type", "bathroom") in blabels
    assert ("feature", "double_vanity") in blabels

    # Unreadable flagged
    assert "unreadable" in by_id[bad.name]["quality_flags"]

    # Rollup amenities should include kitchen_island and stainless_kitchen
    roll = out["rollup"]
    assert "kitchen_island" in roll["amenities"]
    assert "stainless_kitchen" in roll["amenities"]
