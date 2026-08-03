# cli

## Purpose / Responsibilities

* User-facing **command-line entry points** for the three operational workflows:

  * **`ingest_cli.py`** — ingest a listing (local file or URL) into structured artifacts (normalized listing, photo insights, media bundle).
  * **`report_cli.py`** — render a Markdown investment report from JSON artifacts (forecast, insights, thesis, media insights).
  * **`advisor_cli.py`** — analyze **multiple deals**, rank them with the deal-intelligence scoring stack, and summarize a portfolio.
* Thin argument-parsing layers; all real logic lives in `src/core/*` (ingest, reports, advisor, intelligence).

> **Packaging note:** `pyproject.toml` declares `ingest-listing`, `deal-report`, and `deal-advisor` console scripts. After `pip install -e .` (with the requirements files installed for runtime deps) these are available on `PATH` directly, e.g. `ingest-listing --help`. Running the CLIs as modules — `python -m src.cli.<name>` — also still works.

## Commands

### 1) `ingest_cli` — listing ingestion

```bash
python -m src.cli.ingest_cli --file listing.html --photos ./photos
python -m src.cli.ingest_cli --url https://example.com/listing --online 1 --render 0
```

Key flags (all deterministic-first; network and AI are opt-in):

| Flag | Default | Meaning |
| --- | --- | --- |
| `--url` / `--file` | — | Listing source. If both are given, `--url` wins (the fetch path is used and `--file` is ignored). |
| `--photos` | — | Optional local photo directory for photo insights. |
| `--out-cache` | `data/cache` | Cache directory for fetches/artifacts. |
| `--online` | `0` | Allow network fetch when `--url` is used (robots.txt respected; safe fetch policy). |
| `--ai` | `0` | Switches the photo-insight detection provider from `local` to `vision` (`use_ai=True` → `core.cv.build_photo_insights`). **This does change the output**: `image_detections`, `amenity_counts`, `detections_total`, `version` and `provenance` all differ from the default path, and the derived fields (`amenities` booleans, `parking` summary) can move with them. It is **not** a model call — the `vision` slot currently holds a hand-written threshold over image brightness, colour spread and aspect ratio, so its artifacts are stamped `version="vision-stub-v1"` and `provenance.provider_kind="heuristic_stub"`. Treat its labels as a placeholder, not as observations. The flag exists so a real classifier (fine-tuned ViT, a hosted API, or a user-supplied model) can be registered behind that seam; `provider_kind` reports `"model"` once one is. |
| `--render` | `0` | Render JS via headless browser before parsing (requires `--url`). |
| `--pretty` | `1` | Console-formatting knob only: pretty-prints the full listing/insights/photos JSON to stdout. Does **not** affect what is written to `--out-cache` or whether a screenshot is saved (see `--save-screenshot`, below — these two used to be silently tied together). |
| `--save-screenshot` | `1` | Save a render screenshot to disk when `--render` is used (`FetchPolicy.save_screenshot`). Independent of `--pretty`. |
| `--download-media` | `1` | Discover & download listing media. **Only has an effect when there is an HTML source to scan** (`--url`, with or without `--render`) — `collect_media` needs a URL/snapshot to find `<img>`/`og:image`/JSON-LD references, and the local-folder walker (`core.media.local.collect_local_assets`, used by the orchestrators) is not wired into `ingest_listing`. `--file` alone therefore yields an empty media bundle; the CLI prints a note to stderr explaining this, and `--photos` remains the way to get photo insights from a local folder. |
| `--max-media` | `64` | Max media assets to fetch. Same `--file`-mode caveat as `--download-media`. |
| `--media-intel` | `0` | Enable media intelligence (perceptual hash, quality, palette, hero ranking). Same `--file`-mode caveat as `--download-media`. |
| `--media-kinds` | all | Comma-separated filter: `image,video,floorplan,document,other`. An invalid value is a clean argparse usage error (exit 2), not a traceback. Same `--file`-mode caveat as `--download-media`. |

The console output always prints a one-line summary of `result.media`/`result.media_insights` (when present) and of the computed `result.insights`/`result.photos` — the pipeline's synthesized outputs are not silently discarded. `--pretty 1` additionally dumps the full JSON of the listing (including the structured `address_structure` block, when parsed), insights, and photos.

Delegates to `src.core.ingest.listing_ingest.ingest_listing()` and returns an `IngestResult` (see `src/schemas/models.py`).

### 2) `report_cli` — report rendering

```bash
python -m src.cli.report_cli \
  --forecast data/examples/forecast.json \
  --insights data/examples/insights.json \
  --thesis data/examples/thesis.json \
  --media-insights data/examples/media.json \
  --out out/investment_report.md
```

The example above uses only the JSON files committed under `data/examples/`, so it runs as
written. `--media-report` and `--provenance` (below) take artifacts produced by an actual run —
there are no committed examples of them, because a checked-in `provenance.json` would describe a
run that never happened.

