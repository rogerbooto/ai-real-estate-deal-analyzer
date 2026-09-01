# GD.1 — Gate D VETO review: the tolerance rule (D.3)

**Mission 5 · Gate D · principles guardian, VETO authority · routed fable (router escalation)**
**Baseline:** `mission/5-adjoint-differentiation` @ `87efd22`
**Artifact reviewed:** `docs/plans/mission-5-discovery/D3_tolerance_rule.md` (in full), plus every
file it describes, first-hand (list below).

---

## VERDICT: VETO LIFTED WITH CONDITIONS

Implementation of the tolerance rule (Impl-T wave) may proceed once the conditions below are
accepted as tracker rows. AD implementation remains gated on the tolerance rule being shipped and
green, per the charter's own sequencing.

**RATIONALE:**

- **Reviewed against:**
  `docs/plans/mission-5-discovery/D3_tolerance_rule.md` ·
  `tests/core/finance/test_golden_forecasts.py` (`:181`, `:191`, `:217`, `:225`, docstring `:2-134`) ·
  `tests/core/finance/generate_golden_forecasts.py` ·
  `tests/data/golden/finance_engine_forecasts.json` (via programmatic flatten, all 34 cases) ·
  `src/core/finance/amortization.py:60-109` ·
  `src/core/README.md` ("Determinism first"; the Gate 3 / G2-N1 / M21 records) ·
  `README.md:11` + reconciliation stamps ·
  `src/schemas/README.md` (determinism claims; confirmed no schema surface is touched) ·
  `CONTRIBUTING.md` ·
  `docs/plans/MISSION_5_adjoint_differentiation.md:128-174` (the chartered contract Roger approved) ·
  `docs/manual testing/MISSION_5_MANUAL_TESTING.md:30-104` ·
  project memory (`MEMORY.md`, `git-workflow-direct-to-main.md` — founder holds all gates).
  Licensing files not re-read this turn: the proposal is test-tree only, adds no dependency and
  moves no code, so it has zero licensing surface.
- **Principle invoked:** Deterministic core ("same inputs ⇒ same output"; `src/core/README.md`
  "Determinism first"; `README.md:11` "fully deterministic and reproducible") — plus the
  no-fabrication principle for the 9.4e-8 provenance question.
- **Independent verification performed (not taken on faith):**
  1. `git log --all -S"9.4e-8"` → exactly one commit, `87efd22` (the charter itself). Orchestrator
     finding 1 confirmed: the figure has no pre-Mission-5 provenance.
  2. `git log --all -- tests/data/golden/finance_engine_forecasts.json` → exactly one commit,
     `912a55f`. Orchestrator finding 2 confirmed: "the ORIGINAL golden" is unambiguous.
  3. **D.3's two walls and the defect signature reproduced from scratch** (scratchpad script,
     monkeypatching `amortization_payment` per D.3 §5.3, all 34 cases, 11,360 float fields):
     baseline unpatched = bit-identical to the committed golden; 1 ULP → max rel **1.1510e-13**
     (D.3: 1.151e-13); `×(1+9.4e-8)` → **1.3477e-5**, 2,958 fields > 1e-9 (D.3: 1.348e-5, 2,958);
     `round(payment,4)` → **1.1325e-7**, 1,613 fields (D.3: 1.133e-7, 1,613); `round(payment,6)` →
     **9.7904e-10**, 0 fields > 1e-9 (D.3: 9.790e-10). Every load-bearing number in D.3 §1.3/§5
     checks out. The "1e-9 was located, not chosen" argument stands on verified measurement.

---

## Ruling on the six questions

### (1) Does 1e-9 weaken the deterministic-core invariant? — NO, and the decisive text is the harness's own

The documented invariant — `src/core/README.md` "Determinism first", `README.md:11` "fully
deterministic and reproducible" — is a property of a fixed program: same inputs, same code, same
output. That property remains enforced at `==`, forever, by
`test_determinism_repeated_calls_are_identical` (`:191`) and `test_metrics_parity.py`, both
untouched. What relaxes is cross-version bit-stability — a stronger, undocumented, surplus
guarantee the golden harness added ahead of the Mission 4 vectorisation.

I tested D.3's argument rather than accepting it. The strongest case against: (a) "reproducible"
in `README.md:11` could be read by a user as "my saved report reproduces after an upgrade" — but
every rendered surface rounds to the dollar/cent or the fourth decimal of a rate, four-plus orders
above anything 1e-9 can move, so no user-visible number can change within tolerance; (b) bit-exact
meant *any* change to money math was detectable at zero threshold, and that capability is genuinely
relinquished — a `round(payment, 8)` bug (measured 1.67e-11) now lands silently. That residual is
real, is 1e-8 dollars on the payment, and cannot reach any rendered or guardrail surface. I rule it
an acceptable, measured price.

