# src/core/reports/photo_report.py
"""
Builder for MediaReport from PhotoInsights (+ optional ListingNormalized).

This module contains a single pure function, `build_media_report`, which maps the
lower-level CV output (PhotoInsights) to a stable, agent-friendly `MediaReport`.
It performs light joining across the image indices/labels/detections and computes
coverage stats and warnings. No network/file I/O is performed beyond checking
local file existence to set `readable`.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from src.schemas.models import (
    DetectedLabelModel,
    ListingNormalized,
    PhotoInsights,
)

from .report_models import (
    MediaCoverage,
    MediaItemSummary,
    MediaReport,
    ParkingSummary,
)

# -----------------------------
# Coercion / normalization
# -----------------------------


def _as_parking_summary(value: Any) -> ParkingSummary:
    """
    Coerce a PhotoInsights.parking payload into a ParkingSummary.

    Accepts either a dict-like object or a model with attributes.
    """
    if value is None:
        return ParkingSummary(parking_type="none", parking_spots=None, ev_charging=False)

    if isinstance(value, dict):
        return ParkingSummary(**value)

    # Fallback: attribute access
    return ParkingSummary(
        parking_type=getattr(value, "parking_type", "none"),
        parking_spots=getattr(value, "parking_spots", None),
        ev_charging=getattr(value, "ev_charging", False),
    )


def _normalize_tags(raw_tags: Iterable[Any]) -> list[dict[str, Any]]:
    """
    Accept strings or dicts and return a list[dict] like: {"label": <str>}.
    """
    out: list[dict[str, Any]] = []
    for t in raw_tags or []:
        if isinstance(t, str):
            out.append({"label": t})
        elif isinstance(t, dict):
            out.append(dict(t))
        else:
            # ignore unknown types
            pass
    return out


def _normalize_detections(raw_dets: Iterable[Any]) -> list[dict[str, Any]]:
    """
    Accept DetectedLabelModel or dict and return list[dict] with keys:
    {"name", "category", "confidence", ... (other fields passthrough)}.
    """
    out: list[dict[str, Any]] = []
    for d in raw_dets or []:
        if isinstance(d, DetectedLabelModel):
            out.append(d.model_dump())
        elif isinstance(d, dict):
            out.append(dict(d))
        else:
            # ignore unknown types
            pass
    return out


# -----------------------------
# Join helpers
# -----------------------------


def _iter_image_items(
    image_index: dict[str, str],
    image_labels: dict[str, list[Any]],
    image_detections: dict[str, list[Any]],
) -> tuple[list[MediaItemSummary], int]:
    """
    Join image_index with labels and detections to build MediaItemSummary entries.

    Returns:
        (items, images_readable)
    """
    items: list[MediaItemSummary] = []
    readable_count = 0

    for sha256, path in image_index.items():
        # Logical ID: filename stem is stable and human-friendly
        image_path = Path(path)
        image_id = image_path.stem or sha256[:8]

        readable = image_path.exists()
        if readable:
            readable_count += 1

        raw_tags = image_labels.get(sha256, []) or []
        raw_dets = image_detections.get(sha256, []) or []

        items.append(
            MediaItemSummary(
                image_id=image_id,
                path=str(image_path),
                sha256=sha256,
                readable=readable,
                tags=_normalize_tags(raw_tags),
                detections=_normalize_detections(raw_dets),
            )
        )

    return items, readable_count


# -----------------------------
# Public builder
# -----------------------------


def build_media_report(
    photos: PhotoInsights,
    listing: ListingNormalized | None = None,
) -> MediaReport:
    """
    Build a MediaReport from the provided PhotoInsights and optional ListingNormalized.

    Mapping rules (deterministic):
      - room_counts      ← photos.room_counts
      - amenities        ← photos.amenities
      - defects          ← photos.defect_counts
      - quality_flags    ← photos.quality_flags
      - parking          ← _as_parking_summary(photos.parking)
      - images           ← join(photos.image_index, image_labels, image_detections)
      - images_readable  ← count of `readable` among images
      - coverage         ← images_total / images_readable / detections_total / provider / version
      - ontology_version ← photos.ontology_version
      - provenance       ← photos.provenance
      - listing enrichment from `listing` if provided (title/source_url/address)

    Warnings:
      - If images_total == 0 → "no images found"
      - If all amenity booleans are False → "no amenities detected"
    """
    # --- Source counts & joins ----------------------------------------------------
    image_index: dict[str, str] = getattr(photos, "image_index", {}) or {}
    image_labels: dict[str, list[Any]] = getattr(photos, "image_labels", {}) or {}
    image_detections: dict[str, list[Any]] = getattr(photos, "image_detections", {}) or {}

    items, images_readable = _iter_image_items(image_index, image_labels, image_detections)

    # images_total: prefer PhotoInsights.images_total if provided; else derive
    images_total = getattr(photos, "images_total", None)
    if images_total is None:
        images_total = len(image_index)

    # detections_total: prefer PhotoInsights.detections_total if provided; else sum
    detections_total = getattr(photos, "detections_total", None)
    if detections_total is None:
        detections_total = sum(len(d) for d in image_detections.values())

    # --- High-level signals -------------------------------------------------------
    room_counts: dict[str, int] = dict(getattr(photos, "room_counts", {}) or {})
    amenities: dict[str, bool] = dict(getattr(photos, "amenities", {}) or {})
    defects: dict[str, int] = dict(getattr(photos, "defect_counts", {}) or {})
    quality_flags: dict[str, float] = dict(getattr(photos, "quality_flags", {}) or {})
    parking: ParkingSummary = _as_parking_summary(getattr(photos, "parking", None))

    # --- Coverage & provenance ----------------------------------------------------
    provider: str = getattr(photos, "provider", "unknown")
    version: str = getattr(photos, "version", "unknown")

    coverage = MediaCoverage(
        images_total=int(images_total or 0),
        images_readable=int(images_readable),
        detections_total=int(detections_total or 0),
        provider=provider,
        version=version,
    )

    ontology_version: str = getattr(photos, "ontology_version", "unknown")
    provenance: dict[str, Any] = dict(getattr(photos, "provenance", {}) or {})

    # --- Warnings ----------------------------------------------------------------
    warnings: list[str] = []
    if coverage.images_total == 0:
        warnings.append("no images found")
    if amenities and all(v is False for v in amenities.values()):
        warnings.append("no amenities detected")

    # --- Listing enrichment -------------------------------------------------------
    listing_title: str | None = None
    source_url: str | None = None
    address: str | None = None
    if listing is not None:
        listing_title = getattr(listing, "title", None)
        source_url = getattr(listing, "source_url", None)
        address = getattr(listing, "address", None)

    # --- Assemble report ----------------------------------------------------------
    report = MediaReport(
        listing_title=listing_title,
        source_url=source_url,
        address=address,
        room_counts=room_counts,
        amenities=amenities,
        defects=defects,
        quality_flags=quality_flags,
        parking=parking,
        coverage=coverage,
        warnings=warnings,
        ontology_version=ontology_version,
        provenance=provenance,
        images=items,
    )
    return report
