# tests/unit/test_breakeven.py
"""
Unit coverage for the assumption breakeven / margin-of-safety analysis (Mission 5) in
`src.market.breakeven`: the GD3 shape rule (the recourse "ask" reading must be INEXPRESSIBLE on
the breakeven type -- the mission's binding guardian invariant), the three-outcome honesty
contract (breakeven_found / never_breaks_in_range / undetermined -- an exhausted search never
reads as proven), confirm-by-rerun provenance (every shipped number independently reproduced by
a full, un-differentiated `run_financial_model`), the "never breaks within the possible range"
path (proven, and itself rerun-confirmed at the stated edge), determinism, and the engine's
`occupancy or 1.0` zero-quirk guard.

Fixtures are the two committed sample deals (`82_champlain_dieppe` -- 3 passing guardrails, all
three outcomes' natural habitat; `36_kelly_moncton` -- 2 passing) plus derived deals pinned on
real engine numbers: kelly at a 28% price cut (all guardrails pass -- the founder's worked
example: "clears DSCR until occupancy falls to ~92.3%; you assumed 95%"), a tiny-opex champlain
(expense growth MOVES the IRR but never breaks it in range -- the metric_moves=True proven
path), kelly at +50% price (nothing passes -- attempted=False), and kelly with expense_growth
already beyond the search ceiling (the degenerate zero-width bracket).
"""

from __future__ import annotations

from typing import get_args

import pytest
from pydantic import BaseModel, ConfigDict

from src.agents.chief_strategist import guardrail_checks_from_metrics
from src.core.finance.engine import metrics_of, run_financial_model
from src.core.finance.partition import (
    BARRED_ASSUMPTION_AXES,
    LEVER_IMAGE,
    MODEL_ASSUMPTIONS,
    assert_breakeven_shape,
)
from src.inputs.inputs import load_inputs
from src.market.breakeven import (
    _ASSUMPTION_ORDER,
    _ASSUMPTION_PATHS,
    _BREAKEVEN_TOL,
    _ENGINE_REFUSAL_TEXT,
    _IRR_UNDEFINED_WARNING_PREFIX,
    _OCCUPANCY_ADVERSE_EDGE,
    DEFAULT_BREAKEVEN_MAX_ITER,
    AssumptionName,
    _adverse_edge,
    _irr_is_coalesced,
    _is_engine_refusal,
    _perturb_assumption,
    _probe,
    compute_breakevens,
)
from src.market.recourse import _ok
from src.schemas.models import AssumptionBreakeven, BreakevenAnalysis, FinancialInputs

_CHAMPLAIN = "data/sample_listings/82_champlain_dieppe/inputs.json"
_KELLY = "data/sample_listings/36_kelly_moncton/inputs.json"


def _champlain() -> FinancialInputs:
    return load_inputs(_CHAMPLAIN).inputs


def _kelly() -> FinancialInputs:
    return load_inputs(_KELLY).inputs


def _kelly_at_price_factor(factor: float) -> FinancialInputs:
    fi = _kelly()
    return fi.model_copy(update={"financing": fi.financing.model_copy(update={"purchase_price": fi.financing.purchase_price * factor})})


# ---------------------------------------------------------------------------
# GD3 -- the shape rule: the recourse reading has no field to live in.
# ---------------------------------------------------------------------------


def test_gd3_breakeven_types_pass_the_shape_rule() -> None:
    """`partition.assert_breakeven_shape` (the guardian's enforced check, Ruling 2.4) accepts
    both shipped breakeven types. `src/market/breakeven.py` also calls this at import time, so
    a violating field would already have broken the whole suite -- this test names the invariant
    so its failure is self-explanatory."""
    assert_breakeven_shape(AssumptionBreakeven)
    assert_breakeven_shape(BreakevenAnalysis)


