# src/core/advisor/scenarios.py
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Scenario:
    """
    Scenario knobs (absolute targets) that approximate impact on CF/IRR.

    - down_payment_pct: 0.00..1.00 absolute fraction to *target* for the scenario
    - interest_rate: absolute annual interest rate to *target* for the scenario
    - renovation_budget: one-time additional cash requirement at close
    """

    name: str
    down_payment_pct: float
    interest_rate: float
    renovation_budget: float = 0.0


# Sensible defaults you can tweak
DEFAULT_SCENARIOS: tuple[Scenario, ...] = (
    Scenario("downside", down_payment_pct=0.20, interest_rate=0.065, renovation_budget=0.0),
    Scenario("base", down_payment_pct=0.25, interest_rate=0.055, renovation_budget=0.0),
    Scenario("upside", down_payment_pct=0.30, interest_rate=0.045, renovation_budget=5000.0),
)


def _num(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def apply_scenario(finance: Any, scenario: Scenario) -> dict[str, float | str | None]:
    """
    Pure function: returns a compact scenario summary dict derived from a finance-like object.
    This is intentionally *approximate* and does not re-run the engine.

    Expected finance attributes (best-effort with fallbacks):
      - cashflow_monthly (float)
      - irr (float in 0..1)
      - purchase_price (float)
      - down_payment_rate (optional; default 0.25)
      - interest_rate (optional; default 0.055)
      - acquisition_cash (optional; default purchase_price * down_payment_rate)

    Heuristics:
      - Increasing down payment improves CF (less debt service)
      - Increasing interest rate reduces CF
      - Reno budget adds to acquisition cash (one-time drag)
      - IRR proxy = annualized CF delta / (new acquisition cash), added to base IRR
    """
    # Baseline readings with safe fallbacks
    price = _num(getattr(finance, "purchase_price", 0.0))
    cf0 = _num(getattr(finance, "cashflow_monthly", 0.0))
    irr0 = _num(getattr(finance, "irr", 0.0))
    dp0 = _num(getattr(finance, "down_payment_rate", 0.25), 0.25)
    r0 = _num(getattr(finance, "interest_rate", 0.055), 0.055)
    acq0 = _num(getattr(finance, "acquisition_cash", price * dp0), price * dp0)

    # Targets from scenario
    dp1 = float(scenario.down_payment_pct)
    r1 = float(scenario.interest_rate)
    reno = float(scenario.renovation_budget)

    # Deterministic “toy” impact model (keep it simple & stable for tests)
    # Positive change in DP% → *increase* CF (less debt service)
    # Positive change in rate → *decrease* CF
    # Coefficients tune sensitivity; choose stable, interpretable numbers
    cf_from_dp = (dp1 - dp0) * (price / 1000.0) * 0.4  # ~$0.40 per $1k price per 1.0 dp delta
    cf_from_rate = (r0 - r1) * (price / 1000.0) * 1.2  # ~$1.20 per $1k price per 1.0 rate delta

    cf1 = cf0 + cf_from_dp + cf_from_rate
    acq1 = acq0 + reno

    # IRR proxy: add annualized CF delta divided by cash at close
    irr_delta = 0.0
    if acq1 > 1e-9:
        irr_delta = max(-0.10, min(0.10, (cf1 - cf0) * 12.0 / acq1))  # clamp ±10pp to avoid wild swings
    irr1 = max(0.0, min(1.0, irr0 + irr_delta))

    return {
        "name": scenario.name,
        "cashflow_monthly": round(cf1, 2),
        "irr_est": round(irr1, 4) if irr1 is not None else None,
        "delta_cashflow": round(cf1 - cf0, 2),
        "acquisition_cash_est": round(acq1, 2),
        "note": "Approximate scenario; does not re-run engine.",
    }


def summarize_scenarios(finance: Any, scenarios: Iterable[Scenario] = DEFAULT_SCENARIOS) -> list[dict[str, float | str | None]]:
    """
    Convenience wrapper: run a set of scenarios and return list of summaries.
    """
    return [apply_scenario(finance, sc) for sc in scenarios]
