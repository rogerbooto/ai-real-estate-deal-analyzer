# src/core/cv/photo_insights.py

from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from statistics import mean
from typing import Any, cast

from src.core.cv.amenities_defects import ProviderName
from src.core.cv.runner import tag_amenities_and_defects, tag_images

# Centralized labels/enums + helpers
from src.schemas.labels import (
    MATERIAL_TO_AMENITY_SURFACE,
    PHOTOINSIGHTS_AMENITY_SURFACE,
    ROOM_COUNT_CANONICAL,
    AmenityLabel,
    MaterialTag,
    ParkingType,
    RoomType,
    to_photoinsights_amenities_surface,
)
from src.schemas.models import MediaAsset, PhotoInsights

# Accept raw file paths or MediaAsset objects
AssetLike = str | Path | MediaAsset

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def _iter_images(photo_dir: Path) -> list[Path]:
    if not photo_dir.exists() or not photo_dir.is_dir():
        return []
    return [p for p in sorted(photo_dir.iterdir()) if p.is_file() and p.suffix.lower() in _IMAGE_EXTS]


def _is_natural_light(tag: dict[str, Any]) -> bool:
    return "natural_light" in str(tag.get("label", "")).lower()


def _is_renovated(tag: dict[str, Any]) -> bool:
    lab = str(tag.get("label", "")).lower()
    return ("renovated" in lab) or ("updated" in lab)


def _is_exterior(tag: dict[str, Any]) -> bool:
    return "exterior" in str(tag.get("label", "")).lower()


_QUALITY_PREDICATES: dict[str, Callable[[dict[str, Any]], bool]] = {
    "natural_light_score": _is_natural_light,
    "renovated_score": _is_renovated,
    "curb_appeal_score": _is_exterior,
}


def _parking_summary(dets_per_sha: Mapping[str, list[Mapping[str, Any]]]) -> dict[str, Any]:
    counts: dict[str, list[float]] = {}
    for dets in dets_per_sha.values():
        for d in dets:
            name = str(d.get("name", "")).lower()
            conf = float(d.get("confidence", 0.0) or 0.0)
            counts.setdefault(name, []).append(conf)

    def strong(label: AmenityLabel, thr: float = 0.6) -> int:
        return sum(1 for c in counts.get(label.value, []) if c >= thr)

    if strong(AmenityLabel.parking_garage) >= 2:
        parking_type = ParkingType.garage.value
    elif strong(AmenityLabel.parking_driveway) >= 2:
        parking_type = ParkingType.driveway.value
    elif AmenityLabel.street_parking.value in counts:
        parking_type = ParkingType.street.value
    else:
        parking_type = ParkingType.none.value

    ev_charging = any(c >= 0.6 for c in counts.get(AmenityLabel.ev_charger.value, []))
    spots = strong(AmenityLabel.parking_garage) + strong(AmenityLabel.parking_driveway)
    if spots == 0 and AmenityLabel.street_parking.value in counts:
        spots = 1
    if spots > 3:
        spots = 3

    return {
        "parking_type": parking_type,
        "parking_spots": spots if spots else None,
        "ev_charging": ev_charging,
    }


