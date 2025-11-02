# src/core/normalize/listing_html.py

"""
Deterministic listing normalizer (HTML/XML → ListingNormalized).

Resilient, offline-safe parser that extracts common real-estate signals:
  - beds, baths (handles ½ and 1/2), sqft (supports 1,200 / thin spaces), price, year built
  - parking, laundry type, heating/cooling
Returns a best-effort ListingNormalized; unknowns remain None.
"""

from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup
from pydantic import ValidationError

from src.core.normalize.address import parse_address
from src.core.normalize.title import infer_title

# Centralized label parsing & phrase maps
from src.schemas.labels import (
    LAUNDRY_PHRASE_MAP,
    AmenityLabel,
    detect_cooling,
    detect_heating,
    extract_listing_common,
    has_any_parking_specific,
    normalize_amenities_from_text,
)
from src.schemas.models import ListingNormalized

# ---------- Public API ----------


def parse_listing_from_tree(tree: str | Path) -> ListingNormalized:
    """
    Parse a listing from an HTML/XML DOM string or file path → ListingNormalized.
    Unknown fields remain None; returns a valid object even on partial info.
    """

    html = Path(tree).read_text(encoding="utf-8") if isinstance(tree, Path) else tree
    soup = BeautifulSoup(html, "lxml")

    notes: list[str] = []
    text = soup.get_text(" ", strip=True)
    lt = text.lower()

    bds, bas, sqft_i, prc, yr = extract_listing_common(text, notes)

    # Structured address first (targeted → fallback)
    addr_res = parse_address(text=text, soup=soup)
    # Compose the legacy single-line address string from the structured parts, if present
    addr_line = None
    postal_code = None
    if addr_res:
        addr_line = (
            ", ".join(
                p
                for p in [
                    addr_res.address_line or "",
                    addr_res.postal_code or "",
                    addr_res.state_province or "",
                    addr_res.country_hint or "",
                ]
                if p
            )
            or None
        )
        postal_code = addr_res.postal_code or None

    title, conf, src, candidates = infer_title(text=text, soup=soup, addr=addr_res)

    # Centralized amenity parsing (covers dishwasher, parking* variants, laundry synonyms, etc.)
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
            title=title or None,
            title_confidence=conf,
            title_source=src,
            title_candidates=candidates,
            source_url=None,  # if available upstream, set it there
            address=addr_line,
            address_structure=addr_res,
            postal_code=postal_code,  # keep easy access
            price=prc,
            bedrooms=bds,
            bathrooms=bas,
            sqft=sqft_i,
            year_built=yr,
            parking=parking,
            laundry=laundry,
            heating=heating,
            cooling=cooling,
            notes="; ".join(notes) if notes else None,
        )
    except ValidationError:
        data = {
            "title": title or None,
            "address": addr_line,
            "address_struct": addr_res,  # NEW
            "postal_code": postal_code,
            "price": prc,
            "bedrooms": bds,
            "bathrooms": bas,
            "sqft": sqft_i,
            "year_built": yr,
            "parking": parking,
            "laundry": laundry,
            "heating": heating,
            "cooling": cooling,
            "notes": "; ".join(notes) if notes else None,
        }
        return ListingNormalized.model_validate({k: v for k, v in data.items() if v is not None})