def test_gd3_breakeven_type_cannot_carry_an_ask_delta_or_target_field() -> None:
    """THE SHAPE RULE, pinned directly (RED if anyone adds such a field to the schema type):
    no field of the breakeven types may contain 'target', 'delta', or 'ask' -- the harmful
    sentence ("raise your vacancy assumption to 8% and the deal passes") must have no field to
    live in. This duplicates `assert_breakeven_shape`'s own token scan ON PURPOSE: if the
    partition guard is ever weakened, this test still fails on the field itself."""
    for model_cls in (AssumptionBreakeven, BreakevenAnalysis):
        for name in model_cls.model_fields:
            lowered = name.lower()
            for token in ("target", "delta", "ask"):
                assert token not in lowered, (
                    f"GD3 shape-rule violation: {model_cls.__name__}.{name} could express a recourse "
                    f"'ask' on an assumption axis (token {token!r}). See src/core/finance/partition.py "
                    "(assert_breakeven_shape) and GD3 Ruling 2.4."
                )


@pytest.mark.parametrize("bad_field", ["ask", "target_value", "delta", "vacancy_ask", "occupancy_target"])
def test_gd3_shape_guard_rejects_an_ask_shaped_extension(bad_field: str) -> None:
    """The guard has real teeth: a would-be extension of the breakeven type with any ask-shaped
    field raises `RuntimeError` naming GD3 and the Founder Proxy escalation path."""
    mutant = type(
        "MutantBreakeven",
        (BaseModel,),
        {
            "__annotations__": {"guardrail": str, bad_field: float},
            "model_config": ConfigDict(frozen=True),
        },
    )
    with pytest.raises(RuntimeError) as excinfo:
        assert_breakeven_shape(mutant)
    message = str(excinfo.value)
    assert "GD3" in message
    assert "FOUNDER PROXY ESCALATION" in message
    assert bad_field in message


def test_gd3_axes_are_classified_assumptions_and_nothing_else() -> None:
    """Every breakeven axis is a `MODEL_ASSUMPTIONS` path; none is barred (Ruling 3 -- exit cap,
    cap drift and horizon live inside the terminal-equity proxy); none collides with the lever
    image (a lever axis is recourse territory). Mirrors the module's own import-time guards so
    a weakened guard still fails here."""
    axis_paths = frozenset(_ASSUMPTION_PATHS.values())
    assert axis_paths <= MODEL_ASSUMPTIONS
    assert not axis_paths & BARRED_ASSUMPTION_AXES
    assert not axis_paths & LEVER_IMAGE
    # The barred axes must have NO breakeven surface at all (partition condition C5).
    assert BARRED_ASSUMPTION_AXES == frozenset({"market.cap_rate_drift", "refi.exit_cap_rate", "horizon_years"})
    schema_axes = get_args(AssumptionBreakeven.model_fields["assumption"].annotation)
    assert schema_axes == _ASSUMPTION_ORDER == get_args(AssumptionName) == ("occupancy", "rent_growth", "expense_growth")


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", [_CHAMPLAIN, _KELLY])
def test_deterministic_byte_identical(path: str) -> None:
    fi = load_inputs(path).inputs
    first = compute_breakevens(fi)
    second = compute_breakevens(fi)
    assert first.model_dump_json() == second.model_dump_json()


# ---------------------------------------------------------------------------
# Confirm-by-rerun: every shipped number is independently reproducible.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", [_CHAMPLAIN, _KELLY])
def test_every_breakeven_value_reconfirmed_by_independent_full_rerun(path: str) -> None:
    """For every `breakeven_found` row: an INDEPENDENT full `run_financial_model` at exactly
    `breakeven_value` observes the guardrail FAILING, `metric_at_breakeven` is bit-identical to
    that run's metric (or None when that run's IRR is the engine's coalesced sentinel -- the
    IRR-cliff contract, N-B1), and the guardrail passes at the assumed value (the margin is real
    room, measured from a passing baseline to a confirmed-failing point on the adverse side)."""
    from src.market.recourse import _metric

    fi = load_inputs(path).inputs
    analysis = compute_breakevens(fi)
    found = [r for r in analysis.rows if r.outcome == "breakeven_found"]
    assert found, "fixture regressed: expected at least one breakeven_found row"
    for row in found:
        assert row.breakeven_value is not None and row.margin is not None
        # Adverse side of the assumed value, by the row's own declared direction.
        if row.adverse_direction == "down":
            assert row.breakeven_value < row.assumed_value
        else:
            assert row.breakeven_value > row.assumed_value
        assert row.margin == abs(row.breakeven_value - row.assumed_value)
        # Independent confirming re-run -- full engine, no light path, no search state.
        perturbed = _perturb_assumption(fi, row.assumption, row.breakeven_value)
        confirm = metrics_of(run_financial_model(perturbed))
        checks = guardrail_checks_from_metrics(confirm, fi.market)
        assert not _ok(checks, row.guardrail), f"{row.assumption} x {row.guardrail}: shipped breakeven does not fail on re-run"
        if row.guardrail == "irr" and _irr_is_coalesced(confirm):
            # THE IRR CLIFF (N-B1): the confirming run's 0.0 is the engine's undefined-IRR
            # sentinel, not a measurement -- it must ship as None, never as a number. (Neither
            # sample deal currently exhibits this; the dedicated golden-case tests below do.)
            assert row.metric_at_breakeven is None
        else:
            assert row.metric_at_breakeven is not None
            assert row.metric_at_breakeven == _metric(confirm, row.guardrail)
            assert row.metric_at_breakeven < row.bar
        # And the baseline really passes -- the margin starts from safety, not from failure.
        base_checks = guardrail_checks_from_metrics(metrics_of(run_financial_model(fi)), fi.market)
        assert _ok(base_checks, row.guardrail)
        assert row.resolution == _BREAKEVEN_TOL
        assert row.probes_used <= DEFAULT_BREAKEVEN_MAX_ITER


