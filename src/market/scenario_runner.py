# src/market/scenario_runner.py
"""Scenario runner (Mission 1, Wave 2).

Composes the (already-tested) ``src/market`` scenario engine with the **frozen** finance
engine to emit prior-weighted scenario outcomes:

    snapshot -> generate_hypotheses -> reject_unrealistic -> per-scenario engine run -> aggregate

Nothing here edits ``src/core/finance``. Each accepted hypothesis perturbs a deep copy of the
inputs (``adapter.perturb_inputs``) and re-runs ``run_financial_model`` on that copy. The
aggregation is pure-Python (no numpy): a deterministic, no-interpolation inverse-CDF weighted
percentile with a total order over (value asc, hypothesis lexicographic key) — design note §4/§8.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from src.core.finance.engine import run_financial_model
from src.market.adapter import perturb_inputs
from src.market.hypotheses import generate_hypotheses
from src.market.rejector import reject_unrealistic
from src.market.snapshot import build_snapshot
from src.schemas.models import (
    FinancialInputs,
    MarketHypothesis,
    MarketSnapshot,
    ScenarioAnalysis,
    ScenarioMetricBand,
    ScenarioOutcome,
)

# Same lexicographic key the rejector/generator sort by (rejector.py:155-167). Used as the
# total-order tie-break when two scenarios share a metric value, so aggregation is reproducible.
_HypKey = tuple[float, float, float, float, float, bool]

# (value, weight, tie-break key) triples fed to the weighted-percentile aggregator.
_ValueWeightKey = tuple[float, float, _HypKey]


def _hyp_key(h: MarketHypothesis) -> _HypKey:
    return (
        h.rent_delta,
        h.expense_growth_delta,
        h.interest_rate_delta,
        h.cap_rate_delta,
        h.vacancy_delta,
        h.str_viability,
    )


def resolve_snapshot(inputs: FinancialInputs, *, market_block: Mapping[str, Any] | None = None) -> MarketSnapshot:
    """Resolve the ``MarketSnapshot`` for scenario generation (design note §5).

    Source priority:
      1. An explicit ``market`` block (parsed by the existing ``build_snapshot``) — source of truth.
      2. Fallback derivation from ``FinancialInputs`` when no block is present:
         ``region="Unspecified"``, ``vacancy_rate = 1 - income.occupancy``,
         ``rent_growth = income.rent_growth``, ``expense_growth = opex.expense_growth``,
         ``interest_rate = financing.interest_rate``, ``cap_rate = market.cap_rate_purchase``.
      3. Loud fail: if there is no ``market`` block AND the cap cannot be derived
         (``market.cap_rate_purchase is None``), raise a clear ``ValueError`` — we never
         silently invent a cap (invariant #5).
    """
    if market_block is not None:
        return build_snapshot(market_block)

    cap = inputs.market.cap_rate_purchase
    if cap is None:
        raise ValueError(
            "Cannot derive a market snapshot cap rate for scenario analysis: no 'market' block was "
            "provided and inputs.market.cap_rate_purchase is None. Fix by adding a 'market' block to "
            "the inputs (region/vacancy_rate/cap_rate/rent_growth/expense_growth/interest_rate) or by "
            "setting market.cap_rate_purchase."
        )

    return MarketSnapshot(
        region="Unspecified",
        vacancy_rate=1.0 - inputs.income.occupancy,
        cap_rate=cap,
        rent_growth=inputs.income.rent_growth,
        expense_growth=inputs.opex.expense_growth,
        interest_rate=inputs.financing.interest_rate,
        notes="Derived from FinancialInputs (no explicit market block).",
    )


def _weighted_band(pairs: list[_ValueWeightKey]) -> ScenarioMetricBand:
    """Deterministic prior-weighted band for one metric (design note §4).

    Weighted percentile = no-interpolation inverse-CDF: sort by (value asc, hypothesis key),
    accumulate prior mass, and take the value at the smallest index whose cumulative mass
    reaches ``p * total`` (p=0.25 downside, p=0.50 median). ``mean`` is the prior-weighted
    mean (the EXPECTED value); ``min``/``max`` are absolute over the accepted set.
    """
    total = sum(w for _, w, _ in pairs)
    ordered = sorted(pairs, key=lambda t: (t[0], t[2]))

    def _quantile(p: float) -> float:
        threshold = p * total
        cumulative = 0.0
        for value, weight, _ in ordered:
            cumulative += weight
            if cumulative >= threshold - 1e-12:
                return value
        return ordered[-1][0]

    values = [v for v, _, _ in ordered]
    mean = sum(v * w for v, w, _ in ordered) / total if total > 0 else values[0]

    return ScenarioMetricBand(
        p25=_quantile(0.25),
        p50=_quantile(0.50),
        mean=mean,
        min=min(values),
        max=max(values),
    )


def _band_for(outcomes: tuple[ScenarioOutcome, ...], getter: Callable[[ScenarioOutcome], float]) -> ScenarioMetricBand:
    pairs: list[_ValueWeightKey] = [(getter(o), o.hypothesis.prior, _hyp_key(o.hypothesis)) for o in outcomes]
    return _weighted_band(pairs)


def run_scenarios(inputs: FinancialInputs, snapshot: MarketSnapshot, *, seed: int = 42) -> ScenarioAnalysis:
    """Run the full scenario pipeline and aggregate prior-weighted bands.

    Steps (design note §4/§8):
      (a) one baseline ``run_financial_model(inputs)`` -> ``base_cap`` from ``PurchaseMetrics.cap_rate``
          (reuses the engine's own cap math; no core edit, no re-derivation of NOI);
      (b) ``generate_hypotheses(snapshot, seed=seed)``;
      (c) ``reject_unrealistic(...)`` (may return an empty set);
      (d) per accepted hypothesis: perturb a deep copy, re-run the engine, extract headline metrics;
      (e) aggregate prior-weighted bands per metric.

    Determinism: same ``seed`` + same inputs => identical serialized ``ScenarioAnalysis``.
    Accepted priors sum to 1.0 (±1e-12).
    """
    baseline = run_financial_model(inputs)
    base_cap = baseline.purchase.cap_rate
    # Invariant across scenarios (the adapter never perturbs the financing term); carried so the
    # report can render the interest-only caveat when > 0 (design note §3a / §7a #6).
    io_years = inputs.financing.io_years

    generated = generate_hypotheses(snapshot, seed=seed)
    n_generated = len(generated.items)

    accepted = reject_unrealistic(generated, snapshot)

    if not accepted.items:
        return ScenarioAnalysis(
            snapshot=snapshot,
            seed=seed,
            io_years=io_years,
            n_generated=n_generated,
            n_accepted=0,
            prior_sum=0.0,
            outcomes=(),
            dscr=None,
            coc=None,
            cash_flow_y1=None,
            irr_10yr=None,
            equity_multiple_10yr=None,
            notes=accepted.notes or "No admissible scenarios under the current guardrails.",
        )

    outcomes: list[ScenarioOutcome] = []
    for hypothesis in accepted.items:
        perturbed = perturb_inputs(inputs, hypothesis, base_cap=base_cap)
        forecast = run_financial_model(perturbed)
        outcomes.append(
            ScenarioOutcome(
                hypothesis=hypothesis,
                rent_growth_applied=perturbed.income.rent_growth,
                expense_growth_applied=perturbed.opex.expense_growth,
                interest_rate_applied=perturbed.financing.interest_rate,
                occupancy_applied=perturbed.income.occupancy,
                cap_rate_purchase_applied=perturbed.market.cap_rate_purchase,
                dscr_y1=forecast.purchase.dscr,
                coc_y1=forecast.purchase.coc,
                cash_flow_y1=forecast.years[0].cash_flow,
                irr_10yr=forecast.irr_10yr,
                equity_multiple_10yr=forecast.equity_multiple_10yr,
            )
        )

    outcomes_tuple: tuple[ScenarioOutcome, ...] = tuple(outcomes)
    prior_sum = sum(o.hypothesis.prior for o in outcomes_tuple)

    return ScenarioAnalysis(
        snapshot=snapshot,
        seed=seed,
        io_years=io_years,
        n_generated=n_generated,
        n_accepted=len(outcomes_tuple),
        prior_sum=prior_sum,
        outcomes=outcomes_tuple,
        dscr=_band_for(outcomes_tuple, lambda o: o.dscr_y1),
        coc=_band_for(outcomes_tuple, lambda o: o.coc_y1),
        cash_flow_y1=_band_for(outcomes_tuple, lambda o: o.cash_flow_y1),
        irr_10yr=_band_for(outcomes_tuple, lambda o: o.irr_10yr),
        equity_multiple_10yr=_band_for(outcomes_tuple, lambda o: o.equity_multiple_10yr),
        notes=accepted.notes,
    )
