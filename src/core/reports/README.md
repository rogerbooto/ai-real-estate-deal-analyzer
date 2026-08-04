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

* `generate_report(insights: ListingInsights | None, forecast: FinancialForecast, thesis: InvestmentThesis | None = None, title_override: str | None = None, *, media_insights: MediaInsights | None = None, media_report: MediaReport | None = None, provenance: RunProvenance | None = None, scenarios: ScenarioAnalysis | None = None, baseline: BaselineOutlook | None = None) -> str`

  Builds a Markdown investment report with sections:

  1. **Header** — property identity (address → inferred title → "Subject Property"), an
     **As listed** line of stated facts (price, beds/baths, sqft, $/sqft, year built), amenities,
     notes, condition tags and defects.
  2. **Purchase Metrics** — cap rate, CoC, DSCR, debt service, acquisition cash, spread.
  3. **Forecasting Methodology** — baseline, stress-test, and NOI-based formulas + refi rule.
  4. **Media Overview** — counts, dimensions, duplicates, hero image (when `media_insights` provided).
  5. **Photo Coverage** — which rooms the photo set documents, amenities visible in photos, and
     provider provenance (when `media_report` provided). Describes what the photos *show*, where
     Media Overview describes the *files*.
  6. **Investment Thesis** (when provided).
  7. **Pro Forma (Summary)** — annual GSI/GOI/OPEX/NOI/DS/CF/DSCR/balance table.
  8. **Valuation tables** — Baseline, Stress-Test, and NOI-Based.
  9. **OPEX Detail (Year 1)**.
  10. **Adjustments Applied** — renders `YearBreakdown.notes` for any year that carries them (in
      practice only Year 1, since insight modifiers apply once at the top of the model).
      **This section IS reachable on the plain deterministic engine.** The engine's *income*
      modifiers fire whenever `FinancialInputs.income_is_estimated` is `True` (a documented,
      user-settable field, `src/schemas/models.py:135`) and the listing yields the amenity
      `parking` or `in-unit laundry` — no AI, no `--engine crewai`, no `AIREAL_LLM_MODE`.
      Reproduced: a text-path listing saying "Parking" with `income_is_estimated=True` produces
      `Y1 notes: ['amenity uplift: parking (+$50/mo/unit other income)']`, and
      `tests/orchestrators/test_orchestration_result_field_guard.py:48-55` relies on exactly that
      path. The demo bundle simply does not set `income_is_estimated`, which is why *its* report
      is unaffected.
      **⚠ The narrower claim, which is true: the two OPEX-bump triggers are unreachable
      deterministically** — the engine's OPEX triggers
      (`src/core/finance/engine.py:64,68`) check for the literal strings `"old roof"` in
      `condition_tags` and `"water stain"` in `defects`, but no path that assembles a
      `ListingInsights` deterministically can produce either string: on the text-ingestion path,
      condition tags come from `_CONDITION_KEYWORDS`'s free-string list
      (`src/core/ingest/listing_parser.py:37-45`, which has `"new roof"`, not `"old roof"`), and
      defects come from the closed `ConditionTag`/`DefectLabel` enums (`src/schemas/labels.py`),
      where `"water stain"` is normalized to `DefectLabel.water_leak_suspected` before the
      engine's literal check ever sees it (`labels.py:241`). The demo report is byte-identical
      with and without this section on that path. **It is reachable via `--engine crewai` with
      `AIREAL_LLM_MODE=1`**, however: `ListingAnalystAgent`'s LLM-authored `ListingInsights`
      (`src/agents/crewai_components.py`) are parsed straight from model JSON into the schema with
      no normalization pass, so an LLM that writes the literal strings `"old roof"` or
      `"water stain"` reaches the engine unnormalized and fires this section for real. It also
      renders if a caller hand-constructs a `ListingInsights` with those exact strings directly
      (e.g. a unit test). This is a documentation-honesty note about the deterministic path, not a
      claim that the section can never fire — see
      `docs/plans/MISSION_2_SPRINT_TRACKER.md` (Gate 2 record, findings V2/C2) for how the original,
      broader "cannot appear on any real pipeline run" claim was found to over-claim.
  11. **Refinance Event**, **Returns Summary**, **Warnings**.
  12. **Market Scenarios** — opt-in what-if overlay, appended **last** and rendered **only** when a `ScenarioAnalysis` is supplied (keyword-only `scenarios`). With `scenarios=None` the output is byte-for-byte identical to today's. Includes the fixed verbatim "About these scenarios" honesty block (`ABOUT_SCENARIOS_BLOCK`), a top-5-by-prior grid, prior-weighted bands (`downside (p25)` / `median (p50)` / `mean (expected)` / `min` / `max`), caveats, and an honest empty-set state when no scenarios are admitted.
  13. **Appendix — Run Provenance** (always emitted; see below).
  14. **Appendix — Definitions** (always emitted, last; see below).

