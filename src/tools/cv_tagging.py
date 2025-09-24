# src/tools/cv_tagging.py
"""
CV Tagging Orchestrator (V2.1: Always-AI in AI mode + Batch-first)

Changes in 2.1
--------------
- When AI mode is enabled, we now run AI on **every readable image**, regardless
  of filename cues (forgiveness for mislabels). We still run deterministic
  tagging and merge, keeping the strongest per (category, label).
- Prefer **batch analysis** via `run_batch(provider, paths)` when AI is enabled.

Public API unchanged:
def tag_photos(photo_paths: list[str], *, use_ai: bool | None = None) -> dict
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

from .vision.ontology import derive_amenities, map_raw_tags
from .vision.provider_base import VisionProvider, run_batch

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}

ROOM_KEYWORDS = {
    "kitchen": ["kitchen"],
    "bathroom": ["bath", "bathroom"],
    "bedroom": ["bedroom", "br"],
    "living_room": ["living", "livingroom", "living_room"],
    "basement_finished": ["basement_finished"],
    "basement_unfinished": ["basement_unfinished"],
    "basement": ["basement"],
    "exterior_front": ["exterior", "front", "facade", "curb"],
    "garage": ["garage", "carport"],
    "utility_room": ["furnace", "boiler", "hvac", "utility"],
    "patio": ["patio"],
    "balcony": ["balcony"],
}
UPDATED_HINTS = ["updated", "renovated", "new", "remodeled", "modernized", "refinished"]
DEFECT_MAP = {
    "mold_suspected": ["mold", "mildew"],
    "water_stain_ceiling": ["water stain", "water_stain", "waterstain"],
    "leak_suspected": ["leak", "leaking"],
    "peeling_paint": ["peeling paint", "peeling_paint", "peeling"],
    "cracked_tile": ["cracked tile", "cracked_tile", "crackedtile"],
    "damaged_drywall": ["damaged drywall", "drywall damage", "hole drywall"],
}
FEATURE_TO_AMENITY = {
    "dishwasher": "dishwasher",
    "kitchen_island": "kitchen_island",
    "stainless_appliances": "stainless_kitchen",
    "balcony": "balcony",
    "patio": "patio",
    "fireplace": "fireplace",
    "stacked_laundry": "in_unit_laundry",
    "side_by_side_laundry": "in_unit_laundry",
    "off_street_parking": "parking",
    "fence": "fenced_yard",
}


# provider selection
def _get_provider() -> VisionProvider | None:
    provider_name = os.getenv("AIREAL_VISION_PROVIDER", "mock").lower()
    try:
        if provider_name == "mock":
            from .vision.mock_provider import MockVisionProvider

            return MockVisionProvider()
        elif provider_name == "openai":
            from .vision.openai_provider import OpenAIProvider

            return OpenAIProvider()
        else:
            return None
    except Exception:
        return None


def tag_photos(photo_paths: list[str], *, use_ai: bool | None = None) -> dict:
    if use_ai is None:
        use_ai = os.getenv("AIREAL_USE_VISION", "0").lower() in ("1", "true", "yes")

    provider = None
    warnings: list[str] = []
    if use_ai:
        provider = _get_provider()
        if provider is None:
            warnings.append("Vision provider unavailable; falling back to deterministic tagging.")
            use_ai = False

    images_out: list[dict] = []
    rollup_amenities: set[str] = set()
    rollup_conditions: set[str] = set()
    rollup_defects: set[str] = set()

    # Filter readability + maintain mapping from index -> path/image_id
    readable_indices: list[int] = []
    paths_readable: list[str] = []
    for i, path in enumerate(photo_paths):
        if Path(path).suffix.lower() in IMAGE_EXTS and Path(path).exists():
            readable_indices.append(i)
            paths_readable.append(path)

    # Deterministic pass on all readable
    det_per_img: dict[int, list[dict]] = {}
    det_amenities_per_img: dict[int, set[str]] = {}
    det_conditions_per_img: dict[int, set[str]] = {}
    det_defects_per_img: dict[int, set[str]] = {}

    for i in readable_indices:
        det_tags, _features, _conditions, _defects, _amenities = _deterministic_tag_single(photo_paths[i])
        det_per_img[i] = det_tags
        det_amenities_per_img[i] = set(_amenities)
        det_conditions_per_img[i] = set(_conditions)
        det_defects_per_img[i] = set(_defects)

    # AI pass (batch-first) on all readable when enabled
    ai_per_img: dict[int, list[dict]] = {}
    if use_ai and provider is not None and paths_readable:
        try:
            raw_batches = run_batch(provider, paths_readable)  # list[list[RawTag]] aligned to paths_readable
            if len(raw_batches) != len(paths_readable):
                raise ValueError("Provider batch returned inconsistent length.")
            for idx, raw in zip(readable_indices, raw_batches, strict=False):
                ai_per_img[idx] = map_raw_tags(cast(Iterable[dict[str, Any]], raw))
        except Exception as e:
            warnings.append(f"vision_error:{type(e).__name__}")
            # Fall back to deterministic only

    # Assemble outputs in original order
    for i, path in enumerate(photo_paths):
        img = _empty_img_dict(path)
        if i not in det_per_img and i not in ai_per_img:
            img["quality_flags"].append("unreadable")
            images_out.append(img)
            continue

        det_tags = det_per_img.get(i, [])
        ai_tags = ai_per_img.get(i, [])
        merged = _merge_tags(det_tags, ai_tags)
        derived = set(derive_amenities(merged))
        derived.update(det_amenities_per_img.get(i, set()))

        img["tags"] = merged
        img["derived_amenities"] = sorted(derived)
        images_out.append(img)

        # Rollup aggregation
        rollup_amenities.update(derived)
        for t in merged:
            if t["category"] == "condition":
                rollup_conditions.add(t["label"])
            elif t["category"] == "issue":
                rollup_defects.add(t["label"])
        rollup_conditions.update(det_conditions_per_img.get(i, set()))
        rollup_defects.update(det_defects_per_img.get(i, set()))

    rollup = {
        "amenities": sorted(rollup_amenities),
        "condition_tags": sorted(rollup_conditions),
        "defects": sorted(rollup_defects),
        "warnings": warnings,
    }
    return {"images": images_out, "rollup": rollup}


# ---------- deterministic internals unchanged ----------
def _deterministic_tag_single(path: str) -> tuple[list[dict], list[str], list[str], list[str], list[str]]:
    name = Path(path).name.lower()
    tags: list[dict] = []
    features: set[str] = set()
    conditions: set[str] = set()
    defects: set[str] = set()
    derived_amenities: set[str] = set()

    matched_rooms: set[str] = set()
    for canon, words in ROOM_KEYWORDS.items():
        if any(w in name for w in words):
            matched_rooms.add(canon)
    for r in matched_rooms:
        tags.append(_mk_tag(label=r, category="room_type", conf=0.85, evidence=f"name contains '{r.split('_')[0]}'"))

    if any(h in name for h in UPDATED_HINTS):
        for r in matched_rooms or {"kitchen"}:
            label = (
                "renovated_kitchen"
                if r.startswith("kitchen")
                else "updated_bath"
                if r.startswith("bathroom")
                else "new_flooring"
                if "floor" in name
                else "well_maintained"
            )
            conditions.add(label)
            tags.append(_mk_tag(label=label, category="condition", conf=0.62, evidence="filename updated/renovated"))

    for canon, phrases in DEFECT_MAP.items():
        if any(ph in name for ph in phrases):
            defects.add(canon)
            tags.append(_mk_tag(label=canon, category="issue", conf=0.60, evidence="defect keyword in name"))

    if "island" in name:
        features.add("kitchen_island")
    if "dishwasher" in name:
        features.add("dishwasher")
    if "stainless" in name:
        features.add("stainless_appliances")
    if "fireplace" in name:
        features.add("fireplace")
    if "balcony" in name:
        features.add("balcony")
    if "patio" in name:
        features.add("patio")

    for f in sorted(features):
        tags.append(_mk_tag(label=f, category="feature", conf=0.55, evidence="feature keyword in name"))
        if f in FEATURE_TO_AMENITY:
            derived_amenities.add(FEATURE_TO_AMENITY[f])

    return tags, list(features), list(conditions), list(defects), list(derived_amenities)


def _merge_tags(det: list[dict[str, Any]], ai: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[tuple[str, str], dict[str, Any]] = {}

    merged_tags = det + ai

    for merged_tag in merged_tags:
        cat = merged_tag.get("category")
        lab = merged_tag.get("label")
        if not (isinstance(cat, str) and isinstance(lab, str)):
            continue
        if cat not in {"room_type", "feature", "condition", "issue"}:
            continue

        key: tuple[str, str] = (cat, lab)
        prev = best.get(key)
        if prev is None or float(merged_tag.get("confidence", 0.0)) > float(prev.get("confidence", 0.0)):
            best[key] = merged_tag

    return sorted(best.values(), key=lambda x: (x["category"], x["label"]))


def _empty_img_dict(path: str) -> dict:
    return {"image_id": Path(path).name, "tags": [], "notes": [], "derived_amenities": [], "quality_flags": []}


def _mk_tag(*, label: str, category: str, conf: float, evidence: str, bbox: list[int] | None = None) -> dict:
    obj = {"label": label, "category": category, "confidence": float(conf), "evidence": evidence[:60]}
    if bbox:
        obj["bbox"] = [int(x) for x in bbox]
    return obj
