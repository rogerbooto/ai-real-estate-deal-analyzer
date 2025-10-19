# src/core/finance/amortization.py

from __future__ import annotations

from dataclasses import dataclass

_EPS = 1e-6  # for floating cleanup


@dataclass(frozen=True)
class YearDebt:
    year: int
    interest: float
    principal: float
    payment: float
    ending_balance: float


def _pad_to_horizon(rows: list[YearDebt], horizon_years: int) -> list[YearDebt]:
    """Pad with zero rows up to horizon (idempotent), then slice."""
    last_bal = rows[-1].ending_balance if rows else 0.0
    for y in range(len(rows) + 1, horizon_years + 1):
        rows.append(YearDebt(y, interest=0.0, principal=0.0, payment=0.0, ending_balance=last_bal))
    return rows[:horizon_years]


def amortization_payment(principal: float, rate: float, years: int) -> float:
    """Annual P&I payment for a fully amortizing loan (rate is annual fraction)."""
    if principal < 0:
        raise ValueError("principal must be >= 0")
    if years < 0:
        raise ValueError("years must be >= 0")
    if years == 0:
        return 0.0
    if rate <= 0:
        return principal / years
    r = rate
    return r * principal / (1.0 - (1.0 + r) ** (-years))


def amortization_schedule(
    principal: float,
    rate: float,
    amort_years: int,
    io_years: int,
    horizon_years: int,
) -> list[YearDebt]:
    """
    Annual schedule with optional interest-only front years, then amortization.
    All rates are annual fractions; payments are annual.
    """
    if principal < 0:
        raise ValueError("principal must be >= 0")
    if any(x < 0 for x in (amort_years, io_years, horizon_years)):
        raise ValueError("amort_years, io_years, and horizon_years must be >= 0")

    out: list[YearDebt] = []
    bal = float(principal)

    # IO years
    for y in range(1, io_years + 1):
        interest = bal * max(rate, 0.0)
        payment = interest  # IO means no principal
        out.append(YearDebt(y, interest=interest, principal=0.0, payment=payment, ending_balance=bal))

    # Amortizing years
    if amort_years > 0:
        pay = amortization_payment(bal, rate, amort_years)
        for i in range(1, amort_years + 1):
            y = io_years + i
            interest = bal * max(rate, 0.0)
            principal_pay = max(0.0, pay - interest)
            bal = max(0.0, bal - principal_pay)
            # Clean tiny residual drift
            if bal < _EPS:
                bal = 0.0
            out.append(YearDebt(y, interest=interest, principal=principal_pay, payment=pay, ending_balance=bal))

    return _pad_to_horizon(out, horizon_years)


def interest_only_schedule(
    principal: float,
    rate: float,
    io_years: int,
    horizon_years: int,
) -> list[YearDebt]:
    """IO-only convenience schedule (no amortization), padded to horizon."""
    if principal < 0:
        raise ValueError("principal must be >= 0")
    if any(x < 0 for x in (io_years, horizon_years)):
        raise ValueError("io_years and horizon_years must be >= 0")

    out: list[YearDebt] = []
    bal = float(principal)

    for y in range(1, io_years + 1):
        interest = bal * max(rate, 0.0)
        payment = interest
        out.append(YearDebt(y, interest=interest, principal=0.0, payment=payment, ending_balance=bal))

    return _pad_to_horizon(out, horizon_years)
