# Roadmap Tracker — AI Real Estate Deal Analyzer

Standing ledger owned by the mission-planner. Read first, update last, every run.

---

## 1. Current state (as-built)

**Composite grade: B-** _(planner-derived 2026-07-23; to be confirmed by app-evaluator when spawnable)_
Base (Mission 3 charter run, 2026-08-19): `main @ a00a265`, tree clean, **1 commit ahead of `origin/main @ 0ea42fd`** — the unpushed docs backfill `a00a265` ("docs(missions): backfill Roger-facing manual-test + plain-English docs; reconcile roadmap ledger to as-shipped v0.3.0"); Roger controls the push. _(Prior run's base was `main @ 8ed9397`, **in sync with `origin/main`** at that time; verified 2026-08-19: `git rev-list --left-right --count origin/main...main` = `0 0` then.)_ Mission 2 has since been merged AND pushed; the earlier "origin has never received Mission 1" divergence is closed — origin now carries everything through `8ed9397`. _(Historical: the dirty working tree the Mission 1 charter described as its baseline had landed as `6147839` — sample bundle restore, parsing regex fixes, report identity/glossary/provenance wiring, `PASS`→`DECLINE` rename, `.env.example` rewrite.)_ The tree is now clean. Planner-verified, orchestrator-reproduced in the real `airedeal` env (`/home/rtokime/anaconda3`, NOT `~/miniconda3`): `pytest` green, coverage 81.87%, `ruff` + `mypy` clean. Graph rebuilt against the working tree (1631 nodes / 4013 edges).

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
| 1 | Scenario Intelligence (wire `src/market` into pipeline + reports; Wave 0 packaging fix; authorized IRR-solver core fix) | **Shipped and pushed** — Roger's mission gate approved; merged to `main`, and `main`'s subsequent history (including Mission 2) reached `origin/main` on 2026-08-05 (see §3, "`origin/main` has never received Mission 1" row) | 2026-07-23 → 2026-07-24 |
| 2 | Close the end-to-end wiring gaps (Tier 0 false-report fixes, Tier 1 silent-drop wiring + anti-regression guard, Tier 3 CLI honesty, T4/T5 wire-first disposition) | **Shipped, merged, released, pushed** — Gate 3 passed (principles-guardian VETO lifted, staff code review approved); merged `--no-ff` as `8b2acf8` ("Merge Mission 2: close the end-to-end wiring gaps"), released as v0.3.0 (`652acd7`), CI fixed and green at `66ffacd`, mission closed at `8ed9397`. **Merged AND pushed — local `main` in sync with `origin/main`** (verified 2026-08-19: `git rev-list --left-right --count origin/main...main` = `0 0`). 27/28 tasks done; the remainder (3.1c) is a threshold decision for Roger, not engineering work (branch `mission/2-wiring-gaps`) | 2026-08-03 → 2026-08-05 |

---

## 3. Blocker / pre-condition ledger

| Blocker | Gates | Status |
| --- | --- | --- |
| Uncommitted working-tree changes on `main` (core.zip deletion, .gitignore, doc reconciliation) | Any mission branching from main | **Closed 2026-07-24** — landed on `main` (Mission 1 Wave 0) |
| `pyproject.toml` missing `[project]` metadata (broken install, dead console scripts) | Truthful CLI docs; distribution; UI missions | **Closed 2026-07-24** — `[build-system]`+`[project]`+discovery added (Mission 1 Wave 0.2); `pip install -e .` + 3 console scripts verified |
| Media-intelligence API refactor incomplete/broken (caller `insights.py` + tests not propagated to new signatures; ruff/mypy/tests red; env-dependent `_dct2` pHash) | Any work touching `src/core/media/` | **Open 2026-07-24** — orphaned WIP parked in `git stash@{0}`; deferred to its own branch `feat/media-intelligence-refactor` (NOT Mission 1). Fix list in `MISSION_1_SPRINT_TRACKER.md` parking note |
| GitHub SSH **signing** key not registered ("Dell Laptop" key is an auth key only) | Verified commits; clean pushes without admin bypass | **Open 2026-07-24** — commits SSH-signed locally (git 2.55 shim, `~/.gitmodern-bin`) but show Unverified; Roger to add the key as a Signing key in GitHub settings |
| `CITATION.cff` version `1.0.0` ≠ `pyproject`/CHANGELOG `0.1.0` | Any version tag / release cut | **Closed 2026-08-05** — the v0.3.0 release (`652acd7`) reconciled both to `0.3.0`; verified against `main @ 8ed9397` on 2026-08-19 (`CITATION.cff` and `pyproject.toml` both read `0.3.0`). |
| No real AI provider (vision/LLM stubs only) | Any "AI-powered" marketing claim; CrewAI kickoff mission | Open — deferred (backlog #3) |
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
| 3 | **Real vision provider behind the existing CV seam** — see the detailed note below, added 2026-08-03 at Roger's request. **Slice sub-1 (BYO ONNX model) CHARTERED as Mission 3, 2026-08-19** — the lowest-blast offering, wiring the existing `register_onnx_provider` to a real CLI/env path; offerings 2 (hosted API key) and 3 (shipped ViT) remain OPEN backlog. | High (makes the "AI" headline true) | **sub-1 (ONNX): near-zero** (additive CLI/env wiring + provider-selection at an existing seam; no finance/schema/ontology diff). sub-2/sub-3: Med-High (API keys, cost, non-determinism policy; training/licensing) | CV provider registry (`register_onnx_provider` **already exists**, `amenities_defects.py:382`; `build_photo_insights` selection seam `photo_insights.py:314-324`) | CV/AI C+→B (real user model path); unlocks the 6 filename labels | CV/AI, Orchestration, Docs | sub-1: none outstanding (Mission 2 honest-provenance + 70/30 rule landed). sub-2: determinism/key-hygiene policy. sub-3: training data + licensing |
| 4 | Streamlit UI for interactive scenario exploration | High (portfolio wow) | Med (new surface, new deps) | Reads existing JSON artifacts | Distribution | Packaging, Portfolio | #1 (scenarios give the UI something to explore), #2 |
| 5 | Live market data ingestion (comps, cap-rate drift) | Med | High (network, data licensing, freshness) | fetch/ policy | Market realism | Market | #1; compliance review |
| 7 | **F3 "Adjustments Applied" note is unreachable on real data** (found in the 2026-08-19 manual-test pass; documented as Mission 2 case F3 / defect #4). The report renderer correctly ships whatever OPEX-adjustment notes the engine emits, but the engine's triggers test **pre-normalization** strings (`"old roof"`, `"water stain"`) that the CV/label layer normalizes away before the engine sees them (e.g. `"water stain"` → `water_leak_suspected`), so on any real pipeline run the notes are empty and the section never appears. **Real defect, survived Mission 2.** | Low-Med (report honesty — a shipped section that can never populate on real input misleads by omission) | Med (fixing the engine side is inside `src/core/finance/`; fixing the normalization map has CV/label blast — a product decision) | engine OPEX-modifier ↔ CV-label vocabulary | Reports/Finance honesty | Reports, CV/AI | Roger decides which side moves (trigger/label reconciliation) |
| 8 | **Stale editable-install metadata** (found 2026-08-19): `pip show ai-real-estate-deal-analyzer` reports `Version: 0.1.0` while `pyproject.toml` reads `0.3.0`, because an earlier `pip install -e .` cached the old metadata. Cosmetic; console scripts resolve and run correctly. Refreshed by re-running `pip install -e .`. | Very low (cosmetic; no functional impact) | Minimal (no source change; a re-install, or a docs note) | packaging | Packaging polish | Packaging | — |

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
**exact arithmetic, not statistics** — invert the guardrail formula. No distribution is needed to
answer "how far from flipping", which is a deterministic question.

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

**Mission 3 — Wire the bring-your-own ONNX model provider to a real user path (CHARTERED 2026-08-19,
not yet built).** A scoped slice of backlog #3: **offering 1 of 3 only** (BYO ONNX model) — NOT the
hosted-API-key offering, NOT a project-shipped ViT. Baseline `main @ a00a265`; branch
`mission/3-byo-onnx-provider`. Artifacts: `docs/plans/MISSION_3_byo_onnx_provider.md` (charter),
`docs/plans/MISSION_3_SPRINT_TRACKER.md`, `docs/plans/MISSION_3_HANDOFF.md` (pasteable prompt),
`docs/plans/MISSION_3_PLAIN_ENGLISH.md`, `docs/manual testing/MISSION_3_MANUAL_TESTING.md`.

**Why now / why this one.** Highest reward-to-blast on the board. The machinery is already built and
tested — `register_onnx_provider(model_path, labels_path)` (`amenities_defects.py:382`), the
capability-declaration mechanism, and `provider_kind` returning `"model"` — but it has **zero callers**:
no CLI flag or env var reaches it, and `build_photo_insights` (`photo_insights.py:314-324`) hard-selects
`"vision"|"local"`, never `"onnx"`. So this is wiring + a minimal provider-selection change, not new
capability. Blast is near-zero (no `src/core/finance/`, no `src/schemas/models.py` breaking edit), it
takes CV/AI from "honest stub only" toward a real user model path, and — because Mission 2 landed the
honest-provenance labelling and the 70/30 confirm-don't-fabricate rule — it unlocks the six
filename-inferred labels (`mold_suspected`, `water_leak_suspected`, `ev_charger`, `parking_garage`,
`parking_driveway`, `dishwasher`) as confirmable observations with **no ontology change**. Pre-conditions
are met; offerings 2 & 3 stay backlog because their blast (cost/non-determinism policy; training/
licensing) is much higher. Backlog #8 (`pip install -e .` reinstall) folded in as one-line Wave 0
housekeeping. Carried constraints: AI observes but never authors the verdict; security review of the
user-supplied model-file surface; honest framing (no overclaim — it is the *user's* model).

**Where the rest of the backlog stands (candidates, not the current pick):**
- **#6 "What would have to change?"** (Roger's actionable-recourse design, §4) — the 3.1c threshold
  calls should be revisited *after* it ships.
- **#4 Streamlit UI**, **#5 live market data** — unchanged.
- **#7** the unreachable F3 "Adjustments Applied" note (real, report-honesty). **#8** stale
  editable-install version metadata — folded into Mission 3 Wave 0 housekeeping.

**Still-open blockers that gate certain futures (§3):** no real AI provider yet (gates any
"AI-powered" claim); the GitHub SSH **signing** key remains unregistered (commits show Unverified);
the parked media-intelligence refactor (`parked/media-intelligence-refactor`) still gates any
`src/core/media/` work.

---

## 6. Changelog

* **2026-08-19 (Mission 3 CHARTERED — Wire the bring-your-own ONNX model provider; docs-only, no code,
  no git ops)** — Phase 0: verified baseline `main @ a00a265`, tree clean, **1 commit ahead of
  `origin/main @ 0ea42fd`** (the unpushed docs backfill; Roger controls the push — noted for Wave
  Sync/Integrate). Formalized the Sonnet-selected Mission 3: a scoped slice of backlog #3 — **offering
  1 of 3 only (BYO ONNX model)**, explicitly NOT the hosted-API-key offering and NOT a shipped ViT.
  Verified every `path:line` against the real files at `a00a265`: `register_onnx_provider`
  (`amenities_defects.py:382`) has **zero prod/CLI callers** (only docs, tests, README); `--ai` lives
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
