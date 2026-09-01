# tests/unit/test_recourse_combinations.py
"""
Unit coverage for the multi-lever recourse search (Mission 5, Half B / IB.1) in
`src.market.recourse`: the per-subset solve (AD direction, bisected distance), the unified joint
plausibility gate (R1/R2/R3), the THREE-outcome contract (found / proven_null / undetermined),
confirm-by-rerun provenance, determinism, and the GD3 lever-partition scope pin.

Fixtures are the two committed sample deals (`82_champlain_dieppe` — gate open, 3 failing, fills
the section; `36_kelly_moncton` — the proven-null stress case D.5 established from the dense
frontier: 0/91 feasible points pass the joint gate) plus one derived deal (kelly at a 2% lower
price) that lands the honest-null-with-exemplar path on real engine numbers.
"""

from __future__ import annotations

from typing import get_args

import pytest

from src.agents.chief_strategist import guardrail_checks_from_metrics
from src.core.finance.engine import metrics_of, precompute_income, run_financial_model
from src.core.finance.jacobian import forecast_metrics_with_jacobian
from src.inputs.inputs import load_inputs
from src.market.recourse import (
    _COMBINATION_ASK_BUDGET,
    _COMBINATION_RAY_TOL,
    _LEVER_ORDER,
    _MIN_COMBINATION_LEVERS,
    DEFAULT_COMBINATION_MAX_ITER,
    _baseline_value,
    _combination_subsets,
    _derive_snapshot,
    _direction_weights,
    _failing_guardrails,
    _judge_plausibility,
    _lever_cap,
    _lever_directions,
    _live_guardrails,
    _metric,
    _perturb_combo,
    _ray_asks,
    compute_combinations,
    compute_recourse,
    judge_combination,
)
from src.schemas.models import CombinationLeverMove, FinancialInputs

_CHAMPLAIN = "data/sample_listings/82_champlain_dieppe/inputs.json"
_KELLY = "data/sample_listings/36_kelly_moncton/inputs.json"


def _champlain() -> FinancialInputs:
    return load_inputs(_CHAMPLAIN).inputs


def _kelly() -> FinancialInputs:
    return load_inputs(_KELLY).inputs


def _kelly_98() -> FinancialInputs:
    """Kelly at a 2% lower price: gate-open-adjacent deal shape whose ONLY within-budget crossing
    is gate-rejected by R2 — the honest-null-with-exemplar path, on real engine numbers."""
    fi = _kelly()
    return fi.model_copy(update={"financing": fi.financing.model_copy(update={"purchase_price": fi.financing.purchase_price * 0.98})})


def _baseline_artifacts(fi: FinancialInputs):
    pre = precompute_income(fi.income)
    base_forecast = run_financial_model(fi, precomputed_income=pre)
    bm = metrics_of(base_forecast)
    live = _live_guardrails(fi.market)
    failing = _failing_guardrails(guardrail_checks_from_metrics(bm, fi.market), live)
    snapshot = _derive_snapshot(fi, base_forecast)
    total_opex = base_forecast.years[0].total_opex
    baselines = {lever: _baseline_value(fi, lever, total_opex_y1=total_opex) for lever in _LEVER_ORDER}
    return pre, bm, live, failing, snapshot, total_opex, baselines


# ---------------------------------------------------------------------------
# The worked jointly-implausible fixture (D.4 §3, orchestrator-verified) — R2 fires JOINTLY
# ---------------------------------------------------------------------------


