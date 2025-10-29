# tests/reports/test_media_report_unit.py
"""
Unit tests for the MediaReport builder and DTOs.

Reuses shared test scaffolding:
- `photo_dir` (from conftest.py) → materializes deterministic sample images
- `sample_photo_insights` (from conftest.py) → ready-made PhotoInsights for photo_dir
- `photo_insights_factory` (from conftest.py) → build custom PhotoInsights on-the-fly

These tests validate:
- basic field mapping (smoke),
- listing enrichment passthrough,
- warnings behavior (no images / no amenities),
- readable counting using actual files from `photo_dir`.
"""

from __future__ import annotations

from pathlib import Path

from src.core.reports.photo_report import build_media_report
from src.schemas.models import ListingNormalized
from tests import sha256_of


def test_media_report_smoke(sample_photo_insights) -> None:
    """
    Build a MediaReport with the ready-made PhotoInsights from `photo_dir` to test:
    - mapping of key fields,
    - coverage math (images_total / readable / detections_total).
    """
    report = build_media_report(photos=sample_photo_insights)

    # High-level signals
    assert report.room_counts == {"kitchen": 2, "bath": 1}
    assert report.amenities.get("dishwasher") is True
    assert report.parking.parking_type in {"garage", "driveway", "street", "none"}
    assert report.ontology_version == "amenities_defects_v1"

    # Coverage (photo_dir has 3 real files)
    assert report.coverage.images_total == 3
    assert report.coverage.images_readable == 3
    # Provided by the factory (dishwasher + toilet)
    assert report.coverage.detections_total >= 2

    # Images list populated with readable flags
    assert len(report.images) == 3
    assert all(item.readable for item in report.images)


def test_media_report_listing_enrichment(sample_photo_insights) -> None:
    """
    Verify ListingNormalized passthrough for title/source_url/address.
    """
    listing = ListingNormalized(
        title="Charming Triplex",
        source_url="https://example.com/listing/123",
        address="123 Main St, Springfield, 01101",
    )

    report = build_media_report(photos=sample_photo_insights, listing=listing)
    assert report.listing_title == "Charming Triplex"
    assert report.source_url == "https://example.com/listing/123"
    assert report.address == "123 Main St, Springfield, 01101"


def test_media_report_warnings_no_images(photo_insights_factory, tmp_path: Path) -> None:
    """
    No images → include 'no images found' warning.
    (Empty index; totals computed by factory.)
    """
    photos = photo_insights_factory(
        [],  # no image paths
        room_counts={},
        amenities={},  # empty (no all-false check when map is empty)
        defects={},
        quality_flags={},
    )
    report = build_media_report(photos)
    assert any("no images found" in w for w in report.warnings)


def test_media_report_warnings_no_amenities(photo_insights_factory, tmp_path: Path) -> None:
    """
    Amenities map present but all False → include 'no amenities detected' warning.
    """
    # Create one real file for readable counting
    img = tmp_path / "single.jpg"
    img.write_bytes(b"\x00")

    photos = photo_insights_factory(
        [img],
        room_counts={},
        amenities={"dishwasher": False, "in_unit_laundry": False},
        defects={},
        quality_flags={},
    )
    report = build_media_report(photos)
    assert any("no amenities detected" in w for w in report.warnings)
    # Sanity: coverage reflects 1 readable image
    assert report.coverage.images_total == 1
    assert report.coverage.images_readable == 1


def test_media_report_readable_mixed(photo_insights_factory, tmp_path: Path) -> None:
    """
    Mix a real file and a missing file to exercise the 'readable=False' branch
    in the builder and bump overall coverage.
    """
    existing = tmp_path / "exists.jpg"
    existing.write_bytes(b"\x01\x02")

    missing = tmp_path / "missing.jpg"  # do NOT create

    photos = photo_insights_factory(
        [existing, missing],
        room_counts={},
        amenities={},
        defects={},
        quality_flags={},
    )
    report = build_media_report(photos)

    assert report.coverage.images_total == 2
    assert report.coverage.images_readable == 1

    # Verify per-image readable flags via sha keys
    missing_sha = sha256_of(missing)
    exist_sha = sha256_of(existing)

    by_sha = {i.sha256: i for i in report.images}
    assert by_sha[exist_sha].readable is True
    assert by_sha[missing_sha].readable is False
