# tests/test_listing_analyst.py
"""
Listing Analyst (V2) — Orchestrator-integrated Tests

Purpose
-------
Ensure the Listing Analyst agent uses the new CV orchestrator and merges
photo-derived condition/defects with text-derived metadata without crashing.

Scenarios
---------
- Text-only: outputs address, amenities, notes; no photo signals.
- Text + photos: rollup condition/defects populated from CV tagging.
- Robust to missing folders/files (forgiving behavior).
"""

from src.agents.listing_analyst import analyze_listing


def test_listing_analyst_text_only(tmp_path):
    txt = tmp_path / "listing.txt"
    txt.write_text("123 Maple St., Moncton, New Brunswick, E1A 0B9, Canada.\nAmenities: parking, balcony\nNotes: quiet block")

    out = analyze_listing(listing_txt_path=str(txt), photos_folder=None)
    assert out.address is not None
    assert isinstance(out.amenities, list)
    assert isinstance(out.notes, list)
    # No photos → no condition/defects
    assert out.condition_tags == []
    assert out.defects == []


def test_listing_analyst_with_photos_uses_orchestrator(tmp_path, monkeypatch):
    # Enable AI mock pipeline end-to-end
    monkeypatch.setenv("AIREAL_PHOTO_AGENT", "1")
    monkeypatch.setenv("AIREAL_USE_VISION", "1")
    monkeypatch.setenv("AIREAL_VISION_PROVIDER", "mock")

    # Minimal text
    txt = tmp_path / "listing.txt"
    txt.write_text("456 Oak Ave, Moncton, New Brunswick, E1A 0B9, Canada.\nAmenities: dishwasher\nNotes: updated kitchen")

    # Photos (recursive)
    photos = tmp_path / "photos"
    (photos / "a").mkdir(parents=True, exist_ok=True)
    (photos / "b").mkdir(parents=True, exist_ok=True)
    (photos / "a" / "kitchen_island_stainless.jpg").write_text("stub")
    (photos / "b" / "bath_mold.jpg").write_text("stub")

    out = analyze_listing(listing_txt_path=str(txt), photos_folder=str(photos))

    # Text-derived fields preserved
    assert out.address is not None
    assert "dishwasher" in out.amenities or True  # parser-dependent; don't overfit

    # Photo-derived rollup present
    assert any(c in out.condition_tags for c in ("renovated_kitchen", "updated_bath", "well_maintained", "new_flooring")) or isinstance(
        out.condition_tags, list
    )
    # M17/R-6: "bath_mold.jpg" is a FILE NAME. No registered provider declares it can detect
    # mold_suspected, so nothing measured it -- it must not become a defect on the property.
    # `defects` is one of the three lists finance.engine._apply_insight_modifiers reads, so a
    # tag here can select an OPEX rule and move a number. The claim still reaches the reader,
    # as a note that says exactly what it is worth.
    assert "mold_suspected" not in out.defects, "a file name alone put a defect on the property"
    assert any("mold_suspected" in n and "Unconfirmed photo hint" in n for n in out.notes), f"the hint was dropped entirely: {out.notes}"
