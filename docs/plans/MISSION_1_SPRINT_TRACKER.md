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

* Tasks: **10 / 14** done
* Waves: **3 / 4** complete (Wave 2 done; Wave 3 validation + docs next)
* Gates passed: **2 / 3**

## Wave summary

| Wave | Focus | Tasks | Done | Status |
| --- | --- | --- | --- | --- |
| 0 | Enablement (commit hygiene, packaging) | 3 | 3 | ✅ |
| 1 | Discovery & design | 3 | 3 | ✅ |
| 2 | Implementation | 4 | 4 | ✅ |
| 3 | Validation & docs | 4 | 0 | ⬜ |

---

## Wave 0 — Enablement

| # | Task | Agent → Tier | Status | Notes |
| --- | --- | --- | --- | --- |
| 0.1 | Branch `chore/land-pending-work`; land hygiene + doc reconciliation (core.zip deletion, .gitignore `.claude/`, README/CHANGELOG/CONTRIBUTING + 7× `src/*/README.md`, `docs/plans/` artifacts); PR; CI green | staff-release-coordinator → standard | ✅ | Landed on `main` @ `f19678d` (2 commits: `1bc0b94` hygiene, `f19678d` docs), pushed 2026-07-24 via direct FF merge at Roger's instruction — **branch protection bypassed** (unsigned commits, no PR, "tests" check not gated; admin bypass). **Media refactor descoped** (was in original 0.1 scope). Code-reviewer (2026-07-24) found the working-tree `insights.py`/`intelligence.py` refactor broken: API rewritten but caller + tests not propagated → 10 mypy / 13 ruff errors, 4 failing tests + 1 collection ImportError. It exists on **no branch** (orphaned WIP). Parked in `git stash@{0}` (recoverable); media files restored to committed `main` (green — 7 tests pass). Deferred to its own branch per Roger's "new branch per work-item" directive → see backlog note below. |
| 0.2 | `[project]` metadata in pyproject; verify `pip install -e .` + 3 console scripts; update README/CONTRIBUTING caveats | staff-release-coordinator → standard | ✅ | Committed **local, signed** `9baa6bd` (not yet pushed — see Gate 0). Added `[build-system]` (setuptools) + `[project]` (name/version `0.1.0`/requires-python `>=3.10`, per CHANGELOG+CI/mypy/ruff) + namespace-aware discovery of `src`. **Verified in `airedeal` conda env** (not venv, per Roger): `pip install -e .` succeeds; `ingest-listing`/`deal-report`/`deal-advisor --help` all exit 0. Fixed README/CONTRIBUTING/`src/cli/README.md` caveats + CHANGELOG "Known Gaps"→"Fixed". Follow-ups (see note): CITATION.cff version `1.0.0` ≠ pyproject `0.1.0`; `src/*` subpackages lack `__init__.py` (rely on `namespaces=true`). |
| 0.3 | Review Wave 0 changes (flow is direct-to-main, no PRs per Roger) | staff-code-reviewer + orchestrator inline | ✅ | Media refactor got a full staff-code-reviewer pass (→ descoped). 0.1 hygiene/docs + 0.2 packaging reviewed inline by orchestrator (diffs re-read; install re-verified in conda). No separate formal reviewer pass on the trivial packaging/doc diff — offered to Roger if he wants one before Gate 0. |

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

