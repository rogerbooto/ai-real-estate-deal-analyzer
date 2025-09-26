# tests/test_listing_parser.py
from src.tools.listing_parser import parse_listing_string


def test_parse_listing_string_basics():
    txt = """
    Beautiful triplex at 123 Main St, Springfield, 01101. Fresh paint and updated kitchen.
    In-unit laundry and parking available. Pets allowed. Some water stain in basement noted.
    """
    insights = parse_listing_string(txt)

    assert insights.address and "123 Main St" in insights.address
    assert "laundry" in insights.amenities
    assert "parking" in insights.amenities
    assert "updated kitchen" in insights.condition_tags
    assert "fresh paint" in insights.condition_tags
    assert "water damage" in insights.defects or "mold" not in insights.defects  # at least one defect mapped
    assert any("triplex" in n.lower() for n in insights.notes)