def test_r2_joint_worked_fixture_individually_fine_jointly_implausible():
    """82_champlain: rate −90 bps + price −$90,000 (14.88%). Each lever passes the production
    single-lever `_judge_plausibility`; jointly, the engine-computed implied-cap delta (+121 bps)
    against the −90 bps rate delta trips the rejector's own cross-axis rule
    (|−0.0090 − (+0.0121)| = 0.0211 > 0.02) through the UNMODIFIED `reject_unrealistic`."""
    fi = _champlain()
    _, bm, live, failing, snapshot, total_opex, baselines = _baseline_artifacts(fi)
    assert failing == ("dscr", "spread", "coc")

    asks = (("purchase_price", 90_000.0), ("interest_rate", 0.0090))
    target = metrics_of(run_financial_model(_perturb_combo(fi, asks, total_opex_y1=total_opex)))

    # Not a strawman: the combination genuinely closes every failing guardrail (real re-run).
    checks = guardrail_checks_from_metrics(target, fi.market)
    from src.market.recourse import _num_fails

    assert _num_fails(checks, live) == 0

    # Each lever individually plausible, through the REAL production single-lever judge, on both
    # a cap-proxy guardrail (spread) and a non-proxy one (dscr) — D.4's four verified rows.
    for lever, delta in (("interest_rate", -0.0090), ("purchase_price", -90_000.0)):
        single = metrics_of(run_financial_model(_perturb_combo(fi, ((lever, abs(delta)),), total_opex_y1=total_opex)))
        for guardrail in ("dscr", "spread"):
            plausible, _ = _judge_plausibility(
                lever=lever,
                guardrail=guardrail,
                delta=delta,
                relative_change=abs(delta) / abs(baselines[lever]),
                base_forecast=bm,
                target_forecast=single,
                snapshot=snapshot,
                market=fi.market,
            )
            assert plausible is True, f"{lever} should be individually plausible vs {guardrail}"

    # Jointly: ONE MarketHypothesis carrying both axes -> reject_unrealistic -> implausible.
    cap_delta = target.cap_rate - bm.cap_rate
    assert cap_delta == pytest.approx(0.0121, abs=0.0002)
    judgment = judge_combination(
        {"interest_rate": -0.0090, "purchase_price": -90_000.0},
        base_metrics=bm,
        target_metrics=target,
        baselines=baselines,
        snapshot=snapshot,
        market=fi.market,
    )
    assert judgment.plausible is False
    assert judgment.tripped_rules == ("R2",)
    # PD.2 R2 condition 1: the reason names both numbers and the bound.
    reason = " ".join(judgment.reasons)
    assert "90 bps rate cut" in reason
    assert "+121 bps" in reason
    assert "200 bps" in reason


def test_r2_fires_with_rate_lever_untouched():
    """D.4's second measured variant: price −15% + opex −20%, NO rate move — the joint rule still
    fires (|0 − (+0.0202)| > 0.02), proving R2 is not merely a rate-lever rule."""
    fi = _champlain()
    _, bm, _, _, snapshot, total_opex, baselines = _baseline_artifacts(fi)
    asks = (
        ("purchase_price", 0.15 * baselines["purchase_price"]),
        ("annual_opex", 0.20 * baselines["annual_opex"]),
    )
    target = metrics_of(run_financial_model(_perturb_combo(fi, asks, total_opex_y1=total_opex)))
    judgment = judge_combination(
        {"purchase_price": -asks[0][1], "annual_opex": -asks[1][1]},
        base_metrics=bm,
        target_metrics=target,
        baselines=baselines,
        snapshot=snapshot,
        market=fi.market,
    )
    assert judgment.plausible is False
    assert "R2" in judgment.tripped_rules


