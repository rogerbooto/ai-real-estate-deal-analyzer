# Mission 1 — Scenario Intelligence

_Chartered: 2026-07-23 · Base: main @ `e4716df` · Owner of gate: Roger (never self-approve)_

## Executive Summary

Wire the existing, fully-tested market scenario engine (`src/market`: snapshot → hypothesis grid → rejector → renormalized priors) into the deterministic analysis pipeline and the report generator, so a run can produce **prior-weighted scenario outcomes** (expected/downside DSCR, CoC, cash flow, IRR ranges) instead of relying solely on raw env-knob stress overrides. Wave 0 first clears two hygiene blockers: landing the uncommitted working-tree changes on `main`, and adding the missing `[project]` metadata to `pyproject.toml` so `pip install -e .` and the three declared console scripts actually work.

This is composition at a purpose-built seam. The finance engine is **not modified**: each accepted hypothesis perturbs a **copy** of `FinancialInputs`, the engine is re-run per scenario, and outcomes are aggregated with the hypothesis priors.

## In Scope

* Wave 0 (enablement):
  * Commit/land the current working-tree changes (media insights/intelligence refactor, `src/core.zip` deletion, `.gitignore`) via branch + PR.
  * Add `[project]` name/version/requires-python metadata (+ setuptools package config as needed) so `pip install -e .` works and `ingest-listing` / `deal-report` / `deal-advisor` resolve. Update README/CONTRIBUTING packaging caveats to match.
* A small adapter module (new file(s), e.g. `src/market/adapter.py`) mapping `MarketSnapshot` + accepted `MarketHypothesis` deltas onto perturbed copies of `FinancialInputs` (rent growth, expense growth, interest rate, cap rate, vacancy/occupancy).
* A scenario runner (e.g. `src/market/scenario_runner.py`) that: builds snapshot → `generate_hypotheses` → `reject_unrealistic` → runs `run_financial_model` per scenario → aggregates prior-weighted outcomes into a typed result (new additive Pydantic model(s), e.g. `ScenarioOutcome`, `ScenarioAnalysis`).
* Opt-in wiring: `main.py --scenarios` flag (and/or `AIREAL_SCENARIOS=1`, `run.scenarios` in `AppInputs.run`), market snapshot sourced from the existing `MarketAssumptions`/config JSON (`market` block).
* Report: a new "Market Scenarios" section in `core/reports/generator.py` (rendered only when scenario results are supplied) — scenario table (top-N by prior), expected values, downside (e.g. min / p25-by-prior) outcomes, and rejection notes.
* Tests: adapter unit tests, scenario-runner determinism tests (same seed → identical output; priors sum to 1), report-section tests, one end-to-end integration test.
* Docs: `src/market/README.md` wiring status, root README roadmap (move the integration item from V3-planned to shipped), CHANGELOG Unreleased entries.

## Out of Scope (explicitly)