def _rollup(dets_per_sha: Mapping[str, list[Mapping[str, Any]]], *, category: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for dets in dets_per_sha.values():
        seen: set[str] = set()
        for det in dets:
            if det.get("category") != category:
                continue
            name = str(det.get("name", "")).lower()
            if name and name not in seen:
                seen.add(name)
                out[name] = out.get(name, 0) + 1
    return out


def _quality_scores(generic: dict[str, list[str]], dets: Mapping[str, list[Mapping[str, Any]]]) -> dict[str, float]:
    all_shas = set(generic) | set(dets)
    buckets: dict[str, list[float]] = {k: [] for k in _QUALITY_PREDICATES}
    for sha in all_shas:
        tags: list[dict[str, Any]] = [{"label": lab, "confidence": 0.66} for lab in generic.get(sha, [])]
        tags += [{"label": det.get("name"), "confidence": float(det.get("confidence", 0.0) or 0.0)} for det in dets.get(sha, [])]
        for tag in tags:
            conf = float(tag.get("confidence", 0.0) or 0.0)
            for key, pred in _QUALITY_PREDICATES.items():
                if pred(tag):
                    buckets[key].append(conf)
    return {k: (mean(v) if v else 0.0) for k, v in buckets.items()}


def _amenities_surface_from(amenity_counts: dict[str, int], image_labels: dict[str, list[str]]) -> dict[str, bool]:
    """
    Build the PhotoInsights amenity booleans from:
      1) Closed-set detections (amenity_counts)
      2) Promoted materials in filename tags (image_labels)
    """
    found: set[AmenityLabel] = set()

    # From detections (ontology names)
    for name in amenity_counts.keys():
        try:
            found.add(AmenityLabel(name))
        except Exception:
            # ontology names that map to surface:
            if name == "laundry_in_unit":
                found.add(AmenityLabel.in_unit_laundry)
            elif name == MaterialTag.stainless_appliances.value:
                found.add(AmenityLabel.stainless_kitchen)
            # else ignore non-surface labels

    # Promote materials from filename tags → amenity surface
    for labs in image_labels.values():
        for lab in labs:
            try:
                mt = MaterialTag(lab)
            except Exception:
                continue
            mapped = MATERIAL_TO_AMENITY_SURFACE.get(mt)
            if mapped:
                found.add(mapped)

    return to_photoinsights_amenities_surface(found)


# ---------- Main ----------


def build_photo_insights(photo_dir: Path, *, use_ai: bool = False) -> PhotoInsights:
    paths = _iter_images(photo_dir)
    if not paths:
        return PhotoInsights(
            room_counts={},
            amenities={a.value: False for a in PHOTOINSIGHTS_AMENITY_SURFACE},
            quality_flags={k: 0.0 for k in _QUALITY_PREDICATES},
            provider="cv_v2",
            version="ai" if use_ai else "deterministic",
            image_index={},
            image_labels={},
            image_detections={},
            amenity_counts={},
            defect_counts={},
            parking={"parking_type": ParkingType.none.value, "parking_spots": None, "ev_charging": False},
            ontology_version="amenities_defects_v1",
            images_total=0,
            detections_total=0,
            provenance={
                "selected_provider": "local",
                "use_ai": bool(use_ai),
                "cache_root": os.getenv("AIREDEAL_CACHE_DIR", str(Path(".") / ".cache" / "cv")),
            },
        )

    provider: ProviderName = "vision" if use_ai else "local"

    # 1) Generic filename-derived labels (schema form)
    generic_schema: dict[str, Any] = cast(dict[str, Any], tag_images(cast(Sequence[AssetLike], paths), use_ai=use_ai, return_schema=True))
    image_records: list[dict[str, Any]] = list(generic_schema.get("images", []) or [])

    # sha -> labels (strings) from schema records (used for quality + material promotion)
    image_labels: dict[str, list[str]] = {}
    for rec in image_records:
        sha = rec.get("sha256")
        labs: list[str] = []
        tags = rec.get("tags", [])
        if isinstance(tags, list):
            for t in tags:
                if isinstance(t, dict):
                    label = t.get("label")
                    if isinstance(label, str):
                        labs.append(label)
        if isinstance(sha, str):
            image_labels[sha] = labs

    # sha -> path
    image_index: dict[str, str] = {}
    for rec in image_records:
        sha = rec.get("sha256")
        p = rec.get("path")
        if isinstance(sha, str) and isinstance(p, str):
            image_index[sha] = p

    # 2) Closed-set detections (for rollups and quality)
    dets = tag_amenities_and_defects(cast(Sequence[AssetLike], paths), provider=provider, use_cache=True)

    # 3) Room counts — RoomType → PhotoInsights key via ROOM_COUNT_CANONICAL
    room_counts: dict[str, int] = {}
    for rec in image_records:
        for tag in rec.get("tags", []):
            if not isinstance(tag, dict):
                continue
            if str(tag.get("category", "")).lower() != "room_type":
                continue
            raw = str(tag.get("label", "")).lower().strip()
            try:
                rt = RoomType(raw)
            except Exception:
                continue
            key = ROOM_COUNT_CANONICAL.get(rt)
            if key:
                room_counts[key] = room_counts.get(key, 0) + 1

    # 4) Rollups
    amenity_counts = _rollup(cast(Mapping[str, list[Mapping[str, Any]]], dets), category="amenity")
    defect_counts = _rollup(cast(Mapping[str, list[Mapping[str, Any]]], dets), category="defect")

    # 5) Amenity booleans (detections + promoted materials)
    amenities_bool = _amenities_surface_from(amenity_counts, image_labels)

    # 6) Quality proxies/scores from generic labels + detections
    quality_flags = _quality_scores(image_labels, cast(Mapping[str, list[Mapping[str, Any]]], dets))

    # 7) Parking summary from detections
    parking = _parking_summary(cast(Mapping[str, list[Mapping[str, Any]]], dets))

    total_dets = sum(len(v) for v in dets.values())

    return PhotoInsights(
        room_counts=room_counts,
        amenities=amenities_bool,
        quality_flags=quality_flags,
        provider="cv_v2",
        version="ai" if use_ai else "deterministic",
        image_index=image_index,
        image_labels=image_labels,
        image_detections=dets,
        amenity_counts=amenity_counts,
        defect_counts=defect_counts,
        parking=parking,
        ontology_version="amenities_defects_v1",
        images_total=len(paths),
        detections_total=total_dets,
        provenance={
            "selected_provider": provider,
            "use_ai": bool(use_ai),
            "cache_root": os.getenv("AIREDEAL_CACHE_DIR", str(Path(".") / ".cache" / "cv")),
        },
    )
