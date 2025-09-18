# src/orchestrator/crew.py
"""
V1 Orchestrator (deterministic, Crew-ready seam)

Purpose
-------
Execute the agent pipeline in a deterministic sequence:
  1) Listing Analyst -> ListingInsights
  2) Financial Forecaster -> FinancialForecast
  3) Chief Strategist -> InvestmentThesis

Design
------
- Pure Python, no LLM calls in V1 (easy to test, deterministic).
- Interface mirrors what a CrewAI-based orchestrator would need:
  pass inputs, collect structured outputs.

Public API
----------
run_orchestration(listing_txt_path, photos_folder, inputs, horizon_years=10)
  -> OrchestrationResult(insights, forecast, thesis)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.schemas.models import FinancialInputs
from src.schemas.models import ListingInsights, FinancialForecast, InvestmentThesis
from src.agents.listing_analyst import analyze_listing
from src.agents.financial_forecaster import forecast_financials
from src.agents.chief_strategist import synthesize_thesis


@dataclass(frozen=True)
class OrchestrationResult:
    """Bundle of final artifacts from the agent pipeline."""
    insights: ListingInsights
    forecast: FinancialForecast
    thesis: InvestmentThesis


def run_orchestration(
    inputs: FinancialInputs,
    listing_txt_path: Optional[str] = None,
    photos_folder: Optional[str] = None,
    *,
    horizon_years: int = 10,
) -> OrchestrationResult:
    """
    Execute the V1 deterministic pipeline: Analyst -> Forecaster -> Strategist.

    Args:
        inputs: FinancialInputs (financing, opex, income, refi, market).
        listing_txt_path: Optional path to local listing .txt file.
        photos_folder: Optional path to folder of property photos.
        horizon_years: Number of years to forecast (default 10).

    Returns:
        OrchestrationResult with insights, forecast, and investment thesis.

    Notes:
        - This is a clean seam to swap in a CrewAI-based orchestrator in V2+.
        - Missing assets (no text/photos) are handled gracefully by agents.
    """
    insights = analyze_listing(listing_txt_path=listing_txt_path, photos_folder=photos_folder)
    forecast = forecast_financials(inputs=inputs, insights=insights, horizon_years=horizon_years)
    thesis = synthesize_thesis(forecast)
    return OrchestrationResult(insights=insights, forecast=forecast, thesis=thesis)
