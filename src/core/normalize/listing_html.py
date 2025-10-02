# src/core/normalize/listing_html.py
"""
Deterministic listing normalizer (HTML/XML → ListingNormalized).

Resilient, offline-safe parser that extracts common real-estate signals:
  - beds, baths (handles ½ and 1/2), sqft (supports 1,200 / thin spaces), price, year built
  - parking, laundry type, heating/cooling
Returns a best-effort ListingNormalized; unknowns remain None.
"""

from __future__ import annotations

import re
from pathlib import Path

from bs4 import BeautifulSoup
from pydantic import ValidationError

from src.core.normalize.address import extract_address
from src.schemas.models import ListingNormalized

# ---------- Regex & keyword tables ----------

_BED_RE = re.compile(r"(?i)\b(\d+(?:\.\d+)?)\s*(?:bed(?:room)?s?|bdrm|br)\b")
_BATH_RE = re.compile(r"(?i)\b(\d+(?:\.\d+|½|1/2)?)\s*(?:bath(?:room)?s?|ba)\b")
_SQFT_RE = re.compile(r"(?i)\b(~?\s*(?:\d{1,3}(?:[,\u00A0\u2009\u202F\. ]\d{3})+|\d{3,5}))\s*(?:sq\s?ft|ft²|sqft|square\s?feet)\b")
_PRICE_RE = re.compile(r"(?i)(?:\$|usd|cad)\s*([0-9][0-9,\.]{2,})")
_YEAR_RE = re.compile(r"(?i)\bbuilt\s*(\d{4})\b")

_LAUNDRY_TABLE = {
    "in-unit": "in-unit",
    "in unit": "in-unit",
    "on-site": "on-site",
    "onsite": "on-site",
    "none": "none",
}
_HEAT_KEYS = ["forced air", "baseboard", "radiant", "heat pump", "electric", "gas"]
_COOL_KEYS = ["central air", "ac", "air conditioning", "heat pump"]
_PARKING_RE = re.compile(r"(?i)\b(parking|garage|driveway)\b")

# ---------- Helpers ----------


def _normalize_half_notation(s: str) -> str:
    # 1½ → 1.5 ; "1 / 2" → .5 (so "1 1/2" won’t become "11/2")
    s = re.sub(r"\s*½", "½", s).replace("½", ".5")
    return re.sub(r"\s*1\s*/\s*2\s*", ".5", s)


def _clean_num(text: str) -> float | None:
    try:
        t = text.replace("$", "").lstrip("~").strip()
        # Remove common thousand groupings (comma, spaces incl. NBSP/thin, dot-as-thousands)
        t = t.replace(",", "").replace(" ", "").replace("\u00a0", "").replace("\u2009", "").replace("\u202f", "")
        t = re.sub(r"\.(?=\d{3}\b)", "", t)  # 1.200 → 1200
        return float(t)
    except Exception:
        return None


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

    bds, bas, sqft_i, prc, yr = _extract_common(text, notes)

    # Best-effort address from flattened text
    addr = extract_address(text)

    title = soup.title.string.strip() if soup.title and soup.title.string else None
    lt = text.lower()
    laundry = next((v for k, v in _LAUNDRY_TABLE.items() if k in lt), None)
    heating = next((k for k in _HEAT_KEYS if k in lt), None)
    cooling = next((k for k in _COOL_KEYS if k in lt), None)
    parking = bool(_PARKING_RE.search(text))

    try:
        return ListingNormalized(
            title=title or None,
            address=addr,
            price=prc,
            bedrooms=bds,
            bathrooms=bas,
            sqft=sqft_i,
            year_built=yr,
            parking=parking if parking else None,
            laundry=laundry,
            heating=heating,
            cooling=cooling,
            notes="; ".join(notes) if notes else None,
        )
    except ValidationError:
        # Partial dict fallback
        data = {
            "title": title or None,
            "price": prc,
            "bedrooms": bds,
            "bathrooms": bas,
            "sqft": sqft_i,
            "year_built": yr,
            "parking": parking or None,
            "laundry": laundry,
            "heating": heating,
            "cooling": cooling,
            "notes": "; ".join(notes) if notes else None,
        }
        return ListingNormalized.model_validate({k: v for k, v in data.items() if v is not None})
