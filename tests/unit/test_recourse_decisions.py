# tests/unit/test_recourse_decisions.py
"""Mission 4 (task I.2) RED-when-broken coverage for `src.market.recourse`'s Gate D product
decisions, complementary to (never duplicating) the implementer's own `tests/unit/test_recourse.py`
and the centrepiece non-independence trap in `tests/unit/test_recourse_nonindependence_trap.py`.

Each section below states the decision, pins it with an assertion against the shipped module, and
DEMONSTRATES (not merely asserts) what a revert would look like -- either by constructing the
broken shape locally (never by editing `src/`) or, where practical, by permanently monkeypatching
the module's own private machinery within a single test and showing the same assertion shape
would fail.

Decisions covered:
    1. Flag-don't-remove   -- an implausible-but-closing row keeps its numbers, never dropped.
    2. Cheapest-first + other gaps remain -- ordering is deterministic; other failures survive.
    3. Honest-null         -- "nothing closes this" is a full, populated answer, never blanked.
    4. Determinism         -- the cheapest-pick tie-break is order-independent BECAUSE it includes
                              (lever, guardrail); demonstrated against a broken key that lacks it.
    5. Round-away-from-zero -- rounding DOWN (toward zero) would print an ask that provably does
                              not clear the bar; rounding away from zero does.
    6. No caller mutation  -- compute_recourse never mutates the FinancialInputs it is handed, by
                              value AND by identity of untouched submodels; demonstrated against a
                              monkeypatched in-place-mutating stand-in for `_perturb`.
"""

from __future__ import annotations

import pytest

from src.agents.chief_strategist import MIN_COC_Y1
from src.core.finance.engine import run_financial_model
from src.inputs.inputs import load_inputs
from src.market import recourse as recourse_mod
from src.market.recourse import compute_recourse
from src.schemas.models import FinancialInputs, RecourseLever
from tests.utils import make_financial_inputs, make_market_assumptions

_DEMO_DEAL_PATH = "data/sample_listings/36_kelly_moncton/inputs.json"


def _demo_deal_inputs() -> FinancialInputs:
    return load_inputs(_DEMO_DEAL_PATH).inputs


def _near_miss_decline_three_fails() -> FinancialInputs:
    """Exactly three guardrails fail (dscr, spread, irr) -- a DIFFERENT deal from I.1's own
    fixture of the same shape, so `remaining_after_cheapest` is exercised on independent numbers.
    Verified (once, here, in the module docstring's spirit) to fail exactly dscr/spread/irr and
    leave two guardrails un-closed by the single cheapest fix."""
    c = make_financial_inputs(num_units=4)
    return c.model_copy(
        update={
            "financing": c.financing.model_copy(update={"purchase_price": 555_000.0, "down_payment_rate": 0.15, "interest_rate": 0.06}),
        }
    )


def _honest_null_fixture() -> FinancialInputs:
    """A deal engineered so that NO lever, within any search bound, can close ANY failing
    guardrail: a tiny 2-unit rent roll against a $2,000,000 purchase price makes DSCR/CoC/Y1-cash-
    flow unreachable even at the generous-but-finite search bounds (100% rent increase, 40% price
    cut, 300bps rate cut, 40% opex cut), and an overridden `cap_rate_purchase` makes spread/
    cap_floor structurally hopeless for every lever. `honest_null` is verified True by
    construction, not by chance -- see `test_honest_null_is_true_and_deterministic_for_this_fixture`."""
    c = make_financial_inputs(num_units=2)
    return c.model_copy(
        update={
            "financing": c.financing.model_copy(update={"purchase_price": 2_000_000.0, "down_payment_rate": 0.20, "interest_rate": 0.07}),
            "market": make_market_assumptions(cap_rate_purchase=0.03),
        }
    )


# ---------------------------------------------------------------------------
# 1) Flag-don't-remove: an implausible-but-closing row keeps its numbers, never dropped.
# ---------------------------------------------------------------------------


def test_implausible_row_carries_full_numbers_not_a_blanked_placeholder():
    """The committed sample deal's own rent-vs-dscr row: a 26.9% rent increase is flagged (>10%
    threshold) but the row still reports the exact target/delta/relative_change the search found.
    """
    analysis = compute_recourse(_demo_deal_inputs())
    row = next(r for r in analysis.levers if r.lever == "rent_per_unit_month" and r.guardrail == "dscr")

    assert row.closes_guardrail is True
    assert row.plausible is False
    assert row.plausibility_reason is not None and "26.9%" in row.plausibility_reason
    # THE decision: numbers intact, not None, not zeroed out.
    assert row.target_value == pytest.approx(1840.0, abs=1.0)
    assert row.delta == pytest.approx(390.0, abs=1.0)
    assert row.relative_change is not None and row.relative_change > 0.0
    assert row.also_closes  # a real, non-fabricated side-effect list, not blanked to ()


