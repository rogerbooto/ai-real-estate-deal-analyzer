# src/core/normalize/title.py
from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any, Literal

from bs4 import BeautifulSoup

from src.schemas.labels import (
    _BATH_INLINE_RE,
    _BATH_LABEL_RE,
    _BED_INLINE_RE,
    _BED_LABEL_RE,
    _clean_num,
)
from src.schemas.models import AddressResult

Booster = Literal["html", "text", "user"]

# --- Boilerplate / marketing tails we never want in titles ---
# kill CTA fragments like "... unit download", "apply now", "view photos", etc.
_BOILERPLATE_TAIL_RE = re.compile(r"(?i)\b(download|apply now|contact agent|view (?:map|photos?)|schedule (?:a )?tour|get directions)\b.*$")

# Remove obvious price fragments from candidate titles
_PRICE_RE = re.compile(r"(?i)(?:\$|usd|cad)\s*[0-9][0-9,\.]{2,}")

# Kill double/multiple spaces and stray punctuation
_SPACE_CLEAN_RE = re.compile(r"\s{2,}")

# Looks like a streety thing: “123 Main”, “47 Perrot”, etc.
_ADDRESSISH_RE = re.compile(r"\b\d{1,6}\s+[A-Za-z]")

# These are too generic to be a good title on their own
_GENERIC_HOST_TOKENS = ("realtor.ca", "mls®", "real estate", "for sale by owner")


def _attr_as_str(v: Any) -> str | None:
    """
    BeautifulSoup attribute values can be str | list[str] | None.
    Return a single string (first item for lists) or None.
    """
    if isinstance(v, str):
        return v
    if isinstance(v, Sequence) and not isinstance(v, (str | bytes)) and v and isinstance(v[0], str):
        return v[0]
    return None


def _clean_candidate(s: str) -> str:
    s = _BOILERPLATE_TAIL_RE.sub("", s)
    s = _PRICE_RE.sub("", s)
    s = s.strip(" ,;|-–—\n\t")
    s = _SPACE_CLEAN_RE.sub(" ", s)
    return s


def _looks_like_listing_title(s: str) -> bool:
    s_low = s.lower()
    if any(tok in s_low for tok in _GENERIC_HOST_TOKENS):
        return False
    # Must have some letters, avoid single words, and avoid being pure numbers
    if not any(ch.isalpha() for ch in s):
        return False
    if len(s.strip()) < 6:
        return False
    # Prefer something that either looks address-ish or at least two words
    return bool(_ADDRESSISH_RE.search(s) or len(s.strip().split()) >= 2)


def _meta_title(soup: BeautifulSoup | None) -> tuple[str | None, Booster | None]:
    if not soup:
        return None, None
    meta = soup.select_one('meta[property="og:title"], meta[name="og:title"]')
    if meta:
        title_text = _attr_as_str(meta.get("content"))

        if title_text:
            cand = _clean_candidate(title_text)

        if _looks_like_listing_title(cand):
            return cand, "html"
    if soup.title and soup.title.string:
        cand = _clean_candidate(soup.title.string)
        if _looks_like_listing_title(cand):
            return cand, "html"
    return None, None


def _derive_from_bed_bath_text(blob: str, city: str | None) -> tuple[str | None, float | None]:
    bed_m = _BED_LABEL_RE.search(blob) or _BED_INLINE_RE.search(blob)
    bath_m = _BATH_LABEL_RE.search(blob) or _BATH_INLINE_RE.search(blob)
    if not (bed_m and bath_m):
        return None, None

    b = _clean_num(bed_m.group(1))
    a = _clean_num(bath_m.group(1))
    if b is None or a is None:
        return None, None

    title_core = f"{int(b) if b.is_integer() else b}BR/{int(a) if a.is_integer() else a}BA"
    return (f"{title_core} — {city}" if city else title_core, 0.65)


def _first_readable_line(blob: str) -> str | None:
    for raw in blob.splitlines() if blob else []:
        ln = _clean_candidate(raw.strip())
        if len(ln) >= 12 and any(ch.isalpha() for ch in ln) and _looks_like_listing_title(ln):
            return ln
    return None


def infer_title(
    *, text: str | None, soup: BeautifulSoup | None, addr: AddressResult | None
) -> tuple[str | None, float, Literal["html", "text", "user"] | None, list[str]]:
    candidates: list[str] = []

    mt, src = _meta_title(soup)
    if mt and _looks_like_listing_title(mt):
        candidates.append(mt)

    if addr and addr.address_line:
        candidates.append(f"{addr.address_line}, {addr.city}" if addr.city else addr.address_line)

    blob = text or ""
    bed_m = _BED_LABEL_RE.search(blob) or _BED_INLINE_RE.search(blob)
    bath_m = _BATH_LABEL_RE.search(blob) or _BATH_INLINE_RE.search(blob)
    if bed_m and bath_m and addr and addr.city:
        num_bed = _clean_num(bed_m.group(1))
        num_bath = _clean_num(bath_m.group(1))
        candidates.append(f"{num_bed}BR/{num_bath}BA — {addr.city}")

    for line in blob.splitlines() if blob else []:
        ln = line.strip()
        if len(ln) >= 12 and any(ch.isalpha() for ch in ln):
            candidates.append(ln)
            break

    # --- Choose best candidate
    if candidates:
        chosen = candidates[0]
        if src == "html" and chosen == mt:
            conf = 1.0
        elif addr and addr.address_line and chosen.startswith(addr.address_line):
            conf = 0.9
        else:
            conf = 0.6
        return chosen, conf, (src or "text"), candidates

    # --- Explicit fallback when nothing works
    return None, 0.0, None, []
