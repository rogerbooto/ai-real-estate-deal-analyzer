# Mission 4 Handoff — Actionable Recourse ("What would have to change?")

**How to use this prompt:** Open a fresh Claude Code session at the repo root
(`/home/rtokime/projects/Personal/ai-real-estate-deal-analyzer`) and paste everything between the
BEGIN/END markers verbatim. That session becomes the mission orchestrator. This mission is **chartered,
not yet built** — no code exists for it. **It must not begin until Mission 3
(`mission/3-byo-onnx-provider`) has cleared Roger's mission gate and merged to `main`** (solo-dev
one-mission-at-a-time cap). The first concrete action is Wave Sync, then Wave Branch. Roger holds the
mission gate (merge + push); the orchestrator never self-approves.

=== BEGIN MISSION PROMPT ===

You are the orchestrator for **Mission 4 — Actionable Recourse ("What would have to change?")** of the
AI Real Estate Deal Analyzer (deterministic-first real estate underwriting tool; solo developer: Roger).

## ⛔ Sequencing pre-condition (check this FIRST)

Mission 4 branches off freshly-synced `main` **only after Mission 3 has cleared Roger's founder gate
and merged to `main`.** If `git log --oneline main` does **not** show the Mission 3 merge commit, STOP
and tell Roger: Mission 4 is blocked on Mission 3's mission gate. Do not open Mission 4 concurrently —
the solo-dev cap is one mission at a time. Mission 4 is technically *independent* of Mission 3 (it
touches finance/schema/reports, never CV/vision/ONNX), so nothing in its code depends on Mission 3;
the gate is a process cap, not a code coupling.

## Mission identity (one read)

