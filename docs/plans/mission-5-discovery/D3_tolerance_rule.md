# D.3 — The Tolerance Rule: relaxing the golden invariant from bit-exact to 1e-9 relative

**Mission 5, Discovery wave · task D.3 · `staff-python-engineer` (routed opus)**
**Baseline:** branch `mission/5-adjoint-differentiation` @ `87efd22`
**Status:** DESIGN ONLY — no production code, no tests written. Reviewed by the
**principles guardian under VETO authority at Gate D.**
**Scope note:** D.1 owns the AD math and the Jacobian API; D.2 owns perf measurement. This memo
owns the tolerance rule and nothing else.

---

## 0. TL;DR for the reviewer

| Question | Answer |
|---|---|
| Comparison rule | `abs(actual - expected) <= 1e-9 * abs(expected)`, asymmetric (expected in the denominator), **`abs_tol = 0`**, `expected == 0.0` requires `actual == 0.0` exactly, non-float fields stay `==`. |
| Uniform or per-field? | **Uniform. No per-field exceptions, including `irr_10yr`.** Measured, not assumed. |
| Why 1e-9 and not another number | It is the geometric midpoint (to within 25%) of a **measured** empty band: FP-reordering noise floor **1.15e-13**, calibration defect **1.35e-5**. |
| Structural anchor | **Digest pin on the `cases` subtree** + a committed `ANCHOR.json` provenance record + a generator that **refuses to write on drift-only changes**. |
| 9.4e-8 calibration figure | **NOT CONFIRMED as a historical artifact.** It appears for the first time in the Mission 5 charter commit itself. It *is* arithmetically consistent and *is* representative of a real, reproducible defect class in this repo. Details and a real recipe in §5. |
| Approaching-tolerance | Band `[5e-10, 1e-9)` = **50% of tolerance**. **FAILS the build**, convertible to PASS by a committed, scoped, self-expiring ledger entry. Not a warning. |
| Relax | `test_forecast_matches_golden_bit_exact` (`:181`), `test_sample_deal_matches_golden_bit_exact` (`:217`). |
| Stay bit-exact | `test_determinism_repeated_calls_are_identical` (`:191`), `test_sample_deal_verified_baseline_numbers` (`:225`), all of `test_metrics_parity.py`, all of `test_engine_bitexact_refactors.py`. |
| Blocking conflict found | `docs/manual testing/MISSION_5_MANUAL_TESTING.md:91` prescribes a calibration procedure that **mutates the anchor** and therefore cannot produce the failure it asks Roger to observe. Must be corrected before IT.2 and before Gate V. See §5.4. |

---

# PART I — THE VALUES ARGUMENT

The guardian holds VETO here, so this part leads. It gives both sides at full strength.

## 1.1 What is actually being relaxed — and what is not

The deterministic-core invariant, as this project states it, is: **same inputs ⇒ same output.**

That is a property of a **fixed program**. It is enforced today by
`tests/core/finance/test_golden_forecasts.py::test_determinism_repeated_calls_are_identical`
(`:191`) — same inputs, same code, same process, run twice, `==` — and by
`tests/core/finance/test_metrics_parity.py`, which pins the full path against the light path of the
*same code version* on raw IEEE-754 bytes.

**Neither of those tests is touched by this design. Both stay bit-exact.**

The golden harness enforces a different, stronger property that has never been part of the stated
invariant:

> **output of program version _N+1_ is bit-identical to output of program version _N_.**

That is **stability across a code change**, not determinism. The project could afford it — and was
right to take it — for as long as the arithmetic in `src/core/finance/` was frozen. It is a surplus
guarantee, not the invariant. Mission 5 spends part of that surplus, deliberately, at a price this
memo measures rather than asserts.

Conflating the two is the actual error available to a reviewer here, in both directions: a reviewer
who thinks the relaxation touches determinism will veto something that does not exist; a reviewer
who accepts "it's only cross-version" without a measured price will wave through an unbounded
concession. Both are avoidable, because the price is measurable.

## 1.2 The price, measured, in dollars

A 1e-9 relative rule is blind to any change smaller than one part in a billion. Concretely, across
the committed 34-case matrix (11,789 numeric field comparisons):

| | worst-case absolute blindness |
|---|---|
| Largest number in the entire matrix (`units_500_horizon_50::years[49].est_value` = $213,118,291.76) | **$0.213** |
| The **shipped** sample deal (`36_kelly_moncton`), largest field (`years[9].est_value` = $533,347.71) | **$0.00053** |
| Any rate/ratio field (fractions in [0,1]) — worst is `horizon_50::equity_multiple_10yr` = 157.24 | **1.57e-7** (absolute, on a multiple) |
| Any true rate (`cap_rate`, `coc`, `dscr`, `irr_10yr`, `spread_vs_rate`, all ≤ 31.2) | **≤ 3.1e-8** absolute |

**Honest reading:** on a synthetic 500-unit / 50-year portfolio valuation we accept blindness to
21 cents. On the deal this product actually ships, we accept blindness to five hundredths of a
cent. On every rate the guardrails and the thesis read, we accept blindness in the eighth decimal
place of a fraction — four orders below the fourth-decimal precision the human-verified baseline
test (`:225`) asserts and the reports render.

That is the concession. It is stated in the units the founder thinks in, not in epsilons.

## 1.3 Why 1e-9 is not an arbitrary number

The single strongest argument for this design is that **1e-9 was not chosen; it was located**, and
the two measurements that locate it are reproducible in this repo.

I measured both walls of the band, end-to-end through `run_financial_model` across all 34 cases and
all 11,789 numeric fields, by injecting perturbations into `amortization.amortization_payment` — the
most-amplified intermediate in the engine (see §1.4):

| | measured max relative deviation | what it represents |
|---|---|---|
| **Floor** — 1 ULP injected (relative ~1.1e-16) | **1.151e-13** | The largest deviation a *legitimate* floating-point reassociation can produce. AD's dual-number threading is exactly this class. |
| 4 ULP | 1.172e-13 | |
| 16 ULP | 4.604e-13 | |
| **Ceiling** — 9.4e-8 relative injected (the calibration defect) | **1.348e-5** | The smallest defect class the harness is contractually required to catch. |

```
1e-16 ────── 1.15e-13 ──────────── 1e-9 ──────────── 1.35e-5 ────── 1e-3
             FP reordering          THE RULE           calibration
             noise floor                                 defect
                        ← 8,696x →        ← 13,478x →
```

- 1e-9 sits **8,696x above** the measured reordering noise floor. It cannot be tripped by AD's
  arithmetic reordering, with nearly four orders of margin.
- 1e-9 sits **13,478x below** the calibration defect's measured signature. The defect is caught
  with nearly four orders of margin.
