# src/core/cv/photo_insights.py

from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
from hashlib import sha256
from pathlib import Path
from statistics import mean
from typing import Any, NamedTuple, cast

from src.core.cv.amenities_defects import ProviderName, is_contested_hint, is_unconfirmed_hint, provider_kind
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

#: `PhotoInsights.version` for the `use_ai=True` path.
#:
#: The `"vision"` provider slot holds a hand-written heuristic, not a model (see
#: `core.cv.amenities_defects._provider_vision_stub`). Stamping its output `"ai"` made those
#: artifacts indistinguishable from a future real classifier's, so the value names the actual
#: producer instead. A real vision provider registered into the slot ships its own version
#: string with it; `provenance["provider_kind"]` flips to `"model"` automatically either way.
VISION_STUB_VERSION = "vision-stub-v1"

#: `PhotoInsights.version` for the default (`use_ai=False`) path. Unchanged: the local provider
#: is also a heuristic, but this label claims only determinism, which is true.
DETERMINISTIC_VERSION = "deterministic"

# Sanity thresholds
_MIN_BYTES = 1024  # 1 KiB
_LOW_ENTROPY_SAMPLE = 8192  # bytes to inspect for "blank" check
_LOW_ENTROPY_UNIQUE_RATIO = 0.01  # <1% unique byte ratio in head sample → suspiciously blank


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


class _SplitDetections(NamedTuple):
    """The three streams :func:`_split_measured_and_hints` produces. See its docstring."""

    measured: dict[str, list[Mapping[str, Any]]]
    unconfirmed_counts: dict[str, int]
    contested_counts: dict[str, int]


def _split_measured_and_hints(dets_per_sha: Mapping[str, list[Mapping[str, Any]]]) -> _SplitDetections:
    """Separate what a detector reported from what only a file name claims.

    Everything downstream of this split -- roll-ups, quality scores, the parking summary, the
    amenity booleans -- is a claim about the property, and several of them reach the deterministic
    finance rules through ``ListingInsights``. So ``measured`` must mean exactly one thing: **a
    provider emitted this label from the pixels.** Two filename states fail that test and are
    routed out of it:

    ``filename_unconfirmed``
        Nothing was ABLE to look. The entry has no confidence (nothing produced one), so letting it
        through would either crash the count-based consumers or, worse, silently score it 0.0 and
        drag an average down with a measurement that never happened.

    ``filename_contested``
        A detector that CAN see the label looked and did not report it. It does carry a score, and
        that score is what used to make it look safe -- but `_apply_insight_modifiers` selects OPEX
        and income rules by MEMBERSHIP in ``amenities``/``defects`` and never reads a confidence, so
        a contested ``parking_garage`` in ``amenity_counts`` became the tag ``"parking"`` and moved
        Y1 cash flow by $1,105.80 (G2-N1). A claim a detector contradicted is a *weaker* basis for
        moving a number than one nothing could check, not a stronger one.

    ``filename_confirmed`` stays in ``measured``: there, the detector did emit the label and the
    file name merely agreed.

    Counts use the same "images exhibiting this" convention as the roll-ups.
    """
    measured: dict[str, list[Mapping[str, Any]]] = {}
    unconfirmed_counts: dict[str, int] = {}
    contested_counts: dict[str, int] = {}
    for sha, dets in dets_per_sha.items():
        kept: list[Mapping[str, Any]] = []
        seen_unconfirmed: set[str] = set()
        seen_contested: set[str] = set()
        for det in dets or []:
            name = str(det.get("name", "")).lower()
            if is_unconfirmed_hint(det):
                if name and name not in seen_unconfirmed:
                    seen_unconfirmed.add(name)
                    unconfirmed_counts[name] = unconfirmed_counts.get(name, 0) + 1
                continue
            if is_contested_hint(det):
                if name and name not in seen_contested:
                    seen_contested.add(name)
                    contested_counts[name] = contested_counts.get(name, 0) + 1
                continue
            kept.append(det)
        measured[sha] = kept
    return _SplitDetections(measured, unconfirmed_counts, contested_counts)


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


# ---------- Sanity checks (filtering) ----------


def _sha256_of(path: Path) -> str:
    try:
        return sha256(path.read_bytes()).hexdigest()
    except Exception:
        return f"missing:{path.name}"


