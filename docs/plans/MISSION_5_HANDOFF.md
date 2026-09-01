# Mission 5 Handoff — Forward-Mode Differentiation & Optimized Recourse Search

**How to use this prompt:** Open a fresh Claude Code session at the repo root
(`/home/rtokime/projects/Personal/ai-real-estate-deal-analyzer`) and paste everything between the
BEGIN/END markers verbatim. That session becomes the mission orchestrator. This mission is **chartered,
not yet built** — no code exists for it. It runs **two halves in sequence (A then B)** with a hard
internal AD go/no-go checkpoint between them (Roger expanded the mission on 2026-08-31 to include the
multi-lever optimizer that was previously slated for a Mission 6). Mission 4 is already merged to `main`
(`7cfd449`), so the sequencing pre-condition is satisfied; the first concrete action is Wave Sync, then
Wave Branch. Roger holds the mission gate (merge + push); the orchestrator never self-approves.

=== BEGIN MISSION PROMPT ===

You are the orchestrator for **Mission 5 — Forward-Mode Differentiation & Optimized Recourse Search** of the
AI Real Estate Deal Analyzer (deterministic-first real estate underwriting tool; solo developer: Roger).

This mission has **two halves, run strictly in sequence**:
- **Half A** — the tolerance rule + forward-mode (tangent-linear) differentiation + single-lever recourse acceleration (the
  original charter, unchanged in mechanics; its *rationale* is corrected below — AD is not a speed play).
- **Half B** — the multi-lever recourse optimizer that adds a second report section listing up to **11
  minimal-ask propositions** (one per lever subset, unranked, cheapest labelled "cheapest total
  negotiation"), alongside the existing single-lever menu (added by Roger's 2026-08-31 expand decision;
  previously slated for a separate Mission 6; **top-3/Lagrangian design superseded 2026-08-31, see
  below**). **Half B, not Half A's speed, is now the mission's centre of gravity.**

## ⛔ Three rules that gate the whole mission (read FIRST)

1. **THE TOLERANCE RULE SHIPS BEFORE ANY AD WORK.** Automatic differentiation reorders floating-point
   arithmetic and cannot meet Mission 4's bit-exact golden. Roger approved relaxing the invariant to a
   **~1e-9 relative tolerance, always measured against the ORIGINAL golden (never the previous
   version)**, and this relaxation must ship, go green, and clear the guardian VETO **before a single
   line of AD code is written.** It is what makes AD's output reviewable. This is a hard wave boundary.
2. **THE INTERNAL AD GO/NO-GO CHECKPOINT SHIPS BEFORE ANY HALF B (OPTIMIZER) WORK.** Half B's optimizer
   builds directly on Half A's AD Jacobian. Before a single line of optimizer code, the AD foundation
   must be **proven**: single-lever AD answers match today's bisection within tolerance, the IRR/Brent
   differentiation is sound, and the 7×4 Jacobian API is stable. **GO → build Half B. NO-GO → Half B
   defers and the mission ships Half A alone** (tolerance + AD, or tolerance alone if Gate D also
   no-goed AD). This is a hard wave boundary — it is what makes a wrong top-3 unambiguously an
   *optimizer* bug, not a maybe-AD bug.
3. **INVOKE `staff-cost-aware-model-router` AT KICKOFF, before the first dispatch batch** — not "only
   when ambiguous" (standing rule §3a.1). Record `task → agent → tier` and log any deviation at
   dispatch time.

Also load-bearing: **every subagent prompt you issue MUST carry the GRAPHIFY CONTRACT block verbatim**
(reproduced at the end of this prompt).

## Sequencing pre-condition (check this FIRST)