The verdict engine answers BUY / CONDITIONAL / DECLINE well, but cannot say **how close a near-miss is**
or **what would move it across the line** — and it states the gap in *our* units ("DSCR is weak at 1.19
(< 1.20)"), which no investor negotiates in. This mission keeps the verdict and **attaches to a
near-miss a recourse analysis**: the distance to each failing guardrail and what single change would
close it, in levers an investor can actually move — **rent per unit per month, purchase price, interest
rate, annual operating costs**. One gap, several currencies; the investor picks the lever they have
leverage on. This is the established field of *actionable recourse / counterfactual explanations*.

**The one discipline that makes or breaks this build: re-run the engine, never invert a guardrail
formula.** The levers are **not independent** — cutting the purchase price shrinks the loan, improves
the cap rate, and changes cash-in all at once; raising rent moves NOI, cap rate, coverage, and
cash-on-cash together. Inverting one guardrail formula in isolation gives wrong, optimistically-biased
numbers (it would promise a $9,800 price cut closes a gap it does not close). Find each lever's flip
point by **re-running `run_financial_model` with a single input changed** — the exact pattern
`build_baseline_outlook` (`src/orchestrators/crew.py:65`) and `run_scenarios`
(`src/market/scenario_runner.py:126`, step (d): "perturb a deep copy, re-run the engine") already use —
then test the perturbed scenario for plausibility with the existing rejector (`reject_unrealistic`,
`src/market/rejector.py:54`).

Blast is low and additive: **zero `src/core/finance/` diff** (the engine is a black box), **additive
schema only** (new `RecourseLever`/`RecourseAnalysis` beside `ScenarioAnalysis`, `src/schemas/models.py:1277`;
nothing renamed/removed; `InvestmentThesis.levers` untouched), and **one appended report section**
(like Mission 1's "Market Scenarios" overlay, `src/core/reports/generator.py:1246`). The verdict stays
authored by `synthesize_thesis` (`src/agents/chief_strategist.py:137`); this mission adds **no model,
no AI, no network, no external input surface.**

Verify every `path:line` against the real file at the real baseline before touching it (the graph and
this charter reflect a snapshot commit, not necessarily HEAD; two prior missions found charter path
drift).

## Read these first (canonical, in order)

1. `docs/plans/MISSION_4_actionable_recourse.md` — the charter (baseline, branch, in/out of scope,
   waves, DoD, agent roster, binding constraints, gates). Authoritative for scope.
2. `docs/plans/MISSION_4_SPRINT_TRACKER.md` — the live task tracker you keep current.
3. `docs/manual testing/MISSION_4_MANUAL_TESTING.md` — the acceptance/manual-test plan you keep
   accurate as fixes land, and that Roger validates by hand at the mission gate.
4. `docs/plans/ROADMAP_TRACKER.md` §4 "Backlog #6" (Roger's verbatim design, his three decisions, the
   non-independence trap, the research findings) — the specification behind this mission; §1, §3, §5.
5. The seams you compose (re-read each before touching): `src/agents/chief_strategist.py`
   (`synthesize_thesis`, the guardrails + verdict fail-count), `src/orchestrators/crew.py`
   (`build_baseline_outlook`, the re-run pattern), `src/market/scenario_runner.py` (`run_scenarios`),
   `src/market/rejector.py` (`reject_unrealistic`), `src/schemas/models.py` (`ScenarioAnalysis` shape,
   `InvestmentThesis`), `src/core/reports/generator.py` (Market Scenarios append pattern).

Re-read any `path:line` you touch before changing it.

## Environment (critical — the common conda path is wrong)

Run all project Python in the `airedeal` conda env:
`source /home/rtokime/anaconda3/etc/profile.d/conda.sh && conda activate airedeal`
(NOT `~/miniconda3` — that path does not exist and silently falls back to the wrong interpreter).
Confirm `which python` → `/home/rtokime/anaconda3/envs/airedeal/bin/python`.

## Baseline & branch

`base = main @ <established at Wave Sync, after Mission 3 merges>.` At charter time `main @ 6d9c000` and
Mission 3 was uncommitted on its branch; the real baseline is whatever `main` reads once Mission 3 has
landed. Re-confirm every charter anchor at that commit. Branch: `mission/4-actionable-recourse`, cut
off freshly-synced `main`. Surface any origin delta to Roger at Wave Sync; never force-push; push only
at Roger's instruction.

## What you are building (scope)

* **A recourse analysis for a near-miss verdict.** For CONDITIONAL (and DECLINE where genuinely close),
  compute distance-to-line per failing guardrail and one single-lever change per lever that would close
  it, in several investor-facing currencies.
* **Every lever answer from an engine re-run.** Perturb one input on a deep copy of `FinancialInputs`,
  re-run `run_financial_model`, read the resulting `InvestmentThesis`/metrics; bounded (bisection)
  search for the minimum flipping change. **Never invert a guardrail formula.**
* **Plausibility via the existing rejector.** Test each perturbed scenario with `reject_unrealistic`/
  snapshot bounds; **flag implausible levers with a reason, never remove them** (decision 1).
* **Multi-guardrail ordering.** Lead with the cheapest single fix, **flag that other gaps remain**
  (decision 2).
* **Honest-null.** When nothing realistic closes it, **say so plainly** (decision 3).
* **Additive schema.** `RecourseLever`/`RecourseAnalysis` beside `ScenarioAnalysis`; nothing renamed/
  removed; `InvestmentThesis.levers` unchanged.
* **A new report section** "What would have to change?", appended like the Market Scenarios overlay;
  absent (byte-identical to today) when there is no near-miss.
* **Honest wording:** "**WOULD** close it, holding the other levers fixed" — never "WILL".
* **Docs** + backlog #6 closure note.

## Waves & gates

Wave Sync (re-sync after M3 merges; re-confirm anchors; pin baseline + pre-mission report sha) → Wave
Branch (`mission/4-actionable-recourse`) → Evaluator confirmation (`app-evaluator` confirms grades/gap
severity) → Wave Discovery (recourse spec, incl. the non-independence trap test design) → **Gate D**
(guardian honesty VETO + bounded founder product call + perf sanity call — all blocking; **no security
gate**, no external surface) → Wave Implementation (≤3 concurrent: module+schema · RED suite · report
copy · docs) → Wave Validation (full battery + byte-identity + every manual-test command runs) →
**Gate V** (code review + guardian VETO) → **Mission gate (Roger)** → Wave Integrate.
Check every DoD box in the charter before requesting the mission gate.

## Binding constraints (non-negotiable)

1. **Zero `src/core/finance/` diff.** The engine is a black box called **once per perturbed input**,
   **never by inverting a guardrail formula**. The verdict stays in `synthesize_thesis`.
2. **THE NON-INDEPENDENCE TRAP is a first-class test requirement.** The RED suite MUST include a case
   that only passes because the answer came from re-running the engine — a case where the naive
   inverted-formula answer differs measurably from the true re-run answer, and reverting to a
   formula-inversion implementation turns the test RED.
3. **Schema additive-only** (`src/schemas/models.py`) — new models only; nothing renamed/retyped/removed;
   `InvestmentThesis.levers` unchanged.
4. **Honesty as values, not copy.** "WOULD, holding others fixed" not "WILL"; flag-don't-remove
   (decision 1); cheapest-first-flag-the-rest (decision 2); say-so-plainly when nothing works
   (decision 3). Guardian VETO enforces.
5. **Determinism** — same inputs ⇒ byte-identical `RecourseAnalysis` + report section; deterministic
   search (fixed bounds/tolerance, no unseeded randomness); default (no near-miss) output byte-identical
   to pre-mission.
6. **No threshold/policy change** — 3.1c is a later mission; this feature only *enables* revisiting it.
7. **No new external surface** — no file paths, no network, no untrusted input, no AI/model.
8. **Prove-the-test** — every fix ships a test that turns RED on revert; demonstrate it.
9. **Quality gate** — `ruff format --check` + `ruff check` + `mypy .` clean; coverage ≥80%.
10. **Git** — branch off freshly-synced `main` after M3 merges; no PRs; merge only after Roger's mission
    gate; never force-push `main`; reconcile any origin delta; push only at Roger's instruction.

## Bounded product call (founder-proxy)

One decision, bounded — do not let it sprawl into threshold decisions: (a) the exact investor-facing
wording per lever; (b) the default set of "currencies" shown per gap (e.g. $/unit/month AND % increase;
$ off price AND % below asking; bps off the rate; $ off annual opex); (c) the flag-don't-remove copy —
how an implausible lever is presented with its reason. Route to `principal-founder-proxy` at Gate D, or
earlier if it blocks Discovery.

## Orchestration protocol

* **Agents (fleet in `.claude/agents/`; ≤3 concurrent):** `app-evaluator` (confirm grades/gap
  severity), `staff-python-engineer` (Discovery spec; recourse module + additive schema),
  `principal-founder-proxy` (bounded product call), `principal-performance-engineer` (perf sanity),
  `principal-principles-guardian` (honesty VETO, Gate D + Gate V), `staff-qa-test-engineer` (RED suite
  incl. the non-independence trap), `staff-report-experience-designer` (report section + copy),
  `staff-documentation-maintainer` (docs), `staff-code-reviewer` (Gate V review). Roger holds the
  mission gate. **No `principal-security-engineer`** — no external input surface.
* **Cost routing:** **invoke `staff-cost-aware-model-router` at kickoff** to confirm tiers BEFORE the
  first dispatch batch (standing rule — not "only when ambiguous"). Planner proposal: evaluator +
  founder call → capable (opus); spec/module/tests/report/reviews/guardian → standard (sonnet); perf +
  docs → cheap (haiku). Record `task → agent → tier` in the tracker and log any deviation at dispatch
  time.
* **Verify inline:** never trust an agent's "done" — re-run its tests, re-read its diff, revert-check
  each RED test (especially the non-independence trap), git-verify the finance-core zero-diff and schema
  additivity yourself, and tick the DoD before marking DONE.
* **Branch-and-integrate:** Wave Sync = confirm Mission 3 merged, `git fetch`, confirm canonical latest,
  surface any origin delta, re-confirm anchors, re-run the battery green + pin the baseline. Wave Branch
  = `git switch main && git switch -c mission/4-actionable-recourse`. Wave Integrate (after Validation
  GREEN **and** Roger's mission gate) = `git fetch`, rebase/merge onto latest, re-run the **full**
  battery post-rebase (a pre-rebase green does not count), `git merge --no-ff`, reconcile+push only at
  Roger's instruction, record the merge sha. Never self-approve; never force-push `main`.
* **Tracker discipline:** update `docs/plans/MISSION_4_SPRINT_TRACKER.md` after every state change —
  full updates (counts + wave summary + rows), never partial; carry the tests-tree SHA on every count;
  date every gate record.
* **Manual-testing discipline:** keep `docs/manual testing/MISSION_4_MANUAL_TESTING.md` accurate as
  fixes land — every command in it must actually run and produce the stated result by the time the
  mission gate is requested. The boxes are Roger's to flip; the mission gate is not clear until the
  document-level box reads VALIDATED.
* **Research-first + YAGNI:** read the seam before changing it; build only what the charter scopes. Do
  NOT touch finance-core internals, do NOT invert a guardrail formula, do NOT change any threshold, do
  NOT add a UI or a data feed. Vectorise only if the Gate D perf call proves the naive re-run too slow.

## GRAPHIFY CONTRACT — every subagent prompt you issue MUST carry this block verbatim

--- BEGIN GRAPHIFY CONTRACT (paste verbatim into the handoff and every subagent prompt) ---
A knowledge graph of this repo lives at `graphify-out/graph.json`. Prefer it over blind Grep sweeps when you need to locate a symbol, trace what calls what, find which module owns a concern, or work out what a change would break.
Useful commands (all read the graph; none need an API key):
    graphify affected "<symbol>" --depth 3    # reverse traversal: what depends on this
    graphify path "<A>" "<B>"                 # shortest path between two nodes
    graphify explain "<node>"                 # plain-language node + neighbours
    graphify god-nodes --top 10               # most-connected architectural hubs
TOKEN DISCIPLINE: NEVER cat/Read graph.json whole (~1600 nodes). NEVER run bare `graphify query` (pass --budget N). For bulk analysis filter the JSON programmatically and print only what you need. Schema: nodes[]={label, source_file, source_location, community}; links[]={relation, source, target, confidence}; plus hyperedges[], built_at_commit. Community names in graphify-out/.graphify_labels.json.
TRUST BOUNDARY: the graph is a snapshot (built_at_commit). If it disagrees with git log, or a source_file no longer exists, treat the graph as a LEAD and confirm against the actual file. Never cite a graph edge without opening what it points at. Do NOT run `graphify update` yourself.
--- END GRAPHIFY CONTRACT ---

## First concrete action

**Confirm the sequencing pre-condition:** run `git log --oneline -5 main` and verify the Mission 3
merge commit is present. If it is not, STOP and tell Roger Mission 4 is blocked on Mission 3's mission
gate. If it is present, execute **Wave Sync**: run `git fetch`, `git status --porcelain` (expect
clean), confirm `main` is the canonical latest, surface any origin delta to Roger. Re-confirm every
charter `path:line` against the file at the real baseline (`synthesize_thesis`, `build_baseline_outlook`,
`run_scenarios`, `reject_unrealistic`, `ScenarioAnalysis`, the report append pattern). Run the full gate
battery (`pytest`, `ruff format --check`, `ruff check`, `mypy .`, `python main.py`) green — pin the
suite count, coverage, tests-tree SHA, and the pre-mission `python main.py` report sha256 in the
tracker. Then execute **Wave Branch**: `git switch main && git switch -c mission/4-actionable-recourse`.
Update the sprint tracker after each step.

=== END MISSION PROMPT ===
