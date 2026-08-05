from __future__ import annotations

import statistics
from collections.abc import Sequence
from typing import cast

import numpy as np

from src.schemas.models import RegionalIncomeTable


def _validate(region: str, bedrooms: int, comps: Sequence[float]) -> None:
    if not region or not isinstance(region, str):
        raise ValueError("region must be a non-empty string")
    if bedrooms <= 0:
        raise ValueError("bedrooms must be a positive integer")
    if len(comps) == 0:
        raise ValueError("comps must be a non-empty sequence of numbers")
    if any(c <= 0 for c in comps):
        raise ValueError("all comps must be positive numbers")


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

    ``RegionalIncomeTable.str_multiplier`` is always ``None``: Gate 3 (mission/2-wiring-gaps) found
    the previous ``1.5x`` value fabricated -- gated by ``_region_allows_str``, a "placeholder policy
    hook" whose entire body was ``return True``, in a jurisdiction (New Brunswick) that regulates
    short-term rentals -- so this builder no longer invents one.

    ``RegionalIncomeTable.turnover_cost`` remains a *required* field on the schema (it predates this
    finding and removing it would touch `src/schemas/models.py`, which this project treats as
    additive-only), so it still gets a value here for schema validity. It is a rule-of-thumb
    (``median_rent * 0.5``) that Gate 3 also found uncited, and callers must not surface it: see
    ``src.cli.advisor_cli._regional_income_payload``/``_regional_income_summary``, which are the
    only production consumers of this function's output and deliberately exclude both fields.
    """
    _validate(region, bedrooms, comps)

    median_rent = float(statistics.median(comps))
    p25_rent = float(cast(float, np.percentile(comps, 25)))
    p75_rent = float(cast(float, np.percentile(comps, 75)))
    turnover_cost = median_rent * 0.5

    return RegionalIncomeTable(
        region=region,
        bedrooms=bedrooms,
        median_rent=median_rent,
        p25_rent=p25_rent,
        p75_rent=p75_rent,
        turnover_cost=turnover_cost,
        str_multiplier=None,
    )
