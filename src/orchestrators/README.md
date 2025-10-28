# orchestrators

## Purpose / Responsibilities

* Coordinate multi-step execution flows combining agents, tools, and core modules.
* Serve as the **entry point for deterministic orchestration** in V1 and as the seam for CrewAI-based orchestration in V2.
* Expose functions and classes that can run end-to-end investment analyses from a listing input to a generated report.

## Public APIs / Contracts

* **Imports:**

  ```python
  from src.orchestrators.crew import run_orchestration
  from src.orchestrators.cv_tagging_orchestrator import run_cv_tagging
  from src.orchestrators.crewai_runner import run_crewai_orchestration
  ```

### Deterministic Orchestrator (V1)

* `run_orchestration(inputs: FinancialInputs | dict, *, debug: bool = False) -> dict`
  Runs the **full deterministic pipeline**:

  1. Parses input (`inputs/inputs.py`).
  2. Calls `agents/listing_analyst.py` → listing normalization + photo insights.
  3. Invokes `agents/financial_forecaster.py` → forecast metrics.
  4. Invokes `agents/chief_strategist.py` → thesis generation.
  5. Sends outputs to `reports/generator.py` → markdown summary.

  Returns a dictionary or structured report depending on flags.

### Computer Vision Orchestrator

* `run_cv_tagging(photo_paths: list[str|Path], *, use_ai: bool | None = None) -> dict`
  Wrapper over `tools/cv_tagging.tag_images()` with built-in retry, logging, and optional provider selection.
  Used when `AIREAL_PHOTO_AGENT=0` to bypass agent layer.

### CrewAI Orchestrator (V2)

* `run_crewai_orchestration(inputs: AppInputs, *, model: str = "gpt-5") -> dict`
  Optional LLM-assisted orchestration pipeline.

  * Activated when `AIREAL_LLM_MODE=1`.
  * Uses `CREWAI_MODEL` for reasoning (default: `gpt-5`).
  * Integrates `crewai_components.py` agents for planning and validation.

## Usage Examples

### 1) Deterministic run

```python
from src.orchestrators.crew import run_orchestration
from src.schemas.models import FinancialInputs

inputs = FinancialInputs.from_json_path("./examples/sample_inputs.json")
result = run_orchestration(inputs, debug=True)
print(result["thesis"]["summary"])
```

### 2) CV tagging only

```python
from src.orchestrators.cv_tagging_orchestrator import run_cv_tagging

out = run_cv_tagging(["photo1.jpg", "photo2.jpg"], use_ai=False)
print(out)
```

### 3) CrewAI orchestration (LLM-enabled)

```python
from src.orchestrators.crewai_runner import run_crewai_orchestration
from src.schemas.models import AppInputs

inputs = AppInputs.from_json_path("./examples/app_inputs.json")
result = run_crewai_orchestration(inputs)
```

## Design Notes / Invariants

* **V1 = Deterministic Path:** no network calls beyond optional CV provider.
* **V2 = CrewAI Path:** enabled via `AIREAL_LLM_MODE=1`; uses structured `AppInputs`.
* **Logging:** controlled by `AIREAL_DEBUG` flag; verbose if enabled.
* **Model Selection:** `CREWAI_MODEL` defines LLM backbone; defaults to `gpt-5`.
* **Graceful Fallbacks:**

  * If `AIREAL_USE_VISION=0`, vision step skipped.
  * If `AIREAL_PHOTO_AGENT=0`, uses `cv_tagging_orchestrator` directly.
  * Missing media or parsing errors log warnings but continue.
* **Output Consistency:** ensures all orchestrations return dictionary objects compatible with `reports/generator.py`.

## Dependencies / Optional Providers

* Core logic: [`../core/README.md`](../core/README.md)
* Agents: [`../agents/README.md`](../agents/README.md)
* Tools (vision, ingest): [`../tools/README.md`](../tools/README.md)
* Reports (output): [`../reports/README.md`](../reports/README.md)
* Market (V2 optional): [`../market/README.md`](../market/README.md)
* Schemas: [`../schemas/README.md`](../schemas/README.md)

Supported environment variables:

* `AIREAL_LLM_MODE`
* `AIREAL_DEBUG`
* `CREWAI_MODEL`
* `AIREAL_USE_VISION`
* `AIREAL_PHOTO_AGENT`

## Test Strategy

* Unit & Integration tests:

  * `tests/integration/test_orchestrator_crew.py` — deterministic pipeline.
  * `tests/integration/test_orchestrator_cv_tagging.py` — CV flow.
  * `tests/integration/test_orchestrator_crewai_runner.py` — LLM seam tests (mocked API).
* Run:

  ```bash
  pytest -q tests/integration/test_orchestrator_*.py
  ```

## Cross-links

* Back to [Main README](../README.md)
* Types: [`../schemas/README.md`](../schemas/README.md)
* Agents: [`../agents/README.md`](../agents/README.md)
* Core Logic: [`../core/README.md`](../core/README.md)
* Tools: [`../tools/README.md`](../tools/README.md)
* Reports: [`../reports/README.md`](../reports/README.md)
* Market (future integration): [`../market/README.md`](../market/README.md)

## Change Log Notes (scoped)

* V1 orchestrator finalized under `orchestrators/crew.py`.
* Path header corrected from `src/orchestrator/crew.py` to `src/orchestrators/crew.py`.
* Added `run_crewai_orchestration` as LLM seam for V2 experimentation.
* CV orchestrator standardized for batch-first tagging and retries.
