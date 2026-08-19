# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **Creating a deterministic agent no longer requires an OpenAI key** (`src/agents/crewai_components.py`). All three agent classes built a crewai `Agent` shell unconditionally in `__init__`; newer `crewai` (1.x) backfills a default model when `llm=None` and validates `OPENAI_API_KEY` at `Agent` **construction**, not at call time, so merely instantiating `FinancialForecasterAgent` or `ChiefStrategistAgent` — neither of which has any code path that ever calls `kickoff()` — began requiring a key. Locally invisible (a `.env` supplies one), so CI (no key, and `crewai>=0.28.0` with no ceiling resolving `1.15.11`) went red on tests whose whole premise is that no model is involved. `ListingAnalystAgent` now builds its shell lazily — a property, reached only from `_run_llm()` — and `FinancialForecasterAgent`/`ChiefStrategistAgent` build no shell at all.

### Changed
- **Dependencies locked.** Two hash-pinned lockfiles: **`requirements.lock`** (runtime only, so someone who just wants to run the tool does not also install `pytest`/`ruff`/`mypy`) and **`requirements-dev.lock`** (runtime + dev tooling). CI installs the dev lock (`pip install -r requirements-dev.lock`); regenerate both with `uv pip compile` — see CONTRIBUTING, and regenerate them together, since updating one alone leaves the two disagreeing about a shared package instead of resolving the loose ranges in `requirements.txt`/`requirements-dev.txt` fresh on every run, so a green suite on one machine means the same thing on another. `crewai` is now ceilinged at `crewai>=0.28.0,<1.0.0` — the previously-unbounded range is what let CI resolve `1.15.11` against a developer machine still on `0.193.2`, the 0.x → 1.x jump that caused the agent-construction regression above. `onnxruntime>=1.16.0,<2.0.0` is now declared directly: it is imported by `core/cv/amenities_defects.py`'s registered ONNX provider but previously arrived only as a transitive dependency of `crewai`, so downgrading or dropping the agent framework would have silently taken the ONNX CV seam with it.

## [v0.3.0] - 2026-08-05

**The V3 generation, released.** `main.py` now announces V3 — it had been printing "V2" since
before the Market Scenarios overlay shipped on 2026-07-24, so the banner was a generation behind
the code. The README roadmap already recorded V3 as shipped; this closes the gap between what the
program says and what it is, which is the same class of drift Mission 2 was chartered to remove.

Versioned `0.3.0` rather than `3.0.0`: the V-numbers are **product generations** documented in the
README roadmap, not semver majors. The package stays pre-1.0 because it is not published and the
schema is still moving — claiming a stable major would assert an API freeze that is not true.
`CITATION.cff` said `1.0.0` while `pyproject.toml` said `0.1.0`; the citation file predates the
0.1.0 release and was wrong. Both now read `0.3.0`.

_Status note (2026-07-24): section reconciled against main @ e4716df — the entries below reflect work actually merged since v0.1.0. Market Scenarios (opt-in scenarios overlay, Mission 1 Wave 2) now shipped._

_Status note (2026-08-03, Mission 2 Wave 2 reachability audit — does not rewrite the entries below):
the "Deal intelligence & advisor" bullet's "narrative/report builders" and "scenario what-ifs" are
narrated as shipped alongside the rest of that feature set. Per Mission 2's reachability analysis
(`docs/plans/MISSION_2_wiring_gaps.md`, finding T4, re-verified 2026-08-03 @ 74c985c):
`src/core/intelligence/narrative_builder.py` and `report_builder.py` exist and are unit-tested, but
have zero production callers (only reachable from `tests/core/intelligence/`); `src/core/advisor/scenarios.py`
has zero callers of any kind, production or test. Neither is reachable from `main.py`, any `src/cli/*`
entry point, or any orchestrator today. Mission 2 Wave 3 (OPD-3, "wire-first") will either wire each
into a live path or delete it as un-wireable; this note will be updated once that lands. The rest of
that bullet (deal fusion, composite scoring, multi-deal ranking, portfolio summary, risk flags,
CSV/Markdown exports) is unaffected — those are live and reachable from the `deal-advisor` CLI._

_Status note (2026-08-05, Mission 2 Wave 3 task 3.1b, OPD-3 "wire-first" — superseded by the Gate 3
note directly below; kept for the record of what this task actually did before Gate 3 pulled part
of it): wired `narrative_builder.build_narrative_md` / `report_builder.write_markdown_report` into
a new `deal-advisor --narrative` flag and `advisor/scenarios.py`'s `summarize_scenarios` into a new
`--what-if` flag. Same task also wired `src/market/regional_income.py` into
`deal-advisor --regional-income`, and replaced `advisor_cli.py`'s hand-rolled `--markdown`/
`--save-artifacts` internals with `src/core/utils/markdown.py` / `src/core/utils/serialize.py`._

