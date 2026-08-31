# Mission 5 Sprint Tracker — Adjoint Differentiation & Optimized Recourse Search

_Live tracker. The executing orchestrator keeps this current — full updates only (counts + wave
summary + rows), never partial. Date every gate decision. Carry the tests-tree SHA on every count
(Mission 2's hardest-won lesson: a number typed into a doc is a claim with no test behind it — pin it
to a commit)._

**Charter:** `docs/plans/MISSION_5_adjoint_differentiation.md` · **Handoff:** `docs/plans/MISSION_5_HANDOFF.md`
**Manual tests:** `docs/manual testing/MISSION_5_MANUAL_TESTING.md`
**Baseline:** `main @ 7cfd449` (Mission 4 merged, validated by Roger 2026-08-31, 9/9) · **Branch:** `mission/5-adjoint-differentiation`

> **Status at charter time (2026-08-31): CHARTERED, NOT YET STARTED.** Mission 4 is merged to `main`
> as `7cfd449`; `main` is clean and in sync with `origin/main`. The sequencing pre-condition is
> satisfied. Wave Sync re-establishes the baseline and re-confirms every charter `path:line` before any
> work.

> Every subagent prompt issued in this mission MUST carry the GRAPHIFY CONTRACT verbatim (see the
> handoff). Any reachability/blast claim citing the graph is confirmed against the file at the graph's
> own `built_at_commit`, never the current tree (Mission 2's trust-boundary incident).

> **HARD SEQUENCING (two boundaries):** (1) the tolerance rule (T-sub-wave) ships and goes green, and
> the guardian VETO on its design is lifted, **before any AD code is written** (AD-sub-wave). (2) The
> **INTERNAL AD go/no-go checkpoint** (ADC.1) must record GO **before any Phase B optimizer code is
> written**; on NO-GO, Half B defers and the mission ships Half A alone. Both are wave boundaries, not
> preferences.

> **Scope (2026-08-31, EXPANDED by Roger):** this mission now runs TWO halves in sequence. **Half A** =
> tolerance rule + adjoint differentiation + single-lever recourse acceleration (the original charter).
> **Half B** = the multi-lever recourse optimizer producing a second "top-3 combinations" report
> section (previously recommended as a separate Mission 6; folded in by Roger). Half B is entered ONLY
> if the internal AD checkpoint = GO.

## Cost routing

Invoke `staff-cost-aware-model-router` at kickoff (standing rule §3a.1) to confirm the tiers below
BEFORE the first dispatch batch — not "only when ambiguous." Record the actual dispatch in each row's
"Agent → tier" column, and log any deviation from the confirmed table **at dispatch time**. Tier→model
mapping: **capable = opus · standard = sonnet · cheap = haiku · top reasoning = fable**. **No
`principal-security-engineer`** this mission — there is no external input surface.

### Planner-proposed routing (router confirms at dispatch)

| Task | Agent | Tier |
| --- | --- | --- |
| EV.1 confirm axis grades / gap severity | `app-evaluator` | opus |
| D.1 AD design + IRR/Brent differentiation reasoning (gnarliest math) | `staff-python-engineer` (top reasoning) | **fable** |
| D.2 current perf baseline (reconcile 73 ms claim) + target/projection | `principal-performance-engineer` | opus |
| D.3 tolerance-rule design (1e-9, anchor-to-origin, approaching-tolerance, ~9.4e-8 calibration) | `staff-python-engineer` | sonnet |
| GD.1 **VETO** on the invariant relaxation (tolerance design as values change) | `principal-principles-guardian` | opus |
| PD.1 product calls (ratify 1e-9; `GENUINELY_CLOSE_MAX_FAILS`; horizon-100 / money-field / CLI dispositions) | `principal-founder-proxy` | opus |
| PF.1 perf **go/no-go** on the AD portion | `principal-performance-engineer` | opus |
| IT.1 tolerance harness + anchor-to-origin + approaching-tolerance state | `staff-python-engineer` | sonnet |
| IT.2 tolerance RED suite (incl. ~9.4e-8 calibration) | `staff-qa-test-engineer` | sonnet |
| IA.1 AD machinery + 7×4 Jacobian API + Newton-on-guardrail single-lever + confirm-by-rerun + fallback | `staff-python-engineer` (fable math support) | sonnet (+ fable) |
| IA.2 AD-vs-rerun agreement + probe-count + determinism + fallback RED suite | `staff-qa-test-engineer` | sonnet |
| IA.3 perf benchmark extension (probe-count + before→after vs 30 ms) | `principal-performance-engineer` | opus |
| D.4 Half B design (optimizer method selection + rejector-unification + top-3 selection) | `staff-python-engineer` (top reasoning) | **fable** |
| PD.2 Half B product calls (combination-plausibility rule; top-3 selection policy) | `principal-founder-proxy` | opus |
| IB.1 constrained optimizer (Lagrangian/KKT) + deterministic multi-start + unified all-four-lever plausibility gate + confirm-by-rerun | `staff-python-engineer` | **fable** |
| IB.2 two-section report output (single-lever menu + top-3 combinations; flag-don't-remove; honest-null) | `staff-report-experience-designer` | sonnet |
| IB.3 optimizer RED suite (multi-start determinism; feasibility gate incl. jointly-implausible; diversity; parsimony; local-minima; every-combination-confirmed-by-rerun) | `staff-qa-test-engineer` | sonnet |
| I.4 docs Half A (README / finance & market READMEs / CHANGELOG) — reasoning, verify vs real symbols | `staff-documentation-maintainer` | **sonnet (STANDARD, not haiku)** |
| I.5 docs Half B (two-section output + unified gate in market/reports READMEs + CHANGELOG) — verify vs real symbols | `staff-documentation-maintainer` | **sonnet (STANDARD, not haiku)** |
| OI.1 money-field lower-bound pass + RED test | `staff-python-engineer` | sonnet |
| OI.2 horizon 50→100 raise + RED test | `staff-python-engineer` | sonnet |
| OI.3 CLI out-of-range-horizon clean message + RED test | `staff-python-engineer` | sonnet |
| GV.1 code review of full diff | `staff-code-reviewer` | sonnet |
| GV.2 guardian invariant-relaxation re-check (VETO) | `principal-principles-guardian` | opus |

Deviations from this table are logged at dispatch time in the row itself.

### Router confirmation — _PENDING (record here at kickoff)_

## Status legend

`TODO` · `IN-PROGRESS` · `BLOCKED` (needs a prior gate or a product call) · `REVIEW` (agent says done,
orchestrator verifying) · `DONE` (verified inline) · `DEFERRED`

## Overall progress

- Mission status: **CHARTERED (scope EXPANDED by Roger 2026-08-31 to Half A + Half B), NOT YET
  STARTED.** Baseline `main @ 7cfd449`, clean, in sync with origin. First action = Wave Sync, then Wave
  Branch.
- Tasks: **0 / 25 DONE** · 0 IN-PROGRESS · 25 TODO. _(18 Half A + the internal AD checkpoint ADC.1 + 6
  Half B tasks D.4, PD.2, IB.1, IB.2, IB.3, I.5 — the Impl Phase B tasks are BLOCKED until ADC.1 = GO.)_
- **Suite baseline — to be PINNED at Wave Sync** (measured in `airedeal`): pytest count, coverage,
  tests-tree SHA, and the pre-mission `python main.py` report sha256. _(charter-time reference only,
  re-measure at Sync: Mission 4's committed 5,000u/100y benchmark reads best 181–197 ms / median up to
  ~213 ms against `BUDGET_MS = 250.0`.)_

## Wave summary

| Wave | Status | Tasks | Notes |
| --- | --- | --- | --- |
| Sync | TODO | — | Re-confirm `main @ 7cfd449` canonical + clean; STOP if a later mission is mid-flight; re-verify anchors; pin baseline battery. |
| Branch | TODO | — | `git switch main && git switch -c mission/5-adjoint-differentiation`. |
| Discovery | TODO | EV.1, D.1, D.2, D.3, D.4 | AD forward-vs-reverse MEASURED; IRR/Brent differentiation; tolerance design; perf baseline (reconcile 73 ms); **Half B design** (optimizer method + rejector-unification + top-3). No production code. |
| Gate D | TODO | GD.1, PD.1, PF.1, PD.2 | **Guardian VETO on the invariant relaxation** (mandatory) + founder product calls (incl. **Half B: combination-plausibility rule + top-3 policy**) + perf **go/no-go** on the AD portion. |
| Impl Phase A — Tolerance (FIRST) | BLOCKED (on Gate D VETO lift) | IT.1, IT.2, I.4, OI.* | Tolerance rule shipped + green before any AD code. |
| Impl Phase A — AD (single-lever) | BLOCKED (on Impl-T green + VETO lifted + PF.1 go) | IA.1, IA.2, IA.3 | Only if Gate D says GO. If NO-GO, mission ships the tolerance rule alone. |
| **Internal AD go/no-go checkpoint** | BLOCKED (on Impl Phase A AD green) | ADC.1 | **Hard gate.** AD proven (single-lever matches bisection within tolerance; IRR/Brent sound; 7×4 Jacobian API stable) BEFORE any optimizer code. GO → Phase B; NO-GO → Half B defers, Half A ships alone. |
| Impl Phase B — multi-lever optimizer | BLOCKED (on ADC.1 = GO) | IB.1, IB.2, IB.3, I.5 | Lagrangian/KKT + multi-start + unified all-four-lever gate + two-section report + optimizer RED suite + Half B docs. Every combination confirmed by a real re-run. |
| Validation | TODO | — | Full battery; BOTH ruff commands; within-tolerance golden; perf recorded vs 30 ms; every manual-test command runs (incl. Half B cases). |
| Gate V | TODO | GV.1, GV.2 | Code review (every answer AND combination rerun-confirmed; unified gate all-four-lever; multi-start deterministic; no decomposed basis surfaced) + guardian re-check (VETO). |
| Mission gate | TODO | — | Roger validates the manual-testing doc by hand; document-level box → VALIDATED. |
| Integrate | TODO | — | Rebase, re-run full battery, `merge --no-ff`, push at Roger's instruction. Record merge sha. |

## Wave: Discovery

| ID | Task | Agent → tier | Status | Notes |
| --- | --- | --- | --- | --- |
| EV.1 | Confirm axis grades / gap severity justify the mission | `app-evaluator` → opus | TODO | |
| D.1 | AD design (forward-vs-reverse MEASURED, 4-in/≤7-out) + IRR/Brent differentiation (IFT vs converged root) | `staff-python-engineer` → fable | TODO | Gnarliest math; dual-number 4-pass is the hypothesis to beat, not a foregone conclusion. |
| D.2 | Current perf baseline (reconcile the 73 ms claim vs committed 181–213 ms) + target/projection | `principal-performance-engineer` → opus | TODO | |
| D.3 | Tolerance-rule design (1e-9, anchor-to-origin, approaching-tolerance state, ~9.4e-8 calibration) | `staff-python-engineer` → sonnet | TODO | Artifact the guardian VETO reviews. |
| D.4 | **Half B design**: (g) constrained-optimization method selection (Lagrangian/KKT variant, by measurement) + deterministic multi-start; (h) **rejector-unification** — one joint all-four-lever plausibility gate (core new engineering); (i) normalization-free top-3 selection (parsimony · within-axis magnitude · diversity) | `staff-python-engineer` → fable | TODO | Grounded: `_judge_plausibility` (`recourse.py:609`) judges one lever at a time today; rent/opex have no rejector axis. No production code. |

## Wave: Gate D (decision records)

| ID | Task | Agent → tier | Status | Decision record |
| --- | --- | --- | --- | --- |
| GD.1 | **VETO** — tolerance rule as values-level relaxation of the deterministic-core invariant | `principal-principles-guardian` → opus | TODO | _Record VETO lift/hold + date. No AD code until lifted._ |
| PD.1 | Product calls: ratify 1e-9; `GENUINELY_CLOSE_MAX_FAILS`; horizon-100 / money-field / CLI dispositions | `principal-founder-proxy` → opus | TODO | _Record each decision + date._ |
| PD.2 | **Half B product calls**: what makes a four-lever COMBINATION plausible (the unified gate's rule); top-3 selection policy (parsimony / within-axis magnitude / diversity weighting) | `principal-founder-proxy` → opus | TODO | _Record each decision + date. Gates the Impl Phase B design._ |
| PF.1 | Perf **go/no-go** on the AD portion (win vs finance-core blast) | `principal-performance-engineer` → opus | TODO | _Record GO / NO-GO + measured basis + date._ |

## Wave: Implementation Phase A — Tolerance (FIRST)

| ID | Task | Agent → tier | Status | Notes |
| --- | --- | --- | --- | --- |
| IT.1 | Tolerance harness + anchor-to-origin + approaching-tolerance state | `staff-python-engineer` → sonnet | BLOCKED | Needs GD.1 VETO lifted. |
| IT.2 | Tolerance RED suite (catches ~9.4e-8; passes legit 1e-9 drift; anchors to origin) | `staff-qa-test-engineer` → sonnet | BLOCKED | |
| OI.1 | Money-field lower-bound pass + RED test (negative price rejected cleanly) | `staff-python-engineer` → sonnet | BLOCKED | Founder-confirmed field list (PD.1). |
| OI.2 | Horizon `le=50`→`le=100` + RED test (100 accepted, 101 rejected) | `staff-python-engineer` → sonnet | BLOCKED | Founder-ratified (PD.1). |
| OI.3 | CLI out-of-range-horizon clean message + RED test (no traceback) | `staff-python-engineer` → sonnet | BLOCKED | |

## Wave: Implementation Phase A — AD single-lever (only if Gate D = GO)

| ID | Task | Agent → tier | Status | Notes |
| --- | --- | --- | --- | --- |
| IA.1 | AD machinery + **7×4 Jacobian API** + Newton-on-guardrail single-lever search + confirm-by-rerun + fallback | `staff-python-engineer` → sonnet (+ fable) | BLOCKED | On IT green + VETO lifted + PF.1 GO. The Jacobian API is the seam Half B consumes. |
| IA.2 | AD-vs-rerun agreement + probe-count + determinism + fallback RED suite | `staff-qa-test-engineer` → sonnet | BLOCKED | |
| IA.3 | Perf benchmark extension (probe-count + before→after vs 30 ms) | `principal-performance-engineer` → opus | BLOCKED | |

## Gate: Internal AD go/no-go checkpoint (HARD boundary; decision record)

| ID | Task | Agent → tier | Status | Decision record |
| --- | --- | --- | --- | --- |
| ADC.1 | **Validate the AD foundation BEFORE any optimizer code**: single-lever AD matches bisection within tolerance; IRR/Brent differentiation sound; 7×4 Jacobian API stable | orchestrator (verify inline) + `staff-python-engineer` → fable | BLOCKED | _Record **GO / NO-GO** + measured basis + date. GO → Impl Phase B. NO-GO → Half B DEFERS, mission ships Half A alone (record explicitly). A wrong top-3 must be an optimizer bug, not an AD bug._ |

## Wave: Implementation Phase B — multi-lever optimizer (only if ADC.1 = GO)

| ID | Task | Agent → tier | Status | Notes |
| --- | --- | --- | --- | --- |
| IB.1 | Constrained optimizer (Lagrangian/KKT, method from D.4) + deterministic multi-start + **unified all-four-lever combination-plausibility gate** + every-combination-confirmed-by-a-real-rerun | `staff-python-engineer` → fable | BLOCKED | On ADC.1 = GO + PD.2 decisions. The gnarly constrained-optimization math. |
| IB.2 | Two-section report output (single-lever menu + top-3 combinations; flag-don't-remove; honest-null) | `staff-report-experience-designer` → sonnet | BLOCKED | Both sections ship (Roger: offer both). |
| IB.3 | Optimizer RED suite (multi-start determinism; feasibility gate incl. jointly-implausible-but-individually-fine; diversity; parsimony; local-minima; every-combination-confirmed-by-rerun) | `staff-qa-test-engineer` → sonnet | BLOCKED | |

## Wave: Docs

| ID | Task | Agent → tier | Status | Notes |
| --- | --- | --- | --- | --- |
| I.4 | Docs Half A (README / finance & market READMEs / CHANGELOG) — verify vs real symbols | `staff-documentation-maintainer` → sonnet (STANDARD) | TODO | Reasoning task; NOT haiku (Mission 4 fabricated-docs lesson). |
| I.5 | Docs Half B (two-section output + unified gate in market/reports READMEs + CHANGELOG) — verify vs real symbols | `staff-documentation-maintainer` → sonnet (STANDARD) | BLOCKED | On Impl Phase B landing. NOT haiku. |

## Wave: Gate V (decision records)

| ID | Task | Agent → tier | Status | Decision record |
| --- | --- | --- | --- | --- |
| GV.1 | Code review (every answer AND every combination rerun-confirmed; no hand-inverted formula; anchor-to-origin; unified gate all-four-lever; multi-start deterministic; no decomposed basis surfaced; finance-core justified) | `staff-code-reviewer` → sonnet | TODO | |
| GV.2 | Guardian invariant-relaxation re-check (VETO) | `principal-principles-guardian` → opus | TODO | |

## Mission gate (Roger)

| Item | Status |
| --- | --- |
| Manual-testing doc fully VALIDATED by Roger (document-level box) | TODO |
| Merge `--no-ff` to `main` | TODO |
| Push at Roger's instruction (reconcile origin delta; never force-push) | TODO |
| Merge sha recorded | TODO |
