# src/core/normalize/address.py

from __future__ import annotations

import re
from re import Match
from typing import Literal

import usaddress
from bs4 import BeautifulSoup

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
# Street line pattern (Retained for Civic Number Detection and Fallback)
# ----------------------------
_STREET_TYPES = (
    "Street|St|Road|Rd|Avenue|Ave|Boulevard|Blvd|Drive|Dr|Court|Ct|Lane|Ln|Way|Place|Pl|Terrace|Ter|Trl|"
    "Parkway|Pkwy|Highway|Hwy|Square|Sq|Circle|Cir|Crescent|Cres|Close|Alley|Aly"
)
_DIRECTIONALS = r"(?:N|S|E|W|NE|NW|SE|SW)\b"

# We use a simpler regex here specifically to find the start of a civic number for anchoring.
_CIVIC_RE = re.compile(r"\b(?P<civic_number>\d{1,6})(?:\s*[-\/]\s*[A-Za-z0-9#-]+)?\b")

_STREET_RE = re.compile(
    rf"""
    (?P<line>
        \b
        # Optional unit/suite number for formats like "601 - 1111"
        (?:(?P<unit_suite>[A-Za-z0-9#-]+)\s*[-\/]\s*)?

        (?P<house_number>\d{{1,6}})          # house number
        \s+
        (?P<street_name>[A-Za-z0-9.'\-]+(?:\s+[A-Za-z0-9.'\-]+)*)
        \s+
        (?:{_STREET_TYPES})\.?\b            # CRITICAL: Added \b to enforce word boundary
        (?:\s+{_DIRECTIONALS})?             # optional directional
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

CountryHint = Literal["CA", "US", "UK", "NL", "EU"]

# ----------------------------
# US/CA state/province patterns
# ----------------------------
_US_CA_STATE_PROVINCE_CODES = (
    "AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|"
    "MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|"
    "AS|DC|FM|GU|MH|MP|PR|PW|VI|"  # US Territories/Districts
    "AB|BC|MB|NB|NL|NS|NT|NU|ON|PE|QC|SK|YT"  # Canada
)

# src/core/normalize/address.py (Near other constants)

_STATE_PROVINCE_NAME_TO_CODE = {
    # --------------------
    # UNITED STATES (US)
    # --------------------
    "ALABAMA": "AL",
    "ALASKA": "AK",
    "ARIZONA": "AZ",
    "ARKANSAS": "AR",
    "CALIFORNIA": "CA",
    "COLORADO": "CO",
    "CONNECTICUT": "CT",
    "DELAWARE": "DE",
    "FLORIDA": "FL",
    "GEORGIA": "GA",
    "HAWAII": "HI",
    "IDAHO": "ID",
    "ILLINOIS": "IL",
    "INDIANA": "IN",
    "IOWA": "IA",
    "KANSAS": "KS",
    "KENTUCKY": "KY",
    "LOUISIANA": "LA",
    "MAINE": "ME",
    "MARYLAND": "MD",
    "MASSACHUSETTS": "MA",
    "MICHIGAN": "MI",
    "MINNESOTA": "MN",
    "MISSISSIPPI": "MS",
    "MISSOURI": "MO",
    "MONTANA": "MT",
    "NEBRASKA": "NE",
    "NEVADA": "NV",
    "NEW HAMPSHIRE": "NH",
    "NEW JERSEY": "NJ",
    "NEW MEXICO": "NM",
    "NEW YORK": "NY",
    "NORTH CAROLINA": "NC",
    "NORTH DAKOTA": "ND",
    "OHIO": "OH",
    "OKLAHOMA": "OK",
    "OREGON": "OR",
    "PENNSYLVANIA": "PA",
    "RHODE ISLAND": "RI",
    "SOUTH CAROLINA": "SC",
    "SOUTH DAKOTA": "SD",
    "TENNESSEE": "TN",
    "TEXAS": "TX",
    "UTAH": "UT",
    "VERMONT": "VT",
    "VIRGINIA": "VA",
    "WASHINGTON": "WA",
    "WEST VIRGINIA": "WV",
    "WISCONSIN": "WI",
    "WYOMING": "WY",
    # US Territories/Districts
    "DISTRICT OF COLUMBIA": "DC",
    "PUERTO RICO": "PR",
    "AMERICAN SAMOA": "AS",
    "GUAM": "GU",
    "MARSHALL ISLANDS": "MH",
    "NORTHERN MARIANA ISLANDS": "MP",
    "VIRGIN ISLANDS": "VI",
    # --------------------
    # CANADA (CA)
    # --------------------
    "ALBERTA": "AB",
    "BRITISH COLUMBIA": "BC",
    "MANITOBA": "MB",
    "NEW BRUNSWICK": "NB",
    "NOVA SCOTIA": "NS",
    "NEWFOUNDLAND AND LABRADOR": "NL",
    "ONTARIO": "ON",
    "PRINCE EDWARD ISLAND": "PE",
    "QUEBEC": "QC",
    "QUÉBEC": "QC",  # French variant
    "SASKATCHEWAN": "SK",
    "NORTHWEST TERRITORIES": "NT",
    "NUNAVUT": "NU",
    "YUKON": "YT",
}

_STATE_PROVINCE_CODES_SET: set[str] = set(_US_CA_STATE_PROVINCE_CODES.split("|"))

_PUNCT_STRIP_RE = re.compile(r"[,\.\-;:()\[\]{}]")


def _tokenize_upper(s: str) -> list[str]:
    # Split on whitespace, strip lightweight punctuation, uppercase
    out: list[str] = []
    for raw in s.split():
        tok = _PUNCT_STRIP_RE.sub("", raw).strip().upper()
        if tok:
            out.append(tok)
    return out


def _choose_state_province(candidate: str | None, search_space: str) -> str | None:
    """
    Prefer a 2-letter code if present; otherwise map a full name to its code.
    Search order:
      1) tokens from candidate (if any)
      2) tokens from the broader search space (blob/scoped_blob)
      3) regex match of any full name in the broader search space
    """
    # 1) Try tokens from candidate first (most targeted)
    if candidate:
        for tok in _tokenize_upper(candidate):
            if tok in _STATE_PROVINCE_CODES_SET:
                return tok

    # 2) Then scan tokens from the broader text
    for tok in _tokenize_upper(search_space):
        if tok in _STATE_PROVINCE_CODES_SET:
            return tok

    # 3) Finally, look for full names (multi-word handled) in the broader text
    #    Iterate names by descending length to prefer "NEW BRUNSWICK" over a stray "NEW"
    for name in sorted(_STATE_PROVINCE_NAME_TO_CODE.keys(), key=len, reverse=True):
        # Word-boundary regex, case-insensitive, accepts accents already present in the dict (e.g., QUÉBEC)
        if re.search(rf"\b{name}\b", search_space, flags=re.IGNORECASE):
            return _STATE_PROVINCE_NAME_TO_CODE[name]

    # If nothing found, return a cleaned 2-letter candidate if it already looks like a code
    if candidate:
        cand = candidate.strip(" ,.-").upper()
        if cand in _STATE_PROVINCE_CODES_SET:
            return cand

    return None


# ----------------------------
# Public API
# ----------------------------


def extract_address(text: str, soup: BeautifulSoup | None = None) -> AddressResult | None:
    """
    Backwards-compatible single-line address extractor.
    """
    return parse_address(text=text, soup=soup)


def parse_address(text: str | None, soup: BeautifulSoup | None = None) -> AddressResult | None:
    """
    Parse a possibly multi-line blob for a best-effort street line, postal/ZIP,
    and structured components.

    Strategy:
      1. Extract **targeted HTML data** (High Confidence Target) separately.
      2. Normalize raw input text into 'blob'.
      3. **Unified Anchor-Based Logic:** Find anchors (postal/civic) and use them to define the search scope.
    """
    if text is None and soup is None:
        return None

    # Step 1: Extract targeted HTML data (High Confidence Target)
    targeted_text = _extract_address_targeted(soup) if soup else None

    # Step 2: Normalize raw input text into 'blob'
    blob = text or ""

    blob = blob.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    blob = re.sub(r"\s{2,}", " ", blob).strip()

    if not blob:
        if targeted_text:
            blob = targeted_text
        else:
            return None

    # --- UNIFIED ANCHOR-BASED LOGIC (Find Anchors) ---

    # 2a. Find Postal Anchor (End Anchor)
    postal_code, country, pidx = _detect_postal(blob)

    # If no postal code is found, we cannot reliably anchor.
    if postal_code is None or pidx is None:
        return None

    # 2b. Find Civic Anchor (Start Anchor)
    civic_match = _detect_civic_number(blob)

    # If no civic number, we start the scope at the beginning of the blob.
    civic_idx = civic_match.start() if civic_match else 0

    # 2c. Define Scoped Blob for Parsing
    postal_end_idx = pidx + len(postal_code)

    # Scope: From the start of the civic number/blob to slightly past the end of the postal code
    scoped_blob = blob[civic_idx : postal_end_idx + 10]

    # 3. Attempt NLP Parsing (US/CA only) to get the best ADDRESS LINE
    is_us_ca_postal = country in {"US", "CA"}

    postal_code = postal_code.replace(" ", "")

    # Predeclare to satisfy mypy across branches
    street_line: str | None = None
    civic_number: str | None = None
    unit_suite: str | None = None
    city: str | None = None
    state_province: str | None = None

    if is_us_ca_postal:
        street_line, civic_number, unit_suite, city, state_province = _parse_with_usaddress_components(scoped_blob)
    else:
        # 5. Final Fallback: Use Regex on the Scoped Blob (or full blob if no civic anchor)

        # Re-run the detailed street regex on the scoped blob

        # Note: Using the complex _STREET_RE here for fine-grained component capture
        street_iter = list(_STREET_RE.finditer(scoped_blob))

        if street_iter:
            # The best match is simply the first, highest-confidence one in the clean, scoped text
            best_match = street_iter[0]

            # Extract components from the match
            street_line = _clean_line(best_match.group("line"), postal_code)
            civic_number = best_match.group("house_number")
            unit_suite = best_match.group("unit_suite") or None

        # City/State extraction relies on patterns near the postal code (still running on original full blob for context)
        if country in {"US", "CA"} and postal_code:
            pc_esc = re.escape(postal_code)
            state_province_re = rf"({_US_CA_STATE_PROVINCE_CODES})"

            patterns = [
                rf"\b([A-Za-z .'\-]+?),\s*{state_province_re}\s*{pc_esc}\b",
                rf"\b([A-Za-z .'\-]+)\s+{state_province_re}\s*{pc_esc}\b",
            ]
            for pat in patterns:
                m = re.search(pat, scoped_blob)
                if m:
                    city = m.group(1).strip(" ,")
                    state_province = m.group(2).upper()
                    break

    # --- Clean / detect state or province ---
    if state_province:
        state_province = _choose_state_province(state_province, scoped_blob)

        # Final whitespace / punctuation cleanup
        if isinstance(state_province, str):
            state_province = state_province.strip(" ,.-")
        else:
            state_province = None

    # Final check
    if not (street_line or postal_code or city):
        return None

    return AddressResult(
        address_line=street_line,
        city=city,
        civic_number=civic_number,
        unit_suite=unit_suite,
        state_province=state_province,
        postal_code=postal_code,
        country_hint=country,
    )


# ----------------------------
# Internals - NLP Helpers
# ----------------------------

# The set of labels that constitute the street line (house number + street name + unit)
_STREET_RECONSTRUCTION_LABELS = {
    "AddressNumber",
    "AddressNumberSuffix",
    "StreetNamePreDirectional",
    "StreetName",
    "StreetNamePreType",
    "StreetNamePostType",
    "StreetNamePostDirectional",
    "OccupancyType",
    "OccupancyIdentifier",
    "SubaddressType",
    "SubaddressIdentifier",
}


def _reconstruct_street_line_from_tokens(parsed_list: list[tuple[str, str]]) -> str | None:
    """
    Reconstructs a clean street line by iterating through the ordered token list
    and only including tokens corresponding to street/house/unit components.
    """
    street_parts = []

    for token, label in parsed_list:
        if label in _STREET_RECONSTRUCTION_LABELS:
            street_parts.append(token)
        elif label in {"PlaceName", "StateName", "StateAbbreviation", "ZipCode", "Recipient", "CountryName"}:
            # Stop once we hit location/junk data, as the street line is almost always before this.
            break

    # Final check: Must contain at least a number and a word to be considered a street
    if street_parts and re.search(r"\d", " ".join(street_parts)) and re.search(r"[A-Za-z]", " ".join(street_parts)):
        return _clean_space(" ".join(street_parts))

    return None


def _parse_with_usaddress_components(blob: str) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    """
    Attempt to parse the address using usaddress.
    Returns a tuple containing (street_line, civic_number, unit_suite, city, state_province).
    """

    try:
        # Use parse() to avoid the RepeatedLabelError. Returns list of (token, label).
        parsed_list = usaddress.parse(blob)

        # Manually consolidate tokens and build labeled_data, prioritizing first occurrence
        # and correctly combining sequential tokens for multi-word components.
        labeled_data = {}
        critical_labels = {
            "AddressNumber",
            "OccupancyIdentifier",
            "SubaddressIdentifier",
            "PlaceName",
            "StateName",
            "StateAbbreviation",
            "ZipCode",
        }

        # --- Token Consolidation Logic ---
        consolidated_tokens = []
        current_label = None
        current_group = []

        for token, label in parsed_list:
            # Check for consolidation condition: sequential tokens sharing the same label
            if label == current_label:
                current_group.append(token)
            else:
                # If the label changes, finalize the previous group
                if current_label and current_label not in labeled_data and current_label in critical_labels:
                    labeled_data[current_label] = _clean_space(" ".join(current_group))

                # Start a new group
                current_label = label
                current_group = [token]

            consolidated_tokens.append((token, label))

        # Finalize the last group after the loop ends
        if current_label and current_label not in labeled_data and current_label in critical_labels:
            labeled_data[current_label] = _clean_space(" ".join(current_group))

        # --- Check Validity and Extract ---

        # If no new core components were found, return empty tuple
        if not (labeled_data.get("AddressNumber") or labeled_data.get("ZipCode")):
            return None, None, None, None, None

        # Extract components from the consolidated data
        street_line = _reconstruct_street_line_from_tokens(parsed_list)
        civic_number = labeled_data.get("AddressNumber")
        unit_suite = labeled_data.get("OccupancyIdentifier") or labeled_data.get("SubaddressIdentifier")

        # Ensure 'city' is extracted, using the cleaned, consolidated PlaceName
        city_raw = labeled_data.get("PlaceName")
        city = city_raw.strip(", ") if city_raw else None

        # Ensure 'state_province' is extracted, using the cleaned, consolidated StateName/StateAbbreviation
        state_province = labeled_data.get("StateAbbreviation") or labeled_data.get("StateName")

        return street_line, civic_number, unit_suite, city, state_province

    except Exception:
        # If parsing fails, return None for all 5 components.
        return None, None, None, None, None


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


def _detect_civic_number(text: str) -> Match[str] | None:
    """
    Detects the first instance of a civic number (including potential unit/suite prefix) for anchoring.
    """
    # Use the simplified civic regex created for this purpose
    m = _CIVIC_RE.search(text)
    return m


def _detect_postal(text: str) -> tuple[str | None, CountryHint | None, int | None]:
    # Canada
    m = _CA_POSTAL_RE.search(text)
    if m:
        code = f"{m.group(1).upper()} {m.group(2).upper()}"
        return code, "CA", m.start()
    # UK
    m = _UK_POSTCODE_RE.search(text.upper())
    if m:
        code = f"{m.group(1)} {m.group(2)}".upper()
        return code, "UK", m.start()
    # NL
    m = _NL_POSTCODE_RE.search(text.upper())
    if m:
        code = f"{m.group(1)} {m.group(2)}".upper()
        return code, "NL", m.start()
    # US
    m = _US_ZIP_RE.search(text)
    if m:
        code = m.group(1) + (f"-{m.group(2)}" if m.group(2) else "")
        return code, "US", m.start()
    # EU generic
    m = _EU_5DIGIT_RE.search(text)
    if m:
        return m.group(1), "EU", m.start()
    return None, None, None


def _clean_space(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip(" ,;|\n\t")


def _join_tokens(*parts: str) -> str | None:
    toks = [p for p in (p.strip(" ,") for p in parts) if p]
    if not toks:
        return None
    out = _clean_space(", ".join(toks))
    # Heuristic: must contain at least a street-ish signal or postal/zip to be useful
    if (
        not re.search(r"\d", out)
        and not re.search(r"\b[A-Z]\d[A-Z]\s?\d[A-Z]\d\b", out, re.I)
        and not re.search(r"\b\d{5}(-\d{4})?\b", out)
    ):
        # allow cases like "Some Building, City" if clearly labeled as address in DOM
        return out if len(out) >= 8 else None
    return out


def _extract_address_from_schema(soup: BeautifulSoup) -> str | None:
    # itemtype PostalAddress
    for node in soup.select('[itemtype*="schema.org/PostalAddress" i]'):
        street = node.select_one('[itemprop="streetAddress" i]')
        city = node.select_one('[itemprop="addressLocality" i]')
        region = node.select_one('[itemprop="addressRegion" i]')
        postal = node.select_one('[itemprop="postalCode" i]')
        country = node.select_one('[itemprop="addressCountry" i]')
        return _join_tokens(
            street.get_text(" ", strip=True) if street else "",
            city.get_text(" ", strip=True) if city else "",
            region.get_text(" ", strip=True) if region else "",
            postal.get_text(" ", strip=True) if postal else "",
            country.get_text(" ", strip=True) if country else "",
        )

    # itemprop="address" that contains a PostalAddress, or plain text
    for node in soup.select('[itemprop="address" i]'):
        # nested PostalAddress?
        nested = node.select_one('[itemtype*="schema.org/PostalAddress" i]')
        if nested:
            street = nested.select_one('[itemprop="streetAddress" i]')
            city = nested.select_one('[itemprop="addressLocality" i]')
            region = nested.select_one('[itemprop="addressRegion" i]')
            postal = nested.select_one('[itemprop="postalCode" i]')
            country = nested.select_one('[itemprop="addressCountry" i]')
            return _join_tokens(
                street.get_text(" ", strip=True) if street else "",
                city.get_text(" ", strip=True) if city else "",
                region.get_text(" ", strip=True) if region else "",
                postal.get_text(" ", strip=True) if postal else "",
                country.get_text(" ", strip=True) if country else "",
            )
        # plain text payload
        txt = node.get_text(" ", strip=True)
        if txt and len(txt) >= 8:
            return _clean_space(txt)
    return None


def _extract_address_from_meta(soup: BeautifulSoup) -> str | None:
    # Some sites expose fragments in meta tags (OpenGraph or custom)
    def meta(*names: str) -> str:
        sel = ",".join([f'meta[name="{n}"], meta[property="{n}"]' for n in names])
        m = soup.select_one(sel)

        if not m:
            return ""

        val = m.get("content", "")

        if isinstance(val, list):
            val = " ".join(x for x in val if isinstance(x, str))

        return (val or "").strip()

    street = meta("og:street-address", "street-address", "address")
    city = meta("og:locality", "addressLocality", "locality", "city")
    region = meta("og:region", "addressRegion", "region", "state")
    postal = meta("og:postal-code", "postal-code", "postalCode", "zip")
    country = meta("og:country-name", "addressCountry", "country")

    return _join_tokens(street, city, region, postal, country)


def _extract_address_from_dom_hints(soup: BeautifulSoup) -> str | None:
    # Elements whose id/class suggest "address" or "location"
    hint_sel = [
        '[id*="address" i]',
        '[class*="address" i]',
        '[id*="location" i]',
        '[class*="location" i]',
        '[id*="map" i]',
        '[class*="map" i]',
    ]
    for node in soup.select(", ".join(hint_sel)):
        txt = node.get_text(" ", strip=True)
        if txt and len(txt) >= 8:
            # try to trim excessive map/cta text
            txt = re.sub(r"(?i)\b(get directions|view map|map)\b.*$", "", txt).strip()
            cand = _clean_space(txt)
            if cand:
                return cand
    # Map links (Google/Apple)
    for a in soup.select('a[href*="google.com/maps" i], a[href*="maps.apple.com" i], a[href*="/maps" i]'):
        # Use link text if looks like an address, else the surrounding container
        txt = a.get_text(" ", strip=True)
        if txt and len(txt) >= 8 and not re.search(r"(?i)\b(map|directions)\b", txt):
            return _clean_space(txt)
        parent = a.find_parent()
        if parent:
            ptxt = parent.get_text(" ", strip=True)
            if ptxt and len(ptxt) >= 8:
                return _clean_space(ptxt)
    return None


def _extract_address_targeted(soup: BeautifulSoup) -> str | None:
    # Priority: schema → meta → DOM hints
    return _extract_address_from_schema(soup) or _extract_address_from_meta(soup) or _extract_address_from_dom_hints(soup)
