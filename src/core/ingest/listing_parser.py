# src/core/ingest/listing_parser.py

"""
Lightweight, deterministic parser for local listing text (V2, centralized labels).
"""

from __future__ import annotations

import re

from src.core.normalize.address import parse_address
from src.core.normalize.title import infer_title
from src.schemas.labels import (
    extract_listing_common,
    normalize_amenities_from_text,
    normalize_defects_from_text,
    to_photoinsights_amenities_surface,
)
from src.schemas.models import ListingInsights

# ----------------------------
# Address & simple fields
# ----------------------------

_ADDRESS_RE = re.compile(
    r"(?P<line>\b\d{1,6}\s+[A-Za-z0-9.'\-]+\s+(Street|St|Road|Rd|Avenue|Ave|Boulevard|Blvd|Drive|Dr|Court|Ct|Lane|Ln)"
    r"(?:\s*,?\s*[A-Za-z .'-]+){0,2}\s*(?:\d{5})?)",
    flags=re.IGNORECASE,
)

_UNITS_HINT_RE = re.compile(
    r"\b(?:(\d+)\s+units?)|(duplex|triplex|fourplex|quadplex|quadruplex)\b",
    flags=re.IGNORECASE,
)

# Minimal text-only condition cues to satisfy tests (kept separate from CV condition tags)
_CONDITION_KEYWORDS = {
    "updated kitchen": [r"updated kitchen", r"renovated kitchen", r"new kitchen"],
    "fresh paint": [r"fresh paint", r"new paint", r"repainted"],
    "updated bath": [r"updated bath", r"renovated bath", r"new bath(?:room)?\b"],
    "renovated": [r"recently renovated", r"newly renovated", r"fully renovated", r"just renovated"],
    "move-in ready": [r"move[\s-]?in ready", r"turn[\s-]?key"],
    "new roof": [r"new roof", r"roof (?:was )?replaced", r"roof \(20\d{2}\)"],
    "new windows": [r"new windows", r"windows (?:were )?replaced"],
}


# ----------------------------
# Public API
# ----------------------------


def parse_listing_text(path: str) -> ListingInsights:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    return parse_listing_string(text)


def parse_listing_string(text: str) -> ListingInsights:
    """
    Parse raw listing text into ListingInsights using centralized label normalizers.
    """
    norm = " ".join(text.split())  # collapse whitespace

    # Address (best effort)
    addr_res = parse_address(norm)

    # --- Centralized amenities ---
    amenity_labels = normalize_amenities_from_text(norm)
    amenity_surface = to_photoinsights_amenities_surface(amenity_labels)

    # Emit canonical keys where True
    amenities: list[str] = sorted([k for k, v in amenity_surface.items() if v])

    # Coarsen for test expectations: add "laundry" if in-unit laundry present
    if "in_unit_laundry" in amenities and "laundry" not in amenities:
        amenities.append("laundry")
        amenities.sort()

    # --- Centralized defects ---
    defect_labels = normalize_defects_from_text(norm)
    defects: list[str] = sorted([d.value for d in defect_labels])

    # --- Simple text-only condition tags ---
    lt = norm.lower()
    condition: list[str] = []
    for canon, patterns in _CONDITION_KEYWORDS.items():
        if any(re.search(pat, lt, flags=re.IGNORECASE) for pat in patterns):
            condition.append(canon)
    condition = sorted(set(condition))

    # Notes (simple, deterministic)
    notes = _compose_notes(norm)

    # Title is a fallback identity for the report when no address parses (e.g. a listing whose
    # street line carries no street type). Deterministic: text-only, soup=None.
    title, _conf, _src, _cands = infer_title(text=norm, soup=None, addr=addr_res)

    # Stated facts, via the same shared extractor the HTML/text normalizers use, so all three
    # ingestion paths report identical numbers for identical copy.
    beds, baths, sqft, price, year_built = extract_listing_common(norm, notes)

    return ListingInsights(
        address=addr_res.address_line if addr_res else None,
        title=title,
        price=price,
        sqft=sqft,
        bedrooms=beds,
        bathrooms=baths,
        year_built=year_built,
        amenities=amenities,
        condition_tags=condition,
        defects=defects,
        notes=notes,
    )


# ----------------------------
# Internals
# ----------------------------


def _compose_notes(text: str) -> list[str]:
    notes: list[str] = []
    m = _UNITS_HINT_RE.search(text)
    if m:
        raw = m.group(0)
        notes.append(raw.strip())
    return notes
