# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- (placeholder) Add Streamlit demo UI.
- (placeholder) Add live data ingestion for comps.
- (placeholder) Add OpenTelemetry traces for agent pipeline.

### Changed
- (placeholder) Refactor financial model module into smaller units.

### Fixed
- (placeholder) Resolve rounding edge case in amortization schedule.

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
