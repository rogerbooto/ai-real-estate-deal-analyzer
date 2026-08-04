# market

## Purpose / Responsibilities

* Deterministic **market context & scenario utilities** used for forecasting and guardrails:

  * Build a `MarketSnapshot` from user/JSON inputs.
  * Generate a small **Cartesian grid** of “what-if” `MarketHypothesis` deltas around a snapshot.
  * Apply **rejector** rules to prune unrealistic combos and renormalize priors.
  * Produce **regional income tables** for sanity-checks and scenario seeding. **Not currently
    wired into any production caller**: `build_regional_income` (`regional_income.py`) is a
    working, directly-importable function, but as of 2026-08-03 the only thing that calls it is
    `tests/unit/test_market_regional_income.py` — no CLI, orchestrator, or agent reaches it.
    Whether/how to wire it as a real public entry point is an open Mission 2 Wave 3 decision
    (see `docs/plans/MISSION_2_wiring_gaps.md`, finding T4, OPD-3 "wire-first"); this README
    will be updated once that lands.
  * **NEW — Wave 2:** Perturb financial inputs per hypothesis and re-run the frozen finance engine to produce prior-weighted scenario outcomes (`adapter.py`, `scenario_runner.py`).
* **Current status**: fully implemented and tested; wired into the pipeline as an **opt-in** “Market Scenarios” overlay behind `--scenarios` / `AIREAL_SCENARIOS` / `run.scenarios`. When OFF (default), the hot path adds zero scenario imports and produces byte-identical output. Scenarios are deterministic what-if calculations, not predictions.

## Public APIs / Contracts

* **Imports:**

  ```python
  from src.market.snapshot import build_snapshot
  from src.market.hypotheses import generate_hypotheses
  from src.market.rejector import reject_unrealistic
  from src.market.regional_income import build_regional_income
  from src.market.adapter import perturb_inputs
  from src.market.scenario_runner import resolve_snapshot, run_scenarios
  ```
* **Key Types** (see ../schemas/README.md):

  * `MarketSnapshot` (fractional fields, frozen) — baseline context.
  * `MarketHypothesis` (absolute **deltas**; priors; rationale; STR flag).
  * `HypothesisSet` (collection with notes/seed; priors sum to 1 after rejector).
  * `RegionalIncomeTable` (median/p25/p75, turnover, optional STR uplift).
* **Functions / Classes:**

  * `build_snapshot(m: Mapping[str, Any]) -> MarketSnapshot`
    Validates required keys; enforces **fractions** for rates (e.g., 0.05 for 5%).
  * `generate_hypotheses(snapshot, *, seed=42, bands=None, grid_steps=None) -> HypothesisSet`
    Deterministic grid over ordered axes: `("rent_delta","expense_growth_delta","interest_rate_delta","cap_rate_delta","vacancy_delta")`. Deltas are **absolute percentage points** (e.g., `0.02 == +200 bps`). Computes priors and notes.
  * `reject_unrealistic(hs: HypothesisSet, snap: MarketSnapshot) -> HypothesisSet`
    Applies hard bounds and soft penalties, flips incoherent STR flags, **renormalizes priors**, and returns a **deterministically ordered** set.
  * `build_regional_income(region: str, bedrooms: int, comps: list[float]) -> RegionalIncomeTable`
    Aggregates comp rents; returns frozen table with convenience `summary()`. **Reachable only
    from tests today** (0 production callers) — see the reachability note above and Mission 2's
    T4/OPD-3.
  * `perturb_inputs(fi: FinancialInputs, hypothesis: MarketHypothesis, *, base_cap: float) -> FinancialInputs`
    (Wave 2) Returns a perturbed **deep copy** of `FinancialInputs` with deltas applied (income, opex, financing, market fields) per the hypothesis. Original untouched. `base_cap` is the engine-derived purchase cap from untouched inputs.
  * `resolve_snapshot(inputs: FinancialInputs, *, market_block: Mapping | None) -> MarketSnapshot`
    (Wave 2) Resolves the `MarketSnapshot` for scenario generation. Source priority: (1) explicit `market` block if provided (parsed by `build_snapshot`); (2) fallback derivation from `FinancialInputs`; (3) loud-fail if no cap is derivable. Never silently invents a cap (invariant §5).
  * `run_scenarios(inputs: FinancialInputs, snapshot: MarketSnapshot, *, seed: int = 42) -> ScenarioAnalysis`
    (Wave 2) Runs the full scenario pipeline: baseline engine pass (for `base_cap`) → generate hypotheses → reject unrealistic → per-scenario engine re-run → prior-weighted aggregation. Deterministic; returns `ScenarioAnalysis` with prior-weighted bands (p25/p50/mean/min/max) per metric.

## Usage Examples

### 1) Build a snapshot

```python
from src.market.snapshot import build_snapshot

snap = build_snapshot({
    "market": {
        "region": "Metro A",
        "vacancy_rate": 0.06,
        "cap_rate": 0.055,
        "rent_growth": 0.03,
        "expense_growth": 0.02,
        "interest_rate": 0.045,
    }
})
print(snap.summary())  # "[MarketSnapshot] Metro A | Vac..."
```

### 2) Generate hypotheses and apply rejector

```python
from src.market.hypotheses import generate_hypotheses
from src.market.rejector import reject_unrealistic

hs = generate_hypotheses(snap, seed=42)
hs_clean = reject_unrealistic(hs, snap)

# Priors renormalized; ordering is deterministic (lexicographic over deltas, then STR)
assert abs(sum(h.prior for h in hs_clean.items) - 1.0) < 1e-12
print(hs_clean.summary(top_n=3))
```