* `write_report(path: str | Path, insights: ListingInsights | None, forecast: FinancialForecast, thesis: InvestmentThesis | None = None, *, media_insights: MediaInsights | None = None, media_report: MediaReport | None = None, provenance: RunProvenance | None = None, scenarios: ScenarioAnalysis | None = None, baseline: BaselineOutlook | None = None) -> None`
  Convenience wrapper; creates parent directories and writes the Markdown file. All keyword-only
  arguments are forwarded to `generate_report` unchanged.

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
* **Portable:** output is plain Markdown; PDF/HTML rendering is external (see also `core/intelligence/report_builder.py` for the deal-intelligence Markdown/HTML path — as of 2026-08-03 that module exists and is tested but has no production caller; see Mission 2 charter finding T4).

## Test Strategy

* `tests/core/reports/` — generator sections, formatting, media overview.
* `tests/integration/test_report_cli_*.py` — CLI rendering paths (minimal, media, errors).
* Run:

  ```bash
  pytest -q --no-cov tests/core/reports tests/integration/test_report_cli_minimal.py
  ```

  `--no-cov` disables coverage for this subset run only; the project's ≥80% coverage gate
  (`pytest.ini`, `--cov-fail-under=80`) is enforced against the **full** `pytest` suite, not any
  one subset command.

## Cross-links

* Back to [Main README](../../../README.md)
* Schemas: [`../../schemas/README.md`](../../schemas/README.md)
* Core: [`../README.md`](../README.md)
* CLI: [`../../cli/README.md`](../../cli/README.md)
* Agents: [`../../agents/README.md`](../../agents/README.md)
* Orchestrators: [`../../orchestrators/README.md`](../../orchestrators/README.md)

---

_Last reconciled: 2026-08-04 against mission/2-wiring-gaps @ d18ee1a (Gate 2 VETO remediation: narrowed the "Adjustments Applied" honesty note — it is unreachable from the deterministic pipeline (text-path condition tags come from the free-string `_CONDITION_KEYWORDS` list, not only the closed enum) but reachable via `--engine crewai` with `AIREAL_LLM_MODE=1`, where LLM-authored observations bypass normalization; dropped the dangling "charter finding M10" citation (no such charter text exists) in favour of the tracker's actual Gate 2 record. Earlier note: 2026-08-03 @ 74c985c, `generate_report`/`write_report` signatures corrected to include `media_report`/`provenance`)._

### Appendix — Definitions

`_render_glossary()` emits a definitions table **last, on every report** (unlike the optional media
and scenario sections). Entries live in the `_GLOSSARY` tuple and define each term **as the engine
computes it**, not in its textbook form — notably `Debt Service`, which discloses that amortization
uses annual periods and therefore runs above a monthly-pay loan of the same rate and term.

Terms in the body link to it via explicit `<a id="g-..."></a>` anchors (explicit rather than
heading-derived so the links survive PDF export). `tests/core/reports/test_report_glossary.py`
fails if any `](#g-...)` link has no matching anchor, so a linked term without a definition
cannot ship.

### Appendix — Run Provenance

`_render_provenance()` records the settings a report was generated under: cap-rate drift,
baseline appreciation, stress basis adjustment, plus the engine, scenarios flag, AI-vision flag
and inputs file when the caller supplies a `RunProvenance`.

It exists because `.env` is gitignored and VS Code's Python extension auto-loads it, so two runs
of the same command on the same inputs could disagree with nothing explaining why.

**The block cannot drift out of sync with the numbers it describes:** the three valuation knobs are
read from the same accessors (`_cap_drift_per_year`, `_appreciation_rate`, `_stress_adj`) that
produced the valuation tables, never from values passed in alongside.
`tests/core/reports/test_report_provenance.py` asserts a claimed drift is actually visible in the
NOI table and a claimed appreciation in the baseline heading.
