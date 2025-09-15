# tests/test_listing_analyst.py
from pathlib import Path

from src.agents.listing_analyst import analyze_listing


def test_analyze_listing_with_text_and_photos(tmp_path: Path):
    # --- prepare listing text ---
    txt = tmp_path / "listing.txt"
    txt.write_text(
        """
        Beautiful triplex at 123 Main St, Springfield 01101.
        In-unit laundry, parking, and balcony. Fresh paint noted.
        """,
        encoding="utf-8",
    )

    # --- prepare photo filenames (empty bytes are fine; we key off names) ---
    (tmp_path / "photos").mkdir()
    (tmp_path / "photos" / "kitchen_updated.jpg").write_bytes(b"")
    (tmp_path / "photos" / "basement_mold.png").write_bytes(b"")
    (tmp_path / "photos" / "roof_leak.JPG").write_bytes(b"")

    insights = analyze_listing(
        listing_txt_path=str(txt),
        photos_folder=str(tmp_path / "photos"),
    )

    # Text-derived fields
    assert insights.address and "123 Main St" in insights.address
    assert "laundry" in insights.amenities
    assert "parking" in insights.amenities
    assert isinstance(insights.notes, list)

    # Photo-derived condition/defects
    assert "updated kitchen" in insights.condition_tags
    assert "mold" in insights.defects
    assert "roof leak" in insights.defects


def test_analyze_listing_handles_missing_sources_gracefully(tmp_path: Path):
    # No files at all — should not raise, returns empty-but-valid object
    insights = analyze_listing(listing_txt_path=None, photos_folder=None)
    assert insights.address is None
    assert insights.amenities == []
    assert insights.condition_tags == []
    assert insights.defects == []
    assert insights.notes == []

    # Provide only fallback text
    insights2 = analyze_listing(
        fallback_text="Cozy duplex at 9 Oak Rd. Parking available.",
        photos_folder=None,
    )
    assert insights2.address and "Oak Rd" in insights2.address
    assert "parking" in insights2.amenities
    assert insights2.condition_tags == []  # no photos => no condition tags
