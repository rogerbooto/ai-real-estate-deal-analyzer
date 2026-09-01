# D.2 — Measured performance baseline, the 73 ms reconciliation, and the Amdahl arithmetic

**Mission 5, Discovery wave · `principal-performance-engineer` · 2026-08-31**
**Branch `mission/5-adjoint-differentiation` @ `87efd22` · env `airedeal` (`/home/rtokime/anaconda3/envs/airedeal/bin/python`, 3.10.18)**
**No production code written. All instrumentation lived in a scratchpad and is discarded.**

---

## 0. Headline

> The mission's premise is **half right**. Recourse search really is ~95% of the budgeted row — but
> the cost is not in the *search arithmetic*, it is in the *perturbation object graph*. **74.5% of
> the 5,000u/100y row is `_perturb` rebuilding 5,000 pydantic `UnitIncome` models 39 times, and
> 36% of the whole row is the garbage collection that churn causes.** Cutting probes 12.5 → 4 per
> pair attacks that term only proportionally, and lands at **~82 ms — 2.7× over the 30 ms target.**
> **AD cannot reach 30 ms on its own at any plausible dual-pass cost.** Two interventions with a
> fraction of AD's blast radius get closer: a scoped GC threshold change is a **measured 119 ms**
> and touches zero finance-core code; an O(1) rent aggregate projects to ~44–49 ms.

---

## 1. The measured baseline — 5,000u / 100y PRIMARY row

Command (repeated; the committed harness, unmodified):

```
source /home/rtokime/anaconda3/etc/profile.d/conda.sh && conda activate airedeal
python -m tests.perf.bench_finance_engine --repeats 9
```

| # | source | best ms | median ms | machine state |
|---|--------|--------:|----------:|---------------|
| 1 | committed bench, `--repeats 9` | **197.8** | 203.0 | quiet-ish (load ~4) |
| 4 | committed bench, `--repeats 9` | **187.2** | 189.3 | load 5.4 |
| — | direct `compute_recourse`, **21 consecutive samples** | **174.9** | 181.2 (max 186.4) | load 5.2 |
| — | 4 further control runs (n=9) during the GC experiment | 187.4 / 189.9 / 191.0 / 192.8 | 195.6–197.8 | load 5.2–5.5 |
| 2 | committed bench, `--repeats 9` | 353.7 | 365.5 | **contended** |
| 3 | committed bench, `--repeats 9` | 332.9 | 342.7 | **contended** |

**Honest baseline: best 175–198 ms, median 181–203 ms in a quiet window; 333–366 ms under
contention.** Verdict against `BUDGET_MS = 250.0` (`tests/perf/bench_finance_engine.py:97`):
**PASS quiet, FAIL contended** — exactly the thin-headroom failure mode the constant's own comment
predicts at `:91-96`. This reproduces the committed docstring's "181–197 ms best / up to 213 ms
median" without correction.

**Variance, stated plainly.** Within a single warm process the spread is tight (21 samples:
174.9–186.4, ±3%). Across processes in similar conditions it is ±12%. Across load states it is
**1.9×**. A single run is not a baseline; every comparative number below was taken back-to-back
inside one process, so the *ratios* are sound even where the absolutes drift.

**Machine-noise caveat (material).** 24 cores / 31 GB. An unrelated PhD training job
(`rt-steering`) held ~5 cores at 100% throughout, load avg 5.2–5.9, **swap fully consumed
(2047/2047 MB)**, ~5 GB available RAM, `/proc/pressure/memory` `some avg300 = 1.09`. Runs 2 and 3
inflated *uniformly* ~1.8× across every attribution cell (engine-only 163→296 µs, price-search
175→311 µs), which is the signature of machine-wide contention, not a regression.

### Other rows (same runs)

| row | best/median (quiet) | probes |
|---|---|---|
| 5,000u / 100y (ceiling) | 187.2–197.8 / 189.3–203.0 ms | 150 |
| `36_kelly_moncton` (10y, **real deal**) | 8.5 / 8.6 ms | 159 |
| `82_champlain_dieppe` (10y, **real deal**) | 7.3 / 7.4 ms | 135 |

Attribution table, quiet run (µs per probe): `engine-only` 163.3 · `price full` 685.7 ·
`price +reuse` 390.6 · `price search` 175.0 · **`rent search` 3836.1** — the rent shape is **21.9×**
the price shape.

### The budgets I own, re-verified today

