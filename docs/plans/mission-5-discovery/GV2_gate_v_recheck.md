# GV.2 — Gate V guardian re-check: Mission 5 as-built

**Mission 5 · Gate V · principles guardian, VETO authority · routed fable (diff touches
`src/core/finance/` and `src/schemas/models.py`)**
**Tree reviewed:** `mission/5-forward-mode-differentiation`, working tree (nothing committed),
26 files changed, +4,289/−426.
**Method:** every condition below verified against shipped code first-hand, not against any
implementer or orchestrator report; the load-bearing suites re-run in `airedeal`
(`/home/rtokime/anaconda3/envs/airedeal/bin/python`): **385 passed, 1 skipped** across
`test_partition.py`, `test_income_shift.py`, `test_golden_forecasts.py`, `test_golden_anchor.py`,
`test_golden_tolerance_walls.py`, `test_golden_tolerance_helper.py`, `test_metrics_parity.py`,
`test_engine_bitexact_refactors.py`, `test_breakeven.py`. The GD3 shape rule was live-fired in
this review (a synthetic `vacancy_ask` model), and it killed the mutant with the escalation
message intact.

---

## VERDICT: CLEARED-WITH-CONDITIONS

Three documentation-only corrections (GV2-M1..M3 below). None touches code, none requires
guardian re-review; each is a one-to-three-line doc edit verifiable by grep before the founder's
mission gate. Everything load-bearing — both prior rulings as built, the aggregate-shift seam,
the three-outcome contract, the report copy, and the rewritten rationale — is verified compliant.

---

## 1. GD1 (tolerance relaxation, VETO LIFTED WITH CONDITIONS) — per-condition verification

| Cond. | Status | Evidence (verified first-hand this turn) |
| --- | --- | --- |
| **C1** — determinism boundary frozen | **VERIFIED AGAINST CODE** | `git diff` vs `87efd22`: `test_metrics_parity.py` and `test_engine_bitexact_refactors.py` have **zero diff**. `test_determinism_repeated_calls_are_identical` (`test_golden_forecasts.py:232`) stays `==` with the required exclusion docstring ("Stays `==`, forever... automatic escalation... citing GD1 condition C1", `:236-248`). `test_sample_deal_verified_baseline_numbers` (`:292-306`) assertion-for-assertion identical, with the C1/D.3 §6.2 exclusion rationale recorded at `:262-266`. |
| **C2** — cumulative-drift budget mandatory | **VERIFIED AGAINST CODE** | `CUMULATIVE_DRIFT_BUDGET = 1e-8` (`golden_tolerance.py:159`); `cumulative_drift` walks the full `supersedes` chain (`:640-656`); `test_golden_anchor.py::test_anchor_cumulative_drift_is_within_budget` (`:100-116`) enforces it, and its failure message states verbatim: *"This does NOT mean raise the budget. It means the numbers must be independently re-verified by a human."* The non-decaying element is real and executable. |
| **C3** — supersession discipline | **VERIFIED AGAINST CODE** | `generate_golden_forecasts.py:243-248` hard-errors on `--supersede-anchor` without `--rationale` AND without `--approved-by`; the numeric-only refusal gate and the structural-must-not-co-carry-numeric-drift refusal both exist (`:39-40`, `_refusal_message` `:189-212`, citing C3 by name); anchor records require non-empty `approved_by`/`rationale` (`test_golden_anchor.py:73-74`). No supersession has yet occurred (single-node chain, `supersedes: null`, pinned by `test_anchor_baseline_is_the_single_committed_golden_version`). |
| **C4(a)** — manual-test Case 1 corrected | **VERIFIED** | `MISSION_5_MANUAL_TESTING.md:93-104`: both steps moved to computed-side perturbation (monkeypatch `amortization_payment`), with a dated orchestrator correction block explaining *why* golden-side perturbation was the wrong habit. |
| **C4(b)** — four charter docs corrected | **VERIFIED, one residual (GV2-M2)** | Charter `:169-178` carries the dated correction block ("contract calibration constant... NOT a prior measurement"); `HANDOFF:174-177`, `ROADMAP_TRACKER:132/305-306/377-380`, and the manual doc `:130-135` all corrected. Residual: the charter's Definition of Done (`:376`) still reads "the ~9.4e-8 **injected rounding bug**" without a marker — covered by the same document's correction block, but the phrase should not survive into the mission's own DoD checklist. |
| **C4(c)** — contract status + recipe in-repo | **VERIFIED** | `golden_tolerance.py:116-130` records the full contract status (`git log --all -S"9.4e-8"` → one commit), the `round(payment, 4)` recipe, and the measured 1.1325e-7 signature; the ceiling test (`test_golden_tolerance_walls.py:129-146`) executes the recipe and additionally proves the class invisible at 1e-6. |
| **C5** — ledger anti-over-provisioning | **VERIFIED AGAINST CODE** | `evaluate_ledger_entry` (`golden_tolerance.py:459-508`) rejects `max_rel >= REL_TOL` (OUT_OF_RANGE, regardless of measurement), `max_rel > measured × 1.10` (OVER_PROVISIONED), and drift fallen below the band (STALE). All three RED tests exist and pass (`test_golden_tolerance_helper.py:237-270`), plus UNDERCOVERED and UNKNOWN_FIELD beyond what C5 asked. |
| **C6** — walls + boundary executable | **VERIFIED AGAINST CODE** | `test_golden_tolerance_walls.py` re-derives the 1-ULP floor (`<1e-11`, below `APPROACHING_LO`) and the `round(payment,4)` ceiling (`>1e-7`, invisible at 1e-6) end-to-end through `run_financial_model` over all 34 cases; `test_dollar_blindness_boundary_on_the_shipped_deal` asserts `REL_TOL × max(|shipped-deal field|) < 0.005` with a founder-decision failure message, and the measured $0.000533 figure is pinned separately. §6.3 prohibitions (no `abs_tol`, no `isclose`, no per-field override, no runtime configurability) are in `golden_tolerance.py`'s docstring (`:53-84`) and true of the code. |
| **C7** — harness docstring truth + renames | **VERIFIED** | The "BIT-EXACT, NOT APPROXIMATE" section is replaced by a dated "TOLERANCE RULE — 2026-08-31, Mission 5, IT.1" record in the regeneration-record format (`test_golden_forecasts.py:12-54`); both relaxed tests renamed to `..._within_tolerance` with the rename rationale in their own docstrings (`:214-221`, `:277-280`). |

