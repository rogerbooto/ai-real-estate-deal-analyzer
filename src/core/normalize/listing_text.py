# src/core/normalize/listing_text.py
"""
Deterministic listing normalizer (plain text → ListingNormalized).
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import ValidationError

from src.schemas.models import ListingNormalized

from .listing_html import (  # reuse regexes/helpers for single-source-of-truth logic
    _BATH_RE,
    _BED_RE,
    _COOL_KEYS,
    _HEAT_KEYS,
    _LAUNDRY_TABLE,
    _PARKING_RE,
    _PRICE_RE,
    _SQFT_RE,
    _YEAR_RE,
    _clean_num,
    _normalize_half_notation,
)


def _extract_common(text: str, notes: list[str]) -> tuple[float | None, float | None, int | None, float | None, int | None]:
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
    """
    text = Path(doc).read_text(encoding="utf-8") if isinstance(doc, Path) else doc
    notes: list[str] = ["Parsed from plain text."]

    bds, bas, sqft_i, prc, yr = _extract_common(text, notes)

    lt = text.lower()
    parking = bool(_PARKING_RE.search(text))
    laundry = next((v for k, v in _LAUNDRY_TABLE.items() if k in lt), None)
    heating = next((k for k in _HEAT_KEYS if k in lt), None)
    cooling = next((k for k in _COOL_KEYS if k in lt), None)

    try:
        return ListingNormalized(
            price=prc,
            bedrooms=bds,
            bathrooms=bas,
            sqft=sqft_i,
            year_built=yr,
            parking=parking or None,
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
            "parking": parking or None,
            "laundry": laundry,
            "heating": heating,
            "cooling": cooling,
            "notes": "; ".join(notes),
        }
        return ListingNormalized.model_validate({k: v for k, v in data.items() if v is not None})
