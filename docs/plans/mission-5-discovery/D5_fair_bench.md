# D.5 — Fair head-to-head: multi-lever recourse search architectures (Mission 5, Discovery)

**Branch** `mission/5-adjoint-differentiation` @ `87efd22` · **Date** 2026-08-31 ·
**Status** Discovery finding — no production code written; all instruments in the session
scratchpad (`scratchpad/d5/`: `common.py`, `contenders.py`, `reference.py`, `bench.py`,
`gate_eval.py`, `det_run.py`), reusing D.4's harness and D.1's validated Dual4 forward-AD
prototype from the same scratchpad. Every number reproduces under the `airedeal` conda env
(`source /home/rtokime/anaconda3/etc/profile.d/conda.sh && conda activate airedeal`).

**Mandate.** D.4 benchmarked augmented Lagrangian and interior point as *cold-start standalone*
methods and concluded against gradient-based search. Roger's specified architecture — one AD
pass → n gradient-informed starting points → gradient-based constrained optimization from each —
was never tested. This memo tests it, tuned in good faith, against D.4's incumbent and the
gradient-direction/bisection-distance synthesis, on the real engine, with quality and coverage
measured against a dense offline reference frontier — not probe counts alone. D.4's conclusion
was treated as an untested hypothesis throughout.

---

## 0. The contenders, as actually implemented

All consume the same `Probe` (real `forecast_metrics`/`_perturb` light path), search the same
plausibility box in own-fraction space `x ∈ [0,1]⁴`, and feed the same K-order top-3 selector
(parsimony → leximin, D.4 §4). Cost convention: **p-eq** = engine probes + AD passes × 4.11
(the re-measured Dual4/engine ratio, §2).

- **A — Founder's architecture** (three tuned variants, so no strawman survives):
  - **A1 (faithful):** one Dual4 AD pass at t=0 → the full margin Jacobian → **4 per-partial
    seeds** (each lever's linearized single-lever fix, clipped to its cap) + 1 LP-combined seed
    → full 4-D constrained optimization from each. Two optimizers benched: **SLSQP** (SQP
    family; objective = total own-fraction ask, constraint gradients from the AD oracle) and a
    **properly built augmented Lagrangian** (hinge form, normalized constraints, L-BFGS-B inner
    solver with AD gradients, λ warm-started, ρ₀=10 ×10/outer — schedule documented, sensitivity
    measured in §6). A Chebyshev-objective variant (min max-fraction) was also run.
  - **A2 (tuned to the product contract):** the same SQP, restricted per lever-subset (11
    subsets), gradient-seeded, both scalarizations — the strongest version of "gradient methods
    find proper solutions" for a 3-diverse-combination product.
  - **A3 (gate-internalized):** A2 with the joint gate's R2 rejector band
    (|rate_delta − cap_delta| ≤ 0.02, via the AD cap-rate tangent) and R3 budget (Σf ≤ B) as
    differentiable constraints inside the SQP — something no bisection grid can do; measured
    where the gate binds.
- **B — D.4's incumbent:** the fixed 39-ray grid (balanced + 0.5-tilts over 11 subsets),
  safeguarded bisection to 1e-3 per ray.
- **C — The synthesis:** one AD pass at t=0 → per-subset **direction selection** by two tiny
  deterministic LPs on the linearized margins (min-sum and min-max directions — the principled
  form of "steepest margin-gain per unit ask") → **bisection for distance** along each chosen
  direction (≤22 rays). Honest fallback to the balanced ray when the linearization is
  infeasible.
- **D — Baseline:** production `compute_recourse` (single-lever menu), probe-counted via
  monkeypatched engine entry points.

All optimizer outputs pass through one common post-step (mirroring production
round-away-from-zero): epsilon-infeasible boundary points are inflated by the smallest factor
from a fixed ladder (≤6 probes). Without it SLSQP ships boundary-sitting points that fail a
strict feasibility check — a real integration cost of the gradient family, charged to it fairly
(≤6 probes) rather than used to disqualify it.

**The AD oracle is real AD, not a stand-in:** D.1's Dual4 slice, re-validated this session
against central FD of the *production* engine on all three deals at t=0 and mid-box —
max relative Jacobian discrepancy 1.3e-3 (near_miss), 1.5e-4 (champlain), 2.4e-4 (kelly);
primal margins bit-identical to the engine (≤4e-12).

## 1. The reference frontier (the coverage oracle)

Per deal, per subset: a dense deterministic direction fan (179 angles per pair, 253/286
simplex-grid directions per triple/quad — 2,372 directions), each bisected to the guardrail
frontier. Offline; cost no object (17.5k–22.3k probes/deal).

| Deal | frontier points | feasible subsets | near-optimal points |
|---|---|---|---|
| near_miss (4u fixture) | 1,237 | 10/11 (interest+annual infeasible) | 372 |
| 82_champlain | 1,644 | 11/11 | 622 |
| 36_kelly | 91 | **4/11** — no 2-lever combination exists at all | 29 |

## 2. The two facts re-verified (not assumed)

- **Monotonicity / up-set property: HOLDS, and more broadly than D.4 measured.** D.4's full
  scan re-run: 61-point scans × 4 axes × 11 diagonals × 3 deals — zero non-monotone segments.
  New this session: **308 arbitrary (non-diagonal) rays** — every 10th reference direction —
  scanned at 21 points each: **zero multi-crossings, zero feasible→infeasible reversals**.
  Contender C's foundation stands on strictly wider evidence than before. (Still an empirical
  property of these deal shapes, not a theorem — see §8.)
