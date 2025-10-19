# tools

## Purpose / Responsibilities

* Operational utilities and entry points for ingestion, parsing, and computer vision tagging.
* Provides the deterministic backbone for listing data and media enrichment pipelines.
* Exposes both CLI-friendly functions and callable APIs used by agents and orchestrators.

## Public APIs / Contracts

* **Imports:**

  ```python
  from src.tools.listing_ingest import ingest_listing
  from src.tools.listing_parser import parse_listing
  from src.tools.cv_tagging import tag_photos

  # Vision providers
  from src.tools.vision.provider_base import VisionProvider
  from src.tools.vision.openai_provider import OpenAIVisionProvider
  from src.tools.vision.mock_provider import MockVisionProvider
  ```

### Listing Ingestion & Parsing

* `ingest_listing(path_or_url: str, *, save_dir: Path | None = None) -> dict`
  Deterministic ingestion pipeline that reads a local file or remote URL, normalizes structure, and extracts listing fields.
* `parse_listing(html: str | Path) -> dict`
  HTML-based parser used by ingestion or orchestrators; deterministic output schema aligned with `FinancialInputs` and listing metadata.

### Computer Vision Tagging

* `tag_photos(photo_paths: list[str|Path], *, use_ai: bool | None = None) -> dict`
  Batch-first photo tagging orchestrator. Returns a mapping of `{category: {label: confidence}}`. If AI is disabled, uses deterministic filename heuristics.
* **Vision Providers:**

  * `VisionProvider` (abstract): defines `analyze_photos(photo_paths)`.
  * `MockVisionProvider`: returns predictable tags for tests or offline mode.
  * `OpenAIVisionProvider`: connects to OpenAI Vision API when `AIREAL_USE_VISION=1` and `AIREAL_VISION_PROVIDER=openai`.

## Usage Examples

### 1) Ingest a listing

```python
from src.tools.listing_ingest import ingest_listing

data = ingest_listing("https://example.com/listing.html", save_dir="./artifacts")
print(data.keys())  # e.g., ['metadata', 'photos', 'text']
```

### 2) Tag photos deterministically or via AI

```python
from src.tools.cv_tagging import tag_photos

# Deterministic (mock) mode
result = tag_photos(["img1.jpg", "img2.jpg"], use_ai=False)

# AI mode (requires OPENAI_API_KEY and AIREAL_USE_VISION=1)
ai_result = tag_photos(["img1.jpg"], use_ai=True)
print(ai_result)
```

## Design Notes / Invariants

* **Batch-first:** All tagging runs operate in batch mode; results merged by strongest confidence.
* **Determinism:** With `use_ai=False` or `AIREAL_USE_VISION=0`, outputs are stable and reproducible.
* **AI Providers:**

  * Selected by `AIREAL_VISION_PROVIDER` env var (`mock` or `openai`).
  * Timeouts (`AIREAL_VISION_TIMEOUT_S`) and retries (`AIREAL_VISION_MAX_RETRIES`) enforced by the orchestrator layer.
* **Error Handling:**

  * Provider failures trigger retry logic before fallback to deterministic mode.
  * Invalid image paths skipped with warnings; batch continues.

## Dependencies / Optional Providers

* Requires [`../core/README.md`](../core/README.md) for normalization and CV bridge usage.
* Optional AI provider (`OpenAIVisionProvider`) activated when `AIREAL_USE_VISION=1`.
* Supported environment variables:

  * `AIREAL_USE_VISION`
  * `AIREAL_VISION_PROVIDER`
  * `AIREAL_PHOTO_AGENT`
  * `AIREAL_VISION_MODEL`
  * `AIREAL_VISION_TIMEOUT_S`
  * `AIREAL_VISION_MAX_RETRIES`
  * `OPENAI_API_KEY`

## Test Strategy

* Unit tests:

  * `tests/unit/test_tools_cv_tagging.py` — tag merging, confidence, deterministic output.
  * `tests/unit/test_vision_mock_provider.py` — ensures repeatability.
  * `tests/unit/test_vision_openai_provider.py` — timeout and API call stubs.
  * `tests/integration/test_ingest_pipeline.py` — end-to-end listing ingestion.
* Run:

  ```bash
  pytest -q tests/unit/test_tools_* tests/unit/test_vision_* tests/integration/test_ingest_pipeline.py
  ```

## Cross-links

* Back to [Main README](../README.md)
* Core logic: [`../core/README.md`](../core/README.md)
* Schemas: [`../schemas/README.md`](../schemas/README.md)
* Agents: [`../agents/README.md`](../agents/README.md)
* Orchestrators: [`../orchestrators/README.md`](../orchestrators/README.md)
* Reports: [`../reports/README.md`](../reports/README.md)
* Market: [`../market/README.md`](../market/README.md)

## Change Log Notes (scoped)

* Added `tag_photos` with AI/deterministic hybrid.
* Unified ingestion pipeline (`ingest_listing`) for file/URL inputs.
* Mock/OpenAI vision providers standardized under `tools/vision`.