- The geometric midpoint of `[1.151e-13, 1.348e-5]` is **1.245e-9**. The proposed constant is
  within 25% of the exact centre of the empty band, biased *tighter*.

**This is the load-bearing fact of the whole design.** 1e-9 is not a taste; it is the middle of a
four-order-wide gap in which nothing this repo produces has ever been measured to live. Anyone
proposing a different constant is obliged to move one of the two walls, by measurement.

Reproduce: `/tmp/.../scratchpad/d3/exp4_inject.py`, `exp5_sweep.py`, `exp6_floor.py` (throwaway;
IT.2 should re-derive both walls as part of the RED suite so the numbers live in the repo, not in a
scratchpad).

## 1.4 One measurement that changes how the rule should be read

Injecting a **1e-9** relative error into the amortization payment produces a **1.434e-7** maximum
relative deviation in the output (`interest_rate_high::years[9].principal_paid`) — a **~143x
amplification**.

The cause is catastrophic cancellation: `principal_pay = max(0.0, pay - interest)`
(`src/core/finance/amortization.py:93`). On `interest_rate_high`, interest is ~99.3% of the payment,
so `principal_paid` is a ~$505 difference of ~$72,500 numbers. `available_equity` (`est_value` minus
balance) cancels similarly.

Two consequences the guardian should weigh:

1. **The field-level rule is far stricter than an input-level rule.** Requiring every *output* field
   to hold 1e-9 implicitly requires the engine's *inputs and intermediates* to hold ~7e-12. The rule
   is conservative by a factor of ~143 relative to the naive reading of "we allow 1e-9 of drift."
2. **The harness's most sensitive detector is a cancellation field**, and it must not be blinded.
   This is the decisive argument against an absolute-tolerance floor (§2.3).

## 1.5 The strongest case AGAINST this design (stated honestly)

A reviewer should have these, not a sales pitch:

1. **The harness acquires a mode.** Pass / approaching / fail. Modes are where controls go to die,
   because the middle mode becomes the default landing zone. Mitigated by making the middle mode
   *fail-closed* (§4) — but the objection is real and the mitigation is the only thing standing
   between this and a warning nobody reads.
2. **$0.21 is not zero.** On the largest matrix case we go blind to a fifth of a dollar. If the
   product ever reports portfolio values at that scale to a user, "a number nobody vouches for" is
   21 cents, not 0. I do not think this is disqualifying — the sample deal's figure is $0.00053 and
   the rendered reports round to the dollar or the fourth decimal of a rate — but I am not going to
   round it away in the memo.
3. **Two things now have to stay in sync** (the golden file and its anchor record). Desync fails
   RED, which is the safe direction, but it is friction and friction gets routed around.
4. **The relaxation is a precedent.** Someone will cite it. §6.3 exists specifically to bound what
   it can be cited for, and that section should be read as part of the ruling, not as an appendix.
5. **The calibration figure has no provenance** (§5). The mission's stated acceptance criterion
   rests on a number that first appears in the mission's own charter. I recommend keeping it, but
   the guardian should know it is a *contract*, not a *measurement*, before ruling.

## 1.6 The case FOR, in one paragraph

AD's output is only reviewable if there is a defined, tight, measured band inside which its
arithmetic reordering is allowed to differ from the current engine. Without that band, every AD
landing is a bit-exact failure that can only be resolved by regenerating the golden — which is the
ratchet, arriving on day one and permanently. The tolerance rule is not a loosening; it is the thing
that lets the golden file **stop moving**. Under this design, in-tolerance drift is never a reason to
regenerate (§3.3), so the anchored numbers become *more* stable, not less.

---

# PART II — THE MECHANISM

## 2. The comparison rule

### 2.1 The predicate

```
REL_TOL = 1e-9      # module constant. Not env-configurable, not CLI-configurable. See §6.3.
WARN_FRACTION = 0.5 # see §4

for each leaf field, by path, after a structural check:
    non-numeric (str, NoneType, bool)         -> actual == expected           (exact)
    int          (years[*].year, refi.year)   -> actual == expected           (exact)
    float, expected == 0.0                    -> actual == 0.0                (exact)
    float, expected != 0.0                    -> abs(actual - expected) <= REL_TOL * abs(expected)
```

### 2.2 Why this formula and not `math.isclose`

Use the **explicit asymmetric** form, not `math.isclose(a, b, rel_tol=1e-9)`.

`math.isclose` scales by `max(abs(a), abs(b))` — the *symmetric* form. That makes the pass/fail
predicate depend on the value under test. For a golden harness that is the wrong dependency: **the
anchored value is the authority, and the authority belongs in the denominator alone.** The
practical difference is tiny (isclose is very slightly more permissive when `|actual| > |expected|`),
but the conceptual difference is the whole point of an anchor — a rule whose scale is set partly by
the thing being judged is not an anchor. The explicit form also makes the intent readable in the
failure message ("46% of tolerance"), which `isclose` cannot express.

`<=` not `<`: a deviation of exactly `1e-9 * |expected|` passes. Stated so the boundary is not
folklore.

### 2.3 `abs_tol` = 0. There is no absolute floor. Ever.

This is the sharpest call in the design and I want it argued, not assumed.

**The case for a nonzero `abs_tol`:** fields that are legitimately small differences of large
numbers get a punishing absolute budget. `interest_rate_high::years[0].principal_paid` = $505.72
gets a budget of 5.06e-7 dollars. That looks unreasonable.

**Why it is nevertheless correct, by measurement:** the measured noise floor *at that exact field*
is 1.151e-13 relative = **5.8e-11 dollars** — four orders of margin inside its own budget. The
tight budget is not a false-positive risk; it is the harness's single most sensitive detector, and
it is sensitive precisely because cancellation amplifies upstream error by ~143x (§1.4). An
`abs_tol` of even 1e-6 would set that detector's threshold at ~2e-9 relative — blinding the one
field most likely to see a defect first.

**And the structural argument:** an `abs_tol` is how a relative rule quietly becomes a blanket rule.
It is a second constant with a second justification, applied to fields nobody enumerated, and its
effect grows as values shrink — i.e. it is largest exactly where the numbers are most delicate. One
constant, one derivation.

### 2.4 Exact zeros: `expected == 0.0` requires `actual == 0.0`

The golden matrix contains **652 exact-zero numeric entries across 20 distinct field paths**:

```
years[*].principal_paid 65 · years[*].ltv_pct 63 · years[*].interest_paid 60
years[*].ending_balance 53 · years[*].debt_service 50 · years[*].dscr 50
years[*].{hoa_fees, landscaping, other_expenses, property_management,
          repairs_maintenance, reserves, snow_removal, trash, utilities} 30 each
years[*].available_equity 28 · years[*].est_value 10
irr_10yr 1 · purchase.annual_debt_service 1 · purchase.dscr 1
```

