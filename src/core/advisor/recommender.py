# src/core/advisor/recommender.py
from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Type-only import to avoid runtime circular dependency
    from src.core.intelligence.deal_fusion import DealIntelligence  # noqa: F401


def _coerce_score(x: Any) -> float:
    """
    Convert a duck-typed score to float, falling back to 0.0 on None/invalid.
    Accepts numeric types or numeric strings.
    """
    if isinstance(x, (int | float)):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x)
        except ValueError:
            return 0.0
    return 0.0


def rank_deals(deals: Iterable[Any]) -> list[tuple[Any, float]]:
    """
    Rank deals by their composite score (duck-typed).
    We don't import DealIntelligence at runtime to avoid circular imports.
    """
    scored: list[tuple[Any, float]] = []
    for d in deals:
        # Prefer 'composite_score'; fall back to 'score'; else 0.0
        score = getattr(d, "composite_score", None)
        if score is None:
            score = getattr(d, "score", 0.0)

        raw_score = getattr(d, "composite_score", None)

        if raw_score is None:
            raw_score = getattr(d, "score", 0.0)

        scored.append((d, _coerce_score(raw_score)))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored
