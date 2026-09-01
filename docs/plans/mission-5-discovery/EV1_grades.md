# EV.1 — As-built axis grades, gap severity, and whether Mission 5's premise still holds

**Mission 5, Discovery wave · `app-evaluator` · 2026-08-31**
**Branch `mission/5-adjoint-differentiation` @ `87efd22` · env `airedeal` (`/home/rtokime/anaconda3/envs/airedeal/bin/python`, 3.10.18)**
**As-built mode. No production code or tests written; the only repo write is this file.**

---

## 0. Headline

> **Composite: 84.3 / B** (Build 86.8 / B, Market 78.6 / C+) — up from the ledger's stale `B-`, and
> the four shipped missions earned it. **But the mission chartered on top of it is premised on a
> number that has been retracted, and both independent discovery memos now say so from opposite
> directions.** D.2 measured that AD-only lands at ~82 ms against a 30 ms target; D.1 measured
> `k = 4.1` and concluded that per-pair wall time is **a wash**, writing: *"If Gate D judges Mission 5
> by 'make Mission 4 faster,' the honest answer is no-go."* Two memos, two methods, one verdict.
>
> **Performance is not a high-severity gap.** Real deals measure **8.22 ms** and **7.19 ms** best
> (my own runs, this session) inside a **0.67 s** `python main.py`. The 5,000u/100y row is a synthetic
> ceiling, is currently *inside* its own 250 ms budget, and **is not gated by anything in CI** — there
> is no perf step in `.github/workflows/ci.yml` and `BUDGET_MS` has no reader outside the bench file.
>
> **The mission survives anyway — but not for the reason it was chartered.** Half B (multi-lever
> "top-3 combinations") is the single highest-value item on the board and is a **product gap, not a
> perf gap**. My recommendation: **proceed with a rewritten rationale and a resequenced scope** —
> promote Half B to *be* the mission, demote AD to an optional enabler with its own later gate, and
> spend one day first on two cheap wins that beat the entire chartered Half A on the axis it was
> chartered for.

---

## 1. Reconciliation before grading — doc claims checked against source

Per the hard constraint on this task (memo is my only repo write) I **flagged rather than fixed**.
Each item below was verified by opening the file, not by reading another doc.

| # | Claim | Where | Reality (verified) |
|---|---|---|---|
| R1 | "87 test files"; "coverage 81.87%"; "Composite grade: **B-**" | `docs/plans/ROADMAP_TRACKER.md` §1 | **148** `test_*.py` files, **3,198** collected tests, **88.37%** coverage (measured this session). Grade stamp is dated 2026-07-23, four missions ago. |
| R2 | "the **seven live** guardrails" | `CHANGELOG.md` [Unreleased]; `src/agents/chief_strategist.py:85` (`GuardrailChecks` docstring) and its `guardrail_checks` docstring; `docs/plans/MISSION_4_SPRINT_TRACKER.md:121` | **Five** are live by default. `_live_guardrails` (`src/market/recourse.py:191-202`) seeds `{dscr, spread, irr, coc}`, adds `cf_y1` because `REQUIRE_POSITIVE_CF_Y1 = True`, and *cannot* add `cf_all` because `REQUIRE_POSITIVE_CF_ALL = False` is a module constant (`chief_strategist.py:56-57`); `cap_floor` only when `market.cap_rate_floor` is set — **neither shipped sample sets it** (both `data/sample_listings/*/inputs.json` have `market.cap_rate_floor = None`). Seven is the *declared* union (`GuardrailName`, `recourse.py:79`), not the live set. `MISSION_4_DISCOVERY_SPEC.md:583` independently says "six live." Three documents, three different numbers, none of them 5. |
| R3 | "73 ms, down from 13 s" | Mission 5 brief | **Retracted.** D.2 §2 traced it to a superseded harness that priced the loop entirely on `purchase_price` and never ran the rent lever. Roger's own retraction at `docs/manual testing/MISSION_4_MANUAL_TESTING.md:513`. The charter already hedges it correctly. |
| R4 | "catches the injected rounding bug that appears at ~**9.4e-8** relative" | `MISSION_5_adjoint_differentiation.md` In-scope #1; DoD | **No provenance.** D.3 §5.1: the figure first appears in the Mission 5 charter commit itself. It is arithmetically consistent and representative of a real defect class, but it is a *contract*, not a *measurement*. |
| R5 | "**30 ms**" target | charter, ROADMAP §5 | Appears nowhere in code. No measurement has ever supported it. Correctly labelled a target, not a budget. |
| R6 | `--cov=src/tools`; `known-first-party = [..., "reports", "tools"]` | `pytest.ini`; `ruff.toml` | Neither `src/tools` nor top-level `reports`/`tools` exists. Dead config. |
| R7 | "Grant Cardone–inspired investment analysis" | `README.md:9` | Marketing framing with no anchor in code. The actual thresholds (`chief_strategist.py:39-57`) are conventional underwriting numbers — DSCR 1.20, spread 150 bps, IRR 12%, CoC 3% — each with a rationale docstring. The *thresholds* are exemplary; the *attribution* is unverifiable. |
| R8 | Manual-test Case 1 calibration procedure | `docs/manual testing/MISSION_5_MANUAL_TESTING.md:91` | D.3 §5.4: perturbing a golden number mutates the anchor, so the anchor test fires first with a *different* error. The procedure cannot produce the observation it asks Roger to make. **Blocking before IT.2 and Gate V.** |