# ---------------------------------------------------------------------------
# The three-outcome contract: an exhausted search NEVER reads as a proven result.
# ---------------------------------------------------------------------------


def test_exhausted_budget_reports_undetermined_never_proven() -> None:
    """With a probe budget of 1, every row that needs bisection must report `undetermined`
    (breakeven_value/margin/metric None -- no number ships), while rows whose search COMPLETED
    within one probe (the metric never moves / never breaks) keep their proven outcome. Compare
    against the default-budget run: every default `breakeven_found` row becomes `undetermined`
    -- never `never_breaks_in_range`, which would report "we stopped looking" as safety."""
    fi = _champlain()
    full = compute_breakevens(fi)
    starved = compute_breakevens(fi, max_iter=1)
    assert starved.max_iter == 1
    by_key = {(r.assumption, r.guardrail): r for r in starved.rows}
    assert not any(r.outcome == "breakeven_found" for r in starved.rows)
    for row in full.rows:
        starved_row = by_key[(row.assumption, row.guardrail)]
        if row.outcome == "breakeven_found":
            assert starved_row.outcome == "undetermined"
            assert starved_row.breakeven_value is None
            assert starved_row.margin is None
            assert starved_row.metric_at_breakeven is None
            assert starved_row.probes_used == 1
        else:
            assert starved_row.outcome == row.outcome  # a completed proof is budget-independent


def test_undetermined_is_deterministic_including_the_exhaustion_point() -> None:
    fi = _champlain()
    assert compute_breakevens(fi, max_iter=2).model_dump_json() == compute_breakevens(fi, max_iter=2).model_dump_json()


def test_nonpositive_max_iter_raises() -> None:
    with pytest.raises(ValueError, match="max_iter"):
        compute_breakevens(_champlain(), max_iter=0)


# ---------------------------------------------------------------------------
# "Never breaks within the possible range" -- a proven, strong result.
# ---------------------------------------------------------------------------


def test_never_breaks_when_metric_is_structurally_independent() -> None:
    """Year-1 guardrails never read the growth rates (growth applies from year 2), so
    rent_growth x cf_y1 on champlain is `never_breaks_in_range` with metric_moves=False -- and
    the claim is itself rerun-confirmed here: a full engine run at the stated adverse edge
    (rent_growth = -1.0, income zero from year 2) still passes cf_y1."""
    fi = _champlain()
    analysis = compute_breakevens(fi)
    rows = {(r.assumption, r.guardrail): r for r in analysis.rows}
    row = rows[("rent_growth", "cf_y1")]
    assert row.outcome == "never_breaks_in_range"
    assert row.metric_moves is False
    assert row.searched_to == -1.0
    assert row.breakeven_value is None and row.margin is None
    # Rerun-confirm the proven claim at the stated edge, independently and with the full engine.
    at_edge = metrics_of(run_financial_model(_perturb_assumption(fi, "rent_growth", -1.0)))
    assert _ok(guardrail_checks_from_metrics(at_edge, fi.market), "cf_y1")


