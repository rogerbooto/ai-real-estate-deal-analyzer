# PD.2 — Half B founder product calls (the combination optimizer)

**Mission 5 · `principal-founder-proxy` speaking for Roger Booto Tokime · routed opus**
**Branch:** `mission/5-adjoint-differentiation` · **Baseline:** `87efd22`
**Date:** 2026-08-31
**Scope:** exactly the six questions in `D4_halfb_design.md` §8. Nothing else. Anything else I
would have liked to rule on is in the backlog at the end, as a backlog row, not a decision.

**Standing founder direction applied (Roger, 2026-08-31):** ship the full Half B scope. Half B is
the mission's centre of gravity and ships regardless of the AD checkpoint outcome. D.4 §7 makes
that structurally true — the winning search consumes no derivatives — so nothing below is
conditioned on Half A.

**Read before deciding:** `D4_halfb_design.md` (in full) · `PD1_product_calls.md` (in full) ·
`src/market/recourse.py:80-143`, `:213-234`, `:237-257`, `:372-407`, `:519-639` ·
`src/market/rejector.py` (in full) · `README.md:267-297`, `:500` ·
`docs/manual testing/MISSION_4_MANUAL_TESTING.md:105-115`.

**Measurements taken for this memo** — I re-derived D.4's two load-bearing numeric claims myself
rather than accept them, in the `airedeal` env at this baseline
(`scratchpad/pd2/verify_r2.py`, `scratchpad/pd2/verify_r3.py`). Results are inline under (1) and
(2). Both reproduce. One of them (2) produced a stronger result than D.4 reported, and it changes
how I justify that call.

---

## (1) R2 — the joint-rejector rule — ADOPT

**DECISION: Adopt R2 as specified in D.4 §3. One `MarketHypothesis` carrying both the
combination's signed `interest_rate_delta` and the engine-computed `cap_rate_delta`, through the
unmodified `reject_unrealistic`. No edit to `src/market/rejector.py`. No new constant.**

### Does it actually unify, or merely re-route? — it unifies, and I checked

The question is fair, because "route an existing function a new input" can be dressed up as
architecture. Here is why it is the real thing.

`_rates_vs_cap_ok` (`rejector.py:7-23`) is a **cross-axis** rule. It was written to judge a
hypothesis in which rates and cap move together or apart. It was even *fixed* in Mission 4 Gate D
because its one-sided form never bounded a rate cut — and the fix comment
(`rejector.py:10-16`) records that recourse had to grow `RATE_MAGNITUDE_THRESHOLD` as a *separate*
100 bps fallback precisely because this rule never flagged anything for recourse.

The reason it never flagged anything is in `_rejector_flagged` (`recourse.py:539-563`): it
populates **exactly one axis per call**. Rate lever → `interest_rate_delta` only. Price/rent/opex
on `spread`/`cap_floor` → `cap_rate_delta` only. So the cross-axis rule has only ever been asked
`|x − 0| ≤ 0.02` — a degenerate one-sided magnitude test, weaker than the magnitude fallback that
sits beside it. A cross rule evaluated against a zero is not a cross rule.

R2 is the first time the module hands that rule the input it was written for. That is unification
in the only sense that counts: **a rule the codebase already owns starts doing the job it was
written to do, and a capability the module was missing — "individually fine, jointly implausible"
— falls out with zero new numbers.** The 200 bps divergence bound, the [3%, 12%] cap band, and the
`+1e-12` comparison discipline are all already in the tree, already reviewed, already tested.

### Verified independently, at this baseline

D.4's worked fixture reproduces exactly (`verify_r2.py`, `82_champlain_dieppe`, h=10):

| | measured |
|---|---|
| baseline cap (engine) = snapshot cap (`_derive_snapshot`) | **6.921934%** |
| combination: rate −90 bps, price −$90,000 (−14.876%) | both strictly inside their own caps (100 bps; 15%) |
| each lever judged alone through the **real production `_judge_plausibility`**, on `dscr` and on `spread` | **plausible=True, reason=None — all four rows** |
| combination's engine-computed cap | 6.9219% → **8.1316%**, `cap_rate_delta = +0.0121` |
| `\|rate_delta − cap_delta\| = \|−0.0090 − 0.0121\|` | **0.0211 > 0.02** → `reject_unrealistic` returns empty → **jointly implausible** |
| does the combination actually close the deal? | **yes** — failing guardrails after the combination: `()` |

