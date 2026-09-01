# Roadmap Tracker — AI Real Estate Deal Analyzer

Standing ledger owned by the mission-planner. Read first, update last, every run.

---

## 1. Current state (as-built)

**Composite grade: B-** _(planner-derived 2026-07-23; to be confirmed by app-evaluator when spawnable)_
**Current baseline (Mission 5 close, 2026-09-01): Mission 5 merged to `main`; `main` is AHEAD of `origin/main` and UNPUSHED (the merge, the Mission 5 work commit, and the still-unpushed charter commit `87efd22`) — Roger controls the push.** Mission 5 validated by Roger 17/17 PASS 2026-09-01. _Prior baseline (Mission 5 charter run, 2026-08-31): `main @ 7cfd449`, tree clean, in sync with `origin/main`_ — Mission 4 merged (`7cfd449`, Roger-validated 9/9 2026-08-31); Mission 3 merged (`8b59399`, Roger-validated 9/9 2026-08-29). `git status` clean at charter time; charter planned read-only against `7cfd449`.
_Historical base (Mission 3 charter run, 2026-08-19): `main @ a00a265`, tree clean, **1 commit ahead of `origin/main @ 0ea42fd`**_ — the unpushed docs backfill `a00a265` ("docs(missions): backfill Roger-facing manual-test + plain-English docs; reconcile roadmap ledger to as-shipped v0.3.0"); Roger controls the push. _(Prior run's base was `main @ 8ed9397`, **in sync with `origin/main`** at that time; verified 2026-08-19: `git rev-list --left-right --count origin/main...main` = `0 0` then.)_ Mission 2 has since been merged AND pushed; the earlier "origin has never received Mission 1" divergence is closed — origin now carries everything through `8ed9397`. _(Historical: the dirty working tree the Mission 1 charter described as its baseline had landed as `6147839` — sample bundle restore, parsing regex fixes, report identity/glossary/provenance wiring, `PASS`→`DECLINE` rename, `.env.example` rewrite.)_ The tree is now clean. Planner-verified, orchestrator-reproduced in the real `airedeal` env (`/home/rtokime/anaconda3`, NOT `~/miniconda3`): `pytest` green, coverage 81.87%, `ruff` + `mypy` clean. Graph rebuilt against the working tree (1631 nodes / 4013 edges).

| Axis | Grade | One-liner |
| --- | --- | --- |
| Finance core | A- | Deterministic engine with IO/amortization, refi, IRR, insight-aware modifiers; well tested (`src/core/finance/`). **Plus (Mission 4):** "What would have to change?" recourse module computes investor-actionable fixes for near-miss verdicts by re-running the engine, never inverting formulas. |
| Ingestion & media | B+ | File/URL ingest with fetch policy + robots; media discovery/download/manifest; opt-in phash/quality/hero intelligence. In-progress API refactor parked (broken; `git stash@{0}`) for a dedicated branch. |
| CV / AI | B | Closed-set ontology + provider seams; `vision`/`llm` providers are deterministic stubs by default, but users can bring their own ONNX model via CLI (`--onnx-model` / `--onnx-labels`, Mission 3). Six filename-inferred labels become detector-confirmed when a real model is registered. |
| Orchestration | B | Clean deterministic pipeline; CrewAI engine is a validated parity shell (`kickoff()` never called). **Plus (Mission 4):** recourse computation wired when near-miss criteria met. |
| Market / scenarios | B+ | `src/market` (snapshot, hypotheses grid, rejector, regional income) now **wired** into the pipeline + report as an opt-in prior-weighted scenario overlay (Mission 1: `adapter.py`, `scenario_runner.py`). **Plus (Mission 4):** `recourse.py` module for actionable recourse computation. |
| Reports | A- | Rich Markdown reports (baseline/stress/NOI valuation tables, media overview) **plus** a principled opt-in "Market Scenarios" section (prior-weighted DSCR/CoC/CF/IRR bands, honesty framing) replacing ad-hoc env-knob stress as the scenario story. **Plus (Mission 4):** "What would have to change?" section adjacent to Investment Thesis for near-miss verdicts, with investor-movable changes expressed in multiple currencies. |
| Advisor / intelligence | B | Multi-deal fusion, composite scoring, ranking, portfolio summary via `deal-advisor` CLI. |
| Packaging / distribution | B | `pyproject.toml` has `[project]` metadata (`pip install -e .` works, console scripts live); both fixed in Mission 1 Wave 0.2. Runtime deps via lockfiles (Mission 4). |
| Docs | A | Fully reconciled 2026-08-29 (Mission 4 task I.4). |
| Tests / CI | B+ | 87 test files; 80% coverage gate on core/schemas/market; ruff + mypy strict in CI. **Plus (Mission 4):** RED suite for recourse (non-independence trap, cheapest-first ordering, honest-null, determinism). |

---

## 2. Mission history

| # | Mission | Status | Dates |
| --- | --- | --- | --- |
| — | (pre-tracker) v0.1.0 MVP, media pipeline, CV v2, advisor/intelligence, address parsing | Shipped organically | 2025-09 → 2025-11 |
| 1 | Scenario Intelligence (wire `src/market` into pipeline + reports; Wave 0 packaging fix; authorized IRR-solver core fix) | **Shipped and pushed** — Roger's mission gate approved; merged to `main`, and `main`'s subsequent history (including Mission 2) reached `origin/main` on 2026-08-05 (see §3, "`origin/main` has never received Mission 1" row) | 2026-07-23 → 2026-07-24 |
| 2 | Close the end-to-end wiring gaps (Tier 0 false-report fixes, Tier 1 silent-drop wiring + anti-regression guard, Tier 3 CLI honesty, T4/T5 wire-first disposition) | **Shipped, merged, released, pushed** — Gate 3 passed (principles-guardian VETO lifted, staff code review approved); merged `--no-ff` as `8b2acf8` ("Merge Mission 2: close the end-to-end wiring gaps"), released as v0.3.0 (`652acd7`), CI fixed and green at `66ffacd`, mission closed at `8ed9397`. **Merged AND pushed — local `main` in sync with `origin/main`** (verified 2026-08-19: `git rev-list --left-right --count origin/main...main` = `0 0`). 27/28 tasks done; the remainder (3.1c) is a threshold decision for Roger, not engineering work (branch `mission/2-wiring-gaps`) | 2026-08-03 → 2026-08-05 |
| 3 | Bring-your-own ONNX photo provider (offering 1 of backlog #3: wire `register_onnx_provider` to a real `--onnx-model`/`--onnx-labels` CLI + env path; adjudicated 70/30 labels; docs) | **Shipped, merged, pushed** — all four gates cleared; **Roger's manual validation 9/9 PASS 2026-08-29**; merged `--no-ff` as **`8b59399`** and pushed (also carried the previously-unpushed Mission 2 validation record `6d9c000`); `origin/main...main` = `0 0`. Branch `mission/3-byo-onnx-provider` | 2026-08-19 → 2026-08-29 |
| 4 | Actionable Recourse ("What would have to change?") — near-miss recourse via re-run-the-engine bisection (backlog #6); plus the finance-core perf work it forced (charter amendment: `engine.py`/`irr.py`/`amortization.py` rewritten for perf + a real solver-crash fix; golden re-baselined) | **Shipped, merged, pushed** — Gate D + Gate V cleared 2026-08-20; **Roger's manual validation 9/9 PASS 2026-08-31** (one defect found and fixed in-pass: Case 7 benchmark; `BUDGET_MS` re-baselined 120→250 ms, ratified); merged `--no-ff` as **`7cfd449`**. Branch `mission/4-actionable-recourse` | 2026-08-29 → 2026-08-31 |
| 5 | Forward-Mode Differentiation & Optimized Recourse Search (backlog #9) — **Half A** the 1e-9 anchored tolerance rule + the digest-pinned anti-ratchet anchor, plus the recourse-loop acceleration (aggregate-income seam + scoped GC); **Half B** multi-lever recourse — 11 minimal-ask propositions, one per lever subset, unranked, smallest total ask labelled, behind a unified all-four-lever plausibility gate; plus a margin-of-safety report section (new scope) and the folded-in open items (#10 money-field bounds, #11 horizon 100 + clean CLI message, #12 `GENUINELY_CLOSE_MAX_FAILS`) | **Shipped, merged — NOT YET PUSHED** — **Roger's manual validation 17/17 PASS 2026-09-01**; merged `--no-ff` as **`dc240bc`**. **Two charter premises were measured and retracted rather than kept:** AD-Newton was rejected on measurement (a dual pass costs ~4× a plain pass) and **the 30 ms target was not met** (71.4 ms, from 459.5 ms, via the seam + GC, neither of which is AD). AD ships as direction selection only. Branch `mission/5-forward-mode-differentiation` | 2026-08-31 → 2026-09-01 |

---

## 3. Blocker / pre-condition ledger

| Blocker | Gates | Status |
| --- | --- | --- |
| Uncommitted working-tree changes on `main` (core.zip deletion, .gitignore, doc reconciliation) | Any mission branching from main | **Closed 2026-07-24** — landed on `main` (Mission 1 Wave 0) |
| `pyproject.toml` missing `[project]` metadata (broken install, dead console scripts) | Truthful CLI docs; distribution; UI missions | **Closed 2026-07-24** — `[build-system]`+`[project]`+discovery added (Mission 1 Wave 0.2); `pip install -e .` + 3 console scripts verified |
| Media-intelligence API refactor incomplete/broken (caller `insights.py` + tests not propagated to new signatures; ruff/mypy/tests red; env-dependent `_dct2` pHash) | Any work touching `src/core/media/` | **Open 2026-07-24** — orphaned WIP parked in `git stash@{0}`; deferred to its own branch `feat/media-intelligence-refactor` (NOT Mission 1). Fix list in `MISSION_1_SPRINT_TRACKER.md` parking note |
| GitHub SSH **signing** key not registered ("Dell Laptop" key is an auth key only) | Verified commits; clean pushes without admin bypass | **Open 2026-07-24** — commits SSH-signed locally (git 2.55 shim, `~/.gitmodern-bin`) but show Unverified; Roger to add the key as a Signing key in GitHub settings |
| `CITATION.cff` version `1.0.0` ≠ `pyproject`/CHANGELOG `0.1.0` | Any version tag / release cut | **Closed 2026-08-05** — the v0.3.0 release (`652acd7`) reconciled both to `0.3.0`; verified against `main @ 8ed9397` on 2026-08-19 (`CITATION.cff` and `pyproject.toml` both read `0.3.0`). |
| No real AI provider (vision/LLM stubs only) | Any "AI-powered" marketing claim; CrewAI kickoff mission | **Partially closed 2026-08-20** — backlog #3, offering 1 (bring-your-own ONNX model) documented and shipped via Mission 3 Wave I.3. Users can now pass `--onnx-model` / `--onnx-labels` (or env vars) to `ingest-listing` to register their own classifier. The six filename-inferred labels become detector-adjudicated (confirmed or contested) when a real model is registered. Offerings 2 (hosted API key) and 3 (project-shipped ViT) remain OPEN backlog. |
| Doc drift | Planning on stale docs | **Closed 2026-08-05** — Mission 2 T6 found `README:46-47` (no-op ingest cmd), `CHANGELOG:17` (claims dead narrative/report builders + scenario what-ifs ship), `market/README:22,86` (documents dead `regional_income` as public), `reports/README` (signatures omit `media_report`/`provenance`); fixed in Mission 2 Wave 2. **Re-opened and re-closed 2026-08-19** — a doc-maintainer audit against `main @ 8ed9397` found new drift introduced by the post-release CI fix (`ee023ee`, agent shells no longer built eagerly) and the dependency lock (`66ffacd`): `src/agents/README.md`, `src/orchestrators/README.md`, and root `README.md` still described all three CrewAI agent classes as building an Agent/Task shell, and the "Deps"/install sections omitted `requirements.lock`. Fixed the same day; see the `_Last reconciled` stamps in those files. |
| **`origin/main` has never received Mission 1.** Local `main` diverged at Mission 1's merge and every commit since compounds on top (7 at charter time → 9 at Mission 2 branch-point: + mission-zero `6147839`, + the Mission 2 docs commit; the mission branch adds more) | Any push; Mission 2 Wave Integrate | **Resolved 2026-08-05** — Mission 2 merged (`8b2acf8`), released as v0.3.0 (`652acd7`), and pushed; CI green at `66ffacd`. Verified 2026-08-19: `main` and `origin/main` both resolve to `8ed9397` (`git rev-list --count origin/main..main` = 0). |
| Report asserts false claims (`cap_rate_floor` unread → "respects the floor policy" always prints; lone `--listing` inherits default bundle financials) | Truthful reports | **Closed 2026-08-05** — OPD-2 shipped: `run_financial_model` now reads `market.cap_rate_floor` and emits the "cap rate below floor" warning (verified at `src/core/finance/engine.py:305-308` against `main @ 8ed9397` on 2026-08-19); the `--listing`-without-`--config` case now loud-fails (`main.py::resolve_config_path`) instead of borrowing the demo bundle's financials. |
| OPD-1..4 (Mission 2 product decisions) | Mission 2 Waves 0.2 / 3 | **SHIPPED 2026-08-05** (decided by Roger 2026-08-03, then executed and merged in Mission 2 — no longer just resolved-on-paper): OPD-1 `strategist.py` reconciled then **deleted** (verified absent at `main @ 8ed9397`); OPD-2 F1 cap-floor warning **wired into `run_financial_model`**; OPD-3 Tier-4 wire-first landed (un-wireable `orchestrator.py`/`agents/listing_ingest.py` deleted; the toy `scenarios.py`/`narrative_builder`/`report_builder` deleted at the Gate-3 founder ruling; `--regional-income` kept); OPD-4 Tier-5 fields **populated into the reports** (cap-floor value, media schema/ontology/provenance rows). Confirmed live on 2026-08-19 via the Mission 2 manual-test pass. |
| Transforms rebuild models field-by-field (silent field-drop); nothing tests end-to-end reachability | Any new schema field surviving to the report; truthful CLI/doc claims | **Closed 2026-08-05** — Mission 2 shipped the anti-regression sentinel-model builder (`tests/utils.py:659`) and feature→reachable-path guards (`tests/integration/test_cli_reachable_paths.py`, `tests/orchestrators/test_baseline_outlook.py:94`); verified present against `main @ 8ed9397` on 2026-08-19. |

---

## 3a. Standing process rules (Roger, 2026-08-05) — apply to EVERY mission

**1. Never dispatch agents without `staff-cost-aware-model-router`.** Not "when the call is
ambiguous" — always, before a batch of dispatches. Record `task → agent → tier` and any deviation
**at dispatch time**, not in a post-mortem.

**2. Never run without the graphify CLI. Refresh the graph after EVERY code update** (Roger,
2026-08-05) — not at milestones, after each update that lands, so the next step always reads
accurate data. In practice: after each commit, or as each batch of agents lands.

**Why these are rules rather than guidance** — both failed in Mission 2, the same way:

- I declined to spawn the router at kickoff, reasoning that its charter says invoke it only for
  *ambiguous* calls and the planner's table was unambiguous. Defensible in isolation. But I then
  drifted from that table — dispatching ~4 tasks the charter rated `std` (sonnet) at `opus` — and
  never logged it, despite my own note saying to. Roger caught it. **The failure was not the
  reasoning; it was that nothing forced me to notice I had left the plan.**
- The graph went ~50 commits stale while I fell back to greps. A stale edge claiming
  `chief_strategist` calls `form_thesis` nearly blocked a correct deletion, and I initially
  "verified" it against today's tree rather than against the graph's own commit — the wrong
  comparison, which happened to give the right answer.

**Operational notes:**
- `graphify update . --force` — `--force` is **required** after deletions, since the rebuild has
  fewer nodes and the tool refuses to shrink the graph otherwise.
- **Back up `graphify-out/graph.json` first.** It is gitignored; there is no other safety net.
- **Never rebuild while subagents are mid-write** — concurrent rebuilds corrupt the output. Refresh
  at quiet points, between waves or after a commit.
- Confirm any graph edge against the file **at the graph's own `built_at_commit`**, not against the
  current tree. Those are different propositions.

## 3b. Architecture decision — where the agent layer begins (Roger, 2026-08-05)

**An agent exists only where a model might one day enter. Everything deterministic is called
directly in `core/`.**

**Why this came up.** Mission 2 found ~10 dead modules and the disposition looked like a
wire-or-delete chore. Digging into the history showed it was not: they are **two half-finished
architecture migrations pointing in opposite directions**, and neither could be finished without
choosing a direction first.

| Migration | Evidence | Status |
| --- | --- | --- |
| **Agents as a uniform wrapper layer** — orchestrators talk to agents, agents wrap core | `agents/photo_tagger.py` ("thin policy wrapper that delegates to the CV stack") and `agents/listing_ingest.py` ("wraps `ingest_listing` and adapts the result for orchestrators"), both created alongside the pipelines they wrap, both documented in `src/agents/README.md:62,66` | **Abandoned in practice** — `crew.py` imports 3 agents then reaches straight past them into `core.cv`, `core.media`, `core.reports` |
| **Pull deterministic logic out of agents into core** — `core/strategy/strategist.py`, added 2025-10-19 in *"Implement financial intelligence layer"*, the same commit that created `core/finance/engine.py` and deleted `tools/financial_model.py` | `chief_strategist.py` predates it by a month (2025-09-15), so `strategist.py` is **not** legacy — it is the newer, unfinished half of that move | **Stranded** — the agent kept its own copy |

**The decision draws the line where it actually matters**: an agent is where a model *could* enter;
`core/` is where one never does. That is the same boundary as Roger's R-1 verdict ruling (a model may
observe, only rules may decide), applied to package layout instead of to control flow.

**Disposition rule this yields:**
- Wraps something deterministic, adds no model seam → **delete the wrapper**, call core directly.
- Deterministic logic sitting in `core/` with no caller → **wire it**, it is already in the right place.
- A model might plausibly enter → **keep the agent** (listing analysis: text/vision; strategy: the
  crewai seam, even though the verdict itself is now always deterministic).

**Known consequence, deliberately deferred.** By this rule `financial_forecaster` (documented as never
LLM-backed) and arguably `chief_strategist` (whose verdict is now always deterministic) belong in
`core/`. That is a real refactor with real blast radius and it is **not** Mission 2 work — Mission 2 is
a wiring-gap mission. Recorded here so a future planner inherits the reasoning rather than
rediscovering it, and so the two live agents are understood as *known exceptions under review*, not as
counter-examples that undermine the rule.

## 4. Opportunity backlog (leverage-ranked)

| Rank | Candidate | Reward | Blast | Seam | Gap closed | Axes moved | Pre-conditions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ✅ 1 | **Scenario Intelligence** — wire `src/market` hypotheses/rejector into pipeline + report scenario section | **SHIPPED 2026-07-24 (Mission 1)** — delivered exactly as scoped; Market C→B+, Reports B+→A-; plus an authorized IRR-solver core fix | — | — | Market C→B+, Reports B+→A- | Market, Reports, Orchestration, Docs | — done |
| ✅ 2 | Packaging metadata fix (`[project]` table) | **SHIPPED 2026-07-24 (Mission 1 Wave 0.2)** — Packaging D→B; `pip install -e .` + 3 console scripts verified | — | pyproject only | Packaging D→B | Packaging, Docs | — done |
| 3 | **Real vision provider behind the existing CV seam** — see the detailed note below, added 2026-08-03 at Roger's request. **Slice sub-1 (BYO ONNX model) CHARTERED as Mission 3, 2026-08-19** — the lowest-blast offering, wiring the existing `register_onnx_provider` to a real CLI/env path; offerings 2 (hosted API key) and 3 (shipped ViT) remain OPEN backlog. | High (makes the "AI" headline true) | **sub-1 (ONNX): near-zero** (additive CLI/env wiring + provider-selection at an existing seam; no finance/schema/ontology diff). sub-2/sub-3: Med-High (API keys, cost, non-determinism policy; training/licensing) | CV provider registry (`register_onnx_provider` **already exists**, `amenities_defects.py:441`; `build_photo_insights` selection seam `photo_insights.py:314-324`) | CV/AI C+→B (real user model path); unlocks the 6 filename labels | CV/AI, Orchestration, Docs | sub-1: none outstanding (Mission 2 honest-provenance + 70/30 rule landed). sub-2: determinism/key-hygiene policy. sub-3: training data + licensing |
| 4 | Streamlit UI for interactive scenario exploration | High (portfolio wow) | Med (new surface, new deps) | Reads existing JSON artifacts | Distribution | Packaging, Portfolio | #1 (scenarios give the UI something to explore), #2 |
| 5 | Live market data ingestion (comps, cap-rate drift) | Med | High (network, data licensing, freshness) | fetch/ policy | Market realism | Market | #1; compliance review |
| 7 | **F3 "Adjustments Applied" note is unreachable on real data** (found in the 2026-08-19 manual-test pass; documented as Mission 2 case F3 / defect #4). The report renderer correctly ships whatever OPEX-adjustment notes the engine emits, but the engine's triggers test **pre-normalization** strings (`"old roof"`, `"water stain"`) that the CV/label layer normalizes away before the engine sees them (e.g. `"water stain"` → `water_leak_suspected`), so on any real pipeline run the notes are empty and the section never appears. **Real defect, survived Mission 2.** | Low-Med (report honesty — a shipped section that can never populate on real input misleads by omission) | Med (fixing the engine side is inside `src/core/finance/`; fixing the normalization map has CV/label blast — a product decision) | engine OPEX-modifier ↔ CV-label vocabulary | Reports/Finance honesty | Reports, CV/AI | Roger decides which side moves (trigger/label reconciliation) |
| 8 | **Stale editable-install metadata** (found 2026-08-19): `pip show ai-real-estate-deal-analyzer` reports `Version: 0.1.0` while `pyproject.toml` reads `0.3.0`, because an earlier `pip install -e .` cached the old metadata. **Refreshed 2026-08-20** by re-running `pip install -e .`; `pip show` now reads `0.3.0`. Cosmetic; console scripts resolve and run correctly. | Very low (cosmetic; no functional impact) | Minimal (no source change; a re-install) | packaging | Packaging polish | Packaging | — |
| 9 | **Forward-mode (tangent-linear) differentiation + optimized recourse search** — **(Half A)** replace Mission 4's ~10–20-probe bisection with exact derivatives + Newton on the guardrail (~3–4 probes), shipping a **tolerance rule first** (relax bit-exact golden to ~1e-9 relative, anchored to the ORIGINAL golden, calibrated against the ~9.4e-8-relative shape of a `round(payment, 4)` defect — a **contract constant**, not a prior measurement, `git log --all -S"9.4e-8"` → only `87efd22`); **(Half B, EXPANDED IN by Roger 2026-08-31)** the **multi-lever recourse optimizer** — up to **11** minimal-ask propositions (one per lever subset), the cheapest labelled "cheapest total negotiation," gated by a **unified all-four-lever combination-plausibility gate**. **CHARTERED as Mission 5, 2026-08-31; scope EXPANDED same day to include Half B (was previously slated for a separate Mission 6, now folded in).** **⚠ CORRECTED 2026-08-31 (C4(b)):** the original rationale — AD as "the remaining path to Roger's 30 ms target" — was measured and refuted (Newton costs ~4× a plain evaluation per dual pass, 11–41 probes vs bisection's fixed ~11); the measured path to 30 ms is GC-threshold tuning + an aggregate-income seam that removes the rent-roll copy (74.5% of the budgeted row), neither touched by AD. AD ships as Half B's direction-selection/Jacobian enabler; **Half B — a product/capability gain — is now the mission's centre of gravity.** The original "top-3 actionable combinations" + Lagrangian/KKT design is likewise superseded (see `docs/plans/MISSION_5_SPRINT_TRACKER.md`, "FINAL HALF B ARCHITECTURE" / "ROGER'S GATE-D DECISION"). | High (portfolio-scale speed; algorithmic-differentiation credibility; + multi-lever recourse — richer, more actionable output) | **High — touches `src/core/finance/` (engine/irr AD) AND relaxes a values-level invariant** (bit-exact → tolerance); Half B adds a new optimizer + a unified plausibility gate. De-risked: tolerance rule ships first & is independently valuable; Gate D is a real go/no-go on the AD portion; **an internal AD go/no-go checkpoint gates Half B (NO-GO → Half B defers, Half A ships alone)**. | recourse search (`recourse.py` `_bisect`/`_rerun`/`_judge_plausibility`) + finance engine (`engine.py`, `irr.py` Brent) + golden harness + `rejector.py` (unified gate) | Finance/perf, Market, Reports, portfolio credibility | Finance core, Market, Reports, Tests | Guardian VETO on the invariant relaxation; perf go/no-go; **internal AD checkpoint before optimizer**; every number AND combination confirmed by a real engine re-run |
| 10 | **Money-field lower bounds** — `purchase_price` (and peers) accept negative values today (`models.py:24`, no `ge=`; and see the "silently unenforceable constraint" note `inputs.py:210`). A deliberate money-field pass, not one patch. | Low-Med (input honesty; a negative price should not validate) | Low (additive field constraints + clean error messages) | schema validation | Input robustness | Schemas, Tests | Founder-proxy confirms field list + floor semantics. **Folded into Mission 5 as an open-item disposition.** |
| 11 | **Raise horizon ceiling `le=50`→`le=100`** (`inputs.py:74`) — 99-year leases are real and work post-Mission-4. **CLI out-of-range-horizon also surfaces a raw pydantic traceback** with the useful message at the bottom (polish to one clean line). | Low (real leases fit; friendlier error) | Low (one constraint + one error-handling branch) | inputs validation + CLI | Usability | Inputs, CLI, Tests | Founder-ratified. **Folded into Mission 5 as open-item dispositions.** |
| 12 | **`GENUINELY_CLOSE_MAX_FAILS = 3`** (`recourse.py:143`) — the near-miss threshold, chosen by necessity during Mission 4 rather than decided. Needs a real product decision. | Low (a threshold Roger should own explicitly) | Minimal (a constant + its test) | recourse gate | Product clarity | Market | **Founder-proxy call folded into Mission 5 Gate D** (the one near-miss threshold the mission may decide). |
| 13 | **Integer-cents money representation (sibling/successor to Mission 5)** — represent money as integer cents so summation is order-independent (removing the constraint that limited Mission 4's vectorization) and money arithmetic is exact. **Named as a related/successor mission, NOT in scope for Mission 5.** | High (exactness + unlocks vectorization) | **High — refactors the finance core AND money-carrying schema fields** | finance core + schemas | Finance exactness, perf headroom | Finance core, Schemas, Tests | Sequenced after Mission 5; likely its own charter |

### Backlog #6 — "What would have to change?" (Roger's design, 2026-08-05)

_Captured verbatim from a design conversation during Mission 2. **Not built** — Mission 2 is a
wiring-gap mission and this is a new feature; smuggling it in is exactly what the charter forbids.
Recorded here while the design is fresh so the next planner inherits the decisions, not just the idea._

**The problem it solves.** Verdicts are pass/fail against hard lines, so a deal that misses debt
coverage by 0.01 gets the same stamp as one that misses by 0.5. Worse, the report states the gap in
*our* units — "DSCR is weak at 1.19 (< 1.20)" — which no investor negotiates in. Roger's objection,
verbatim: *"the unit of measurement does not talk to an investor. Can we find a way to make the
distance talk to an investor, like translating that distance to something tangible?"*

**The feature.** Keep the BUY / CONDITIONAL / DECLINE label, but attach to it *how far from the line
the deal sits* and *what would close the gap*, expressed in things an investor can actually move:

    CONDITIONAL — debt coverage falls just short.
    Any ONE of these closes it:
      - $38 more rent per unit per month (a 3.1% increase)   ⚑ flagged: already top-of-market
      - $9,800 off the purchase price (2.4% below asking)
      - 0.18% off your interest rate
      - $460 less in annual operating costs

One gap, several currencies; the investor picks the lever they have leverage on. The translation is
**exact arithmetic, not statistics**. No distribution is needed to answer "how far from flipping", which is a deterministic question.

> **Status note (2026-08-29, Mission 4 SHIPPED):** The initial framing said "invert the guardrail formula", but Roger's own discipline (see §6.5-6.7 below) later clarified the ONE discipline: RE-RUN THE ENGINE, never invert a formula. The trap that breaks a naive inversion is documented in §6.3 below and confirmed real on committed data. Mission 4 built it correctly: `compute_recourse()` bisects on each lever and re-runs the engine for every candidate answer. This is now shipped and delivered.

**Roger's design decisions (these are the specification, not suggestions):**
1. **Flag implausible levers, never remove them.** *"we provide theoretical results, and the investor
   may have other influence that we don't."* A silent removal asserts knowledge of their situation
   that we do not have. Say **why** it was flagged, and link sources once sourcing exists.
2. **When several guardrails fail at once**, lead with the cheapest single fix but **flag that other
   gaps remain** — a counter or a more elegant device — so a partial fix is never mistaken for a
   complete one.
3. **When nothing realistic closes it, say so plainly.** *"If no realistic change can be done, well it
   is what it is. We tell them."*

**Most of the machinery already exists.** Mission 1 shipped the scenario generator, the plausibility
rejector, and the report section that shows outcome bands across surviving scenarios (`src/market/`).
The missing question is *"which of these flip the verdict?"* — an addition, not a new subsystem.

**A design note worth preserving.** Roger's first framing reached for z-scores and a softmax over the
guardrail inputs to attribute "contribution" to the decision. That was talked through and set aside
for two reasons: softmax reports relative magnitude, not causation (a wildly-off IRR that changes
nothing would dominate, while a coverage ratio sitting 0.01 from the line would not), and the verdict
is a **count of failures**, not a weighted sum, so there is nothing to decompose. Distributions do earn
their place in judging **plausibility** — which is what the rejector already does. Keeping the verdict
deterministic also preserves Roger's own R-1 ruling that rules decide and models only observe.

**⚠ THE TRAP THAT WILL BREAK A NAIVE BUILD: the levers are not independent.** Confirmed by research
(the counterfactual-explanation literature calls these *causal constraints* — a suggested change must
not violate real relationships between variables). It bites immediately here:

- Cut the purchase price and **three** things move at once: the loan shrinks (debt service falls), the
  cap rate improves (NOI over a smaller price), and the cash-in changes.
- Raise the rent and NOI, cap rate, coverage and cash-on-cash all move together.

So algebraically inverting one guardrail formula in isolation gives **wrong numbers, and optimistic
ones** — the report would promise a $9,800 price cut closes a gap it does not close.

**The build must therefore RE-RUN THE ENGINE with the single input changed**, not invert a formula.
Slower, but it cannot drift from what the engine actually does. The pattern already exists —
`build_baseline_outlook` (`src/orchestrators/crew.py`) re-runs the engine for the comparison column.

**This was Roger's intent from the start** and is why he never described the inputs as orthogonal:
his original framing — *"pass the decision-shifting characteristic to our … keep-only-plausible-ones
service and see if the decision remains the same or can flip"* — meant **recompute the shifted
scenario, then test it for plausibility.** Recorded explicitly because the orchestrator initially
read it as a filtering step only, and a future reader could make the same mistake.

**Performance note (Roger, 2026-08-05).** Searching for the flip point across several levers × several
guardrails × the plausibility sweep is a lot of engine runs. Vectorising the arithmetic — numpy or
similar — is the intended optimisation. **Not needed for a first version**; recorded so it is a known
option rather than a rediscovery. Measure before optimising: the engine is pure and fast, and the
scenario runner already handles a grid.

**What the research confirmed** (searched 2026-08-05):
- The idea is an established field — **actionable recourse** / **counterfactual explanations**. Its
  canonical example is loan denial: *"if annual salary increased to $50,000, the application would be
  approved."* Same shape, different domain.
- **Offering several routes is the recommended practice**, for exactly Roger's reason: one person can
  move income, another can only move location. His several-currencies design matches it.
- **Flag-don't-remove is ahead of the standard approach.** The usual method filters to "mutable
  features" chosen by the system; recent work on *individualized* rather than universal actionability
  raises Roger's objection — the system does not know what this particular person can move.
- **Plausibility is the field's hardest open problem.** This project has a head start: the rejector
  already exists.
- The underlying arithmetic is **routine in commercial real estate** — break-even and sensitivity
  analysis, lenders stress-testing coverage against rent drops and rate rises. The distinctive part is
  presenting it to the investor as recourse rather than as risk.

**Interaction with Mission 2's open threshold decisions.** This feature makes hard lines far less
punishing, because a near-miss becomes legible rather than fatal-looking. A future planner should
revisit the Year-1 CoC floor and the DECLINE shortcut *after* this ships, not before.

**Status note (2026-08-29, Mission 4 SHIPPED).** Backlog #6 has been built, shipped, and is now live on `main`. The feature is complete as specified by Roger (2026-08-05): four levers (rent/price/rate/opex), flag-don't-remove for implausible moves, cheapest-single-fix ordering with remaining-gap counters, and the honest-null message when nothing realistic closes the gap. Every figure comes from re-running the engine, never from inverting a formula (the non-independence trap is real, measured on committed data: $2,243 gap in a real deal). A pre-computation "genuinely close" gate decides whether recourse is even attempted; when it is not, output is byte-identical. The feature appears adjacent to the Investment Thesis in the report when a near-miss CONDITIONAL verdict is found. Delivered in Mission 4 Waves I.1–I.4 (feature + schema + tests + docs); Gate D and Gate V passed 2026-08-20; Roger's manual validation 9/9 PASS on 2026-08-29; merged to `main` as commit `8b59399` and pushed.

### Backlog #3 in detail — why `--ai` is a stub, and what "real" looks like
_Added 2026-08-03 at Roger's request during Mission 2, so a future mission can plan it properly._

**What `--ai 1` does today.** It is wired end-to-end — `use_ai=True` reaches
`core.cv.build_photo_insights` — but the provider behind the seam is
`_provider_vision_stub` (`src/core/cv/amenities_defects.py:253-300`), a **deterministic heuristic, not
a model**. It infers labels from image statistics: notably `"street parking", parking_spots=1` from
`aspect == "landscape" and lum >= 0.50`, i.e. a property claim derived from a photo being wide and
bright. Switching it on changes **7 fields** of `PhotoInsights` (`amenities, version,
image_detections, amenity_counts, parking, detections_total, provenance`), so it is **not** inert —
Mission 2 corrected help text that wrongly said it was, and corrected the provenance labelling so
stub output is distinguishable from a future real classifier's.

**Roger's stated direction (verbatim, 2026-08-03):**
> "it's currently a stub, but in the long-run I want to hook it with either a custom classifier
> (fine-tuned for real estate and based on ViT; or a SOTA one; or even letting the user add their API
> key to a model or hook their own model)"

So there are **three distinct offerings** behind one seam, and they have different blast profiles —
a future mission should probably not treat them as one item:
1. **Bring-your-own-model (ONNX).** ⚠️ **Largely already built.** `register_onnx_provider(model_path,
   labels_path)` (`amenities_defects.py:161`) registers a user's own ONNX classifier behind the same
   provider registry, and raises a clear error if `onnxruntime` is absent. **It has zero callers and
   no CLI can reach it** — Python-API only. Making this real is mostly *wiring plus docs*, not new
   capability. Lowest blast of the three; highest ratio of value to effort.
2. **User-supplied API key to a hosted vision model.** Needs the cost/non-determinism/key-hygiene
   policy that gates this whole backlog item, plus a caching story (the CV cache is content-addressed
   by sha256, so it already suits this well).
3. **A fine-tuned real-estate ViT shipped by the project.** Largest effort: training data, licensing,
   model distribution size, and an accuracy claim the project would then have to stand behind.

**Second constraint, and the thing that makes a real provider immediately valuable** (Roger, 2026-08-04,
Mission 2 R-6): a filename may **suggest** a label; only a detector that actually examined the pixels
may **confirm** it. Confirmed labels score **70% detector confidence + 30% filename corroboration**;
labels no provider is capable of detecting stay unscored hints and never move a dollar.

Providers therefore declare the vocabulary they can detect — which `register_onnx_provider`'s
`labels_path` already is. That declaration is what flips a label from "nothing can see this" to
"something looked", so **a real classifier upgrades the six filename-inferred labels
(`mold_suspected`, `water_leak_suspected`, `ev_charger`, `parking_garage`, `parking_driveway`,
`dishwasher`) with no code change**. Today the ontology can express all six and no built-in provider
emits any of them, so all six are unscored hints. Whichever offering above ships first should be
judged partly on how much of that vocabulary it covers.

**Constraint any of these must respect** (established by Mission 2, Roger's ruling): the AI layer
produces **observations only**. All arithmetic stays in `src/core/finance/`, and the
BUY/CONDITIONAL/DECLINE verdict must come from the deterministic `synthesize_thesis` — an AI must
never author it. Mission 2 also added AI-impact transparency to the report (baseline vs
AI-influenced, with per-line attribution of what each observation changed), which any real provider
inherits for free.

---

## 5. Current recommendation

> ## ✅ MISSION 5 SHIPPED — validated by Roger 17/17 PASS, 2026-09-01; merged `--no-ff` as `dc240bc`; **not yet pushed.**
>
> **No mission is currently chartered.** Picking the next one is the mission-planner's next run — it is
> deliberately not chosen here, because choosing it is a planning job (reconcile the docs to what Mission 5
> actually shipped, then rank what is now highest-leverage), not a bookkeeping one.
>
> **What Mission 5 leaves on the table for whoever charters next**, stated plainly so it is not rediscovered:
> the **30 ms perf target is still unmet** (71.4 ms on Roger's box; the perf gate sits at 250 ms because a
> 30 ms gate would flake on a ±12% spread); **backlog #13, integer-cents money**, is the named successor and
> is the thing that would make money arithmetic exact and unlock the vectorization Mission 4's summation-order
> constraint blocked; and **this mission's own sprint tracker stopped being updated at Gate D**, which is a
> process failure worth fixing before the next mission runs, not just a stale file.
>
> _The text below is the CHARTER-TIME recommendation, kept as history. It describes the mission as planned —
> including the AD-Newton framing and the top-3 combination design, both of which were superseded during
> execution. Read it against §2's Mission 5 row and the manual-testing document for what actually shipped._

**Mission 5 — Forward-Mode Differentiation & Optimized Recourse Search — CHARTERED 2026-08-31; scope
EXPANDED by Roger the same day; mid-flight (Discovery/Gate D in progress as of this entry).** Baseline
`main @ 7cfd449` (Mission 4 merged, Roger-validated 9/9 2026-08-31); branch
`mission/5-forward-mode-differentiation`. Backlog #9. **Two halves, run in sequence with a hard internal
AD go/no-go checkpoint between them.** **Half A** replaces Mission 4's ~10–20-probe bump-and-reprice
bisection with **exact derivatives + Newton on the guardrail** (~3–4 probes). **Half B (EXPANDED IN, was
to be a separate Mission 6)** adds a **multi-lever recourse optimizer** — up to **11** minimal-ask
propositions (one per surviving lever subset, gate-filtered, unranked), the smallest-total-ask one
labelled "cheapest total negotiation," AD-gradient-seeded and solved by subset-restricted bisection, with
feasibility from a **unified all-four-lever combination-plausibility gate** (the core new engineering:
today `_judge_plausibility` `recourse.py:609` judges one lever at a time; rent/opex have no rejector
axis). Coordinates stay the interpretable real levers (no PCA/eigen/SVD/LDA, no learned surrogate —
recorded one-reason rationale in the charter). **Neither half violates "re-run the engine, never invert a
formula":** every single-lever answer AND every proposition is confirmed by one real, un-differentiated
engine re-run. **A tolerance rule ships FIRST and gates all AD work:** relax the bit-exact golden to
~1e-9 relative, **anchored to the ORIGINAL golden**, calibrated against the ~9.4e-8-relative shape of a
`round(payment, 4)` defect (a **contract constant** — `git log --all -S"9.4e-8"` finds no prior
measurement of it, only this mission's own charter — not a claim it was previously caught in
production); approaching-tolerance demands written justification.

> **⚠ CORRECTED 2026-08-31 (C4(b) documentation sweep).** The paragraph above describes the CHARTERED
> plan. Discovery has since measured that **AD is not the path to the honest current baseline's speed
> target** (best 175–198 ms / median 181–203 ms quiet against `BUDGET_MS = 250.0`; "73 ms" is retracted
> by Roger himself at `docs/manual testing/MISSION_4_MANUAL_TESTING.md:513`, and "30 ms" is Roger's
> stated target, never a measurement) — Newton-on-guardrail measured 11–41 probes vs bisection's fixed
> ~11 because a dual pass costs ~4× a plain evaluation. The dominant cost is the rent-roll copy (74.5%
> of the row) and garbage collection (~35%, 183.5 ms → 117.7 ms tuned), neither of which AD touches.
> **Roger's decision: rewrite the rationale, ship the full scope.** AD's real justification is Half B's
> direction-seeding/sensitivity Jacobian (one forward pass yields all partials at ~4.1–4.4× an engine
> pass vs 8 passes for central finite differences), not speed — **Half B, a product/capability gain, is
> now the mission's centre of gravity.** The original "top-3 actionable combinations" + Lagrangian/KKT
> design (in the paragraph above) is superseded by the "≤ 11 propositions, unranked, labelled cheapest"
> design already folded into the paragraph above as of this correction. Full record:
> `docs/plans/MISSION_5_SPRINT_TRACKER.md` ("FINAL HALF B ARCHITECTURE", "ROGER'S GATE-D DECISION").

Artifacts: `docs/plans/MISSION_5_forward_mode_differentiation.md` (charter),
`docs/plans/MISSION_5_SPRINT_TRACKER.md`, `docs/plans/MISSION_5_HANDOFF.md` (pasteable prompt),
`docs/plans/MISSION_5_PLAIN_ENGLISH.md`, `docs/manual testing/MISSION_5_MANUAL_TESTING.md`.

**Why now / why this one.** Highest strategic reward on the board after four wiring/feature missions: it
adds real quant-desk credibility (algorithmic differentiation) and now, per the correction above,
primarily makes recourse output materially richer (bundles, not just single levers) — that richness,
not perf, is the mission's centre of gravity. Blast is **High
and honestly flagged** — it touches `src/core/finance/` (engine/irr AD), relaxes a **values-level
invariant** (bit-exact → tolerance), and Half B adds an optimizer + a unified plausibility gate — but
Mission 4 already opened the finance-core door, and the mission is de-risked by **three** structural
devices: the tolerance rule is **independently valuable and ships first**; **Gate D is a genuine go/no-go
on the AD portion**; and an **internal AD go/no-go checkpoint gates Half B** so the optimizer builds only
on a proven Jacobian (NO-GO → Half B defers, Half A ships alone; a wrong proposition is then
unambiguously an optimizer bug, not an AD bug). Guardian VETO on the invariant relaxation is
**mandatory** at Gate D. Three low-blast
open items fold in with their own RED tests: money-field lower bounds (#10), horizon `le=50`→`le=100` +
CLI clean-error (#11), and the `GENUINELY_CLOSE_MAX_FAILS` product call (#12). **Integer-cents money
representation (#13) remains the named sibling/successor mission, explicitly NOT in scope.**

> **Planner's registered over-scope concern (Roger has read it and elected to expand anyway).** Combining
> Half A (gnarly AD through a bracketed Brent root-find + a values-level invariant relaxation) with Half
> B (a constrained optimizer + a new unified plausibility gate + a new report section) in one mission is
> a lot of high-blast, high-uncertainty work for a solo dev — the split into a Mission 6 would have given
> a clean debugging boundary. Roger overrode the split; the internal AD checkpoint is the device that
> preserves that boundary without needing two missions. If Phase B sprawls past the cap even after a
> clean checkpoint, the orchestrator surfaces it to Roger as a candidate to carve Half B back out.

**Where the rest of the backlog stands (candidates, not the current pick):**
- **#13 Integer-cents money** — the named successor to Mission 5 (exact money arithmetic; unlocks
  vectorization); likely its own charter after Mission 5.
- **Multi-lever recourse optimizer** — no longer a separate candidate: **folded into Mission 5 as Half B**
  (2026-08-31). There is no Mission 6 for it.
- **#4 Streamlit UI**, **#5 live market data** — unchanged.
- **#7** the unreachable F3 "Adjustments Applied" note (real, report-honesty) — **still open**, not
  addressed by Missions 3–5; a future report-honesty candidate.

**Still-open blockers that gate certain futures (§3):** no real AI provider yet (gates any
"AI-powered" claim); the GitHub SSH **signing** key remains unregistered (commits show Unverified);
the parked media-intelligence refactor (`parked/media-intelligence-refactor`) still gates any
`src/core/media/` work.

---

## 6. Changelog

* **2026-09-01 (Mission 5 CLOSED — Roger validated 17/17 PASS; merged `--no-ff`, NOT pushed).** Roger ran
  all 17 cases of `docs/manual testing/MISSION_5_MANUAL_TESTING.md` by hand and every one passed; the
  document-level box reads VALIDATED and each case row now carries his own measured output rather than the
  orchestrator's. Two of his numbers differ from the recorded observations and **his were written into the
  doc**: Case 5 measured 459.5 → 71.4 ms (against 65.5 from 438) and Case 16 took 50.85s (against 32.89s) —
  timing only, on a slower box, with every conclusion unchanged. One procedural deviation, checked and
  cleared by him: `$OUT` was `/tmp/m4` rather than a fresh `/tmp/m5`; he verified no stale file was read.
  Mission 5's work was committed on `mission/5-forward-mode-differentiation` and merged `--no-ff` to `main`
  as **`dc240bc`**. **`main` is not pushed** — it carries the merge, the work commit, and the
  charter commit `87efd22` that has been unpushed since 2026-08-31; Roger controls the push. **Also recorded,
  because it is a process failure and not a detail:** `docs/plans/MISSION_5_SPRINT_TRACKER.md`'s status blocks
  and task rows stopped being updated after Gate D and still read "0 / 26 DONE" mid-execution. They were
  **not** retro-fitted with reconstructed statuses — a banner at the top of that file marks them stale and
  points at the artifacts that were actually verified (the manual-testing doc, the CHANGELOG's Gate V entries,
  the code and tests). Fixing the tracker discipline belongs to the next mission's charter.

* **2026-08-31 (Mission 5 — C4(b) documentation correction sweep, docs-only, no code, no git ops).**
  The guardian ruled four documented claims did not survive measurement and directed a correction sweep
  (`staff-documentation-maintainer`, sonnet STANDARD) before Gate V. **(1)** The retracted "73 ms, down
  from 13 s" figure struck everywhere found — it is Roger's own retraction at
  `docs/manual testing/MISSION_4_MANUAL_TESTING.md:513`, from a superseded harness no longer in the
  tree; honest baseline is **best 175–198 ms / median 181–203 ms** quiet against `BUDGET_MS = 250.0`,
  and **30 ms is Roger's stated target, never a measurement.** **(2)** "~9.4e-8" relabelled everywhere
  as a **contract calibration constant** bound to the reproducible `round(payment, 4)` recipe (real
  measured signature **1.1325e-7** across 1,613 fields), not a prior measurement — `git log --all
  -S"9.4e-8"` returns only this mission's own charter commit `87efd22`. **(3)** "Seven live guardrails"
  corrected to "(up to) six" in every instance found (`README.md:291`, `CHANGELOG.md:10`/`:11`,
  `src/market/README.md:28`/`:70`, `src/schemas/README.md:76`, plus one more found in this sweep,
  `docs/manual testing/MISSION_5_MANUAL_TESTING.md:66`) — `cf_all_ok` is pinned `True` by the shipped
  `REQUIRE_POSITIVE_CF_ALL = False` (`src/agents/chief_strategist.py:56`) and can never fail; the
  seventh (`cap_floor`) is live only when `market.cap_rate_floor` is set. Two further instances left
  **unedited, reported to their owning agents**: `src/market/recourse.py:135` (module docstring) and
  `src/agents/chief_strategist.py:83` (`GuardrailChecks` docstring) — both `.py` files outside this
  sweep's remit. **(4)** The mission rationale rewritten per Roger's decision: AD is **not** "the
  remaining credible path to 30 ms" (Newton-on-guardrail measured 11–41 probes vs bisection's fixed
  ~11, a wash or a loss at ~4× cost per dual pass); the measured path is GC-threshold tuning +
  removing the rent-roll copy (74.5% of the row) via an aggregate-income seam. AD's justification is
  Half B's direction-selection/sensitivity Jacobian, not speed. **Half B's original "top-3 actionable
  combinations" + Lagrangian/KKT design is superseded** by Roger's settled architecture: **≤ 11
  minimal-ask propositions** (one per lever subset), unranked, the smallest-total-ask one labelled
  "cheapest total negotiation" (a computed `argmin`, not a search). Edited: charter, handoff,
  plain-English brief, manual-testing doc, this ledger (§4 row 9, §5), `README.md`, `CHANGELOG.md`,
  `src/market/README.md`, `src/schemas/README.md`. Full measured record:
  `docs/plans/MISSION_5_SPRINT_TRACKER.md` (D.1, D.2, D.3, D.5 results; "FINAL HALF B ARCHITECTURE";
  "ROGER'S GATE-D DECISION") — not edited (orchestrator-owned).
* **2026-08-31 (Mission 5 RENAMED — "Adjoint" was technically wrong; caught by Roger).** The mission,
  its branch, its charter filename and its docs all said **"Adjoint Differentiation."** **Adjoint
  differentiation (AAD) means REVERSE mode**, whose whole value is **many inputs → few outputs.** This
  problem is **inverted — 4 levers in, 8 metric rows out** — and Discovery measured accordingly:
  **reverse-mode Wengert tape 6.9x an engine pass vs forward-mode `Dual4` 4.11x**, so **forward mode was
  chosen** (D.1, re-confirmed by D.5). What `src/core/finance/dual.py` and `jacobian.py` actually
  implement is **forward-mode (tangent-linear) AD** — the opposite of an adjoint. Roger: _"a quant
  reviewer spots this in ten seconds."_ **Renamed before Gate V:** branch
  `mission/5-adjoint-differentiation` -> **`mission/5-forward-mode-differentiation`**; charter
  `MISSION_5_adjoint_differentiation.md` -> **`MISSION_5_forward_mode_differentiation.md`** (via
  `git mv`, history preserved); title -> **"Mission 5 — Forward-Mode Differentiation & Optimized
  Recourse Search"** across the charter, handoff, plain-English brief, sprint tracker, manual-testing
  doc, this ledger, and two shipped docstrings in `tests/core/finance/`. **Deliberately KEPT:** the
  passages that explain *what AAD is and why it was rejected* (handoff L71, charter L145) -- those uses
  are correct and load-bearing; and the verbatim quote of commit `87efd22`'s message, which is immutable
  history. Nothing about the implementation changed -- **only the label, which was describing the
  algorithm we measured and did not build.**

* **2026-08-31 (Mission 5 SCOPE EXPANDED by Roger — Half B multi-lever optimizer folded in; docs-only,
  no code, no git ops).** Roger decided to **expand Mission 5 to include the multi-lever recourse
  optimizer** (Half B) rather than defer it to a separate Mission 6, overriding the planner's
  split recommendation. Updated the five existing (uncommitted) Mission 5 artifacts **in place** (same
  filenames; human title broadened to "Adjoint Differentiation & Optimized Recourse Search" -- **a name
  since CORRECTED, see the 2026-08-31 renaming entry below**) plus this ledger. **What Half B adds:** a **second report
  section, "top-3 actionable combinations",** alongside the existing single-lever menu (Roger: offer
  both — we don't know if the investor can move one lever or several). It is a **constrained optimization**
  (Lagrangian/KKT — augmented Lagrangian / SQP / projected-gradient / interior-point, chosen by
  measurement in Discovery) over the four levers, consuming Half A's exact AD Jacobian, made global by
  **deterministic multi-start** (fixed grid/scatter seeds, never stochastic). **Design decisions settled
  with Roger and recorded so they are not re-litigated:** feasibility-not-optimization (FILTER to
  plausible combinations, no cross-lever cost normalization; the plausibility gate is a deterministic
  boolean feasibility projection, not a differentiable objective term — the gradient comes from the
  guardrail margins); normalization-free top-3 selection (parsimony · within-axis magnitude · diversity,
  DiCE-style); interpretable real-lever coordinates only (a blended/singular direction may be an internal
  heuristic, translated back before display). **The core new engineering task** is a **unified
  all-four-lever joint combination-plausibility gate**: grounded against the code at `7cfd449` —
  `_judge_plausibility` (`recourse.py:609`) unites `_rejector_flagged` (`recourse.py:519`, reusing
  `reject_unrealistic` `rejector.py:68`) and `_magnitude_flagged` (`recourse.py:584`) but judges **one
  lever at a time**; the rejector's real cross-axis rules (`|interest_rate_delta − cap_rate_delta| ≤
  0.02` `rejector.py:23`; `rent_delta ≥ +0.03 ⇒ vacancy_delta ≤ +0.015` `rejector.py:38-41`; STR
  coherence `rejector.py:44-64`) operate on **market-hypothesis deltas**, two of the four recourse levers
  (rent, opex) have **no** rejector axis, and price reaches it only via a cap-rate proxy — which is why
  Mission 4 bolted on `RATE_MAGNITUDE_THRESHOLD` (`recourse.py:130`) and `_MAGNITUDE_RELATIVE_THRESHOLD`
  (`recourse.py:120`). Unifying these into one gate that judges a **full four-lever combination**
  (including joint plausibility — e.g. cutting price AND raising rent may each be individually fine yet
  jointly implausible) is the real design work; **what makes a combination plausible is a founder-proxy
  product call.** **Recorded the ONE-REASON rationale for rejecting learned/decomposition methods** (no
  CNN/MLP, no learned surrogate, no TPE/Bayesian optimization, no PCA/eigen/SVD/LDA for the user-facing
  answer): we OWN the exact, cheap, post-Half-A-differentiable generating function; every
  learning/decomposition tool targets the opposite regime (expensive/unknown/noisy function, or data
  needing reduction); classical numerical optimization on the real model is the correct and robust family
  precisely because Roger generates and controls the data (and eigen/SVD/LDA axes are uninterpretable
  blends that destroy the interpretability that is the product). **Risk-containment sequencing** encoded
  in the waves: Sync → Branch → Discovery (both halves, incl. the AD-Jacobian output API as the clean 7×4
  seam, optimizer method selection, rejector-unification, top-3 selection) → Gate D (guardian VETO +
  founder product calls incl. the combination-plausibility rule & top-3 policy + perf go/no-go) → Impl
  Phase A (tolerance FIRST, then single-lever AD, proven against today's bisection) → **INTERNAL AD
  go/no-go checkpoint** (AD must be validated — same answers within tolerance, IRR/Brent sound, 7×4
  Jacobian API stable — BEFORE the optimizer builds on it; NO-GO → Half A ships as the value, Half B
  defers) → Impl Phase B (the optimizer on the now-stable Jacobian) → Validation → Gate V → Roger's
  mission gate → Integrate. The **internal AD-proven-before-optimizer checkpoint is explicit in both the
  charter (§Waves, §Gates summary, binding constraint 10) and the sprint tracker (ADC.1 gate row + the
  wave-summary boundary)** — so a wrong top-3 is unambiguously an optimizer bug, not maybe-an-AD-bug.
  Roster additions for Half B: constrained-optimization design + Lagrangian/multi-start → `staff-python-engineer`
  at **fable**; two-section report output → `staff-report-experience-designer` / sonnet; the Half B
  product calls → `principal-founder-proxy` / opus; optimizer RED suite → `staff-qa-test-engineer` /
  sonnet; guardian VETO still `principal-principles-guardian`; docs still `staff-documentation-maintainer`
  at STANDARD (not haiku), verified against real symbols; code review `staff-code-reviewer` / sonnet;
  ≤3 concurrent per wave. GRAPHIFY CONTRACT remains verbatim in the handoff. **Registered the planner's
  over-scope concern** in the charter (§Risks) and §5 — Roger has read it and elected to expand; the
  internal checkpoint is the device that preserves the debugging boundary the split would have given.
  Ledger re-touched: §4 folded the former "Mission 6 multi-lever optimizer" candidate into Mission 5's
  scope (no longer a separate mission) while keeping integer-cents money (#13) as the named
  sibling-successor; §5 → the **expanded** Mission 5. **No code, no git ops, no commit** — the five
  artifacts + this ledger left uncommitted for Roger.
* **2026-08-31 (Mission 5 CHARTERED — Forward-Mode Differentiation for the Recourse Search; docs-only, no
  code, no git ops).** Baseline confirmed read-only: `main @ 7cfd449` (Mission 4 merged, "validated by
  Roger 2026-08-31, 9/9 PASS"), tree clean, in sync with `origin/main` (gate pre-verified by the
  orchestrator). Verified every design anchor against the tree at `7cfd449`: the recourse search
  (`compute_recourse` `recourse.py:792`, `_bisect` `:471`, `_rerun` `:412`, `GENUINELY_CLOSE_MAX_FAILS=3`
  `:143`), the engine (`run_financial_model` `engine.py:638`, `forecast_metrics` `:671`), the **bracketed
  Brent** IRR root-find (`irr` `irr.py:188`, `_brent_root` `:83` — flagged as the hardest AD target), the
  **bit-exact** golden harness (`test_golden_forecasts.py:188`, 34 `CASE_IDS`, golden at
  `tests/data/golden/finance_engine_forecasts.json`, regen via `generate_golden_forecasts.py`), and the
  committed benchmark (`bench_finance_engine.py`, PRIMARY 5,000u/100y, `BUDGET_MS=250.0`). **Two honesty
  corrections to the brief, encoded in the charter rather than papered over:** (1) the brief's "Mission 4
  left it at 73 ms" is NOT what the tree measures — a fresh run reads **best 169.8 / median 178.0 ms,
  150 probes** for the 5,000u/100y row against a 250 ms budget; "30 ms" appears nowhere in code and is
  recorded as Roger's *target*, with Discovery (D.2) required to reconcile the 73 ms claim by
  measurement; (2) Mission 4 already **waived** its own zero-finance-core-diff constraint and rewrote
  `engine.py`/`irr.py`/`amortization.py`, so Mission 5's AD work is a continuation of an already-opened
  core, still **high blast** and gated accordingly. Chartered the mission with the **tolerance rule as
  the first shipped deliverable, gating all AD work** (~1e-9 relative, anchored to the ORIGINAL golden,
  catches ~9.4e-8, approaching-tolerance ⇒ written justification), the **guardian VETO on the
  values-level invariant relaxation mandatory at Gate D**, the AD portion behind a real **perf go/no-go**
  (tolerance rule is independently valuable, so the mission delivers value even on a NO-GO), a measured
  forward-vs-reverse decision (dual-number 4-pass is the hypothesis to beat, not a foregone conclusion),
  the IRR/Brent differentiation approach (implicit-function-theorem vs converged-root), a numpy
  re-measurement, and the **every-number-confirmed-by-a-real-engine-re-run** invariant. Folded three
  low-blast open items in with RED tests (money-field lower bounds; horizon `le=50`→`le=100` + CLI
  clean-error; `GENUINELY_CLOSE_MAX_FAILS` product call) and **named integer-cents money as the
  sibling/successor mission, explicitly out of scope.** Roster co-designed for router confirmation at
  dispatch, with the AD/IRR math at the **top reasoning tier (fable)** and **doc reconciliation at
  STANDARD, not haiku** (Mission 4 routed doc-vs-code verification cheap and got fabricated API docs).
  Wrote all five artifacts (charter, sprint tracker, handoff with the GRAPHIFY CONTRACT verbatim,
  plain-English brief, manual-testing acceptance plan with unchecked VALIDATED boxes). Branch:
  `mission/5-forward-mode-differentiation`. Reconciled the ledger: §1 baseline → `main @ 7cfd449` in sync with
  origin; §2 added Mission 3 (`8b59399`) and Mission 4 (`7cfd449`) as SHIPPED; §4 added backlog rows
  #9–#13; §5 → Mission 5 recommendation. Files left uncommitted for Roger; **no state-mutating git ops
  performed** (no commit, no branch, no push).
* **2026-08-29 (Mission 3 SHIPPED — Roger's 9/9 manual pass, then merged and pushed)** —
  Roger drove every case in `docs/manual testing/MISSION_3_MANUAL_TESTING.md` by hand in the `airedeal`
  env on branch `mission/3-byo-onnx-provider` (tree on top of `main @ 6d9c000`, `OUT=/tmp/m3`):
  **9 / 9 PASS, 0 FAIL, 0 BLOCKED, no blocking issues.** Confirmed end-to-end — a self-built ONNX
  fixture registers and runs (`version=onnx-byo-v1`, `selected_provider='onnx'`,
  `provider_kind='model'`); **both** adjudication branches reproduce in one run (a confirmed
  `mold_suspected` hint and a *contested* `parking_garage` hint absent from every counted total);
  flag-over-env precedence holds per field (bogus env paths never touched when flags are present);
  ONNX outranks `--ai`, and `--ai` alone still falls back to `vision-stub-v1`; `python main.py` stays
  byte-identical (`545e22b2…`) even with the ONNX env vars set — the documented, intended scope
  boundary; all 8 error paths exit 1 with one clean line and no traceback; cold-vs-warm-cache output is
  byte-identical on both streams; whole suite green (**684 passed**, coverage **87.20%**, ruff format
  216 files + ruff check + mypy 214 files all clean). The DEFERRED table (offerings 2 hosted-API-key and
  3 project-trained model, both deliberately unbuilt) was reviewed and accepted. DoD box 12 flipped;
  all 12 now ticked. **Then, at Roger's instruction, the mission shipped:** committed as `bfb9cc2` on
  `mission/3-byo-onnx-provider`, merged `--no-ff` into `main` as **`8b59399`**, and pushed
  (`5dcdf1a..8b59399`) — which also carried the previously-unpushed `6d9c000` (Mission 2's validation
  record), closing both outstanding pushes; `origin/main...main` is now `0 0`, no force-push. Post-merge
  battery re-run on `main`: **684 passed / 0 failed / 0 skipped**, coverage **87.20%**, ruff (216 files)
  + mypy (214 files) clean, and `python main.py` on a cold cache still hashes `545e22b2…`. The Mission 4
  planning artifacts were deliberately left untracked and are not part of this merge. Updated the
  manual-testing doc (case-by-case observed results), `MISSION_3_SPRINT_TRACKER.md` (status block, wave
  summary, DoD item 12, INT.1, mission-gate record), and §5 here.
* **2026-08-19 (Mission 3 CHARTERED — Wire the bring-your-own ONNX model provider; docs-only, no code,
  no git ops)** — Phase 0: verified baseline `main @ a00a265`, tree clean, **1 commit ahead of
  `origin/main @ 0ea42fd`** (the unpushed docs backfill; Roger controls the push — noted for Wave
  Sync/Integrate). Formalized the Sonnet-selected Mission 3: a scoped slice of backlog #3 — **offering
  1 of 3 only (BYO ONNX model)**, explicitly NOT the hosted-API-key offering and NOT a shipped ViT.
  Verified every `path:line` against the real files at `a00a265`: `register_onnx_provider`
  (`amenities_defects.py:441`) has **zero prod/CLI callers** before Mission 3, now has CLI/env path; `--ai` lives
  on `ingest-listing` (`ingest_cli.py:50`, sets `use_ai` at `:151`), and `build_photo_insights`
  (`photo_insights.py:314-324`) hard-selects `"vision"|"local"` — never `"onnx"` (the crux seam);
  `provider_kind` (`amenities_defects.py:644`) already returns `"model"` for a non-stub bound fn; the
  six labels exist in the closed set (`schemas/labels.py`, `core/cv/ontology.py`) — no ontology change
  needed; error paths confirmed (missing onnxruntime `:271`, bad labels `:283`, bad model `:288`).
  Blast near-zero: no `src/core/finance/`, no `src/schemas/models.py` breaking edit. Wrote all five
  artifacts: charter (`MISSION_3_byo_onnx_provider.md`), sprint tracker, handoff prompt (GRAPHIFY
  CONTRACT embedded verbatim; every subagent prompt must carry it), plain-English brief
  (CHARTERED-NOT-YET-BUILT), and the manual-testing acceptance plan (`docs/manual testing/
  MISSION_3_MANUAL_TESTING.md` — 8 cases currently demonstrating the gap, VALIDATED boxes all
  unchecked for Roger). Branch: `mission/3-byo-onnx-provider`. Agent roster co-designed with the
  planner's proposal (task → agent → tier recorded in the charter/tracker; `staff-cost-aware-model-router`
  to be invoked at dispatch time per §3a.1). Folded backlog #8 (`pip install -e .` reinstall) into
  Wave 0 housekeeping. SSH signing-key blocker (§3) carries forward unchanged — does not gate this
  work. Updated §1 baseline, §4 backlog #3 row (ONNX slice → CHARTERED), §5 → Mission 3 recommendation.
  Files left uncommitted for Roger to review and commit; no git ops performed.
* **2026-08-19 (manual-testing backfill + ledger reconcile, docs-only, no code, no git ops)** —
  **Backfilled four Roger-facing docs and reconciled the ledger to as-shipped reality.** Confirmed
  with Roger that Mission 2 shipping was intentional. Wrote two manual-testing handoffs under
  `docs/manual testing/` (`MISSION_1_MANUAL_TESTING.md` — 7 cases, every command run and PASSing in
  the `airedeal` env today; `MISSION_2_MANUAL_TESTING.md` — 28 cases across Waves 0-3 as a
  *verification* checklist, since Mission 2 is shipped, not a red-until-fixed plan; a representative
  set spot-run live, deferred items flagged) and two plain-English briefs
  (`docs/plans/MISSION_1_PLAIN_ENGLISH.md`, `docs/plans/MISSION_2_PLAIN_ENGLISH.md`). Reconciled the
  tracker: §1 baseline → `main @ 8ed9397, in sync with origin`; §2 Mission 2 → SHIPPED (merged
  `8b2acf8`, released v0.3.0 `652acd7`, closed `8ed9397`, `origin/main...main` = `0 0`); §3 OPD-1..4
  row → SHIPPED (not merely resolved-on-paper); §5 → **OPEN, next mission not yet chosen (awaiting
  Roger)** — deliberately did NOT charter a new mission. Logged two findings from the manual-test
  pass into §4 backlog: **#7** the F3 "Adjustments Applied" note is unreachable on real data (engine
  OPEX-trigger strings are normalized away by the CV layer before the renderer sees them — real
  defect, survived Mission 2), and **#8** stale editable-install metadata (`pip show` reads `0.1.0`
  vs pyproject `0.3.0` — cosmetic).
* **2026-08-19** — **Doc-maintainer reconciliation against `main @ 8ed9397` (docs-only).** Closed
  five §3 blocker rows found stale: `CITATION.cff` version (resolved at v0.3.0's release, `652acd7`),
  "Doc drift" (T6 findings fixed in Mission 2 Wave 2; re-opened/re-closed same day for a fresh
  round found by this pass — see below), "`origin/main` has never received Mission 1" (resolved —
  `main`/`origin/main` both at `8ed9397`), "Report asserts false claims" (OPD-2 shipped;
  `cap_rate_floor` now read at `src/core/finance/engine.py:305-308`), and "Transforms rebuild
  models field-by-field" (anti-regression + reachable-path tests shipped in Mission 2 Waves 1-2).
  Corrected the Mission 1 and Mission 2 rows in §2 (both read as in-flight; both are shipped,
  merged, released, and pushed). New drift found and fixed the same pass, all introduced by
  post-release commits `ee023ee` (agent construction no longer requires an API key —
  `ListingAnalystAgent`'s shell is now lazy; `FinancialForecasterAgent`/`ChiefStrategistAgent`
  build none) and `66ffacd` (hash-pinned `requirements.lock`, which CI installs instead of the
  loose ranges): `src/agents/README.md` and `src/orchestrators/README.md` still described all
  three CrewAI agent classes as constructing an Agent/Task shell; root `README.md`'s High-Level
  Architecture section called the seam "a parity shell that validates the environment" without
  naming that no shell is built by default, and its Tech Stack/Developer Setup sections omitted
  `requirements.lock` and the `pip install -e .`/console-script fix that had already landed.
  `CHANGELOG.md [Unreleased]` gained entries for both post-release fixes, which had shipped with
  no changelog record. Did **not** touch §1's composite grade table or Mission-history one-liners
  beyond the two status/date fixes above — those are editorial judgments this doc-maintainer pass
  does not have the authority to re-grade.
* **2026-08-03 (later)** — **Mission 2 kickoff decisions folded into the docs (docs-only, no code).**
  Roger resolved all four OPDs and approved the full mission (Waves 0–3 as one). OPD-1 =
  reconcile-then-delete `strategist.py` (port preferred thresholds into `chief_strategist` first,
  review, then delete). OPD-2 = **wire the F1 cap-floor warning into `run_financial_model`** — the
  high-blast path (16 prod + 25 test files) that **moves every golden number**; the charter/tracker/
  handoff now call out the deliberate golden re-baseline (regenerate + human-review; anti-regression
  tests still RED on true regressions) and the deterministic-core carve-out. OPD-3 = wire-first the
  Tier-4 dead modules, deleting only the un-wireable (`orchestrator.py` 0-byte, `agents/listing_ingest.py`
  true-duplicate, `advisor/__init__.py` bypassed facade). OPD-4 = populate the Tier-5 unread fields into
  the reports (additive-only). All four blockers marked CLOSED; the split-into-Mission-3 recommendation
  retained as history only. Refuted/dropped items (`income_is_estimated`, F9 `onnxruntime`) kept out of
  active scope; GRAPHIFY CONTRACT still verbatim in the handoff. Edited all four planning docs.
* **2026-08-03** — **Mission 2 — Close the end-to-end wiring gaps CHARTERED (not executing).**
  Phase 0: corrected the wrong conda path in the brief (real env `/home/rtokime/anaconda3/envs/airedeal`);
  re-verified the baseline (310-ish passed, 81.87% cov, ruff+mypy clean) — the brief's numbers hold.
  Flagged a non-standard baseline: local `main` ahead of `origin/main` by 7 (Mission 1 unpushed) + a
  dirty working tree that IS the intended baseline (audit + graph built against it) → decision to land
  it first as a mission-zero commit. Independently re-validated all 20 findings + Tiers 4/5/6
  (reproduce + falsify): 12 CONFIRMED, 5 PARTIAL/downgraded (F7 lxml, F8 playwright, F9 onnx, F15,
  F20), 2 loud refutations — **`income_is_estimated` is NOT discarded (read at `engine.py:98`)** and
  **F9 onnxruntime dropped from active fixing** (deliberate opt-in provider, no CLI path). Confirmed
  the Tier-4 reachability closure via static import sweep (no dynamic dispatch anywhere in `src/`) +
  `graphify affected`: `strategist.py`/`narrative`+`report_builder`/`photo_tagger`/`regional_income`
  dead-in-prod, `scenarios.py`/`utils/markdown`/`utils/serialize`/`agents/listing_ingest` zero-ref,
  `orchestrator.py` 0-byte. Key blast insight: `run_financial_model()` reverse-affects 16 prod + 25
  test files → F1's engine-side fix (OPD-2 fork a) is high-blast; consumer-side fork (b) is not.
  Chartered Mission 2 (plan + sprint tracker + handoff prompt) scoped to surviving findings only,
  with 4 open product decisions (OPD-1..4) gating Waves 0.2/3. Recommended Roger split Waves 0–1 from
  Waves 2–3.
* **2026-07-24** — **Mission 1 — Scenario Intelligence SHIPPED.** Wave 0 landed commit hygiene + packaging (`pip install -e .` works). Waves 1–3 delivered the opt-in `--scenarios` overlay: `src/market/adapter.py` + `scenario_runner.py` compose the hypothesis grid with the frozen finance engine into prior-weighted DSCR/CoC/CF/IRR bands (downside = prior-weighted p25), a fixed verbatim honesty block, and honest caveats; additive `ScenarioMetricBand`/`ScenarioOutcome`/`ScenarioAnalysis` models; default-off byte-identical. All 4 review gates passed (finance-semantics, founder-proxy scope, code-review, principles-guardian VETO ×2). One founder-authorized frozen-core carve-out: fixed an IRR Newton-Raphson solver artifact (`src/core/finance/irr.py`) that returned economically-meaningless sub-(−100%) roots — math verified against IRR-domain references, surgical (touches only the one artifact). Axis moves: Market C→B+, Reports B+→A-, Packaging D→B. `main` @ `8f4ce2a`, all commits SSH-signed, CI green. Follow-ups logged (§3): GitHub signing-key registration, CITATION/pyproject version reconcile, parked media-intelligence refactor.
* **2026-07-23** — First run. Phase A: full documentation reconciliation against main @ `e4716df` + working tree — fixed root README (license badge MIT→Research & Education, V1→V2 output, phantom `src/tools`/`src/reports` index entries, CLI docs added, coverage 90%→80%, honest CrewAI-seam framing, roadmap split V1/V2-shipped/V3-planned, packaging caveat), rewrote `src/cli/README.md` (was the old tools README), rewrote `src/core/README.md` (removed nonexistent `cv.bridge`/`xirr`/`media_pipeline`/`build_strategy`; added advisor/intelligence/ingest subareas), rewrote `src/agents/README.md` and `src/orchestrators/README.md` (real signatures, class-based agents, functional-vs-docstring env flags, CrewAI parity-shell honesty), rewrote `src/core/reports/README.md` (write_report, media overview, env overrides, fixed nested links), rewrote `src/inputs/README.md` (InputsLoader/AppInputs/RunOptions live here; real env overrides), rewrote `src/schemas/README.md` (per-unit IncomeModel, real field names, media/ingest models, labels ontology), patched `src/market/README.md` (status + links), reconciled CHANGELOG Unreleased placeholders into the actual shipped V2 feature list with dated status note, fixed CONTRIBUTING install instructions. Phase B: created this tracker; chartered **Mission 1 — Scenario Intelligence** (plan, sprint tracker, handoff prompt written).