**GD1 finding (GV2-M1):** two shipped docstrings — `test_golden_tolerance_walls.py` (scope note,
~`:25-29`) and `test_golden_anchor.py` (`test_editing_the_golden_trips_the_anchor_test_first`
docstring) — refer readers to `tests/core/finance/test_golden_tolerance_calibration.py`, **which
does not exist in the tree**. The calibration recipes were in fact discharged inside the walls
file itself (the ceiling test and the direct 9.4e-8 injection in
`test_floor_and_ceiling_bracket_rel_tol_with_wide_margin`). The substance is present; the
reference is a false claim about where it lives — exactly the defect class C4 exists to prevent,
in miniature. Correct both references to point at the walls file (or ship the file under that
name); do not leave a docstring naming a file that is not there.

## 2. GD3 (lever/assumption partition, ADOPTED-WITH-CONDITIONS) — per-condition verification

| Cond. | Status | Evidence |
| --- | --- | --- |
| **C1** — single source of truth + drift guards | **VERIFIED AGAINST CODE** | `src/core/finance/partition.py` declares `INVESTOR_LEVERS` (closed four), `MODEL_ASSUMPTIONS` (all ten guardian-named paths present, pinned by `test_model_assumptions_covers_the_guardian_named_minimum`), `LEVER_SEED_TARGETS` (opex image derived **live** from `OperatingExpenses.model_fields`, not a fifth copy), and the invariant text verbatim. Import-time `RuntimeError` guards: partition self-check (`:142-147`, `:197-215`, `:260`), `jacobian.py:153-172` (SeedTarget universe == `LEVER_IMAGE`, plus `assert_disjoint_from_assumptions` over the seed universe and `_CoreOverrides` fields), `recourse.py:115-124` (`LeverName` == `INVESTOR_LEVERS`). |
| **C2** — YAGNI retired | **VERIFIED** | `grep -rn YAGNI src/` → two hits: `partition.py:29` (quoting the retired rationale in order to reject it) and `engine.py:306` (defers an unbuilt dual-shift extension — a genuine scope note, immediately followed at `:309-317` by "THE ABSENCE OF ANY ASSUMPTION FIELD HERE IS NOT A SCOPE CHOICE — it is THE LEVER/ASSUMPTION PARTITION (GD3)"). GD3 cited as the primary closure rationale at all three mandated sites (jacobian `:133-137`, `_CoreOverrides` docstring, recourse module docstring `:7-12`). |
| **C3** — RED tests naming the invariant | **VERIFIED + RUN** | `test_partition.py`: seeding any assumption path raises (`test_seeding_a_model_assumption_path_raises`, parametrized); disjointness failure message names FOUNDER PROXY ESCALATION CITING GD3 (`test_disjointness_assertion_names_founder_proxy_and_gd3`); `RecourseLever.lever` Literal pinned to `INVESTOR_LEVERS` (live-fired this review: `('rent_per_unit_month', 'purchase_price', 'interest_rate', 'annual_opex')`). |
| **C4** — documented where contributors read | **VERIFIED** | `src/schemas/README.md:79-104` ("GD3 — the lever/assumption partition") and `src/market/README.md:80-95` each carry the partition, the two readings, and the shape rule. |
| **C5** — terminal-model bar recorded + enforced | **VERIFIED AGAINST CODE** | `BARRED_ASSUMPTION_AXES = {market.cap_rate_drift, refi.exit_cap_rate, horizon_years}` (`partition.py:176`) with the full four-step prerequisite chain in the docstring (`:61-67`, "no rationale string waives any of them"); enforced by `test_no_seed_target_exists_for_any_barred_axis`, `test_no_core_overrides_field_exists_for_any_barred_axis`, `test_no_breakeven_surface_exists_for_any_barred_axis`. **Barred axes held as built:** no seed target, no `_CoreOverrides` field, and `breakeven.py` scopes to occupancy / rent growth / expense growth only, importing `BARRED_ASSUMPTION_AXES` to exclude the rest. |
| **C6** — combination search scope pinned | **VERIFIED** | The Half-B search draws its candidate space exclusively from `partition.investor_lever_combinations` (`recourse.py:1065-1068`); RED test `test_investor_lever_combinations_is_red_if_an_assumption_axis_is_injected` exists and passes. |
| **C7** — escalation clause in-repo | **VERIFIED** | `partition.py:77-83` carries the Ruling-4 sign-off rules with the load-bearing sentence verbatim: "extension of `INVESTOR_LEVERS` is a Founder Proxy escalation citing GD3; a rationale string is not a clearance." The same sentence rides every guard's failure message. |