_Status note (2026-08-05, Mission 2 Gate 3 remediation — corrects the note directly above; does not
rewrite the entries below it): the founder-proxy blocked `--what-if` and `--narrative` at Gate 3 and
both are now **removed**, not shipped. `--what-if` rendered a fabricated `irr_est` — base IRR plus a
clamped ±10pp proxy from invented coefficients (`(dp1-dp0)*(price/1000)*0.4`,
`(r0-r1)*(price/1000)*1.2`, no amortization anywhere) computed against a down-payment-rate fallback
(`0.25`) that did not match the sample deal's real rate (`0.05`) — and its own returned `"note":
"Approximate scenario; does not re-run engine."` never reached the rendered page. `--narrative`
duplicated `deal-report`'s output with strictly less information and printed `IRR: 0.12` where every
other surface in the project renders `12.29%`. `src/core/advisor/scenarios.py`,
`src/core/intelligence/narrative_builder.py`, and `src/core/intelligence/report_builder.py` are
deleted; see **Removed**, below. `deal-advisor --regional-income` (`src/market/regional_income.py`)
is kept: its median/p25/p75 are real (`statistics.median`/`numpy.percentile` over the supplied
comps), but its `str_multiplier` (a hardcoded 1.5x STR uplift gated by a policy hook whose entire
body was `return True`, in a province that regulates short-term rentals) and `turnover_cost` (an
uncited "median rent × 0.5" rule of thumb, rendered beside real percentiles in identical formatting)
no longer reach any `--out`/`--markdown`/console output; `str_multiplier` is no longer computed at
all. `turnover_cost` remains a required field on `RegionalIncomeTable` — dropping it needs a schema
change, which Gate 3 remediation deliberately left for a follow-up decision rather than editing
`src/schemas/models.py` unilaterally (that file is additive-only by this project's convention).
`--markdown`/`--save-artifacts` switching to `src/core/utils/markdown.py`/`serialize.py` is
unaffected by this note and remains as described above. If engine-backed what-ifs are wanted, the
bar is `src/market/scenario_runner.py`: it perturbs `FinancialInputs` and re-runs
`run_financial_model`, rather than approximating outside the engine._

_Status note (2026-08-04, Mission 2 Gate 2 VETO remediation — does not rewrite the entry below):
the "CrewAI engine seam" bullet's "`crew.kickoff()` not yet called" is now false as a blanket
statement, as of `5e85836`. With `AIREAL_LLM_MODE` unset (the default), the claim still holds — the
seam is a parity shell delegating to deterministic math. With `AIREAL_LLM_MODE` set **and** a
provider key present, `ListingAnalystAgent` now calls a real `crew.kickoff()` (`src/agents/crewai_components.py:382`)
and an LLM authors the `ListingInsights` observations (condition tags, defects, amenities), which
reach the forecast through the deterministic insight modifiers — so an LLM run can move the money
numbers that flow from those observations. **The verdict cannot be LLM-authored in any mode**:
`ChiefStrategistAgent.run` always calls `chief_strategist.synthesize_thesis` on the forecast
(`_run_llm` was deleted from that class); `FinancialForecasterAgent` never calls `kickoff()` either,
so the arithmetic stays exact and reproducible. See `src/orchestrators/crewai_runner.py`'s module
docstring and `src/agents/crewai_components.py`'s module docstring for the full account, and
`docs/plans/MISSION_2_SPRINT_TRACKER.md` (Gate 2 record, finding V3) for how this was found._

### Added
- **The verdict now looks at the return on your own cash.** `PurchaseMetrics.coc` — Year-1 cash-on-cash, `Year-1 cash flow / acquisition cash` — was computed on every run and read by no decision. `chief_strategist` gained `MIN_COC_Y1 = 0.03`, a tunable Year-1 cash-on-cash floor alongside `MIN_DSCR_Y1` / `MIN_SPREAD` / `MIN_IRR_10YR`: it prints its own numbered rationale line ("Cash-on-cash (Y1) is weak at 2.94% (< 3.00%)."), contributes its own levers, and counts as a failure toward DECLINE. It sees what its neighbours cannot — DSCR asks whether the lender is covered and the Year-1 cash-flow rule asks whether the deal is above water in dollars, so a deal bought with a large down payment can clear both while the buyer's equity earns under 3%. Inclusive at the bar (exactly 3.00% passes), matching every other guardrail in the module. Ported from the deleted `core/strategy/strategist.py` (see **Removed**).
- **Market Scenarios overlay** (Mission 1, Wave 2): opt-in `--scenarios` / `AIREAL_SCENARIOS` / `run.scenarios` flag wires `src/market` (snapshot → hypotheses → rejector) through the frozen finance engine; produces prior-weighted scenario outcomes (DSCR, CoC, cash flow, IRR). New modules: `src/market/adapter.py` (delta → FinancialInputs perturbation), `src/market/scenario_runner.py` (composition + deterministic weighted-percentile aggregation). New Pydantic models: `ScenarioAnalysis`, `ScenarioOutcome`, `ScenarioMetricBand`. Report section appended last with fixed verbatim honesty block, top-N-by-prior grid, prior-weighted bands (p25/p50/mean/min/max), caveats (priors-heuristic, cap-sensitivity, rate-shock, IO-period), and narrative-flag rendering. Default OFF → byte-identical to V2. Scenarios are deterministic what-ifs, not predictions/live data.
- **Listing ingestion pipeline** (`src/core/ingest`, `ingest-listing` CLI): file/URL ingestion with `FetchPolicy` (network opt-in, robots.txt respect, caching, optional JS rendering).
- **Media pipeline** (`src/core/media`): HTML media discovery → filtered download → `MediaBundle` manifests; **media intelligence** (opt-in perceptual-hash near-duplicate detection, quality scoring, palette extraction, hero-image ranking).
- **CV tagging v2** (`src/core/cv`): closed-set amenities/defects ontology, provider seams (`local`/`vision`/`llm` deterministic stubs, user-registered ONNX), per-provider JSON caching; consolidated under `CvTaggingOrchestrator` (removed legacy `tools/vision`).
- **Address parsing** (`src/core/normalize/address.py`): US/CA parsing via `usaddress` + schema.org/meta/DOM hints; state/province code selection.
- **Deal intelligence & advisor** (`src/core/intelligence`, `src/core/advisor`, `deal-advisor` CLI): deal fusion, composite scoring, multi-deal ranking, portfolio summary, risk flags, a regional-income (median/p25/p75 rent) market sanity-check; CSV/Markdown exports. (Narrative/report builders and scenario what-ifs were attempted and removed at Gate 3 — see **Removed**.)
- **Report CLI** (`deal-report`): renders Markdown reports from JSON artifacts, including a Media Overview section.
- **CrewAI engine seam** (`src/orchestrators/crewai_runner.py`): `--engine crewai` with fail-fast env validation; currently delegates to deterministic math (parity shell — `crew.kickoff()` not yet called).

### Changed
- **Reports gained an "Appendix — Run Provenance" section**, closing the reproducibility gap that the `.env` rewrite could only half-address. Every report now records the settings that shaped its numbers — cap-rate drift, baseline appreciation, stress basis adjustment, orchestration engine, scenarios flag, AI-vision flag, and the inputs file — each named alongside the variable that controls it. Two reports that disagree can now be diffed on this block first. The three valuation knobs are read from the *same accessors that produced the valuation tables*, so the block cannot claim a setting the figures did not use; tests assert a claimed drift is visible in the NOI table and a claimed appreciation in the baseline heading. New additive `RunProvenance` schema; `vision_enabled()` exposes the value the CV layer captured at import rather than re-reading the env, which would let a report claim a mode the run never used.
- **Reports gained an "Appendix — Definitions" section.** Every acronym the report uses (GSI, GOI, OPEX, NOI, DSCR, CoC, IRR, LTV, cap rate, equity multiple, terminal equity, acquisition cash outlay, IO, $/sq ft) is defined **as the engine computes it**, with the implemented formula rather than the textbook one. Terms in the body link to the appendix through explicit HTML anchors so the links survive PDF export; a test fails the build if any link lacks a definition. The `Debt Service` entry discloses that amortization uses **annual** periods, which runs ~1.2% above a monthly-pay loan of the same rate and term — previously undocumented anywhere a report reader would see it.
- **Verdict `PASS` renamed to `DECLINE`** (`src/agents/chief_strategist.py`, `src/core/strategy/strategist.py` — the second file has since been deleted, see **Removed**; the path is kept here because that is where the rename landed at the time). `PASS` meant *pass on the deal* — walk away — but reads as approval, so a report recommending rejection was headed by a word most people take as a green light. `BUY` / `CONDITIONAL` are unchanged. Nothing branches on the verdict string; it is display-only.
- **Photos now reach the report.** `OrchestrationResult` gained `media_insights` and `media_report`, so `main.py` renders the **Media Overview** section (file counts, dimensions, duplicates, hero image) and a new **Photo Coverage** section (rooms documented, amenities visible in photos, provider provenance). Both were previously unreachable outside `deal-report --media-insights`: the renderer and the entire `core/reports/photo_report.py` builder were tested but fed by nothing. New `src/core/media/local.py` bridges a local photo folder to the media layer, which until now only the download pipeline could produce assets for.
- **The report now states what the listing states.** `ListingInsights` gained additive optional `price`, `sqft`, `bedrooms`, `bathrooms`, `year_built`, rendered as an **As listed** line. The pipeline had been extracting none of them despite `ingest-listing` extracting all of them from the same file.
- **Condition tags come from text *and* photos** (`src/agents/listing_analyst.py`). Sourcing them from photo rollup alone made the field structurally always empty whenever the CV providers are deterministic stubs — i.e. by default. Defects merge the same way, and the CV rollup's amenity labels (computed, then discarded) now reach the report too.
- **Amenity and condition vocabularies extended**: multi-unit laundry phrasings (`separate laundry`, `private laundry`, `ensuite laundry`, `washer and dryer`) map to `in_unit_laundry`; bare `laundry` deliberately does not, since it may describe a shared room. Condition keywords gained `renovated`, `move-in ready`, `updated bath`, `new roof`, `new windows`.
- Report generator extended with media overview, baseline/stress/NOI-based valuation tables, and env-driven overrides (`AIREAL_CAP_DRIFT_BPS`, `AIREAL_APPRECIATION_PCT`, `AIREAL_STRESS_ADJ`).
- Vision provider interface refactored; tests reorganized under `tests/core/*`, `tests/integration/*`.
- Coverage gate set to 80% over `src/core`, `src/schemas`, `src/market` (`pytest.ini` + `.coveragerc`).

### Fixed
- **`.env.example` documented non-default values**, making it a reproducibility trap rather than a contract. It shipped `AIREAL_CAP_DRIFT_BPS=5` against a code default of `0` (and `AIREAL_DEBUG=1` against off), so anyone who copied it to `.env` — which VS Code's Python extension auto-loads via `python.envFile` — silently got a drifting cap rate and a report nobody without that `.env` could reproduce. It also documented five knobs that no code reads (`AIREAL_PHOTO_AGENT`, `AIREAL_VISION_PROVIDER`, `AIREAL_VISION_MODEL`, `AIREAL_VISION_TIMEOUT_S`, `AIREAL_VISION_MAX_RETRIES`) while omitting six that it does (`AIREAL_OUT`, `AIREAL_HORIZON`, `AIREAL_LISTING`, `AIREAL_PHOTOS`, `AIREAL_ENGINE`, `AIREAL_SCENARIOS`). Rewritten so every documented value IS the code default — copying it verbatim now produces output byte-identical to running with no `.env` at all — with unimplemented names listed explicitly as inert. `tests/test_env_example.py` fails if a documented value drifts from its code default or a newly-read variable goes undocumented.
- **Demo bundle path regression**: `e4716df` deleted the `data/sample/` bundle in favour of `data/sample_listings/`, but left every reference pointing at the old path — so `InputsLoader.load(None)` always failed on a missing `data/sample/inputs.json`, and `main.py` masked it by fabricating a 53-byte listing plus two 0-byte JPEGs on every run (creating an untracked `data/sample/` and producing a report about nothing). The 36 Kelly bundle is restored as `data/sample_listings/36_kelly_moncton/` (listing, 12 photos, `inputs.json`, `finance.json`); `main.py` now defaults to it and fails loudly rather than fabricating assets; loader defaults, `deal-advisor` error copy, and docs repointed.
- **Square footage could be the purchase price** (`src/schemas/labels.py`): the `sq ft` pattern separated number from unit with `\s*`, which spans newlines, so `"Price: $399,900\nSquare Feet: 1,936"` matched `399,900` + `Square Feet` and reported **399900** as the floor area; the label-first form (`Square Feet: N`) was additionally never recognized. Separators are now horizontal-whitespace only, the labelled form is parsed (and takes precedence, since callers collapse newlines first), and a `:`/`-` separator is required so a trailing figure cannot be swallowed. Corrupted `price_per_sqft` and every downstream signal derived from it.
- **Bedroom count could be the square footage** (`src/schemas/labels.py`): the same `\s*`-spans-newlines defect as the sqft pattern, one field over. `"Square Feet: 1,936\nBedrooms: 3"` matched `936` + `Bedrooms` and reported **936 bedrooms**. The label-first patterns were additionally anchored to `^`, so they never matched after callers collapse the text to one line, guaranteeing the fallthrough to the broken inline form. Inline separators are now horizontal-whitespace only, and the label forms are unanchored with a required `:`/`-`.
- **`ListingInsights` fields were silently dropped in the analyst merge** (`src/agents/listing_analyst.py`): the merge rebuilt the model field by field, so anything added to the schema later never survived to the report. Replaced with `model_copy(update=...)`, naming only the fields the agent actually merges — a structural fix, not a per-field one.
- **Reports were nameless when the address did not parse** (`src/core/reports/generator.py`): the header read `insights.address` alone and fell back to "Subject Property". `ListingInsights` gains an additive optional `title`, populated deterministically by `listing_parser`, and the header resolves address → title → generic.
- **Invalid postal code in the sample listing**: `36 Kelly` carried `U1C 2R7`; Canadian postal codes never begin with `U`, so address parsing correctly declined and the demo report was titled "Subject Property". Corrected to `E1C 2R7`.
- **IRR solver domain robustness** (`src/core/finance/irr.py`): the Newton-Raphson step could converge to a spurious real root of the NPV polynomial where `1 + r < 0` (economically meaningless, e.g. a reported IRR of −179% for a deep-underwater deal whose true IRR is ≈ −18.6%). The solver now rejects any root ≤ −100% and hands off to the existing domain-bounded bisection, guaranteeing a valid IRR `> −100%` — matching the `irr_10yr >= -1.0` invariant already asserted in the engine tests. Surfaced by Mission 1 scenario corners; math verified against standard IRR/root-finding references.
- **Packaging**: added `[build-system]` + `[project]` metadata (name/version/requires-python) and namespace-aware setuptools package discovery, so `pip install -e .` now succeeds and the `ingest-listing` / `deal-report` / `deal-advisor` console scripts resolve. Runtime dependencies still come from the requirements files (matching CI).

### Removed
- **`src/core/advisor/scenarios.py`, `src/core/intelligence/narrative_builder.py`, `src/core/intelligence/report_builder.py` — Mission 2 Gate 3.** Wired into `deal-advisor` in `29ed89b` behind `--what-if`/`--narrative`; blocked by the founder-proxy before merge and deleted rather than fixed, because there was no honest fix that kept the same shape. `scenarios.py` invented its sensitivity coefficients from nothing amortization-shaped and rendered a fabricated `irr_est` while its own disclaimer (`"Approximate scenario; does not re-run engine."`) never reached the page; it was also unanchored to the deal (a hardcoded `0.25` down-payment-rate fallback against a real `0.05`). `narrative_builder`/`report_builder` duplicated `deal-report`'s output with strictly less information and printed raw fractions (`IRR: 0.12`) where every other surface renders a percentage (`12.29%`). An engine-backed what-if belongs behind `src/market/scenario_runner.py` (perturb `FinancialInputs`, re-run `run_financial_model`), not a standalone approximation — see the 2026-08-05 Gate 3 status note above for the full record. `deal-advisor --regional-income` is unaffected other than dropping its two fabricated fields (`str_multiplier`, `turnover_cost`) from output — see the same note.
- **`src/core/strategy/` (`form_thesis`) — the project's second verdict engine.** It formed a BUY/CONDITIONAL/DECLINE thesis with its own thresholds and was called by nothing but its own two unit tests, so the repo carried two answers to "is this a good deal?" and shipped only one of them. Deleted **after** both guardrails it had and the live `agents/chief_strategist` lacked were ported: judging the cap-rate spread against the user's configured `market.cap_rate_spread_target` rather than a hardcoded 150 bps, and the Year-1 cash-on-cash floor (now `MIN_COC_Y1`, see **Added**). Everything else it did the live module already did, and did more strictly — it also has an IRR floor `form_thesis` never had — and its `coc < 0 AND dscr < 1.0` DECLINE shortcut is fully subsumed by the live `num_fails >= 3` rule once the CoC floor counts as a failure (verified across 21,600 generated deals: 8,400 hits, 8,400 already DECLINE). No behaviour was lost and no public API changed; nothing outside `tests/unit/test_strategist*.py` imported it. Rationale: an agent exists only where a model might one day enter, and everything deterministic is called directly from `core/` — verdict formation is a judgment with an LLM-shaped seam, so it belongs to the agent layer, not to two places at once.

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