The decisive textual authority is the harness's own docstring (`test_golden_forecasts.py:17-20`):
*"If a genuinely-derived field could not be pinned exactly … that would be called out explicitly
here with a named, justified tolerance."* The original author defined the legitimate form of this
exact relaxation: **named and justified**. D.3 supplies the most thoroughly justified tolerance
this repository has ever seen — both walls measured, reproduced by this review — and 1e-9 is three
orders *tighter* than the "1e-6 tolerance philosophy" the harness itself invoked when the golden
last moved (docstring `:83-84`). This is not a breach of the invariant; it is the invariant's own
documented escape clause, exercised correctly, with Roger's in-principle approval.

### (2) The anchor — structural, not a speed bump, but ONLY with the second tooth

The insight is correct: the ratchet is caused by re-anchoring being *cheaper for small drifts than
large ones*. Today a regenerated golden is a thousands-of-lines float diff no human can grade by
eye — 1e-12 drift and 1e-3 drift look identical in review. The digest pin + `ANCHOR.json` converts
that into a two-file, self-incriminating diff carrying `max_rel_drift_vs_previous_anchor` as a
single reviewable number, and the generator refusal removes drift as a *trigger* for regeneration
entirely. In this repo's actual workflow (direct-to-main, founder holds all gates — project
memory), every supersession is necessarily a founder-visible event. `git log -S'--supersede-anchor'`
enumerates the full re-anchoring history forever. That is structural.

**Where it decays:** an agent under deadline runs `--supersede-anchor --rationale "AD drift"` and
the marginal cost of hop N is one boilerplate string. Individually-rationalized hops can still
compound unbounded — the ratchet with paperwork. The only element that does NOT decay is §3.5, the
cumulative-drift budget: at 1e-8 cumulative the chain hard-fails, and the failure **cannot be
cleared by another rationale** — only by independent human re-derivation in the spirit of `:225`.
That is a genuine hard stop. Therefore §3.5 is **mandatory** (condition C2), not a SHOULD. With it,
"ten re-anchors cost ten founder approvals *and then the eleventh is impossible without human
re-verification*" is actually true. Without it, the answer to the orchestrator's question would be
"it decays," and this section of the design would not have cleared review.

The one unreviewed path — the structural branch changes the digest without `--supersede-anchor` —
is correctly identified by D.3 itself; IT.2 must pin that a structural regeneration refusing to
also carry numeric drift (condition C3).

### (3) The 9.4e-8 figure — keep as contract, but the fiction must be corrected. This is a condition, not a preference

Five charter documents say "the **injected** rounding bug that **appears at** ~9.4e-8" — language
asserting a historical event that never occurred. Verified: the figure's first appearance in this
repository's entire history is the Mission 5 charter commit. This project's documented culture
treats unverified provenance claims in docs as defects of the fabrication class — see the M21
guardian record in `src/core/README.md` ("a provenance stamp that names the wrong tree is the
defect this file documents, applied to itself") and the Mission 4 doc-audit record in `README.md`'s
reconciliation stamp. An acceptance criterion resting on a number presented as a measurement when
it is not one is exactly veto trigger territory, *left uncorrected*.

D.3's disposition is the honest one: the figure is arithmetically self-consistent (any value in
(1e-9, 1e-6) satisfies the criterion), and the defect class it stands for is real and reproducible
— I reproduced `round(payment, 4)` → 1.1325e-7 myself, same order of magnitude, invisible at 1e-6,
unmissable at 1e-9. **Ruling: keep 9.4e-8 as the contract constant** (renumbering five documents to
1.133e-7 churns more than it buys and nothing depends on the exact value), **on condition C4**: the
"injected bug" fiction is corrected in the charter documents, the manual test is fixed before IT.2,
and the calibration test's own docstring records in-repo that 9.4e-8 is a contract figure bound to
the reproducible recipe, not a measurement. Estimates labeled as estimates, with the assumption
visible — the project's own rule, applied to its own planning documents.

### (4) Approaching-tolerance: fail-closed is correct; the ledger is a genuine control with one hole, now closed

Fail-vs-warn: this codebase has already ruled on warnings nobody sees — Gate 3 blocked a scenario
feature partly because its own disclaimer "never reached the rendered page" (`src/core/README.md`).
A pytest warning is that same failure. Fail-closed with a committed, reviewed escape hatch is the
right call, and it is what the charter's "written justification, not a green tick" actually
requires once you take "not a green tick" seriously.

The ledger's two properties — scoped to `(case, field)` and bounded by `max_rel` so it cannot cover
later, larger drift; self-expiring so stale entries fail — are precisely what distinguish a ledger
from a suppression list with better manners. **The one hole:** nothing in D.3 stops an entry being
written with `max_rel` generously above the measured drift (measured 6.1e-10, recorded 9.9e-10),
pre-authorizing future growth — a mini-ratchet inside the anti-ratchet. Condition C5 closes it: the
harness must reject over-provisioned entries. With that, I rule the ledger a genuine control.

