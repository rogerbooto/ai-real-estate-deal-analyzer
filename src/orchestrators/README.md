# orchestrators

## Purpose / Responsibilities

* Coordinate multi-step execution flows combining agents and core modules.
* Serve as the **entry point for deterministic orchestration** and as the seam for CrewAI-based orchestration.
* Expose functions/classes that run end-to-end investment analyses from listing inputs to a report-ready result bundle.

## Public APIs / Contracts

* **Imports (verified):**

  ```python
  from src.orchestrators.crew import run_orchestration, OrchestrationResult
  from src.orchestrators.cv_tagging_orchestrator import CvTaggingOrchestrator
  from src.orchestrators import crewai_runner  # crewai_runner.run_orchestration
  ```

### Deterministic Orchestrator (default)

* `run_orchestration(inputs: FinancialInputs, listing_txt_path: str | None = None, photos_folder: str | None = None, *, horizon_years: int = 10) -> OrchestrationResult`

  Executes the pipeline **Analyst → Forecaster → Strategist**:

  1. `agents.listing_analyst.analyze_listing()` → `ListingInsights`.
  2. `agents.financial_forecaster.forecast_financials()` → `FinancialForecast`.
  3. `agents.chief_strategist.synthesize_thesis()` → `InvestmentThesis`.

  Returns `OrchestrationResult(insights, forecast, thesis, media_insights, media_report)`. The two media
  fields are populated only when `photos_folder` is supplied and readable — `media_insights` from
  `core.media.local.collect_local_assets` → `core.media.insights.analyze_media` (file stats), and
  `media_report` from `core.cv.photo_insights.build_photo_insights` → `core.reports.photo_report.build_media_report`
  (room coverage). Report rendering is the caller's job (see `main.py` → `core.reports.generator.write_report`).

### CV Tagging Orchestrator

* `CvTaggingOrchestrator` — the **single door** for photo tagging:

  * `analyze_paths(photo_paths)` / `analyze_folder(folder, recursive=True)` → per-image records + rollups (amenities, condition tags, defects, warnings).
  * Combines deterministic generic labels (`tag_images`) with closed-set detections (`tag_amenities_and_defects`), promoting filename-derived materials to amenity surfaces.
  * Reads `AIREAL_USE_VISION` at import time: `1` selects the `vision` provider path, else `local`. Providers are deterministic stubs unless an ONNX model is registered.

### CrewAI Orchestrator (seam)

* `crewai_runner.run_orchestration(inputs, listing_txt_path=None, photos_folder=None, *, horizon_years=10) -> OrchestrationResult`

  * Selected via `main.py --engine crewai` (or `AIREAL_ENGINE=crewai` through the inputs loader).
  * **Fail-fast validation**: requires a provider key (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `OPENROUTER_API_KEY`) and an importable `crewai` package.
  * **Parity shell by default**: with `AIREAL_LLM_MODE` unset, Agent/Task shells are constructed but the actual work delegates to the same deterministic functions the `crew` orchestrator uses — `crew.kickoff()` is not called, and output is byte-identical to the deterministic engine.
  * **With `AIREAL_LLM_MODE` set and a provider key present, exactly one step changes**: `ListingAnalystAgent` runs a real `crew.kickoff()` and an LLM authors the `ListingInsights` observations (condition tags, defects, amenities) — falling back to the deterministic analyzer if the call or the JSON parse fails. Those observations reach the forecast through the deterministic insight modifiers, so an LLM run can move the numbers. `FinancialForecasterAgent` and `ChiefStrategistAgent` never call `crew.kickoff()`, in any mode: the arithmetic and the BUY/CONDITIONAL/DECLINE verdict are always produced by the same deterministic engine and rule set (`chief_strategist.synthesize_thesis`). See `src/orchestrators/crewai_runner.py`'s module docstring for the full account.

## Design Notes / Invariants

* **Deterministic path is the default** and requires no external services. The CrewAI engine is a validated seam that is byte-identical to it unless `AIREAL_LLM_MODE` is set with a provider key, in which case only the Listing Analyst's observations can differ — the forecast math and the verdict logic are identical in every mode.
* **Environment flags (functional):**

  * `AIREAL_USE_VISION` — CV provider selection (read in `cv_tagging_orchestrator.py`).
  * `AIREAL_LLM_MODE`, `AIREAL_DEBUG` — read by `agents/crewai_components.py`.
  * `AIREAL_OUT`, `AIREAL_HORIZON`, `AIREAL_LISTING`, `AIREAL_PHOTOS`, `AIREAL_ENGINE` — run-option overrides applied by `src/inputs/inputs.py`.
* **Graceful fallbacks:** missing media or parsing errors log/degrade but never crash the pipeline.
* **Output consistency:** both engines return `OrchestrationResult` consumable by `core.reports.generator`.

## Test Strategy

* `tests/integration/test_orchestrator_deterministic.py`, `test_orchestrator.py` — deterministic pipeline.
* `tests/integration/test_orchestrator_crewai.py` — CrewAI seam (env validation, parity; mocked).
* `tests/orchestrators/test_cv_tagging_orchestrator_basic.py` — path normalization & delegation.
* Run:

  ```bash
  pytest -q --no-cov tests/integration tests/orchestrators
  ```

  `--no-cov` disables coverage for this subset run only; the project's ≥80% coverage gate
  (`pytest.ini`, `--cov-fail-under=80`) is enforced against the **full** `pytest` suite, not any
  one subset command.

## Cross-links

* Back to [Main README](../../README.md)
* Types: [`../schemas/README.md`](../schemas/README.md)
* Agents: [`../agents/README.md`](../agents/README.md)
* Core logic: [`../core/README.md`](../core/README.md)
* CLI entry points: [`../cli/README.md`](../cli/README.md)
* Reports: [`../core/reports/README.md`](../core/reports/README.md)
* Market (future integration): [`../market/README.md`](../market/README.md)

---

_Last reconciled: 2026-08-04 against mission/2-wiring-gaps @ d18ee1a (Gate 2 VETO remediation: the CrewAI Orchestrator entry corrected — `crew.kickoff()` **is** called for the Listing Analyst under `AIREAL_LLM_MODE`; the forecast math and verdict stay deterministic in every mode; added the full-suite coverage-gate note)._