**These zeros are semantic, not numeric.** They mean: the loan is retired
(`schedule_columns` clamps `bal = 0.0` when `bal < _EPS`, `amortization.py:98`); this expense is
absent from the model; there is no debt, so there is no debt service and no DSCR. They are not the
residue of cancellation, so demanding exactness costs nothing.

**And it catches real defects.** Two of my injection experiments flipped `ending_balance` from an
anchored `0.0` to `6.31` (float32 round-trip of the payment) and to `1.27e-4` (payment truncated to
10 significant digits) — i.e. "the loan is paid off" silently became "the loan is not paid off."
Under a relative rule with no `abs_tol`, `expected == 0` has no defined relative denominator; the
only two coherent options are *require exact zero* or *fall back to `abs_tol`*. The first catches
both of those defects. The second, at any `abs_tol >= 1e-3`, misses one of them.

Related decisions:
- **Signed zero:** `-0.0 == 0.0` is `True` in Python and this rule accepts it. Verified: the
  committed golden contains **zero** negative zeros, so this is currently vacuous. Accepted
  deliberately — the sign of zero is not a money fact. (Note that `test_metrics_parity.py` *does*
  distinguish them, via `struct.pack`; that test is unaffected and stays.)
- **`actual == 0.0` where `expected != 0.0`:** relative deviation is 1.0, i.e. a hard FAIL. Correct.
- **NaN / inf:** `model_dump(mode="json")` on a NaN would already be a schema-level problem. The
  predicate fails closed (`abs(nan - x) <= t` is `False`), which is the right direction. IT.2 should
  pin this with a case.

### 2.5 Non-float fields — census, verified against the committed artifact

Do not assume every golden field is a float. Measured over all 34 cases:

| path | type | count | rule |
|---|---|---|---|
| `years[*].year` | `int` | 426 | exact `==` — a counter, not a measurement |
| `refi.year` | `int` | 3 | exact `==` — same |
| `warnings[*]` | `str` | 40 | exact `==`, **order-sensitive list equality** |
| `years[*].notes[*]` | `str` | 4 | exact `==`, order-sensitive |
| `refi` | `None` | 31 of 34 | exact — `None` vs object is a structural difference |
| everything else (**38** distinct paths) | `float` | 11,360 | the relative rule |

Two traps to call out for the implementer:

1. **`isinstance(True, int)` is `True` in Python.** The type dispatch must test `bool` *before*
   `int`/`float` or a future boolean field silently enters the numeric path. No bools exist in
   `FinancialForecast` today; the guard is one line and prevents a silent future hole.
2. **The `warnings` list is a load-bearing bit-exact assertion.** The second Mission 4 regeneration
   (harness docstring `:89-133`) existed *solely* to add one warning string to `units_1_horizon_10`.
   Warnings are the visible surface of the IRR-undefined ruling. They get no tolerance, no
   set-comparison, no ordering slack.

### 2.6 Structural checks come first

Before any numeric comparison: identical key sets at every level, identical list lengths
(`len(years)`, `len(warnings)`, `len(notes)`), identical leaf types. A missing field, an extra
field, a short `years` list, or a `float` where an `int` was anchored is a FAIL with a structural
message — never a numeric one. `test_golden_file_covers_every_defined_case` (`:176`) already covers
the case-set level and is unchanged.

### 2.7 Uniform, not per-field — and specifically **no exception for `irr_10yr`**

**Position: one constant, applied to every float field, with no per-field or per-case override
mechanism in the harness at all.**

Against the actual value ranges: the committed golden spans **0.0027**
(`purchase.cap_rate` min non-zero) to **2.13e8** (`est_value` max) — eleven orders of magnitude
across 38 distinct float field paths. A relative rule is the only scale-free rule over that span.
A per-field *absolute* rule would need 38 hand-maintained constants: a config knob nobody turns, and a YAGNI
violation on its face.

The one field with a *plausible* claim to a looser tolerance is **`irr_10yr`** — the only
iteratively-solved field in `FinancialForecast` (`engine.py:589`, via `irr.py::_brent_root`, whose
stopping criterion is `tol1 = 2*eps*|b| + 0.5*tol` with `tol = 1e-6`, `irr.py:143`). A reviewer will
reasonably ask: *if the solver only promises ±5e-7 absolute, how can its output be pinned to 1e-9
relative?*

**Measured, and the exception is not needed.** Perturbing one cashflow at a time by relative deltas
from 1e-16 to 1e-6 and measuring the response of the returned root:

| case | amplification (Δrel irr / Δrel cashflow) |
|---|---|
| `sample_deal_36_kelly_moncton` | 0.72x |
| `all_cash_deal` | 2.32x |
| `vacancy_high` | 0.21x |
| `horizon_30` | 0.96x |
| `negative_cash_flow_decline_shaped` | 1.02x |

Two findings:
- The condition number is **O(1)** (0.2x–2.3x). The Brent solve does not amplify.
- The response is **perfectly linear across ten orders of magnitude** — there is **no iteration-path
  discontinuity** in this regime. The `tol = 1e-6` stopping criterion bounds the distance from the
  *true* root; it does not make the *returned* root a step function of the inputs. The returned root
  is a smooth, well-conditioned function of the cashflows.

So `irr_10yr` needs no special treatment. This is the most important measurement in the memo
because it is the obvious place a careful reviewer would demand an exception, and the data says no.

**Residual risk, stated:** worst measured amplification is 2.3x. If the primal ever drifts *at* the
1e-9 ceiling, `irr_10yr` could show ~2.3e-9 and fail. That is not a reason to loosen `irr_10yr`; it
is the harness correctly reporting that a 1e-9 primal drift is not acceptable. Real AD-induced
primal drift is expected at ~1e-13 (§1.3), where 2.3x is irrelevant.

**And the structural argument against per-field tolerance:** a per-field override table *is* a
per-field ratchet. The moment the harness can express "this one field gets 1e-7," every future drift
finds a field-shaped hole to hide in, and the anti-ratchet work in §3 is defeated at a different
level. Do not build the mechanism.

---

## 3. THE ANCHOR — making "compare to the original" structural

### 3.1 What "the ORIGINAL golden" identifies — verified against git, not assumed

The charter says "anchor to the ORIGINAL golden, never the previous version," and the harness
docstring documents **two** regenerations (`:36-119`). The obvious worry is: *original meaning
which of three states?*

**Verified at this baseline — the question does not arise, and this is a genuinely useful finding:**