### (5) Scope — the boundary is drawn in exactly the right place

Confirmed line-by-line against the harness file:
- **Relax:** `:181` and `:217` only, renamed so "bit_exact" no longer appears in the name of a test
  that is not (a test name is a claim; false claims in names are still false claims).
- **Stays `==`:** `:191` — I affirm D.3's §6.2 in the strongest terms: this test detects hidden
  nondeterminism, which manifests as tiny differences; a tolerance here would delete the harness's
  enforcement of the actual invariant while looking like consistency. It is the reason ruling (1)
  is possible at all.
- **Stays as-is:** `:225` (human-verified display-precision numbers — already ~5.6e-5 relative;
  the tolerance rule is meaningless there), `test_metrics_parity.py` and
  `test_engine_bitexact_refactors.py` (intra-version equivalences and algebraic identities — a
  tolerance request against either is an AD design defect, ruled stop-and-consult below).
- Nothing swept in: blast radius verified by D.3 (three files reference the golden), and the design
  touches no `src/` code, no schema, no dependency — `src/schemas/README.md` correctly untouched.

One addition (condition C7): the harness module docstring's "BIT-EXACT, NOT APPROXIMATE" section
(`:10-20`) becomes false the day the tolerance ships and must be rewritten with a dated TOLERANCE
RULE record block in the existing regeneration-record format. This project's reconciliation-stamp
culture does not tolerate a module docstring that misdescribes its own tests.

### (6) The dollar concession — acceptable, with the unacceptability boundary stated

$0.213 on a $213M *synthetic, never-rendered* matrix value; $0.00053 on the largest field of the
deal this product actually ships. The tolerance's blindness on the shipped deal is one order below
the finest display quantum (half a cent), and on every guardrail-read rate it is ≤3.1e-8 absolute —
four orders below the fourth-decimal precision the human-verified baseline asserts and reports
render. No decision-bearing or rendered surface can perceive it. **Acceptable.**

**What would make it unacceptable, stated as a rule:** the tolerance becomes unacceptable the day
`REL_TOL × |field|` reaches half the display quantum of a rendered, decision-bearing surface, or
the day a guardrail comparison could flip within tolerance. Concretely: cent-rendered money fields
above ~$5M property scale (1e-9 × $5e6 = $0.005), or any widening of `REL_TOL` itself. IT.2's Test
D suite must pin the first as an executable assertion over the shipped-deal golden (condition C6),
so growth of the product into a scale where the blindness bites turns the justification RED instead
of leaving it stale prose.

---

## Answers to D.3's five open questions (§8)

1. **§1.2 — is the blindness acceptable?** Yes — ruling (6) above, with the unacceptability
   boundary made executable (C6).
2. **§3.5 — cumulative-drift budget?** **Adopt. Mandatory, not SHOULD** (C2). It is the only
   element of the anchor design that does not decay under deadline pressure, and it is the direct
   answer to the charter's own stated fear. Budget exhaustion means independent human
   re-verification, never a budget raise — write that sentence into the failure message.
3. **§5.1 — 9.4e-8 disposition?** Keep as the contract figure bound to the `round(payment, 4)`
   recipe; do not substitute 1.133e-7. Conditional on the corrections in C4. An unsourced number
   presented as a measurement is a values breach; the same number presented as a labeled contract
   bound to a reproducible recipe is not.
4. **§5.4 — who owns the manual-test correction?** The orchestrator (it owns the document), before
   IT.2 writes the calibration test. **And the correction is larger than D.3 flagged:** Case 1
   step 2 (`MISSION_5_MANUAL_TESTING.md:93`) perturbs a golden number too, and has the same
   anchor-mutation defect as step 1. Both steps move to computed-side perturbation (C4a).
5. **§6.2 — parity and refactor suites?** Confirmed: `test_metrics_parity.py` and
   `test_engine_bitexact_refactors.py` stay bit-exact. **Ruled formally: an AD implementation that
   cannot keep them green is a stop-and-consult-the-Founder-Proxy event, not a tolerance request.**
   A request to relax either file is an automatic escalation, and this memo is the citation.

---

## CONDITIONS (each becomes a tracker row; each is checkable)

- **C1 — Determinism boundary frozen.** `test_determinism_repeated_calls_are_identical` (`:191`),
  `test_sample_deal_verified_baseline_numbers` (`:225`), `test_metrics_parity.py`, and
  `test_engine_bitexact_refactors.py` ship with **no assertion changes**. The `:191` docstring
  hardening (why it is excluded from the tolerance rule) is **required**, not optional. Any future
  request to relax any of these four is an escalation to the Founder Proxy, citing this memo.
  *Check: diff of Impl-T touches no assertion in those tests; `:191` docstring contains the
  exclusion statement.*
