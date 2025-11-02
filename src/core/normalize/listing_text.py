# src/core/normalize/listing_text.py

"""
Deterministic listing normalizer (plain text → ListingNormalized).

Now aligned with the HTML normalizer:
- Reuses shared regexes and numeric helpers for beds/baths/sqft/price/year.
- Uses the centralized address parser to populate:
    address (single-line), address_structure (structured parts), postal_code.
- Uses centralized amenity/parking/laundry/heating/cooling detectors.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

# Centralized parsing utilities
from src.core.normalize.address import parse_address
from src.core.normalize.title import infer_title
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


def parse_listing_from_text(doc: str | Path) -> ListingNormalized:
    """
    Parse a listing from a plain-text string or file path → ListingNormalized.
    Uses centralized address parsing and label helpers (amenities/heating/cooling/laundry).
    """
    text = Path(doc).read_text(encoding="utf-8") if isinstance(doc, Path) else doc
    lt = text.lower()
    notes: list[str] = ["Parsed from plain text."]

    bds, bas, sqft_i, prc, yr = extract_listing_common(text, notes)

    # ---------- Address (structured first → compose legacy single-line) ----------
    addr_res = parse_address(text=text, soup=None)  # text-only mode

    # Title inference (no HTML title available here)
    title, conf, src, candidates = infer_title(text=text, soup=None, addr=addr_res)

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

    # ---------- Amenities / parking / laundry / HVAC ----------
    amenities_found = normalize_amenities_from_text(lt)
    parking = has_any_parking_specific(amenities_found) or None

    if AmenityLabel.in_unit_laundry in amenities_found:
        laundry: str | None = "in-unit"
    else:
        laundry = next((v for k, v in LAUNDRY_PHRASE_MAP.items() if k in lt), None)

    heating = detect_heating(lt)
    cooling = detect_cooling(lt)

    # ---------- Build model (best-effort) ----------
    try:
        return ListingNormalized(
            title=title or None,
            title_confidence=conf,
            title_source=src,
            title_candidates=candidates,
            source_url=None,
            address=addr_line,
            address_structure=addr_res,
            postal_code=postal_code,
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
        # Fallback: keep as many fields as we can; mirror HTML parser’s shape
        data = {
            "address": addr_line,
            "address_struct": addr_res,  # mirrors listing_html fallback key
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
            "notes": "; ".join(notes),
        }
        return ListingNormalized.model_validate({k: v for k, v in data.items() if v is not None})
