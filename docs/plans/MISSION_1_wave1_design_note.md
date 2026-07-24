# Mission 1 · Wave 1 — Scenario Intelligence Design Note

_Design only. No production code lands with this note._
_Author: staff-python-engineer · Date: 2026-07-24 · Base: `main` @ `e4716df`_
_Reviewers (Gate 1): staff-code-reviewer + staff-financial-result-interpreter; principal-principles-guardian VETO check._

---

## 0. Purpose & honesty framing

Compose the already-tested `src/market` scenario engine (snapshot → hypothesis grid → rejector →
renormalized priors) with the **frozen** finance engine so a run can emit **prior-weighted scenario
outcomes** (DSCR, CoC, cash flow, IRR) as an opt-in report section.

**Honesty statement — FIXED VERBATIM STRING.** The report must render this exact block, byte-for-byte
identical on every run, adjacent to the scenario numbers (no paraphrasing, no per-run interpolation):

> **About these scenarios.** These are deterministic what-if calculations over your own market and
> financing assumptions — the same underwriting math re-run on perturbed copies of your inputs. They
> are **not** predictions, forecasts, or live market data. The scenario weights ("priors") are
> **heuristic penalty weights**, not calibrated probabilities, so the weighted figures are what-if
> quantiles over a rule-based grid — not statistical percentiles of real-world outcomes. Every number
> here is exactly reproducible from your inputs and the fixed seed.

This string is a module-level constant (Wave 2) rendered verbatim; because it is fixed text it does
not threaten the default-off byte-identical guarantee (it only appears when scenarios are ON).

**Priors are heuristic weights, not probabilities.** The `prior` on each hypothesis is a normalized
**penalty weight**: the generator down-weights jointly-extreme corners
(`src/market/hypotheses.py:143-148`) and the rejector applies a soft ×0.8 penalty to incoherent
opex-vs-rent combos (`src/market/rejector.py:105`), then everything renormalizes to sum 1. These are
rule-of-thumb weights, **not** empirical or calibrated probabilities. Consequently "prior-weighted
p25" (§4) is a **what-if quantile over a heuristic grid**, not a statistical 25th percentile of
real-world outcomes. The report states this next to the numbers (see the verbatim block above).

**Reuse-first note.** `src/core/advisor/scenarios.py` already has a `Scenario`/`apply_scenario`
utility — but it is explicitly an *approximate toy* that does **not** re-run the engine
(`src/core/advisor/scenarios.py:41-95`, note string at line 94 "does not re-run engine"). Mission 1
is the honest counterpart: it perturbs a **copy** of `FinancialInputs` and re-runs
`run_financial_model`. We do **not** extend or reuse the advisor toy; they serve different products
(advisor knobs vs. market-context grid). This is called out so Gate 1 does not read it as duplication.

---

## 1. Delta → `FinancialInputs` mapping table

`MarketHypothesis` delta axes (`src/schemas/models.py:342-347`) are stored as **fractions** and are
documented as *absolute changes* (e.g. `rent_delta=0.02` == +200 bps == +0.02 in fraction space —
`src/schemas/models.py:342`, `src/market/README.md:86`). The frozen engine consumes **fractions**
everywhere. **There is no percent or bps representation anywhere in the data path** — the only
"bps" language is prose in field descriptions. Therefore every mapping below is **fraction + fraction**
with **no numeric unit conversion**, except the one **sign flip** on vacancy (call-out in §2).

Baseline anchoring rule (see §1a): deltas are applied **additively to the user's own
`FinancialInputs` value** (the value the engine actually consumes), not to the `MarketSnapshot`
value. `cap_rate_delta` has no stored user field, so it anchors on the **engine-derived purchase cap
from untouched inputs** — still additive to the value the engine itself would use, consistent with
the rule above (§1b).

