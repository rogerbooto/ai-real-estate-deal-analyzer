# D.1 — Algorithmic Differentiation Design Memo (Mission 5, Discovery)

**Branch** `mission/5-adjoint-differentiation` @ `87efd22` · **Date** 2026-08-31 ·
**Status** Discovery finding — no production code written; all prototypes live in the session
scratchpad (`scratchpad/d1/`: `bench_baseline.py`, `proto_dual.py`, `proto_reverse.py`,
`proto_extra.py`, `proto_dual4_opt.py`, `validate_second_deal.py`, `attribute_second.py`,
`check_d2_claims.py`). Every number below is reproducible by re-running those scripts under the
`airedeal` conda env
(`source /home/rtokime/anaconda3/etc/profile.d/conda.sh && conda activate airedeal`).

Incorporates the D.2 (performance) findings relayed mid-task: the numpy-substrate veto
(sanity-checked here, §1), the rent-`_perturb` copy dominance, the retracted-73 ms correction,
and D.2's four explicit asks (answered in §4a). **D.2's single flip question — can AD obtain
d(metric)/d(rent) without materialising a perturbed rent roll? — is answered YES, with
measurement, in §1a.**

All `path:line` anchors below were re-verified against the working tree at `87efd22`.
Charter/code deltas are in §7.

---

## 0. The problem shape (read out of the code, not assumed)

**Levers — 4** (`src/market/recourse.py:80` `LeverName`, applied by `_perturb`
`src/market/recourse.py:372`, all searched in one helpful direction, magnitude `t >= 0`):

| # | Lever | How `_perturb` applies `t` |
|---|-------|-----------------------------|
| 0 | `rent_per_unit_month` | `+t` added to **every** unit's `rent_month` |
| 1 | `purchase_price` | `financing.purchase_price − t` |
| 2 | `interest_rate` | `max(0.0, financing.interest_rate − t)` (kink at rate 0) |
| 3 | `annual_opex` | every one of the 12 opex lines × `(1 − t/total_opex_y1)` |

**Guardrail metrics — up to 7 live** (`GuardrailName`, `src/market/recourse.py:79`; scalar read
by `_metric` `src/market/recourse.py:166`; all computed in `_forecast_core`
`src/core/finance/engine.py:309` and surfaced through `ForecastMetrics`
`src/core/finance/engine.py:253`). Per the Mission 4 record, **only 4 are live and failing at
the gate-limit scenario** — the API consequence is handled in §3 (rows are metrics, consumption
is dynamic; nothing hardcodes 7).

| Guardrail | `ForecastMetrics` field | Where computed |
|-----------|--------------------------|----------------|
| `dscr` | `purchase_dscr` (== `year1_dscr` from the engine) | `noi_y1 / debt_service_y1`, year loop `engine.py:493` |
| `spread` | `spread_vs_rate` | `cap_rate_purchase − interest_rate`, `engine.py:395` |
| `irr` | `irr_10yr` | `irr(cashflows)` `engine.py:589` → `irr.py:188` (Brent root of NPV) |
| `coc` | `coc` | `cash_flow_y1 / acquisition_cash`, `engine.py:570` |
| `cf_y1` | `cash_flow_y1` | year-1 `noi − ds` |
| `cf_all` | `min_cash_flow` | `min` over the horizon's cash flows |
| `cap_floor` | `cap_rate` | `noi_y1 / purchase_price` (or the `market.cap_rate_purchase` override), `engine.py:392` |

Note for the API design: `guardrail_checks_from_metrics` tests `year1_dscr` while
`recourse._metric` reads `purchase_dscr` — the engine sets both from the same float, but the
docstring on `ForecastMetrics` explicitly keeps them separate. The AD API therefore exposes
**metric-named rows (8 float fields), not guardrail-named rows**, and lets the market layer keep
owning the guardrail↔metric mapping (see §3).

**Today's search cost, measured** (`bench_baseline.py`, near-miss fixture from
`tests/unit/test_recourse.py` — 4 units, 3 failing guardrails, 12 solved rows):

```
compute_recourse: light probes=132  full runs=13  rows=12  wall=15.7 ms
→ ~11 light probes (bound + ~10 bisection) + 1 full confirming run per (lever, guardrail) pair
```

One engine pass on the committed demo deal (2 units, horizon 10):
`forecast_metrics` ≈ **42 µs**, `run_financial_model` ≈ **68 µs** (min-of-7×2000,
`bench_baseline.py`). The charter's "~10–20 probes per pair" matches at the low end.

**Scale correction (from D.2, adopted):** the 5,000-unit/100-year baseline is **best 175–198 ms /
median 181–203 ms** per `compute_recourse` row; the "73 ms" figure in older briefs is retracted
and nothing here anchors to it. D.2's measured decomposition: engine forecast ≈ 20% of the row;
**≈ 74.5% is the 39 `rent_per_unit_month` `_perturb` calls** (~3,692–4,200 µs each — the
materialisation of ~195,000 short-lived `UnitIncome` objects per analysis, corroborated by
`docs/manual testing/MISSION_4_MANUAL_TESTING.md:513`), and ~35% of the row is GC churn
recoverable with zero finance-core diff. Everything in §4/§5 is weighed against *that* profile,
not against the engine-forecast share the mission premise assumed.

