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
- Delegates all math to src.core.finance.run_financial_model().
- Leaves domain rules (warnings, cap-rate floors, etc.) to the model.
- Provides a clean seam to add optional AI reasoning in V2+ if needed.

Public API
----------
forecast_financials(inputs, insights=None, horizon_years=10) -> FinancialForecast
"""

from __future__ import annotations

from src.core.finance import run_financial_model
from src.schemas.labels import DefectLabel
from src.schemas.models import FinancialForecast, FinancialInputs, ListingInsights


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


# `core.finance.engine._apply_insight_modifiers` tests literal, PRE-normalization phrases for its
# OPEX bumps (`"water stain" in defs`) -- deliberately frozen there; see ROADMAP_TRACKER.md backlog
# #7 / Mission 2 "defect #4". The CV/label layer (`schemas.labels`) normalizes listing text like
# "water stain" to the closed-set `DefectLabel.water_leak_suspected` *before* the engine ever sees
# it (`schemas/labels.py` DEFECT_TOKEN_ALIASES), so on every real pipeline run the engine's trigger
# was unreachable and the report's "Adjustments Applied" section could never appear.
#
# This map translates each normalized label the engine cannot see back into the literal phrase it
# is still watching for. It is additive-only and applied to a COPY used solely for the engine call
# -- the caller's `insights` (and therefore the report's "Condition & Defects" list) is untouched,
# so the reader never sees a duplicate-looking "water stain" bullet next to "water_leak_suspected".
#
# NOTE: "old roof" (the engine's other literal trigger) has no entry here on purpose. No ontology
# concept for roof condition exists anywhere in the CV/label layer (text or photo path) to translate
# back from -- closing that gap means inventing new vocabulary (a schema change), which is a
# separate, larger, explicitly out-of-scope decision (see ROADMAP_TRACKER.md backlog #7 and Mission
# 2 Sprint Tracker's "defect #4" record).
_ENGINE_DEFECT_TRIGGER_ALIASES: dict[DefectLabel, str] = {
    DefectLabel.water_leak_suspected: "water stain",
}


def _reconcile_engine_trigger_vocabulary(insights: ListingInsights | None) -> ListingInsights | None:
    """Restore the engine's literal OPEX-modifier triggers alongside their normalized labels.

    Additive-only translation at the CV/label seam, not a change to the engine: for every
    normalized defect label in ``insights.defects`` that has a legacy trigger phrase the engine
    still tests for (``_ENGINE_DEFECT_TRIGGER_ALIASES``), add that phrase to a COPY of ``defects``.
    Returns ``insights`` unchanged (same object) whenever there is nothing to add, so a run with no
    matching defect stays byte-identical to before this existed.
    """
    if insights is None or not insights.defects:
        return insights
    defect_set = {d.lower().strip() for d in insights.defects}
    additions = {
        trigger for label, trigger in _ENGINE_DEFECT_TRIGGER_ALIASES.items() if label.value in defect_set and trigger not in defect_set
    }
    if not additions:
        return insights
    return insights.model_copy(update={"defects": sorted({*insights.defects, *additions})})


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
        - Reconciles normalized listing-insight vocabulary back to the literal phrases the engine's
          OPEX-insight modifiers test for (see ``_reconcile_engine_trigger_vocabulary``), using a
          copy scoped to this call only -- the caller's ``insights`` object is never mutated.
        - Delegates all math and warning logic to the financial_model engine.
    """
    safe_inputs = _normalize_inputs(inputs)
    engine_insights = _reconcile_engine_trigger_vocabulary(insights)
    forecast = run_financial_model(safe_inputs, insights=engine_insights, horizon_years=horizon_years)
    return forecast
