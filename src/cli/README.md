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
| `--url` / `--file` | — | Listing source (exactly one). |
| `--photos` | — | Optional local photo directory for photo insights. |
| `--out-cache` | `data/cache` | Cache directory for fetches/artifacts. |
| `--online` | `0` | Allow network fetch (robots.txt respected; safe fetch policy). |
| `--ai` | `0` | Enable AI photo-insight path (falls back to deterministic stubs). |
| `--render` | `0` | Render JS via headless browser before parsing. |
| `--download-media` | `1` | Discover & download listing media. |
| `--max-media` | `64` | Max media assets to fetch. |
| `--media-intel` | `0` | Enable media intelligence (perceptual hash, quality, palette, hero ranking). |
| `--media-kinds` | all | Comma-separated filter: `image,video,floorplan,document,other`. |

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

* `--forecast` (required): `FinancialForecast` JSON.
* `--insights`, `--thesis`, `--media-insights` (optional): `ListingInsights`, `InvestmentThesis`, `MediaInsights` JSON.
* `--title`: override the report H1.
* Delegates to `src.core.reports.generator.write_report()`.

### 3) `advisor_cli` — multi-deal ranking & portfolio summary

```bash
# One or more deal-bundle directories (each: listing.(txt|md|html), photos/, finance.json, optional inputs.json)
python -m src.cli.advisor_cli --dir data/sample_listings/47_perrot_shediac --out out/advisor_output.json --markdown

# Config JSONs or globs also work
python -m src.cli.advisor_cli --files deal_a.json deal_b.json --export-csv
python -m src.cli.advisor_cli --glob "data/sample_listings/*" --save-artifacts --debug
```

* Inputs: `--dir`, `--files`, `--glob` (URL mode is intentionally rejected — a finance mapping is required per deal).
* Outputs: ranked deals + portfolio summary JSON (`--out`), optional CSVs (`--export-csv`), Markdown summary (`--markdown`), and per-deal artifacts (`--save-artifacts`).
* Delegates to `src.core.intelligence.deal_fusion.fuse_deal_intelligence()`, `src.core.advisor.recommender.rank_deals()`, and `src.core.advisor.portfolio.portfolio_summary()`.

## Design Notes / Invariants

* **Deterministic-first:** every CLI runs fully offline by default; network (`--online`), rendering (`--render`), and AI (`--ai`) are explicit opt-ins.
* **Typed contracts:** all JSON artifacts round-trip through Pydantic models in `src/schemas/models.py`.
* **No hidden state:** outputs are written where you point them; caches live under `--out-cache`.

## Test Strategy

* `tests/integration/test_advisor_cli_dir_mode.py` — advisor directory discovery & ranking.
* `tests/integration/test_report_cli_minimal.py`, `test_report_cli_media.py`, `test_report_cli_errors.py` — report CLI paths.
* `tests/integration/test_listing_ingest.py`, `tests/listing/test_ingest.py` — ingestion flows.

Run:

```bash
pytest -q tests/integration
```

## Cross-links

* Back to [Main README](../../README.md)
* Core logic: [`../core/README.md`](../core/README.md)
* Reports: [`../core/reports/README.md`](../core/reports/README.md)
* Schemas: [`../schemas/README.md`](../schemas/README.md)

---

_Last reconciled: 2026-07-23 against main @ e4716df._