---

## 1. Forward vs reverse — decided by measurement

### Method

A throwaway slice (`proto_dual.py::forecast_slice`) replicates `_forecast_core`'s arithmetic
(no-refi, no-insights path — the demo deal's path) in lever-perturbation space
`t = (t_rent, t_price, t_rate, t_opex)`, exactly as `_perturb` applies them. Primal parity vs the
real engine at `t = 0`: **0 to 1 ulp on all 7 metrics, on both test deals**. That slice was then
run four ways:

1. **Forward dual** — operator-overloaded dual numbers carrying a 4-vector tangent
   (one pass = full Jacobian + all values). Variants: tuple-tangent, fixed-width unrolled
   `Dual4` with slots `d0..d3` (`proto_dual4_opt.py`), and numpy-array tangent
   (`check_d2_claims.py`, the D.2 sanity check).
2. **Reverse tape** — minimal Wengert tape (parents + local partials per op), one forward record
   + one backward sweep per output (6 metric sweeps + 1 IFT sweep for IRR) (`proto_reverse.py`).
3. **Float** — control.

### Measured numbers (demo deal, horizon 10; min-of-7 batches; reproduce with the scripts above)

| Pass | µs | × engine float pass |
|---|---|---|
| real `forecast_metrics` (float) | 41–43 | 1.0× |
| slice float (control for slice fidelity) | 48 | 1.15× |
| forward dual-4, tuple tangents — full Jacobian | 267–272 | **6.5×** |
| forward dual-1, tuple (single lever column) | 229 | 5.5× |
| **forward `Dual4`, unrolled slots — full Jacobian** | **173** | **4.1×** |
| forward dual-4, numpy-array tangents | 346 | 8.4× |
| reverse tape — full Jacobian (record + 7 sweeps) | 296 | 6.9× |

**numpy sanity check (D.2's veto, re-measured here rather than taken on faith):** on this
full-slice workload, numpy-backed tangents are 1.3× slower than tuple tangents and 2.0× slower
than the unrolled `Dual4` — same Jacobian to 0.0 relative difference. My penalty is milder than
D.2's 11.3× (theirs measured a different, smaller-op-count shape where numpy's per-op allocation
dominates even harder), but the direction is identical and decisive: **numpy is never faster at
width 4; the dual substrate is pure-Python scalars with unrolled float slots.** Mission 4's
"do not vectorise" verdict stands re-measured, and no dependency is needed or wanted.

Tape length: **443 entries per pass at horizon 10** (grows ~linearly with horizon and amort
years; ~4,000+ at horizon 100 — live memory and allocation cost per probe that forward mode
simply does not have, and fresh GC pressure exactly where D.2 showed GC is already ~35% of the
row).

Cross-validation: **reverse and forward Jacobians agree to ≤ 4.1×10⁻¹⁶ relative** (machine
epsilon) on all 28 entries including the IRR row.

### Correctness vs the real engine (not the slice)

Central finite differences of the **real** `forecast_metrics` + `_perturb` at `t = 0`:

- All 24 non-IRR entries: AD matches FD to **≤ 1.6×10⁻⁸ relative** (FD truncation dominates).
- IRR row: ~1×10⁻⁶ on the demo deal, up to 1.8×10⁻⁴ on the 4-unit near-miss deal — **fully
  attributed to Brent-tolerance noise in the FD baseline, not AD error**: re-doing the FD against
  a `tol=1e-13` root collapses the gap to 3.2×10⁻⁷ (demo) / 2.7×10⁻⁶ and 7.1×10⁻⁷ (near-miss)
  (`proto_extra.py`, `attribute_second.py`). The residual ~10⁻⁶ is the IFT-at-inexact-root error,
  O(tol) — see §2.

### Decision

**Forward mode, one pass, fixed-width pure-Python vector tangents (`Dual4`).** At 4 inputs ×
7–8 outputs:

- Forward is **faster measured** (4.1× vs 6.9× an engine pass for the same Jacobian), despite
  reverse's theoretical op-count advantage at ≥2 outputs — in pure Python, per-op interpreter
  overhead and tape allocation swamp the op-count argument at this tiny input count.
- Tangent width is nearly free: dual-1 (229 µs) vs dual-4 (272 µs) — ~4% of pass cost per extra
  column. There is **no case for per-lever scalar passes**; always compute the full Jacobian.
- Forward needs no tape, no O(ops) memory per probe, no graph lifetime management, and its
  branch behaviour is trivially identical to the float path (comparisons read the primal).
- No dependency: `Dual4` is ~60 lines of stdlib Python, and numpy is measured slower (above).

**What would overturn this:** the input count growing by an order of magnitude — concretely, a
future feature differentiating with respect to **each unit's rent individually** on a large roll
(5,000 inputs × 1 objective is classic reverse/AAD territory), or the lever set growing past
~30–50 named directions. Mission 5 treats rent as one collective lever — and §1a shows the rent
column collapses to a single aggregate seed anyway — so forward stands. If Half B ever asks for
per-unit recourse, this decision must be re-measured, not extrapolated.

---

## 1a. THE FLIP QUESTION (D.2): rent sensitivity without materialising a rent roll — **YES**

> *Can AD obtain d(metric)/d(rent) WITHOUT materialising a perturbed rent roll?*

**Yes — measured, exact, and O(1) in unit count.** The engine's own data flow makes it so:
income enters `_forecast_core` **only** through the two floats `(gsi_y1, goi_y1)`
(`engine.py:367–370` — the single O(units) pass, or the `PrecomputedIncome` reuse of it,
`engine.py:186` `precompute_income`). The rent lever adds `t` to every unit's `rent_month`, so

```
gsi_annual(t) = gsi_annual(0) + 12 · num_units · t      (exactly linear)
⇒ the rent tangent seed is the constant 12 · num_units on gsi_annual — nothing per-unit exists.
```

`check_d2_claims.py` §(2) seeds the dual tangent directly on the precomputed aggregate
(`Dual(pre.gsi_annual, (12·N, 0, 0, 0))`), builds **zero** `UnitIncome` objects, and reproduces
the full Jacobian — including the entire rent column and the IRR row —
**bit-identically (max relative difference 0.0)** against the per-unit-seeded pass, at 258 µs
independent of roll size. The O(units) work happens once, in the existing `precompute_income`;
every derivative probe after that is O(horizon) only.

Consequences, stated carefully:

- **AD-Newton search never calls `_perturb("rent_per_unit_month", ...)`.** Newton iterates for
  the rent lever evaluate value + slope at shifted `t` via the same aggregate seed
  (`gsi_annual + 12·N·t` with tangent `12·N`) — still no roll materialisation. The 39
  rent-`_perturb` calls per analysis (74.5% of D.2's row) collapse to **one real `_perturb` +
  full `run_financial_model` per solved rent row** — the confirming re-run, which must stay a
  real perturbed-inputs run for provenance (§4) and is ≤ 4 rows at the gate-limit scenario
  (≤ 7 in general). That is the term D.2's table said nothing else touches: AD's design kills it
  for search.
- **Honesty note — this kill does not actually require dual numbers.** The same seam evaluated
  in plain float (`gsi_annual + 12·N·t`, no tangents) gives bisection the same escape from
  `_perturb` for rent *search* probes. The aggregate-shift seam is separable from AD and could
  ship alone with Mission-4 bisection. AD needs the seam anyway; the seam does not need AD.
  Gate D should weigh AD on §5's grounds, not credit it with a win a ~20-line float seam
  achieves. (Two caveats on the float variant: `Σ(rᵢ+t)` vs `Σrᵢ + N·t` differ in rounding at
  the ulp level, so search probes are ~1-ulp off the `_perturb` path — irrelevant because every
  shipped number comes from the real confirming re-run; and either variant needs a *sanctioned*
  engine seam, because `PrecomputedIncome`'s identity check exists precisely to make a lying
  aggregate impossible — this must be a new explicit parameter, e.g. an income-shift argument
  validated against the base income object, never a bypass of that check.)
- **Not a guardrail inversion.** No guardrail formula is solved for a lever. This is a statement
  about the engine's input plumbing — the same class of documented data-flow fact as
  `_STATICALLY_HOPELESS` (`recourse.py:92`) — and the derivative still comes from propagating
  through the actual model. The re-run discipline is untouched.
- **Precondition:** the aggregate seed is valid only when income enters unmodified — i.e. no
  insight income uplifts (`income_is_estimated` + amenities rebuilds the `IncomeModel` inside
  the engine, `engine.py:192`). The recourse path never passes insights (`_rerun`,
  `recourse.py:412`), and the seam must raise loudly if asked to combine the two — the exact
  posture `PrecomputedIncome` already takes.

---

## 2. Differentiating through the Brent root-find in `irr.py`

### The two candidates, against this implementation

`irr` (`src/core/finance/irr.py:188`) computes `r*` such that
`f(r, θ) = Σ_t CF_t(θ) · (1+r)^(−t) = 0`, via a domain-bounded bracket search (`irr.py:300`,
`lo,hi = -0.99, 1.0` with up to 8 expansions floored at −0.999999) feeding `_brent_root`
(`irr.py:83`, tol `1e-6`, max_iter 100, Numerical-Recipes zbrent step-for-step).

**(a) Implicit function theorem (recommended).** Treat the converged root as defined by
`f(r*, θ) = 0`:

```
dr*/dθ = − (∂f/∂θ) / (∂f/∂r),   evaluated at r̂ (the returned root)
∂f/∂θ  = Σ_t (dCF_t/dθ) · (1+r̂)^(−t)          ← tangents already on the dual cash flows
∂f/∂r  = Σ_t −t · CF_t · (1+r̂)^(−(t+1))
```

The engine's dual pass carries tangents on every cash-flow amount; the **primal** amounts (plain
floats, extracted) go through the **unmodified production `irr()`** — bracket search, Brent,
tol, max_iter, all bit-identical to today — and the IFT is applied after, as two extra NPV-shaped
sums. `_brent_root` never sees a dual number. Cash-flow *times* are fixed integers here
(`engine.py` builds periodic flows), so `θ` only enters through the amounts — no time-derivative
term exists. Measured incremental cost: **~4.7 µs per probe at horizon 10** (O(horizon) — two
11-term sums + one division; `check_d2_claims.py` §(3)).

**(b) Pushing duals through the Brent iterations (rejected).** Analysis against this exact
implementation, no benefit of the doubt:

- **The tangents would be structurally wrong, not just noisy.** The bracket endpoints
  (`irr.py:300`) are **constants** in θ — their tangents are exactly zero. Every bisection step
  `d = xm = 0.5·(c − b)` (`irr.py:172`) propagates only endpoint tangents, so a run that ends on
  a bisection step returns a tangent built from zeros — garbage that *looks* like a derivative.
  Only interpolation steps (secant/IQI, `irr.py:148–160`) inject θ-sensitivity through `f`
  evaluations, and only a *contraction* argument makes iterate-tangents converge to `dr*/dθ`;
  bisection is not such a contraction for the tangent. Which step type the final iterate took is
  data-dependent (`min1`/`min2` guards, `irr.py:163`), so the tangent quality would be
  **non-deterministic across deals** — the worst possible property for a seam Half B must trust.
- Branch flips under infinitesimal θ change also make the iterate-path non-smooth even when the
  root itself is perfectly smooth.
- It also costs more: every Brent iteration's NPV loop would run on duals (~4–5× per-op) instead
  of floats.

### The concrete concerns, one by one (IFT recommendation)

- **What is `∂f/∂r` and can it vanish?** `∂f/∂r = −Σ t·CF_t(1+r)^(−t−1)`. For the classic shape
  (negative `CF_0`, mostly positive later flows) it is strictly negative at the root. It can get
  small when the cash-flow vector has multiple sign changes (NPV with a near-tangent root) —
  exactly the shapes for which `irr()` already returns unstable/None answers. **Check:** guard
  `|∂f/∂r|` against a scale floor (e.g. `eps · Σ t·|CF_t|(1+r̂)^(−t−1)`); below it, or non-finite,
  report the IRR partials as unavailable (`None`) — never a number (§3). Measured on both test
  deals: `∂f/∂r` is O(acquisition-cash·years), nowhere near vanishing.
- **The `tol = 1e-6` convergence boundary.** IFT at r̂ instead of the true r* has derivative
  error O(|r̂ − r*|) = O(tol) — the derivative **inherits the root tolerance once**, it is not
  exact-to-machine. Measured: 3.2×10⁻⁷ relative on the demo deal. This is far more than adequate
  for a Newton *search* whose every answer is re-run-confirmed (§4); Newton needs a good slope,
  not a perfect one. If a future consumer ever needs better, one float Newton polish of r̂
  (`r̂ − f/f_r`, two extra NPV sums) drops the error to O(tol²) — noted, not proposed (YAGNI).
- **`irr` returns `None` (no bracket / no sign change / max_iter).** The engine coalesces to
  `0.0` + warning (`engine.py:590`, `engine.py:617`). The metric is then a **constant** with a
  jump discontinuity in θ — there is no derivative to report. The API must return `None` for the
  IRR row's partials in that case (and the primal keeps its 0.0-plus-warning contract untouched).
  Reporting `0.0` partials would silently tell Newton "this lever can never fix IRR" — wrong and
  invisible. **Check:** the AD entry point tests `irr_raw is None` explicitly, same as the engine.
- **max_iter / non-convergence** is the same `None` path (`_brent_root`'s final `return None`,
  `irr.py:185`) — covered by the same rule.
- **Brent branch switching / determinism:** irrelevant under IFT — the root used is the
  production root, byte-for-byte, and the IFT formula does not care how Brent found it.

**Failure modes of the recommendation, stated plainly:** (1) near-tangent roots give
ill-conditioned `1/∂f/∂r` — mitigated by the floor-check → `None` → bisection fallback, and by
the confirm-by-rerun contract which makes a bad slope a *slow* search, never a wrong answer;
(2) the O(tol) derivative error means AD-vs-FD tests must use tolerance bands (~1e-5 relative on
the IRR row), not exact comparisons — a test-design constraint, documented so nobody "fixes" it
by loosening the root tolerance.

---

## 3. The Jacobian API — the seam Half B consumes

### Shape ruling first (D.2's §5.ii ask): not 7×4, not 4×4 — **8 metric rows × N caller-named columns, consumed dynamically**

The Mission 4 record is right that only 4 guardrails are live and failing at the gate-limit
scenario. The seam must not hardcode 7 — and it doesn't, because its rows are **not guardrails**:
they are `ForecastMetrics`' 8 float fields, which always exist for every deal regardless of which
guardrails are live, failing, or configured off. "Live" and "failing" are market-layer facts
(`_live_guardrails`, `guardrail_checks_from_metrics`) that change per deal and per config; baking
them into the differentiation seam would make its shape config-dependent — exactly the
implicit-ordering defect this section exists to prevent. Computing all 8 rows is also free:
tangent propagation produces every metric's tangent in the same pass (measured — the full
Jacobian at 4.1× vs a single column at ~5.5×; row count does not appear in the cost at all).
Consumers project: recourse/Half B reads only the rows for its live failing guardrails via
`_metric`-style named access, and a 4-guardrail deal simply reads 4 rows of a complete, named,
always-shaped object.

