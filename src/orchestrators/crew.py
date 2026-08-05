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
from src.core.reports.baseline import BaselineOutlook
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
    #: The same deal re-run with no listing observations applied, so the report can show both
    #: pictures. None whenever no observation moved a number — which is the common case, and what
    #: keeps a run with no live insight modifiers byte-identical to one from before this existed.
    baseline: BaselineOutlook | None = None


def build_baseline_outlook(
    inputs: FinancialInputs,
    forecast: FinancialForecast,
    *,
    horizon_years: int,
) -> BaselineOutlook | None:
    """
    Re-run the deal with every listing observation suppressed, for the report's comparison.

    Shared by both orchestrators. The forecaster and the strategist are deterministic in *every*
    mode by construction (see ``crewai_runner``'s module docstring and ``ChiefStrategistAgent``),
    so calling the underlying functions directly here is the same computation the CrewAI engine
    would perform through its own wrappers — there is no second code path to diverge from.

    Args:
        inputs: The exact inputs the observed forecast was produced from.
        forecast: The observed forecast, used only to detect whether any observation fired.
        horizon_years: Same horizon as the observed forecast, so the two are comparable.

    Returns:
        A ``BaselineOutlook`` when at least one insight modifier fired, otherwise ``None``.

    Notes:
        ``YearBreakdown.notes`` is the engine's own record of a fired modifier — one note per
        rule applied. No notes means ``insights=None`` would reproduce the observed forecast
        exactly, so the second engine run is skipped: it would cost time to prove the two
        pictures are the same picture, and the report has nothing to compare.
    """
    if not any(y.notes for y in forecast.years):
        return None
    base_forecast = forecast_financials(inputs=inputs, insights=None, horizon_years=horizon_years)
    return BaselineOutlook(forecast=base_forecast, thesis=synthesize_thesis(base_forecast, market=inputs.market))


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
        were supplied — media insights over that folder. Also carries a ``baseline`` outlook
        whenever a listing observation actually moved a number, so the report can show the
        same deal with and without those observations.

    Notes:
        - This is a clean seam to swap in a CrewAI-based orchestrator in V2+.
        - Missing assets (no text/photos) are handled gracefully by agents.
    """
    insights = analyze_listing(listing_txt_path=listing_txt_path, photos_folder=photos_folder)
    forecast = forecast_financials(inputs=inputs, insights=insights, horizon_years=horizon_years)
    # `market=` is what makes the thesis judge the spread against the target the user configured —
    # the same number the engine tests when it warns "cap-rate spread below target".
    thesis = synthesize_thesis(forecast, market=inputs.market)
    baseline = build_baseline_outlook(inputs, forecast, horizon_years=horizon_years)

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
        baseline=baseline,
    )
