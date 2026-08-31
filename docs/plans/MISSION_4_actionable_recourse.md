# Mission 4 — Actionable Recourse ("What would have to change?")

_Charter. Owned by the mission-planner; the executing orchestrator keeps the sprint tracker current,
not this file. `path:line` anchors below were verified against the tree at the commit named in
§Baseline; re-read any you touch before changing it._

---

## Executive Summary

The verdict engine answers a yes/no question — BUY / CONDITIONAL / DECLINE — and answers it well.
What it cannot say is **how close a near-miss is** or **what would move it across the line**. A deal
that misses debt coverage by 0.01 gets the same "weak DSCR" stamp as one that misses by 0.5, and the
gap is stated in *our* units ("DSCR is weak at 1.19 (< 1.20)"), which no investor negotiates in.

This mission keeps the verdict exactly as it is and **attaches to a near-miss a recourse analysis**:
how far from the line the deal sits, and what single change would close the gap — expressed in levers
an investor can actually move (rent per unit, purchase price, interest rate, annual operating costs).
One gap, **several currencies**; the investor picks the lever they have leverage on. This is the
established field of **actionable recourse / counterfactual explanations** (its canonical example is
loan denial: "if income rose to $50,000 the application would be approved") applied to real-estate
underwriting.

**The load-bearing engineering discipline: re-run the engine, never invert a guardrail formula.** The
levers are *not* independent — cutting the purchase price shrinks the loan, improves the cap rate, and
changes cash-in all at once; raising rent moves NOI, cap rate, coverage and cash-on-cash together.
Algebraically inverting one guardrail in isolation gives wrong, optimistically-biased numbers. The
build must find each lever's flip point by **re-running `run_financial_model` with a single input
changed** — the exact pattern `build_baseline_outlook` (`src/orchestrators/crew.py:65`) and
`run_scenarios` (`src/market/scenario_runner.py:126`) already use — then testing the perturbed
scenario for plausibility with the existing rejector (`reject_unrealistic`, `src/market/rejector.py:54`).

**Blast is low and additive.** The deterministic finance core (`src/core/finance/`) is called as a
black box, once per perturbed input, and is **never edited**. The verdict stays in `synthesize_thesis`
(`src/agents/chief_strategist.py:137`) — a model may never author it, and this mission adds no model.
Schema changes are **additive only**: new `RecourseLever` / `RecourseAnalysis` models alongside the
existing `ScenarioAnalysis` pattern (`src/schemas/models.py:1277`), nothing renamed or removed. The
report gains one new section, appended exactly like Mission 1's "Market Scenarios" overlay
(`src/core/reports/generator.py:1246`).

**Technically independent of Mission 3.** This feature operates on `FinancialInputs` /
`FinancialForecast` / `InvestmentThesis` and never touches CV, vision, ONNX, or media. It is sequenced
*after* Mission 3 only because of the solo-dev one-mission-at-a-time cap, not because of any code
dependency.

---

## Baseline

`base = main @ <TBD at Wave Sync>, synced <TBD>.`

**Sequencing (hard pre-condition, not a preference):** Mission 4 branches off freshly-synced `main`
**only after Mission 3 clears its founder gate and merges to `main`.** At charter time (2026-08-28)
Mission 3 (`mission/3-byo-onnx-provider`) is built and through Gate V but has **not** cleared Roger's
mission gate or merged. The solo-dev one-mission-at-a-time cap forbids opening Mission 4 before then.
Wave Sync re-establishes the true baseline against whatever `main` reads once Mission 3 has landed;
every `path:line` in this charter must be re-confirmed at that commit.