**What verified clean.** I machine-checked every backticked `symbol()` reference in all eight
per-folder READMEs against every `def`/`class` in `src/` — **zero missing symbols**. The one-line
quickstart runs verbatim and prints exactly what `README.md:24-28` says it prints, in 0.67 s.
`CITATION.cff:4` and `pyproject.toml:7` both read `0.3.0`. Gates are green:
`pytest` (3,198 tests, 88.37%), `ruff format --check` (238 files), `ruff check`, `mypy --strict` (74 files).

---

## 2. The scorecard

Weights are the one subjective input. **Stated, and I will recompute on request.**

| Axis | Lens | Weight | Score | Grade | One-line basis |
|---|---|---:|---:|---|---|
| Engineering & Architecture | Build | 18% | **89** | **B+** | Import-time schema drift guards; one forecast implementation; identity-checked precompute; half-migrated agent layer |
| Financial-Model Correctness | Build | 18% | **85** | **B** | IRR/Brent work is A-grade; several undocumented conservative modeling biases in the headline ratios |
| Testing & CI | Build | 14% | **88** | **B+** | 3,198 tests / 88.37% / strict mypy / hash-pinned lockfile — **but zero perf gate** and a single Python version |
| Robustness of Ingestion & CV | Build | 10% | **83** | **B** | Offline-first, robots-aware, capability-declaring provider registry; robots fails open; unfenced LLM prompt (bounded blast) |
| Docs & Reproducibility | Build | 10% | **88** | **B+** | Living docs verify 100% clean and self-correct their own stamps; planning ledger + one source docstring are stale |
| Product & Portfolio Value | Market | 18% | **83** | **B** | Real, genuinely novel differentiator — **invisible in the flagship demo**, and "AI" outruns the shipped AI |
| Competitive Position | Market | 12% | **72** | **C−** | Category-leading on one axis (recourse, determinism); zero data coverage; CLI-only |

**Build subtotal (70%) = 86.8 / B.** **Market subtotal (30%) = 78.6 / C+.**
**Composite = 84.3 → B.**

Arithmetic: `89(.18) + 85(.18) + 88(.14) + 83(.10) + 88(.10) + 83(.18) + 72(.12) = 16.02 + 15.30 + 12.32 + 8.30 + 8.80 + 14.94 + 8.64 = 84.32`.

### 2.1 Engineering & Architecture — 89 / B+

**Credit where it is due, with evidence.** Three patterns here are staff-level and rare in a solo repo:

- **Schema contracts enforced at import time, not in prose.** `src/core/finance/engine.py:135-142`
  rebuilds `_year_row`'s kwarg set from `__code__.co_varnames` and raises `RuntimeError` at import if
  it diverges from `YearBreakdown`'s fields. `src/market/recourse.py:360-368` does the same for
  `_fast_unit_income` vs `UnitIncome`. These are validation-bypassing fast paths that **cannot**
  silently drift from their schema.
- **One implementation of the forecast.** `_forecast_core` (`engine.py:309-323`): `want_rows` gates
  exactly one `years.append(...)` statement and *no arithmetic whatsoever*, so the light search path
  and the full report path cannot diverge. Pinned bit-for-bit by `tests/core/finance/test_metrics_parity.py`.
  The docstring names the alternative it rejected and why.
- **Misuse made impossible rather than discouraged.** `PrecomputedIncome` carries a reference to the
  exact `IncomeModel` it was derived from and `_forecast_core` **raises** on mismatch
  (`engine.py:369-375`) — including correctly rejecting the one legitimate mismatch (insight income
  uplifts build a new `IncomeModel`).

Layering holds where it matters: network appears in exactly two files, `src/core/fetch/html_fetcher.py:15`
and `src/core/media/downloader.py:11` (grep-verified across `src/core/`). 15 `AIREAL_*` env opt-ins.
38 Pydantic v2 models with `validate_assignment=True`. `mypy --strict` clean on 74 files.

**What holds it below A−:**
- The agent layer is an acknowledged half-migration. `src/orchestrators/crew.py` imports agents then
  reaches past them into `core.cv`/`core.media`/`core.reports`; by the project's own rule
  (`ROADMAP_TRACKER.md` §3b, "an agent exists only where a model might one day enter")
  `financial_forecaster` and `chief_strategist` belong in `core/`. Recorded as "known exceptions
  under review" — an architecture rule stated but not enforced.
- `crewai` is a heavyweight dependency for a seam whose only `kickoff()` call site is
  `src/agents/crewai_components.py:396`, reachable only under `AIREAL_LLM_MODE`.
- Latent duplication the AD design already tripped over: `guardrail_checks_from_metrics` tests
  `year1_dscr` while `recourse._metric` reads `purchase_dscr` (D.1 §0). Same float today, two names.
- Dead config (R6). No `src/core/finance/README.md`, which the charter itself hedges around.

### 2.2 Financial-Model Correctness — 85 / B

**Correct against textbook, verified in source:** NOI = GOI − Σ12 opex lines (`engine.py:471-483`);
GOI = GSI × occupancy × bad-debt (`engine.py:145-150`); cap rate = NOI₁/price or explicit override
(`engine.py:392`); DSCR = NOI/DS with a `ds > 0` guard (`engine.py:494`); **CoC = Y1 CF ÷ acquisition
cash where acquisition cash = down + closing + capex reserve + upfront MIP** (`engine.py:341-343`,
`:568-570`) — the correct denominator, which a surprising number of commercial calculators get wrong.
Fraction-vs-percent discipline is consistent throughout (rates are fractions, `ge=0, le=1` on
`interest_rate` and `down_payment_rate`).

