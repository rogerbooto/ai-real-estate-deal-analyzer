# src/core/normalize/listing_text.py


"""
Deterministic listing normalizer (plain text → ListingNormalized).
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import ValidationError

# Centralized parsing utilities
from src.schemas.labels import (
    LAUNDRY_PHRASE_MAP,
    AmenityLabel,
    detect_cooling,
    detect_heating,
    has_any_parking_specific,
    normalize_amenities_from_text,
)
from src.schemas.models import ListingNormalized

# Reuse shared regexes and numeric helpers from listing_html for consistency
from .listing_html import (
    _BATH_RE,
    _BED_RE,
    _PRICE_RE,
    _SQFT_RE,
    _YEAR_RE,
    _clean_num,
    _normalize_half_notation,
)


def _extract_common(text: str, notes: list[str]) -> tuple[float | None, float | None, int | None, float | None, int | None]:
    """Extract basic numeric and textual features from raw listing text."""
    bed = _BED_RE.search(text)
    bath = _BATH_RE.search(text)
    sqft = _SQFT_RE.search(text)
    price = _PRICE_RE.search(text)
    year = _YEAR_RE.search(text)

    bds = _clean_num(bed.group(1)) if bed else None
    bas = None
    if bath:
        raw = _normalize_half_notation(bath.group(1))
        bas = _clean_num(raw)

    sqft_i = int(_clean_num(sqft.group(1)) or 0) if sqft else None
    prc = _clean_num(price.group(1)) if price else None
    yr = int(year.group(1)) if year else None

    if (bath and ("½" in bath.group(0) or "1/2" in bath.group(0))) or re.search(r"\b1\s*/\s*2\b", text):
        notes.append("Parsed half bath notation.")
    if bds is None and re.search(r"(?i)\bstudio\b", text):
        bds = 0.0
        notes.append("Detected studio → 0 bedrooms.")
    return bds, bas, sqft_i, prc, yr


def parse_listing_from_text(doc: str | Path) -> ListingNormalized:
    """
    Parse a listing from a plain-text string or file path → ListingNormalized.
    Uses centralized label helpers for amenities, heating, cooling, and laundry.
    """
    text = Path(doc).read_text(encoding="utf-8") if isinstance(doc, Path) else doc
    lt = text.lower()
    notes: list[str] = ["Parsed from plain text."]

    bds, bas, sqft_i, prc, yr = _extract_common(text, notes)

    # Centralized amenity parsing
    amenities_found = normalize_amenities_from_text(lt)

    # parking: True if any specific parking amenity present
    parking = has_any_parking_specific(amenities_found) or None

    laundry: str | None = None

    # laundry: prefer explicit amenity, else fall back to phrase map
    if AmenityLabel.in_unit_laundry in amenities_found:
        laundry = "in-unit"
    else:
        laundry = next((v for k, v in LAUNDRY_PHRASE_MAP.items() if k in lt), None)

    # heating/cooling via centralized detectors
    heating = detect_heating(lt)
    cooling = detect_cooling(lt)

    try:
        return ListingNormalized(
            price=prc,
            bedrooms=bds,
            bathrooms=bas,
            sqft=sqft_i,
            year_built=yr,
            parking=parking,
            laundry=laundry,
            heating=heating,
            cooling=cooling,
            notes="; ".join(notes),
        )
    except ValidationError:
        data = {
            "price": prc,
            "bedrooms": bds,
            "bathrooms": bas,
            "sqft": sqft_i,
            "year_built": yr,
            "parking": parking,
            "laundry": laundry,
            "heating": heating,
            "cooling": cooling,
            "notes": "; ".join(notes),
        }
        return ListingNormalized.model_validate({k: v for k, v in data.items() if v is not None})