So it is not a strawman: this is a combination that genuinely fixes the deal, whose every part is
individually blessed by shipped code, and which a gate-less optimizer would put at the top of the
list. The second variant reproduces too: price −15% + opex −20% with **no rate move** →
`|0 − 0.0202| = 0.0202 > 0.02` → rejected. The joint rule fires with the rate lever untouched.

### Reasoning

- **Source:** `rejector.py:7-23` (the rule and its Mission 4 fix record) · `recourse.py:519-563`
  (the one-axis-per-call limitation) · `D4_halfb_design.md` §3, reproduced above.
- **Aligned with:** reuse-first / no invented thresholds; "assumptions are shown, never hidden";
  seams over surgery (the rejector is not edited).

**Trade-off accepted, in writing:** R2 will reject combinations a human could defend. "I bought at
an 8.1% implied cap in a 6.9% market because I negotiated hard" is a real thing that happens. R2
calls that implausible *when it is asked for alongside a 90 bps rate cut*, because the pair tells
two opposite market stories at once. I accept that. The tool is opinionated; the opinion has to be
visible.

**Binding on implementation — three conditions, because the trade-off above is only acceptable if
the investor can argue with it:**

1. **The reason string names both numbers and the bound.** Not "jointly implausible" — the shape
   D.4 drafted: *"a 90 bps rate cut alongside a price cut that lifts the implied cap rate by 121
   bps moves rates and cap in opposite directions by more than the 200 bps divergence this project
   treats as a realistic market hypothesis."* Every figure in that sentence is one the user can
   check against their own market.
2. **The semantic stretch is documented, not silent.** `cap_rate_delta` in the rejector means "the
   market's cap rate moves"; here it carries "this deal's *implied* cap moves because we cut the
   price." Those are not the same claim. The module already makes this exact stretch today for
   single levers (`recourse.py:551`, and the shipped reason string at `:577-581`), so R2 extends a
   shipped, Gate-D-approved reuse rather than inventing a new one — but the gate's docstring and
   `src/market/README.md` must say so in one sentence. An assumption that is only true because
   nobody wrote it down is a hidden assumption.
3. **The degenerate case is pinned by a test.** When `market.cap_rate_purchase` is overridden the
   implied cap cannot move, so `cap_rate_delta = 0` and R2 collapses to `|rate_delta| ≤ 0.02` —
   weaker than R1's own 100 bps cap, i.e. **inert**. D.4 calls that honest degradation and I agree,
   but "this rule silently does nothing on override deals" is exactly the kind of fact that rots.
   One test asserting the collapse, with the reason in the docstring.

---

## (2) R3 — total own-fraction ask budget — ADOPT at B = 2.0, with its derivation corrected

**DECISION: Adopt R3. `Σ_i |delta_i| / cap_i ≤ 2.0`. And — this is the substantive part of the
call — B = 2.0 is NOT a new invented constant and must not be written into the tree as one. It is
the arity floor of the combination space, expressed in the sum's own natural unit. It ships as a
derived expression with an executable band assertion, or it does not ship.**

### Why I scrutinised this and what I found

D.4 flags B as "the module's first genuinely NEW constant… with no repo provenance." This project
has an earned allergy to that. PD.1 (b) kept `GENUINELY_CLOSE_MAX_FAILS = 3` specifically because
3 *reuses* `synthesize_thesis`' own DECLINE boundary; `RATE_MAGNITUDE_THRESHOLD` is written as
`abs(DEFAULT_BANDS["interest_rate_delta"][0])` (`recourse.py:130`) rather than `0.01` for the same
reason. So: is 2.0 derivable, or is it a number someone liked?

**It is derivable, and the derivation is not decorative.** Each `f_i = |delta_i| / cap_i` is the
lever's move as a fraction of **its own** single-ask plausibility threshold. So `f_i = 1.0` means
exactly "this lever, at the largest single ask this project already calls realistic," and for a
k-lever subset `Σf ∈ [0, k]`. The sum's unit is therefore literally **"maxed-out single asks."**
The combination section enumerates subsets with `|S| ≥ 2` — and that floor is not arbitrary
either, it is forced by the product decision that singletons belong to Mission 4's existing
section. So:

