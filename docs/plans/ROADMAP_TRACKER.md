# Roadmap Tracker — AI Real Estate Deal Analyzer

Standing ledger owned by the mission-planner. Read first, update last, every run.

---

## 1. Current state (as-built)

**Composite grade: B-** _(planner-derived 2026-07-23; to be confirmed by app-evaluator when spawnable)_
Base (this run): `main @ 6147839`, synced 2026-08-03. **`origin/main` has never received Mission 1** — local `main` diverged at Mission 1's merge and every commit since compounds on top (see §3; check the live count, don't trust a written number). The dirty working tree the charter describes as the baseline **landed as `6147839`** (sample bundle restore, parsing regex fixes, report identity/glossary/provenance wiring, `PASS`→`DECLINE` rename, `.env.example` rewrite); the tree is now clean. Planner-verified, orchestrator-reproduced in the real `airedeal` env (`/home/rtokime/anaconda3`, NOT `~/miniconda3`): `pytest` green, coverage 81.87%, `ruff` + `mypy` clean. Graph rebuilt against the working tree (1631 nodes / 4013 edges).

| Axis | Grade | One-liner |
| --- | --- | --- |
| Finance core | A- | Deterministic engine with IO/amortization, refi, IRR, insight-aware modifiers; well tested (`src/core/finance/`). |
| Ingestion & media | B+ | File/URL ingest with fetch policy + robots; media discovery/download/manifest; opt-in phash/quality/hero intelligence. In-progress API refactor parked (broken; `git stash@{0}`) for a dedicated branch. |
| CV / AI | C+ | Closed-set ontology + provider seams, but `vision`/`llm` providers are deterministic stubs; no real AI path. Honest, now documented as such. |
| Orchestration | B | Clean deterministic pipeline; CrewAI engine is a validated parity shell (`kickoff()` never called). |
| Market / scenarios | B+ | `src/market` (snapshot, hypotheses grid, rejector, regional income) now **wired** into the pipeline + report as an opt-in prior-weighted scenario overlay (Mission 1: `adapter.py`, `scenario_runner.py`). |
| Reports | A- | Rich Markdown reports (baseline/stress/NOI valuation tables, media overview) **plus** a principled opt-in "Market Scenarios" section (prior-weighted DSCR/CoC/CF/IRR bands, honesty framing) replacing ad-hoc env-knob stress as the scenario story. |
| Advisor / intelligence | B | Multi-deal fusion, composite scoring, ranking, portfolio summary via `deal-advisor` CLI. |
| Packaging / distribution | D | `pyproject.toml` lacks `[project]` metadata → `pip install -e .` fails; declared console scripts are dead; CLIs only run via `python -m`. |
| Docs | A | Fully reconciled 2026-07-23 (see changelog entry below). |
| Tests / CI | B+ | 87 test files; 80% coverage gate on core/schemas/market; ruff + mypy strict in CI. |

---

## 2. Mission history

| # | Mission | Status | Dates |
| --- | --- | --- | --- |
| — | (pre-tracker) v0.1.0 MVP, media pipeline, CV v2, advisor/intelligence, address parsing | Shipped organically | 2025-09 → 2025-11 |
| 1 | Scenario Intelligence (wire `src/market` into pipeline + reports; Wave 0 packaging fix; authorized IRR-solver core fix) | **Shipped** — Roger's mission gate approved; branch merged to local `main` (unpushed) | 2026-07-23 → 2026-07-24 |
| 2 | Close the end-to-end wiring gaps (Tier 0 false-report fixes, Tier 1 silent-drop wiring + anti-regression guard, Tier 3 CLI honesty, T4/T5 wire-first disposition) | **Chartered + kickoff-approved 2026-08-03 — all 4 OPDs CLOSED, zero open blockers, ready to execute** (branch `mission/2-wiring-gaps`) | 2026-08-03 → — |

---

## 3. Blocker / pre-condition ledger

