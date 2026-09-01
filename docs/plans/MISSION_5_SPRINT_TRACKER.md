# Mission 5 Sprint Tracker — Forward-Mode Differentiation & Optimized Recourse Search

_Live tracker. The executing orchestrator keeps this current — full updates only (counts + wave
summary + rows), never partial. Date every gate decision. Carry the tests-tree SHA on every count
(Mission 2's hardest-won lesson: a number typed into a doc is a claim with no test behind it — pin it
to a commit)._

**Charter:** `docs/plans/MISSION_5_forward_mode_differentiation.md` · **Handoff:** `docs/plans/MISSION_5_HANDOFF.md`
**Manual tests:** `docs/manual testing/MISSION_5_MANUAL_TESTING.md`
**Baseline:** `main @ 7cfd449` (Mission 4 merged, validated by Roger 2026-08-31, 9/9) · **Branch:** `mission/5-forward-mode-differentiation`

> **Status at charter time (2026-08-31): CHARTERED, NOT YET STARTED.** Mission 4 is merged to `main`
> as `7cfd449`; `main` is clean and in sync with `origin/main`. The sequencing pre-condition is
> satisfied. Wave Sync re-establishes the baseline and re-confirms every charter `path:line` before any
> work.

> ## ✅ MISSION CLOSED — VALIDATED BY ROGER 2026-09-01, 17/17 PASS
>
> Roger ran `docs/manual testing/MISSION_5_MANUAL_TESTING.md` by hand on 2026-09-01 and every one of
> the 17 cases passed; the document-level box reads **VALIDATED** and each case carries his own
> measured numbers. One procedural deviation, checked and cleared by him: `$OUT` was `/tmp/m4` rather
> than a fresh `/tmp/m5`, and he verified no stale file was read. He declared the mission complete the
> same day.
>
> **⚠️ READ THE PER-TASK ROWS BELOW AS STALE.** The status blocks and wave/task tables in this file
> were kept current through Gate D and then stopped being updated while execution continued — they
> still read "0 / 26 DONE" with Impl, Docs, Gate V and Validation as TODO/BLOCKED, which is not what
> happened. What actually shipped is recorded in artifacts that were verified rather than asserted:
> the manual-testing document (17 cases, each with a runnable command and Roger's observed output),
> `CHANGELOG.md`'s Unreleased section (including the three Gate V findings B1, N1 and N3, which is how
> Gate V is known to have run), and the code and tests themselves. Those are the record; the task rows
> below are a mid-flight snapshot left in place rather than retro-fitted with statuses nobody can now
> verify.

> **STATUS 2026-08-31 (execution opened): Wave Sync DONE · Wave Branch DONE · Wave Discovery
> IN-PROGRESS.** Sequencing pre-condition satisfied with one **expected, surfaced delta**: `main` is
> **1 commit ahead of `origin/main`** — local tip is `87efd22` _(commit message quoted verbatim as immutable history; the mission has since been RENAMED -- "Adjoint" was technically wrong, see below)_ _"docs(mission-5): charter Adjoint
> Differentiation & Optimized Recourse Search"_, sitting on `7cfd449`. It is **docs-only** (6 files,
> all under `docs/`, +1742/-28) and is **this mission's own charter commit**, not a later mission. No
> `mission/6-*` branch exists and no unexpected code commit follows `7cfd449`, so the solo-dev
> one-mission-at-a-time cap is not violated and execution proceeded. **The unpushed charter commit is
> surfaced to Roger and must be reconciled at Wave Integrate.** Effective baseline for the mission
> branch: **`87efd22` (= `7cfd449` + charter docs)**.