**The IRR work is the best code in the repo.** `irr()` (`irr.py:188`) does a domain-bounded bracket
search then Brent (`_brent_root`, `irr.py:83`), with a *stated structural guarantee* that the returned
root lies inside the original bracket — the guarantee the previous unbracketed Newton design could not
give. Saturating overflow (`_discount_base`, `irr.py:14`) and underflow (`_safe_div`, `irr.py:38`)
handling, each with the economic limit argument written out. An undefined IRR is surfaced as a warning
(`engine.py:625-630`) rather than silently printed. The comment at `irr.py:266-272` records the measured
reason `sum(map(truediv, …))` is used instead of `np.sum`/`math.fsum` — actual doubles, not assertion.

**Thresholds are explicit assumptions, not hidden magic** (`chief_strategist.py:39-57`): `MIN_DSCR_Y1 = 1.20`,
`MIN_SPREAD = 0.015`, `MIN_IRR_10YR = 0.12`, `MIN_COC_Y1 = 0.03`, each named, each with a rationale
docstring, and `spread_target_for()` exists specifically so the thesis and the report's Warnings
section cannot disagree about the same number.

**The gaps, in severity order:**

1. **Annual amortization cadence, undocumented bias.** `amortization_payment` (`amortization.py:28-39`)
   computes `r·P / (1 − (1+r)^−n)` on **annual** periods. Real mortgages amortize monthly. At 6% / 30y
   the annual form gives 7.266% of principal per year against 7.195% for twelve monthly payments — a
   **~1% overstatement of debt service**, which propagates into DSCR, cash flow, CoC and IRR. The
   *cadence* is disclosed ("annual cadence", `engine.py:346`); the *consequence* is not stated anywhere
   I found. Conservative direction, but it is an unflagged systematic bias in the single most-quoted ratio.
2. **`irr(cashflows) or 0.0`** (`engine.py:589`). A `None` IRR becomes a float `0.0` that a guardrail
   reads as "0% return." The CHANGELOG logs this verbatim as a "**Known open gap, not fixed**." The
   Mission 4 warning mitigates the display; the guardrail still cannot tell the two apart.
3. **`EQUITY_LTV = 0.80` (`engine.py:21`) does double duty.** It is the refi-ready LTV mark *and*
   the terminal sale-proceeds proxy (`engine.py:583`: `terminal_equity = max(0, 0.80·est_value − balance)`).
   As a cost-of-sale proxy that is a 20% haircut against a conventional 5–8%. Conservative, materially
   drives IRR and equity multiple, and carries no docstring justifying the second use.
4. **`RefinancePlan.do_refi` defaults to `True`** (`models.py:105-107`, with `year_to_refi = 5`,
   `refi_ltv = 0.75`). **Measured this session** on a minimal 2-unit config that omits the `refi` block:
   IRR **10.974%** with the default vs **9.879%** with `do_refi=False` — **+110 bps from an unstated
   default**. Mitigated: the report *does* render a "Refinance Event" card when one fires
   (`generator.py:1189`), and both shipped samples set `do_refi` explicitly. So: optimistic default,
   disclosed in output, not silent.
5. **Negative money validates.** Verified live: `FinancingTerms(purchase_price=-500000, closing_costs=-1)`
   and `OperatingExpenses(insurance=-5000)` both construct. `models.py:24-32` and `:50-62` carry no `ge=`.
   Roadmap #10; **in Mission 5 scope** as an open-item disposition.
6. **The insight→money path is unreachable on real data.** `_apply_insight_modifiers`
   (`engine.py:222-243`) triggers on the literal strings `"old roof"`, `"water stain"`,
   `"in-unit laundry"`, `"parking"`; the CV/label layer normalizes to `water_leak_suspected` etc.
   before the engine sees them. Roadmap #7, confirmed in source. The whole "AI moves the numbers"
   surface is four string triggers and four hardcoded dollar amounts, and on a real pipeline run none
   of them fire.
7. Spread is `cap_rate − note rate` (`engine.py:396`), not against the debt constant. Defensible
   simplification, undocumented.

**Golden coverage is real:** 34 bit-exact cases (`test_golden_forecasts.py:188`) plus metrics parity,
bit-exact-refactor proofs, and four IRR test files including a pinned known-crash case.

### 2.3 Testing & CI — 88 / B+

**Measured this session:** 148 `test_*.py` files, **3,198** collected tests, suite green, **88.37%**
coverage against `--cov-fail-under=80` (`pytest.ini`) and codecov project+patch 80% (`codecov.yml`).
`ruff format --check` (238 files), `ruff check`, `mypy --strict` (74 files) all clean, all three gated
in `.github/workflows/ci.yml`. CI installs from the **hash-pinned** `requirements-dev.lock` with the
rationale for that decision written into the workflow.

Real golden-number finance testing, not smoke tests: `test_golden_forecasts.py` (34 cases, `==`),
`test_metrics_parity.py`, `test_engine_bitexact_refactors.py` (verified over 214,641 random
twelve-term vectors including signed zeros and subnormals), `test_irr_brent_solver.py`,
`test_irr_edge_cases.py`, `test_irr_overflow_known_bug.py`, `test_irr_undefined_warning.py`.
Determinism asserted across ~20 files. Structural anti-regression guards exist and are the good kind:
`tests/utils.py` sentinel-model builder, `tests/integration/test_cli_reachable_paths.py`,
`tests/orchestrators/test_orchestration_result_field_guard.py`,
`tests/imports/test_heavy_sdks_stay_lazy.py`.

