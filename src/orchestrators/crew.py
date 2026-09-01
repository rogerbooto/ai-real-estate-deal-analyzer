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
from src.market.breakeven import compute_breakevens
from src.market.recourse import compute_recourse, is_genuinely_close
from src.schemas.models import (
    BreakevenAnalysis,
    FinancialForecast,
    FinancialInputs,
    InvestmentThesis,
    ListingInsights,
    MediaInsights,
    RecourseAnalysis,
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
    #: "What would have to change?" (Mission 4). None whenever `is_genuinely_close` (a
    #: pre-computation scoping gate on the baseline forecast alone) says this deal is not a near
    #: miss — which keeps a run with no near-miss byte-identical to one from before this existed.
    #: Never a blanked-out result: once computed, it is always the full analysis, honest_null and
    #: all (see `src/market/recourse.py` module docstring).
    recourse: RecourseAnalysis | None = None
    #: "How wrong can these guesses be?" (Mission 5) — the margin of safety each currently-passing
    #: guardrail has against the model assumptions the user had to guess at (vacancy, rent growth,
    #: expense growth). Deliberately NOT behind `is_genuinely_close`: recourse's gate exists because
    #: recourse has nothing to say unless a guardrail is failing, whereas a deal where everything
    #: passes is exactly the deal whose margins of safety matter most. Always the complete
    #: `BreakevenAnalysis`, `attempted=False` and all — the whether-to-render call is the report
    #: layer's (see `src/market/breakeven.py`'s `compute_breakevens` docstring). None only for a
    #: caller that never computed one.
    breakeven: BreakevenAnalysis | None = None


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


def build_recourse(inputs: FinancialInputs, *, horizon_years: int) -> RecourseAnalysis | None:
    """
    "What would have to change?" (Mission 4) — shared by both orchestrators, mirroring
    ``build_baseline_outlook``'s exact shape.

    Args:
        inputs: The exact inputs the observed forecast was produced from.
        horizon_years: Same horizon as the observed forecast.

    Returns:
        A full ``RecourseAnalysis`` when ``is_genuinely_close`` (a pre-computation scoping gate
        evaluated on a fresh baseline forecast alone) says this deal is worth attempting recourse
        for, otherwise ``None``. Never a blanked-out analysis: once the gate opens, whatever
        ``compute_recourse`` finds — including an honest "nothing realistic closes this" — is
        returned in full.
    """
    if not is_genuinely_close(inputs, horizon_years=horizon_years):
        return None
    return compute_recourse(inputs, horizon_years=horizon_years)


def build_breakevens(inputs: FinancialInputs, *, horizon_years: int) -> BreakevenAnalysis:
    """
    "How wrong can these guesses be?" (Mission 5) — shared by both orchestrators, mirroring
    ``build_recourse``'s exact shape.

    THE ONE DELIBERATE DIFFERENCE FROM ``build_recourse``: there is no pre-computation gate here.
    ``is_genuinely_close`` exists because recourse has nothing to say about a deal with no failing
    guardrail — there is no gap for a lever to close. The margin-of-safety question is the mirror
    image: it is asked of the guardrails that currently PASS, so a clean ``BUY`` is precisely the
    deal it has the most to say about, and gating it behind a near-miss would silence it exactly
    where it matters. ``compute_breakevens`` is self-contained and cheap (one baseline run plus a
    bounded probe budget per row), and it reports ``attempted=False`` itself when no live guardrail
    passes.

    Args:
        inputs: The exact inputs the observed forecast was produced from.
        horizon_years: Same horizon as the observed forecast, so the two are comparable.

    Returns:
        The complete ``BreakevenAnalysis``, never a blanked-out one: ``attempted`` is False (rows
        empty) exactly when no live guardrail currently passes, and the decision not to render a
        section in that case belongs to the report layer, not here.
    """
    return compute_breakevens(inputs, horizon_years=horizon_years)


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
        same deal with and without those observations. Also carries a ``recourse`` analysis
        whenever the deal is a genuine near-miss (see ``build_recourse``); ``None`` otherwise,
        which keeps report output byte-identical for a BUY or a deep DECLINE. Also carries a
        ``breakeven`` margin-of-safety analysis, computed unconditionally (see
        ``build_breakevens`` for why it has no near-miss gate).

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
    recourse = build_recourse(inputs, horizon_years=horizon_years)
    breakeven = build_breakevens(inputs, horizon_years=horizon_years)

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
        recourse=recourse,
        breakeven=breakeven,
    )
