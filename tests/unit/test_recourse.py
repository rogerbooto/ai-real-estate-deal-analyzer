# tests/unit/test_recourse.py
"""
Unit coverage for `src.market.recourse` (Mission 4 — "What would have to change?").

This is the implementer's own coverage for the module built in task I.1: the pre-computation
scoping gate, the always-full-never-None result contract, determinism, the rounding-and-re-run
discipline, the statically-hopeless exclusion, and flag-don't-remove plausibility. The dedicated
non-independence-trap RED suite (naive formula-inversion vs. true re-run divergence on the CoC
guardrail) is task I.2's job and is intentionally NOT duplicated here -- this file exercises a
different, complementary set of behaviours.
"""

from __future__ import annotations

import pytest

from src.agents.chief_strategist import MIN_COC_Y1, synthesize_thesis
from src.core.finance.engine import run_financial_model
from src.inputs.inputs import load_inputs
from src.market.recourse import (
    GENUINELY_CLOSE_MAX_FAILS,
    RATE_MAGNITUDE_THRESHOLD,
    ROUND_STEP,
    compute_recourse,
    is_genuinely_close,
)
from src.schemas.models import FinancialInputs
from tests.utils import make_financial_inputs, make_market_assumptions

_DEMO_DEAL_PATH = "data/sample_listings/36_kelly_moncton/inputs.json"


def _good_buy_inputs() -> FinancialInputs:
    good = make_financial_inputs(num_units=6)
    return good.model_copy(
        update={
            "financing": good.financing.model_copy(update={"purchase_price": 380_000.0, "down_payment_rate": 0.30}),
            "income": good.income.model_copy(update={"occupancy": 0.97, "bad_debt_factor": 0.98}),
        }
    )


def _conditional_inputs() -> FinancialInputs:
    """Two guardrails soft (spread, irr) -- a genuine CONDITIONAL near-miss."""
    c = make_financial_inputs(num_units=4)
    return c.model_copy(
        update={
            "financing": c.financing.model_copy(update={"purchase_price": 540_000.0, "down_payment_rate": 0.20, "interest_rate": 0.058}),
        }
    )


def _near_miss_decline_inputs() -> FinancialInputs:
    """Exactly three guardrails fail (dscr, spread, irr) -- a DECLINE, but within
    GENUINELY_CLOSE_MAX_FAILS."""
    c = make_financial_inputs(num_units=4)
    return c.model_copy(
        update={
            "financing": c.financing.model_copy(update={"purchase_price": 555_000.0, "down_payment_rate": 0.15, "interest_rate": 0.06}),
        }
    )


def _demo_deal_inputs() -> FinancialInputs:
    """The ACTUAL committed sample deal (not a reconstruction): four of six live guardrails fail
    (dscr, spread, coc, cf_y1) -- a genuine multi-fail DECLINE, deliberately beyond
    GENUINELY_CLOSE_MAX_FAILS. Loaded from the real file so every number matches the discovery
    spec's independently-verified figures exactly (e.g. the $58,900 rounded price-cut ask below)."""
    return load_inputs(_DEMO_DEAL_PATH).inputs


# ---------------------------------------------------------------------------
# is_genuinely_close -- the pre-computation scoping gate
# ---------------------------------------------------------------------------


def test_gate_closed_for_a_buy():
    assert is_genuinely_close(_good_buy_inputs()) is False


def test_gate_open_for_a_conditional_near_miss():
    assert is_genuinely_close(_conditional_inputs()) is True


def test_gate_open_for_a_decline_within_the_fail_bound():
    assert is_genuinely_close(_near_miss_decline_inputs()) is True


def test_gate_closed_for_a_deep_decline_beyond_the_fail_bound():
    """The committed sample deal itself: 4 fails > GENUINELY_CLOSE_MAX_FAILS (3). This is also
    what keeps `python main.py`'s default report byte-identical to pre-Mission-4 output."""
    assert is_genuinely_close(_demo_deal_inputs()) is False


def test_gate_threshold_is_the_documented_constant():
    assert GENUINELY_CLOSE_MAX_FAILS == 3


