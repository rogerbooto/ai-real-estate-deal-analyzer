# tests/core/normalize/test_title_infer.py

from bs4 import BeautifulSoup

from src.core.normalize.title import infer_title
from src.schemas.models import AddressResult


def test_infer_html_title_has_confidence():
    soup = BeautifulSoup('<meta property="og:title" content="47 Perrot Street, Shediac - MLS NB127621">', "lxml")
    title, conf, src, candidates = infer_title(text=None, soup=soup, addr=None)
    assert title.startswith("47 Perrot")
    assert conf == 1.0
    assert src == "html"
    assert len(candidates) >= 1
    assert "47 Perrot" in candidates[0]


def test_infer_address_city_sets_text_source():
    addr = AddressResult(
        address_line="47 Perrot Street",
        civic_number="47",
        city="Shediac",
        state_province="NB",
        postal_code="E4P 0H3",
        country_hint="CA",
        unit_suite=None,
    )
    title, conf, src, candidates = infer_title(text=None, soup=None, addr=addr)
    assert title == "47 Perrot Street, Shediac"
    assert conf == 0.9
    assert src == "text"
    assert len(candidates) >= 1
    assert "47 Perrot" in candidates[0]


def test_infer_derived_bedbath_confidence():
    addr = AddressResult(
        address_line=None, civic_number=None, city="Shediac", state_province="NB", postal_code="E4P 0H3", country_hint="CA", unit_suite=None
    )
    title, conf, src, candidates = infer_title(text="3 bedrooms and 1 bath in Shediac", soup=None, addr=addr)
    assert conf == 0.60
    assert src == "text"
    assert "Shediac" in title
    assert "Shediac" in candidates[0]
    assert "Shediac" in candidates[1]


def test_infer_fallback_line():
    title, conf, src, candidates = infer_title(text="Charming bungalow in NB\n...", soup=None, addr=None)
    assert conf == 0.6
    assert src == "text"
    assert len(candidates) >= 1
    assert title.startswith("Charming bungalow")
    assert "Charming bungalow" in candidates[0]


def test_infer_title_returns_candidates_and_confidence():
    html = "<html><head><title>Charming 3BR near River</title></head><body></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    addr = AddressResult(
        address_line="123 Main St",
        city="Moncton",
        civic_number="123",
        unit_suite=None,
        state_province="NB",
        postal_code="E4P 0H3",
        country_hint="CA",
    )
    chosen, conf, src, candidates = infer_title(text="3 bed 1 bath — Lovely area", soup=soup, addr=addr)

    assert chosen is not None
    assert isinstance(conf, float) and 0.0 <= conf <= 1.0
    assert src in {"html", "text", "user", None}
    assert isinstance(candidates, list) and len(candidates) >= 1