- **Known state at charter time (2026-08-28):** `main @ 6d9c000` ("docs(mission-2): record Roger's
  manual validation pass — 28/28 PASS, VALIDATED"); Mission 3's work is uncommitted on branch
  `mission/3-byo-onnx-provider`. `main` was 1 commit ahead of `origin/main` at Mission 3's Wave Sync
  (the unpushed Mission 2 validation record `6d9c000`); Roger controls that push. Wave Sync must
  re-check the origin delta and surface it.
- **Anchors verified against the tree at `6d9c000`** (re-verify at the real baseline once M3 lands):
  `synthesize_thesis` `src/agents/chief_strategist.py:137` (guardrails evaluated `:172-179`, verdict
  fail-count `:227-252`); `build_baseline_outlook` `src/orchestrators/crew.py:65` (re-runs the engine
  with observations suppressed, returns `None` when nothing fired); `run_scenarios`
  `src/market/scenario_runner.py:126` (step (d): "perturb a deep copy, re-run the engine"); `reject_unrealistic`
  `src/market/rejector.py:54` (hard rejections + soft prior penalty + renormalize); `ScenarioAnalysis`
  `src/schemas/models.py:1277` (frozen `ConfigDict(frozen=True, extra="ignore")` — the shape to mirror);
  `InvestmentThesis` `src/schemas/models.py:282` (`verdict`/`rationale`/`levers`; today `levers` is a
  free-text `list[str]`); report append pattern `src/core/reports/generator.py:1246` ("Market
  Scenarios" overlay, appended only when supplied; `write_report` `:1520`).
- Verified env: `airedeal` conda env at `/home/rtokime/anaconda3` (NOT `~/miniconda3`).
- The graphify graph is a lead only; confirm against the file at its own `built_at_commit`.

**Precise note on the guardrail count.** Roger's design names five independent boolean checks (DSCR,
cap-rate spread, IRR, Year-1 CoC, cap-rate floor). The code confirms these five are **always active**,
plus **two conditional** cash-flow checks (`cf_y1_ok`, `cf_all_ok`) gated by `REQUIRE_POSITIVE_CF_Y1`
/ `REQUIRE_POSITIVE_CF_ALL` (`chief_strategist.py:177-178`). The verdict is a **fail-count over up to
seven guardrails** — BUY at zero fails, DECLINE at ≥3 fails or (cap-floor breach **and** DSCR fail),
else CONDITIONAL (`chief_strategist.py:227-252`). Discovery must map every lever to the guardrail(s)
it can move against the live seven, not the five in the summary.

---

## Branch

`mission/4-actionable-recourse` — cut off freshly-synced `main` in Wave Branch, **after** Mission 3
has merged. All mission work commits here; nothing lands on `main` until Roger's mission gate, then
Wave Integrate merges `--no-ff`.

---

## In scope

1. **A recourse analysis for a near-miss verdict.** For a CONDITIONAL (and, where honest, a DECLINE
   that is genuinely close), compute how far the deal sits from each failing guardrail and what single
   change to an investor-movable lever would close it. Levers: **rent per unit per month**, **purchase
   price**, **interest rate**, **annual operating costs**. One gap, several currencies.
2. **Every lever answer comes from re-running the engine, not inverting a formula.** For each lever,
   perturb a single input on a deep copy of `FinancialInputs`, re-run `run_financial_model`, and read
   the resulting `InvestmentThesis` / metrics — exactly as `run_scenarios` step (d) and
   `build_baseline_outlook` already do. Bounded search (e.g. bisection) finds the minimum change that
   flips the failing guardrail(s). **No guardrail formula is ever algebraically inverted.**
3. **Plausibility via the existing rejector.** Each proposed lever change is tested for realism using
   the machinery Mission 1 shipped (`reject_unrealistic` / the snapshot bounds), and levers that fall
   outside realistic ranges are **flagged, never removed** (Roger's decision 1), with a stated reason.
4. **Multi-guardrail ordering.** When several guardrails fail at once, lead with the **cheapest single
   fix** but **flag that other gaps remain** (Roger's decision 2), so a partial fix is never mistaken
   for a complete one.
5. **The honest-null case.** When nothing realistic closes the gap, **say so plainly** (Roger's
   decision 3) — no invented lever, no false hope.
6. **Additive schema.** New `RecourseLever` / `RecourseAnalysis` models in `src/schemas/models.py`,
   shaped like `ScenarioAnalysis` (frozen, `extra="ignore"`), carrying: the verdict context, the
   distance-to-line per failing guardrail, the levers (each with native-unit magnitude, several
   human-facing currencies, plausibility flag + reason, and which guardrail(s) it closes), the
   multi-failure ordering, and the honest-null flag. Nothing renamed, retyped, or removed.
7. **A new report section.** Append a "What would have to change?" section to the report, following the
   Mission 1 "Market Scenarios" append pattern (`generator.py:1246`) — rendered only for a near-miss,
   absent (byte-identical to today) otherwise. Copy is designed by
   `staff-report-experience-designer` and cleared by the guardian.
8. **Honesty as a values commitment, not just copy.** Levers say "**WOULD** close it, holding the other
   levers fixed" — never "WILL". Flag-implausible-never-remove. Lead-cheapest-flag-the-rest. Say-so
   plainly when nothing works. `principal-principles-guardian` holds an overclaim VETO at Gate D and
   re-checks at Gate V.
9. **Tests.** Every shipped behaviour ships a RED-on-regression test (revert the fix → the test fails).
   **The suite MUST include the non-independence trap case** (see Binding Constraints) — a case that
   only passes because the answer came from re-running the engine, and would fail against an
   algebraically-inverted answer. Also: rejector integration (implausible lever flagged not removed),
   multi-guardrail cheapest-first ordering, the honest-null case, and determinism (same inputs ⇒
   byte-identical `RecourseAnalysis`).
10. **Docs.** README / `src/core/README.md` (or the owning subarea README) / CHANGELOG `[Unreleased]`
    updated to describe the new section honestly; close backlog #6 in the ledger's §4 (see the ledger-
    updates section at the end of this charter).

## Out of scope (explicitly)

- **Any `src/core/finance/` internals edit.** Zero finance-core diff. The engine is a black box called
  once per perturbed input; the verdict stays in `synthesize_thesis`. If a lever seems to need a core
  change, stop — the approach drifted toward formula inversion.
- **Any non-additive `src/schemas/models.py` change.** New models only; nothing renamed, retyped, or
  removed. `InvestmentThesis.levers` (the existing free-text list) is **not** repurposed or changed —
  the structured recourse rides in the new models beside it.
- **Threshold / policy changes.** Mission 2's deferred Year-1 CoC floor and DECLINE-shortcut decisions
  (3.1c) are **not** touched here. This feature makes those decisions *revisitable after it ships*
  (a near-miss becomes legible rather than fatal-looking) — but revisiting them is a **later mission**,
  explicitly not this one.
- **Live market data.** No comps, no cap-rate drift feeds, no network. Plausibility uses the existing
  in-repo rejector/snapshot machinery only.
- **Any UI.** No Streamlit, no interactive surface. The output is the Markdown report section.
- **A model / AI path of any kind.** Recourse is deterministic arithmetic via the engine. No LLM, no
  vision, no ONNX. (This is what makes it independent of Mission 3.)
- **Vectorised / numpy-optimised search**, unless the perf call (Gate D) proves the naive
  re-run-per-perturbation is too slow at report time. Default: measure first, optimise only if needed
  (Roger's performance note, "not needed for a first version").

---

## Waves & gates

`Wave Sync → Wave Branch → Wave Discovery → Gate D (pre-impl: guardian honesty VETO + bounded founder
product call + perf sanity call) → Wave Implementation → Wave Validation → Gate V (code review +
guardian overclaim re-check) → Mission gate (Roger) → Wave Integrate.`

> **No `principal-security-engineer` gate this mission.** Unlike Mission 3, there is **no external
> input surface** — no user-supplied file paths, no network, no untrusted deserialization. Recourse
> operates entirely on already-validated `FinancialInputs`. A security review would be ceremony.

| Wave | What happens |
| --- | --- |
| **Sync** | Phase 0 re-sync **after Mission 3 has merged to `main`**: `git fetch`; confirm `main` fast-forwards to canonical latest; re-confirm/surface any origin delta to Roger (do **not** push). Re-confirm every charter `path:line` at the real baseline. Re-run the full gate battery green in `airedeal`; pin the suite count + tests-tree SHA. |
| **Branch** | `git switch main && git switch -c mission/4-actionable-recourse`. |
| **Discovery** | `staff-python-engineer` produces a short spec: the lever set and each lever→guardrail mapping against the live seven guardrails; the bounded-search strategy (bisection bounds, convergence tolerance, monotonicity assumptions and how they're checked, what "flip" means per guardrail); the rejector integration point and how plausibility is judged per lever; the multi-failure ordering rule ("cheapest single fix"); the honest-null definition; the additive `RecourseLever`/`RecourseAnalysis` shape; and the non-independence trap test design. **No production code.** `app-evaluator` confirms the current axis grades / gap severity that justify this mission; `principal-founder-proxy` and `principal-performance-engineer` feed in (see Gate D). |
| **Gate D (pre-impl)** | `principal-principles-guardian` reviews the honesty framing of the spec (WOULD-not-WILL, flag-don't-remove, cheapest-first-flag-the-rest, honest-null) and holds a **VETO**. `principal-founder-proxy` makes the bounded product call: lever wording, the default set of "currencies" per gap, and the flag-don't-remove copy. `principal-performance-engineer` makes the explicit call: is naive re-run-per-perturbation fast enough at report time, or must the first version vectorise? All blocking for their scope. |
| **Implementation** | ≤3 concurrent: (a) `staff-python-engineer` builds the recourse orchestration module (engine re-run search + rejector integration) and the additive schema; (b) `staff-qa-test-engineer` writes the RED-on-regression suite incl. the non-independence trap case, rejector integration, multi-failure ordering, honest-null, determinism; (c) `staff-report-experience-designer` designs the report section + copy (several-currencies block, flag-don't-remove, honest-null). |
| **Validation** | Full battery in `airedeal`: `pytest` green + coverage ≥80%; `ruff format --check` + `ruff check` clean; `mypy .` clean; default `python main.py` byte-identical to pre-mission for any deal with no near-miss recourse section. Every command in the manual-testing doc actually runs and produces the stated result. |
| **Gate V** | `staff-code-reviewer` reviews the diff (esp. that no `src/core/finance/` line changed and no guardrail formula was inverted); `principal-principles-guardian` re-checks overclaim (VETO). |
| **Mission gate (Roger)** | Roger runs `docs/manual testing/MISSION_4_MANUAL_TESTING.md` by hand and flips the boxes. Not clear until the document-level box reads VALIDATED. Roger holds this gate; the orchestrator never self-approves. |
| **Integrate** | Only after Validation GREEN **and** Roger's mission gate: `git fetch`; rebase/merge onto latest `main`; re-run the **full** battery post-rebase (a pre-rebase green does not count); `git switch main && git merge --no-ff mission/4-actionable-recourse`; **push only at Roger's instruction** (reconcile any origin delta — never force-push). Record the merge sha + push result in the tracker. |

---

## Definition of Done

- [ ] A near-miss verdict (CONDITIONAL, and DECLINE where genuinely close) produces a `RecourseAnalysis`
      stating the distance to each failing guardrail and one single-lever change per lever that would
      close it, in several investor-facing currencies.
- [ ] **Every lever answer is produced by re-running `run_financial_model` on a single perturbed
      input** — demonstrated in code and tests — and **no guardrail formula is algebraically inverted.**
- [ ] **The RED-on-regression suite includes the non-independence trap case**: a scenario where the
      naive inverted-formula answer differs measurably from the true re-run answer, and the test passes
      only for the re-run answer. Reverting to a formula-inversion implementation turns it RED.
- [ ] Implausible levers are **flagged with a reason, never removed** (decision 1); when several
      guardrails fail, the output **leads with the cheapest single fix and flags that other gaps remain**
      (decision 2); when nothing realistic closes the gap, the output **says so plainly** (decision 3).
- [ ] Every user-facing lever line says "**WOULD** close it, holding the other levers fixed" — never
      "WILL". Guardian overclaim VETO lifted.
- [ ] The report gains a "What would have to change?" section (appended like the Market Scenarios
      overlay), rendered only for a near-miss; with no near-miss, report output is **byte-identical** to
      pre-mission.
- [ ] New `RecourseLever` / `RecourseAnalysis` models are **additive** — nothing in `src/schemas/models.py`
      renamed, retyped, or removed; `InvestmentThesis.levers` unchanged.
- [ ] **No** `src/core/finance/` diff. The verdict is still authored solely by `synthesize_thesis`.
- [ ] Determinism: same inputs ⇒ byte-identical `RecourseAnalysis` and report section.
- [ ] Every shipped behaviour has a RED-on-regression test, demonstrated (revert → RED → restore →
      GREEN).
- [ ] `pytest` green, coverage ≥80%; `ruff format --check` + `ruff check` clean; `mypy .` clean.
- [ ] `principal-principles-guardian` lifted its overclaim VETO; `principal-founder-proxy` made the
      bounded product call; `principal-performance-engineer` made the explicit measure-vs-vectorise call.
- [ ] README / owning-subarea README / CHANGELOG `[Unreleased]` describe the section honestly; backlog
      #6 recorded as delivered in the ledger (see ledger-updates section).
- [ ] **NON-NEGOTIABLE:** The manual tests in `docs/manual testing/MISSION_4_MANUAL_TESTING.md` have
      been conducted and validated by Roger — **every** test case marked VALIDATED in its status box, and
      the document-level box reading VALIDATED. **This is a precondition of the founder gate; the mission
      gate cannot be requested until this line is satisfiable.**

---

## Agent roster (task → agent → model tier; ≤3 concurrent per wave)

> `staff-cost-aware-model-router` **must be invoked at dispatch time** (standing rule §3a.1) to confirm
> the tier assignments below before the first batch. Record `task → agent → tier` and any deviation at
> dispatch time, not in a post-mortem. Tier→model mapping used by prior missions: capable=opus ·
> standard=sonnet · cheap=haiku. **No `principal-security-engineer`** — no external input surface.

| Wave | Task | Agent | Tier |
| --- | --- | --- | --- |
| Discovery | Confirm axis grades / gap severity that justify the mission | `app-evaluator` | opus |
| Discovery | Recourse spec: lever set, guardrail↔lever mapping, bounded-search strategy, rejector integration, non-independence trap test design | `staff-python-engineer` | sonnet |
| Gate D | Strategic + bounded product call (lever wording, default currencies, flag-don't-remove copy) | `principal-founder-proxy` | opus |
| Gate D | Perf sanity — is naive re-run-per-perturbation fast enough at report time, or make the measure-before-vectorising call explicit | `principal-performance-engineer` | haiku |
| Gate D | Honesty VETO on the spec framing (WOULD-not-WILL, flag-don't-remove, cheapest-first, honest-null) | `principal-principles-guardian` | sonnet |
| Impl | Recourse orchestration module (engine re-run search + rejector integration) + additive schema | `staff-python-engineer` | sonnet |
| Impl (parallel) | RED suite incl. the non-independence trap case, rejector integration, multi-failure ordering, honest-null, determinism | `staff-qa-test-engineer` | sonnet |
| Impl (parallel) | Report section design + copy (several-currencies block, flag-don't-remove, honest-null) | `staff-report-experience-designer` | sonnet |
| Impl / Docs | Docs (README / owning README / CHANGELOG; backlog #6 closure note) | `staff-documentation-maintainer` | haiku |
| Gate V | Code review of the full diff (no finance-core diff; no formula inversion) | `staff-code-reviewer` | sonnet |
| Gate V | Overclaim re-check (VETO) | `principal-principles-guardian` | sonnet |

Roger holds the mission gate (merge + push). No agent self-approves it.

---

## Binding constraints (non-negotiable)

1. **Deterministic core untouched, called as a black box.** Zero diff inside `src/core/finance/`. The
   engine is invoked **once per perturbed input** (like `build_baseline_outlook` / `run_scenarios`),
   **never by inverting a guardrail formula**. The BUY/CONDITIONAL/DECLINE verdict comes from
   `synthesize_thesis`; recourse observes distance, it does not re-author the verdict.
2. **THE NON-INDEPENDENCE TRAP is a first-class requirement.** The levers are not independent — cutting
   price moves the loan, the cap rate, and the cash-in together; raising rent moves NOI, cap rate,
   coverage, and cash-on-cash together. The RED-on-regression suite **must include a case that only
   passes because the answer was produced by re-running the engine, and that a naive inverted-formula
   answer fails** (i.e. the naive answer differs measurably from the true re-run answer for that case).
3. **Schema additive-only.** New `RecourseLever` / `RecourseAnalysis` models alongside `ScenarioAnalysis`;
   nothing in `src/schemas/models.py` renamed, retyped, or removed. `InvestmentThesis.levers` unchanged.
4. **Honesty as a values commitment.** "WOULD close it, holding the other levers fixed" — never "WILL".
   Flag-implausible-levers-never-remove (decision 1). Lead cheapest single fix, flag other gaps remain
   (decision 2). Say so plainly when nothing realistic closes it (decision 3). Guardian VETO enforces.
5. **Determinism.** Same inputs ⇒ byte-identical `RecourseAnalysis` and report section. Any bounded
   search must be deterministic (fixed bounds, fixed tolerance, no unseeded randomness). Default
   (no near-miss) report output stays byte-identical to pre-mission.
6. **Threshold decisions untouched.** No change to any guardrail constant or verdict threshold (3.1c is
   a later mission). This feature *enables* revisiting them later; it does not revisit them now.
7. **No new external surface.** No file paths, no network, no untrusted input, no AI/model of any kind.
8. **Prove-the-test.** Every fix ships a test that turns RED on revert — demonstrated, not assumed.
9. **Quality gate.** `ruff format --check` + `ruff check` + `mypy .` clean; coverage ≥80%.
10. **Git.** Branch off freshly-synced `main` **after Mission 3 merges**; no PRs; merge to `main` only
    after Roger's mission gate; never force-push `main`; reconcile any origin delta; push only at
    Roger's instruction.

---

## Gates summary

- **Gate D (pre-implementation):** guardian honesty VETO + bounded founder-proxy product call + perf
  sanity call — all blocking for their scope. No security gate (no external surface).
- **Gate V (post-implementation):** code review (no finance-core diff; no formula inversion) + guardian
  overclaim VETO.
- **Mission gate (Roger only):** manual-testing doc fully VALIDATED by Roger; then merge; then push at
  Roger's instruction. The orchestrator never self-approves.

---

## Ledger updates to apply when this charter is committed to main

> **Do NOT edit `docs/plans/ROADMAP_TRACKER.md` now** — it carries uncommitted Mission 3 work, and
> editing it would tangle Mission 4's charter into Mission 3's in-flight changes. Apply the updates
> below to the tracker **after** this charter is committed to `main` (i.e. once Mission 3 has landed and
> the tree is clean), so they land cleanly.

**§4 Opportunity backlog — Backlog #6 row.** Mark it **CHARTERED as Mission 4, 2026-08-28** (not yet
built), sequenced after Mission 3's founder gate. Add a status line: _"Actionable Recourse chartered as
Mission 4 (branch `mission/4-actionable-recourse`); artifacts under `docs/plans/MISSION_4_*` and
`docs/manual testing/MISSION_4_MANUAL_TESTING.md`. Re-run-the-engine design honored as spec; the
non-independence trap is a first-class test requirement. Independent of Mission 3 (operates on
FinancialInputs/FinancialForecast/InvestmentThesis, never CV/vision). Makes Mission 2's deferred 3.1c
threshold decisions revisitable AFTER it ships, not before."_

**§5 Current recommendation.** Replace the Mission 3 recommendation with:
_"**Mission 4 — Actionable Recourse ('What would have to change?') — CHARTERED 2026-08-28, not yet
built; sequenced after Mission 3 clears its founder gate.** Backlog #6. Keeps the verdict, attaches to
a near-miss how far from the line it sits and what single investor-movable lever (rent/unit, price,
rate, opex) would close the gap, in several currencies. Re-runs the deterministic engine once per
perturbed input (never inverts a guardrail formula — the levers are non-independent), reuses the
existing rejector for plausibility, flags-don't-removes implausible levers, leads cheapest-first, and
says so plainly when nothing realistic closes it. Low blast: zero `src/core/finance/` diff, additive
schema only, one appended report section. Baseline + branch established at Wave Sync after Mission 3
merges. Artifacts: `docs/plans/MISSION_4_actionable_recourse.md` (charter),
`docs/plans/MISSION_4_SPRINT_TRACKER.md`, `docs/plans/MISSION_4_HANDOFF.md` (pasteable prompt),
`docs/plans/MISSION_4_PLAIN_ENGLISH.md`, `docs/manual testing/MISSION_4_MANUAL_TESTING.md`."_

Note under §5 that Mission 3's own status/merge sha should be recorded in §2 mission history when it
lands (that is Mission 3's closing task, not Mission 4's).

**§6 Changelog — append a dated entry:**
_"**2026-08-28 (Mission 4 CHARTERED — Actionable Recourse 'What would have to change?'; docs-only, no
code, no git ops).** Formalized the Sonnet-selected Mission 4 (backlog #6) into its five-artifact
charter package while Mission 3 remained in flight (uncommitted on `mission/3-byo-onnx-provider`;
`main @ 6d9c000`). Did NOT touch `ROADMAP_TRACKER.md` (dirty with M3 work) — tracker updates recorded
in the charter's 'Ledger updates' section for later application. Verified every design anchor against
the tree at `6d9c000`: `synthesize_thesis` (`chief_strategist.py:137`; five always-on guardrails +
two conditional CF checks; verdict = fail-count, `:227-252`), the re-run-the-engine pattern
(`build_baseline_outlook` `crew.py:65`; `run_scenarios` step (d) `scenario_runner.py:126`),
`reject_unrealistic` (`rejector.py:54`), the `ScenarioAnalysis` frozen-model shape to mirror
(`models.py:1277`), and the Market-Scenarios report append pattern (`generator.py:1246`). Baked in the
non-independence trap as a first-class RED-on-regression test requirement, additive-schema and
zero-finance-core-diff constraints, honest-framing (WOULD-not-WILL, flag-don't-remove, cheapest-first,
honest-null), and the sequencing rule (branches after Mission 3's founder gate; technically independent
of it). Agent roster co-designed for router confirmation at dispatch; **no security gate** (no external
input surface). Interaction noted: this feature makes Mission 2's deferred 3.1c threshold decisions
revisitable after it ships, not before. Files left uncommitted for Roger; no git ops performed."_