* Any change to the math inside `src/core/finance/` (high-blast; forbidden here).
* Breaking or reshaping existing models in `src/schemas/models.py` (additive new models only).
* Real LLM/vision providers, CrewAI kickoff (backlog #3).
* Live market data ingestion, UI work.
* Changing default behavior: with scenarios off, reports must be **byte-identical** to today.

## Waves

### Wave 0 — Enablement (hygiene blockers)
1. Branch from `main`; commit working-tree changes with a clean message; open PR; CI green; merge.
2. Packaging metadata fix; verify `pip install -e .` + all three console scripts in a fresh venv; update README/CONTRIBUTING caveats.

### Gate 0 — Roger merges Wave 0 PRs.

### Wave 1 — Discovery & Design (no production code)
1. Map each `MarketHypothesis` delta axis to concrete `FinancialInputs` fields; write a 1-page design note (in the PR description or `docs/plans/`), including how `vacancy_delta` maps to `occupancy`, how `interest_rate_delta` interacts with existing financing, and what "downside" summary statistic is reported. Confirm semantics with the financial-result-interpreter reviewer.
2. Decide the snapshot source of truth (config `market` block vs. `MarketAssumptions`) and the exact CLI/env opt-in surface.

### Gate 1 — Design review: staff-code-reviewer + staff-financial-result-interpreter sign off; principal-principles-guardian VETO check (honesty of scenario semantics, determinism preserved).

### Wave 2 — Implementation
1. Adapter + scenario runner + additive result models, mypy-strict clean.
2. `main.py` / inputs opt-in wiring.
3. "Market Scenarios" report section (report-experience-designer shapes it; python-engineer lands it).

### Wave 3 — Validation
1. Full test additions (unit + integration + determinism); coverage gate ≥80% holds.
2. Run against `data/sample_listings/47_perrot_shediac` and at least one `artifacts/` deal config; financial-result-interpreter sanity-reviews the numbers.
3. Docs + CHANGELOG updates.

### Gate 2 — Final: staff-code-reviewer approval, guardian VETO pass, CI green, then **Roger's mission gate** (PR merge + optional tag).

## Definition of Done

* [ ] Wave 0: working tree clean on main; `pip install -e .` succeeds; `ingest-listing --help`, `deal-report --help`, `deal-advisor --help` all run from a fresh venv.
* [ ] `python main.py --scenarios` (demo inputs) emits a report containing a "Market Scenarios" section with prior-weighted outcomes; without the flag, output is byte-identical to pre-mission.
* [ ] Scenario results are deterministic: fixed seed → identical bytes across runs; accepted priors sum to 1 (±1e-12).
* [ ] No diffs inside `src/core/finance/` (except imports-free additive adapter living outside it); no breaking schema changes.
* [ ] New tests pass; overall coverage ≥80%; ruff format/check, mypy strict, CI green.
* [ ] `src/market/README.md`, root README roadmap, CHANGELOG updated truthfully.
* [ ] Guardian VETO passed; Roger approved the mission gate.

## Agent Roster (≤3 concurrent) — task → agent → model tier

_Tiers proposed by planner; confirm with `staff-cost-aware-model-router` at kickoff. Tiers: cheap (haiku-class), standard (sonnet-class), capable (top reasoning)._

| Task | Agent | Tier |
| --- | --- | --- |
| Wave 0 commit hygiene + packaging metadata + CI verify | staff-release-coordinator | standard |
| Wave 0 review | staff-code-reviewer | standard |
| Wave 1 delta→inputs mapping design note | staff-python-engineer | capable |
| Wave 1 scenario-semantics review (finance meaning) | staff-financial-result-interpreter | capable |
| Wave 1 scope sanity (product value) | principal-founder-proxy | capable |
| Wave 2 adapter + runner + wiring | staff-python-engineer | standard |
| Wave 2 scenario report section design | staff-report-experience-designer | standard |
| Wave 2/3 tests (unit, integration, determinism) | staff-qa-test-engineer | standard |
| Wave 3 numeric sanity on sample deals | staff-financial-result-interpreter | standard |
| Wave 3 docs + CHANGELOG | staff-documentation-maintainer | cheap |
| Gate reviews (code) | staff-code-reviewer | standard |
| Gate VETO (honesty, determinism, values) | principal-principles-guardian | capable |
| Release coordination (merge order, optional tag) | staff-release-coordinator | cheap |

## Binding Constraints

1. **Deterministic-core invariant**: `src/core/finance/*` math untouched; scenarios only perturb *copies* of inputs and re-run the engine.
2. **Schema contracts**: `src/schemas/models.py` changes are additive-only (new models); nothing existing is renamed, retyped, or removed.
3. **Default-off**: scenario analysis is opt-in; baseline outputs byte-identical when off.
4. **Honesty**: report language must state scenarios are deterministic what-ifs over user-provided market assumptions — not predictions or live market data.
5. **License boundary**: Research & Education license unchanged; no new runtime dependencies without explicit justification.
6. **Solo-dev cap**: one mission at a time; ≤3 concurrent agents; small PRs (Wave 0 separate from Waves 1–3).

## Gates

* **Guardian VETO** (principal-principles-guardian): may block on honesty/determinism/values grounds at Gate 1 and Gate 2.
* **Founder gate**: Roger merges every PR and approves mission completion. No agent self-approves.