- **C2 — Adopt §3.5, mandatory.** `ANCHOR.json` records carry `max_rel_drift_vs_previous_anchor`;
  `test_golden_anchor.py` walks the `supersedes` chain and fails when cumulative drift from the
  first anchor exceeds 1e-8; the failure message states that the remedy is independent human
  re-verification, never a budget raise. *Check: test exists, chain-walk asserted, message text.*
- **C3 — Supersession discipline.** `--supersede-anchor` requires `--rationale`; every supersession
  also requires a dated record block in the harness docstring (existing regeneration-record format)
  and an `approved_by` naming the founder. A structural regeneration (case/field added or removed)
  must refuse to also carry numeric drift without `--supersede-anchor` — IT.2 pins this path.
  *Check: generator refusal test + the structural-plus-numeric RED test exist.*
- **C4 — Calibration honesty.** (a) `MISSION_5_MANUAL_TESTING.md` Case 1 **steps 1 AND 2**
  corrected to computed-side perturbation (D.3 §5.3 recipes) **before IT.2 writes the calibration
  test**; (b) the "injected rounding bug that appears at ~9.4e-8" language in
  `MISSION_5_adjoint_differentiation.md`, `MISSION_5_HANDOFF.md`, `MISSION_5_SPRINT_TRACKER.md`,
  and `ROADMAP_TRACKER.md` corrected **before Gate V** to state it is a contract calibration
  constant with no pre-Mission-5 measurement behind it; (c) the calibration test's docstring
  records the contract status and the reproducible recipe (`round(payment, 4)` → measured
  1.133e-7). *Check: grep the five documents for the corrected language; read the test docstring.*
- **C5 — Ledger anti-over-provisioning.** The harness rejects a `DRIFT_LEDGER.json` entry whose
  `max_rel` exceeds the currently-measured drift by more than 10%, and rejects any entry with
  `max_rel >= REL_TOL`. Stale entries (drift below the band floor) fail as designed. *Check: three
  RED tests — over-provisioned entry, out-of-range entry, stale entry.*
- **C6 — Walls and boundary live in-repo.** IT.2's Test D re-derives the noise floor (~1.15e-13)
  and the defect signature (~1.35e-5) in the suite, and additionally asserts
  `REL_TOL × max(|shipped-deal golden field|) < 0.005` (half a display cent), so the tolerance's
  justification and its dollar-blindness boundary turn RED if the engine, the constant, or the
  product's scale moves. The §6.3 prohibitions (no `abs_tol`, no per-field override mechanism, no
  runtime/env/CLI configurability of `REL_TOL`) are stated in `golden_tolerance.py`'s module
  docstring. *Check: assertions present; docstring present.*
- **C7 — Harness docstring truth.** The module docstring's "BIT-EXACT, NOT APPROXIMATE" section is
  rewritten with a dated "TOLERANCE RULE — Mission 5" record block in the existing format, and the
  two relaxed tests are renamed (`within_tolerance`, per D.3 §6.1). *Check: read the docstring and
  test names.*

**PATH FORWARD:** Impl-T proceeds against D.3 as written, plus C1–C7. AD-sub-wave remains gated on
the tolerance harness being shipped and green, per the charter.

**EVIDENCE OF READING:**
- `D3_tolerance_rule.md` — comparison rule, anchor, band, calibration, scope; §8's five questions answered above.
- `test_golden_forecasts.py:17-20` — "named, justified tolerance" — the harness's own escape clause, the decisive text for ruling (1).
- `generate_golden_forecasts.py:5-13` — "a diff here is a FINDING, not a chore" — the refusal gate extends this, it does not contradict it.
- `finance_engine_forecasts.json` — flattened programmatically: 11,360 float fields, baseline bit-identical to the current engine.
- `amortization.py:93-96` — the seam and the `max(0.0, pay - interest)` cancellation behind the ~143x amplification, confirmed first-hand.
- `src/core/README.md` — "Determinism first"; the Gate 3 disclaimer-never-rendered record grounding ruling (4); M21 grounding ruling (3).
- `README.md:11` — "fully deterministic and reproducible" — satisfied at every rendered precision under the rule.
- `src/schemas/README.md` — deterministic serialization; no schema surface touched by this design.
- `CONTRIBUTING.md` — tests must pass; no bearing beyond that.
- `MISSION_5_adjoint_differentiation.md:132-143` — the chartered contract this design implements, including Roger's in-principle approval of the relaxation.
- `MISSION_5_MANUAL_TESTING.md:76-101` — both steps of Case 1 perturb a golden number; both corrected under C4a.
- Project memory — direct-to-main, founder holds all gates: the workflow the anchor ceremony is designed for.

— Principles Guardian, Gate D, 2026-08-31
