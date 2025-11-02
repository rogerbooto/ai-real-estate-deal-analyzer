from pathlib import Path

from src.core.finance.adapters import FinanceSummary, finance_summary_from_json


def test_finance_flat_parses_and_coerces():
    src = Path("tests/data/finance_flat.json")
    fs = finance_summary_from_json(src)
    assert isinstance(fs, FinanceSummary)
    # defaults
    assert fs.area_safety_index == 0.5
    # coercions
    assert fs.irr == 0.12
    assert fs.cashflow_monthly == 350.0
    assert fs.price_per_sqft == 220.5
    assert fs.market_ppsf == 240.0
    assert fs.purchase_price == 350000.0


def test_finance_nested_parses_and_coerces():
    src = Path("tests/data/finance_nested.json")
    fs = finance_summary_from_json(src)
    assert isinstance(fs, FinanceSummary)
    assert fs.area_safety_index == 0.62
    assert fs.irr == 0.15
    assert fs.cashflow_monthly == 425.0
    assert fs.price_per_sqft == 210.0
    assert fs.market_ppsf == 235.5
    assert fs.purchase_price == 410000.0