- **AD cost: 4.11× one engine pass at demo scale, re-measured** (`d1/proto_dual4_opt.py`
  re-run: 183 µs vs 44.5 µs). **At 5,000 units the headline does not hold without the D.1 §1a
  rent-aggregate seam:** the Dual4 pass measured **5.9 ms = 36.6× a plain pass** (0.16 ms),
  because the O(units) rent loop gets dualized while the plain engine reuses precomputed
  income. Even so it beats the FD alternative at scale (8 probes incl. 2 rent-materialising
  ≈ 9.8 ms). With the aggregate seam both collapse; the seam governs everyone's budget, as
  D.4 §7 said.

## 3. Head-to-head results

### 3a. Solution quality — the product's shipped top-3

**On every fixture, A2, B, and C ship the identical K-order top-3** (differences ≤0.001 of a
cap fraction, below `ROUND_STEP`):

| Deal | shipped top-3 (identical for A2 / B / C) |
|---|---|
| 82_champlain | rent 0.605 + price 0.605 · price 0.642 + rate 0.642 · rent 0.679 + rate 0.679 |
| near_miss | rent 0.638 + price 0.638 · price 0.722 + opex 0.722 · price 0.805 + rate 0.805 |
| 36_kelly | rent+price+rate 0.771 · rent+price+opex 0.894 · price+rate+opex 0.934 (pre-gate; §5) |

**A1 (faithful) ships ONE combination**, not a menu: all 4–5 seeds converge to the same global
min-total-ask point (e.g. champlain: rent 0.129 + price 1.000, Σf = 1.129). Under min-sum that
point is **genuinely the best answer any contender found** — but it is a single, price-maxed
negotiation, ranked last by the product's leximin key, and it cannot fill three diverse slots.
The founder's n-seeds idea produces n *starts*, not n *answers*: with a shared objective and a
connected feasible set, they collapse to one optimum. Diversity requires subset restriction —
at which point A structurally becomes C-with-SQP-distance (A2).

**Per-subset optimality, measured against the reference** (gap = contender best − reference
best, worst subset):

| Contender | gap on max-fraction (leximin metric) | gap on sum-fraction (total-ask metric) |
|---|---|---|
| A2 | **≤0.001** (occasionally −0.001, beats bisection tol) | **≤0.004 on pairs; beats the dense reference itself on kelly triples** (2.229 vs grid 2.339) |
| B | **0.000 — exactly optimal on every subset, every deal** | 0.04–0.45 worse (see 3b) |
| C | 0.000–0.001 | ≤0.004 on 4/6 pairs; 0.03–0.25 worse on triples |