| Hypothesis delta | Unit (as stored) | Target `FinancialInputs` field | file:line | Transform (applied to a **copy**) | Unit handling | Engine consumers |
|---|---|---|---|---|---|---|
| `rent_delta` | fraction (Δ rent growth) | `income.rent_growth` | `models.py:86` | `new = income.rent_growth + rent_delta` | fraction+fraction, no conversion | rent/other-income growth `engine.py:156` → GSI/GOI/NOI/CF/DSCR/IRR |
| `expense_growth_delta` | fraction (Δ opex growth) | `opex.expense_growth` | `models.py:58` | `new = opex.expense_growth + expense_growth_delta` | fraction+fraction, no conversion | per-line opex growth `engine.py:161-175` → NOI/CF/DSCR/IRR |
| `interest_rate_delta` | fraction (Δ APR) | `financing.interest_rate` | `models.py:27` | `new = clamp(financing.interest_rate + interest_rate_delta, 0.0, 1.0)` | fraction+fraction, no conversion; clamp to field bounds `ge=0,le=1` | amortization rate `engine.py:113`, refi re-amort `engine.py:264`, `spread_vs_rate` `engine.py:138` → debt service/CF/DSCR/CoC/IRR (§3) |
| `cap_rate_delta` | fraction (Δ cap rate) | `market.cap_rate_purchase` (**see §1b**) | `models.py:110` | `new = base_cap + cap_rate_delta`, where `base_cap` = **engine-derived purchase cap from untouched inputs** = `market.cap_rate_purchase` if set else `NOI_Y1_base / purchase_price`; then `clamp(new, floor=0.03)` | fraction+fraction, no conversion | valuation `engine.py:135-138,197-198`, refi exit-cap fallback `engine.py:252`, terminal equity `engine.py:293` → est_value/IRR/equity-multiple (not NOI/DSCR/CF) |
| `vacancy_delta` | fraction (Δ vacancy) | `income.occupancy` (**sign flip, §2**) | `models.py:82` | `new_occupancy = clamp(income.occupancy − vacancy_delta, 0.0, 1.0)` | fraction+fraction; **subtract** because occupancy = 1 − vacancy | occupancy `engine.py:158` → GOI/NOI/CF/DSCR/CoC/IRR |
| `str_viability` | bool | **none** (**no clean target, §7 metadata only**) | — | not applied to engine; carried into `ScenarioOutcome` for narration | n/a | none — informational flag only in this wave |

All perturbations are produced on a **deep copy** of `FinancialInputs`
(`fi.model_copy(deep=True)` then `model_copy(update=…)` on the nested submodels) so the original
inputs — and the frozen engine — are untouched.

### 1a. Baseline anchoring decision (additive-to-user)

Two candidate semantics:
- **(A) additive-to-user** — `engine_field = user_value + delta`. The user's own assumption is the
  anchor; the grid explores ± around it. Honest reading: "what if rents grow 200 bps faster than
  *you* assumed."
- **(B) snapshot-overwrite** — `engine_field = snapshot_value + delta`, discarding the user's value.
  Asserts the market snapshot supersedes the user's input.

