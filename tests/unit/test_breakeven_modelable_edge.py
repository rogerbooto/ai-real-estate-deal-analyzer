# tests/unit/test_breakeven_modelable_edge.py
"""
``src/market/breakeven.py``'s MODELABLE EDGE: what the search does when the engine declines to
model the deal at the nominal adverse edge.

The mechanism is real and reachable from the committed pipeline, which is how it was found: on a
deal that REFINANCES, deep enough adversity drives year-`n` NOI negative, so
``engine._forecast_core``'s NOI-based refi valuation goes negative, so ``refi_ltv * value`` is a
negative loan and ``amortization.schedule_columns`` raises ``ValueError("principal must be >= 0")``
— the engine correctly refusing to score a deal it cannot model. Before ``_modelable_edge``, the
adverse-edge probe for rent growth and expense growth propagated that straight out of
``compute_breakevens`` and crashed the report run.

Three properties are pinned here, and all three are honesty properties rather than convenience
ones: the search does not crash, it does not pretend the refused probe passed, and the range it
CLAIMS to have searched (``searched_to``) is the range it really covered — so a "never breaks"
scoped to a clipped edge can never ship in an unclipped edge's words.
"""

from __future__ import annotations

import pytest

from src.core.finance.engine import forecast_metrics
from src.market.breakeven import (
    _EXPENSE_GROWTH_ADVERSE_EDGE,
    _OCCUPANCY_ADVERSE_EDGE,
    _RENT_GROWTH_ADVERSE_EDGE,
    compute_breakevens,
)
from src.schemas.models import (
    FinancialInputs,
    FinancingTerms,
    IncomeModel,
    MarketAssumptions,
    OperatingExpenses,
    RefinancePlan,
    UnitIncome,
)

_NOMINAL = {
    "occupancy": _OCCUPANCY_ADVERSE_EDGE,
    "rent_growth": _RENT_GROWTH_ADVERSE_EDGE,
    "expense_growth": _EXPENSE_GROWTH_ADVERSE_EDGE,
}


def _refi_deal() -> FinancialInputs:
    """The same fixture ``tests/integration/test_orchestrator_crewai.py`` runs the pipeline on."""
    return FinancialInputs(
        financing=FinancingTerms(
            purchase_price=500_000.0, closing_costs=10_000.0, down_payment_rate=0.25, interest_rate=0.055, amort_years=30, io_years=0
        ),
        opex=OperatingExpenses(
            insurance=2400.0,
            taxes=6000.0,
            utilities=3600.0,
            water_sewer=1800.0,
            property_management=4800.0,
            repairs_maintenance=2400.0,
            trash=1200.0,
            landscaping=800.0,
            snow_removal=600.0,
            hoa_fees=0.0,
            reserves=1500.0,
            other=500.0,
            expense_growth=0.02,
        ),
        income=IncomeModel(
            units=[UnitIncome(rent_month=1200.0, other_income_month=50.0)] * 2
            + [UnitIncome(rent_month=1200.0, other_income_month=0.0)] * 2,
            occupancy=0.95,
            bad_debt_factor=0.97,
            rent_growth=0.03,
        ),
        refi=RefinancePlan(do_refi=True, year_to_refi=5, refi_ltv=0.75),
        market=MarketAssumptions(cap_rate_spread_target=0.015, cap_rate_floor=None),
    )


@pytest.mark.parametrize("axis", ["rent_growth", "expense_growth"])
def test_the_engine_really_does_refuse_the_nominal_edge_for_this_deal(axis: str) -> None:
    """The premise, asserted rather than assumed: if the engine ever stops refusing here, the two
    tests below stop testing anything and this one says so instead of passing silently."""
    fi = _refi_deal()
    value = _NOMINAL[axis]
    if axis == "rent_growth":
        perturbed = fi.model_copy(update={"income": fi.income.model_copy(update={"rent_growth": value})})
    else:
        perturbed = fi.model_copy(update={"opex": fi.opex.model_copy(update={"expense_growth": value})})
    with pytest.raises(ValueError, match="principal must be >= 0"):
        forecast_metrics(perturbed, horizon_years=10)


def test_compute_breakevens_does_not_propagate_the_engine_refusal() -> None:
    """The crash this fixed: before `_modelable_edge`, wiring the analysis into the pipeline made
    `python main.py` fail outright on any refinancing deal."""
    analysis = compute_breakevens(_refi_deal(), horizon_years=10)
    assert analysis.attempted is True
    assert analysis.rows


def test_a_refused_edge_is_clipped_in_and_reported_as_the_range_actually_searched() -> None:
    """`searched_to` is the range the search really covered, strictly inside the nominal edge and
    strictly on the adverse side of the assumed value. It is the field every "never breaks" claim
    is scoped by, so a wrong value here would let a narrow search ship in a wide search's words."""
    analysis = compute_breakevens(_refi_deal(), horizon_years=10)
    clipped = [r for r in analysis.rows if r.assumption in ("rent_growth", "expense_growth")]
    assert clipped

    for row in clipped:
        nominal = _NOMINAL[row.assumption]
        assert row.searched_to != nominal
        if row.adverse_direction == "down":
            assert nominal < row.searched_to < row.assumed_value
        else:
            assert row.assumed_value < row.searched_to < nominal


def test_the_clipped_edge_is_itself_modelable() -> None:
    """It is not an arbitrary retreat: the value reported as searched is one the engine really did
    forecast, which is what makes a "still clears at that edge" claim a measurement."""
    fi = _refi_deal()
    analysis = compute_breakevens(fi, horizon_years=10)
    for row in analysis.rows:
        if row.searched_to == row.assumed_value:
            continue
        if row.assumption == "occupancy":
            perturbed = fi.model_copy(update={"income": fi.income.model_copy(update={"occupancy": row.searched_to})})
        elif row.assumption == "rent_growth":
            perturbed = fi.model_copy(update={"income": fi.income.model_copy(update={"rent_growth": row.searched_to})})
        else:
            perturbed = fi.model_copy(update={"opex": fi.opex.model_copy(update={"expense_growth": row.searched_to})})
        forecast_metrics(perturbed, horizon_years=10)  # must not raise


def test_an_unreachable_edge_never_becomes_a_pass() -> None:
    """The refusal is never read as "the guardrail cleared there". Every row on this deal is either
    a confirmed crossing, a never-breaks scoped to a range that was really searched, or an honest
    `undetermined` — never a claim resting on a probe the engine declined to run."""
    analysis = compute_breakevens(_refi_deal(), horizon_years=10)
    for row in analysis.rows:
        assert row.outcome in ("breakeven_found", "never_breaks_in_range", "undetermined")
        if row.outcome == "breakeven_found":
            assert row.breakeven_value is not None and row.margin is not None and row.metric_at_breakeven is not None
        else:
            assert row.breakeven_value is None and row.margin is None and row.metric_at_breakeven is None


def test_the_clip_stays_inside_the_row_probe_budget() -> None:
    """`_MODELABLE_EDGE_STEPS` is spent from the same per-row budget as the bisection, so a clipped
    row must still finish inside `max_iter` rather than starve into a spurious `undetermined`."""
    analysis = compute_breakevens(_refi_deal(), horizon_years=10)
    assert all(row.probes_used <= analysis.max_iter for row in analysis.rows)
    assert all(row.outcome != "undetermined" for row in analysis.rows)


def test_the_result_is_still_byte_identical_across_runs() -> None:
    fi = _refi_deal()
    assert compute_breakevens(fi, horizon_years=10) == compute_breakevens(fi, horizon_years=10)
