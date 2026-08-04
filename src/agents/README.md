# agents

## Purpose / Responsibilities

* High-level wrappers orchestrating specialized modules from `core/`.
* Each agent performs a distinct role in the deterministic pipeline or the CrewAI-seamed orchestration.
* Designed to be composable, forgiving (missing assets never crash the pipeline), and independently testable.

## Public APIs / Contracts

* **Imports (verified):**

  ```python
  from src.agents.listing_analyst import analyze_listing
  from src.agents.financial_forecaster import forecast_financials
  from src.agents.chief_strategist import synthesize_thesis
  from src.agents.photo_tagger import PhotoTaggerAgent
  from src.agents.listing_ingest import ListingIngestAgent
  from src.agents.crewai_components import (
      ListingAnalystAgent, FinancialForecasterAgent, ChiefStrategistAgent,
  )
  ```

### Listing Analyst

* `analyze_listing(listing_txt_path: str | None = None, photos_folder: str | None = None, *, fallback_text: str | None = None) -> ListingInsights`

  * Parses listing text (file path or raw string fallback) and aggregates photo condition tags/defects.
  * Photo tagging routes through `CvTaggingOrchestrator` (the single door to deterministic/AI CV paths; AI enabled via `AIREAL_USE_VISION=1`).
  * Never raises for missing/broken assets — fields default to empty.

### Financial Forecaster

* `forecast_financials(inputs: FinancialInputs, insights: ListingInsights | None = None, horizon_years: int = 10) -> FinancialForecast`

  * Deterministic wrapper around `core.finance.engine.run_financial_model()`.
  * Normalizes/clamps inputs and guarantees a consistent schema for downstream strategy agents.

### Chief Strategist

* `synthesize_thesis(forecast: FinancialForecast) -> InvestmentThesis`

  * Rule-based verdict (DSCR, cash-flow, spread guardrails) with rationale and improvement levers.
  * **Never LLM-authored, in any mode.** `ChiefStrategistAgent.run` (see `crewai_components.py`) always calls this function on the forecast — `AIREAL_LLM_MODE` does not change that; `_run_llm` was deleted from that class specifically so the verdict cannot bypass it.

### Photo Tagger

* `PhotoTaggerAgent` — thin policy wrapper that delegates batch photo tagging to the CV stack (`src.core.cv.runner`).

### Listing Ingest Agent

* `ListingIngestAgent` — wraps `core.ingest.listing_ingest.ingest_listing()` and adapts the result (address-first insights) for orchestrators.

### CrewAI components

* `ListingAnalystAgent` / `FinancialForecasterAgent` / `ChiefStrategistAgent` — Agent/Task shells used by `orchestrators/crewai_runner.py`. With `AIREAL_LLM_MODE` unset (the default), all three `run()` methods delegate to the same deterministic functions above for math parity — no `crew.kickoff()` is called. With `AIREAL_LLM_MODE` set **and** a provider key present (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `OPENROUTER_API_KEY`), **`ListingAnalystAgent.run()` calls a real `crew.kickoff()`** and an LLM authors the `ListingInsights` it returns (address, amenities, condition tags, defects, notes) — an *observation* layer, falling back to the deterministic `analyze_listing()` if the call or the JSON parse fails. `FinancialForecasterAgent` and `ChiefStrategistAgent` never call `kickoff()`, in any mode: the forecast math and the BUY/CONDITIONAL/DECLINE verdict are always deterministic. Honors `AIREAL_LLM_MODE` and `AIREAL_DEBUG`.

## Design Notes / Invariants

* **Deterministic-first:** all agents default to reproducible behavior.
* **Feature flags (functional today):**

  * `AIREAL_USE_VISION` — enables the AI CV path inside `CvTaggingOrchestrator` (providers are deterministic stubs unless ONNX is registered).
  * `AIREAL_LLM_MODE` — read by `crewai_components.py` for the CrewAI seam.
  * `AIREAL_DEBUG` — verbose logging in CrewAI components.
* **Composition:** agents are composable; orchestrators simply call them in sequence.
* **Inputs/Outputs:** each agent consumes and returns typed Pydantic models from `schemas.models`.
* **Isolation:** no agent persists state; all results are returned upward to orchestrators.

## Test Strategy

* Integration tests:

  * `tests/integration/test_listing_analyst.py` — text + photo aggregation.
  * `tests/integration/test_chief_strategist.py` — rule-based verdicts.
  * `tests/integration/test_photo_tagger_agent*.py` — deterministic tagging paths.
  * `tests/integration/test_listing_ingest.py` — ingestion agent flow.
* Unit tests: `tests/unit/test_financial_forecaster*.py`, `tests/unit/test_strategist*.py`.
* Run:

  ```bash
  pytest -q --no-cov tests/integration tests/unit/test_financial_forecaster.py
  ```

  `--no-cov` disables coverage for this subset run only; the project's ≥80% coverage gate
  (`pytest.ini`, `--cov-fail-under=80`) is enforced against the **full** `pytest` suite, not any
  one subset command.

## Cross-links

* Back to [Main README](../../README.md)
* Types: [`../schemas/README.md`](../schemas/README.md)
* Core logic: [`../core/README.md`](../core/README.md)
* CLI entry points: [`../cli/README.md`](../cli/README.md)
* Orchestrators: [`../orchestrators/README.md`](../orchestrators/README.md)
* Reports: [`../core/reports/README.md`](../core/reports/README.md)
* Market (future scenario inputs): [`../market/README.md`](../market/README.md)

---

_Last reconciled: 2026-08-04 against mission/2-wiring-gaps @ d18ee1a (Gate 2 VETO remediation: Chief Strategist and CrewAI-components entries corrected — `ListingAnalystAgent.run()` does call a real `crew.kickoff()` under `AIREAL_LLM_MODE`, but the verdict is never LLM-authored, in any mode; added the full-suite coverage-gate note)._