def _is_low_entropy(b: bytes) -> bool:
    # Inspect a head sample; if almost all bytes are identical, treat as blank-ish.
    if not b:
        return True
    sample = b[:_LOW_ENTROPY_SAMPLE]
    unique = len(set(sample))
    ratio = unique / max(1, len(sample))
    return ratio < _LOW_ENTROPY_UNIQUE_RATIO


def _filter_photos(paths: list[Path]) -> tuple[list[Path], list[str], dict[str, int]]:
    kept: list[Path] = []
    warnings: list[str] = []
    drop_reasons: dict[str, int] = {"too_small": 0, "duplicate": 0, "low_entropy": 0}

    seen_hash: dict[str, Path] = {}

    for p in paths:
        try:
            b = p.read_bytes()
        except Exception:
            warnings.append(f"unreadable:{p.name}")
            # treat as too small, effectively skip
            drop_reasons["too_small"] += 1
            continue

        if len(b) < _MIN_BYTES:
            warnings.append(f"too_small:{p.name}(<{_MIN_BYTES}B)")
            drop_reasons["too_small"] += 1
            continue

        if _is_low_entropy(b):
            warnings.append(f"low_entropy:{p.name}")
            drop_reasons["low_entropy"] += 1
            continue

        h = sha256(b).hexdigest()
        if h in seen_hash:
            warnings.append(f"duplicate:{p.name}->{seen_hash[h].name}")
            drop_reasons["duplicate"] += 1
            continue

        seen_hash[h] = p
        kept.append(p)

    return kept, warnings, drop_reasons


# ---------- Main ----------


def build_photo_insights(photo_dir: Path, *, use_ai: bool = False) -> PhotoInsights:
    paths_all = _iter_images(photo_dir)

    # Filter images with sanity checks
    paths, quality_warnings, drop_reasons = _filter_photos(paths_all)

    # Provider selection and its provenance labels are computed once so the empty-folder
    # early return and the main path can never disagree about what produced the artifact.
    provider: ProviderName = "vision" if use_ai else "local"
    version = VISION_STUB_VERSION if use_ai else DETERMINISTIC_VERSION
    kind = provider_kind(provider)

    if not paths:
        return PhotoInsights(
            room_counts={},
            amenities={a.value: False for a in PHOTOINSIGHTS_AMENITY_SURFACE},
            quality_flags={k: 0.0 for k in _QUALITY_PREDICATES},
            provider="cv_v2",
            version=version,
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
                "selected_provider": provider,
                "provider_kind": kind,
                "use_ai": bool(use_ai),
                "cache_root": os.getenv("AIREDEAL_CACHE_DIR", str(Path(".") / ".cache" / "cv")),
                "quality_warnings": quality_warnings,
                "filtered": {
                    "input_count": len(paths_all),
                    "kept_count": 0,
                    "dropped_count": len(paths_all),
                    "drop_reasons": drop_reasons,
                },
            },
        )

    # 1) Generic filename-derived labels (schema form)
    generic_schema: dict[str, Any] = cast(
        dict[str, Any],
        tag_images(cast(Sequence[AssetLike], paths), use_ai=use_ai, return_schema=True),
    )
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
    raw_dets = tag_amenities_and_defects(cast(Sequence[AssetLike], paths), provider=provider, use_cache=True)
    # Filename claims no detector emitted -- both the unmeasured and the contradicted kind -- are
    # pulled out here, once, before anything derives a number from them. `dets` from this point on
    # is exactly "what a detector reported".
    split = _split_measured_and_hints(cast(Mapping[str, list[Mapping[str, Any]]], raw_dets))
    dets = {sha: cast(list[Any], entries) for sha, entries in split.measured.items()}

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
        version=version,
        image_index=image_index,
        image_labels=image_labels,
        image_detections=dets,
        amenity_counts=amenity_counts,
        defect_counts=defect_counts,
        unconfirmed_hint_counts=split.unconfirmed_counts,
        contested_hint_counts=split.contested_counts,
        parking=parking,
        ontology_version="amenities_defects_v1",
        images_total=len(paths),
        detections_total=total_dets,
        provenance={
            "selected_provider": provider,
            "provider_kind": kind,
            "use_ai": bool(use_ai),
            "cache_root": os.getenv("AIREDEAL_CACHE_DIR", str(Path(".") / ".cache" / "cv")),
            "quality_warnings": quality_warnings,
            "filtered": {
                "input_count": len(paths_all),
                "kept_count": len(paths),
                "dropped_count": len(paths_all) - len(paths),
                "drop_reasons": drop_reasons,
            },
        },
    )
