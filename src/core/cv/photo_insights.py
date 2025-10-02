# src/core/cv/photo_insights.py
"""
Build PhotoInsights by scanning a directory, running the app's CV tagging bridge,
and normalizing to the project schema.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from statistics import mean
from typing import Any

from src.schemas.models import PhotoInsights

from .bridge import run_cv_tagging

# Recognized image extensions
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}

# Canonical room keys for room_counts
_ROOM_ALIASES = {
    "kitchen": "kitchen",
    "bathroom": "bath",
    "bedroom": "bedroom",
    "living_room": "living",
    "exterior_front": "exterior",
    "garage": "garage",
    "laundry_room": "laundry",
    "patio": "patio",
    "balcony": "balcony",
}

# Amenity keys we expose as booleans (extend as needed)
_AMENITY_KEYS = [
    "in_unit_laundry",
    "dishwasher",
    "stainless_kitchen",
    "kitchen_island",
    "balcony",
    "patio",
    "fireplace",
    "parking",
    "fenced_yard",
]

# Quality signals derived from tag confidences (mean aggregation)
# - natural_light_score: tags labeled "natural_light"
# - renovated_score: any condition label containing "renovated" or "updated"
# - curb_appeal_score: heuristic based on "exterior_front" room_type tags
_QUALITY_LABELS: dict[str, Callable[[dict[str, Any]], bool]] = {
    "natural_light_score": lambda t: t.get("label") == "natural_light",
    "renovated_score": lambda t: (t.get("category") == "condition" and any(k in str(t.get("label", "")) for k in ("renovated", "updated"))),
    "curb_appeal_score": lambda t: (t.get("category") == "room_type" and t.get("label") == "exterior_front"),
}


def _iter_images(photo_dir: Path) -> list[str]:
    if not photo_dir.exists() or not photo_dir.is_dir():
        return []
    return [str(p) for p in sorted(photo_dir.iterdir()) if p.is_file() and p.suffix.lower() in _IMAGE_EXTS]


def _room_counts_from_tags(images: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for img in images:
        for tag in img.get("tags", []):
            if tag.get("category") != "room_type":
                continue
            lab = str(tag.get("label", "")).lower()
            canon = _ROOM_ALIASES.get(lab)
            if canon:
                counts[canon] = counts.get(canon, 0) + 1
    return counts


def _amenities_from_rollup(rollup_amenities: Iterable[str]) -> dict[str, bool]:
    roll = set(a.lower() for a in rollup_amenities)
    out = {k: False for k in _AMENITY_KEYS}
    for k in _AMENITY_KEYS:
        out[k] = k in roll
    return out


def _quality_scores(images: Iterable[dict[str, Any]]) -> dict[str, float]:
    buckets: dict[str, list[float]] = {k: [] for k in _QUALITY_LABELS}
    for img in images:
        for tag in img.get("tags", []):
            try:
                conf = float(tag.get("confidence", 0.0))
            except Exception:
                conf = 0.0
            for key, pred in _QUALITY_LABELS.items():
                try:
                    if pred(tag):
                        buckets[key].append(conf)
                except Exception:
                    continue
    # Mean aggregation; empty → 0.0
    return {k: (mean(v) if v else 0.0) for k, v in buckets.items()}


def build_photo_insights(photo_dir: Path, *, use_ai: bool = False) -> PhotoInsights:
    """
    Scan a directory for images, run cv_tagging.bridge, and normalize to PhotoInsights.

    Args:
        photo_dir: Directory containing listing photos (files with known image extensions).
        use_ai:    If True, ask the underlying orchestrator to run AI tagging pass.

    Returns:
        PhotoInsights (immutable Pydantic model).
    """
    image_paths = _iter_images(photo_dir)

    # Run the project's canonical tagging pipeline
    out = run_cv_tagging(image_paths, use_ai=use_ai)
    images = out.get("images", [])
    rollup = out.get("rollup", {})

    room_counts = _room_counts_from_tags(images)
    amenities = _amenities_from_rollup(rollup.get("amenities", []))
    quality = _quality_scores(images)

    # Provider/version: we don't have a direct handle; expose coarse metadata.
    # Convention: provider = "cv_tagging" and version reflects AI vs deterministic pass.
    provider = "cv_tagging"
    version = "ai" if use_ai else "deterministic"

    return PhotoInsights(
        room_counts=room_counts,
        amenities=amenities,
        quality_flags=quality,
        provider=provider,
        version=version,
    )
