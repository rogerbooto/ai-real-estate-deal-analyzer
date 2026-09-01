# PD.1 — Gate D founder product calls (Half A)

**Mission 5 · Gate D · `principal-founder-proxy` speaking for Roger Booto Tokime · routed opus**
**Baseline:** `mission/5-adjoint-differentiation` @ `87efd22`
**Date:** 2026-08-31
**Scope:** exactly the five calls chartered for PD.1. Nothing else. Half B (combination
plausibility, top-3 selection) is **PD.2 and is not decided here**.

**Inputs read before deciding:** `docs/plans/mission-5-discovery/D3_tolerance_rule.md` (in full) ·
`docs/plans/mission-5-discovery/GD1_veto_review.md` (VETO LIFTED WITH CONDITIONS C1–C7) ·
`src/market/recourse.py:79-143`, `:213-234`, `:280-301` · `src/agents/chief_strategist.py:56-57`,
`:294-326` · `src/schemas/models.py:17-160` · `src/inputs/inputs.py:71-80`, `:195-235`, `:294-320` ·
`main.py:118`, `:225-260` · `src/core/reports/generator.py:1323-1332`, `:1545-1572` ·
`tests/perf/bench_finance_engine.py:150-175`, `:295-307` ·
`docs/manual testing/MISSION_4_MANUAL_TESTING.md:540-590` ·
`docs/manual testing/MISSION_5_MANUAL_TESTING.md:279-315` ·
`docs/plans/MISSION_5_adjoint_differentiation.md:487` · `docs/plans/ROADMAP_TRACKER.md:134`.

**Measurements taken for this memo** (conda env `airedeal`, this baseline, not taken on faith):
recorded inline under each call.

---

## (a) Tolerance value — RATIFY 1e-9 relative

**DECISION: Ratified. `REL_TOL = 1e-9`, relative, asymmetric, `abs_tol = 0`, exact zeros exact,
non-float fields exact — exactly as D.3 §2 specifies, subject to Guardian conditions C1–C7. No
different value.**

### Reasoning

- **Source:** `D3_tolerance_rule.md` §1.2–§1.4, §2; `GD1_veto_review.md` rulings (1) and (6), which
  reproduced both walls independently. The orchestrator re-ran them a third time. Three independent
  derivations of the same two numbers is more evidence than any constant in this repository has
  ever carried.
