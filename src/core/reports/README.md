# reports

## Purpose / Responsibilities

* Generate **human-readable investment reports** summarizing forecasts, listing insights, media insights, and the investment thesis.
* Final presentation layer of the deterministic pipeline; also powers the `deal-report` CLI (`src/cli/report_cli.py`).
* Converts Pydantic models (`FinancialForecast`, `ListingInsights`, `InvestmentThesis`, `MediaInsights`, `PhotoInsights`) into Markdown and structured report models.

## Public APIs / Contracts

* **Imports (verified):**

  ```python
  from src.core.reports.generator import generate_report, write_report
  from src.core.reports.photo_report import build_media_report
  from src.core.reports.report_models import MediaReport, MediaItemSummary, MediaCoverage, ParkingSummary
  ```

### Report Generator

* `generate_report(insights: ListingInsights | None, forecast: FinancialForecast, thesis: InvestmentThesis | None = None, title_override: str | None = None, *, media_insights: MediaInsights | None = None, scenarios: ScenarioAnalysis | None = None) -> str`

  Builds a Markdown investment report with sections:

  1. **Header** — property summary (address, amenities, notes).
  2. **Purchase Metrics** — cap rate, CoC, DSCR, debt service, acquisition cash, spread.
  3. **Forecasting Methodology** — baseline, stress-test, and NOI-based formulas + refi rule.
  4. **Media Overview** — counts, dimensions, duplicates, hero image (when `media_insights` provided).
  5. **Investment Thesis** (when provided).
  6. **Pro Forma (Summary)** — annual GSI/GOI/OPEX/NOI/DS/CF/DSCR/balance table.
  7. **Valuation tables** — Baseline, Stress-Test, and NOI-Based.
  8. **OPEX Detail (Year 1)**, **Refinance Event**, **Returns Summary**, **Warnings**.
  9. **Market Scenarios** — opt-in what-if overlay, appended **last** and rendered **only** when a `ScenarioAnalysis` is supplied (keyword-only `scenarios`). With `scenarios=None` the output is byte-for-byte identical to today's. Includes the fixed verbatim "About these scenarios" honesty block (`ABOUT_SCENARIOS_BLOCK`), a top-5-by-prior grid, prior-weighted bands (`downside (p25)` / `median (p50)` / `mean (expected)` / `min` / `max`), caveats, and an honest empty-set state when no scenarios are admitted.

* `write_report(path, insights, forecast, thesis=None, *, media_insights=None, scenarios=None) -> None`
  Convenience wrapper; creates parent directories and writes the Markdown file. `scenarios` is forwarded to `generate_report` unchanged.

### Media Report

* `build_media_report(photos: PhotoInsights, listing: ListingNormalized | None = None) -> MediaReport`
  Deterministic mapping of photo insights (room counts, amenities, defects, quality flags, parking) into a structured `MediaReport`.

### Environment overrides (read at render time)

| Flag | Effect |
| --- | --- |
| `AIREAL_CAP_DRIFT_BPS` | Annual cap-rate drift (basis points) used in valuation tables. |
| `AIREAL_APPRECIATION_PCT` | Baseline appreciation rate override. |
| `AIREAL_STRESS_ADJ` | Stress adjustment applied in the stress-test valuation table. |

## Design Notes / Invariants

* **Deterministic layout:** section order and headings are fixed for consistency; empty sections are omitted.
* **Stable rounding:** monetary values to two decimals; rates to two percentage decimals.
* **Pure function:** `generate_report()` has no side effects; `write_report()` only writes the target file.
* **Portable:** output is plain Markdown; PDF/HTML rendering is external (see also `core/intelligence/report_builder.py` for the deal-intelligence Markdown/HTML path).

## Test Strategy

* `tests/core/reports/` — generator sections, formatting, media overview.
* `tests/integration/test_report_cli_*.py` — CLI rendering paths (minimal, media, errors).
* Run:

  ```bash
  pytest -q tests/core/reports tests/integration/test_report_cli_minimal.py
  ```

## Cross-links

* Back to [Main README](../../../README.md)
* Schemas: [`../../schemas/README.md`](../../schemas/README.md)
* Core: [`../README.md`](../README.md)
* CLI: [`../../cli/README.md`](../../cli/README.md)
* Agents: [`../../agents/README.md`](../../agents/README.md)
* Orchestrators: [`../../orchestrators/README.md`](../../orchestrators/README.md)

---

_Last reconciled: 2026-07-23 against main @ e4716df._
