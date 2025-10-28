# agents

## Purpose / Responsibilities

* High-level wrappers orchestrating specialized modules from `core/` and `tools/`.
* Each agent performs a distinct role in the deterministic pipeline or LLM-enabled orchestration.
* Designed to be composable and independently testable.

## Public APIs / Contracts

* **Imports:**

  ```python
  from src.agents.listing_analyst import analyze_listing
  from src.agents.financial_forecaster import forecast_financials
  from src.agents.chief_strategist import synthesize_thesis
  from src.agents.photo_tagger import tag_listing_photos
  from src.agents.listing_ingest import ingest_listing_agent
  ```

### Listing Analyst

* `analyze_listing(raw_listing: dict | str, *, use_ai: bool | None = None) -> dict`

  * Normalizes textual and visual listing data.
  * Calls `core.normalize` and `core.cv` to extract structure + visual tags.
  * When `AIREAL_USE_VISION=1`, delegates photo tagging to `PhotoTaggerAgent`.

### Financial Forecaster

* `forecast_financials(inputs: FinancialInputs) -> FinancialForecast`

  * Deterministic wrapper around `core.finance.engine.run_financial_model()`.
  * Enforces data validation and guarantees consistent schema for downstream strategy agents.

### Chief Strategist

* `synthesize_thesis(forecast: FinancialForecast, insights: ListingInsights) -> InvestmentThesis`

  * Generates qualitative reasoning based on forecasted metrics and listing insights.
  * Rule-based in V1; may incorporate LLM reasoning in V2 (when `AIREAL_LLM_MODE=1`).

### Photo Tagger

* `tag_listing_photos(photo_paths: list[str|Path], *, use_ai: bool | None = None) -> dict`

  * Delegates to `src.core.cv.runner.tag_images()`.
  * Acts as a policy layer controlled by `AIREAL_PHOTO_AGENT`.

### Listing Ingest Agent

* `ingest_listing_agent(path_or_url: str) -> dict`

  * Wraps `tools.listing_ingest.ingest_listing()` and adds logging/debug handling.
  * Used by orchestrators as the first step before analysis.

## Usage Examples

### 1) Listing analysis

```python
from src.agents.listing_analyst import analyze_listing

data = analyze_listing("https://example.com/listing.html", use_ai=True)
print(data["insights"])  # normalized listing + photo tags
```

### 2) Forecast and thesis

```python
from src.agents.financial_forecaster import forecast_financials
from src.agents.chief_strategist import synthesize_thesis
from src.schemas.models import FinancialInputs

inputs = FinancialInputs.from_json_path("./examples/sample_inputs.json")
forecast = forecast_financials(inputs)
thesis = synthesize_thesis(forecast, insights={})
print(thesis.summary())
```

## Design Notes / Invariants

* **Deterministic-first:** all agents default to reproducible behavior.
* **Feature Flags:**

  * `AIREAL_USE_VISION`: enables AI photo tagging.
  * `AIREAL_PHOTO_AGENT`: toggles between policy layer and direct call.
  * `AIREAL_LLM_MODE`: activates CrewAI reasoning for strategist agent.
* **Composition:** agents are composable; orchestrators simply call them in sequence.
* **Inputs/Outputs:** each agent consumes and returns typed Pydantic models or dicts compatible with `schemas.models`.
* **Isolation:** no agent persists state; all results are returned upward to orchestrators.

## Dependencies / Optional Providers

* Depends on:

  * [`../core/README.md`](../core/README.md) for finance, CV, normalization, insights, and strategy logic.
  * [`../tools/README.md`](../tools/README.md) for ingestion and vision providers.
  * [`../schemas/README.md`](../schemas/README.md) for model definitions.
* Optional LLM layer via `AIREAL_LLM_MODE=1` (CrewAI orchestrator).

## Test Strategy

* Unit tests:

  * `tests/unit/test_agent_listing_analyst.py` — normalization + photo merge.
  * `tests/unit/test_agent_financial_forecaster.py` — model output and determinism.
  * `tests/unit/test_agent_chief_strategist.py` — rule-based logic and expected thesis outputs.
  * `tests/unit/test_agent_photo_tagger.py` — deterministic vs AI tagging.
  * `tests/unit/test_agent_listing_ingest.py` — ingestion flow.
* Run:

  ```bash
  pytest -q tests/unit/test_agent_*.py
  ```

## Cross-links

* Back to [Main README](../README.md)
* Types: [`../schemas/README.md`](../schemas/README.md)
* Core Logic: [`../core/README.md`](../core/README.md)
* Tools: [`../tools/README.md`](../tools/README.md)
* Orchestrators: [`../orchestrators/README.md`](../orchestrators/README.md)
* Reports: [`../reports/README.md`](../reports/README.md)
* Market (future scenario inputs): [`../market/README.md`](../market/README.md)

## Change Log Notes (scoped)

* Introduced PhotoTaggerAgent policy layer (`AIREAL_PHOTO_AGENT`).
* Chief Strategist agent extended for LLM integration (`AIREAL_LLM_MODE`).
* Listing Analyst unified deterministic + AI insights path.
* Financial Forecaster wrapped core engine for stable API.
