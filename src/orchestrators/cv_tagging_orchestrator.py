# src/orchestrators/cv_tagging_orchestrator.py
from __future__ import annotations

import os
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, cast

from src.core.cv.amenities_defects import ProviderName, is_filename_derived, is_unconfirmed_hint, provider_kind
from src.core.cv.photo_insights import DETERMINISTIC_VERSION, VISION_STUB_VERSION
from src.core.cv.runner import tag_amenities_and_defects, tag_images
from src.core.insights.provenance import dedupe_and_sort, detection_observation, filename_observation
from src.schemas.labels import MATERIAL_TO_AMENITY_SURFACE, MaterialTag
from src.schemas.models import ObservationKind, ObservationProvenance

JSONDict = dict[str, Any]

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
_VISION_ENABLED = os.getenv("AIREAL_USE_VISION", "0").lower() in ("1", "true", "yes")


def vision_enabled() -> bool:
    """Whether the AI photo path is active for THIS process.

    Reads the module-level constant captured at import, not the environment: setting
    AIREAL_USE_VISION after import does not take effect, so re-reading it here would let a
    report claim a mode the run never used.
    """
    return _VISION_ENABLED


class CvTaggingOrchestrator:
    def analyze_paths(self, photo_paths: Sequence[str]) -> JSONDict:  # Sequence for variance safety
        normalized = _normalize_paths(photo_paths)
        if not normalized:
            return {
                "images": [],
                "rollup": {"amenities": [], "condition_tags": [], "defects": [], "warnings": [], "unconfirmed_hints": []},
                "observations": [],
            }

        # 1) Deterministic generic labels, schema shape (includes image_id)
        out = tag_images(cast(Sequence[str], normalized), use_ai=_VISION_ENABLED, return_schema=True)
        image_records = list(out.get("images", []) or [])

        # 2) Closed-set detections for rollups (provider based on vision flag)
        provider: ProviderName = "vision" if _VISION_ENABLED else "local"  # typed as Literal union
        dets = tag_amenities_and_defects(cast(Sequence[str], normalized), provider=provider, use_cache=True)

        # Per-tag provenance for everything this rollup produces. The detections already carry
        # confidence/evidence/rationale and the provider is known here; collapsing them to a bare
        # name set (which is all `rollup` can hold) threw that away before it reached the report.
        kind_val = provider_kind(provider)
        # Same version labels build_photo_insights stamps, so a tag traced through either entry
        # point names the same producer instead of one of them reporting "no version".
        version = VISION_STUB_VERSION if _VISION_ENABLED else DETERMINISTIC_VERSION
        observations: list[ObservationProvenance] = []

        # 3) Build rollups (detections)
        amenity_names: set[str] = set()
        defect_names: set[str] = set()
        unconfirmed_names: set[str] = set()
        for sha, per_img in dets.items():
            for d in per_img:
                name = str(d.get("name", "")).lower()
                if not name:
                    continue
                cat = str(d.get("category", ""))
                if cat not in ("amenity", "defect"):
                    continue

                # A label nothing was ABLE to look for does not enter the tag lists. Those three
                # lists are what `finance.engine._apply_insight_modifiers` reads to select OPEX and
                # income rules, so putting an unmeasured claim in one lets a file name move a
                # dollar. It is not dropped -- it ships in `rollup["unconfirmed_hints"]`, which the
                # analyst surfaces to the reader as a note. Shown, never counted.
                if is_unconfirmed_hint(d):
                    unconfirmed_names.add(name)
                    continue

                if cat == "amenity":
                    amenity_names.add(name)
                else:
                    defect_names.add(name)
                obs_kind: ObservationKind = "amenity" if cat == "amenity" else "defect"

                # `runner._augment_from_filename` splices filename-suggested labels into this same
                # list. One a detector CONTRADICTED (`filename_contested`) is still the file name's
                # claim, not the detector's, so it keeps `origin="photo_filename"` and carries no
                # detection payload -- stamping it as a detection is how a blank grey image called
                # "mold_basement.jpg" became a 0.90-confidence "mould suspected" *finding*. Its
                # corroboration score and the disagreement itself go in `detail`, where a reader
                # sees them for what they are.
                #
                # Written as "filename-derived AND not confirmed" rather than "== contested" so a
                # source value added later defaults to the cautious branch: an unrecognised
                # filename state must not be promoted to a detector's finding by omission.
                if is_filename_derived(d) and str(d.get("source", "")) != "filename_confirmed":
                    observations.append(
                        filename_observation(
                            name,
                            kind=obs_kind,
                            detail=_contested_detail(d),
                            source_image_sha=sha,
                        )
                    )
                    continue
                # `pixels` and `filename_confirmed` alike: a detector looked at the image and
                # emitted this label. `filename_confirmed` differs only in that a second,
                # independent signal agreed and lifted the confidence -- the detection's own
                # rationale records the arithmetic.
                observations.append(
                    detection_observation(
                        d,
                        tag=name,
                        kind=obs_kind,
                        provider=provider,
                        provider_kind=kind_val,
                        provider_version=version,
                        source_image_sha=sha,
                    )
                )

        # 3b) Promote filename-derived materials → amenity surface (e.g., kitchen_island)
        promoted: set[str] = set()
        for rec in image_records:
            rec_sha = rec.get("sha256")
            for t in rec.get("tags", []) or []:
                if not isinstance(t, dict):
                    continue
                if str(t.get("category", "")).lower() != "material":
                    continue
                raw = str(t.get("label", "")).strip().lower()
                try:
                    mt = MaterialTag(raw)
                except Exception:
                    continue
                mapped = MATERIAL_TO_AMENITY_SURFACE.get(mt)
                if mapped:
                    promoted.add(mapped.value)
                    # origin="photo_filename", NOT cv_provider: `tag_images` read the file name,
                    # no detector looked at the pixels.
                    observations.append(
                        filename_observation(
                            mapped.value,
                            kind="amenity",
                            detail=raw,
                            source_image_sha=rec_sha if isinstance(rec_sha, str) else None,
                        )
                    )

        amenity_names |= promoted

        # Rollup is expected to be a dict; coerce if not
        raw_rollup: Any = out.get("rollup")
        if not isinstance(raw_rollup, dict):
            raw_rollup = {"amenities": [], "condition_tags": [], "defects": [], "warnings": [], "unconfirmed_hints": []}
        rollup: dict[str, list[str]] = cast(dict[str, list[str]], raw_rollup)

        rollup["amenities"] = sorted(amenity_names)
        rollup["defects"] = sorted(defect_names)
        # Sibling key, deliberately NOT merged into the three above: those are observations, this
        # is a question nothing answered. Consumers that only know the original three keys keep
        # working and simply never see an unmeasured claim, which is the safe default.
        rollup["unconfirmed_hints"] = sorted(unconfirmed_names)

        out_dict: dict[str, Any] = cast(dict[str, Any], out)
        out_dict["rollup"] = rollup
        # Sibling of `rollup`, not a replacement for it: `rollup` stays the bare-string contract
        # every existing consumer reads, `observations` carries why each of those strings is there.
        # Typed ObservationProvenance objects, not dicts -- this crosses a pipeline boundary.
        out_dict["observations"] = dedupe_and_sort(observations)

        return out_dict

    def analyze_folder(self, folder: str, *, recursive: bool = False) -> JSONDict:
        images = self.list_images(folder, recursive=recursive)
        return self.analyze_paths(images)

    @staticmethod
    def list_images(folder: str, *, recursive: bool = False) -> list[str]:
        base = Path(folder)
        if not base.exists() or not base.is_dir():
            return []

        if not recursive:
            files = [p for p in sorted(base.iterdir(), key=lambda x: x.name.lower()) if p.is_file() and p.suffix.lower() in _IMAGE_EXTS]
            return [str(p) for p in files]

        collected: list[str] = []
        for dirpath, _dirnames, filenames in _walk_sorted(base):
            for name in filenames:
                p = Path(dirpath) / name
                if p.suffix.lower() in _IMAGE_EXTS and p.is_file():
                    collected.append(str(p))
        return collected