* Date: 2026-07-24
* Decision: **PASSED.** Roger directed direct-to-main pushes (no PR flow — confirmed via history that the project's flow is mixed but he owns the repo and chose direct). Wave 0 landed on `origin/main` @ `f332feb`.
* CI: **green** — run `30088749627` on `f332feb` `conclusion=success` (ruff format+lint, mypy strict, pytest w/ 80% coverage gate all pass in CI env). Local `airedeal` showed 79.87% coverage — env artifact (missing a dev dep), not a regression; CI authoritative.
* Notes: Commits SSH-signed locally (git 2.55 shim) but GitHub still shows **unverified** — signing-key not yet registered on GitHub (push used admin bypass of the verified-signatures + PR + status-check rules). Roger to register the Dell Laptop key as a **Signing key** for future clean pushes. Media-intelligence refactor descoped/parked (`stash@{0}`) → separate branch. CITATION.cff (`1.0.0`) vs pyproject/CHANGELOG (`0.1.0`) mismatch to reconcile before any tag.

## Wave 1 — Discovery & Design

| # | Task | Agent → Tier | Status | Notes |
| --- | --- | --- | --- | --- |
| 1.1 | Design note: hypothesis-delta → FinancialInputs mapping, downside statistic, snapshot source, opt-in surface | staff-python-engineer → capable | ✅ | `docs/plans/MISSION_1_wave1_design_note.md`. Orchestrator verified schema claims inline (all deltas fractions; occupancy=1−vacancy confirmed; cap_rate_purchase None-derivation confirmed). Key findings: no percent/bps anywhere (fraction+fraction, zero unit conversion); 2 flagged decisions for reviewers — downside=prior-weighted p25 (vs min), cap_rate_delta anchoring when cap unset; str_viability has no engine target (narration-only); **no market-snapshot source currently wired** (new `market` JSON block + resolver designed). |
| 1.2 | Finance-semantics review of design note | staff-financial-result-interpreter → capable | ✅ | **CHANGES REQUESTED** (5/6 items signed off). Substantive: anchor `cap_rate_delta` on the engine-derived NOI/price cap from untouched inputs (not `snapshot.cap_rate`) so scenario-base==headline + stays consistent with additive-to-user; floor-clamp ~0.03. Plus honesty fixes: (2) label p50=median/mean=expected (don't call p50 "expected"); (3) report must state priors are heuristic weights, not calibrated probabilities; (4) IO-period caveat — Y1 DSCR/CoC/CF optimistic when `io_years>0`; (5) disclose rate shock hits both acquisition+refi loans. All engine file:line refs verified by orchestrator. |
| 1.3 | Product-scope sanity check | principal-founder-proxy → capable | ✅ | **SCOPE OK** → Wave 2. Binding conditions: (1) `str_viability` renders with "not modeled — narrative flag only" label or omitted; (2) scenario section structurally separate/labeled, cap caveat adjacent, else drop cap perturbation — *largely dissolved by the finance cap-anchoring fix (base==headline)*. Tightening: honesty note = fixed verbatim string (drop "in-spirit"). Loud-fail resolver, default-off, additive models approved. No escalation to Roger needed at this gate. |

### Gate 1 decision record — Design review + Guardian VETO check

* Date: 2026-07-24 — **CLEARED**
* Reviewer verdicts: finance-semantics = CHANGES REQUESTED → **resolved** in revised note (cap→engine-derived-cap anchor so base==headline; p50=median/mean=expected label fix; priors-are-heuristic honesty; IO-period + rate-shock caveats). Founder-proxy = **SCOPE OK** (str_viability "not modeled" label / omit; separate labeled section; verbatim honesty string). staff-code-reviewer = **SIGN OFF** (no must-fix; no name collisions, no import cycle, write_report/OrchestrationResult additive backward-compat confirmed, numpy already a dep).
* Guardian VETO: **PASS (no veto)** — all 5 focus areas; 7 conditions bind Wave 2 (see design note §10), re-checked at Gate 2.
* Decision: **Gate 1 PASSED.** Design note `MISSION_1_wave1_design_note.md` ratified; §10 captures binding Wave 2 conditions (2 code-reviewer advisories + 7 guardian conditions). Proceed to Wave 2 implementation.

## Wave 2 — Implementation

| # | Task | Agent → Tier | Status | Notes |
| --- | --- | --- | --- | --- |
| 2.1 | Adapter (`src/market/adapter.py`): deltas → perturbed FinancialInputs copies | staff-python-engineer → standard | ✅ | `perturb_inputs(fi, hyp, *, base_cap)` — deep copy, sign-flip on vacancy, cap floor 0.03, str_viability not applied. Orchestrator re-verified: 17 scenario tests pass, mypy/ruff clean (ruff-format applied by orchestrator), **zero `src/core/finance/` edits**. |
| 2.2 | Scenario runner + additive result models (`ScenarioMetricBand`/`ScenarioOutcome`/`ScenarioAnalysis`) | staff-python-engineer → standard | ✅ | `scenario_runner.py`: snapshot resolver (loud-fail on underivable cap), `run_scenarios` (baseline→base_cap from `PurchaseMetrics.cap_rate`, generate→reject→per-scenario perturb+run→pure-Python weighted-percentile bands), empty-set path. Models appended additive to `models.py`. **Orchestrator added `io_years` to `ScenarioAnalysis`** (invariant, for the §7a #6 IO caveat) + test. Full suite 205→206 passing, coverage 80.40%. |
| 2.3 | Opt-in wiring: `main.py --scenarios`, `AIREAL_SCENARIOS`, `run.scenarios` | staff-python-engineer → standard | ✅ | `RunOptions.scenarios`, `AIREAL_SCENARIOS` env, `--scenarios` CLI (precedence CLI>env>JSON>default). Market block plumbed via additive `AppInputs.market` (top-level, off the frozen schema). Scenario work gated in `if run_scenarios_flag:` with lazy `src.market` import. Orchestrator verified live: `--help` shows flag; OFF report has no section; loud-fail on sample = clear ValueError. |
| 2.4 | "Market Scenarios" report section (design + implementation) | staff-report-experience-designer + staff-python-engineer → standard | ✅ | Spec `MISSION_1_wave2_report_section_spec.md` (mockup + G1–G7). Implemented in `generator.py`: `ABOUT_SCENARIOS_BLOCK` verbatim constant (G1), top-5-by-prior grid with cap-applied (G5), bands labeled downside(p25)/median(p50)/mean(expected) (G4), caveats w/ IO gated on `io_years>0` (G3), str_viability "not modeled — narrative flag only" (G4), empty-set no fabrication (G7); `scenarios` keyword-only on both fns (C1); section only when supplied (G2). Orchestrator verified: byte-identical OFF, ON deterministic. Full suite 231 pass, coverage 80.73%, ruff+mypy clean. |

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