B's perfect max-fraction column is not luck: **under the verified monotone up-set geometry, the
min-max point of every subset frontier lies exactly on the balanced diagonal — B's balanced ray
IS the Chebyshev optimum by construction.** This is the cleanest fact in the whole bench and
explains D.4's grid-stability table: the product's leximin ordering is precisely the metric the
balanced grid cannot lose.

### 3b. ⭐ Coverage — does the 39-ray grid miss combinations? Yes: one specific class.

The grid misses the **minimum-total-ask family** — solutions concentrated on the cheapest
lever(s), lying between/outside its 1.0/0.5 tilt patterns. Measured, per subset best Σf:

| Deal, subset | reference Σ* | gradient (A2) | grid (B) | B's excess ask |
|---|---|---|---|---|
| champlain, price+opex | 1.199 | 1.195 | 1.305 | +0.106 cap-fractions |
| champlain, rate+opex | 1.558 | 1.555 | 1.641 | +0.086 |
| champlain, rent+price | 1.129 | **1.129** | 1.175 | +0.046 |
| near_miss, rent+price | 1.189 | **1.187** | 1.230 | +0.043 |
| 36_kelly, rent+price+opex | 2.339† | **2.229** | 2.681 | **+0.452** |
| 36_kelly, price+rate+opex | 2.625† | **2.566** | 2.801 | +0.235 |

† the dense reference grid's own minimum; A2 found strictly better points than the reference —
gradient search reaches places even a 2,372-direction fan does not.

In native units (champlain rent+price): the gradient answer is rent **+$18/mo** + price
**−$90,750**; the grid's best is rent +$55/mo + price −$71k. Different negotiation postures;
the gradient one asks measurably less in total. These points **survive the joint gate** on
champlain and near_miss (§5) — they are not implausible artifacts.

**However: none of the missed points win under the product's current K-order** (parsimony →
leximin). Every one has a maxed or near-maxed lever, so leximin ranks it below the balanced
crossings B already finds. The grid's blindness is invisible in today's shipped top-3 and
becomes a product defect **only if** the founder wants a "cheapest total negotiation" slot —
which is a live product question this memo surfaces for PD, not an engineering call.

**Frontier recall** (share of reference points within L∞ ε of any candidate; nR = recall of the
near-optimal region):

| Contender | champlain R@.05/R@.10/nR@.05 | near_miss | kelly |
|---|---|---|---|
| A1 | 0.01 / 0.01 / 0.02 | 0.01 / 0.02 / 0.02 | 0.00 / 0.01 / 0.00 |
| A2 | 0.08 / 0.22 / 0.22 | 0.08 / 0.21 / 0.26 | 0.03 / 0.09 / 0.10 |
| B | **0.13 / 0.37 / 0.26** | **0.11 / 0.33 / 0.30** | 0.03 / 0.09 / 0.10 |
| C | 0.09 / 0.25 / 0.23 | 0.07 / 0.18 / 0.23 | **0.04 / 0.11 / 0.10** |

B's 34–39 spread-out candidates give it the best raw frontier coverage; near-optimal-region
recall is comparable (0.10–0.30) for A2/B/C. No contender "covers" a continuous 3-manifold with
≤40 points — the product ships representatives, and on the representatives that matter
(per-subset optima) the table in 3a is the decisive one. Subset coverage is 10/10, 11/11, 4/4
for A2/B/C everywhere; A1 covers 1 subset by construction.

### 3c. Cost (search only; the gate adds ~1 probe per candidate for everyone)

