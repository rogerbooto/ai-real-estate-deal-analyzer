# src/schemas/labels.py
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from enum import Enum
from re import Pattern
from typing import TypeVar

T = TypeVar("T", bound=Enum)

# =========================
# Canonical label enums
# =========================


class RoomType(str, Enum):
    kitchen = "kitchen"
    bathroom = "bathroom"
    bedroom = "bedroom"
    living_room = "living_room"
    exterior = "exterior"
    garage = "garage"
    laundry = "laundry"
    patio = "patio"
    balcony = "balcony"


class MaterialTag(str, Enum):
    stainless_appliances = "stainless_appliances"
    kitchen_island = "kitchen_island"


class AmenityLabel(str, Enum):
    # Boolean surface expected by PhotoInsights:
    in_unit_laundry = "in_unit_laundry"
    dishwasher = "dishwasher"
    stainless_kitchen = "stainless_kitchen"  # surfaced from MaterialTag.stainless_appliances
    kitchen_island = "kitchen_island"
    balcony = "balcony"
    patio = "patio"
    fireplace = "fireplace"
    parking = "parking"  # aggregate: true if any specific parking amenity present
    fenced_yard = "fenced_yard"

    # Specific detections (can also be shown directly when needed):
    ev_charger = "ev_charger"
    parking_garage = "parking_garage"
    parking_driveway = "parking_driveway"
    street_parking = "street_parking"


class DefectLabel(str, Enum):
    """
    Canonical defect labels recognized by the system.
    These correspond to visual and textual defect categories that may appear
    in listings, inspection notes, or CV detections.
    """

    # --- Moisture / water issues ---
    mold_suspected = "mold_suspected"
    water_leak_suspected = "water_leak_suspected"

    # --- Structural / foundation ---
    foundation_crack = "foundation_crack"
    wall_crack = "wall_crack"

    # --- Surfaces / paint / finishes ---
    peeling_paint = "peeling_paint"
    cracked_tile = "cracked_tile"
    dirty_grout = "dirty_grout"
    floor_scratches = "floor_scratches"

    # --- Windows / fixtures / cabinetry ---
    broken_window = "broken_window"
    damaged_cabinet = "damaged_cabinet"
    rust_fixture = "rust_fixture"
    appliance_dent = "appliance_dent"

    # --- Mechanical / electrical ---
    old_hvac = "old_hvac"
    old_wiring = "old_wiring"

    # --- Generic / catch-all ---
    cosmetic_damage = "cosmetic_damage"
    unknown = "unknown"


class ConditionTag(str, Enum):
    renovated_kitchen = "renovated_kitchen"
    updated_bath = "updated_bath"
    well_maintained = "well_maintained"
    new_flooring = "new_flooring"
    # Quality proxies (used as scored “quality_flags” in PhotoInsights):
    natural_light = "natural_light"
    curb_appeal = "curb_appeal"


class ParkingType(str, Enum):
    garage = "garage"
    driveway = "driveway"
    street = "street"
    none = "none"
    unknown = "unknown"


# =========================
# Canonical surfaces/sets
# =========================

PHOTOINSIGHTS_AMENITY_SURFACE: list[AmenityLabel] = [
    AmenityLabel.in_unit_laundry,
    AmenityLabel.dishwasher,
    AmenityLabel.stainless_kitchen,
    AmenityLabel.kitchen_island,
    AmenityLabel.balcony,
    AmenityLabel.patio,
    AmenityLabel.fireplace,
    AmenityLabel.parking,
    AmenityLabel.fenced_yard,
]

MATERIAL_TO_AMENITY_SURFACE = {
    MaterialTag.stainless_appliances: AmenityLabel.stainless_kitchen,
    MaterialTag.kitchen_island: AmenityLabel.kitchen_island,
}

ROOM_COUNT_CANONICAL = {
    RoomType.kitchen: "kitchen",
    RoomType.bathroom: "bath",
    RoomType.bedroom: "bedroom",
    RoomType.living_room: "living",
    RoomType.exterior: "exterior",
    RoomType.garage: "garage",
    RoomType.laundry: "laundry",
    RoomType.patio: "patio",
    RoomType.balcony: "balcony",
}

