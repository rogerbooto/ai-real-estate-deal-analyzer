# src/core/cv/runner.py
from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal, NamedTuple

from PIL import Image, UnidentifiedImageError

from src.core.cv.amenities_defects import (
    FILENAME_SOURCES,
    DetectedLabel,
    ProviderName,
    detect_from_image,
    provider_capabilities,
)
from src.core.cv.ontology import AMENITIES_DEFECTS_V1 as DEFAULT_ONTOLOGY

# Unified labels & normalizers
from src.schemas.labels import (
    AmenityLabel,
    DefectLabel,
    MaterialTag,
    RoomType,
    normalize_materials_from_name,
    normalize_rooms_from_name,
)
from src.schemas.models import MediaAsset  # MediaAsset(path: Path, sha256: str)

# Accept raw file paths or MediaAsset objects
AssetLike = str | Path | MediaAsset


# ---------- Cache paths & helpers ----------

# Bump when a provider's DETECTION BEHAVIOUR changes, so previously-cached results stop being
# served. Entries are keyed by (provider, image sha256) alone, which encodes *what was looked at*
# but not *what the looker would say today* — so without this segment a behaviour fix silently
# fails to reach anyone holding a warm cache, on disk, indefinitely.
#
# This is not hypothetical: v1 → v2 is the fix that stopped `_provider_vision_stub` asserting
# "street parking, 1 spot" from an image merely being wide and bright. 8 cached entries in this
# checkout still carried that fabricated detection after the code was corrected, and would have
# kept serving it. A cached answer must not outlive the reason it was true.
#
# v3 → v4: filename-derived entries changed shape. They now carry a corroboration score (or, when
# nothing can look, no confidence at all) and a four-valued `source`; a v3 entry holds the old
# hardcoded 0.90/0.85/0.75/0.70/0.66 payloads.
#
# v4 → v5: `_provider_llm_stub` stopped emitting `"on-street parking"` from an image being wide and
# bright (Mission 2, task 3.3). A v4 entry for provider `llm` holds that fabricated detection.
# The capability digest below would in fact have segregated this one on its own -- the declaration
# shrank with the emission, so the key changes anyway -- but the version is the segment a human
# reads and reasons about, and "a provider's detection payload changed" is exactly what it is for.
# Belt and suspenders, at a cost of one recompute.
_CACHE_BEHAVIOUR_VERSION = "v5"


def _cache_root() -> Path:
    env_dir = os.getenv("AIREDEAL_CACHE_DIR")
    base = Path(env_dir) if env_dir else Path(".") / ".cache" / "cv"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _capability_fingerprint(provider: ProviderName) -> str:
    """Short, stable digest of what the provider CURRENTLY bound to ``provider`` declares it detects.

    Part of the cache key, not decoration. A cached entry's filename-derived records depend on the
    provider's declared vocabulary — the same image under the same name yields `filename_unconfirmed`
    from a provider that cannot see the label and `filename_contested` from one that can. Keying only
    on (provider slot, image sha) would therefore serve a pre-registration answer forever to anyone
    holding a warm cache, silently defeating the auto-upgrade this feature is for.
    ``_CACHE_BEHAVIOUR_VERSION`` cannot cover it: registration happens at runtime, a constant does not.
    """
    caps = "\x00".join(sorted(provider_capabilities(provider)))
    return hashlib.sha256(caps.encode("utf-8")).hexdigest()[:12]


def _cache_behaviour_segment(provider: ProviderName) -> str:
    """The one path segment that scopes a cache entry to the behaviour that produced it."""
    return f"{_CACHE_BEHAVIOUR_VERSION}-{_capability_fingerprint(provider)}"


def _provider_cache_dir(provider: ProviderName) -> Path:
    p = _cache_root() / "providers" / provider / _cache_behaviour_segment(provider)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _provider_cache_path(provider: ProviderName, sha256: str) -> Path:
    return _provider_cache_dir(provider) / f"{sha256}.json"


# ---------- Image & path utils ----------