| metric | budget | measured | verdict |
|---|---|---|---|
| `python main.py` cold | ≤ 5 s | **0.86 s** | PASS (17%) |
| `python main.py` warm | ≤ 2 s | **0.68 s** | PASS (34%) |
| Peak RSS, sample pipeline | ≤ 500 MB | **78.6 MB** (`/usr/bin/time -v`) | PASS (16%) |
| `import src` | ≤ 1 s | **8.4 ms** (`-X importtime`) | PASS |
| PRIMARY 5,000u/100y | ≤ 250 ms | 175–198 ms quiet | PASS quiet, FAIL contended |

**No budget is currently exceeded. Nothing to block.**

---

## 2. The "73 ms" verdict — **(b) a different operation, compounded by (c) staleness**

**Provenance found, and it is not a mystery.** `git log -S"73 ms"` resolves to the Mission 4 commit
`912a55f`. In `docs/plans/MISSION_4_SPRINT_TRACKER.md` (Case 7, "Actual result observed"):

> The run printed `5,000u / 100y … 73.8/ 74.0ms … <= 120 ms: PASS`, but that PASS did not measure
> the production loop.

That line is Roger's own **retraction**, written 2026-08-30. The figure came from the *second,
superseded* version of `bench_finance_engine.py`, which timed 432 synthetic probes **all using the
cheap `purchase_price` lever shape** and excluded `rent_per_unit_month` entirely — the shape that is
**~85% of the real cost**. The same tracker entry records the correction measured the same day:
calling the real `compute_recourse` at 5,000u/100y fires **150 probes in 192.7 ms**. The harness was
then rewritten to *call* the production loop and *count* its probes, and the budget was re-baselined
120 → 250 ms.

**So: 73.8 ms is a retracted number produced by a benchmark that no longer exists in the tree. It
never measured `compute_recourse`.** It is (b) a different operation — a synthetic model of the loop
priced entirely on its cheapest lever — and (c) stale, superseded within hours of being printed. Not
(a) a different row, not (d) a different machine, not (e) arithmetic error.