| p-eq (probes + 4.11×AD) | near_miss | champlain | 36_kelly | null deal† | 5,000u wall (10y, failing deal) |
|---|---|---|---|---|---|
| A1-SQP (faithful) | 146 | 204 | 192 | 236 | 810 ms (1 combo) |
| A1-AL (faithful) | 782 | 843 | 810 | — | — |
| A2-SQP sub | 624 | 475 | **1,686** | **2,356** | 798 ms |
| A3-SQP gate-in | 507 | 532 | **3,856** | — | — |
| B 39-ray | 339 | 379 | 89 | 39 | 1,862 ms |
| C AD-dir+bisect | **186** | **246** | **77** | **15** | 1,023 ms |
| D single-lever (context) | 171 | 160 | 188 | — | — |

† constructed guardrail-infeasible deal (price 900k variant): all four contenders correctly
report the honest null; C proves it in ~15 p-eq (one AD pass shows the linearization
infeasible + 11 edge probes confirm), B in 39, while SQP burns 60 iterations per subset
before giving up — **infeasibility detection is bisection-family territory**; a production A
would need to bolt on exactly the edge-probe guard B/C already have. Note kelly: A2/A3's worst
numbers are this same failure mode (7 of 11 subsets infeasible). At 5,000 units the ordering
flips toward the gradient family (fewer rent-materialising probes): A2 798 ms < C 1,023 ms <
B 1,862 ms — all dominated by the 4.5 ms rent probe the D.1 aggregate seam removes.

## 4. Determinism

All six variants (A1-SQP, A1-AL, A2, A3, B, C): **byte-identical serialized candidate lists and
top-3 across repeated fresh-process runs under PYTHONHASHSEED=0 and =42**, on champlain and
near_miss. Enumeration is fixed-tuple ordered; no RNG; scipy's SLSQP/L-BFGS-B/HiGHS are
deterministic on a fixed build. **Caveat that separates the families:** A and C-as-benched take
a scipy dependency into the answer path; byte-stability across *scipy upgrades* is not
guaranteed for optimizer iterates. B is stdlib-pure. C's LP is small enough to replace with a
closed-form/pure-Python direction rule if that guarantee is wanted — the direction only needs
to be *good*, since bisection owns correctness of the distance.

## 5. Gate composition (R1 + R2 joint rejector + R3 budget)

- **champlain, near_miss (B=2.0): every candidate of every contender survives** — including
  A1's price-maxed min-sum points (rate untouched ⇒ R2's divergence stays inside the 0.02
  band). The gate does not rescue or penalize any architecture on the open-gate deals.
- **36_kelly: the post-gate null is REAL, and everyone reports it.** New measurement: all 91
  dense-reference frontier points AND their 1.05× inflations fail the gate (minimum R2
  divergence 0.0215 > 0.02). The guardrail-feasible ∩ gate-plausible set is **empty** — D.4's
  full-null rendering path is confirmed as the correct product outcome, from the frontier
  itself, not from any search's failure. A3 (gate-internalized SQP) burned 3,856 p-eq to
  discover this emptiness; C+filter proved the same for ~83.
