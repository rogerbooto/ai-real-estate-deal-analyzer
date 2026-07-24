# Roadmap Tracker — AI Real Estate Deal Analyzer

Standing ledger owned by the mission-planner. Read first, update last, every run.

---

## 1. Current state (as-built)

**Composite grade: B-** _(planner-derived 2026-07-23; to be confirmed by app-evaluator when spawnable)_
Base: main @ `e4716df` + uncommitted working-tree refactors (`src/core/media/insights.py`, `src/core/media/intelligence.py`, deleted `src/core.zip`, `.gitignore`). CI green on main (run 19407486629).

| Axis | Grade | One-liner |
| --- | --- | --- |
| Finance core | A- | Deterministic engine with IO/amortization, refi, IRR, insight-aware modifiers; well tested (`src/core/finance/`). |
| Ingestion & media | B+ | File/URL ingest with fetch policy + robots; media discovery/download/manifest; opt-in phash/quality/hero intelligence. In-progress API refactor parked (broken; `git stash@{0}`) for a dedicated branch. |
| CV / AI | C+ | Closed-set ontology + provider seams, but `vision`/`llm` providers are deterministic stubs; no real AI path. Honest, now documented as such. |
| Orchestration | B | Clean deterministic pipeline; CrewAI engine is a validated parity shell (`kickoff()` never called). |
| Market / scenarios | C | `src/market` (snapshot, hypotheses grid, rejector, regional income) fully built + tested but **wired into nothing** — dormant value. |
| Reports | B+ | Rich Markdown reports (baseline/stress/NOI valuation tables, media overview); stress knobs are raw env vars, not principled scenarios. |
| Advisor / intelligence | B | Multi-deal fusion, composite scoring, ranking, portfolio summary via `deal-advisor` CLI. |
| Packaging / distribution | D | `pyproject.toml` lacks `[project]` metadata → `pip install -e .` fails; declared console scripts are dead; CLIs only run via `python -m`. |
| Docs | A | Fully reconciled 2026-07-23 (see changelog entry below). |
| Tests / CI | B+ | 87 test files; 80% coverage gate on core/schemas/market; ruff + mypy strict in CI. |

---

## 2. Mission history

| # | Mission | Status | Dates |
| --- | --- | --- | --- |
| — | (pre-tracker) v0.1.0 MVP, media pipeline, CV v2, advisor/intelligence, address parsing | Shipped organically | 2025-09 → 2025-11 |
| 1 | Scenario Intelligence (wire `src/market` into pipeline + reports; Wave 0 packaging fix) | **Chartered** — awaiting Roger's gate | 2026-07-23 → |

---

## 3. Blocker / pre-condition ledger

