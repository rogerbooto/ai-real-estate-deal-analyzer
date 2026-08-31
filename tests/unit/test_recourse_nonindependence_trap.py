# tests/unit/test_recourse_nonindependence_trap.py
"""THE CENTREPIECE (Mission 4, task I.2): the non-independence trap.

The levers in `src.market.recourse` are not independent -- a purchase-price cut shrinks the loan,
lifts the cap rate, and changes cash-in *simultaneously*. Every recourse answer MUST come from
re-running `run_financial_model` on a perturbed copy of the inputs, never from algebraically
inverting a guardrail formula. A formula inversion gives a confidently wrong number.

The trap case (independently re-derived here, not merely asserted): for the `coc` guardrail via
the `purchase_price` lever, `coc = cash_flow_y1(price) / acquisition_cash(price)` has BOTH the
numerator (via the annual debt service, which scales with the loan) and the denominator (the down
payment + upfront MIP, both proportional to price) depend on price. A naive implementer who
inverts the CoC formula while freezing `acquisition_cash` at its BASELINE value (forgetting that a
price cut also shrinks the down payment and the MIP add-on) computes a target price that looks
plausible in isolation but is provably wrong once re-run through the real engine.

Every OTHER lever/guardrail pair in this engine is an exact, closed-form relationship with no
hidden coupling (see `test_only_coc_shows_the_coupling_dscr_does_not` below, which proves this
concretely for `dscr`) -- `coc` is the one guardrail where the numerator AND the denominator both
move with the same lever, which is exactly why "just solve for x" is a real, tempting, wrong
shortcut for this one pair, and exactly why the re-run discipline is not optional for any of them.

Every number asserted below was independently re-derived against the live engine (never assumed):

    baseline purchase_price ............... $399,900.00
    baseline acquisition_cash ($45,991.00 -- FROZEN by the naive/buggy inversion below)
    true re-run flip point ................ $341,057.63   (CoC there == 3.000000%, inclusive bar)
    naive formula-inversion answer ........ $338,814.34   (its OWN believed CoC there: 3.00% --
                                                            its REAL re-run CoC there: 3.4073%)
    divergence ............................. $2,243.29    (~22x the $100 price search tolerance)
    shipped module's rounded ask ........... a $58,900 cut -> target $341,000.00, re-run CoC 3.0104%
"""

from __future__ import annotations

import pytest

from src.agents.chief_strategist import MIN_COC_Y1, MIN_DSCR_Y1, guardrail_checks_from_metrics
from src.core.finance.engine import metrics_of, run_financial_model
from src.inputs.inputs import load_inputs
from src.market import recourse as recourse_mod
from src.market.recourse import ROUND_STEP, compute_recourse
from src.schemas.models import FinancialInputs

_DEMO_DEAL_PATH = "data/sample_listings/36_kelly_moncton/inputs.json"

# Independently re-derived, not copied from the module under test.
_TRUE_REREUN_FLIP_UNROUNDED = 341_057.63
_NAIVE_FORMULA_ANSWER = 338_814.34
_NAIVE_FORMULA_REAL_COC_AT_ITS_OWN_ANSWER = 0.034073  # ~3.4073%, NOT the 3.00% it believed
_SHIPPED_ROUNDED_TARGET = 341_000.0
_SHIPPED_ROUNDED_DELTA = -58_900.0
_DIVERGENCE = _TRUE_REREUN_FLIP_UNROUNDED - _NAIVE_FORMULA_ANSWER  # ~$2,243.29


def _demo_deal_inputs() -> FinancialInputs:
    return load_inputs(_DEMO_DEAL_PATH).inputs


def _naive_price_for_coc_target(inputs: FinancialInputs, *, target_coc: float = MIN_COC_Y1) -> float:
    """THE BUG, reproduced as a pure, closed-form calculation (never calling the module under
    test): solve `coc(price) = target_coc` for `price`, freezing `acquisition_cash` at the
    BASELINE value -- exactly the tempting shortcut the module's docstring warns against.

    Debt service scales linearly with the loan (`loan0 = price * (1 - down_payment_rate)`) for a
    fixed rate/term, so `payment_per_dollar` (read off one real baseline run, not re-derived) lets
    this stay a pure scaling calculation with no amortization-formula reimplementation.
    """
    base = run_financial_model(inputs)
    y1 = base.years[0]
    pm = base.purchase
    f = inputs.financing
    loan0_baseline = f.purchase_price * (1 - f.down_payment_rate)
    payment_per_dollar = pm.annual_debt_service / loan0_baseline
    acquisition_cash_baseline = pm.acquisition_cash  # <-- THE BUG: never recomputed at the new price
    return (y1.noi - target_coc * acquisition_cash_baseline) / (payment_per_dollar * (1 - f.down_payment_rate))