### 3) Build regional income table

```python
from src.market.regional_income import build_regional_income

tbl = build_regional_income("Metro A", bedrooms=2, comps=[1500, 1550, 1600, 1700, 1800])
print(tbl.summary())  # includes P25/Median/P75 and turnover; STR multiplier if present
```

> This example uses a real, working import — the function runs fine standalone. What it does
> **not** have, today, is a caller inside `src/` (main pipeline, any CLI, any agent); the only
> current caller is `tests/unit/test_market_regional_income.py`. See the reachability note in
> "Purpose / Responsibilities" above.

## Design Notes / Invariants

* **Fractions everywhere** for baseline snapshot fields (e.g., `0.05` = 5%). (Models are frozen; extra keys ignored.)
* **Deltas are absolute percentage points** for hypotheses (e.g., `rent_delta=0.02` means **+200 bps**). Fixed axis order:

  ```
  ("rent_delta","expense_growth_delta","interest_rate_delta","cap_rate_delta","vacancy_delta")
  ```
* **Generate (grid) → Reject (rules) → Renormalize (priors)**:

  * **Hard bounds** (must hold after applying deltas):

    * `interest_rate_delta - cap_rate_delta ≤ 0.02`
    * `cap_total ∈ [0.03, 0.12]`
    * `vacancy_total ∈ [0.00, 0.20]`
  * **Correlation guard**: if `rent_delta ≥ +0.03` then `vacancy_delta ≤ +0.015`.
  * **STR coherence**: if flagged `True` but violates coherence (e.g., rate shock), **flip to False** instead of rejecting.
  * **Soft penalty**: increases prior penalty when `expense_growth_delta - rent_delta > 0`.
* **Determinism**:

  * 3-point grids only (`min/base/max`) in current milestone; stable ordering; `seed` reserved for future tie-breaking.
* **Units**:

  * Money amounts are consistent currency; growth/cap/rates are **fractions**; deltas are **absolute pts**.

## Dependencies / Optional Providers

* Depends on `src.schemas.models` types (`MarketSnapshot`, `MarketHypothesis`, `HypothesisSet`, `RegionalIncomeTable`, `ScenarioAnalysis`, `ScenarioOutcome`, `ScenarioMetricBand`).
* Depends on `src.core.finance.engine.run_financial_model` for scenario re-runs (one-way composition; no core edit).
* No external services; **pure deterministic** utilities.
* **Wired** into the main pipeline: called from `main.py` when `--scenarios` is ON; results passed to `write_report` for the "Market Scenarios" overlay section. With scenarios OFF, zero market imports occur on the hot path. This wiring covers `snapshot.py` → `hypotheses.py` → `rejector.py` → `adapter.py` → `scenario_runner.py`; it does **not** include `regional_income.py`, which has no caller in that chain (see reachability note above).

## Test Strategy

* Unit tests:

  * `tests/unit/test_market_snapshot.py` — snapshot building/validation.
  * `tests/unit/test_market_hypotheses.py` — deltas, symbols (▲/▼/➝), priors, immutability.
  * `tests/unit/test_rejector.py` — hard bounds, rent-vs-vacancy rule, STR coherence flip, renormalization, deterministic order.
  * `tests/unit/test_market_regional_income.py` — table shape & summaries.
* Run:

  ```
  pytest -q --no-cov tests/unit/test_market_*.py tests/unit/test_rejector.py
  ```

  `--no-cov` disables coverage for this subset run only; the project's ≥80% coverage gate
  (`pytest.ini`, `--cov-fail-under=80`) is enforced against the **full** `pytest` suite, not any
  one subset command.

## Cross-links

* Back to [Main README](../README.md)
* Types anchor: [`../schemas/README.md`](../schemas/README.md)
* Finance context (how scenarios affect underwriting): [`../core/README.md`](../core/README.md)
* Orchestrator wiring status & proposal: [`../orchestrators/README.md`](../orchestrators/README.md)
* Agents that could consume scenarios (future): [`../agents/README.md`](../agents/README.md)
* Reporting patterns for scenario outputs: [`../core/reports/README.md`](../core/reports/README.md)

## Change Log Notes (scoped)

* Milestone B: Introduced 3-point grid generator, rejector hard/soft rules, STR coherence flip, deterministic ordering.
* Wave 1 (Design, 2026-07-24): Designed scenario semantics, delta→inputs mapping, weighted-percentile bands, honesty framing, opt-in wiring (design note § 0–10).
* Wave 2 (Implementation, 2026-07-24): Implemented `adapter.py` (perturbation), `scenario_runner.py` (composition + aggregation), `_render_market_scenarios` in reports, wired through `main.py`, appended to `ScenarioAnalysis` models in schemas. Opt-in behind `--scenarios` / `AIREAL_SCENARIOS` / `run.scenarios`; default-OFF byte-identical guarantee verified.

---

_Last reconciled: 2026-08-04 against mission/2-wiring-gaps @ d18ee1a (Gate 2 VETO remediation: added the full-suite coverage-gate note; no other content change — the guardian confirmed this file's OPD-3 framing accurate at Gate 2. Earlier note: 2026-08-03 @ 74c985c, clarified `build_regional_income` is reachable only from tests today; Wave 3/OPD-3 will decide whether to wire it)._