**The gap that matters for this mission: there is no perf gate anywhere.**
`BUDGET_MS = 250.0` (`tests/perf/bench_finance_engine.py:97`) has **no reader outside that file**
(grep-verified across `tests/`). `bench_finance_engine.py` defines **no `test_*` function** and runs
only under `if __name__ == "__main__"`. `.github/workflows/ci.yml` has **no perf step** (grep for
`perf|bench` returns nothing). **The budget Mission 5 is chartered against is defended by a human
remembering to run a script.** A gap nobody guards is not a gap the project is currently defending.

Also: single Python version and single OS (3.10, ubuntu-latest), no matrix. `codecov-action@v4` runs
with `fail_ci_if_error: false` and the token commented out, so the upload is advisory. Coverage is
thinnest exactly where hostile input lands — `src/core/media/downloader.py` 72.5%,
`src/core/normalize/address.py` 73.8%, `src/core/ingest/listing_ingest.py` 65.1%,
`src/core/intelligence/deal_fusion.py` 63.2%, `src/core/advisor/recommender.py` 61.8%.

### 2.4 Robustness of Ingestion & CV — 83 / B

Offline-first fetcher with an explicit `FetchPolicy`; robots respected when configured
(`html_fetcher.py:296-300` → `robots.py:16`); `OfflineRequiredError` on cache miss with networking
disabled (`html_fetcher.py:293`); CAPTCHA/WAF detection with strict and lenient modes
(`html_fetcher.py:331, :370`); content-addressed cache.

The provider seam is the strong part. `register_provider(name, fn, *, detects=…)`
(`amenities_defects.py:423`) makes a provider **declare the vocabulary it can detect**, and the 70/30
filename-corroboration rule means a label nothing can detect never moves a dollar. That is a
genuinely principled answer to "how do I know the AI actually looked?" — and Mission 4's fix (a
provider that *raised* no longer reports "examined and disagreed") shows the invariant is being
maintained, not just declared. AI-off degradation is the default and is byte-identical; verified,
`python main.py` runs with no keys in 0.67 s.

**Gaps:**
- **robots fails open** (`robots.py:26-28`): an unreachable or 5xx `robots.txt` is treated as allow,
  and that is not policy-configurable. Defensible as best-effort, but it is the permissive direction.
  No crawl-delay honored.
- **The LLM prompt is unfenced.** Untrusted listing text is interpolated directly into the task
  description at `crewai_components.py:378` with no delimiter or escaping. Containment is
  *architectural* rather than input-level, and it is good containment: output is parsed into a strict
  `ListingInsights`, the verdict is always deterministic (`synthesize_thesis`), origin is stamped
  `provider_kind="model"`, input truncates at 8,000 chars, and any parse failure falls back to the
  deterministic analyzer. Blast radius through `_apply_insight_modifiers` is capped at +$300 reserves,
  +$200 R&M, and +$25–50/unit — and only when `income_is_estimated`. So the exposure is small and
  bounded. It is still undocumented as a threat model, and it grows with every modifier added.
- The default `vision` provider remains a heuristic over image statistics
  (`_provider_vision_stub`, `amenities_defects.py:542`). The README is unusually honest about this.

### 2.5 Docs & Reproducibility — 88 / B+

**The quickstart works verbatim.** `python main.py` printed exactly the three lines `README.md:24-28`
claims, in 0.673 s. **Every backticked `symbol()` in all eight per-folder READMEs resolves to a real
`def`/`class` in `src/`** — machine-checked, zero misses. Each README carries a `_Last reconciled:`
stamp, and at least one of those stamps *corrects a previous stamp for naming a tree that did not
contain the content it claimed to have reconciled*. That is documentation hygiene above what this
class of project normally reaches. The CHANGELOG `[Unreleased]` retracts its own prior perf numbers
in place, distinguishes an analytic ceiling from a measurement, and logs a known open gap it chose
not to fix. Version metadata is reconciled (`CITATION.cff:4` = `pyproject.toml:7` = `0.3.0`).
License posture explicit: Research & Education (`LICENSE.md`) + separate `LICENSE-commercial.md`.

Held down by R1, R2, R6, R7 above: three stale numbers in the *first section a planner reads*, a
guardrail count that is wrong in shipped source and in the user-facing CHANGELOG, dead cov/lint
config, and an unverifiable marketing attribution in the README's second sentence.

### 2.6 Product & Portfolio Value — 83 / B

**The core idea is real and, as far as I can find, unique.** "Any ONE of these closes it," expressed
in four investor currencies, with the non-independence trap honored by *re-running the engine rather
than inverting a formula* — I searched the 2026 commercial landscape and found nobody doing this.
The design principles behind it are also right: flag-don't-remove (`_judge_plausibility`,
`recourse.py:609`), cheapest-first with a remaining-gap counter, honest-null. That is ahead of the
counterfactual-explanation literature's usual "system picks the mutable features" filter.
The deterministic/LLM split — model observes, rules decide — is a coherent architecture story and a
strong interview artifact. Solo-dev sustainable: no service, no data licensing, 0.67 s, 78.6 MB.

**Then the demo doesn't show it.** Measured this session:
`is_genuinely_close(36_kelly_moncton, horizon_years=10)` → **`False`**, and `investment_analysis.md`
— the file the one-line quickstart produces — has **no "What would have to change?" section** (its
section list runs Purchase Metrics → … → Appendix, with no recourse heading). The flagship feature of
the most recent mission is invisible in the flagship demo, and reaching it requires knowing to point
the tool at `82_champlain_dieppe`. For a portfolio piece this is the loudest single defect I found.

