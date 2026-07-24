# Mission 1 Handoff — Scenario Intelligence

**How to use this prompt:** Open a fresh Claude Code session at the repo root
(`/home/rtokime/projects/Personal/ai-real-estate-deal-analyzer`) and paste everything between the
BEGIN/END markers verbatim. The session becomes the mission orchestrator. Roger holds all merge and
mission gates.

=== BEGIN MISSION PROMPT ===

You are the orchestrator for **Mission 1 — Scenario Intelligence** of the AI Real Estate Deal
Analyzer (deterministic-first real estate underwriting tool; solo developer: Roger).

## Mission identity (one read)

Wire the existing, fully-tested market scenario engine (`src/market`: snapshot → hypothesis grid →
rejector → renormalized priors) into the deterministic pipeline and the Markdown report, producing
opt-in, prior-weighted scenario outcomes (expected/downside DSCR, CoC, cash flow, IRR). Before
that, Wave 0 clears two hygiene blockers: commit the pending working-tree changes on `main`, and
add the missing `[project]` metadata to `pyproject.toml` so `pip install -e .` and the declared
console scripts (`ingest-listing`, `deal-report`, `deal-advisor`) actually work.

## Read these first (canonical, in order)

1. `docs/plans/MISSION_1_scenario_intelligence.md` — the mission charter (scope, waves, DoD, constraints).
2. `docs/plans/MISSION_1_SPRINT_TRACKER.md` — live task tracker; you keep it current.
3. `src/market/README.md` — the scenario engine you are wiring (APIs, invariants, rejector rules).
4. `src/core/README.md` and `src/core/reports/README.md` — the engine and report seams you compose with.
5. `docs/plans/ROADMAP_TRACKER.md` §1 and §3 — current state and blocker ledger.

All docs were reconciled against code on 2026-07-23 (main @ `e4716df`); trust them, but verify any
API you touch by reading the source.

## What you are building

* **Wave 0 (two small PRs, sequential):**
  1. Branch from `main`; commit the pending working-tree changes (refactors of
     `src/core/media/insights.py` and `src/core/media/intelligence.py`, deletion of `src/core.zip`,
     `.gitignore` addition); PR; CI green.
  2. Add `[project]` name/version/requires-python (+ setuptools package discovery config) to
     `pyproject.toml`; verify in a fresh venv that `pip install -e .` succeeds and all three console
     scripts run `--help`; update the packaging caveats in `README.md`, `CONTRIBUTING.md`, and
     `src/cli/README.md` to say installation now works.
* **Waves 1–3 (one feature PR):**
  * `src/market/adapter.py` — map each accepted `MarketHypothesis` delta (rent, expense growth,
    interest rate, cap rate, vacancy) onto a **perturbed copy** of `FinancialInputs`.
  * `src/market/scenario_runner.py` — build snapshot → `generate_hypotheses(seed=…)` →
    `reject_unrealistic` → run `src.core.finance.engine.run_financial_model` once per accepted
    hypothesis → aggregate prior-weighted outcomes into additive Pydantic models
    (`ScenarioOutcome`, `ScenarioAnalysis`).
  * Opt-in wiring: `main.py --scenarios`, env `AIREAL_SCENARIOS`, and `run.scenarios` in
    `src/inputs/inputs.py` `RunOptions`; snapshot sourced per the Wave 1 design note.
  * New "Market Scenarios" section in `src/core/reports/generator.py`, rendered only when scenario
    results are passed; includes a top-N-by-prior scenario table, expected values, a downside
    summary, and an explicit honesty note ("deterministic what-ifs over user-provided assumptions,
    not predictions").
  * Tests: adapter units; determinism (fixed seed → byte-identical output); accepted priors sum to
    1 (±1e-12); report-section rendering; one end-to-end integration test; a byte-identical
    baseline test with scenarios off.

## Waves & gates

Wave 0 (enablement) → **Gate 0** (Roger merges) → Wave 1 (design note: delta→inputs mapping,
downside statistic, snapshot source, opt-in surface) → **Gate 1** (code-reviewer +
financial-result-interpreter sign-off; principles-guardian VETO check) → Wave 2 (implementation) →
Wave 3 (validation + docs) → **Gate 2** (final review, guardian VETO, CI green, Roger's mission
gate). Definition of Done is in the charter — check every box before requesting Gate 2.

## Binding constraints (non-negotiable)

1. **Deterministic core untouched:** zero diffs inside `src/core/finance/`; scenarios perturb input
   copies and re-run the engine.
2. **Schema contracts:** `src/schemas/models.py` additive-only; nothing renamed, retyped, removed.
3. **Default-off:** with scenarios disabled, all outputs are byte-identical to pre-mission.
4. **Honesty:** scenario language never implies prediction or live market data.
5. **License/deps:** no new runtime dependencies without explicit justification in the PR.
6. **Small blast:** Wave 0 PRs separate from the feature PR; keep the feature PR reviewable.

## Orchestration protocol

* **Agents:** use the project fleet in `.claude/agents/` — `staff-release-coordinator` (Wave 0),
  `staff-python-engineer` (design + implementation), `staff-financial-result-interpreter`
  (scenario semantics + numeric sanity), `staff-report-experience-designer` (report section),
  `staff-qa-test-engineer` (tests), `staff-documentation-maintainer` (docs),
  `staff-code-reviewer` (all reviews), `principal-principles-guardian` (VETO at Gates 1 and 2),
  `principal-founder-proxy` (scope sanity only — Roger holds the actual gates). **≤3 agents
  concurrent.**
* **Cost routing:** confirm tiers with `staff-cost-aware-model-router` at kickoff; planner's
  proposal: docs/mechanical → cheap; implementation/tests/reviews → standard; Wave 1 design,
  finance semantics, and guardian calls → capable. Record `task → agent → tier` in the sprint
  tracker.
* **Verify inline:** never trust an agent's "done" — re-run its tests, re-read its diff, and check
  DoD items yourself before marking ✅.
* **Branch + PR flow:** feature branches off `main`; conventional commits; PRs to `main`; Roger
  merges. Never push to `main` directly. Never self-approve a gate.
* **Tracker discipline:** update `docs/plans/MISSION_1_SPRINT_TRACKER.md` after every task state
  change — full updates (overall counts + wave summary + task rows), never partial; date every
  gate decision record.
* **Research-first + YAGNI:** read the actual seam code before writing new code; build only what
  the charter scopes — no speculative extensions (no UI, no live data, no LLM providers).

## First concrete action

Run `git status` and `git log --oneline -3` to confirm the working-tree state matches the charter
(modified `.gitignore`, `src/core/media/insights.py`, `src/core/media/intelligence.py`; deleted
`src/core.zip`; base `e4716df`). Then start Wave 0 task 0.1: create branch
`chore/land-media-refactor`, review the diff with `staff-code-reviewer`, commit, open the PR, and
update the sprint tracker.

=== END MISSION PROMPT ===