**GD3 shape rule, as shipped:** `AssumptionBreakeven` (`models.py:1624`) carries exactly the
breakeven reading — `assumed_value`, `adverse_direction`, `searched_to`, `outcome`,
`breakeven_value`, `margin`, `metric_at_breakeven`, `bar`, `resolution`, `probes_used` — no
ask/delta/target field anywhere; `assert_breakeven_shape` is called against both breakeven types
at `breakeven.py:150-151` import time. The harmful sentence has no field to live in. This is the
invariant carried by shape, exactly as ruled.

**GD3 finding (GV2-M3):** `partition.py:118-121` still says the recourse-side guard is "out of
this module's edit boundary this session — see the handoff report for the exact guard snippet
`recourse.py` should carry." The guard **has since shipped** (`recourse.py:115-124`). The comment
now understates the enforcement that exists. Update it to state the guard is live.

## 3. RULING — the aggregate-shift seam (`ShiftedIncome` / `shift_income`): **APPROVED. The invariant is genuinely no weaker; on one axis it is strictly stronger.**

This is the mission's highest-blast change and the one surface I had not reviewed. I did not
grade the implementer's "provenance, not permission" framing; I tried to break it. Findings:

**The structural claim checks out against the source, not the report.**
`run_financial_model` (`engine.py:902-908`) has exactly
`(fi, *, horizon_years, insights, precomputed_income)` — **no shift parameter**. The earlier
grep hit at `:941` is `forecast_metrics`, the search path. So a shifted aggregate is
*type-and-signature incapable* of producing the number on the page — not forbidden, absent.
`_forecast_core` hard-errors on `income_shift` with `want_rows=True` (`:528`), with
`precomputed_income` (`:523`), and with `_overrides` (`:513`); each refusal is pinned by
`test_income_shift.py` (`test_run_financial_model_structurally_refuses_shifts`,
`test_forecast_core_refuses_shift_with_want_rows`,
`test_forecast_core_refuses_shift_alongside_overrides`).

**The attacks I constructed, and where each dies:**

1. *Stale base (different `IncomeModel`)* — dies at the engine's own `is` re-check
   (`engine.py:584-590`), the identical check the pre-existing `PrecomputedIncome` contract uses.
   Pinned RED (`test_shift_from_a_different_income_model_is_a_hard_error`).
2. *Double application (shift + materialised perturbation)* — dies at the same identity check:
   `_perturb`'s rent path builds a NEW `IncomeModel`, so a shift built over the baseline cannot
   accompany it. Additionally impossible by type: `shift_income` accepts only a
   `PrecomputedIncome`, so shifts cannot chain, and each `ShiftedIncome` recomputes
   `gsi = base.gsi_annual + 12·N·t` from the base — no accumulation state exists to go stale.
   Pinned RED (`test_double_application_on_a_materialised_perturbation_is_a_hard_error`).