Run `git log --oneline -5 main`. Confirm the **Mission 4 merge commit `7cfd449`** ("Merge Mission 4:
actionable recourse … validated by Roger 2026-08-31, 9/9 PASS") is present and is the tip of `main`.
If a **later** mission is mid-flight (a commit on `main` after `7cfd449` you did not expect, or an
in-progress `mission/6-*` branch), STOP and tell Roger — do not open Mission 5 concurrently (solo-dev
one-mission-at-a-time cap). If `main` is at `7cfd449`, clean, and in sync with origin, proceed to Wave
Sync.

## Mission identity (one read)

Mission 4 shipped **actionable recourse**: for a near-miss deal, "what single change closes the gap?"
answered by **bump-and-reprice** — perturb one lever, re-run the whole engine, bisect until the failing
guardrail flips (`compute_recourse` `src/market/recourse.py:792`; `_bisect` `:471`; `_rerun` `:412`).
That is ~10–20 engine probes per lever/guardrail pair — honest, obvious, slow. Quant desks abandoned
this for **algorithmic differentiation**: get the derivative of the model itself and jump to the answer.
Same mathematics as backpropagation — the engine is a computation graph; one pass yields exact partial
derivatives. Exact derivatives turn bisection into **Newton's method on the guardrail**, dropping
~10–20 probes to ~3–4.

> **⚠ RATIONALE CORRECTED 2026-08-31 (Roger's decision, C4(b)) — struck: "the remaining path toward
> Roger's 30 ms target."** Measured three times independently and refuted: Newton-on-guardrail costs
> ~4× a plain evaluation per dual pass and converges in **11–41 probes vs bisection's fixed ~11** — a
> wash or a loss. The budgeted row's dominant cost is the **rent-roll copy** (74.5%) and **garbage
> collection** (~35%, 183.5 ms → 117.7 ms tuned) — neither touched by AD. **Roger's decision: rewrite
> the rationale, ship the full scope.** The measured path to 30 ms is GC tuning + an aggregate-income
> seam, not AD. **AD's real justification is direction selection and sensitivity** for Half B: one
> forward pass yields all partials at ~4.1–4.4× an engine pass vs **8 passes** for central finite
> differences — bisection owns *how far*, AD now owns *which direction*. **Half B — a
> product/capability gain, not a perf one — is the mission's centre of gravity.** Full record:
> `docs/plans/MISSION_5_SPRINT_TRACKER.md` (D.1, D.2, D.5; "ROGER'S GATE-D DECISION").

**This does not violate "re-run the engine, never invert a formula."** The derivative comes from the
*actual model* (dual numbers / a tape over the real `run_financial_model`), not from hand-algebra on a
guardrail formula — **and every reported answer is confirmed by one real, un-differentiated engine
re-run** before it ships. AD accelerates the search; it never replaces the answer.

**Start Discovery from this finding, do not rediscover it:** reverse-mode AD (true AAD) wins when
inputs vastly outnumber outputs. This problem is **inverted — 4 levers in, ≤7 guardrails out.**
Forward-mode AD via **dual numbers** needs 4 passes, is far simpler than a tape, and needs **no autograd
dependency.** But justify the choice with **MEASUREMENTS against the real 4-in/≤7-out shape**, not by
reaching for the famous name. The **hardest part** is differentiating through `irr.py`'s bracketed Brent
root-find (`irr` `:188`, `_brent_root` `:83`): decide between the **implicit function theorem** and
**differentiating the converged root**, and document the assumptions and checks. Design the **AD-Jacobian
output API (the clean 7×4 seam)** in Half A — Half B's optimizer consumes it.

**Half B (only after the internal AD checkpoint = GO): the multi-lever recourse optimizer.** Today
recourse answers only single-lever questions ("any ONE of these closes it"). But an investor may move
several levers at once, so Half B adds a **second report section** — alongside the single-lever menu.
Both ship (Roger: offer both, we don't know if they can move one lever or several).

> **⚠ CORRECTED 2026-08-31 (Roger, C4(b)) — the description below is the ORIGINAL, now-superseded
> design.** No "top-3" cut and no Lagrangian/KKT: Roger's settled architecture is **one minimal-ask
> proposition per multi-lever subset** (≤ 11 propositions across the 11 non-singleton subsets of the 4
> levers), each seeded by the AD gradient's *direction* and solved for *distance* by subset-restricted
> bisection (Lagrangian penalty machinery measured as a wash, dropped). The smallest-total-ask
> proposition is **labelled** "cheapest total negotiation" — an `argmin` over the already-computed set,
> not a separate ranked search — so **there is no ranking at all**. See
> `docs/plans/MISSION_5_SPRINT_TRACKER.md` ("FINAL HALF B ARCHITECTURE") for the full design. **Half B
> is now the mission's centre of gravity as a product/capability gain, not a perf one** — see the
> rationale correction below.

**Original chartered design (superseded, kept for the record):** it was a **constrained optimization**
solved with a **Lagrangian/KKT method** (augmented Lagrangian / SQP / projected-gradient / interior-point
— Discovery picks the concrete one **by measurement**) consuming Half A's exact AD Jacobian, made global
with **deterministic multi-start** (fixed grid/scatter seeds — never stochastic). **The core new
engineering task** is a **unified all-four-lever
joint combination-plausibility gate**: today `_judge_plausibility` (`recourse.py:609`) judges one lever
at a time — the rejector's axes are market-hypothesis deltas, rent/opex have no rejector axis, price
reaches it only via a cap-rate proxy (which is why `RATE_MAGNITUDE_THRESHOLD` `recourse.py:130` and
`_MAGNITUDE_RELATIVE_THRESHOLD` `recourse.py:120` were bolted on). Unify these into one gate that judges
a **full four-lever combination**, including **joint** plausibility (cutting price AND raising rent may
each be individually fine yet jointly implausible). **What makes a combination plausible is a founder
product call.** Feasibility-not-optimization: FILTER to plausible combinations (no cross-lever cost
normalization); the gate is a deterministic boolean **feasibility projection**, not a differentiable
objective term — the gradient comes from the guardrail margins. Top-3 selection is normalization-free
(**parsimony · within-axis magnitude · diversity**, DiCE-style). **Interpretable real-lever coordinates
only** — a blended/singular direction may be an internal heuristic, translated back before display; NO
PCA/eigen/SVD/LDA, NO learned surrogate, NO TPE/Bayesian optimization (the one-reason rationale, recorded
in the charter's §"Design decisions": we OWN the exact, cheap, post-Half-A-differentiable generating
function; every learning/decomposition tool targets the opposite regime). **Every combination confirmed
by one real engine re-run**, exactly as single-lever answers are.

## Read these first (canonical, in order)

1. `docs/plans/MISSION_5_forward_mode_differentiation.md` — the charter (baseline, branch, in/out of scope,
   waves, DoD, agent roster, binding constraints, gates, open-items dispositions, the integer-cents
   sibling-successor note). Authoritative for scope.
2. `docs/plans/MISSION_5_SPRINT_TRACKER.md` — the live task tracker you keep current.
3. `docs/manual testing/MISSION_5_MANUAL_TESTING.md` — the acceptance/manual-test plan you keep accurate
   as work lands, and that Roger validates by hand at the mission gate.
4. `docs/plans/ROADMAP_TRACKER.md` §1, §3, §4 (backlog rows for the open items + the integer-cents
   sibling), §5.
5. The seams you compose (re-read each before touching): `src/market/recourse.py` (`compute_recourse`,
   `_bisect`, `_rerun`, `_perturb`, `_search_one`, `is_genuinely_close`), `src/core/finance/engine.py`
   (`run_financial_model` `:638`, `forecast_metrics` `:671`, `precompute_income` `:186`,
   `_forecast_core` `:309`), `src/core/finance/irr.py` (`irr` `:188`, `_brent_root` `:83`),
   `tests/core/finance/test_golden_forecasts.py` (bit-exact `:188`; the two documented regenerations
   `:36-119`) + `tests/core/finance/generate_golden_forecasts.py` + `tests/data/golden/finance_engine_forecasts.json`,
   `tests/perf/bench_finance_engine.py` (PRIMARY 5,000u/100y `:79`, `BUDGET_MS = 250.0` `:97`).

Re-read any `path:line` you touch before changing it. The graph and this charter reflect a snapshot
commit, not necessarily HEAD (two prior missions found charter path drift).

## Environment (critical — the common conda path is WRONG)

Run all project Python in the `airedeal` conda env:
`source /home/rtokime/anaconda3/etc/profile.d/conda.sh && conda activate airedeal`
(NOT `~/miniconda3` — that path does not exist and silently falls back to the wrong interpreter).
Confirm `which python` → `/home/rtokime/anaconda3/envs/airedeal/bin/python` before trusting any command.

## Baseline & branch

`base = main @ 7cfd449, synced 2026-08-31.` Re-confirm at Wave Sync. Branch:
`mission/5-forward-mode-differentiation`, cut off freshly-synced `main`. Surface any origin delta to Roger at
Wave Sync; never force-push; push only at Roger's instruction.

> **⚠ Do not trust the brief's perf numbers as fact.** The brief says "Mission 4 left it at 73 ms, down
> from 13 s." The committed benchmark at `7cfd449` reads **best 181–197 ms / median up to ~213 ms** for
> the budgeted 5,000u/100y row (`BUDGET_MS = 250.0`, re-baselined from 120 on 2026-08-30); "30 ms"
> appears nowhere in code. Treat 30 ms as Roger's *target* and 73 ms as an **unverified** figure to
> reconcile against a fresh measurement in Discovery (D.2). Report the *measured* before→after.

## What you are building (scope)

**Half A — tolerance + forward-mode (tangent-linear) differentiation + single-lever acceleration:**
* **The tolerance rule (FIRST).** Relax the golden harness from bit-exact to **~1e-9 relative**,
  **anchored to the ORIGINAL golden**. It must still **catch the ~9.4e-8 injected rounding bug** (the
  calibration point: 1e-9 catches it, 1e-6 does not — **⚠ "~9.4e-8" is a contract constant bound to the
  reproducible `round(payment, 4)` recipe, not a prior measurement; its real measured signature is
  1.1325e-7 across 1,613 fields, `git log --all -S"9.4e-8"` returns only the Mission 5 charter commit
  `87efd22`; corrected 2026-08-31, C4(b) — see the manual-testing doc, Case 1**), and must surface an
  **"approaching-tolerance"** state that demands **written justification** rather than a silent green.
  Guardian VETO reviews this design as a values-level relaxation before any AD code.
* **AD-accelerated single-lever recourse (only if Gate D says GO).** Forward-vs-reverse decided by
  measurement; exact partial derivatives of guardrail metrics wrt the four levers, from the real engine;
  Newton on the failing guardrail; **every answer confirmed by one un-differentiated engine re-run**,
  falling back to the bisection's confirmed point on failure. Ship the **7×4 AD-Jacobian output API** as
  a clean seam — Half B consumes it.
* **Perf measured against 30 ms** for the 5,000u/100y row (honest baseline ~180 ms / ~150 probes, NOT
  the brief's unverified 73 ms); probe-count drop (~10–20 → ~3–4) shown.
* **numpy re-measurement** (Mission 4 rejected it; re-measure, don't assume).
* **Open items:** money-field lower bounds (negative price rejected cleanly), horizon `le=50`→`le=100`,
  CLI out-of-range-horizon clean message (no traceback) — each with a RED test.
* **Docs (Half A)** — tolerance rule + (if shipped) AD search, at STANDARD tier, verified against real
  symbols.

**Internal AD go/no-go checkpoint** — prove the AD foundation (single-lever AD matches bisection within
tolerance; IRR/Brent sound; 7×4 Jacobian API stable) BEFORE any optimizer code. GO → Half B; NO-GO →
Half B defers, Half A ships alone (record explicitly).

**Half B — multi-lever recourse optimizer (only if the AD checkpoint = GO). ⚠ Design superseded
2026-08-31 — see the correction above; the bullets below are corrected to match Roger's settled
architecture (`docs/plans/MISSION_5_SPRINT_TRACKER.md`, "FINAL HALF B ARCHITECTURE"):**
* **A second report section listing up to 11 minimal-ask propositions** (one per surviving lever
  subset), unranked, the smallest-total-ask one labelled "cheapest total negotiation" — alongside the
  existing single-lever menu. Both ship. Flag-don't-remove; honest-null. (Originally chartered as a
  ranked "top-3 actionable combinations" section — superseded, no ranking is needed.)
* **AD-gradient-seeded direction + subset-restricted bisection for distance** over the four levers,
  consuming Half A's AD Jacobian, one solve per lever subset (**deterministic**). (Originally chartered
  as a Lagrangian/KKT constrained optimization — measured as a wash against this approach and dropped.)
* **The unified all-four-lever joint combination-plausibility gate** — the core new engineering; unify
  `_rejector_flagged` (`recourse.py:519`) + `_magnitude_flagged` (`recourse.py:584`) into one gate that
  judges a full combination, including joint plausibility. What makes a combination plausible is a
  founder product call. **(Unchanged by the design correction above.)**
* **No selection criterion needed** — every surviving subset's proposition ships; distinctness is
  structural (one per subset); interpretable real-lever coordinates only (no decomposed basis
  surfaced, unchanged). (Originally chartered as "normalization-free top-3 selection" — superseded.)
* **Every proposition confirmed by one real engine re-run. (Unchanged.)**
* **RED suite** — multi-start determinism, feasibility gate (incl. jointly-implausible-but-individually-
  fine), diversity, parsimony, local-minima, every-combination-confirmed-by-rerun.
* **Docs (Half B)** — the two-section output + unified gate, at STANDARD tier, verified against real
  symbols.

## Waves & gates

Wave Sync (confirm `main @ 7cfd449` canonical/clean; STOP if a later mission is mid-flight; re-confirm
anchors; pin baseline battery + pre-mission report sha) → Wave Branch
(`mission/5-forward-mode-differentiation`) → Wave Discovery (BOTH halves: AD forward-vs-reverse MEASURED;
IRR/Brent differentiation; tolerance design; 7×4 Jacobian API design; perf baseline reconciling 73 ms;
**Half B design — optimizer method selection + rejector-unification + top-3 selection**) → **Gate D**
(guardian **VETO on the invariant relaxation** + founder product calls **incl. the Half B combination-
plausibility rule + top-3 selection policy** + perf **go/no-go** on the AD portion — all blocking; **no
security gate**) → **Wave Implementation Phase A** **T-FIRST** (tolerance rule + its RED suite +
open-item fixes; then single-lever AD + the 7×4 Jacobian API, only after T is green, the VETO is lifted,
and Gate D said GO) → **INTERNAL AD go/no-go checkpoint** (GO → Phase B; NO-GO → Half B defers, Half A
ships alone) → **Wave Implementation Phase B** (the multi-lever optimizer on the now-stable Jacobian:
Lagrangian/KKT + multi-start + unified gate + diverse top-3 + the new report section; every combination
confirmed by a real re-run) → Wave Validation (full battery; BOTH ruff commands; within-tolerance golden;
perf recorded vs 30 ms; every manual-test command runs, incl. Half B cases) → **Gate V** (code review +
guardian re-check VETO) → **Mission gate (Roger)** → Wave Integrate.
Check every DoD box in the charter before requesting the mission gate.

> **Two go/no-go structures are real.** (1) The tolerance rule is independently valuable and ships first;
> if the measured AD study + IRR-differentiation analysis show the win does not justify the finance-core
> blast, Roger may stop the mission after the tolerance rule ships. (2) The internal AD checkpoint gates
> Half B: if the AD foundation doesn't prove out, Half B defers and Half A ships alone. AD is a measured
> bet, not a foregone conclusion; the optimizer builds only on a proven Jacobian.

## Binding constraints (non-negotiable)

1. **Every reported number — single-lever AND every combination — is confirmed by a real engine
   re-run.** AD accelerates the search, never authors the answer. Newton (or the optimizer) proposes;
   one un-differentiated `run_financial_model` re-run confirms; on failure, fall back to the bisection's
   confirmed point (`_search_one` already models this). Non-independence is real; re-run, never invert.
2. **Tolerance rule ships FIRST and governs everything after.** Anchor to the ORIGINAL golden; ~1e-9
   relative; catches ~9.4e-8; approaching-tolerance ⇒ written justification. No AD code until it is
   green and the guardian VETO on its design is lifted.
   **And: the internal AD checkpoint gates Half B — no optimizer code until AD is proven (single-lever
   matches bisection within tolerance; IRR/Brent sound; 7×4 Jacobian API stable). NO-GO → Half B defers.**
3. **Finance-core changes are high-blast and justified.** Mission 4 already touched `engine.py`,
   `irr.py`, `amortization.py`; extend for AD only with explicit justification, guardian sign-off, and
   every golden change within tolerance and documented. The verdict stays authored by `synthesize_thesis`.
4. **Deterministic; no new external surface; no network; no AI/model.** Same inputs ⇒ same
   `RecourseAnalysis` (within tolerance where AD is involved).
5. **New dependencies need written justification + re-measurement.** numpy was rejected in Mission 4 on
   measurement; re-measure. No autograd/JAX/PyTorch unless measurement forces it and Roger approves.
6. **Prove-the-test** — every fix ships a test that turns RED on revert; demonstrate with real failure
   output.
7. **Quality gate** — `ruff format --check` **AND** `ruff check` **AND** `mypy .` clean; coverage ≥80%.
   RUN BOTH ruff commands (Mission 4 lesson: an agent reported "ruff clean" having run only `ruff check`).
8. **Doc reconciliation is a reasoning task** — STANDARD tier or above, output **verified against the
   real symbols** (Mission 4 fabricated 7 of 8 documented model fields when this was routed cheap).
9. **Git** — branch off freshly-synced `main`; no PRs; merge only after Roger's mission gate; never
   force-push `main`; reconcile any origin delta; push only at Roger's instruction.

## Bounded product calls (founder-proxy, Gate D)

Bounded — do not let these sprawl into general threshold decisions: (a) ratify the tolerance value
(~1e-9); (b) the `GENUINELY_CLOSE_MAX_FAILS` decision (currently 3, chosen by necessity in Mission 4 —
this is the one near-miss threshold the mission may decide); (c) dispositions for the open items —
which money fields get lower bounds and the floor semantics, ratifying horizon `le=50`→`le=100`, and
the CLI clean-message polish; **(d) the Half B calls — what makes a four-lever COMBINATION plausible
(the unified gate's rule).** (Top-3 selection policy is superseded — see the Half B correction above;
Roger's final design ships all surviving propositions unranked with a "cheapest total negotiation"
label, so there is no selection policy left to ratify.) Route all to `principal-founder-proxy`.

## Orchestration protocol

* **Agents (fleet in `.claude/agents/`; ≤3 concurrent):** `app-evaluator` (grades/gap severity),
  `staff-python-engineer` (AD design + Half B constrained-optimization design at top reasoning tier;
  tolerance rule; AD machinery; the optimizer + unified plausibility gate; open-item fixes),
  `principal-performance-engineer` (perf baseline, go/no-go, benchmark), `principal-founder-proxy`
  (product calls incl. the Half B combination-plausibility rule + top-3 policy), `principal-principles-guardian`
  (**VETO on the invariant relaxation**, Gate D + Gate V), `staff-qa-test-engineer` (RED suites, Half A
  + Half B), `staff-report-experience-designer` (the two-section report output), `staff-documentation-maintainer`
  (docs, STANDARD), `staff-code-reviewer` (Gate V). Roger holds the mission gate. **No
  `principal-security-engineer`** — no external input surface. **Read the live fleet before dispatch;
  don't select from memory.**
* **Cost routing:** **invoke `staff-cost-aware-model-router` at kickoff** to confirm tiers BEFORE the
  first dispatch batch. Planner proposal: AD design/IRR-differentiation reasoning AND the Half B
  constrained-optimization design + Lagrangian/multi-start implementation → **fable (top)** — the
  gnarliest math on the board; perf, evaluator, founder calls, guardian VETO, go/no-go → opus
  (capable); tolerance rule, single-lever AD impl, report output, tests, code review → sonnet
  (standard); **docs → sonnet (STANDARD, NOT haiku)**. Record `task → agent → tier` in the tracker; log
  any deviation at dispatch.
* **Verify inline:** never trust an agent's "done" — re-run its tests, re-read its diff, revert-check
  each RED test (especially the ~9.4e-8 tolerance calibration and the AD-vs-rerun agreement),
  git-verify finance-core changes are justified and every golden change is within tolerance and
  documented, confirm the anchor-to-origin is structural, and tick the DoD before marking DONE.
* **Branch-and-integrate:** Wave Sync = confirm `main @ 7cfd449` canonical + clean, `git fetch`, surface
  any origin delta, re-confirm anchors, run the battery green + pin the baseline. Wave Branch =
  `git switch main && git switch -c mission/5-forward-mode-differentiation`. Wave Integrate (after Validation
  GREEN **and** Roger's mission gate) = `git fetch`, rebase/merge onto latest, re-run the **full**
  battery post-rebase (a pre-rebase green does not count), `git merge --no-ff`, reconcile+push only at
  Roger's instruction, record the merge sha. Never self-approve; never force-push `main`.
* **Tracker discipline:** update `docs/plans/MISSION_5_SPRINT_TRACKER.md` after every state change —
  full updates (counts + wave summary + rows), never partial; carry the tests-tree SHA on every count;
  date every gate record.
* **Manual-testing discipline:** keep `docs/manual testing/MISSION_5_MANUAL_TESTING.md` accurate as
  work lands — every command in it must actually run and produce the stated result by the time the
  mission gate is requested. The boxes are Roger's to flip; the mission gate is not clear until the
  document-level box reads VALIDATED.
* **Research-first + YAGNI:** read the seam before changing it; build only what the charter scopes. Do
  NOT write AD code before the tolerance rule is green and the VETO is lifted; **do NOT write any Half B
  optimizer code before the internal AD checkpoint records GO**; do NOT invert a guardrail formula; do
  NOT ship any recourse number or combination without a confirming engine re-run; **do NOT surface a
  decomposed basis (PCA/eigen/SVD/LDA) or reach for a learned surrogate / TPE / Bayesian optimizer —
  classical constrained optimization on the real model is the decided family (charter §Design
  decisions)**; do NOT start the integer-cents money refactor (it is the named sibling-successor
  mission); do NOT add a UI, a data feed, or a heavyweight AD framework without measurement + Roger's
  approval. If Phase B shows signs of sprawling past the solo-dev cap even after a clean AD checkpoint,
  surface it to Roger as a candidate to carve Half B back out — do not push through silently.

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

**Confirm the sequencing pre-condition:** run `git log --oneline -5 main` and verify the tip is the
Mission 4 merge `7cfd449`. If a later mission is mid-flight, STOP and tell Roger. Otherwise execute
**Wave Sync**: `git fetch`, `git status --porcelain` (expect clean), confirm `main` is canonical latest
and in sync with origin, surface any delta to Roger. Re-confirm every charter `path:line` against the
file at the real baseline (`compute_recourse`, `_bisect`, `_rerun` in `recourse.py`; `run_financial_model`,
`forecast_metrics` in `engine.py`; `irr`/`_brent_root` in `irr.py`; the bit-exact golden harness;
`bench_finance_engine.py`). Run the full gate battery (`pytest`, `ruff format --check`, `ruff check`,
`mypy .`, `python main.py`) green in `airedeal` — pin the suite count, coverage, tests-tree SHA, and the
pre-mission `python main.py` report sha256 in the tracker. **Invoke `staff-cost-aware-model-router`** to
confirm tiers. Then execute **Wave Branch**: `git switch main && git switch -c mission/5-forward-mode-differentiation`.
Update the sprint tracker after each step.

=== END MISSION PROMPT ===