def test_gate_evaluated_on_baseline_alone_matches_a_fresh_engine_run():
    """The gate must not silently depend on horizon_years defaults diverging from an explicit
    re-run at the same horizon."""
    inputs = _near_miss_decline_inputs()
    assert is_genuinely_close(inputs, horizon_years=10) == is_genuinely_close(inputs)


# ---------------------------------------------------------------------------
# compute_recourse -- always full, never None, regardless of honest_null
# ---------------------------------------------------------------------------


def test_compute_recourse_never_returns_none_even_for_a_deep_decline():
    """`is_genuinely_close` decides WHETHER to call this; once called, the result is always full
    -- even for a deal `is_genuinely_close` itself would have gated out."""
    analysis = compute_recourse(_demo_deal_inputs())
    assert analysis is not None
    assert len(analysis.failing_guardrails) == 4
    # Every (lever, guardrail) row for every failing guardrail is present -- nothing silently
    # dropped, including hopeless/null rows (4 levers x 4 failing guardrails).
    assert len(analysis.levers) == 4 * len(analysis.failing_guardrails)


def test_compute_recourse_row_count_covers_every_lever_times_failing_guardrail():
    analysis = compute_recourse(_demo_deal_inputs())
    expected_rows = 4 * len(analysis.failing_guardrails)  # 4 levers
    assert len(analysis.levers) == expected_rows


def test_compute_recourse_verdict_matches_synthesize_thesis():
    inputs = _conditional_inputs()
    forecast = run_financial_model(inputs)
    expected_verdict = synthesize_thesis(forecast, market=inputs.market).verdict
    assert compute_recourse(inputs).verdict == expected_verdict


def test_honest_null_analysis_is_still_fully_populated_not_blanked():
    """A pathological deal where recourse is attempted but nothing found should still carry every
    row (all null/hopeless), never revert to an empty or None result."""
    # A cap-rate override makes `spread`/`cap_floor` structurally hopeless for every lever (the
    # cap can never move), and a tiny, near-zero rent roll makes rent/opex levers unable to reach
    # any bound at all -- engineered to stress the "everything null" path without asserting a
    # specific outcome the RED-suite (I.2) already owns.
    inputs = _demo_deal_inputs().model_copy(update={"market": make_market_assumptions(cap_rate_purchase=0.03, cap_rate_floor=0.05)})
    analysis = compute_recourse(inputs)
    assert analysis is not None
    assert len(analysis.levers) > 0
    if analysis.honest_null:
        assert analysis.cheapest is None
        assert analysis.remaining_after_cheapest == ()
    else:
        assert analysis.cheapest is not None


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_same_inputs_produce_byte_identical_analysis():
    inputs = _demo_deal_inputs()
    first = compute_recourse(inputs)
    second = compute_recourse(inputs)
    assert first == second
    assert first.model_dump() == second.model_dump()


def test_compute_recourse_does_not_mutate_caller_inputs():
    inputs = _demo_deal_inputs()
    snapshot_before = inputs.model_dump()
    compute_recourse(inputs)
    assert inputs.model_dump() == snapshot_before


# ---------------------------------------------------------------------------
# Round-away-from-zero + re-run at the rounded ask (Gate D product decision)
# ---------------------------------------------------------------------------


def test_rounds_the_ask_away_from_zero_and_rerun_confirms_the_bar():
    """The founder-proxy's own worked example: a required price cut of $58,842.37 (the true
    bisection flip point on the committed sample deal, purchase_price lever vs. coc guardrail)
    must round UP to $58,900 -- never down to $58,800, which would print an ask that does not
    clear the bar -- and the reported target_value must come from a re-run AT that rounded value.
    """
    inputs = _demo_deal_inputs()
    analysis = compute_recourse(inputs)
    row = next(r for r in analysis.levers if r.lever == "purchase_price" and r.guardrail == "coc")

    assert row.closes_guardrail is True
    assert row.delta == pytest.approx(-58_900.0, abs=1e-6)
    assert row.target_value == pytest.approx(399_900.0 - 58_900.0, abs=1e-6)
    # A multiple of the lever's rounding step, not an arbitrary bisection artifact.
    assert row.target_value % ROUND_STEP["purchase_price"] == pytest.approx(0.0, abs=1e-6)

    perturbed = inputs.model_copy(update={"financing": inputs.financing.model_copy(update={"purchase_price": row.target_value})})
    forecast = run_financial_model(perturbed)
    assert forecast.purchase.coc >= MIN_COC_Y1


