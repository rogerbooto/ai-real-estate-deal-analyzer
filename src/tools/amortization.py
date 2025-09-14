# src/tools/amortization.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass(frozen=True)
class PaymentBreakdown:
    """
    Immutable record of a single monthly payment.

    Attributes:
        month (int): 1-based month index.
        interest (float): Interest paid this month.
        principal (float): Principal paid this month.
        total (float): Total payment this month (interest + principal).
        balance (float): Remaining principal balance after this month's payment.
    """
    month: int
    interest: float
    principal: float
    total: float
    balance: float


def monthly_payment(principal: float, annual_rate: float, years: int) -> float:
    """
    Compute the constant monthly payment for a fully-amortizing fixed-rate loan.

    Formula (standard annuity):
        PMT = [ P * r * (1 + r)^n ] / [ (1 + r)^n - 1 ]

    Where:
        PMT = monthly payment (principal + interest)
        P   = principal (initial loan balance)
        r   = monthly interest rate = annual_rate / 12
        n   = total number of monthly payments = years * 12

    Intuition:
        - The numerator (P * r * (1+r)^n) scales the periodic interest by the growth factor.
        - The denominator ((1+r)^n - 1) amortizes the loan over a finite horizon (n months).
          Without this denominator, you would be computing perpetual interest.

    Args:
        principal: Starting loan balance (> 0).
        annual_rate: APR as a fraction (e.g., 0.045 for 4.5%).
        years: Amortization term in years (excludes any IO period).

    Returns:
        The fixed monthly P&I payment.

    Notes:
        - If annual_rate == 0, the formula reduces to principal / n.
        - Interest-only (IO) periods are modeled separately in generate_schedule().
    """
    if principal <= 0:
        return 0.0
    if years <= 0:
        raise ValueError("Amortization years must be > 0 for a fully-amortizing schedule.")

    r = annual_rate / 12.0
    n = years * 12

    if r == 0:
        return principal / n

    num = principal * r * (1 + r) ** n
    den = (1 + r) ** n - 1
    return num / den


def generate_schedule(
    principal: float,
    annual_rate: float,
    amort_years: int,
    io_years: int = 0,
) -> List[PaymentBreakdown]:
    """
    Build a monthly amortization schedule with an optional initial interest-only (IO) period.

    Model:
        - During IO months: payment = principal * r, principal does not change.
        - After IO: switch to fully-amortizing payments over remaining amort_years.

    Args:
        principal: Initial balance.
        annual_rate: APR as a fraction (e.g., 0.05 = 5%).
        amort_years: Amortization years after any IO period (can be 0 for pure IO loans).
        io_years: Interest-only years at the start of the loan.

    Returns:
        List[PaymentBreakdown]: One entry per month (IO months first, then amortization months).

    Notes:
        - If amort_years == 0, the schedule will be purely IO (no principal reduction).
        - We guard the final month for rounding so the balance never becomes negative.
    """
    if principal <= 0:
        return []
    if amort_years < 0 or io_years < 0:
        raise ValueError("Years cannot be negative.")

    r = annual_rate / 12.0
    schedule: List[PaymentBreakdown] = []
    bal = principal
    month = 0

    # --- Interest-Only period ---
    io_months = io_years * 12
    for _ in range(io_months):
        month += 1
        interest = bal * r
        principal_paid = 0.0
        total = interest
        schedule.append(PaymentBreakdown(month, interest, principal_paid, total, bal))

    # --- Amortization period ---
    if amort_years > 0:
        n_amort_months = amort_years * 12
        pmt = monthly_payment(bal, annual_rate, amort_years)
        for _ in range(n_amort_months):
            month += 1
            interest = bal * r
            principal_paid = max(0.0, pmt - interest)
            # Guard for rounding drift in the final payment
            if principal_paid > bal:
                principal_paid = bal
                pmt = interest + principal_paid
            bal = max(0.0, bal - principal_paid)
            schedule.append(PaymentBreakdown(month, interest, principal_paid, pmt, bal))

    return schedule


def annual_debt_service_and_split(
    schedule: List[PaymentBreakdown],
    year_index: int,
) -> Tuple[float, float, float]:
    """
    Aggregate annual debt service for a given 1-based year.

    Definitions:
        - Debt Service (DS) for the year = sum of monthly totals (interest + principal).
        - Interest paid = sum of monthly interest.
        - Principal paid = sum of monthly principal.

    Args:
        schedule: Full monthly schedule from generate_schedule().
        year_index: 1-based year index (Year 1, Year 2, ...).

    Returns:
        (total_debt_service_year, interest_paid_year, principal_paid_year)

    Notes:
        - If year_index exceeds the schedule length, returns zeros.
        - This is used to compute DSCR and cash flow per Year in the pro forma.
    """
    if year_index <= 0:
        raise ValueError("year_index is 1-based (Year 1, Year 2, ...).")

    start = (year_index - 1) * 12
    end = min(len(schedule), year_index * 12)
    if start >= len(schedule):
        return (0.0, 0.0, 0.0)

    total = sum(p.total for p in schedule[start:end])
    interest = sum(p.interest for p in schedule[start:end])
    principal = sum(p.principal for p in schedule[start:end])
    return (total, interest, principal)


def balance_after_years(schedule: List[PaymentBreakdown], years_elapsed: int) -> float:
    """
    Get the ending principal balance after a whole number of years.

    Args:
        schedule: Full monthly schedule from generate_schedule().
        years_elapsed: Whole years since loan start (0, 1, 2, ...).

    Returns:
        Ending balance after years_elapsed years (clamped to schedule length).
    """
    if not schedule:
        return 0.0
    if years_elapsed <= 0:
        # End of month 0 is the original principal; first record holds end of month 1.
        return schedule[0].balance
    cutoff = min(len(schedule), years_elapsed * 12)
    return schedule[cutoff - 1].balance


def remaining_term_years(schedule: List[PaymentBreakdown], from_year: int) -> int:
    """
    Compute remaining full years in the schedule after a given 1-based year.

    Args:
        schedule: Full monthly schedule.
        from_year: 1-based year after which we measure remaining time (e.g., at refi).

    Returns:
        Remaining whole years (floor division of remaining months by 12).

    Notes:
        Useful for modeling a refinance: you may size the new loan and
        optionally compute a new amortization term from the remaining months.
    """
    total_months = len(schedule)
    months_elapsed = min(from_year * 12, total_months)
    remaining_months = max(0, total_months - months_elapsed)
    return remaining_months // 12