- **Aligned with:** "the numbers must be real"; "deterministic core"; the harness's own documented
  escape clause (`tests/core/finance/test_golden_forecasts.py:17-20` — "a named, justified
  tolerance").
- **Why not tighter.** 1e-11 is only ~87× above the measured reordering noise floor (1.151e-13),
  and the approaching-band trips at half of that — ~43×. With the ~143× cancellation amplification
  at `principal_paid` (D.3 §1.4), a tighter constant starts failing builds on arithmetic that is
  correct. That is a control that gets disabled, which is worse than a slightly looser one that
  gets respected.
- **Why not looser.** 1e-8 would still catch `round(payment, 4)` (1.1325e-7), so it is not
  technically wrong — it just multiplies the dollar blindness by ten and buys nothing. There is no
  measured pressure to loosen. Don't spend what you don't have to.
- **The concession, in the units I think in.** $0.213 on the largest number in a synthetic
  500-unit/50-year matrix case that is never rendered to anyone; $0.00053 on `36_kelly_moncton`,
  the deal this product actually ships; ≤3.1e-8 absolute on every rate a guardrail reads. Every
  rendered surface rounds to the dollar or to four decimals of a rate. Nothing a user or a verdict
  can see moves within this band.

### One refinement neither D.3 nor GD.1 stated in dollars — and it matters to the ratification

The **nominal** tolerance is 1e-9, but the *silence* threshold is 5e-10, because the approaching
band `[5e-10, 1e-9)` **fails the build** (D.3 §4.2). So the honest figure for "drift that passes
without any human ever seeing it" is:

| | silent blindness at 5e-10 |
|---|---|
| largest synthetic matrix value ($213,118,291.76) | **$0.107** |
| largest shipped-deal field (`36_kelly_moncton`, $533,347.71) | **$0.000267** |

That is the number I am actually ratifying, and it is half of what the charter asked me to accept.
`round(payment, 6)` — an ordinary "someone rounded money" bug measured at 9.790e-10 — lands **inside**
that band and therefore fails the build rather than passing quietly. The fail-closed band is not a
nicety; it is what makes the 1e-9 headline honest.

**Trade-off accepted:** a defect at or below `round(payment, 8)` scale (measured 1.669e-11) now
lands silently. It cannot reach a rendered figure or a guardrail comparison. I accept it, in
writing, with the number attached.

**Binding on implementation:** C6's executable boundary is what keeps this ratification true as the
product grows. `REL_TOL × max(|shipped-deal golden field|) < 0.005` must be an assertion in the
suite, not a sentence in a memo. If this product ever underwrites at a scale where that assertion
goes red, the tolerance comes back to me — it does not get widened by whoever is on shift.

**Not re-litigated here:** everything in D.3 §6.3 stands as written. `REL_TOL` is a test-tree
module constant. It never appears in `src/`. It is not an `AIREAL_*` flag — those gate optional
features, never the strictness of a correctness check.

---

## (b) `GENUINELY_CLOSE_MAX_FAILS` — KEEP 3

**DECISION: Keep `GENUINELY_CLOSE_MAX_FAILS = 3` (`src/market/recourse.py:143`). The value does not
change. Its stated derivation is wrong in five places and must be corrected (docs-only).**

### What I measured first, because the charter's framing rests on a number that is wrong

| deal | live guardrails | failing | gate |
|---|---|---|---|
| `data/sample_listings/82_champlain_dieppe` (the near-miss fixture) | **6** — cap_floor, cf_y1, coc, dscr, irr, spread | **3** — dscr, spread, coc | **OPEN** (DECLINE) |
| `data/sample_listings/36_kelly_moncton` (the shipped demo) | **6** | **4** — dscr, spread, coc, cf_y1 | **CLOSED** |
| `bench_finance_engine.build_gate_limit_inputs(5000, 100)` | **5** — no `cap_rate_floor` configured | **3** — dscr, spread, irr | at the limit |

Two documented figures are wrong and both bear on this call:

1. **"up to seven LIVE guardrails"** (`src/market/recourse.py:135`, `src/market/README.md:28`,
   `README.md:291`, `CHANGELOG.md:10`) is **false under the shipped configuration**.
   `REQUIRE_POSITIVE_CF_ALL = False` (`src/agents/chief_strategist.py:56`), so `cf_all` is never
   live. **Maximum live is 6**, and 6 requires the user to have configured a `cap_rate_floor`.
   Seven is reachable only by editing a module constant.
2. **"only 4 guardrails are live and failing at the gate-limit scenario"**
   (`docs/plans/mission-5-discovery/D1_ad_design.md:37`, `:296`) is **also wrong**. Measured at the
   benchmark's own gate-limit workload: **5 live, 3 failing.** (D.1's *conclusion* — 8 metric rows ×
   N caller-named columns — is unaffected, because its rows are `ForecastMetrics` fields, not
   guardrails. No rework for D.1; correct the sentence, keep the ruling.)

So the real proportion is: the gate opens at **up to 3 of 5 or 6** live guardrails failing — half to
sixty percent, not "3 of 7."

### Reasoning

- **Source:** `src/market/recourse.py:132-143` (the constant and Roger's 2026-08-29 Gate D ruling it
  records) · `src/agents/chief_strategist.py:315` (DECLINE at `num_fails >= 3`) ·
  `src/core/reports/generator.py:1323-1332` (`ABOUT_RECOURSE_BLOCK`, the rendered copy) ·
  `data/sample_listings/82_champlain_dieppe/README.md:6-8`.
- **Aligned with:** descriptive-not-prescriptive; flag-don't-remove; reuse-first / YAGNI.

**First: this is not an honesty question, and I want that said plainly, because the worse proportion
above invites the wrong worry.** The rendered section is titled *"What would have to change?"* and
its fixed honesty block says the numbers are "the smallest single change to ONE input that WOULD
close it… **'Would,' not 'will'**… the levers are not independent." It makes **no closeness claim
anywhere**. There is no sentence in the report that a higher fail count could turn into a lie. So
the gate is a **scoping and signal-to-noise decision**, not a truthfulness one — and it should be
argued as such rather than as a moral question.

