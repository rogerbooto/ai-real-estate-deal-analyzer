# tests/listing/test_sqft_parsing_regressions.py
"""Regressions for square-footage extraction in ``src.schemas.labels``.

The bug these guard: ``_SQFT_RE`` separated the number from its unit with a bare ``\\s*``,
which spans newlines. In a listing shaped like::

    Price: $399,900
    Square Feet: 1,936

the price on one line spliced onto the "Square Feet" label on the next, and the parser
reported **399900** as the floor area — the purchase price silently masquerading as sqft,
which then poisons every downstream price-per-sqft signal.

Two independent defects were in play, so both are pinned here:
  1. the label-first form ("Square Feet: N") was not recognized at all; and
  2. the inline form was allowed to match across a line break.
"""

from __future__ import annotations

import pytest

from src.schemas.labels import extract_listing_common


def _sqft(text: str) -> int | None:
    """Return just the sqft field of the shared extractor."""
    return extract_listing_common(text, [])[2]


# ---------------------------------------------------------------------------
# The actual regression: a price must never be read as an area
# ---------------------------------------------------------------------------


def test_price_on_preceding_line_is_not_read_as_sqft() -> None:
    text = "Price: $399,900\nSquare Feet: 1,936"
    assert _sqft(text) == 1936, "price spliced across the newline into the area"


def test_price_on_same_line_is_not_read_as_sqft() -> None:
    # ``parse_listing_string`` collapses whitespace before extraction, so the newline
    # defence alone is not enough — the labelled form must win on a single line too.
    text = "Price: $399,900 Square Feet: 1,936"
    assert _sqft(text) == 1936


def test_no_area_present_yields_none_not_the_price() -> None:
    assert _sqft("Price: $399,900\nNo area given") is None


# ---------------------------------------------------------------------------
# Both surface forms parse
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # label-first (previously unrecognized)
        ("Square Feet: 1,936", 1936),
        ("Square Feet: 1936", 1936),
        ("Sq Ft - 900", 900),
        ("Square Footage: 2,400", 2400),
        # inline (pre-existing behaviour, must not regress)
        ("Finished area: 1,016 sq ft", 1016),
        ("850 sq ft", 850),
        ("1200 sqft", 1200),
        ("900 ft²", 900),
        ("~ 1 200 sqft", 1200),
    ],
)
def test_sqft_surface_forms(text: str, expected: int) -> None:
    assert _sqft(text) == expected


def test_label_form_requires_a_separator() -> None:
    # Without a required ':' or '-', "sq ft" followed by any number would swallow the
    # next figure. The first (inline) area must win here.
    assert _sqft("1,016 sq ft 1200") == 1016


# ---------------------------------------------------------------------------
# Beds/baths carried the SAME defect: the inline pattern's `\s*` spanned newlines,
# so "Square Feet: 1,936\nBedrooms: 3" matched "936 Bedrooms" and reported 936 beds.
# ---------------------------------------------------------------------------


def _beds_baths(text: str) -> tuple[float | None, float | None]:
    beds, baths, _sqft, _price, _year = extract_listing_common(text, [])
    return beds, baths


@pytest.mark.parametrize(
    "text",
    [
        "Square Feet: 1,936\nBedrooms: 3\nBathrooms: 1",
        # Callers collapse whitespace before extraction, so the one-line form must hold too.
        "Square Feet: 1,936 Bedrooms: 3 Bathrooms: 1",
    ],
)
def test_preceding_number_is_not_read_as_a_bedroom_count(text: str) -> None:
    assert _beds_baths(text) == (3, 1)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3 bed, 1.5 bath", (3, 1.5)),
        ("Upper Unit: 3 bedrooms, 1 bathroom", (3, 1)),
        ("2 br / 1 ba", (2, 1)),
        ("Bedrooms: 3", (3, None)),
    ],
)
def test_bed_bath_surface_forms(text: str, expected: tuple[float | None, float | None]) -> None:
    assert _beds_baths(text) == expected