> **A combination may not ask for more, in total, than the smallest combination this section will
> ever show — two levers, each at its individual limit.**

`B = 2` is that sentence. It is a count in the same dimensionless unit the sum is measured in — the
same class of move as deriving 3 from the DECLINE boundary. And the derivation *constrains*: in
lever-count space the candidates are 1 (measured infeasible — every real crossing exceeds it),
2 (the arity floor), 3 (no structural meaning here; subsets run 2–4), and 4 (= the corner itself,
i.e. no rule at all). Only 2 is both defensible and non-vacuous.

### My own calibration — which is stronger evidence than D.4 reported

D.4 justified 2.0 mainly by "real crossings sum 1.3–1.6, the maxed corner is 4.0, B=1.5 is too
aggressive." I re-measured on both runnable committed deals (`verify_r3.py`, balanced ray per
subset, bisected to 1e-12, all live guardrails, h=10) and got something better:

| deal | gate (`is_genuinely_close`) | balanced-ray crossings, `Σf` |
|---|---|---|
| `82_champlain_dieppe` (6 live, 3 failing) | **OPEN** | all 11 subsets feasible, **1.210 – 1.640** |
| `36_kelly_moncton` (6 live, 4 failing) | **CLOSED** | 6 subsets edge-infeasible; the 5 that cross land **2.309 – 2.799** |

The two deals separate cleanly, and **B = 2.0 falls in the gap** — 22% of headroom above the
largest crossing on the gate-open deal, 13% below the smallest crossing on the gate-closed one.
Two independent scoping rules — the fail-count gate at 3, and the ask budget at 2 — sort the only
two real deals this repo ships the same way. That is corroboration I did not expect and did not
manufacture; it is the difference between a threshold and a calibrated threshold.

It also sharpens D.4's rejection of B = 1.5: on `82_champlain` the `rent+opex` (1.608) and
`rate+opex` (1.640) crossings die at 1.5. Real answers, on a gate-open deal. 1.5 is out.

**The honest caveat, stated rather than buried:** my sums are balanced-ray. A tilted ray can cross
at a different `Σf`, possibly higher, and if the *only* R2-surviving ray on some subset crosses
above 2.0, B kills a real answer. That is why the band assertion below is mandatory rather than
nice, and why the honest-null counters (call 4) matter: if B starts biting, it shows up as
`rays_gate_rejected` with a named reason in the data contract, not as a silent shrug.

### Reasoning

- **Source:** `recourse.py:117-130` (own-cap thresholds — the `cap_i` in the formula) ·
  `recourse.py:126-130` (the derive-don't-type precedent) · `PD1_product_calls.md` (b) (the reuse
  precedent for 3) · `D4_halfb_design.md` §3 R3, §8 Q2 · measurements above.
- **Aligned with:** no invented thresholds; the numbers must be real; assumptions shown, never
  hidden.
- **Trade-off accepted:** R3 is a **new rule**, and I am not pretending otherwise — only its
  *value* is derived. Declining R3 means a 4-lever combination sitting on all four caps at once
  (`Σf = 4.0`, every part individually blessed) ships unflagged wherever R2 does not happen to
  catch it. That is the "appearance of an answer" failure this product exists not to commit. The
  rule earns its place.

**Binding on implementation — four conditions:**

1. **No magic float.** The budget is written as an expression of the same module constant that
   sets the minimum combination arity — e.g. `_MIN_COMBINATION_LEVERS = 2` used both by subset
   enumeration and as `_COMBINATION_ASK_BUDGET = float(_MIN_COMBINATION_LEVERS)`. If someone ever
   changes the arity floor, the budget moves with it *visibly*, or the change is incomplete. Same
   discipline as PD.1 (e)'s "bounds read from the field constraints, never typed as literals."
2. **An executable band assertion, in the suite, not in this memo.** The PD.1 (a) / C6 pattern:
   assert that the budget sits strictly between the largest crossing on a gate-open committed deal
   and the smallest crossing on a gate-closed one, **measured on the real 39-ray grid**, not on my
   balanced-ray proxy. If that assertion ever goes red, the budget comes back to me. It does not
   get widened by whoever is on shift.