def _true_rerun_flip_price(inputs: FinancialInputs, *, guardrail_ok, tol: float = 0.01) -> float:
    """An independent (re-run-based, never algebraic) bisection for the smallest price whose
    REAL re-run clears `guardrail_ok`. Deliberately NOT imported from `src.market.recourse` --
    this is the oracle the module under test is judged against, not a copy of its own machinery.
    """
    lo, hi = 1.0, inputs.financing.purchase_price
    for _ in range(80):
        mid = (lo + hi) / 2.0
        perturbed = inputs.model_copy(update={"financing": inputs.financing.model_copy(update={"purchase_price": mid})})
        forecast = run_financial_model(perturbed)
        if guardrail_ok(forecast):
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return hi


# ---------------------------------------------------------------------------
# 1) The shipped module's answer IS the re-run answer, and IS NOT the naive answer.
# ---------------------------------------------------------------------------


def test_shipped_price_coc_row_matches_true_rerun_not_naive_formula():
    inputs = _demo_deal_inputs()
    analysis = compute_recourse(inputs)
    row = next(r for r in analysis.levers if r.lever == "purchase_price" and r.guardrail == "coc")

    assert row.closes_guardrail is True
    # Matches the true re-run answer (rounded away from zero, re-confirmed by re-run).
    assert row.target_value == pytest.approx(_SHIPPED_ROUNDED_TARGET, abs=1.0)
    assert row.delta == pytest.approx(_SHIPPED_ROUNDED_DELTA, abs=1.0)

    # Does NOT match the naive formula-inversion answer -- the divergence ($2,243.29) is far
    # larger than any rounding/tolerance noise ($100 bisection tol, $100 rounding step).
    assert row.target_value != pytest.approx(_NAIVE_FORMULA_ANSWER, abs=250.0)
    assert abs(row.target_value - _NAIVE_FORMULA_ANSWER) > 2_000.0

    # The rounded ask actually clears the bar when fed back through the real engine.
    perturbed = inputs.model_copy(update={"financing": inputs.financing.model_copy(update={"purchase_price": row.target_value})})
    forecast = run_financial_model(perturbed)
    assert forecast.purchase.coc >= MIN_COC_Y1


def test_true_rerun_flip_point_is_independently_reproducible():
    """The true flip point, re-derived HERE via an independent re-run bisection (not imported
    from the module under test), lands where this file's module docstring claims."""
    inputs = _demo_deal_inputs()
    flip = _true_rerun_flip_price(inputs, guardrail_ok=lambda f: f.purchase.coc >= MIN_COC_Y1)
    assert flip == pytest.approx(_TRUE_REREUN_FLIP_UNROUNDED, abs=1.0)

    perturbed = inputs.model_copy(update={"financing": inputs.financing.model_copy(update={"purchase_price": flip})})
    forecast = run_financial_model(perturbed)
    assert forecast.purchase.coc == pytest.approx(MIN_COC_Y1, abs=1e-4)


# ---------------------------------------------------------------------------
# 2) The naive formula is not just "a bit off" -- it is WRONG about its own answer.
# ---------------------------------------------------------------------------


def test_naive_formula_believes_the_wrong_coc_at_its_own_answer():
    """The naive answer does not merely undershoot/overshoot the bar by a rounding hair -- when
    actually re-run, its real CoC (3.4073%) is NOT the 3.00% bar the naive algebra believed it
    was landing on exactly. This is the crux of the trap: the naive formula is not "close but
    imprecise", it is *provably inconsistent with itself* once you stop trusting the formula and
    re-run the real engine."""
    inputs = _demo_deal_inputs()
    naive_price = _naive_price_for_coc_target(inputs, target_coc=MIN_COC_Y1)
    assert naive_price == pytest.approx(_NAIVE_FORMULA_ANSWER, abs=1.0)

    perturbed = inputs.model_copy(update={"financing": inputs.financing.model_copy(update={"purchase_price": naive_price})})
    real_coc_at_naive_answer = run_financial_model(perturbed).purchase.coc

    assert real_coc_at_naive_answer == pytest.approx(_NAIVE_FORMULA_REAL_COC_AT_ITS_OWN_ANSWER, abs=1e-4)
    # NOT the 3.00% bar the naive algebra believed it had hit exactly.
    assert real_coc_at_naive_answer != pytest.approx(MIN_COC_Y1, abs=1e-3)


def test_naive_vs_true_divergence_dwarfs_the_search_tolerance():
    """The divergence ($2,243.29) is ~22x the $100 price-lever bisection tolerance -- this cannot
    be a coincidence of where two independent numerical searches happened to stop; it is a
    structural consequence of freezing acquisition_cash."""
    inputs = _demo_deal_inputs()
    naive_price = _naive_price_for_coc_target(inputs)
    true_flip = _true_rerun_flip_price(inputs, guardrail_ok=lambda f: f.purchase.coc >= MIN_COC_Y1)
    divergence = abs(true_flip - naive_price)

    assert divergence == pytest.approx(_DIVERGENCE, abs=5.0)
    price_lever_tolerance = 100.0  # src.market.recourse._BISECT_TOL["purchase_price"]
    assert divergence > 20 * price_lever_tolerance


