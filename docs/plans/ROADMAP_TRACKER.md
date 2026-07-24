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
| Market / scenarios | B+ | `src/market` (snapshot, hypotheses grid, rejector, regional income) now **wired** into the pipeline + report as an opt-in prior-weighted scenario overlay (Mission 1: `adapter.py`, `scenario_runner.py`). |
| Reports | A- | Rich Markdown reports (baseline/stress/NOI valuation tables, media overview) **plus** a principled opt-in "Market Scenarios" section (prior-weighted DSCR/CoC/CF/IRR bands, honesty framing) replacing ad-hoc env-knob stress as the scenario story. |
| Advisor / intelligence | B | Multi-deal fusion, composite scoring, ranking, portfolio summary via `deal-advisor` CLI. |
| Packaging / distribution | D | `pyproject.toml` lacks `[project]` metadata → `pip install -e .` fails; declared console scripts are dead; CLIs only run via `python -m`. |
| Docs | A | Fully reconciled 2026-07-23 (see changelog entry below). |
| Tests / CI | B+ | 87 test files; 80% coverage gate on core/schemas/market; ruff + mypy strict in CI. |

---

## 2. Mission history

| # | Mission | Status | Dates |
| --- | --- | --- | --- |
| — | (pre-tracker) v0.1.0 MVP, media pipeline, CV v2, advisor/intelligence, address parsing | Shipped organically | 2025-09 → 2025-11 |
| 1 | Scenario Intelligence (wire `src/market` into pipeline + reports; Wave 0 packaging fix; authorized IRR-solver core fix) | **Shipped** — Roger's mission gate approved | 2026-07-23 → 2026-07-24 |

---

## 3. Blocker / pre-condition ledger

