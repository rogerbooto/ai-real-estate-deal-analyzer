# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

_Status note (2026-07-23): section reconciled against main @ e4716df — the entries below reflect work actually merged since v0.1.0._

### Added
- **Listing ingestion pipeline** (`src/core/ingest`, `ingest-listing` CLI): file/URL ingestion with `FetchPolicy` (network opt-in, robots.txt respect, caching, optional JS rendering).
- **Media pipeline** (`src/core/media`): HTML media discovery → filtered download → `MediaBundle` manifests; **media intelligence** (opt-in perceptual-hash near-duplicate detection, quality scoring, palette extraction, hero-image ranking).
- **CV tagging v2** (`src/core/cv`): closed-set amenities/defects ontology, provider seams (`local`/`vision`/`llm` deterministic stubs, user-registered ONNX), per-provider JSON caching; consolidated under `CvTaggingOrchestrator` (removed legacy `tools/vision`).
- **Address parsing** (`src/core/normalize/address.py`): US/CA parsing via `usaddress` + schema.org/meta/DOM hints; state/province code selection.
- **Deal intelligence & advisor** (`src/core/intelligence`, `src/core/advisor`, `deal-advisor` CLI): deal fusion, composite scoring, narrative/report builders, multi-deal ranking, portfolio summary, risk flags, scenario what-ifs; CSV/Markdown exports.
- **Report CLI** (`deal-report`): renders Markdown reports from JSON artifacts, including a Media Overview section.
- **CrewAI engine seam** (`src/orchestrators/crewai_runner.py`): `--engine crewai` with fail-fast env validation; currently delegates to deterministic math (parity shell — `crew.kickoff()` not yet called).

### Changed
- Report generator extended with media overview, baseline/stress/NOI-based valuation tables, and env-driven overrides (`AIREAL_CAP_DRIFT_BPS`, `AIREAL_APPRECIATION_PCT`, `AIREAL_STRESS_ADJ`).
- Vision provider interface refactored; tests reorganized under `tests/core/*`, `tests/integration/*`.
- Coverage gate set to 80% over `src/core`, `src/schemas`, `src/market` (`pytest.ini` + `.coveragerc`).

### Known Gaps
- `src/market` hypothesis/rejector modules remain unwired from the main pipeline.
- `pyproject.toml` lacks `[project]` metadata, so `pip install -e .` and the declared console scripts do not work yet (use `python -m src.cli.*`).

---

## [v0.1.0] - 2025-09-23
### Added
- **End-to-end demo pipeline** (Listing Analyst → Financial Forecaster → Chief Strategist) with sample inputs.
- **Demo artifacts**: generated Markdown/PDF investment report (see Release assets).
- **Unit tests** (pytest) and **coverage** (pytest-cov + Codecov).
- **CI pipeline** (GitHub Actions): lint (ruff), type checks (mypy), tests, coverage upload, artifact upload.
- **Repo badges**: CI, Codecov, Python version, License, Release.
- **Architecture docs**: Mermaid flow, sequence diagrams, and debt-service model.
- **Configs**: `ruff.toml`, `mypy.ini`, `codecov.yml`, `pyproject.toml`.
- **Contributing & Licensing**: CONTRIBUTING, LICENSE, commercial license, NOTICE, CITATION.

### Known Limitations
- Inputs are local (no live scraping) in V1.
- No public UI yet; CLI-first demo.

[Unreleased]: https://github.com/rogerbooto/ai-real-estate-deal-analyzer/compare/v0.1.0...HEAD
[v0.1.0]: https://github.com/rogerbooto/ai-real-estate-deal-analyzer/releases/tag/v0.1.0
