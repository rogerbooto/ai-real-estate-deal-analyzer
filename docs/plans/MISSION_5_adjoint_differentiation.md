# Mission 5 — Adjoint Differentiation & Optimized Recourse Search

_Charter. Owned by the mission-planner; the executing orchestrator keeps the sprint tracker current,
not this file. `path:line` anchors below were verified against the tree at the commit named in
§Baseline; re-read any you touch before changing it._

> **Scope note (2026-08-31, EXPANDED by Roger).** This mission was originally chartered as Half A
> alone (adjoint differentiation + single-lever recourse acceleration), with the multi-lever recourse
> optimizer recommended for a *separate* Mission 6. **Roger has decided to expand this mission to
> include the optimizer**, overriding the split recommendation. The mission now runs **two halves in
> sequence** (A then B) with a hard **internal AD go/no-go checkpoint** between them so the AD
> foundation is proven before the optimizer builds on it. The mission slug and filenames keep
> `adjoint_differentiation` for continuity; the human title is broadened to reflect both halves.
> The planner's over-scope concern is registered in §Risks — Roger has read it and elected to expand.

---

## Executive Summary

Mission 4 shipped **actionable recourse**: for a near-miss deal it answers "what single change would
close the gap?" by **bump-and-reprice** — perturb one lever, re-run the whole engine, bisect until the
failing guardrail flips. It is honest and obvious, and it works: `compute_recourse`
(`src/market/recourse.py:792`) bisects each lever (`_bisect`, `recourse.py:471`), re-running
`run_financial_model` for every candidate (`_rerun`, `recourse.py:412`) — roughly **10–20 engine probes
per lever/guardrail pair**. It is also slow, and Mission 4's own perf work says so: the committed
benchmark (`tests/perf/bench_finance_engine.py`) times the institutional-ceiling row (5,000 units /
100 years) at **best 181–197 ms / median up to ~213 ms against a `BUDGET_MS = 250.0`** (re-baselined
from 120 ms during Mission 4 validation, 2026-08-30, `bench_finance_engine.py:86-98`), and its own
comment identifies the rent-lever bisection probes as ~85% of that cost. The **honest current baseline**
Discovery must reconcile is **~180 ms / ~150 probes** against the 250 ms budget — **NOT** the brief's
unverified "73 ms". **30 ms is Roger's stated target**, not a measured floor.

This mission has **two halves, run strictly in sequence**:

**HALF A — adjoint differentiation + single-lever acceleration (the existing chartered scope,
unchanged).** Quant desks faced exactly this bump-and-reprice cost and largely abandoned it: instead of
*searching* for the answer, get the **derivative of the model itself** and jump to it — the same
mathematics as backpropagation, because the engine is a computation graph and one pass yields exact
partial derivatives. This half investigates and (subject to a measured go/no-go) implements that:
**exact derivatives turn bisection into Newton's method on the guardrail**, dropping ~10–20 probes to
**~3–4**, every answer confirmed by one real engine re-run. It ships a **tolerance rule FIRST** (below),
decides **forward-vs-reverse AD by measurement** on the 4-in/≤7-out shape, and does the hard, uncertain
part — **differentiating through the IRR/Brent bracketed root-find**. This is the remaining credible
path toward Roger's **30 ms** target for the 5,000-unit / 100-year analysis.