### Placement and layering

- `src/core/finance/dual.py` — the `Dual4` scalar (private mechanics; not exported from the
  package `__init__`).
- `src/core/finance/jacobian.py` — the public seam below. Core stays pure and imports nothing
  from `src/market/`.
- Lever semantics stay in `src/market/` (they are `_perturb`'s domain): a small
  `lever_directions(inputs)` helper next to `_perturb` builds the four `TangentDirection`s from
  the **same** constants `_perturb` uses, so lever meaning has one home and cannot drift.

### Signatures (mypy-strict; final names subject to reviewer taste, shapes are the contract)

```python
# src/core/finance/jacobian.py
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

MetricName = Literal[
    "cap_rate", "coc", "purchase_dscr", "year1_dscr",
    "spread_vs_rate", "irr_10yr", "cash_flow_y1", "min_cash_flow",
]  # exactly ForecastMetrics' float fields; drift-guarded at import time against the dataclass

SeedTarget = (
    Literal[
        "financing.purchase_price",
        "financing.interest_rate",
        "income.gsi_annual",            # the §1a aggregate seed — the rent lever's target
    ]
    | tuple[Literal["opex"], OpexFieldName]               # one of the 12 opex line items
)  # ONLY what the four levers need (YAGNI); unknown targets raise ValueError at call time

@dataclass(frozen=True)
class TangentDirection:
    name: str                                  # caller's label, echoed back verbatim
    seeds: tuple[tuple[SeedTarget, float], ...]  # (field, d(field)/d(direction)) pairs

@dataclass(frozen=True)
class MetricsJacobian:
    metrics: ForecastMetrics                   # the PRIMAL — bit-identical to forecast_metrics()
    directions: tuple[str, ...]                # column names, caller's order, echoed
    partials: Mapping[MetricName, tuple[float, ...] | None]
    degraded: tuple[str, ...]                  # human-readable reasons for every None row

    def partial(self, metric: MetricName, direction: str) -> float | None: ...
    def value(self, metric: MetricName) -> float: ...

def forecast_metrics_with_jacobian(
    fi: FinancialInputs,
    directions: Sequence[TangentDirection],
    *,
    horizon_years: int = DEFAULT_HORIZON_YEARS,
    precomputed_income: PrecomputedIncome | None = None,
) -> MetricsJacobian: ...
```

```python
# src/market/recourse.py (or a sibling module) — lever-space adapter
def lever_directions(inputs: FinancialInputs) -> tuple[TangentDirection, ...]:
    # ("rent_per_unit_month", +12·num_units on income.gsi_annual)   # §1a — no per-unit seeds
    # ("purchase_price",      −1 on financing.purchase_price)       # t = cut magnitude
    # ("interest_rate",       −1 on financing.interest_rate)        # t = cut; kink at rate 0
    # ("annual_opex",         −base_i/total_opex_y1 on each line)   # same spread as _perturb
    ...
```

(§1a changed one thing here versus the pre-D.2 draft: the rent lever's seed target is the
**income aggregate**, not per-unit `rent_month` entries — measured bit-identical and O(1) in
roll size. A per-unit seed target is deliberately NOT offered; it would invite exactly the
O(units)-per-probe pattern D.2 measured as 74.5% of the row.)

### The contract, point by point

- **No positional guessing.** Rows are addressed by `MetricName` literals (drift-guarded against
  `ForecastMetrics` at import, in the house style of `_YB_FIELDS`, `engine.py:53`); columns by
  the caller's own direction names via `.partial(metric, direction)`. A bare matrix is never
  exposed. Row set is the 8 metric fields, **not** the guardrail names: guardrail↔metric mapping
  (and "does this guardrail apply / is it live") stays in the market/strategist layer where it
  lives today (`_metric` `recourse.py:166`, `guardrail_checks_from_metrics`). Both DSCR fields
  are carried, matching `ForecastMetrics`' own documented reason.
- **Value + derivative from one pass.** `metrics` is the primal of the same evaluation — Newton
  reads residual `value(m) − bar` and slope `partial(m, lever)` off one object, one engine-shaped
  pass (measured 4.1× a float pass for all 32 entries).
- **Honest degradation.** `partials[m] is None` ⇔ no trustworthy derivative exists at this point:
  IRR undefined (`irr()` → `None`), `|∂NPV/∂r|` under the conditioning floor, or any non-finite
  tangent (each tangent checked with `isfinite` before packing). Every `None` row appends a
  reason to `degraded`. `None` ≠ 0.0, ever: a true zero sensitivity (e.g. `cap_rate` wrt
  `interest_rate`, which independently re-derives `_STATICALLY_HOPELESS`, `recourse.py:92`) is a
  real `0.0`. Callers seeing `None` fall back to Mission-4 bisection for that row.
- **What it does NOT expose:** `Dual4`, seeds-application internals, the tape-free pass
  structure, or any guardrail decision. It also does not accept `insights` — the recourse/search
  path never passes them today (`_rerun`, `recourse.py:412`), and income uplifts rebuild the
  `IncomeModel` mid-engine, which is exactly the case `PrecomputedIncome` already refuses;
  differentiation through insight modifiers is out of scope and loudly rejected
  (`ValueError`) if requested (this also protects the §1a aggregate seed's precondition).
- **Why a wrong top-3 in Half B is an optimizer bug, not a maybe-AD bug.** Before any optimizer
  code exists, the go/no-go checkpoint pins: (i) `MetricsJacobian.metrics` **bit-identical** to
  `forecast_metrics(fi, ...)` across the golden matrix (same parity discipline as
  `test_metrics_parity.py`); (ii) every partial vs central FD of the real engine within measured
  bands (≤1e-6 rel non-IRR rows, ≤1e-4 rel IRR row — the bands §1/§2 measured, FD-noise-aware);
  (iii) `None`-propagation for the IRR-undefined golden cases (`units_1_horizon_10` is a known
  one, `engine.py:606`); (iv) determinism: two calls, identical object contents. With those four
  green, the seam's outputs are pinned to the engine and to independent FD — an optimizer
  producing a wrong ranking on correct named values and correct named slopes has nowhere left to
  hide.

---

## 4. Blast radius and the confirm-by-rerun contract

### What must become dual-generic

The discipline that forbids a second metrics implementation (`_forecast_core`'s own docstring,
`engine.py:316-336`) cuts both ways: the differentiated pass must be **the same
`_forecast_core`**, made generic over `float | Dual4`, not a parallel slice (my prototype slice
is a measurement instrument, not a design). Float-path bit-identity is then **by construction**:
when no `Dual4` enters, every operation executes the identical float bytecode — same ops, same
order — pinned by the existing 34-case golden matrix + `test_metrics_parity.py` +
`test_engine_bitexact_refactors.py`, all of which must stay green untouched.

Concrete touch list (verified against the code, not the charter):

| File | Change | Risk notes |
|---|---|---|
| `src/core/finance/dual.py` (new) | `Dual4` with unrolled slots, primal-branch comparisons | new file, zero blast |
| `src/core/finance/engine.py:309` `_forecast_core` | seeds applied to the seed targets (incl. the §1a aggregate); internal scalars become generic | the year loop already is generic arithmetic; the non-arithmetic spots that need explicit care: `if cap_applied and noi >= 0` (`engine.py:484` — truthiness on a scalar; needs `Dual4.__bool__` or an explicit primal read), `max(0.0, …)` / `min(…)` (work via primal-valued comparisons), `dscr_y1 = 0.0` init (`engine.py:407`), and the **refi block** (`engine.py:543-566`): `RefiEvent` is a pydantic float model — in a dual pass the generic `cash_out` must stay a local scalar feeding the cash-flow vector, with `RefiEvent` built from primal values only |
| `src/core/finance/amortization.py:28,60` | `amortization_payment`, `schedule_columns` generic | `max(0.0, pay−interest)`, `max(0.0, bal−…)` and the `bal < _EPS → 0.0` snap all take primal-branch semantics ("differentiate the program as written"); the snap zeroes a ~1e-6 tangent tail — inside the mission tolerance |
| `src/core/finance/irr.py` | **no change to `irr` or `_brent_root`** — an IFT adapter in `jacobian.py` extracts primal amounts, calls production `irr()`, applies §2's formula | zero blast on the root-finder itself |
| `src/core/finance/jacobian.py` (new) | §3's seam, incl. the sanctioned income-shift/seed entry (the §1a seam — an explicit parameter validated against the base income object, never a bypass of `PrecomputedIncome`'s identity check) | new file, but the income-shift validation is finance-core-adjacent and needs the same loud-failure posture as `PrecomputedIncome` |
| `src/market/recourse.py` | `lever_directions` + Newton-within-bracket replacing `_bisect`'s interior (probe/confirm structure of `_search_one` `recourse.py:663` unchanged) | Half A scope |

**mypy strategy (flagged as the main implementation friction):** annotate `_forecast_core`'s
generic internals with a constrained `ScalarT = TypeVar("ScalarT", float, Dual4)`; mixed
`float · ScalarT` expressions resolve through `Dual4`'s typed reflected operators. Expect real
annotation work in the year loop (mypy checks the body once per constraint). If it turns
unreasonable, the fallback is annotating the hot loop's locals as `float` and keeping the dual
path behind a narrow `Any`-free façade — decided at implementation review, not silently.

**Non-smoothness inventory** (kinks where a Jacobian is one-sided or jumps — Newton must be
safeguarded, see below): rate clamp at 0 (`_perturb`), IO/amortizing payment `max`es and the
balance snap (`amortization.py`), `est_value` branch at `noi < 0` (`engine.py:484`), terminal
equity `max(0, …)` (`engine.py:586`), `min_cash_flow` argmin switches, MIP threshold at
`down_payment_rate == 0.20` (`engine.py:342` — not lever-reachable today), refi-year branch.
None are new; bisection walks the same landscape today. The check that catches all of them at
once: **Newton runs inside the bisection's bracket** (classic safeguarded Newton — reject any
step leaving `[lo, hi]`, bisect instead, shrink the bracket every iteration). Worst case
degrades to exactly Mission 4's bisection; it can never do worse or land outside the bracket.

