from __future__ import annotations

import statistics
from collections.abc import Sequence
from typing import Final, cast

import numpy as np

from src.schemas.models import RegionalIncomeTable

_DEFAULT_STR_MULTIPLIER: Final[float] = 1.5


def _validate(region: str, bedrooms: int, comps: Sequence[float]) -> None:
    if not region or not isinstance(region, str):
        raise ValueError("region must be a non-empty string")
    if bedrooms <= 0:
        raise ValueError("bedrooms must be a positive integer")
    if len(comps) == 0:
        raise ValueError("comps must be a non-empty sequence of numbers")
    if any(c <= 0 for c in comps):
        raise ValueError("all comps must be positive numbers")


def _region_allows_str(_: str) -> bool:
    """
    Placeholder policy hook.
    Deterministically returns True (allowed everywhere) for Milestone A.
    Replace with policy lookups in later milestones.
    """
    return True


def build_regional_income(
    region: str,
    bedrooms: int,
    comps: Sequence[float],
) -> RegionalIncomeTable:
    """
    Deterministic builder:
      - median_rent = statistics.median(comps)
      - p25_rent = np.percentile(comps, 25)
      - p75_rent = np.percentile(comps, 75)
      - turnover_cost = median_rent * 0.5
      - str_multiplier = 1.5 if region allows STR else None
    """
    _validate(region, bedrooms, comps)

    median_rent = float(statistics.median(comps))
    p25_rent = float(cast(float, np.percentile(comps, 25)))
    p75_rent = float(cast(float, np.percentile(comps, 75)))
    turnover_cost = median_rent * 0.5

    str_multiplier: float | None = (
        _DEFAULT_STR_MULTIPLIER if _region_allows_str(region) else None
    )

    return RegionalIncomeTable(
        region=region,
        bedrooms=bedrooms,
        median_rent=median_rent,
        p25_rent=p25_rent,
        p75_rent=p75_rent,
        turnover_cost=turnover_cost,
        str_multiplier=str_multiplier,
    )
