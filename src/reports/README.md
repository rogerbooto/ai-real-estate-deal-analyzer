# reports

## Purpose / Responsibilities

* Generate **human-readable investment reports** summarizing forecasts, insights, and strategies.
* Acts as the final presentation layer in the deterministic pipeline.
* Converts Pydantic model data (`FinancialForecast`, `InvestmentThesis`) into Markdown or structured text artifacts.

## Public APIs / Contracts

* **Imports:**

  ```python
  from src.reports.generator import generate_report, _fmt_currency, _fmt_pct
  ```

### Report Generator

* `generate_report(forecast: FinancialForecast, thesis: InvestmentThesis, *, output_path: str | Path | None = None) -> str`

  * Builds a Markdown-formatted investment report.
  * Optionally writes to `output_path` (defaults to in-memory string).
  * Sections:

    1. **Header** — Property summary, assumptions, and scenario context.
    2. **Financial Overview** — Purchase metrics, IRR, DSCR, cash-on-cash.
    3. **Operational Forecast** — Yearly breakdown with cash flows and equity growth.
    4. **Investment Thesis** — Summary from strategist agent.
    5. **Appendices** — Model configuration and stress parameters.

### Formatting Helpers

* `_fmt_currency(value: float) -> str` — Formats numbers as currency with `$` and commas.
* `_fmt_pct(value: float) -> str` — Formats rates as percentages with two decimal precision.

## Usage Examples

### 1) Generate Markdown report

```python
from src.reports.generator import generate_report
from src.schemas.models import FinancialForecast, InvestmentThesis

report_md = generate_report(forecast=my_forecast, thesis=my_thesis, output_path="./artifacts/report.md")
print(report_md[:300])  # preview first lines
```

### 2) Custom formatting

```python
from src.reports.generator import _fmt_currency, _fmt_pct

print(_fmt_currency(12345.678))  # "$12,345.68"
print(_fmt_pct(0.0567))          # "5.67%"
```

## Design Notes / Invariants

* **Deterministic layout:** section order and headings fixed for consistency.
* **Stable rounding:** monetary values rounded to two decimals; rates to two percentage decimals.
* **Pure function:** `generate_report()` has no side effects except optional file write.
* **Portable:** output is plain Markdown; rendering handled externally (e.g., GitHub, PDF exporter).
* **Scenario context:** ready for integration with Market hypotheses in future releases.

## Dependencies / Optional Providers

* Depends on:

  * [`../schemas/README.md`](../schemas/README.md) for `FinancialForecast` and `InvestmentThesis` types.
  * [`../agents/README.md`](../agents/README.md) (upstream producers of forecast and thesis).
  * [`../core/README.md`](../core/README.md) (forecast source logic).
* No external dependencies beyond standard library and Pydantic models.

## Test Strategy

* Unit tests:

  * `tests/unit/test_reports_generator.py` — formatting, currency/percent helpers.
  * `tests/unit/test_reports_with_thesis.py` — integration of forecast + thesis content.
* Run:

  ```bash
  pytest -q tests/unit/test_reports_*.py
  ```

## Cross-links

* Back to [Main README](../README.md)
* Schemas: [`../schemas/README.md`](../schemas/README.md)
* Agents: [`../agents/README.md`](../agents/README.md)
* Orchestrators: [`../orchestrators/README.md`](../orchestrators/README.md)
* Core: [`../core/README.md`](../core/README.md)
* Market (future scenario reporting): [`../market/README.md`](../market/README.md)

## Change Log Notes (scoped)

* Markdown report generator finalized for V1 deterministic pipeline.
* Helper formatting functions `_fmt_currency` and `_fmt_pct` added.
* Prepared structure for integration with Market scenarios and stress-test summaries.