# ---------------------------------------------------------------------------
# Statically hopeless exclusion (interest_rate <-> cap_floor)
# ---------------------------------------------------------------------------


def test_interest_rate_vs_cap_floor_is_always_structurally_hopeless():
    inputs = _demo_deal_inputs().model_copy(update={"market": make_market_assumptions(cap_rate_floor=0.20)})
    analysis = compute_recourse(inputs)
    assert "cap_floor" in analysis.failing_guardrails  # a 20% floor is unmet by construction here

    row = next(r for r in analysis.levers if r.lever == "interest_rate" and r.guardrail == "cap_floor")
    assert row.structurally_hopeless is True
    assert row.closes_guardrail is False
    assert row.target_value is None
    assert row.delta is None
    assert row.relative_change is None
    assert row.plausible is True
    assert row.plausibility_reason is None


# ---------------------------------------------------------------------------
# also_closes / remaining_after_cheapest bookkeeping
# ---------------------------------------------------------------------------


def test_also_closes_and_remaining_after_cheapest_are_consistent():
    analysis = compute_recourse(_demo_deal_inputs())
    assert analysis.cheapest is not None
    cheapest = analysis.cheapest

    # Every guardrail in also_closes was actually failing (never invents a guardrail that wasn't
    # in scope) and is never the cheapest row's own guardrail.
    assert set(cheapest.also_closes) <= set(analysis.failing_guardrails)
    assert cheapest.guardrail not in cheapest.also_closes

    expected_remaining = tuple(g for g in analysis.failing_guardrails if g != cheapest.guardrail and g not in cheapest.also_closes)
    assert analysis.remaining_after_cheapest == expected_remaining


def test_cheapest_is_the_smallest_relative_change_among_plausible_closing_rows():
    analysis = compute_recourse(_demo_deal_inputs())
    plausible_closing = [row for row in analysis.levers if row.closes_guardrail and row.plausible]
    assert plausible_closing  # sanity: this deal has at least one plausible fix
    best = min(row.relative_change for row in plausible_closing if row.relative_change is not None)
    assert analysis.cheapest is not None
    assert analysis.cheapest.plausible is True
    assert analysis.cheapest.relative_change == pytest.approx(best)


# ---------------------------------------------------------------------------
# Flag-don't-remove plausibility (never silently drops a found fix)
# ---------------------------------------------------------------------------


def test_implausible_lever_is_flagged_not_removed():
    """An engineered deal where the only way to close a guardrail via the rent lever is an
    unrealistically large per-unit increase -- the row must still carry its found target_value,
    just flagged."""
    inputs = make_financial_inputs(num_units=2).model_copy(
        update={
            "financing": make_financial_inputs(num_units=2).financing.model_copy(
                update={"purchase_price": 900_000.0, "down_payment_rate": 0.05, "interest_rate": 0.07}
            ),
            "income": make_financial_inputs(num_units=2).income.model_copy(update={"rent_growth": 0.03}),
        }
    )
    analysis = compute_recourse(inputs)
    flagged_rows = [r for r in analysis.levers if r.closes_guardrail and not r.plausible]
    for row in flagged_rows:
        assert row.plausibility_reason is not None
        assert row.target_value is not None
        assert row.delta is not None


# ---------------------------------------------------------------------------
# Module constants sourced from existing machinery (reuse, not invention)
# ---------------------------------------------------------------------------


def test_rate_magnitude_threshold_is_sourced_from_default_bands():
    from src.market.hypotheses import DEFAULT_BANDS

    assert RATE_MAGNITUDE_THRESHOLD == abs(DEFAULT_BANDS["interest_rate_delta"][0])
    assert RATE_MAGNITUDE_THRESHOLD == pytest.approx(0.01)