**And the "down from 13 s" half is spliced from a different table at a different horizon.** Case 8's
pre-fix measurements give full recourse with naive `deepcopy` at **5,000u / 50y = 12.68 s → 6.91 s**
surgical (quoted elsewhere in the same commit as "11.37 s wall time"); 5,000u/**100y** did not
produce a number at all — it **crashed** with `OverflowError` in `irr.py`. So the brief's
"73 ms, down from 13 s" pairs a 100-year figure from a retracted harness with a 50-year figure from
a deepcopy table. Neither endpoint describes the row Mission 5 is trying to move.

**Recommendation:** strike 73 ms from the mission narrative and replace it with **175–198 ms best /
181–203 ms median, 150 counted probes**. "30 ms" remains Roger's *target*; it appears nowhere in
code and no measurement has ever supported it.

---

## 3. Where the time actually goes

### 3.1 Probe count — **counted, not assumed**

One `compute_recourse` at 5,000u/100y, 3 failing guardrails (`dscr`, `spread`, `irr`), 4 levers =
**12 lever/guardrail pairs**:

```
_perturb total : 150   {purchase_price: 75, rent_per_unit_month: 39, interest_rate: 33, annual_opex: 3}
_rerun  total  : 141   (light path, forecast_metrics)
full run_financial_model inside recourse : 10  (9 confirming re-runs + 1 baseline)
```

| lever | probes per pair | structure |
|---|---:|---|
| `purchase_price` | **25** | 1 bound + 23 bisect + 1 confirm |
| `rent_per_unit_month` | **13** | 1 bound + 11 bisect + 1 confirm |
| `interest_rate` | **11** | 1 bound + 9 bisect + 1 confirm |
| `annual_opex` | **1** | bound probe fails → null row, no bisection |

**The mission's "~10–20 probes per lever/guardrail pair" is accurate** (measured 11–25 for the nine
pairs that bisect). Mean 12.5 across all 12 pairs.

### 3.2 The split — engine vs search vs everything else

Timed per call inside a real `compute_recourse` (best of 9; instrumented total 193.3 ms, which
brackets the uninstrumented 175–198 ms, so wrapper overhead is ≲1 ms):

| bucket | calls | best ms | µs/call | % of row |
|---|---:|---:|---:|---:|
| **`_perturb` rent_per_unit_month** | 39 | **143.99** | **3692** | **74.5%** |
| engine light probe, rent | 36 | 17.09 | 474.7 | 8.8% |
| engine light probe, price | 72 | 11.96 | 166.0 | 6.2% |
| engine light probe, rate | 30 | 4.97 | 165.8 | 2.6% |
| full `run_financial_model` confirms | 9 | 4.43 | ~490 | 2.3% |
| engine light probe, opex | 3 | 0.51 | 170.6 | 0.3% |
| baseline `run_financial_model` | 1 | 0.40 | 402 | 0.2% |
| `_perturb` price / rate / opex | 111 | 0.49 | ~4.3 | 0.3% |
| residual (thesis, snapshot, plausibility, model build, loop overhead) | — | 9.42 | — | 4.9% |

**Rolled up: engine forecast ≈ 39.4 ms (20.4%) · perturbation ≈ 144.5 ms (74.8%) · everything else
≈ 9.4 ms (4.9%).** The mission expected the split to fall out as "engine × probe count". It does
not: **the engine is a fifth of the row; the copy is three quarters of it.**

`cProfile -s tottime` corroborates independently — `_fast_unit_income` (585,000 calls) 0.325 s +
`set.copy` (588,900 calls) 0.155 s + the rent listcomp 0.087 s + `__new__` 0.028 s = **0.595 s of
0.851 s = 70%**. Note that `_UI_FIELDS_TEMPLATE.copy()` — one `set.copy()` per unit, for
`__pydantic_fields_set__` — is **18% of the entire analysis on its own.**

### 3.3 The finding nobody was looking for: **36% of the row is garbage collection**

Controlled ON → OFF → ON, same process, n=9 each:

| condition | best ms | median ms |
|---|---:|---:|
| `gc` enabled (control) | 192.8 | 196.1 |
| **`gc.disable()`** | **123.8** | 125.1 |
| `gc` re-enabled (control) | 191.0 | 197.8 |
| `gc.freeze()` after warm-up | 147.2 | 148.1 |
| `gc.set_threshold(700, 50, 50)` | 138.3 | 140.5 |
| **`gc.set_threshold(50000, 10, 10)`** | **119.0** | 119.6 |

**GC costs 69 ms — 35.8% of the row.** The ON/OFF/ON control rules out drift. Re-running the split
with GC disabled localises it completely: `_perturb` rent falls **3692 → 1729 µs/call** (−53%,
144.0 → 67.5 ms) while *every other bucket is unchanged* (engine rent 474.7 → 451.7, price
166.0 → 163.2, residual 9.42 → 9.93). The cause is unambiguous: **39 rent perturbations × 5,000
units = 195,000 short-lived `UnitIncome` objects per analysis**, which trips gen-0 collection
continuously and drags gen-1/gen-2 scans behind it.

This matters for the mission because it is a **~70 ms (36%) win available from a scoped GC
threshold change that touches no finance-core code, no golden values, and no arithmetic** — a
category of intervention the mission has not considered, sitting next to one that opens `engine.py`,
`irr.py`, and the 34-case bit-exact golden.

### 3.4 Amdahl arithmetic — **is 30 ms reachable at all?**

Built from the measured per-call costs above, holding the counted structure fixed. `k` = cost of an
AD dual pass relative to a plain forecast pass (**D.1 owns this number**; I parametrise it).
"AD" = probes 12.5 → 4 per pair (1 bound + ~2 Newton + 1 confirm), opex unchanged at 1.

| # | scenario | projected 5,000u/100y | vs 30 ms |
|---|---|---:|---|
| B | **measured baseline** | 175–198 ms | 6.4× |
| S1 | **AD only** (k=3; k=2 → 75, k=4 → 89) | **~82 ms** | **2.7× — MISSES** |
| S2 | GC threshold tuned, nothing else | **119 ms (measured, not projected)** | 4.0× |
| S3 | O(1) rent aggregate on the **search path only**, exact rebuild kept for the 3 confirms | ~44–49 ms | 1.6× |
| S4 | **S3 + AD** | ~34–35 ms | 1.15× — misses |
| S5 | S4 + O(1) aggregate on the confirming path too | **~29 ms** | just under |

**Structural floor.** With the rent rebuild eliminated everywhere, what remains is: baseline forecast
0.40 + `precompute_income` 0.27 + 12 bound probes ~2.0 + 9 confirming full re-runs 4.4 + residual
~9.4 ≈ **16.5 ms**. Keep the exact rebuild for the 3 rent confirms and it is **~22 ms**. So 30 ms
sits **8–13 ms above an irreducible floor** — reachable, but with almost no slack, and only in S5.

**Three conclusions, in order of decision weight:**

1. **AD alone cannot reach 30 ms at any plausible `k`.** Even at `k = 1` (a free dual pass) S1 lands
   at ~70 ms, because 44 ms of it is 12 surviving rent perturbations that AD does not remove.
2. **The binding constraint is the rent-roll rebuild, not the probe count.** Fixing it is worth
   ~145 ms *before* AD and still ~14 ms *after*; AD is worth ~14 ms *after* the rent fix and ~110 ms
   *before* it. **They are substitutes competing for the same dominant term, not complements** — and
   the cheaper one wins more of it.
3. **At a 30 ms target the ~9.4 ms residual becomes the #2 cost (31% of budget).** `cProfile` shows
   `_judge_plausibility`, `reject_unrealistic`, `synthesize_thesis`, `_derive_snapshot` and pydantic
   model construction are all ≪1 ms; the residual is interpreter overhead in the `_bisect`/
   `_search_one` loops plus my own instrumentation. It is measurement-limited and needs its own
   attribution pass **if and only if** 30 ms is adopted as a real budget.

---

## 4. numpy — re-measured, not assumed

**Installed in `airedeal`: numpy 1.26.4, scipy 1.15.3.** Both already present; adopting either costs
no new dependency.

| operation | pure Python | numpy | ratio |
|---|---:|---:|---|
| rent-roll aggregate, 5,000 units (`_annual_income` genexpr sum) | 260.3 µs | **2.7 µs** (pre-built arrays) | **96× faster** |
| …but building the arrays from pydantic models each time (`np.fromiter`) | — | 194.7 µs | wash |
| rent-perturbed aggregate `sum(u.rent + t …)` | 181.3 µs | **2.5 µs** (`(rents + t).sum()`) | **73× faster** |
| 100-year loop, one elementwise op | 1.672 µs | 0.466 µs | 3.6× on 1% of the pass |
| **AD proxy: 2,000-op chain, 4 dual components** | **154.4 µs** (4 scalar passes) | **1746.2 µs** (length-4 array) | **numpy 11.3× SLOWER** |

**Verdict — Mission 4's "do not vectorise" stands, re-measured, with one named exception and one
hard warning:**

* **The exception.** numpy is 96× on the O(units) rent-roll aggregate, but *only* if the arrays live
  in `PrecomputedIncome` and are built once per analysis. That is exactly the same intervention as
  the "O(1) rent aggregate" in S3/S5 — numpy is one implementation of it, not an independent win.
  **Both carry the same catch: pairwise summation ≠ sequential `sum()`, so neither is bit-exact**,
  which collides head-on with the 34-case golden. Both are therefore only defensible on the *search*
  path, with the shipped confirming re-run left exact.
* **The year loop does not vectorise.** 3.6× on ~1.7 µs of a 165 µs pass, and the loop is a
  *dependent recurrence* (the amortisation balance carries year to year), so it cannot be
  array-ified across years without restructuring `_forecast_core`. Bad trade, unchanged.
* **⚠ HARD INPUT TO D.1: dual numbers must NOT be numpy arrays.** A length-4 numpy vector carrying
  4 dual components is **11.3× slower** than 4 separate scalar passes, because numpy's ~0.87 µs
  per-op dispatch dwarfs a ~50 ns float op at length 4. If the AD design proposes numpy-backed
  duals, that is an 11× regression, and it would push `k` from ~2–4 to ~40 and make S1 *slower than
  the baseline*. Dual numbers here must be pure-Python scalars or a plain tuple.

---

## 5. Preliminary Gate D (PF.1) read

### **NO-GO on AD *as a performance intervention*. Conditional GO on AD *as the Half-B enabler*.**

**Basis (all measured above):**

1. AD alone projects to **~82 ms (75–89 across k = 2…4)** — **2.7× over the 30 ms target**. The
   performance rationale the mission gives for AD does not survive measurement.
2. **74.5%** of the row is `_perturb`'s rent path and **35.8%** of it is the GC that path causes.
   Two cheaper interventions beat AD on this term: GC threshold tuning is a **measured 119 ms** with
   *zero* finance-core diff; an O(1)/array rent aggregate projects to ~44–49 ms touching `_perturb`
   and `PrecomputedIncome` — **not** `irr.py`, **not** `_brent_root`.
3. AD's **marginal** contribution once the rent path is fixed is ~49 → ~35 ms: **~14 ms, or 7% of
   the original baseline** — paid for by opening the finance core, the bit-exact 34-case golden, and
   differentiating a bracketed Brent root-find (`src/core/finance/irr.py:83`) that the charter
   itself names as the hardest part of the mission. **On these numbers the win does not justify the
   blast radius.**
4. **No user feels any of it.** Real deals measure **8.5 ms** (`36_kelly_moncton`) and **7.3 ms**
   (`82_champlain_dieppe`), inside a `python main.py` that runs in **0.68–0.86 s** at **78.6 MB**
   peak RSS. Every projection above leaves those rows untouched. The 5,000u/100y row is a synthetic
   institutional ceiling, and it is currently **inside its 250 ms budget**.
5. Therefore, if AD ships, it must be justified by **Half B** — the multi-lever optimizer genuinely
   needs a Jacobian, and bump-and-reprice supplies one badly (12 pairs × finite differences, with
   step-size error on top). That is an *engineering-quality* argument, and it is a legitimate one.
   It is not the argument the charter currently makes.

### Evidence I need from D.1 before this read goes final

| # | needed | why it moves the number |
|---|---|---|
| a | **Measured `k`** — dual-pass cost multiple on `_forecast_core` at 5,000u/100y | S1 swings 75–89 ms on it; at `k > ~5` AD makes the row *slower* at reduced probe count |
| b | **Can AD get d(metric)/d(rent) WITHOUT materialising a perturbed rent roll?** | **The one finding that could flip me to GO.** If yes, AD subsumes the rent-perturb fix and S1 collapses toward the ~16.5 ms floor. If no, S1 (~82 ms) stands |
| c | IRR/Brent differentiation cost — extra `npv` evaluations per probe under the implicit function theorem | `irr` is 453 calls/3 passes in the profile; a per-probe multiplier here lands directly on `k` |
| d | Is the Jacobian computed **once at baseline** (amortised over 12 pairs) or **once per Newton step**? | Changes the AD pass count from ~12 to ~39 |
| e | From the tolerance-rule owner: **does the ~1e-9 rule tolerate a non-bit-exact SEARCH path?** | Both cheap alternatives (analytic aggregate, numpy sum) trade bit-exactness on the search path only, keeping the shipped confirming re-run exact |

### Budgets for Mission 5 — set and binding

| metric | budget | status |
|---|---|---|
| `python main.py` cold / warm | ≤ 5 s / ≤ 2 s | HOLD — 0.86 s / 0.68 s |
| Peak RSS, sample pipeline | ≤ 500 MB | HOLD — 78.6 MB |
| `import src` | ≤ 1 s | HOLD — 8.4 ms |
| PRIMARY 5,000u/100y | **`BUDGET_MS = 250.0` — UNCHANGED** | Do **not** tighten to 30 during the mission |
| **NEW — real-deal regression guard** | `36_kelly_moncton` ≤ **15 ms**, `82_champlain_dieppe` ≤ **15 ms** | currently 8.5 / 7.3 ms |

**30 ms is a target, not a budget.** With the measured spread (175–198 ms quiet, 333–366 ms
contended, ±12% process-to-process) a 30 ms *gate* would be a flake generator. To
`staff-qa-test-engineer`: any timed assertion on this row must use **best-of-N, never median**, and
keep the 250 ms gate with its existing `median > 1.15 × best` noise warning.

The **new real-deal guard is deliberate**: those two rows are the only numbers a user experiences,
and no projection in §3.4 moves them. That is itself the strongest argument in this memo about the
AD blast radius.

---

## Appendix — reproduction

* Env: `source /home/rtokime/anaconda3/etc/profile.d/conda.sh && conda activate airedeal`
  (verify `which python` → `/home/rtokime/anaconda3/envs/airedeal/bin/python`).
* Committed benchmark: `python -m tests.perf.bench_finance_engine --repeats 9` (~4 min).
* Everything in §3 and §4 came from throwaway harnesses under the session scratchpad
  (`.../scratchpad/d2/{decompose,numpy_probe,residual}.py`) — deliberately **not** committed, per
  the discovery no-production-code constraint. Each is a thin monkey-patch wrapper around
  `src.market.recourse._perturb` / `_rerun` / `run_financial_model`, following the pattern the
  committed harness already uses in `count_probes` (`bench_finance_engine.py:175`).
* All GC figures are from a single process with ON → OFF → ON controls.