3. *Insight-adjusted income + shift* — insights build a new `IncomeModel` inside the engine, so
   the identity check fails loudly; same fail-closed posture as the unshifted precompute.
4. *Units-list reassignment/resize (same object)* — identity cannot see it; the seam's
   `num_units` use-time re-check catches it
   (`test_in_place_units_mutation_is_a_hard_error`). **Note: the plain `PrecomputedIncome` path
   has no such check — on this class the seam is strictly stronger than the mechanism it
   extends.**
5. *Same-length in-place element mutation* (`income.units[0].rent_month = X` after precompute)
   — invisible to both identity and unit count. **This residual is real, but it is not new:** it
   is byte-for-byte the residual of the already-shipped, already-guardian-reviewed
   `PrecomputedIncome` (identity is "the strongest form available", per its own docstring, and
   element mutation defeats identity there identically). Schema models are
   `validate_assignment=True`, not frozen; in-repo, `recourse.py` deep-copies and never mutates
   (`:432`), so no shipped caller can trigger it. The seam inherits this exposure; it does not
   widen it. No condition — recorded here so a future frozen-models proposal knows what it buys.

**The numeric concession is inside the already-ruled framework.** The shift differs from a
materialised probe only in summation order; measured worst drift 3.5–4.7e-14 at 5,000 units
(pinned at both scales by `test_income_shift.py`, with t=0 pinned **bit-exact**) — below the
1.15e-13 reordering noise floor the walls suite re-derives, ~4 orders below `APPROACHING_LO`.
This is precisely the legitimate-reassociation class GD1's tolerance rule was measured against;
no widening was requested and none occurred. And the drift can only ever exist on *search*
probes: the shipped number's provenance is a materialised roll through the full engine
(`recourse.py:812-814`), with even the defensive fallback re-derived from a full run
(`:824-826`), and the shipped `RecourseAnalysis` verified byte-identical between shift and
forced-materialised paths.

**Ruling:** the documented invariant — *"a stale or mismatched precompute is a silently-wrong
dollar figure... a hard error, not a quiet fallback"* — is preserved at full strength, enforced
at the same site (the engine, not the caller), extended with one check the original lacked, and
walled off from every rendered surface by construction rather than convention. This is not
differently-worded; it is the same invariant with a provenance record attached. **The seam is
approved as shipped.** The `jacobian.py` guardian-review reservation for a future *dual*-pass
shift (`t ≠ 0` under differentiation) remains in force — that extension is a new review, not
covered by this one.

## 4. The three-outcome contract — VERIFIED AT ALL THREE LAYERS

- **Schema:** `outcome: Literal["found", "proven_null", "undetermined"]` (`models.py:1536`), with
  the load-bearing field description at `:1554`: *"NEVER True on 'undetermined' — reporting an
  exhausted [budget]..."*; breakeven's own three-way
  `Literal["breakeven_found", "never_breaks_in_range", "undetermined"]` at `:1665`.
- **Search:** honoured in `recourse.py` and `breakeven.py` (exhaustion is `undetermined`, never a
  null; `never_breaks_in_range` is scoped to a stated `searched_to` edge, never "safe").
- **Rendered report:** `generator.py:1671-1709` reads the outcome from `analysis.outcome` — never
  inferred from an empty list — and the `undetermined` copy is exactly what the honest-null rule
  demands: *"this run stopped looking, and that is not a finding that nothing exists... nothing
  in this part should be read as saying that none does."* The `proven_null` branch earns its
  claim ("ran every one of them to a conclusion"). Verified in the rendering code, each branch
  worded so it cannot be mistaken for another.
- One note for the record: `compute_breakevens` currently has **no rendered surface** (no
  consumer outside its own module and tests). Nothing dishonest can render from a surface that
  does not exist; when breakeven rendering ships, it must render all three outcomes
  distinguishably under margin-of-safety copy (the `src/market/README.md:78` contract already
  commits to this), and that rendering falls under GD3's Report row.

## 5. Report copy — VERIFIED DESCRIPTIVE

No advisory language found in `generator.py`, `recourse.py`, or `breakeven.py` (scanned for the
prescriptive vocabulary class). The `found` branch goes further than required: *"This is not a
ranking... this tool has no way to know which of them is open to you, so it does not order them
for you."* No assumption is presented as changeable anywhere in the rendered path — assumptions
have no recourse container to be rendered from, which is the point of GD3.

## 6. The rewritten rationale — VERIFIED HONEST

