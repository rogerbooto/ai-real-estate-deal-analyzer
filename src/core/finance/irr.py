from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from typing import cast

CashFlowItem = float | tuple[float, date | datetime | float]
CashFlows = Iterable[CashFlowItem]


def _to_years(t0: date | datetime | float, t: date | datetime | float) -> float:
    """Convert two time markers into a year fraction."""
    # numeric → already a year offset
    if isinstance(t0, int | float) and isinstance(t, int | float):
        return float(t) - float(t0)

    # date/datetime → day count / 365.0
    if isinstance(t0, datetime):
        base = t0
    elif isinstance(t0, date):
        base = datetime(t0.year, t0.month, t0.day)
    else:
        # fallback: treat as zero and return numeric t as-is
        return float(t) if isinstance(t, int | float) else 0.0

    if isinstance(t, datetime):
        other = t
    elif isinstance(t, date):
        other = datetime(t.year, t.month, t.day)
    else:
        # fallback for mixed types
        return float(t) if isinstance(t, int | float) else 0.0

    return (other - base).days / 365.0


def irr(cash_flows: CashFlows, *, max_iter: int = 100, tol: float = 1e-6) -> float | None:
    """
    Compute annual IRR (Internal Rate of Return).
    Uses Newton-Raphson with a fallback bisection if non-convergent.

    Accepts either:
      - An iterable of cash amounts at integer periods, e.g. [-1000, 200, 200, ...]
      - An iterable of (amount, time) where time is a date/datetime or a numeric
        year offset, e.g. [(-1000, date(2024,1,1)), (1100, date(2025,1,1))]

    Returns:
      IRR as a decimal (0.12 for 12%), or None if undefined / not bracketing / no convergence.
    """
    # Normalize input
    try:
        raw: list[CashFlowItem] = list(cash_flows)
    except TypeError:
        return None

    if len(raw) < 2:
        return None

    # Detect format
    is_tuple = isinstance(raw[0], tuple | list) and len(raw[0]) == 2

    if is_tuple:
        # Dated cash flows: align times to the first timestamp
        amounts: list[float] = []
        times: list[float] = []
        t0 = cast(tuple[float, date | datetime | float], raw[0])[1]
        for item in raw:
            amt, current_t = cast(tuple[float, date | datetime | float], item)
            amounts.append(float(amt))
            times.append(_to_years(t0, current_t))
    else:
        # Simple periodic cash flows at integer periods 0..n
        amounts = [float(cast(float, x)) for x in raw]
        times = [float(i) for i in range(len(amounts))]

    # Must have sign change to have a real IRR
    has_pos = any(a > 0 for a in amounts)
    has_neg = any(a < 0 for a in amounts)
    if not (has_pos and has_neg):
        return None

    def npv(rate: float) -> float:
        return float(sum(a / ((1.0 + rate) ** t) for a, t in zip(amounts, times, strict=False)))

    def dnpv(rate: float) -> float:
        # derivative of NPV w.r.t. rate
        return float(sum(-t * a / ((1.0 + rate) ** (t + 1.0)) for a, t in zip(amounts, times, strict=False) if t != 0.0))

    # Newton-Raphson
    r = 0.10
    for _ in range(max_iter):
        f = npv(r)
        df = dnpv(r)
        if abs(df) < 1e-12:
            break
        new_r = r - f / df
        if abs(new_r - r) < tol:
            return new_r
        r = new_r

    # Bisection fallback: look for a bracket with opposite signs.
    # Start with a wide interval; expand if needed up to a cap.
    lo, hi = -0.99, 1.0
    for _ in range(8):  # try a few expansions to find a sign change
        f_lo, f_hi = npv(lo), npv(hi)
        if f_lo == 0.0:
            return lo
        if f_hi == 0.0:
            return hi
        if f_lo * f_hi < 0.0:
            break
        # expand symmetrically
        hi *= 2.0
        lo = max(lo * 2.0, -0.999999)
    else:
        # never bracketed
        return None

    for _ in range(200):
        mid = (lo + hi) / 2.0
        val = npv(mid)
        if abs(val) < tol:
            return mid
        if val > 0.0:
            lo = mid
        else:
            hi = mid

    return None
