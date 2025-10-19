# src/core/finance/irr.py

from __future__ import annotations


def irr(cash_flows: list[float], *, max_iter: int = 100, tol: float = 1e-6) -> float:
    """
    Compute annual IRR (Internal Rate of Return) for a series of cash flows.
    Uses Newton-Raphson with a fallback bisection if non-convergent.

    Args:
        cash_flows: Sequence of annual cash flows. cash_flows[0] is usually negative (equity outlay).
        max_iter: Max iterations for Newton-Raphson.
        tol: Convergence tolerance.

    Returns:
        IRR as a decimal fraction (e.g., 0.12 for 12%). Returns 0.0 if undefined or non-convergent.
    """
    if not cash_flows or all(x >= 0 for x in cash_flows) or all(x <= 0 for x in cash_flows):
        return 0.0

    # Initial guess (10%)
    r = 0.10

    def npv(rate: float) -> float:
        return sum(cf / ((1 + rate) ** t) for t, cf in enumerate(cash_flows))

    def dnpv(rate: float) -> float:
        return sum(-t * cf / ((1 + rate) ** (t + 1)) for t, cf in enumerate(cash_flows) if t > 0)

    # Newton-Raphson iterations
    for _ in range(max_iter):
        f = npv(r)
        df = dnpv(r)
        if abs(df) < 1e-12:
            break
        new_r = r - f / df
        if abs(new_r - r) < tol:
            return new_r
        r = new_r

    # Fallback: bisection between -99% and +100%
    lo, hi = -0.99, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        val = npv(mid)
        if abs(val) < tol:
            return mid
        if val > 0:
            lo = mid
        else:
            hi = mid
    return r
