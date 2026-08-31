# Mission 4 — Discovery Spec: Actionable Recourse ("What would have to change?")

_Task D.1 (Discovery). Written spec only — **zero production code**. Nothing under `src/` or
`tests/` was touched to produce this document. All `path:line` anchors below were re-verified
against the tree at `main @ bfdf565` (branch `mission/4-actionable-recourse`) on 2026-08-29, in the
`airedeal` conda env. Where the charter's assumptions did not survive contact with the actual code,
that is called out explicitly under **§0 Discovered drift** — read that section first._

---

## §0. Discovered drift from the charter (read this first)

The charter (`docs/plans/MISSION_4_actionable_recourse.md`) says plausibility is judged "using the
machinery Mission 1 shipped (`reject_unrealistic` / the snapshot bounds)." Two things surprised me
once I read `src/market/rejector.py`, `src/market/hypotheses.py`, `src/market/adapter.py`, and
`src/core/finance/engine.py` line-by-line, and one seam is simply missing:

1. **`reject_unrealistic` bounds five *market-condition deltas* — none of which are the four
   recourse levers.** `MarketHypothesis` carries `rent_delta` (a change to the **rent *growth*
   rate**, not a Year-1 rent *level*), `expense_growth_delta` (same shape, for OPEX growth),
   `interest_rate_delta`, `cap_rate_delta`, and `vacancy_delta`. Of the four recourse levers, only
   **interest rate** has a literal one-to-one axis. **Purchase price**, **rent per unit/month**,
   and **annual operating costs** have *no* axis on `MarketHypothesis` at all — they are absolute,
   one-time level changes, not growth-rate deltas. Reusing `reject_unrealistic` for those three
   verbatim is a category error, not "the machinery already exists." §3 below designs the actual
   integration: a **derived cap-rate-delta proxy** (real reuse, for two of the three) plus a
   lever-native magnitude fallback (new, small, and said so honestly).
2. **`InvestmentThesis` does not expose *which* of the seven guardrails failed.** `synthesize_thesis`
   (`src/agents/chief_strategist.py:137`) computes `dscr_ok`, `spread_ok`, `irr_ok`, `coc_ok`,
   `cf_y1_ok`, `cf_all_ok`, `no_cap_floor_breach` as **local variables** (`:172-179`) and returns
   only `verdict: str`, `rationale: list[str]`, `levers: list[str]` — free text. Recourse needs the
   seven booleans on *every* perturbed re-run, and there is no seam that returns them today. §6
   below proposes the fix and both options are laid out for Gate D to bless.
3. **`resolve_snapshot` (`src/market/scenario_runner.py:47`) cannot back the plausibility check in
   the case where it would matter most.** Its market-block-less fallback raises `ValueError` unless
   `inputs.market.cap_rate_purchase` is already set — but that is exactly the case where price/
   rent/opex levers **do not move the cap rate at all** (see §1), so a real snapshot cap is needed
   precisely when `cap_rate_purchase is None`, which is precisely when `resolve_snapshot` cannot
   build one without an explicit `market` block that recourse (running with no CLI flags, unlike
   `--scenarios`) cannot assume exists. §3 designs a narrower, always-available derivation instead.

None of this blocks the mission; all three are resolved below with concrete, low-blast designs.
Flagging them now because two prior missions "found charter path drift" and this is that drift.

---

## §1. The four levers, and the lever → guardrail map

### 1.1 Levers, and the exact `FinancialInputs` field each perturbs

| Lever (machine name) | What it means | Field(s) perturbed | Direction searched |
| --- | --- | --- | --- |
| `rent_per_unit_month` | A uniform dollar increase applied to every unit's Year-1 rent | `income.units[i].rent_month` for every `i` (add the same Δ to each; **not** `income.rent_growth`, which is a different, untouched field) | increase only (0 → +bound) |
| `purchase_price` | Negotiate a lower contract price | `financing.purchase_price` (single scalar) | decrease only (0 → −bound) |
| `interest_rate` | Negotiate/shop a lower rate | `financing.interest_rate` (fraction [0,1]) | decrease only (0 → −bound) |
| `annual_opex` | An aggregate operating-cost cut, spread proportionally | **every** line item of `opex` (`insurance, taxes, utilities, water_sewer, property_management, repairs_maintenance, trash, landscaping, snow_removal, hoa_fees, reserves, other`), each scaled by the same factor `1 − cut/total_opex_y1`; **not** `opex.expense_growth`, which stays untouched | decrease only (0 → −bound) |

Rationale for "proportional scaling" on `annual_opex`: the lever is stated as one aggregate dollar
figure ("$460 less"), but `OperatingExpenses` has 12 line items. Picking one item to cut
arbitrarily would be a fabricated claim about *which* vendor bid improved; scaling every non-zero
line item by the same factor is the only choice that doesn't invent a specific negotiation story,
and it composes cleanly with a single bisection scalar (the aggregate cut, or equivalently the
scale factor).