| Blocker | Gates | Status |
| --- | --- | --- |
| Uncommitted working-tree changes on `main` (core.zip deletion, .gitignore, doc reconciliation) | Any mission branching from main | **In review 2026-07-24** — landed on branch `chore/land-pending-work` (2 commits, awaiting PR + Roger merge); media refactor split out (see next row) |
| Media-intelligence API refactor incomplete/broken (caller `insights.py` + tests not propagated to new signatures; ruff/mypy/tests red; env-dependent `_dct2` pHash) | Any work touching `src/core/media/` | **Open 2026-07-24** — orphaned WIP parked in `git stash@{0}`; deferred to its own branch `feat/media-intelligence-refactor` (NOT Mission 1). Fix list in `MISSION_1_SPRINT_TRACKER.md` parking note |
| `pyproject.toml` missing `[project]` metadata (broken install, dead console scripts) | Truthful CLI docs; distribution; UI missions | **Open** — scheduled in Mission 1 Wave 0 |
| No real AI provider (vision/LLM stubs only) | Any "AI-powered" marketing claim; CrewAI kickoff mission | Open — deferred (backlog #3) |
| Doc drift | Planning on stale docs | **Closed 2026-07-23** (full reconciliation) |

---

## 4. Opportunity backlog (leverage-ranked)

| Rank | Candidate | Reward | Blast | Seam | Gap closed | Axes moved | Pre-conditions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | **Scenario Intelligence** — wire `src/market` hypotheses/rejector into pipeline + report scenario section | High (closes oldest promised feature; principled scenario analysis replaces raw env knobs; portfolio + product + honesty) | Low-Med (pure composition: perturb input copies, re-run engine; no finance-core or schema-contract edits) | `src/market` was explicitly built as a V2 seam; report generator is additive | Market axis C→B+, Reports B+→A- | Market, Reports, Orchestration, Docs | Commit hygiene + packaging fix (Wave 0) |
| 2 | Packaging metadata fix (`[project]` table) | Med (credibility; documented console scripts become true) | Tiny | pyproject only | Packaging D→B | Packaging, Docs | None — folded into Mission 1 Wave 0 |
| 3 | Real AI provider behind existing seams (OpenAI vision for CV; CrewAI kickoff for thesis narrative) | High (makes the "AI" headline true) | Med-High (API keys, cost, non-determinism policy needed; guardian gate) | CV provider registry + crewai_runner shell | CV/AI C+→B+ | CV/AI, Orchestration | Mission 1 done (stable scenario outputs to narrate); determinism policy approved |
| 4 | Streamlit UI for interactive scenario exploration | High (portfolio wow) | Med (new surface, new deps) | Reads existing JSON artifacts | Distribution | Packaging, Portfolio | #1 (scenarios give the UI something to explore), #2 |
| 5 | Live market data ingestion (comps, cap-rate drift) | Med | High (network, data licensing, freshness) | fetch/ policy | Market realism | Market | #1; compliance review |

---

## 5. Current recommendation

**Mission 1 — Scenario Intelligence** (charter: `docs/plans/MISSION_1_scenario_intelligence.md`).

Why now: it is the highest reward-per-blast item on the board. The scenario engine already exists, is fully tested, and was designed for exactly this integration — the mission is composition at a purpose-built seam, not new invention. It closes the oldest public roadmap promise ("Integration of Market Hypotheses and Rejector modules"), upgrades the report's stress analysis from ad-hoc env knobs to prior-weighted scenario outcomes, and visibly differentiates the portfolio piece. Wave 0 clears the two open hygiene blockers (uncommitted main changes; packaging metadata) at trivial cost. The deterministic finance core and schema contracts are explicitly out of bounds.

Handoff prompt: `docs/plans/MISSION_1_HANDOFF.md` — ready to paste into a fresh Claude Code session. Roger holds the mission gate.

---

## 6. Changelog

* **2026-07-23** — First run. Phase A: full documentation reconciliation against main @ `e4716df` + working tree — fixed root README (license badge MIT→Research & Education, V1→V2 output, phantom `src/tools`/`src/reports` index entries, CLI docs added, coverage 90%→80%, honest CrewAI-seam framing, roadmap split V1/V2-shipped/V3-planned, packaging caveat), rewrote `src/cli/README.md` (was the old tools README), rewrote `src/core/README.md` (removed nonexistent `cv.bridge`/`xirr`/`media_pipeline`/`build_strategy`; added advisor/intelligence/ingest subareas), rewrote `src/agents/README.md` and `src/orchestrators/README.md` (real signatures, class-based agents, functional-vs-docstring env flags, CrewAI parity-shell honesty), rewrote `src/core/reports/README.md` (write_report, media overview, env overrides, fixed nested links), rewrote `src/inputs/README.md` (InputsLoader/AppInputs/RunOptions live here; real env overrides), rewrote `src/schemas/README.md` (per-unit IncomeModel, real field names, media/ingest models, labels ontology), patched `src/market/README.md` (status + links), reconciled CHANGELOG Unreleased placeholders into the actual shipped V2 feature list with dated status note, fixed CONTRIBUTING install instructions. Phase B: created this tracker; chartered **Mission 1 — Scenario Intelligence** (plan, sprint tracker, handoff prompt written).
