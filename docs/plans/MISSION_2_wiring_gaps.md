# Mission 2 — Close the end-to-end wiring gaps

_Charter. Owned by mission-planner. Kickoff approved by Roger 2026-08-03 (all product decisions
resolved, zero open blockers); ready to execute — this planning session does not execute it._

---

## Executive summary

A four-agent audit + planner re-validation found that several report claims are false, several
computed artifacts are silently dropped before they reach the report, several CLI flags are inert or
misleading, and ~350 LOC across ~11 modules is reachable only from tests. Root cause is structural,
not incidental: **nothing tests end-to-end reachability**, and transforms **rebuild models
field-by-field** so any field added later is silently dropped. This mission fixes the confirmed
defects behind a reachability/anti-regression safety net, on a dedicated branch, one wave at a time.

**Every finding in the source brief was independently re-validated by the planner** (reproduce +
falsify + verdict). The scope below is the **surviving** set only. Loud refutations and downgrades
are recorded in §"Validation outcomes".

> **Kickoff decisions (Roger, 2026-08-03) — all four product decisions are RESOLVED; there are zero
> open blockers.** Scope: **full mission, Waves 0–3 approved as one mission.** F1: **wire the
> cap-floor warning into the engine** (high-blast, deliberately re-establishes the golden-number
> baseline). `strategist.py`: **reconcile thresholds then delete.** Tier 4/5: **wire-first** —
> prefer wiring dead code into live paths and populating unread fields into reports over deleting;
> deletion is the fallback only for genuinely un-wireable items. Details in §"Resolved product
> decisions". _(Planner had recommended splitting Waves 2–3 into a follow-on mission; Roger elected
> to run the full mission as one — noted here for history only.)_

---

## Baseline

`base = fix/sample-listings-paths @ 0d1b976 + uncommitted working-tree changes, synced 2026-08-03.`

**This is a NON-STANDARD baseline — three things Roger must note (HALT-CONSULT items):**

1. **Local `main` is ahead of `origin/main` by 7 commits** (all of Mission 1, never pushed). This
   mission's `main` is not the remote's `main`. Wave Integrate cannot cleanly `pull --ff-only`;
   the push step must reconcile the 7-commit delta first (Roger decides push timing).
2. **The working tree is dirty** — substantial uncommitted work on `fix/sample-listings-paths`
   (sample bundle restore, sqft/beds-baths regex fixes, report `title` fallback + "As listed" line
   + Media Overview/Photo Coverage wiring + glossary + Run Provenance appendix, `PASS`→`DECLINE`
   rename, `.env.example` rewrite). Per policy we plan against committed state; here the audit,
   the graph, and all `path:line` anchors were taken against this **working tree**, so the tree is
   the intended baseline. **Decision (see Wave Sync): land it first as a dedicated mission-zero
   commit** — it is coherent, green (310 passed, 81.87% cov, ruff+mypy clean, planner-reproduced in
   the `airedeal` env), and several findings depend on it. Do NOT discard or silently fold it.
3. The graph at `graphify-out/graph.json` was rebuilt against this working tree
   (`built_at_commit 0d1b976`, 1631 nodes / 4013 edges) — trust file contents over graph metadata.

**Verified baseline gate (planner-run, `airedeal` conda env):** `pytest` exit 0, coverage 81.87%
(≥80% gate met), `ruff check .` clean, `mypy .` clean (179 files). The instructions' conda path
`~/miniconda3/...` is WRONG — the real env is `/home/rtokime/anaconda3/envs/airedeal`
(`source /home/rtokime/anaconda3/etc/profile.d/conda.sh; conda activate airedeal`). Correct this in
every command.

---

## Branch

`mission/2-wiring-gaps`, cut from `main` **after** the mission-zero commit lands (see Wave Sync /
Wave Branch). All mission work commits here. No PRs (direct-to-main flow); merge to `main` only
after Roger approves the mission gate.

---

## Validation outcomes (surviving scope = CONFIRMED / PARTIAL only)