def test_r2_collapses_honestly_when_cap_rate_is_overridden():
    """PD.2 R2 binding condition 3: with `market.cap_rate_purchase` overridden the implied cap
    cannot move, so `cap_rate_delta` is 0 and R2 collapses to |rate_delta| <= 0.02 — weaker than
    R1's own 100 bps cap, i.e. INERT. Pinned so 'this rule silently does nothing on override
    deals' cannot rot into a surprise."""
    fi = _champlain()
    _, bm, _, _, _, total_opex, baselines = _baseline_artifacts(fi)
    fi_ovr = fi.model_copy(update={"market": fi.market.model_copy(update={"cap_rate_purchase": bm.cap_rate})})
    pre_o = precompute_income(fi_ovr.income)
    base_o = run_financial_model(fi_ovr, precomputed_income=pre_o)
    bmo = metrics_of(base_o)
    snap_o = _derive_snapshot(fi_ovr, base_o)
    asks = (("purchase_price", 90_000.0), ("interest_rate", 0.0090))
    target = metrics_of(run_financial_model(_perturb_combo(fi_ovr, asks, total_opex_y1=total_opex)))
    assert target.cap_rate == bmo.cap_rate  # the override pins the implied cap
    judgment = judge_combination(
        {"interest_rate": -0.0090, "purchase_price": -90_000.0},
        base_metrics=bmo,
        target_metrics=target,
        baselines=baselines,
        snapshot=snap_o,
        market=fi_ovr.market,
    )
    # The exact combination R2 rejects on the un-overridden deal sails through: R2 is inert here.
    assert "R2" not in judgment.tripped_rules
    assert judgment.plausible is True


# ---------------------------------------------------------------------------
# R1 and R3 — self-contained gate rules
# ---------------------------------------------------------------------------


def test_r1_trips_on_an_over_cap_ask():
    fi = _champlain()
    _, bm, _, _, snapshot, total_opex, baselines = _baseline_artifacts(fi)
    over = 0.16 * baselines["purchase_price"]  # past the 15% single-ask cap
    target = metrics_of(
        run_financial_model(_perturb_combo(fi, (("purchase_price", over), ("annual_opex", 100.0)), total_opex_y1=total_opex))
    )
    judgment = judge_combination(
        {"purchase_price": -over, "annual_opex": -100.0},
        base_metrics=bm,
        target_metrics=target,
        baselines=baselines,
        snapshot=snapshot,
        market=fi.market,
    )
    assert "R1" in judgment.tripped_rules
    assert judgment.plausible is False


def test_r3_budget_is_derived_from_the_arity_floor_not_typed():
    """PD.2 R3 condition 1 (no magic float): the budget IS the arity floor, expressed in the
    sum's own unit (maxed-out single asks). Change the floor and the budget must move with it."""
    assert _COMBINATION_ASK_BUDGET == float(_MIN_COMBINATION_LEVERS)
    assert _MIN_COMBINATION_LEVERS == 2


def test_r3_trips_and_states_its_unit():
    fi = _champlain()
    _, bm, _, _, snapshot, total_opex, baselines = _baseline_artifacts(fi)
    # Three levers each at ~90% of their own cap: sum of fractions ~2.7 > 2.0.
    asks = (
        ("rent_per_unit_month", 0.9 * _lever_cap("rent_per_unit_month", baseline_value=baselines["rent_per_unit_month"])),
        ("interest_rate", 0.9 * _lever_cap("interest_rate", baseline_value=baselines["interest_rate"])),
        ("annual_opex", 0.9 * _lever_cap("annual_opex", baseline_value=baselines["annual_opex"])),
    )
    target = metrics_of(run_financial_model(_perturb_combo(fi, asks, total_opex_y1=total_opex)))
    judgment = judge_combination(
        {"rent_per_unit_month": asks[0][1], "interest_rate": -asks[1][1], "annual_opex": -asks[2][1]},
        base_metrics=bm,
        target_metrics=target,
        baselines=baselines,
        snapshot=snapshot,
        market=fi.market,
    )
    assert "R3" in judgment.tripped_rules
    # PD.2 R3 condition 3: the rule states itself in its own unit wherever it bites.
    assert any("maxed-out single asks" in r for r in judgment.reasons)


