# inputs

## Purpose / Responsibilities

* Define and validate user-provided **input data** for the Deal Analyzer.
* Support both **legacy** and **structured** input formats, ensuring backward compatibility.
* Normalize financial, market, and operational parameters before orchestrator execution.

## Public APIs / Contracts

* **Imports:**

  ```python
  from src.inputs.inputs import load_inputs, parse_inputs
  ```

### Input Loading

* `load_inputs(path: str | Path | dict) -> FinancialInputs | AppInputs`

  * Reads and parses JSON or dictionary input.
  * Auto-detects format (legacy or structured) and returns the appropriate model.
  * Environment overrides (if set) apply last.

### Input Parsing

* `parse_inputs(raw: dict) -> FinancialInputs | AppInputs`

  * Internal helper used by orchestrators.
  * Validates numeric consistency (non-negative rates, currency alignment).
  * Coerces rates expressed as percentages (e.g., `5` → `0.05`).

## Input Formats

### 1) Legacy format (FinancialInputs root)

```json
{
  "financing": {
    "purchase_price": 199900,
    "down_payment_rate": 0.05,
    "interest_rate": 0.047,
    "amort_years": 25,
    "io_years": 0,
    "mortgage_insurance_rate": 0.04
  },
  "opex": {
    "insurance": 1200,
    "taxes": 2621,
    "repairs_maintenance": 2000,
    "property_management": 1596,
    "water_sewer": 1200,
    "snow_removal": 600
  },
  "income": {
    "gross_rent": 24000,
    "vacancy_rate": 0.05
  }
}
```

### 2) Structured format (AppInputs)

```json
{
  "run_options": {
    "llm_mode": 0,
    "debug": true
  },
  "financial_inputs": {
    "financing": { ... },
    "opex": { ... },
    "income": { ... }
  }
}
```

### Environment Overrides

Optional environment variables applied during load:

* `AIREAL_CAP_DRIFT_BPS`  — modifies annual cap rate drift (+/- basis points).
* `AIREAL_APPRECIATION_PCT`  — adjusts property appreciation rate.
* `AIREAL_STRESS_ADJ`  — adds stress factor to financial projection.
* These overrides affect model assumptions before forecasting.

## Usage Examples

### 1) Load structured input

```python
from src.inputs.inputs import load_inputs
inputs = load_inputs("./examples/app_inputs.json")
print(inputs.financial_inputs.financing.interest_rate)
```

### 2) Use with orchestrator

```python
from src.orchestrators.crew import run_orchestration
from src.inputs.inputs import load_inputs

inputs = load_inputs("./examples/sample_inputs.json")
result = run_orchestration(inputs)
```

## Design Notes / Invariants

* **Rates as fractions [0–1]:** all numeric rates are fractional, not percentages.
* **Environment-first precedence:** runtime `.env` values override file defaults.
* **Non-negativity enforced:** validators reject negative monetary or percentage inputs.
* **JSON-only serialization:** YAML and CSV not supported.
* **Backwards-compatible:** legacy format automatically normalized to structured schema internally.

## Dependencies / Optional Providers

* Depends on [`../schemas/README.md`](../schemas/README.md) for model definitions (`FinancialInputs`, `AppInputs`, `RunOptions`).
* Used by [`../orchestrators/README.md`](../orchestrators/README.md) and [`../agents/README.md`](../agents/README.md).
* No external providers required.

## Test Strategy

* Unit tests:

  * `tests/unit/test_inputs_parser.py` — validation, coercion, env overrides.
  * `tests/unit/test_inputs_loader.py` — legacy vs structured detection.
* Run:

  ```bash
  pytest -q tests/unit/test_inputs_*.py
  ```

## Cross-links

* Back to [Main README](../README.md)
* Schemas: [`../schemas/README.md`](../schemas/README.md)
* Core Logic: [`../core/README.md`](../core/README.md)
* Agents: [`../agents/README.md`](../agents/README.md)
* Orchestrators: [`../orchestrators/README.md`](../orchestrators/README.md)

## Change Log Notes (scoped)

* Unified input handling for deterministic and LLM pipelines.
* Added environment override support for financial stress testing.
* Legacy input compatibility retained for backward compatibility.
