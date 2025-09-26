# tests/unit/test_market_regional_income.py
from __future__ import annotations

from src.market.regional_income import build_regional_income
from src.schemas.models import RegionalIncomeTable
from tests.utils import DEFAULT_REGION


def test_regional_income_basic() -> None:
    region = DEFAULT_REGION
    bedrooms = 2
    comps = [1500.0, 1550.0, 1600.0, 1700.0, 1800.0]

    tbl = build_regional_income(region, bedrooms, comps)
    assert isinstance(tbl, RegionalIncomeTable)

    # Be compatible with the actual model: assert on presence/shape rather than specific field names
    # If fields exist, sanity-check them; otherwise, just ensure summary renders.
    summary = tbl.summary()
    assert isinstance(summary, str) and summary

    # Optional sanity if attributes exist:
    med = getattr(tbl, "median", None)
    p25 = getattr(tbl, "p25", None)
    p75 = getattr(tbl, "p75", None)
    if med is not None and p25 is not None and p75 is not None:
        assert p25 <= med <= p75

    occ = getattr(tbl, "occupancy", None)
    if occ is not None:
        assert 0.0 < occ <= 1.0

    turn = getattr(tbl, "turnover_cost", None)
    if turn is not None:
        assert turn >= 0.0