def _contested_detail(det: Mapping[str, Any]) -> str | None:
    """The one free-text 'what fired' line for a filename-suggested tag a detector did not confirm.

    ``ObservationProvenance`` gives filename origins exactly one slot and no confidence field (by
    design -- a filename guess must not be able to look like a scored detection), so the
    corroboration score goes here, in words, next to the fact that a detector disagreed. A bare
    "file name contains 'mold'" would leave the reader unable to tell this apart from the case
    where nothing looked at all.
    """
    evidence = next(iter(det.get("evidence") or ()), None)
    conf = det.get("confidence")
    if isinstance(conf, (int | float)):
        return (
            f"{evidence or 'file name match'}; a detector that covers this label "
            f"did not report it (corroboration score {float(conf):.2f})"
        )
    return str(evidence) if evidence else None


def _normalize_paths(paths: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for p in paths:
        ap = str(Path(p).resolve())
        key = ap.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(ap)
    return out


def _walk_sorted(base: Path) -> Iterable[tuple[str, list[str], list[str]]]:
    stack = [base]
    while stack:
        current = stack.pop(0)
        if not current.is_dir():
            continue
        dirnames = sorted([d.name for d in current.iterdir() if d.is_dir()], key=str.lower)
        filenames = sorted([f.name for f in current.iterdir() if f.is_file()], key=str.lower)
        yield (str(current), dirnames, filenames)
        for d in dirnames:
            stack.append(current / d)
