# src/core/intelligence/__init__.py

from __future__ import annotations

from .deal_fusion import DealIntelligence, fuse_deal_intelligence
from .scoring import DEFAULT_WEIGHTS, compute_composite_score
from .types import ScoreComponents  # re-export

__all__ = [
    "ScoreComponents",
    "compute_composite_score",
    "DEFAULT_WEIGHTS",
    "DealIntelligence",
    "fuse_deal_intelligence",
]