3. **The rule is stated in the output wherever it bites.** "This combination totals 2.4 maxed-out
   single asks; this project shows at most 2." The unit is explainable in one sentence; use it.
4. **R3 is applied as D.4 §3 specifies — an a priori box projection, not a post-hoc rejection.**
   A ray whose crossing needs more than B becomes edge-infeasible, which is already an honest,
   counted exit. No probe is spent on a combination the rule would reject.

---

## (3) R4 — price-cut + rent-raise posture rule — REJECT for v1

**DECISION: Not adopted. Not deferred with a design — rejected, with a stated bar for ever
reopening it.**

D.4 defaults to "no for v1 (YAGNI)." I go further than defer, because I think the rule's intuition
is partly wrong and partly already covered, and a deferred rule with a plausible-sounding
rationale is how a fifth threshold eventually walks in.

**Already covered, mechanically.** `cap_rate = noi_y1 / purchase_price`. A rent raise lifts NOI;
a price cut lowers the denominator. **Both push implied cap in the same direction**, so a
price+rent combination *compounds* the cap delta and makes R2 **more** likely to fire, not less.
My own measurement bears this out: price −15% + opex −20% alone reaches `cap_delta = +0.0202` and
trips R2 with no rate move at all. Deep price+rent combinations are exactly the ones R2 catches.

**Partly wrong, for the shallow cases.** R4's concern — "you're telling the seller two different
stories" — sounds right and mostly isn't. A modest rent raise plus a modest price cut is the
ordinary value-add thesis: *the units are under-rented, and I'm offering less because of the
deferred capex that's why they're under-rented.* Those are the same story, not two. Flagging it
would be the tool inventing a negotiation opinion it has no basis for — which is over the
descriptive/prescriptive line, not just over the YAGNI line.

**And there is no C.** D.4 says so plainly. Inventing a second new constant in the same gate, in
the same week, to guard a case the first rule already covers, is how thresholds stop being
explainable.

- **Source:** `D4_halfb_design.md` §3 R4, §8 Q3 · `verify_r2.py` cap-delta measurements above ·
  the engine's cap-rate definition.
- **Aligned with:** reuse-first / YAGNI; descriptive, not prescriptive; no invented thresholds.
- **Trade-off accepted:** a mild price+rent combination that a sharp negotiator would call
  awkward ships unflagged. Good. The tool shows the two asks and their sizes; the investor knows
  their own seller.

**Bar for reopening (backlog, not Mission 5):** a measured combination on a real deal that (i) R2
does not catch, (ii) a competent investor calls incoherent, and (iii) admits a C with repo
provenance — all three, or it stays closed.

---

## (4) Rejected combinations — FILTER, with aggregate reasons, plus one exemplar on the null

**DECISION: Filter, as D.4 defaults — counts and deduped reasons ship in the data contract so a
null is explained rather than silent. WITH one addition I am taking up from D.4's own offer: when
the section ships **zero** combinations, it also carries the single minimal-K gate-rejected
candidate and the reason it was rejected. Not when it ships one, two or three.**

### Why filtering does not break flag-don't-remove — the reasoning, so a Guardian can check it

Flag-don't-remove is a real documented value here and Roger ruled on its neighbourhood at Mission
4 Gate D (`recourse.py:139-142`): the earlier "compute recourse, then discard it post-hoc" design
was rejected because it "would have hidden a real, computed answer." I take that seriously enough
to spell out why it does not simply settle this question.

What that ruling actually produced was not "always show everything." It produced a **pre-computation
scoping gate** — decide before you look, and if you looked and found something, don't hide it. And
the single-lever menu shows implausible rows for a specific structural reason: it is a **complete
enumeration of a small, user-meaningful space** (4 levers × failing guardrails). Every row answers
a question the reader implicitly asked — *what about rent?* Deleting the flagged rows would leave
holes the reader could not distinguish from "no answer."

The combination space is not that. It is 39 search rays over 11 subsets; multiple rays round to
the same asks; nobody asked "what about the balanced ray on {rent, price, opex}?" Rendering
rejected rays is rendering search internals, and rendering 30-odd implausible negotiations
manufactures a menu — the appearance of an answer, which is the thing this product refuses. The
substance of flag-don't-remove survives at the aggregate: `rays_searched`,
`rays_edge_infeasible`, `rays_gate_rejected`, `gate_reasons`, `confirm_failed`. Nothing computed is
discarded; it is summarised.