Also: "AI" in the product name is carried by a BYO-ONNX seam and a heuristic stub; the AI-impact
attribution machinery in the report is more elaborate than the four-string-trigger effect it
attributes, and that effect is itself unreachable on real data (§2.2 item 6). No UI (roadmap #4).
Recourse is single-lever only — which is exactly what Half B addresses.

### 2.7 Competitive Position — 72 / C−

Capability matrix, 0–5, from live search (Aug 2026):

| | Deal-analysis depth | Data / comps | **Actionable recourse** | **Determinism / auditability** | Distribution & UX | Reporting |
|---|---:|---:|---:|---:|---:|---:|
| DealCheck (free–$29/mo) | 4 | 4 | 1 | 3 | 5 | 4 |
| BiggerPockets calculators | 4 | 3 | 1 | 3 | 5 | 5 |
| Mashvisor | 3 | 5 | 1 | 2 | 4 | 3 |
| PropStream (160M+ records) | 2 | 5 | 0 | 3 | 4 | 3 |
| Zilculator | 3 | 3 | 0 | 3 | 4 | 5 |
| Stessa (free core, ~$20/mo) | 1 | 3 | 0 | 3 | 5 | 4 |
| AI-native CRE (Kolena, Archer, Blooma, Apers XL-2, ARGUS) | 5 | 5 | 2 | 2 | 4 | 5 |
| **This project** | **3** | **0** | **5** | **5** | **2** | **4** |

**Tier: not competitive as a product; category-leading on one axis.** It is below every named tool on
data and distribution, and below the AI-native CRE entrants on modeling depth (no multi-tranche debt,
no waterfall, no lease-level DCF, no development pro forma, annual cadence). The best any competitor
manages on recourse is a **dynamic multi-variable sensitivity table** — which answers "what happens
if" and not "what would have to change, and does it actually flip." It is also the only tool in the
set whose verdict is provably not model-authored and whose numbers are pinned by a bit-exact golden.

A data score of 0 is the disqualifier: the `market` block is user-supplied, and both shipped samples'
own `market.notes` say *"Derived from this file and the engine's own Y1 output, not external market data."*

---

## 3. The sharpened question

### 3.1 Is performance actually a high-severity gap? — **No. Low as a user gap; medium as a credibility proxy.**

| Evidence | Source |
|---|---|
| `36_kelly_moncton` recourse: **best 8.22 ms / median 8.51 ms** | measured by me this session, n=9 |
| `82_champlain_dieppe` recourse: **best 7.19 ms / median 7.24 ms** | measured by me this session, n=9 |
| `python main.py` end-to-end: **0.673 s** | measured this session (D.2: 0.68–0.86 s, 78.6 MB peak RSS) |
| 5,000u/100y: 175–198 ms best against `BUDGET_MS = 250.0` — **inside budget** | D.2 §1, orchestrator-reproduced |
| Perf is **not gated anywhere** in CI | `.github/workflows/ci.yml` (no perf step); `BUDGET_MS` has no reader outside `bench_finance_engine.py:97` |

**The 5,000u/100y row is a synthetic institutional stress ceiling, not a user-facing gap.** No user
experiences it; both real deals are ~25× under it; it is currently passing its own budget; and nothing
automated defends that budget. It *is* a legitimate proxy for two things — headroom (a scaling story
for an institutional pitch) and engineering credibility (a portfolio piece that can say "5,000 units ×
100 years" has said something). But 180 ms already tells that story, and **119 ms tells it better for
free** (D.2 §3.3, orchestrator-reproduced ON/OFF/ON: 183.5 → 120.7 → 117.7 → 179.6 ms).

Severity: **LOW as a user gap. MEDIUM as unclaimed leverage** — 36% of the row is garbage collection
recoverable with zero finance-core diff, and nobody is holding the line with a test.

### 3.2 If performance is the gap, is AD the right intervention? — **No. Clear no, from two independent directions.**

The two discovery memos reached the same verdict by different methods, which is the strongest form
this evidence could take:

- **D.2 (perf attribution, measured):** AD-only projects to **~82 ms** (75–89 across k = 2…4) —
  **2.7× over the 30 ms target**, and **~70 ms even at a free dual pass (k = 1)**, because 44 ms of it
  is 12 surviving rent perturbations AD does not remove. 74.5% of the row is `_perturb` rebuilding
  5,000 `UnitIncome` models 39 times; **AD does not touch that term.**
- **D.1 (AD design, measured):** `k = 4.1` for the unrolled `Dual4` full Jacobian — the *top* of D.2's
  parametrized band. D.1's own projection: **probe count drops ~3× (the charter's goal, met) but
  per-pair wall time is 0.8–1.3× — a wash.** Its own words: *"If Gate D judges Mission 5 by 'make
  Mission 4 faster,' the honest answer is no-go: bisection is already fast enough and maximally
  dumb-auditable."*

**Two cheaper interventions dominate the term AD does not touch:**

| Intervention | Result | Finance-core diff | Touches the bit-exact golden? |
|---|---|---|---|
| GC threshold tune | **119 ms, measured** (from 183–193) | **zero** | **no** |
| O(1) rent aggregate, search path only | ~44–49 ms, projected | `_perturb` + `PrecomputedIncome` | no (shipped confirms stay exact) |
| **AD** | ~82 ms alone; **~14 ms marginal** after the rent fix | `engine.py`, `amortization.py`, a new scalar type, refi-block restructure | **yes — that is why the tolerance rule exists** |

**On D.2's flip-condition (b) — "can AD get d/d(rent) without materialising a perturbed rent roll?"
The answer is no, and it is readable in the code.** Forward-mode AD gives you the slope *at the
current point*; Newton then has to **evaluate** the model at the proposed point, and evaluating at a
perturbed rent still requires a rent roll unless `_perturb`'s rent path is independently made O(1)
(`_annual_income`, `engine.py:145-150`, reduces over `income.units`). AD and the rent-aggregate fix
are **substitutes competing for the same dominant term, not complements** — and the cheap one wins
the bigger share. D.2's GO-flip condition does not fire.

**Verdict: AD as a performance intervention is dead on measurement.** Its ~14 ms marginal win —
7% of the original baseline, on a row no user touches, which is already inside its budget — does not
buy opening the most protected directory in the repo, relaxing a values-level invariant, and
differentiating a bracketed Brent root-find that the charter itself names as the hardest part.

**One thing the charter should also absorb: "the tolerance rule is independently valuable" is doing
more work than the evidence supports.** D.3 §1.6's own case-FOR is entirely AD-conditional. And
there is an unanswered prior question: D.1 §1 states the AD **primal is bit-identical by
construction**, and the confirm-by-rerun contract means every shipped number comes from an
un-differentiated `run_financial_model`. **So it is not established that AD moves the 34-case golden
at all.** That should be answered *before* a values-level invariant is relaxed — relaxing an
invariant to accommodate a drift nobody has demonstrated is the wrong order. (The tolerance rule does
have real standing value as reviewability infrastructure for the integer-cents mission and for any
non-bit-exact aggregate on the *confirming* path. That is a good argument. It is not the one made.)

### 3.3 Which axis does Half B move, and by how much? — **This is where the real severity is.**

**Half B is a product/capability gap, and it is the highest-value single item on the board.**

Today `_search_one` (`recourse.py:663`) answers only "any ONE of these closes it," one lever per row.
An investor who can move two levers a little — rather than one lever a lot — gets no answer, and the
report cannot tell them whether such a bundle exists. That is a capability hole, not a latency hole.

Projected axis movement:
- **Product & Portfolio Value: 83 → ~87.** The differentiator goes from "one lever" to "one lever OR a
  realistic bundle," which is the shape an actual negotiation takes.
- **Competitive Position: 72 → ~76.** It widens the *one* column where the project already scores 5/5
  and where the 2026 AI-native CRE tools top out at 2/5 with sensitivity tables. Widening your only
  moat is better leverage than narrowing someone else's.
- Composite effect ≈ **+0.9**, the largest single-item move available.

**And Half B genuinely wants a Jacobian.** D.1 measured it: Half B's 4-lever gradient costs 8
central-FD probes ≈ 0.34 ms with step-size fragility, versus **1 dual pass ≈ 0.17 ms, exact**. That
is 2× *and* it removes a class of failure where finite-difference step-size error compounds into a
reported dollar figure. **That is an engineering-quality argument and it is legitimate — it is just
not the argument the charter makes.**

**Two honest caveats on Half B:**

1. **The hardest part of Half B has no AD content at all.** Scope item #14 — the unified all-four-lever
   *joint* plausibility gate — is the real engineering and the real product decision.
   `_judge_plausibility` (`recourse.py:609`) judges one lever at a time; `rejector.py` has **no rent or
   opex axis** (its cross-axis rules are `rejector.py:23, 38-41, 44-64`), which is precisely why
   Mission 4 had to bolt on `RATE_MAGNITUDE_THRESHOLD` (`recourse.py:130`) and
   `_MAGNITUDE_RELATIVE_THRESHOLD` (`recourse.py:120`). Deciding what makes a *combination* plausible
   is a founder call that AD neither helps nor hinders.
2. **Half B can ship a defensible v1 on finite differences.** 0.34 ms vs 0.17 ms per gradient, on a
   **7–9 ms** analysis, is 2.4% of one deal. The exactness argument is about *correctness of the
   reported slope*, not speed, and it should be argued on those terms — with evidence from a shipped
   FD optimizer that the step-size fragility actually bites.

### 3.4 Is there a higher-leverage mission right now?

Three things outrank the *chartered* Half A. None outranks Half B.

- **The two cheap wins (below, L1 + L2) outrank the entire chartered Half A** on the axis Half A was
  chartered for. One day of work versus a high-blast mission, for a better measured number.
- **Roadmap #4, Streamlit UI**, is the single biggest move available on Product + Competitive — the
  two weakest axes, 30% of the composite between them — and it reads existing JSON artifacts, so its
  blast on the deterministic core is near-zero. Distribution/UX is where this project scores 2/5
  against a field that scores 4–5.
- **Roadmap #13, integer-cents**, has a **sequencing conflict with Mission 5 that should be surfaced
  to Roger explicitly.** Integer-cents makes summation order-independent and money arithmetic exact —
  which *removes the reason the tolerance band exists*. Relaxing a values-level invariant in Mission 5
  to accommodate FP reordering, and then deleting FP reordering in the successor mission, is backwards.
  Either do integer-cents first, or accept that the tolerance rule is transitional and say so in the
  charter.

---

## 4. Severity-ranked gap list

Legend for the last column: **✅ addresses** · **◐ partially** · **✗ does not touch** · **⚠ may worsen**.

| # | Gap | Sev | Evidence (`path:line`) | Mission 5 as chartered |
|---|---|---|---|---|
| G1 | **Flagship demo does not show the flagship feature.** `is_genuinely_close(36_kelly_moncton)` = `False`; the quickstart's `investment_analysis.md` has no recourse section | **HIGH** | measured this session; `investment_analysis.md` section list; `recourse.py:213` | **⚠** Half B adds a *second* section to a report the demo never renders |
| G2 | **Recourse is single-lever only** — no answer for an investor who can move two levers a little | **HIGH** | `recourse.py:663` (`_search_one`), `:609` (`_judge_plausibility`) | **✅** Half B. This is the mission's real value |
| G3 | **Zero market/comps data.** Every market number is user-supplied | **HIGH** (Competitive) | both `data/sample_listings/*/inputs.json` `market.notes`; roadmap #5 | **✗** |
| G4 | **No automated perf gate.** The budget this mission is chartered against is defended by a human running a script | **MED-HIGH** | `bench_finance_engine.py:97` has no reader outside the file; no `test_*` in it; no perf step in `ci.yml` | **◐** scope #7 records a measurement; a measurement is not a gate |
| G5 | **Three unverified/retracted numbers load-bearing in the mission narrative**: 73 ms (retracted), 9.4e-8 (no provenance), 30 ms (never measured) | **MED-HIGH** for decision quality | D.2 §2; D.3 §5.1; grep for "30 ms" in code = nothing | **◐** Discovery has now reconciled all three — which is exactly what Discovery is for |
| G6 | **Annual amortization cadence** → ~1% overstatement of debt service into DSCR/CF/CoC/IRR, undocumented consequence | **MED** | `amortization.py:28-39`; cadence disclosed at `engine.py:346`, bias is not | **✗** |
| G7 | **`irr(...) or 0.0`** conflates "undefined" with "0% return" for a guardrail | **MED** | `engine.py:589`; CHANGELOG logs it as a known open gap | **✗** |
| G8 | **Negative money validates** — `purchase_price=-500000`, `insurance=-5000` both construct | **MED** | verified live; `models.py:24-32, :50-62` (no `ge=`) | **✅** open-item disposition, scope #8 |
| G9 | **Insight→money path unreachable on real data** — engine triggers on pre-normalization strings the CV layer has already rewritten | **MED** | `engine.py:222-243`; roadmap #7 | **✗** |
| G10 | **`do_refi` defaults `True`** → +110 bps IRR on a config that omits the block (measured 10.974% vs 9.879%) | **MED** | `models.py:105-107`; measured this session; disclosed by `generator.py:1189` | **✗** |
| G11 | **`EQUITY_LTV = 0.80` does double duty** as refi mark and terminal sale-proceeds proxy; a 20% haircut with no stated justification | **MED** | `engine.py:21`, `:583` | **✗** |
| G12 | **Doc drift: "seven live guardrails" is five** — wrong in shipped source and in the user-facing CHANGELOG; three docs give three different numbers | **MED** | `recourse.py:191-202` vs `chief_strategist.py:56-57, :85`, CHANGELOG, `MISSION_4_SPRINT_TRACKER.md:121`, `MISSION_4_DISCOVERY_SPEC.md:583` | **◐** scope #10 doc reconciliation would likely catch it |
| G13 | **Manual-test Case 1 cannot produce its own stated observation** — perturbing the golden fires the anchor test first | **MED** (blocks Gate V as written) | `MISSION_5_MANUAL_TESTING.md:91`; D.3 §5.4 | **◐** must be fixed before IT.2 |
| G14 | **No UI.** Distribution/UX 2/5 against a field at 4–5 | **MED** | roadmap #4 | **✗** |
| G15 | **36% of the ceiling row is GC**, recoverable with a threshold tweak and zero finance-core diff | **MED** as unclaimed leverage | D.2 §3.3; orchestrator-reproduced 183.5 → 120.7 → 117.7 → 179.6 ms | **✗** — the charter does not consider it |
| G16 | **Half-migrated agent layer** — the project's own §3b rule is stated but not enforced | **LOW-MED** | `ROADMAP_TRACKER.md` §3b; `crew.py` reaches past agents into `core.*` | **✗** |
| G17 | **Single-version, single-OS CI**; codecov upload advisory (`fail_ci_if_error: false`, token commented out) | **LOW-MED** | `.github/workflows/ci.yml` | **✗** |
| G18 | **robots fails open** (unreachable robots.txt ⇒ allow, not configurable); **LLM prompt unfenced** (blast bounded to ±$300/±$200/±$25–50) | **LOW** | `robots.py:26-28`; `crewai_components.py:378` | **✗** |
| G19 | **Dead config**: `pytest.ini --cov=src/tools`, `ruff.toml known-first-party` names nonexistent packages | **LOW** | `pytest.ini`, `ruff.toml` | **✗** |

### Cross-cutting themes (flagged by ≥2 axes — these are priorities, not reviewer taste)

- **T1 — The perf premise is dead, and two independent memos say so.** D.2 by attribution, D.1 by
  measuring `k = 4.1` and finding the wall time a wash. When the perf specialist and the AD designer
  independently reach "no-go on the perf case," that is not a close call.
- **T2 — The one true differentiator is both under-shipped and under-shown.** G1 (invisible in the
  demo) + G2 (single-lever only) + the Competitive matrix's lone 5/5 column are the same root, hit
  from three axes. **Fix the showing before deepening the shipping** — a bundle nobody sees is worth
  no more than a single lever nobody sees.
- **T3 — The project measures beautifully and gates nothing on the measurement.** No perf gate (G4),
  advisory coverage upload, single-version CI (G17). The rigor is real; the *enforcement* of the
  rigor stops at correctness and does not extend to performance.
- **T4 — Systematic, undocumented conservative modeling defaults.** Annual amortization (G6), the
  0.80 terminal-equity proxy (G11), `do_refi=True` (G10), spread vs note rate. Each individually
  small and each in the safe direction; collectively an unstated bias in the exact numbers the
  product exists to produce. For a tool whose pitch is auditability, this is the least-audited part.

### Leverage-ordered fixes

| | Fix | Cost | Closes | Axes moved |
|---|---|---|---|---|
| **L1** | **Make the quickstart show recourse** — default to a near-miss bundle, or add the second command to Quick Start, or ship a third sample | hours | G1 | Product, Competitive |
| **L2** | **The cheap perf slice + a real CI perf gate** — GC threshold tune (measured 119 ms, zero finance-core diff) + O(1) rent aggregate on the search path (proj. 44–49 ms) + a best-of-N pytest assertion on `BUDGET_MS` **and** the two real-deal rows | ~1 day | G4, G15 | Testing/CI, Engineering, Product(credibility) — **and it closes the perf story Mission 5 was chartered for, at ~5% of its cost** |
| **L3** | **Half B on finite differences first; AD second (or never)** — ship the multi-lever optimizer and the unified joint plausibility gate, which is the actual hard part and has no AD content | the mission | G2 | Product, Competitive, Market, Reports |
| **L4** | **The undocumented-defaults pass** — state the amortization-cadence bias, justify or split `EQUITY_LTV`'s second use, reconsider `do_refi=True`, add money-field lower bounds | ~1 day | G6, G8, G10, G11, T4 | Finance, Docs |
| **L5** | **Doc reconciliation** — the guardrail count in source + CHANGELOG, the three unverified figures, ROADMAP §1's stale numbers, the manual-test Case 1 recipe, dead config | hours | G5, G12, G13, G19 | Docs, Testing/CI |
| **L6** | **Sequence integer-cents (#13) against the tolerance rule, deliberately** — exact money arithmetic deletes the reason the tolerance band exists | charter-level decision | — | Finance, Schemas |

---

## 5. Verdict

**Not "proceed as chartered." Not "abandon." → Proceed with a rewritten rationale and a resequenced
scope, and do two cheap things first.**

1. **First, before any AD work (≈1 day):** L1 + L2. This *closes the perf gap Mission 5 was chartered
   to close*, measured, with zero finance-core diff on the GC half — and finally puts a test behind
   the budget. Retire "30 ms," or re-adopt it as a budget only after the cheap work lands and the real
   number is known. Keep `BUDGET_MS = 250.0` as the gate; D.2 is right that a 30 ms gate on a row with
   ±12% process-to-process spread would be a flake generator.
2. **Rewrite the honest rationale.** Mission 5 is not a speed mission. It is **"multi-lever actionable
   recourse."** Half B *is* the mission; Half A is optional infrastructure for it. Strike 73 ms and
   strike the claim that AD is "the remaining credible path to 30 ms" — it is not, at any measured `k`.
   State the AD case as what D.1 actually found: exact, named, degradation-honest slopes for a
   multi-lever optimizer, worth ~14 ms and one class of finite-difference failure, against opening the
   finance core.
3. **Run Half B first, on finite differences,** with the unified all-four-lever joint plausibility gate
   as the centre of the mission. Ship the two-section report. That is the product value, and none of
   it depends on the premise that moved.
4. **AD becomes a follow-on**, chartered on Half B's *measured* FD pain, sequenced alongside or after
   integer-cents. **The tolerance rule ships with AD, not before it** — and only after someone answers
   the prior question: given a bit-identical primal (D.1 §1) and the confirm-by-rerun contract, does AD
   move the 34-case golden at all? Relaxing a values-level invariant to accommodate a drift nobody has
   demonstrated is the wrong order of operations.

**If Roger wants one sentence:** the charter's premise moved, but the mission survives it — the value
was always in Half B, so promote Half B to *be* the mission, demote AD to an optional enabler with its
own later gate, and spend one day first on the two cheap wins (a demo that shows the feature, and a
GC/rent-aggregate perf slice with a real CI gate) that together beat the entire chartered Half A on the
one axis it was chartered for.

---

## Appendix — what I measured myself

```bash
source /home/rtokime/anaconda3/etc/profile.d/conda.sh && conda activate airedeal
# gates
pytest -q                                        # green; 3,198 tests; 88.37% (gate 80%)
ruff format --check .                            # 238 files already formatted
ruff check .                                     # All checks passed!
mypy --config-file mypy.ini src main.py          # Success: no issues found in 74 source files
time python main.py                              # 0.673 s; output matches README:24-28 verbatim
# real-deal recourse cost, n=9 each
#   36_kelly_moncton   best 8.22 ms / median 8.51 ms  (is_genuinely_close = False)
#   82_champlain_dieppe best 7.19 ms / median 7.24 ms  (is_genuinely_close = True)
# negative money accepted: FinancingTerms(purchase_price=-500000, closing_costs=-1) constructs
# do_refi default True on a minimal config: IRR 10.974% vs 9.879% with do_refi=False (+110 bps)
# README symbol audit: every backticked symbol() in all 8 src/**/README.md resolves in src/ — 0 misses
```

Weights used: Engineering 18 · Finance 18 · Testing/CI 14 · Ingestion/CV 10 · Docs 10 · Product 18 ·
Competitive 12. **Say the word and I will recompute on any reweighting** — the composite is not
sensitive enough to flip the verdict in §5 under any plausible reweighting, because the §3 findings
are measurements, not weights.