- **near_miss with the aggressive R3 B=1.5** (D.4's known-local-minima scenario): every
  multi-start contender still fills a full, plausible top-3 from survivors (A2, A3, B, C all
  do; A3 satisfies the budget *by construction*). D.4's false-null risk is a **single-start**
  failure mode, not a gradient-method failure mode.
- Where the gate-feasible set is nonempty and R3 binds, A3's constraint-internalization works
  as designed (produces budget-satisfying candidates directly). Where it is empty, it has the
  worst cost profile in the bench. Search-then-filter with a fallback grid is the robust
  composition; internalization is an optimization, not a foundation.

## 6. Robustness

- **Knob sensitivity — D.4's central objection to the Lagrangian family does NOT reproduce
  when the method is built properly.** The tuned AL returns the *identical* answer for
  ρ₀ ∈ {1, 10, 100} and ×2 vs ×10 growth (only cost moves: 843–1,036 p-eq). SLSQP's top-3 is
  stable across ftol 1e-6→1e-10 (≤0.001, sub-ROUND_STEP). D.4's "answer visibly depends on the
  ρ-schedule" was an artifact of its fixed-step, no-inner-solver prototype. Withdrawn as an
  argument against A; replaced by the real costs above.
- **Capped lever** (rate baseline 0.4%, price 750k — failing irr+cap_floor): no contender
  mis-behaves; the gradient methods additionally *discover the active set collapses to single
  levers* (price −30.6% of cap alone suffices) — asks that Mission 4's own menu covers.
- **Engine bug found by this bench** (report, don't fix — Discovery):
  `amortization_payment` (`src/core/finance/amortization.py:39`) raises `ZeroDivisionError`
  for `rate ∈ (0, ~1e-12)` — the `rate <= 0` guard misses denormal-small rates where
  `(1.0+r)**(-years) == 1.0` in floats. Repro: `amortization_payment(1e5, 1e-17, 30)`.
  Unreachable from parsed listings; **reachable by any optimizer or bisection walking the rate
  lever to its floor — exactly Mission 5's code path.** Implementation week must add a guard
  (core/finance touch: flag, justify, golden-test per invariant 6/8).

## 7. Recommendation

**Adopt contender C — gradient-chosen directions, bisection-owned distances — as the Half-B
search architecture, and absorb the founder's insight into it explicitly: the AD pass's n
partial derivatives ARE the n starting points, expressed as starting *directions*.** The
Lagrangian/SQP polish stage of the faithful architecture is measured as optional: it buys
0.00–0.03 cap-fractions on pairs over C's LP-direction crossings, at 2–10× the cost, with two
integration burdens C doesn't have (epsilon-infeasible outputs needing a polish ladder;
pathological cost on infeasible subsets/deals).

Concretely, against each alternative:
- **vs B:** equal shipped top-3 on every fixture (and provably equal on the leximin metric —
  B's balanced rays are Chebyshev-optimal under re-verified monotonicity); 35–50 % fewer
  probes at demo scale, 1.8× at 5,000 units; the cheapest honest-null proof in the bench
  (15 vs 39 p-eq globally; 1 AD pass prunes infeasible subsets before any probe on kelly-class
  deals); and it can reach the min-sum family B cannot express (within 0.03 on pairs).
- **vs A-faithful:** A yields one combination, not a menu; its single answer is the min-sum
  optimum, which C approximates to 0.03 and an optional single SQP polish run (+~100 p-eq)
  recovers exactly, **if** PD wants a "cheapest total negotiation" fourth slot — that product
  question is this bench's most useful escalation. If Roger says yes, the winning design is
  C + one A-style polish on the best min-sum direction, and the founder's architecture ships
  as that component.

**The strongest argument against this recommendation:** C's advantage rests on (i) an
empirical monotonicity property — re-verified across 2,196 segments + 308 arbitrary rays with
zero violations, but an engine change (refi paths, new guardrails) could break it silently,
and B degrades identically in that world while pure-SQP would not care; and (ii) a scipy
dependency in the answer path that B alone avoids — cross-version byte-stability requires
either pinning or replacing the tiny LP with a closed-form direction rule. If the founder
weighs zero-dependency byte-stability and maximal frontier spread (B's R@.10 = 0.33–0.37 vs
C's 0.18–0.25) over ~40 % of the probe budget and min-sum reachability, **B remains a
defensible choice — this bench found no fixture where B ships a wrong or worse top-3.** What
it cannot do, measured: express any solution off its 39 directions (up to +0.45 cap-fractions
of unnecessary total ask on kelly-class asks), prune an infeasible subset for less than one
probe, or honor an R3-style budget by construction.

## 8. What AD is worth in the winning design — precisely

- **Direction selection: this is where AD earns its keep.** One pass at t=0 (4.11 probe-equiv
  demo / 5.9 ms at 5,000u pre-seam) yields all n partials → per-subset optimal directions →
  35–50 % probe savings vs the fixed grid at equal shipped quality, plus subset pruning and
  the 15-p-eq global-null proof. This *is* the founder's "n starting points from n partial
  derivatives," landed in direction space where the product's diversity requirement lives.
- **Distance along a direction: AD is worth nothing.** Re-confirmed: bisection's fixed 10
  probes beat every derivative scheme on the frontier landing; D.4 was right here and stays
  right.
- **As fuel for a full Lagrangian/SQP solve:** it works — converges, knob-robust (D.4's
  contrary claim withdrawn as an implementation artifact), and finds strictly-better min-sum
  answers (up to 0.45 cap-fractions on kelly) — but it is worth paying for **only** if the
  product adds a min-total-ask proposition; it is not needed for the current top-3, which
  three different architectures reproduce identically.
- **As gate-constraint fuel (A3):** works where the gate-feasible set is nonempty; worst-in-
  bench where it is empty. Keep the gate as a filter with C's fallback rays.
- **Versus FD if AD never ships:** FD-8 replaces the pass at ~2× its cost at demo scale and
  ~1.7× at 5,000u; every conclusion above survives with FD, so **Half B remains not hostage
  to the AD checkpoint** (D.4 §7 upheld) — AD just makes the winning design's first move
  cheaper and exact.
- **Scale caveat:** the 4.11× ratio is a demo-scale number. Without the D.1 §1a rent-aggregate
  seam a 5,000-unit Dual4 pass is 36.6× a plain pass (still cheaper than FD-8's rent probes).
  The seam is the scale budget for every contender and must ship with Half B regardless.

## 9. Deltas against the planning record (for the tracker)

1. **D.4's anti-Lagrangian evidence is corrected:** the knob-sensitivity and 182-probe figures
   described a cold-start, fixed-step prototype. Tuned and AD-seeded, the founder's
   architecture converges deterministically and knob-robustly to the true min-sum optimum.
   D.4's *conclusion* survives on different grounds: menu diversity, infeasibility-detection
   cost, and the K-order metric where the grid is provably optimal.
2. **New geometric fact:** under the (re-verified, broadened) monotone up-set property, the
   balanced ray's crossing is the exact Chebyshev-minimal point of each subset — the incumbent
   grid is optimal on the product's primary metric *by construction*, which is why every
   architecture agrees on the shipped top-3.
3. **Quantified grid blindness:** the 39-ray grid over-asks by 0.04–0.45 summed cap-fractions
   on the min-total-ask family. Product question for PD.2: is "cheapest total negotiation" a
   fourth proposition? If yes, one SQP polish run joins the design.
4. **36_kelly's post-gate null is proven empty** from the dense frontier (0/91 pass, min R2
   divergence 0.0215), not merely observed by one search.
5. **Engine bug:** `amortization_payment` div-by-zero for denormal-small rates
   (`src/core/finance/amortization.py:39`) — must be guarded in implementation week.
6. Monotonicity: re-verified, including 308 non-diagonal rays (0 violations). AD ratio:
   re-verified 4.11× at demo scale; does **not** hold at 5,000u without the aggregate seam
   (36.6×, still < FD-8).

## 10. Reproduction

```bash
source /home/rtokime/anaconda3/etc/profile.d/conda.sh && conda activate airedeal
S=/tmp/claude-1002/-home-rtokime-projects-Personal-ai-real-estate-deal-analyzer/cf7ad590-667f-45d2-a021-0d4460f8c353/scratchpad/d5
cd $S
python ../d4/scan_monotone.py         # monotonicity re-verification (D.4 scan, re-run)
python ../d1/proto_dual4_opt.py       # AD ratio re-verification (4.11x)
python reference.py 82_champlain      # dense reference frontier (+ per-deal ref_*.json)
python bench.py 82_champlain          # §3 tables (quality, recall, cost) per deal
python gate_eval.py 36_kelly          # §5 post-gate results incl. A3
PYTHONHASHSEED=0 python det_run.py 82_champlain a.json   # §4 determinism (diff vs seed 42)
```

(Scratchpad is session-local; instruments are throwaway per the discovery constraint, quoted
so a reviewer can re-create them from this memo.)

— staff-python-engineer · Mission 5 Discovery D.5 · 2026-08-31
