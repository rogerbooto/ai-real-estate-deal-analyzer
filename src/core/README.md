# core

## Purpose / Responsibilities

* Deterministic domain logic for underwriting, data preparation, media plumbing, and insights.
* Provides stable, testable primitives that agents/orchestrators compose. No network calls except controlled fetch/media helpers.
* Sub-areas:

  * **finance/**: underwriting engine (cash flows, IRR, metrics).
  * **normalize/**: listing text/HTML/address parsing into structured signals.
  * **cv/**: bridge from photo tags → `ListingInsights` (provider-agnostic).
  * **media/**: discovery, download pipeline, and media-derived insights.
  * **fetch/**: HTML fetching, robots, simple cache, typed errors.
  * **insights/**: synthesis of listing + CV into higher-level insights.
  * **strategy/**: rules that feed the investment thesis.

## Public APIs / Contracts

* **Imports (selected):**

  ```python
  # Finance
  from src.core.finance.engine import run_financial_model
  from src.core.finance.amortization import amortization_schedule
  from src.core.finance.irr import xirr

  # Normalize
  from src.core.normalize.listing_text import parse_listing_text
  from src.core.normalize.listing_html import extract_listing_from_html
  from src.core.normalize.address import normalize_address

  # CV bridge & insights
  from src.core.cv.bridge import merge_photo_tags
  from src.core.cv.photo_insights import tags_to_insights

  # Media & Fetch
  from src.core.media.downloader import download_media
  from src.core.media.html_finder import find_media_in_html
  from src.core.media.pipeline import media_pipeline
  from src.core.fetch.html_fetcher import fetch_html
  from src.core.fetch.robots import is_allowed

  # Insights & Strategy
  from src.core.insights.synthesis import synthesize_listing_insights
  from src.core.strategy.strategist import build_strategy
  ```

### Finance

* `run_financial_model(inputs: FinancialInputs) -> FinancialForecast`
  Main underwriting entrypoint; returns forecast with `YearBreakdown[]` and `PurchaseMetrics`.
* `amortization_schedule(principal, rate, years, *, io_years=0) -> list[dict]`
  Deterministic monthly schedule; supports interest-only phase before amortization.
* `irr(cashflows: list[tuple[datetime,date|str,float]]) -> float`
  Date-aware IRR used by engine; expects signed cash flows.

### Normalize

* `parse_listing_text(text: str) -> dict`
  Extracts bed/bath/parking/sqft/amenities from free text deterministically.
* `extract_listing_from_html(html: str) -> dict`
  Pulls the same signals from DOM text.
* `normalize_address(raw: str) -> dict`
  Canonicalizes street/city/province/postal if present.

### CV bridge & insights

* `merge_photo_tags(deterministic: dict, ai: dict|None) -> dict`
  Merges filename heuristics with AI tags; keeps strongest per (category,label).
* `tags_to_insights(tags: dict) -> ListingInsights`
  Converts tag dictionary to typed insights consumed by `agents/listing_analyst`.

### Media & Fetch

* `find_media_in_html(html: str) -> list[str]`
  Returns media URLs (images, floorplans, video thumbs) with simple dedupe.
* `download_media(urls: list[str], dest_dir: Path) -> list[Path]`
  Deterministic downloader with basic retry; returns local file paths.
* `media_pipeline(html: str, dest_dir: Path) -> dict`
  Finds → downloads → indexes media; returns manifest.
* `fetch_html(url: str, *, timeout_s: int = 15) -> str`
  Simple HTTP GET via requests-like interface (tests mock); raises typed errors.
* `is_allowed(url: str, user_agent: str) -> bool`
  Robots.txt check helper; conservative deny on parsing errors.

### Insights & Strategy

* `synthesize_listing_insights(text_signals: dict, photo_insights: ListingInsights) -> ListingInsights`
  Combines textual and visual cues (e.g., reno level, layout risk) deterministically.
* `build_strategy(forecast: FinancialForecast, insights: ListingInsights) -> dict`
  Rule-based levers and guardrails used by `agents/chief_strategist.py`.

## Usage Examples

### Finance: run model

```python
from src.core.finance.engine import run_financial_model
from src.schemas.models import FinancialInputs, OperatingExpenses, FinancingTerms

inputs = FinancialInputs(
    financing=FinancingTerms(purchase_price=300000, down_payment_rate=0.05,
                             interest_rate=0.045, amort_years=25, io_years=0,
                             mortgage_insurance_rate=0.04),
    opex=OperatingExpenses(insurance=1200, taxes=2600, repairs_maintenance=2000, management=1500),
    income={"gross_rent": 24000, "vacancy_rate": 0.05}
)
forecast = run_financial_model(inputs)
print(forecast.purchase.metrics.coc_return)
```

### Normalize + CV merge to insights

```python
from src.core.normalize.listing_text import parse_listing_text
from src.core.cv.bridge import merge_photo_tags
from src.core.cv.photo_insights import tags_to_insights

text = parse_listing_text("2BR + den, 1.5 bath, 900 sqft, parking, balcony")
merged = merge_photo_tags({"kitchen": {"modern": 0.8}}, {"bath": {"dated": 0.6}})
ins = tags_to_insights(merged)
```

### Media pipeline from HTML

```python
from pathlib import Path
from src.core.media.pipeline import media_pipeline

manifest = media_pipeline("<html>...<img src=\"/a.jpg\">...</html>", Path("./artifacts"))
print(manifest["images"])  # local paths
```

## Design Notes / Invariants

* **Determinism first**: all modules are pure or have controlled side effects (FS/network) behind narrow helpers.
* **Rates are fractions [0–1]**: engine expects fractional inputs (e.g., 0.05 for 5%).
* **IO → Amortization**: interest-only years precede amortization in schedules.
* **No hidden globals**: configuration flows via explicit parameters or higher layers (agents/orchestrators).
* **Stable ordering**: schedules, manifests, and merges use deterministic ordering for testability.
* **Error handling**: typed errors from fetch/media paths; conservative fallbacks (e.g., robots deny on error).

## Dependencies / Optional Providers

* Consumes types from [`../schemas/README.md`](../schemas/README.md).
* Can receive AI tags from `tools/vision` via the CV bridge, but operates without AI by design.
* Network/FS accesses are isolated in `fetch/` and `media/` for mocking in tests.

## Test Strategy

* Unit tests cover: amortization math, IRR, engine cash flows, normalization parsing, CV merges, media finder/downloader, fetch and robots, insights synthesis, strategy rules.
* Integration tests exercise end-to-end flow via orchestrators with deterministic inputs.
* Run examples:

  ```bash
  pytest -q tests/unit/test_finance_* tests/unit/test_core_* tests/integration/test_orchestrator_*.py
  ```

## Cross-links

* Back to [Main README](../README.md)
* Types: [`../schemas/README.md`](../schemas/README.md)
* Tools (vision/tagging & ingest): [`../tools/README.md`](../tools/README.md)
* Orchestrators (E2E flow): [`../orchestrators/README.md`](../orchestrators/README.md)
* Agents (wrappers): [`../agents/README.md`](../agents/README.md)
* Reports (rendering): [`../reports/README.md`](../reports/README.md)
* Market (scenario utilities): [`../market/README.md`](../market/README.md)

## Change Log Notes (scoped)

* Finance engine stabilized with IO→Amortization support and XIRR.
* CV bridge introduced to unify deterministic and AI tags.
* Media pipeline hardened with deterministic manifests and retrying downloader.
