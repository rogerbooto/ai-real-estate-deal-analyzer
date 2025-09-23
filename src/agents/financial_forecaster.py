# src/agents/financial_forecaster.py
"""
Financial Forecaster Agent (V1)

Purpose
-------
Thin agent wrapper around the deterministic financial engine. It normalizes
inputs when appropriate, invokes the core model, and returns the resulting
FinancialForecast for downstream consumption.

Design
------
- Deterministic: no external calls, no randomness.
- Delegates all math to src/tools/financial_model.run().
- Leaves domain rules (warnings, cap-rate floors, etc.) to the model.
- Provides a clean seam to add optional AI reasoning in V2+ if needed.

Public API
----------
forecast_financials(inputs, insights=None, horizon_years=10) -> FinancialForecast
"""

from __future__ import annotations

from src.schemas.models import FinancialForecast, FinancialInputs, ListingInsights
from src.tools.financial_model import run as run_financial_model


def _clamp01(x: float) -> float:
    """Clamp a float to the inclusive [0, 1] range."""
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def _normalize_inputs(inputs: FinancialInputs) -> FinancialInputs:
    """
    Apply conservative, non-destructive normalizations for robustness.
    Notes:
      - Occupancy and bad_debt_factor should be in [0, 1].
      - Leave growth rates and interest as provided (caller responsibility).
      - Do not mutate original Pydantic model; return a shallow-copied instance.
    """
    income = inputs.income.model_copy(
        update={
            "occupancy": _clamp01(inputs.income.occupancy),
            "bad_debt_factor": _clamp01(inputs.income.bad_debt_factor),
        }
    )
    return inputs.model_copy(update={"income": income})


def forecast_financials(
    inputs: FinancialInputs,
    insights: ListingInsights | None = None,
    horizon_years: int = 10,
) -> FinancialForecast:
    """
    Run the deterministic financial forecast over a fixed horizon.

    Args:
        inputs: FinancialInputs bundle (financing, opex, income, refi, market).
        insights: Optional ListingInsights that may influence OPEX/CapEx in future versions.
        horizon_years: Number of years to model (default 10).

    Returns:
        FinancialForecast with purchase metrics, year-by-year breakdown,
        optional refi event, 10-year IRR, equity multiple, and warnings.

    Behavior:
        - Clamps occupancy & bad_debt_factor to [0, 1] for safety.
        - Delegates all math and warning logic to the financial_model engine.
    """
    safe_inputs = _normalize_inputs(inputs)
    forecast = run_financial_model(safe_inputs, insights=insights, horizon_years=horizon_years)
    return forecast
