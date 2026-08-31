# market

## Purpose / Responsibilities

* Deterministic **market context & scenario utilities** used for forecasting and guardrails:

  * Build a `MarketSnapshot` from user/JSON inputs.
  * Generate a small **Cartesian grid** of “what-if” `MarketHypothesis` deltas around a snapshot.
  * Apply **rejector** rules to prune unrealistic combos and renormalize priors.
  * Produce **regional income tables** for sanity-checks and scenario seeding. As of 2026-08-05
    (Mission 2 task 3.1b, OPD-3 “wire-first”) `build_regional_income` (`regional_income.py`) is
    reachable in production via `deal-advisor`'s `--regional-income <path>` flag: a JSON file
    `{“region”: ..., “bedrooms”: ..., “comps”: [rent, ...]}` is loaded, built into a
    `RegionalIncomeTable`, and its real comps-derived fields (median/p25/p75 rent) are embedded in
    the advisor's JSON/`--markdown` output as a portfolio-level sanity-check (it is not per-deal —
    comps describe a market, not one listing). It is a deliberately separate entry point from the
    scenario overlay below: it needs only comps, not a `FinancialInputs`/engine run. **Gate 3
    correction (2026-08-05):** `RegionalIncomeTable.str_multiplier`/`turnover_cost` were found
    fabricated (a hardcoded 1.5x STR uplift gated by a policy hook that always returned `True`, and
    an uncited “median rent × 0.5” rule of thumb) and neither reaches `deal-advisor`'s output;
    `build_regional_income` no longer computes an STR multiplier at all (`str_multiplier` is always
    `None`) and `RegionalIncomeTable.summary()` no longer renders either field or the
    `[RegionalIncomeTable]` class-name prefix it used to print. `turnover_cost` remains a required
    schema field computed internally for validity; `advisor_cli.py`'s `_regional_income_payload`
    additionally keeps it out of `--out`'s JSON specifically (the field-removal question is left to
    a follow-up schema decision — see `CHANGELOG.md` “Removed”).
  * **Perturb financial inputs per hypothesis and re-run the frozen finance engine** to produce prior-weighted scenario outcomes (`adapter.py`, `scenario_runner.py`).
  * **Actionable recourse for near-miss deals (Mission 4):** The gate is verdict-independent — `is_genuinely_close` runs a fail-count test on the baseline forecast alone: `0 < num_fails <= GENUINELY_CLOSE_MAX_FAILS` (currently 3), over the same seven live `chief_strategist.py` guardrails the verdict itself is computed from. It never inspects the verdict string. In practice this means: `BUY` (0 fails, by the verdict rule's own definition) never opens the gate; `CONDITIONAL` deals (1–2 fails, without the cap-floor+DSCR DECLINE shortcut) always do; and `DECLINE` deals open it too whenever they still land in the 1–3 range (either via the cap-floor+DSCR shortcut at low fail counts, or via exactly 3 fails). (The shipped fixture `data/sample_listings/82_champlain_dieppe/` is a **DECLINE** with the gate open — 3 of 6 live guardrails failing — chosen deliberately so this section has real, non-CONDITIONAL data to render against.) When it opens, compute what single investor-movable change (rent, price, interest rate, annual opex) would close each failing guardrail — by re-running the engine, never by inverting formulas, because the levers are not independent. (`recourse.py` with `is_genuinely_close()` and `compute_recourse()`).
* **Current status**: fully implemented and tested; wired into the pipeline as an **opt-in** “Market Scenarios” overlay behind `--scenarios` / `AIREAL_SCENARIOS` / `run.scenarios`. When OFF (default), the hot path adds zero scenario imports and produces byte-identical output. Scenarios are deterministic what-if calculations, not predictions. **Recourse is not opt-in** — there is no flag or env var; `compute_recourse` runs automatically, unconditionally, whenever `is_genuinely_close` returns `True` for the baseline forecast, and its result is appended to `OrchestrationResult` and rendered by the report layer.

## Public APIs / Contracts

* **Imports:**

  ```python
  from src.market.snapshot import build_snapshot
  from src.market.hypotheses import generate_hypotheses
  from src.market.rejector import reject_unrealistic
  from src.market.regional_income import build_regional_income
  from src.market.adapter import perturb_inputs
  from src.market.scenario_runner import resolve_snapshot, run_scenarios
  from src.market.recourse import is_genuinely_close, compute_recourse
  ```
* **Key Types** (see ../schemas/README.md):

  * `MarketSnapshot` (fractional fields, frozen) — baseline context.
  * `MarketHypothesis` (absolute **deltas**; priors; rationale; STR flag).
  * `HypothesisSet` (collection with notes/seed; priors sum to 1 after rejector).
  * `RegionalIncomeTable` (median/p25/p75; also carries `turnover_cost`/`str_multiplier` fields the
    schema still defines but no production caller renders — see the Gate 3 correction above).
* **Functions / Classes:**

  * `build_snapshot(m: Mapping[str, Any]) -> MarketSnapshot`
    Validates required keys; enforces **fractions** for rates (e.g., 0.05 for 5%).
  * `generate_hypotheses(snapshot, *, seed=42, bands=None, grid_steps=None) -> HypothesisSet`
    Deterministic grid over ordered axes: `("rent_delta","expense_growth_delta","interest_rate_delta","cap_rate_delta","vacancy_delta")`. Deltas are **absolute percentage points** (e.g., `0.02 == +200 bps`). Computes priors and notes.
  * `reject_unrealistic(hs: HypothesisSet, snap: MarketSnapshot) -> HypothesisSet`
    Applies hard bounds and soft penalties, flips incoherent STR flags, **renormalizes priors**, and returns a **deterministically ordered** set.
  * `build_regional_income(region: str, bedrooms: int, comps: list[float]) -> RegionalIncomeTable`
    Aggregates comp rents; returns frozen table with convenience `summary()`. Reachable in
    production via `deal-advisor --regional-income` (see the reachability note above); also
    directly importable.
  * `perturb_inputs(fi: FinancialInputs, hypothesis: MarketHypothesis, *, base_cap: float) -> FinancialInputs`
    (Wave 2) Returns a perturbed **deep copy** of `FinancialInputs` with deltas applied (income, opex, financing, market fields) per the hypothesis. Original untouched. `base_cap` is the engine-derived purchase cap from untouched inputs.
  * `resolve_snapshot(inputs: FinancialInputs, *, market_block: Mapping | None) -> MarketSnapshot`
    (Wave 2) Resolves the `MarketSnapshot` for scenario generation. Source priority: (1) explicit `market` block if provided (parsed by `build_snapshot`); (2) fallback derivation from `FinancialInputs`; (3) loud-fail if no cap is derivable. Never silently invents a cap (invariant §5).
  * `run_scenarios(inputs: FinancialInputs, snapshot: MarketSnapshot, *, seed: int = 42) -> ScenarioAnalysis`
    (Wave 2) Runs the full scenario pipeline: baseline engine pass (for `base_cap`) → generate hypotheses → reject unrealistic → per-scenario engine re-run → prior-weighted aggregation. Deterministic; returns `ScenarioAnalysis` with prior-weighted bands (p25/p50/mean/min/max) per metric.
  * `is_genuinely_close(inputs: FinancialInputs, *, horizon_years: int = DEFAULT_HORIZON_YEARS) -> bool`
    (Mission 4) Pre-computation scoping gate. Evaluates a fresh baseline forecast of `inputs` alone (no search, no bisection, no lever perturbation) and counts how many of the *live* guardrails (the seven from `chief_strategist.py`, minus any not applicable to this deal's `market` config) currently fail. Returns `True` iff `0 < num_fails <= GENUINELY_CLOSE_MAX_FAILS` (`GENUINELY_CLOSE_MAX_FAILS = 3`). There is no per-guardrail margin or "closeness tolerance" — this is a pure fail-count test, verdict-independent (a DECLINE with 1–3 failing guardrails opens the gate exactly as a CONDITIONAL would; a BUY with 0 fails never opens it; a DECLINE with 4+ fails never opens it either). Does not peek at whether any lever could actually close a gap — that is `compute_recourse`'s job, run only after this gate opens.
  * `compute_recourse(inputs: FinancialInputs, *, horizon_years: int = DEFAULT_HORIZON_YEARS) -> RecourseAnalysis`
    (Mission 4) For each failing guardrail, find the single most impactful investor-movable change (rent/price/rate/opex) that would close it — by bisecting on each lever and re-running the engine, never by inverting a formula. Returns a fully populated `RecourseAnalysis` with one row per lever/guardrail pair; implausible levers are flagged with a reason but not removed. Cheapest-fix rows are ranked first; remaining-gap counts prevent partial-fix confusion. Does not itself check `is_genuinely_close` — callers gate before calling this.

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
print(tbl.summary())  # region/bedrooms/P25/Median/P75 rent -- same string deal-advisor prints
```

> As of 2026-08-05 this is also reachable from `deal-advisor --regional-income <path>` (Mission 2
> task 3.1b) — see the reachability note in "Purpose / Responsibilities" above and
> `src/cli/README.md`.

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
* **Wired** into the main pipeline: called from `main.py` when `--scenarios` is ON; results passed to `write_report` for the "Market Scenarios" overlay section. With scenarios OFF, zero market imports occur on the hot path. This wiring covers `snapshot.py` → `hypotheses.py` → `rejector.py` → `adapter.py` → `scenario_runner.py`; it does **not** include `regional_income.py`, which is a separate entry point reached from `deal-advisor --regional-income` instead (see reachability note above) — it needs only comps, not an engine run, so it was never part of this chain.

## Test Strategy

* Unit tests:

  * `tests/unit/test_market_snapshot.py` — snapshot building/validation.
  * `tests/unit/test_market_hypotheses.py` — deltas, symbols (▲/▼/➝), priors, immutability.
  * `tests/unit/test_rejector.py` — hard bounds, rent-vs-vacancy rule, STR coherence flip, renormalization, deterministic order.
  * `tests/unit/test_market_regional_income.py` — table shape & summaries.
  * `tests/integration/test_advisor_cli_wiring.py` — `deal-advisor --regional-income` end-to-end
    (embeds the real `build_regional_income()` median/p25/p75 output; loud-fails on missing keys;
    asserts `turnover_cost`/`str_multiplier` never appear in `--out`/`--markdown`/console output).
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

_Last reconciled: 2026-08-29 against mission/4-actionable-recourse (doc-audit correction): the same-mission pass that first added `recourse.py` to this file mis-described the feature twice — the Purpose bullet said recourse only fires "for deals with a `CONDITIONAL` verdict" (false: `is_genuinely_close` is a verdict-independent fail-count test, `0 < num_fails <= GENUINELY_CLOSE_MAX_FAILS = 3`, and the shipped fixture `data/sample_listings/82_champlain_dieppe/` is a DECLINE with the gate open), and `is_genuinely_close`'s row invented a per-guardrail "closeness tolerance" margin that does not exist in `src/market/recourse.py`. Both corrected against the source (`grep -n GENUINELY_CLOSE_MAX_FAILS src/market/recourse.py`; `python -c "from src.market.recourse import is_genuinely_close; ..."` against the fixture, verified `is_genuinely_close(...) == True`, `verdict == "DECLINE"`, on 2026-08-29). Also corrected the status note: recourse is not opt-in (no flag/env var exists for it; only Market Scenarios is). Earlier note: 2026-08-05 against mission/2-wiring-gaps (Gate 3 remediation): corrected the
`build_regional_income`/`RegionalIncomeTable` bullets above — `str_multiplier`/`turnover_cost` were
fabricated and no longer reach `deal-advisor`'s output (`str_multiplier` is no longer computed at
all); every code sample and reachability note updated to say so. See `CHANGELOG.md` "Removed".
Earlier note: 2026-08-05 against mission/2-wiring-gaps (task 3.1b, OPD-3 "wire-first"):
`build_regional_income` is now wired into `deal-advisor --regional-income`, closing the
reachability gap this file has tracked since 2026-08-03 — every "reachable only from tests"
mention above is updated accordingly. Earlier note: 2026-08-04 against mission/2-wiring-gaps @ d18ee1a (Gate 2 VETO remediation: added the full-suite coverage-gate note; no other content change — the guardian confirmed this file's OPD-3 framing accurate at Gate 2. Earlier note: 2026-08-03 @ 74c985c, clarified `build_regional_income` is reachable only from tests today; Wave 3/OPD-3 will decide whether to wire it)._