PARKING_SPECIFIC_AMENITIES = {
    AmenityLabel.parking_garage,
    AmenityLabel.parking_driveway,
    AmenityLabel.street_parking,
}


# =========================
# Alias/token maps (with synonyms)
# Used by filename/text parsing across the app.
# =========================

ROOM_TOKEN_ALIASES = {
    "kitchen": RoomType.kitchen,
    "bath": RoomType.bathroom,
    "bathroom": RoomType.bathroom,
    "bed": RoomType.bedroom,
    "bedroom": RoomType.bedroom,
    "living": RoomType.living_room,
    "living room": RoomType.living_room,
    "exterior": RoomType.exterior,
    "front": RoomType.exterior,
    "garage": RoomType.garage,
    "laundry": RoomType.laundry,
    "patio": RoomType.patio,
    "balcony": RoomType.balcony,
}

MATERIAL_TOKEN_ALIASES = {
    "stainless": MaterialTag.stainless_appliances,
    "stainless steel": MaterialTag.stainless_appliances,
    "ss appliances": MaterialTag.stainless_appliances,
    "island": MaterialTag.kitchen_island,
    "kitchen island": MaterialTag.kitchen_island,
}

# Amenity synonyms (rich)
AMENITY_TOKEN_ALIASES = {
    # direct amenities
    "dishwasher": AmenityLabel.dishwasher,
    "dish washer": AmenityLabel.dishwasher,
    "dw": AmenityLabel.dishwasher,
    "in-unit laundry": AmenityLabel.in_unit_laundry,
    "in unit laundry": AmenityLabel.in_unit_laundry,
    "in suite laundry": AmenityLabel.in_unit_laundry,
    "laundry in unit": AmenityLabel.in_unit_laundry,
    # Multi-unit MLS phrasings that unambiguously mean each unit has its own laundry.
    # Bare "laundry" is deliberately NOT an alias: it may describe a shared/common room.
    "separate laundry": AmenityLabel.in_unit_laundry,
    "private laundry": AmenityLabel.in_unit_laundry,
    "own laundry": AmenityLabel.in_unit_laundry,
    "ensuite laundry": AmenityLabel.in_unit_laundry,
    "en-suite laundry": AmenityLabel.in_unit_laundry,
    "washer/dryer": AmenityLabel.in_unit_laundry,
    "washer and dryer": AmenityLabel.in_unit_laundry,
    "washer & dryer": AmenityLabel.in_unit_laundry,
    "w/d": AmenityLabel.in_unit_laundry,
    "wd": AmenityLabel.in_unit_laundry,
    "balcony": AmenityLabel.balcony,
    "balconies": AmenityLabel.balcony,
    "patio": AmenityLabel.patio,
    "deck": AmenityLabel.patio,  # treat deck as patio for coarse surface
    "fireplace": AmenityLabel.fireplace,
    "gas fireplace": AmenityLabel.fireplace,
    "wood fireplace": AmenityLabel.fireplace,
    "fenced yard": AmenityLabel.fenced_yard,
    "fenced backyard": AmenityLabel.fenced_yard,
    "fenced-in yard": AmenityLabel.fenced_yard,
    # parking family
    "parking": AmenityLabel.parking,
    "garage": AmenityLabel.parking_garage,
    "attached garage": AmenityLabel.parking_garage,
    "detached garage": AmenityLabel.parking_garage,
    "driveway": AmenityLabel.parking_driveway,
    "driveway parking": AmenityLabel.parking_driveway,
    "off-street parking": AmenityLabel.parking_driveway,
    "street parking": AmenityLabel.street_parking,
    "on-street parking": AmenityLabel.street_parking,
    # EV
    "ev charger": AmenityLabel.ev_charger,
    "ev charging": AmenityLabel.ev_charger,
    "level 2 charger": AmenityLabel.ev_charger,
    "tesla charger": AmenityLabel.ev_charger,
    # materials promoted to boolean surface
    "stainless appliances": AmenityLabel.stainless_kitchen,  # direct phrase
    "stainless steel appliances": AmenityLabel.stainless_kitchen,
    "ss kitchen": AmenityLabel.stainless_kitchen,
}