Full reproduction commands + literal outputs are in the planner's validation report (returned to
Roger with this charter). Compact verdicts:

| # | Finding | Verdict | Scope decision |
| --- | --- | --- | --- |
| 1 | `cap_rate_floor` read by 0 lines; engine emits only `cap-rate spread below target` / `negative cash flow` — never a "below floor" warning, so `chief_strategist.py:122` `no_cap_floor_breach` is always True → "respects the floor policy" always prints + 1 of 6 DECLINE inputs is dead | **CONFIRMED** | Wave 0 — **RESOLVED (OPD-2 = wire into engine; high-blast, re-baselines goldens)** |
| 2 | `--listing`/`--photos` without `--config` pairs the given asset with the **default bundle's** financials (`config_path = args.config or DEFAULT_INPUTS`) | **CONFIRMED** | Wave 0 |
| 3 | Engine writes `YearBreakdown.notes` (`engine.py:246`); generator renders `insights.notes` + `analysis.notes` but never `forecast.years[*].notes` → OPEX-mutation explanations never ship | **CONFIRMED** | Wave 1 |
| 4 | `synthesize_listing_insights` returns only `address/amenities/condition_tags/defects/notes` → drops `title/price/sqft/bedrooms/bathrooms/year_built` (`synthesis.py:204`) | **CONFIRMED** | Wave 1 (canonical instance of root cause 2) |
| 5 | `crewai_runner` returns `OrchestrationResult` without `media_insights`/`media_report` (deterministic path sets both) → `--engine crewai` drops two report sections | **CONFIRMED** | Wave 1 |
| 6 | `report_cli` calls `write_report` with only `media_insights` — omits `media_report` + `provenance` (both accepted by the signature) → output not comparable to `main.py` | **CONFIRMED** | Wave 1 |
| 7 | `lxml` undeclared in `requirements.txt`; 8 unguarded `BeautifulSoup(..., "lxml")` sites | **PARTIAL** | Wave 0 — declaration only; **severity DOWNGRADED** (crash-on-clean-install unproven: `lxml` is transitively pulled by `python-docx`/crewai tree and is present in the env). Cheap belt-and-suspenders declare. |
| 8 | `playwright` undeclared + `except Exception: rendered_bytes = None` (`html_fetcher.py:336-337`) | **PARTIAL** | Wave 0 — **the silent swallow is the keeper defect** (a failed `--render` continues with no warning); the missing-declaration half is minor (playwright present in env). |
| 9 | `onnxruntime` undeclared; ONNX provider is Python-API-only, no CLI reaches it | **CONFIRMED (low severity)** | **DROP from active fixing** — deliberate lazy import, opt-in provider, no CLI path. Doc-note only. |
| 10 | `ingest_cli --photos` computes photo insights + synthesized `ListingInsights` but the CLI never prints `result.insights`/`result.photos` | **CONFIRMED** | Wave 2 |
| 11 | `--download-media/--max-media/--media-kinds/--media-intel` inert in `--file` mode (`collect_media` needs url/snapshot; `collect_local_assets` not wired into `ingest_listing`) | **CONFIRMED** | Wave 2 |
| 12 | `advisor_cli --debug` dead (only at `add_argument`, `args.debug` never read) | **CONFIRMED** | Wave 2 |
| 13 | `advisor_cli --markdown` with `--out x.md` → `md_path = out.with_suffix(".md") == out` clobbers the JSON | **CONFIRMED** (only when `--out` ends `.md`) | Wave 2 |
| 14 | `report_cli --insights` accepts any JSON (ListingInsights all-optional) → empty-insights report, no error | **CONFIRMED** | Wave 2 |
| 15 | `ingest_cli --ai` has no help text; "runs no AI" | **PARTIAL** | Wave 2 — no help text CONFIRMED; the flag **is** wired (`use_ai`→`build_photo_insights`); "no AI" only because providers are deterministic stubs. Low severity. |
| 16 | `ingest_cli --pretty` undocumented dual purpose (console dump + `save_screenshot`) | **CONFIRMED** | Wave 2 |
| 17 | `advisor_cli --files` error cites `inputs.json` "as an example" but that file's keys are `inputs/run/market`, not `listing_path/photos_dir/finance_inputs_path` | **CONFIRMED** | Wave 2 |
| 18 | `--media-kinds <invalid>` raises raw `argparse.ArgumentTypeError` traceback (helper called post-`parse_args`, not as a `type=`) | **CONFIRMED** (reproduced) | Wave 2 |
| 19 | `report_cli` missing forecast file → raw `FileNotFoundError`; the `ap.error("--forecast is required…")` is unreachable (`required=True`) | **CONFIRMED** (reproduced) | Wave 2 |
| 20 | `address_struct` vs `address_structure` — model field is `address_structure`; `ingest_cli.py:99` reads `address_struct` → structured-address print never fires | **CONFIRMED (nuanced)** | Wave 2 — the **main normalize path populates the field correctly** (`listing_text.py:90`/`listing_html.py:101`); only the CLI print + the `:107/:118` fallback dicts use the wrong key. |
| T4 | Reachability closure (no dynamic dispatch anywhere in `src/`; static closure authoritative): `strategy/strategist.py`, `intelligence/narrative_builder.py`+`report_builder.py`, `agents/photo_tagger.py`, `market/regional_income.py` = dead in production (tests only); `advisor/scenarios.py`, `utils/markdown.py`, `utils/serialize.py`, `agents/listing_ingest.py` = zero refs (0 prod, 0 test); `orchestrators/orchestrator.py` = 0-byte; `core/advisor/__init__.py` = bypassed lazy facade | **CONFIRMED** | Wave 3 — **RESOLVED (OPD-1 reconcile-then-delete `strategist.py`; OPD-3 wire-first the rest, delete only un-wireable)** |
| T5 | Computed-then-discarded fields: `RefinancePlan.market_cap_rate` (inert + docstring promises a fallback the engine doesn't do), `YearBreakdown.{ltv_pct,available_equity,est_value}` recomputed in `generator.py:592-596`, `MarketSnapshot.notes` unrendered, and the rest of the listed set | **CONFIRMED (class)** — representative members verified | Wave 3 — **RESOLVED (OPD-4 = populate every field into the reports; schema additive-only)** |
| T5-x | `FinancialInputs.income_is_estimated` "gates a live branch nothing sets" | **REFUTED (loud)** | **DROP** — it **is read** at `engine.py:98` (`allow_income_adjustments=fi.income_is_estimated`); a wired, user-settable input flag, not a discarded field. |
| T6 | Docs assert unwired features: `README.md:46-47` ingest command effectively no-ops (per F10/F11), `CHANGELOG.md:17` claims narrative/report builders + scenario what-ifs ship (contradicted by T4), `market/README.md:22,86` documents dead `regional_income` as a public entry point, `reports/README.md` signatures omit `media_report`/`provenance` | **CONFIRMED (class)** | Wave 2 (living docs) / dated-note for CHANGELOG released sections |

**Non-findings (explicitly out of scope, notes only):** annual amortization periods (~1.17% above
monthly-pay; deliberate, documented, now disclosed in the glossary — changing it moves every golden
number, needs its own decision) and the `3/1` duplex beds/baths parse (known limitation).

---

## Resolved product decisions (Roger, 2026-08-03 — all CLOSED, zero open blockers)

- **OPD-1 — `strategist.py` → RECONCILE, THEN DELETE.** `src/core/strategy/strategist.py` is a dead
  second verdict engine with diverged hardcoded thresholds (`dscr < 1.20` / `coc < 0.03`). Wave 3
  task, **strictly sequenced:** (1) audit whether those thresholds are values Roger actually wants
  live; (2) port any preferred values into the **tunable constants that feed
  `src/agents/chief_strategist.py`** (`MIN_DSCR_Y1`, etc.); (3) get the threshold-change reviewed
  (code-reviewer + finance-interpreter); (4) **only then** delete `strategist.py` and its tests. The
  delete must never land before the reconciliation review. If any threshold changes, expect verdict
  goldens to move — regenerate + human-review.
- **OPD-2 — F1 → WIRE THE WARNING INTO THE ENGINE (high-blast, deliberate re-baseline).**
  `run_financial_model` (`src/core/finance/engine.py`) will **emit a real "cap rate below floor"
  warning** when the purchase cap rate breaches `cap_rate_floor`; `chief_strategist` then consumes a
  real signal (its `no_cap_floor_breach` DECLINE input becomes live). This is the **deterministic
  finance-core carve-out** for this mission (see Binding constraints §1). Blast: `run_financial_model()`
  reverse-affects **16 prod + 25 test files** and **this fix moves every golden number in the suite**
  that flows a forecast through a report/thesis. That is expected and intended: the golden-number
  baseline is **re-established deliberately** as part of F1 — regenerate the goldens, **human-review
  the new values for correctness** (they must reflect the added warning, nothing else), and confirm
  the anti-regression tests still turn RED on *true* regressions (i.e. the goldens are re-pinned to
  reviewed-correct outputs, not blindly overwritten).
- **OPD-3 — Tier 4 → WIRE-FIRST, delete only the un-wireable.** Default disposition is to **wire
  each dead module into a live reachable path** rather than delete it: `narrative_builder` +
  `report_builder` → feed the report; `scenarios.py` → wire the advisor scenario what-ifs
  (`CHANGELOG:17` already claims they ship); `regional_income` → wire as the public entry point its
  `market/README` documents; `utils/markdown` → replace the inline reimplementation at
  `advisor_cli.py:391-411`; `utils/serialize` → use at the serialization sites; `photo_tagger` →
  wire into ingest if a real consumer exists. **Fallback to deletion only for genuinely un-wireable
  items** (list explicitly): `orchestrators/orchestrator.py` (0-byte), `agents/listing_ingest.py`
  (truly duplicate of the live `core/ingest/listing_ingest.py`, no consumer), and
  `core/advisor/__init__.py` (a lazy-dispatch facade every caller bypasses — keep or delete, no wire
  target). Wiring grows blast/surface, so **each wired item ships its own RED-on-regression test.**
- **OPD-4 — Tier 5 → POPULATE INTO THE REPORTS (additive-only).** Default disposition is to
  **render/populate every computed-then-discarded field** into the report rather than document it
  away: `RefinancePlan.market_cap_rate` (implement the promised fallback or drop the false
  docstring), `YearBreakdown.{ltv_pct,available_equity,est_value}` (render the stored values instead
  of recomputing at `generator.py:592-596`), `MarketSnapshot.notes`, and the rest of the listed set.
  Schema stays additive-only. Each populated field ships a RED-on-regression test.

---

## Scope

### In scope
- **Wave 0 (Truth):** F2; **F1 — wire the cap-floor breach warning into `run_financial_model`
  (finance-core carve-out) and consume it in `chief_strategist`; regenerate + human-review the
  moved golden numbers**; F7 declare `lxml`; F8 emit a warning instead of a silent render swallow;
  F9 doc-note.
- **Wave 1 (Wiring + anti-regression guard):** F3, F4, F5, F6, **plus the root-cause-2 guard**: a
  test that constructs each source model with every field non-default, pushes it through each
  transform (`synthesize_listing_insights`, the orchestration-result assembly, the report
  generators), and asserts nothing reverts to its default.
- **Wave 2 (CLI honesty + docs + reachability-to-docs test):** F10–F20 (surviving), living-doc
  reconciliation (T6), and **a test that ties each documented feature/CLI flag to a reachable
  path** (root causes 1 and 4).
- **Wave 3 (Disposition — wire-first):** Tier 4 — wire each dead module into a live path (delete
  only the un-wireable `orchestrator.py` / `agents/listing_ingest.py` / `advisor/__init__.py`);
  `strategist.py` = reconcile-then-delete (OPD-1 sequence). Tier 5 — populate every unread field
  into the reports. Each wired/populated item ships a RED-on-regression test.

### Out of scope
- Any change inside `src/core/finance/` **except** the **F1 cap-floor warning carve-out** (Roger
  approved wiring it into `run_financial_model` under OPD-2). No other finance-core edits.
- Removing or retyping any `src/schemas/models.py` field (additive-only). Populating unread fields
  is additive rendering, not a schema change.
- The annual-amortization convention and the duplex beds/baths parse (notes only).
- Real AI providers, UI, live market data (backlog, not this mission).
- Cross-input building-mismatch validation (root cause 3) — worthy, but a **new feature**; log to
  backlog, do not smuggle into a wiring-fix mission.

---

## Waves

| Wave | Name | Content | Gate |
| --- | --- | --- | --- |
| Sync | Wave Sync | Verify tree matches this charter; commit the pending work as the **mission-zero commit** on `fix/sample-listings-paths` (or the mission branch); re-run the full gate battery green. Surface the main-ahead-of-origin-by-7 divergence to Roger. | — |
| Branch | Wave Branch | `git switch -c mission/2-wiring-gaps` off the post-mission-zero tip. | — |
| 0 | Truth | F2; **F1 = wire cap-floor warning into `run_financial_model` + consume in `chief_strategist` + regenerate & human-review the moved goldens** (finance-core carve-out, 16 prod + 25 test blast); F7 lxml decl; F8 swallow→warning; F9 doc-note. Each fix ships a RED-on-revert test. | **Gate 0** (code-reviewer + finance-interpreter on F1 + the re-baselined goldens; security on deps; guardian VETO; Roger) |
| 1 | Wiring + guard | F3, F4, F5, F6 + the all-fields-non-default transform guard. | **Gate 1** (code-reviewer + qa; guardian VETO) |
| 2 | CLI honesty + docs | F10–F20, T6 living-doc reconcile + CHANGELOG dated-note, feature→reachable-path test. | **Gate 2** (code-reviewer + docs; guardian VETO) |
| 3 | Disposition (wire-first) | T4 wire-first (delete only un-wireable; `strategist.py` reconcile-then-delete per OPD-1 sequence), T5 populate unread fields into reports. Each item ships a RED-on-regression test. | **Gate 3** (founder-proxy product sign-off; code-reviewer; guardian VETO) |
| Val | Validation | Full gate battery after the last implementation wave. | — |
| Int | Wave Integrate | Re-sync, re-run battery, `--no-ff` merge to `main`, reconcile+push the 7-commit delta (Roger's timing). | **Mission gate — Roger only** |

---

## Definition of Done
- Every surviving finding across Waves 0–3 is fixed (wired-first where applicable) **or** consciously
  deferred with a logged reason; each fix ships a test that **turns RED when the fix is reverted**
  (proven, not assumed).
- **F1 golden re-baseline:** the moved golden numbers are regenerated **and human-reviewed** to
  confirm they reflect only the added cap-floor warning; the anti-regression suite still turns RED on
  true regressions (goldens re-pinned to reviewed-correct outputs, never blindly overwritten).
- The anti-regression transform guard exists and fails if any transform drops a newly-added field.
- A feature→reachable-path test exists and fails if a documented CLI flag/feature becomes
  unreachable.
- `strategist.py` deleted **only after** its thresholds were reconciled into `chief_strategist`'s
  tunable constants and that change was reviewed (OPD-1 sequence).
- Same input ⇒ byte-identical output (against the **re-baselined** goldens); the only intended
  output change vs pre-mission is F1's added warning and the newly-wired Tier-4/Tier-5 content.
- The only diff inside `src/core/finance/` is F1's cap-floor warning (OPD-2 carve-out);
  `src/schemas/models.py` additive-only.
- `pytest` green, coverage ≥80%, `ruff format` + `ruff check` + `mypy` clean (real `airedeal` env).
- Living docs reconciled with `_Last reconciled_` stamps; CHANGELOG released sections get dated
  notes, not rewrites.
- Tracker fully updated; every gate has a dated decision record; Roger approved the mission gate
  before any merge/push.

## Agent roster (≤3 concurrent; `task → agent → model tier`; co-author with cost-router at kickoff)

| Task | Agent | Model tier (planner proposal) |
| --- | --- | --- |
| Mission-zero commit / release hygiene | `staff-release-coordinator` + `staff-code-reviewer` | standard |
| F1 verdict logic / F2 pairing (finance-adjacent) | `staff-python-engineer` + `staff-financial-result-interpreter` | capable |
| F3/F6 report rendering | `staff-report-experience-designer` | standard |
| F4/F5 wiring + anti-regression guard | `staff-python-engineer` + `staff-qa-test-engineer` | standard |
| F7/F8/F9 dependency + supply-chain safety | `principal-security-engineer` | standard |
| CLI fixes (F10–F20) | `staff-python-engineer` | standard / cheap |
| Docs (T6) + CHANGELOG dated notes | `staff-documentation-maintainer` | cheap |
| Feature→reachable-path + reachability tests | `staff-qa-test-engineer` | standard |
| Dead-code / field disposition (Wave 3) | `staff-python-engineer` + `staff-code-reviewer` | standard |
| OPD-1..4 product calls / scope sanity | `principal-founder-proxy` | capable |
| VETO at every gate | `principal-principles-guardian` | capable |
| Tier assignment for every task | `staff-cost-aware-model-router` | cheap |

## Binding constraints
1. **Deterministic-core invariant (with one approved carve-out):** the **only** permitted diff
   inside `src/core/finance/` is F1's cap-floor breach warning in `run_financial_model` (Roger
   approved under OPD-2). It is deterministic (a pure comparison of purchase cap vs `cap_rate_floor`),
   adds no network, and its golden impact is re-baselined + human-reviewed. No other finance-core
   edits; scenarios still perturb copies and re-run the engine.
2. **Schema contracts:** `src/schemas/models.py` additive-only — nothing renamed, retyped, removed.
   Populating unread fields (Tier 5) is additive report rendering, not a schema change.
3. **Determinism:** same input ⇒ byte-identical output **against the re-baselined goldens**;
   `--scenarios` off stays byte-identical except for F1's warning and the newly-wired content.
4. **Prove-the-test:** every fix ships a test that turns RED on revert — demonstrated, not assumed.
5. **Quality gate:** `ruff format` + `ruff check` + `mypy` clean; coverage ≥80%.
6. **License/deps:** new declarations (`lxml`, optionally `playwright`) justified in the commit;
   no new *runtime-required* dependency without security sign-off.
7. **Git:** branch from post-mission-zero tip; no PRs; merge to `main` only after Roger's mission
   gate; never force-push `main` (the origin delta is reconciled, not overwritten).

## Gates
Guardian VETO at every wave gate (honesty/values); founder-proxy product sign-off at Gate 3;
**Roger holds the mission gate** (merge + push) — never self-approved.

## Flags (historical — resolved at kickoff)
The planner had flagged this mission as over-scoped for one minimum-blast unit and recommended
splitting Waves 2–3 into a follow-on. **Roger elected to run all of Waves 0–3 as a single mission
(2026-08-03).** Retained here only as history; the active plan above is the full mission with zero
open blockers. The refuted/dropped items remain out of active scope: `income_is_estimated` (REFUTED
— read at `engine.py:98`) and F9 `onnxruntime` (deliberate opt-in provider, no CLI path — doc-note
only). Note that OPD-2 (wire F1) + OPD-3/4 (wire-first) deliberately grow blast and surface beyond
the minimum-blast default; that is Roger's accepted trade for closing the whole class in one pass.