**HALF B — the multi-lever recourse optimizer (NEW, added by Roger's expand decision).** Today recourse
answers only *single-lever* questions: "any ONE of these closes it." But an investor may be able to move
*several* levers at once. Half B adds a **second output section** — **"top-3 actionable
combinations"** — alongside the existing single-lever menu, so the report offers **both**: the single
cheapest change AND up to three realistic *bundles* of changes. It is a **constrained optimization**
solved with a **Lagrangian/KKT method** consuming the exact AD Jacobian Half A produces, made global
with **deterministic multi-start**, with feasibility supplied by a **unified all-four-lever
combination-plausibility gate** (the real new engineering — see §Design decisions). Every reported
combination is confirmed by one real engine re-run, exactly as single-lever answers are. **Half B is
gated by an internal AD go/no-go checkpoint: if the AD foundation does not validate, Half A's tolerance
rule + AD still ship as the mission's value and Half B defers.**

**It does not violate the founder invariant "re-run the engine, never invert a formula."** The
derivative is computed *from the actual model* (dual-number or tape-based differentiation of the real
`run_financial_model`), not from hand-algebra on a guardrail formula — **and the final reported answer
is always confirmed by one real, un-differentiated engine re-run** before it is shipped. AD accelerates
the search; it never replaces the answer.

**One thing must ship BEFORE any AD work, and it is the reason the mission is reviewable at all: a
tolerance rule.** Mission 4 held the golden forecasts **bit-exact** (`assert actual == expected`,
`tests/core/finance/test_golden_forecasts.py:188`; 34 cases). Automatic differentiation reorders
floating-point arithmetic and **cannot** meet bit-exactness. Roger approved relaxing the invariant from
"no shipped number moves at all" to "**no shipped number moves by more than a nine-nines relative
tolerance (~1e-9)**, always measured against the *original* golden, never the previous version." That
relaxation is a **values-level change** to the deterministic-core invariant, so it is gated by a
mandatory `principal-principles-guardian` VETO at Gate D — and the tolerance rule's design is the
artifact the guardian reviews. **Tolerance ships first; AD is built against it.**

---

## Baseline

`base = main @ 7cfd449, synced 2026-08-31.`

- **Gate already verified by the orchestrator:** Mission 4 is merged to `main` as `7cfd449`
  ("Merge Mission 4: actionable recourse … validated by Roger 2026-08-31, 9/9 PASS"); `main` is clean
  and in sync with `origin/main`. This charter is planned read-only against that commit.
- **Anchors verified against the tree at `7cfd449`** (re-verify at Wave Sync before touching):
  - `compute_recourse` `src/market/recourse.py:792`; `_bisect` `recourse.py:471`; `_rerun`
    `recourse.py:412`; `_perturb` `recourse.py:372`; `is_genuinely_close` `recourse.py:213`;
    `GENUINELY_CLOSE_MAX_FAILS = 3` `recourse.py:143`; `_search_one` `recourse.py:663`.
  - `run_financial_model` `src/core/finance/engine.py:638`; `forecast_metrics` (light search path)
    `engine.py:671`; `precompute_income` `engine.py:186`; `_forecast_core` `engine.py:309`.
  - `irr` `src/core/finance/irr.py:188` uses a **bracketed** domain-bounded search + Brent's method
    (`_brent_root`, `irr.py:83`) — a bracketed iterative root-find. Differentiating **through** this
    is the hardest part (see Discovery / Binding Constraints).
  - Golden harness: `tests/core/finance/test_golden_forecasts.py` — **bit-exact** (`assert actual ==
    expected`, `:188`; determinism `:191`; 34 `CASE_IDS` from `tests/core/finance/golden_cases.py`).
    Golden data file `tests/data/golden/finance_engine_forecasts.json`; regeneration only via
    `tests/core/finance/generate_golden_forecasts.py`. The file header already documents two
    deliberate, human-reviewed regenerations (`test_golden_forecasts.py:36-119`).
  - Committed benchmark `tests/perf/bench_finance_engine.py`: PRIMARY row `("5,000u / 100y", 5_000,
    100)` (`:79`), `BUDGET_MS = 250.0` (`:97`), `PRIOR_BUDGET_MS = 120.0` (`:98`); imports the real
    `_perturb` so it cannot drift from production (`:54-66`).
  - `purchase_price` field has **no lower bound** (`src/schemas/models.py:24` — `Field(...)`, no `ge=`);
    horizon ceiling `le=50` at `src/inputs/inputs.py:74` (with the "silently unenforceable constraint"
    note at `inputs.py:210`).
- **Mission 4 already opened the finance-core door.** Mission 4 waived its own zero-`finance-core`-diff
  constraint mid-mission (charter amendment) and rewrote `engine.py`, `irr.py`, and `amortization.py`
  for performance + a real solver-crash fix, and re-baselined the golden. So Mission 5's AD work is a
  *continuation* of an already-touched core — not a first breach — but it is still **high blast** and
  is gated accordingly (see Binding Constraints, Gate D).
- **⚠ Number to reconcile, do not assume.** The brief states "Mission 4 left it at 73 ms, down from
  13 s." The committed benchmark at `7cfd449` reads **best 181–197 ms / median up to ~213 ms** for the
  budgeted 5,000u/100y row, not 73 ms; "30 ms" appears **nowhere** in the code. Treat 30 ms as Roger's
  stated *target* and 73 ms as an **unverified** figure Discovery must reconcile against a fresh
  measurement (see PF.1). The mission is judged on the *measured* before→after, not on the brief's
  numbers.
- Verified env: `airedeal` conda env at `/home/rtokime/anaconda3` (NOT `~/miniconda3`), Python 3.10.
- The graphify graph (`built_at_commit` differs from HEAD) is a **lead only**; confirm every edge
  against the file at its own commit.

---

## Branch

`mission/5-adjoint-differentiation` — cut off freshly-synced `main` in Wave Branch. All mission work
commits here; nothing lands on `main` until Roger's mission gate, then Wave Integrate merges `--no-ff`
and pushes only at Roger's instruction.

---

## In scope

### Half A — adjoint differentiation + single-lever acceleration (unchanged chartered scope)

1. **The tolerance rule — SHIPPED FIRST, gating everything after (Wave 1 of implementation).**
   - Relax the golden invariant from bit-exact equality to a **relative tolerance of ~1e-9**
     ("nine nines"). Calibration is a hard requirement: the tolerance MUST still **catch the injected
     rounding bug that appears at ~9.4e-8 relative** (a 1e-9 rule catches it; a 1e-6 rule does not).
   - **Anchor to the ORIGINAL golden, never the previous version.** Each change is measured against the
     first-correct golden, so ten successive 1e-8 drifts cannot ratchet the tolerance while every step
     shows green. The comparison harness must make anchoring structural, not a convention.
   - **Any change that *approaches* the tolerance requires WRITTEN JUSTIFICATION**, not a green tick —
     a recorded note (in-repo, like the existing regeneration records) explaining why the drift is
     legitimate. The harness surfaces "approaching tolerance" as a distinct state, not silent pass.
   - This is a **values-level relaxation** of the deterministic-core invariant → guardian VETO at
     Gate D reviews its design before any AD code is written.
2. **A measured forward-vs-reverse AD decision (Discovery), then the chosen implementation.**
   - Start from the design finding, do not rediscover it: reverse-mode AD (true AAD) wins when inputs
     vastly outnumber outputs; **this problem is inverted — 4 levers in, ≤7 guardrails out.** Forward-mode
     AD via **dual numbers** needs 4 passes, is far simpler than a tape, and needs **no autograd
     dependency.** Discovery must nonetheless **justify the choice with MEASUREMENTS against the real
     4-in/≤7-out shape**, not by reaching for the famous name.
   - Implement exact partial derivatives of the guardrail metrics with respect to the four levers,
     computed from the real engine, and use them to replace bisection with **Newton's method on the
     failing guardrail** in the recourse search.
3. **Every reported recourse number confirmed by one real engine re-run.** The Newton step proposes an
   answer; a single un-differentiated `run_financial_model` re-run confirms it clears the guardrail
   before it is shipped. If confirmation fails, fall back to the existing bisection's confirmed point
   (the safety pattern `_search_one` already uses at `recourse.py:723-735`).
4. **The IRR/Brent differentiation approach** — differentiating through the bracketed Brent root-find
   in `irr.py` is the hardest part. Discovery decides between the **implicit function theorem** (the
   derivative of a converged root without differentiating each iteration) and **differentiating the
   converged solution**, and documents monotonicity/convergence assumptions and how they are checked.
5. **A numpy re-measurement.** Mission 4 rejected numpy on measurement (~70 ms import cost per CLI run
   vs ~15 ms saved). Re-measure against the current tree rather than assuming that verdict holds; state
   the disposition. Any new dependency needs written justification.
6. **RED-on-regression tests, prove-the-test.** Every shipped behaviour ships a test that turns RED on
   revert, demonstrated with real failure output: the tolerance harness (catches ~9.4e-8, passes a
   legitimate 1e-9 AD drift, anchors to origin); the AD-vs-engine-rerun agreement on a near-miss deal;
   the probe-count drop; determinism; and the confirmation-fallback path.
7. **Perf measurement recorded against the 30 ms target.** Extend/reuse the committed benchmark to
   report the measured before→after for the 5,000u/100y row and the probe-count drop. **State the
   result honestly** — a measured near-miss of 30 ms is a *result*, not a failure.
8. **Open-item dispositions** (see §Open items) — the money-field lower-bound pass, the horizon-100
   raise, and the CLI-traceback polish are folded in as bounded, low-blast fixes where they are cheap
   and independently valuable; each with its own RED test and manual-test case.
9. **The AD-Jacobian output API — the clean 7×4 seam Half B consumes.** Discovery designs, and Half A
   implements, a stable internal API that returns the exact partial-derivative matrix (≤7 guardrails ×
   4 levers) from a single point evaluation, in the **real lever basis** (a column = "move one lever,
   see the impact on all guardrails"). Half A uses it for single-lever Newton; Half B's optimizer
   consumes the *same* seam. Designing this as a clean seam in Half A is what lets the internal AD
   checkpoint (below) cleanly separate an AD bug from an optimizer bug.

10. **Docs (Half A).** README / `src/core/finance/README.md` (or owning subarea README) /
    `src/market/README.md` / CHANGELOG `[Unreleased]` updated honestly to describe the tolerance rule
    and (if shipped) the AD search. **Doc reconciliation is a reasoning task** — routed at STANDARD
    tier and verified against the real symbols (Mission 4 lesson).

### Half B — the multi-lever recourse optimizer (NEW; behind the internal AD go/no-go checkpoint)

> **Half B is entered ONLY if the internal AD checkpoint passes** (Half A's AD gives the same answers
> within tolerance and the IRR/Brent differentiation is sound). If AD no-gos, Half B defers and Half A
> ships alone — see §Waves and §Risks. Every design decision below is settled with Roger and recorded
> in §"Design decisions & rejected alternatives" so it is not re-litigated.

11. **A second report output section: "top-3 actionable combinations".** The report keeps the existing
    **single-lever menu** ("any ONE of these closes it") and adds a **second section** listing up to
    **three realistic COMBINATIONS** of levers moved together. Both sections ship — *why both* (Roger):
    we do not know whether the investor can act on one lever or several at once, so offer both. Same
    honesty framing as Mission 4: flag-don't-remove, honest-null when nothing plausible closes it.

12. **A constrained optimization over the four levers, solved with a Lagrangian/KKT method.** The
    optimizer consumes the exact **AD Jacobian** from Half A (scope #9). The concrete method (augmented
    Lagrangian / SQP / projected-gradient / interior-point) is **chosen by measurement in Discovery**,
    not assumed. **Deterministic multi-start** provides globality: seeds come from a **fixed grid /
    scatter** (never stochastic), so the same input yields the same three combinations, every run.

13. **A feasibility-not-optimization cost model.** Rather than minimize an ill-defined *cross-lever*
    cost (which would demand normalizing a dollar of price against a dollar of rent), the optimizer
    **FILTERS** to combinations the plausibility gate calls feasible ("makes sense"). The gate is a
    **deterministic boolean feasibility projection**, NOT a differentiable objective term — the gradient
    that drives the search comes from the **guardrail margins** (the AD Jacobian), not from the gate.

14. **THE CORE NEW ENGINEERING TASK: a unified all-four-lever joint combination-plausibility gate.**
    Today `_judge_plausibility` (`recourse.py:609`) judges **one lever at a time**, uniting two
    single-lever checks: `_rejector_flagged` (`recourse.py:519`), which reuses `reject_unrealistic`
    (`src/market/rejector.py:68`), and `_magnitude_flagged` (`recourse.py:584`). But the rejector's axes
    are **market-hypothesis deltas** — its real cross-axis rules are `|interest_rate_delta −
    cap_rate_delta| ≤ 0.02` (`rejector.py:23`), `rent_delta ≥ +0.03 ⇒ vacancy_delta ≤ +0.015`
    (`rejector.py:38-41`), and STR coherence (`rejector.py:44-64`). **Two of the four recourse levers
    (rent, opex) have NO rejector axis, and price only reaches it via a cap-rate proxy** — which is
    exactly why Mission 4 bolted on `RATE_MAGNITUDE_THRESHOLD` (`recourse.py:130`) and
    `_MAGNITUDE_RELATIVE_THRESHOLD` (`recourse.py:120`). Half B **unifies these into one joint gate that
    judges a FULL four-lever combination**, including **joint** plausibility — e.g. simultaneously
    cutting price AND raising rent may each be individually fine yet **jointly** implausible. **What
    makes a COMBINATION plausible is a product decision** (founder-proxy, Gate D) — this is the real
    design work, and it gets its own Discovery sub-task and product call.

15. **Normalization-free top-3 selection.** The three surfaced combinations are chosen by three
    normalization-free criteria: **parsimony** (fewer levers moved), each lever's move as a fraction of
    **ITS OWN plausible range** (within-axis, never cross-axis), and **diversity** (distinct routes,
    DiCE-style — three genuinely different bundles, not three variants of one). **No metric that makes a
    dollar of price commensurable with a dollar of rent** is introduced anywhere.

16. **Interpretable coordinates only.** The optimizer operates in the **real lever basis**; coupling is
    read directly from the AD Jacobian (a column = move one lever, see impact on all guardrails). A
    blended/singular search direction MAY be used as an **internal heuristic only**, translated back to
    real levers before anything is displayed. **No decomposed basis (PCA/eigen/SVD/LDA) is ever
    surfaced** — see §Design decisions for the one-reason rationale.

17. **Every reported combination confirmed by one real engine re-run.** Exactly as single-lever answers
    are (scope #3). Non-independence stays real — one lever fans out to loan / cap-rate / cash-in;
    several levers each move one or more guardrails — so the optimizer **re-runs the engine, never
    inverts**; every displayed combination is confirmed by one un-differentiated `run_financial_model`
    re-run before it ships.

18. **RED-on-regression tests for Half B** — multi-start determinism (same input ⇒ same three), the
    feasibility gate (an implausible combination is rejected, including a jointly-implausible one that is
    individually fine), diversity (the three are distinct), parsimony ordering, local-minima behavior,
    and every-combination-confirmed-by-a-real-rerun. Each turns RED on revert, demonstrated.

19. **Docs (Half B).** The two-section report output and the unified plausibility gate documented
    honestly in `src/market/README.md` / reports README / CHANGELOG `[Unreleased]`, at STANDARD tier,
    verified against real symbols.

## Out of scope (explicitly)

- **Integer-cents money representation.** This is the **named sibling/successor mission** (see
  §Related/successor missions), not this one. It makes summation order-independent and gives exact
  money arithmetic — a larger, high-blast refactor. Mission 5 does not start it.
- **Any learned surrogate or decomposition method for the user-facing answer** — no CNN/MLP, no learned
  surrogate model, no TPE / Bayesian optimization, no PCA / eigen / SVD / LDA basis for what the
  investor sees. **The one-reason rationale (recorded so no future planner or orchestrator
  re-litigates it):** we OWN the exact, cheap, and (post-Half-A) differentiable generating function.
  Every learning/decomposition tool is built for the *opposite* regime — an expensive, unknown, or noisy
  function, or data that needs reduction. Classical numerical optimization on the real model is the
  correct and robust family here precisely because Roger generates and controls the data. (And
  orthogonalizing via eigen/SVD/LDA yields axes that are uninterpretable *blends* of levers — destroying
  the interpretability that is the product.) See §"Design decisions & rejected alternatives".
- **Any threshold/policy change beyond the one bounded product call on `GENUINELY_CLOSE_MAX_FAILS`.**
  The tolerance *value* (1e-9) and the near-miss threshold are the only two numbers a founder-proxy
  call may set this mission. No guardrail constant, no verdict threshold, no horizon-ceiling *policy*
  beyond the specific 50→100 raise disposed of in §Open items is touched.
- **No new external surface** — no file paths, no network, no untrusted input, no AI/model. The AD
  machinery is internal deterministic math.
- **No autograd/JAX/PyTorch dependency unless measurement forces it and Roger approves it.** The
  design finding says forward-mode dual numbers need none; a heavyweight framework would be a large new
  surface. Any dependency needs written justification and re-measurement (see #5).
- **Replacing bisection wholesale / deleting the engine-rerun path.** The confirmed engine re-run stays
  as the source of truth and the fallback; AD sits *in front of* it, not instead of it.

---

## Waves & gates

`Wave Sync → Wave Branch → Wave Discovery → Gate D (guardian VETO on the invariant relaxation + founder
product calls + perf go/no-go) → Wave Implementation Phase A (tolerance FIRST, then single-lever AD) →
INTERNAL AD GO/NO-GO CHECKPOINT → Wave Implementation Phase B (multi-lever optimizer) → Wave Validation
→ Gate V (code review + guardian re-check VETO) → Mission gate (Roger) → Wave Integrate.`

> **Two go/no-go structures de-risk this expanded mission.**
> 1. **Gate D perf go/no-go on the AD portion.** The tolerance rule is **independently valuable** (it
>    makes any future non-bit-exact change reviewable) and ships first. If the measured
>    forward-vs-reverse study and the IRR-differentiation analysis show the win does not justify the
>    finance-core blast, Roger may stop the mission after the tolerance rule ships — and it will still
>    have delivered real value. AD is a measured bet, not a foregone conclusion.
> 2. **The INTERNAL AD checkpoint between Phase A and Phase B (this is how Roger's expand decision
>    honors the debugging boundary the split would have given).** Half B builds the optimizer directly
>    on Half A's AD Jacobian. Before a single line of the optimizer is written, the AD foundation must
>    be **proven**: single-lever AD answers match today's bisection within tolerance, and the IRR/Brent
>    differentiation is sound. **If AD no-gos, Half A's tolerance rule + AD (or the tolerance rule
>    alone) ships as the mission's value and Half B defers.** Making this checkpoint explicit means a
>    wrong top-3 is unambiguously an *optimizer* bug, not maybe-an-AD-bug.

| Wave | What happens |
| --- | --- |
| **Sync** | Phase 0 re-sync: `git fetch`; confirm `main @ 7cfd449` is canonical latest and clean; STOP if a later mission is mid-flight. Re-confirm every charter `path:line` at the real baseline. Run the full gate battery green in `airedeal` (`pytest`, `ruff format --check`, `ruff check`, `mypy .`, `python main.py`); pin suite count, coverage, tests-tree SHA, and the pre-mission `python main.py` report sha256. |
| **Branch** | `git switch main && git switch -c mission/5-adjoint-differentiation`. |
| **Discovery** | `app-evaluator` confirms current axis grades / gap severity. `staff-python-engineer` + (for the gnarly math) the top-tier AD reasoning task produce a spec covering BOTH halves: **(Half A)** (a) forward-vs-reverse AD **measured** against the 4-in/≤7-out shape, with the dual-number 4-pass approach as the hypothesis to beat; (b) the IRR/Brent differentiation approach (implicit function theorem vs differentiating the converged root) — flagged as the hardest part, with monotonicity/convergence assumptions and checks; (c) the tolerance-rule design (1e-9, anchor-to-origin, approaching-tolerance⇒justification, calibration against ~9.4e-8); (d) the numpy re-measurement; (e) the confirmation-by-real-rerun protocol and fallback; **(f) the AD-Jacobian output API — the clean 7×4 seam Half B consumes.** **(Half B)** (g) the constrained-optimization method selection (augmented Lagrangian / SQP / projected-gradient / interior-point — decided **by measurement**) + deterministic multi-start design; (h) **the rejector-unification design** — one joint all-four-lever combination-plausibility gate (the core new engineering task); (i) the normalization-free top-3 selection design (parsimony · within-axis magnitude · diversity). `principal-performance-engineer` produces the measured current baseline (reconciling the 73 ms claim; honest baseline ~180 ms / ~150 probes) and the projected/target comparison. **No production code.** |
| **Gate D (pre-impl)** | `principal-principles-guardian` reviews the **tolerance-rule design as a values-level relaxation of the deterministic-core invariant** and holds a **mandatory VETO** — no AD code until lifted. `principal-founder-proxy` makes the product calls: the tolerance value (ratify 1e-9); the `GENUINELY_CLOSE_MAX_FAILS` decision; the horizon-100 / money-field / CLI-polish dispositions; **and the Half B calls — what makes a four-lever COMBINATION plausible (the unified gate's rule), and the top-3 selection policy (parsimony / within-axis magnitude / diversity weighting).** `principal-performance-engineer` makes the explicit **go/no-go** on the AD portion: does the measured win justify the finance-core blast, or does the mission ship the tolerance rule alone? All blocking for their scope. |
| **Implementation Phase A** | **Sequenced, not parallel across the T/AD boundary.** T-sub-wave first (≤3 concurrent): tolerance harness + anchor-to-origin + approaching-tolerance state (`staff-python-engineer`) · its RED suite incl. the ~9.4e-8 calibration test (`staff-qa-test-engineer`) · docs (`staff-documentation-maintainer`, STANDARD). **AD-sub-wave only after the tolerance rule is green and the guardian VETO is lifted** (≤3 concurrent): AD machinery + the 7×4 Jacobian API + Newton-on-guardrail single-lever search + confirm-by-rerun + fallback (`staff-python-engineer`, with fable-tier AD reasoning support) · AD-vs-engine agreement + probe-count + determinism RED suite (`staff-qa-test-engineer`) · perf benchmark extension (`principal-performance-engineer`). Open-item fixes fold into whichever sub-wave they fit, each with a RED test. **Proven against today's bisection.** |
| **INTERNAL AD go/no-go checkpoint** | **A hard wave boundary, recorded as a decision in the tracker.** The AD foundation must be validated BEFORE Phase B builds on it: single-lever AD answers match bisection within tolerance, the IRR/Brent differentiation is sound, and the 7×4 Jacobian API is stable. **GO → Phase B.** **NO-GO → Half B defers; the mission ships Half A (tolerance + AD, or tolerance alone if Gate D also no-goed AD) as its value**, recorded explicitly. This is what makes a later wrong top-3 unambiguously an optimizer bug. |
| **Implementation Phase B** (only if the AD checkpoint = GO) | The multi-lever optimizer on the now-stable Jacobian (≤3 concurrent): the constrained-optimization solver (Lagrangian/KKT) + deterministic multi-start + the **unified all-four-lever combination-plausibility gate** + normalization-free diverse top-3 selection + **every combination confirmed by a real engine re-run** (`staff-python-engineer` at fable for the constrained-optimization math) · the **two-section report output** — single-lever menu + top-3 combinations, flag-don't-remove, honest-null (`staff-report-experience-designer`) · the optimizer RED suite — multi-start determinism, feasibility gate (incl. a jointly-implausible-but-individually-fine combination), diversity, parsimony, local-minima, every-combination-confirmed-by-rerun (`staff-qa-test-engineer`) · Half B docs (`staff-documentation-maintainer`, STANDARD). |
| **Validation** | Full battery in `airedeal`: `pytest` green + coverage ≥80%; **BOTH** `ruff format --check` **and** `ruff check` clean (Mission 4 lesson: an agent reported "ruff clean" having run only `ruff check`); `mypy .` clean; default `python main.py` still within tolerance of the pinned pre-mission golden (documented if any shipped number moves, with justification). Every command in the manual-testing doc actually runs and produces the stated result — **including the Half B cases** (top-3 section appears; each combination flips the verdict on re-run; the unified gate rejects an implausible combination; the three are distinct; multi-start is deterministic; parsimony ordering). Perf measured and recorded vs the 30 ms target. |
| **Gate V** | `staff-code-reviewer` reviews the diff (esp.: every reported recourse number **and every combination** is confirmed by a real engine re-run; no guardrail formula is hand-inverted; the tolerance harness anchors to origin; the unified gate covers all four levers; multi-start is deterministic; no decomposed basis is surfaced; finance-core changes are justified). `principal-principles-guardian` re-checks the invariant relaxation as-built (VETO). |
| **Mission gate (Roger)** | Roger runs `docs/manual testing/MISSION_5_MANUAL_TESTING.md` by hand and flips the boxes. Not clear until the document-level box reads VALIDATED. Roger holds this gate; the orchestrator never self-approves. |
| **Integrate** | Only after Validation GREEN **and** Roger's mission gate: `git fetch`; rebase/merge onto latest `main`; re-run the **full** battery post-rebase (a pre-rebase green does not count); `git switch main && git merge --no-ff mission/5-adjoint-differentiation`; **push only at Roger's instruction** (reconcile any origin delta — never force-push). Record the merge sha + push result in the tracker. |

---

## Definition of Done

- [ ] **The tolerance rule shipped and governs everything after it.** The golden harness compares at a
      **~1e-9 relative tolerance anchored to the ORIGINAL golden** (never the previous version); it
      **still catches the ~9.4e-8 injected rounding bug** (proven by a RED test), and **would pass a
      legitimate 1e-9-scale AD drift**; any change *approaching* the tolerance produces an
      "approaching-tolerance" state that demands written justification, not a silent green.
- [ ] `principal-principles-guardian` reviewed the tolerance rule as a **values-level relaxation of the
      deterministic-core invariant** and lifted its VETO (Gate D), and re-confirmed as-built (Gate V).
- [ ] The forward-vs-reverse AD decision is **justified by measurement** against the real 4-in/≤7-out
      shape (not by name), and the IRR/Brent differentiation approach is documented with its
      assumptions and checks.
- [ ] **Every reported recourse number is confirmed by one real, un-differentiated engine re-run**
      before it is shipped; if confirmation fails, the search falls back to the bisection's confirmed
      point. Demonstrated in code and tests. (If Gate D's go/no-go stopped the AD portion, this DoD line
      is satisfied vacuously and the mission ships the tolerance rule alone — recorded explicitly.)
- [ ] The probe count per lever/guardrail pair **dropped measurably** (target ~10–20 → ~3–4), visible
      in benchmark/log output, with a RED-on-regression test pinning it.
- [ ] The perf measurement is **recorded against the 30 ms target** for the 5,000u/100y run (and the
      brief's 73 ms claim reconciled against a fresh measurement). A measured near-miss is reported
      honestly as a result.
- [ ] The numpy re-measurement is recorded with a disposition (keep out / justify in).
- [ ] Open-item dispositions applied as scoped (see §Open items), each shipped fix with a RED test.
- [ ] Every shipped behaviour has a RED-on-regression test, demonstrated (revert → RED → restore →
      GREEN) with real failure output.
- [ ] `pytest` green, coverage ≥80%; **BOTH** `ruff format --check` **and** `ruff check` clean;
      `mypy .` clean.
- [ ] **The internal AD go/no-go checkpoint was recorded** (GO or NO-GO, with its measured basis and
      date) BEFORE any optimizer code was written. On NO-GO, Half B is deferred and the mission ships
      Half A as its value — recorded explicitly.
- [ ] **(Half B, if the AD checkpoint = GO) Both output sections are present** — the existing
      single-lever menu AND the "top-3 actionable combinations" section — with flag-don't-remove and
      honest-null framing.
- [ ] **(Half B) Every single-lever answer AND every reported combination is confirmed by one real,
      un-differentiated engine re-run** before it ships.
- [ ] **(Half B) The unified combination-plausibility gate judges a full four-lever combination**
      (including joint plausibility — e.g. a jointly-implausible-but-individually-fine combination is
      rejected), replacing the per-lever-only judgement; and **multi-start is deterministic** (same
      input ⇒ same three combinations, pinned by a RED test).
- [ ] **(Half B) The three surfaced combinations are selected normalization-free** (parsimony /
      within-axis magnitude / diversity) and **no decomposed basis (PCA/eigen/SVD/LDA) is surfaced**;
      any blended direction is an internal heuristic only, translated back to real levers before display.
- [ ] README / owning-subarea README / `src/market/README.md` / CHANGELOG `[Unreleased]` describe the
      tolerance rule, the AD search, and (if shipped) the multi-lever optimizer + two-section output
      honestly; doc reconciliation done at STANDARD tier and **verified against the real symbols**.
- [ ] **NON-NEGOTIABLE:** The manual tests in `docs/manual testing/MISSION_5_MANUAL_TESTING.md` have
      been conducted and validated by Roger — **every** test case marked VALIDATED in its status box,
      and the document-level box reading VALIDATED. **This is a precondition of the founder gate; the
      mission gate cannot be requested until this line is satisfiable.**

---

## Agent roster (task → agent → model tier; ≤3 concurrent per wave)

> `staff-cost-aware-model-router` **must be invoked at kickoff** (standing rule §3a.1) to confirm the
> tier assignments below **before the first dispatch batch** — not "only when ambiguous." Record
> `task → agent → tier` and any deviation at dispatch time. Tier→model mapping used by prior missions:
> capable = opus · standard = sonnet · cheap = haiku · **top reasoning = fable** (reserved for the
> gnarliest math). **No `principal-security-engineer`** — no external input surface.

| Wave | Task | Agent | Tier |
| --- | --- | --- | --- |
| Discovery | Confirm axis grades / gap severity that justify the mission | `app-evaluator` | opus (capable) |
| Discovery | **AD design + IRR/Brent differentiation reasoning** (forward-vs-reverse measured; implicit-function-theorem vs converged-root) — the gnarliest math on the board | `staff-python-engineer` (top-tier reasoning) | **fable (top)** |
| Discovery | Current perf baseline (reconcile the 73 ms claim) + target/projection | `principal-performance-engineer` | opus (capable) |
| Discovery / Impl-T | Tolerance-rule design + implementation (1e-9, anchor-to-origin, approaching-tolerance state) | `staff-python-engineer` | sonnet (standard) |
| Impl-T / Impl-AD | RED suites (tolerance calibration ~9.4e-8; AD-vs-rerun agreement; probe-count; determinism; fallback) | `staff-qa-test-engineer` | sonnet (standard) |
| Gate D | **VETO on the invariant relaxation** (tolerance-rule design as values change) | `principal-principles-guardian` | opus (capable/fable) |
| Gate D | Product calls: ratify 1e-9; `GENUINELY_CLOSE_MAX_FAILS` decision; horizon-100 / money-field / CLI-polish dispositions | `principal-founder-proxy` | opus (capable) |
| Gate D / Impl-AD | Perf go/no-go on the AD portion; benchmark extension for probe-count + before→after | `principal-performance-engineer` | opus (capable) |
| Impl-AD (Phase A) | AD machinery + 7×4 Jacobian API + Newton-on-guardrail single-lever search + confirm-by-rerun + fallback | `staff-python-engineer` (with fable-tier AD support) | sonnet (standard), math support **fable** |
| Impl-B | **Constrained-optimization design + Lagrangian/KKT + deterministic multi-start + unified all-four-lever plausibility gate** — the gnarly constrained-optimization math | `staff-python-engineer` | **fable (top)** |
| Impl-B | Two-section report output (single-lever menu + top-3 combinations; flag-don't-remove; honest-null) | `staff-report-experience-designer` | sonnet (standard) |
| Gate D / Impl-B | Product calls: combination-plausibility rule (what makes a four-lever combo plausible) + top-3 selection policy | `principal-founder-proxy` | opus (capable) |
| Impl-B | Optimizer RED suite (multi-start determinism; feasibility gate incl. jointly-implausible; diversity; parsimony; local-minima; every-combination-confirmed-by-rerun) | `staff-qa-test-engineer` | sonnet (standard) |
| Impl | Docs (README / finance & market READMEs / CHANGELOG) — **reasoning task, verify against real symbols** | `staff-documentation-maintainer` | **sonnet (STANDARD, NOT haiku)** |
| Gate V | Code review of the full diff (rerun-confirmation on every answer AND combination; no hand-inverted formula; anchor-to-origin; unified gate covers all four levers; multi-start deterministic; no decomposed basis surfaced; finance-core changes justified) | `staff-code-reviewer` | sonnet (standard) |
| Gate V | Invariant-relaxation re-check (VETO) | `principal-principles-guardian` | opus (capable) |

Roger holds the mission gate (merge + push). No agent self-approves it.

---

## Binding constraints (non-negotiable)

1. **The claim survives: every reported number is confirmed by a real engine re-run.** AD accelerates
   the search; it never authors the answer. A Newton-proposed lever value is shipped **only** after one
   un-differentiated `run_financial_model` re-run confirms it clears the guardrail; on failure, fall
   back to the bisection's confirmed point.
2. **The tolerance rule ships FIRST and governs everything after.** No AD code is written until the
   tolerance rule is implemented, green, and the guardian VETO on its design is lifted. Anchor to the
   ORIGINAL golden; ~1e-9 relative; catches ~9.4e-8; approaching-tolerance ⇒ written justification.
3. **Finance-core changes are high-blast and justified.** Mission 4 already touched `engine.py`,
   `irr.py`, `amortization.py`; Mission 5 may extend them for AD **only** with explicit justification,
   guardian sign-off on the invariant relaxation, and every golden change within tolerance and
   documented. The verdict is still authored solely by `synthesize_thesis`.
4. **Deterministic; no new external surface; no network; no AI/model.** Same inputs ⇒ same
   `RecourseAnalysis` (now within tolerance rather than bit-exact, where AD is involved).
5. **New dependencies need written justification + re-measurement.** numpy was rejected in Mission 4 on
   measurement; re-measure, do not assume. No autograd/JAX/PyTorch unless measurement forces it and
   Roger approves.
6. **Prove-the-test.** Every fix ships a test that turns RED on revert — demonstrated with real failure
   output, not assumed.
7. **Quality gate.** `ruff format --check` **AND** `ruff check` **AND** `mypy .` clean; coverage ≥80%.
   Run BOTH ruff commands (Mission 4 lesson).
8. **Doc reconciliation is a reasoning task** — STANDARD tier or above, output verified against the
   real symbols (Mission 4 fabricated-API-docs lesson).
9. **Git.** Branch off freshly-synced `main`; no PRs; merge to `main` only after Roger's mission gate;
   never force-push `main`; reconcile any origin delta; push only at Roger's instruction.
10. **(Half B) The internal AD checkpoint is a hard gate.** No optimizer code is written until the AD
    foundation is proven (single-lever AD matches bisection within tolerance; IRR/Brent differentiation
    sound; 7×4 Jacobian API stable). A wrong top-3 must be diagnosable as an optimizer bug, not an AD
    bug — that is the whole point of the checkpoint.
11. **(Half B) Every reported combination is confirmed by one real engine re-run** — same discipline as
    single-lever answers. Non-independence is real; re-run the engine, never invert.
12. **(Half B) Interpretable coordinates only; no decomposed basis surfaced.** The optimizer works in
    the real lever basis; a blended/singular direction is an internal heuristic only, translated back to
    real levers before display. No PCA/eigen/SVD/LDA, no learned surrogate, no TPE/Bayesian optimization
    — for the recorded one-reason rationale, see §"Design decisions & rejected alternatives".
13. **(Half B) The plausibility gate is a deterministic boolean feasibility projection, not a
    differentiable objective term.** The optimizer's gradient comes from the guardrail margins (the AD
    Jacobian); the gate filters. Top-3 selection is normalization-free — nothing makes a dollar of price
    commensurable with a dollar of rent.

---

## Design decisions & rejected alternatives (Half B — settled with Roger, do not re-litigate)

These were settled with Roger in the expand-decision session (2026-08-31). They are the specification;
recorded here so no future planner or orchestrator re-opens them.

| Decision | What was chosen | Why (and what was rejected) |
| --- | --- | --- |
| **Optimization family** | Classical constrained optimization — a **Lagrangian/KKT method** (augmented Lagrangian / SQP / projected-gradient / interior-point; Discovery picks the concrete one by measurement) over the real levers, consuming the exact AD Jacobian, made global by **deterministic multi-start** (fixed grid/scatter seeds). | **Rejected: any learned surrogate / CNN / MLP, TPE / Bayesian optimization, and PCA / eigen / SVD / LDA decomposition for the user-facing answer.** ONE reason: we OWN the exact, cheap, post-Half-A-differentiable generating function. Every learning/decomposition tool targets the *opposite* regime — an expensive, unknown, or noisy function, or data needing reduction. Classical numerical optimization on the real model is correct and robust precisely because Roger generates and controls the data. |
| **Cost metric** | **Feasibility, not optimization.** FILTER to combinations the unified plausibility gate calls feasible; no cross-lever cost to minimize. | Rejected an ill-defined cross-lever cost that would demand normalizing a dollar of price against a dollar of rent. The gate is a deterministic boolean **feasibility projection**, not a differentiable objective term. |
| **Feasibility source** | The **unified all-four-lever joint combination-plausibility gate** (scope #14) — the rejector's cross-axis rules + the per-lever magnitude fallback, unified to judge a *full combination*, including joint plausibility. | Today's `_judge_plausibility` judges one lever at a time; rent/opex have no rejector axis, price reaches it only via a cap-rate proxy. Unifying these into one joint gate is the mission's core new engineering. What makes a *combination* plausible is a founder-proxy product call. |
| **Top-3 selection** | Normalization-free: **parsimony** (fewer levers), **within-axis magnitude** (each lever's move as a fraction of ITS OWN plausible range), **diversity** (distinct routes, DiCE-style). | Rejected any metric that makes different levers commensurable. Within-axis only, never cross-axis. |
| **Coordinates** | **Interpretable real-lever basis only.** Coupling read from the AD Jacobian (a column = one lever → all guardrails). A blended (singular) direction may be an **internal** search heuristic, translated back before display. | Orthogonalizing via eigen/SVD/LDA yields axes that are uninterpretable *blends* — destroying the interpretability that is the product. |
| **Non-independence** | Stays real — one lever fans out to loan / cap-rate / cash-in; several levers each move one or more guardrails. **Re-run the engine, never invert;** every combination confirmed by one real re-run. | Same discipline as Mission 4 single-lever recourse. |

---

## Risks & the registered over-scope concern

**Planner's registered concern (Roger has read it and elected to expand anyway).** Combining Half A
(gnarly AD through a bracketed Brent root-find, a values-level invariant relaxation, finance-core blast)
with Half B (a constrained optimizer + a brand-new unified plausibility gate + a new report section) in
**one** mission is **a lot of high-blast, high-uncertainty work for a solo dev** — exactly the kind of
scope the one-mission-at-a-time cap exists to contain. The split into a Mission 6 would have given a
clean debugging boundary and a natural stopping point. **Roger overrode the split.** The risk is
contained — not removed — by three structural devices, all mandatory:

1. **Tolerance rule ships first** and is independently valuable (value even on a full AD no-go).
2. **Gate D perf go/no-go** can stop the mission after the tolerance rule.
3. **The internal AD checkpoint** gates Half B: if AD does not prove out, Half B defers and Half A ships
   alone. This preserves the debugging boundary the split would have given — a wrong top-3 is an
   optimizer bug, never a maybe-AD bug — without needing two missions.

If, during execution, Phase B shows signs of sprawling past the solo-dev cap even after a clean AD
checkpoint, the orchestrator should surface it to Roger as a candidate to **carve Half B back out** to a
follow-on, rather than push through.

---

## Open items (disposition stated for each)

| Item | Disposition |
| --- | --- |
| **`purchase_price` has no lower bound** (`models.py:24`) → a negative price is accepted despite `validate_assignment=True`; likely true of other money fields | **IN SCOPE as a bounded money-field pass** (not one patch). Add lower bounds to money fields, with a RED test that a negative value is rejected with a clean message (not a traceback). Founder-proxy confirms which fields and the floor semantics at Gate D. |
| **Horizon ceiling `le=50`** (`inputs.py:74`); standing recommendation to raise to 100 (99-year leases are real and now work post-Mission-4) | **IN SCOPE, founder-ratified at Gate D.** Raise `le=50`→`le=100`; RED test that horizon 100 is accepted and 101 rejected. Low blast (one constraint), independently valuable. |
| **`--horizon 100` (pre-raise) / out-of-range surfaces a raw pydantic traceback** with the useful message at the bottom | **IN SCOPE as CLI polish.** Catch the validation error and print one clean line; RED test that an out-of-range horizon exits non-zero with a clean message, no traceback. |
| **`GENUINELY_CLOSE_MAX_FAILS = 3`** — chosen by necessity during Mission 4, not decided | **Founder-proxy product call at Gate D** (`principal-founder-proxy`). This is the one near-miss-threshold decision the mission may make. No code change unless Roger changes the value. |
| **Integer-cents money representation** | **OUT OF SCOPE — named sibling/successor mission** (see below). Recorded in the backlog; not started here. |

---

## Related / successor missions

- **Integer-cents money representation (sibling successor).** Represent money as integer cents so
  summation is order-independent and money arithmetic is exact. This *removes* the constraint that
  limited Mission 4's vectorization and would make parts of the AD/perf story cleaner — but it is a
  large, high-blast refactor of the finance core and the schemas, and it is **not** Mission 5 work.
  Named here so a future planner inherits it as a first-class candidate, sequenced after Mission 5.
- **~~Mission 6 — multi-lever recourse optimizer~~ (folded IN).** Previously recommended as a separate
  successor mission; **Roger folded it into Mission 5 as Half B on 2026-08-31.** It is no longer a
  distinct mission. Recorded here so the merge is traceable.

---

## Gates summary

- **Gate D (pre-implementation):** guardian **VETO on the values-level invariant relaxation** (the
  tolerance-rule design is the artifact) + bounded founder-proxy product calls (tolerance value;
  `GENUINELY_CLOSE_MAX_FAILS`; open-item dispositions; **and the Half B calls — the combination-
  plausibility rule and the top-3 selection policy**) + perf **go/no-go** on the AD portion. All blocking
  for their scope. No security gate (no external surface).
- **Internal AD go/no-go checkpoint (between Phase A and Phase B):** the AD foundation must be proven
  (single-lever AD matches bisection within tolerance; IRR/Brent differentiation sound; 7×4 Jacobian API
  stable) before any optimizer code. GO → Phase B; NO-GO → Half B defers, Half A ships alone. Recorded
  as a decision in the tracker.
- **Gate V (post-implementation):** code review (rerun-confirmation on every answer AND every
  combination; no hand-inverted formula; anchor-to-origin; unified gate covers all four levers;
  multi-start deterministic; no decomposed basis surfaced; finance-core changes justified) + guardian
  invariant-relaxation re-check (VETO).
- **Mission gate (Roger only):** manual-testing doc fully VALIDATED by Roger; then merge; then push at
  Roger's instruction. The orchestrator never self-approves.

---

## Ledger updates applied with this charter

Applied to `docs/plans/ROADMAP_TRACKER.md` in the same (uncommitted) change set: §2 records Mission 4 as
SHIPPED (`7cfd449`, validated 2026-08-31, 9/9) and Mission 3 as SHIPPED (`8b59399`); §4 adds the
open-items as backlog rows and names the integer-cents money sibling-successor; §5 recommendation →
Mission 5; §6 a dated changelog entry (2026-08-31). Files left uncommitted for Roger.

**Amended 2026-08-31 (scope EXPANSION by Roger):** Mission 5 broadened from Half A alone to Half A +
Half B (the multi-lever recourse optimizer), overriding the recommendation to split Half B into a
Mission 6. The internal AD go/no-go checkpoint between Phase A and Phase B is the risk-containment
device that preserves the debugging boundary the split would have given. Ledger re-touched: §4 folds the
former "Mission 6 multi-lever optimizer" candidate into Mission 5's scope (no longer a separate mission)
while keeping integer-cents money (#13) as the named sibling-successor; §5 recommendation → the
**expanded** Mission 5; §6 a dated changelog entry (2026-08-31). Still no code, no git ops.
