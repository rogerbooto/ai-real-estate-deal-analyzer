# src/core/finance/amortization.py

from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

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


class DebtColumns(NamedTuple):
    """The same schedule as `amortization_schedule`, as four parallel float lists.

    PERF (Mission 4, PV.3). `src/core/finance/engine.py` reads exactly four numbers per year off
    the debt schedule and never touches a `YearDebt` object as an object. Building one per year
    -- a frozen dataclass, so five `object.__setattr__` calls each -- cost ~53 us of a ~243 us
    portfolio-scale run, over a fifth of the total, purely to wrap floats the caller immediately
    unwraps. These are those floats. `amortization_schedule` is unchanged as the public API and
    is now a thin wrapper over this, so there is ONE schedule implementation, not two: the
    arithmetic below is the original's, statement for statement and in the same order.
    """

    payment: list[float]
    principal: list[float]
    interest: list[float]
    ending_balance: list[float]


def schedule_columns(
    principal: float,
    rate: float,
    amort_years: int,
    io_years: int,
    horizon_years: int,
) -> DebtColumns:
    """Column-oriented form of `amortization_schedule`. See `DebtColumns`."""
    if principal < 0:
        raise ValueError("principal must be >= 0")
    if any(x < 0 for x in (amort_years, io_years, horizon_years)):
        raise ValueError("amort_years, io_years, and horizon_years must be >= 0")

    payments: list[float] = []
    principals: list[float] = []
    interests: list[float] = []
    balances: list[float] = []
    bal = float(principal)

    # `max(rate, 0.0)` is loop-invariant; hoisted out, it is the identical float every iteration
    # used to recompute.
    eff_rate = max(rate, 0.0)

    # IO years
    for _ in range(io_years):
        interest = bal * eff_rate
        interests.append(interest)
        principals.append(0.0)
        payments.append(interest)  # IO means no principal
        balances.append(bal)

    # Amortizing years
    if amort_years > 0:
        pay = amortization_payment(bal, rate, amort_years)
        for _ in range(amort_years):
            interest = bal * eff_rate
            principal_pay = max(0.0, pay - interest)
            bal = max(0.0, bal - principal_pay)
            # Clean tiny residual drift
            if bal < _EPS:
                bal = 0.0
            interests.append(interest)
            principals.append(principal_pay)
            payments.append(pay)
            balances.append(bal)

    # Pad with zero rows up to horizon (idempotent), then slice -- `_pad_to_horizon`'s behaviour.
    n = len(payments)
    if n < horizon_years:
        last_bal = balances[-1] if balances else 0.0
        pad = horizon_years - n
        zeros = [0.0] * pad
        interests += zeros
        principals += zeros
        payments += zeros
        balances += [last_bal] * pad
    elif n > horizon_years:
        del payments[horizon_years:], principals[horizon_years:], interests[horizon_years:], balances[horizon_years:]

    return DebtColumns(payment=payments, principal=principals, interest=interests, ending_balance=balances)


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
    cols = schedule_columns(principal, rate, amort_years, io_years, horizon_years)
    return [
        YearDebt(y, interest=i, principal=p, payment=pay, ending_balance=b)
        for y, (pay, p, i, b) in enumerate(zip(cols.payment, cols.principal, cols.interest, cols.ending_balance, strict=True), start=1)
    ]


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
