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
  * **intelligence/**: deal fusion, composite scoring (`DealIntelligence`). `narrative_builder.py`
    (`build_narrative_md`) and `report_builder.py` (`write_markdown_report`) also live here — as of
    2026-08-05 (Mission 2 task 3.1b, OPD-3 "wire-first") both are reachable in production, via
    `deal-advisor`'s `--narrative` flag (one Markdown narrative file per ranked deal;
    `write_markdown_report` calls `build_narrative_md` internally). `md_to_html` remains
    reachable only from `tests/core/intelligence/test_report_builder.py` — no CLI renders HTML.
  * **advisor/**: multi-deal ranking, portfolio summary, risk flags. `advisor/scenarios.py`
    ("scenario what-ifs", `summarize_scenarios`) is reachable in production as of 2026-08-05
    (Mission 2 task 3.1b) via `deal-advisor`'s `--what-if` flag, which attaches each deal's
    down-payment/rate/renovation-budget what-ifs to both the JSON output and the `--markdown`
    summary. It remains a deliberately approximate heuristic (documented in its own docstring) —
    it does not re-run the finance engine, unlike `src/market`'s scenario overlay (see
    `src/market/README.md`), which does.
  * *(**strategy/** is gone. It held one function, `form_thesis` — a second rule-based
    thesis-formation implementation that no production code ever called. Mission 2 task 3.1a
    reconciled it into the live path and deleted it, per OPD-1's binding reconcile→review→delete
    sequence. Both of its guardrails that the live strategist lacked now live in
    `agents/chief_strategist.py`: judging the cap-rate spread against the user's
    `market.cap_rate_spread_target` instead of a hardcoded constant (`synthesize_thesis` takes an
    optional `market=` for exactly that), and the `coc < 0.03` Year-1 cash-on-cash floor, now
    `MIN_COC_Y1`. Its remaining rules were already present and stricter in the live module — which
    also has an IRR floor `form_thesis` never had — and its `coc < 0 AND dscr < 1.0` DECLINE
    shortcut is subsumed by `num_fails >= 3` once the CoC floor is live. The architecture ruling
    behind the deletion is in `docs/plans/ROADMAP_TRACKER.md` §3b: an agent exists only where a
    model might one day enter; everything deterministic is called directly in `core/`. Verdict
    formation is a judgment with an LLM-shaped seam, so it belongs to the agent.)*
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

  # Insights, Intelligence, Advisor
  from src.core.insights.synthesis import synthesize_listing_insights
  from src.core.insights.provenance import attach, text_observation, detection_observation
  from src.core.intelligence.deal_fusion import fuse_deal_intelligence, DealIntelligence
  from src.core.intelligence.scoring import compute_composite_score
  from src.core.advisor.recommender import rank_deals
  from src.core.advisor.portfolio import portfolio_summary
  from src.core.advisor.risk import compute_risk_flags
  ```

### Finance

* `run_financial_model(fi: FinancialInputs, *, horizon_years: int = 10, insights: ListingInsights | None = None) -> FinancialForecast`
  Main underwriting entrypoint; returns forecast with `YearBreakdown[]`, `PurchaseMetrics`, optional `RefiEvent`, and warnings. Insight-aware **income** modifiers only fire when `income_is_estimated` is set (read at `engine.py:98`). Insight-aware **OPEX** modifiers (`"old roof"` → +$300/yr reserves, `"water stain"` → +$200/yr repairs & maintenance, `_apply_insight_modifiers` in `engine.py:64-70`) are unconditional in code but **unreachable from the deterministic pipeline**: on the text-ingestion path, condition tags come from `_CONDITION_KEYWORDS`'s free-string list (`src/core/ingest/listing_parser.py:37-45`, which has `"new roof"`, not `"old roof"`), and defects come from the closed `ConditionTag`/`DefectLabel` enums (`src/schemas/labels.py`), where `"water stain"` is normalized to `DefectLabel.water_leak_suspected` before the engine's literal string check ever sees it (`labels.py:241`). **They are reachable via `--engine crewai` with `AIREAL_LLM_MODE=1`**: `ListingAnalystAgent`'s LLM-authored `ListingInsights` (`src/agents/crewai_components.py`) are parsed straight from model JSON with no normalization pass, so an LLM that writes the literal strings reaches the engine unnormalized. They also fire if a caller hand-constructs a `ListingInsights` with those exact strings directly (e.g. a unit test). See `docs/plans/MISSION_2_SPRINT_TRACKER.md` (Gate 2 record, findings V2/C2) and `core/reports/README.md`'s "Adjustments Applied" section, which the same mechanism affects.
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
  Closed-set amenities/defects detection with per-provider JSON cache (`.cache/cv/providers/<provider>/<behaviour>-<capability-digest>/<sha>.json`). Providers: `local` (heuristics), `vision` / `llm` (deterministic stubs), `onnx` (user-registered local model via `register_onnx_provider`). The cache path carries the provider's declared capabilities as well as `_CACHE_BEHAVIOUR_VERSION`, so registering a different detector cannot be served a pre-registration answer.
* `register_provider(name, fn, *, detects)` / `provider_capabilities(name) -> frozenset[str]`
  A provider **declares the label vocabulary it can emit**. `register_onnx_provider`'s `labels_path` is that declaration for a real model. Declarations are keyed by the function object, not the slot name, so a slot rebound at runtime reports the new function's vocabulary with no table to update — the same identity rule `provider_kind` uses. An undeclared provider covers **nothing** (silence is not evidence that something looked).

#### Filename suggestions: SUGGEST vs CONFIRM

A file name may **suggest** a label; only a detector that actually looked may **confirm** it. `runner._augment_from_filename` classifies each match against `provider_capabilities`, producing one of three `DetectedLabel.source` values (see `amenities_defects.DetectionSource`):

| provider covers the label? | provider reported it? | `source` | confidence |
| --- | --- | --- | --- |
| yes | yes | `filename_confirmed` | `CV_CONFIRMATION_WEIGHT × cv + FILENAME_CORROBORATION_BONUS` (0.7 · cv + 0.3) |
| yes | no — a genuine disagreement | `filename_contested` | `0.30` |
| no — nothing could look | n/a | `filename_unconfirmed` | **none at all** |

The two weights are a tunable split summing to 1.0 (`runner.CV_CONFIRMATION_WEIGHT` / `FILENAME_CORROBORATION_BONUS`); the 0.30 is a flat corroboration credit for a *binary* filename match, not "we are 30% sure". Registering a provider that declares the label moves it from unconfirmed to contested with no code change.

**Neither an unconfirmed nor a contested claim may reach a number.** Both are kept out of `ListingInsights.amenities/condition_tags/defects` — the three lists `finance/engine._apply_insight_modifiers` reads — and surfaced to the reader through `ListingInsights.notes` plus `PhotoInsights.unconfirmed_hint_counts` / `contested_hint_counts` instead.

The **0.30 is not what makes the contested case safe**, and an earlier version of this table said it was, on the grounds that it sits below the 0.6 bar `_parking_summary` applies. That bar does not gate every route: `amenity_counts` → `synthesis` → the literal tag `"parking"` → `_apply_insight_modifiers` reads **membership, not confidence**, so a blank grey `garage.jpg` with a detector that covers `parking_garage` and reported nothing moved Y1 cash flow by $1,105.80 (G2-N1). What makes it safe is that the tag never arrives, enforced in two independent places:

* `photo_insights._split_measured_and_hints` keeps contested entries out of `amenity_counts` / `defect_counts` / `image_detections`, so `image_detections` means exactly "what a detector reported";
* `synthesis._amenities_from` refuses to ship an amenity tag whose only support is a claim a covering detector rejected — the guard that still holds if a *different* producer builds `PhotoInsights` without filtering.

The marker itself now survives validation: `DetectedLabelModel.source` (see `schemas.models.DetectionSource`) is a declared field. It previously was not, and `extra="ignore"` deleted it at the boundary, which is why `synthesis` stamped contested records `origin="cv_provider", provider_kind="model"` — crediting a detector with a finding it had explicitly rejected (G2-N2). A consumer cannot decline to vouch for evidence it was never handed.

### Media & Fetch

* `find_media_candidates(...)` / `collect_media(...)`
  Discover media in listing HTML and orchestrate the download into a `MediaBundle`.
* `download_media(...)`
  Filtered, deduplicating downloader (icon/logo prefilter, size postfilter, sha256 hashing).
* `analyze_media(assets) -> MediaInsights`
  Counts, byte totals, dimension/orientation stats, exact-duplicate detection, hero guess.
* `enrich_with_intelligence(bundle, insights, enable=False)`
  Opt-in perceptual-hash near-duplicate detection, quality scoring, palette extraction, and hero ranking.

### Insights, Intelligence, Advisor

* `synthesize_listing_insights(listing: ListingNormalized, photos: PhotoInsights) -> ListingInsights`
  Deterministically combines textual and visual cues (address resolution, amenities, condition tags, notes), and
  populates `ListingInsights.observations` with per-tag provenance.
* `core.insights.provenance` — builders for that ledger: `text_observation` / `filename_observation` /
  `detection_observation` / `derived_observation` / `unattributed_observation`, plus `attach`,
  `dedupe_and_sort`, `retain_recorded_tags`, `stamp_uniform_origin`. Pure and deterministic; they never
  *infer* an origin — a producer that cannot attribute a tag records `origin="unknown"` rather than guessing,
  and a keyword match is never given a fabricated confidence.
* `fuse_deal_intelligence(...) -> DealIntelligence`
  Fuses listing, finance summary, media, and photo insights into a scored deal object.
* `compute_composite_score(...)` — weighted scoring components (see `intelligence/types.py`).
* `rank_deals(deals)` (`core.advisor.recommender`) / `portfolio_summary(deals)` (`core.advisor.portfolio`) /
  `compute_risk_flags(...)` (`core.advisor.risk`) — advisor layer used by the `deal-advisor` CLI and
  `core.intelligence.deal_fusion`. Import the submodules directly; `core.advisor.__init__` is a bare
  package marker (Mission 2 Wave 3 removed its dead lazy-wrapper re-exports — every caller already
  imported the submodules, so the facade had zero callers).
* Thesis formation lives **outside** `core/`, at `agents.chief_strategist.synthesize_thesis`. There is
  no second implementation: `core/strategy/form_thesis` was deleted in Mission 2 task 3.1a after its
  guardrails were reconciled into that function (see the `strategy/` note under Structure above).

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
  pytest -q --no-cov tests/core
  ```

  `--no-cov` disables coverage for this subset run only; the project's ≥80% coverage gate
  (`pytest.ini`, `--cov-fail-under=80`) is enforced against the **full** `pytest` suite, not any
  one subset command.

## Cross-links

* Back to [Main README](../../README.md)
* Types: [`../schemas/README.md`](../schemas/README.md)
* CLI entry points: [`../cli/README.md`](../cli/README.md)
* Orchestrators (E2E flow): [`../orchestrators/README.md`](../orchestrators/README.md)
* Agents (wrappers): [`../agents/README.md`](../agents/README.md)
* Reports (rendering): [`reports/README.md`](reports/README.md)
* Market (scenario utilities, not yet wired): [`../market/README.md`](../market/README.md)

---

_Last reconciled: 2026-08-05 against mission/2-wiring-gaps (task 3.1b, the wiring half): the
`narrative_builder.py`/`report_builder.py` and `advisor/scenarios.py` bullets above now describe
the live `deal-advisor --narrative`/`--what-if` callers instead of "no production caller" — see
`src/cli/README.md` for the flags and `docs/plans/MISSION_2_SPRINT_TRACKER.md` row 3.1b for the
RED-on-revert proof. Earlier note: 2026-08-05 against mission/2-wiring-gaps @ 8f31eaa + uncommitted
Wave 3 work. **Task 3.1a** (that stamp's author): `core/strategy/` deleted after its guardrails
were reconciled into `agents/chief_strategist`; `form_thesis` removed from Structure, the import
block and the API list. The same working tree also carries **task 3.1b**'s `core/advisor/__init__.py`
facade removal, reflected in the advisor bullets above but stamped by that task, not this one — two
tasks edited this file concurrently and neither stamp covers the other's hunks. Earlier note: 2026-08-05 @ 615aaaf (corrected — the previous stamp cited `a626e9d`, a tree that does not contain the per-tag provenance content it claimed to have reconciled: `ObservationProvenance` appears 0 times there and 6 times at HEAD. A provenance stamp that names the wrong tree is the defect this file documents, applied to itself. Guardian M21.) (documented the new `core/insights/provenance` builders and `synthesize_listing_insights`' provenance output). Earlier note: 2026-08-04 @ d18ee1a (Gate 2 VETO remediation: narrowed the OPEX-modifier honesty note — unreachable from the deterministic pipeline (text-path condition tags come from the free-string `_CONDITION_KEYWORDS` list, not only the closed enum) but reachable via `--engine crewai` with `AIREAL_LLM_MODE=1`; dropped the dangling "charter finding M10" citation. Earlier note: 2026-08-03 @ 74c985c, corrected the claim that insight-aware OPEX modifiers work on real data; clarified `strategist.py`/`form_thesis`, `narrative_builder.py`/`report_builder.py`, and `advisor/scenarios.py` are dead code with no production caller today, pending Mission 2 Wave 3 disposition)._