### Confirm-by-rerun (restated concretely — the contract does not move)

`_search_one` (`recourse.py:663`) keeps its exact shape: AD-Newton replaces only the interior of
the search between the reachability probe and the rounding step. The number on the page still
comes from **one real, un-differentiated `run_financial_model`** (`engine.py:638`) at the rounded
ask — for the rent lever this is a real `_perturb`-materialised roll, deliberately: the one
place the O(units) copy survives is the one place provenance demands it — read through
`metrics_of` + `guardrail_checks_from_metrics`, and on a failed confirm the row falls back to
the search's own last confirmed-passing point, re-derived from a full run — byte-for-byte the
discipline already at `recourse.py:723-739`. No dual number, tangent, or Newton iterate is ever
shipped, logged into a report, or compared against a bar for a shipped claim. AD steers; the
engine decides.

### §4a. D.2's four asks, answered

- **(a) The dual-pass multiple k:** measured **4.1×** one engine float pass for the full
  8-row × 4-column Jacobian with the unrolled pure-Python `Dual4` (6.5× tuple-tangent, 8.4×
  numpy — rejected). Effectively flat in tangent width (~4%/column) and flat in row count.
- **(b) The flip question:** **YES** — §1a. Rent sensitivity comes from one constant seed
  (`12·num_units`) on the precomputed income aggregate; zero `UnitIncome` objects; bit-identical
  Jacobian; O(1) in roll size per probe. AD-Newton search performs **no rent `_perturb` calls**;
  only the per-row confirming `run_financial_model` still materialises a roll (≤ 4 such rows at
  the gate-limit scenario, vs 39 rent probes today). The same seam in plain float mode would
  also de-`_perturb` bisection's rent search — AD is sufficient but not necessary for this kill
  (§1a honesty note; §5).
