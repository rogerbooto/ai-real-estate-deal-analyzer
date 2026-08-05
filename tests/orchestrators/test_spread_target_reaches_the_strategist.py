# tests/orchestrators/test_spread_target_reaches_the_strategist.py
"""
Wiring guard for Mission 2 / Wave 3 task 3.1a (guardian M4).

`synthesize_thesis` can only honour the user's `cap_rate_spread_target` if somebody hands it
the market block. Both orchestrators must do so. Fixing the strategist and forgetting either
call site would leave the report free to contradict itself again on that engine only — and the
two engines free to disagree with each other on the same inputs, which the mission's parity
work exists to prevent.

These tests drive the orchestrators end to end (no mocking of the strategist) with a configured
target the hardcoded fallback would answer differently, so dropping `market=inputs.market` at
either call site turns them RED.
"""

from __future__ import annotations

import pytest

from src.agents.chief_strategist import MIN_SPREAD, synthesize_thesis
from src.orchestrators import crew as deterministic_orchestrator
from src.schemas.models import (
    FinancialInputs,
    FinancingTerms,
    IncomeModel,
    MarketAssumptions,
    OperatingExpenses,
    RefinancePlan,
    UnitIncome,
)

#: Well above the 1.50% fallback and above this deal's actual spread, so the two bars disagree.
STRICT_TARGET = 0.15


def _inputs(target: float) -> FinancialInputs:
    """A comfortable deal (11.50% spread, clean BUY at the fallback) with only the target varied."""
    return FinancialInputs(
        financing=FinancingTerms(
            purchase_price=450_000.0,
            closing_costs=8_000.0,
            down_payment_rate=0.30,
            interest_rate=0.05,
            amort_years=30,
            io_years=0,
        ),
        opex=OperatingExpenses(
            insurance=2000.0,
            taxes=5000.0,
            utilities=3000.0,
            water_sewer=1500.0,
            property_management=3600.0,
            repairs_maintenance=1800.0,
            trash=1000.0,
            landscaping=600.0,
            snow_removal=500.0,
            hoa_fees=0.0,
            reserves=1200.0,
            other=400.0,
            expense_growth=0.02,
        ),
        income=IncomeModel(
            units=[UnitIncome(rent_month=1300.0, other_income_month=100.0) for _ in range(6)],
            occupancy=0.96,
            bad_debt_factor=0.98,
            rent_growth=0.03,
        ),
        refi=RefinancePlan(do_refi=False),
        market=MarketAssumptions(cap_rate_purchase=None, cap_rate_floor=None, cap_rate_spread_target=target),
        capex_reserve_upfront=0.0,
    )


def _assert_judged_on_the_configured_target(result) -> None:  # type: ignore[no-untyped-def]
    """The thesis must cite the configured target, and must agree with the engine's warning."""
    assert result.forecast.purchase.spread_vs_rate > MIN_SPREAD, "fixture must clear the fallback bar, or it proves nothing"
    assert "cap-rate spread below target" in result.forecast.warnings

    spread_lines = [line for line in result.thesis.rationale if "Cap-rate spread" in line]
    assert spread_lines == ["Cap-rate spread is thin at 11.50% (< 15.00%)."]
    assert result.thesis.verdict != "BUY"
    # With a verdict other than BUY the levers exist, so the engine's warning is explained.
    assert "Address: cap-rate spread below target" in result.thesis.levers


def test_deterministic_orchestrator_passes_the_configured_target() -> None:
    """RED on revert: drop `market=inputs.market` in `crew.run_orchestration` and this fails."""
    inputs = _inputs(STRICT_TARGET)
    result = deterministic_orchestrator.run_orchestration(inputs=inputs, horizon_years=10)
    _assert_judged_on_the_configured_target(result)


def test_crewai_orchestrator_passes_the_configured_target(monkeypatch: pytest.MonkeyPatch) -> None:
    """RED on revert: the CrewAI seam must reach the identical verdict, from the identical target.

    No LLM is involved: with `AIREAL_LLM_MODE` unset every step delegates to the same local
    functions. The API key only satisfies `_require_provider_env`.
    """
    monkeypatch.delenv("AIREAL_LLM_MODE", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")
    from src.orchestrators import crewai_runner

    inputs = _inputs(STRICT_TARGET)
    result = crewai_runner.run_orchestration(inputs=inputs, horizon_years=10)
    _assert_judged_on_the_configured_target(result)

    # Engine parity: same inputs, same verdict object, whichever orchestrator produced it.
    assert result.thesis == deterministic_orchestrator.run_orchestration(inputs=inputs, horizon_years=10).thesis


def test_baseline_outlook_is_judged_on_the_same_target() -> None:
    """The observation-free comparison run must use the same bar as the observed run.

    Otherwise the report's baseline-vs-observed table could attribute a verdict change to a
    listing observation when the two columns were simply scored differently.
    """
    inputs = _inputs(STRICT_TARGET)
    forecast = deterministic_orchestrator.run_orchestration(inputs=inputs, horizon_years=10).forecast
    # `build_baseline_outlook` short-circuits when no observation moved a number, so drive it
    # through a forecast that carries a note.
    noted = forecast.model_copy(deep=True)
    noted.years[0].notes = ["synthetic: forces the baseline re-run"]

    outlook = deterministic_orchestrator.build_baseline_outlook(inputs, noted, horizon_years=10)

    assert outlook is not None
    assert outlook.thesis == synthesize_thesis(outlook.forecast, market=inputs.market)
    assert any("(< 15.00%)" in line for line in outlook.thesis.rationale)
