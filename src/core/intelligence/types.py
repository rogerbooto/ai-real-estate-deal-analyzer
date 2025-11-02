# src/core/intelligence/types.py

from __future__ import annotations

from pydantic import BaseModel


# -----------------------------
# Data containers (public API)
# -----------------------------
class ScoreComponents(BaseModel):
    """Deterministic components that feed the composite score."""

    media_quality: float = 0.0  # [0,1] — from photo quality flags
    roi_index: float = 0.0  # [0,1] — proxy using finance IRR (already a fraction if provided)
    neighborhood_safety: float = 0.5  # [0,1] — optional finance-derived index, default mid
    defect_penalty: float = 0.0  # [0,1] — higher means worse
