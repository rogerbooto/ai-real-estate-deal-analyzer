# tests/orchestrators/test_build_breakevens.py
"""
``build_breakevens`` -- the Mission 5 shared helper for the assumption margin-of-safety analysis,
mirroring ``build_recourse``'s shape with ONE deliberate difference: it has no pre-computation
gate. ``is_genuinely_close`` exists because recourse has nothing to say about a deal with no
failing guardrail; the margin-of-safety question is the mirror image — it is asked of the
guardrails that currently PASS, so a clean BUY is precisely the deal it has the most to say about,
and gating it behind a near-miss would silence it exactly where it matters most.

Both ``crew.run_orchestration`` and ``crewai_runner.run_orchestration`` call this one function, so
the two engines cannot diverge on margins of safety the way they cannot on the verdict.
"""

from __future__ import annotations

from src.inputs.inputs import load_inputs
from src.orchestrators.crew import OrchestrationResult, build_breakevens, build_recourse, run_orchestration
from src.schemas.models import BreakevenAnalysis
from tests.utils import make_financial_inputs

_DEMO_DEAL_PATH = "data/sample_listings/36_kelly_moncton/inputs.json"
_CHAMPLAIN_PATH = "data/sample_listings/82_champlain_dieppe/inputs.json"


def _buy() -> object:
    good = make_financial_inputs(num_units=6)
    return good.model_copy(
        update={
            "financing": good.financing.model_copy(update={"purchase_price": 380_000.0, "down_payment_rate": 0.30}),
            "income": good.income.model_copy(update={"occupancy": 0.97, "bad_debt_factor": 0.98}),
        }
    )


def test_orchestration_result_defaults_breakeven_to_none():
    """Additive field: existing callers that never pass `breakeven=` keep working unchanged."""
    assert OrchestrationResult.__dataclass_fields__["breakeven"].default is None


def test_build_breakevens_runs_where_recourse_does_not():
    """THE point of having no gate. On the committed demo deal recourse never runs (four failing
    guardrails is past its near-miss bound), and two guardrails still pass — so there are two real
    margins of safety to report, and a gate copied from recourse would have discarded both."""
    inputs = load_inputs(_DEMO_DEAL_PATH).inputs
    assert build_recourse(inputs, horizon_years=10) is None

    analysis = build_breakevens(inputs, horizon_years=10)
    assert isinstance(analysis, BreakevenAnalysis)
    assert analysis.attempted is True
    assert analysis.passing_guardrails and analysis.rows


def test_build_breakevens_runs_for_a_buy():
    """A deal where everything passes is the deal whose margins of safety matter most."""
    analysis = build_breakevens(_buy(), horizon_years=10)  # type: ignore[arg-type]
    assert analysis.attempted is True
    assert analysis.failing_guardrails == ()
    assert analysis.rows


def test_build_breakevens_never_blanks_a_computed_analysis():
    """Once computed it is returned in full — `attempted=False` and all. Whether to RENDER is the
    report layer's call (see `compute_breakevens`' own docstring), not this helper's."""
    analysis = build_breakevens(load_inputs(_CHAMPLAIN_PATH).inputs, horizon_years=10)
    assert set(analysis.passing_guardrails) & set(analysis.failing_guardrails) == set()
    assert {r.guardrail for r in analysis.rows} <= set(analysis.passing_guardrails)


def test_run_orchestration_attaches_the_analysis():
    inputs = load_inputs(_CHAMPLAIN_PATH).inputs
    result = run_orchestration(inputs=inputs, horizon_years=10)
    assert isinstance(result.breakeven, BreakevenAnalysis)
    assert result.breakeven.rows


def test_build_breakevens_is_deterministic():
    inputs = load_inputs(_CHAMPLAIN_PATH).inputs
    assert build_breakevens(inputs, horizon_years=10) == build_breakevens(inputs, horizon_years=10)
