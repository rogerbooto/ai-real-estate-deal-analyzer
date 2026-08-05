# src/core/insights/provenance.py
"""
Builders for ``ListingInsights.observations`` -- the per-tag provenance ledger.

Why this module exists
----------------------
``ListingInsights.condition_tags`` / ``defects`` / ``amenities`` are bare strings. Every producer
in this pipeline already knows *more* than a string -- the listing parser knows which phrase
matched, the CV pipeline knows the provider, its confidence, its evidence and its rationale -- and
all of it was being discarded at the boundary. A report reading only the strings therefore cannot
say "AI observed 'old roof'" without lying, because nothing tells it whether a model was involved.

These helpers are pure, deterministic and side-effect free. They never *infer* an origin: a caller
that cannot attribute a tag records ``origin="unknown"`` rather than guessing.

Shape
-----
``observations`` is a flat ``list``, not a dict keyed by tag, and holds ONE RECORD PER
(tag, origin, source). A tag seen by two sources -- "parking" in the copy *and* a garage detected
in a photo -- produces two records, because collapsing them would force a lossy "which source
wins?" decision at record time, which is the exact defect class this ledger exists to close.
Grouping by tag at render time is trivial; recovering per-source records from a merged dict is
impossible.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from src.schemas.models import (
    DetectedLabelModel,
    ListingInsights,
    ObservationKind,
    ObservationOrigin,
    ObservationProvenance,
)

#: ``ListingInsights`` list name for each observation kind. Used to check a record actually
#: corresponds to a shipped tag (see :func:`retain_recorded_tags`).
_LIST_FOR_KIND: dict[ObservationKind, str] = {
    "amenity": "amenities",
    "condition": "condition_tags",
    "defect": "defects",
}


def _sort_key(obs: ObservationProvenance) -> tuple[str, ...]:
    """Total, content-derived ordering so a rebuilt ledger is byte-identical run to run."""
    return (
        obs.kind,
        obs.tag,
        obs.origin,
        obs.provider or "",
        obs.source_image_sha or "",
        obs.detail or "",
        obs.detection.name if obs.detection else "",
    )


def dedupe_and_sort(observations: Iterable[ObservationProvenance]) -> list[ObservationProvenance]:
    """Deterministic ledger: drop exact re-observations, then sort by content.

    Two records that agree on kind/tag/origin/provider/image/detail are the same observation
    reported twice (e.g. the same photo folder walked by two code paths), not two independent
    sightings, so the first is kept. Records that differ in ANY of those -- notably a different
    source image -- are distinct sightings and both survive.
    """
    seen: dict[tuple[str, ...], ObservationProvenance] = {}
    for obs in observations:
        seen.setdefault(_sort_key(obs), obs)
    return [seen[key] for key in sorted(seen)]


def text_observation(
    tag: str,
    *,
    kind: ObservationKind,
    detail: str | None = None,
) -> ObservationProvenance:
    """A tag read out of the listing copy (keyword match or normalized listing fact).

    Carries no confidence and no provider on purpose: a keyword match has neither. Inventing a
    number here would make a regex hit indistinguishable from a scored detection.
    """
    return ObservationProvenance(tag=tag, kind=kind, origin="listing_text", detail=detail)


def filename_observation(
    tag: str,
    *,
    kind: ObservationKind,
    detail: str | None = None,
    source_image_sha: str | None = None,
) -> ObservationProvenance:
    """A tag derived from an image's FILE NAME rather than its pixels.

    Distinct from ``cv_provider`` because no detector looked at the image; "kitchen_island.jpg"
    asserts an amenity through its filename alone. Recording it as a CV detection would let a
    future real classifier's output and a filename guess read identically.
    """
    return ObservationProvenance(
        tag=tag,
        kind=kind,
        origin="photo_filename",
        detail=detail,
        source_image_sha=source_image_sha,
    )


def detection_observation(
    detection: Mapping[str, Any] | DetectedLabelModel,
    *,
    tag: str,
    kind: ObservationKind,
    provider: str,
    provider_kind: str | None,
    provider_version: str | None = None,
    source_image_sha: str | None = None,
) -> ObservationProvenance:
    """A tag a ``core/cv`` detector produced from an image, with its own record attached.

    ``detection`` is the raw ``DetectedLabel`` mapping; it is validated into a
    :class:`DetectedLabelModel` so confidence/evidence/rationale travel with the tag instead of
    being reduced to a bare string. A mapping that fails validation yields ``detection=None``
    rather than a raised error -- the origin is still worth recording even when the payload is
    malformed, and this path must never crash the pipeline.
    """
    if isinstance(detection, DetectedLabelModel):
        detail_model: DetectedLabelModel | None = detection
    else:
        try:
            detail_model = DetectedLabelModel.model_validate(dict(detection))
        except Exception:
            detail_model = None

    kind_literal: ObservationKind = kind
    provider_kind_literal: Any = provider_kind if provider_kind in ("heuristic_stub", "model") else None
    return ObservationProvenance(
        tag=tag,
        kind=kind_literal,
        origin="cv_provider",
        provider=provider,
        provider_kind=provider_kind_literal,
        provider_version=provider_version,
        source_image_sha=source_image_sha,
        detection=detail_model,
    )


def derived_observation(
    tag: str,
    *,
    kind: ObservationKind,
    detail: str,
    provider: str | None = None,
    provider_kind: str | None = None,
    provider_version: str | None = None,
) -> ObservationProvenance:
    """A tag a caller computed from AGGREGATE detector output rather than one detection.

    Example: ``synthesize_listing_insights`` turns ``quality_flags['renovated_score'] >= 0.6``
    into the condition tag "renovated". No single detection backs it, so there is no
    ``DetectedLabelModel`` to attach -- but the threshold that tripped is real evidence and goes
    in ``detail``. Origin is ``cv_provider`` when a provider is named (pixels were involved
    somewhere upstream) and ``unknown`` when it is not, because a tag whose producer we cannot
    name must not borrow anyone else's credibility.
    """
    origin: ObservationOrigin = "cv_provider" if provider else "unknown"
    provider_kind_literal: Any = provider_kind if provider_kind in ("heuristic_stub", "model") else None
    return ObservationProvenance(
        tag=tag,
        kind=kind,
        origin=origin,
        detail=detail,
        provider=provider,
        provider_kind=provider_kind_literal,
        provider_version=provider_version,
    )


def unattributed_observation(tag: str, *, kind: ObservationKind, detail: str | None = None) -> ObservationProvenance:
    """A tag that IS on the insights but whose producer this path cannot name.

    Recorded deliberately: an absent record and an unattributable one are different facts, and a
    consumer must be able to tell "nobody wrote provenance here" from "we looked and could not
    attribute it".
    """
    return ObservationProvenance(tag=tag, kind=kind, origin="unknown", detail=detail)


def retain_recorded_tags(insights: ListingInsights, observations: Iterable[ObservationProvenance]) -> list[ObservationProvenance]:
    """Keep only observations whose ``tag`` actually shipped in the matching insights list.

    Merges upstream (set unions, surface mappings, thresholds) can drop a tag after its
    provenance was built. A record pointing at a tag the reader cannot find is worse than no
    record, so it is discarded here rather than rendered as a dangling claim.
    """
    kept: list[ObservationProvenance] = []
    for obs in observations:
        list_name = _LIST_FOR_KIND.get(obs.kind)
        if list_name is None:  # pragma: no cover - ObservationKind is closed
            continue
        if obs.tag in getattr(insights, list_name, []):
            kept.append(obs)
    return kept


def attach(insights: ListingInsights, observations: Iterable[ObservationProvenance]) -> ListingInsights:
    """Return ``insights`` with a filtered, deduped, deterministically-ordered ledger attached.

    ``model_copy(update=...)`` rather than a field-by-field rebuild: rebuilding is how fields
    added later get silently dropped (Mission 2 root cause 2).
    """
    ledger = dedupe_and_sort(retain_recorded_tags(insights, observations))
    return insights.model_copy(update={"observations": ledger})


def stamp_uniform_origin(
    insights: ListingInsights,
    *,
    origin: ObservationOrigin,
    provider: str | None = None,
    provider_kind: str | None = None,
    provider_version: str | None = None,
    detail: str | None = None,
) -> ListingInsights:
    """Attribute EVERY tag on ``insights`` to one producer.

    For producers that author the whole object at once and expose no per-tag handle -- today the
    LLM path in ``agents/crewai_components``, which gets a JSON blob back and cannot say which
    sentence produced which tag. One origin for all tags is the honest description of that.
    """
    provider_kind_literal: Any = provider_kind if provider_kind in ("heuristic_stub", "model") else None
    records: list[ObservationProvenance] = []
    for kind, list_name in sorted(_LIST_FOR_KIND.items()):
        for tag in getattr(insights, list_name, []) or []:
            records.append(
                ObservationProvenance(
                    tag=str(tag),
                    kind=kind,
                    origin=origin,
                    detail=detail,
                    provider=provider,
                    provider_kind=provider_kind_literal,
                    provider_version=provider_version,
                )
            )
    return attach(insights, records)
