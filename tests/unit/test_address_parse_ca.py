# tests/unit/test_address_parse_ca.py

from src.core.normalize.address import parse_address


def test_parse_canada_city_and_postal():
    text = "123 Bloor St W, Toronto, ON M5V 2T6"
    res = parse_address(text)
    assert res is not None
    assert res.country_hint == "CA"
    assert res.city == "Toronto"
    assert res.postal_code == "M5V2T6"
    # address_line should contain street and city-ish portion
    assert "Bloor" in (res.address_line or "")
