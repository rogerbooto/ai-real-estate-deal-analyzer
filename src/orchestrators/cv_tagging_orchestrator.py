# src/orchestrators/cv_tagging_orchestrator.py
from __future__ import annotations

import os
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, cast

from src.core.cv.amenities_defects import ProviderName, is_contested_hint, is_uncorroborated_filename_claim, provider_kind
from src.core.cv.photo_insights import DETERMINISTIC_VERSION, VISION_STUB_VERSION
from src.core.cv.runner import tag_amenities_and_defects, tag_images
from src.core.insights.provenance import dedupe_and_sort, detection_observation
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
                "rollup": {
                    "amenities": [],
                    "condition_tags": [],
                    "defects": [],
                    "warnings": [],
                    "unconfirmed_hints": [],
                    "contested_hints": [],
                },
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
        contested_names: set[str] = set()
        for sha, per_img in dets.items():
            for d in per_img:
                name = str(d.get("name", "")).lower()
                if not name:
                    continue
                cat = str(d.get("category", ""))
                if cat not in ("amenity", "defect"):
                    continue
                obs_kind: ObservationKind = "amenity" if cat == "amenity" else "defect"

                # A label the FILE NAME claims but no detector confirmed does not enter the tag
                # lists -- neither the case nothing was ABLE to look (`filename_unconfirmed`) nor
                # the case a covering detector looked and disagreed (`filename_contested`). Those
                # three lists are what `finance.engine._apply_insight_modifiers` reads to select
                # OPEX and income rules, so putting either kind of claim in one lets a file name
                # move a dollar -- `insights.amenities: ['parking_garage']` from a blank grey
                # `garage.jpg` plus a detector that declared `parking_garage` and reported nothing
                # was exactly this route, saved from moving money today only by an unrelated
                # label-vs-rule mismatch (defect #4), not by any guard.
                #
                # `is_uncorroborated_filename_claim` is the single predicate every producer in this
                # codebase uses to draw this line (`core.insights.synthesis` is the sibling that
                # already used it) -- written as "filename-derived AND NOT confirmed" so a source
                # value added later defaults to the cautious branch rather than being promoted to a
                # detector's finding by omission. It is not dropped -- it still reaches the reader
                # through `rollup["unconfirmed_hints"]` / `rollup["contested_hints"]`, worded to say
                # which of the two facts is true (nothing looked, vs. something looked and
                # disagreed).
                source_val = d.get("source")
                if is_uncorroborated_filename_claim(str(source_val) if source_val is not None else None):
                    if is_contested_hint(d):
                        contested_names.add(name)
                    else:
                        unconfirmed_names.add(name)
                    continue

                if cat == "amenity":
                    amenity_names.add(name)
                else:
                    defect_names.add(name)
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

        # 3b) Filename-derived materials (e.g., kitchen_island) suggest an amenity surface.
        #
        # `tag_images` never examines pixels for these labels -- `_filename_generic_labels`
        # (`core/cv/runner.py`) reads only the file name, with no provider/capability concept at
        # all -- so there is no detector here that could ever CONFIRM or CONTEST one of these the
        # way the loop above does for `tag_amenities_and_defects` labels. Every material promotion
        # is therefore structurally the "nothing was able to look" case, under the same
        # suggest-vs-confirm rule (R-6) that keeps a contested or unconfirmed detection out of
        # `amenities`/`condition_tags`/`defects`. Task 3.5's decision: fix it rather than merely
        # flag it, for consistency with the loop above -- an amenity a reader was told "the file
        # name says so" does not belong inside the one list the finance engine reads just because
        # it arrived through a different function. It hits no engine rule today (no dollars move
        # either way), but "safe by accident" is exactly the shape this mission spent three rows
        # (defect #4, G2-N1, G2-N2) closing, so it is not left as a fourth.
        for rec in image_records:
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
                    unconfirmed_names.add(mapped.value)

        # A hint and a tag are per-LABEL facts, but the loops above are per-DETECTION-RECORD: one
        # photo in the folder can put a label in `unconfirmed_names`/`contested_names` while a
        # DIFFERENT photo in the same folder puts the SAME label in `amenity_names`/`defect_names`
        # (a covering detector genuinely saw it there). Without this, both buckets would ship the
        # label at once -- the tag list saying a detector observed it, and the hint note saying in
        # the same breath that "no detector... does not affect any number in this analysis", which
        # is false the moment the tag is present. A confirmed sighting anywhere in the folder makes
        # the hint moot for that label everywhere in the folder, so the tag lists win. The two hint
        # buckets stay distinct from EACH OTHER on purpose (a filename-unconfirmed and a
        # filename-contested claim are still different facts); only confirmed tags subtract.
        _confirmed = amenity_names | defect_names
        unconfirmed_names -= _confirmed
        contested_names -= _confirmed

        # Rollup is expected to be a dict; coerce if not
        raw_rollup: Any = out.get("rollup")
        if not isinstance(raw_rollup, dict):
            raw_rollup = {
                "amenities": [],
                "condition_tags": [],
                "defects": [],
                "warnings": [],
                "unconfirmed_hints": [],
                "contested_hints": [],
            }
        rollup: dict[str, list[str]] = cast(dict[str, list[str]], raw_rollup)

        rollup["amenities"] = sorted(amenity_names)
        rollup["defects"] = sorted(defect_names)
        # Sibling keys, deliberately NOT merged into the three above: those are observations, these
        # are questions nothing answered (or answered "no"). Consumers that only know the original
        # three keys keep working and simply never see an unmeasured or contradicted claim, which
        # is the safe default.
        rollup["unconfirmed_hints"] = sorted(unconfirmed_names)
        rollup["contested_hints"] = sorted(contested_names)

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
