# tests/normalize/test_address_parsing.py

from __future__ import annotations

import re

import pytest
from bs4 import BeautifulSoup

from src.core.normalize.address import parse_address


def _s(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def test_schema_org_postaladdress_extraction():
    html = """
    <div itemscope itemtype="https://schema.org/PostalAddress">
      <span itemprop="streetAddress">123 Main St</span>
      <span itemprop="addressLocality">Springfield</span>
      <span itemprop="addressRegion">IL</span>
      <span itemprop="postalCode">62704</span>
      <span itemprop="addressCountry">US</span>
    </div>
    """
    soup = _s(html)
    res = parse_address(text="", soup=soup)
    assert res is not None
    assert res.postal_code == "62704"
    assert res.country_hint == "US"
    assert (res.state_province or "") == "IL"
    # Street line should include the house number and street name
    assert "123" in (res.address_line or "")
    assert "Main" in (res.address_line or "")


def test_meta_tag_extraction():
    html = """
    <head>
      <meta property="og:street-address" content="456 Market Ave">
      <meta property="og:locality" content="Portland">
      <meta property="og:region" content="OR">
      <meta property="og:postal-code" content="97205">
      <meta property="og:country-name" content="US">
    </head>
    """
    soup = _s(html)
    res = parse_address(text="", soup=soup)
    assert res is not None
    assert res.postal_code == "97205"
    assert res.country_hint == "US"
    assert (res.state_province or "") == "OR"
    assert "456" in (res.address_line or "")
    assert "Market" in (res.address_line or "")


def test_dom_hints_extraction_and_canadian_zip_normalization():
    html = """
    <div id="address">
      67 Peter St Moncton NB E1A 3W3 Canada
    </div>
    """
    soup = _s(html)
    res = parse_address(text="", soup=soup)
    assert res is not None
    # Canadian postal should be normalized without space
    assert res.postal_code == "E1A3W3"
    assert res.country_hint == "CA"
    # Province should be NB
    assert (res.state_province or "") == "NB"
    assert "Peter" in (res.address_line or "")


def test_anchor_based_canadian_no_space_in_blob():
    blob = "Lovely home at 2237 Rue de Beaurivage Montreal QC H1L5V8 — call now!"
    res = parse_address(text=blob, soup=None)
    assert res is not None
    assert res.country_hint == "CA"
    assert res.postal_code == "H1L5V8"
    # Make sure street line looks like a street (contains civic number token)
    assert "2237" in (res.address_line or "")
    assert re.search(r"Beaurivage", res.address_line or "", re.IGNORECASE)


def test_usaddress_parsing_for_us_address():
    blob = "1600 Amphitheatre Parkway, Mountain View CA 94043"
    res = parse_address(text=blob, soup=None)
    assert res is not None
    assert res.country_hint == "US"
    assert res.postal_code == "94043"
    assert (res.state_province or "") == "CA"
    assert re.search(r"Mountain\s+View", res.city or "", re.IGNORECASE)
    assert re.search(r"Amphitheatre\s+Parkway", res.address_line or "", re.IGNORECASE)


@pytest.mark.parametrize(
    "blob",
    [
        "",
        "???",
        "just some random text without address or postal",
    ],
)
def test_returns_none_when_no_meaningful_components(blob: str):
    res = parse_address(text=blob, soup=None)
    assert res is None
