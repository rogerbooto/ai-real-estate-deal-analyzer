from __future__ import annotations

import math

from src.market.regional_income import build_regional_income
from src.schemas.models import RegionalIncomeTable


def test_regional_income_basic() -> None:
    region = "Metro A"
    bedrooms = 2
    comps = [1500.0, 1550.0, 1600.0, 1700.0, 1800.0]

    tbl = build_regional_income(region, bedrooms, comps)
    assert isinstance(tbl, RegionalIncomeTable)

    # Median of [1500,1550,1600,1700,1800] is 1600
    assert math.isclose(tbl.median_rent, 1600.0, rel_tol=1e-9)

    # P25 ≈ 1550, P75 ≈ 1725 by linear interpolation
    assert math.isclose(tbl.p25_rent, 1550.0, rel_tol=1e-9)
    assert math.isclose(tbl.p75_rent, 1700.0, rel_tol=1e-9)

    # turnover = 0.5 * median
    assert math.isclose(tbl.turnover_cost, 800.0, rel_tol=1e-9)

    # Milestone A policy = STR allowed everywhere → multiplier present
    assert tbl.str_multiplier is not None
    assert math.isclose(tbl.str_multiplier or 0.0, 1.5, rel_tol=1e-9)
    assert "RegionalIncomeTable" in tbl.summary()


def test_regional_income_validation() -> None:
    try:
        build_regional_income("", 2, [1000.0, 1100.0])
        assert False, "Expected ValueError for empty region"
    except ValueError as e:
        assert "region" in str(e)

    try:
        build_regional_income("Metro B", 0, [1000.0])
        assert False, "Expected ValueError for bedrooms <= 0"
    except ValueError as e:
        assert "bedrooms" in str(e)

    try:
        build_regional_income("Metro C", 2, [])
        assert False, "Expected ValueError for empty comps"
    except ValueError as e:
        assert "comps" in str(e)

    try:
        build_regional_income("Metro D", 2, [1200.0, -10.0])
        assert False, "Expected ValueError for negative comp"
    except ValueError as e:
        assert "comps" in str(e)