```
$ git log --oneline -- tests/data/golden/finance_engine_forecasts.json
912a55f feat(recourse): actionable recourse ... plus the engine work it forced
```

Both Mission 4 regenerations happened *inside* Mission 4's development and were **squashed into the
single commit `912a55f`**. The repository therefore contains **exactly one committed version** of
this artifact:

```
git blob : c2051c5de5b1ba9d1c1b36a5defc40207ef26627
sha256   : 936734c627f16d888b5033e7f9564c198d36bcbbb5367b296f35c13a4d4fa5cc
at commit: 87efd22 (Mission 5 baseline)
```

**The anchor is that artifact.** Not a compromise: both prior regenerations were founder-approved
*corrections* (Newton→Brent solver correctness; IRR-undefined visibility), each accompanied by a
field-by-field before/after record. Anchoring to a pre-correction state would anchor to numbers the
project has explicitly ruled wrong. The correct anchor is *the most recent state a human
independently vouched for* — and Mission 4's Gate V is that vouching event.

**This also kills one of the candidate mechanisms outright** (§3.2, option D): there is nothing
earlier in git history to reach back to.

### 3.2 Candidate mechanisms — considered and disposed

**A. A comment saying "always compare to the original." REJECTED.**
This is the convention the router escalated this row to prevent. It rots on first contact with a
tired engineer at 6pm, and it leaves no artifact in a diff.

