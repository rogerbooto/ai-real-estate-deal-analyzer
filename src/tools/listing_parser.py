# src/tools/listing_parser.py
"""
Lightweight, deterministic parser for local listing text (V1).

Goal:
  - Extract a few useful, low-regret signals from a plain-text listing file
    without scraping or model calls.
  - Populate ListingInsights for downstream agents and the report header.

Inputs:
  - A .txt file under data/, e.g., data/sample/listing.txt

Outputs:
  - ListingInsights:
      address: best-effort single-line address if found
      amenities: small curated set (e.g., parking, laundry, balcony)
      condition_tags: descriptive condition tags (e.g., "updated kitchen")
      defects: potential negative signals (e.g., "roof leak")
      notes: free-form highlights kept for human review

Heuristics:
  - Regexes for common address formats and integers for unit counts (not stored here,
    schema keeps units inside IncomeModel; we still surface notes if we find them).
  - Keyword-based amenities/condition/defects extraction (case-insensitive).
  - Non-destructive: if a field isn't found, we return a valid object with defaults.

This is intentionally simple (no ML, no web) to keep V1 deterministic and testable.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from src.core.normalize.address import parse_address
from src.schemas.models import ListingInsights

# ----------------------------
# Keyword maps (expandable)
# ----------------------------

_AMENITY_KEYWORDS = {
    "parking": ["parking", "garage", "driveway", "carport"],
    "laundry": ["in-unit laundry", "laundry in unit", "washer", "dryer", "laundry room"],
    "balcony": ["balcony", "patio", "terrace", "deck"],
    "hvac": ["central air", "air conditioning", "a/c", "ac", "forced air"],
    "storage": ["storage", "storage locker", "pantry"],
    "elevator": ["elevator", "lift"],
    "gym": ["gym", "fitness center"],
    "pool": ["pool", "swimming pool"],
    "pets": ["pet friendly", "pets allowed", "cats ok", "dogs ok"],
}

_CONDITION_KEYWORDS = {
    "updated kitchen": ["updated kitchen", "renovated kitchen", "new cabinets", "granite", "quartz", "stainless"],
    "updated bath": ["updated bath", "renovated bath", "new vanity", "tile shower"],
    "new floors": ["new floors", "hardwood", "laminate", "vinyl plank", "refinished floors"],
    "fresh paint": ["fresh paint", "new paint", "repainted"],
    "new roof": ["new roof", "roof replaced", "recent roof"],
    "energy efficient": ["energy efficient", "insulated windows", "double pane"],
}

_DEFECT_KEYWORDS = {
    "roof leak": ["roof leak", "leaking roof"],
    "water damage": ["water damage", "water stain", "flooded basement"],
    "mold": ["mold", "mildew"],
    "foundation crack": ["foundation crack", "structural issue"],
    "old hvac": ["old furnace", "old hvac", "aging boiler"],
    "knob and tube": ["knob and tube", "aluminum wiring"],
}


# ----------------------------
# Address & simple fields
# ----------------------------

# Best-effort address line (very permissive; OK for notes/header)
_ADDRESS_RE = re.compile(
    r"(?P<line>\b\d{1,6}\s+[A-Za-z0-9.'\-]+\s+(Street|St|Road|Rd|Avenue|Ave|Boulevard|Blvd|Drive|Dr|Court|Ct|Lane|Ln)"
    r"(?:\s*,?\s*[A-Za-z .'-]+){0,2}\s*(?:\d{5})?)",
    flags=re.IGNORECASE,
)

# Examples: "4 units", "triplex", "duplex" (we surface as a note)
_UNITS_HINT_RE = re.compile(
    r"\b(?:(\d+)\s+units?)|(duplex|triplex|fourplex|quadplex|quadruplex)\b",
    flags=re.IGNORECASE,
)


# ----------------------------
# Public API
# ----------------------------


def parse_listing_text(path: str) -> ListingInsights:
    """
    Parse a local listing text file into ListingInsights.

    Args:
        path: Path to the .txt listing file.

    Returns:
        ListingInsights with best-effort address, amenities, condition_tags, defects, and notes.

    Notes:
        - File I/O errors propagate to the caller; keep try/except at the call site if needed.
        - This parser is intentionally conservative: if a signal is ambiguous, we prefer not to emit it.
    """
    with open(path, encoding="utf-8") as f:
        text = f.read()
    return parse_listing_string(text)


def parse_listing_string(text: str) -> ListingInsights:
    """
    Parse raw listing text into ListingInsights.

    Args:
        text: Free-form listing description.

    Returns:
        ListingInsights with extracted fields.
    """
    norm = " ".join(text.split())  # collapse whitespace for easier regex

    address_result = parse_address(norm)
    amenities = _extract_keywords(norm, _AMENITY_KEYWORDS)
    condition = _extract_keywords(norm, _CONDITION_KEYWORDS)
    defects = _extract_keywords(norm, _DEFECT_KEYWORDS)
    notes = _compose_notes(norm)

    return ListingInsights(
        address=address_result.address_line if address_result else None,
        amenities=sorted(set(amenities)),
        condition_tags=sorted(set(condition)),
        defects=sorted(set(defects)),
        notes=notes,
    )


# ----------------------------
# Internals
# ----------------------------


def _extract_keywords(text: str, dictionary: Mapping[str, Any]) -> list[str]:
    """
    Return canonical keys for any keyword hit present in text.

    Example:
        dictionary = { "parking": ["parking", "garage"] }
        -> returns ["parking"] if either word is present.
    """
    hits: list[str] = []
    lowered = text.lower()
    for canon, words in dictionary.items():
        for w in words:
            if w.lower() in lowered:
                hits.append(canon)
                break  # only add each canonical once
    return hits


def _compose_notes(text: str) -> list[str]:
    """
    Create a compact list of human-friendly notes from simple hints:
      - Units hints (e.g., 'duplex', '4 units')
      - Any standout phrases we want to preserve verbatim in V1

    Returns:
        A small list of strings (kept short to avoid noisy output).
    """
    notes: list[str] = []

    # Units hint
    m = _UNITS_HINT_RE.search(text)
    if m:
        raw = m.group(0)
        notes.append(raw.strip())

    # You can add more heuristics here if needed (e.g., "as-is sale", "estate sale")
    return notes
