# D.4 — Half B Design Memo: the multi-lever recourse optimizer (Mission 5, Discovery)

**Branch** `mission/5-adjoint-differentiation` @ `87efd22` · **Date** 2026-08-31 ·
**Status** Discovery finding — no production code written; all prototypes live in the session
scratchpad (`scratchpad/d4/`: `harness.py`, `scan_monotone.py`, `proto_methods.py`,
`proto_methods2.py`, `proto_gate.py`, `proto_pipeline.py`, `proto_scale.py`,
`proto_globality.py`, `proto_globality2.py`, `proto_final_checks.py`, `proto_fixture_qa.py`).
Every number below is reproducible under the `airedeal` conda env
(`source /home/rtokime/anaconda3/etc/profile.d/conda.sh && conda activate airedeal`).

Starts from the verified corrections, not the charter's stale figures: the Jacobian seam is
**8 metric rows × N caller-named columns** with `.partial(metric, direction)` / `.value(metric)`
accessors and `None ≠ 0.0` (D.1 §3); maximum live guardrails is **6** (and 6 requires a
user-set `cap_rate_floor`; `REQUIRE_POSITIVE_CF_ALL = False`, `chief_strategist.py:56`), the
bench gate-limit deal is **5 live / 3 failing** (PD.1 (b)); the rent lever is exactly linear in
the income aggregate (`gsi = gsi_base + 12·n·t`, drift below the noise floor at 5,000 units —
D.1 §1a). The decided design family — classical constrained optimization on the real model, no
learned/decomposition methods — is taken as given and not relitigated.

---

## 0. The problem shape, measured before any method was tried

The Half-B problem in lever-perturbation space `t = (t_rent, t_price, t_rate, t_opex)`, all
`t ≥ 0` (every lever one-directional, `_perturb` `src/market/recourse.py:372`):