def test_would_go_red_if_flagged_rows_were_silently_dropped():
    """Demonstrates the revert this decision guards against: build the analysis for real, then
    show that a "drop flagged rows instead of flagging them" variant (the vetoed shape) would
    make the row unfindable -- i.e. the exact lookup the previous test relies on raises, proving
    that test is not vacuous."""
    analysis = compute_recourse(_demo_deal_inputs())

    # Real, correct behaviour: the row is there.
    real_row = next(r for r in analysis.levers if r.lever == "rent_per_unit_month" and r.guardrail == "dscr")
    assert real_row.plausible is False

    # The vetoed "flag, then discard" shape, reconstructed locally (never imported from a
    # modified src/): silently drop every closing-but-implausible row instead of flagging it.
    dropped_rows = tuple(r for r in analysis.levers if not (r.closes_guardrail and not r.plausible))
    assert len(dropped_rows) < len(analysis.levers)  # the drop actually removed something real

    with pytest.raises(StopIteration):
        next(r for r in dropped_rows if r.lever == "rent_per_unit_month" and r.guardrail == "dscr")


# ---------------------------------------------------------------------------
# 2) Cheapest-first + other gaps remain.
# ---------------------------------------------------------------------------


def test_cheapest_first_ordering_and_remaining_gaps_on_an_independent_three_fail_deal():
    inputs = _near_miss_decline_three_fails()
    analysis = compute_recourse(inputs)

    assert set(analysis.failing_guardrails) == {"dscr", "spread", "irr"}
    assert analysis.cheapest is not None
    assert analysis.honest_null is False

    # Cheapest really is the minimum relative_change among plausible, closing rows.
    plausible_closing = [r for r in analysis.levers if r.closes_guardrail and r.plausible]
    best = min(r.relative_change for r in plausible_closing if r.relative_change is not None)
    assert analysis.cheapest.relative_change == pytest.approx(best)

    # The single cheapest fix does NOT close every failing guardrail on this deal -- other gaps
    # genuinely remain, and the module says so rather than implying "one fix solves everything".
    assert analysis.remaining_after_cheapest != ()
    expected_remaining = tuple(
        g for g in analysis.failing_guardrails if g != analysis.cheapest.guardrail and g not in analysis.cheapest.also_closes
    )
    assert analysis.remaining_after_cheapest == expected_remaining
    assert len(analysis.remaining_after_cheapest) >= 1


# ---------------------------------------------------------------------------
# 3) Honest-null: fully populated, never blanked, never None.
# ---------------------------------------------------------------------------


def test_honest_null_is_true_and_deterministic_for_this_fixture():
    inputs = _honest_null_fixture()
    analysis = compute_recourse(inputs)

    assert analysis.honest_null is True
    assert analysis.cheapest is None
    assert analysis.remaining_after_cheapest == ()

    # Still fully populated -- never a blanked-out result.
    assert len(analysis.failing_guardrails) > 0
    assert analysis.verdict in ("CONDITIONAL", "DECLINE")
    expected_row_count = 4 * len(analysis.failing_guardrails)
    assert len(analysis.levers) == expected_row_count
    assert all(row.plausible is True for row in analysis.levers)  # null rows are never "flagged"
    assert all(row.closes_guardrail is False for row in analysis.levers)


def test_honest_null_would_go_red_against_the_vetoed_computed_then_discarded_shape():
    """Roger's Gate D veto, made concrete: build the vetoed shape directly (a `RecourseAnalysis`
    that computed something internally but discarded it into a blanked result before returning --
    the exact bug pattern that got prior code deleted) and show the "fully populated" assertions
    above would fail against it."""
    inputs = _honest_null_fixture()
    real_analysis = compute_recourse(inputs)
    assert real_analysis.honest_null is True

    from src.schemas.models import RecourseAnalysis

    vetoed_blanked_shape = RecourseAnalysis(
        verdict=real_analysis.verdict,
        failing_guardrails=real_analysis.failing_guardrails,
        levers=(),  # <-- THE VETOED BUG: computed rows discarded instead of kept
        cheapest=None,
        remaining_after_cheapest=(),
        honest_null=True,
    )

    with pytest.raises(AssertionError):
        assert len(vetoed_blanked_shape.levers) == 4 * len(vetoed_blanked_shape.failing_guardrails)
    with pytest.raises(AssertionError):
        assert len(vetoed_blanked_shape.levers) > 0