* `--forecast` (required): `FinancialForecast` JSON. A missing, unreadable, or syntactically-invalid file fails with a clear `SystemExit` message naming the path, not a raw `FileNotFoundError`/`json.JSONDecodeError` traceback. A syntactically-valid file that doesn't match the schema still surfaces pydantic's own `ValidationError` (e.g. missing `purchase`/`years`), since that message is already actionable.
* `--insights`, `--thesis`, `--media-insights` (optional): `ListingInsights`, `InvestmentThesis`, `MediaInsights` JSON.
* `--media-report` (optional): `MediaReport` JSON (`src/core/reports/report_models.py`) — renders the **Photo Coverage** section. Distinct from `--media-insights`, which drives the file-level **Media Overview** section.
* `--provenance` (optional): `RunProvenance` JSON (`src/schemas/models.py`) — renders the pipeline-facts rows of the **Run Provenance** appendix. This CLI only renders already-computed JSON artifacts; it does not itself pick an orchestration engine, run Market Scenarios, or run vision tagging, so it cannot truthfully *construct* a `RunProvenance` describing those choices. Point it at the provenance file emitted by the run that produced the other artifacts (e.g. `main.py`'s) rather than fabricating one — an absent `--provenance` simply omits those rows (the appendix header and valuation-knob rows still render, since those apply to every run).
* `--title`: override the report H1.
* Delegates to `src.core.reports.generator.write_report()`.

**`--insights` recognizability guard:** every field on `ListingInsights` is optional (absent facts
are legitimate — this project never fabricates listing data), which means `{}` or a JSON object
with no relation to the schema (e.g. `{"totally": "unrelated"}`) used to validate cleanly and
silently produce a report with an empty listing section. `--insights` now rejects JSON that shares
no key with any real `ListingInsights` field, while a genuinely sparse-but-real file (e.g. just
`{"address": "..."}`) is untouched. This gate is scoped to `--insights` only: the other optional
artifacts (`--thesis`, `--media-insights`, `--media-report`, `--provenance`) each have at least one
*required* field on their model, so unrelated JSON already fails there via pydantic's own
`ValidationError` — the same gate would only replace one clear error with a different one, for no
behavioral gain.

### 3) `advisor_cli` — multi-deal ranking & portfolio summary

```bash
# One or more deal-bundle directories (each: listing.(txt|md|html), photos/, finance.json, optional inputs.json)
python -m src.cli.advisor_cli --dir data/sample_listings/47_perrot_shediac --out out/advisor_output.json --markdown

# Config JSONs or globs also work -- see data/examples/advisor_deal_config.json for a
# working config-JSON example (listing_path/photos_dir/finance_inputs_path/optional title)
python -m src.cli.advisor_cli --files data/examples/advisor_deal_config.json --export-csv
python -m src.cli.advisor_cli --glob "data/sample_listings/*" --save-artifacts --debug
```

* Inputs: `--dir`, `--files`, `--glob` (URL mode is intentionally rejected — a finance mapping is required per deal). `--files` accepts bundle directories (auto-discovery) or config JSONs; a config JSON missing `listing_path`/`photos_dir`/`finance_inputs_path` raises a clear error pointing at `data/examples/advisor_deal_config.json`.
* Outputs: ranked deals + portfolio summary JSON (`--out`), optional CSVs (`--export-csv`), Markdown summary (`--markdown`), and per-deal artifacts (`--save-artifacts`).
* `--debug` additionally prints the full ranked/portfolio JSON payload to stdout (the compact table is always printed regardless of this flag).
* `--markdown` writes `<out-stem>.md` next to `--out`. If `--out` already ends in `.md` (so that path would collide with the JSON artifact), it writes `<out-stem>_report.md` instead and prints a note — the JSON at `--out` is never overwritten.
* Delegates to `src.core.intelligence.deal_fusion.fuse_deal_intelligence()`, `src.core.advisor.recommender.rank_deals()`, and `src.core.advisor.portfolio.portfolio_summary()`.

## Design Notes / Invariants

* **Deterministic-first:** every CLI runs fully offline by default; network (`--online`), rendering (`--render`), and AI (`--ai`) are explicit opt-ins.
* **Typed contracts:** all JSON artifacts round-trip through Pydantic models in `src/schemas/models.py`.
* **No hidden state:** outputs are written where you point them; caches live under `--out-cache`.

## Test Strategy

* `tests/integration/test_advisor_cli_dir_mode.py` — advisor directory discovery & ranking.
* `tests/integration/test_advisor_cli_flags.py` — advisor CLI flag honesty: `--debug` payload dump, `--markdown` not clobbering `--out` when it ends in `.md`, and the `--files` missing-key error citing a real, working example.
* `tests/integration/test_report_cli_minimal.py`, `test_report_cli_media.py`, `test_report_cli_errors.py`, `test_report_cli_media_report_and_provenance.py` — report CLI paths.
* `tests/integration/test_report_cli_bad_input_guards.py` — `report_cli` input-honesty checks: `--insights` rejects `{}`/unrelated JSON but still accepts a sparse-but-real file; `--forecast` fails cleanly (not a raw traceback) on a missing file, malformed JSON, or a directory path; the recognized-field gate stays scoped to `ListingInsights` (a schema-invalid `--forecast` still raises pydantic's own `ValidationError`).
* `tests/integration/test_listing_ingest.py`, `tests/listing/test_ingest.py` — ingestion flows.
* `tests/integration/test_ingest_cli.py` — `ingest_cli` CLI honesty checks: printed insights/photos, the `--file`-without-`--url` media-flag note, `--ai`/`--pretty`/`--save-screenshot` help text, the `--media-kinds` usage error, and the `address_structure` dump.

Run:

```bash
pytest -q --no-cov tests/integration
```

## Cross-links

* Back to [Main README](../../README.md)
* Core logic: [`../core/README.md`](../core/README.md)
* Reports: [`../core/reports/README.md`](../core/reports/README.md)
* Schemas: [`../schemas/README.md`](../schemas/README.md)

---

_Last reconciled: 2026-07-23 against main @ e4716df._