DEFECT_TOKEN_ALIASES = {
    # --- Moisture / water issues ---
    "mold": DefectLabel.mold_suspected,
    "mould": DefectLabel.mold_suspected,  # Canadian/UK spelling
    "black mold": DefectLabel.mold_suspected,
    "mildew": DefectLabel.mold_suspected,
    "leak": DefectLabel.water_leak_suspected,
    "leaking": DefectLabel.water_leak_suspected,
    "water leak": DefectLabel.water_leak_suspected,
    "roof leak": DefectLabel.water_leak_suspected,
    "pipe leak": DefectLabel.water_leak_suspected,
    "leaky faucet": DefectLabel.water_leak_suspected,
    "water stain": DefectLabel.water_leak_suspected,
    "water stains": DefectLabel.water_leak_suspected,
    "water staining": DefectLabel.water_leak_suspected,
    "water damage": DefectLabel.water_leak_suspected,
    "water-damaged": DefectLabel.water_leak_suspected,
    "flooded basement": DefectLabel.water_leak_suspected,
    "moisture damage": DefectLabel.water_leak_suspected,
    "damp": DefectLabel.water_leak_suspected,
    "humidity issue": DefectLabel.water_leak_suspected,
    # --- Structural / foundation ---
    "foundation crack": DefectLabel.foundation_crack,
    "cracked foundation": DefectLabel.foundation_crack,
    "settling": DefectLabel.foundation_crack,
    "structural issue": DefectLabel.foundation_crack,
    "uneven floor": DefectLabel.foundation_crack,
    "sagging floor": DefectLabel.foundation_crack,
    "wall crack": DefectLabel.foundation_crack,
    "cracked wall": DefectLabel.foundation_crack,
    # --- Surfaces / paint / finishes ---
    "peeling paint": DefectLabel.peeling_paint,
    "flaking paint": DefectLabel.peeling_paint,
    "chipped paint": DefectLabel.peeling_paint,
    "stained wall": DefectLabel.peeling_paint,
    "dirty wall": DefectLabel.peeling_paint,
    "faded paint": DefectLabel.peeling_paint,
    "cracked tile": DefectLabel.cracked_tile,
    "broken tile": DefectLabel.cracked_tile,
    "missing tile": DefectLabel.cracked_tile,
    "loose tile": DefectLabel.cracked_tile,
    "damaged grout": DefectLabel.dirty_grout,
    "dirty grout": DefectLabel.dirty_grout,
    "stained grout": DefectLabel.dirty_grout,
    "moldy grout": DefectLabel.dirty_grout,
    # --- Flooring ---
    "scratched floor": DefectLabel.floor_scratches,
    "floor scratches": DefectLabel.floor_scratches,
    "floor scuffs": DefectLabel.floor_scratches,
    "damaged flooring": DefectLabel.floor_scratches,
    "warped floor": DefectLabel.floor_scratches,
    # --- Windows / fixtures / cabinets ---
    "broken window": DefectLabel.broken_window,
    "cracked window": DefectLabel.broken_window,
    "shattered window": DefectLabel.broken_window,
    "foggy window": DefectLabel.broken_window,
    "condensation window": DefectLabel.broken_window,
    "damaged cabinet": DefectLabel.damaged_cabinet,
    "broken cabinet": DefectLabel.damaged_cabinet,
    "cabinet damage": DefectLabel.damaged_cabinet,
    "warped cabinet": DefectLabel.damaged_cabinet,
    "drawer issue": DefectLabel.damaged_cabinet,
    "rust fixture": DefectLabel.rust_fixture,
    "rusty faucet": DefectLabel.rust_fixture,
    "rust stain": DefectLabel.rust_fixture,
    "rust on fixture": DefectLabel.rust_fixture,
    "corrosion": DefectLabel.rust_fixture,
    "appliance dent": DefectLabel.appliance_dent,
    "dented appliance": DefectLabel.appliance_dent,
    "dented fridge": DefectLabel.appliance_dent,
    "scratched appliance": DefectLabel.appliance_dent,
    "appliance scratch": DefectLabel.appliance_dent,
    # --- Electrical / HVAC ---
    "old hvac": DefectLabel.old_hvac,
    "outdated hvac": DefectLabel.old_hvac,
    "old furnace": DefectLabel.old_hvac,
    "aging boiler": DefectLabel.old_hvac,
    "no heat": DefectLabel.old_hvac,
    "hvac issue": DefectLabel.old_hvac,
    "broken ac": DefectLabel.old_hvac,
    "no ac": DefectLabel.old_hvac,
    "knob and tube": DefectLabel.old_wiring,
    "aluminum wiring": DefectLabel.old_wiring,
    "outdated wiring": DefectLabel.old_wiring,
}

