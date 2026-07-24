# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

_Status note (2026-07-24): section reconciled against main @ e4716df — the entries below reflect work actually merged since v0.1.0. Market Scenarios (opt-in scenarios overlay, Mission 1 Wave 2) now shipped._

### Added
- **Market Scenarios overlay** (Mission 1, Wave 2): opt-in `--scenarios` / `AIREAL_SCENARIOS` / `run.scenarios` flag wires `src/market` (snapshot → hypotheses → rejector) through the frozen finance engine; produces prior-weighted scenario outcomes (DSCR, CoC, cash flow, IRR). New modules: `src/market/adapter.py` (delta → FinancialInputs perturbation), `src/market/scenario_runner.py` (composition + deterministic weighted-percentile aggregation). New Pydantic models: `ScenarioAnalysis`, `ScenarioOutcome`, `ScenarioMetricBand`. Report section appended last with fixed verbatim honesty block, top-N-by-prior grid, prior-weighted bands (p25/p50/mean/min/max), caveats (priors-heuristic, cap-sensitivity, rate-shock, IO-period), and narrative-flag rendering. Default OFF → byte-identical to V2. Scenarios are deterministic what-ifs, not predictions/live data.
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

### Fixed
- **IRR solver domain robustness** (`src/core/finance/irr.py`): the Newton-Raphson step could converge to a spurious real root of the NPV polynomial where `1 + r < 0` (economically meaningless, e.g. a reported IRR of −179% for a deep-underwater deal whose true IRR is ≈ −18.6%). The solver now rejects any root ≤ −100% and hands off to the existing domain-bounded bisection, guaranteeing a valid IRR `> −100%` — matching the `irr_10yr >= -1.0` invariant already asserted in the engine tests. Surfaced by Mission 1 scenario corners; math verified against standard IRR/root-finding references.
- **Packaging**: added `[build-system]` + `[project]` metadata (name/version/requires-python) and namespace-aware setuptools package discovery, so `pip install -e .` now succeeds and the `ingest-listing` / `deal-report` / `deal-advisor` console scripts resolve. Runtime dependencies still come from the requirements files (matching CI).

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
