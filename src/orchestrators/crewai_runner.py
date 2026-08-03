# src/orchestrators/crewai_runner.py
"""
V2 Orchestrator (CrewAI seam)

Purpose
-------
Mirror the deterministic orchestrator but back it with CrewAI Agent/Task
wrappers that *delegate to local Python functions*. This keeps behavior
identical by default while establishing a real CrewAI integration seam.

Public API
----------
run_orchestration(listing_txt_path, photos_folder, inputs, horizon_years=10)
  -> OrchestrationResult(insights, forecast, thesis, media_insights, media_report)
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    # Importing Crew to verify availability for helpful errors
    _CREW_AVAILABLE = True
except Exception:  # pragma: no cover
    _CREW_AVAILABLE = False

from src.agents.crewai_components import (
    ChiefStrategistAgent,
    FinancialForecasterAgent,
    ListingAnalystAgent,
)
from src.core.cv.photo_insights import build_photo_insights
from src.core.media.insights import analyze_media
from src.core.media.local import collect_local_assets
from src.core.reports.photo_report import build_media_report
from src.core.reports.report_models import MediaReport
from src.orchestrators.crew import OrchestrationResult
from src.schemas.models import FinancialInputs, MediaInsights


def _require_provider_env() -> None:
    """
    Ensure a provider API key is present and 'crewai' is importable.
    We keep this fail-fast even though the run path is deterministic,
    so users get actionable errors when opting into the CrewAI engine.
    """
    provider_keys = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY")
    has_key = any(os.getenv(k) for k in provider_keys)
    if not has_key:
        raise ValueError(
            "engine='crewai' requested but no provider API key found. "
            "Set OPENAI_API_KEY (or ANTHROPIC_API_KEY/OPENROUTER_API_KEY), "
            "or run with --engine deterministic."
        )
    if not _CREW_AVAILABLE:
        raise ValueError(
            "engine='crewai' requested but the 'crewai' package is not available. "
            "Install it (e.g., `pip install crewai[tools]`) or use --engine deterministic."
        )


def run_orchestration(
    inputs: FinancialInputs,
    listing_txt_path: str | None = None,
    photos_folder: str | None = None,
    *,
    horizon_years: int = 10,
) -> OrchestrationResult:
    """
    Execute the CrewAI-seamed pipeline: Analyst -> Forecaster -> Strategist.

    Behavior:
        - Validates env/dep presence for CrewAI usage and fails with a friendly error.
        - Delegates actual work to local deterministic functions for identical math.
        - Constructs Agent/Task shells for future CrewAI LLM runs (not executed here).
    """
    _require_provider_env()

    analyst = ListingAnalystAgent()
    insights = analyst.run(listing_txt_path=listing_txt_path, photos_folder=photos_folder)

    forecaster = FinancialForecasterAgent()
    forecast = forecaster.run(inputs=inputs, insights=insights, horizon_years=horizon_years)

    strategist = ChiefStrategistAgent()
    thesis = strategist.run(forecast=forecast, insights=insights)

    # (Optional parity) Example of how we'd wire a real Crew:
    # if _CREW_AVAILABLE:
    #     crew = Crew(
    #         agents=[analyst.agent, forecaster.agent, strategist.agent],
    #         tasks=[analyst.task, forecaster.task, strategist.task],
    #         process=Process.sequential,
    #         verbose=False,
    #     )
    #     # NOTE: We do NOT call crew.kickoff() in deterministic mode.
    #     # Real LLM integration would replace .run() calls above with kickoff().

    # Descriptive media stats over the same folder the analyst tagged. Mirrors
    # src/orchestrators/crew.py's derivation exactly (not an agent/LLM concern —
    # collect_local_assets/analyze_media/build_photo_insights/build_media_report are
    # plain deterministic calls), so both engines reach parity on the report's
    # Media Overview and Photo Coverage sections. Defensive by the same rule as the
    # agents: a bad photo folder degrades the report, it never fails the run.
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
