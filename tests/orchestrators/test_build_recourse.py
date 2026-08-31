# tests/orchestrators/test_build_recourse.py
"""
``build_recourse`` -- the Mission 4 shared helper, mirroring ``build_baseline_outlook``'s exact
shape (gate on the baseline forecast alone, `None` when the gate is closed, a full analysis when
it is open). Both ``crew.run_orchestration`` and ``crewai_runner.run_orchestration`` call this one
function, so the two engines cannot diverge on recourse the way they cannot on the verdict.
"""

from __future__ import annotations

from src.inputs.inputs import load_inputs
from src.orchestrators.crew import OrchestrationResult, build_recourse
from tests.utils import make_financial_inputs

_DEMO_DEAL_PATH = "data/sample_listings/36_kelly_moncton/inputs.json"


def test_orchestration_result_defaults_recourse_to_none():
    """Additive field: existing callers that never pass `recourse=` keep working unchanged."""
    result = OrchestrationResult.__dataclass_fields__["recourse"]
    assert result.default is None


def test_build_recourse_is_none_for_a_buy():
    good = make_financial_inputs(num_units=6)
    good = good.model_copy(
        update={
            "financing": good.financing.model_copy(update={"purchase_price": 380_000.0, "down_payment_rate": 0.30}),
            "income": good.income.model_copy(update={"occupancy": 0.97, "bad_debt_factor": 0.98}),
        }
    )
    assert build_recourse(good, horizon_years=10) is None


def test_build_recourse_is_none_for_the_demo_deal_deep_decline():
    """The committed sample deal: 4 fails > GENUINELY_CLOSE_MAX_FAILS (3) -- this is what keeps
    `python main.py`'s default report byte-identical to pre-Mission-4 output."""
    inputs = load_inputs(_DEMO_DEAL_PATH).inputs
    assert build_recourse(inputs, horizon_years=10) is None


def test_build_recourse_returns_a_full_analysis_for_a_conditional_near_miss():
    conditional = make_financial_inputs(num_units=4)
    conditional = conditional.model_copy(
        update={
            "financing": conditional.financing.model_copy(
                update={"purchase_price": 540_000.0, "down_payment_rate": 0.20, "interest_rate": 0.058}
            ),
        }
    )
    analysis = build_recourse(conditional, horizon_years=10)
    assert analysis is not None
    assert analysis.verdict == "CONDITIONAL"
    assert len(analysis.levers) > 0
