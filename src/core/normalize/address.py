# src/core/normalize/address.py

from __future__ import annotations

import re
from re import Match
from typing import Literal

from src.schemas.models import AddressResult

# ----------------------------
# Postal / ZIP patterns
# ----------------------------
_CA_POSTAL_RE = re.compile(
    r"\b([ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTV-Z])\s?(\d[ABCEGHJ-NPRSTV-Z]\d)\b",
    re.IGNORECASE,
)
_UK_POSTCODE_RE = re.compile(
    r"\b([A-Z]{1,2}\d[A-Z\d]?)\s*(\d[ABD-HJLNP-UW-Z]{2})\b",
    re.IGNORECASE,
)
_NL_POSTCODE_RE = re.compile(r"\b(\d{4})\s*([A-Z]{2})\b", re.IGNORECASE)
_US_ZIP_RE = re.compile(r"\b(\d{5})(?:-(\d{4}))?\b")
_EU_5DIGIT_RE = re.compile(r"\b(\d{5})\b")

# ----------------------------
# Street line pattern
# ----------------------------
_STREET_TYPES = (
    "Street|St|Road|Rd|Avenue|Ave|Boulevard|Blvd|Drive|Dr|Court|Ct|Lane|Ln|Way|Place|Pl|Terrace|Ter|Trail|Trl|"
    "Parkway|Pkwy|Highway|Hwy|Square|Sq|Circle|Cir|Crescent|Cres|Close|Alley|Aly"
)
_DIRECTIONALS = r"(?:N|S|E|W|NE|NW|SE|SW)\b"
_STREET_RE = re.compile(
    rf"""
    (?P<line>
        \b
        \d{{1,6}}                              # house number
        \s+
        [A-Za-z0-9.'\-]+(?:\s+[A-Za-z0-9.'\-]+)*   # street name (1+ tokens)
        \s+
        (?:{_STREET_TYPES})\.?                  # street type
        (?:\s+{_DIRECTIONALS})?                 # optional directional
        (?:\s*,?\s*[A-Za-z .'\-]+){{0,3}}       # optional city/region tokens
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

CountryHint = Literal["CA", "US", "UK", "NL", "EU"]

# ----------------------------
# Public API
# ----------------------------


def extract_address(text: str) -> str | None:
    """
    Backwards-compatible single-line address extractor.

    Builds a single line by joining the available parts from parse_address()
    in this order: street line, postal/ZIP, country hint. Any missing part
    is simply omitted (no '<unknown*>' placeholders). Returns None if all
    parts are missing.
    """
    res = parse_address(text)
    parts = [res.address_line or "", res.postal_code or "", res.country_hint or ""]
    line = ", ".join(p for p in parts if p.strip())
    return line or None


def parse_address(text: str) -> AddressResult:
    """
    Parse a possibly multi-line blob for a best-effort street line and postal/ZIP.

    Strategy:
      1) Normalize whitespace.
      2) Detect postal/ZIP by prioritized regexes (CA → UK → NL → US → EU 5-digit).
      3) Detect a street-like line via a permissive street regex.
      4) Return structured AddressResult (empty strings for missing parts are fine).
    """
    blob = (text or "").replace("\r", " ").replace("\n", " ").replace("\t", " ")
    blob = re.sub(r"\s{2,}", " ", blob).strip()

    postal_code, country_hint = _detect_postal(blob)

    street_line = None
    street_iter = list(_STREET_RE.finditer(blob))
    if street_iter:
        if postal_code:
            pidx = _find_postal_index(blob, postal_code)
            if pidx is not None:
                street_line = _closest_street_to_index(street_iter, pidx)
            else:
                street_line = _clean_line(street_iter[0].group("line"))
        else:
            street_line = _clean_line(street_iter[0].group("line"))

    # Allow empty strings for any missing piece
    return AddressResult(
        address_line=street_line or "",
        postal_code=postal_code or "",
        country_hint=country_hint or None,
    )


# ----------------------------
# Internals
# ----------------------------


def _clean_line(line: str, postal_code: str | None = None) -> str:
    """
    Normalize a candidate street line:
      - Strip commas/extra spaces
      - Remove dangling tokens that duplicate or precede the postal code
    """
    line = line.strip(" ,")
    line = re.sub(r"\s{2,}", " ", line)
    line = re.sub(r"\s+,", ",", line)

    if postal_code:
        # If postal appears inside line, cut everything after it
        idx = line.upper().find(postal_code.upper())
        if idx != -1:
            line = line[:idx].rstrip(" ,")

    # Drop trailing single letters (like stray 'E')
    line = re.sub(r",?\s+[A-Z]\b$", "", line, flags=re.IGNORECASE)

    return line


def _find_postal_index(text: str, code: str) -> int | None:
    m = re.search(re.escape(code), text, flags=re.IGNORECASE)
    return m.start() if m else None


def _closest_street_to_index(matches: list[Match[str]], idx: int) -> str | None:
    if not matches:
        return None
    best = min(matches, key=lambda m: abs(m.start() - idx))
    return _clean_line(best.group("line"))


def _detect_postal(text: str) -> tuple[str | None, CountryHint | None]:
    # Canada
    m = _CA_POSTAL_RE.search(text)
    if m:
        code = f"{m.group(1).upper()} {m.group(2).upper()}"
        return code, "CA"
    # UK
    m = _UK_POSTCODE_RE.search(text.upper())
    if m:
        code = f"{m.group(1)} {m.group(2)}".upper()
        return code, "UK"
    # NL
    m = _NL_POSTCODE_RE.search(text.upper())
    if m:
        code = f"{m.group(1)} {m.group(2)}".upper()
        return code, "NL"
    # US
    m = _US_ZIP_RE.search(text)
    if m:
        code = m.group(1) + (f"-{m.group(2)}" if m.group(2) else "")
        return code, "US"
    # EU generic
    m = _EU_5DIGIT_RE.search(text)
    if m:
        return m.group(1), "EU"
    return None, None
