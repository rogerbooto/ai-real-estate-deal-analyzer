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

    # Amenity flagged True (derived from filename -> feature -> amenity)
    assert ins.amenities.get("dishwasher") is True

    # Quality mean: 'renovated_kitchen' appears once at 0.62 confidence
    # photo_insights aggregates MEAN over seen values; with one value it should be ~0.62
    renovated = ins.quality_flags.get("renovated_score", 0.0)
    assert 0.60 <= renovated <= 0.64

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
