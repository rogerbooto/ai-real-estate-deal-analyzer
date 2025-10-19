# tests/unit/test_amortization.py
import pytest

from src.core.finance.amortization import (
    amortization_payment,
    amortization_schedule,
    interest_only_schedule,
)


def test_amortization_payment_basic():
    # Annual payment for 300k @ 6% over 30 years
    pmt = amortization_payment(300_000, 0.06, 30)
    # ≈ 21,798
    assert 21_700 < pmt < 21_900


def test_schedule_lengths_io_then_amort():
    # 2 years IO, then 30 years amort → horizon 32 years total
    sched = amortization_schedule(200_000, 0.05, amort_years=30, io_years=2, horizon_years=32)
    assert len(sched) == 32
    # First year IO: principal should be zero
    assert abs(sched[0].principal - 0.0) < 1e-9
    # First amortizing year (year 3): principal > 0
    assert sched[2].principal > 0.0


def test_year1_totals_no_io():
    sched = amortization_schedule(120_000, 0.04, amort_years=20, io_years=0, horizon_years=20)
    y1 = sched[0]
    # payment = principal + interest (by construction)
    assert abs((y1.principal + y1.interest) - y1.payment) < 1e-9


def test_balance_after_5_years_with_io():
    sched = amortization_schedule(500_000, 0.045, amort_years=30, io_years=1, horizon_years=31)
    # After 1 IO year + 4 amort years → end of year 5 = index 4
    bal_5 = sched[4].ending_balance
    assert 0 < bal_5 < 500_000


def test_one_year_term():
    sched = amortization_schedule(12_000, 0.06, amort_years=1, io_years=0, horizon_years=1)
    assert len(sched) == 1
    assert sched[-1].ending_balance == pytest.approx(0.0, abs=1e-6)


def test_pure_io_then_no_amortization():
    sched = interest_only_schedule(50_000, 0.05, io_years=3, horizon_years=3)
    # Balance should never change
    balances = {p.ending_balance for p in sched}
    assert balances == {50_000}


def test_zero_interest_rate():
    # 2-year amortizing loan, zero rate → payment = principal / years
    sched = amortization_schedule(24_000, 0.0, amort_years=2, io_years=0, horizon_years=2)
    payments = {p.payment for p in sched}
    assert payments == {12_000.0}
    assert sched[-1].ending_balance == pytest.approx(0.0, abs=1e-6)


def test_last_balance_zero_except_pure_io():
    # Standard amortizing loan
    sched = amortization_schedule(100_000, 0.05, amort_years=10, io_years=0, horizon_years=10)
    assert sched[-1].ending_balance == pytest.approx(0.0, abs=1e-6)

    # IO then amortization should still end at zero
    sched_io = amortization_schedule(100_000, 0.05, amort_years=10, io_years=2, horizon_years=12)
    assert sched_io[-1].ending_balance == pytest.approx(0.0, abs=1e-6)

    # Pure IO (no amortization) should not end at zero
    sched_pure_io = interest_only_schedule(100_000, 0.05, io_years=2, horizon_years=2)
    assert sched_pure_io[-1].ending_balance == pytest.approx(100_000, abs=1e-6)