def test_r3_band_assertion_on_the_rays_production_walks():
    """PD.2 R3 condition 2, the executable band assertion: the budget sits strictly between the
    largest unclipped crossing on the gate-open committed deal and the smallest on the
    gate-closed one — measured on the REAL rays production walks (the AD-gradient ray and the
    balanced fallback, per subset), not a proxy. If this goes red, B goes back to the founder
    proxy; it does not get widened on shift."""

    def crossings(fi: FinancialInputs) -> list[float]:
        pre, bm, live, failing, _, total_opex, baselines = _baseline_artifacts(fi)
        caps = {lever: _lever_cap(lever, baseline_value=baselines[lever]) for lever in _LEVER_ORDER}
        available = tuple(lever for lever in _LEVER_ORDER if caps[lever] > 0.0)
        jac = forecast_metrics_with_jacobian(fi, _lever_directions(fi, available, total_opex_y1=total_opex), precomputed_income=pre)
        from src.core.finance.engine import forecast_metrics
        from src.market.recourse import _num_fails

        def feasible(asks) -> bool:
            m = forecast_metrics(_perturb_combo(fi, asks, total_opex_y1=total_opex))
            return _num_fails(guardrail_checks_from_metrics(m, fi.market), live) == 0

        sums: list[float] = []
        for subset in _combination_subsets(available):
            gradient = _direction_weights(subset, jac, failing=failing, market=fi.market, caps=caps)
            balanced = tuple(1.0 for _ in subset)
            rays = (gradient, balanced) if gradient != balanced else (balanced,)
            for weights in rays:
                if not feasible(_ray_asks(subset, weights, caps, 1.0)):  # full-box edge, UNCLIPPED
                    continue
                lo, hi = 0.0, 1.0
                while hi - lo > _COMBINATION_RAY_TOL:
                    mid = (lo + hi) / 2.0
                    if feasible(_ray_asks(subset, weights, caps, mid)):
                        hi = mid
                    else:
                        lo = mid
                sums.append(hi * sum(weights))
        return sums

    open_deal = crossings(_champlain())
    closed_deal = crossings(_kelly())
    assert open_deal, "gate-open deal must have crossings"
    assert closed_deal, "gate-closed deal must have reachable crossings at the full box"
    assert max(open_deal) < _COMBINATION_ASK_BUDGET < min(closed_deal)


# ---------------------------------------------------------------------------
# End-to-end: found / proven_null / undetermined — the three-outcome contract
# ---------------------------------------------------------------------------


def test_champlain_fills_the_section_and_every_combination_is_rerun_confirmed():
    """Outcome `found`; every shipped combination closes ALL live guardrails, verified here by an
    INDEPENDENT full `run_financial_model` re-run at the shipped asks whose margins must equal
    the shipped `confirmed_margins` exactly — the number on the page and the metric beside it
    come from the same run (AD proposes; the engine confirms)."""
    fi = _champlain()
    _, _, live, _, _, total_opex, baselines = _baseline_artifacts(fi)
    ca = compute_combinations(fi)
    assert ca.attempted is True
    assert ca.outcome == "found"
    assert ca.honest_null is False
    assert ca.subsets_searched == 11
    assert len(ca.combinations) >= 1
    assert ca.rejected_exemplar is None  # exemplar ships ONLY on the honest null (PD.2 call 4)

    from src.market.recourse import _GUARDRAIL_ORDER, _num_fails

    for combo in ca.combinations:
        assert combo.closes_all_live_guardrails is True
        assert len(combo.moves) >= _MIN_COMBINATION_LEVERS
        # moves in fixed _LEVER_ORDER, all inside their own caps, GD3-closed lever names
        levers = tuple(m.lever for m in combo.moves)
        assert levers == tuple(lv for lv in _LEVER_ORDER if lv in set(levers))
        for m in combo.moves:
            assert 0.0 < m.fraction_of_cap <= 1.0 + 1e-9
            assert m.target_value == pytest.approx(m.baseline_value + m.delta)
        assert combo.total_fraction_of_caps == pytest.approx(sum(m.fraction_of_cap for m in combo.moves))

        # THE CONFIRM-BY-RERUN PIN: independent full engine run at the shipped asks.
        asks = tuple((m.lever, abs(m.delta)) for m in combo.moves)
        rerun = metrics_of(run_financial_model(_perturb_combo(fi, asks, total_opex_y1=total_opex)))
        assert _num_fails(guardrail_checks_from_metrics(rerun, fi.market), live) == 0
        expected = {g: _metric(rerun, g) for g in _GUARDRAIL_ORDER if g in live}
        shipped = {gm.guardrail: gm.value for gm in combo.confirmed_margins}
        assert shipped == expected  # exact equality: same engine, same inputs, same run semantics
        for gm in combo.confirmed_margins:
            assert gm.value >= gm.bar  # every live bar cleared, not only the originally-failing