### Why one exemplar on the null, and only there

Aggregates are honest but abstract. "39 rays, all rejected" is a fact; *"the closest thing to an
answer was a 90 bps rate cut plus a $90,000 price cut — it does close all three guardrails, and it
is not shown because it moves rates and cap apart by 211 bps, past the 200 bps this project treats
as one market story"* is a fact you can check and disagree with. In the zero-combination case there
is nothing for it to compete with, and it is the difference between "we found nothing" and "we
found something and here is exactly why it does not qualify." That is the same bargain the
single-lever flagged rows already make, applied where it works.

Above zero, it competes with real answers for the reader's attention, and a rejected option
displayed next to three accepted ones reads as a fourth option. So: null only.

- **Source:** `D4_halfb_design.md` §6, §8 Q4 (which explicitly offers the exemplar) ·
  `recourse.py:139-142` (Roger's Gate D ruling) · `README.md:291` (the shipped flag-don't-remove
  copy for the single-lever menu).
- **Aligned with:** honest-null; no manufactured appearance of an answer; assumptions shown.
- **Trade-off accepted:** when 1–3 combinations ship, the investor cannot see the specific
  almost-plausible combination that was rejected. They can see that some were, how many, and why.

**Binding on implementation — four conditions:**

1. One optional field on `CombinationAnalysis`, populated **iff `honest_null` is True**. Not
   populated-and-unrendered: a contract should not carry what nothing renders.
2. **The exemplar gets a real confirm-by-rerun**, exactly like a shipped combination (§5). One
   extra `run_financial_model` in the only case where we would otherwise do zero — ~3 ms at
   portfolio scale. No figure ships beside a combination that did not come from its own confirming
   run. If the confirm fails, there is no exemplar; the null is plain.
3. **It renders with its rejection reason adjacent and inseparable.** Never a bare
   `closes_all_live_guardrails: True` row. The reason is the point of showing it.
4. `staff-report-experience-designer` owns the words, as D.4 says — but the null copy must state
   the counts *and* the reasons, not just the counts. A number with no "why" is silence with a
   receipt.

**Guardian note:** if `principal-principles-guardian` reads Roger's Mission 4 flag-don't-remove
ruling as binding on the combination space and not merely on the single-lever menu, that is a
legitimate VETO. I will take it to Roger rather than argue it.

---

## (5) Top-3 ordering — parsimony strictly before magnitude, and no padding — YES to both

**DECISION: Adopt D.4 §4's sort key K unchanged. Parsimony (`len(A)`) strictly precedes the
leximin own-fraction comparison. Fewer than three distinct lever-sets ships as the honest count;
never padded with near-duplicates.**

**Parsimony first is right on execution grounds, not aesthetic ones.** Each lever is a different
**counterparty**: rent is the market and the tenants, price is the seller, rate is the lender,
opex is operations and vendors. Adding a lever does not add a number, it adds a conversation — and
the third conversation may not exist at all (you may have no lender leverage whatsoever). Two asks
at 70% of plausible are more executable than three at 40%. It is also the more conservative claim:
fewer moving parts means fewer things the tool is implicitly asserting are achievable.

**The pathological case is real and bounded.** A 2-lever combination at 0.9/0.9 outranks a 3-lever
at 0.3/0.3/0.3, and `Σf = 1.8` clears R3. I accept it, for two reasons. First, diversity selection
picks three **distinct lever-sets**, so the leaner 3-lever route still *appears*; the ordering
decides display order among three shown routes, not what exists. Second, D.4 measured that every
fixture surfaces 2-lever routes first regardless.

**No padding is not close.** Honest-null is documented and shipped. Three near-duplicates of one
route is a manufactured menu, which is the same failure as call (4) wearing different clothes.
Show two if there are two. Show none if there are none, with the counts and reasons.

