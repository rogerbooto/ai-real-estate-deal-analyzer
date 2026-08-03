# src/orchestrators/crew.py
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
  -> OrchestrationResult(insights, forecast, thesis, media_insights, media_report)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.agents.chief_strategist import synthesize_thesis
from src.agents.financial_forecaster import forecast_financials
from src.agents.listing_analyst import analyze_listing
from src.core.cv.photo_insights import build_photo_insights
from src.core.media.insights import analyze_media
from src.core.media.local import collect_local_assets
from src.core.reports.photo_report import build_media_report
from src.core.reports.report_models import MediaReport
from src.schemas.models import (
    FinancialForecast,
    FinancialInputs,
    InvestmentThesis,
    ListingInsights,
    MediaInsights,
)


@dataclass(frozen=True)
class OrchestrationResult:
    """Bundle of final artifacts from the agent pipeline."""

    insights: ListingInsights
    forecast: FinancialForecast
    thesis: InvestmentThesis
    #: Descriptive stats over the photo folder. None when no photos were supplied (or none
    #: were readable), which is what keeps the report's Media Overview section optional.
    media_insights: MediaInsights | None = None
    #: What the photos *show* — room coverage, detected amenities, provider provenance.
    media_report: MediaReport | None = None


def run_orchestration(
    inputs: FinancialInputs,
    listing_txt_path: str | None = None,
    photos_folder: str | None = None,
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
        OrchestrationResult with insights, forecast, investment thesis, and — when photos
        were supplied — media insights over that folder.

    Notes:
        - This is a clean seam to swap in a CrewAI-based orchestrator in V2+.
        - Missing assets (no text/photos) are handled gracefully by agents.
    """
    insights = analyze_listing(listing_txt_path=listing_txt_path, photos_folder=photos_folder)
    forecast = forecast_financials(inputs=inputs, insights=insights, horizon_years=horizon_years)
    thesis = synthesize_thesis(forecast)

    # Descriptive media stats over the same folder the analyst tagged. Defensive by the same
    # rule as the agents: a bad photo folder degrades the report, it never fails the run.
    media_insights: MediaInsights | None = None
    media_report: MediaReport | None = None
    if photos_folder:
        try:
            assets = collect_local_assets(photos_folder)
            if assets:
                media_insights = analyze_media(assets)
        except Exception:
            media_insights = None
        try:
            media_report = build_media_report(build_photo_insights(Path(photos_folder)))
        except Exception:
            media_report = None

    return OrchestrationResult(
        insights=insights,
        forecast=forecast,
        thesis=thesis,
        media_insights=media_insights,
        media_report=media_report,
    )