def test_cheapest_total_label_is_the_true_argmin():
    """No ranking ships (founder call superseding the top-3 ordering); the one label is an argmin
    over the set already computed — re-derived here independently."""
    ca = compute_combinations(_champlain())
    assert ca.combinations and ca.cheapest_total_index is not None
    totals = [c.total_fraction_of_caps for c in ca.combinations]
    assert ca.cheapest_total_index == totals.index(min(totals))


def test_kelly_proven_null_with_explained_counters():
    """D.5 proved 36_kelly's null from the dense frontier (0/91 feasible points pass the gate).
    Production must land the same verdict as `proven_null` — a completed search, never an
    exhausted one — with every subset's exit named in a counter."""
    ca = compute_combinations(_kelly())
    assert ca.attempted is True
    assert ca.outcome == "proven_null"
    assert ca.honest_null is True
    assert ca.combinations == ()
    assert ca.cheapest_total_index is None
    assert ca.subsets_exhausted == 0  # a proven null is NEVER an exhausted search
    accounted = (
        ca.subsets_infeasible
        + ca.subsets_edge_infeasible
        + ca.subsets_gate_rejected
        + ca.subsets_collapsed
        + ca.subsets_exhausted
        + ca.confirm_failed
        + len(ca.combinations)
    )
    assert accounted == ca.subsets_searched == 11


def test_honest_null_ships_the_rejected_exemplar_rerun_confirmed():
    """PD.2 call 4: on a zero-combination result, the minimal-total-ask gate-rejected candidate
    ships WITH its reason (adjacent and inseparable), and it went through a real confirming
    re-run exactly like a shipped combination — verified independently here."""
    fi = _kelly_98()
    _, _, live, _, _, total_opex, _ = _baseline_artifacts(fi)
    ca = compute_combinations(fi)
    assert ca.outcome == "proven_null"
    assert ca.honest_null is True
    assert ca.subsets_gate_rejected >= 1
    assert ca.gate_reasons  # the null is explained, not silent
    ex = ca.rejected_exemplar
    assert ex is not None
    assert ex.reason and ex.reason in ca.gate_reasons
    assert ex.combination.closes_all_live_guardrails is True
    # The exemplar's own confirm-by-rerun, re-verified independently:
    from src.market.recourse import _num_fails

    asks = tuple((m.lever, abs(m.delta)) for m in ex.combination.moves)
    rerun = metrics_of(run_financial_model(_perturb_combo(fi, asks, total_opex_y1=total_opex)))
    assert _num_fails(guardrail_checks_from_metrics(rerun, fi.market), live) == 0


def test_max_iter_exhaustion_is_undetermined_never_a_null():
    """The founder-required `max_iter` bound: an exhausted budget is reported as UNDETERMINED —
    structurally distinct from a proven null (`outcome` literal + `honest_null` stays False) —
    and deterministically (same inputs, same exhaustion point, byte-identical payloads)."""
    fi = _champlain()
    ca1 = compute_combinations(fi, max_iter=3)
    ca2 = compute_combinations(fi, max_iter=3)
    assert ca1.outcome == "undetermined"
    assert ca1.honest_null is False  # NEVER "nothing can save this deal" when we ran out of budget
    assert ca1.combinations == ()
    assert ca1.subsets_exhausted == 11
    assert ca1.max_iter == 3
    assert ca1.model_dump_json() == ca2.model_dump_json()
    # And a budget large enough to finish reports found again — the bound only ever stops search.
    assert compute_combinations(fi, max_iter=DEFAULT_COMBINATION_MAX_ITER).outcome == "found"