- **(c) IRR/Brent differentiation cost per probe:** production `irr()` runs unchanged on primal
  floats (zero delta); the IFT adapter adds **~4.7 µs at horizon 10**, O(horizon) — two
  NPV-shaped sums + one division. No dual ever enters `_brent_root`.
- **(d) Jacobian once at baseline, or per Newton step?** **Per Newton step** — Newton needs the
  residual and slope at the *current iterate*, so each iteration is one dual pass at that point
  (cost k = 4.1×; the pass returns all rows, so one iterate serves every guardrail being chased
  on that lever). The *baseline* Jacobian is additionally computed once and shared: it prices
  the first Newton step of every (lever, guardrail) pair and is the object Half B consumes
  directly. Estimated safeguarded-Newton depth: 2–4 iterations per pair (estimate, labelled as
  such; the per-pair landscape is near-hyperbolic per the module docstring, `recourse.py:19`).

### Probe-count and wall-time projection (candid; wall-time multipliers measured, iteration counts estimated)

| | today (measured) | AD-Newton + §1a seam (projected) |
|---|---|---|
| engine evaluations per solved pair | ~11 light + 1–2 full | **3–5** (1 shared baseline Jacobian + 2–4 safeguarded iterations) + 1–2 full |
| rent-roll materialisations per analysis (5,000u) | 39 × ~3.7–4.2 ms ≈ **74.5% of the row** (D.2) | **≤ #solved rent rows** (≤ 4 at gate limit) — search never materialises |
| single-pair wall time (engine-bound pairs) | ~11 × 42 µs ≈ 0.5 ms | ~3.5 × 4.1 × 42 µs ≈ 0.6 ms → a wash |
| Half B gradient evaluation (4-lever) | 8 central-FD probes + FD-step fragility | **1 pass at 4.1×, exact** — ~2× cheaper and no step-size failure mode |

