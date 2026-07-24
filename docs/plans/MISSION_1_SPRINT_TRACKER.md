# Mission 1 — Scenario Intelligence — Sprint Tracker

_Charter: `docs/plans/MISSION_1_scenario_intelligence.md` · Base: main @ `e4716df`_

## Status legend

| Symbol | Meaning |
| --- | --- |
| ⬜ | Not started |
| 🔄 | In progress |
| ✅ | Done (verified inline by orchestrator — never trust an agent's "done") |
| ⛔ | Blocked |
| 🚫 | Dropped (record why) |

## Overall progress

* Tasks: **1 / 14** done
* Waves: **0 / 4** complete
* Gates passed: **0 / 3**

## Wave summary

| Wave | Focus | Tasks | Done | Status |
| --- | --- | --- | --- | --- |
| 0 | Enablement (commit hygiene, packaging) | 3 | 1 | 🔄 |
| 1 | Discovery & design | 3 | 0 | ⬜ |
| 2 | Implementation | 4 | 0 | ⬜ |
| 3 | Validation & docs | 4 | 0 | ⬜ |

---

## Wave 0 — Enablement

| # | Task | Agent → Tier | Status | Notes |
| --- | --- | --- | --- | --- |
| 0.1 | Branch `chore/land-pending-work`; land hygiene + doc reconciliation (core.zip deletion, .gitignore `.claude/`, README/CHANGELOG/CONTRIBUTING + 7× `src/*/README.md`, `docs/plans/` artifacts); PR; CI green | staff-release-coordinator → standard | ✅ | Landed on `main` @ `f19678d` (2 commits: `1bc0b94` hygiene, `f19678d` docs), pushed 2026-07-24 via direct FF merge at Roger's instruction — **branch protection bypassed** (unsigned commits, no PR, "tests" check not gated; admin bypass). **Media refactor descoped** (was in original 0.1 scope). Code-reviewer (2026-07-24) found the working-tree `insights.py`/`intelligence.py` refactor broken: API rewritten but caller + tests not propagated → 10 mypy / 13 ruff errors, 4 failing tests + 1 collection ImportError. It exists on **no branch** (orphaned WIP). Parked in `git stash@{0}` (recoverable); media files restored to committed `main` (green — 7 tests pass). Deferred to its own branch per Roger's "new branch per work-item" directive → see backlog note below. |
| 0.2 | `[project]` metadata in pyproject; fresh-venv verify `pip install -e .` + 3 console scripts; update README/CONTRIBUTING caveats | staff-release-coordinator → standard | ⬜ | |
| 0.3 | Review both PRs | staff-code-reviewer → standard | ⬜ | |

### Media-refactor parking note (2026-07-24)

* The incomplete media-intelligence API refactor is preserved in `git stash@{0}`
  ("WIP: incomplete media-intelligence API refactor (broken per review 2026-07-24…)").
* Blocking defects to fix before it can land (from staff-code-reviewer): propagate the new
  `compute_phash`/`compute_quality`/`extract_palette`/`rank_hero` signatures to the caller
  `src/core/media/insights.py:147-195`; restore or migrate `PaletteColor`/`load_bounded_thumbnail`;
  update `tests/unit/test_intelligence.py` + `tests/unit/test_media_intelligence_basic.py`;
  clear ruff/mypy; resolve the `_dct2` backend-dependent (cv2 vs scipy vs FFT) pHash determinism hazard.
* **Action:** finish on a dedicated branch (e.g. `feat/media-intelligence-refactor`) as its own scoped
  PR — NOT part of Mission 1. Logged to `ROADMAP_TRACKER.md` blocker/backlog ledger.

### Gate 0 decision record — Roger merges Wave 0

* Date: —
* Decision: —
* Notes: —

## Wave 1 — Discovery & Design

| # | Task | Agent → Tier | Status | Notes |
| --- | --- | --- | --- | --- |
| 1.1 | Design note: hypothesis-delta → FinancialInputs mapping, downside statistic, snapshot source, opt-in surface | staff-python-engineer → capable | ⬜ | |
| 1.2 | Finance-semantics review of design note | staff-financial-result-interpreter → capable | ⬜ | |
| 1.3 | Product-scope sanity check | principal-founder-proxy → capable | ⬜ | |

### Gate 1 decision record — Design review + Guardian VETO check

* Date: —
* Reviewer verdicts: —
* Guardian VETO: —
* Decision: —

## Wave 2 — Implementation

| # | Task | Agent → Tier | Status | Notes |
| --- | --- | --- | --- | --- |
| 2.1 | Adapter (`src/market/adapter.py`): deltas → perturbed FinancialInputs copies | staff-python-engineer → standard | ⬜ | |
| 2.2 | Scenario runner + additive result models (`ScenarioOutcome`, `ScenarioAnalysis`) | staff-python-engineer → standard | ⬜ | |
| 2.3 | Opt-in wiring: `main.py --scenarios`, `AIREAL_SCENARIOS`, `run.scenarios` | staff-python-engineer → standard | ⬜ | |
| 2.4 | "Market Scenarios" report section (design + implementation) | staff-report-experience-designer + staff-python-engineer → standard | ⬜ | |

## Wave 3 — Validation & Docs

| # | Task | Agent → Tier | Status | Notes |
| --- | --- | --- | --- | --- |
| 3.1 | Tests: adapter units, determinism (seed→bytes), priors-sum, report section, E2E; coverage ≥80% | staff-qa-test-engineer → standard | ⬜ | |
| 3.2 | Numeric sanity run on `47_perrot_shediac` + one artifacts deal | staff-financial-result-interpreter → standard | ⬜ | |
| 3.3 | Byte-identical baseline check (scenarios off) | staff-qa-test-engineer → standard | ⬜ | |
| 3.4 | Docs: market README wiring status, root README roadmap, CHANGELOG | staff-documentation-maintainer → cheap | ⬜ | |

### Gate 2 decision record — Final review + Guardian VETO + Roger's mission gate

* Date: —
* Code review: —
* Guardian VETO: —
* CI: —
* Roger's decision: —

---

## Tracker discipline

Full updates always: overall counts + wave summary + task rows together — never partial. Every status change gets a dated note. Blockers move to the Blocker Ledger in `ROADMAP_TRACKER.md` if they outlive the mission.