| Blocker | Gates | Status |
| --- | --- | --- |
| Uncommitted working-tree changes on `main` (core.zip deletion, .gitignore, doc reconciliation) | Any mission branching from main | **Closed 2026-07-24** — landed on `main` (Mission 1 Wave 0) |
| `pyproject.toml` missing `[project]` metadata (broken install, dead console scripts) | Truthful CLI docs; distribution; UI missions | **Closed 2026-07-24** — `[build-system]`+`[project]`+discovery added (Mission 1 Wave 0.2); `pip install -e .` + 3 console scripts verified |
| Media-intelligence API refactor incomplete/broken (caller `insights.py` + tests not propagated to new signatures; ruff/mypy/tests red; env-dependent `_dct2` pHash) | Any work touching `src/core/media/` | **Open 2026-07-24** — orphaned WIP parked in `git stash@{0}`; deferred to its own branch `feat/media-intelligence-refactor` (NOT Mission 1). Fix list in `MISSION_1_SPRINT_TRACKER.md` parking note |
| GitHub SSH **signing** key not registered ("Dell Laptop" key is an auth key only) | Verified commits; clean pushes without admin bypass | **Open 2026-07-24** — commits SSH-signed locally (git 2.55 shim, `~/.gitmodern-bin`) but show Unverified; Roger to add the key as a Signing key in GitHub settings |
| `CITATION.cff` version `1.0.0` ≠ `pyproject`/CHANGELOG `0.1.0` | Any version tag / release cut | **Open 2026-07-24** — reconcile before tagging |
| No real AI provider (vision/LLM stubs only) | Any "AI-powered" marketing claim; CrewAI kickoff mission | Open — deferred (backlog #3) |
| Doc drift | Planning on stale docs | **Closed 2026-07-23** (full reconciliation) |

---

## 4. Opportunity backlog (leverage-ranked)

| Rank | Candidate | Reward | Blast | Seam | Gap closed | Axes moved | Pre-conditions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ✅ 1 | **Scenario Intelligence** — wire `src/market` hypotheses/rejector into pipeline + report scenario section | **SHIPPED 2026-07-24 (Mission 1)** — delivered exactly as scoped; Market C→B+, Reports B+→A-; plus an authorized IRR-solver core fix | — | — | Market C→B+, Reports B+→A- | Market, Reports, Orchestration, Docs | — done |
| ✅ 2 | Packaging metadata fix (`[project]` table) | **SHIPPED 2026-07-24 (Mission 1 Wave 0.2)** — Packaging D→B; `pip install -e .` + 3 console scripts verified | — | pyproject only | Packaging D→B | Packaging, Docs | — done |
| 3 | Real AI provider behind existing seams (OpenAI vision for CV; CrewAI kickoff for thesis narrative) | High (makes the "AI" headline true) | Med-High (API keys, cost, non-determinism policy needed; guardian gate) | CV provider registry + crewai_runner shell | CV/AI C+→B+ | CV/AI, Orchestration | Mission 1 done (stable scenario outputs to narrate); determinism policy approved |
| 4 | Streamlit UI for interactive scenario exploration | High (portfolio wow) | Med (new surface, new deps) | Reads existing JSON artifacts | Distribution | Packaging, Portfolio | #1 (scenarios give the UI something to explore), #2 |
| 5 | Live market data ingestion (comps, cap-rate drift) | Med | High (network, data licensing, freshness) | fetch/ policy | Market realism | Market | #1; compliance review |

---

## 5. Current recommendation

**Mission 1 — Scenario Intelligence: SHIPPED 2026-07-24.** Delivered as chartered (opt-in `--scenarios` overlay, prior-weighted bands, honesty framing, default-off byte-identical) plus a Roger-authorized IRR-solver core fix. Market C→B+, Reports B+→A-, Packaging D→B. `main` @ `8f4ce2a`, CI green, all gates passed.

**Next mission — to be chartered by `mission-planner`.** Leading candidates now that Mission 1's pre-condition ("stable scenario outputs") is met:

* **Backlog #3 — Real AI provider** behind the existing CV/LLM seams (OpenAI vision; CrewAI kickoff for thesis narrative). Highest reward (makes the "AI" headline true) but Med-High blast — needs an API-key/cost/non-determinism policy and a guardian gate. Pre-condition (Mission 1 done) now satisfied.
* **Backlog #4 — Streamlit UI** for interactive scenario exploration (now that scenarios give it something to explore). Portfolio-visible; new surface/deps.

Clear the two release blockers first (§3): register the GitHub signing key; reconcile `CITATION.cff` vs `pyproject` version. Invoke `mission-planner` to reconcile docs and charter the next mission.

---

## 6. Changelog

* **2026-07-24** — **Mission 1 — Scenario Intelligence SHIPPED.** Wave 0 landed commit hygiene + packaging (`pip install -e .` works). Waves 1–3 delivered the opt-in `--scenarios` overlay: `src/market/adapter.py` + `scenario_runner.py` compose the hypothesis grid with the frozen finance engine into prior-weighted DSCR/CoC/CF/IRR bands (downside = prior-weighted p25), a fixed verbatim honesty block, and honest caveats; additive `ScenarioMetricBand`/`ScenarioOutcome`/`ScenarioAnalysis` models; default-off byte-identical. All 4 review gates passed (finance-semantics, founder-proxy scope, code-review, principles-guardian VETO ×2). One founder-authorized frozen-core carve-out: fixed an IRR Newton-Raphson solver artifact (`src/core/finance/irr.py`) that returned economically-meaningless sub-(−100%) roots — math verified against IRR-domain references, surgical (touches only the one artifact). Axis moves: Market C→B+, Reports B+→A-, Packaging D→B. `main` @ `8f4ce2a`, all commits SSH-signed, CI green. Follow-ups logged (§3): GitHub signing-key registration, CITATION/pyproject version reconcile, parked media-intelligence refactor.
* **2026-07-23** — First run. Phase A: full documentation reconciliation against main @ `e4716df` + working tree — fixed root README (license badge MIT→Research & Education, V1→V2 output, phantom `src/tools`/`src/reports` index entries, CLI docs added, coverage 90%→80%, honest CrewAI-seam framing, roadmap split V1/V2-shipped/V3-planned, packaging caveat), rewrote `src/cli/README.md` (was the old tools README), rewrote `src/core/README.md` (removed nonexistent `cv.bridge`/`xirr`/`media_pipeline`/`build_strategy`; added advisor/intelligence/ingest subareas), rewrote `src/agents/README.md` and `src/orchestrators/README.md` (real signatures, class-based agents, functional-vs-docstring env flags, CrewAI parity-shell honesty), rewrote `src/core/reports/README.md` (write_report, media overview, env overrides, fixed nested links), rewrote `src/inputs/README.md` (InputsLoader/AppInputs/RunOptions live here; real env overrides), rewrote `src/schemas/README.md` (per-unit IncomeModel, real field names, media/ingest models, labels ontology), patched `src/market/README.md` (status + links), reconciled CHANGELOG Unreleased placeholders into the actual shipped V2 feature list with dated status note, fixed CONTRIBUTING install instructions. Phase B: created this tracker; chartered **Mission 1 — Scenario Intelligence** (plan, sprint tracker, handoff prompt written).