Rent and opex only ever *help* every guardrail (more NOI is never bad); price and rate cuts only
ever help too (per §2's monotonicity discussion) — hence "one direction only" above. This also
means the search space is a single non-negative scalar per lever, not a signed one.

### 1.2 The live seven guardrails (confirmed against `chief_strategist.py:172-179`, `:236`, `:240`)

| Guardrail (machine name) | Local variable in `chief_strategist.py` | Live by default? |
| --- | --- | --- |
| `dscr` | `dscr_ok` | always |
| `spread` | `spread_ok` | always |
| `irr` | `irr_ok` | always |
| `coc` | `coc_ok` | always |
| `cf_y1` | `cf_y1_ok` | **yes** — `REQUIRE_POSITIVE_CF_Y1 = True` (`:52`) |
| `cf_all` | `cf_all_ok` | **no** — `REQUIRE_POSITIVE_CF_ALL = False` (`:51`); when off, `cf_all_ok` is forced `True` and `chief_strategist.py` never even emits a rationale line for it (`:206-208` guard). Recourse must mirror that silence: **skip `cf_all` entirely while the flag is off** — there is nothing failing to explain. |
| `cap_floor` | `no_cap_floor_breach` | **only when `market.cap_rate_floor is not None`.** When the floor is unset, the guardrail is trivially `True` forever (`chief_strategist.py:190-211`'s own documented "SILENCE" case) — recourse must skip it too. |

So in the *shipped default configuration* exactly **6 of the 7** guardrails are ever live
(`cf_all` is off); `cap_floor` is additionally conditional per-deal on whether the user set a
floor. Recourse iterates only over guardrails that are (a) live per the module constants above and
(b) actually failing on this forecast — a passing guardrail gets no recourse row at all.

### 1.3 Lever → guardrail reachability (confirmed by reading `engine.py:94-318`, not by re-running)

`cap_rate_purchase` (line 135-137) is computed **once**, from Year-1 numbers only, as
`mkt.cap_rate_purchase if not None else noi_y1/purchase_price` — it never depends on
`interest_rate`, and (when overridden) never depends on `purchase_price`/rent/opex either. That one
fact drives the whole reachability table:

| Lever ↓ / Guardrail → | `dscr` | `spread` | `irr` | `coc` | `cf_y1` | `cf_all` | `cap_floor` |
| --- | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| `rent_per_unit_month` | ✅ | ✅* | ✅ | ✅ | ✅ | ✅ | ✅* |
| `purchase_price` | ✅ | ✅* | ✅ | ✅ | ✅ | ✅ | ✅* |
| `interest_rate` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **❌ structurally hopeless** |
| `annual_opex` | ✅ | ✅* | ✅ | ✅ | ✅ | ✅ | ✅* |

`✅*` = reachable **only when `market.cap_rate_purchase is None`** (cap computed from NOI/price);
when the user has overridden the cap rate with a fixed number, `spread` and `cap_floor` become
**exogenous constants** that no lever except a hypothetical direct cap-rate negotiation can move —
this is a *second*, runtime-only structurally-hopeless condition, and it must be **detected, not
assumed** (see §2's probe step): the implementation re-runs at the lever's search bound and checks
whether `purchase.cap_rate` actually moved from baseline; if it is bit-for-bit identical, the pair
is hopeless for this deal, independent of the static table above.

**The one *statically* hopeless pair, true for every deal regardless of configuration:**
`interest_rate ↔ cap_floor`. Interest rate never appears in the cap-rate formula at all — no
amount of rate negotiation can ever cure a cap-rate-floor breach. This pair is excluded before any
engine call is made (a documented fact about the engine's data-flow, not a formula inversion of a
verdict guardrail).

`irr` deserves a note: it is reachable by every lever (all of them ultimately move the Year-1
cash-flow stream and/or the terminal value via `cap_rate`), but IRR is a root of a cash-flow
polynomial with no closed form — nobody would attempt to "invert the IRR guardrail" in the first
place, which is exactly why the re-run discipline is not optional for it.

---

## §2. Bounded-search strategy

### 2.1 Reachability probe before any bisection (the "check, don't assume" step)

For every `(lever, guardrail)` pair that is not statically excluded (§1.3's `interest_rate ↔
cap_floor`):

1. The **baseline** re-run is already in hand (it's the forecast the verdict was computed from) —
   this is probe #1, free.
2. Re-run the engine **once** at the lever's most generous bound (§2.2) — probe #2, the only new
   engine call this step costs.
3. Read the guardrail's underlying metric (e.g. `purchase.dscr`, `purchase.cap_rate`, the
   `"cap rate below floor"` warning string) off both forecasts:
   - **Identical within floating-point noise** (`abs(delta) < 1e-9` for numeric metrics; string
     membership unchanged for `cap_floor`) → the guardrail **does not move at all** with this
     lever, for this deal (this is where the runtime cap-override case from §1.3 gets caught, in
     addition to the static exclusion). Mark `structurally_hopeless=True`, do not bisect.
   - **Moves in the helpful direction** (toward passing) → proceed to bisection (§2.3).
   - **Moves in the unhelpful direction, or the bound itself does not flip the guardrail** → do
     **not** assume a fix exists further out; this pair gets `closes_guardrail=False,
     structurally_hopeless=False` — an honest "searched and found nothing within the bound," which
     feeds the honest-null definition (§5). The implementation must not extrapolate past the bound
     and must not assume monotonicity continues to hold outside it.

This probe is what "checks monotonicity rather than assumes it," per the charter's explicit ask —
the implementation never hard-codes "raising rent always helps `coc`" as an assumption baked into
the search; it *observes* the direction on this specific deal's own re-run before trusting it.

### 2.2 Bisection bounds per lever ("generous but finite")

Two **different** numbers are defined per lever, and they serve different jobs — conflating them
was the single easiest mistake to make while writing this spec, so the distinction is called out
explicitly:

- **Search bound**: how far the bisection is *allowed* to look for a flip point. Deliberately wide
  — wide enough that if a fix exists at all via this lever alone, the bracket contains it. Being
  "too generous" here costs nothing but a few extra engine calls; being too narrow silently
  produces false honest-nulls.
- **Plausibility threshold** (§3): a *much* tighter, product-judgment number that decides whether
  the flip point found is worth showing without a flag. A found fix can sit inside the search bound
  and still get flagged as unrealistic.

| Lever | Search bound (from baseline) | Justification | Tolerance |
| --- | --- | --- | --- |
| `rent_per_unit_month` | 0 to **+100%** of current average rent/unit/month | Doubling rent is already absurd for an existing rent roll; anything a real fix needs will sit far inside this, and the honest-null path (§5) catches the rest. | $1.00/month |
| `purchase_price` | 0 to **−40%** of current price | A cut beyond ~40% off asking stops being "the same deal being renegotiated" in any real sense; generous enough to contain any realistic flip point. | $100 |
| `interest_rate` | 0 to **−300 bps**, floored at 0% | Comfortably wider than the ±100–200 bps the *existing* market-hypothesis generator already treats as its own most extreme band (`hypotheses.py` `DEFAULT_BANDS["interest_rate_delta"] = (-0.01, 0.00, 0.02)`, i.e. the codebase's own working definition of "a big rate move"), so the search bracket is guaranteed not to be the binding constraint. | 1 bp (0.0001) |
| `annual_opex` | 0 to **−40%** of current total Year-1 opex | Symmetric with the price bound; a 40%-across-the-board vendor rebid is already at the edge of credible, wide enough to contain real fixes. | $50/year |

**Numeric bounds/tolerances above are my proposal, not a settled policy** — they are exactly the
kind of number `principal-founder-proxy`'s Gate D "bounded product call" exists to confirm or
adjust. They are concrete so implementation is not blocked, not because I have unilateral authority
over them.

### 2.3 The bisection itself

Standard bisection on the already-probed bracket `[0, bound]` (in the lever's own perturbation
units), re-running `run_financial_model` on a **deep copy** of `FinancialInputs` at each candidate
(exactly the `perturb → deep copy → re-run` shape of `scenario_runner.run_scenarios` step (d),
`src/market/scenario_runner.py:126`, and `build_baseline_outlook`,
`src/orchestrators/crew.py:65`). Reads the guardrail's own boolean off the re-run (see §6 for how)
and narrows the bracket toward the smallest lever change that flips it. **No guardrail formula is
solved algebraically for the unknown lever value at any point** — every candidate is a full engine
re-run.

**"Flip" per guardrail — with the inclusive-boundary trap named explicitly**, because every one of
these bars is `>=`, not `>`, in `chief_strategist.py`:

- `dscr`: `y1.dscr >= MIN_DSCR_Y1` (`:172`) — a deal landing at exactly 1.20 clears it.
- `spread`: `purchase.spread_vs_rate >= spread_target_for(market)` (`:173`) — landing exactly at
  target clears it.
- `irr`: `forecast.irr_10yr >= MIN_IRR_10YR` (`:174`).
- `coc`: `purchase.coc >= MIN_COC_Y1` (`:176`) — the source comment there is explicit: "inclusive
  at the bar... a deal landing on 3.00% clears it."
- `cf_y1` / `cf_all`: `cash_flow >= 0.0` (`:177-178`) — exactly zero clears it.
- `cap_floor`: absence of the `"cap rate below floor"` warning string
  (`chief_strategist.py:179`'s exact predicate, mirrored verbatim — see §6) — this one has **no**
  numeric bar to be inclusive or exclusive *about*; it is a re-run-and-recheck-the-warning-list
  test by construction, which is itself the strongest illustration of "there is no formula here to
  invert."

Because every numeric bar is inclusive, the bisection's stopping rule must find the smallest lever
value such that the guardrail's own `>=` test is satisfied **at that value when actually re-run**
— not an open-interval infimum. Concretely: iterate while `hi − lo > tolerance`; at the end, report
`hi` (the smaller-magnitude-change side that is confirmed, by a real re-run, to satisfy the bar) as
`target_value`, never `lo` (which is confirmed to still fail). This guarantees the reported fix,
if re-run once more by a skeptical reader, actually clears the bar — never an "off by the last
tolerance step" false positive.

### 2.4 Worst-case engine-re-run count (for `PF.1` to measure against)

Per non-excluded `(lever, guardrail)` pair: **1 reachability probe + up to `N` bisection re-runs**,
where `N = ⌈log2(bound_width / tolerance)⌉`. Computed per lever from §2.2's numbers, `N` ranges
7–13 in practice (e.g. rent: `⌈log2(1450/1)⌉ = 11` for a $1,450 average rent; price:
`⌈log2(160,000/100)⌉ = 11` for a $400k deal's 40%-of-price window; rate: `⌈log2(0.03/0.0001)⌉ = 9`;
opex: `⌈log2(5,600/50)⌉ = 7` for a $14k opex base). Using `N=15` as a defensive round number per
pair:

- **Excluded pairs**: exactly 1 (`interest_rate × cap_floor`), always, at zero engine-call cost.
- **Worst case** (a pathological deal failing all seven live guardrails, though the verdict
  arithmetic (`chief_strategist.py:240`) makes that a deep DECLINE, not a near-miss): `4 levers × 7
  guardrails − 1 excluded = 27 pairs × (1 + 15) = 432` engine re-runs for one report.
- **Typical case** (a real CONDITIONAL, 1–2 failing guardrails): `4 levers × ~1.5 guardrails ≈ 6
  pairs × 16 ≈ 96` engine re-runs.

Formula for `PF.1`: `n_pairs × (1 + ⌈log2(bound_width / tolerance)⌉)`, `n_pairs ≤ 27`. Early-exit
once `hi − lo ≤ tolerance` (deterministic — no randomness or wall-clock is introduced by
terminating early) will make the typical case cheaper than this worst-case bound in practice.

---

## §3. The rejector integration point

### 3.1 Why literal reuse only reaches two of the four levers, and how

`reject_unrealistic` (`src/market/rejector.py:54`) takes a `HypothesisSet` of `MarketHypothesis`
(five deltas: `rent_delta`, `expense_growth_delta`, `interest_rate_delta`, `cap_rate_delta`,
`vacancy_delta`) and a `MarketSnapshot`, and returns the survivors + a renormalized/soft-penalized
set. Its **hard bounds**, read straight from the function:

- `interest_rate_delta − cap_rate_delta <= 0.02` (`_rates_vs_cap_ok`)
- `snapshot.cap_rate + cap_rate_delta ∈ [0.03, 0.12]` (`_cap_bounds_ok`)
- `snapshot.vacancy_rate + vacancy_delta ∈ [0.00, 0.20]` (`_vacancy_bounds_ok`)
- `rent_delta >= 0.03 ⟹ vacancy_delta <= 0.015` (`_rent_vs_vacancy_ok`)

Only two of these axes correspond to anything recourse computes:

**Interest rate lever — real, literal reuse.** Build
`MarketHypothesis(rent_delta=0, expense_growth_delta=0, interest_rate_delta=−delta, cap_rate_delta=0,
vacancy_delta=0, str_viability=False, prior=1.0, rationale="recourse:interest_rate")`
(`delta` is the magnitude the bisection found; the hypothesis's sign convention matches
`MarketHypothesis.interest_rate_delta`'s "absolute change" semantics), wrap it in a one-item
`HypothesisSet`, and call the real `reject_unrealistic(hset, snapshot)`. `plausible =
bool(result.items)`.

**Purchase price / rent / opex — real reuse *only when the cap rate is not overridden*, via a
derived `cap_rate_delta`.** When `market.cap_rate_purchase is None`, these three levers move
`purchase.cap_rate` (§1.3), and that movement is exactly what `_cap_bounds_ok` is built to judge
("does the implied yield still look like a market cap rate"). So: read `new_cap =
<flip-point re-run>.purchase.cap_rate` and `base_cap = <baseline forecast>.purchase.cap_rate`
(**both already-computed values off real engine runs, never derived by formula**), build
`cap_rate_delta = new_cap − base_cap`, and run the **same** one-item-`HypothesisSet` through
`reject_unrealistic`. When the cap rate *is* overridden, `new_cap == base_cap` identically (the
§2.1 probe already caught this as `structurally_hopeless` for the `spread`/`cap_floor` guardrails
specifically — this proxy simply degenerates to a no-op for those two, and is skipped for them; it
is never applicable to `dscr`/`irr`/`coc`/`cf_y1`/`cf_all` in the first place, since those don't
route through `cap_rate` at all).

### 3.2 The `MarketSnapshot` recourse actually has available (§0 item 3, resolved)

`reject_unrealistic` needs a real `MarketSnapshot`. Recourse cannot assume `--scenarios` was used
or that a `market` block was supplied, and `resolve_snapshot`'s fallback (`scenario_runner.py:47`)
raises exactly when `cap_rate_purchase is None` — the one case the price/rent/opex proxy needs a
snapshot cap for. **Resolution: recourse builds its own minimal, always-available derived
snapshot**, structurally similar to `resolve_snapshot`'s fallback branch but using the
**already-computed** `baseline_forecast.purchase.cap_rate` (always present, override or not)
instead of `inputs.market.cap_rate_purchase` (sometimes `None`):

```
MarketSnapshot(
    region="recourse-derived",
    vacancy_rate=1.0 - inputs.income.occupancy,
    cap_rate=baseline_forecast.purchase.cap_rate,   # engine-computed, always available
    rent_growth=inputs.income.rent_growth,
    expense_growth=inputs.opex.expense_growth,
    interest_rate=inputs.financing.interest_rate,
    notes="Derived for recourse plausibility only; not the scenario-analysis snapshot.",
)
```

This is a **new**, small, additive helper next to (not calling into) `resolve_snapshot` — the two
functions solve genuinely different preconditions and conflating them would either break recourse's
always-on requirement or silently narrow scenario_runner's stricter contract. `HypothesisSet.seed`/
`snapshot_region` are carry-through record-keeping fields only (not read by any bound check), so
placeholders (`seed=0`, `region="recourse-derived"`) are safe and introduce no non-determinism.

### 3.3 Flag-don't-remove: where the reason string comes from (Roger's decision 1)

The accept/reject **decision** always comes from the real `reject_unrealistic` call above — never
locally re-derived. The **reason string** shown to the reader, though, needs to be more specific
than `HypothesisSet.notes`'s generic `"All hypotheses rejected by guardrails."` (that string never
says *which* bound tripped). So the reason is composed by checking, purely for messaging, which of
`reject_unrealistic`'s own **documented, numeric, already-public** constants
(`0.02` rate-vs-cap spread, `[0.03, 0.12]` cap bounds, `[0.00, 0.20]` vacancy bounds, `0.03`/`0.015`
rent-vs-vacancy) the synthetic hypothesis actually violates, and naming it: e.g. *"a price cut this
large pushes the implied cap rate to {cap:.2%}, outside the [3.00%, 12.00%] range this project
treats as a realistic market cap rate."* This is bound-checking arithmetic on **already-public
constants of a plausibility heuristic**, not the money-math verdict guardrails invariant #6 forbids
inverting — it never substitutes for the real `reject_unrealistic` call, which remains the sole
source of truth for accept/reject, and a parity test pins that the two never disagree.

**Lever-native magnitude fallback** (always applied, in addition to the above, since two of the
four levers have no rejector axis at all and even the cap-proxy degenerates when cap is
overridden): flag if `|relative_change|` (§4.1's normalization) exceeds — **proposed defaults,
Gate D confirms**: rent 10%, price 15% (independent of the cap-proxy check above), opex 20%. When
both a rejector-based and a magnitude-based reason apply, both are shown; the flag itself is a
single boolean (`plausible=False`), never a silent drop, and the found `target_value`/`delta` are
still populated exactly as computed — a flagged lever is never blanked out, only annotated.

---

## §4. Multi-failure ordering: "cheapest single fix"

### 4.1 Cross-currency normalization

**Rule: cheapest = smallest `|delta| / baseline_value`, i.e. the smallest percentage move away from
what is already underwritten, using each lever's own current value as its own baseline.** Applied
uniformly to all four levers:

- `rent_per_unit_month`: `|Δrent| / current_average_rent_per_unit_month`
- `purchase_price`: `|Δprice| / current_purchase_price`
- `interest_rate`: `|Δrate| / current_interest_rate` (e.g. a 50 bp cut off a 5.50% rate is a 9.1%
  relative move — the same yardstick as the other three, just computed on the rate number itself)
- `annual_opex`: `|Δopex| / current_total_annual_opex`

**Why this and not a dollar-cost-of-the-ask common currency** (e.g. "what price cut alone would buy
the same fix as this rate cut" as a universal converter): that approach needs an *extra* bisection
per lever purely for comparison, and arbitrarily privileges price as the "unit of account" for no
principled reason. The percent-of-own-baseline rule needs no extra engine calls (both numbers are
already known once a lever's flip point is found), treats all four levers symmetrically, and — not
incidentally — is already how Roger's own illustrative example expresses three of the four levers
("a 3.1% increase," "2.4% below asking"). This is a **discovery-level judgment call**, flagged
explicitly for `principal-founder-proxy` to confirm at Gate D, with a concrete default so
implementation is not blocked.

### 4.2 The ordering rule itself

Among **all** `(lever, guardrail)` rows with `closes_guardrail=True`:

1. Prefer `plausible=True` rows over flagged ones (leading with something already flagged as
   unrealistic would undercut the "actionable" framing) — but if every closing row for every
   guardrail happens to be flagged, lead with the cheapest flagged one anyway (decision 1: never
   silently omit), clearly labeled with its reason.
2. Within that preference tier, pick the smallest `relative_change` (§4.1).
3. Ties (identical `relative_change` to floating-point precision) break on a fixed lexicographic
   order over `(lever, guardrail)` machine names — deterministic, never on insertion order or a
   dict's iteration order.

That row becomes `RecourseAnalysis.cheapest`.

### 4.3 "Flag that other gaps remain" — for free, no extra engine calls

At the `cheapest` row's flip point, the **same** `FinancialForecast` used to confirm the flip is
already sitting in memory. Recourse checks the **other** currently-failing guardrails against that
*same* re-run (their own `>=` tests, per §2.3/§6) and records which ones happen to close as a side
effect (`also_closes`) and which remain (`RecourseAnalysis.remaining_after_cheapest =
failing_guardrails − {cheapest.guardrail} − also_closes`). This costs zero additional engine calls
— it is reading fields that are already computed, never a second guess about what "probably" also
improved.

---

## §5. The honest-null definition (Roger's decision 3)

**Per-row null**: a `(lever, guardrail)` row is null when the §2.1 probe finds the guardrail moves
in the helpful direction but the §2.3 bisection never crosses the bar within the §2.2 search bound
— `structurally_hopeless=False, closes_guardrail=False, target_value=None, delta=None,
relative_change=None`. This is not an error; it is the honest report that *this specific lever,
alone, within a generous bound, does not close this gap* — a different lever, or a combination, may
still.

**Whole-analysis null** (`RecourseAnalysis.honest_null = True`): **every** row for **every**
currently-failing guardrail is either structurally hopeless or a per-row null as above — i.e.
`cheapest is None`. This is Roger's "well, it is what it is. We tell them" case, and the report
must say so in plain language (copy owned by `staff-report-experience-designer`, cleared by the
guardian; out of scope for this spec beyond the structured signal it renders from).

**Rendering implication, tying into determinism (binding constraint 5)**: a **CONDITIONAL** verdict
always gets a rendered "What would have to change?" section, even when `honest_null=True` — a
CONDITIONAL is by construction a near-miss, and "nothing realistic closes it" is itself the
informative content decision 3 asks for. For a **DECLINE**, I propose rendering the section **only
when `honest_null=False`** (i.e. at least one genuine, non-hopeless fix — plausible or flagged —
exists for at least one failing guardrail); an all-null DECLINE (a deal failing so badly that no
single lever within any generous bound helps) renders **no** section, preserving byte-identical
report output for that case and avoiding a wall of nulls that adds no decision-relevant content.
**This DECLINE-rendering threshold is a product call, not a settled decision** — flagged explicitly
for Gate D; the CONDITIONAL-always-renders rule is the one I am confident does not need
confirmation, since it flows directly from the charter's own framing.

---

## §6. The additive schema shape

### 6.1 A schema-level seam gap this spec must surface (§0 item 2)

`InvestmentThesis` (`src/schemas/models.py:282`) does not expose the seven guardrail booleans —
only free-text `rationale`/`levers`. Recourse needs them on **every** perturbed re-run (to know
which guardrail(s), if any, a candidate closes). Two ways to get them, for Gate D / the
implementer to choose between (this spec does not decide it, since it is blast-surface-adjacent):

- **Option A (recommended default, zero existing-file diff):** the new recourse module computes
  the seven booleans itself, by importing `MIN_DSCR_Y1, MIN_SPREAD, MIN_IRR_10YR, MIN_COC_Y1,
  REQUIRE_POSITIVE_CF_Y1, REQUIRE_POSITIVE_CF_ALL, spread_target_for` from `chief_strategist.py`
  (already-public names) and mirroring the exact seven `>=`/warning-membership tests at
  `chief_strategist.py:172-179` verbatim. **Duplication risk is real but bounded and pinned**: a
  cross-check test (`test_recourse_guardrail_checks_match_synthesize_thesis`) asserts, over a
  battery of representative forecasts, that recourse's local seven-booleans agree with
  `synthesize_thesis`'s actual verdict via the same fail-count arithmetic
  (`num_fails >= 3 or (cap_floor breach and dscr fail)`, `chief_strategist.py:236-240`) — any future
  threshold or logic change that isn't mirrored turns this test **red immediately**, not silently.
  Costs zero lines of diff to any shipped file.
- **Option B:** extract the seven comparisons out of `synthesize_thesis` into a small, pure,
  additive helper (e.g. `guardrail_checks(forecast, market) -> GuardrailChecks`) that
  `synthesize_thesis` itself then calls, with a golden/parity test asserting `synthesize_thesis`'s
  output is byte-identical before/after the refactor. Lower duplication risk, non-zero (but
  behavior-preserving, non-threshold-touching) diff to `src/agents/chief_strategist.py`.

I recommend **Option A** as the lower-blast default (true zero diff to any existing shipped file,
the extra risk fully covered by a mandatory parity test), but this is exactly the kind of
seam-choice Gate D exists to bless, not something Discovery should unilaterally lock in.

### 6.2 `RecourseLever`

One row per `(lever, guardrail)` search attempt. Mirrors `MarketHypothesis`/`ScenarioOutcome`'s
frozen, `extra="ignore"` shape (`src/schemas/models.py:388`, `:1213`).

```python
class RecourseLever(BaseModel):
    """
    One candidate single-lever fix for one currently-failing guardrail, found by re-running
    ``run_financial_model`` on a perturbed deep copy of ``FinancialInputs`` — never by inverting
    the guardrail's own formula (see src/market/recourse.py module docstring for why).
    """

    guardrail: Literal["dscr", "spread", "irr", "coc", "cf_y1", "cf_all", "cap_floor"] = Field(
        ..., description="Which of the seven live chief_strategist.py guardrails this row targets."
    )
    lever: Literal["rent_per_unit_month", "purchase_price", "interest_rate", "annual_opex"] = Field(
        ..., description="Which investor-movable input this row perturbs, holding all others fixed."
    )
    baseline_value: float = Field(
        ..., description="The lever's current value before perturbation, in its own native unit."
    )
    target_value: float | None = Field(
        None, description="The lever's value at the flip point. None when no flip was found (honest-null for this row)."
    )
    delta: float | None = Field(
        None, description="target_value - baseline_value, signed. None alongside target_value."
    )
    relative_change: float | None = Field(
        None, ge=0, description="abs(delta) / abs(baseline_value) — the cross-currency cheapness score (see §4.1). None when delta is None or baseline_value is 0."
    )
    closes_guardrail: bool = Field(
        ..., description="True iff a flip point was found within this lever's search bound (see §2.2)."
    )
    structurally_hopeless: bool = Field(
        ..., description="True iff the reachability probe (§2.1) found this guardrail's underlying metric does not move at all with this lever, for this deal (e.g. interest_rate vs. cap_floor, always; or any lever vs. spread/cap_floor when market.cap_rate_purchase is overridden)."
    )
    plausible: bool = Field(
        ..., description="True iff the plausibility check (§3) raised no flag. Always True when closes_guardrail is False (nothing to judge)."
    )
    plausibility_reason: str | None = Field(
        None, description="Human-readable reason when plausible is False (see §3.3). None otherwise."
    )
    also_closes: tuple[Literal["dscr", "spread", "irr", "coc", "cf_y1", "cf_all", "cap_floor"], ...] = Field(
        default_factory=tuple,
        description="Other currently-failing guardrails also closed by this same target_value, read off the same re-run (§4.3) at zero extra engine-call cost.",
    )

    model_config = ConfigDict(frozen=True, extra="ignore")
```

### 6.3 `RecourseAnalysis`

```python
class RecourseAnalysis(BaseModel):
    """
    Recourse ("what would have to change?") attached to a near-miss InvestmentThesis. Additive:
    lives beside InvestmentThesis, never inside it; InvestmentThesis.levers (free-text) is
    unchanged and is a different concept from the structured levers here.
    """

    verdict: str = Field(..., description="The InvestmentThesis.verdict this analysis is attached to (BUY never gets one).")
    failing_guardrails: tuple[Literal["dscr", "spread", "irr", "coc", "cf_y1", "cf_all", "cap_floor"], ...] = Field(
        ..., description="Machine names of the guardrails that failed on this forecast, in the fixed lexicographic order of §1.2's table, and for which recourse was attempted."
    )
    levers: tuple[RecourseLever, ...] = Field(
        ..., description="Every (lever, guardrail) row attempted, including structurally-hopeless and honest-null rows (flag/show, never silently drop)."
    )
    cheapest: RecourseLever | None = Field(
        None, description="The single lead recommendation per §4.2. None iff honest_null is True."
    )
    remaining_after_cheapest: tuple[Literal["dscr", "spread", "irr", "coc", "cf_y1", "cf_all", "cap_floor"], ...] = Field(
        default_factory=tuple,
        description="failing_guardrails minus {cheapest.guardrail} minus cheapest.also_closes (§4.3). Empty tuple when cheapest is None or fixes everything.",
    )
    honest_null: bool = Field(
        ..., description="True iff no row in `levers` has closes_guardrail=True — nothing realistic (within the search bounds) closes any failing guardrail (§5)."
    )

    model_config = ConfigDict(frozen=True, extra="ignore")
```

Both models are new, alongside `ScenarioAnalysis`/`MarketHypothesis`/`ScenarioOutcome`, nothing in
`src/schemas/models.py` renamed, retyped, or removed. `InvestmentThesis.levers` (`:287`) is
untouched — it is free-text, general-purpose "suggested actions," a different concept from the
structured, engine-verified `RecourseLever` here, per the charter's explicit instruction not to
overload it.

### 6.4 Threading it through (seam, not a new pipeline)

Mirrors the `baseline`/`scenarios` precedent exactly: `OrchestrationResult`
(`src/orchestrators/crew.py:48-62`, a dataclass) gains an additive `recourse: RecourseAnalysis |
None = None` field, computed in `run_orchestration` right after `thesis = synthesize_thesis(...)`
whenever the verdict is not `"BUY"`. `generate_report`/`write_report`
(`src/core/reports/generator.py:1520` and the `parts` list around `:1503`) gain an additive
`recourse: RecourseAnalysis | None = None` keyword, appended to `parts` exactly like
`scenarios` is today (`if scenarios is not None: parts.append(_render_market_scenarios(scenarios))`)
— `if recourse is not None: parts.append(_render_recourse(recourse))`. With no near-miss (`BUY`, or
an all-null DECLINE per §5), `recourse` stays `None` and report output is untouched, byte-for-byte.

---

## §7. The non-independence trap — concrete case, real numbers

### 7.1 Which lever/guardrail pair actually diverges, and why the others don't

I first tried to find divergence on `dscr`/`spread`/`cap_floor` for the `purchase_price` lever, and
they are **exact** — no divergence to demonstrate. Here is why, confirmed by reading
`engine.py:94-318` and `amortization.py:26-38`: `amortization_payment(principal, rate, years)` is
**exactly proportional** to `principal` (`r*principal/(1-(1+r)^-n)`, no additive term), and
`loan0 = purchase_price*(1-down_payment_rate)` is linear in price with `down_payment_rate` held
fixed. So `debt_service(price)` is exactly linear in `price`, `noi_y1` does not depend on price at
all, and therefore `DSCR(price) = noi_y1 / (price*(1-down_rate)*k)` is an **exact, closed-form
hyperbola** with no hidden coupling — a naive single-formula inversion for `dscr` via `price` gets
the *right* number. Same story for `spread` and `cap_floor` (`cap_rate = noi_y1/price`, again
exact, no other variable feeds in).

**`coc` via `purchase_price` is where the coupling actually bites**, because
`coc = cash_flow_y1(price) / acquisition_cash(price)` has **both** the numerator *and* the
denominator depending on `price`:

- `cash_flow_y1(price) = noi_y1 − price*(1-down_rate)*k` (linear, via debt service)
- `acquisition_cash(price) = price*down_rate + closing_costs + capex_reserve_upfront +
  price*mortgage_insurance_rate` (also linear, when `down_payment_rate < 0.20` triggers MIP —
  `engine.py:107`)

A price cut shrinks **both** at once — exactly the charter's own words, "changes cash-in all at
once." The natural, tempting, wrong shortcut: invert the `coc` formula **holding
`acquisition_cash` fixed at its currently-computed baseline value** (i.e. forgetting a price cut
also shrinks the down payment and the MIP add-on). That is a real, plausible bug, not a straw man —
it is what "invert the guardrail formula" looks like in code for this specific guardrail.

### 7.2 Real numbers, from the real engine, on the real committed sample deal

Computed in the `airedeal` env against `data/sample_listings/36_kelly_moncton/inputs.json` (the
same deal `python main.py`'s determinism hash is pinned against) via a throwaway script, since
deleted per instructions. The deal's baseline (verified, matches the DECLINE described in this
task's baseline facts):

```
VERDICT: DECLINE
 - DSCR (Y1) is weak at 0.90 (< 1.20).
 - Cap-rate spread is thin at 0.85% (< 1.50%).
 - Projected IRR (10y) is 12.29% (>= 12.00%)      [passes]
 - Cash-on-cash (Y1) is weak at -6.41% (< 3.00%).
 - Year-1 cash flow is negative at $-2,946.
 - Purchase cap rate is 6.35% (>= the 5.00% floor you set)  [passes]
price=$399,900, down_payment_rate=0.05, mortgage_insurance_rate=0.04 (MIP active),
acquisition_cash=$45,991.00
```

Four of the six live guardrails fail (`dscr`, `spread`, `coc`, `cf_y1`) — a genuine multi-failure
DECLINE, useful ground for §4's "cheapest fix, flag the rest" too. Isolating the `purchase_price`
lever against the `coc` guardrail specifically:

**Naive** (invert `coc`'s formula, freeze `acquisition_cash` at the baseline $45,991.00):

```
price_naive = (noi_y1 - MIN_COC_Y1 * acq_cash_base) / ((1 - down_rate) * per_dollar_payment_factor)
            = $338,814.34   (claims a $61,085.66 cut off $399,900)

Real engine CoC actually produced at $338,814.34: 3.4073%  (naive believed it was hitting exactly 3.00%)
```

**True** (bisect on the real engine — deep-copy `FinancialInputs`, set `financing.purchase_price`,
re-run `run_financial_model`, read `purchase.coc`, repeat):

```
price_true  = $341,057.63   (a $58,842.37 cut — $2,243.29 SMALLER than the naive answer)
Real engine CoC at price_true: 3.0000%   (exactly the bar, per §2.3's inclusive-boundary rule)
```

**The divergence is $2,243.29 on the price recommendation itself** (a ~3.7% relative error on the
size of the ask), and it is fully explained by the mechanism in §7.1: at `price_true`, the *true*
`acquisition_cash` is `0.09 × $341,057.63 + $10,000 = $40,695.19` — **$5,295.81 smaller** than the
frozen $45,991.00 the naive formula used — so the naive calculation, holding "cash-in" artificially
high, has to demand a *larger* price cut than the deal actually needs to clear the 3.00% CoC bar.
In this specific direction the naive error happens to be conservative (it still clears the bar, just
asks for more than necessary — a real, quantifiable harm of its own: an investor could walk from a
negotiable deal believing a bigger price cut is required than actually is) rather than the
charter's illustrative "promises a fix that doesn't work" framing; both directions are possible
depending on which variable a given naive implementation freezes, and this spec does not need the
sign to match the charter's flavor text to be a valid, real, reproducible divergence.

### 7.3 The test this pins (must turn RED on reversion to formula inversion)

```python
def test_price_lever_coc_recourse_uses_true_engine_rerun_not_formula_inversion():
    """
    THE NON-INDEPENDENCE TRAP (Mission 4, discovery §7). Pins the recourse module to the
    re-run-the-engine discipline for the one lever/guardrail pair in this codebase where a
    naive single-formula inversion (coc = cash_flow/acquisition_cash, holding acquisition_cash
    fixed at baseline) provably diverges from re-running run_financial_model on the real,
    perturbed FinancialInputs.

    Fixture: data/sample_listings/36_kelly_moncton/inputs.json (the committed sample deal).
    Verified real numbers (computed independently of the implementation, see discovery §7.2):
      - naive (formula-inversion, denominator frozen at baseline): price = $338,814.34
      - true  (bisection on the real engine):                     price = $341,057.63
      - divergence: $2,243.29 -- comfortably outside the $100 price tolerance (§2.2)

    A regression to formula inversion returns $338,814.34 (or anything within $100 of it) and
    this test goes RED.
    """
    inputs = load_inputs("data/sample_listings/36_kelly_moncton/inputs.json")
    analysis = compute_recourse(inputs)  # the Mission 4 orchestration entry point

    row = _row_for(analysis, lever="purchase_price", guardrail="coc")
    assert row.closes_guardrail is True
    assert row.target_value == pytest.approx(341_057.63, abs=100.0)   # the TRUE re-run answer
    assert row.target_value != pytest.approx(338_814.34, abs=100.0)   # NOT the naive/inverted answer

    # Re-run the real engine at the returned target_value to prove the promise actually holds --
    # the point of the whole discipline: the reported number, checked once more, clears the bar.
    perturbed = inputs.model_copy(
        update={"financing": inputs.financing.model_copy(update={"purchase_price": row.target_value})}
    )
    forecast = run_financial_model(perturbed)
    assert forecast.purchase.coc >= MIN_COC_Y1
```

---

## Summary of open items for Gate D (none block writing the implementation spec above; all are
flagged inline where they arise)

1. **Seam choice for exposing the seven guardrail booleans** (§6.1, Option A vs. B) —
   blast-surface call.
2. **Plausibility threshold numbers** (§2.2 search bounds; §3.3 magnitude-flag percentages; §4.1's
   normalization rule) — bounded product call, concrete defaults given.
3. **DECLINE section-rendering threshold** (§5) — render only when `honest_null=False`; a product
   call, not settled by this spec.
4. **Honesty framing** ("WOULD close it, holding the other levers fixed," flag-don't-remove,
   cheapest-first-flag-the-rest, honest-null plain statement) is designed into the *data* here
   (§4–§5); the actual user-facing copy is `staff-report-experience-designer`'s job and
   `principal-principles-guardian`'s VETO, both out of this spec's scope by charter design.
