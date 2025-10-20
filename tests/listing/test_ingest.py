# tests/listing/test_ingest.py
"""
Unit tests for src/tools/listing_ingest.py

Covers:
  - Suffix-based parser selection (HTML vs text).
  - Source URL behavior on file-based ingest (None).
  - Photo insights integration using ingest_listing which calls tag_photos internally.
"""

from __future__ import annotations

from pathlib import Path

from src.tools.listing_ingest import ingest_listing


def test_ingest_uses_html_parser_and_sets_fields(document_factory, photo_dir: Path):
    html_content = "<html><head><title>T</title></head>" "<body>$1,200 | 2 br | 1 ba | 850 sqft | Built 2001</body></html>"

    doc = document_factory(html=html_content)

    # File-based ingest (no network); source_url should be None
    result = ingest_listing(file=doc, photos_dir=photo_dir, download_media=False)
    listing, photo_insights = result.listing, result.photos

    # HTML path recognized → parsed title present
    assert listing.title == "T"
    assert listing.source_url is None
    assert listing.price == 1200.0
    assert listing.bedrooms == 2.0
    assert listing.bathrooms == 1.0
    assert listing.sqft == 850
    assert listing.year_built == 2001

    # Photo insights (1 kitchen image detected)
    assert photo_insights.room_counts.get("kitchen") == 2
    assert isinstance(photo_insights.provider, str) and len(photo_insights.provider) > 0
    assert isinstance(photo_insights.version, str) and len(photo_insights.version) > 0


def test_ingest_uses_text_parser_when_not_html(document_factory, photo_dir: Path):
    doc_content = "USD 1200  |  2 bed  |  1 bath  |  850 sqft  |  built 2001"

    doc = document_factory(text=doc_content)

    result = ingest_listing(file=doc, photos_dir=photo_dir, download_media=False)
    listing, photo_insights = result.listing, result.photos

    # Text path has no DOM/title
    assert listing.title is None
    assert listing.price == 1200.0
    assert listing.bedrooms == 2.0
    assert listing.bathrooms == 1.0
    assert listing.sqft == 850
    assert listing.year_built == 2001

    # Still got insights based on deterministic file-name tagging
    assert photo_insights.room_counts.get("kitchen") == 2
