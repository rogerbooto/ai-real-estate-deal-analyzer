# tests/normalize/test_address_parametrized.py

import pytest

from src.core.normalize.address import parse_address


@pytest.mark.parametrize(
    "raw,expect_substr",
    [
        # US
        ("123 Main St, Springfield, IL 62704", "Springfield"),
        ("1600 Pennsylvania Ave NW, Washington, DC 20500", "20500"),
        # UK (with country name)
        ("10 Downing St, London SW1A 2AA, UK", "SW1A"),
        # Canada
        ("24 Sussex Dr, Ottawa, ON K1M 1M4", "K1M"),
        # US (no explicit country hint; ZIP anchors parsing)
        ("350 Fifth Ave, New York, NY 10118", "10118"),
        # Netherlands
        ("Damrak 1, 1012 LG Amsterdam, Netherlands", "1012"),
        # UK alt format
        ("221B Baker Street, London NW1 6XE, United Kingdom", "NW1"),
        # Missing city/state but has ZIP → should still parse
        ("742 Evergreen Terrace 49007", "49007"),
        # NL with explicit postcode (parser requires a postcode anchor)
        ("Eendrachtsplein 12, 3012 CM Rotterdam, NL", "3012"),
    ],
)
def test_parse_varied_addresses(raw, expect_substr):
    out = parse_address(raw)
    assert out is not None  # postcode is required; all cases include one
    # Compose a loose string to assert branch coverage without coupling to exact formatting
    s = " ".join(
        [
            out.address_line or "",
            out.city or "",
            out.state_province or "",
            out.postal_code or "",
            out.country_hint or "",
        ]
    )
    assert expect_substr in s