- **Feasibility target:** every LIVE guardrail passes — not "close the one failing guardrail"
  (a combination is an answer to the whole deal; the single-lever menu already answers
  per-guardrail). Margins read as `_metric(m, g) − bar` off the same
  `guardrail_checks_from_metrics` the thesis uses; higher is better for all of them
  (`_metric`'s own docstring, `recourse.py:166`).
- **The plausibility box** (per-lever caps, reused verbatim from Mission 4's constants
  `_MAGNITUDE_RELATIVE_THRESHOLD` `recourse.py:120` / `RATE_MAGNITUDE_THRESHOLD`
  `recourse.py:130`): rent ≤ 10% of avg rent, price ≤ 15%, rate ≤ 100 bps (floored at 0),
  opex ≤ 20%. The optimizer searches **inside this box** — the box IS the R1 rule of the gate
  (§3), so search never wastes probes on combinations the gate would reject on magnitude.

**Measured facts that decide the design** (three deals: the 4-unit near-miss fixture from
`tests/unit/test_recourse.py`, committed `82_champlain_dieppe`, committed `36_kelly_moncton`;
`scan_monotone.py`, `proto_final_checks.py`):

1. **Every live guardrail margin is monotone non-decreasing along every lever axis AND every
   diagonal ray within the plausibility box** — 61-point scans × 4 axes × 11 diagonal subsets ×
   3 deals, zero non-monotone segments above 1e-12. Inside the box, the guardrail-feasible set
   is an up-set: a ray from the origin crosses its boundary **at most once**. (Measured, not
   assumed — see §1's overturn conditions and §5: correctness never depends on it.)
2. **All three deals are guardrail-feasible at the full plausibility box** — jointly-plausible
   fixes exist even for `36_kelly` (4 fails, gate closed).
3. **No single lever, capped at its own plausibility threshold, closes all fails on either
   near-miss deal** (all 8 lever/deal combinations measured infeasible). This is Half B's
   product case in one measurement: on exactly the deals the recourse gate opens for, Mission
   4's plausible single-lever menu cannot finish the job, while jointly-plausible 2-lever
   combinations exist (§2's results).
4. Engine probe costs at the 5,000-unit/100-year ceiling: light probe **0.20 ms** on a
   non-rent lever, **3.01 ms** on a rent-containing combination (the `_perturb` roll
   materialisation D.2 profiled), full `run_financial_model` confirm of a 3-lever combination
   **3.06 ms**.

---

## 1. The constrained-optimization method — chosen by measurement

### The contenders, run against the real model

All measured on the real engine (light path `forecast_metrics`, identical to the search path
`_rerun` uses), on the near-miss fixture (3 failing) and `82_champlain` (3 failing). Task: land
on a **minimal feasible point** (the feasible-set boundary — anything interior is a
larger-than-necessary ask). Probe = one engine evaluation; FD Jacobian = 8 probes (2/lever,
central), standing in for one AD pass (D.1: 4.1× one float pass ≈ 4.1 probe-equivalents).

| Method | Engine probes to ONE minimal feasible point | Iterations | Failure modes observed |
|---|---|---|---|
| **Ray restriction + bisection** (1 reachability probe at the box edge + bisect the ray scalar to 1e-3) | **11, fixed** | 10 bisections, fixed | none — fixed budget, no tuning, lands on the frontier by construction |
| Ray restriction + safeguarded Newton (slope via central FD on the ray, 2 probes/slope) | 11–41 | 3–10 | slope near guardrail kinks sends iterates outside the bracket → safeguard bisects anyway; **never beat bisection**; with AD slopes (~4.1 probe-equiv each) best case ≈ parity |
| SQP-lite (Gauss-Newton on violated margins, min-norm step, box-projected) + frontier walk-back | 10 + 10 = **20** | 2 + 10 | reaches feasibility in 2 iterations but at an **interior, non-minimal** point (e.g. rent=1.0, price=1.0 of cap); the walk-back to the frontier is… ray bisection; the landing direction is **emergent from the least-squares step** (numerically determined, not chosen) — parsimony/diversity by accident |
| Projected gradient (squared-violation potential) | 10 to feasibility, non-minimal | 2 | same interior-landing defect + a step-size knob and a per-guardrail scaling choice that is a covert cross-normalization |
| Augmented Lagrangian | **182**, non-minimal | 2 outer × inner | answer visibly depends on ρ-schedule and step sizes — tuning knobs nobody turns, exactly the invariant-7 smell; landed at a blended interior point |
| Interior point (log-barrier from the feasible box corner, LSE-smoothed max-fraction objective, FD gradients + backtracking) | **518–558** | 12 outer | ~50× the ray cost to approximate the same balanced frontier point ray-bisection found in 11 probes; needs a strictly-feasible start and smooth margins (D.1's kink inventory says they aren't) |

(`proto_methods.py`, `proto_methods2.py`.)

### Decision

**Deterministic multi-start ray restriction + safeguarded 1-D bisection** — Mission 4's own
search primitive (`_bisect` `recourse.py:471`), applied to the ray scalar instead of a single
lever. Structurally this is the projected-gradient family degenerated to its honest core for
this problem shape: with a feasibility-not-optimization contract there is **no objective to
step down**, every 4-D method must either invent one (violating the spirit of the no-cross-lever
rule internally) or stop at an arbitrary interior feasible point, and every one of them still
needs a 1-D frontier landing at the end — which is the ray search itself. The measured facts
that decide it:

- 11 probes, **fixed**, per candidate, vs 20 (SQP+walk-back, uncontrolled direction), 182
  (AL), 518+ (IP). At 0.20 ms/probe (portfolio scale, non-rent) a candidate costs ~2.2 ms.
- Zero tuning constants. AL and PG both carry step/penalty schedules whose values change the
  answer; the ray scheme's only parameters are the fixed ray grid (§2) and the existing
  `_BISECT_TOL`-style tolerance.
- Monotone margins (measured fact 1) make the first crossing the only crossing, so the ray
  answer is the exact minimal feasible point on that ray, not a local one.
- The failure surface is Mission 4's, already survived in production: bisection walks kinks
  without derivative trouble.

**Where the Jacobian earns its keep in Half B** (consumed via D.1's named accessors, never
positionally): (a) **subset pruning** — a lever whose column is `0.0` on every failing metric
(a true zero, never `None`) is dropped from subsets before any probe, generalising
`_STATICALLY_HOPELESS` (`recourse.py:92`) dynamically; a `None` partial prunes nothing
(honest degradation — no derivative ≠ no effect); (b) **one optional blended ray** — the
baseline Jacobian's per-own-box-fraction margin-closing rates define a deterministic
"best-bang" direction, one extra ray in the multi-start family, translated back to real lever
asks before anything is displayed (charter #16's internal-heuristic clause, exercised
exactly once). The search itself steps by bisection, not by gradient.

**What would overturn this choice:** (i) a measured non-monotone live-guardrail margin inside
the plausibility box on a real deal shape (none found in 2,196 scan segments; would demote the
ray answer from "exact minimal on the ray" to "confirmed feasible, possibly not minimal" and
reopen Newton-with-safeguards); (ii) the lever count growing past ~5–6 (subset enumeration is
2^n; at 4 levers it is 11 multi-lever subsets, at 8 it would be 247 and a real 4-D method with a
sanctioned internal objective becomes right); (iii) a future product decision to introduce a
genuine scalar objective (then SQP on that objective, measured again, not extrapolated).

---

## 2. Deterministic multi-start

### The scheme

Everything is enumerated in fixed order off module tuples — never dict/set iteration:

- **Subsets:** all lever subsets with |S| ≥ 2, in `(|S|, lexicographic-in-_LEVER_ORDER)` order
  — 11 subsets (`itertools.combinations` over the module constant `_LEVER_ORDER`
  `recourse.py:86`; singletons are Mission 4's existing section, not re-searched here). A lever
  with a zero-width plausible box (e.g. baseline interest rate 0.0) is excluded from subsets
  statically, with the exclusion recorded — deterministic by rule, not by float accident.
- **Rays per subset**, as fixed own-box-fraction patterns: the **balanced ray** `(1, 1, …)`
  plus **one-lever-emphasized tilts** — for each lever in S, the pattern with that lever at 1.0
  and the others at 0.5. That is 3 rays per pair, 4 per triple, 5 for the full set: **39 rays**
  total, plus the optional Jacobian blended ray (§1) = 40. Ray `(S_i, pattern_j)` carries the
  unique ordinal `(i, j)` used as the final tiebreak everywhere (§4).
- **Per ray:** 1 reachability probe at the box edge (edge infeasible → ray closed, honest
  per-ray null — no extrapolation past the box, same posture as `_search_one`'s bound probe
  `recourse.py:694`); then bisect the ray scalar on `[0, 1]` to 1e-3 (finer in every lever's own
  units than its `ROUND_STEP`); round each lever's delta **away from zero** with the existing
  `ROUND_STEP` (`recourse.py:110`) — the gate (§3) then judges the **rounded** asks, because
  the rounded ask is what ships.

### Why this many starts — measured

Top-3 stability vs grid refinement (`proto_pipeline.py`), identical procedure at three grid
sizes on both open-gate deals:

| Ray grid | rays | light probes | top-3 (near-miss) | top-3 (82_champlain) |
|---|---|---|---|---|
| balanced only | 11 | 121–132 | baseline | baseline |
| + 0.5-tilts | 39 | 369–413 | **identical** | **identical** |
| + 0.25-tilts | 67 | 496–617 | **identical** | **identical** |

The top-3 is **bit-stable from the balanced-only grid up** on every feasible deal measured —
parsimony + leximin ordering (§4) inherently prefer the balanced small-max crossings, so finer
tilts only append dominated candidates. The tilts are kept anyway (39, not 11) because they are
the fallback when a gate rule kills a balanced crossing: on `36_kelly` the R2 joint rule
rejected 4 of 4 reachable balanced rays, and on the near-miss fixture with the candidate R3
budget rule at B=1.5, **7 of 11 balanced-grid rays were gate-rejected and the scheme still
produced a full, plausible top-3 from the survivors** (`proto_final_checks.py`) — a
single-start method descending along the best joint direction lands on a rejected point and
reports a false null. That measured case is the **known-local-minima acceptance test**: the
"local minimum" in a pure feasibility problem is a gate-rejected crossing that hides the
plausible answers on neighbouring rays, and deterministic enumeration is what finds them.
39 is therefore justified as: the smallest fixed grid that (a) covers every subset, (b) offers
a non-balanced alternative on every subset when a gate rule rejects the balanced direction, and
(c) is measured top-3-identical to the 67-ray refinement.

### Determinism guarantee

Same inputs ⇒ same top-3, **exactly**: enumeration order is fixed by module tuples; candidate
keys (§4) end in the unique `(subset_ordinal, ray_ordinal)`; rounding is the deterministic
`_round_away_from_zero`; duplicate rounded combinations (different rays rounding to the same
asks) dedupe by keeping the minimal key. No RNG, no dict/set iteration order, no wall clock.
Measured: two fresh end-to-end runs on `82_champlain` produce byte-identical serialized top-3
(`proto_scale.py`).

---

## 3. The unified all-four-lever joint plausibility gate — the core new engineering

### Interface

One pure function, replacing the pair `_rejector_flagged` (`recourse.py:519`) +
`_magnitude_flagged` (`recourse.py:584`) for combinations (the single-lever path keeps its
existing behaviour; a single lever is the 1-element case of the same gate):

```python
@dataclass(frozen=True)
class CombinationJudgment:
    plausible: bool                      # AND over all rules
    reasons: tuple[str, ...]             # one composed reason per tripped rule, fixed rule order
    tripped_rules: tuple[RuleName, ...]  # machine names, for honest-null aggregation (§6)

def judge_combination(
    deltas: Mapping[LeverName, float],   # SIGNED, rounded, as shipped (rent +, cuts −)
    *,
    base_metrics: ForecastMetrics,
    target_metrics: ForecastMetrics,     # the light-path metrics at the combination
    baselines: Mapping[LeverName, float],
    snapshot: MarketSnapshot,            # recourse's own _derive_snapshot (recourse.py:237)
    market: MarketAssumptions,
) -> CombinationJudgment: ...
```

Deterministic, boolean, engine-free except that `target_metrics` is handed in (the gate never
runs the engine itself — the caller already has the crossing's metrics; the gate stays a pure
judgment). It is a **feasibility filter, not an objective term**: nothing in it is
differentiated, weighted, or traded off against a margin.

### The rules (mechanism mine; every threshold value is PD.2's)

Fixed evaluation order, all rules always evaluated (reasons compose, as
`_judge_plausibility` does today):

- **R1 — per-lever caps (reuse).** `|delta_i| ≤` the lever's own existing threshold
  (`_MAGNITUDE_RELATIVE_THRESHOLD`, `RATE_MAGNITUDE_THRESHOLD`) — the same constants, same
  strict-`>`-plus-1e-12 comparison. Because the optimizer searches inside this box, R1 can only
  trip via rounding-away-from-zero pushing an ask past a cap; it stays in the gate so the gate
  is self-contained (the gate must be able to judge ANY combination handed to it, including in
  tests, not only optimizer output).
- **R2 — joint rejector reuse (the unification).** ONE `MarketHypothesis` carrying **both**
  populated axes at once: `interest_rate_delta` = the combination's signed rate delta, and
  `cap_rate_delta` = the **engine-computed** implied-cap change of the FULL combination
  (`target_metrics.cap_rate − base_metrics.cap_rate` — real re-run cap rates, never a
  re-derivation), through the unmodified `reject_unrealistic` (`src/market/rejector.py:68`).
  Today's `_rejector_flagged` populates exactly one axis per call, so the rejector's own
  cross-axis rule `|interest_rate_delta − cap_rate_delta| ≤ 0.02` (`_rates_vs_cap_ok`,
  `rejector.py:7`) has never once fired jointly — this rule is where "individually fine,
  jointly implausible" becomes decidable with **zero new constants**. Also inherits the cap
  band [3%, 12%] (`_cap_bounds_ok`) on the combination's implied cap for free. When
  `market.cap_rate_purchase` is overridden the implied cap never moves (the
  `_STATICALLY_HOPELESS`-class data-flow fact); R2 then degrades honestly to the rate axis
  alone — exactly today's single-lever behaviour, and stated in the reason string when it
  matters.
- **R3 — total ask budget (NEW; founder call, §8 Q2).** `Σ_i |delta_i| / cap_i ≤ B` — the sum
  of own-axis fractions. This is NOT cross-lever commensuration of dollars: each term is the
  lever's move as a fraction of ITS OWN plausible range (the exact quantity charter #15
  blesses), and the sum is "how many maxed-out single asks is this negotiation, in total."
  Without it, a 4-lever combination maxing all four caps simultaneously (each individually
  fine) ships un-flagged. Recommended default B = 2.0; measured calibration in §8.
- **R4 — price-cut + rent-raise posture coherence (NEW; founder call, §8 Q3).** Recommended
  default: **not adopted in v1** (YAGNI — no repo-derived value exists for it, and R2 already
  fires on the market-math component of deep price+rent combinations). Shape if adopted:
  `f_price + f_rent ≤ C` when both are non-zero.

### How the gate composes with the optimizer — projection, and honest degradation

The gate participates twice, in two different capacities:

1. **A priori, as a box projection.** R1 and R3 are closed-form in own-fraction coordinates
   (a box and a half-space), so the search space is their intersection **by construction** —
   the deterministic projection is: clip each lever to its cap, then, if the fraction-sum
   exceeds B, scale the whole combination down by `B / Σf` (one multiplication; deterministic;
   stays on the ray). No probe is ever spent on a combination R1/R3 would reject.
2. **A posteriori, as a filter.** R2 depends on the engine-computed implied cap, which is not
   available until the crossing is found — so R2 (and R4 if adopted) run on the rounded
   crossing, and a trip **closes that ray with a recorded reason** (flag-don't-remove at the
   aggregate level: the count and reasons feed the honest-null contract, §6). It is never
   "projected around" — there is no pretending a cheap inverse exists for an engine-computed
   quantity, the same reasoning that forbids formula inversion everywhere else in this module.

Degradation is honest at every exit: an edge-infeasible ray, an R2-rejected crossing, and a
failed confirm (§5) each increment a named counter with a reason; none is silently retried
with different constants.

### The worked fixture — jointly implausible, individually fine (measured, committed deal)

`data/sample_listings/82_champlain_dieppe` (the near-miss fixture deal, gate open: 3 failing —
dscr, spread, coc). Baseline cap rate **6.922%** (engine-computed; snapshot cap identical via
`_derive_snapshot`). The combination, in shipped rounded asks:

| Lever | Ask | Own cap | Individually |
|---|---|---|---|
| `interest_rate` | **−90 bps** (6.80% → 5.90%) | 100 bps | fine — strictly under `RATE_MAGNITUDE_THRESHOLD`; single-lever rejector `\|−0.009 − 0\| = 0.009 ≤ 0.02` passes |
| `purchase_price` | **−$90,000** (−14.88%, $605,000 → $515,000) | 15% | fine — strictly under `_MAGNITUDE_RELATIVE_THRESHOLD`; single-lever cap proxy `\|0 − (+0.0121)\| = 0.0121 ≤ 0.02` passes, implied cap 8.13% inside [3%, 12%] |

Verified through the REAL production `_judge_plausibility` (`recourse.py:609`) per lever, on
both a cap-proxy guardrail (`spread`) and a non-proxy one (`dscr`): **plausible=True on all
four rows** (`proto_fixture_qa.py`).

Jointly: the combination's engine-computed implied cap delta is **+0.0121** (cap 6.922% →
8.13% — the price cut alone does this; the rate cut contributes nothing to cap), and the rate
delta is **−0.0090**, so the rejector's own cross-axis rule sees
`|−0.0090 − (+0.0121)| = 0.0211 > 0.02` → `reject_unrealistic` returns an empty set →
**jointly implausible**, reason: *"a 90 bps rate cut alongside a price cut that lifts the
implied cap rate by 121 bps moves rates and cap in opposite directions by more than the 200 bps
divergence this project treats as a realistic market hypothesis."* And it is not a strawman:
the combination genuinely **closes all three failing guardrails**, confirmed by a full
`run_financial_model` re-run (margins: dscr +0.214, spread +0.0073, coc +0.0776) — exactly the
combination a gate-less optimizer would happily ship. Both asks sit strictly inside their caps
(90 < 100 bps; 14.88% < 15%), so the QA test has no `==`-threshold fragility. A second measured
variant for the suite: **price −15% + opex −20%, NO rate move** trips R2 too
(`|0 − (+0.0202)| = 0.0202 > 0.02`) — proving the joint rule fires even with the rate lever
untouched (`proto_gate.py`).

---

## 4. Normalization-free top-3 selection

### The ordering, precisely

For each confirmed candidate, with `f_i = |delta_i| / cap_i` (own-axis fraction, in [0, 1]) and
active set `A` (levers with non-zero rounded ask), the sort key is the tuple:

```
K = ( len(A),                                        # 1. parsimony: fewer levers first
      tuple(sorted((f_i for i in A), reverse=True)), # 2. within-axis magnitude: leximin —
                                                     #    compare largest fraction, then next…
      tuple(f_i for i in _LEVER_ORDER),              # 3. deterministic float tiebreak
      subset_ordinal, ray_ordinal )                  # 4. unique final tiebreak
```

ascending lexicographic. No component compares one lever's units against another's: (1) is a
count; (2) compares each lever's move only against its OWN plausible range, and compares
positionally sorted fractions — never a sum, never a weighted mix, never a dollar-to-bps rate;
(3) is fixed-order fractions; (4) is the enumeration ordinal. **Total order proof:** K is a
finite tuple of floats and ints compared lexicographically (a strict total order on tuples of
totally ordered components — all fractions are finite in [0,1] by construction, boxes are
strictly positive or the lever is excluded, §2); antisymmetry holds because component (4) is
unique per generated candidate, so no two distinct candidates share a full key. Duplicate
rounded combinations were already deduped to the minimal key before sorting. Nothing ever
falls through to insertion order — same discipline as `_pick_cheapest`'s documented tie-break
(`recourse.py:771`).

### Diversity (DiCE-style), then the top-3

Greedy selection over the K-sorted candidate list: pick the minimal-K candidate; then the
minimal-K candidate whose **active-lever set differs** from every already-picked one; repeat to
3. Distinct-lever-set is the diversity predicate — interpretable, needs no distance metric, and
therefore no cross-lever commensuration. If fewer than 3 distinct lever-sets survive the gate,
the section ships the honest count (§6) rather than padding with near-duplicates (default;
PD.2 Q5). Measured on `82_champlain`: top-3 = (rent+price: +$90/mo & −$55,000),
(price+rate: −$58,300 & −100 bps), (rent+rate: +$100/mo & −100 bps) — three genuinely
different negotiations, stable across all grid sizes.

### What is framed for PD.2 (weighting)

Parsimony strictly precedes magnitude in K: a 2-lever combination with larger own-fraction
asks outranks a 3-lever one with tiny asks. That is a product stance (fewer negotiations >
smaller negotiations), not a mathematical necessity — §8 Q4 puts it to the founder with the
measured alternative.

---

## 5. Confirm-by-rerun

Protocol, byte-for-byte the Mission 4 discipline (`_search_one`'s confirming block,
`recourse.py:723-739`), applied per shipped combination:

1. Provisional top-3 selected from **light-path** candidates (§4).
2. Each is confirmed by **one real, un-differentiated `run_financial_model`** at the rounded
   asks (a real `_perturb`-materialised input for every lever including rent — the one place
   the O(units) roll copy survives, deliberately, for provenance). Confirmation checks **all
   live guardrails** via `guardrail_checks_from_metrics`, not only the originally-failing ones.
   The metric values shown beside the combination come from this run and no other.
3. **Fallback on a failed confirm** (rounding only enlarges asks toward passing under measured
   monotonicity, so this is defensive): re-confirm at the unrounded crossing `t*` with a second
   full run; if that passes, ship `t*`'s asks (un-rounded, exactly as Mission 4 falls back); if
   it also fails, drop the candidate, increment the `confirm_failed` counter with the ray id,
   and promote the next candidate in K-order (which then gets its own confirm). No candidate
   is ever shipped un-confirmed; no dual number, FD slope, or bisection iterate ever reaches
   the report.

Measured cost: `confirm_fail = 0` across every run on all fixtures (413 rays cumulative);
**one full confirm of a 3-lever combination at 5,000 units / 100 years = 3.06 ms → 3
combinations ≈ 9.2 ms**; at demo scale ≈ 0.2 ms total. Confirmation is never the budget
problem (the search probes are — §7).

---

## 6. Honest-null and the report seam (data contract)

### Schema (additive; `src/schemas/models.py` + README migration note)

```python
class CombinationLeverMove(BaseModel):        # one lever inside one combination
    lever: LeverName
    baseline_value: float
    target_value: float
    delta: float                              # signed, rounded, as shipped
    relative_change: float                    # |delta| / |baseline| — same field semantics as RecourseLever
    fraction_of_cap: float                    # |delta| / own plausibility cap, in (0, 1]

class RecourseCombination(BaseModel):
    moves: tuple[CombinationLeverMove, ...]   # ≥2, in _LEVER_ORDER order
    closes_all_live_guardrails: bool          # always True for shipped combos (confirm-gated)
    confirmed_margins: tuple[GuardrailMargin, ...]  # (guardrail, bar, value) from THE confirming run
    rounded: bool                             # False only on the §5 fallback path

class CombinationAnalysis(BaseModel):
    attempted: bool                           # False ⇒ same gate as Mission 4 said "not close"
    combinations: tuple[RecourseCombination, ...]   # 0..3, in final K-order
    honest_null: bool                         # attempted and combinations == ()
    rays_searched: int
    rays_edge_infeasible: int                 # nothing inside the plausible box closes it, on that ray
    rays_gate_rejected: int
    gate_reasons: tuple[str, ...]             # deduped, fixed rule order — WHY, for the null copy
    confirm_failed: int
```

`RecourseAnalysis` gains one optional field: `combinations: CombinationAnalysis | None = None`
(`None` = feature absent/off — old payloads validate unchanged; additive, not schema-breaking
by PD.1 (c)'s own recorded test). `staff-report-experience-designer` owns every rendered word;
this contract guarantees they can render, without recomputing anything: the three combinations
with per-lever asks in native units plus own-fraction context, the confirming run's margins, and
— for the null and fewer-than-3 cases — **the counts and the deduped reasons** ("all 39
searched combinations either exceeded a plausible-ask range (34) or moved rates and cap rate
apart by more than the 200 bps hypothesis band (5)"), so the null is an explained answer, not
silence. Fewer than 3: render what exists with the honest count; zero: `honest_null` rendering.
Both measured live: `82_champlain` fills all 3; `36_kelly` (run as a stress case) produces the
full-null path — 7 rays edge-infeasible, 4 gate-rejected by R2, 0 candidates.

### Scoping and the demo-fixture problem

The section computes iff `is_genuinely_close` opens — the same gate, one decision, no second
threshold (PD.1 (b) kept 3 and this design does not touch it). The consequence the evaluation
flagged is real and measured: **`36_kelly_moncton` is 4-fails, gate-closed, so the flagship
demo renders NEITHER recourse section**, and Half B would ship a second section invisible in
the default demo. What the design needs from a demo fixture: a committed deal with (i) the gate
open, (ii) ≥3 jointly-plausible distinct-lever-set combinations, (iii) single-lever context
that motivates combinations. **`82_champlain_dieppe` already satisfies all three, measured**
(3 fails; full top-3; and by §0 fact 3 no single lever within its plausible cap closes it —
the exact "one lever isn't enough, three combinations are" story Half B exists to tell).
Recommendation (PD.2 Q6): promote `82_champlain` to the documented demo walkthrough for
recourse (manual-testing doc + READMEs); `36_kelly` and default `python main.py` output stay
byte-identical. QA additionally needs one constructed gate-open deal where ALL rays die (the
`36_kelly` dynamic on an open-gate deal) to pin the honest-null rendering end-to-end.

---

## 7. Does Half B degrade gracefully if the AD checkpoint returns NO-GO? — Yes, and better than that

The measured-winning search **uses no derivatives at all**: bisection on deterministic rays,
exactly Mission 4's primitive. The Jacobian's two Half-B roles (§1: subset pruning, the one
blended ray) both accept D.1's `MetricsJacobian` **shape** regardless of what filled it — an AD
pass (measured 4.1× one engine pass) or 8 central-FD probes (measured ≈0.34 ms vs ≈0.17 ms
dual, D.1/D.2) — and both are droppable entirely: pruning without the Jacobian costs at most
the 1-probe edge test the scheme already pays per ray; the blended ray is one of 40. **Half B
is therefore not hostage to Half A's AD checkpoint in any form: AD is an accelerator and a
cleanliness win for Half A's single-lever Newton, not a Half-B dependency.** The mission
charter's framing ("the optimizer consumes the exact AD Jacobian", gradient-driven search) is
overturned by measurement on this point, and the internal checkpoint's debugging value is
preserved in the opposite direction: a wrong top-3 can only be an optimizer/gate bug, because
the search never consumed a derivative.

The real portfolio-scale dependency is elsewhere: at 5,000 units/100 years the balanced-only
pipeline measured **337 ms**, of which the dominant term is rent-containing probes at 3.01 ms
each (the `_perturb` roll — D.2's 74.5% term wearing its Half-B face; non-rent probes are
0.20 ms). **The D.1 §1a aggregate-shift seam (plain-float variant included) is what keeps
Half B inside any sane budget at scale** (projected ~60–100 ms balanced grid; the 39-ray grid
scales linearly). That seam ships with Half A on D.1's recommendation regardless of the AD
go/no-go, and PF.1 owns the budget ruling; stated here so nobody re-discovers it in
implementation week.

Total measured budget, small deals (2–4 units): 39-ray grid ≈ 370–410 light probes + 3 full
confirms ≈ **30–46 ms** end-to-end in the unoptimized prototype — comfortably inside the
mission's 30 ms target once the confirm-only-top-3 structure (the prototype confirmed every
candidate; the design confirms 3–5) and the rent seam land.

---

## 8. The questions for PD.2 — with recommended defaults

Six questions, grouped; each with the default I would ship and the trade-off bought.

**Gate rules (the policy inside §3's mechanism):**

1. **Adopt R2, the joint-rejector rule?** — **Default: YES.** Pure reuse of
   `reject_unrealistic` with both axes populated (zero new constants); it is the entire
   substance of "individually fine, jointly implausible" (§3's fixture). Trade-off: it will
   reject some combinations a human might defend — e.g. "buy at an 8.1 cap in a 6.9 cap
   market after a 15% cut" — and the reason string must therefore always name both numbers so
   the investor can disagree with the flag, not wonder about it.
2. **Adopt R3 (total ask budget), and at what B?** — **Default: YES, B = 2.0** ("a combination
   may total at most two maxed-out single asks"). Measured calibration: every minimal crossing
   on the fixture deals sums 1.3–1.6 fractions (untouched at B=2.0); the maxed-out 4-lever
   corner sums 4.0 (rejected); B=1.5 measured too aggressive — it rejected 7 of 11 balanced-grid
   crossings on the near-miss fixture. Trade-off: B is a **new constant with no repo
   provenance** — the first one in the recourse module (everything else is reuse); declining R3
   means the maxed-out-everything combination ships un-flagged whenever R2 doesn't happen to
   catch it.
3. **Adopt R4 (price-cut + rent-raise posture rule)?** — **Default: NO for v1** (YAGNI). R2
   already fires on the market-math face of deep price+rent moves; R4's "you're telling the
   seller two different stories" concern is real but has no repo-derived threshold, and
   inventing two constants in one gate is how thresholds stop being explainable. If adopted:
   `f_price + f_rent ≤ C`, and C needs founder provenance, not an engineer's guess.

**Display policy:**

4. **Are gate-rejected combinations ever SHOWN (Mission 4 flag-don't-remove style), or
   filtered with aggregate honest-null reasons (§6)?** — **Default: filtered.** The
   single-lever menu shows flagged rows because there are exactly 4×fails of them and each
   answers "what would it take" for one guardrail; the combination space is 39+ searched rays,
   and rendering rejected ones manufactures a menu of implausible negotiations — the exact
   appearance-of-an-answer this product refuses. The flag-don't-remove spirit is preserved at
   the aggregate: counts + deduped reasons ship in the data contract and the null copy.
   Trade-off: an investor cannot see the specific almost-plausible combination that was
   rejected; if Roger wants one exemplar, the contract can carry the single best-K rejected
   candidate with its reason — say so and it's additive.
5. **Parsimony strictly before magnitude, and no padding below 3?** — **Default: YES to
   both.** Fewer negotiations beat smaller ones (a 2-lever combo with 0.7-fraction asks
   outranks a 3-lever with 0.4s), and fewer-than-3 distinct routes ships as the honest count
   rather than near-duplicate variants. Trade-off: a deal whose cheapest genuine route is
   3-lever ranks it below a chunkier 2-lever route; the measured fixtures all surface 2-lever
   routes first anyway.

**Demo:**

6. **Promote `82_champlain_dieppe` to the documented recourse/combinations demo walkthrough?**
   — **Default: YES** (§6: it is committed, gate-open, and measured to fill all three slots
   with distinct-lever-set combinations while no single plausible lever suffices).
   `36_kelly_moncton` and the default `python main.py` bytes do not move. Trade-off: the
   flagship deal still shows neither recourse section; the alternative — engineering a new
   flagship — is a product-surface change PD.1 (b) already declined once this mission.

---

## 9. Reproduction

```bash
source /home/rtokime/anaconda3/etc/profile.d/conda.sh && conda activate airedeal
S=/tmp/claude-1002/-home-rtokime-projects-Personal-ai-real-estate-deal-analyzer/cf7ad590-667f-45d2-a021-0d4460f8c353/scratchpad/d4
python $S/harness.py             # problem shape: live/failing, boxes, full-box feasibility, 3 deals
python $S/scan_monotone.py       # §0 fact 1: monotone margins, 2,196 segments
python $S/proto_methods.py       # §1 table: ray-bisect vs Newton-FD vs SQP/PG/AL
python $S/proto_methods2.py      # §1 table: SQP walk-back cost, interior point
python $S/proto_gate.py          # §3: joint gate rules + full-box fixture candidates
python $S/proto_fixture_qa.py    # §3: the strictly-interior worked fixture, confirm-by-rerun
python $S/proto_pipeline.py      # §2/§4: grid-stability of the top-3 (import-guarded main)
python $S/proto_scale.py         # §2 determinism, §5/§7 portfolio-scale costs, kelly full-null
python $S/proto_final_checks.py  # §0 fact 3 (no single lever suffices), §2 local-minima demo
```

(Scratchpad is session-local; scripts are throwaway measurement instruments per the discovery
constraint, quoted so a reviewer can re-create them from this memo.)

## 10. Deltas found against the planning record (for the tracker)

- The charter's premise that Half B's optimizer is gradient-driven off the AD Jacobian is
  **overturn-by-measurement** (§1, §7): the winning method is derivative-free; the Jacobian's
  Half-B roles are pruning and one optional ray. The internal AD checkpoint no longer gates
  Half B's viability — only Half A's Newton. This should be restated at the checkpoint so
  NO-GO ≠ defer-Half-B.
- The mission's 30 ms perf target at portfolio scale is governed by the D.1 §1a aggregate-shift
  seam, not by AD and not by the optimizer (§7). PF.1 should budget Half B **with** that seam.
- `36_kelly_moncton` renders no recourse section at all (gate-closed, 4 fails, re-confirmed) —
  the Half-B demo story needs `82_champlain_dieppe` promoted or it ships invisible (§6, PD.2 Q6).

— staff-python-engineer · Mission 5 Discovery D.4 · 2026-08-31
