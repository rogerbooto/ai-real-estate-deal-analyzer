# tests/test_amortization.py
import pytest
from src.tools.amortization import (
    monthly_payment,
    generate_schedule,
    annual_debt_service_and_split,
    balance_after_years,
)

def test_monthly_payment_basic():
    pmt = monthly_payment(300_000, 0.06, 30)  # common mortgage
    assert 1790 < pmt < 1800  # ~1798.65

def test_schedule_lengths_io_then_amort():
    sched = generate_schedule(200_000, 0.05, amort_years=30, io_years=2)
    assert len(sched) == (2 * 12) + (30 * 12)
    # First month IO: principal should be zero
    assert abs(sched[0].principal - 0.0) < 1e-9
    # Month after IO should have principal > 0
    assert sched[24].principal > 0.0

def test_year1_totals_no_io():
    sched = generate_schedule(120_000, 0.04, amort_years=20, io_years=0)
    total, interest, principal = annual_debt_service_and_split(sched, 1)
    assert abs(total - sum(p.total for p in sched[:12])) < 1e-6
    assert abs(interest + principal - total) < 1e-6

def test_balance_after_5_years_with_io():
    sched = generate_schedule(500_000, 0.045, amort_years=30, io_years=1)
    bal_5 = balance_after_years(sched, 5)
    # After 1 IO year + 4 amort years, balance should be < original
    assert 0 < bal_5 < 500_000

def test_one_year_term():
    sched = generate_schedule(12_000, 0.06, amort_years=1, io_years=0)
    # Should have exactly 12 months
    assert len(sched) == 12
    # Last balance should be zero
    assert sched[-1].balance == pytest.approx(0.0, abs=1e-6)

def test_pure_io_then_no_amortization():
    sched = generate_schedule(50_000, 0.05, amort_years=0, io_years=3)
    # 3 years of IO only
    assert len(sched) == 36
    # Balance should never change
    balances = {p.balance for p in sched}
    assert balances == {50_000}

def test_zero_interest_rate():
    # 2 year loan, zero rate → simply principal / n
    sched = generate_schedule(24_000, 0.0, amort_years=2, io_years=0)
    assert len(sched) == 24
    pmts = {p.total for p in sched}
    # All payments equal to 1000
    assert pmts == {1000.0}
    # Balance should hit zero at the end
    assert sched[-1].balance == pytest.approx(0.0, abs=1e-6)

def test_last_balance_zero_except_pure_io():
    # Standard amortizing loan
    sched = generate_schedule(100_000, 0.05, amort_years=10, io_years=0)
    assert sched[-1].balance == pytest.approx(0.0, abs=1e-6)

    # Loan with IO then amortization should still end at zero
    sched_io = generate_schedule(100_000, 0.05, amort_years=10, io_years=2)
    assert sched_io[-1].balance == pytest.approx(0.0, abs=1e-6)

    # Pure IO (no amortization) should not end at zero
    sched_pure_io = generate_schedule(100_000, 0.05, amort_years=0, io_years=2)
    assert sched_pure_io[-1].balance == pytest.approx(100_000, abs=1e-6)