def _sha256_of_path(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _get_asset_path(a: AssetLike) -> Path:
    if isinstance(a, Path):
        return a
    if isinstance(a, str):
        return Path(a)
    # MediaAsset
    return a.path


def _get_asset_sha(a: AssetLike) -> str:
    # Prefer explicit SHA on MediaAsset
    if isinstance(a, MediaAsset):
        sha = a.sha256
        if isinstance(sha, str) and len(sha) >= 16:
            return sha
        return _sha256_of_path(a.path)

    if isinstance(a, Path):
        return _sha256_of_path(a)

    if isinstance(a, str):
        return _sha256_of_path(Path(a))

    # Fallback (shouldn't happen)
    p = Path(a.path)
    return _sha256_of_path(p)


def _load_thumbnail(a: AssetLike, max_side: int = 768) -> tuple[Image.Image | None, bool]:
    """
    Try to open an image and return (image_or_none, readable_flag).
    Never raises; returns (None, False) if unreadable or not an image.
    """
    p = _get_asset_path(a)
    try:
        img = Image.open(p).convert("RGB")
        img.thumbnail((max_side, max_side))
        return img, True
    except (FileNotFoundError, UnidentifiedImageError, OSError, ValueError):
        return None, False


# ---------- Filename corroboration ----------
#
# Roger's rule, 2026-08-04: "we will have to confirm it with a real computer vision based
# algorithm to confirm the filename. And to do so, we can use a 70:30 split weight where the 70%
# is from the computer vision confidence level and 30% from the filename."
#
# The two weights below are a split and must sum to 1.0 (pinned by
# tests/core/cv/test_filename_corroboration.py). They are named constants, not literals, because
# they are calibration: the moment a real classifier's reliability is measured, Roger moves them
# here and every consumer follows. Same pattern as `chief_strategist.MIN_DSCR_Y1`.

#: How much of a corroborated score comes from what the detector actually measured.
CV_CONFIRMATION_WEIGHT = 0.70

#: The flat credit a matching file name contributes. **This is not a confidence.** A filename
#: match is BINARY — the token is in the name or it is not — so it can only ever contribute a
#: fixed amount, and 0.30 is the size of that credit, never "we are 30% sure". A label scored at
#: exactly 0.30 means "a detector that can see this looked and did not see it; only the file name
#: says otherwise".
#:
#: ⚠ 0.30 is NOT a safety guarantee and must never be cited as one. An earlier version of this
#: comment implied it was, on the grounds that it sits below the 0.6 "strong" bar
#: `_parking_summary` applies — but that bar does not gate every route to the money.
#: `amenity_counts` -> `synthesis._amenities_from` -> the literal tag `"parking"` ->
#: `engine._apply_insight_modifiers` reads MEMBERSHIP, not confidence, so a contested 0.30 claim
#: selected an income rule regardless of its score: a blank grey `garage.jpg`, with a detector that
#: covers `parking_garage` and reported nothing, moved Y1 cash flow by $1,105.80 (G2-N1).
#:
#: That route is now closed, and NOT by this number. A contested entry is routed out of
#: `amenity_counts`/`defect_counts` by `photo_insights._split_measured_and_hints` and out of
#: `ListingInsights.amenities` by `synthesis._amenities_from`; it reaches the reader as a note.
#: A tag that never arrives cannot select a rule — that is the guarantee. This constant remains
#: what it always was: the size of a binary file-name match's credit, and nothing more.
FILENAME_CORROBORATION_BONUS = 0.30


def corroborated_confidence(cv_confidence: float) -> float:
    """Blend a detector's own confidence with a binary file-name match.

    ``CV_CONFIRMATION_WEIGHT * cv_confidence + FILENAME_CORROBORATION_BONUS``.

    Only meaningful when something was CAPABLE of measuring the label: a detector that covers it
    and fired (``cv_confidence`` = its confidence) or covers it and did not (``0.0`` → 0.30). When
    no provider covers the label the blend is not computed at all — 0.30 would be an invented
    number for a question nothing asked. See :data:`amenities_defects.DetectionSource`.
    """
    blended = CV_CONFIRMATION_WEIGHT * float(cv_confidence) + FILENAME_CORROBORATION_BONUS
    return max(0.0, min(1.0, blended))


class _FilenameRule(NamedTuple):
    """One filename → label inference. ``tokens`` must ALL appear in the lower-cased file name."""

    label: str
    category: Literal["amenity", "defect"]
    tokens: tuple[str, ...]
    evidence: str


#: The six labels a file name is allowed to SUGGEST. A table rather than six near-identical if
#: blocks so the set is auditable at a glance -- these are property claims, and the list of things
#: a file name may assert about a building deserves to be readable in one place.
_FILENAME_RULES: tuple[_FilenameRule, ...] = (
    _FilenameRule(DefectLabel.mold_suspected.value, "defect", ("mold",), "file name contains 'mold'"),
    _FilenameRule(DefectLabel.water_leak_suspected.value, "defect", ("leak",), "file name contains 'leak'"),
    _FilenameRule(AmenityLabel.ev_charger.value, "amenity", ("ev", "charger"), "file name contains 'ev charger'"),
    _FilenameRule(AmenityLabel.parking_garage.value, "amenity", ("garage",), "file name contains 'garage'"),
    _FilenameRule(AmenityLabel.parking_driveway.value, "amenity", ("driveway",), "file name contains 'driveway'"),
    _FilenameRule(AmenityLabel.dishwasher.value, "amenity", ("dishwasher",), "file name contains 'dishwasher'"),
)


def _covered_labels(provider: ProviderName) -> frozenset[str]:
    """Canonical ontology labels the current ``provider`` binding declares it can detect.

    Declarations may be ontology synonyms (an ONNX labels file says whatever the model's author
    wrote), so they are resolved through the same ontology the detections are normalized against;
    anything outside the closed set is dropped, because a provider cannot surface a label
    ``_normalize_candidates`` would throw away.
    """
    covered: set[str] = set()
    for declared in provider_capabilities(provider):
        meta = DEFAULT_ONTOLOGY.lookup(declared)
        if meta is not None:
            covered.add(meta["name"])
    return frozenset(covered)


def _augment_from_filename(dets: list[DetectedLabel], *, lname: str, covered: frozenset[str]) -> bool:
    """Apply the filename rules to ``dets`` in place; return True if anything changed.

    A file name may SUGGEST; only a detector that actually looked may CONFIRM. Which of the three
    outcomes a match produces depends entirely on ``covered`` -- what some provider declared it is
    ABLE to detect -- and never on the label itself, which is what makes the upgrade automatic.
    """
    changed = False

    for rule in _FILENAME_RULES:
        if not all(tok in lname for tok in rule.tokens):
            continue

        existing = next((d for d in dets if d.get("name") == rule.label), None)
        if existing is not None and str(existing.get("source", "pixels")) in FILENAME_SOURCES:
            # Already corroborated on a previous pass (this runs again over cache hits). Re-blending
            # would compound the bonus every time the cache is touched.
            continue

        if existing is not None:
            # The detector covers this label and fired. Two independent signals agree.
            cv_conf = float(existing.get("confidence", 0.0) or 0.0)
            existing["confidence"] = corroborated_confidence(cv_conf)
            existing["source"] = "filename_confirmed"
            existing["evidence"] = [*(existing.get("evidence") or []), rule.evidence]
            existing["rationale"] = (
                f"Detector confidence {cv_conf:.2f} corroborated by the file name "
                f"({CV_CONFIRMATION_WEIGHT:g}x{cv_conf:.2f} + {FILENAME_CORROBORATION_BONUS:g})."
            )
            changed = True
            continue

        if rule.label in covered:
            # Something CAN see this and looked and did not report it. A real disagreement: the
            # file name's claim is scoreable, and scores weakly on purpose.
            dets.append(
                {
                    "name": rule.label,
                    "category": rule.category,
                    "confidence": corroborated_confidence(0.0),
                    "source": "filename_contested",
                    "evidence": [rule.evidence],
                    "rationale": (
                        "Only the file name suggests this. A detector that can recognise this label examined "
                        "the image and did not report it, so the file name stands uncorroborated."
                    ),
                }
            )
            changed = True
            continue

        # Nothing registered can look for this label. Not a disagreement -- an unanswered question.
        # No confidence: any number here, including 0.30, would be invented. Consumers keep this
        # out of every path that can move a number (see amenities_defects.is_unconfirmed_hint).
        dets.append(
            {
                "name": rule.label,
                "category": rule.category,
                "source": "filename_unconfirmed",
                "evidence": [rule.evidence],
                "rationale": (
                    "Inferred from the file name; no registered detector is able to examine the pixels for "
                    "this label, so nothing has confirmed or contradicted it."
                ),
            }
        )
        changed = True

    return changed


# ---------- Generic labels via unified normalizers ----------


def _filename_generic_labels(name: str) -> list[str]:
    """
    Deterministic filename → generic label mapping (rooms/materials).
    Uses the centralized enums/normalizers and returns a list of label strings.
    """
    name = name.lower()

    out: list[str] = []

    # Rooms
    rooms = normalize_rooms_from_name(name)
    out.extend([r.value for r in rooms])

    # Materials / finishes (generic cues; not amenity detections)
    materials = normalize_materials_from_name(name)
    out.extend([m.value for m in materials])

    return out


# ---------- Public API ----------


def tag_images(
    items: Sequence[AssetLike],
    *,
    use_ai: bool = True,  # reserved; generic labels remain deterministic
    return_schema: bool = False,  # False → legacy {sha: [labels]} ; True → schema {"images":[...],"rollup":{...}}
) -> dict[str, Any] | dict[str, list[str]]:
    """
    Generic labels (rooms/materials) derived from filenames.

    When return_schema=False (legacy):
        returns { "<sha256>": ["kitchen", "bathroom", ...], ... }

    When return_schema=True (orchestrator):
        returns {
          "images": [
            {
              "image_id": "<filename.ext>",
              "path": "<abs-or-rel-path>",
              "sha256": "<sha256>",
              "readable": <bool>,
              "tags": [{"label": str, "category": "room_type"|"material", "confidence": float}]
            }, ...
          ],
          "rollup": {"amenities": [], "condition_tags": [], "defects": [], "warnings": []}
        }
    """
    if not return_schema:
        out: dict[str, list[str]] = {}
        for it in items:
            p = _get_asset_path(it)
            sha = _get_asset_sha(it)
            out[sha] = _filename_generic_labels(p.name)
        return out

    # Schema form for orchestrator/agents
    records: list[dict[str, Any]] = []
    for it in items:
        p = _get_asset_path(it)
        sha = _get_asset_sha(it)
        _img, readable = _load_thumbnail(it)

        labs = _filename_generic_labels(p.name)

        tags: list[dict[str, Any]] = []
        for lab in labs:
            # Decide category based on membership in enums
            if lab in {rt.value for rt in RoomType}:
                category = "room_type"
            elif lab in {mt.value for mt in MaterialTag}:
                category = "material"
            else:
                # Fallback (should not happen if normalizers are exhaustive)
                category = "material"
            tags.append({"label": lab, "category": category, "confidence": 0.66})

        # --- Filename-derived deterministic tags for schema consumers ---
        lname = p.name.lower()

        # Condition: kitchen + (updated|renovated|new) → renovated_kitchen (conf ~0.62)
        if ("kitchen" in lname) and any(w in lname for w in ("updated", "renovated", "new")):
            tags.append({"label": "renovated_kitchen", "category": "condition", "confidence": 0.62})

        # Issues: basement + mold → mold_suspected
        if ("basement" in lname) and ("mold" in lname):
            tags.append({"label": "mold_suspected", "category": "issue", "confidence": 0.90})

        # Issues: roof + leak → water_leak_suspected
        if ("roof" in lname) and ("leak" in lname):
            tags.append({"label": "water_leak_suspected", "category": "issue", "confidence": 0.85})

        records.append(
            {
                "image_id": p.name,  # required by integration tests
                "path": str(p),
                "sha256": sha,
                "readable": bool(readable),
                "tags": tags,
            }
        )

    rollup: dict[str, list[str]] = {"amenities": [], "condition_tags": [], "defects": [], "warnings": []}
    return {"images": records, "rollup": rollup}


def tag_amenities_and_defects(
    assets: Sequence[AssetLike],
    *,
    provider: ProviderName,
    use_cache: bool = True,
) -> dict[str, list[DetectedLabel]]:
    """
    Produce per-image amenity/defect detections as {sha256: [DetectedLabel]}.
    - Caches JSON per (provider, declared capabilities, sha256)
    - Never raises on unreadable inputs (returns [] for that image)
    - Splices in filename-suggested labels, each classified against what this provider declares
      it can detect (see ``_augment_from_filename`` and ``amenities_defects.DetectionSource``):
      a suggestion a detector corroborated, one it contradicted, and one nothing could measure
      are three different facts and are recorded as three different things.
    - IMPORTANT: Empty cache entries no longer short-circuit; we recompute to
      populate deterministic filename-based fallbacks.
    """
    results: dict[str, list[DetectedLabel]] = {}
    # Resolved once per call, not per image: it is a property of the provider binding, and the
    # cache key already depends on it.
    covered = _covered_labels(provider)

    for asset in assets:
        asset_path = _get_asset_path(asset)
        sha = _get_asset_sha(asset)
        cache_path = _provider_cache_path(provider, sha)
        lname = asset_path.name.lower()

        # --- 0) Cache hit: if non-empty, still augment with filename heuristics and re-save
        if use_cache and cache_path.exists():
            try:
                data = json.loads(cache_path.read_text(encoding="utf-8"))
                if isinstance(data, list) and all(isinstance(x, dict) and "name" in x for x in data):
                    if len(data) > 0:
                        dets_cached: list[DetectedLabel] = list(data)
                        if _augment_from_filename(dets_cached, lname=lname, covered=covered):
                            try:
                                cache_path.write_text(json.dumps(dets_cached, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
                            except Exception:
                                pass
                        results[sha] = dets_cached
                        continue
                    # else: empty → fall through to compute fresh
            except Exception:
                pass

        # 1) Try to open thumbnail (best-effort)
        img, _readable = _load_thumbnail(asset)

        # 2) Provider inference (best-effort)
        dets: list[DetectedLabel] = []
        try:
            pil_img = img if img is not None else Image.new("RGB", (8, 8), color=(240, 240, 240))
            dets = detect_from_image(pil_img, provider=provider, ontology=DEFAULT_ONTOLOGY)
        except Exception:
            dets = []

        # 3) Always classify the file name's suggestions against what this provider can see
        _augment_from_filename(dets, lname=lname, covered=covered)

        # 4) Persist cache
        if use_cache:
            try:
                cache_path.write_text(json.dumps(dets, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            except Exception:
                pass

        results[sha] = dets

    return results