# =========================
# HVAC & laundry phrase maps (for listing parsers)
# =========================

# Small, normalized phrase surfaces we want to expose from a single place.
LAUNDRY_PHRASE_MAP = {
    "in-unit": "in-unit",
    "in unit": "in-unit",
    "on-site": "on-site",
    "onsite": "on-site",
    "none": "none",
}

# Keep these as ordered lists so "first match wins" is predictable for detectors below.
HEATING_TOKENS = [
    "forced air",
    "baseboard",
    "radiant",
    "heat pump",
    "electric",
    "gas",
]

COOLING_TOKENS = [
    "central air",
    "ac",
    "air conditioning",
    "heat pump",
]


def detect_heating(text: str) -> str | None:
    """Return the first heating token found in text, or None."""
    s = text.lower()
    for k in HEATING_TOKENS:
        if k in s:
            return k
    return None


def detect_cooling(text: str) -> str | None:
    """Return the first cooling token found in text, or None."""
    s = text.lower()
    for k in COOLING_TOKENS:
        if k in s:
            return k
    return None


# =========================
# Regex compilation
# =========================


def _compile_map(m: Mapping[str, T]) -> list[tuple[Pattern[str], T]]:
    pats: list[tuple[Pattern[str], T]] = []
    # Longer keys first so "street parking" beats "parking"
    for key in sorted(m.keys(), key=len, reverse=True):
        # Escape the key, then make spaces flexible: space|underscore|hyphen (one or more)
        escaped = re.escape(key)
        # Replace escaped spaces with a flexible separator class
        flexible = escaped.replace(r"\ ", r"[ _\-]+")
        # Boundaries: treat only letters/digits as "word" so '_' and '-' are OK as boundaries
        pattern = r"(?<![A-Za-z0-9])" + flexible + r"(?![A-Za-z0-9])"
        pats.append((re.compile(pattern, flags=re.IGNORECASE), m[key]))
    return pats


_ROOM_PATTERNS = _compile_map(ROOM_TOKEN_ALIASES)
_MATERIAL_PATTERNS = _compile_map(MATERIAL_TOKEN_ALIASES)
_AMENITY_PATTERNS = _compile_map(AMENITY_TOKEN_ALIASES)
_DEFECT_PATTERNS = _compile_map(DEFECT_TOKEN_ALIASES)


# =========================
# Normalization helpers
# =========================


def normalize_rooms_from_name(name: str) -> set[RoomType]:
    s = name.lower()
    found: set[RoomType] = set()
    for pat, val in _ROOM_PATTERNS:
        if pat.search(s):
            found.add(val)
    return found


def normalize_materials_from_name(name: str) -> set[MaterialTag]:
    s = name.lower()
    found: set[MaterialTag] = set()
    for pat, val in _MATERIAL_PATTERNS:
        if pat.search(s):
            found.add(val)
    return found


def find_amenities_in_text(text: str) -> dict[AmenityLabel, str]:
    """Amenity labels found in ``text``, each mapped to the literal substring that matched.

    The matched phrase is the only evidence a keyword match has, and throwing it away is why a
    text-derived tag used to be indistinguishable from a model-derived one (see
    ``schemas.models.ObservationProvenance``). ``_AMENITY_PATTERNS`` is ordered longest-alias-first
    and only the first hit per label is kept, so the result is deterministic.
    """
    s = text.lower()
    found: dict[AmenityLabel, str] = {}
    for pat, val in _AMENITY_PATTERNS:
        if val in found:
            continue
        m = pat.search(s)
        if m:
            found[val] = m.group(0)
    return found


