# GD.3 — Ruling: the Lever/Assumption Partition

**Mission 5 · principles guardian, VETO authority · routed fable (touches `src/core/finance/`)**
**Baseline:** `mission/5-forward-mode-differentiation` (HEAD `87efd22` at review time)
**Proposal reviewed:** promote the lever/assumption separation — currently carried by three closed
sets and a YAGNI comment — to a named, enforced, load-bearing invariant.

---

## VERDICT: ADOPTED-WITH-CONDITIONS

The invariant is genuine and values-level, **provided it is worded to govern the output category,
not the computation** — the founder's own framing ("same solve to the same guardrail boundary;
inverted reading") already draws the line correctly, and this ruling adopts that framing while
explicitly rejecting the over-broad misreading ("never differentiate an assumption"), which would
be a design preference that forbids a legitimate and arguably required feature. Conditions C1–C7
below are the enforcement mechanism; each is checkable and becomes a tracker row.

**RATIONALE:**

- **Reviewed against (first-hand this turn):**
  `src/market/recourse.py` (`:1-120`: module docstring, `LeverName` at `:81`, `_LEVER_ORDER`,
  `_STATICALLY_HOPELESS`, `ROUND_STEP`) ·
  `src/core/finance/jacobian.py` (in full: the `:132-135` YAGNI comment, `SeedTarget` `:136-145`,
  `_validated_directions` `:208-238`, the occupancy θ-constant at `:352`, import-time drift guards
  `:95-130`) ·
  `src/core/finance/engine.py` (`EQUITY_LTV` `:22`, `_CoreOverrides` `:213-247`, terminal-equity
  proxy `:701-717`, the "terminal equity proxy" comment `:702`) ·
  `src/schemas/models.py` (`RecourseLever` `:1375-1395` — `lever` is a closed `Literal` **on the
  pydantic model itself** `:1391`; `RecourseAnalysis` `:1426-1438`) ·
  `src/core/reports/generator.py` (`:468` — the proxy's rendered disclosure; `:1675` — "IRR (10yr)
  and the equity multiple are terminal-value / cap-rate dominated") ·
  `README.md` (`:289-297`, the recourse section's public promises) ·
  `src/core/README.md` (Gate 3 record: `advisor/scenarios.py` deleted because its own disclaimer
  "never reached the rendered page"; the CV sibling-producer leak record — "Safe by accident is
  not safe"; "Determinism first") ·
  `src/schemas/README.md` (`MarketAssumptions`/`RefinancePlan`/`RecourseLever`/`RecourseAnalysis`
  rows; the Mission-4 doc-audit record) · `CONTRIBUTING.md` ·
  `docs/plans/mission-5-discovery/PD1_product_calls.md` (`:268-285` — "arithmetic on assumptions
  the user supplied and labelled as such. It is not forecasting") ·
  `docs/plans/mission-5-discovery/PD2_halfb_calls.md` (`:78`, `:100-101` — "An assumption that is
  only true because nobody wrote it down is a hidden assumption") ·
  `docs/plans/mission-5-discovery/GD1_veto_review.md` (the C2 non-decaying-element standard this
  ruling is asked to re-apply) · project memory (direct-to-main, founder holds all gates).
  Licensing files not re-read this turn: the proposal adds no dependency, moves no code, and has
  zero licensing surface.
- **Principle invoked:** descriptive-not-prescriptive (the tool diagnoses; the investor decides) +
  no-fabrication (a suggested "fix" achievable only by altering a guess manufactures a PASS) +
  no-hidden-assumptions + schema-contract discipline.
- **Independent verification performed (the orchestrator's three-layer claim, confirmed, not
  taken on faith):** (1) `LeverName` is the closed four-lever `Literal` (`recourse.py:81`) and the
  schema duplicates the closure at `models.py:1391`; (2) `_validated_directions` raises
  `ValueError` on any target outside `_SCALAR_TARGETS` ∪ `("opex", <line>)`
  (`jacobian.py:229-235`); (3) `_CoreOverrides` has exactly `gsi_annual`/`goi_annual`/
  `purchase_price`/`interest_rate`/`opex` — no vacancy, growth, cap or horizon field
  (`engine.py:213-247`); (4) occupancy and bad-debt are θ-constants on the rent direction — the
  tangent rides `gsi` alone (`jacobian.py:352`). **The harmful output is unreachable today by
  construction.** What is NOT unreachable is the one-line future edit, which is what this ruling
  is about.

---

## Ruling 1 — Genuine invariant, and where the line actually falls

I tested the founder's argument against its strongest counter: sensitivity to vacancy, growth,
exit cap and horizon is legitimate and standard — every competitor ships tornado charts over
exactly these axes, and this project's own doctrine *requires* surfacing an assumption's weight
("An assumption that is only true because nobody wrote it down is a hidden assumption",
PD2:100-101). A rule that forbade differentiating an assumption would therefore forbid a good
feature and I would reject it as a preference.

But that is not the founder's rule. The precise distinction:

- **Computing a sensitivity to an assumption** — descriptive arithmetic on a user-stated guess
  (PD1:275). Permitted; arguably required by the hidden-assumption principle.
- **Solving to the guardrail boundary along an assumption axis** — this IS the breakeven
  computation ("clears DSCR until vacancy hits 9.4%; you assumed 5%"). Permitted; it is a margin
  of safety, the most honest possible surfacing of that assumption.
- **Presenting the assumption's boundary value as a recourse action** — "raise your vacancy
  assumption to 8% and the deal passes." Forbidden. The world does not change when you change
  your guess; only the model does. A recourse row over an assumption is an instruction to fudge
  an input until the model returns PASS — a manufactured verdict (no-fabrication), delivered as
  advice (descriptive→prescriptive, in the worst direction: prescribing model manipulation rather
  than world action).

**So the line falls at the reading — but the reading is determined by the container, which is why
enforcement belongs at the schema boundary, not the copy.** A number shipped in `RecourseLever`
*is* the recourse reading by construction: the field's own description says "investor-movable
input" (`models.py:1392`), and the report renders it under "What would have to change?"
(README:289). This repository has already run the copy-level experiment twice and documented both
failures: `advisor/scenarios.py`'s own returned disclaimer "never reached the rendered page"
(Gate 3, `src/core/README.md`), and the CV sibling producer reached a guarded output surface by a
route the guard did not cover ("Safe by accident is not safe", `src/core/README.md:156`).
Schema-level separation is not engineering taste; it is this project's documented remedy pattern
for its two recorded incident classes. **Values-level. Adopted.**

### The invariant, exact wording

> **THE LEVER/ASSUMPTION PARTITION (GD3).** Every scalar input the pipeline can perturb, search,
> or differentiate is classified exactly once as an **INVESTOR LEVER** (a quantity the investor
> can act on in the world: rent per unit/month, purchase price, interest rate, annual opex) or a
> **MODEL ASSUMPTION** (a quantity the investor guesses: vacancy/occupancy/bad-debt, rent growth,
> expense growth, exit cap and cap drift, hold horizon). A solve toward a guardrail boundary
> along a LEVER axis may be presented as **recourse** — "what would have to change." The same
> solve along an ASSUMPTION axis may only ever be presented as **breakeven / margin of safety** —
> "how wrong can this guess be before the deal fails" — and must ship in a schema type of its own
> in which the recourse reading is inexpressible (no `target_value`/`delta`/ask field; fields
> named for the breakeven reading: assumed value, breakeven value, margin, direction of failure).
> No assumption may ever appear in `LeverName`, `RecourseLever`, `RecourseAnalysis`, the recourse
> search space (single-lever or combination), or any surface rendered under a
> "what would have to change" framing. Computing an assumption's sensitivity or breakeven is
> permitted and encouraged; presenting an assumption change as an action that closes a gap is
> forbidden — it instructs the user to fudge an input until the model passes.

## Ruling 2 — What makes it structural: a closed `Literal` plus a docstring is NOT sufficient

A `Literal` is one line from extension, and `jacobian.py:132`'s stated rationale — "ONLY what the
four levers need (**YAGNI**)" plus a performance argument — is not a fence but an invitation with
an expiry date: scope-economy rationales expire at the exact moment someone has the scope, which
is when the harm arrives. Applying GD1's C2 standard (the only non-decaying element is one whose
failure cannot be cleared by writing another rationale), the enforcement must convert the
one-line-plus-one-rationale edit into a multi-file, self-incriminating diff that has to modify
the invariant's own declaration. In this repo's direct-to-main, founder-holds-all-gates workflow
(project memory), that makes every attempted crossing a founder-visible event by construction.

Concretely (each element verifiable; C1–C4 below):

1. **One source of truth for the partition** — a single module (in `src/core/finance/` or
   `src/schemas/`; implementer's choice, but exactly one) declaring `INVESTOR_LEVERS`,
   `MODEL_ASSUMPTIONS` (as input field paths), the lever→seed-target correspondence (the rent
   lever's image is `income.gsi_annual`, per D.1 §1a), and the invariant text verbatim.
2. **Import-time drift guards, house pattern** (`jacobian.py:95-130` already does exactly this
   for metric rows and opex order): `jacobian.py` fails on import if `SeedTarget`'s members are
   not exactly the image of `INVESTOR_LEVERS`; `recourse.py` fails on import if `LeverName` ≠
   `INVESTOR_LEVERS`; a test pins `_CoreOverrides`' field set and `RecourseLever.lever`'s
   `Literal` args to the same source. Silent divergence becomes impossible; deliberate divergence
   must edit the declaration that carries the invariant's own text.
3. **Disjointness with teeth**: an assertion that `INVESTOR_LEVERS`, the seed-target set, and the
   `_CoreOverrides` field set are disjoint from `MODEL_ASSUMPTIONS`' field paths, whose failure
   message states that extension requires Founder Proxy escalation citing GD3 — the analogue of
   GD1-C2's "the remedy is never a budget raise" message.
4. **The future breakeven feature gets its own home, shaped so the harm cannot be typed**: if and
   when assumption breakevens ship, they ship in a new schema type whose fields cannot express an
   ask. The type-level enforcement is that the harmful sentence has no field to live in — the
   same property that makes `partials[m] is None` never `0.0` (`jacobian.py` docstring): honesty
   carried by shape, not by discipline.

The runtime guard (`_validated_directions`' loud `ValueError`) already exists and is correct; it
becomes *enforcement of this invariant* rather than an incidental validation the day its tests
say so (C3). The report layer is the last line, not the first (Ruling 1's history), but it is
still bound: the recourse renderer consumes `RecourseLever` only.

## Ruling 3 — The terminal-equity proxy does NOT earn a derivative on the axes that live inside it

Confirmed first-hand: `EQUITY_LTV = 0.80` (`engine.py:22`);
`terminal_equity = max(0.0, EQUITY_LTV * term_est_value - term_ending_balance)` (`engine.py:717`);
the engine's own comment calls it a proxy (`:702`); no sale or transaction costs anywhere. Note
the form is not even a simplified *sale*: value − sale costs − balance is a sale; 0.80×value −
balance is a refinance-style available-equity figure pressed into service as one. The one place
it renders, the report says so honestly: "A proxy for sale proceeds to the owner; no sale costs
are modeled" (`generator.py:468`). So the **primal** is compliant — a labeled estimate.

The derivative question splits exactly along the axis, and the ruling is:

- **Lever axes (price, rate, rent, opex) differentiating *through* the proxy — permitted, and
  already shipped** (the IRR row includes terminal-equity terms). The derivative makes no claim
  about the terminal model beyond what the shipped primal IRR already makes; the proxy is one
  additive term among the horizon's cash flows, and its disclosed status covers both.
- **Axes that live wholly or dominantly inside the proxy — exit cap, cap drift, hold horizon —
  are barred from every differentiation and breakeven surface until the terminal model is
  explicit.** d(IRR)/d(exit_cap) is precisely the derivative of the placeholder itself, and the
  report's own methodology note records that IRR is "terminal-value / cap-rate dominated"
  (`generator.py:1675`). A breakeven exit cap would put margin-of-safety confidence — the whole
  point of the breakeven reading — on a functional form chosen for simplicity, not fidelity. The
  founder's analogy is exact: it is the 1e-9-tolerance-on-an-unchecked-formula trap from GD1,
  transposed. (Hold horizon is additionally an integer — no derivative exists; a horizon
  breakeven would be a re-run sweep, mechanically fine, but its IRR signal is terminal-dominated,
  so it clears or falls with the same prerequisite.)
- **Vacancy/growth axes** act through the operating years; for the Y1/operating guardrails (DSCR,
  spread, CoC, cf_y1, cap floor) they never touch the proxy and clear this bar outright. Their
  IRR rows inherit the same disclosed-proxy status as the lever axes — permitted, under the IRR
  row's existing honest-degradation posture.

**Prerequisite to lift the bar** (all four, in order): (i) an explicit terminal sale model —
a named sale-cost assumption as a schema field with a surfaced default, and the `EQUITY_LTV`
haircut either replaced by the sale identity or documented as deliberate conservatism in the
schema and the rendered report (the hidden-assumption principle, applied); (ii) golden cases
pinned over the new terminal math under the GD1 anchor discipline; (iii) guardian review of the
resulting seed target (the same "guardian-reviewed" reservation `jacobian.py:48` already makes
for the aggregate-shift seam); (iv) even then, exit cap / cap drift / horizon are ASSUMPTIONS
under Ruling 1 — breakeven surface only, never recourse. No condition here is waivable by a
rationale string.

## Ruling 4 — Scope and sign-off

The invariant binds **all four layers**, not just Mission 5's seam:

| Layer | Bound surface |
| --- | --- |
| Core seam | `jacobian.SeedTarget`, `engine._CoreOverrides`, any future dual-number entry point |
| Market | `recourse.LeverName`, the single-lever search, and the Half-B combination optimizer — its search space is drawn from `INVESTOR_LEVERS` via the correspondence table, nothing else |
| Schema | `RecourseLever`/`RecourseAnalysis` stay closed to levers; any breakeven type obeys the shape rule (Ruling 2.4) |
| Report | the "What would have to change?" section renders `RecourseLever` rows only; assumption breakevens, if ever built, render from their own type under margin-of-safety copy |

**Sign-off rules:** growing `INVESTOR_LEVERS`, adding any seed target or `_CoreOverrides` field,
or moving a name between the two sets is a **Founder Proxy escalation citing this ruling** —
never a self-approved edit, whatever the rationale. Growing `MODEL_ASSUMPTIONS` is the safe
direction (it only restricts) and may be done by an engineer with a guardian note. Lifting the
Ruling-3 bar requires the full prerequisite chain, founder-approved.

---

## CONDITIONS (each becomes a tracker row; each is checkable)

- **C1 — Partition source of truth + drift guards.** One module declares `INVESTOR_LEVERS`,
  `MODEL_ASSUMPTIONS` (field paths, covering at minimum: `income.occupancy`,
  `income.bad_debt_factor`, `income.rent_growth`, `opex.expense_growth`, `market.cap_rate_drift`,
  `refi.exit_cap_rate`, `horizon_years`, `MarketSnapshot.vacancy_rate/rent_growth/expense_growth`),
  the lever→seed-target correspondence, and the invariant text verbatim. `jacobian.py` and
  `recourse.py` carry import-time guards against it in the existing `:95-130` house pattern.
  *Check: desync of any closed set raises `RuntimeError` on import; single declaration site.*
- **C2 — The YAGNI rationale is retired.** The `jacobian.py:132-135` comment, the
  `_CoreOverrides` docstring, and the `recourse.py` module docstring each state the category
  rationale (assumptions must never enter the recourse path — GD3) as the primary reason the
  sets are closed; scope/perf remarks may remain as secondary. *Check: grep for "YAGNI" as a
  load-bearing justification at these sites — none remains; "GD3" cited at all three.*
- **C3 — RED tests naming the invariant.** (a) A test pins that seeding any
  `MODEL_ASSUMPTIONS` path as a `TangentDirection` target raises `ValueError`; (b) the
  disjointness assertion of Ruling 2.3 exists and its failure message names the Founder Proxy
  escalation and cites GD3; (c) a test pins `RecourseLever.lever`'s `Literal` args ==
  `INVESTOR_LEVERS`. *Check: three tests exist, RED under the one-line edit each guards.*
- **C4 — The partition is documented where contributors read.** One paragraph each in
  `src/schemas/README.md` and `src/market/README.md`: the partition, the two readings, and the
  breakeven shape rule (no ask/delta/target field on an assumption-axis type). *Check: grep.*
- **C5 — Terminal-model bar recorded and enforced.** The partition module lists exit cap, cap
  drift and hold horizon as barred axes with the Ruling-3 prerequisite chain; the C3 disjointness
  test additionally asserts no seed target, `_CoreOverrides` field, or breakeven surface exists
  for them. *Check: barred list present; assertion present.*
- **C6 — Half-B optimizer scope pinned.** The combination search enumerates subsets of
  `INVESTOR_LEVERS` only, and a test asserts its candidate space contains no assumption axis.
  *Check: test exists and is RED if an assumption axis is injected into the candidate set.*
- **C7 — Escalation clause in-repo.** The partition module's docstring carries the sign-off rules
  of Ruling 4 verbatim, including "extension of `INVESTOR_LEVERS` is a Founder Proxy escalation
  citing GD3; a rationale string is not a clearance." *Check: read the docstring.*

**PATH FORWARD:** the invariant is in force as of this ruling; C1–C7 are the implementation of
its enforcement and are verified by the orchestrator before the relevant tracker rows are marked
DONE. Until C1–C3 land, the existing closed sets remain the interim enforcement and any edit to
them is already an escalation under Ruling 4.

**EVIDENCE OF READING:**
- `recourse.py:1-41, 81` — "investor-movable", the four levers, re-run-never-invert; the reading this invariant protects.
- `jacobian.py:132-135, 229-235, 352` — the YAGNI comment under ruling; the loud `ValueError`; occupancy as θ-constant, confirmed.
- `engine.py:22, 213-247, 701-717` — `EQUITY_LTV`; `_CoreOverrides` has no assumption field; the proxy and its own "proxy" comment.
- `models.py:1391` — the schema itself closes `lever` to the four names; the pattern C1 generalizes.
- `generator.py:468, 1675` — the proxy's honest rendered disclosure; IRR recorded as terminal-value dominated — the two facts Ruling 3 stands on.
- `README.md:289-297` — "a currency the investor can move… what single change would close the gap if it happened?" — the public promise that defines the recourse reading.
- `src/core/README.md` — Gate 3 (disclaimer never reached the page) and the sibling-producer leak ("Safe by accident is not safe") — why copy-level separation was rejected.
- `src/schemas/README.md` — assumption fields live in `IncomeModel`/`MarketAssumptions`/`RefinancePlan`; `RecourseLever`/`RecourseAnalysis` rows verified against `model_fields`.
- `CONTRIBUTING.md` — tests required for new behaviour; no further bearing.
- `PD1_product_calls.md:275` / `PD2_halfb_calls.md:100-101` — "arithmetic on assumptions the user supplied and labelled as such"; "an assumption that is only true because nobody wrote it down is a hidden assumption" — the doctrine that makes breakevens legitimate and their mislabeling a breach.
- `GD1_veto_review.md` — the C2 non-decaying-element standard, applied here as Ruling 2.
- Project memory — direct-to-main, founder holds all gates: the workflow that makes the multi-file self-incriminating diff a founder-visible event.

— Principles Guardian, GD.3, 2026-08-31
