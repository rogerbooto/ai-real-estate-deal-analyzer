# src/tools/vision/ontology.py
"""
CV Ontology & Mapping (V1)

Purpose
-------
Provide deterministic, auditable transformation of provider detections into
strict, product-facing tags and derived amenities:
  - Enforce allowed label sets (ontology) per category.
  - Apply global confidence threshold.
  - Dedupe overlapping labels, keeping the strongest signal.
  - Normalize features into user-facing amenities.

Design
------
- Pure functions; no IO or network.
- Stable, sorted outputs to minimize JSON diffs.
- Labels rejected if out-of-ontology (tight coupling to product spec).
- Amenity derivation is explicit (feature → amenity map), not heuristic.

Public API
----------
in_ontology(label: str, category: Category) -> bool
map_raw_tags(raw: Iterable[dict]) -> list[dict]
derive_amenities(mapped_tags: Iterable[dict]) -> list[str]

Invariants & Guardrails
-----------------------
- Confidence threshold (CONF_THRESHOLD) is global and inclusive (>= 0.40).
- Output tag objects contain: label, category, confidence, evidence, optional bbox.
- BBoxes are coerced to ints when valid; otherwise safely dropped.
- Sorting key: (category, label) for reproducible ordering.

Usage
-----
raw = provider.analyze("/path/img.jpg")
tags = map_raw_tags(raw)              # strict, deduped, thresholded
amenities = derive_amenities(tags)    # normalized, sorted, unique

Extension Points
----------------
- Add new labels by appending to the respective sets (ROOM_TYPE/FEATURE/etc.).
- For category-specific thresholds (e.g., `mold_suspected`), add a small
  per-label override table checked before CONF_THRESHOLD.

Testing
-------
- Contract tests validate thresholding, ontology strictness, dedupe, and
  amenity normalization with tiny synthetic inputs.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

Category = Literal["room_type", "feature", "condition", "issue"]

# -------------------------
# Allowed ontology (tight)
# -------------------------

ROOM_TYPE: set[str] = {
    "exterior_front",
    "exterior_back",
    "yard",
    "garage",
    "driveway",
    "entry",
    "living_room",
    "dining_room",
    "kitchen",
    "bedroom",
    "bathroom",
    "laundry",
    "hallway",
    "basement_finished",
    "basement_unfinished",
    "utility_room",
    "balcony",
    "patio",
}

FEATURE: set[str] = {
    "stainless_appliances",
    "gas_range",
    "electric_range",
    "range_hood",
    "double_sink",
    "kitchen_island",
    "dishwasher",
    "microwave",
    "quartz_counters",
    "granite_counters",
    "tile_backsplash",
    "pantry",
    "hardwood_floor",
    "laminate_floor",
    "tile_floor",
    "carpet_floor",
    "fireplace",
    "ceiling_fan",
    "recessed_lighting",
    "large_window",
    "skylight",
    "walk_in_closet",
    "double_vanity",
    "frameless_shower",
    "soaking_tub",
    "stacked_laundry",
    "side_by_side_laundry",
    "thermostat",
    "water_heater",
    "hvac_unit",
    "breaker_panel",
    "smart_lock",
    "security_camera",
    "off_street_parking",
    "fence",
    "shed",
}

CONDITION: set[str] = {
    "renovated_kitchen",
    "updated_bath",
    "new_flooring",
    "fresh_paint",
    "original_finishes",
    "dated_kitchen",
    "dated_bath",
    "minor_wear",
    "well_maintained",
}

ISSUE: set[str] = {
    "water_stain_ceiling",
    "mold_suspected",
    "peeling_paint",
    "cracked_tile",
    "damaged_drywall",
    "exposed_wiring",
    "trip_hazard",
    "smoke_detector_missing",
    "carbon_monoxide_detector_missing",
    "leak_suspected",
    "pest_signs",
}

# ------------------------------------
# Feature → Amenity normalization map
# ------------------------------------

FEATURE_TO_AMENITY: dict[str, str] = {
    "stacked_laundry": "in_unit_laundry",
    "side_by_side_laundry": "in_unit_laundry",
    "dishwasher": "dishwasher",
    "stainless_appliances": "stainless_kitchen",
    "kitchen_island": "kitchen_island",
    "fireplace": "fireplace",
    "smart_lock": "smart_home",
    "off_street_parking": "parking",
    "balcony": "balcony",
    "patio": "patio",
    "fence": "fenced_yard",
}

# -------------------------
# Global inclusion policy
# -------------------------

CONF_THRESHOLD: float = 0.40  # include only tags with confidence >= 0.40


def in_ontology(label: str, category: Category) -> bool:
    """Return True iff `label` is in the allowed set for `category`."""
    if category == "room_type":
        return label in ROOM_TYPE
    if category == "feature":
        return label in FEATURE
    if category == "condition":
        return label in CONDITION
    if category == "issue":
        return label in ISSUE
    return False


def map_raw_tags(raw: Iterable[dict]) -> list[dict]:
    """
    Map provider outputs to strict tags by applying:
    1) Category/label validation against the ontology
    2) Confidence threshold (>= CONF_THRESHOLD)
    3) Deduplication by (category, label), keeping the highest confidence
    4) Optional bbox preservation (int-cast, shape [x_min, y_min, x_max, y_max])

    Returns a stable (sorted) list of tag dicts:
        {"label", "category", "confidence", "evidence", "bbox?"}
    """
    best: dict[tuple[str, str], dict] = {}

    for t in raw:
        label = t.get("label")
        category = t.get("category")
        conf = float(t.get("confidence", 0.0) or 0.0)
        evidence = (t.get("evidence") or "")[:60]
        bbox = t.get("bbox")

        if not isinstance(label, str) or category not in {"room_type", "feature", "condition", "issue"}:
            continue
        if conf < CONF_THRESHOLD:
            continue
        if not in_ontology(label, category):
            continue

        key = (category, label)
        prev = best.get(key)
        if prev is None or conf > prev["confidence"]:
            obj = {
                "label": label,
                "category": category,
                "confidence": conf,
                "evidence": evidence,
            }
            if isinstance(bbox, list) and len(bbox) == 4:
                try:
                    obj["bbox"] = [int(x) for x in bbox]
                except Exception:
                    # If bbox can't be coerced to ints, drop it to keep schema clean.
                    pass
            best[key] = obj

    # Stable ordering for reproducible JSON & minimal diffs
    return sorted(best.values(), key=lambda x: (x["category"], x["label"]))


def derive_amenities(mapped_tags: Iterable[dict]) -> list[str]:
    """
    Normalize feature-level signals into a user-facing amenity list.

    Example:
        stainless_appliances → stainless_kitchen
        stacked_laundry     → in_unit_laundry

    Returns a sorted, de-duplicated list of amenities.
    """
    out: set[str] = set()
    for t in mapped_tags:
        if t["category"] == "feature":
            label = t["label"]
            if label in FEATURE_TO_AMENITY:
                out.add(FEATURE_TO_AMENITY[label])
    return sorted(out)
