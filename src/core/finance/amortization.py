# src/core/finance/amortization.py

from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

from .dual import coerce_like_float, expm1, log1p

_EPS = 1e-6  # for floating cleanup

# `amortization_payment`'s small-rate regime (Mission 5 Discovery defect fix).
#
# For `rate` below float64 machine epsilon (~2.22e-16), `1.0 + rate` rounds to exactly `1.0` in
# `(1.0 + r) ** (-years)`, so `1.0 - (1.0 + r) ** (-years)` is exactly `0.0` and the payment formula
# divides by zero. Above that, but still small, the same `1.0 + r` rounding silently discards
# low-order bits of `rate` -- no crash, but a wrong answer via catastrophic cancellation in
# `1 - (1+r)^-n`.
#
# Derivation of the threshold below which we switch to the numerically stable computation
# (`math.log1p` / `math.expm1`, see `_amortization_payment_stable`):
#
#   Computing `float(1.0 + r)` introduces an absolute rounding error of at most half an ULP of
#   1.0, i.e. `eps/2` where `eps = 2**-52 ~= 2.220446e-16` (IEEE-754 double, round-to-nearest).
#   Propagated through `(1+r)^-n` and then through the `1 - (...)` cancellation (whose result is
#   itself ~`n*r` for small r), the *relative* error surviving in the final payment is, to leading
#   order, `(eps/2) / r` -- notably independent of `n` (the `n` in the numerator and denominator of
#   that propagation cancels). This was verified two ways: (a) analytically, by first-order
#   sensitivity analysis of the formula to a perturbation in `1+r`; (b) empirically, against a
#   60-digit `mpmath` ground truth, across `years` in {1, 2, 5, 10, 30, 50, 100, 200} and principal
#   in {1, 1e5, 1e7} -- the measured relative error matched the `(eps/2)/r` prediction to within a
#   factor of ~2 and stayed within +/-1% across that entire `years`/`principal` grid, confirming
#   the n-independence.
#
#   Solving `(eps/2) / r <= REL_TOL` for the smallest r that keeps the *existing* formula's own
#   error under this codebase's own ratified money-drift budget (`REL_TOL = 1e-9`, see
#   `tests/core/finance/golden_tolerance.py` -- reused rather than inventing a second "how much
#   drift is acceptable" constant) gives `r* = eps / (2 * REL_TOL) ~= 1.110223e-7`.
#
#   `_SMALL_RATE_THRESHOLD = 1e-6` sits ~9x above that analytic crossover: comfortable margin
#   against the empirical grid's factor-of-~2 spread, while remaining far below the smallest
#   realistic financing rate this codebase models (`src/market/recourse.py`'s interest-rate lever
#   floors at 0.0 exactly and steps in units of 1-5 bps, i.e. >= 1e-4) or any rate exercised by the
#   golden/parity fixtures. Below the threshold, at the threshold itself and above it, the two
#   formulas were measured (see `tests/unit/test_amortization_small_rate.py::TestContinuityAcrossThreshold`)
#   to agree to a *relative* difference of ~8e-11 -- two orders of magnitude inside `REL_TOL` and,
#   on a real payment amount, many orders of magnitude below a cent. There is no visible discontinuity.
_SMALL_RATE_THRESHOLD = 1e-6


def _amortization_payment_stable(principal: float, rate: float, years: int) -> float:
    """Numerically stable small-`rate` computation of `amortization_payment`.

    Same formula, `r * P / (1 - (1+r)^-n)`, rewritten with `expm1`/`log1p` so it stays accurate
    (and never divides by an exact zero) all the way down to `rate` values many orders of magnitude
    below float64 epsilon:

        (1+r)^-n = exp(-n * log1p(r))
        1 - (1+r)^-n = -expm1(-n * log1p(r))

    `math.log1p(r)` computes `log(1+r)` accurately for small `r` without first forming `1+r` (which
    is exactly the operation that loses `r`'s low-order bits in the naive formula); `math.expm1(x)`
    computes `exp(x)-1` accurately for small `x` without the cancellation of subtracting two
    numbers close to 1. Verified against 60-digit `mpmath` ground truth to hold ~1e-16 relative
    accuracy across `rate` from `1e-1` down to `1e-19` (the exact-zero floor of this rewritten
    formula is `rate = 0.0`, already handled by the caller's separate `rate <= 0` branch).

    DUAL-GENERIC (Mission 5 Gate V, B1). This branch sits on the engine's AD seam --
    `engine._forecast_core` hands `schedule_columns` the SEEDED rate, so a `Dual4` rate below
    `_SMALL_RATE_THRESHOLD` lands here -- and `math.log1p`/`math.expm1` raise `TypeError` on a
    Dual4 (which refuses `__float__` by design). `dual.log1p`/`dual.expm1` are those exact
    primitives extended with their exact dual forms: for a float they call the `math` function
    bit-for-bit, and for a Dual4 the primal IS that same `math` call on `rate.re` -- so the
    numerically stable primal this branch exists for is preserved unchanged, and the derivative
    comes out exact rather than degraded. Pinned by
    `tests/unit/test_amortization_small_rate.py::TestDualRate` and the sub-threshold-rate case
    in `tests/core/finance/test_jacobian.py`.
    """
    denom = -expm1(-years * log1p(rate))
    return rate * principal / denom


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
    if rate < _SMALL_RATE_THRESHOLD:
        return _amortization_payment_stable(principal, rate, years)
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
    # `coerce_like_float` (Mission 5, IA.1a): `float(x)` bit-for-bit for real numbers -- the
    # pre-existing behaviour -- but a pass-through for a `Dual4` principal on the engine's dual
    # pass, where a bare `float()` would silently truncate the loan tangent (`Dual4` refuses
    # `__float__` for exactly that reason; this is the sanctioned coercion point).
    bal = coerce_like_float(principal)

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