> Every subagent prompt issued in this mission MUST carry the GRAPHIFY CONTRACT verbatim (see the
> handoff). Any reachability/blast claim citing the graph is confirmed against the file at the graph's
> own `built_at_commit`, never the current tree (Mission 2's trust-boundary incident).

> **HARD SEQUENCING (two boundaries):** (1) the tolerance rule (T-sub-wave) ships and goes green, and
> the guardian VETO on its design is lifted, **before any AD code is written** (AD-sub-wave). (2) The
> **INTERNAL AD go/no-go checkpoint** (ADC.1) must record GO **before any Phase B optimizer code is
> written**; on NO-GO, Half B defers and the mission ships Half A alone. Both are wave boundaries, not
> preferences.

> **Scope (2026-08-31, EXPANDED by Roger):** this mission now runs TWO halves in sequence. **Half A** =
> tolerance rule + forward-mode (tangent-linear) differentiation + single-lever recourse acceleration (the original charter).
> **Half B** = the multi-lever recourse optimizer producing a second "top-3 combinations" report
> section (previously recommended as a separate Mission 6; folded in by Roger). Half B is entered ONLY
> if the internal AD checkpoint = GO.

## Cost routing

Invoke `staff-cost-aware-model-router` at kickoff (standing rule §3a.1) to confirm the tiers below
BEFORE the first dispatch batch — not "only when ambiguous." Record the actual dispatch in each row's
"Agent → tier" column, and log any deviation from the confirmed table **at dispatch time**. Tier→model
mapping: **capable = opus · standard = sonnet · cheap = haiku · top reasoning = fable**. **No
`principal-security-engineer`** this mission — there is no external input surface.

### Planner-proposed routing (router confirms at dispatch)

| Task | Agent | Tier |
| --- | --- | --- |
| EV.1 confirm axis grades / gap severity | `app-evaluator` | opus |
| D.1 AD design + IRR/Brent differentiation reasoning (gnarliest math) | `staff-python-engineer` (top reasoning) | **fable** |
| D.2 current perf baseline (reconcile 73 ms claim) + target/projection | `principal-performance-engineer` | opus |
| D.3 tolerance-rule design (1e-9, anchor-to-origin, approaching-tolerance, ~9.4e-8 calibration) | `staff-python-engineer` | **opus** _(router ↑)_ |
| GD.1 **VETO** on the invariant relaxation (tolerance design as values change) | `principal-principles-guardian` | **fable** _(router ↑)_ |
| PD.1 product calls (ratify 1e-9; `GENUINELY_CLOSE_MAX_FAILS`; horizon-100 / money-field / CLI dispositions) | `principal-founder-proxy` | opus |
| PF.1 perf **go/no-go** on the AD portion | `principal-performance-engineer` | opus |
| IT.1 tolerance harness + anchor-to-origin + approaching-tolerance state | `staff-python-engineer` | sonnet |
| IT.2 tolerance RED suite (incl. ~9.4e-8 calibration) | `staff-qa-test-engineer` | sonnet |
| IA.1a AD core — dual-number plumbing through `engine.py` + differentiating the Brent root-find in `irr.py` | `staff-python-engineer` | **fable** _(router split)_ |
| IA.1b 7×4 Jacobian API surface + Newton-on-guardrail single-lever + confirm-by-rerun + bisection fallback | `staff-python-engineer` | sonnet |
| IA.2 AD-vs-rerun agreement + probe-count + determinism + fallback RED suite | `staff-qa-test-engineer` | sonnet |
| IA.3 perf benchmark extension (probe-count + before→after vs 30 ms) | `principal-performance-engineer` | sonnet _(router: mechanical re-measurement)_ |
| D.4 Half B design (optimizer method selection + rejector-unification + top-3 selection) | `staff-python-engineer` (top reasoning) | **fable** |
| PD.2 Half B product calls (combination-plausibility rule; top-3 selection policy) | `principal-founder-proxy` | opus |
| IB.1 constrained optimizer (Lagrangian/KKT) + deterministic multi-start + unified all-four-lever plausibility gate + confirm-by-rerun | `staff-python-engineer` | **fable** |
| IB.2 two-section report output (single-lever menu + top-3 combinations; flag-don't-remove; honest-null) | `staff-report-experience-designer` | **opus** _(router ↑)_ |
| IB.3 optimizer RED suite (multi-start determinism; feasibility gate incl. jointly-implausible; diversity; parsimony; local-minima; every-combination-confirmed-by-rerun) | `staff-qa-test-engineer` | sonnet |
| I.4 docs Half A (README / finance & market READMEs / CHANGELOG) — reasoning, verify vs real symbols | `staff-documentation-maintainer` | **sonnet (STANDARD, not haiku)** |
| I.5 docs Half B (two-section output + unified gate in market/reports READMEs + CHANGELOG) — verify vs real symbols | `staff-documentation-maintainer` | **sonnet (STANDARD, not haiku)** |
| OI.1 money-field lower-bound pass + RED test | `staff-python-engineer` | sonnet |
| OI.2 horizon 50→100 raise + RED test | `staff-python-engineer` | sonnet |
| OI.3 CLI out-of-range-horizon clean message + RED test | `staff-python-engineer` | sonnet |
| GV.1 code review of full diff | `staff-code-reviewer` | **opus** _(router ↑)_ |
| GV.2 guardian invariant-relaxation re-check (VETO) | `principal-principles-guardian` | **fable** _(router ↑)_ |

Deviations from this table are logged at dispatch time in the row itself.

### Router confirmation — CONFIRMED 2026-08-31 by `staff-cost-aware-model-router` (opus)

Router read the charter and adjudicated every row. **Six changes** from the planner proposal, all
upward; the confirmed table below is authoritative and supersedes the planner-proposed table above and
the charter's §Agent roster (charter lines 378-396 disagree and should be reconciled at doc time).

| Row | Change | Router rationale (condensed) |
| --- | --- | --- |
| D.3 | sonnet → **opus** | The tolerance design is the artifact a VETO reviews; "anchoring must be structural, not a convention" is a test-contract decision whose failure mode is a silent ratchet across future missions. Implementation (IT.1) stays sonnet. |
| GD.1 | opus → **fable** | Routing rule 3, unconditional: VETO-holding gate reviews go fable when the diff touches `src/core/finance/` **or** `src/schemas/models.py`. This mission touches both. |
| GV.2 | opus → **fable** | Same rule; as-built re-check over the same blast radius. |
| IA.1 | **split** into IA.1a (**fable**) + IA.1b (**sonnet**) | "sonnet (+ fable)" is not a tier. IA.1a (dual-number plumbing through `engine.py` + differentiating the Brent root-find in `irr.py`) is the hardest item on the board and must not be *relayed*. IA.1b (Jacobian API surface + Newton + confirm-by-rerun + fallback in `recourse.py`) is spec-driven execution once D.1 lands the signature. The split also preserves the clean seam ADC.1 tests. |
| IB.2 | sonnet → **opus** | Routing rule 4, no exceptions: report-facing copy. The deliverable *is* the descriptive-vs-advice nuance; honest-null framing carries the product claim. Clearest under-served row. |
| GV.1 | sonnet → **opus** | The reviewer's checklist is invariant enforcement over a finance-core diff, not routine review. (Router: escalates to fable if this review is granted VETO authority — it is not.) |

Confirmed unchanged: EV.1 opus · D.1 fable · D.2 opus · PD.1 opus · PD.2 opus · PF.1 opus · IT.1
sonnet · IT.2 sonnet · IA.2 sonnet · IA.3 sonnet _(mechanical re-measurement, one tier below D.2's
origination — explicitly not haiku)_ · D.4 **fable** _(confirmed, not waved through: the
normalization-free top-3 math earns it)_ · IB.1 fable · IB.3 sonnet · I.4/I.5 **sonnet (STANDARD, not
haiku)** · OI.1-3 sonnet.

**Tier-deviation triggers to watch at dispatch (router):**
- **T1** — if PD.1 ratifies 1e-9 **and** the approaching-tolerance semantics *before* D.3 dispatches,
  D.3 collapses to spec-following and drops to **sonnet**.
- **T2** — do not run IB.1 as one fable lane: carve the multi-start seed grid + report wiring to
  **sonnet**, keep fable on the KKT method + the joint gate.
- **T3** — if D.4 does not hand over a *concrete* jointly-implausible-but-individually-fine fixture,
  that one IB.3 test case is design work → route it **opus**; the rest stays sonnet.
- **T4** — on ADC.1 = NO-GO, D.4/PD.2/IB.1/IB.2/IB.3/I.5 never dispatch. **Do not pre-spend fable on
  D.4 before ADC.1 exists** — the single largest avoidable spend line in this mission.
- **T5** — under budget pressure: run IA.1a→IA.1b sequentially (already required), consolidate I.4+I.5
  into one agent. Never shrink GD.1 / IB.2 / GV.2 — those are routing-rule floors.
- **T6** — verify `pytest`, `mypy .`, **both** `ruff format --check` and `ruff check` locally before
  each push (Mission 4 lesson).
- **T7** — log any rework produced by a sonnet lane against IT.1 / IA.1b / IT.2-IA.2-IB.3 so the table
  learns.

## Status legend

`TODO` · `IN-PROGRESS` · `BLOCKED` (needs a prior gate or a product call) · `REVIEW` (agent says done,
orchestrator verifying) · `DONE` (verified inline) · `DEFERRED`

## Overall progress

- Mission status: **SHIPPED — validated by Roger 2026-09-01, 17/17 PASS.** Scope EXPANDED by Roger
  2026-08-31 to Half A + Half B. Baseline `main @ 87efd22` (= `7cfd449` + this mission's docs-only
  charter commit), **1 ahead of `origin/main` at charter time — still unpushed, reconciled at
  Integrate.** Both halves shipped, with two charter premises measured and retracted rather than
  quietly kept: Newton-on-an-AD-derivative was **rejected on measurement** (a dual pass costs ~4× a
  plain pass; 11–41 probes against bisection's fixed ~11), and the 30 ms perf target was **not met**
  (71.4 ms on Roger's box, from 459.5 ms, via an aggregate-income seam and scoped GC tuning — neither
  of which is AD). AD ships doing direction selection, one dual pass per analysis. Half B shipped as
  **11 minimal-ask propositions, one per lever subset, unranked, with the smallest total ask
  labelled** — no top-3 cut. A margin-of-safety report section shipped as new scope beyond the charter.
- _Task-row bookkeeping below stopped at Gate D; see the banner at the top of this file._
- Tasks: **0 / 26 DONE** · 0 IN-PROGRESS · 26 TODO. _(19 Half A — IA.1 split into IA.1a/IA.1b by the
  router — + the internal AD checkpoint ADC.1 + 6 Half B tasks D.4, PD.2, IB.1, IB.2, IB.3, I.5 — the
  Impl Phase B tasks are BLOCKED until ADC.1 = GO.)_
- **Suite baseline — PINNED at Wave Sync, 2026-08-31**, measured in the `airedeal` conda env
  (`/home/rtokime/anaconda3/envs/airedeal/bin/python`, Python 3.10.18) at `87efd22`:

  | Item | Pinned value |
  | --- | --- |
  | `pytest` | **3197 passed, 1 skipped**, 0 failed (29.0 s) |
  | Coverage | **88.37%** (4712 stmts / 415 miss / 1538 branch / 226 partial) — gate ≥80% PASS |
  | **Tests-tree SHA** | **`7221722456c39f9e0449eacf2bc5a65edb03768d`** (`git rev-parse HEAD:tests` @ `87efd22`) |
  | `ruff format --check` | clean — **238 files already formatted** |
  | `ruff check` | clean — **All checks passed!** |
  | `mypy .` | clean — **no issues found in 236 source files** |
  | `python main.py` | ran clean; `Thesis verdict: DECLINE`; wrote `investment_analysis.md` |
  | **Pre-mission report sha256** | **`e6451c9af19e491a14495e9055501fff44034040552317325e539ab42b9f9ee9`** (`investment_analysis.md`) |
  | Working tree after battery | `git status --porcelain` **empty** |

  _Perf is NOT pinned here — reconciling the brief's unverified "73 ms" against the committed
  5,000u/100y row (`BUDGET_MS = 250.0` `tests/perf/bench_finance_engine.py:97`; charter-time reference
  best 181–197 ms / median ~213 ms) is **D.2**'s job, by fresh measurement._

### Anchor re-verification (Wave Sync, 2026-08-31, at `87efd22`)

Every charter `path:line` re-confirmed against the real file. **1 drift found, 15 exact:**

| Symbol | Charter | Actual | |
| --- | --- | --- | --- |
| `compute_recourse` (`src/market/recourse.py`) | :792 | :792 | ✅ |
| `_bisect` · `_rerun` · `_perturb` · `_search_one` · `is_genuinely_close` | :471 · :412 · — · — · — | :471 · :412 · :372 · :663 · :213 | ✅ |
| `_judge_plausibility` · `_rejector_flagged` · `_magnitude_flagged` | :609 · :519 · :584 | :609 · :519 · :584 | ✅ |
| `RATE_MAGNITUDE_THRESHOLD` · `_MAGNITUDE_RELATIVE_THRESHOLD` · `GENUINELY_CLOSE_MAX_FAILS` | :130 · :120 · (=3) | :130 · :120 · :143 (`= 3`) | ✅ |
| `run_financial_model` · `forecast_metrics` · `precompute_income` · `_forecast_core` (`engine.py`) | :638 · :671 · :186 · :309 | :638 · :671 · :186 · :309 | ✅ |
| `irr` · `_brent_root` (`irr.py`) | :188 · :83 | :188 · :83 | ✅ |
| bench PRIMARY 5,000u/100y row · `BUDGET_MS = 250.0` | :79 · :97 | :79 (`("5,000u / 100y", 5_000, 100)`) · :97 (`PRIOR_BUDGET_MS = 120.0` :98) | ✅ |
| **golden bit-exact test** (`tests/core/finance/test_golden_forecasts.py`) | **:188** | **`test_forecast_matches_golden_bit_exact` :181** _(also `test_sample_deal_matches_golden_bit_exact` :217)_ | ⚠️ **DRIFT — 7 lines** |

The one drift is cosmetic (the charter's line points inside the same test's decorator/body region, not
at a different symbol), but it is recorded because two prior missions were bitten by charter path
drift. **D.3 and IT.1 must re-read the golden harness before touching it** and cite `:181`, not `:188`.

## Wave summary

| Wave | Status | Tasks | Notes |
| --- | --- | --- | --- |
| Sync | **DONE** (2026-08-31) | — | Pre-condition satisfied: `7cfd449` present, tip is this mission's own docs-only charter commit `87efd22` — **not** a later mission; no `mission/6-*` branch. `git fetch` clean; tree clean; **1 ahead of origin — surfaced to Roger, reconcile at Integrate.** 16 anchors re-verified (1 cosmetic drift: golden bit-exact test is `:181`, charter says `:188`). Baseline battery green + pinned above. |
| Branch | **DONE** (2026-08-31) | — | `mission/5-forward-mode-differentiation` cut from `main @ 87efd22`. Router invoked at kickoff **before the first dispatch batch** (standing rule §3a.1); confirmed table recorded above with 6 upward changes + 7 deviation triggers. |
| Discovery | ✅ **DONE — 5/5** (2026-08-31) | EV.1, D.1, D.2, D.3, D.4 | AD forward-vs-reverse MEASURED; IRR/Brent differentiation; tolerance design; perf baseline (reconcile 73 ms); **Half B design** (optimizer method + rejector-unification + top-3). No production code. |
| Gate D | TODO | GD.1, PD.1, PF.1, PD.2 | **Guardian VETO on the invariant relaxation** (mandatory) + founder product calls (incl. **Half B: combination-plausibility rule + top-3 policy**) + perf **go/no-go** on the AD portion. |
| Impl Phase A — Tolerance (FIRST) | BLOCKED (on Gate D VETO lift) | IT.1, IT.2, I.4, OI.* | Tolerance rule shipped + green before any AD code. |
| Impl Phase A — AD (single-lever) | BLOCKED (on Impl-T green + VETO lifted + PF.1 go) | IA.1, IA.2, IA.3 | Only if Gate D says GO. If NO-GO, mission ships the tolerance rule alone. |
| **Internal AD go/no-go checkpoint** | BLOCKED (on Impl Phase A AD green) | ADC.1 | **Hard gate.** AD proven (single-lever matches bisection within tolerance; IRR/Brent sound; 7×4 Jacobian API stable) BEFORE any optimizer code. GO → Phase B; NO-GO → Half B defers, Half A ships alone. |
| Impl Phase B — multi-lever optimizer | BLOCKED (on ADC.1 = GO) | IB.1, IB.2, IB.3, I.5 | Lagrangian/KKT + multi-start + unified all-four-lever gate + two-section report + optimizer RED suite + Half B docs. Every combination confirmed by a real re-run. |
| Validation | TODO | — | Full battery; BOTH ruff commands; within-tolerance golden; perf recorded vs 30 ms; every manual-test command runs (incl. Half B cases). |
| Gate V | TODO | GV.1, GV.2 | Code review (every answer AND combination rerun-confirmed; unified gate all-four-lever; multi-start deterministic; no decomposed basis surfaced) + guardian re-check (VETO). |
| Mission gate | TODO | — | Roger validates the manual-testing doc by hand; document-level box → VALIDATED. |
| Integrate | TODO | — | Rebase, re-run full battery, `merge --no-ff`, push at Roger's instruction. Record merge sha. |

## Wave: Discovery

| ID | Task | Agent → tier | Status | Notes |
| --- | --- | --- | --- | --- |
| EV.1 | Confirm axis grades / gap severity justify the mission | `app-evaluator` → opus | **DONE** (2026-08-31) — memo `docs/plans/mission-5-discovery/EV1_grades.md` | Scope **sharpened** at dispatch in light of D.2: not "validate the charter" but "is the mission Roger chartered still the best next block of work, now that the number it was premised on is retracted?" Asked explicitly to rank Half B's value as a **product/capability** gap rather than a perf one, and permitted to name a higher-leverage mission. |
| D.1 | AD design (forward-vs-reverse MEASURED, 4-in/≤7-out) + IRR/Brent differentiation (IFT vs converged root) | `staff-python-engineer` → fable | **DONE** (2026-08-31, verified inline) — memo `docs/plans/mission-5-discovery/D1_ad_design.md` | Gnarliest math; dual-number 4-pass is the hypothesis to beat, not a foregone conclusion. |
| D.2 | Current perf baseline (reconcile the 73 ms claim vs committed 181–213 ms) + target/projection | `principal-performance-engineer` → opus | **DONE** (2026-08-31, verified inline) — memo `docs/plans/mission-5-discovery/D2_perf_baseline.md` | Also asked for the **Amdahl arithmetic**: with the measured probe count dropping to ~3–4, is 30 ms reachable at all, or is there an irreducible floor above it? Most decision-relevant number in Discovery. Carries numpy re-measurement + preliminary PF.1 read. |
| D.3 | Tolerance-rule design (1e-9, anchor-to-origin, approaching-tolerance state, ~9.4e-8 calibration) | `staff-python-engineer` → **opus** _(router ↑ from sonnet)_ | **DONE** (2026-08-31, verified inline) — memo `docs/plans/mission-5-discovery/D3_tolerance_rule.md` | Artifact the guardian VETO reviews. Router trigger **T1 did NOT fire** — PD.1 is a Gate D task and has not run, so the design was not reducible to spec-following; opus stands. Prompt carries the confirmed golden-harness drift (`:181`, not `:188`). |
| D.4 | ✅ **DONE** — **Half B design**: (g) constrained-optimization method selection (Lagrangian/KKT variant, by measurement) + deterministic multi-start; (h) **rejector-unification** — one joint all-four-lever plausibility gate (core new engineering); (i) normalization-free top-3 selection (parsimony · within-axis magnitude · diversity) | `staff-python-engineer` → fable | TODO | Grounded: `_judge_plausibility` (`recourse.py:609`) judges one lever at a time today; rent/opex have no rejector axis. No production code. **DONE 2026-08-31, verified inline** — memo `docs/plans/mission-5-discovery/D4_halfb_design.md`. Chose a method **outside** the charter's named family on measurement (16×–50× fewer probes); jointly-implausible fixture verified against `rejector.py:23`. |

### D.1 RESULT — verified inline 2026-08-31. **It answers D.2's flip question YES — and still lands NO-GO on AD-as-perf.**

**Forward mode wins, measured** (demo deal, H=10; engine pass = 42 µs):
| Approach | µs | × engine |
| --- | ---: | ---: |
| **forward `Dual4` unrolled — full Jacobian, one pass** | **173** | **k = 4.1×** |
| forward tuple-tangent dual-4 | 272 | 6.5× |
| forward dual-1 (single column) | 229 | 5.5× — **tangent width is ~free; never do per-lever passes** |
| reverse Wengert tape (record + 7 sweeps) | 296 | 6.9× (+443 tape entries/pass, ~4k at H=100) |
| numpy-array-tangent dual | 346 | 8.4× |

Forward vs reverse Jacobians agree to **≤4.1e-16**; AD vs central finite-difference of the *real* engine
**≤1.6e-8** on all 24 non-IRR entries, the IRR row's ~1e-6 fully attributed to Brent-tol noise (a tight
root collapses it to ~3e-7). **D.2's numpy veto independently confirmed** on a different workload —
direction identical, magnitude differs by benchmark shape. Overturn condition stated: per-unit-rent
differentiation (thousands of inputs) is reverse territory and must be re-measured, not extrapolated.

#### ⭐ The load-bearing new finding — D.2's flip question answered **YES**, and orchestrator-verified

**AD obtains d(metric)/d(rent) with ZERO rent-roll materialisation.** Income enters `_forecast_core`
only via the `(gsi_y1, goi_y1)` aggregate (`engine.py:367-370`), and the rent lever is exactly linear in
it: seed `d(gsi_annual)/d(t_rent) = 12·num_units` on the existing `precompute_income` output. Measured
**bit-identical Jacobian (0.0 relative difference) with zero `UnitIncome` objects, O(1) in roll size.**
AD-Newton performs **no rent `_perturb` calls at all**; only the per-row confirming re-run materialises a
roll (**≤4 rows at the gate limit vs 39 probes today**) — killing the **74.5% term D.2 said nothing else
touches.**

**Orchestrator verification:** confirmed structurally, not on report. `sed -n '309,640p'
src/core/finance/engine.py | grep -n "UnitIncome\|unit_income\|\.units\|per_unit"` returns **nothing** —
`_forecast_core` never touches units anywhere in its ~330 lines. The aggregate seam at `:367-370` is real
and the `precomputed_income` path already exists.

#### ⚠️ …but D.1 volunteers the honesty note that decides the mission

> **The same seam in plain float mode de-`_perturb`s bisection too — the seam is the perf intervention;
> AD rides on it, not vice versa.**

So the 74.5% win is attributable to the **aggregate-shift seam**, which needs **no AD, no dual numbers,
and no finance-core genericity.** AD does not cause that win; it inherits it.

**IRR/Brent — recommendation: implicit function theorem over the production root; NEVER differentiate the
iterations.** Primal floats go through `irr()`/`_brent_root` unmodified, then
`dr*/dθ = −(Σ ĊF_t(1+r̂)^−t) / (Σ −t·CF_t(1+r̂)^−t−1)` — **~4.7 µs extra per probe.** Iterate-differentiation
is *structurally* wrong here, not merely worse: bracket endpoints are θ-constants with zero tangents, so
**bisection-terminated runs return zero-built garbage tangents, non-deterministically by deal.** Assumptions
+ checks: derivative inherits O(tol)=1e-6 error (measured 3.2e-7 — fine for a re-run-confirmed search;
**test bands, not exact comparisons**); `|∂f/∂r|` floor-checked → partials `None` on conditioning failure;
`irr() is None` → partials **`None`, never 0.0** (the coalesced-0.0 metric is a jump discontinuity).

**Jacobian API — and a ruling on the charter's "7×4":** it is **neither 7×4 nor 4×4** but **8 metric rows
(`ForecastMetrics`' float fields, drift-guarded `Literal`) × N caller-named columns**, consumed dynamically
by the live guardrail set. Rows always exist; "live/failing" stays a market-layer fact. New module
`src/core/finance/jacobian.py`: `forecast_metrics_with_jacobian(fi, directions, *, horizon_years,
precomputed_income) -> MetricsJacobian`, with named accessors `.partial(metric, direction)` / `.value(metric)`
— **no positional guessing.** `None` ≠ 0.0; primal pinned bit-identical to `forecast_metrics`;
confirm-by-rerun and `_search_one`'s fallback contract untouched. Per-unit seeds deliberately not offered.

**D.1 go/no-go: GO on AD as the Half-B Jacobian enabler; NO-GO on AD as a performance intervention** —
independently concurring with D.2. **Recommended ship order: GC tuning → aggregate-shift seam → AD riding
on both.** Its own strongest counter-argument, quoted: _"all of AD's unique value is prospective (Half B);
engine-bound Newton is a wall-time wash at k=4.1, and the blast radius is bought for an optimizer that
doesn't exist yet. **If Gate D doubts Half B ships, the consistent call is hold AD.**"_

**Charter-vs-code flags from D.1:** all anchors match at `87efd22`; "7×4" is really 8×N-dynamic (4 live at
the gate limit); "~10–20 probes/pair" measures at the low end (~11+1); and **the mission premise locates
the win in the engine forecast when the measured dominant term is the rent-roll copy.**

### GD.1 VETO VERDICT — **LIFTED WITH CONDITIONS C1–C7** (2026-08-31)

**The guardian verified rather than accepted** — it re-derived D.3's walls from scratch by monkeypatching
`amortization_payment` across all 34 cases, and independently re-confirmed both provenance findings.
**The orchestrator then re-ran the guardian's own script** (`scratchpad/gd1/verify_walls.py`) as a third
independent reproduction. All three agree:

| Injection | max relative | fields > 1e-9 |
| --- | ---: | ---: |
| baseline (no patch) | **0.0** (bit-identical) | 0 |
| 1 ULP — FP-reordering noise floor | **1.1510e-13** | 0 |
| `round(payment, 6)` — approaching-tolerance case | **9.7904e-10** _(98% of budget)_ | 0 |
| `round(payment, 4)` — **the defect class** | **1.1325e-07** | **1,613** |
| `× (1 + 9.4e-8)` — the charter's contract figure | **1.3477e-05** | **2,958** |

**The calibration logic is confirmed empirically: the defect at 1.13e-7 is caught at 1e-9 and INVISIBLE
at 1e-6.** _(Minor unreconciled discrepancy, not material: the guardian's script counts 11,360 numeric
fields, D.3 reported 11,789 — a counting-scope difference, no bearing on any wall.)_

**Rulings:** (1) does **not** weaken the deterministic-core invariant — "same inputs ⇒ same output" is a
fixed-program property still enforced at `==` by `:191` and `test_metrics_parity.py`; what relaxes is
cross-version bit-stability, a *surplus* guarantee, and the harness docstring (`:17-20`) **pre-authorizes
exactly this** ("a named, justified tolerance"). (2) The anchor is structural **only with D.3 §3.5 adopted
as mandatory** — the digest pin flattens the price gradient, but `--supersede-anchor --rationale
"<boilerplate>"` decays under deadline pressure; the **cumulative 1e-8 budget is the only non-decaying
element** because its failure cannot be cleared by another rationale, only by independent human
re-verification. (3) 9.4e-8 stays as a contract constant bound to the `round(payment,4)` recipe — but the
five documents' "injected rounding bug that appears at ~9.4e-8" **fiction is a values breach if left
standing (fabrication-class precedent)**, hence C4. (4) Fail-closed is correct; the ledger is a genuine
control except for over-provisioned `max_rel`, closed by C5. (5) Scope boundary confirmed; **any request
to relax `test_metrics_parity.py` or `test_engine_bitexact_refactors.py` is a formal stop-and-consult
event.** (6) Dollar blindness acceptable — $0.00053 on the shipped deal is one order below half a display
cent — with the unacceptability boundary made **executable** in C6.

| # | Condition (each becomes a checkable tracker row) |
| --- | --- |
| **C1** | Determinism boundary frozen: **no assertion changes** in `:191`, `:225`, `test_metrics_parity.py`, `test_engine_bitexact_refactors.py`; the `:191` docstring exclusion statement is required. |
| **C2** | D.3 §3.5 cumulative-drift budget (**1e-8**) adopted as **mandatory, not SHOULD**; failure message must state the remedy is independent human re-verification, **never a budget raise**. |
| **C3** | Supersession requires `--rationale` + dated harness-docstring record + `approved_by` naming the founder; structural regeneration **refuses to co-carry numeric drift** (IT.2 pins this). |
| **C4** | Calibration honesty: **(a)** manual-test Case 1 steps 1 **AND** 2 corrected **before IT.2**; **(b)** four charter docs corrected **before Gate V**; **(c)** contract status + recipe recorded in the calibration test's docstring. |
| **C5** | Ledger rejects over-provisioned (>10% above measured) and out-of-range (`>= REL_TOL`) entries; stale entries fail. |
| **C6** | Walls re-derived in-repo (Test D) + assert `REL_TOL × max shipped-deal field < $0.005`; §6.3 prohibitions stated in `golden_tolerance.py`'s docstring. |
| **C7** | Harness docstring rewritten with a dated "TOLERANCE RULE — Mission 5" record block; the two relaxed tests renamed. |

**✅ C4(a) DISCHARGED by the orchestrator, 2026-08-31** — `docs/manual testing/MISSION_5_MANUAL_TESTING.md`
Case 1 rewritten. The guardian caught that **step 2 had the same anchor-mutation defect as step 1**; both
are corrected. All four steps now perturb the **computed side** (monkeypatching
`amortization.amortization_payment`) and never edit the golden; each carries its measured signature; a new
step 4 proves the anchor fires with a distinct message when the golden itself is edited; and the
contract-vs-measurement status of 9.4e-8 is recorded in the document Roger validates by hand. **C4(b)
(four charter docs) remains open and is due before Gate V. C1, C2, C3, C5, C6, C7 are IT.1/IT.2
implementation conditions the orchestrator verifies before marking those rows DONE.**

### 🏁 MISSION GATE PACKAGE — ready for Roger (2026-08-31)

**Gate V: code review REQUEST-CHANGES ×2 → all defects fixed and re-verified. Guardian: CLEARED-WITH-CONDITIONS, all discharged.**

| Battery | Result |
| --- | --- |
| `pytest` | **3560 passed, 1 skipped** · coverage **89.60%** (baseline 3197) |
| `pytest --no-cov` | **3560 passed, 1 skipped** |
| `ruff format --check .` | 263 files already formatted |
| `ruff check .` | All checks passed |
| `mypy .` | no issues in 261 source files |
| `python main.py` | clean · verdict DECLINE |
| Manual-testing doc | **fully runnable**, 528 → 1534 lines · **0 of 67 boxes ticked (Roger's to flip)** |

**Four blocking defects found by review, all fixed and orchestrator-re-verified against the reviewer's own repro scripts:**
| # | Defect | Verified fixed |
| --- | --- | --- |
| B1 | AD seam crashed (`TypeError: not Dual4`) at `0 < rate < 1e-6` — the mission's own amortization fix vs its own AD seam, each tested alone, never together | `JACOBIAN OK`; 340 golden×rate passes, 0 crashes, stable primal bit-identical over 20,000 triples |
| B2 | R2 could trip with **zero reasons** → `ValidationError` killing the whole run on any deal with occupancy < 80% | 0 crashes over 204 runs; rejection now names the baseline-vacancy axis |
| B3 | `pytest --no-cov` hard-errored on all three perf gates — an infra crash dressed as a perf failure | both invocations green |
| N-B1 | **Breakeven shipped the engine's "IRR undefined" `0.0` sentinel as a measured IRR**, with a "percentage points of room" figure built on a discontinuity — 15 of 132 rows on the project's own golden cases | **0 sentinels ship; 15 rows honestly degraded; `"measured 0.00%"` appears nowhere** |

**Two pre-existing bugs found while fixing the above:** `_rejector_flagged` had been reporting baseline-vacancy and divergence rejections as *"cap outside [3%, 12%]"* — **a false statement in shipped Mission 4 output**; and `compute_breakevens` **crashed the pipeline on every refinancing deal**, invisible until it was wired to a consumer.

**⚠️ THREE ITEMS FOR ROGER'S JUDGMENT — surfaced, not decided:**
1. **Bit-exactness.** The golden file is **unchanged** and `DRIFT_LEDGER.json` reads `"entries": []`. Across the whole mission — **including the AD landing that was the stated justification** — **zero in-tolerance drift ever occurred.** The repo's strongest check was traded for `REL_TOL = 1e-9` for a need that did not materialise. The reviewer declined to block on it twice and asked that it reach the gate as **a conscious ratification, not an inheritance**. Fair question now: **restore bit-exactness?**
2. **A new declared dependency.** `typing_extensions>=4.7.0`, added so `assert_never` can make B2's exhaustiveness claim true (stdlib `typing.assert_never` is 3.11+; project floors at 3.10). Zero install weight — pydantic already hard-requires it. But this mission **removed** `annotated_types` on adjacent reasoning, so it deserves an explicit yes/no.
3. **A copy discrepancy.** The report renders *"has the smallest total ask"*; the charter says *"cheapest total negotiation."* Behaviour is exactly as specified (one labelled `argmin`, no ranking). One-line change if wanted.

**Honestly NOT met:** Roger's **30 ms** target. Measured **404.7 → 65.4 ms** (6.2×) — and deliberately **not gated at 30 ms**, because the measured ±12% process spread would make it a flake generator. `BUDGET_MS = 250` now has a real gate that actually gates, which it did not before.

### ✅ BREAKEVEN / MARGIN-OF-SAFETY — LANDED (2026-08-31) — _verification pending a settled tree_

The founder's second reading, GD3-cleared. `src/market/breakeven.py` + `AssumptionBreakeven` /
`BreakevenAnalysis` + 23 tests. Axes exactly `income.occupancy`, `income.rent_growth`,
`opex.expense_growth`; import-time guards pin that each is a `MODEL_ASSUMPTIONS` path, **none barred**,
**none in `LEVER_IMAGE`**, and `partition.assert_breakeven_shape` runs at import against both types.

**⭐ GD3'S SHAPE RULE FIRED ON ITS FIRST REAL TEST — the mechanism works.** A mutant `vacancy_ask` field
killed the module at import:
> `RuntimeError: GD3 VIOLATION: AssumptionBreakeven carries field(s) ['vacancy_ask'] that could express a
> recourse 'ask' on a MODEL_ASSUMPTIONS axis ... FOUNDER PROXY ESCALATION CITING GD3; a rationale string
> is not a clearance.`

With the import guard *also* disabled, a belt-and-braces test still caught the field. Two layers, both
verified by real captured failure output. **This is exactly what the founder asked for when he said the
separation should carry VETO weight rather than be an orchestrator's note in a comment.**

**Two design catches worth recording — neither was in the brief:**
1. **Failing guardrails get NO row, deliberately.** A failing guardrail has no *margin of safety*, and
   solving one in the **favorable** direction would be **the forbidden recourse reading in disguise**
   ("improve your vacancy assumption until this passes"). They ship as fact in `failing_guardrails`.
   The agent found the GD3 hazard the brief did not name.
2. **Occupancy's adverse edge is `1e-6`, NOT `0.0`** — because `engine._annual_income` reads
   `income.occupancy or 1.0`, so an occupancy of exactly `0.0` **silently means FULL occupancy.** A real
   footgun, avoided.

**Seed-vs-perturb — decided correctly, no escalation needed.** Widening `SeedTarget` to
`income.occupancy` would require Founder Proxy sign-off citing GD3 and would trip `jacobian.py`'s
import-time drift guard. The agent did not ask, because **AD buys nothing here:** the adverse *direction*
along each axis is a fixed engine data-flow fact (GOI = GSI·occ·bdf; income ∝ (1+rg)^(y−1); opex ∝
(1+eg)^(y−1)), bisection is derivative-free, and Newton was already measured worse. It documented what an
extension *would* require — *"a deliberately multi-file, self-incriminating diff."*

**Three-outcome contract matched to `compute_combinations`:** `breakeven_found` / `never_breaks_in_range`
(proven, **scoped to `searched_to`**, edge-run-confirmed) / `undetermined` (budget exhausted — **never
rendered as safety**; an unconfirmable crossing degrades to `undetermined`, never to a number). Every
shipped value comes from **one full un-differentiated `run_financial_model` re-run observed FAILING**.

**Measured:** champlain **4.24 ms** median (9 rows, 70 probes); kelly **3.04 ms** (6 rows, 55 probes).

**Worked example in the founder's own phrasing** (kelly at a 28% price cut, all guardrails passing):
> **"This deal clears DSCR until vacancy hits 7.7% (occupancy 0.9231); you assumed 5% (occupancy 0.95)"**
> — margin 0.0269; DSCR at the confirmed breakeven is 1.1999 against a 1.20 bar.

**Rendering rules handed to IB.2** (must be honoured): margin-of-safety copy only, never an imperative ·
`undetermined` renders as "not determined within budget", **never as safe** · `never_breaks_in_range` is
a strong result but must be **scoped by `searched_to`** · display vacancy = 1 − occupancy · **round the
displayed margin TOWARD ZERO — never overstate the room** · `metric_moves=False` renders as "does not
depend on this assumption at all."

**Boundary items reported, not fixed:** one `ruff` E501 at `src/market/recourse.py:581` in the perf
agent's live edit, and `tests/perf/test_perf_gates.py::TestRecourseLoopBudgets` wall-clock failures on a
loaded machine with two agents mid-write. **Both belong to in-flight work; the orchestrator re-runs the
full battery on a settled tree before Gate V.**

### ✅ IB.1 — MULTI-LEVER SEARCH LANDED — verified inline (2026-08-31)

**The mission's centrepiece. Orchestrator verified independently rather than on report** — script at
`scratchpad/verify_ib1.py`, run against the real engine and committed fixtures.

**🔴 The three-outcome honesty contract HOLDS — the single most important check in this mission:**
| Run | `outcome` | `honest_null` | `subsets_exhausted` | found |
| --- | --- | --- | ---: | ---: |
| champlain, `max_iter=3` (**starved**) | **`undetermined`** | **False** | 11 | 0 |
| kelly (**genuinely** null) | **`proven_null`** | True | **0** | 0 |
| champlain, full | `found` | False | 0 | **11** |

A starved search says *"we stopped looking"* and **refuses to claim an honest null**; `proven_null`
requires zero findings **AND** zero exhausted subsets. An investor is never told "nothing can save this
deal" when the truth is "we ran out of budget."

| Check | Result |
| --- | --- |
| **Determinism** | **byte-identical** `model_dump_json()` across fresh runs — champlain (10,279 B), kelly (326 B), **and the starved payload** (328 B) |
| **`cheapest_total_index`** | recomputed independently → **matches** (index 0, Σf 1.2421 of 11 values 1.242–1.687). A pure `argmin` over an already-computed set — **no ranking** |
| **GD3** | every ask ∈ `INVESTOR_LEVERS`; **zero** `MODEL_ASSUMPTIONS` present as an ask |
| **Confirm-by-rerun** | all **11/11** combinations carry confirming-run margins |
| **Budget constant** | `_COMBINATION_ASK_BUDGET = float(_MIN_COMBINATION_LEVERS)` — **derived from the arity floor, never a bare 2.0** (PD.2's condition) |
| **GD3 drift guard** | present at `recourse.py:112`, `get_args(LeverName) != INVESTOR_LEVERS` → `RuntimeError` naming the escalation |

**The cheapest combination is legible, which was the whole product point:** champlain →
**rent +$90/mo and price −$54,900** (Σf 1.242).

**As built:** one minimal-ask solve per subset from `partition.investor_lever_combinations(min_size=2)`
(the sanctioned GD3 builder) → corner proof → **AD direction** (ONE shared
`forecast_metrics_with_jacobian` pass, ≤ `MAX_DIRECTIONS`; `None` partials degrade honestly to the
balanced ray) → **R3 as an a priori clip** so no probe is spent past budget → **bisection** to 1e-3
(≤10 probes, **no Newton**) → round → **confirm-by-rerun** → gate on the *confirmed* metrics.
**Subset distinctness confirmed:** the subset bounds which levers may move; the gradient only sets
proportions inside it, so the ≤11 answers cannot collapse to one min-sum optimum (degenerate wider
subsets are deduped, counted `subsets_collapsed`).

**R2 unification shipped as designed** — ONE `MarketHypothesis` carrying both the signed rate delta and
the engine-computed implied-cap delta through the **unmodified** `reject_unrealistic`, **zero new
constants.** Worked fixture verified through the real gate: rate −90 bps + price −$90,000, individually
plausible on all four rows, jointly `|−0.0090 − (+0.0121)| = 0.0211 > 0.02`.

**Measured (demo scale):** champlain **11.1 ms** (132 light + 12 full + 1 AD pass), kelly **1.8 ms**.
**RED captured** for both the R2-joint fixture (reverting the unification → `plausible=True`) and
confirm-by-rerun provenance (stale metrics → all six live guardrails mismatch).

### ✅ C4(b) DOC SWEEP + FINAL CLEANUP — DONE (2026-08-31)

Doc agent **verified provenance itself** (re-ran `git log --all -S"9.4e-8"` → the single charter commit)
rather than trusting the brief, and found **two instances beyond the five named**
(`src/schemas/README.md:76`; `MISSION_5_MANUAL_TESTING.md:66`). Struck the retracted 73 ms, relabelled
9.4e-8 as a **contract figure** with the measured `round(payment,4)` → 1.1325e-7 recipe kept as the real
calibration argument, and rewrote the mission rationale to what measurement supports.

**Orchestrator closed the rest:** `src/agents/chief_strategist.py:83` **and** `:113` (the last two live-code
"seven live" instances), and `engine.py`'s `_CoreOverrides` docstring now states the **GD3 partition** as
the reason no assumption field exists — *"widening this dataclass to reach a `MODEL_ASSUMPTIONS` path is a
Founder Proxy escalation citing GD3 — a rationale string is not a clearance."* **All live-code instances
are fixed**; remaining hits are Mission 4 historical artifacts and reconciliation stamps that *describe*
the correction.

**Manual-testing Cases 7/8/9 converted from ACCEPTANCE TARGETs to real commands + observed output**
(orchestrator-run): negative price → clean `ValidationError` naming field and bound; `--horizon 100` →
report written, exit 0; `--horizon 101` → `Forecast horizon must be between 1 and 100 years; got 101.`,
exit 1, **no traceback**.

### 📊 BATTERY — GREEN on a settled tree (2026-08-31)

| Gate | Result |
| --- | --- |
| `pytest` | **3403 passed, 1 skipped** (baseline 3197) |
| Coverage | **88.98%** (gate ≥80%) |
| `ruff format --check .` | 252 files already formatted |
| `ruff check .` | All checks passed |
| `mypy .` | no issues in 250 source files |
| `python main.py` | clean, verdict DECLINE |

_All three lint/type commands run **separately** (Mission 4 lesson)._

### ⏭️ REMAINING BEFORE THE MISSION GATE

1. **IB.2 — the report section is NOT rendered yet.** IB.1's note: *"the renderer does not yet consume
   `RecourseAnalysis.combinations`."* The data contract is complete (asks in native units,
   `fraction_of_cap`, confirming-run margins, counters + reasons, the exemplar) — **but Half B is
   invisible to a user until the report renders it.** This is the gap between "built" and "shipped".
2. **The acceleration pass** (Roger: *"then we'll try to accelerate the processing speed"*) — GC tuning
   (verified 183.5 → 117.7 ms), the aggregate-shift seam (**guardian review required** — it touches
   `precompute_income`'s deliberate identity check), and **benching a wider dual** (`Dual4` is
   fixed-width; 10 assumption columns would need `Dual10`, and D.1's "width is nearly free" was measured
   only *up to the unrolled slot count* — an extrapolation, not a measurement).
3. **Assumptions → breakeven** (GD3-cleared for vacancy + growth rates; **exit cap, cap drift and
   horizon are BARRED** until a real terminal sale model exists).
4. **Gate V** (code review + guardian re-check), then **Roger's mission gate**.
5. Stale **"7×4 Jacobian API"** language in charter/handoff — the shipped seam is **8 × N**.

### 🏷️ MISSION RENAMED — "Adjoint" was technically wrong (Roger, 2026-08-31)

**Roger caught a naming error that would not have survived expert review.** The mission, branch, charter
filename and docs all said **"Adjoint Differentiation."**

**Adjoint differentiation (AAD) means REVERSE mode.** Its entire value proposition is **many inputs → few
outputs** — that is *why* quant desks adopted it. **This problem is inverted: 4 levers in, 8 metric rows
out.** Discovery measured exactly that and chose the opposite mode:

| Mode | Measured | Chosen |
| --- | ---: | --- |
| reverse-mode Wengert tape (**true AAD**) | **6.9×** an engine pass (+443 tape entries/pass, ~4k at H=100) | ❌ |
| **forward-mode `Dual4`** (tangent-linear) | **4.11×**, full 8×4 Jacobian in one pass | ✅ |

`src/core/finance/dual.py` and `jacobian.py` implement **forward-mode (tangent-linear) AD — the opposite
of an adjoint.** Roger: _"a quant reviewer spots this in ten seconds."_ He is right, and the label was
describing **the algorithm we measured and deliberately did not build.**

**Renamed before Gate V:**
| Item | From → To |
| --- | --- |
| Branch | `mission/5-adjoint-differentiation` → **`mission/5-forward-mode-differentiation`** _(local only, never pushed — no remote rename needed, no force-push)_ |
| Charter file | `MISSION_5_adjoint_differentiation.md` → **`MISSION_5_forward_mode_differentiation.md`** _(via `git mv`, history preserved)_ |
| Title | → **"Mission 5 — Forward-Mode Differentiation & Optimized Recourse Search"** |
| Files updated | charter · handoff · plain-English brief · this tracker · manual-testing doc · `ROADMAP_TRACKER.md` · **two shipped docstrings** in `tests/core/finance/golden_tolerance.py` and `test_golden_forecasts.py` |

**Deliberately NOT changed** — three occurrences where "AAD"/"Adjoint" is *correct*:
1. `MISSION_5_HANDOFF.md:71` and charter `:145` — _"reverse-mode AD (true AAD) wins when inputs vastly
   outnumber outputs"_. These **explain what AAD is and why it was rejected**; they are accurate and
   load-bearing. Scrubbing them would delete the reasoning.
2. The verbatim quote of commit `87efd22`'s message — **immutable history**, annotated in place rather
   than altered.

**Nothing about the implementation changed — only the label.** The mission-5-discovery memos retain the
old name in their own titles/prose as dated historical artifacts.

### ✅ BUG.1 — `amortization_payment` zero-division + small-rate accuracy — **DONE, verified inline (2026-08-31)**

Found by D.5 as a side-finding, reproduced by the orchestrator, fixed and independently re-verified.
**Not a Mission 5 regression — a latent finance-core defect Mission 5's harder lever search would have
walked straight into** (`recourse.py`'s rate lever is `max(0.0, interest_rate - t)` and bisection drives
`t` toward the floor).

**Cause:** for `r` below ~float64 epsilon, `1.0 + r` rounds to exactly `1.0`, so `(1.0+r)**(-years)` is
exactly `1.0` and the denominator `1.0 - 1.0` is exactly zero. The `rate <= 0` guard never covered
`0 < rate < ~1.1e-16`. **A second, worse defect sat above the crash:** catastrophic cancellation made
`rate=1e-12` return **3333.037 against a true 3333.333** — a silently wrong *money number*, reachable
long before the crash threshold.

**Fix:** `denom = -math.expm1(-years * math.log1p(rate))` for `0 < rate < 1e-6`; paths for `rate <= 0`
and `rate >= 1e-6` **byte-for-byte untouched**. Clamp-to-limit was rejected for fixing only the crash;
a series expansion was rejected as reuse-hostile — `log1p`/`expm1` are the stdlib's own primitives for
exactly this cancellation, need no truncation-order judgment, and hold ~1e-16 relative accuracy from
1e-1 down to 1e-19 (verified against 60-digit `mpmath`).

**⭐ The threshold is derived, not invented** — the project's no-new-constants discipline applied
correctly, one hour after IT.1 shipped the constant it reuses. The naive formula's surviving relative
error is `(eps/2)/r`, independent of `n` (confirmed ±1% across years ∈ {1,2,5,10,30,50,100,200} and
principal ∈ {1, 1e5, 1e7}). Solving `(eps/2)/r <= REL_TOL` against **`REL_TOL = 1e-9` from
`tests/core/finance/golden_tolerance.py`** gives `r* ≈ 1.110223e-7`; `1e-6` sits ~9× above it and far
below any real financing rate (the rate lever steps in 1–5 bps, i.e. ≥1e-4).

**Orchestrator verification (independent, not on report):**
| Check | Result |
| --- | --- |
| Crash | `rate=1e-17` → **3333.3333333333335** (was `ZeroDivisionError`) — exactly the limit |
| Accuracy | `rate=1e-12` → **3333.3333333849996** (was 3333.037; error 0.3 → 5e-11) |
| Bit-identical on normal rates | **0 mismatches** across 126 combinations (7 rates × 6 terms × 3 principals, all ≥1e-4) vs the frozen pre-fix formula |
| Continuity across threshold | 8.2e-11 relative — two orders inside `REL_TOL`, invariant across years |
| `tests/core/finance/` (golden, anchor, parity, bit-exact) | **361 passed, 1 skipped** |
| RED proof | Captured real `ZeroDivisionError` traceback on revert; restored green |
| Suite | **3267 passed, 1 skipped**, coverage **88.38%** |

_Files: `src/core/finance/amortization.py`, `tests/unit/test_amortization_small_rate.py` (new, 45 tests)._

### ✅ FINAL HALF B ARCHITECTURE — settled by Roger, 2026-08-31 (supersedes D.4's design and PD.2 call 5)

**Roger's design, in his words:** *"the n starting points can be discarded based on them being rejected
or not. So at the end we'll have at most n propositions and a minimal one (which is already among the
n); we can expect ≤ n outputs."* Plus: *"with a 'cheapest total negotiation' alongside the others, we
have no more need for a ranking."*

#### The output contract

| Piece | Decision |
| --- | --- |
| **Search unit** | One **minimal-ask** solve per **lever subset**, seeded by the AD gradient's direction within that subset. |
| **n** | The **11 multi-lever subsets** (4 levers → 15 non-empty subsets; the 4 singletons already ship as Mission 4's single-lever menu). |
| **Filter** | Drop subsets the unified plausibility gate rejects, and those with no feasible crossing. |
| **Output** | **≤ 11 propositions**, each the minimal ask for its subset. Both sections ship (single-lever + combinations) — Roger: *"we do not know if the investor can act on one or multiple levers."* |
| **Cheapest total** | A **LABEL on one of the n**, not a separate search. |
| **RANKING** | ❌ **ELIMINATED.** Not "parked" — **no longer needed.** |
| **Confirmation** | Every proposition confirmed by one real, un-differentiated `run_financial_model` re-run. Unchanged. |

**Why the ranking problem dissolved rather than being deferred.** Every combination belongs to some lever
subset, so the global minimum-total-ask **is provably the minimum over the per-subset answers** — it
cannot be anywhere else. So "cheapest total" is an `argmin` over a set already computed, needing no
separate search and **no ordering criterion**. With all surviving propositions shown (≤ n) there is no
top-3 cut, hence nothing to rank. **This deletes three things at once:** D.4's arbitrary 39-ray grid, the
top-3 cut, and the `parsimony → leximin` order — which the orchestrator had flagged as *"a product
opinion wearing a formula."* Output size now derives from the problem's own structure instead of a
product choice. **PD.2 call 5 is superseded; the designed order is shelved, not deleted.**

#### ⚠️ Mechanism requirement — seeds alone are NOT enough

D.5 measured the faithful architecture returning **1 combination, not n**: *"all seeds collapse to the
min-sum optimum."* Expected in hindsight — on a monotone problem the unconstrained minimum-total-ask has
**one** answer, so every starting point walks to it. **Different seeds do not produce different answers
on their own.** Each run must be **restricted to its own lever subset**. D.5 benched exactly that variant
(`A tuned`, subset-restricted) and it was the **best coverage in the field: 100% of feasible subsets,
optimality gap ≤ 0.004**, beating the dense reference itself on kelly's min-sum. The AD gradient sets the
**direction within** each subset; the **subset restriction** is what keeps the n answers distinct.

#### 🛡️ `max_iter` — Roger, 2026-08-31: *"to avoid infinite runs, a max-iter parameter representing the maximum number of iterations to find the global min."*

**This targets a MEASURED pathology, not a hypothetical one.** D.5 found the subset-restricted architecture
we adopted is **worst-in-bench on infeasible subsets — 1,686 probes on kelly, 2,356 on the null deal**,
versus ~77–246 on the healthy path. That is precisely the runaway `max_iter` bounds. Bisection's own inner
loop already converges geometrically (~11 probes); `max_iter` guards the **outer per-subset solve** and the
pathological/infeasible cases where the cost actually explodes.

**🔴 BINDING HONESTY REQUIREMENT — three outcomes, never two.** Budget exhaustion means *"we did not find
one,"* **not** *"there isn't one."* These must not be conflated:

| Outcome | Meaning | Precedent |
| --- | --- | --- |
| **FOUND** | A plausible combination, confirmed by a real engine re-run. | — |
| **PROVEN NULL** | No feasible/plausible combination exists. | D.5 **proved** kelly's null: 0 of 91 frontier points pass, min R2 divergence 0.0215. |
| **UNDETERMINED** | `max_iter` exhausted; the search ran out of budget. | **NEW — must be visibly distinct.** |

Reporting an UNDETERMINED as a PROVEN NULL would tell an investor "nothing can save this deal" when the
truth is "we stopped looking." That is the exact class of dishonesty the honest-null rule exists to
prevent. **`max_iter` must also be deterministic** — same inputs ⇒ same outcome including the same
exhaustion — or the determinism invariant breaks.

### 🔄 REVERSAL — "DROP AD" IS UNWOUND. Roger's architecture was never benchmarked. (2026-08-31, later)

**Status: the AD sub-wave is REINSTATED and RE-SCOPED. The earlier "drop AD, charter it later" decision
is VOID.** Recorded in full because the reasoning matters more than the outcome.

#### What went wrong — an orchestrator error, stated plainly

Discovery asked, and answered, **"does the recourse *search* need derivatives?"** The answer was no, and
that answer is sound. But **that is not the question Roger asked.** His stated purpose for AD, in his own
words:

> *"AD is used as a global search to provide 4 starting points — in reality **n** starting points based on
> the number of partial derivatives — then we try to find proper solutions applying gradient methods like
> the Lagrangian optimizer."*
> *"In one pass we have four scenarios instead of doing one at a time."*

**The orchestrator escalated a recommendation to drop AD on the strength of an evaluation that never
tested the architecture Roger specified.** Roger caught it. Two distinct failures:

1. **Wrong question.** Every agent evaluated AD as a *search accelerator* (Newton-vs-bisection on the
   distance sub-problem). Nobody evaluated it as a **direction-selection and analysis capability**, which
   is what Roger wanted. "Derivatives as a product rather than a search tool" was even listed by the
   orchestrator as a *hypothetical* condition under which AD would be justified — while being the actual
   stated requirement all along.
2. **Unfair benchmark, reported as a finding.** D.4 measured augmented Lagrangian at **182 probes** and
   interior point at **518–558**, and the orchestrator relayed this as *"the charter's prescribed family
   lost by 16×–50×."* **That was overstated.** D.4 benched them **cold-start and standalone**, and itself
   noted "penalty-schedule knobs that change the answer" — i.e. an unconfigured method. **Roger's
   architecture seeds the optimizer from the AD gradient; that configuration was never on the bench.**
   A straw man's defeat was reported as a measurement.

#### The revised design — gradient for DIRECTION, bisection for DISTANCE

The one durable Discovery finding (**margins measured monotone** along every axis and diagonal — 2,196
segments, 3 deals, zero violations) splits the problem cleanly, and the two approaches turn out to be
**complementary, not rival**:

| Sub-problem | Winner | Why |
| --- | --- | --- |
| **WHICH direction to move** | **AD gradient (Roger's design)** | One forward pass yields **all n partials** at **4.1× an engine pass** vs **8 passes** for central FD — and **tangent width is nearly free** (dual-1 measured 5.5×, *worse* than dual-4's 4.1×). This is literally "four scenarios in one pass." Steepest margin-gain-per-unit-ask is a **model-informed** direction choice; D.4's 39 fixed rays are an arbitrary grid approximating the same thing badly. |
| **HOW FAR along it** | **Bisection (D.4's finding)** | Monotone ⇒ exactly one crossing. A dual pass costs ~4× a plain evaluation, so Newton's fewer-but-costlier steps measured **11–41 probes vs bisection's fixed 11**. This finding stands. |

**What drops out is the Lagrangian's penalty machinery — NOT the gradient, and NOT Roger's seeding idea.**
Re-scope accordingly: **keep** the forward dual pass + the n-lever Jacobian for direction seeding (and as a
user-facing sensitivity capability); **drop** Newton-on-guardrail, which measured as a wash.

**This also restores AD's justification on measured grounds** rather than on the retracted perf story: it
is what makes direction selection principled instead of a grid of 39 guesses.

#### ⭐ The coverage question that decides it — and was never asked

A fixed 39-ray grid can only find combinations lying **along one of its 39 predetermined directions.** A
better combination sitting *between* two rays is **invisible to it.** Nobody measured this. It is a
**product-quality** question — does the investor get shown the best available option, or merely the best
one that happened to lie on a grid line? — and it outranks probe count.

#### D.5 — FAIR BENCH commissioned (dispatched 2026-08-31, `staff-python-engineer` → **fable**)

Given to a **fresh agent**, deliberately: D.4's author had already reached a conclusion. Instructed to
treat D.4's verdict as *an untested hypothesis, not a finding*, and to **be fair to the contender D.4
rejected** — to configure the Lagrangian properly and report knob-sensitivity as a finding rather than
leaving it naive and reporting its defeat. Four contenders: **A** Roger's architecture (AD gradient → n
seeded starting points → tuned gradient optimization), **B** D.4's 39-ray + bisection incumbent, **C** the
synthesis (gradient for direction, bisection for distance), **D** the single-lever baseline.
**Primary metric is QUALITY, not speed** — solution minimality, **recall against a dense reference set of
truly-minimal combinations**, determinism, robustness — with probes/wall-time secondary.

#### Also settled in the same exchange — RANKING

Roger asked whether a ranking solution was ever chartered. **It was, and one exists** — he had simply lost
track of it. Charter: *normalization-free top-3 (parsimony · within-axis magnitude · diversity, DiCE-style)*;
D.4 designed the total order `(parsimony, leximin-sorted own-fractions, fixed-order fraction tuple, subset
ordinal, ray ordinal)`; PD.2 ratified parsimony-strictly-before-magnitude, no padding below 3, and required
`fraction_of_cap` per lever so the investor can override it.

**But its weakness is real and the orchestrator flagged it:** *"parsimony before magnitude" is a stated
product preference, not a derived result — a product opinion wearing a formula.* **Roger's call: PARK
RANKING AS OPTIONAL for v1.** Ship the combinations with their per-lever asks and **do not assert an
order**. More honest than a heuristic ranking, and it removes the only part of Half B with no principled
basis. The designed order is kept on the shelf, not deleted. **PD.2's call 5 is superseded on this point.**

#### Net effect on the mission

| Item | Status |
| --- | --- |
| Tolerance rule (IT.1) | **Unaffected — built and green.** |
| GC tuning + aggregate seam | **Unaffected — still in scope**, still the measured path to the perf target. |
| AD sub-wave | **REINSTATED, re-scoped** to forward dual pass + n-lever Jacobian for direction seeding + sensitivity. **Newton-on-guardrail dropped.** Pending D.5. |
| Half B | **Unaffected in purpose**; its *search architecture* is now pending D.5 rather than settled on D.4. |
| Top-3 ranking | **PARKED as optional (Roger, 2026-08-31).** Combinations ship unranked in v1. |
| ADC.1 (internal AD checkpoint) | **Still a hard gate**, re-scoped to the new AD surface. |

### ⭐ ROGER'S GATE-D DECISION — 2026-08-31

Discovery inverted the mission's rationale, and the fork was put to Roger rather than resolved by the
orchestrator. **Both answers recorded verbatim:**

| Question | **Roger's decision** |
| --- | --- |
| Mission path, given AD is measured NO-GO as a perf play | **"Rewrite rationale, ship all of it."** Tolerance rule → cheap perf wins → AD, justified honestly as **Half B's Jacobian enabler** rather than as a speed play → Half B optimizer. Full chartered scope survives; the *rationale* is corrected. |
| The two NEW perf wins Discovery uncovered (not in the charter) | **"Both, this mission."** GC threshold tuning **and** the aggregate-shift seam are **IN SCOPE**. |

**Consequences, now binding:**
1. **The mission's rationale is rewritten.** "AD is the remaining credible path to 30 ms" is **struck** —
   it is false at every measured `k`. AD ships as **infrastructure for Half B**, and Half B is the
   mission's centre of gravity. **"73 ms" is struck** as retracted. The charter documents must be
   corrected (this also discharges part of guardian condition **C4(b)**, due before Gate V).
2. **Scope ADDED (Roger-approved, charter did not anticipate):** GC threshold tuning + the
   aggregate-shift seam. These, not AD, are the actual path to the 30 ms target.
3. The **internal AD checkpoint (ADC.1) still gates Half B implementation** — unchanged. But see the
   orchestrator adjudication below: D.4 is asked whether Half B **degrades gracefully to finite
   differences**, so that Half B is not hostage to Half A.

### 🔬 ORCHESTRATOR ADJUDICATION — D.1 vs EV.1 on the aggregate seam (2026-08-31)

**The two agents directly contradicted each other on the finding Roger just put in scope, so the
orchestrator settled it by measurement rather than by picking a side.**

- **D.1 claimed** AD gets `d(metric)/d(rent)` with zero rent-roll materialisation, via the
  `(gsi_y1, goi_y1)` aggregate.
- **EV.1 claimed** the flip condition does **not** fire: *"forward mode gives the slope at the current
  point; Newton must then evaluate at the proposed point, and `_annual_income` reduces over
  `income.units`."*

**Verdict: D.1 is right on the mathematics; EV.1 is right only about the code as it stands today.**
Read at `recourse.py:390-392`, the rent lever is `rent_month + t` per unit with **no clamping**, so
`gsi = (Σ(rent_i + other_i) + n·t)·12 = gsi_base + 12·n·t` — **exactly linear**, and
`goi = gsi·occupancy·bad_debt` is linear in `gsi`. So the perturbed aggregate has a **closed form**:
you never call `_annual_income`, which is what EV.1's objection assumed you must. EV.1 is nonetheless
correct that the **current** path forces materialisation — `precompute_income`'s deliberate identity
check (`engine.py:369`, *"misuse is made impossible, not merely discouraged"*) refuses a mismatched
aggregate. **Removing that constraint safely is the real engineering work in the seam, and it touches a
documented safety invariant — flag for guardian review when it lands.**

#### ⚠️ And a third finding neither agent reported — measured by the orchestrator

The closed-form shift is **mathematically exact but NOT bit-exact**: floating-point summation order
differs between `Σ(rent_i + t)` and `Σ(rent_i) + n·t`.

| units | worst relative drift | vs noise floor **1.151e-13** | vs `REL_TOL` 1e-9 |
| ---: | ---: | --- | --- |
| 500 | **3.893e-15** | below | ~257,000× inside |
| 5,000 | **3.456e-14** | below | ~29,000× inside |

**This is load-bearing and it changes an argument on the board.** EV.1 objected that _"'the tolerance
rule is independently valuable' is doing more work than the evidence supports — D.3 §1.6's case-FOR is
entirely AD-conditional."_ **That objection is now refuted by measurement:** the aggregate-shift seam —
which Roger put in scope, and which is the *actual* perf win — **also breaks bit-exactness and also
needs the tolerance rule.** The tolerance rule is therefore independently valuable on a second,
completely AD-independent ground. Its drift sits comfortably below the reordering noise floor, so it
must pass cleanly **without** tripping the approaching-tolerance band — a requirement now written into
IT.1's brief and to be pinned by IT.2.

### 📋 EV.1 RESULT — composite **84.3 / B** (independent, deliberately adversarial re-scope)

Graded as-built on real file evidence. **Engineering 89 · Finance 85 · Testing/CI 88 · Ingestion/CV 83 ·
Docs 88 · Product 83 · Competitive 72.** Build 86.8 / Market 78.6 — up from the ledger's stale `B-`
(dated 2026-07-23, four missions ago). **Competitive read:** not competitive as a *product* (no data,
CLI-only) but **category-leading on exactly two columns — actionable recourse 5/5** (best competitor
manages 2/5) **and determinism/auditability 5/5** (the only tool in the set whose verdict is provably
not model-authored).

**Its verdict — "no, not as chartered; proceed with a rewritten rationale" — is the position Roger
adopted.** Findings carried forward:
- **Perf is NOT a real user gap: LOW.** Measured `36_kelly_moncton` **8.22 ms**, `82_champlain_dieppe`
  **7.19 ms**, inside a **0.673 s** `python main.py`. **And nothing gates it:** `BUDGET_MS` has no
  reader outside its own file, that file defines **no `test_*`**, and `ci.yml` has **no perf step**.
  Theme: _"the project measures beautifully and gates nothing on the measurement."_
- **Half B is the real severity** — a **product/capability** gap: Product 83→~87, Competitive 72→~76.
- ⚠️ **HIGH, and it is a Mission 5 risk, not just a backlog row:** the **flagship demo does not show the
  flagship feature** — `is_genuinely_close(36_kelly_moncton)` is **False**, so the quickstart's
  `investment_analysis.md` has **no recourse section at all**. Half B would add a *second* section to a
  report the demo never renders. **Folded into D.4's brief** as a required design input.
- **Half B can ship a defensible v1 on finite differences** (8 central-FD probes ≈0.34 ms vs 1 dual pass
  ≈0.17 ms, on a 7–9 ms analysis) — **so Half B need not be hostage to Half A. D.4 is asked to confirm
  the design degrades gracefully to FD.**
- Doc reconciliation flagged: ROADMAP §1 says "87 test files / 81.87% / grade B-"; actual **148 /
  88.37% / B**. Dead config (`pytest.ini --cov=src/tools`); an unverifiable "Grant Cardone–inspired"
  README claim.
- Backlog (not Mission 5, recorded): annual amortization cadence overstates debt service ~1% into
  DSCR/CF/CoC/IRR undocumented; `irr(...) or 0.0` conflates undefined with 0%; `do_refi` defaults
  `True` → measured **+110 bps IRR** when the block is omitted; insight→money path unreachable on real
  data.

### 📋 PD.1 RESULT — all five founder calls DECIDED; nothing escalated

| Call | Decision |
| --- | --- |
| **(a) Tolerance** | **RATIFIED `1e-9`.** Tighter is unsafe (1e-11 is only ~87× above the 1.151e-13 noise floor against ~143× cancellation amplification — it would fail builds on *correct* arithmetic); looser buys nothing measured. **Refinement neither prior memo stated:** because the approaching band `[5e-10, 1e-9)` **fails the build**, real silent blindness is **5e-10, not 1e-9** — **$0.107** on the largest synthetic value, **$0.000267** on the shipped deal, i.e. **half what the charter asked him to accept.** Binding: C6's assertion must be executable, not prose. |
| **(b) `GENUINELY_CLOSE_MAX_FAILS`** | **KEEP 3.** Not an honesty question (`ABOUT_RECOURSE_BLOCK` makes no closeness claim) but scoping/signal-to-noise. **2** re-couples the gate to the verdict (the coupling Mission 4 explicitly rejected) and kills `82_champlain`'s reason to exist; **4** turns recourse on for `36_kelly_moncton`, *changing the flagship demo report* — a product change smuggled in as a threshold tweak. **3 is the fail count at which `synthesize_thesis` itself first turns DECLINE (`chief_strategist.py:315`)** — a reused threshold, not a fifth invented number, with a committed fixture either side. |
| **(c) Money bounds** | **17 fields.** `purchase_price` **`gt=0`** (all-cash is `down_payment_rate=1.0`, never a zero price — confirmed against the `all_cash_deal` golden); every other money field **`ge=0`** (`closing_costs`, 12 opex lines, `rent_month`, `other_income_month`, `capex_reserve_upfront`) — zero is legitimate for each. No rate/ratio/year field touched. Blast radius verified **zero** across all 34 goldens + both bundles; all four recourse search bounds stay inside the new floors. |
| **(d) Horizon → 100** | **RATIFIED**, on provenance that *does* check out (unlike 9.4e-8): `MISSION_4_MANUAL_TESTING.md:540-579`, *"a 99-year ground lease is a real financial instrument."* **Explicitly rejected the benchmark as justification** — the bench row bypasses `RunOptions`; a stress ceiling is not a product envelope. Honesty: under shipped defaults **no guardrail reads past Year 10**. |
| **(e) CLI message** | `Forecast horizon must be between 1 and 100 years; got 101.` — stderr, `SystemExit`, exit 1, no traceback; **bounds read from the field constraint, never typed as literals.** Found **two further holes** folded into the same defect: `main.py:256` `horizon = args.horizon or 10` **bypasses validation entirely**, and `src/inputs/inputs.py:305-311` **silently ignores** an unparseable `AIREAL_HORIZON` — *worse than a traceback, because the user gets a report at a horizon they did not choose.* |

**⚠️ PD.1 corrected a claim the ORCHESTRATOR relayed — recorded plainly.** I forwarded to D.1, quoting
`MISSION_4_MANUAL_TESTING.md`, that *"only 4 guardrails are live and failing at the gate limit."* PD.1
**measured 5 live / 3 failing**, and that shipped **max live is 6, not 7** (`REQUIRE_POSITIVE_CF_ALL =
False`; 6 needs a user-set `cap_rate_floor`). The quote was correctly attributed but **the Mission 4
record it came from is itself wrong** — so my relay propagated a bad number into D.1's memo
(`D1_ad_design.md:37`, `:296`). **D.1's ruling survives the correction** (its Jacobian rows are
`ForecastMetrics` fields, not guardrails) but the sentence does not. **"Up to seven live guardrails" is
wrong in six places** — `recourse.py:135`, `src/market/README.md:28` and `:70`, `README.md:291`,
`CHANGELOG.md:10`. This is the **third doc-audit finding of this exact shape** this mission; folded into
the C4(b) documentation sweep and into D.4's brief.

### 📋 D.4 RESULT — verified inline 2026-08-31. **The charter's prescribed optimizer family LOST on measurement.**

**Method chosen by measurement: deterministic multi-start ray restriction + safeguarded 1-D bisection**
— Mission 4's own `_bisect` primitive applied to a ray scalar. Measured against the real engine on two
open-gate deals:

| Method | Measured probes | Note |
| --- | ---: | --- |
| **ray-restriction + bisection** | **11 (fixed)** | lands one *minimal feasible* point |
| ray-Newton with slopes | 11–41 | **never beat bisection**; parity at best even with AD slopes |
| SQP-lite | 10 + 10 walk-back | reaches a **non-minimal interior** point via an emergent, uncontrolled direction; the walk-back *is* ray bisection |
| augmented Lagrangian | **182** | penalty-schedule knobs that **change the answer** |
| interior point | **518–558** | to approximate what the ray got in 11 |

**The enabling measured fact:** all live guardrail margins are **monotone non-decreasing** along every
lever axis and every diagonal ray inside the plausibility box — **2,196 scan segments, 3 deals, zero
violations** — so first crossing = only crossing. Overturn conditions stated: a non-monotone margin,
lever count > ~6, or a future genuine scalar objective.

**⚠️ This is outside the charter's named family** (augmented Lagrangian / SQP / projected-gradient /
interior-point). **Accepted**, because the charter's binding instruction was *"Discovery picks the
concrete one **by measurement**"* — and this **is** that measurement, with the named family measured and
beaten by 16×–50× on probe count. It also reuses an existing primitive rather than importing new
machinery, which is the project's documented YAGNI posture. **Recorded as a charter deviation for Gate V
and for PD.2's awareness.**

**Multi-start:** fixed **39-ray grid** (11 subsets |S|≥2 × balanced + one-lever-0.5-tilts), enumerated off
`_LEVER_ORDER` tuples with a unique `(subset, ray)` ordinal as final tiebreak — **no dict/set ordering
anywhere.** Measured: top-3 **bit-stable** from the balanced-only grid through a 67-ray refinement on both
deals; two fresh runs **byte-identical**. Measured local-minima case: at B=1.5, 7 of 11 balanced rays are
gate-rejected on the near-miss fixture and the enumeration still returns a full plausible top-3 that a
single-start descent would have missed.

**The unified joint gate — R1..R4, and R2 is the real unification.** R2 routes **one `MarketHypothesis`
carrying both the signed rate delta AND the engine-computed implied-cap delta of the full combination**
through the **unmodified `reject_unrealistic`** — making the rejector's own `|rate − cap| ≤ 0.02` axis fire
**jointly for the first time, with ZERO new constants.** It is an **a posteriori filter on an
engine-computed quantity — not a pretend-inverse** of one, which keeps the "never invert a formula"
invariant intact.

**✅ Worked jointly-implausible fixture — ORCHESTRATOR-VERIFIED.** On committed `82_champlain_dieppe`:
**rate −90 bps + price −$90,000 (14.88%)**. Every single lever passes the real production
`_judge_plausibility`; jointly `|−0.0090 − (+0.0121)| = **0.0211 > 0.02**` trips the rejector. Verified
against `src/market/rejector.py:23` — `_rates_vs_cap_ok` is `abs(interest_rate_delta - cap_rate_delta)
<= 0.02 + 1e-12`; the arithmetic and the crossing both check out. The combination genuinely closes all
three failing guardrails and is confirmed by a full run. **Both asks sit strictly inside their individual
caps — no `==`-threshold fragility for QA.** Second variant: price −15% + opex −20% with *no* rate move
also trips. _(This is exactly the fixture the charter demanded and the QA suite requires.)_

**Top-3:** total-order key `(parsimony, leximin-sorted own-fractions, fixed-order fraction tuple, subset
ordinal, ray ordinal)` — **no sums, no cross-lever conversion anywhere**; antisymmetry via the unique
ordinal (proof in memo §4). Diversity = greedy over distinct active-lever sets. Measured champlain top-3:
three genuinely different 2-lever negotiations.

**Confirm-by-rerun:** provisional top-3 from light-path candidates; each shipped combination confirmed by
one real `run_financial_model` at **rounded** asks against **all** live guardrails; fallback to unrounded
`t*` (second full run), then drop-and-promote. Measured **zero confirm failures** across all fixtures;
**3 confirms = 9.2 ms** at 5,000u/100y, ~0.2 ms at demo scale.

**Honest-null + report seam:** additive `CombinationAnalysis` on `RecourseAnalysis` (0–3 combinations,
confirmed margins, plus `rays_searched / edge_infeasible / gate_rejected / gate_reasons` counters so a
null is **explained, not silent**). Measured full-null path exists.

#### 🚨 …and the finding that erodes AD's LAST justification

> **The winning search uses NO DERIVATIVES AT ALL.** The Jacobian's only Half-B roles are subset pruning
> and one optional blended ray — **both accept an FD-filled `MetricsJacobian` (measured 0.34 ms) or
> nothing at all. Half B is NOT hostage to Half A's AD go/no-go.**

**This is the third successive erosion of the AD rationale, and it postdates Roger's decision:**
| # | Claim | Status |
| --- | --- | --- |
| 1 | AD is the path to 30 ms | **Refuted** (D.2, D.1, EV.1 — three methods, ~82 ms at best) |
| 2 | AD is justified as Half B's Jacobian enabler | **Substantially eroded** (D.4 — Half B needs no derivatives; the KKT family that would have needed them lost by 16×–50×) |
| 3 | The real scale win | **The aggregate-shift seam, again** — rent probes 3.01 ms → 0.20 ms at 5,000 units; pipeline measured 337 ms without it, projected ~60–100 ms with it. **Needs no AD.** |

**⚠️ ESCALATED TO ROGER.** He decided "ship all of it" **on the premise that Half B needed the Jacobian**.
D.4 measured that it does not. That is new information postdating the decision, so it goes back to him
rather than being absorbed silently. **Half B and the tolerance rule are unaffected and continue; only the
AD sub-wave is in question.**

### Dispatch log — Wave Discovery

**Batch 1 dispatched 2026-08-31** (concurrency cap ≤3 respected): **D.1** `staff-python-engineer` →
fable · **D.2** `principal-performance-engineer` → opus · **D.3** `staff-python-engineer` → opus.
All three at the router-confirmed tier; **no tier deviation in batch 1.** Every prompt carried the
GRAPHIFY CONTRACT verbatim, the `airedeal` conda-path warning (with the explicit "`~/miniconda3` is
WRONG" note), the re-read-before-you-reason rule, the confirmed golden-harness drift, and an explicit
**no-production-code** constraint scoping writes to one memo under
`docs/plans/mission-5-discovery/` plus a per-agent scratchpad.

**Batch 2: EV.1 → opus dispatched and DONE 2026-08-31** at the confirmed tier when D.2's lane freed.

**D.4 → fable: HOLD RELEASED, dispatched 2026-08-31** once Roger committed to shipping Half B. The
hold did its job — it deferred the largest spend line until the flip question was answered and the fork
was Roger's. Original reasoning retained below.

**~~D.4 → fable: HELD, pending D.1.~~** This is an ordering decision *within* Wave Discovery, not a change
to a chartered gate boundary — D.4 still runs in Discovery and PD.2 still decides at Gate D. The reason
is that D.2's NO-GO read makes router trigger **T4 materially more live** than it was at kickoff: if the
AD case does not hold, Half B does not happen and D.4's fable spend is fully sunk. D.1 answers the flip
question, so D.4 dispatches the moment D.1 lands — at which point we will know whether we are designing
Half B or shelving it. Cost avoided if AD is NO-GO; nothing lost if it is GO.

#### D.2 RESULT — verified inline 2026-08-31, and it moves the mission's premise

**Orchestrator verification (never trust an agent's "done"):**
- **73 ms reconciliation — CONFIRMED.** Located Roger's own retraction at
  `docs/manual testing/MISSION_4_MANUAL_TESTING.md:513`; `git log -S"73.8"` → `912a55f`. _(D.2 cited
  the quote as living in `MISSION_4_SPRINT_TRACKER.md`; it is actually in the manual-testing doc — a
  citation slip, substance exact.)_ The same passage **independently corroborates D.2's cost split**,
  in Roger's words: _"39 of the 150 real probes are `rent_per_unit_month`, measured at ~4,200 µs each
  against ~178 µs for the price shape (~24×) — ~164 ms, or 85% of the total, in the one lever the
  harness excluded."_
- **GC finding — INDEPENDENTLY REPRODUCED** on the orchestrator's own harness against the real
  `compute_recourse` at 5,000u/100y: **GC on 183.5 ms best / 187.9 median → GC off 120.7 / 122.6 →
  GC re-enabled 179.6 / 185.0 → `gc.set_threshold(50000,10,10)` 117.7 / 119.0.** The effect is real,
  reversible, and worth **~35% of the row for zero finance-core diff.**

**Findings of record:**
| # | Finding |
| --- | --- |
| 1 | Honest baseline **best 175–198 ms / median 181–203 ms** quiet; **333–366 ms contended** (machine had a competing job + fully consumed swap). PASS vs `BUDGET_MS=250` quiet, FAIL contended. **"73 ms" is retracted — strike it from the mission narrative.** |
| 2 | **150 probes** confirmed (141 light `_rerun` + 9 confirming full re-runs + 1 baseline), 12 pairs; per pair price 25 / rent 13 / rate 11 / opex 1 — the charter's "~10–20 per pair" is accurate. |
| 3 | **The premise is half wrong.** Recourse search ≈95% of the row, but the **engine forecast is only ~20%** of it; **74.5% is the 39 rent `_perturb` calls** (~3692 µs each) — the *copy*, not the arithmetic. `set.copy()` alone is 18% of the whole analysis. |
| 4 | **~36% of the row is garbage collection** — 195,000 short-lived `UnitIncome` objects per analysis. |
| 5 | **AD alone cannot reach 30 ms at any plausible k** (~82 ms at k=3, ~70 ms even at k=1) because ~44 ms is 12 surviving rent perturbations AD does not remove. AD and the rent fix are **substitutes competing for the same term, not complements**; the cheap one wins more (rent fix ~145 ms before AD, AD ~14 ms after it). Structural floor ≈16.5–22 ms. |
| 6 | **numpy re-measured and re-rejected.** ⚠ Hard input to D.1: a **length-4 numpy dual vector measured 1746 µs vs 154 µs for 4 scalar passes — 11.3× SLOWER.** Duals must be pure-Python; numpy-backed duals would push k ~3→~40 and make AD slower than baseline. Mission 4's "do not vectorise" stands, re-measured. |
| 7 | **Real deals are 7–9 ms** inside a ~0.7 s pipeline — no user experiences the budgeted row. |

**D.2's preliminary PF.1 read: NO-GO on AD as a performance intervention; conditional GO on AD as the
Half-B Jacobian enabler.** Budgets set: `BUDGET_MS = 250` unchanged (**do not tighten to 30 during the
mission — a 30 ms gate would flake at the measured spread**); timed assertions best-of-N, never median;
**new guard — the two real-deal rows stay ≤ 15 ms.**

**Orchestrator actions taken:** D.2's findings, the numpy-dual constraint, and its four open questions
were forwarded to the in-flight D.1, along with **the one question that would flip the verdict to GO —
_can AD obtain d(metric)/d(rent) WITHOUT materialising a perturbed rent roll?_** If a dual pass gets
rent sensitivity analytically through `precompute_income` (`engine.py:186`) instead of rebuilding 5,000
`UnitIncome` objects per probe, AD kills the 74.5% term nothing else in D.2's table touches and the perf
case reverses. D.1 was also told the Mission 4 record states **only 4 guardrails are live and failing at
the gate limit, not 7** — which bears directly on whether the seam is 7×4, 4×4, or dynamically shaped.

**⚠️ FOR ROGER — this is a Gate D input, not an orchestrator decision.** Two of the mission's premises
(the 73 ms figure; "engine probes are the cost") did not survive measurement. The tolerance rule and
Half B's product value are untouched by this. Gate D (PF.1) formally decides; EV.1 was re-scoped to
give an independent read on whether the mission still justifies itself.

#### ⚠️ Logged deviation — router trigger T4 considered and OVERRIDDEN (2026-08-31)

The router's **T4** advises: _"on ADC.1 = NO-GO, D.4/PD.2/IB.1/IB.2/IB.3/I.5 never dispatch. Do not
pre-spend fable on D.4 before ADC.1 exists — the single largest avoidable spend line in this mission."_

**Decision: D.4 runs in Discovery as chartered.** Reasons: (1) the charter and Roger's 2026-08-31
expand decision place D.4 in Discovery and **PD.2 at Gate D** — deferring D.4 past the AD checkpoint
would leave PD.2 with nothing to decide on and would silently move a chartered gate boundary, which is
not the orchestrator's call; (2) the charter is authoritative for scope and sequencing, and the router's
trigger is a **cost** judgement, not a correctness one; (3) D.4 is design-only and produces the
rejector-unification analysis that informs how the IA.1b Jacobian seam is shaped — value that survives
even an ADC.1 NO-GO.

**Accepted cost:** if ADC.1 records NO-GO, D.4's fable spend is sunk. **Surfaced to Roger** as the one
live cost objection on the board; Roger may direct D.4 be held until after ADC.1, which would defer
PD.2 with it. Router triggers **T2, T3, T5, T6, T7 remain armed** and unactioned.

### D.3 RESULT — verified inline 2026-08-31; the router's escalation to opus paid for itself

**Orchestrator verification of D.3's three provenance claims — all three CONFIRMED:**
| Claim | Verification |
| --- | --- |
| The `~9.4e-8` calibration figure has **no pre-Mission-5 provenance** | **CONFIRMED.** `git log --all -S"9.4e-8"` returns **exactly one commit: `87efd22`** — the Mission 5 charter commit itself. Every occurrence sits in Mission 5 planning docs (`MISSION_5_MANUAL_TESTING.md` ×4, `ROADMAP_TRACKER.md` ×3, the charter ×5, the handoff ×2). **Five charter documents assert it as if it were a prior measurement. It is not one.** |
| Exactly **one** committed version of the golden JSON | **CONFIRMED.** `git log --all -- tests/data/golden/finance_engine_forecasts.json` → `912a55f` only; both Mission 4 regenerations were squashed into it. "The ORIGINAL golden" is therefore unambiguous — **and git-history-based anchoring is impossible**, killing that option on the merits. |
| `MISSION_5_MANUAL_TESTING.md:91` prescribes an unobservable procedure | **CONFIRMED.** It reads _"Perturb one golden number by ~9.4e-8 relative"_ — mutating the anchor, which trips the digest test first with a different error. The doc marks it `[ACCEPTANCE TARGET — not yet runnable]` and says _"the orchestrator will supply two real commands here"_ — **orchestrator-owned; see the open item below.** |

**Design of record (subject to GD.1):** asymmetric `abs(actual-expected) <= 1e-9 * abs(expected)`, **not**
`math.isclose` _(isclose scales by `max(|a|,|b|)`, making the predicate depend partly on the value under
test — the wrong dependency for an anchor; the anchored value belongs in the denominator alone)_.
**`abs_tol = 0`, no absolute floor** — the tightest-budget field has a measured noise floor of 5.8e-11
against a 5.1e-7 budget, and it is the harness's most sensitive detector because
`principal_pay = max(0.0, pay - interest)` cancellation amplifies upstream error ~143×; any `abs_tol`
blinds it. **652 exact zeros are semantic** → compared exactly. **Uniform, no per-field exceptions** —
including `irr_10yr`, whose condition number measured 0.2–2.3× and whose response is linear across ten
orders, so Brent's `tol=1e-6` forces no carve-out _(and a per-field override table is itself a
per-field ratchet)_.

**1e-9 was located, not chosen** — measured end-to-end across all 34 cases / 11,789 numeric fields:
1 ULP into the most-amplified intermediate → max **1.151e-13** (the reordering noise floor); the
calibration defect → max **1.348e-5**. **1e-9 sits 8,696× above the floor and 13,478× below the defect**,
within 25% of the geometric centre (1.245e-9) of a four-order empty gap, biased tighter.

**Anchor mechanism proposed:** `tests/data/golden/ANCHOR.json` (digest + provenance + `supersedes` chain)
+ a dedicated `test_golden_anchor.py` + a generator that **refuses numeric-only regeneration** without
`--supersede-anchor --rationale`. Digests the `cases` subtree canonically, so `_meta` prose stays free
while no digit can move silently. Its argument — _the ratchet is caused by re-anchoring being cheaper
for small drifts than large ones; a digest pin makes every re-anchor cost the same_ — is exactly what
GD.1 is asked to stress-test.

**Approaching-tolerance:** band `[5e-10, 1e-9)` (50% — the fraction at which "one more change of this
size would breach" is literally true), **fails the build**, with a `DRIFT_LEDGER.json` escape hatch whose
entries cannot be reused for larger drift and self-expire when drift disappears.

**Relax exactly 2:** `:181`, `:217`. **Stays `==`:** `:191` determinism _(a tolerance there would hide
the very class of bug it exists to catch)_, `:225` verified-baseline _(already ~5.6e-5 via `round()`)_,
`test_metrics_parity.py`, `test_engine_bitexact_refactors.py` — the last two flagged as **AD-interaction
risks: if AD cannot keep them green that is an AD design defect, not a tolerance question.**

**Open items created by D.3:**
1. **⚠️ ORCHESTRATOR-OWNED, BLOCKING IT.2 — `MISSION_5_MANUAL_TESTING.md:91` must be rewritten** to
   monkeypatch the computed side (`amortization.amortization_payment`) rather than perturb the golden.
   As written Roger cannot observe the stated pass criterion, and it teaches editing the golden to test
   the tolerance — step one of the ratchet. **Held until GD.1's verdict settles the design**, so the
   correction is not written twice; Manual Case 2 is fine as-is.
2. **⚠️ FOR ROGER / GD.1 — the 9.4e-8 charter correction.** D.3 recommends keeping it as a **contract
   figure** bound to a reproducible recipe (`round(payment, 4)` → 1.133e-7, red at 1e-9, invisible at
   1e-6) and saying so in-repo. GD.1 may make correcting the five charter documents a **condition of
   lifting the VETO**. The *calibration logic* is sound and was reproduced; only the number's
   provenance is unsupported.
3. Backlog only, not Mission 5: `:225` uses `round()` (banker's rounding), so a value landing exactly
   on a half could flip.
4. `graphify-out/graph.json` is **stale** (`built_at_commit eb73341`, not in recent history) — used as a
   lead only, everything confirmed against files. Consistent with the standing trust boundary.

## Wave: Gate D (decision records)

| ID | Task | Agent → tier | Status | Decision record |
| --- | --- | --- | --- | --- |
| GD.1 | **VETO** — tolerance rule as values-level relaxation of the deterministic-core invariant | `principal-principles-guardian` → **fable** _(router ↑)_ | **DONE — VETO LIFTED WITH CONDITIONS C1–C7, 2026-08-31** (verified inline; orchestrator independently re-ran the guardian's own verification script as a third reproduction) | **VERDICT: LIFTED WITH CONDITIONS.** Impl-T may proceed against D.3 as written plus C1–C7. The AD sub-wave remains gated on the tolerance harness shipping green. C4(a) already discharged. Full ruling recorded above. **Dispatched ahead of Discovery closing**, deliberately: D.3 is GD.1's complete and only input, the tolerance rule is independently valuable and ships first regardless of the AD outcome, and it is the hard blocker on Impl Phase A — so reviewing it early costs nothing and unblocks the critical path. It does **not** move a wave boundary: no implementation code proceeds until the verdict lands. Prompt carries the three verified provenance findings and asks for a ruling on the unsourced 9.4e-8 figure. |
| PD.1 | Product calls: ratify 1e-9; `GENUINELY_CLOSE_MAX_FAILS`; horizon-100 / money-field / CLI dispositions | `principal-founder-proxy` → opus | **DONE — all five decided, nothing escalated** (2026-08-31) — record `docs/plans/mission-5-discovery/PD1_product_calls.md` | _Record each decision + date._ |
| PD.2 | **Half B product calls**: what makes a four-lever COMBINATION plausible (the unified gate's rule); top-3 selection policy (parsimony / within-axis magnitude / diversity weighting) | `principal-founder-proxy` → opus | **IN-PROGRESS** (dispatched 2026-08-31, tier as confirmed) | Six questions from D.4 §8, each with a default. Flagged for extra scrutiny: **R3's B=2.0 is the module's first genuinely NEW constant** — everything else reuses an existing threshold, and PD.1 kept `MAX_FAILS=3` specifically *because* it reused `synthesize_thesis`' own DECLINE boundary. Also carries the **HIGH-severity flagship-demo gap** (Q6). | _Record each decision + date. Gates the Impl Phase B design._ |
| PF.1 | Perf **go/no-go** on the AD portion (win vs finance-core blast) | `principal-performance-engineer` → opus | TODO | _Record GO / NO-GO + measured basis + date._ |

## Wave: Implementation Phase A — Tolerance (FIRST)

| ID | Task | Agent → tier | Status | Notes |
| --- | --- | --- | --- | --- |
| IT.1 | Tolerance harness + anchor-to-origin + approaching-tolerance state | `staff-python-engineer` → sonnet | BLOCKED | Needs GD.1 VETO lifted. |
| IT.2 | Tolerance RED suite (catches ~9.4e-8; passes legit 1e-9 drift; anchors to origin) | `staff-qa-test-engineer` → sonnet | BLOCKED | |
| OI.1 | Money-field lower-bound pass + RED test (negative price rejected cleanly) | `staff-python-engineer` → sonnet | BLOCKED | Founder-confirmed field list (PD.1). |
| OI.2 | Horizon `le=50`→`le=100` + RED test (100 accepted, 101 rejected) | `staff-python-engineer` → sonnet | BLOCKED | Founder-ratified (PD.1). |
| OI.3 | CLI out-of-range-horizon clean message + RED test (no traceback) | `staff-python-engineer` → sonnet | BLOCKED | |

## Wave: Implementation Phase A — AD single-lever (only if Gate D = GO)

| ID | Task | Agent → tier | Status | Notes |
| --- | --- | --- | --- | --- |
| IA.1a | **AD core** — dual-number plumbing through `engine.py` (`run_financial_model` `:638`, `_forecast_core` `:309`) + differentiating the Brent root-find in `irr.py` (`irr` `:188`, `_brent_root` `:83`) | `staff-python-engineer` → **fable** _(router split)_ | BLOCKED | On IT green + VETO lifted + PF.1 GO. Hardest item on the board; must not be relayed through a lower tier. |
| IA.1b | **7×4 Jacobian API** surface + Newton-on-guardrail single-lever search + confirm-by-rerun + bisection fallback (`recourse.py`) | `staff-python-engineer` → sonnet | BLOCKED | On IA.1a. Spec-driven execution once D.1 lands the signature. The Jacobian API is the seam Half B consumes and ADC.1 tests. |
| IA.2 | AD-vs-rerun agreement + probe-count + determinism + fallback RED suite | `staff-qa-test-engineer` → sonnet | BLOCKED | |
| IA.3 | Perf benchmark extension (probe-count + before→after vs 30 ms) | `principal-performance-engineer` → sonnet _(router: mechanical re-measurement, one tier below D.2)_ | BLOCKED | |

## Gate: Internal AD go/no-go checkpoint (HARD boundary; decision record)

| ID | Task | Agent → tier | Status | Decision record |
| --- | --- | --- | --- | --- |
| ADC.1 | **Validate the AD foundation BEFORE any optimizer code**: single-lever AD matches bisection within tolerance; IRR/Brent differentiation sound; 7×4 Jacobian API stable | orchestrator (verify inline) + `staff-python-engineer` → fable | BLOCKED | _Record **GO / NO-GO** + measured basis + date. GO → Impl Phase B. NO-GO → Half B DEFERS, mission ships Half A alone (record explicitly). A wrong top-3 must be an optimizer bug, not an AD bug._ |

## Wave: Implementation Phase B — multi-lever optimizer (only if ADC.1 = GO)

| ID | Task | Agent → tier | Status | Notes |
| --- | --- | --- | --- | --- |
| IB.1 | Constrained optimizer (Lagrangian/KKT, method from D.4) + deterministic multi-start + **unified all-four-lever combination-plausibility gate** + every-combination-confirmed-by-a-real-rerun | `staff-python-engineer` → fable | BLOCKED | On ADC.1 = GO + PD.2 decisions. The gnarly constrained-optimization math. |
| IB.2 | Two-section report output (single-lever menu + top-3 combinations; flag-don't-remove; honest-null) | `staff-report-experience-designer` → **opus** _(router ↑: report-facing copy floor)_ | BLOCKED | Both sections ship (Roger: offer both). |
| IB.3 | Optimizer RED suite (multi-start determinism; feasibility gate incl. jointly-implausible-but-individually-fine; diversity; parsimony; local-minima; every-combination-confirmed-by-rerun) | `staff-qa-test-engineer` → sonnet | BLOCKED | |

## Wave: Docs

| ID | Task | Agent → tier | Status | Notes |
| --- | --- | --- | --- | --- |
| I.4 | Docs Half A (README / finance & market READMEs / CHANGELOG) — verify vs real symbols | `staff-documentation-maintainer` → sonnet (STANDARD) | TODO | Reasoning task; NOT haiku (Mission 4 fabricated-docs lesson). |
| I.5 | Docs Half B (two-section output + unified gate in market/reports READMEs + CHANGELOG) — verify vs real symbols | `staff-documentation-maintainer` → sonnet (STANDARD) | BLOCKED | On Impl Phase B landing. NOT haiku. |

## Wave: Gate V (decision records)

| ID | Task | Agent → tier | Status | Decision record |
| --- | --- | --- | --- | --- |
| GV.1 | Code review (every answer AND every combination rerun-confirmed; no hand-inverted formula; anchor-to-origin; unified gate all-four-lever; multi-start deterministic; no decomposed basis surfaced; finance-core justified) | `staff-code-reviewer` → **opus** _(router ↑)_ | TODO | |
| GV.2 | Guardian invariant-relaxation re-check (VETO) | `principal-principles-guardian` → **fable** _(router ↑)_ | TODO | |

## Mission gate (Roger)

| Item | Status |
| --- | --- |
| Manual-testing doc fully VALIDATED by Roger (document-level box) | ✅ **DONE — 2026-09-01, 17/17 PASS.** Every case ticked with Roger's own observed output; document-level box VALIDATED; no blocking issues. |
| Merge `--no-ff` to `main` | ✅ **DONE — dc240bc** (2026-09-01) |
| Push at Roger's instruction (reconcile origin delta; never force-push) | TODO — awaiting Roger's word. `main` will be **2 commits + the merge ahead of `origin/main`** (the unpushed charter commit `87efd22` rides along). |
| Merge sha recorded | ✅ **dc240bc** |
