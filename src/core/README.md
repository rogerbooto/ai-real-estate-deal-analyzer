# core

## Purpose / Responsibilities

* Deterministic domain logic for underwriting, ingestion, data preparation, media plumbing, and deal intelligence.
* Provides stable, testable primitives that agents/orchestrators compose. No network calls except controlled fetch/media helpers.
* Sub-areas:

  * **finance/**: underwriting engine (cash flows, amortization, IRR, metrics) + finance-summary adapters.
  * **ingest/**: end-to-end listing ingestion (file or URL → normalized listing + media + photo insights).
  * **normalize/**: listing text/HTML/address/title parsing into structured signals.
  * **cv/**: deterministic CV tagging v2 — generic room/material labels + closed-set amenities/defects with provider seams.
  * **media/**: media discovery, filtered download, bundle manifests, and media intelligence (phash/quality/palette/hero).
  * **fetch/**: HTML fetching, robots.txt policy, caching, typed errors.
  * **insights/**: synthesis of listing + photo insights into `ListingInsights`.
  * **intelligence/**: deal fusion, composite scoring, narrative + report builders (`DealIntelligence`).
  * **advisor/**: multi-deal ranking, portfolio summary, risk flags, scenario what-ifs.
  * **strategy/**: rule-based thesis formation.
  * **reports/**: Markdown report generation (see [`reports/README.md`](reports/README.md)).
  * **utils/**: markdown/serialization helpers.

## Public APIs / Contracts

* **Imports (selected, verified):**

  ```python
  # Finance
  from src.core.finance.engine import run_financial_model
  from src.core.finance.amortization import amortization_schedule, amortization_payment
  from src.core.finance.irr import irr
  from src.core.finance.adapters import finance_summary_from_json

  # Ingest & Normalize
  from src.core.ingest.listing_ingest import ingest_listing
  from src.core.normalize import parse_any_to_normalized
  from src.core.normalize.listing_html import parse_listing_from_tree
  from src.core.normalize.address import parse_address, extract_address

  # CV v2
  from src.core.cv.runner import tag_images, tag_amenities_and_defects
  from src.core.cv.amenities_defects import register_onnx_provider, detect_from_image

  # Media & Fetch
  from src.core.media.pipeline import find_media_candidates, collect_media
  from src.core.media.downloader import download_media
  from src.core.media.insights import analyze_media, enrich_with_intelligence
  from src.core.media.intelligence import compute_phash, compute_quality, extract_palette, rank_hero

  # Insights, Intelligence, Advisor, Strategy
  from src.core.insights.synthesis import synthesize_listing_insights
  from src.core.intelligence.deal_fusion import fuse_deal_intelligence, DealIntelligence
  from src.core.intelligence.scoring import compute_composite_score
  from src.core.advisor import rank_deals, portfolio_summary, compute_risk_flags
  from src.core.strategy.strategist import form_thesis
  ```

### Finance

* `run_financial_model(fi: FinancialInputs, *, horizon_years: int = 10, insights: ListingInsights | None = None) -> FinancialForecast`
  Main underwriting entrypoint; returns forecast with `YearBreakdown[]`, `PurchaseMetrics`, optional `RefiEvent`, and warnings. Insight-aware modifiers only adjust income when `income_is_estimated` is set.
* `amortization_schedule(principal, rate, amort_years, *, io_years=0, horizon_years) -> list[YearDebt]`
  Deterministic annual schedule; interest-only years precede amortization; padded to horizon.
* `irr(cash_flows, *, max_iter=100, tol=1e-6) -> float | None`
  Date-aware IRR (Newton + bisection fallback); expects signed cash flows.

### Ingest & Normalize

* `ingest_listing(...) -> IngestResult`
  File-or-URL ingestion honoring a `FetchPolicy` (network opt-in, robots respected, caching, optional JS render); produces normalized listing, media bundle, and photo insights.
* `parse_any_to_normalized(doc) -> ListingNormalized`
  Single door for text/HTML documents.
* `parse_address(text, soup=None) -> AddressResult | None`
  US/CA address parsing via `usaddress` plus schema.org/meta/DOM hints.

### CV v2

* `tag_images(paths, *, use_ai=None, return_schema=False) -> dict`
  Deterministic generic room/material tagging keyed by image sha256.
* `tag_amenities_and_defects(assets, *, provider, use_cache=True) -> dict[str, list[DetectedLabel]]`
  Closed-set amenities/defects detection with per-provider JSON cache (`.cache/cv/providers/<provider>/<sha>.json`). Providers: `local` (heuristics), `vision` / `llm` (deterministic stubs), `onnx` (user-registered local model via `register_onnx_provider`).

### Media & Fetch

* `find_media_candidates(...)` / `collect_media(...)`
  Discover media in listing HTML and orchestrate the download into a `MediaBundle`.
* `download_media(...)`
  Filtered, deduplicating downloader (icon/logo prefilter, size postfilter, sha256 hashing).
* `analyze_media(assets) -> MediaInsights`
  Counts, byte totals, dimension/orientation stats, exact-duplicate detection, hero guess.
* `enrich_with_intelligence(bundle, insights, enable=False)`
  Opt-in perceptual-hash near-duplicate detection, quality scoring, palette extraction, and hero ranking.

### Insights, Intelligence, Advisor, Strategy

* `synthesize_listing_insights(listing: ListingNormalized, photos: PhotoInsights) -> ListingInsights`
  Deterministically combines textual and visual cues (address resolution, amenities, condition tags, notes).
* `fuse_deal_intelligence(...) -> DealIntelligence`
  Fuses listing, finance summary, media, and photo insights into a scored deal object.
* `compute_composite_score(...)` — weighted scoring components (see `intelligence/types.py`).
* `rank_deals(deals)` / `portfolio_summary(deals)` / `compute_risk_flags(...)` — advisor layer used by the `deal-advisor` CLI.
* `form_thesis(ff: FinancialForecast, mkt: MarketAssumptions) -> InvestmentThesis`
  Rule-based thesis used by the Chief Strategist.

## Design Notes / Invariants

* **Determinism first**: all modules are pure or have controlled side effects (FS/network) behind narrow helpers; AI providers default to deterministic stubs.
* **Rates are fractions [0–1]**: the engine expects fractional inputs (e.g., 0.05 for 5%).
* **IO → Amortization**: interest-only years precede amortization in schedules.
* **No hidden globals**: configuration flows via explicit parameters or higher layers (agents/orchestrators); env flags are read at the edges.
* **Stable ordering**: schedules, manifests, tag outputs, and rankings use deterministic ordering for testability.
* **Error handling**: typed errors from fetch/media paths; conservative fallbacks (e.g., robots deny on error).

## Dependencies / Optional Providers

* Consumes types from [`../schemas/README.md`](../schemas/README.md).
* AI vision/LLM providers are seams — deterministic stubs unless a user registers an ONNX model.

  **ONNX provider (optional):** The `register_onnx_provider()` function allows you to bring your own trained ONNX classification model to the amenities/defects detector. This is a **Python-API-only, opt-in feature** — it is never invoked by any CLI command, only through direct Python code. To use it:
  1. Install `onnxruntime` separately: `pip install onnxruntime`
  2. Call `register_onnx_provider(model_path, labels_path)` once during your app initialization (not built into the default pipeline)
  3. Pass `provider="onnx"` to `tag_amenities_and_defects()` or `detect_from_image()`

  If `onnxruntime` is not installed, calling `register_onnx_provider()` raises a clear error message. The package is intentionally not declared in `requirements.txt` because it is an opt-in dependency for advanced users only.

* Network/FS access is isolated in `fetch/` and `media/` for mocking in tests.

## Test Strategy

* Unit tests under `tests/core/` cover: finance math, normalization/address parsing, CV providers and caching, media finder/downloader/intelligence, insights synthesis, intelligence scoring, advisor ranking, report rendering.
* Integration tests (`tests/integration/`) exercise end-to-end flows via orchestrators and CLIs.
* Run:

  ```bash
  pytest -q tests/core
  ```

## Cross-links

* Back to [Main README](../../README.md)
* Types: [`../schemas/README.md`](../schemas/README.md)
* CLI entry points: [`../cli/README.md`](../cli/README.md)
* Orchestrators (E2E flow): [`../orchestrators/README.md`](../orchestrators/README.md)
* Agents (wrappers): [`../agents/README.md`](../agents/README.md)
* Reports (rendering): [`reports/README.md`](reports/README.md)
* Market (scenario utilities, not yet wired): [`../market/README.md`](../market/README.md)

---

_Last reconciled: 2026-07-23 against main @ e4716df (including uncommitted working-tree refactors of `media/insights.py` and `media/intelligence.py`)._
