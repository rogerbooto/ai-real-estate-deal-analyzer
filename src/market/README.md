# market

## Purpose / Responsibilities

* Deterministic **market context & scenario utilities** used for forecasting and guardrails:

  * Build a `MarketSnapshot` from user/JSON inputs.
  * Generate a small **Cartesian grid** of “what-if” `MarketHypothesis` deltas around a snapshot.
  * Apply **rejector** rules to prune unrealistic combos and renormalize priors.
  * Produce **regional income tables** for sanity-checks and scenario seeding.
* **Status in V1**: not yet wired into `orchestrators/crew.py` main pipeline; treat as **V2 optional utilities** ready for integration.

## Public APIs / Contracts

* **Imports:**

  ```python
  from src.market.snapshot import build_snapshot
  from src.market.hypotheses import generate_hypotheses
  from src.market.rejector import reject_unrealistic
  from src.market.regional_income import build_regional_income
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
    Aggregates comp rents; returns frozen table with convenience `summary()`.

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

* Depends on `src.schemas.models` types (`MarketSnapshot`, `MarketHypothesis`, `HypothesisSet`, `RegionalIncomeTable`).
* No external services; **pure deterministic** utilities.
* Intended to feed **Core Finance** (../core/README.md) by perturbing inputs for scenario analysis; **not yet wired** into the default orchestrator.

## Test Strategy

* Unit tests:

  * `tests/unit/test_market_snapshot.py` — snapshot building/validation.
  * `tests/unit/test_market_hypotheses.py` — deltas, symbols (▲/▼/➝), priors, immutability.
  * `tests/unit/test_rejector.py` — hard bounds, rent-vs-vacancy rule, STR coherence flip, renormalization, deterministic order.
  * `tests/unit/test_market_regional_income.py` — table shape & summaries.
* Run:

  ```
  pytest -q tests/unit/test_market_*.py tests/unit/test_rejector.py
  ```

## Cross-links

* Back to [Main README](../README.md)
* Types anchor: [`../schemas/README.md`](../schemas/README.md)
* Finance context (how scenarios affect underwriting): [`../core/README.md`](../core/README.md)
* Orchestrator wiring status & proposal: [`../orchestrators/README.md`](../orchestrators/README.md)
* Agents that could consume scenarios (future): [`../agents/README.md`](../agents/README.md)
* Reporting patterns for scenario outputs: [`../reports/README.md`](../reports/README.md)

## Change Log Notes (scoped)

* Milestone B: Introduced 3-point grid generator, rejector hard/soft rules, STR coherence flip, deterministic ordering.
* Current: Marked as **V2 optional utilities** pending integration into `orchestrators
