# src/tools/cv_tagging.py
"""
V1 CV tagging stub (deterministic, no external models).

Approach
--------
- Keyword heuristics on image filenames to simulate CV tags.
- Works on common image extensions; ignores non-image files.
- Emits canonical tags (e.g., "kitchen", "bathroom") plus prefixed tags:
  * "cond:<label>"    -> condition tags (e.g., "cond:updated kitchen")
  * "defect:<label>"  -> defect tags (e.g., "defect:mold")

Why prefixes?
-------------
Keeps the raw per-file tag list simple and makes it trivial to aggregate into
ListingInsights.condition_tags / ListingInsights.defects via summarize_cv_tags().

Public API
----------
- tag_images_in_folder(folder: str) -> dict[str, list[str]]
    Returns tags per image file in `folder`.

- summarize_cv_tags(tags_by_file: dict[str, list[str]]) -> dict[str, set[str]]
    Returns {"condition_tags": set[str], "defects": set[str]} aggregated across files.

Notes
-----
- Intentionally conservative and explainable for V1.
- Expandable: add new keyword rules without changing call sites.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Iterable, List, Set


# ----------------------------
# Configuration / Keyword maps
# ----------------------------

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}

# Room/area keywords (produce plain tags like "kitchen", "bathroom", etc.)
ROOM_KEYWORDS = {
    "kitchen": ["kitchen"],
    "bathroom": ["bath", "bathroom"],
    "bedroom": ["bedroom", "br"],
    "living": ["living", "livingroom", "living_room"],
    "basement": ["basement"],
    "roof": ["roof"],
    "exterior": ["exterior", "front", "facade", "curb"],
    "garage": ["garage", "carport"],
    "hvac": ["furnace", "boiler", "hvac"],
}

# Condition keywords (combined with room keywords for specific conditions)
UPDATED_HINTS = ["updated", "renovated", "new", "remodeled", "modernized", "refinished"]

# Defect keywords (map to canonical defect labels)
DEFECT_MAP = {
    "mold": ["mold", "mildew"],
    "water damage": ["water stain", "water_stain", "water damage", "flood", "flooded"],
    "crack": ["crack", "cracking"],
    "leak": ["leak", "leaking"],
    "peeling paint": ["peeling paint", "peeling_paint"],
    "rot": ["rot", "rotten"],
}


# ----------------------------
# Public API
# ----------------------------

def tag_images_in_folder(folder: str) -> Dict[str, List[str]]:
    """
    Tag images in a folder using filename keyword heuristics.

    Args:
        folder: Path to a directory containing image files.

    Returns:
        dict of {filename: [tags...]}, where tags include:
          - plain room/area tags (e.g., "kitchen")
          - "cond:<label>" condition tags (e.g., "cond:updated kitchen")
          - "defect:<label>" defect tags (e.g., "defect:mold")

    Behavior:
        - Only files with image extensions are considered.
        - Case-insensitive filename matching.
        - Deterministic: no randomness or external calls.
    """
    out: Dict[str, List[str]] = {}
    p = Path(folder)
    if not p.exists() or not p.is_dir():
        return out

    for f in sorted(p.iterdir(), key=lambda x: x.name.lower()):
        if not f.is_file():
            continue
        if f.suffix.lower() not in IMAGE_EXTS:
            continue
        tags = _tags_from_filename(f.name)
        out[f.name] = tags
    return out


def summarize_cv_tags(tags_by_file: Dict[str, List[str]]) -> Dict[str, Set[str]]:
    """
    Aggregate prefixed tags across all files into ListingInsights-like buckets.

    Returns:
        {
            "condition_tags": { ... },   # from tags prefixed with "cond:"
            "defects": { ... }           # from tags prefixed with "defect:"
        }
    """
    condition: Set[str] = set()
    defects: Set[str] = set()

    for tags in tags_by_file.values():
        for t in tags:
            if t.startswith("cond:"):
                condition.add(t.split("cond:", 1)[1])
            elif t.startswith("defect:"):
                defects.add(t.split("defect:", 1)[1])
    return {"condition_tags": condition, "defects": defects}


# ----------------------------
# Internals
# ----------------------------

def _tags_from_filename(name: str) -> List[str]:
    """
    Infer tags from a filename using keyword rules.

    Rules:
      - Add room tags when room keywords appear.
      - If UPDATED_HINTS present with a specific room, add "cond:updated <room>".
      - Map defect phrases to canonical defects via DEFECT_MAP.
      - Special case: if "roof" and a "leak" hint appear together, prefer "defect:roof leak".

    Example:
      "kitchen_updated.jpg" -> ["kitchen", "cond:updated kitchen"]
      "basement_mold.png"   -> ["basement", "defect:mold"]
      "roof_leak.JPG"       -> ["roof", "defect:roof leak"]
    """
    lowered = name.lower()
    tags: List[str] = []

    # 1) Room/area tags
    matched_rooms: Set[str] = set()
    for canon, words in ROOM_KEYWORDS.items():
        if any(w in lowered for w in words):
            matched_rooms.add(canon)
            tags.append(canon)

    # 2) Condition hints (updated/renovated/new per room)
    if any(h in lowered for h in UPDATED_HINTS):
        for r in matched_rooms:
            # More descriptive for kitchen/bath/roof; generic 'updated <room>' otherwise
            if r == "kitchen":
                tags.append("cond:updated kitchen")
            elif r == "bathroom":
                tags.append("cond:updated bath")
            elif r == "roof":
                tags.append("cond:new roof")
            else:
                tags.append(f"cond:updated {r}")

    # 3) Defects
    defects_found: Set[str] = set()
    for canon, phrases in DEFECT_MAP.items():
        if any(ph in lowered for ph in phrases):
            defects_found.add(canon)

    # Special case: roof + leak => "roof leak"
    if "roof" in matched_rooms and ("leak" in lowered or "leaking" in lowered):
        defects_found.discard("leak")
        tags.append("defect:roof leak")

    # Add remaining canonical defects
    for d in sorted(defects_found):
        tags.append(f"defect:{d}")

    return tags