| Blocker | Gates | Status |
| --- | --- | --- |
| Uncommitted working-tree changes on `main` (core.zip deletion, .gitignore, doc reconciliation) | Any mission branching from main | **Closed 2026-07-24** — landed on `main` (Mission 1 Wave 0) |
| `pyproject.toml` missing `[project]` metadata (broken install, dead console scripts) | Truthful CLI docs; distribution; UI missions | **Closed 2026-07-24** — `[build-system]`+`[project]`+discovery added (Mission 1 Wave 0.2); `pip install -e .` + 3 console scripts verified |
| Media-intelligence API refactor incomplete/broken (caller `insights.py` + tests not propagated to new signatures; ruff/mypy/tests red; env-dependent `_dct2` pHash) | Any work touching `src/core/media/` | **Open 2026-07-24** — orphaned WIP parked in `git stash@{0}`; deferred to its own branch `feat/media-intelligence-refactor` (NOT Mission 1). Fix list in `MISSION_1_SPRINT_TRACKER.md` parking note |
| GitHub SSH **signing** key not registered ("Dell Laptop" key is an auth key only) | Verified commits; clean pushes without admin bypass | **Open 2026-07-24** — commits SSH-signed locally (git 2.55 shim, `~/.gitmodern-bin`) but show Unverified; Roger to add the key as a Signing key in GitHub settings |
| `CITATION.cff` version `1.0.0` ≠ `pyproject`/CHANGELOG `0.1.0` | Any version tag / release cut | **Open 2026-07-24** — reconcile before tagging |
| No real AI provider (vision/LLM stubs only) | Any "AI-powered" marketing claim; CrewAI kickoff mission | Open — deferred (backlog #3) |
| Doc drift | Planning on stale docs | **Re-opened 2026-08-03** — Mission 2 T6 found `README:46-47` (no-op ingest cmd), `CHANGELOG:17` (claims dead narrative/report builders + scenario what-ifs ship), `market/README:22,86` (documents dead `regional_income` as public), `reports/README` (signatures omit `media_report`/`provenance`). Fixed in Mission 2 Wave 2. |
| **`origin/main` has never received Mission 1.** Local `main` diverged at Mission 1's merge and every commit since compounds on top (7 at charter time → 9 at Mission 2 branch-point: + mission-zero `6147839`, + the Mission 2 docs commit; the mission branch adds more) | Any push; Mission 2 Wave Integrate | **Open 2026-08-03** — Roger decides push timing. Reconcile the delta, **never force-push `main`**. Check the live count with `git rev-list --count origin/main..main` rather than trusting a number written here. |
| Report asserts false claims (`cap_rate_floor` unread → "respects the floor policy" always prints; lone `--listing` inherits default bundle financials) | Truthful reports | **Open 2026-08-03** — Mission 2 Wave 0; F1 decided (OPD-2 = wire the warning into `run_financial_model`; re-baselines goldens) |
| OPD-1..4 (Mission 2 product decisions) | Mission 2 Waves 0.2 / 3 | **CLOSED 2026-08-03 (Roger):** OPD-1 reconcile-then-delete `strategist.py`; OPD-2 wire F1 into engine; OPD-3 wire-first Tier-4 (delete only un-wireable); OPD-4 populate Tier-5 fields into reports |
| Transforms rebuild models field-by-field (silent field-drop); nothing tests end-to-end reachability | Any new schema field surviving to the report; truthful CLI/doc claims | **Open 2026-08-03** — Mission 2 anti-regression guard (Wave 1) + feature→reachable-path test (Wave 2) |

---

## 4. Opportunity backlog (leverage-ranked)

| Rank | Candidate | Reward | Blast | Seam | Gap closed | Axes moved | Pre-conditions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ✅ 1 | **Scenario Intelligence** — wire `src/market` hypotheses/rejector into pipeline + report scenario section | **SHIPPED 2026-07-24 (Mission 1)** — delivered exactly as scoped; Market C→B+, Reports B+→A-; plus an authorized IRR-solver core fix | — | — | Market C→B+, Reports B+→A- | Market, Reports, Orchestration, Docs | — done |
| ✅ 2 | Packaging metadata fix (`[project]` table) | **SHIPPED 2026-07-24 (Mission 1 Wave 0.2)** — Packaging D→B; `pip install -e .` + 3 console scripts verified | — | pyproject only | Packaging D→B | Packaging, Docs | — done |
| 3 | **Real vision provider behind the existing CV seam** — see the detailed note below, added 2026-08-03 at Roger's request | High (makes the "AI" headline true) | Med-High (API keys, cost, non-determinism policy; guardian gate) | CV provider registry (`register_onnx_provider` **already exists**) | CV/AI C+→B+ | CV/AI, Orchestration | Determinism policy approved; Mission 2's honest-provenance labelling landed |
| 4 | Streamlit UI for interactive scenario exploration | High (portfolio wow) | Med (new surface, new deps) | Reads existing JSON artifacts | Distribution | Packaging, Portfolio | #1 (scenarios give the UI something to explore), #2 |
| 5 | Live market data ingestion (comps, cap-rate drift) | Med | High (network, data licensing, freshness) | fetch/ policy | Market realism | Market | #1; compliance review |

### Backlog #3 in detail — why `--ai` is a stub, and what "real" looks like
_Added 2026-08-03 at Roger's request during Mission 2, so a future mission can plan it properly._

**What `--ai 1` does today.** It is wired end-to-end — `use_ai=True` reaches
`core.cv.build_photo_insights` — but the provider behind the seam is
`_provider_vision_stub` (`src/core/cv/amenities_defects.py:253-300`), a **deterministic heuristic, not
a model**. It infers labels from image statistics: notably `"street parking", parking_spots=1` from
`aspect == "landscape" and lum >= 0.50`, i.e. a property claim derived from a photo being wide and
bright. Switching it on changes **7 fields** of `PhotoInsights` (`amenities, version,
image_detections, amenity_counts, parking, detections_total, provenance`), so it is **not** inert —
Mission 2 corrected help text that wrongly said it was, and corrected the provenance labelling so
stub output is distinguishable from a future real classifier's.

**Roger's stated direction (verbatim, 2026-08-03):**
> "it's currently a stub, but in the long-run I want to hook it with either a custom classifier
> (fine-tuned for real estate and based on ViT; or a SOTA one; or even letting the user add their API
> key to a model or hook their own model)"

So there are **three distinct offerings** behind one seam, and they have different blast profiles —
a future mission should probably not treat them as one item:
1. **Bring-your-own-model (ONNX).** ⚠️ **Largely already built.** `register_onnx_provider(model_path,
   labels_path)` (`amenities_defects.py:161`) registers a user's own ONNX classifier behind the same
   provider registry, and raises a clear error if `onnxruntime` is absent. **It has zero callers and
   no CLI can reach it** — Python-API only. Making this real is mostly *wiring plus docs*, not new
   capability. Lowest blast of the three; highest ratio of value to effort.
2. **User-supplied API key to a hosted vision model.** Needs the cost/non-determinism/key-hygiene
   policy that gates this whole backlog item, plus a caching story (the CV cache is content-addressed
   by sha256, so it already suits this well).
3. **A fine-tuned real-estate ViT shipped by the project.** Largest effort: training data, licensing,
   model distribution size, and an accuracy claim the project would then have to stand behind.

**Constraint any of these must respect** (established by Mission 2, Roger's ruling): the AI layer
produces **observations only**. All arithmetic stays in `src/core/finance/`, and the
BUY/CONDITIONAL/DECLINE verdict must come from the deterministic `synthesize_thesis` — an AI must
never author it. Mission 2 also added AI-impact transparency to the report (baseline vs
AI-influenced, with per-line attribution of what each observation changed), which any real provider
inherits for free.

---

## 5. Current recommendation

**Mission 2 — Close the end-to-end wiring gaps: CHARTERED + KICKOFF-APPROVED 2026-08-03 (ready to execute).**
Artifacts: `docs/plans/MISSION_2_wiring_gaps.md` (charter), `docs/plans/MISSION_2_SPRINT_TRACKER.md`
(tracker), `docs/plans/MISSION_2_HANDOFF.md` (pasteable prompt). Branch `mission/2-wiring-gaps`.

**Why now:** the reports currently assert things that are false (a `cap_rate_floor` read by zero
lines makes "Purchase cap rate respects the floor policy" print for every deal; a lone `--listing`
inherits the default bundle's financials) and silently drop computed artifacts before they reach the
report (stated listing facts, per-year OPEX notes, `--engine crewai` media sections). These are the
highest-reward, mostly-lowest-blast fixes available (report honesty is the product's core promise),
and the mission installs the anti-regression + reachability net that prevents the whole class from
recurring.

**Kickoff decisions (Roger, 2026-08-03):** full mission (Waves 0–3) approved as one; all four product
decisions CLOSED — OPD-1 reconcile-then-delete `strategist.py`; **OPD-2 wire the F1 cap-floor warning
into `run_financial_model`** (high-blast; deliberately re-baselines every golden number — regenerate
+ human-review); OPD-3 wire-first the Tier-4 dead modules (delete only the un-wireable); OPD-4
populate the Tier-5 unread fields into the reports. Zero open blockers; the mission is ready to
execute. _(Planner had recommended splitting Waves 2–3 into a follow-on; Roger chose one mission —
history only.)_

**Before merge/push (§3):** reconcile the local-`main`-ahead-of-origin-by-7 delta (Roger's push
timing); the GitHub signing key + `CITATION.cff`/`pyproject` version blockers remain open from
Mission 1.

**Deferred backlog** (unchanged): Real AI provider behind CV/LLM seams (#3); Streamlit UI (#4);
cross-input building-mismatch validation (root cause 3 — new feature, logged here, out of Mission 2).

---

## 6. Changelog

* **2026-08-03 (later)** — **Mission 2 kickoff decisions folded into the docs (docs-only, no code).**
  Roger resolved all four OPDs and approved the full mission (Waves 0–3 as one). OPD-1 =
  reconcile-then-delete `strategist.py` (port preferred thresholds into `chief_strategist` first,
  review, then delete). OPD-2 = **wire the F1 cap-floor warning into `run_financial_model`** — the
  high-blast path (16 prod + 25 test files) that **moves every golden number**; the charter/tracker/
  handoff now call out the deliberate golden re-baseline (regenerate + human-review; anti-regression
  tests still RED on true regressions) and the deterministic-core carve-out. OPD-3 = wire-first the
  Tier-4 dead modules, deleting only the un-wireable (`orchestrator.py` 0-byte, `agents/listing_ingest.py`
  true-duplicate, `advisor/__init__.py` bypassed facade). OPD-4 = populate the Tier-5 unread fields into
  the reports (additive-only). All four blockers marked CLOSED; the split-into-Mission-3 recommendation
  retained as history only. Refuted/dropped items (`income_is_estimated`, F9 `onnxruntime`) kept out of
  active scope; GRAPHIFY CONTRACT still verbatim in the handoff. Edited all four planning docs.
* **2026-08-03** — **Mission 2 — Close the end-to-end wiring gaps CHARTERED (not executing).**
  Phase 0: corrected the wrong conda path in the brief (real env `/home/rtokime/anaconda3/envs/airedeal`);
  re-verified the baseline (310-ish passed, 81.87% cov, ruff+mypy clean) — the brief's numbers hold.
  Flagged a non-standard baseline: local `main` ahead of `origin/main` by 7 (Mission 1 unpushed) + a
  dirty working tree that IS the intended baseline (audit + graph built against it) → decision to land
  it first as a mission-zero commit. Independently re-validated all 20 findings + Tiers 4/5/6
  (reproduce + falsify): 12 CONFIRMED, 5 PARTIAL/downgraded (F7 lxml, F8 playwright, F9 onnx, F15,
  F20), 2 loud refutations — **`income_is_estimated` is NOT discarded (read at `engine.py:98`)** and
  **F9 onnxruntime dropped from active fixing** (deliberate opt-in provider, no CLI path). Confirmed
  the Tier-4 reachability closure via static import sweep (no dynamic dispatch anywhere in `src/`) +
  `graphify affected`: `strategist.py`/`narrative`+`report_builder`/`photo_tagger`/`regional_income`
  dead-in-prod, `scenarios.py`/`utils/markdown`/`utils/serialize`/`agents/listing_ingest` zero-ref,
  `orchestrator.py` 0-byte. Key blast insight: `run_financial_model()` reverse-affects 16 prod + 25
  test files → F1's engine-side fix (OPD-2 fork a) is high-blast; consumer-side fork (b) is not.
  Chartered Mission 2 (plan + sprint tracker + handoff prompt) scoped to surviving findings only,
  with 4 open product decisions (OPD-1..4) gating Waves 0.2/3. Recommended Roger split Waves 0–1 from
  Waves 2–3.
* **2026-07-24** — **Mission 1 — Scenario Intelligence SHIPPED.** Wave 0 landed commit hygiene + packaging (`pip install -e .` works). Waves 1–3 delivered the opt-in `--scenarios` overlay: `src/market/adapter.py` + `scenario_runner.py` compose the hypothesis grid with the frozen finance engine into prior-weighted DSCR/CoC/CF/IRR bands (downside = prior-weighted p25), a fixed verbatim honesty block, and honest caveats; additive `ScenarioMetricBand`/`ScenarioOutcome`/`ScenarioAnalysis` models; default-off byte-identical. All 4 review gates passed (finance-semantics, founder-proxy scope, code-review, principles-guardian VETO ×2). One founder-authorized frozen-core carve-out: fixed an IRR Newton-Raphson solver artifact (`src/core/finance/irr.py`) that returned economically-meaningless sub-(−100%) roots — math verified against IRR-domain references, surgical (touches only the one artifact). Axis moves: Market C→B+, Reports B+→A-, Packaging D→B. `main` @ `8f4ce2a`, all commits SSH-signed, CI green. Follow-ups logged (§3): GitHub signing-key registration, CITATION/pyproject version reconcile, parked media-intelligence refactor.
* **2026-07-23** — First run. Phase A: full documentation reconciliation against main @ `e4716df` + working tree — fixed root README (license badge MIT→Research & Education, V1→V2 output, phantom `src/tools`/`src/reports` index entries, CLI docs added, coverage 90%→80%, honest CrewAI-seam framing, roadmap split V1/V2-shipped/V3-planned, packaging caveat), rewrote `src/cli/README.md` (was the old tools README), rewrote `src/core/README.md` (removed nonexistent `cv.bridge`/`xirr`/`media_pipeline`/`build_strategy`; added advisor/intelligence/ingest subareas), rewrote `src/agents/README.md` and `src/orchestrators/README.md` (real signatures, class-based agents, functional-vs-docstring env flags, CrewAI parity-shell honesty), rewrote `src/core/reports/README.md` (write_report, media overview, env overrides, fixed nested links), rewrote `src/inputs/README.md` (InputsLoader/AppInputs/RunOptions live here; real env overrides), rewrote `src/schemas/README.md` (per-unit IncomeModel, real field names, media/ingest models, labels ontology), patched `src/market/README.md` (status + links), reconciled CHANGELOG Unreleased placeholders into the actual shipped V2 feature list with dated status note, fixed CONTRIBUTING install instructions. Phase B: created this tracker; chartered **Mission 1 — Scenario Intelligence** (plan, sprint tracker, handoff prompt written).