**Why 3 and not 2.** Two would make the gate arithmetically identical to "CONDITIONAL" (1–2 fails
is the verdict rule's own definition) plus the cap-floor+DSCR shortcut. That silently re-couples the
gate to the verdict — the exact coupling Mission 4 explicitly rejected and then documented twice
after a doc-audit found the CONDITIONAL-only framing wrong (`README.md:500`,
`src/market/README.md:191`). It would also close the gate on
`data/sample_listings/82_champlain_dieppe`, the fixture that exists *for the sole purpose* of
proving this section renders on a non-CONDITIONAL deal. Deleting a fixture's reason to exist is a
real cost that a marginally tidier integer does not buy off.

**Why 3 and not 4.** At 4, the "cheapest single fix" leaves three gaps standing. Four gap blocks,
each of which individually fixes nothing, is a menu that reads like guidance and functions like
noise — and this product's whole claim is that it does not manufacture the appearance of an answer.
Concretely, 4 would turn recourse on for `36_kelly_moncton`, changing the shape of the flagship
demo report. That is a visible product change smuggled in under a threshold tweak, and I am not
signing it as one.

**What actually anchors 3.** It is the fail count at which `synthesize_thesis` itself first turns
DECLINE (`chief_strategist.py:315`, `num_fails >= 3`). The rule reads cleanly in one sentence:
*recourse is offered up to and including the first rung of DECLINE, and no further.* That is reuse
of a threshold this project already decided, not a fifth independent number — the same move the
neighbouring `RATE_MAGNITUDE_THRESHOLD = abs(DEFAULT_BANDS["interest_rate_delta"][0])` makes at
`recourse.py:130`.

And the value is flanked by live regression evidence on **both** sides: 82_champlain (3 fails, gate
open) and 36_kelly (4 fails, gate closed) are both shipped, both tested
(`tests/unit/test_recourse.py:86`, `:92`). A boundary with a committed fixture immediately either
side of it is worth more than a differently-shaped integer with none.

**Trade-off accepted:** a user with 3 of 5 live guardrails failing gets a menu of single fixes for a
deal that is, in plain terms, not close. `remaining_after_cheapest` and the honesty block already
tell them so. I would rather over-inform with the caveats visible than withhold a computed answer —
which is the same ruling Roger already made at Mission 4's Gate D about never discarding a computed
result post-hoc.

### Required with this decision (docs-only; no behaviour change)

- **MUST:** correct "up to seven LIVE guardrails" → "up to six live under the shipped configuration
  (`cf_all` is off by default; `cap_floor` is live only when the user sets `market.cap_rate_floor`)"
  in `src/market/recourse.py:133`, `src/market/README.md:28`, `src/market/README.md:70`,
  `README.md:291`, `CHANGELOG.md:10`.
- **MUST:** state in `recourse.py`'s constant docstring that 3 is the DECLINE threshold from
  `chief_strategist.py:315`, so the two cannot drift apart unnoticed.
- **SHOULD (cheap, non-blocking):** give `chief_strategist.py:315`'s bare literal a name
  (`DECLINE_MIN_FAILS = 3`) and have `recourse.py` derive `GENUINELY_CLOSE_MAX_FAILS` from it. Zero
  behaviour change (3 == 3). If it is not a five-minute edit, it is a backlog row, not a Mission 5
  obligation.
- **Relay to the orchestrator:** `D1_ad_design.md:37` and `:296` need the "4 live and failing"
  sentence corrected to "5 live, 3 failing." I did not edit D.1's artifact.

---

## (c) Money-field lower bounds (OI.1) — DECIDED, field by field

**DECISION: Add lower bounds to exactly the 17 currency-denominated fields of `FinancialInputs`.
`purchase_price` is `gt=0`. Every other money field is `ge=0`. No upper bounds. No new bounds on
any rate, ratio, or year-count field in this pass.**

Enumerated from `model_fields` at this baseline, not from memory.

| model | field | floor | why this floor and not the other one |
|---|---|---|---|
| `FinancingTerms` (`models.py:24`) | `purchase_price` | **`gt=0`** | It is the denominator of `cap_rate`, `coc`, `ltv` and the base of the loan, the down payment and the MIP. At 0 the engine currently returns `cap_rate = 0.0` and a report full of guarded zeros — verified. There is no deal at a zero price; an all-cash purchase is modelled as `down_payment_rate = 1.0` (see the `all_cash_deal` golden case), never as a zero price. |
| `FinancingTerms` (`:25`) | `closing_costs` | `ge=0` | Zero is legitimate (seller pays all costs). Negative is not: see the note below. |
| `OperatingExpenses` (`:50-61`) | `insurance`, `taxes`, `utilities`, `water_sewer`, `property_management`, `repairs_maintenance`, `trash`, `landscaping`, `snow_removal`, `hoa_fees`, `reserves`, `other` — **all 12** | `ge=0` | Zero means "this expense is absent from the model," which is common and correct: self-managed (`property_management = 0`), owner pays no utilities, no HOA. The golden matrix anchors 30 exact zeros on each of nine of these paths. A negative operating expense is income wearing a costume; it belongs in `other_income_month`. |
| `UnitIncome` (`:75`) | `rent_month` | `ge=0` | Zero is legitimate and real: a vacant unit, a unit under renovation, the owner-occupied unit in a house-hack. Negative rent is not a thing. |
| `UnitIncome` (`:76`) | `other_income_month` | `ge=0` | Same. |
| `FinancialInputs` (`:153`) | `capex_reserve_upfront` | `ge=0` | Zero is the default and the common case. |

**Explicitly NOT in this pass** (rates, ratios and counters — different question, different memo):
`expense_growth`, `rent_growth` (legitimately negative — declining markets exist),
`cap_rate_purchase`, `cap_rate_floor`, `cap_rate_spread_target`, `cap_rate_drift`, `exit_cap_rate`,
`market_cap_rate`, `amort_years`, `io_years`, `year_to_refi`. Several of those are genuinely
unguarded too (`amort_years` accepts 0 and negatives today). **Backlog, not Mission 5.** The charter
asked for money fields; widening this into a general bounds sweep is exactly the sprawl I was told
not to do.

### Reasoning

- **Source:** `src/schemas/models.py` `model_fields`, enumerated programmatically at `87efd22`;
  `docs/plans/MISSION_5_SPRINT_TRACKER.md:471` (OI.1, blocked on this call).
- **Aligned with:** schema-first (`src/schemas/models.py` is the single source of truth); loud fail
  on misconfig; "if a number can't be traced to an input, it doesn't belong in the report" — and its
  contrapositive, that an input the model cannot mean should not be accepted.
- **Verified blast radius = zero.** I checked all 34 golden cases and every `inputs.json` under
  `data/` and `tests/` against the proposed floors: **no violations.** No fixture churn, no golden
  regeneration, no anchor supersession. This lands additively.
- **Verified no interaction with recourse.** All four search bounds stay inside the new floors:
  price cuts are capped at 40% (`recourse.py:299`), the opex lever scales every line by
  `(1 − t/total)` with `t ≤ 0.40 × total` (`:301`), the rate lever is `max(0.0, rate − t)`, and the
  rent lever only increases. The `_perturb` fast path cannot construct a value these bounds reject.

**On `closing_costs` and the one case that argues the other way.** A seller credit larger than the
buyer's closing costs is a real transaction, and someone will reach for `closing_costs = -5000`.
I am rejecting that anyway, and the field description must say why in one sentence: *"Model a seller
credit as a lower purchase price, not as negative closing costs — a negative here would silently
change the cap-rate denominator's meaning."* Opinionated, stated, visible. That is the deal this
product makes everywhere else.

**On whether this needs Roger.** HALT-CONSULT trigger 3 names "schema-breaking change to
`FinancialInputs`." I ruled this is **not** one, and I am recording the reasoning so a Guardian can
check it rather than guess: no field is added, removed, renamed or retyped; the JSON wire shape is
unchanged; serialization is unchanged; every currently-valid deal still validates (verified across
34 golden cases and both shipped bundles); and the change is trivially reversible. It narrows the
*rejection surface only*, which is the whole point. It still lands with a `CHANGELOG.md` entry and a
`src/schemas/README.md` update, because a config that used to be accepted and now loud-fails is a
user-visible change and this project stamps those.

**Out of scope, noted:** `InputsLoader.load` does not format `FinancialInputs` validation errors the
way `_revalidate_run` formats run-option errors (`inputs.py:225-234`), so a rejected price will
still surface as a raw pydantic error at the CLI. That is the same defect class as (e). If OI.1 and
OI.3 land in the same wave, reuse one formatter for both. If not, backlog it — do not invent a
second one.

---

## (d) Horizon `le=50` → `le=100` (OI.2) — RATIFIED

**DECISION: Ratified. Raise `RunOptions.horizon` to `Field(10, ge=1, le=100)`
(`src/inputs/inputs.py:74`). 100 accepted, 101 rejected, RED tests pin both.**

### Reasoning

- **Source:** `docs/plans/ROADMAP_TRACKER.md:134` (row 11, marked *Founder-ratified*) ·
  `docs/plans/MISSION_5_adjoint_differentiation.md:487` · and — the part that actually decides it —
  **`docs/manual testing/MISSION_4_MANUAL_TESTING.md:540-579`**, which is genuine pre-Mission-5
  provenance: Mission 4 Case 8 fixed an `OverflowError` in the IRR solver at 5,000 units × horizon
  99 and recorded, in Roger's own manual test, *"a 99-year ground lease is a real financial
  instrument."*
- **Aligned with:** solo-dev cap (one constraint); reuse-first; loud fail on misconfig.
- **This is a real instrument, not a benchmark artifact.** 99-year ground leases and leaseholds are
  ordinary — including on leased land in Canada. A user modelling one is blocked today at 50 for no
  reason anyone chose. Mission 4 already did the engineering that makes 99 work; leaving the cap at
  50 means the fix is real and unreachable.
- **The benchmark is NOT the justification, and I want that on the record.** The 5,000u/100y row
  calls `run_financial_model` directly and never goes through `RunOptions`. "The code is exercised
  at 100 so the schema should say 100" is confusing a stress ceiling with a product envelope. If
  the 99-year lease case did not exist, I would decline this. It does, so I ratify it.

**On whether the tool should render a 100-year projection at all — the honesty question, answered
rather than dodged.** Under the shipped configuration, **no guardrail reads past Year 10**: DSCR,
spread, CoC and cap-floor are purchase/Year-1 figures, IRR is the 10-year IRR, and `cf_all` — the
only metric that scans the whole horizon — is off (`REQUIRE_POSITIVE_CF_ALL = False`). So years 11
through 100 add rows to a table and change **nothing** about the verdict. That is not a reason to
refuse them; it is the reason they are safe. The report already titles the section
`{horizon}-Year Pro Forma` (`generator.py:783-785`), so the horizon the user chose is on the page,
and the growth rates that generate it are their own stated inputs. The tool is doing arithmetic on
assumptions the user supplied and labelled as such. It is not forecasting.

**Trade-off accepted:** a 100-year table is compounded extrapolation, and Year 100's `est_value` is
a number no one should plan around. It is the user's assumption, compounded exactly as they stated
it, under a heading that names the horizon. That is the same bargain every other row in the pro
forma makes.

**Scope control:** raise the constraint and update the field description to say the cap is
deliberate and where it came from (long-dated ground leases). **Do not** add report copy, a
long-horizon caveat block, or a second warning in this open item. If someone thinks the pro forma
needs a horizon caveat, that is a separate proposal with its own review — not a rider on a
one-constant change.

---

## (e) CLI out-of-range-horizon message (OI.3) — DECIDED, with text

**DECISION: An out-of-range or unparseable horizon exits non-zero with one clean line on stderr and
no traceback, at every entry point that can set the horizon.**

### Current behaviour, reproduced at this baseline

`python main.py --config … --horizon 75` → an 18-line double traceback
(`pydantic_core.ValidationError` chained into `ValueError`) whose only useful content is the last
two lines. The message itself is already fine; the presentation is not.

Two further holes found while checking, both the same defect and both fixed here:

1. **`main.py:256`** — the no-config fallback does `horizon = args.horizon or 10`, bypassing
   `RunOptions` entirely. That path accepts any integer, including 500 and negatives.
2. **`src/inputs/inputs.py:305-311`** — `AIREAL_HORIZON=abc` is caught and **silently ignored**
   ("Ignore bad value; keep validated cfg.horizon"). The user asks for one horizon, gets another,
   and no line of output says so. That is worse than a traceback, and it is precisely the class of
   defect Mission 4's PV.2 was opened to kill.

### The text

Exactly these, on **stderr**, via `raise SystemExit(msg)` — reusing the convention already at
`main.py:200`, not inventing an exit path:

```
Forecast horizon must be between 1 and 100 years; got 101.
```

```
AIREAL_HORIZON must be a whole number of years between 1 and 100; got 'abc'.
```

```
Forecast horizon must be between 1 and 100 years; got 101 (run.horizon in data/my_deal/inputs.json).
```

Rules for the implementer, so this does not need a second decision:

- **One line. No traceback. No "Error:" prefix. No stack, no `ValidationError` repr, no URL.**
  Exit code 1, matching `main.py:200`.
- **The bounds in the message are read from the `RunOptions.horizon` field constraints, never
  typed as literals.** When the cap moves again, the message moves with it or the change is
  incomplete. A message that can disagree with the rule it describes is a future lie.
- **The three sources are distinguishable** — bare (CLI flag), named env var, named config key with
  its file path — because "which of the three things I set is wrong" is the actual question the user
  has.
- **`AIREAL_HORIZON` stops being silently ignored.** Unparseable or out of range, it fails loudly
  with the message above. Loud fail on misconfig is a documented invariant; a silently discarded
  override is a report produced at a horizon the user did not choose.
- **`main.py`'s no-config branch validates through the same path.** One function, both branches. A
  second, unvalidated door is how this was reachable in the first place.

### Reasoning

- **Source:** `docs/plans/ROADMAP_TRACKER.md:134` ("polish to one clean line") ·
  `docs/manual testing/MISSION_5_MANUAL_TESTING.md:298-313` (Case 9's acceptance target, whose
  suggested wording I have adopted almost verbatim — reuse, not invention) ·
  `CHANGELOG.md:26` (Mission 4's precedent: "Replaces a silent data corruption with a loud error").
- **Aligned with:** loud fail on misconfig; plain, honest, direct voice.
- **Trade-off accepted:** the raw pydantic error is more diagnostic for a developer. It is being
  hidden from a CLI user who cannot act on it. `--horizon` has exactly one constraint and the
  message states it, so nothing diagnostic is lost.
- **Scope note:** the env-var and no-config-branch fixes are two small additive branches on the
  same field, not a new work item. They are in because "an out-of-range horizon behaves properly"
  is not true if two of the three ways to set one still misbehave.

---

## Escalations to Roger

**None of the five calls requires escalation.** All five resolved against documented sources or
measurements taken for this memo. Recorded so the absence is deliberate rather than assumed:

- (a) was already ruled on values by the Guardian; I ratified it as a product call and added the
  5e-10 effective-silence figure. No new ground.
- (c) touches `FinancialInputs`, which is a HALT-CONSULT-adjacent surface. I ruled it not
  schema-breaking and recorded the full reasoning above precisely so that ruling is checkable. **If
  either Guardian disagrees that a lower-bound addition is non-breaking, that is a legitimate VETO
  and I will take it back to Roger rather than argue it.**
- (d) reverses nothing: the charter, the roadmap tracker and Mission 4's own manual test all point
  the same way, and the pre-Mission-5 provenance for the 99-year-lease justification is real
  (unlike the 9.4e-8 figure, which is not).

**Two things Roger should see, which are findings rather than decisions:**

1. **A second unsourced figure in the Mission 5 planning set.** `D1_ad_design.md:37` and `:296`
   state "only 4 guardrails are live and failing at the gate-limit scenario," attributed to "the
   Mission 4 record." Measured at the benchmark's own gate-limit workload: **5 live, 3 failing.**
   Same class as the 9.4e-8 provenance problem the Guardian already conditioned on (C4). D.1's
   ruling survives the correction; the sentence does not.
2. **"Up to seven live guardrails" is wrong across five shipped documents and one source comment**
   (`src/market/recourse.py:135`, `src/market/README.md:28`, `:70`, `README.md:291`,
   `CHANGELOG.md:10`). Maximum live under the shipped configuration is **six**, and six requires a
   user-configured `cap_rate_floor`. Docs-only, but it is the derivation printed next to a
   threshold, and this repo has now had three separate doc-audit findings of exactly this shape.

## Backlog opened by this memo (NOT Mission 5)

- Lower bounds on the non-money numeric fields: `amort_years`, `io_years`, `year_to_refi`, and the
  six cap-rate fields. **Warning for whoever picks this up:** `amort_years` is **not** `ge=1`. The
  `all_cash_deal` golden case ships `amort_years = 0` with `down_payment_rate = 1.0`, and a naive
  floor there would break a committed case and force an anchor supersession. Measure before you
  bound — which is the whole lesson of this mission.
- A shared CLI formatter for `FinancialInputs` validation errors, so (c)'s new rejections read like
  (e)'s message instead of a pydantic dump.
- Naming `chief_strategist.py:315`'s bare `3`, if it does not land as the SHOULD under (b).

— Principal Founder Proxy, speaking for Roger Booto Tokime · Gate D · 2026-08-31