def test_max_iter_must_be_positive():
    with pytest.raises(ValueError):
        compute_combinations(_champlain(), max_iter=0)


def test_nothing_to_search_is_not_attempted():
    """A deal with zero failing live guardrails: attempted False, outcome None — not a null."""
    from tests.utils import make_financial_inputs

    good = make_financial_inputs(num_units=6)
    good = good.model_copy(
        update={
            "financing": good.financing.model_copy(update={"purchase_price": 380_000.0, "down_payment_rate": 0.30}),
            "income": good.income.model_copy(update={"occupancy": 0.97, "bad_debt_factor": 0.98}),
        }
    )
    ca = compute_combinations(good)
    assert ca.attempted is False
    assert ca.outcome is None
    assert ca.honest_null is False
    assert ca.combinations == ()


# ---------------------------------------------------------------------------
# Determinism — byte-identical output, no dict/set iteration order anywhere
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", [_CHAMPLAIN, _KELLY])
def test_byte_identical_repeats(path: str):
    fi = load_inputs(path).inputs
    assert compute_combinations(fi).model_dump_json() == compute_combinations(fi).model_dump_json()


# ---------------------------------------------------------------------------
# Integration with compute_recourse — additive, flag-don't-remove
# ---------------------------------------------------------------------------


def test_compute_recourse_carries_the_combination_section_additively():
    """Both sections ship: the Mission 4 single-lever menu is untouched and the combination
    analysis rides beside it (the founder: 'we do not know if the investor can act on one or
    multiple levers')."""
    ra = compute_recourse(_champlain())
    assert ra.levers  # the single-lever menu is still there, untouched
    assert ra.combinations is not None
    assert ra.combinations.attempted is True
    assert ra.combinations.outcome == "found"
    # And it matches the standalone computation byte-for-byte (same baseline discipline).
    assert ra.combinations.model_dump_json() == compute_combinations(_champlain()).model_dump_json()


# ---------------------------------------------------------------------------
# GD3 — the lever/assumption partition (C6: the candidate space is levers only)
# ---------------------------------------------------------------------------


def test_gd3_combination_space_contains_no_assumption_axis():
    """GD3-C6: the combination search enumerates subsets of the four investor levers ONLY, and
    the shipped schema cannot express an assumption as an ask (`CombinationLeverMove.lever` is
    closed to the same Literal as `recourse.LeverName`). Extending either set requires editing
    the declaration that carries the GD3 invariant — a founder-visible event by construction."""
    subsets = _combination_subsets(_LEVER_ORDER)
    assert len(subsets) == 11  # 2^4 - 1 - 4 singletons
    lever_set = set(_LEVER_ORDER)
    for subset in subsets:
        assert len(subset) >= _MIN_COMBINATION_LEVERS
        assert set(subset) <= lever_set
    schema_levers = get_args(CombinationLeverMove.model_fields["lever"].annotation)
    assert tuple(schema_levers) == _LEVER_ORDER
    for banned in ("occupancy", "vacancy", "rent_growth", "expense_growth", "exit_cap", "cap_rate_drift", "horizon"):
        assert all(banned not in lever for lever in schema_levers)


