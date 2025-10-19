# tests/listing/test_ingest.py
"""
Unit tests for src/listing/ingest.py

Covers:
  - Suffix-based parser selection (HTML vs text).
  - Source URL propagation into ListingNormalized.
  - Photo insights integration using ToolsCVProvider (cv_tagging adapter).
"""

from __future__ import annotations

from pathlib import Path

from src.listing.ingest import ingest_listing
from src.listing.providers.cv_tools_adapter import ToolsCVProvider


def _write_files(tmp: Path, is_html: bool) -> tuple[Path, Path]:
    doc = tmp / ("doc.html" if is_html else "doc.txt")
    photos = tmp / "photos"
    photos.mkdir(parents=True, exist_ok=True)

    if is_html:
        doc.write_text(
            "<html><head><title>T</title></head>" "<body>$1,200 | 2 br | 1 ba | 850 sqft | Built 2001</body></html>",
            encoding="utf-8",
        )
    else:
        doc.write_text("USD 1200  |  2 bed  |  1 bath  |  850 sqft  |  built 2001", encoding="utf-8")

    # Use filenames that the deterministic tagger recognizes:
    # one kitchen image and one unrelated image.
    (photos / "kitchen_1.jpg").write_bytes(b"\x00")
    (photos / "livingroom_a.png").write_bytes(b"\x00")

    return doc, photos


def test_ingest_uses_html_parser_and_sets_source_url(tmp_path: Path):
    doc, photos = _write_files(tmp_path, is_html=True)
    src_url = "https://example.com/listing/123"

    provider = ToolsCVProvider(use_ai=False)  # deterministic-only
    listing, insights = ingest_listing(doc, photos, source_url=src_url, provider=provider)

    # HTML path recognized → parsed title present
    assert listing.title == "T"
    assert listing.source_url == src_url
    assert listing.price == 1200.0
    assert listing.bedrooms == 2.0
    assert listing.bathrooms == 1.0
    assert listing.sqft == 850
    assert listing.year_built == 2001

    # Provider integrated (1 kitchen image detected)
    assert insights.room_counts.get("kitchen") == 1
    assert insights.provider == "ToolsCVProvider"
    assert isinstance(insights.version, str) and len(insights.version) > 0


def test_ingest_uses_text_parser_when_not_html(tmp_path: Path):
    doc, photos = _write_files(tmp_path, is_html=False)

    provider = ToolsCVProvider(use_ai=False)
    listing, insights = ingest_listing(doc, photos, provider=provider)

    assert listing.title is None  # text path has no DOM/title
    assert listing.price == 1200.0
    assert listing.bedrooms == 2.0
    assert listing.bathrooms == 1.0
    assert listing.sqft == 850
    assert listing.year_built == 2001

    # Still got insights based on deterministic provider
    assert insights.room_counts.get("kitchen") == 1