# ---------------------------------------------------------------------------
# 3) Why coc, and not another guardrail: dscr is EXACTLY invertible for the same lever.
# ---------------------------------------------------------------------------


def test_only_coc_shows_the_coupling_dscr_does_not():
    """DSCR = noi_y1 / debt_service_y1(price). noi_y1 does not depend on price at all, and
    debt_service scales EXACTLY linearly with the loan for a fixed rate/term -- so, unlike CoC,
    there is no second, price-dependent term hiding in the denominator. A naive closed-form
    inversion for DSCR and an independent re-run-based bisection for DSCR must land within a
    hair of each other (no $2000+ trap here) -- proving the coupling that makes CoC special is a
    real, structural fact about this one guardrail, not a generic quirk of "any lever, any
    guardrail" in this engine.
    """
    inputs = _demo_deal_inputs()
    base = run_financial_model(inputs)
    y1 = base.years[0]
    pm = base.purchase
    f = inputs.financing
    loan0_baseline = f.purchase_price * (1 - f.down_payment_rate)
    payment_per_dollar = pm.annual_debt_service / loan0_baseline
    naive_dscr_price = y1.noi / (MIN_DSCR_Y1 * payment_per_dollar * (1 - f.down_payment_rate))

    true_dscr_flip = _true_rerun_flip_price(inputs, guardrail_ok=lambda fc: fc.years[0].dscr >= MIN_DSCR_Y1)

    # Essentially zero divergence (well within one bisection tolerance), in stark contrast to
    # CoC's ~$2,243 divergence for the identical lever on the identical deal.
    assert abs(naive_dscr_price - true_dscr_flip) < 5.0


# ---------------------------------------------------------------------------
# 4) THE PROOF: a formula-inverted stand-in for `_bisect` makes this exact test fail.
# ---------------------------------------------------------------------------


def _naive_bisect_stand_in(original_bisect):
    """A drop-in replacement for `src.market.recourse._bisect` that reverts to formula inversion
    for the (purchase_price, coc) pair ONLY -- every other (lever, guardrail) pair still uses the
    real, re-run-based bisection, so this is a surgical revert of exactly the one discipline this
    file exists to guard, not a wholesale rewrite.
    """

    # `precomputed` mirrors `_bisect`'s own signature (the PV.3 rent-roll precompute) and is
    # forwarded untouched, so this stand-in stays a surgical revert of the FORMULA-INVERSION
    # discipline only -- it does not also quietly revert the perf path.
    def _stand_in(inputs, lever, guardrail, market, *, bound, tol, total_opex_y1, horizon_years, precomputed):
        if lever == "purchase_price" and guardrail == "coc":
            naive_price = _naive_price_for_coc_target(inputs, target_coc=MIN_COC_Y1)
            t_star = min(max(inputs.financing.purchase_price - naive_price, 0.0), bound)
            perturbed = inputs.model_copy(
                update={"financing": inputs.financing.model_copy(update={"purchase_price": inputs.financing.purchase_price - t_star})}
            )
            # `_bisect` returns the light `ForecastMetrics` record (PV.3), not a full forecast --
            # mirrored here so the stand-in stays type-faithful to the thing it replaces.
            metrics_star = metrics_of(run_financial_model(perturbed, horizon_years=horizon_years))
            checks_star = guardrail_checks_from_metrics(metrics_star, market)
            return t_star, metrics_star, checks_star
        return original_bisect(
            inputs,
            lever,
            guardrail,
            market,
            bound=bound,
            tol=tol,
            total_opex_y1=total_opex_y1,
            horizon_years=horizon_years,
            precomputed=precomputed,
        )

    return _stand_in


def test_meta_a_formula_inverted_stand_in_fails_this_files_own_trap_assertion(monkeypatch: pytest.MonkeyPatch):
    """RED-when-broken, operationalized permanently: this test monkeypatches the module's OWN
    `_bisect` with a formula-inverted stand-in for the exact (purchase_price, coc) pair, and
    proves that the SAME shape of assertion `test_shipped_price_coc_row_matches_true_rerun_...`
    makes above would then fail. If a future change ever loosens this file's tolerances enough to
    accept the naive answer, THIS test starts failing for a different reason (no exception
    raised inside `pytest.raises`), which is itself a signal that the trap has gone stale.
    """
    original_bisect = recourse_mod._bisect
    monkeypatch.setattr(recourse_mod, "_bisect", _naive_bisect_stand_in(original_bisect))

    inputs = _demo_deal_inputs()
    analysis = recourse_mod.compute_recourse(inputs)
    row = next(r for r in analysis.levers if r.lever == "purchase_price" and r.guardrail == "coc")

    # The formula-inverted stand-in's answer is NOT within a tight band of the true re-run flip.
    with pytest.raises(AssertionError):
        assert row.target_value == pytest.approx(_SHIPPED_ROUNDED_TARGET, abs=1.0)

    # ... and it IS suspiciously close to the naive answer this file independently derived.
    assert row.target_value == pytest.approx(_NAIVE_FORMULA_ANSWER, abs=ROUND_STEP["purchase_price"])