def find_defects_in_text(text: str) -> dict[DefectLabel, str]:
    """Defect labels found in ``text``, each mapped to the literal substring that matched.

    See :func:`find_amenities_in_text` for why the matched phrase is retained.
    """
    s = text.lower()
    found: dict[DefectLabel, str] = {}
    for pat, val in _DEFECT_PATTERNS:
        if val in found:
            continue
        m = pat.search(s)
        if m:
            found[val] = m.group(0)
    return found


def normalize_amenities_from_text(text: str) -> set[AmenityLabel]:
    return set(find_amenities_in_text(text))


def normalize_defects_from_text(text: str) -> set[DefectLabel]:
    return set(find_defects_in_text(text))


def materials_to_amenity_surface(materials: Iterable[MaterialTag]) -> set[AmenityLabel]:
    out: set[AmenityLabel] = set()
    for m in materials:
        mapped = MATERIAL_TO_AMENITY_SURFACE.get(m)
        if mapped:
            out.add(mapped)
    return out


def has_any_parking_specific(amenities: Iterable[AmenityLabel]) -> bool:
    s = set(amenities)
    return any(a in s for a in PARKING_SPECIFIC_AMENITIES)


def to_photoinsights_amenities_surface(amenities_found: Iterable[AmenityLabel]) -> dict[str, bool]:
    """
    Convert a set of AmenityLabel (specific + direct) to the boolean surface expected
    by PhotoInsights. 'parking' is aggregated from any of the specific parking labels,
    but if AmenityLabel.parking is present explicitly, treat it as True as well.
    """
    s = set(amenities_found)
    d = {a.value: False for a in PHOTOINSIGHTS_AMENITY_SURFACE}
    for a in PHOTOINSIGHTS_AMENITY_SURFACE:
        if a == AmenityLabel.parking:
            d[a.value] = (AmenityLabel.parking in s) or has_any_parking_specific(s)
        else:
            d[a.value] = a in s
    return d


# =========================
# Listing parsing regex & helpers (shared by HTML/Text normalizers)
# =========================

# Inline (number BEFORE label) — "3 bed", "1.5 bath".
# The number/label separator is HORIZONTAL whitespace only. With a bare ``\s*`` these spanned
# newlines, so "Square Feet: 1,936\nBedrooms: 3" matched "936 Bedrooms" and reported 936 beds.
_BED_INLINE_RE = re.compile(r"(?i)\b(\d+(?:\.\d+)?)[ \t\u00A0\u2009\u202F]*(?:bed(?:room)?s?|bdrm|br)\b")
_BATH_INLINE_RE = re.compile(r"(?i)\b(\d+(?:\.\d+|½|1/2)?)[ \t\u00A0\u2009\u202F]*(?:bath(?:room)?s?|ba)\b")

# Label-first (label BEFORE number) — "Bedrooms: 3", "Bathrooms - 1 1/2".
# Not anchored to ``^``: callers such as ``parse_listing_string`` collapse the text to a single
# line first, which would leave the anchored form unmatchable and fall through to the inline
# pattern above. The ':'/'-' separator is required so prose like "3 bedrooms" is not re-read here.
_BED_LABEL_RE = re.compile(r"(?i)\bbed(?:room)?s?[ \t]*[:\-][ \t]*(\d+(?:\.\d+)?)\b")
_BATH_LABEL_RE = re.compile(r"(?i)\bbath(?:room)?s?[ \t]*[:\-][ \t]*(\d+(?:\.\d+|½|1/2)?)\b")

# sqft — supports 1,016 / thin spaces / "~ 1 200", plus the label-first "Square Feet: 1,936".
#
# Separators are HORIZONTAL whitespace only. A bare ``\s*`` spans newlines, which let a number on
# one line splice onto a unit on the next: "Price: $399,900\nSquare Feet: 1,936" matched "399,900"
# followed by "Square Feet" and reported the purchase price as the floor area.
_H = r"[ \t\u00A0\u2009\u202F]"
_SQFT_NUM = r"(?:\d{1,3}(?:[,\u00A0\u2009\u202F\. ]\d{3})+|\d{3,5})"
_SQFT_UNIT = rf"(?:sq{_H}?ft|ft\u00B2|sqft|square{_H}?feet|square{_H}?footage)"