# ---------------------------------------------------------------------------
# 4) Determinism: the cheapest-pick tie-break is order-independent because it names
#    (lever, guardrail), demonstrated against a broken key that omits it.
# ---------------------------------------------------------------------------


def _tied_rows() -> tuple[RecourseLever, RecourseLever]:
    def mk(lever: str, guardrail: str) -> RecourseLever:
        return RecourseLever(
            guardrail=guardrail,  # type: ignore[arg-type]
            lever=lever,  # type: ignore[arg-type]
            baseline_value=100.0,
            target_value=110.0,
            delta=10.0,
            relative_change=0.10,  # IDENTICAL relative_change on both rows -- an engineered tie.
            closes_guardrail=True,
            structurally_hopeless=False,
            plausible=True,
            plausibility_reason=None,
            also_closes=(),
        )

    return mk("purchase_price", "coc"), mk("annual_opex", "dscr")


def _broken_pick_cheapest_missing_tie_break(levers: tuple[RecourseLever, ...]) -> RecourseLever | None:
    """The revert this decision guards against: the SAME cheapest-pick logic, minus the
    `(lever, guardrail)` tie-break tail -- i.e. exactly what `_pick_cheapest` would look like if
    that tail were ever "simplified" away."""
    closing = [row for row in levers if row.closes_guardrail]
    if not closing:
        return None

    def _key(row: RecourseLever) -> tuple[int, float]:
        tier = 0 if row.plausible else 1
        rc = row.relative_change if row.relative_change is not None else float("inf")
        return (tier, rc)  # BUG: no tie-break -> order-dependent on exact ties.

    return min(closing, key=_key)


def test_real_pick_cheapest_is_order_independent_on_an_engineered_tie():
    a, b = _tied_rows()
    winner_ab = recourse_mod._pick_cheapest((a, b))
    winner_ba = recourse_mod._pick_cheapest((b, a))

    assert winner_ab is not None and winner_ba is not None
    assert (winner_ab.lever, winner_ab.guardrail) == (winner_ba.lever, winner_ba.guardrail)


def test_broken_tie_break_would_be_order_dependent_proving_the_real_one_matters():
    a, b = _tied_rows()
    winner_ab = _broken_pick_cheapest_missing_tie_break((a, b))
    winner_ba = _broken_pick_cheapest_missing_tie_break((b, a))

    assert winner_ab is not None and winner_ba is not None
    # THE REVERT SIGNATURE: without (lever, guardrail) in the key, min() breaks ties by
    # insertion order -- the same two rows, differently ordered, pick different winners.
    assert (winner_ab.lever, winner_ab.guardrail) != (winner_ba.lever, winner_ba.guardrail)


def test_same_inputs_produce_byte_identical_analysis_on_two_more_fixtures():
    """Complements I.1's own byte-identical test (on the demo deal) with two independent
    fixtures exercising different branches (an honest-null path and a some-levers-close path)."""
    for build in (_honest_null_fixture, _near_miss_decline_three_fails):
        inputs = build()
        first = compute_recourse(inputs)
        second = compute_recourse(build())  # a FRESH, independently-constructed inputs object
        assert first.model_dump_json() == second.model_dump_json()


# ---------------------------------------------------------------------------
# 5) Round-away-from-zero: rounding DOWN would print an ask that does not clear the bar.
# ---------------------------------------------------------------------------


def test_rounding_toward_zero_would_undershoot_the_bar_rounding_away_from_zero_clears_it():
    """The demo deal's purchase_price/coc row: the TRUE unrounded flip point is $341,057.63.
    Rounding the required cut DOWN (toward zero, to the nearest $100 -- i.e. a SMALLER cut,
    landing at $341,100) leaves the price ABOVE the true flip point, so CoC there does NOT clear
    3.00%. Rounding AWAY from zero (a bigger cut, landing at the shipped $341,000) does clear it.
    This is why the module rounds away from zero and re-runs to confirm, never the other way."""
    inputs = _demo_deal_inputs()

    round_toward_zero_price = 341_100.0  # a SMALLER cut than required
    perturbed_undershoot = inputs.model_copy(
        update={"financing": inputs.financing.model_copy(update={"purchase_price": round_toward_zero_price})}
    )
    coc_undershoot = run_financial_model(perturbed_undershoot).purchase.coc
    assert coc_undershoot < MIN_COC_Y1  # PROVABLY does not clear the bar

    shipped_ask = compute_recourse(inputs)
    row = next(r for r in shipped_ask.levers if r.lever == "purchase_price" and r.guardrail == "coc")
    assert row.target_value == pytest.approx(341_000.0, abs=1.0)
    perturbed_shipped = inputs.model_copy(update={"financing": inputs.financing.model_copy(update={"purchase_price": row.target_value})})
    coc_shipped = run_financial_model(perturbed_shipped).purchase.coc
    assert coc_shipped >= MIN_COC_Y1  # the actual reported ask clears it


