"""Portfolio-scale benchmark for the recourse re-run loop (Mission 4, task PV.3).

THE WORKLOAD IS THE CONTRACT, AND THIS FILE RUNS THE WORKLOAD IT DESCRIBES.

Two earlier versions of this benchmark each measured something other than what they claimed, in
the same direction -- cheaper than production -- so the history is kept here as a warning:

  1. The first claimed "432 engine re-runs -- one full ``compute_recourse`` pass" while calling
     the engine 432 times on the SAME ``FinancialInputs`` object. A probe builds a perturbed copy
     and re-runs; the copy is part of the cost.
  2. The second (fixed #1) built a real perturbed copy per probe, but priced ALL 432 probes with
     the ``purchase_price`` lever shape -- the CHEAP shape, which shares the rent roll by
     reference and reuses its precomputed aggregate. The ``rent_per_unit_month`` shape, which
     rebuilds every ``UnitIncome`` and is ~24x more expensive at 5,000 units, was excluded from
     the table and reported separately in DIFFERENT UNITS (per-probe, next to a per-432-probe
     table). It then printed ``<= 120 ms: PASS`` against a budget the real loop misses by ~60%.

So this version does not model the production loop at all. **It calls it.** The headline number
below is a real ``compute_recourse`` on a real deal, with the real lever mix, and the probe count
is COUNTED rather than assumed.

What the numbers mean:

  * ``PRIMARY`` -- the honest end-to-end figure and the only one the budget judges. The 5,000-unit
    / 100-year row is the institutional ceiling Roger set as the standard, priced so that exactly
    ``GENUINELY_CLOSE_MAX_FAILS`` guardrails fail: the worst case the production gate actually
    admits (at 4+ fails ``is_genuinely_close`` returns False and ``compute_recourse`` is never
    called). The committed sample deals are shown alongside it -- that is what a REAL deal costs.
  * ``ATTRIBUTION`` -- per-probe cost by lever shape, for pinning a regression on the engine vs.
    the perturbation. Both shapes are in the same table, in the same units (microseconds per
    probe). Never quote these as the cost of an analysis; multiply by a counted probe total, or
    just read PRIMARY.

On 432: it is the discovery spec's §2.4 analytic CEILING (``27 non-excluded pairs x (1 + 15)``),
never a measurement. Real analyses fire far fewer -- 159 probes on ``36_kelly_moncton``, 135 on
``82_champlain_dieppe``, 150 on the 5,000-unit ceiling workload. It is retained only to project
attribution costs onto that worst case, and is labelled as a ceiling everywhere it appears.

Run:  python -m tests.perf.bench_finance_engine
A script, not a pytest test: not collected by the default suite, so it never adds CI wall time.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import src.market.recourse as recourse_mod
from src.core.finance.engine import PrecomputedIncome, forecast_metrics, precompute_income, run_financial_model
from src.market.recourse import (
    GENUINELY_CLOSE_MAX_FAILS,
    _failing_guardrails,
    _live_guardrails,
    _perturb,
    _rerun,
    compute_recourse,
    guardrail_checks_from_metrics,
    metrics_of,
)
from src.schemas.models import FinancialInputs

#: Discovery spec §2.4 worst-case CEILING on probes for one report -- an analytic bound, NOT a
#: measurement. Used only to project per-probe attribution costs onto the worst case.
CEILING_PROBES = 432

#: Probe repetitions for the attribution table. The rent CONFIRM shape (materialised roll +
#: full engine) gets fewer because it is the one remaining O(units) shape; everything is
#: normalised to microseconds/probe, so the counts need not match.
PRICE_PROBE_REPS = 432
RENT_PROBE_REPS = 24

#: (label, units, horizon_years) -- the primary point first.
WORKLOADS: tuple[tuple[str, int, int], ...] = (
    ("5,000u / 100y", 5_000, 100),
    ("5,000u /  50y", 5_000, 50),
    ("1,000u /  30y", 1_000, 30),
)

#: Budget for the PRIMARY 5,000u/100y row, in milliseconds.
#:
#: HISTORY: 120.0 (Mission 4 validation, set against a benchmark that never ran the rent lever)
#: -> 250.0 (2026-08-30, honest re-baseline: 181-197 ms best measured, ~85% of it the rent
#: lever's O(units) `_perturb` copy) -> KEPT at 250.0 after the Mission 5 acceleration pass
#: (2026-08-31), which removed that copy from the search path entirely.
#:
#: The acceleration measured on this row, same machine, same harness: 404.7 ms best with the
#: Half B combination search included (98 rent probes x ~3.4 ms of roll rebuilding) -> 73.4 ms
#: after the `engine.ShiftedIncome` aggregate-shift seam (rent search probes became O(1)) ->
#: 63-66 ms after the scoped GC tuning (`recourse._search_gc_tuned`). The budget deliberately
#: keeps ~3.5-4x headroom over that best: this constant now GATES CI (imported and enforced
#: best-of-N by `tests/perf/test_perf_gates.py`), and CI hardware is slower and noisier than the
#: dev box that produced the 63 ms figure. Roger's 30 ms TARGET remains a target, not a gate:
#: the measured process spread is ~+/-12%, so a 30 ms assertion would flake rather than inform.
#: What this budget really guards is the seam itself -- losing the O(1) rent path puts this row
#: straight back above 400 ms, ~1.6x over budget, loudly.
BUDGET_MS = 250.0
PRIOR_BUDGET_MS = 120.0

#: Committed sample deals shown next to the synthetic ceiling, so "what a real deal costs" is on
#: the same screen as the institutional worst case and the two can never be confused again.
SAMPLE_DEALS: tuple[tuple[str, str], ...] = (
    ("36_kelly_moncton", "data/sample_listings/36_kelly_moncton/inputs.json"),
    ("82_champlain_dieppe", "data/sample_listings/82_champlain_dieppe/inputs.json"),
)
SAMPLE_HORIZON = 10


def build_inputs(units: int, *, price_per_unit: float | None = None) -> FinancialInputs:
    """A realistic, deterministic rent roll -- rents vary so a 'sum unit 0 n times' bug shows up."""
    rent_roll: list[dict[str, float]] = [
        {"rent_month": 1200.0 + 10.0 * (i % 3) + 0.37 * (i % 7), "other_income_month": 50.0 if i % 2 == 0 else 0.0} for i in range(units)
    ]
    price = 500_000.0 + 95_000.0 * units if price_per_unit is None else price_per_unit * units
    payload: dict[str, Any] = {
        "financing": {
            "purchase_price": price,
            "closing_costs": 10_000.0,
            "down_payment_rate": 0.25,
            "interest_rate": 0.055,
            "amort_years": 30,
            "io_years": 0,
            "mortgage_insurance_rate": 0.04,
        },
        "opex": {
            "insurance": 2400.0,
            "taxes": 6000.0,
            "utilities": 3600.0,
            "water_sewer": 1800.0,
            "property_management": 4800.0,
            "repairs_maintenance": 2400.0,
            "trash": 1200.0,
            "landscaping": 800.0,
            "snow_removal": 600.0,
            "hoa_fees": 250.0,
            "reserves": 1500.0,
            "other": 500.0,
            "expense_growth": 0.02,
        },
        "income": {"units": rent_roll, "occupancy": 0.95, "bad_debt_factor": 0.97, "rent_growth": 0.03},
        "refi": {"do_refi": False, "year_to_refi": 5, "refi_ltv": 0.75},
        "market": {"cap_rate_spread_target": 0.02, "cap_rate_drift": 0.001},
        "capex_reserve_upfront": 0.0,
    }
    return FinancialInputs.model_validate(payload)


def count_failing(fi: FinancialInputs, horizon: int) -> tuple[str, ...]:
    """Which live guardrails this deal currently fails -- the same call `compute_recourse` makes."""
    base = run_financial_model(fi, horizon_years=horizon)
    checks = guardrail_checks_from_metrics(metrics_of(base), fi.market)
    return tuple(_failing_guardrails(checks, _live_guardrails(fi.market)))


def build_gate_limit_inputs(units: int, horizon: int) -> tuple[FinancialInputs, tuple[str, ...]]:
    """A deal at the production gate's LIMIT: exactly `GENUINELY_CLOSE_MAX_FAILS` guardrails failing.

    Searched at run time rather than pinned to a hard-coded price, so that an engine change which
    shifts where the guardrails break moves the workload with it instead of silently benchmarking
    a deal that no longer stresses the loop. The default `build_inputs` deal passes everything and
    fires ZERO probes -- benchmarking it would report a fast, meaningless number.
    """
    for price_per_unit in range(150_000, 400_001, 5_000):
        fi = build_inputs(units, price_per_unit=float(price_per_unit))
        failing = count_failing(fi, horizon)
        if len(failing) == GENUINELY_CLOSE_MAX_FAILS:
            return fi, failing
    raise AssertionError(
        f"no price in the scanned range produces exactly {GENUINELY_CLOSE_MAX_FAILS} failing guardrails at "
        f"{units} units / {horizon}y. The guardrail thresholds or the engine moved; widen the scan or "
        "rebuild the workload, but do NOT benchmark a deal that fires no probes."
    )


def count_probes(fi: FinancialInputs, horizon: int) -> tuple[int, dict[str, int]]:
    """Count real engine probes in one `compute_recourse` pass, by lever.

    Deliberately run UNTIMED and separately from the timed passes: the counting wrapper is cheap
    but not free, and a benchmark that measures its own instrumentation is how this file got into
    trouble twice already.

    TWO WRAPPERS, BECAUSE THE RENT LEVER NO LONGER PERTURBS (Mission 5 acceleration): rent
    SEARCH probes ride `_rerun`'s O(1) `rent_shift` aggregate path and never call `_perturb`,
    so counting `_perturb` alone would silently undercount exactly the probes the seam
    optimised -- the same "cheaper than production" failure mode this docstring warns about.
    `_perturb` still counts every non-rent probe and the rent lever's materialised confirming
    re-runs; `_rerun` with `rent_shift != 0.0` counts the shifted rent search probes.
    """
    counts: dict[str, int] = {}
    original = _perturb
    original_rerun = recourse_mod._rerun

    def counting_perturb(fi_: FinancialInputs, lever: Any, t: float, *, total_opex_y1: float) -> Any:
        counts[lever] = counts.get(lever, 0) + 1
        return original(fi_, lever, t, total_opex_y1=total_opex_y1)

    def counting_rerun(perturbed: FinancialInputs, **kwargs: Any) -> Any:
        if kwargs.get("rent_shift", 0.0) != 0.0:
            counts["rent_per_unit_month"] = counts.get("rent_per_unit_month", 0) + 1
        return original_rerun(perturbed, **kwargs)

    recourse_mod._perturb = counting_perturb  # type: ignore[assignment]
    recourse_mod._rerun = counting_rerun  # type: ignore[assignment]
    try:
        compute_recourse(fi, horizon_years=horizon)
    finally:
        recourse_mod._perturb = original  # type: ignore[assignment]
        recourse_mod._rerun = original_rerun  # type: ignore[assignment]
    return sum(counts.values()), counts


def time_analysis(fi: FinancialInputs, horizon: int, *, repeats: int) -> tuple[float, float]:
    """Return (best, median) wall milliseconds for ONE full `compute_recourse` call."""
    compute_recourse(fi, horizon_years=horizon)  # warm the code paths, not the result
    samples: list[float] = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        compute_recourse(fi, horizon_years=horizon)
        samples.append((time.perf_counter() - t0) * 1000.0)
    return min(samples), statistics.median(samples)


def assert_precompute_is_actually_reused(fi: FinancialInputs) -> None:
    """Fail loudly if a price-lever probe stops sharing the income object by reference.

    THIS GUARD EXISTS BECAUSE ITS ABSENCE IS EXPENSIVE AND SILENT. `_rerun` reuses the rent-roll
    aggregate only when `perturbed.income is baseline_income`; if a future change to `_perturb`
    (or a hand-rolled stand-in in a harness) breaks that identity, everything still WORKS and every
    number is still correct -- the engine just quietly recomputes the O(units) sum on every probe.
    Cheap to check, so it is checked before anything is timed.
    """
    opex_y1 = run_financial_model(fi, horizon_years=1).years[0].total_opex
    probe = _perturb(fi, "purchase_price", 100.0, total_opex_y1=opex_y1)
    if probe.income is not fi.income:
        raise AssertionError(
            "price-lever perturbation no longer shares the IncomeModel by reference: the rent-roll "
            "precompute will NOT be reused and every number below is ~2.6x pessimistic. Fix "
            "_perturb (or this benchmark) before reading the results."
        )


def _make_probe(fi: FinancialInputs, horizon: int, mode: str, pre: PrecomputedIncome) -> Callable[[int], object]:
    """Build the per-probe callable for `mode`. Every mode but `engine-only` builds a real
    perturbed copy first, varying the lever value so nothing can be accidentally cached."""
    opex_y1 = run_financial_model(fi, horizon_years=1).years[0].total_opex
    income = fi.income

    if mode == "engine-only":
        return lambda i: forecast_metrics(fi, horizon_years=horizon, precomputed_income=pre)
    if mode == "price-full":
        return lambda i: run_financial_model(_perturb(fi, "purchase_price", 100.0 * (i + 1), total_opex_y1=opex_y1), horizon_years=horizon)
    if mode == "price-reuse":
        return lambda i: run_financial_model(
            _perturb(fi, "purchase_price", 100.0 * (i + 1), total_opex_y1=opex_y1),
            horizon_years=horizon,
            precomputed_income=pre,
        )
    if mode == "price-search":
        return lambda i: _rerun(
            _perturb(fi, "purchase_price", 100.0 * (i + 1), total_opex_y1=opex_y1),
            horizon_years=horizon,
            baseline_income=income,
            precomputed=pre,
        )
    if mode == "rent-search":
        # THE PRODUCTION RENT SEARCH SHAPE (Mission 5 acceleration): the O(1) aggregate shift
        # (`engine.ShiftedIncome` via `_rerun(rent_shift=...)`). No perturbed copy exists.
        return lambda i: _rerun(
            fi,
            horizon_years=horizon,
            baseline_income=income,
            precomputed=pre,
            rent_shift=5.0 * (i + 1),
        )
    if mode == "rent-confirm":
        # The rent lever's CONFIRMING shape: materialise the roll (every UnitIncome rebuilt) and
        # run the FULL engine, exactly `_search_one`'s provenance rule. This is where the old
        # O(units) copy cost now lives -- a handful of confirms per analysis, not ~100 probes.
        return lambda i: run_financial_model(
            _perturb(fi, "rent_per_unit_month", 5.0 * (i + 1), total_opex_y1=opex_y1),
            horizon_years=horizon,
        )
    raise ValueError(f"unknown mode {mode!r}")


def time_probes(fi: FinancialInputs, horizon: int, *, mode: str, probes: int, repeats: int) -> tuple[float, float]:
    """Return (best, median) MICROSECONDS PER PROBE.

    BOTH are reported, deliberately. `best` is the least-contaminated estimate of the real cost;
    a `median` far above it means the machine was busy and the run should be repeated rather than
    quoted. This benchmark has been observed inflating ~1.4-1.8x when run immediately after the
    test suite on a loaded box, which is more than any single optimisation below is worth.
    """
    pre = precompute_income(fi.income)
    probe = _make_probe(fi, horizon, mode, pre)
    probe(0)  # warm the code paths, not the result
    samples: list[float] = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        for i in range(probes):
            probe(i)
        samples.append((time.perf_counter() - t0) * 1_000_000.0 / probes)
    return min(samples), statistics.median(samples)


def load_sample_deal(path: str) -> FinancialInputs | None:
    """Load a committed sample deal, or None if it is not on disk (bench must still run)."""
    p = Path(path)
    if not p.is_file():
        return None
    raw = json.loads(p.read_text())
    return FinancialInputs.model_validate(raw["inputs"] if "inputs" in raw else raw)


def run_primary(repeats: int) -> bool:
    """The production loop, called for real. Returns True if the budgeted row is within budget."""
    print("PRIMARY -- real compute_recourse(), the production loop. THIS is the cost of an analysis.")
    print(f"{'deal':>24}  {'best/median':>19}  {'probes':>7}  {'by lever':<44}  verdict")
    print("-" * 118)

    within_budget = True
    fi, failing = build_gate_limit_inputs(5_000, 100)
    assert_precompute_is_actually_reused(fi)
    total, by_lever = count_probes(fi, 100)
    best, median = time_analysis(fi, 100, repeats=repeats)
    within_budget = best <= BUDGET_MS
    verdict = f"<= {BUDGET_MS:.0f} ms: " + ("PASS" if within_budget else f"FAIL (+{best - BUDGET_MS:.1f} ms)")
    breakdown = ", ".join(f"{k.split('_')[0]}:{v}" for k, v in sorted(by_lever.items()))
    print(f"{'5,000u / 100y (ceiling)':>24}  {best:8.1f}/{median:8.1f}ms  {total:7d}  {breakdown:<44}  {verdict}")
    print(
        f"{'':>24}  fails {len(failing)} guardrails {failing} -- the gate's limit (GENUINELY_CLOSE_MAX_FAILS={GENUINELY_CLOSE_MAX_FAILS})"
    )

    for name, path in SAMPLE_DEALS:
        deal = load_sample_deal(path)
        if deal is None:
            print(f"{name:>24}  (not on disk -- skipped)")
            continue
        total, by_lever = count_probes(deal, SAMPLE_HORIZON)
        best, median = time_analysis(deal, SAMPLE_HORIZON, repeats=repeats)
        breakdown = ", ".join(f"{k.split('_')[0]}:{v}" for k, v in sorted(by_lever.items()))
        print(
            f"{name + ' (' + str(SAMPLE_HORIZON) + 'y)':>24}  {best:8.1f}/{median:8.1f}ms  {total:7d}  {breakdown:<44}  (real deal, not budgeted)"
        )
    return within_budget


def run_attribution(repeats: int) -> bool:
    """Per-probe cost by lever shape. Returns True if the machine looked quiet."""
    modes = ("engine-only", "price-full", "price-reuse", "price-search", "rent-search", "rent-confirm")
    titles = {
        "engine-only": "engine-only*",
        "price-full": "price full",
        "price-reuse": "price +reuse",
        "price-search": "price search",
        "rent-search": "rent search",
        "rent-confirm": "rent confirm",
    }
    print("\n\nATTRIBUTION -- MICROSECONDS PER PROBE, both lever shapes, same units.")
    header = f"{'workload':>16}  " + "  ".join(f"{titles[m]:>19}" for m in modes)
    print(header)
    print("-" * len(header))

    noisy = False
    for label, units, horizon in WORKLOADS:
        fi = build_inputs(units)
        assert_precompute_is_actually_reused(fi)
        cells = []
        for mode in modes:
            probes = RENT_PROBE_REPS if mode == "rent-confirm" else PRICE_PROBE_REPS
            best, median = time_probes(fi, horizon, mode=mode, probes=probes, repeats=repeats)
            noisy = noisy or median > best * 1.15
            cells.append(f"{best:8.1f}/{median:6.1f}us")
        print(f"{label:>16}  " + "  ".join(f"{c:>19}" for c in cells))
    return noisy


def main() -> int:
    ap = argparse.ArgumentParser(description="Recourse loop benchmark. See module docstring.")
    ap.add_argument("--repeats", type=int, default=7, help="timing repeats; BEST and MEDIAN are both reported")
    args = ap.parse_args()

    within_budget = run_primary(args.repeats)
    noisy = run_attribution(args.repeats)

    print(f"\n(best/median of {args.repeats}; Python {sys.version.split()[0]})")
    print("Every figure above runs the REAL production probe shape: non-rent probes build a real")
    print("perturbed copy (src.market.recourse._perturb); rent SEARCH probes ride the O(1) aggregate")
    print("shift (engine.ShiftedIncome) exactly as compute_recourse does; 'rent confirm' is the")
    print("materialised-roll full-engine confirming shape. PRIMARY additionally calls the REAL")
    print("src.market.recourse.compute_recourse, and COUNTS its probes (shift probes included).")
    print("* engine-only = same object re-run, no perturbation. A LOWER BOUND for attribution only --")
    print("  it is not the cost of an analysis and must not be quoted as one.")
    print("432 probes is the discovery-spec §2.4 analytic CEILING, never a measurement: real analyses")
    print(f"  fire the counted 'probes' totals above. Projecting a shape onto the ceiling = us/probe x {CEILING_PROBES}.")
    print(f"BUDGET_MS re-baselined {PRIOR_BUDGET_MS:.0f} -> {BUDGET_MS:.0f} ms (2026-08-30); see the constant's comment for why.")
    if noisy:
        print("\nWARNING: median > 1.15x best on at least one cell -- the machine was busy. Re-run before quoting.")
    if not within_budget:
        print("\nBUDGET EXCEEDED on the 5,000u/100y row.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
