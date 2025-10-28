# tools

## Purpose / Responsibilities

* Operational utilities and entry points for **ingestion** and **parsing**.
* Works alongside the **v2 CV stack** in `src/core/cv` for all computer-vision tagging.
* Exposes CLI-friendly functions and callable APIs used by agents and orchestrators.

## Public APIs / Contracts

**Imports:**

```python
from src.tools.listing_ingest import ingest_listing
from src.tools.listing_parser import parse_listing

# CV v2 (generic labels + amenities/defects)
from src.core.cv.runner import tag_images, tag_amenities_and_defects
```

### Listing Ingestion & Parsing

* `ingest_listing(path_or_url: str, *, save_dir: Path | None = None) -> dict`
  Deterministic ingestion pipeline that reads a local file or remote URL, normalizes structure, and extracts listing fields.

* `parse_listing(html: str | Path) -> dict`
  HTML-based parser used by ingestion or orchestrators; deterministic output schema aligned with `FinancialInputs` and listing metadata.

### Computer Vision (v2)

* `tag_images(photo_paths: list[str|Path], *, use_ai: bool | None = None) -> dict[str, list[str]]`
  Minimal deterministic **generic room/material tagging**, keyed by image **sha256**.

* `tag_amenities_and_defects(assets: list[Path|MediaAsset], *, provider: str, use_cache: bool = True) -> dict[str, list[DetectedLabel]]`
  Closed-set **amenities/defects** detection keyed by sha256, with thumbnailing and per-provider JSON cache.
  Providers (all offline/deterministic stubs unless you register ONNX):

  * `local` — fast heuristics
  * `vision` — deterministic “vision-stub”
  * `llm` — deterministic “caption-stub” (temp=0)
  * `onnx` — user-registered local model (see `register_onnx_provider` in `src/core/cv/amenities_defects.py`)

> Confidence gating and ontology enforcement live in `src/core/cv/amenities_defects.py`.

## Usage Examples

### 1) Ingest a listing

```python
from src.tools.listing_ingest import ingest_listing

data = ingest_listing("https://example.com/listing.html", save_dir="./artifacts")
print(data.keys())  # e.g., ['metadata', 'photos', 'text']
```

### 2) Tag photos (generic) and detect amenities/defects

```python
from pathlib import Path
from src.core.cv.runner import tag_images, tag_amenities_and_defects

photos = [Path("img1.jpg"), Path("img2.jpg")]

generic = tag_images(photos)  # {sha256: ["kitchen", "tile_floor", ...]}

dets = tag_amenities_and_defects(photos, provider="local", use_cache=True)
# {sha256: [{"name":"parking_garage","category":"amenity","confidence":0.72,...}, ...]}
```

### 3) (Optional) Register a custom ONNX provider

```python
from src.core.cv.amenities_defects import register_onnx_provider

register_onnx_provider(
    model_path="my_model.onnx",
    labels_path="labels.json",   # {"labels":["parking_garage","ev_charger",...]}
    # input_name="input_0",      # optional
    # image_size=(224,224),      # optional
)
# then:
dets = tag_amenities_and_defects(photos, provider="onnx")
```

## Design Notes / Invariants

* **Deterministic-first:** default paths are offline and reproducible.
* **Closed-set CV:** All amenity/defect outputs are constrained to the ontology with per-label confidence cutoffs.
* **Caching:** Per-provider JSON cache at `.cache/cv/providers/<provider>/<sha>.json`.
* **Thumbnails:** Max side ≤ 768 px for performance; ONNX provider rescales internally.

## Environment Variables (honored by orchestrators/agents)

* `AIREAL_USE_VISION` — enable AI paths in higher layers (if used)
* `AIREAL_PHOTO_AGENT` — toggle agent vs. direct runner call
* `AIREDEAL_CACHE_DIR` — override cache root (defaults to `./.cache/cv`)

## Test Strategy

* Unit:

  * `tests/core/cv/test_amenities_defects*.py` — ontology, providers, ONNX registration (mocked), cutoff gating
  * `tests/core/cv/test_runner*.py` — sha keys, cache layout, generic labels
* Orchestrators:

  * `tests/orchestrators/test_cv_tagging_orchestrator_basic.py` — path normalization & delegation

Run:

```bash
pytest -q
```

## Change Log Notes (scoped)

* **Removed `tools/vision` module** and v1 `cv_tagging.py`.
* Consolidated all CV functionality under **v2**: `src/core/cv/runner.py` & `src/core/cv/amenities_defects.py`.
* Added optional ONNX provider registration for custom local models.
