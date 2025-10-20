# tests/listing/test_html_extractor.py
"""
Unit tests for src/listing/html_extractor.py

Covers:
  - HTML happy path (beds/baths/sqft/price/year/keywords).
  - Plain-text fallback path.
  - Missing/odd formats tolerated with None + notes.
"""

from __future__ import annotations

from pathlib import Path

from src.core.normalize import parse_listing_from_text, parse_listing_from_tree


def _write_html(tmp: Path, body: str) -> Path:
    p = tmp / "sample.html"
    p.write_text(f"<html><head><title>Cozy 2BR</title></head><body>{body}</body></html>", encoding="utf-8")
    return p


def test_html_happy_path(tmp_path: Path):
    html = _write_html(
        tmp_path,
        """
        Price: $1,895 | 2 bed, 1½ bath | ~900 sqft
        Heating: forced air | Cooling: central air | Parking: driveway
        Built 1998. Laundry: in-unit.
        """,
    )
    m = parse_listing_from_tree(html)
    assert m.title == "Cozy 2BR"
    assert m.price == 1895.0
    assert m.bedrooms == 2.0
    assert m.bathrooms == 1.5
    assert m.sqft == 900
    assert m.year_built == 1998
    assert m.parking is True
    assert m.laundry == "in-unit"
    assert m.heating == "forced air"
    assert m.cooling == "central air"
    assert "Parsed half bath notation." in (m.notes or "")


def test_text_fallback(tmp_path: Path):
    txt = tmp_path / "sample.txt"
    txt.write_text(
        "USD 2,300 | 3br | 2 ba | 1,200 sqft | Built 2005 | Onsite laundry | Heat pump AC",
        encoding="utf-8",
    )
    m = parse_listing_from_text(txt)
    assert m.price == 2300.0
    assert m.bedrooms == 3.0
    assert m.bathrooms == 2.0
    assert m.sqft == 1200
    assert m.year_built == 2005
    # Keyword tables
    assert m.laundry in {"on-site", "in-unit"}  # "Onsite" → "on-site"
    assert m.heating == "heat pump" or m.cooling == "heat pump"


def test_missing_fields_are_none():
    m = parse_listing_from_text("Charming apartment near park. No numeric details.")
    assert m.bedrooms is None
    assert m.bathrooms is None
    assert m.sqft is None
    assert m.price is None
    assert m.year_built is None
    assert isinstance(m.notes, str)
