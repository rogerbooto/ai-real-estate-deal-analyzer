# Mission 4 Sprint Tracker — Actionable Recourse ("What would have to change?")

_Live tracker. The executing orchestrator keeps this current — full updates only (counts + wave
summary + rows), never partial. Date every gate decision. Carry the tests-tree SHA on every count
(Mission 2's hardest-won lesson: a number typed into a doc is a claim with no test behind it — pin it
to a commit)._

**Charter:** `docs/plans/MISSION_4_actionable_recourse.md` · **Handoff:** `docs/plans/MISSION_4_HANDOFF.md`
**Manual tests:** `docs/manual testing/MISSION_4_MANUAL_TESTING.md`
**Baseline:** `main @ <TBD at Wave Sync — after Mission 3 merges>` · **Branch:** `mission/4-actionable-recourse`

> **Status at charter time (2026-08-28): CHARTERED, NOT YET STARTED.** Mission 3
> (`mission/3-byo-onnx-provider`) is built and through Gate V but has **not** cleared Roger's mission
> gate or merged to `main`. Per the solo-dev one-mission-at-a-time cap, **Mission 4 does not begin
> until Mission 3 has merged.** Wave Sync establishes the real baseline against `main` at that point
> and re-confirms every charter `path:line`.

> Every subagent prompt issued in this mission MUST carry the GRAPHIFY CONTRACT verbatim (see the
> handoff). Any reachability/blast claim citing the graph is confirmed against the file at the graph's
> own `built_at_commit`, never the current tree (Mission 2's trust-boundary incident).

## Cost routing

Invoke `staff-cost-aware-model-router` at kickoff (standing rule §3a.1) to confirm the tiers below
BEFORE the first dispatch batch — not "only when ambiguous." Record the actual dispatch in each row's
"Agent → tier" column, and log any deviation from the confirmed table **at dispatch time**. Tier→model
mapping: **capable = opus · standard = sonnet · cheap = haiku**. **No `principal-security-engineer`**
this mission — there is no external input surface (no file paths, no network, no untrusted input).

### Planner-proposed routing (router confirms at dispatch)

| Task | Agent | Tier |
| --- | --- | --- |
| EV.1 confirm axis grades / gap severity | `app-evaluator` | opus |
| D.1 recourse spec | `staff-python-engineer` | sonnet |
| PD.1 bounded product call (wording, currencies, flag-don't-remove copy) | `principal-founder-proxy` | opus |
| PF.1 perf sanity (measure vs vectorise) | `principal-performance-engineer` | haiku |
| GD.1 honesty VETO on spec framing | `principal-principles-guardian` | sonnet |
| I.1 recourse module + additive schema | `staff-python-engineer` | sonnet |
| I.2 RED suite (incl. non-independence trap) | `staff-qa-test-engineer` | sonnet |
| I.3 report section design + copy | `staff-report-experience-designer` | sonnet |
| I.4 docs (README / owning README / CHANGELOG; backlog #6) | `staff-documentation-maintainer` | haiku |
| GV.1 code review | `staff-code-reviewer` | sonnet |
| GV.2 guardian re-check (VETO) | `principal-principles-guardian` | sonnet |

Deviations from this table are logged at dispatch time in the row itself.

### Router confirmation — 2026-08-29 (`staff-cost-aware-model-router`)

**CONFIRMED as proposed — zero tier deviations.** Final spend shape: **2 opus · 7 sonnet · 2 haiku.**
The three judgment calls were adjudicated explicitly:

* **D.1 recourse spec → sonnet (not opus).** The charter's precision downgrades it: the lever→guardrail
  map, bisection bounds, convergence tolerance, "flip" semantics and the trap-case brief are all
  pre-specified, so this is execution against a checklist, not architecture. Agent escalates if the
  per-guardrail bounds or the trap case prove harder to construct than the charter assumes.
* **I.2 non-independence trap RED test → sonnet (not opus).** The conceptual trap is supplied by the
  charter (price cut moves loan + cap rate + cash-in together); what remains is test-case design and
  proving RED-on-revert — standard test methodology.
* **EV.1 `app-evaluator` → opus (kept).** Not pure confirmation: the task includes the founder-facing
  judgment "gap severity **justifies** this mission", which is a decision about whether to build.

No further downgrades judged safe: the haiku tasks (PF.1, I.4) are already mechanical, and every
VETO-holding gate review (GD.1, GV.1, GV.2) is floored at sonnet by routing policy. **I.3 is already a
tier split** — copy *strategy* originates at opus (PD.1 founder-proxy), copy *implementation* resumes at
sonnet against that locked voice.

## Status legend

`TODO` · `IN-PROGRESS` · `BLOCKED` (needs a prior gate or a product call) · `REVIEW` (agent says done,
orchestrator verifying) · `DONE` (verified inline) · `DEFERRED`

## Overall progress

- Mission status: **UNBLOCKED and running (2026-08-29).** Mission 3 shipped — merge `8b59399`,
  `main` at `bfdf565`, validated by Roger 9/9 PASS. Wave Sync and Wave Branch are DONE; D.1 (Discovery
  spec) is dispatched. The sequencing pre-condition is now satisfied as the charter intended.
- Tasks: **3 / 13 DONE** · 3 IN-PROGRESS (Gate D batch: PD.1 · PF.1 · GD.1) · 7 TODO
  (EV.1 dispatches as the 4th Gate D task when a slot frees — charter cap is ≤3 concurrent)
- **Suite baseline — PINNED at `main @ bfdf565`, measured in `airedeal` 2026-08-29:**
  * **684 passed**, coverage **87.20%** (gate ≥80%)
  * `ruff format --check` → 216 files already formatted · `ruff check` → All checks passed ·
    `mypy .` → Success, no issues in 214 source files
  * **tests-tree SHA** (sha256 over sorted `tests/**/*.py`): `c39ed9e81dc7633de632fcea6ba4e7d3c495b61384ad15bc3f4cd09d287ca524`
  * **Pre-mission report sha256** (`python main.py` → `investment_analysis.md`, gitignored):
    `545e22b20b967b37c5b7ba20477f9df7c85f5b5a7c151f2e0d79b543d69d31f0` — **verified deterministic**
    (two consecutive runs, identical sha). This is the byte-identity baseline for constraint 5.
  * Baseline deal verdict: **DECLINE**. Note for I.2/Validation: the default demo deal is *not* a
    CONDITIONAL near-miss, so the "no near-miss ⇒ byte-identical output" case is what `main.py`
    exercises; near-miss coverage needs a purpose-built fixture.
- Gates cleared: **0 / 3** — ☐ Gate D (pre-impl: guardian + founder call + perf call) · ☐ Gate V
  (post-impl: code review + guardian) · ☐ Mission gate (Roger)
- Product calls outstanding: **1** — the bounded founder-proxy call (PD.1): lever wording, default set
  of currencies per gap, flag-don't-remove copy. Decide at Gate D (or earlier if it blocks Discovery).
- Manual-testing doc: **NOT VALIDATED** (authored as an acceptance plan; Roger validates by hand at the
  mission gate — every box currently unchecked)

## Wave summary

| Wave | Name | Tasks | DONE | Status | Gate |
| --- | --- | --- | --- | --- | --- |
| Sync | Wave Sync (re-sync after M3 merges; re-confirm anchors; pin baseline) | 1 | 1 | **DONE** | — |
| Branch | Wave Branch | 1 | 1 | **DONE** | — |
| EV | Evaluator confirmation (grades / gap severity) | 1 | 0 | TODO — **re-sequenced to run at Gate D, after D.1** | — |
| D | Discovery (recourse spec) | 1 | 1 | **DONE** — verified inline | — |
| GD | Gate D (guardian VETO + founder product call + perf call) | 3 | 0 | **IN-PROGRESS** | **Gate D** |
| Impl | Implementation (module+schema · tests · report copy · docs) | 4 | 0 | TODO | — |
| Val | Validation | 1 | 0 | TODO | — |
| GV | Gate V (code review + guardian) | 2 | 0 | TODO | **Gate V** |
| Int | Wave Integrate | 1 | 0 | TODO | Mission gate: Roger |

## Wave Sync

> **DONE — 2026-08-29.** Sequencing pre-condition **MET**: Mission 3 merged (`8b59399`) and pushed;
> `main` = `origin/main` = **`bfdf565`**, no origin delta, working tree clean apart from the untracked
> `MISSION_4_*` docs. (An earlier attempt on 2026-08-29 was held at this gate while Mission 3 was still
> unmerged and uncommitted; Roger declined a concurrent worktree and elected to wait. That hold is now
> lifted by Mission 3 shipping.)
>
> **Charter anchors re-verified at the real baseline `bfdf565` — all exact, no drift:**
> `synthesize_thesis` `chief_strategist.py:137` · the **seven live guardrails** `chief_strategist.py:172-179`
> (`dscr_ok`, `spread_ok`, `irr_ok`, `coc_ok`, `cf_y1_ok`, `cf_all_ok`, `no_cap_floor_breach`) ·
> `build_baseline_outlook` `crew.py:65` · `run_scenarios` `scenario_runner.py:126` ·
> `reject_unrealistic` `rejector.py:54` · `ScenarioAnalysis` `models.py:1277` ·
> `InvestmentThesis` `models.py:282` · Market Scenarios append pattern `generator.py:1246`.
> Mission 3 touched none of them (it landed in CV / ONNX / CLI). Unlike the two prior missions, this
> charter shows **no path drift** — at either baseline.

| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| S.1 | **After Mission 3 has merged to `main`:** `git fetch`; confirm `main` is canonical latest; surface any origin delta to Roger (do not push); re-confirm every charter `path:line` at the real baseline; run the full gate battery green in `airedeal`; pin suite count + coverage + tests-tree SHA + pre-mission `python main.py` report sha in Overall progress | orchestrator (inline) → n/a | **DONE** (baseline `bfdf565` pinned above) |

## Wave Branch

| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| B.1 | `git switch main && git switch -c mission/4-actionable-recourse` off freshly-synced `main` | orchestrator (inline) → n/a | **DONE** — branch cut off `bfdf565` |

## Evaluator confirmation

> **Re-sequenced 2026-08-29 on the router's dispatch-order call.** EV.1 was originally slated to run
> concurrently with Discovery. It is not runnable there: the task requires recording *"the Reports/Advisor
> axis lines the recourse section moves"*, which cannot be answered before D.1 defines what the recourse
> section **is**. Running it blind either omits that clause or assumes a wrong section shape and is
> re-done — opus tokens spent twice. EV.1 is a confirmation/synthesis task, so it resumes against a
> locked spec rather than originating against placeholders. It therefore joins the **Gate D** batch.
>
> This costs one serialized Discovery step and buys back the rework. Dispatch order is now:
> **Wave Branch (inline) → D.1 solo → Gate D batch (EV.1 · PD.1 · PF.1 · GD.1, ≤3 concurrent).**
> PD.1 was checked for the same dependency and does **not** block Discovery: the product call (lever
> wording, currency set, flag-don't-remove copy) is input to **I.3** (report copy), not to D.1
> (the recourse algorithm). The charter's "earlier if it blocks Discovery" valve is not needed.


| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| EV.1 | **Re-sequenced: runs at Gate D, after D.1 lands** (see routing note below). `app-evaluator` confirms the current composite + per-axis grades and the gap severity that justifies this mission (do not re-derive; consult). Record the Reports/Advisor axis lines the recourse section moves | app-evaluator → opus | TODO |

## Wave Discovery

| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| D.1 | Recourse spec (no production code): (i) the four levers and each lever→guardrail mapping against the **live seven** guardrails (`chief_strategist.py:172-179,227-252`); (ii) the bounded-search strategy — bisection bounds per lever, convergence tolerance, monotonicity assumption per guardrail and how it is checked, the definition of "flip" per guardrail; (iii) the rejector integration point (how a perturbed scenario is judged plausible via `reject_unrealistic`/snapshot bounds) and the flag-don't-remove mechanism; (iv) the multi-failure "cheapest single fix" ordering rule; (v) the honest-null definition; (vi) the additive `RecourseLever`/`RecourseAnalysis` shape mirroring `ScenarioAnalysis` (`models.py:1277`); (vii) **the non-independence trap test design** — a concrete case where the naive inverted-formula answer differs measurably from the re-run answer | staff-python-engineer → sonnet | **DONE** — `docs/plans/MISSION_4_DISCOVERY_SPEC.md` (667 lines), verified inline 2026-08-29 |

## Gate D — pre-implementation (blocking)

### D.1 orchestrator verification — 2026-08-29 (what I checked myself, not what the agent claimed)

* **Zero code diff confirmed.** `git diff --stat bfdf565 -- src tests` is empty; `git status` shows
  docs only. Discovery wrote the spec and nothing else.
* **The non-independence trap numbers are REAL — independently re-derived.** I wrote my own bisection
  from scratch against the live engine on `data/sample_listings/36_kelly_moncton/inputs.json` and
  reproduced the spec's figures **to the cent**:
  * true re-run flip point, `purchase_price` lever vs. `coc` guardrail: **$341,057.63** (CoC there =
    exactly 3.000000, the inclusive bar)
  * naive formula-inversion answer (denominator frozen at baseline `acquisition_cash` = $45,991.00):
    **$338,814.34**, whose **real** CoC is **3.4073%** — the naive method believed it was landing
    exactly on 3.00%
  * **divergence $2,243.29**, ~22× the spec's $100 price tolerance — a trap test built on this cannot
    pass by accident.
  This is a genuine, reproducible trap on the committed sample deal, not an invented example.
* **A finding worth recording:** Discovery first tried `dscr`/`spread`/`cap_floor` for the price lever
  and found them **exactly** invertible — `amortization_payment` is exactly proportional to principal
  and `cap_rate = noi/price`, so no coupling exists there. `coc` is the **one** guardrail in this engine
  where numerator *and* denominator both move with price. That negative result is load-bearing: it
  means the trap test had to be found, not assumed, and it names the only pair that can carry it.

### Charter drift found by Discovery — three items (recorded; §0 of the spec)

1. **`reject_unrealistic` does not fit three of the four levers.** The charter said plausibility
   "reuses the machinery Mission 1 shipped". In fact `MarketHypothesis` bounds five market-condition
   **growth-rate** deltas; only **interest rate** maps one-to-one. **Purchase price, rent level and
   annual opex have no axis at all** — they are absolute one-time level changes. Verbatim reuse would
   have been a category error. Spec designs a derived cap-rate-delta proxy (real reuse, 2 of 3) plus a
   lever-native magnitude fallback (new — and the spec says so honestly).
2. **`InvestmentThesis` does not expose which guardrail failed.** The seven booleans are **locals** in
   `synthesize_thesis` (`chief_strategist.py:172-179`); the model returns only `verdict` +
   free-text `rationale`/`levers`. Recourse needs them on every perturbed re-run and no seam returns
   them today. → escalated to Gate D as the §6.1 seam choice.
3. **`resolve_snapshot` loud-fails exactly where it is most needed.** Its market-block-less fallback
   raises `ValueError` unless `inputs.market.cap_rate_purchase` is set — precisely the case where the
   levers do not move the cap rate, so a real snapshot cap is needed. Spec designs a narrower,
   always-available derivation off `baseline_forecast.purchase.cap_rate` instead.

### Open item escalated to this gate — the §6.1 seam choice

`InvestmentThesis` doesn't expose the seven guardrail booleans. **Option A** (Discovery's recommended
default): the recourse module **duplicates** the seven comparisons, importing the public threshold
constants, pinned by a parity test — zero diff to any shipped file. **Option B**: extract them into a
small pure additive helper that `synthesize_thesis` itself calls, with a golden parity test — single
source of truth, small behavior-preserving diff to `src/agents/chief_strategist.py`.

The charter's binding zero-diff constraint is scoped to **`src/core/finance/`**; `chief_strategist.py`
is not finance core, so **Option B does not violate it**. Orchestrator's lean is **Option B**
(duplicating threshold comparisons across files in a deterministic-first financial tool is the drift
that bites later; a parity test proves a duplicate *agrees* without removing the duplicate), but the
call is the guardian's. **GD.1 rules on it.**


| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| PD.1 | Bounded founder-proxy product call: (a) lever wording (the exact investor-facing phrasing per lever); (b) the default set of "currencies" shown per gap (e.g. $/unit/month AND % increase; $ off price AND % below asking); (c) the flag-don't-remove copy — how an implausible lever is presented with its reason. Bounded — do not let it sprawl into threshold decisions | principal-founder-proxy → opus | **IN-PROGRESS** (dispatched 2026-08-29) |
| PF.1 | Perf sanity: measure the naive re-run-per-perturbation cost (levers × guardrails × bisection steps × rejector) at report time on a representative deal, and make the **explicit** call — fast enough for a first version, or must it vectorise now? Record the measurement, not a guess (Roger's "measure before optimising") | principal-performance-engineer → haiku | **DONE** — fast enough for v1; extrapolation corrected inline (168 ms worst, not 3,100 ms) |
| GD.1 | Honesty VETO on the spec framing: WOULD-not-WILL wording, flag-don't-remove (decision 1), cheapest-first-flag-the-rest (decision 2), honest-null (decision 3), and that no lever line asserts a certainty the engine did not produce | principal-principles-guardian → sonnet | **DONE** — CLEAR-WITH-CONDITIONS (2 blocking; Option B ruled) |

### Gate D decision record — **CLOSED 2026-08-29** (all four tasks in; Roger's four decisions recorded)

#### GD.1 — `principal-principles-guardian`: **CLEAR-WITH-CONDITIONS** (2 blocking items)

**Blocking modification #1 — the DECLINE honest-null must not be discarded.** Spec §5 proposed that
an all-null DECLINE renders **no** section, and §6.4 nulls `recourse` back to `None` — so the analysis
*was run*, an answer *was found* ("nothing realistic closes this"), and then that answer evaporates
before it reaches `OrchestrationResult`, indistinguishable from never having been attempted.

The guardian tied this to **project precedent, not taste**: `src/core/README.md` records a prior Gate 3
where a real computed caveat ("Approximate scenario; does not re-run engine.") "never reached the
rendered page" — and both offending files were **deleted** for it. This is the same bug shape in a new
feature. It also rejected the determinism justification: constraint 5's byte-identity applies to the
case recourse *is not computed at all* (BUY); found-but-hidden is not that case, and rendering one
honest line is exactly as deterministic as rendering nothing.

Required: either (preferred) render a short fixed single line for the honest-null DECLINE, or gate
*whether recourse is attempted at all* on an independent pre-computation "genuinely close" test —
never use the downstream `honest_null` result post-hoc to justify hiding what was already computed.

It also surfaced an unexamined conflation: `honest_null` ("did any lever close any guardrail") is not
the charter's own scoping predicate ("is this deal genuinely close"). A deal whose only failing
guardrails are ones no lever can reach is arguably the *most* "genuinely close, nothing to suggest"
case there is — and it is precisely the one the proposed rule would go silent on.

**Blocking item #2 — §6.1 seam: ruled OPTION B** (extract `guardrail_checks(...)` as a pure additive
helper that `synthesize_thesis` itself calls, pinned by a golden parity test). This overrides
Discovery's Option A recommendation and matches the orchestrator's lean — but on stronger grounds than
the orchestrator had. The guardian found **this file's own precedent, twice**:
* `spread_target_for` docstring (`chief_strategist.py:57-75`): *"The strategist must test the same
  number, or a report can print 'cap-rate spread below target' under Warnings while its own Investment
  Thesis says the spread meets target."* — fixed with a **shared function**, not two call sites.
* cap-floor comment block (`chief_strategist.py:202-217`): *"The breach/clear decision always comes
  from the engine's warning, never from a comparison re-done here."*

Option A would reintroduce exactly the anti-pattern this codebase twice engineered away from. A parity
test protects against *known* cases; a shared helper makes divergence **structurally impossible**.
Confirmed `chief_strategist.py` is agent-layer, not finance-core — Option B does not trip the charter's
zero-diff constraint.

**Cleared as written:** the four-lever design, reachability probe, bisection discipline, rejector
integration, cheapest-first ordering, and the non-independence trap test. §7's framing judged honest —
because every candidate is a real re-run (§2.3), the optimistic-direction failure mode is structurally
excluded feature-wide, not merely untested for this pair.

**Carried forward to Gate V** (guardian's own forward note, recorded so it is not lost):
1. Rendered copy must not imply the trap error is *always* conservative — the mechanism, not the
   observed direction, is load-bearing.
2. Confirm `remaining_after_cheapest` cannot be rendered below the fold or omitted when non-empty — a
   reader stopping at the cheapest fix must not mistake it for sufficiency.

#### Roger's Gate D decisions — 2026-08-29 (all four, binding)

1. **DECLINE rendering → pre-computation closeness gate.** Decide *before* running recourse whether the
   deal is genuinely close. Not close ⇒ never compute, section absent, byte-identical output. Close ⇒
   render whatever was found, **including the honest-null line**. This is the guardian's Option 2 and it
   resolves the guardian/founder-proxy conflict: nothing computed is ever hidden, and a deep DECLINE
   still does not get a section that reads as a rescue plan.
2. **Placement → adjacent to the Investment Thesis** (EV.1's R3), *not* the append-after-Warnings slot
   the founder-proxy proposed. In the append slot the section lands ~115 lines below the verdict it
   explains, separated by five tables. Overrides PD.1's placement call.
3. **The old heuristic lever block → visibly marked as heuristic.** `_levers_for`
   (`chief_strategist.py:84-131`) prints unverified advice ("Increase down payment…", which is not even
   one of recourse's four levers) directly under the verdict. Its **logic stays untouched** (charter
   forbids repurposing `InvestmentThesis.levers`); only its **rendering** gains a visible qualitative/
   unverified marker, so a reader can tell guessed advice from computed.
4. **Fix the one-sided rejector now** — scope expansion approved beyond the charter's blast radius.
   `_rates_vs_cap_ok` (`rejector.py:7-9`) returns `(interest_rate_delta - cap_rate_delta) <= 0.02`; a
   rate **cut** is negative, so it always passes — **the rejector cannot flag a rate cut at any
   magnitude** (confirmed by orchestrator against the file). Make it two-sided, with a test proving a
   rate cut *can* be rejected. Note this touches shared Mission 1 machinery — regression-test the
   existing scenario paths.

#### ⚠ CHARTER AMENDMENT — binding constraint 1 WAIVED by Roger, 2026-08-29

**Constraint 1 ("Zero `src/core/finance/` diff — the engine is a black box") is waived.** Roger
authorised three scope expansions after challenging the perf call and being shown measurements at
portfolio scale:

1. **Target scale = 5000 units, 50y+** (not the ~50-unit shape the mission was sized against).
2. **Vectorise `run_financial_model` inside Mission 4.**
3. **Fix the `irr.py` `OverflowError` inside Mission 4.**

**Process consequences — these are not optional:**

* **Gate D's clearance no longer covers the mission.** `principal-principles-guardian` cleared Gate D
  explicitly on the basis of the zero-finance-diff blast radius. That basis is gone. **Gate D must be
  re-cleared by the guardian under the amended constraint set before the engine rewrite merges.**
* The mission's character has changed from "additive report section, engine untouched" to "additive
  report section **plus a rewrite of the component every shipped number depends on**." Blast radius,
  review depth, and the manual-test plan all have to be resized accordingly.
* **PV.1 (golden-number harness) is a hard prerequisite for any engine edit** and was dispatched first,
  before any rewrite work, precisely so the rewrite can be *proved* equivalent rather than asserted.

#### The measurements that drove the amendment — orchestrator, 2026-08-29

Roger rejected the earlier "no scale issue" finding and asked for 5000 units to 100 years. **He was
right and the earlier finding was wrong** — it had been measured only to 1000 units, which understated
the problem. Full recourse (432 re-runs), total wall time:

| units | 10y | 30y | 50y | 100y |
| --- | --- | --- | --- | --- |
| 1000 | 1.28 s | 1.85 s | 2.39 s | 3.75 s |
| 2500 | 3.29 s | 4.47 s | 5.68 s | 8.97 s |
| 5000 | 6.62 s | 8.91 s | 11.37 s | **crash** |

**Also corrected: the earlier claim that a 30-year horizon "is not reachable through the normal path"
was WRONG.** `main.py:118` exposes `--horizon` and threads it through `run_orchestration`; 30y/50y/100y
are all reachable today. (`amort_years` — the mortgage term, default **30** — is a *separate* field from
`horizon_years`, the analysis window, default 10. The two were conflated.) The PF.1 agent's 30-year
scenario was therefore legitimate; only its *numbers* were wrong.

**THE BOTTLENECK IS NOT THE ENGINE — it is `copy.deepcopy`.** At 5000 units, deepcopy costs ~12 ms
against the engine's ~3 ms (≈79% of per-iteration cost at short horizons): the re-run pattern
deep-copies a 5000-unit rent roll 432 times to change one scalar. Measured surgical-copy fix
(`model_copy(update={...})`, rebuilding only the mutated submodel):

| case | naive deepcopy | surgical | full recourse |
| --- | --- | --- | --- |
| 1000u / 30y | 4.69 ms | 2.17 ms (**2.17×**) | 2.03 s → **0.94 s** |
| 5000u / 30y | 22.6 ms | 9.72 ms (**2.33×**) | 9.78 s → **4.20 s** |
| 5000u / 50y | 29.4 ms | 16.0 ms (**1.83×**) | 12.68 s → **6.91 s** |

Results **bit-identical** (verified on `purchase.coc` and `years[0].dscr`). This costs ~nothing and
touches no finance-core code — folded into I.1. **Caveat flagged to I.1:** surgical copy shares
untouched submodels by reference, so it is only safe if the engine never mutates its input; I.1 must
verify that and report any in-place mutation (which would be a latent bug in the existing
`run_scenarios` path too).

Residual after the surgical fix is still ~6.9 s at 5000u/50y — that gap, and only that gap, is what
justifies vectorisation.

#### FINANCE-CORE BUG FOUND — `irr.py` OverflowError (Roger: fix inside Mission 4)

`run_financial_model` raises **`OverflowError`** at `src/core/finance/irr.py:83` —
`(1.0 + rate) ** t` inside the Newton-Raphson `npv` — when unit count is **≥3000 AND horizon = 100y**.
Boundary confirmed: 2000u/100y ok · 3000u/100y and 5000u/100y crash · 500u fine at every horizon to
100y. **Reachable in shipped code** via `main.py --horizon 100`. Newton probes a large rate and the
discount base exceeds float range. Pinned as a known-crash test by PV.1; fix is a separate task.

#### PF.1 addendum — Roger's scale challenge, measured 2026-08-29

Roger challenged the naive-re-run call: paying customers evaluate 10+ units, and deterministic math
should never be the bottleneck once AI/CV land. **Premise tested and found not to hold for this
engine**; the underlying architectural principle **confirmed and already satisfied.**

| units | ms/run | vs 2u | 432 re-runs |
| --- | --- | --- | --- |
| 10 | 0.138 | 1.2× | **60 ms** |
| 20 | 0.149 | 1.3× | 64 ms |
| 100 | 0.211 | 1.9× | 91 ms |
| 1000 | 0.859 | 7.7× | 371 ms |

**No knee exists** — 500× the units costs 4.7×. Structural reason: the engine sums rents to a portfolio
total then loops **per year**, so units are a summation, not a loop dimension. The scaling axis is the
**horizon**, not unit count (20u/50y = 0.554 ms > 1000u/10y = 0.859 ms is close; horizon dominates per
unit added). Vectorisation gain ≤371 ms at absurd scale; cost = rewriting `run_financial_model` to an
array-of-scenarios form — the component under the zero-diff constraint and the basis of every number
shipped. Bad trade at every measured point.

**`main.py` cProfile confirms Roger's own principle already holds:** of 760 ms in `run_orchestration`,
**673 ms is `_load_thumbnail` (`src/core/cv/runner.py:145`, 38 loads ≈ 18 ms each)**. The finance engine
does not appear in the top 18 cumulative-time functions. CV is already the dominant cost; recourse adds
~9% of what CV alone spends. **Decision unchanged (do not vectorise) — but on Roger's grounds, not
YAGNI's.** Revisit trigger recorded: **batch analysis across many listings**, not unit count.

#### PF.1 — `principal-performance-engineer`: **FAST ENOUGH FOR V1, do not vectorise**

Verdict **accepted** — and it is safer than the agent argued. Its core measurement reproduced under my
own benchmark (median **0.12 ms** per engine re-run), but **its large-deal extrapolation was wrong and
I corrected it**:

| case | measured median | 432 re-runs |
| --- | --- | --- |
| sample deal (2 units, 10y) | 0.123 ms | **53 ms** |
| 2 units, 30y | 0.288 ms | 124 ms |
| 20 units, 10y | 0.160 ms | 69 ms |
| 20 units, 30y | 0.389 ms | **168 ms** |

The agent claimed a large deal costs ~7 ms/call → **~3,100 ms** ("⚠ Concern", ~360% of baseline). The
real figure is **168 ms** — overstated by **~18×**. Two errors: (a) it asserted `O(horizon × units)`
linear scaling, but 10× the units costs only **1.3×** (the engine aggregates rent; it does not loop
per unit); (b) it assumed a per-deal 30-year horizon, but **`horizon_years` is not a `FinancialInputs`
field at all** — it is a `run_financial_model` keyword defaulting to `DEFAULT_HORIZON_YEARS = 10`
(`engine.py:18,95`), so a "30-year deal" is not reachable through the normal path. Its own arithmetic
also contradicted itself (20u×30y vs 2u×10y is 15×, not the 60× claimed).

Corrected picture: recourse adds **~53 ms to an ~870 ms report (6%)** on the sample deal, and **≤168 ms
even on a deliberately inflated deal**. No perf concern exists at any reachable deal size. Sample-deal
unit count is **2**, not the 4 the agent reported.



· Date: ____ · Founder product call (PD.1): ____ (lever wording / currencies / flag copy locked) ·
Perf call (PF.1): ____ (measure-vs-vectorise, with the measured numbers) · Guardian (GD.1): ☐ VETO /
☐ NO VETO / ☐ NO VETO WITH CONDITIONS (list) · Orchestrator sign-off: ____

## Wave Implementation (≤3 concurrent)

| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| I.1 | Build the recourse orchestration module: engine re-run bisection search per lever (single perturbed input on a deep-copied `FinancialInputs`, `run_financial_model` re-run, read `InvestmentThesis`/metrics — **never invert a formula**), rejector integration for plausibility, multi-failure cheapest-first ordering, honest-null; and the additive `RecourseLever`/`RecourseAnalysis` schema. RED-on-revert for each behaviour | staff-python-engineer → sonnet | **DONE** — verified inline: 712 passed (+28), cov 87.68%, zero finance diff, byte-identity exact |
| I.2 | RED-on-regression suite: **the non-independence trap case** (re-run answer ≠ naive inverted answer; passes only for re-run); rejector integration (implausible lever flagged not removed); multi-guardrail cheapest-first ordering; honest-null; determinism (byte-identical `RecourseAnalysis`). Each RED-on-revert demonstrated | staff-qa-test-engineer → sonnet | **DONE** — verified inline: 24 tests, trap RED-on-revert PROVEN with real failure output, 779 passed |
| I.3 | Report section "What would have to change?" — design + copy: the several-currencies block, WOULD-not-WILL phrasing, the flag-don't-remove presentation, the cheapest-first-with-remaining-gaps layout, and the honest-null message. Appended like the Market Scenarios overlay (`generator.py:1246`); absent (byte-identical) when no near-miss | staff-report-experience-designer → sonnet | TODO |
| I.4 | Docs: README + owning-subarea README + CHANGELOG `[Unreleased]` describe the new section honestly (no overclaim); draft the §4 backlog #6 closure note. `_Last reconciled_` stamps | staff-documentation-maintainer → haiku | TODO |

## ⚠ SYSTEMIC FINDING — pydantic constraints are enforced at construction only

Three separate defects found by three independent agents during Mission 4 share **one root cause**:
**declared field constraints on `src/schemas/models.py` / `src/inputs/inputs.py` are validated when a
model is CONSTRUCTED, and never again.** Every mutation path bypasses them.

| # | Defect | Mechanism | Found by | Verified by orchestrator |
| --- | --- | --- | --- | --- |
| 1 | `--horizon 100` accepted although `run.horizon` declares `Field(10, ge=1, le=50)` | `InputsLoader.with_overrides` applies overrides via `model_copy(update=...)`, which **does not re-run validators** | PV.1 (golden harness) | ✅ loaded `horizon=10` → override → `run.horizon=100`, ceiling is 50 |
| 2 | In-place assignment accepts values the schema forbids — e.g. `financing.purchase_price = -999.0` succeeds | Models are **not frozen** and `validate_assignment` is **not set**, so attribute assignment is wholly unvalidated | I.2 (trap suite) | ✅ set a **negative purchase price** on a live `FinancingTerms` with no error |
| 3 | `OverflowError` at `irr.py:83` | Downstream consequence of #1 — the 100-year horizon that reaches it is only possible because the `le=50` ceiling does not hold | PV.1 + orchestrator | ✅ reproduced at 3000u/100y and 5000u/100y |

**Assessment: #1 and #2 are more serious than #3.** The overflow is a corner case; #1 and #2 mean the schema's
declared invariants are decorative on the CLI-override and mutation paths — the failure is silent, and it
applies to **every** constrained field those paths touch, not just `horizon`. A tool whose value rests on
its numbers should not accept a negative purchase price.

I.2 also demonstrated the concrete blast radius of #2: an in-place-mutating `_perturb` stand-in corrupts
the **caller's** inputs after one call, and inside the bisection loop compounds until it crashes in
`amortization_schedule` with `ValueError: principal must be >= 0`. This is exactly why I.1 was directed to
use a surgical copy — and why "no caller mutation" is a real invariant here, not a defensive nicety.

**Recommended (Roger's call):** set `model_config = ConfigDict(validate_assignment=True)` on the input
models, and make `with_overrides` re-validate. Both are small; both close whole classes of silent error.
Neither is in the mission charter — flagging rather than doing.

#### Two OverflowError triggers, not one (record correction)

PV.1 reported it could not reproduce the orchestrator's boundary. **Both are real; the fixtures differ.**
* **Orchestrator's trigger (realistic deal):** replicate `units[0]` N times — rate **5.5%**, 5% down, refi
  present. Crashes at **3000u/100y** and **5000u/100y**; 2000u/100y is fine. Re-confirmed after PV.1's report.
* **PV.1's trigger (independent):** **zero** interest rate + thin (5%) down + no refi; boundary ~4,539u at
  100y, shape-dependent.

PV.1's committed crash-pins cover **its own** zero-rate fixture. **The realistic-rate path is the more
concerning one and is NOT yet pinned** — the IRR fix task must cover both.

## Mission close-out deliverable (Roger's request, 2026-08-29)

| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| CO.1 | **Full before/after comparison analysis** — plain-English account of what changed and *what action made it better*, with a comparative table. Covers all three strands: (a) **the feature** — what the report said about a near-miss before vs. after; (b) **performance** — the surgical-copy fix and the loop-invariant hoist, with measured numbers at deal *and* portfolio scale; (c) **quality/correctness** — suite counts, coverage, the guardrail-checks single-source-of-truth extraction, the two-sided rejector fix, the `irr.py` overflow fix. Must attribute each gain to the specific action that produced it, not just show deltas | orchestrator (inline) → n/a | TODO — produce at mission end, after all waves land |

**Content already banked for CO.1** (measured, not to be re-derived):
* Pre-mission baseline `main @ bfdf565`: 684 tests, coverage 87.20%, report sha `545e22b2…`, demo verdict DECLINE.
* Post-I.1: 712 tests (+28), coverage 87.68%, byte-identity held.
* Engine hot-path profile at 5000u/50y: `engine.py:155` genexpr = **62%** of engine time (5,001,000 calls), `sum` around it another **33%** → ~95% in one loop-invariant expression.
* Surgical copy vs `deepcopy`: **2.17×** (1000u/30y) · **2.33×** (5000u/30y) · **1.83×** (5000u/50y), bit-identical.
* Loop-invariant hoist (measured in isolation): **27×** (1000u/30y) · **51×** (5000u/50y) · **98×** (5000u/100y), identical results — speedup *grows* with horizon.
* Full-recourse wall time before any fix: 1.28 s (1000u/10y) → 11.37 s (5000u/50y) → crash (5000u/100y).
* `irr.py:83` OverflowError boundary: ≥3000 units AND 100y; 2000u/100y ok, 500u ok at every horizon.

## Wave Validation

| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| V.1 | Full battery in `airedeal`: `pytest` green + coverage ≥80%; `ruff format --check` + `ruff check` clean; `mypy .` clean; **no `src/core/finance/` diff** (git-verified); **no non-additive `src/schemas/models.py` change** (git-verified); default `python main.py` byte-identical to the pinned pre-mission sha for a no-near-miss deal. Every command in the manual-testing doc actually runs and produces the stated result | orchestrator (inline) → n/a | TODO |

## Gate V — post-implementation (blocking)

| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| GV.1 | Code review of the full diff: confirm zero `src/core/finance/` lines changed; confirm **no guardrail formula is algebraically inverted** anywhere (the search re-runs the engine); confirm schema additivity; confirm determinism | staff-code-reviewer → sonnet | TODO |
| GV.2 | Guardian overclaim re-check against the shipped copy (VETO): every user-facing lever line, the flag-don't-remove reasons, the honest-null message | principal-principles-guardian → sonnet | TODO |

### Gate V decision record — _stub, fill at gate_

· Date: ____ · Code review (GV.1): ____ (finance-core diff: none? formula inversion: none? schema
additive? determinism?) · Guardian (GV.2): ☐ VETO / ☐ NO VETO (conditions) · Orchestrator sign-off: ____

## Mission gate (Roger)

| ID | Task | Status |
| --- | --- | --- |
| MG | Roger runs `docs/manual testing/MISSION_4_MANUAL_TESTING.md` by hand and flips every box; document-level box must read VALIDATED. Roger holds this gate; the orchestrator never self-approves | TODO |

### Mission gate decision record — _stub, fill at gate_

· Date: ____ · Manual-testing doc document-level box: ☐ VALIDATED / ☐ VALIDATED WITH ISSUES /
☐ NOT VALIDATED · Blocking issues: ____ · Roger's decision: ____

## Wave Integrate

| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| INT.1 | After Validation GREEN **and** Roger's mission gate: `git fetch`; rebase/merge onto latest `main`; re-run the **full** battery post-rebase (a pre-rebase green does not count); `git switch main && git merge --no-ff mission/4-actionable-recourse`; reconcile any origin delta; **push only at Roger's instruction** (never force-push). Record the merge sha + push result here, and update §2 of the roadmap tracker | orchestrator (inline) → n/a | TODO |

### Integrate record — _stub, fill at integrate_

· Merge sha: ____ · Push result: ____ · Battery post-rebase: ____ · Roadmap §2 updated: ☐