The charter (`MISSION_5_forward_mode_differentiation.md:28-54`) now states: 30 ms is "Roger's
stated target, not a measured floor"; the original "AD is the path to 30 ms" rationale is quoted
and marked refuted by measurement (three independent measurements, Newton ~4× per dual pass);
AD's surviving justification (direction selection / the Jacobian seam for Half B) is stated as
what it is. `ROADMAP_TRACKER.md:132` and `MISSION_5_HANDOFF.md:68-72` carry the same correction.
`CHANGELOG.md` reports 404.7 → 73.4 → 65.4 ms with method (best-of-7, dev box), reports the
gated budget as 250 ms (the only number with a reader), does not claim 30 ms, and ships its
negative results ("no wider dual ships until the ~10-column consumer exists"). `README.md`
gained no performance or breakeven claims. The documents now tell the truth about what was built
and why it was worth building: the mission's honest story — chartered on a refuted premise,
re-justified by what measurement actually supports, target not met and said so — is *better*
evidence of this project's culture than a met target would have been.

---

## MODIFICATIONS REQUIRED (doc-only; verify by grep before the founder gate)

1. **GV2-M1** — `test_golden_tolerance_walls.py` and `test_golden_anchor.py` docstrings: remove
   or redirect the two references to the nonexistent
   `tests/core/finance/test_golden_tolerance_calibration.py` (the calibration recipes live in the
   walls file; say so).
2. **GV2-M2** — charter Definition of Done (`MISSION_5_forward_mode_differentiation.md:376`):
   rephrase "the ~9.4e-8 injected rounding bug" to the corrected contract-constant language (or
   append the ⚠ marker used at `:169`), so the fiction does not survive in the mission's own
   acceptance checklist.
3. **GV2-M3** — `partition.py:118-121`: update the stale "out of this module's edit boundary this
   session" comment to state that `recourse.py`'s import-time guard now exists at
   `recourse.py:115-124`.

Nothing else must change before the founder's mission gate.

---

**EVIDENCE OF READING (files consulted first-hand this turn):**
- `GD1_veto_review.md` / `GD3_lever_assumption_invariant.md` — the two rulings re-checked, in full.
- `tests/core/finance/test_golden_forecasts.py` — C1/C7 verified line-by-line; determinism test `==` forever, both renames, dated tolerance record.
- `tests/core/finance/golden_tolerance.py` — the rule, all six prohibitions, the C4(c) contract record, ledger + anchor machinery.
- `tests/core/finance/test_golden_anchor.py` — C2's budget test and its never-a-budget-raise message; digest pinning; chain well-formedness.
- `tests/core/finance/generate_golden_forecasts.py` — C3's refusal gates, `--rationale`/`--approved-by` requirements.
- `tests/core/finance/test_golden_tolerance_walls.py` / `test_golden_tolerance_helper.py` — C5/C6 executable; the stale calibration-file reference (GV2-M1).
- `src/core/finance/partition.py` — the invariant verbatim, both sets, barred axes, shape rule, escalation clause; the stale edit-boundary comment (GV2-M3).
- `src/core/finance/jacobian.py` / `src/market/recourse.py` — all import-time GD3 guards confirmed present and worded with the escalation.
- `src/core/finance/engine.py:150-320, 456-600, 895-990` — `PrecomputedIncome`/`ShiftedIncome`/`shift_income`, every seam refusal, `run_financial_model`'s actual signature (checked against the orchestrator's claim, not accepted from it).
- `tests/core/finance/test_income_shift.py` — all thirteen seam tests, incl. the mutation and structural-refusal pins.
- `src/market/breakeven.py` / `src/schemas/models.py:1534-1750` — shape-rule enforcement at import; three-outcome Literals; `AssumptionBreakeven`'s field set (live-inspected).
- `src/core/reports/generator.py:1660-1730` — the three-outcome rendering, each branch's copy.
- `src/schemas/README.md` / `src/market/README.md` — GD3 C4 paragraphs present and accurate.
- `MISSION_5_forward_mode_differentiation.md`, `MISSION_5_HANDOFF.md`, `MISSION_5_SPRINT_TRACKER.md`, `ROADMAP_TRACKER.md`, `MISSION_5_MANUAL_TESTING.md`, `CHANGELOG.md`, `README.md` diff — C4(b) corrections, rationale honesty, no hype.
- Licensing files not re-read this turn: the diff adds no dependency, moves no code across the MIT/commercial boundary, and has zero licensing surface (same disposition as GD.1/GD.3, still true of this diff).
- Project memory (`MEMORY.md` + workflow notes) — direct-to-main, founder holds all gates: the workflow every self-incriminating-diff mechanism above is designed for.

— Principles Guardian, Gate V re-check (GV.2), 2026-08-31