**Decision: (A) additive-to-user** for `rent_delta`, `expense_growth_delta`, `interest_rate_delta`,
`vacancy_delta`. Rationale: (1) the deterministic core consumes the `FinancialInputs` value, so
anchoring there keeps the base scenario close to the user's headline; (2) it never silently
contradicts a number the user typed; (3) it matches the honesty framing ("perturb *your*
assumptions"). `cap_rate_delta` cannot use (A) cleanly — see §1b.

### 1b. `cap_rate_delta` — anchoring on the engine-derived purchase cap  ✅ RESOLVED (Gate 1 finance-semantics)

The engine's purchase cap is **derived**, not always stored:
`cap_rate_purchase = market.cap_rate_purchase if provided else NOI_Y1 / purchase_price`
(`engine.py:135-137`). When the user leaves `cap_rate_purchase = None` (the sample does —
`main.py:96`), there is **no stored field to add a delta to**; the cap emerges from NOI.

**Resolution (ratified by finance-semantics review):** anchor the delta on the **engine-derived
purchase cap computed from the UNTOUCHED inputs**, mirroring the engine's own derivation
(`engine.py:135-137`):

```
base_cap = market.cap_rate_purchase            if market.cap_rate_purchase is not None
         = NOI_Y1_base / purchase_price         otherwise      # NOI_Y1_base from untouched inputs
cap      = clamp(base_cap + cap_rate_delta, floor=0.03)         # concrete floor, NOT ">0"
# on the perturbed copy:  market.cap_rate_purchase = cap
```

- **Runner obligation:** the scenario runner must compute `NOI_Y1_base` **once** from the untouched
  inputs (Year-1 GOI − Year-1 total OPEX, exactly as `engine.py:120-134`) to obtain `base_cap`
  **before** perturbing any copy. This can be read straight off a single baseline
  `run_financial_model(untouched_inputs)` call (`PurchaseMetrics.cap_rate`, `engine.py:141`) so we
  reuse the engine's own math rather than re-deriving it — no core edit.
- **Concrete floor `0.03`, not literal `">0"`:** matches the rejector's cap lower bound
  (`rejector.py:12-15`, `0.03 ≤ cap`). A ≤0 (or near-0) cap would make `est_value = NOI / cap`
  nonsense/explosive at `engine.py:198`. The `0.03` floor is the honest guard; no upper clamp is
  needed here (the rejector already bounds cap ≤ 0.12).

**Why this is the honest anchor:**
- The `cap_rate_delta = 0` ("base") scenario reproduces the headline purchase cap **exactly**
  (`base_cap` == the engine's own derived cap), so `est_value == purchase_price` identically at
  Year 1 and the scenario base ties out to the headline forecast — **no "scenario-base ≠ headline"
  divergence** (the earlier caveat is removed).
- It retains full cap → IRR / refi / terminal-value sensitivity (`engine.py:198`, `:252`, `:293`).
- It is consistent with the additive-to-user rule (§1a) — we add the delta to the value the engine
  itself would use — rather than contradicting it with an external snapshot cap.

---

## 2. Vacancy handling (sign flip + clamp)

- `FinancialInputs` has **no vacancy field**; it models **economic occupancy** (`income.occupancy`,
  `models.py:82`, `ge=0,le=1`, engine reads it at `engine.py:158`). The snapshot/hypotheses model
  **vacancy** (`vacancy_delta`, `models.py:346`; `snapshot.vacancy_rate`, `models.py:276`).
- Identity: `occupancy = 1 − vacancy`. A **positive** `vacancy_delta` must **lower** occupancy.
- **Transform:** `new_occupancy = clamp(income.occupancy − vacancy_delta, 0.0, 1.0)`.
- Clamp range **[0.0, 1.0]** to satisfy the field constraint and guard against extreme grid corners.
  (The rejector already bounds `snapshot.vacancy_rate + vacancy_delta ∈ [0, 0.20]`
  — `src/market/rejector.py:18-21` — so pre-clamp values are already sane; the clamp is defensive.)
- `income.bad_debt_factor` (`models.py:83`) is **not** touched — it models collections loss, a
  distinct concept from vacancy. Flagged so reviewers don't expect vacancy to hit two knobs.
- **This sign flip is the single highest unit-drift risk in the mapping.** A golden test in Wave 2
  must pin: `vacancy_delta = +0.02` on `occupancy = 0.95` ⇒ `occupancy = 0.93`, and NOI falls.

---

## 3. Interest-rate handling (composition with financing)

- Target: `financing.interest_rate` (`models.py:27`, APR fraction, `ge=0,le=1`).
- **Composition: additive** — `new = clamp(financing.interest_rate + interest_rate_delta, 0.0, 1.0)`.
- The engine re-derives everything rate-dependent from this single field, so we perturb **only** the
  rate and let the frozen engine recompute:
  - Initial amortization schedule uses `rate=f.interest_rate` (`engine.py:113`).
  - **IO / amortization terms are untouched.** `amort_years` (`models.py:28`) and `io_years`
    (`models.py:29`) stay as the user set them; the delta shifts *rate only*. The engine's
    `amortization_schedule(loan0, rate=…, amort_years=…, io_years=…)` recomputes payment/interest/
    principal for the new rate over the *same* term structure — no scenario logic needed here.
  - Refi re-amortization also reuses `rate=f.interest_rate` (`engine.py:264`), so the post-refi
    schedule automatically reflects the perturbed rate — consistent with the honest reading "the
    whole deal is financed at the shocked rate."
  - `spread_vs_rate = cap_rate_purchase − interest_rate` (`engine.py:138`) and the spread warning
    (`engine.py:301`) move correctly with the perturbed rate.
- **Rate-shock disclosure (report requirement, item 5).** Because both the acquisition schedule
  (`engine.py:113`) and the refi schedule (`engine.py:264`) reuse the single `financing.interest_rate`
  field, an `interest_rate_delta` shock is applied to **both loans** — it **persists through the
  year-5 refinance and across the entire hold**. This is a real modeling assumption, not an
  incidental detail: the report must name it explicitly next to the rate-sensitive metrics ("a rate
  shock is applied to both the acquisition and refinance loans and holds for the full term"). No new
  refi-rate knob (YAGNI, and a second rate would require an engine change — forbidden).

### 3a. IO-period caveat (report requirement, item 4)

When `financing.io_years > 0` (`models.py:29`), Year-1 debt service is **interest-only**, so Year-1
**DSCR, CoC, and cash flow are flattered** (lower debt service than the post-IO amortizing years).
A **Year-1-based "downside"** (§4) can therefore **mask the post-IO amortization shock**: the metric
looks safe in Y1 precisely when the principal burden has not yet started. The sample has
`io_years = 0` (`main.py`), so this does not bite today, but scenarios run on **arbitrary** user
inputs. **Report requirement:** when any scenario's inputs carry `io_years > 0`, the scenario section
must surface a caveat that the Y1 metrics understate the eventual amortizing-period debt load.
Separately, the IRR and equity-multiple downside are **terminal-value / cap-dominated**
(`engine.py:293`), so their honesty is only as good as the cap anchor — which ties directly to §1b
(now anchored on the engine-derived cap, so scenario base == headline).

---

## 4. Downside statistic (definition + defensibility)  ✅ RESOLVED (headline = prior-weighted p25)

For each accepted hypothesis we run the engine once and read four headline metrics (plus equity
multiple for context):

| Metric | Source | Direction |
|---|---|---|
| DSCR (Y1) | `PurchaseMetrics.dscr` / `years[0].dscr` (`engine.py:208,278`) | higher = better |
| CoC (Y1) | `PurchaseMetrics.coc` (`engine.py:277`) | higher = better |
| Cash flow (Y1) | `years[0].cash_flow` (`engine.py:207`) | higher = better |
| IRR (10yr) | `FinancialForecast.irr_10yr` (`engine.py:296`) | higher = better |
| Equity multiple (context) | `FinancialForecast.equity_multiple_10yr` (`engine.py:297`) | higher = better |

All four headline metrics are **"higher is better,"** so the **downside** is always the **lower
tail**.

**Reported "downside" = prior-weighted p25** (25th weighted quantile of the outcome distribution,
weighting each accepted scenario by its normalized prior). Alongside it we report, per metric, a small
band for honesty and context: **prior-weighted p50 (the MEDIAN)**, **prior-weighted mean (the
EXPECTED value)**, **min** (absolute worst accepted), and **max**.

**Label discipline (item 2).** p50 is the **median**, not "expected." The **mean** is the expected
value. In both this note and the report, "expected" maps to the **mean**; the median is always labeled
"median" (or "p50"), never "expected." Where the report shows a single "expected" figure it renders
the **mean**; where it shows both, it labels them "mean (expected)" and "median (p50)" distinctly.
And per §0, all of these are **heuristic-prior-weighted what-if quantiles, not statistical
percentiles/means of real-world outcomes.**

**Weighted-percentile definition (deterministic):**
1. Pair each accepted scenario's metric value `vᵢ` with its normalized prior `wᵢ` (Σwᵢ = 1 ± 1e-12).
2. Sort pairs by `vᵢ` ascending; break ties by the hypothesis's lexicographic key
   (`rent_delta, expense_growth_delta, interest_rate_delta, cap_rate_delta, vacancy_delta,
   str_viability`) — the same key the rejector already sorts by (`rejector.py:155-167`), so ordering
   is stable and reproducible.
3. Accumulate cumulative prior `Cⱼ = Σ_{k≤j} w_k`.
4. p-quantile = the value `vⱼ` at the smallest `j` with `Cⱼ ≥ p` (p=0.25 for downside, 0.50 for
   median). This is the standard "lower-weighted-percentile / inverse-CDF" convention — no
   interpolation, so it is exactly reproducible in float.

**Why p25, not min:** the grid's worst corner is a **jointly-extreme, low-prior** combination
(the generator already *down-weights* joint extremes — `hypotheses.py:143-148`). Reporting the min
would let a single ~1%-prior tail dominate the headline and **overstate** risk. Prior-weighted p25 is
the defensible "reasonable bad case": it respects how plausible each scenario is (subject to the §0
caveat that priors are heuristic weights, not probabilities). We still surface `min` in the band for
full transparency, so nothing is hidden — the reader sees both the reasonable downside and the
absolute worst. **Ratified by finance-semantics review:** headline downside = prior-weighted p25;
`min` retained as context.

Edge cases: if exactly one scenario survives the rejector, p25 = p50 = mean = min = max = that value.
If **zero** survive (rejector can return empty — `rejector.py:92-99`), `ScenarioAnalysis` carries
`n_accepted = 0`, empty `outcomes`, `None` bands, and a note; the report renders "no admissible
scenarios" rather than fabricating numbers.

---

## 5. Snapshot source of truth

**Current reality:** there is **no** market-snapshot source wired anywhere. `FinancialInputs.market`
is `MarketAssumptions` (`models.py:107-119`) — cap-rate guardrails only (`cap_rate_purchase`,
`cap_rate_floor`, `cap_rate_spread_target`, `cap_rate_drift`); it has **none** of the six
`MarketSnapshot` fields (region, vacancy_rate, cap_rate, rent_growth, expense_growth, interest_rate —
`models.py:275-280`). `build_snapshot` already parses a `market` mapping (`src/market/snapshot.py:44-91`)
but nothing calls it, and `data/sample/inputs.json` has no `market` block (verified: grep found none).

**Design — source priority (loud-fail on misconfig, invariant #5):**
1. **Explicit `market` block** in the inputs JSON, parsed by the existing `build_snapshot(...)`
   (`snapshot.py:44`). This is the source of truth. Shape (fractions):
   ```json
   "market": { "region": "Moncton, NB", "vacancy_rate": 0.06, "cap_rate": 0.055,
               "rent_growth": 0.03, "expense_growth": 0.02, "interest_rate": 0.055 }
   ```
   Carried on `AppInputs` as an additive optional field (§6) — **not** added to the frozen
   `FinancialInputs`/schema.
2. **Fallback derivation** from `FinancialInputs` when no block is present (documented, deterministic):
   `region = "Unspecified"` (or listing address if available), `vacancy_rate = 1 − income.occupancy`,
   `rent_growth = income.rent_growth`, `expense_growth = opex.expense_growth`,
   `interest_rate = financing.interest_rate`, `cap_rate = market.cap_rate_purchase` **if set**.
3. **Loud fail:** if `--scenarios` is on AND there is no `market` block AND `cap_rate` cannot be
   derived (`market.cap_rate_purchase is None`), raise a clear `ValueError` at startup naming the fix
   (add a `market` block or set `market.cap_rate_purchase`). We do **not** silently invent a cap.

**Two distinct cap uses — do not conflate (reviewer note).** `snapshot.cap_rate` here feeds
`generate_hypotheses` / the rejector's cap **guardrail bounds** (`rejector.py:12-15`) and is subject
to the loud-fail above (we require the user to be explicit about the market cap for guardrails). This
is *separate* from the **perturbation anchor** in §1b (`base_cap = cap_rate_purchase else
NOI_Y1_base / purchase_price`), which drives the engine's valuation. The §1b `base_cap` is always
computable from the untouched inputs (NOI/price), so the perturbation itself never loud-fails; the
loud-fail governs only the snapshot/guardrail cap. Wave 2 may optionally reconcile the two by
defaulting `snapshot.cap_rate` to the same NOI-derived value, but that is not required by this note.

`scenario_runner` obtains the snapshot from this resolver (proposed helper, Wave 2), never from the
network (core-purity, invariant #3).

---

## 6. Opt-in surface (default OFF, byte-identical when off)

Follows the established `AIREAL_*` + `RunOptions` + CLI-override idiom
(`inputs.py:69-76,243-280`; `main.py:103-118`).

- **CLI:** `main.py` gains `--scenarios` as `action="store_true"`, `default=False`
  (mirrors existing boolean-ish flags). Passed through `with_overrides(...)`.
- **Env:** `AIREAL_SCENARIOS` — truthy (`1/true/yes/on`, case-insensitive) enables; anything else /
  unset = OFF. Parsed in `_apply_env_overrides` (`inputs.py:243`) into `run.scenarios`, matching how
  `AIREAL_ENGINE` etc. are handled.
- **Config:** `RunOptions.scenarios: bool = Field(False, …)` — **additive** field in
  `src/inputs/inputs.py` (`RunOptions`, `inputs.py:69-76`). This is *not* a change to
  `src/schemas/models.py`.
- **Precedence** (match existing): explicit CLI flag > env var > JSON `run.scenarios` > default False.
- **Byte-identical guarantee when OFF:** `main.py`/orchestrator only build the snapshot, call the
  market modules, run extra engine passes, and render the "Market Scenarios" report section **inside
  an `if run.scenarios:` branch**. With the flag off, none of that code executes, no market/scenario
  imports occur on the hot path, and `write_report(...)` is called with the same arguments as today →
  identical bytes. A dedicated "scenarios-off byte-identical" test pins this (charter DoD).

CLI/scripts: `main.py --scenarios` only. No new `[project.scripts]` entry (YAGNI — the three console
scripts are unrelated to this feature).

---

## 7. Additive result models (new Pydantic models, additive-only)

New models live in `src/schemas/models.py` **appended** (they cross the orchestrator→reports
boundary, so schema-first applies — invariant #2). Nothing existing is renamed/retyped/removed.
Rates/fractions throughout; money in the project's implicit currency.

```python
class ScenarioMetricBand(BaseModel):
    """Prior-weighted distribution summary for ONE metric across accepted scenarios."""
    model_config = ConfigDict(frozen=True, extra="ignore")
    p25:  float   # prior-weighted 25th quantile (the DOWNSIDE for higher-is-better metrics)
    p50:  float   # prior-weighted MEDIAN (NOT "expected")
    mean: float   # prior-weighted mean == the EXPECTED value
    min:  float   # absolute worst accepted (context/transparency)
    max:  float   # absolute best accepted
    # NOTE: all five are heuristic-prior-weighted what-if quantiles/moments, NOT
    # statistical percentiles/means of real-world outcomes (see §0 verbatim note).

class ScenarioOutcome(BaseModel):
    """One accepted hypothesis + the engine metrics it produced."""
    model_config = ConfigDict(frozen=True, extra="ignore")
    hypothesis: MarketHypothesis        # carries the deltas + prior + rationale + str_viability
    # applied engine inputs, for transparent audit of the perturbation (all fractions):
    rent_growth_applied:   float
    expense_growth_applied: float
    interest_rate_applied: float
    occupancy_applied:     float
    cap_rate_purchase_applied: float | None   # base_cap + cap_rate_delta, clamped floor 0.03 (§1b);
                                              # populated on every scenario run (loud-fail if underivable, §5)
    # engine outputs (money = currency units; ratios/returns = fractions):
    dscr_y1:              float
    coc_y1:               float
    cash_flow_y1:         float               # currency units
    irr_10yr:             float               # fraction
    equity_multiple_10yr: float               # multiple (x)

class ScenarioAnalysis(BaseModel):
    """Aggregate prior-weighted result for a run; rendered only when scenarios are ON."""
    model_config = ConfigDict(frozen=True, extra="ignore")
    snapshot:    MarketSnapshot
    seed:        int
    io_years:    int                          # financing.io_years from untouched inputs (invariant across
                                              # scenarios); drives the §7a #6 IO caveat (added in Wave 2)
    n_generated: int                          # hypotheses before rejector
    n_accepted:  int                          # after rejector (== len(outcomes))
    prior_sum:   float                        # ~1.0 (±1e-12); 0.0 if none accepted
    outcomes:    tuple[ScenarioOutcome, ...]  # deterministic lexicographic order
    dscr:              ScenarioMetricBand | None   # None iff n_accepted == 0
    coc:               ScenarioMetricBand | None
    cash_flow_y1:      ScenarioMetricBand | None
    irr_10yr:          ScenarioMetricBand | None
    equity_multiple_10yr: ScenarioMetricBand | None
    notes:       str | None                   # rejector notes / "no admissible scenarios"
```

`str_viability` (the axis with no engine target, §1) is preserved inside
`ScenarioOutcome.hypothesis.str_viability` for narration; it never touches the engine.

`write_report`/`generate_report` gain an optional keyword-only
`scenarios: ScenarioAnalysis | None = None` param (default None → today's signature/behavior
unchanged), default-off. (An `OrchestrationResult.scenarios` field was proposed here but **dropped at
Gate 2 per YAGNI** — `main.py` computes the `ScenarioAnalysis` and passes it straight to
`write_report`, so the orchestrator never carries it; a future crewai path can add it when it has a
real producer/consumer.)

**Proposed new modules (Wave 2, per charter):** `src/market/adapter.py` (delta→inputs copy) and
`src/market/scenario_runner.py` (snapshot → generate → reject → per-scenario engine run → aggregate).
Placing them in `src/market` keeps the perturbation seam with the module that owns hypotheses and
respects layering (`market` and `core/finance` both depend only on `schemas`; `market` importing
`core.finance.engine` is a one-way, network-free, deterministic composition — no core edit).

### 7a. "Market Scenarios" report-section rendering requirements (BINDING)

These are hard requirements on `src/core/reports/generator.py` (Wave 2). They encode the
finance-semantics report caveats (items 3/4/5) and the founder-proxy binding conditions (items 6/7).

1. **Structurally separate artifact (item 7).** The "Market Scenarios" section is a distinct,
   clearly-headed section *after* the headline forecast — never interleaved with headline numbers.
   Its heading and lead-in make clear it is a what-if overlay, not the base underwriting. With
   scenarios OFF the section is absent entirely (§6 byte-identical guarantee).
2. **Verbatim honesty block (item 8, §0).** Render the fixed verbatim "About these scenarios" block
   (§0) at the top of the section, byte-for-byte identical every render.
3. **Priors-are-heuristic caveat (item 3).** Immediately adjacent to any prior-weighted figure
   (p25/p50/mean bands, top-N-by-prior table), state that priors are heuristic penalty weights, not
   probabilities, and that the weighted figures are what-if quantiles over a rule-based grid. (The
   verbatim block covers this; the section must not present a weighted number *without* that context
   visible on the same screen/section.)
4. **Label discipline (item 2).** Columns/labels read "downside (p25)", "median (p50)",
   "mean (expected)", "min", "max". Never label p50 "expected."
5. **Cap-sensitivity disclosure adjacent to cap-driven metrics (item 7).** Next to IRR and equity
   multiple, note they are terminal-value/cap-dominated (`engine.py:293`) and that the scenario base
   reproduces the headline cap exactly (§1b) so those figures move only with the modeled cap delta.
6. **IO-period caveat (item 4).** If any scenario's inputs have `io_years > 0`, render a caveat that
   Year-1 DSCR/CoC/CF are interest-only-flattered and understate the post-IO amortizing debt load.
   (Omit the caveat when all scenarios have `io_years == 0`, e.g. the sample.)
7. **Rate-shock disclosure (item 5).** Next to rate-sensitive metrics, state that an
   `interest_rate_delta` is applied to **both** the acquisition and refinance loans and holds for the
   full term.
8. **`str_viability` rendering (item 6, founder-proxy binding).** If the STR flag is shown at all, it
   MUST carry an explicit **"not modeled — narrative flag only"** label and must never appear in a
   position that implies it moved a financial metric (no STR column beside DSCR/CoC/CF/IRR without
   that label). Preferred default: **omit `str_viability` from the numeric scenario table entirely**
   and, if surfaced, place it in a clearly separated "narrative flags (not modeled)" note. The
   engine never consumes it (§1, §7).
9. **Empty-set rendering.** When `n_accepted == 0`, render "no admissible scenarios under the current
   guardrails" plus the rejector `notes`; never fabricate bands (§4 edge case).

---

## 8. Determinism guarantees

Byte-identical output across runs (fixed seed) rests on a chain of already-deterministic steps:

1. **Seed flow:** `generate_hypotheses(snapshot, seed=SEED)` (`hypotheses.py:62`). The seed is
   threaded through to `HypothesisSet.seed` and into `ScenarioAnalysis.seed`. **Note for reviewers:**
   the current generator does **not** actually randomize on `seed` — the grid is a fixed Cartesian
   product and the seed is "reserved for future tie-breaking" (`hypotheses.py:65`,
   `README.md:103`). So determinism does **not** depend on the RNG; we still pass and record a fixed
   `SEED` (propose `42`, the existing default) for forward-compatibility and provenance.
2. **Generation** is a pure Cartesian grid with fixed bands/ordering (`hypotheses.py:78-125`) and a
   final lexicographic sort (`hypotheses.py:191-203`).
3. **Rejector** applies deterministic hard/soft rules and re-sorts lexicographically
   (`rejector.py:154-167`); **priors renormalize to sum exactly 1.0 (±1e-12)** (`rejector.py:121-152`;
   README asserts `abs(sum − 1.0) < 1e-12` at `README.md:70`). `ScenarioAnalysis.prior_sum` records it.
4. **Engine** is pure: no randomness, no wall-clock, no network in the compute path (invariant #3) —
   same inputs ⇒ same `FinancialForecast`.
5. **Aggregation** (weighted percentiles) uses the no-interpolation inverse-CDF with a **total order**
   (value asc, then hypothesis lexicographic key) — no floating tie ambiguity (§4).
6. **Rendering** must format floats with fixed precision (match existing report formatting) so bytes
   are stable.

Determinism test (Wave 2/3): run twice with the same seed ⇒ identical serialized `ScenarioAnalysis`
and identical report bytes; assert `abs(prior_sum − 1.0) ≤ 1e-12` on the accepted set.

---

## 9. Open questions / risks — status after Gate 1 finance-semantics review

**Finance-semantics review (staff-financial-result-interpreter): 6/6 now resolved.**

1. ✅ **RESOLVED** — Downside = **prior-weighted p25** (headline), `min` retained as context. (§4)
2. ✅ **RESOLVED** — `cap_rate_delta` anchors on the **engine-derived purchase cap from untouched
   inputs** (`market.cap_rate_purchase` else `NOI_Y1_base / purchase_price`), delta added, clamped
   floor `0.03`; scenario base == headline; "scenario-base ≠ headline" caveat removed. (§1, §1b)
3. ✅ **RESOLVED / confirmed** — Additive-to-user anchoring for rent/opex/rate/vacancy is the honest
   reading; cap uses the engine-derived base (still additive to the value the engine would use). (§1a, §1b)
4. ✅ **RESOLVED** — Single-rate-field behavior accepted; rate shock hits both acquisition and refi
   loans and holds for the full term — now a **named report disclosure** (item 5). (§3)
5. ✅ **RESOLVED / confirmed** — `bad_debt_factor` stays untouched by `vacancy_delta`. (§2)
6. ✅ **RESOLVED (label + honesty)** — p50 = median, mean = expected (item 2); priors are heuristic
   weights not probabilities, stated verbatim in-report (items 3, 8); IO-period Y1-flattering caveat
   added (item 4). (§0, §3a, §4, §7)

**Founder-proxy (scope): OK.** Binding conditions folded into §7a report requirements —
`str_viability` renders as "not modeled — narrative flag only" or is omitted (item 6); scenario
section is a structurally separate artifact with cap-sensitivity disclosure adjacent to IRR/equity
(item 7); honesty note is a fixed verbatim string (item 8).

**Remaining Gate 1 steps (still open):**

- **staff-code-reviewer** sign-off, focusing on:
  - New models in `src/schemas/models.py` are strictly additive (nothing renamed/retyped/removed);
    boundary object belongs in `schemas`. (§7)
  - Runner/adapter placement in `src/market`; `market → core.finance` is an acceptable one-way,
    network-free composition (both pure, schema-only deps). (§7)
  - No new runtime deps: weighted percentile is pure Python (no numpy on this path). (§8)
- **principal-principles-guardian VETO check**, focusing on:
  - Honesty of scenario semantics (verbatim note, heuristic-priors disclosure, IO/rate/cap caveats).
  - Determinism preserved (fixed seed → byte-identical; priors sum to 1 ± 1e-12).
  - Loud-fail resolver (raise, no silent default) satisfies invariant #5; fallback derivation
    (vacancy = 1 − occupancy, etc.) is honest. (§5)
  - Default-off byte-identical guarantee holds. (§6)

---

## 10. Binding Wave 2 conditions (Gate 1 exit — verified at Gate 2)

Gate 1 cleared 2026-07-24: finance-semantics ✅, founder-proxy ✅, staff-code-reviewer ✅ (SIGN OFF),
principal-principles-guardian ✅ (PASS, no veto). The following are **binding on Wave 2** and will be
re-checked at Gate 2.

**From staff-code-reviewer (engineering advisories):**
- C1. Add the new `scenarios` param **keyword-only** (after `*`) to **both** `write_report` and
  `generate_report` — `generate_report` has a positional `title_override` before `*`
  (`generator.py:507-513`), so a trailing-positional param would break call sites. Keyword-only keeps
  every existing call byte-identical.
- C2. The baseline `run_financial_model(untouched_inputs)` pass (for `base_cap`, §1b) plus per-scenario
  passes live **strictly inside `if run.scenarios:`** — the scenarios-OFF hot path adds zero engine
  passes and zero market imports; the byte-identical-off test must assert exactly this.

**From principal-principles-guardian (VETO conditions — any failure is a Gate 2 veto):**
- G1. The §0 verbatim honesty block ships as a module-level constant, rendered byte-for-byte, no
  per-run interpolation.
- G2. The scenarios-OFF byte-identical test is implemented and green; `write_report(..., scenarios=None)`
  provably alters zero output bytes.
- G3. Every §7a caveat renders under its trigger — IO-period caveat when any scenario has `io_years > 0`;
  rate-shock-both-loans disclosure; cap-sensitivity note adjacent to IRR/equity multiple; priors-are-
  heuristic caveat visible on the same section as any weighted figure. A weighted number without that
  context on-screen is a veto.
- G4. `str_viability` omitted from the numeric table by default, or if shown carries the literal
  "not modeled — narrative flag only" label; never in a column implying it moved a metric.
- G5. Per-scenario `cap_rate_purchase_applied` is shown (clamp visible, not hidden); the downside column
  is labeled "downside (p25)", not a generic "worst case".
- G6. No copy implies the recorded `seed` drives scenario *variation* (provenance only while the
  generator RNG is inert).
- G7. No new runtime dependency (weighted percentile stays pure stdlib) — load-bearing for the
  solo-dev cap and the Research & Education license (charter #5).

**Non-blocking (optional future additive docs pass, NOT a Wave 2 requirement):** tighten the
`MarketHypothesis.prior` docstring (`src/schemas/models.py:348`, currently "Prior probability weight")
toward "heuristic prior weight" so the schema contract and the honest report copy tell the same story.

---

## Constraints honored (self-check)

- **Deterministic core untouched:** zero edits to `src/core/finance/`; scenarios perturb **deep
  copies** and re-run `run_financial_model`. (§1, §7)
- **Schema additive-only:** new `ScenarioMetricBand` / `ScenarioOutcome` / `ScenarioAnalysis`
  appended; `RunOptions.scenarios` added in `src/inputs`; `OrchestrationResult` /`write_report` gain
  defaulted optional params. Nothing renamed/retyped/removed. (§6, §7)
- **Default-off byte-identical:** all scenario work gated behind `run.scenarios`; off ⇒ identical
  bytes. (§6)
- **Honesty:** fixed **verbatim** report note (§0); priors disclosed as heuristic weights not
  probabilities; IO / rate-shock / cap-sensitivity caveats required in-report (§3, §3a, §7a);
  `str_viability` labeled "not modeled" or omitted (§7a). Scenarios are what-ifs over user
  assumptions — not predictions, not live data.
- **No new runtime deps:** stdlib-only aggregation; reuses existing `src/market` + frozen engine. (§8)
- **YAGNI:** no UI, no live data, no LLM, no new console script, no second rate knob, no reuse of the
  advisor toy. (§0, §3, §6)
