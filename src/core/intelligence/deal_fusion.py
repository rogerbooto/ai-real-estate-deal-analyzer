# src/core/intelligence/deal_fusion.py

from __future__ import annotations

from typing import SupportsFloat, SupportsInt

from pydantic import BaseModel

from src.core.advisor.risk import compute_risk_flags
from src.core.finance.adapters import FinanceSummary
from src.schemas.models import ListingNormalized, PhotoInsights

from .scoring import DEFAULT_WEIGHTS, compute_composite_score
from .types import ScoreComponents


class DealIntelligence(BaseModel):
    """Unified, deterministic view of a deal suitable for narratives & ranking."""

    listing: ListingNormalized
    photos: PhotoInsights
    finance: FinanceSummary
    score_components: ScoreComponents
    composite_score: float
    risk_flags: list[str]
    notes: list[str] = []


# -----------------------------
# Helpers (pure, deterministic)
# -----------------------------
def _avg_quality(q: dict[str, float]) -> float:
    """Average known quality flags. Empty → 0.0."""
    if not q:
        return 0.0
    # values are validated in PhotoInsights to be in [0,1]
    return sum(q.values()) / float(len(q))


def _defect_penalty(defects: dict[str, int]) -> float:
    """
    Simple, transparent penalty:
      0.25 per *distinct* defect label, capped at 1.0.
    Deterministic & easy to reason about.
    """
    return min(1.0, 0.25 * float(len(defects or {})))


def _safe_float(x: SupportsFloat | SupportsInt | str | None, default: float) -> float:
    """Safely cast to float; on failure, return default."""
    if x is None:
        return default

    if isinstance(x, (float | int)):
        return float(x)

    if isinstance(x, str):
        try:
            return float(x)
        except ValueError:
            return default

    # Handling of custom classes or numpy types that implement  __float_
    if isinstance(x, SupportsFloat):
        try:
            return float(x)
        except Exception:
            return default

    # Handling of custom classes that implement __int__
    if isinstance(x, SupportsInt):
        try:
            return float(int(x))
        except Exception:
            return default

    return default


# -----------------------------
# Main fusion (pure function)
# -----------------------------
def fuse_deal_intelligence(
    listing: ListingNormalized, photos: PhotoInsights, finance: FinanceSummary, raw_text: str | None = None
) -> DealIntelligence:
    """
    Deterministically compute score components and risk flags from structured inputs only.
    No network, no randomness. All lists are sorted for snapshot stability.
    """

    media_quality = _avg_quality(photos.quality_flags)
    roi_index = _safe_float(getattr(finance, "irr", 0.0), 0.0)
    neighborhood_safety = _safe_float(getattr(finance, "area_safety_index", 0.5), 0.5)
    defect_pen = _defect_penalty(photos.defect_counts)

    comps = ScoreComponents(
        media_quality=media_quality,
        roi_index=roi_index,
        neighborhood_safety=neighborhood_safety,
        defect_penalty=defect_pen,
    )

    composite = compute_composite_score(comps, DEFAULT_WEIGHTS)

    risks: list[str] = []

    risks = compute_risk_flags(listing=listing, photos=photos, finance=finance, raw_text=raw_text)

    # Listing notes (idempotent & sorted)
    raw_notes = getattr(listing, "notes", None)
    notes: list[str] = []
    if isinstance(raw_notes, str) and raw_notes.strip():
        # Accept semicolon-delimited or newline-delimited notes; normalize + sort
        parts: list[str] = []
        for chunk in raw_notes.replace("\r", "").split("\n"):
            parts.extend(x.strip() for x in chunk.split(";"))
        notes = sorted([x for x in parts if x])

    return DealIntelligence(
        listing=listing,
        photos=photos,
        finance=finance,
        score_components=comps,
        composite_score=composite,
        risk_flags=risks,
        notes=notes,
    )
