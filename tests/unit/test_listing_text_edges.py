# tests/unit/test_listing_text_edges.py
from src.core.normalize.listing_text import parse_listing_from_text


def test_parse_listing_from_text_handles_missing_fields():
    lst = parse_listing_from_text("Rent $999 | studio | 1 bath")
    assert lst.price == 999.0
    assert lst.bedrooms is None or lst.bedrooms == 0