# ---------------------------------------------------------------------------
# B2 (Mission 5 Gate V, 2026-08-31): R2 is TOTAL — a rejector rejection always carries a reason
# ---------------------------------------------------------------------------
#
# RED, captured on the pre-fix code (judge_combination re-derived "which rule fired" from
# duplicated literals and reproduced only 2 of the rejector's 4 rules): any deal with
# occupancy < 0.80 puts `_derive_snapshot`'s vacancy (1 - occupancy) past the rejector's 20%
# band, so R2 tripped with `reasons=()` and `RejectedCombination(reason="")` crashed the whole
# analysis run (`crew.py` calls `build_recourse` unguarded):
#
#   pydantic_core._pydantic_core.ValidationError: 1 validation error for RejectedCombination
#   reason
#     String should have at least 1 character [type=string_too_short, input_value='', ...]
#
# The fix: the gate asks the rejector WHICH rule fired (`violated_hard_rules`, the exact function
# `reject_unrealistic`'s hard pass delegates to) and maps each named rule through the TOTAL
# `_r2_reason` — so R2 tripping implies >= 1 reason, by construction.

from src.market.recourse import _perturb, _r2_reason, _rejector_flagged, is_genuinely_close  # noqa: E402
from src.market.rejector import (  # noqa: E402
    CAP_RATE_MAX,
    CAP_RATE_MIN,
    HARD_RULES,
    RATES_VS_CAP_MAX_DIVERGENCE,
    VACANCY_MAX,
    VACANCY_MIN,
)
from tests import make_snapshot  # noqa: E402


def _champlain_low_occupancy() -> FinancialInputs:
    """The Gate V B2 repro: champlain at occupancy 0.795 (derived vacancy 20.5% > the rejector's
    20% band — a routine distressed-multifamily shape), rents x1.05 and price x0.7 so the
    near-miss gate (`is_genuinely_close`) opens and the combination search actually runs."""
    fi = _champlain()
    income = fi.income.model_copy(
        update={
            "occupancy": 0.795,
            "units": tuple(u.model_copy(update={"rent_month": u.rent_month * 1.05}) for u in fi.income.units),
        }
    )
    financing = fi.financing.model_copy(update={"purchase_price": fi.financing.purchase_price * 0.7})
    return fi.model_copy(update={"income": income, "financing": financing})


def test_b2_low_occupancy_deal_completes_with_a_printed_reason_not_a_crash():
    """The crash case (harm 1) AND the silence case (harm 2), on the pipeline-reachable path:
    the run completes, the gate-rejection count carries a "why", and the why names the deal's
    baseline vacancy — the axis the rejector actually fired on, which no investor lever moves —
    never an empty string against `RejectedCombination.reason`'s min_length=1."""
    fi = _champlain_low_occupancy()
    assert is_genuinely_close(fi), "repro invariant: the near-miss gate must open (crew.py path)"
    analysis = compute_combinations(fi)  # RED: raised pydantic ValidationError (string_too_short)
    assert analysis.subsets_gate_rejected > 0
    assert analysis.gate_reasons, "a rejection count with no 'why' beside it is silence with a receipt (PD.2 call 4)"
    assert any("baseline vacancy" in r for r in analysis.gate_reasons)
    if analysis.rejected_exemplar is not None:
        assert analysis.rejected_exemplar.reason.strip()
    # The three-outcome contract is untouched: this is a completed search, never a crash.
    assert analysis.outcome in ("found", "proven_null", "undetermined")


def test_b2_r2_vacancy_rejection_names_the_baseline_not_the_combination():
    """Unit view of the same defect: R2 trips on the vacancy-bounds rule alone (rate and cap
    deltas both inside their bands) and the reason (a) exists and (b) attributes the rejection to
    the deal's baseline vacancy, stating the actual number — not to the size of the asks."""
    fi = _champlain_low_occupancy()
    _, bm, _, _, snapshot, total_opex, baselines = _baseline_artifacts(fi)
    assert snapshot.vacancy_rate == pytest.approx(0.205)  # past the rejector's 20% band at BASELINE
    asks = (("purchase_price", 10_000.0), ("annual_opex", 1_000.0))  # tiny: cap delta stays in-band
    target = metrics_of(run_financial_model(_perturb_combo(fi, asks, total_opex_y1=total_opex)))
    assert abs(target.cap_rate - bm.cap_rate) <= RATES_VS_CAP_MAX_DIVERGENCE  # only vacancy can fire
    judgment = judge_combination(
        {"purchase_price": -10_000.0, "annual_opex": -1_000.0},
        base_metrics=bm,
        target_metrics=target,
        baselines=baselines,
        snapshot=snapshot,
        market=fi.market,
    )
    assert "R2" in judgment.tripped_rules
    assert judgment.reasons, "B2: R2 tripped with zero reasons is the exact defect this pins"
    joined = " ".join(judgment.reasons)
    assert "baseline vacancy of 20.5%" in joined
    assert "not about the asks" in joined


