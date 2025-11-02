# src/core/advisor/__init__.py

from typing import Any

__all__ = ("rank_deals", "portfolio_summary", "compute_risk_flags")


def rank_deals(*args: Any, **kwargs: Any) -> Any:
    from .recommender import rank_deals as _rank_deals

    return _rank_deals(*args, **kwargs)


def portfolio_summary(*args: Any, **kwargs: Any) -> Any:
    from .portfolio import portfolio_summary as _portfolio_summary

    return _portfolio_summary(*args, **kwargs)


def compute_risk_flags(*args: Any, **kwargs: Any) -> Any:
    from .risk import compute_risk_flags as _compute_risk_flags

    return _compute_risk_flags(*args, **kwargs)
