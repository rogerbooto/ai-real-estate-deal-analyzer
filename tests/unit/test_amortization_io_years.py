from src.core.finance.amortization import amortization_schedule


def test_interest_only_years_then_amortize():
    loan = 100_000.0
    rate = 0.06
    sched = amortization_schedule(
        principal=loan,
        rate=rate,
        amort_years=30,
        io_years=2,  # cover IO branch
        horizon_years=5,
    )

    # First two years should be interest-only: payment == interest, principal ~ 0
    y1, y2, y3 = sched[0], sched[1], sched[2]
    assert abs(y1.payment - y1.interest) < 1e-6 and abs(y1.principal) < 1e-6
    assert abs(y2.payment - y2.interest) < 1e-6 and abs(y2.principal) < 1e-6

    # After IO period, principal should start amortizing
    assert y3.principal > 0.0
    assert y3.payment > y3.interest