def test_never_breaks_when_metric_moves_but_survives_the_whole_range() -> None:
    """A deal with negligible operating costs: expense growth genuinely MOVES the IRR
    (metric_moves=True) but cannot break it anywhere in the searched range [assumed, +100%/yr]
    -- the strong 'survives the whole range' result must not read as a failure to compute."""
    fi = _champlain()
    opex_dollar_lines = [name for name in type(fi.opex).model_fields if name != "expense_growth"]
    tiny_opex = fi.model_copy(update={"opex": fi.opex.model_copy(update={dict_line: 1.0 for dict_line in opex_dollar_lines})})
    analysis = compute_breakevens(tiny_opex)
    rows = {(r.assumption, r.guardrail): r for r in analysis.rows}
    row = rows[("expense_growth", "irr")]
    assert row.outcome == "never_breaks_in_range"
    assert row.metric_moves is True
    assert row.searched_to == 1.0
    # Rerun-confirm at the stated ceiling: IRR still clears its bar with costs doubling yearly.
    at_edge = metrics_of(run_financial_model(_perturb_assumption(tiny_opex, "expense_growth", 1.0)))
    assert _ok(guardrail_checks_from_metrics(at_edge, tiny_opex.market), "irr")


def test_degenerate_bracket_when_assumed_already_at_the_adverse_edge() -> None:
    """expense_growth assumed at 1.5 (beyond the +1.0 search ceiling): zero adverse room to
    search, so the row is trivially `never_breaks_in_range` scoped to `searched_to == assumed`
    -- and it costs zero engine probes."""
    fi = _kelly()
    deg = fi.model_copy(update={"opex": fi.opex.model_copy(update={"expense_growth": 1.5})})
    analysis = compute_breakevens(deg)
    rows = {(r.assumption, r.guardrail): r for r in analysis.rows}
    row = rows[("expense_growth", "cap_floor")]
    assert row.outcome == "never_breaks_in_range"
    assert row.probes_used == 0
    assert row.searched_to == row.assumed_value == 1.5


# ---------------------------------------------------------------------------
# Scoping: passing guardrails only; failing ones are recorded as fact, never solved.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", [_CHAMPLAIN, _KELLY])
def test_rows_cover_exactly_assumption_x_passing_guardrail(path: str) -> None:
    """One row per (assumption, PASSING guardrail) in fixed assumption-major order; failing
    guardrails get NO row (no margin of safety exists for them -- and solving them in the
    favorable direction would be the forbidden recourse reading in disguise, GD3)."""
    fi = load_inputs(path).inputs
    analysis = compute_breakevens(fi)
    expected = tuple((a, g) for a in _ASSUMPTION_ORDER for g in analysis.passing_guardrails)
    assert tuple((r.assumption, r.guardrail) for r in analysis.rows) == expected
    assert not set(analysis.failing_guardrails) & {r.guardrail for r in analysis.rows}
    assert not set(analysis.failing_guardrails) & set(analysis.passing_guardrails)


def test_attempted_false_when_nothing_passes() -> None:
    """Kelly at +50% price: every live guardrail fails -- there is no margin of safety to
    measure. attempted=False, rows empty, and the failing set is still recorded as fact."""
    analysis = compute_breakevens(_kelly_at_price_factor(1.5))
    assert analysis.attempted is False
    assert analysis.rows == ()
    assert analysis.passing_guardrails == ()
    assert len(analysis.failing_guardrails) >= 4


# ---------------------------------------------------------------------------
# The engine's `occupancy or 1.0` zero-quirk.
# ---------------------------------------------------------------------------


def test_occupancy_edge_stays_strictly_above_the_engine_zero_quirk() -> None:
    """`engine._annual_income` reads `income.occupancy or 1.0`: exactly 0.0 silently means FULL
    occupancy, so a probe at 0.0 would report the healthiest deal at the sickest assumption.
    The adverse edge must therefore be strictly positive -- and genuinely apocalyptic: the
    engine at the edge must NOT behave like occupancy 1.0."""
    assert _OCCUPANCY_ADVERSE_EDGE > 0.0
    assert _adverse_edge("occupancy") == _OCCUPANCY_ADVERSE_EDGE
    fi = _kelly()
    at_edge = metrics_of(run_financial_model(_perturb_assumption(fi, "occupancy", _OCCUPANCY_ADVERSE_EDGE)))
    at_full = metrics_of(run_financial_model(_perturb_assumption(fi, "occupancy", 1.0)))
    assert at_edge.cash_flow_y1 < at_full.cash_flow_y1  # the edge probe really is near-zero occupancy


