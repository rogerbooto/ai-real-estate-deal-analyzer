# tests/listing/test_photo_insights.py
"""
Unit tests for src/listing/photo_insights.py using the cv_tagging adapter.

Covers:
  - Deterministic room counting and amenity flags via filename heuristics.
  - Quality score aggregation (mean) using 'renovated_kitchen' (0.62 conf).
  - No-image directory returns empty/false/zero structure.
"""

from __future__ import annotations

from pathlib import Path

from src.core.cv.photo_insights import build_photo_insights


def test_counts_amenities_quality(photo_dir: Path):
    """
    We create filenames that the deterministic tagger recognizes:
      - 'kitchen_updated_dishwasher.jpg' → room:kitchen, condition:renovated_kitchen, amenity:dishwasher
      - 'bathroom_1.jpg'                 → room:bathroom
      - 'kitchen_2.jpg'                  → room:kitchen
    """

    ins = build_photo_insights(photo_dir)

    # Rooms: 2 kitchens, 1 bath
    assert ins.room_counts.get("kitchen") == 2
    assert ins.room_counts.get("bath") == 1

    # M17/R-6: "dishwasher" is in the FILE NAME and no built-in provider declares it can detect a
    # dishwasher, so nothing examined the pixels for one. The amenity boolean stays False -- it
    # feeds ListingInsights.amenities, which finance.engine._apply_insight_modifiers reads for the
    # income-uplift rules. The claim is not lost: it is recorded as an unconfirmed hint.
    assert ins.amenities.get("dishwasher") is False, "a file name alone set an amenity that can move income"
    assert ins.unconfirmed_hint_counts.get("dishwasher") == 1
    assert "dishwasher" not in ins.amenity_counts, "an unmeasured hint was counted as a detection"

    # Quality mean: 'renovated_kitchen' appears once at 0.62 confidence
    # photo_insights aggregates MEAN over seen values; with one value it should be ~0.62
    renovated = ins.quality_flags.get("renovated_score", 0.0)
    assert 0.60 <= renovated <= 0.7

    # Provider metadata captured
    assert isinstance(ins.version, str) and len(ins.version) > 0


def test_no_images_returns_empty(tmp_path: Path):
    ins = build_photo_insights(tmp_path)

    assert ins.room_counts == {}
    # All known amenity keys present with False
    assert any(k for k in ins.amenities.keys())
    assert all(v is False for v in ins.amenities.values())
    # All quality keys present with 0.0
    assert any(k for k in ins.quality_flags.keys())
    assert all(v == 0.0 for v in ins.quality_flags.values())


def test_filters_tiny_and_duplicate(tmp_path: Path, make_gradient_img):
    pdir = tmp_path / "photos"
    pdir.mkdir(parents=True, exist_ok=True)

    # Too-small file (will be rejected)
    (pdir / "tiny.jpg").write_bytes(b"\x00")

    # One proper image (kept)
    good = pdir / "kitchen.png"
    make_gradient_img(good, (128, 128), delta=5000)

    # Duplicate of the proper image (rejected as duplicate)
    (pdir / "kitchen_copy.png").write_bytes(good.read_bytes())

    ins = build_photo_insights(pdir)

    # Only the good image should remain
    assert ins.images_total == 1

    prov = ins.provenance or {}
    filt = prov.get("filtered", {})
    assert filt.get("input_count") == 3
    assert filt.get("kept_count") == 1
    assert filt.get("dropped_count") == 2

    warnings = prov.get("quality_warnings", [])
    assert any("too_small" in w for w in warnings)
    assert any("duplicate" in w for w in warnings)
