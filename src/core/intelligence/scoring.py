# src/core/intelligence/scoring.py

from __future__ import annotations

from .types import ScoreComponents

"""
Deterministic composite scoring

Computes a reproducible composite in [0, 1] from ScoreComponents using fixed
weights. Keep all math pure and side-effect free for snapshot stability.
"""


# Single source of truth for weights used across the app.
DEFAULT_WEIGHTS: dict[str, float] = {
    "media_quality": 0.40,
    "roi_index": 0.30,
    "neighborhood_safety": 0.20,
    "defect_penalty": -0.10,
}


def _clamp01(x: float) -> float:
    """Clamp a float to [0, 1] deterministically."""
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def compute_composite_score(
    c: ScoreComponents,
    weights: dict[str, float] = DEFAULT_WEIGHTS,
) -> float:
    """
    Compute a reproducible, clamped composite score in [0, 1].

    s = w_mq * media_quality
      + w_roi * roi_index
      + w_ns * neighborhood_safety
      + w_dp * defect_penalty   # usually negative

    The function is deliberately strict: missing keys will raise a KeyError to
    surface misconfigurations early in CI.
    """
    s = (
        float(weights["media_quality"]) * float(c.media_quality)
        + float(weights["roi_index"]) * float(c.roi_index)
        + float(weights["neighborhood_safety"]) * float(c.neighborhood_safety)
        + float(weights["defect_penalty"]) * float(c.defect_penalty)
    )
    return _clamp01(s)