# ---------------------------------------------------------------------------
# Perturbation hygiene (recourse's surgical-copy discipline).
# ---------------------------------------------------------------------------


def test_perturb_assumption_is_surgical_and_leaves_the_original_untouched() -> None:
    fi = _kelly()
    occ_before, rg_before, eg_before = fi.income.occupancy, fi.income.rent_growth, fi.opex.expense_growth

    p_occ = _perturb_assumption(fi, "occupancy", 0.5)
    p_rg = _perturb_assumption(fi, "rent_growth", -0.5)
    p_eg = _perturb_assumption(fi, "expense_growth", 0.5)

    assert p_occ.income.occupancy == 0.5 and p_occ.opex is fi.opex and p_occ.financing is fi.financing
    assert p_rg.income.rent_growth == -0.5 and p_rg.opex is fi.opex
    assert p_eg.opex.expense_growth == 0.5 and p_eg.income is fi.income  # precompute stays reusable
    assert (fi.income.occupancy, fi.income.rent_growth, fi.opex.expense_growth) == (occ_before, rg_before, eg_before)


# ---------------------------------------------------------------------------
# THE IRR CLIFF (Gate V re-review, N-B1): the engine's coalesced-0.0 IRR sentinel
# never ships as `metric_at_breakeven`.
# ---------------------------------------------------------------------------
#
# Fixtures are unmodified deals from the project's own golden matrix
# (`tests/core/finance/golden_cases.py`) -- the exact cases the re-review reproduced N-B1 on.
# When `irr()` finds no rate that solves NPV=0, the engine coalesces `irr_10yr` to 0.0 and says
# so in the same run's warnings (`engine._forecast_core`). The bisection then converges on a
# real, conservative guardrail boundary -- but that 0.0 is a sentinel, not a measurement, and
# before the fix it shipped as `metric_at_breakeven` and rendered as "the confirming re-run
# there measured 0.00%, below the bar" about a return that never decayed at all.


def _golden_case_inputs(case_id: str) -> tuple[FinancialInputs, int]:
    from tests.core.finance.golden_cases import CASES

    case = next(c for c in CASES if c["id"] == case_id)
    return FinancialInputs.model_validate(case["financial_inputs"]), int(case["horizon_years"])


@pytest.mark.parametrize(
    ("case_id", "assumption"),
    [
        ("units_2_horizon_10", "occupancy"),
        ("units_12_horizon_10", "rent_growth"),
        ("units_12_horizon_10", "expense_growth"),
    ],
)
def test_irr_cliff_never_ships_the_coalesced_sentinel_as_a_measurement(case_id: str, assumption: AssumptionName) -> None:
    """RED before the fix: these unmodified golden-matrix rows shipped
    `metric_at_breakeven == 0.0` -- the sentinel, presented as a confirming measurement. The
    crossing itself is real (the IRR guardrail genuinely stops clearing where the IRR stops
    being computable, on the engine's own conservative ruling), so the row stays
    `breakeven_found` with its margin -- but the metric ships as None, `jacobian.py`'s posture
    for the same value."""
    fi, horizon = _golden_case_inputs(case_id)
    analysis = compute_breakevens(fi, horizon_years=horizon)
    row = {(r.assumption, r.guardrail): r for r in analysis.rows}[(assumption, "irr")]
    assert row.outcome == "breakeven_found"
    assert row.breakeven_value is not None and row.margin is not None and row.margin > 0.0
    # The confirming re-run really cannot compute an IRR at this crossing: the engine's own
    # warning is on that run, its irr_10yr is the coalesced sentinel, and the guardrail fails.
    confirm = metrics_of(run_financial_model(_perturb_assumption(fi, assumption, row.breakeven_value), horizon_years=horizon))
    assert _irr_is_coalesced(confirm)
    assert confirm.irr_10yr == 0.0
    assert not _ok(guardrail_checks_from_metrics(confirm, fi.market), "irr")
    # ... and the sentinel must never reach the schema as a number.
    assert row.metric_at_breakeven is None