The honest headline, updated for D.2: probe count drops ~3× (charter goal, met); engine-bound
wall time per pair is a wash (k = 4.1); and the dominant cost term of the real 5,000u/100y row —
the rent-copy 74.5% — is eliminated *by the aggregate-seed seam*, which AD's rent column
requires and demonstrates, but which does not itself require AD. D.2's ~82 ms AD-only projection
assumed the 12 surviving rent `_perturb`s persist; under §1a they do not (search performs zero),
so the AD+seam path lands in the same neighbourhood as D.2's copy-avoidance row rather than
missing the 30 ms target on the rent term. I have not measured the composed 5,000u/100y row —
that composition is PF.1's call, and the honest statement is: **the seam is the perf
intervention; AD rides on it.**

---

## 5. Go/no-go read

**Recommendation: GO on AD as the Half-B Jacobian enabler; NO-GO on AD *as a performance
intervention* — concurring with D.2's preliminary PF.1 read, with one reframe from §1a.**

The case for GO (scoped exactly as §3/§4): the Jacobian is validated to FD against the real
engine on two deal shapes (28/28 entries), forward-vs-reverse cross-checked to machine epsilon,
the primal is bit-identical by construction, the confirm-by-rerun contract is untouched, no
dependency is needed (numpy measured slower), and Half B's multi-lever optimizer cannot
responsibly be built on FD guesses — exact, named, degradation-honest slopes at 4.1× one engine
pass is precisely the seam it needs, and the IRR question has a clean answer (IFT over the
production root) with measured, bounded error.

