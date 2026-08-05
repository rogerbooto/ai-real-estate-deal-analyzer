# inputs

## Purpose / Responsibilities

* Define and validate user-provided **input payloads** for the Deal Analyzer.
* Support both the **legacy** shape (a bare `FinancialInputs` JSON) and the **structured** shape (`AppInputs` = financial inputs + run options), ensuring backward compatibility.
* Apply environment-variable overrides for run options before orchestrator execution.

## Public APIs / Contracts

* **Imports (verified):**

  ```python
  from src.inputs.inputs import AppInputs, RunOptions, InputsLoader, load_inputs
  ```

### Models (defined here, not in `schemas`)

* `RunOptions` — runtime, non-financial options:
  `out` (default `investment_analysis.md`), `horizon` (1–50, default 10), `listing`, `photos`, `engine` (`"deterministic"` | `"crewai"`), `scenarios` (bool, default `False` — opt-in Market Scenarios overlay).
* `AppInputs` — full payload: `inputs: FinancialInputs` + `run: RunOptions` + optional `market` (a raw market-snapshot block, carried alongside — deliberately **not** part of the frozen `FinancialInputs` — and consumed only by the opt-in scenario engine).

### Loader

* `InputsLoader` (frozen dataclass, `env_prefix="AIREAL_"`):

  * `load(path=None) -> AppInputs` — reads JSON from `path`, or falls back to `./data/sample_listings/36_kelly_moncton/inputs.json` then `./config.json`. Auto-detects legacy vs structured shape, validates with Pydantic, then applies env overrides.
  * `load_json(text) -> AppInputs` — same, from a JSON string.
  * `with_overrides(cfg, *, out=None, horizon=None, listing=None, photos=None, engine=None, scenarios=None) -> AppInputs` — CLI-flag overrides (used by `main.py`). `scenarios` uses `None` = "no CLI override" (so the `--scenarios` `store_true` flag, `False` when absent, defers to env/JSON); pass `True` to force it on.
* `load_inputs(path=None) -> AppInputs` — convenience function wrapping `InputsLoader().load()`.

## Input Formats

### 1) Legacy format (`FinancialInputs` root)

```json
{
  "financing": { "purchase_price": 500000, "down_payment_rate": 0.25,
                 "interest_rate": 0.055, "amort_years": 30, "io_years": 0 },
  "opex":      { "insurance": 2400, "taxes": 6000, "repairs_maintenance": 2400,
                 "property_management": 4800 },
  "income":    { "units": [ { "rent_month": 1200, "other_income_month": 50 } ],
                 "occupancy": 0.95, "bad_debt_factor": 0.97, "rent_growth": 0.03 }
}
```

### 2) Structured format (`AppInputs`)

```json
{
  "inputs": { "financing": { "...": "..." }, "opex": { "...": "..." }, "income": { "...": "..." } },
  "run":    { "out": "out.md", "horizon": 10, "listing": "listing.txt",
              "photos": "./photos", "engine": "deterministic", "scenarios": false },
  "market": { "region": "Moncton, NB", "vacancy_rate": 0.06, "cap_rate": 0.055,
              "rent_growth": 0.03, "expense_growth": 0.02, "interest_rate": 0.055 }
}
```

> The top-level `market` block (sibling of `inputs`/`run`) is the **market-snapshot** source for the opt-in scenario engine. It is distinct from `inputs.market` (`MarketAssumptions`, cap-rate guardrails). When `run.scenarios` is ON, it is parsed by `src.market.snapshot.build_snapshot`; if absent, the resolver falls back to deriving a snapshot from `FinancialInputs` and **loud-fails** when no cap can be derived (`market.cap_rate_purchase is None`).

### Environment overrides (applied last, on run options)

| Variable | Overrides |
| --- | --- |
| `AIREAL_OUT` | `run.out` |
| `AIREAL_HORIZON` | `run.horizon` (int) |
| `AIREAL_LISTING` | `run.listing` |
| `AIREAL_PHOTOS` | `run.photos` |
| `AIREAL_ENGINE` | `run.engine` |
| `AIREAL_SCENARIOS` | `run.scenarios` (truthy `1/true/yes/on` enables; any other non-empty value disables) |

> Financial stress/valuation overrides (`AIREAL_CAP_DRIFT_BPS`, `AIREAL_APPRECIATION_PCT`, `AIREAL_STRESS_ADJ`) are read by the **report generator**, not the inputs loader — see [`../core/reports/README.md`](../core/reports/README.md).

## Design Notes / Invariants

* **Rates as fractions [0–1]:** all numeric rates are fractional, not percentages (validation lives in `schemas.models`).
* **Precedence:** file values → env overrides → explicit CLI overrides (`with_overrides`).
* **Income is per-unit:** the legacy translator maps older income shapes onto the `units[]`-based `IncomeModel`.
* **JSON-only serialization:** YAML and CSV are not supported.

## Dependencies / Optional Providers

* Depends on [`../schemas/README.md`](../schemas/README.md) for `FinancialInputs`.
* Used by `main.py` and [`../orchestrators/README.md`](../orchestrators/README.md).
* No external providers required.

## Test Strategy

* Covered indirectly via orchestrator/integration tests and `main.py` runs; dedicated loader unit tests are a known gap.
* Run:

  ```bash
  pytest -q --no-cov tests/integration
  ```

  `--no-cov` disables coverage for this subset run only; the project's ≥80% coverage gate
  (`pytest.ini`, `--cov-fail-under=80`) is enforced against the **full** `pytest` suite, not any
  one subset command.

## Cross-links

* Back to [Main README](../../README.md)
* Schemas: [`../schemas/README.md`](../schemas/README.md)
* Core logic: [`../core/README.md`](../core/README.md)
* Orchestrators: [`../orchestrators/README.md`](../orchestrators/README.md)

---

_Last reconciled: 2026-08-04 against mission/2-wiring-gaps @ d18ee1a (Gate 2 VETO remediation, condition C4: stamp was stale — content re-verified against current code (imports, `RunOptions`/`AppInputs` fields, env-override table) with no drift found; added the full-suite coverage-gate note)._