def test_a_genuinely_computed_irr_below_the_bar_still_ships_as_the_measurement() -> None:
    """The counterpart that pins the fix's scope: a real IRR crossing (the return computed, and
    measured below 12% by the confirming run) keeps its measured metric. units_2_horizon_10's
    rent_growth x irr row is exactly that shape, in the same analysis whose occupancy x irr row
    is a cliff -- the two must not be conflated."""
    fi, horizon = _golden_case_inputs("units_2_horizon_10")
    analysis = compute_breakevens(fi, horizon_years=horizon)
    row = {(r.assumption, r.guardrail): r for r in analysis.rows}[("rent_growth", "irr")]
    assert row.outcome == "breakeven_found"
    assert row.metric_at_breakeven is not None
    assert 0.0 < row.metric_at_breakeven < row.bar
    confirm = metrics_of(run_financial_model(_perturb_assumption(fi, "rent_growth", row.breakeven_value), horizon_years=horizon))
    assert not _irr_is_coalesced(confirm)
    assert row.metric_at_breakeven == confirm.irr_10yr


def test_irr_cliff_detection_reads_the_engines_own_warning_prefix() -> None:
    """Drift trip-wire for `_IRR_UNDEFINED_WARNING_PREFIX`: the detection must track the text
    the engine actually emits. `units_1_horizon_10` is the committed golden case whose IRR is
    undefined at the BASELINE (all cash flows negative -- no NPV root at any rate; pinned in the
    golden fixture and in `tests/core/finance/test_irr_undefined_warning.py`)."""
    fi, horizon = _golden_case_inputs("units_1_horizon_10")
    metrics = metrics_of(run_financial_model(fi, horizon_years=horizon))
    assert any(w.startswith(_IRR_UNDEFINED_WARNING_PREFIX) for w in metrics.warnings)
    assert _irr_is_coalesced(metrics)


# ---------------------------------------------------------------------------
# N2: the refusal handling is scoped to the engine's ONE documented refusal.
# ---------------------------------------------------------------------------


def test_probe_lets_the_engines_loud_identity_errors_propagate() -> None:
    """RED before the fix: `_probe` caught `(ValueError, ArithmeticError)` wholesale, so the
    engine's deliberately loud stale-precompute identity error (`engine._forecast_core`) came
    back as None -- "the engine declines to model here" -- silently clipping `searched_to` and
    narrowing every claim with no trace. It must propagate."""
    from src.core.finance.engine import precompute_income

    fi = _kelly()
    stale = precompute_income(_champlain().income)  # provably NOT fi.income's precompute
    # expense_growth leaves `inputs.income` untouched by reference, so `_probe` hands the stale
    # precompute to the engine -- which must refuse loudly, and `_probe` must not swallow it.
    with pytest.raises(ValueError, match="different IncomeModel"):
        _probe(fi, "expense_growth", 0.5, horizon_years=10, precomputed=stale)


def test_engine_refusal_matcher_is_scoped_to_the_negative_principal_message() -> None:
    """`_is_engine_refusal` recognises the documented refusal and nothing else -- in particular
    neither of the engine's identity errors, which a broad catch used to swallow."""
    assert _is_engine_refusal(ValueError("principal must be >= 0"))
    assert not _is_engine_refusal(ValueError("precomputed_income was derived from a different IncomeModel than the one being modelled."))
    assert not _is_engine_refusal(ValueError("income_shift was built over 4 units but the modelled IncomeModel now has 5"))


def test_engine_refusal_matcher_tracks_amortizations_actual_raise() -> None:
    """Drift trip-wire for `_ENGINE_REFUSAL_TEXT`: `amortization.schedule_columns` must still
    raise the exact message the matcher is scoped to, or the modelable-edge clipping would break
    loudly on every refinancing deal."""
    from src.core.finance.amortization import schedule_columns

    with pytest.raises(ValueError, match=_ENGINE_REFUSAL_TEXT):
        schedule_columns(-1.0, 0.05, 30, 0, 10)
    try:
        schedule_columns(-1.0, 0.05, 30, 0, 10)
    except ValueError as exc:
        assert _is_engine_refusal(exc)