- **Source:** `D4_halfb_design.md` §4 (the key, the total-order proof, the diversity predicate),
  §8 Q5 · `recourse.py:771` (`_pick_cheapest`'s documented tie-break discipline).
- **Aligned with:** deterministic core (K is a total order with a unique final tiebreak — no
  insertion-order fallthrough anywhere); honest-null; descriptive not prescriptive.
- **Trade-off accepted:** a deal whose genuinely cheapest route is 3-lever ranks it third.

**Binding on implementation — one condition, and it is the one that makes the stance honest:**
every shipped combination renders **`fraction_of_cap` per lever** (the field is already in D.4's
contract). The ordering is my opinion about what matters; the numbers underneath it must let a
reader see that route #1 is chunkier than route #3 and choose differently. The tool shows you the
math. You make the call.

---

## (6) Promote `82_champlain_dieppe` to the documented recourse walkthrough — YES

**DECISION: Yes. Add `82_champlain_dieppe` as the documented recourse/combinations walkthrough in
the README and the manual-testing doc. `36_kelly_moncton` stays the default bundle and the default
`python main.py` output does not move by one byte. And the walkthrough must teach the gate by
contrasting the two deals — a silent deal-swap is not the fix and I am not signing one.**

### What I verified first, because the framing matters

At this baseline (`is_genuinely_close`, h=10, shipped config):

| deal | live | failing | gate |
|---|---|---|---|
| `36_kelly_moncton` (default bundle) | 6 | **4** — dscr, spread, coc, cf_y1 | **CLOSED** |
| `82_champlain_dieppe` | 6 | **3** — dscr, spread, coc | **OPEN** |
| `47_perrot_shediac` | — | — | **not a runnable deal** — no `inputs.json`; it is an ingestion fixture (`listing.txt` + `photos/`) |

And the part that resizes the problem: **README.md:297 already says this in prose** — *"The shipped
fixture `data/sample_listings/82_champlain_dieppe/` is a `DECLINE` with the gate open — three
failing guardrails — precisely to give this section real data to render against."* The README names
the right deal. What it does not have is a **command that runs it**: every runnable example
(`README.md:267`, `:270`, `:274`) points at `36_kelly`, which by design renders no recourse.

So the evaluation's HIGH-severity finding is real, and it is a **documentation coverage gap, not a
product gap**. The fix is making an already-documented sentence executable.

### Is this papering over "the flagship example is a deal the tool declines"? — No, and here is the test

What would be papered over? The claim would be: the product's headline example is a deal it says no
to, with no recourse offered. But `36_kelly` fails 4 of 6 live guardrails. It is not close. The tool
declines it and computes no recourse for it. **That is the system working exactly as specified**,
and a demo that shows it is telling the truth. There is nothing to hide.

The alternative fixes are worse. Loosening the gate to 4 so `36_kelly` renders recourse is a
product-surface change smuggled in under a threshold tweak — PD.1 (b) already declined precisely
that, this mission, in writing. Engineering a new flagship deal to make the demo prettier is
building a fixture to fit a narrative, which is the same sin one layer up.

**What the quickstart teaches under each choice** — this is the deciding argument:

- **Status quo:** "the tool will tell you a deal is bad." True, valuable, incomplete. The strongest
  differentiator is invisible.
- **Silent swap** (make `82_champlain` the demo): "the tool tells you what would have to change."
  Also incomplete, and now *misleading* — a reader would reasonably infer recourse always appears.
- **Promote + contrast** (this decision): "`36_kelly` fails 4 of 6 live guardrails — past the
  3-fail line, so no recourse is computed at all, and the report is byte-identical to a build with
  no recourse feature. `82_champlain` fails 3 — the gate opens, and here is what would have to
  change, including the combinations no single lever can deliver." That teaches the feature **and
  its scoping rule**, using two committed deals sitting either side of the line.

PD.1 (b) already found that pairing and called it the best evidence for keeping the threshold at 3:
*"a boundary with a committed fixture immediately either side of it is worth more than a
differently-shaped integer with none."* The docs should say what the repo already knows.

And on Half B specifically, `82_champlain` is the right deal for a reason no other fixture supplies:
D.4 §0 fact 3 measured that **no single lever within its own plausible cap closes it**, while
jointly-plausible pairs do. That is Half B's entire product case in one committed deal.

- **Source:** `D4_halfb_design.md` §6, §8 Q6 · `README.md:291`, `:297`, `:267-274` ·
  `docs/manual testing/MISSION_4_MANUAL_TESTING.md:105-115` (which already exports both deals as
  `NEARMISS_CFG` / `DECLINE_CFG` — the contrast is half-built already) · measurements above.
- **Aligned with:** honesty of the analysis wins; solo-dev cap (docs-only, no new fixture to
  maintain); deterministic core untouched.
- **Trade-off accepted:** the default bundle still shows neither recourse section. That is correct
  behaviour for a deal that is not close, and the walkthrough will now say so out loud instead of
  leaving it as an unexplained absence.

**Binding on implementation — four conditions:**

1. **Default `python main.py` output is byte-identical.** No change to the default bundle, no
   change to golden or CI surfaces. If a diff appears, the change is wrong.
2. **The walkthrough is a contrast, not a substitution.** Both commands, both fail counts, one
   sentence naming the gate and where it lives (`is_genuinely_close`,
   `GENUINELY_CLOSE_MAX_FAILS = 3`, `recourse.py:143`).
3. **Do not restate the guardrail count from memory.** PD.1 (b) already ordered "up to seven live
   guardrails" corrected to six across five documents, `README.md:291` among them. This edit lands
   in the same paragraph. Correct it in the same pass or leave the sentence alone — do not copy it
   forward.
4. The walkthrough shows real output from a real run at the documented baseline, and says which
   commit produced it. A pasted report nobody re-ran is a future lie.

---

## Escalations to Roger

**None of the six requires escalation.** All six resolved against documented sources or against
measurements I took for this memo. Recorded so the absence is deliberate:

- (2) is the closest call, because it introduces a rule. I decided it rather than escalating
  because the *value* is derived and the pattern is settled precedent in this exact module
  (`RATE_MAGNITUDE_THRESHOLD`, `recourse.py:126-130`). If either Guardian reads B = 2.0 as an
  invented threshold despite the arity derivation and the measured separation band, that is a
  legitimate VETO and it goes to Roger, not into a debate.
- (4) sits nearest the flag-don't-remove line. I recorded the full reasoning above precisely so it
  is checkable rather than assumed, and I flagged the Guardian path in place.
- (6) touches a public README surface but changes no claim and no behaviour; it makes an existing
  documented sentence runnable.

**Three findings Roger should see, which are not decisions:**

1. **The R3 separation result is better evidence than the memo it came from.** The only two
   runnable committed deals land on opposite sides of B = 2.0 — `82_champlain` crossings 1.210–1.640
   (gate open), `36_kelly` crossings 2.309–2.799 (gate closed). The ask budget and the fail-count
   gate independently sort the same two deals the same way. Worth knowing when the constant is
   questioned later, as it should be.
2. **Every runnable demo deal in this repo is a DECLINE.** `36_kelly` (4 fails) and `82_champlain`
   (3 fails) are the only bundles with an `inputs.json`; `47_perrot_shediac` is an ingestion
   fixture with no runnable deal. Nothing in the shipped demo surface shows the tool saying yes.
   That may be the honest face of a tool built to say no — but it is a choice nobody has made
   deliberately, and it should be made deliberately.
3. **`README.md:291` still carries the "seven live guardrails" figure** PD.1 (b) ordered corrected.
   Call (6) edits the adjacent paragraph. Flagging so the two edits land together rather than one
   walking past the other.

## Backlog opened by this memo (NOT Mission 5)

- **R4, if it ever earns a case:** the three-part bar in call (3) — a measured combination R2
  misses, that a competent investor calls incoherent, with a C that has repo provenance.
- **A per-subset outcome surface.** The 11 *subsets* are a user-meaningful enumeration in a way the
  39 rays are not, so a per-subset "no plausible crossing on {price, rate}" line is the version of
  flag-don't-remove that would genuinely transfer to the combination space. Rejected for v1 as
  surface this section does not need while it ships three answers. Revisit only if the aggregate
  counters prove too coarse in real use.
- **A committed BUY or CONDITIONAL deal bundle**, per finding 2. Product-surface change; founder's
  call, not mine, and not this mission.
- **Naming the R3 budget's coupling risk in a comment**: if the minimum combination arity ever
  moves, the budget moves with it. Condition (1) under call (2) makes that structural; a comment
  makes it legible.

— Principal Founder Proxy, speaking for Roger Booto Tokime · Mission 5 · PD.2 · 2026-08-31