The reframe: the biggest *measured* prize this discovery found — killing the 74.5% rent-copy
term — belongs to the **aggregate-seed seam (§1a)**, not to differentiation itself. Ship
priorities should reflect that: (1) GC tuning (~35% of the row, zero finance-core diff — D.2's
finding, not mine to weigh further); (2) the aggregate-shift seam, which fixes the dominant term
and works under plain bisection; (3) AD proper, justified by Half B and by probe-count, riding
on seams (1) and (2) rather than competing with them.

**The strongest argument against my own recommendation:** every piece of AD's remaining unique
value is prospective. Measured today, engine-bound Newton is a wall-time wash (k = 4.1 eats the
3× probe reduction); the rent-term kill doesn't need duals; GC tuning doesn't need duals; and
the price is a new scalar type threaded through the most protected files in the repo
(`_forecast_core`, `amortization.py`, a refi-block restructure, mypy genericity friction) —
blast radius bought almost entirely for Half B's benefit before Half B exists. If Gate D doubts
Half B ships this mission, the consistent call is: take the GC and seam wins now, hold AD until
the optimizer's need is concrete. I recommend GO because the charter's Half B is explicit and
this seam is its stated dependency — but that is the load-bearing assumption, and it should be
challenged at the gate, not smuggled past it.