def test_b2_r2_tripping_implies_reasons_structurally():
    """The structural guarantee: `_r2_reason` is TOTAL over `HardRule` — every rule the rejector
    can name maps to a non-empty reason string (mypy proves the chain exhaustive at type-check
    time; this pins the runtime side, including the rules R2's hypothesis construction cannot
    reach today, so a future edit that reaches them still gets words)."""
    snap = make_snapshot(vacancy_rate=0.205, cap_rate=0.02)  # every rule violated or violable
    for rule in HARD_RULES:
        reason = _r2_reason(rule, rate_delta=-0.0090, cap_delta=0.0121, snapshot=snap)
        assert isinstance(reason, str) and reason.strip(), f"hard rule {rule!r} must map to words"


def test_b2_gate_messages_state_the_rejector_own_thresholds():
    """Threshold-drift guard: the numbers in R2's copy are RENDERED FROM the rejector's named
    constants (`rejector.py` names them once; `recourse` imports them), so the decision and the
    message can only move together, in one diff. The value pins make a move a deliberate act."""
    snap = make_snapshot()
    divergence = _r2_reason("rates_vs_cap", rate_delta=-0.0090, cap_delta=0.0121, snapshot=snap)
    assert f"{RATES_VS_CAP_MAX_DIVERGENCE * 10_000:.0f} bps divergence" in divergence
    cap = _r2_reason("cap_bounds", rate_delta=0.0, cap_delta=0.09, snapshot=snap)
    assert f"[{CAP_RATE_MIN:.2%}, {CAP_RATE_MAX:.2%}]" in cap
    vacancy = _r2_reason("vacancy_bounds", rate_delta=0.0, cap_delta=0.0, snapshot=snap)
    assert f"[{VACANCY_MIN:.0%}, {VACANCY_MAX:.0%}]" in vacancy
    assert (RATES_VS_CAP_MAX_DIVERGENCE, CAP_RATE_MIN, CAP_RATE_MAX, VACANCY_MIN, VACANCY_MAX) == (
        0.02,
        0.03,
        0.12,
        0.00,
        0.20,
    )


def test_b2_single_lever_rejector_message_names_the_vacancy_axis_when_it_is_the_cause():
    """Companion fix, single-lever path: `_rejector_flagged` used to assume the cap-band rule and
    would label a baseline-vacancy rejection as 'pushes the implied cap rate outside [3%, 12%]' —
    a false statement. It now asks the rejector which rule fired and says the true thing."""
    fi = _champlain_low_occupancy()
    _, bm, _, _, snapshot, total_opex, _ = _baseline_artifacts(fi)
    target = metrics_of(run_financial_model(_perturb(fi, "purchase_price", 10_000.0, total_opex_y1=total_opex)))
    flagged, reason = _rejector_flagged(
        lever="purchase_price",
        guardrail="spread",
        delta=-10_000.0,
        base_forecast=bm,
        target_forecast=target,
        snapshot=snapshot,
        market=fi.market,
    )
    assert flagged is True  # the DECISION is unchanged: the rejector still rejects
    assert reason is not None and "baseline vacancy" in reason
    assert "cap rate" not in reason  # never the mislabeled cap-band claim