**B. A separate immutable anchor file (`finance_engine_forecasts.ANCHOR.json`) alongside a live
golden. REJECTED.**
Costs 528 KB of duplication, but the fatal objection is conceptual: **if the comparison is always
against the anchor, the "live" golden has no job.** A file with no job becomes the file people edit,
and the two silently diverge into "the one the tests use" and "the one people look at." Two copies
of a truth is the exact failure shape this codebase has already ruled on twice (see the
`spread_target_for` / cap-floor comment blocks cited in `test_metrics_parity.py`'s docstring). Do
not introduce a second copy of the numbers.

**C. A committed digest + provenance record, enforced by a test. ADOPTED.** See §3.3.

**D. Git-history-based verification (`git cat-file` the blob at a pinned commit). REJECTED, twice
over.**
(i) Tests must not shell out to `git`: CI does shallow clones, source tarballs have no `.git`, and
it introduces an environment dependency into a test path this project keeps pure. (ii) As
established in §3.1, **it would not work anyway** — the pre-regeneration versions do not exist in
this repository's history.

**E. Cumulative-drift accounting across a supersession chain. ADOPTED as a SHOULD (second tooth).**
See §3.5.

### 3.3 The adopted mechanism, concretely

Three parts. Together they remove the ratchet's *gradient*, which is the only thing it can climb.

---

**Part 1 — The anchor record. New file `tests/data/golden/ANCHOR.json`:**

```json
{
  "anchored_artifact": "finance_engine_forecasts.json",
  "cases_sha256": "<sha256 of the canonicalised `cases` subtree>",
  "anchored_at_commit": "87efd22",
  "anchored_on": "2026-08-31",
  "approved_by": "Roger Booto Tokime",
  "rationale": "Mission 5 baseline. The state Mission 4 Gate V vouched for: post-Brent-solver, post-IRR-undefined-warning. See tests/core/finance/test_golden_forecasts.py module docstring, regeneration records at :36 and :89.",
  "max_rel_drift_vs_previous_anchor": null,
  "supersedes": null
}
```

**Part 2 — The digest test. New file `tests/core/finance/test_golden_anchor.py`:**

A single test that recomputes the digest of the golden it just loaded and asserts it equals
`ANCHOR.json::cases_sha256`. It lives in its **own file** so its failure message is unmistakable and
so it fires even if the main harness is deselected or errors during collection.

**Digest the `cases` subtree, not the whole file.** Canonically:

```python
sha256(json.dumps(golden["cases"], sort_keys=True, separators=(",", ":")).encode("utf-8"))
```

Rationale for the cut: the `_meta` banner is prose. Digesting the whole file would mean improving a
sentence in `_meta` requires a re-anchor ceremony — friction on the wrong thing, which teaches people
to route around the ceremony. Digesting `cases` alone means: **prose can change freely; a single
digit in a single number anywhere in any case cannot change without a re-anchor.** That is exactly
the right boundary. (Accepted cost: the `_meta` prose can drift from truth without a test firing.
Prose is not the anchor; the docstring regeneration records are the narrative of record.)

**Part 3 — The generator refuses drift-only regeneration.**
`tests/core/finance/generate_golden_forecasts.py` gains a *safety* gate (not a convenience flag —
its docstring's "intentionally has no CLI flags" is about not allowing partial regeneration, and
this does not violate that). Run bare, it now:

1. computes the full matrix;
2. diffs it against the currently-anchored golden;
3. if the difference is **structural** (a case added/removed in `golden_cases.py`, a schema field
   added/removed) → proceeds, because a numeric anchor cannot exist for a field that did not exist;
4. if the difference is **numeric only** → **refuses to write**, prints the per-case/per-field
   drift table, and exits non-zero with:

   > `REFUSING TO REGENERATE. Every difference here is numeric and within/near tolerance. In-tolerance drift is NEVER a reason to re-anchor — that is the ratchet this harness exists to prevent. If a number genuinely changed for a reason, that reason is a correctness decision: re-run with --supersede-anchor --rationale "<why>" and expect it to be reviewed as one.`

5. `--supersede-anchor --rationale "<text>"` writes the golden **and** rewrites `ANCHOR.json` with a
   new record chaining `supersedes` to the previous digest and recording the measured
   `max_rel_drift_vs_previous_anchor`.

### 3.4 Why this is structural rather than conventional — the argument in its sharpest form

You **cannot** make re-anchoring impossible in a repository where the golden must sometimes
legitimately move. Mission 4 moved it twice, correctly. Any design claiming impossibility is either
lying or is going to be circumvented the first time it is right to move.

**The ratchet is not caused by re-anchoring. It is caused by re-anchoring being cheaper for small
drifts than for large ones.** That price gradient is the slope the ratchet climbs. Remove the
gradient and there is nothing to climb:

- **The digest pin makes every re-anchor cost the same** — a founder-visible, digest-changing,
  record-appending commit — *regardless of whether the drift was 1e-12 or 1e-3*. Ten successive
  1e-9 re-anchors now cost ten founder approvals, which is exactly ten times as loud as one, instead
  of ten silent green ticks.
- **The generator refusal removes the cheapest path entirely**: drift alone can no longer *trigger*
  a regeneration. The response to in-tolerance drift is "nothing happens, the file does not move."
- **`--supersede-anchor` is greppable.** `git log -S'--supersede-anchor'` enumerates every
  re-anchoring in the project's history in one command, forever. A convention leaves no such trace.

Cost of the mechanism: one ~15-line JSON file, one ~30-line test file, ~60 lines added to the
generator. No production code. No new dependency.

Failure modes, stated:
- **Legitimate schema change (Mission 5 or later adds a field to `FinancialForecast`).** The
  structural branch handles it — no numeric anchor exists for a new field. Correct behaviour, but
  note it is the one path where the digest changes without a numeric review. IT.2 should pin that
  the structural branch cannot also carry a numeric change (i.e. adding a field and moving a number
  in the same run must still require `--supersede-anchor`).
- **Someone edits `ANCHOR.json` to match a hand-edited golden.** Not preventable by any in-repo
  mechanism, and neither is `git push --force`. It is now a two-file, self-incriminating diff whose
  only purpose is to be reviewed. That is the achievable bar.
- **Digest brittleness to JSON formatting.** Mitigated by canonicalising (`sort_keys=True`,
  `separators=(",", ":")`) rather than digesting raw bytes, so re-indentation is not a false alarm
  while any numeric change still is.
- **Merge conflicts in `ANCHOR.json`** across concurrent branches. Real but small; the file is 8
  lines and conflicts are the correct signal that two branches both moved the numbers.

### 3.5 The optional second tooth: cumulative-drift accounting

The mission's stated fear is *"ten missions of 1e-9 drift compound into a number nobody vouches
for."* §3.3 makes each hop loud, but nothing yet makes the **sum** visible.

**SHOULD (recommend adopting; guardian may take §3.3 alone):** each `ANCHOR.json` record carries
`max_rel_drift_vs_previous_anchor`, and `test_golden_anchor.py` walks the `supersedes` chain,
composes the recorded per-hop drifts, and **fails** if cumulative drift from the *first* anchor
exceeds a budget of **1e-8** (10 hops at full tolerance).

What that failure means, and this is the point: it does **not** mean "raise the budget." It means
**the numbers must be re-verified independently rather than re-generated** — a human re-derivation
in the spirit of `test_sample_deal_verified_baseline_numbers` (`:225`), which is the only thing that
can restore a claim to vouched-for status. The budget exhausting is the mechanism *working*.

Cost: ~25 more lines of test and one more field per record. Objection to note honestly: composing
*max* per-field drifts across hops is a loose upper bound, not a true error propagation (different
hops may move different fields). It is deliberately conservative and I would rather it be
conservative than clever.

---

## 4. The approaching-tolerance state

### 4.1 The band: `[5e-10, 1e-9)` — 50% of tolerance

**Threshold = 0.5 × `REL_TOL`.** The fraction is derived, not chosen by taste:

- **50% is the fraction at which "one more change of the same size would breach" is literally
  true.** That is a mechanically meaningful definition of "approaching" — and it is precisely the
  anti-ratchet statement expressed at the per-comparison level, mirroring §3. 10% or 25% have no
  such derivation; they are round numbers.
- It is **~4,300x above the measured reordering noise floor** (5e-10 / 1.151e-13), so the band
  **cannot** fire on legitimate floating-point reassociation. Anything reaching it is a change in
  the arithmetic, not a change in the order of the arithmetic.
- It catches the brief's own worked example: a comparison passing at 8e-10 is ≥ 5e-10 and therefore
  fires. The design agrees with the intent that motivated it.

### 4.2 It FAILS the build. It is not a warning.

**Position: fail-closed, with a reviewed escape hatch.**

The argument against warning is the brief's own and it is correct: `pytest -q` output scrolls past,
CI renders a green check, and a green check is what humans read. A warning that changes nothing
observable is not a control; it is a comment with a runtime cost.

The argument against *unconditional* hard failure is also correct: a build that cannot be made green
except by making the drift go away is unshippable, because sometimes the drift is legitimate and
irreducible (AD reordering that lands at 6e-10 on one cancellation field, say).

**Both are answered by making the escape hatch a committed artifact rather than an option flag.**
The developer is never *blocked*; they are *required to write down why*, in a file a reviewer sees in
the diff. Enforced justification, not requested justification. That is exactly what the charter asks
for ("a recorded note, in-repo, like the existing regeneration records"), with teeth.

### 4.3 Where the justification lives: `tests/data/golden/DRIFT_LEDGER.json`

```json
{
  "_doc": "Entries here convert an APPROACHING-TOLERANCE comparison from FAIL to PASS. Each entry is scoped to one (case, field) and to the drift measured when it was written. If the drift grows, the entry stops covering it. If the drift disappears, the entry becomes stale and the suite fails until it is removed. This file is not a suppression list; it is a ledger of accepted, explained, bounded drift.",
  "entries": [
    {
      "case": "interest_rate_high",
      "field": "years[6].principal_paid",
      "max_rel": 6.1e-10,
      "reason": "AD dual-number threading reassociates `pay - interest` in a cancellation-dominated field (interest is 99.3% of payment here); the primal drift upstream is 4e-12 and is amplified ~143x by the cancellation. Confirmed against an independent re-run: see <test/commit>.",
      "mission": "5",
      "date": "2026-09-XX"
    }
  ]
}
```

Two properties make it a ledger rather than a suppression file:

- **Scoped and bounded.** Keyed by `(case, field)` and carrying `max_rel` as measured at the time of
  writing. If a later change pushes that field from 6.1e-10 to 7.4e-10, the entry no longer covers
  it and the suite fails again, demanding a fresh justification. **The acknowledgement cannot be
  reused to cover a later, larger drift** — this is the anti-ratchet operating at the field level,
  composing with the anchor mechanism at the file level.
- **Self-expiring.** If the drift disappears (someone fixes the reordering, or the field is
  reworked), the entry becomes stale and **that is also a failure** — "ledger entry for X no longer
  applies; remove it." The ledger cannot silently accumulate dead suppressions, which is how every
  suppression file in every project eventually dies.

**Why a machine-checked JSON and not a docstring record.** The existing precedent — the regeneration
records in the harness docstring (`:28-133`) and the `_meta` banner — is prose, and prose is the
right medium for *narrative*. But prose cannot be *scoped* or *expired*, so it cannot carry the two
properties above. Division of labour, matching rather than replacing the existing idiom:

| artifact | purpose | required for |
|---|---|---|
| `DRIFT_LEDGER.json` | enforced, scoped, expiring acceptance of in-band drift | every approaching-tolerance comparison |
| harness module docstring — dated record block | the narrative, the before/after table, the reasoning | every **anchor supersession** only (§3.3) |

### 4.4 What the developer actually sees

The failure message is a design artifact, not an afterthought — it is delivered at the exact moment
the temptation to re-anchor appears, so it is where the invariant gets defended:

```
GOLDEN DRIFT — APPROACHING TOLERANCE (unjustified)

  case:      interest_rate_high
  field:     years[6].principal_paid
  anchored:  1365.224607758384
  computed:  1365.2246077590123
  drift:     4.60e-10 relative  (46% of the 1.00e-09 tolerance)
  band:      [5.00e-10, 1.00e-09) -> written justification required

  This is ~4,000x above the measured floating-point reordering noise floor
  (1.15e-13). It is therefore NOT reordering: something in the arithmetic changed.

  To proceed, add an entry to tests/data/golden/DRIFT_LEDGER.json:
    {"case": "interest_rate_high", "field": "years[6].principal_paid",
     "max_rel": 4.60e-10, "reason": "<why this drift is legitimate>",
     "mission": "5", "date": "2026-09-XX"}

  DO NOT REGENERATE THE GOLDEN. In-tolerance drift is never a reason to re-anchor.
  See docs/plans/mission-5-discovery/D3_tolerance_rule.md §3.
```

A FAIL (`>= 1e-9`) gets the same shape without the ledger instructions, and with:
`EXCEEDS TOLERANCE — this is a finding, not a chore. The number this product ships moved.`

### 4.5 Reporting shape

The comparison helper collects **all** deviations across all 34 cases before failing, and the
session prints one summary table (worst 10 by drift, plus counts by state). A per-case parametrized
failure that stops at the first bad field would hide the shape of the change — and the shape is the
diagnostic. Mission 4's own regeneration records were built by exactly this kind of full flatten-and-
diff, "confirmed programmatically, not eyeballed" (`:80`, `:119`); the harness should produce that
artifact directly instead of requiring someone to write the script again.

---

## 5. The calibration point: the ~9.4e-8 figure

### 5.1 Verdict: NOT CONFIRMED as a historical artifact

I searched all 155 commits reachable in this repository:

```
git grep -n "9\.4e-\|9\.4E-\|9\.40e" $(git rev-list --all) -- '*.py' '*.md'
```

**Every single hit is in commit `87efd22` — the Mission 5 charter commit itself** — across five
documents (`MISSION_5_adjoint_differentiation.md`, `MISSION_5_HANDOFF.md`,
`MISSION_5_SPRINT_TRACKER.md`, `MISSION_5_MANUAL_TESTING.md`, `ROADMAP_TRACKER.md`).

There is **no** Mission 4 test, **no** regeneration record, **no** engine artifact, and **no** golden
diff in this repository that produces 9.4e-8. The phrase "the injected rounding bug" implies a prior
event; **no such event is recorded here.**

I also checked the most likely candidate source, the PV.5 Newton→Brent regeneration table (harness
docstring `:43-78`). Converting its 33 absolute `irr_10yr` moves to relative gives a range of
**1.4e-11 … 3.43e-6** (max on `bad_debt_stress`: 1.95e-7 / 0.0568). **9.4e-8 is not the max, min,
median, or mean of that set, and is not any individual entry.** That table is not the source.

Per the brief: I am saying so plainly rather than papering over it.

### 5.2 What IS confirmed

1. **The claim is arithmetically self-consistent.** `1e-9 < 9.4e-8 < 1e-6`, so "a 1e-9 rule catches
   it; a 1e-6 rule does not" is true by construction for any figure in that interval. Nothing in the
   design depends on the figure being 9.4e-8 rather than, say, 1.1e-7.
2. **The defect class it stands for is real and reproducible in this repo — I reproduced it.**
   `round(payment, 4)` in `amortization.amortization_payment` — an entirely ordinary "someone
   rounded a money figure" bug — produces:

   | injected defect | max rel deviation | fields > 1e-9 | caught at 1e-9? | caught at 1e-6? |
   |---|---|---|---|---|
   | `round(payment, 2)` (to cents) | 1.655e-05 | 2,843 / 11,789 | YES | YES |
   | **`round(payment, 4)`** | **1.133e-07** | **1,613 / 11,789** | **YES** | **NO** |
   | payment → 9 significant digits | 2.023e-07 | 1,899 / 11,789 | YES | NO |
   | float32 round-trip of payment | ∞ (zero violation: `ending_balance` 0.0 → 6.31) | 2,889 / 11,789 | YES | YES |
   | `round(payment, 6)` | 9.790e-10 | 0 / 11,789 | NO (passes; lands in the approaching band) | NO |
   | `round(payment, 8)` | 1.669e-11 | 0 / 11,789 | NO | NO |

   `round(payment, 4)` at **1.13e-7** is the same order of magnitude as 9.4e-8 and behaves exactly as
   the charter's calibration requires: **invisible to a 1e-6 rule, unmissable to a 1e-9 rule.**
   The charter's number is not a measurement, but it is a *faithful proxy* for a defect this
   codebase can actually produce.
3. **The margin is enormous, so the figure's exact value does not matter.** Injecting a 9.4e-8
   relative error directly produces a **1.348e-5** max output deviation (§1.3) — **13,478x** above
   the tolerance. Nothing is marginal here.

**Recommendation:** keep 9.4e-8 as the *contract figure* (it is written into the charter, the
handoff, the tracker, and Roger's manual test, and changing it now costs more than it buys), but
**record in the harness that it is a contract, not a measurement**, so no future agent cites it as
an observed fact. Bind it to the reproducible recipe below so the calibration stops being folklore.

### 5.3 How the RED test should reproduce it — the exact recipe for IT.2

Two complementary tests. **The perturbation is applied to the COMPUTED side, never to the anchored
golden** (§5.4 explains why this is not optional).

**Test A — the calibration bug must be caught (the acceptance criterion).**
- **Perturbation:** monkeypatch `src.core.finance.amortization.amortization_payment` to return
  `original(...) * (1.0 + 9.4e-8)`.
- **Where:** module-attribute patch. `schedule_columns` (`amortization.py:91`) resolves the name
  through module globals at call time, so the patch takes effect without touching production code.
  `restore` in a fixture, per the project's existing provider-restore discipline.
- **Observed deviation:** max relative **1.348e-5**, worst at
  `interest_rate_high::years[0].available_equity`; **2,958 of 11,789** numeric fields exceed 1e-9.
- **Assertion:** the comparison reports **FAIL**, and the message names the case and the field path.
- **Companion assertion (this is what makes it a *calibration*, not just a catch):** the same
  deviation set evaluated at `REL_TOL = 1e-6` produces **zero** FAILs at the *source* magnitude —
  i.e. assert directly that `9.4e-8 > 1e-9` and `9.4e-8 < 1e-6` against the injected constant, so
  the test documents *why* 1e-9 and not 1e-6, rather than merely exercising 1e-9.

**Test B — a legitimate AD-scale drift must pass, and must surface the band.**
- Patch the same seam with `* (1.0 + 1e-11)` → max output deviation ~1.4e-9. *(Note the ~143x
  amplification: this exceeds tolerance. Use a smaller input drift for a clean PASS.)*
- For a clean PASS: inject **1 ULP** (`math.nextafter`) → max deviation **1.151e-13**, zero fields
  above 1e-9, **PASS with no band entries**. This is the AD-realistic case.
- For the **band**: `round(payment, 6)` → max deviation **9.790e-10**. That is 98% of tolerance —
  squarely in `[5e-10, 1e-9)` — and gives IT.2 a real, non-synthetic generator for the
  approaching-tolerance state, including the "fails without a ledger entry, passes with one, fails
  again if the entry's `max_rel` is lowered" trio.

**Test C — the anchor cannot be silently moved.** Write a golden with one digit changed to a temp
copy, point the harness at it, assert `test_golden_anchor` fails with a digest mismatch *before* any
numeric comparison runs.

**Test D — the noise floor and the defect wall are re-derived in-repo**, so the two numbers this
design rests on (1.151e-13 and 1.348e-5) live in the test suite rather than in a Discovery
scratchpad, and a future change to the engine that moves either wall turns the tolerance's
justification RED rather than leaving it stale prose.

### 5.4 BLOCKING CONFLICT between two Mission 5 documents

`docs/manual testing/MISSION_5_MANUAL_TESTING.md:91` currently prescribes:

> "**Perturb one golden number** by ~9.4e-8 relative, re-run the harness → it must **FAIL** with an
> 'exceeds tolerance' message naming the case/field"

**Under this design that procedure cannot produce the observation it asks for.** Perturbing a golden
number mutates the anchored artifact, so `test_golden_anchor.py` fires first with
`ANCHOR DIGEST MISMATCH` — a *different*, structurally-earlier failure. Roger would be looking for
"exceeds tolerance naming the case/field," would see a digest error instead, and the manual test's
stated pass criterion would not be met even though the harness is behaving perfectly.

Worse, the procedure teaches the wrong reflex: editing the golden to test the tolerance is the
first step of the ratchet this mission exists to prevent.

**Required correction (orchestrator to action before IT.2 writes the test and before Gate V):**
Case 1 step 1 must perturb the **computed** side (the monkeypatch recipe in §5.3, Test A), not the
golden file. Suggested replacement wording:

> "Inject a ~9.4e-8 relative error into the engine's amortization payment (`pytest
> tests/core/finance/test_golden_tolerance_calibration.py -k calibration_bug_is_caught -q`) → the
> harness must FAIL with an 'exceeds tolerance' message naming the case and field. The golden file
> is not touched; if you find yourself editing it, stop — that is the ratchet."

Manual-test **Case 2** ("drift cannot ratchet") is unaffected and is well-posed as written.

---

## 6. Scope discipline

### 6.1 What relaxes

| test | line | disposition |
|---|---|---|
| `test_forecast_matches_golden_bit_exact` | `test_golden_forecasts.py:181` | **RELAX.** Rename → `test_forecast_matches_golden_within_tolerance`. This is the comparison AD reorders: computed output of code version N+1 vs an anchored artifact from version N. |
| `test_sample_deal_matches_golden_bit_exact` | `:217` | **RELAX**, identically. Same comparison, narrowed to the shipped deal. Renamed the same way. |

Nothing else in the repository relaxes. Verified blast radius: exactly three files reference
`finance_engine_forecasts` (`test_golden_forecasts.py`, `generate_golden_forecasts.py`,
`golden_cases.py` — the last only in a docstring).

### 6.2 What stays bit-exact, and why

**`test_determinism_repeated_calls_are_identical` (`:191`) — STAYS `==`. This is the one that
matters.**

It compares two runs of the **same code**, on the **same inputs**, in the **same process**.
IEEE-754 arithmetic is deterministic: an identical sequence of operations on identical operands
produces identical results, always. There is **no reordering across this boundary**, so there is
nothing for a tolerance to absorb — and therefore any tolerance here is pure loss.

More sharply: this test exists to detect *hidden nondeterminism* — dict/set iteration order leaking
into a sum, `hash()` randomisation, wall-clock dependence, uninitialised state. Those bugs
characteristically manifest as **tiny** differences. **A 1e-9 tolerance would hide exactly the class
of bug this test exists to find.** Relaxing it would not be a weakening of the harness; it would be
a deletion of the harness's most load-bearing assertion, disguised as consistency.

**This test is the enforcement point for the deterministic-core invariant.** It is what §1.1's
argument rests on. Mission 5 must leave it strictly untouched.

*Recommended (docs-only) hardening:* add a sentence to its docstring stating explicitly that it is
deliberately excluded from the tolerance rule and why — so that a future agent tidying the file for
"consistency" cannot relax it without deleting a written objection. Zero behaviour change. I would
consider this part of the Impl-T deliverable, not optional.

---

**`test_sample_deal_verified_baseline_numbers` (`:225`) — STAYS AS-IS. Do not touch.**

It is not a bit-exact test in the first place: it asserts `round(f.purchase.dscr, 4) == 0.8960`,
`round(f.years[0].cash_flow, 2) == -2946.47`, etc. Those are **human-verified numbers at display
precision** — the layer that catches "the golden file itself captured a wrong number," which no
amount of self-consistency can catch.

At `dscr ≈ 0.896`, four-decimal rounding is a ~5.6e-5 relative assertion — **four to five orders
looser than 1e-9**. Applying the tolerance rule here would be strictly weaker than what it already
asserts, i.e. meaningless. Leave it exactly as it is.

*Noted, out of scope:* `round()` uses banker's rounding, so a value landing exactly on a half could
flip. Not a Mission 5 problem, no evidence it is live, and touching it here would be scope creep.
Recorded for the backlog only.

---

**`tests/core/finance/test_metrics_parity.py` (entire file) — STAYS BIT-FOR-BIT (`struct.pack`).**

It pins `forecast_metrics` (the light path) against `run_financial_model` (the full path) for the
**same code version, in the same process**. Same category as the determinism test: an intra-version
equivalence, not a cross-version one. Its own docstring states the structural argument — one
implementation, `_forecast_core`, with `want_rows` gating a single `list.append` and no arithmetic —
and this file is the executable proof of that claim.

This is directly relevant to AD: if AD threads duals through `_forecast_core`, both entry points
share the change, so parity must still hold **exactly**. **If the AD implementation cannot keep this
file green, that is an AD design defect, not a tolerance question.** I would treat a request to
relax this file as a signal to stop and consult the Founder Proxy.

---

**`tests/core/finance/test_engine_bitexact_refactors.py` (entire file) — STAYS BIT-EXACT.**

It pins the *reasoning* behind each PV.3 optimisation (e.g. "the unrolled `total_opex` chain is
byte-identical to `sum([...])`"), on raw IEEE-754 bytes, over a far wider value range than 34 cases
reach. These are algebraic-identity claims about specific expressions, not cross-version output
comparisons. They remain true or false regardless of the tolerance rule.

**Flagged as an AD interaction for D.1/Impl-AD:** if threading dual numbers through `_year_row`
invalidates one of these claims, that is a **finding requiring the founder** — a documented
equivalence stopped holding — and not something the tolerance rule covers or should be asked to
cover.

---

**`test_golden_file_covers_every_defined_case` (`:176`)** — set equality over case IDs. Unaffected.

### 6.3 What this design does NOT permit

Written so the relaxation cannot be cited later to justify a wider one. Each line is a thing a
future reviewer may point at.

1. **It does not relax determinism.** Same code, same inputs, same process ⇒ **bit-identical**,
   forever. `test_determinism_repeated_calls_are_identical` and `test_metrics_parity.py` are outside
   this rule by construction, not by oversight.
2. **It does not permit any tolerance on non-float fields.** `warnings`, `notes`, `years[*].year`,
   `refi.year`, and `refi` presence are exact, ordered, and structural. The `warnings` list in
   particular is the visible surface of the Mission 4 Gate V ruling.
3. **It does not permit an absolute-tolerance floor, ever.** No `abs_tol`, no "just for the small
   fields." An `abs_tol` is the mechanism by which a relative rule becomes a blanket rule, and it
   would blind the harness's most sensitive detector (§2.3).
4. **It does not permit `expected == 0.0` to be matched by a non-zero value.** 652 anchored zeros
   are semantic facts. Two of my injection experiments defeat a lax zero rule and nothing else.
5. **It does not permit per-field, per-case, or per-mission tolerance overrides.** The harness must
   not contain the *mechanism*, because the mechanism is a per-field ratchet regardless of how it is
   initially populated.
6. **It does not permit the tolerance to be configurable at runtime.** `REL_TOL` is a module
   constant. Not an env var (this project's `AIREAL_*` flags gate *optional features*, never the
   strictness of a correctness check), not a CLI flag, not a pytest option, not a fixture parameter.
   A tolerance you can pass on the command line is a tolerance that will be passed on the command
   line.
7. **It does not permit regenerating the golden because of in-tolerance drift.** The generator
   refuses (§3.3). Regeneration is for *structural* change and *founder-approved correctness*
   change only.
8. **It does not permit widening 1e-9 without redoing the two measurements.** The constant is
   derived from a measured noise floor (1.151e-13) and a measured defect signature (1.348e-5).
   Changing it requires moving one of those walls **by measurement**, in the repo, in a test. "It
   feels tight" is not an argument that can reach this constant.
9. **It does not license tolerance anywhere else in the codebase.** Guardrail thresholds, recourse
   confirm-by-rerun assertions, report rendering, `chief_strategist` comparisons — all unchanged.
   This rule applies to exactly two tests, named in §6.1.
10. **It does not permit the drift ledger to become a suppression list.** Entries are scoped to
    `(case, field)`, bounded by the `max_rel` measured when written, and fail when stale. An entry
    that would need to be broadened is a new decision, not a maintenance edit.
11. **It does not weaken `main.py`'s end-to-end output.** The rendered report's sha256 pin, where the
    project uses one, is unaffected: reports round to the dollar and to four decimals of a rate,
    six-plus orders above this tolerance.

---

## 7. Implementation shape (for the Impl-T wave — NOT built here)

| artifact | path | ~size |
|---|---|---|
| Comparison helper (`REL_TOL`, `WARN_FRACTION`, `Deviation`, `compare_golden`) | `tests/core/finance/golden_tolerance.py` | new, ~120 lines |
| Anchor provenance record | `tests/data/golden/ANCHOR.json` | new, ~10 lines |
| Drift ledger | `tests/data/golden/DRIFT_LEDGER.json` | new, ~5 lines (initially empty) |
| Anchor digest test (+ optional chain/budget check) | `tests/core/finance/test_golden_anchor.py` | new, ~50 lines |
| Harness: two tests re-pointed at the helper; new dated record block in the module docstring; determinism docstring hardened | `tests/core/finance/test_golden_forecasts.py` | edit |
| Generator: drift diff, refusal, `--supersede-anchor` / `--rationale` | `tests/core/finance/generate_golden_forecasts.py` | edit, ~60 lines |
| Calibration RED suite (§5.3 Tests A–D) | `tests/core/finance/test_golden_tolerance_calibration.py` | **IT.2 owns this** |

Notes for the implementer:
- **Test-tree only. No `src/` change. No new dependency.** `hashlib` and `json` are stdlib.
- `mypy.ini` sets `[mypy-tests.*] ignore_errors = True`; write it typed anyway, matching the
  neighbouring files' idiom.
- `ruff.toml` allows long lines in `tests/**`, so the failure-message strings need no contortion.
- The docstring's existing REGENERATION RECORD format (`:28`, `:88`) is the template for the new
  "TOLERANCE RULE — 2026-09-XX, Mission 5" record block. Match it; do not invent a new one.
- **No README under `tests/`** exists to update. `src/schemas/README.md` is untouched — no schema
  change here.

---

## 8. Open questions for the guardian

1. **§1.2 — is $0.213 of blindness on a 500-unit/50-year synthetic acceptable?** ($0.00053 on the
   shipped deal.) This is the concession, in dollars. Everything else follows from it.
2. **§3.5 — adopt the cumulative-drift budget (second tooth), or ship §3.3 alone?** Recommend adopt;
   it is the only part that makes "ten missions of 1e-9" visible as a number.
3. **§5.1 — the 9.4e-8 figure has no pre-Mission-5 provenance.** Recommend keeping it as a contract
   figure bound to the reproducible `round(payment, 4)` recipe, and recording in-repo that it is a
   contract rather than a measurement. Guardian to confirm that is acceptable, or to substitute the
   measured **1.133e-7** figure and have the orchestrator correct the five charter documents.
4. **§5.4 — the manual-test procedure conflict is blocking.** Someone must own the correction to
   `MISSION_5_MANUAL_TESTING.md:91` before IT.2 writes the test.
5. **§6.2 — confirm `test_metrics_parity.py` and `test_engine_bitexact_refactors.py` stay
   bit-exact**, and that an AD implementation which cannot keep them green is a *stop-and-consult*,
   not a tolerance request.