# Inline (number BEFORE unit) — "1,016 sq ft", "~ 1 200 sqft"
_SQFT_RE = re.compile(rf"(?i)(~?{_H}*{_SQFT_NUM}){_H}*{_SQFT_UNIT}\b")

# Label-first (unit BEFORE number) — "Square Feet: 1,936", "Sq Ft - 900".
# The ':'/'-' separator is REQUIRED: without it this would read the second number in
# "1,016 sq ft 1200" as the area. Tried BEFORE the inline form, because callers such as
# ``parse_listing_string`` collapse newlines first, which would otherwise let the inline
# pattern splice a price onto a following "Square Feet" label on the same line.
_SQFT_LABEL_RE = re.compile(rf"(?i)\b{_SQFT_UNIT}{_H}*[:\-]{_H}*({_SQFT_NUM})\b")

# price — allows optional "List price:" prefix
_PRICE_RE = re.compile(r"(?i)(?:list(?:ing)?\s*price\s*[:\-]?\s*)?(?:\$|usd|cad)\s*([0-9][0-9,\.]{1,})")

# year built — accepts "Year built: 2015", "built in 2015", "built: 2015"
_YEAR_RE = re.compile(r"(?i)\b(?:year\s*)?built(?:\s*in)?\s*[:\-]?\s*(\d{4})\b")


def _normalize_half_notation(s: str) -> str:
    # 1½ → 1.5 ; "1 / 2" → .5
    s = re.sub(r"\s*½", "½", s).replace("½", ".5")
    return re.sub(r"\s*1\s*/\s*2\s*", ".5", s)


def _clean_num(text: str) -> float | None:
    try:
        t = text.replace("$", "").lstrip("~").strip()
        t = t.replace(",", "").replace(" ", "").replace("\u00a0", "").replace("\u2009", "").replace("\u202f", "")
        t = re.sub(r"\.(?=\d{3}\b)", "", t)  # 1.200 → 1200
        return float(t)
    except Exception:
        return None


def extract_listing_common(text: str, notes: list[str]) -> tuple[float | None, float | None, int | None, float | None, int | None]:
    """
    Extract (bedrooms, bathrooms, sqft, price, year_built) in a way that
    supports both label-first and inline forms.
    """
    # Bedrooms: prefer label-first, then inline
    m_bed = _BED_LABEL_RE.search(text) or _BED_INLINE_RE.search(text)
    bds = _clean_num(m_bed.group(1)) if m_bed else None

    # Bathrooms: prefer label-first, then inline
    m_bath = _BATH_LABEL_RE.search(text) or _BATH_INLINE_RE.search(text)
    bas = None
    if m_bath:
        raw = _normalize_half_notation(m_bath.group(1))
        bas = _clean_num(raw)

    # Sqft — label-first ("Square Feet: 1,936") wins over inline ("1,016 sq ft"): the labelled
    # form is unambiguous, while inline can splice a preceding price onto a following label.
    m_sqft = _SQFT_LABEL_RE.search(text) or _SQFT_RE.search(text)
    sqft_i = int(_clean_num(m_sqft.group(1)) or 0) if m_sqft else None

    # Price
    m_price = _PRICE_RE.search(text)
    prc = _clean_num(m_price.group(1)) if m_price else None

    # Year built
    m_year = _YEAR_RE.search(text)
    yr = int(m_year.group(1)) if m_year else None

    # Notes
    if m_bath and (("½" in m_bath.group(0)) or ("1/2" in m_bath.group(0)) or re.search(r"\b1\s*/\s*2\b", m_bath.group(0))):
        notes.append("Parsed half bath notation.")
    if bds is None and re.search(r"(?i)\bstudio\b", text):
        bds = 0.0
        notes.append("Detected studio → 0 bedrooms.")

    return bds, bas, sqft_i, prc, yr
