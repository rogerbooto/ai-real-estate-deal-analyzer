# tests/unit/test_irr_edges.py


from src.core.finance.irr import irr


def test_irr_empty_or_single_cashflow_returns_zeros():
    assert irr([]) is None
    assert irr([100.0]) is None


def test_irr_simple_case_monotonic():
    # -1000 today, +1100 in one year ≈ 10%
    from datetime import date, timedelta

    d0 = date(2024, 1, 1)
    d1 = d0 + timedelta(days=365)
    rate = irr([(-1000.0, d0), (1100.0, d1)])
    assert rate is not None
    assert 0.09 <= rate <= 0.11