---

## 6. Reproduction commands

```bash
source /home/rtokime/anaconda3/etc/profile.d/conda.sh && conda activate airedeal
S=/tmp/claude-1002/-home-rtokime-projects-Personal-ai-real-estate-deal-analyzer/cf7ad590-667f-45d2-a021-0d4460f8c353/scratchpad/d1
python $S/bench_baseline.py        # engine pass cost + real recourse probe census
python $S/proto_dual.py            # forward dual-4: parity, FD validation, timing
python $S/proto_reverse.py         # reverse tape: cross-validation vs forward, timing
python $S/proto_extra.py           # dual-1 timing + IRR FD-noise attribution (demo deal)
python $S/proto_dual4_opt.py       # optimized Dual4 timing (4.1x)
python $S/validate_second_deal.py  # second deal-shape validation
python $S/attribute_second.py      # second-deal IRR noise attribution
python $S/check_d2_claims.py       # numpy-dual check, THE FLIP QUESTION, IFT cost
```
(Scratchpad is session-local; scripts are throwaway measurement instruments per the discovery
constraint and are quoted here so a reviewer can ask for them or re-create them from this memo.)

## 7. Charter-vs-code / brief-vs-code deltas found

- **None on the charter's anchors** — every `path:line` in the D.1 brief matches the tree at
  `87efd22` (re-verified by grep this session).
- The charter frames the output as a "7×4" Jacobian over guardrails; the code's clean seam is
  **8 metric rows** (`ForecastMetrics`' float fields, with `purchase_dscr`/`year1_dscr` both
  carried for the documented consumer-split reason) × N caller-named directions, consumed
  dynamically by whatever guardrail set is live (4 at the gate-limit scenario per the Mission 4
  record; up to 7 in general). Nothing hardcodes 7 — see §3's shape ruling.
- The charter's "~10–20 probes per lever/guardrail pair" measures at the low end (~11 light + 1
  full) on the near-miss fixture after Mission 4's PV work.
- The mission premise "AD speeds up the search" locates the win in the wrong term at portfolio
  scale: the engine forecast is ~20% of the real row; the dominant term is the rent-roll copy
  (D.2, corroborated by `docs/manual testing/MISSION_4_MANUAL_TESTING.md:513`), which §1a kills
  via a seam that does not itself require AD. The "73 ms" baseline in older briefs is retracted;
  the verified baseline is 175–198 ms best / 181–203 ms median (D.2).