# ---------------------------------------------------------------------------
# 6) No caller mutation: value AND identity of untouched submodels are preserved.
# ---------------------------------------------------------------------------


def test_no_mutation_by_value_or_identity_across_multiple_fixtures():
    for build in (_demo_deal_inputs, _near_miss_decline_three_fails, _honest_null_fixture):
        inputs = build()
        snapshot_before = inputs.model_dump()
        financing_id_before = id(inputs.financing)
        opex_id_before = id(inputs.opex)
        income_id_before = id(inputs.income)
        units_id_before = id(inputs.income.units)
        market_id_before = id(inputs.market)
        refi_id_before = id(inputs.refi)

        compute_recourse(inputs)

        assert inputs.model_dump() == snapshot_before
        # The caller's own submodels are never replaced or mutated in place.
        assert id(inputs.financing) == financing_id_before
        assert id(inputs.opex) == opex_id_before
        assert id(inputs.income) == income_id_before
        assert id(inputs.income.units) == units_id_before
        assert id(inputs.market) == market_id_before
        assert id(inputs.refi) == refi_id_before


def test_perturb_shares_untouched_submodels_by_reference_surgical_copy():
    """Pins the module's own documented architecture directly: `_perturb` for the `rent_per_unit_
    month` lever must share `financing`/`opex`/`market`/`refi` BY REFERENCE with the caller's
    object (only `income` is rebuilt), and vice versa for the `purchase_price`/`interest_rate`
    levers (only `financing` is rebuilt)."""
    inputs = _demo_deal_inputs()
    total_opex_y1 = run_financial_model(inputs).years[0].total_opex

    perturbed_rent = recourse_mod._perturb(inputs, "rent_per_unit_month", 50.0, total_opex_y1=total_opex_y1)
    assert perturbed_rent.financing is inputs.financing
    assert perturbed_rent.opex is inputs.opex
    assert perturbed_rent.market is inputs.market
    assert perturbed_rent.refi is inputs.refi
    assert perturbed_rent.income is not inputs.income  # the ONE submodel this lever touches

    perturbed_price = recourse_mod._perturb(inputs, "purchase_price", 1_000.0, total_opex_y1=total_opex_y1)
    assert perturbed_price.opex is inputs.opex
    assert perturbed_price.income is inputs.income
    assert perturbed_price.market is inputs.market
    assert perturbed_price.refi is inputs.refi
    assert perturbed_price.financing is not inputs.financing


def _mutating_perturb_stand_in(original_perturb):
    """The revert this decision guards against: a `_perturb` that mutates the CALLER's
    `FinancialInputs.financing` in place (legal, because `FinancingTerms` is NOT a frozen
    pydantic model in this codebase) instead of returning a `model_copy`."""

    def _stand_in(inputs, lever, t, *, total_opex_y1):
        if lever == "purchase_price":
            inputs.financing.purchase_price = inputs.financing.purchase_price - t  # THE BUG: in-place
            return inputs
        return original_perturb(inputs, lever, t, total_opex_y1=total_opex_y1)

    return _stand_in


def test_would_go_red_if_perturb_reverted_to_in_place_mutation():
    """A single call to the mutating stand-in already corrupts the caller's `FinancialInputs` --
    proving the no-mutation assertions above are not vacuous. (Wiring this stand-in in for the
    real `_perturb` and running the FULL `compute_recourse` search is even more dramatic: because
    the bisection loop calls `_perturb` on the SAME object dozens of times with different `t`,
    the in-place subtraction compounds across every step and the purchase price runs away
    negative, crashing deep inside `amortization_schedule` with `ValueError: principal must be
    >= 0` -- itself a real, observed failure mode of exactly this revert, just a noisier one than
    a clean assertion.)"""
    inputs = _demo_deal_inputs()
    baseline_price = inputs.financing.purchase_price
    total_opex_y1 = run_financial_model(inputs).years[0].total_opex

    stand_in = _mutating_perturb_stand_in(recourse_mod._perturb)
    stand_in(inputs, "purchase_price", 1_000.0, total_opex_y1=total_opex_y1)

    assert inputs.financing.purchase_price != baseline_price  # THE CORRUPTION the real code prevents
