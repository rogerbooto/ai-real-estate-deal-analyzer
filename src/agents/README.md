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
  from src.agents.crewai_components import (
      ListingAnalystAgent, FinancialForecasterAgent, ChiefStrategistAgent,
  )
  ```

### Listing Analyst

* `analyze_listing(listing_txt_path: str | None = None, photos_folder: str | None = None, *, fallback_text: str | None = None) -> ListingInsights`

  * Parses listing text (file path or raw string fallback) and aggregates photo condition tags/defects.
  * Merges the text and photo **provenance ledgers** into `ListingInsights.observations`: a tag both sources report keeps one record each, so a reader can tell
    "the copy claims it" from "a detector saw it" from "both agree". Records whose tag did not survive the merge are dropped rather than left dangling.
  * Photo tagging routes through `CvTaggingOrchestrator` (the single door to deterministic/AI CV paths; AI enabled via `AIREAL_USE_VISION=1`).
  * Labels a **file name** suggested that no registered detector can look for arrive as `rollup["unconfirmed_hints"]` and are rendered into `notes`, never into
    `amenities`/`condition_tags`/`defects`. Those three lists are what `finance/engine._apply_insight_modifiers` reads, so this is what stops a file name moving a
    number; `notes` reaches the report and nothing in the finance core. See `src/core/README.md` § "Filename suggestions: SUGGEST vs CONFIRM".
  * Never raises for missing/broken assets — fields default to empty.

### Financial Forecaster

* `forecast_financials(inputs: FinancialInputs, insights: ListingInsights | None = None, horizon_years: int = 10) -> FinancialForecast`

  * Deterministic wrapper around `core.finance.engine.run_financial_model()`.
  * Normalizes/clamps inputs and guarantees a consistent schema for downstream strategy agents.

### Chief Strategist

* `synthesize_thesis(forecast: FinancialForecast, *, market: MarketAssumptions | None = None) -> InvestmentThesis`

  * Rule-based verdict (DSCR, cash-flow, cash-on-cash, spread, IRR and cap-floor guardrails) with
    rationale and improvement levers.
  * **`MIN_COC_Y1` (3%) is the Year-1 cash-on-cash floor** — `CoC = Year-1 cash flow / acquisition
    cash`, computed by the engine onto `PurchaseMetrics.coc` and only *read* here. It is a full
    verdict input: it adds its own rationale line naming both numbers, its own levers, and its own
    entry in the `fails` list that drives DECLINE. DSCR covers the lender and Year-1 cash flow
    covers the dollars; neither asks what the buyer's own cash earns, which is why a large down
    payment can clear both while the equity yield stays under 3%.
  * **`market` is what makes the cap-rate-spread test honour the target the user configured.**
    `run_financial_model` warns `"cap-rate spread below target"` against `market.cap_rate_spread_target`;
    pass the same block here and the thesis is judged against that number too. Omit it and the spread
    falls back to the module constant `MIN_SPREAD` (0.015) — which is why the kwarg is additive and no
    existing caller's verdict moved. Both orchestrators pass `inputs.market`; anything that builds a
    thesis outside them should too, or a report can print "spread below target" under **Warnings**
    while its own **Investment Thesis** says the spread meets target.
  * `spread_target_for(market: MarketAssumptions | None) -> float` exposes that resolution (configured
    target, else `MIN_SPREAD`) for callers that need to state the bar they were judged against.
  * **`market` also decides what the cap-rate-floor rationale line can honestly say.** The
    breach/clear decision always comes from the engine's `"cap rate below floor"` warning (this
    module re-does no comparison), but that warning's *absence* means "cleared" and "no floor
    configured" equally. So: with a market block, the line names both numbers like every sibling
    (`"Purchase cap rate is 6.35% (≥ the 5.00% floor you set)."`, or `(< the …)` on a breach);
    without one, a breach still prints as `"Purchase cap rate breaches the configured floor."` and
    a non-breach prints **nothing at all**. Silence on an unconfigured floor is pinned by
    `tests/integration/test_chief_strategist.py::test_no_floor_policy_makes_no_floor_claim`.
  * **Never LLM-authored, in any mode.** `ChiefStrategistAgent.run` (see `crewai_components.py`) always calls this function on the forecast — `AIREAL_LLM_MODE` does not change that; `_run_llm` was deleted from that class specifically so the verdict cannot bypass it.

### CrewAI components

* `ListingAnalystAgent` / `FinancialForecasterAgent` / `ChiefStrategistAgent` — Agent/Task shells used by `orchestrators/crewai_runner.py`. With `AIREAL_LLM_MODE` unset (the default), all three `run()` methods delegate to the same deterministic functions above for math parity — no `crew.kickoff()` is called. With `AIREAL_LLM_MODE` set **and** a provider key present (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `OPENROUTER_API_KEY`), **`ListingAnalystAgent.run()` calls a real `crew.kickoff()`** and an LLM authors the `ListingInsights` it returns (address, amenities, condition tags, defects, notes) — an *observation* layer, falling back to the deterministic `analyze_listing()` if the call or the JSON parse fails. Model-authored tags are stamped `ObservationProvenance(origin="llm", provider=<model name>, provider_kind="model")`; the deterministic fallback keeps its own text/CV provenance and is never relabelled as AI. `FinancialForecasterAgent` and `ChiefStrategistAgent` never call `kickoff()`, in any mode: the forecast math and the BUY/CONDITIONAL/DECLINE verdict are always deterministic. Honors `AIREAL_LLM_MODE` and `AIREAL_DEBUG`.

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
* Unit tests: `tests/unit/test_financial_forecaster*.py`.
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

_Last reconciled: 2026-08-05 against mission/2-wiring-gaps, task 3.2 (the cap-rate-floor rationale line now names the cap and the floor when `market` is supplied, and stays silent when no floor is configured). Earlier note: task 3.1b (deletion half) — removed
`PhotoTaggerAgent` (`agents/photo_tagger.py`) and `ListingIngestAgent` (`agents/listing_ingest.py`):
both were thin wrappers around deterministic core code with zero production callers and no model
seam (Roger's 2026-08-05 architecture ruling, `ROADMAP_TRACKER.md` §3b — "an agent exists only
where a model might one day enter"). `PhotoTaggerAgent` wrapped `CvTaggingOrchestrator` directly;
`ListingIngestAgent` wrapped `core.ingest.listing_ingest.run_listing_ingest_tool` and its
`_listing_to_insights_address_first` dropped every stated fact and hardcoded four fields empty.
Their imports, sections, and test-strategy bullets removed from this file; their tests deleted
(`tests/integration/test_photo_tagger_agent*.py`, 2 tests) — `tests/integration/
test_listing_ingest.py` stays, since it tests `core.ingest.listing_ingest` directly and never
touched the agent. Earlier note: 2026-08-05 @ 615aaaf (corrected — the previous stamp cited
`a626e9d`, a tree that does not contain the per-tag provenance content it claimed to have
reconciled: `ObservationProvenance` appears 0 times there and 6 times at HEAD. A provenance stamp
that names the wrong tree is the defect this file documents, applied to itself. Guardian M21.)
(Listing Analyst merges text + photo provenance ledgers; the CrewAI listing path stamps
model-authored tags `origin="llm"`). Earlier note: 2026-08-04 @ d18ee1a (Gate 2 VETO remediation:
Chief Strategist and CrewAI-components entries corrected — `ListingAnalystAgent.run()` does call a
real `crew.kickoff()` under `AIREAL_LLM_MODE`, but the verdict is never LLM-authored, in any mode;
added the full-suite coverage-gate note)._
