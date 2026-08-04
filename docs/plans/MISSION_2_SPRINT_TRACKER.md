# Mission 2 Sprint Tracker — Close the end-to-end wiring gaps

_Live tracker. The executing orchestrator keeps this current — full updates only (counts + wave
summary + rows), never partial. Date every gate decision._

**Charter:** `docs/plans/MISSION_2_wiring_gaps.md` · **Handoff:** `docs/plans/MISSION_2_HANDOFF.md`
**Baseline:** `main @ 6147839` (the charter's "dirty tree" baseline, now committed) ·
**Branch:** `mission/2-wiring-gaps`

> **Baseline delta found at Wave Sync (2026-08-03, orchestrator).** The charter describes the
> baseline as `fix/sample-listings-paths @ 0d1b976 + uncommitted working-tree work`. By the time
> execution began, **that work had already been committed to `main` as `6147839`** ("fix(demo,report,
> listing): repair the demo bundle regression and wire the report end-to-end") — its message matches
> the charter's Baseline §2 inventory item-for-item. So `6147839` **is** the mission-zero commit; Wave
> Sync reduced to verifying it and landing the planning docs. Consequence: local `main` is ahead of
> `origin/main` by **8**, not 7. All charter `path:line` anchors still hold (they were taken against
> this tree). Charter left unrewritten (historical artifact); this note is the correction of record.

> Every subagent prompt issued in this mission MUST carry the GRAPHIFY CONTRACT verbatim (see the
> handoff). Reachability/blast claims cite `graphify affected` but are confirmed against the file.

## Cost routing (kickoff, 2026-08-03)

Applied the planner's proposed routing table **directly** rather than spawning
`staff-cost-aware-model-router`: that agent's own charter says to invoke it only for *ambiguous*
calls, policy review, or spend post-mortems, and the planner's per-task proposal is unambiguous and
already recorded in the rows below. Spawning it to re-confirm an unambiguous table would be pure
cost. Tier→model mapping used: **capable = opus · standard = sonnet · cheap = haiku.** Each row's
"Agent → tier" column records the actual dispatch. Revisit only if a task turns out mis-tiered (a
cheap agent struggling, or a capable agent doing mechanical work) — log that here if it happens.

## Status legend
`TODO` · `IN-PROGRESS` · `BLOCKED` (needs an OPD or a prior gate) · `REVIEW` (agent says done,
orchestrator verifying) · `DONE` (verified inline) · `DEFERRED`

## Overall progress
- Tasks: **24 / 28 DONE** (one SCOPED — see 0.1) · 3 IN-PROGRESS (Gate 2 VETO remediation) · 0 BLOCKED · 1 TODO
- Suite: **415 tests, exit 0, coverage 83.18%** (mission start: 310 / 81.87%)
- *(Corrected 2026-08-04 — guardian condition C5. These counts had drifted a full wave behind what
  had actually shipped: they read `14/28`, `356 tests`, `82.68%`, and every Wave 2 row still said
  TODO after `74c985c` implemented them. In a mission about documents telling the truth, its own
  record has no exemption. Numbers here are now re-measured, not carried forward.)*
- Gates cleared: **1 / 5 — ✅ Gate 0 PASSED 2026-08-03** (code-reviewer APPROVE · finance-interp PASS ·
  guardian NO VETO, M1+M2 satisfied · **Roger signed off after reproducing the diff himself**)
- **Open questions for Roger at Gate 0:** (1) lxml floor — **RESOLVED 2026-08-03: Roger said raise it
  and ensure it is secure.** Floor now `>=6.1.0`, env upgraded to 6.1.1, CVE **verified closed by
  test** (both vectors pointed at a local canary file; neither read it). Commit `b2f34f2`.
  (2) **RESOLVED 2026-08-03** — Roger reproduced the one-line diff himself (`89d88`) and approved.
- Open product decisions outstanding: **0** — all four CLOSED by Roger 2026-08-03 (see ledger below)

## Wave summary

| Wave | Name | Tasks | DONE | Status | Gate |
| --- | --- | --- | --- | --- | --- |
| Sync | Wave Sync (mission-zero commit) | 2 | 2 | **DONE** 2026-08-03 (mission-zero = `6147839`, already landed) | — |
| Branch | Wave Branch | 1 | 1 | **DONE** 2026-08-03 | — |
| 0 | Truth (Tier 0 + deps) | 5 | 5 | **DONE** 2026-08-03 — all five committed (`705149c`, `2dd36bc`, `5a061aa`, `6fce278`). 0.1 closure scoped to CLI flags (guardian M1). | **Gate 0: Roger only** |
| 1 | Wiring + anti-regression guard | 5 | 5 | **DONE** 2026-08-03 — `db366de`, `6f0642a`, `821cdac`, `369a1f0`, `252e517` | **Gate 1: ready** |
| 2 | CLI honesty + docs | 10 | 10 | **DONE** 2026-08-03 (`74c985c`, `0b5c0b0`, `bb8f54b`) — **Gate 2 VETOED**; remediation in flight (`5e85836` + 3 agents) | Gate 2 🔴 |
| 3 | Disposition (wire-first) | 3 | 0 | TODO | Gate 3 |
| Val | Validation | 1 | 0 | TODO | — |
| Int | Wave Integrate | 1 | 0 | TODO | Mission gate (Roger) |

## Wave Sync
| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| S.1 | Verify tree matches charter; run full gate battery (`airedeal` env) green | orchestrator (inline) → n/a | **DONE** 2026-08-03 — tree did *not* match: the charter's pending work was already committed as `6147839`. Battery re-run in `airedeal`: **310 passed, exit 0; coverage 81.87%; `ruff format --check` 179 files clean; `ruff check` clean; `mypy` clean (179 files)** — matches the charter's verified baseline exactly. |
| S.2 | Commit pending work as the mission-zero commit; re-run battery green; surface origin divergence to Roger | orchestrator (inline) → n/a | **DONE** 2026-08-03 — mission-zero commit is `6147839` (pre-existing). Remaining uncommitted work was **planning docs only** (ROADMAP_TRACKER edit + the three MISSION_2_* files) → landed as a docs-only commit on `main`. Divergence surfaced: local `main` ahead of `origin/main` by **8** (not 7). Generated artifact `investment_analysis.md` left untracked (run output, not source). |

## Wave Branch
| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| B.1 | `git switch -c mission/2-wiring-gaps` off post-mission-zero tip | orchestrator (inline) → n/a | **DONE** 2026-08-03 — branched off the docs commit on top of `6147839`. |

## Wave 0 — Truth (Tier 0 + dependency hygiene)
| ID | Task | Finding | Agent → tier | Status |
| --- | --- | --- | --- | --- |
| 0.1 | Fix config/asset pairing so a lone `--listing`/`--photos` cannot inherit the default bundle's financials (loud-fail or explicit pairing) + RED-on-revert test | F2 | python-eng → capable (opus) | **DONE (SCOPED)** 2026-08-03 — committed `5a061aa`. Loud-fail chosen. **Closure scoped to CLI flags only; the `AIREAL_LISTING`/`AIREAL_PHOTOS` env vector remains OPEN** (guardian M1) — see defect #3. |
| 0.2 | **F1 (OPD-2 = WIRE):** emit a real "cap rate below floor" warning in `run_financial_model` when purchase cap < `cap_rate_floor`; `chief_strategist` consumes the real signal (its `no_cap_floor_breach` DECLINE input goes live). **Finance-core carve-out — 16 prod + 25 test blast; MOVES every golden number.** Regenerate goldens + **human-review** the new values (must reflect only the added warning); confirm anti-regression tests still RED on true regressions. + RED-on-revert test | F1 | python-eng → capable (opus) | **DONE** 2026-08-03 — committed `705149c`. Orchestrator-verified (see 0.2 record below). **Charter premise overturned: zero goldens moved.** |
| 0.3 | Declare `lxml` in `requirements.txt` (belt-and-suspenders; severity downgraded) | F7 | security-eng → std (sonnet) | **DONE** 2026-08-03 — `2dd36bc` + `b2f34f2`. 8 unguarded `BeautifulSoup(..., "lxml")` sites confirmed. **Roger ruled: raise the floor.** Now `>=6.1.0` (env at 6.1.1), CVE-2026-41066 **verified closed by canary test**, not assumed from the version string. |
| 0.4 | Replace the silent render swallow (`html_fetcher.py:336-337`) with a warning/signal; declare `playwright` as optional | F8 | security-eng → std (sonnet) | **DONE** 2026-08-03 — committed `2dd36bc`. **Two** swallow sites found and fixed, not one. `playwright` declared as an optional `render` extra, not runtime-required. RED-on-revert reproduced by the orchestrator. |
| 0.5 | Doc-note `onnxruntime` as an optional opt-in provider dep (no code change) | F9 | docs-maintainer → cheap (haiku) | **DONE** 2026-08-03 — verified inline (see below). |

### 0.2 (F1) — orchestrator verification record, 2026-08-03 · commit `705149c`

**The charter's central premise for F1 is FALSE and Gate 0 must record it as resolved, not open.**
Charter line 121 and tracker row 0.2 both state this fix "moves every golden number in the suite".
**It moves none.** Evidence, independently reproduced by the orchestrator (not taken from the agent):

| Check | Method | Result |
| --- | --- | --- |
| Finance carve-out is minimal | `git diff src/core/finance/` | **Exactly** the 5-line hunk, nothing else |
| Schema untouched | `git diff --stat src/schemas/models.py` | Empty |
| No golden rewritten | `git diff --numstat tests/` | `test_chief_strategist.py` **+75 / −0** — pure append, zero expectations edited |
| **RED-on-revert + no-goldens-moved, one experiment** | Reverted the hunk to HEAD, ran the **full** suite | **Only the 5 new tests fail.** Zero pre-existing tests fail → nothing was re-baselined. Restored → green |
| Suite | `pytest` | 323 collected, exit 0 (baseline 310 + 12 F1 + 1 F8) |
| Coverage | | 81.89% (baseline 81.87%) |
| Demo output unchanged | `python main.py` | Emits no breach warning; 36 Kelly cap 6.35% vs 5% floor |

Why the charter was wrong: the suite had **no coverage of the sub-floor regime at all** — 1 of 3797
engine invocations breaches, and that test asserts only `verdict == "DECLINE"` and `len(levers) > 0`,
both already true. That absence of coverage is *why* the dead code survived unnoticed. The 12 new
tests are the first coverage of it. The finance-interpreter's Gate 0 job is therefore **not** to
human-review moved numbers (there are none) — it is to confirm the warning's semantics and the
strategist consequence below.

**Flagged for 3.1a, deliberately NOT changed:** with the DECLINE input now live, a floor breach
combined with a DSCR failure reaches DECLINE at **2** fails via the `pass_condition` shortcut
(`chief_strategist.py:158`), where every other DECLINE path needs ≥3. Confirmed by reading the code:
`num_fails >= 3 or ((not no_cap_floor_breach) and (not dscr_ok))`. Also confirmed
`REQUIRE_POSITIVE_CF_ALL = False` (`:40`), so there are **5** live verdict inputs, not 6. 3.1a should
inherit this threshold deliberately rather than by accident.

**Also logged for Wave 3 (OPD-4):** the floor *value* is still rendered nowhere. A reader sees
"cap rate below floor" with no number to act on. Correctly out of scope for a minimum-diff
finance-core carve-out; it is exactly OPD-4 territory.

### 0.3/0.4 (F7/F8) — orchestrator verification record, 2026-08-03 · commit `2dd36bc`

- **F8 RED-on-revert independently reproduced:** reverted `html_fetcher.py`, both new tests failed
  with `DID NOT WARN`; restored, green. The fix degrades rather than raising and leaves `strict_dom`
  behaviour unchanged.
- **Scope expansion accepted:** the agent found and fixed a **second**, structurally identical
  swallow site (the CAPTCHA/WAF branch) beyond the one the charter documents. Accepted — same defect,
  same trigger; fixing only the documented one would have left the same lie reachable by another
  route. It was flagged rather than silently widened.
- **Charter path correction:** F8's file is `src/core/fetch/html_fetcher.py`, **not**
  `src/core/ingest/html_fetcher.py` as the charter states. The cited lines 336-337 were exact once
  the right path was found.

**⚠ OPEN GATE 0 DECISION FOR ROGER — lxml floor.** The agent researched CVE-2026-41066 (XXE via
`iterparse()`/`ETCompatXMLParser()`, CVSS 7.5, affects lxml **< 6.1.0**) and correctly concluded it
does not apply here. Orchestrator verified both halves: the codebase **never** calls either API
(grep across `src/`, `main.py`, `tests/` → no hits), **and** the installed lxml is **6.0.2, which is
itself in the vulnerable range**, admitted by the new `>=5.0.0` floor. So the declaration is honest
today but pins a floor that permits a known-vulnerable version — and declaring lxml explicitly makes
that *our* choice rather than a transitive accident. **Options:** (a) keep `>=5.0.0` (unreachable, no
upgrade churn), or (b) raise to `>=6.1.0` (defence-in-depth; needs a resolve check against the
`python-docx`/crewai tree). **Recommendation: (b) if it resolves cleanly, else (a) with this note as
the record.** Not taken silently. The orchestrator trimmed the 5-line CVE comment out of
`requirements.txt` to a one-line house-style note and moved the analysis into the commit message,
per binding constraint 6 ("justified in the commit").

### 0.5 (F9) — orchestrator verification record, 2026-08-03
Agent edited `README.md` (+23) and `src/core/README.md` (+8) only — no `.py`, no `requirements.txt`,
no `src/core/finance/`. Every behavioural claim in the new prose was checked against the code:

| Claim in the doc | Verified against | Verdict |
| --- | --- | --- |
| ONNX is Python-API-only, never invoked by a CLI | `grep` for callers of `register_onnx_provider` | **TRUE, and stronger than claimed** — there are *zero* callers anywhere, including tests |
| `register_onnx_provider()` raises a clear error if `onnxruntime` is missing | `make_onnx_provider` (`amenities_defects.py:152`) constructs `_OnnxModel` **eagerly** → `import onnxruntime` (`:70`) → `RuntimeError("onnxruntime not available; install it to use provider=onnx")` (`:71-72`) | **TRUE** — raises at registration, not deferred to first use |
| Signature `register_onnx_provider(model_path, labels_path)` | `amenities_defects.py:161-165` | **TRUE** |
| Pass `provider="onnx"` to `tag_amenities_and_defects()` / `detect_from_image()` | `runner.py:214-219`, `amenities_defects.py:451-456` | **TRUE** (both keyword-only) |
| Cross-link anchor `#dependencies--optional-providers` | `src/core/README.md:113` `## Dependencies / Optional Providers` | **TRUE** — anchor resolves |

**Follow-up logged for 2.10 (not fixed here — F9 was correctly barred from `.py`):** the docstring at
`src/core/cv/amenities_defects.py:167` says *"Call once during app/CLI init"*, but no CLI (and in fact
no caller at all) ever does. That is a false in-code claim of exactly the class this mission targets.
Fix the docstring during Wave 2 living-doc reconciliation.

## Wave 1 — Wiring + anti-regression guard
| ID | Task | Finding | Agent → tier | Status |
| --- | --- | --- | --- | --- |
| 1.1 | Render `YearBreakdown.notes` (OPEX-mutation explanations) in the report + RED-on-revert test | F3 | report-designer → std (sonnet) | **DONE** 2026-08-03 — committed `db366de`. New "Adjustments Applied" section. RED-on-revert reproduced. **Demo report byte-identical — the section is currently unreachable on real data; see defect #4.** |
| 1.2 | Make `synthesize_listing_insights` carry all stated facts (`title/price/sqft/bedrooms/bathrooms/year_built`) + RED-on-revert test | F4 | python-eng → std (sonnet) | **DONE** 2026-08-03 — committed `6f0642a`. **Fixed the cause, not the instance:** intersection-passthrough (`_stated_facts_from`) so future shared fields flow through automatically. RED-on-revert reproduced. No demo diff — `main.py` never calls this function; it backs the `ingest-listing` CLI. |
| 1.3 | `crewai_runner` sets `media_insights`/`media_report` on `OrchestrationResult` + RED-on-revert test | F5 | python-eng → std (sonnet) | **DONE** 2026-08-03 — committed `821cdac`. Orchestrator-verified: `crew.py` zero diff, RED-on-revert reproduced. **Guarded by a *parity* test** (crewai output `==` deterministic output), so re-drift between the two engines goes RED. Agent caught a vacuous-test trap: the existing zero-byte `.jpg` fixture makes both engines `None`, so parity would have passed comparing `None` to `None`; it added a real-PIL-image fixture instead. |
| 1.4 | `report_cli` passes `media_report` + `provenance` to `write_report` + RED-on-revert test | F6 | python-eng → std (sonnet) | **DONE** 2026-08-03 — committed `369a1f0`. `provenance` **loaded, never constructed** (the CLI makes none of the choices RunProvenance asserts). RED-on-revert reproduced. Orchestrator trimmed a 5-line rationale out of `--help` into the README. |
| 1.5 | **Anti-regression guard:** construct each source model all-fields-non-default, push through each transform, assert no field reverts to default | root cause 2 | qa → std (sonnet) | **DONE** 2026-08-03 — committed `252e517`. 16 tests, 4 transforms, **zero `src/` diff**. See verification record below. |

### 1.5 — orchestrator verification record, 2026-08-03 · commit `252e517`
The guard's design is right where it counts: `build_sentinel_model` enumerates
`model_fields` **dynamically**. A guard that hand-listed field names would carry the identical
defect it guards against. Exclusions live in one `_EXCLUDED[(model, field)] = reason` table — no
silent skips.

**Proven to catch real drops, four ways — two by the author, two independently by me:**

| Break introduced | Caught? | Message |
| --- | --- | --- |
| Revert F4 `_stated_facts_from` (author) | ✅ | names all six fields individually |
| Revert F5 crewai media wiring (author) | ✅ | names both fields |
| **Drop `media_insights` from `crew.py`** — the *deterministic* engine, a transform the author never used for its proof (orchestrator) | ✅ | `[src.orchestrators.crew] OrchestrationResult.media_insights is still at its default` |
| **Add a brand-new `ListingInsights` field nobody wires through** (orchestrator) — *the actual root-cause-2 scenario* | ✅ | report guard fails: sentinel present on source, absent from rendered text |

The last one is the decisive test. Note the *synthesis* guard correctly stayed green there — the
new field is not on `ListingNormalized`, so that transform legitimately cannot carry it; the
**report-level guard is the backstop**. That division of responsibility is correct, not a gap.

**Test-count correction:** the guard agent noted an "unexplained delta" against a 339 baseline.
**The 339 was my error** — I quoted it to two agents without measuring. HEAD was **337**; F6 took it
to 340; +16 guard tests = **356**, which reconciles exactly. No anomaly.

### Seven live gaps the guard surfaced — logged, NOT fixed (zero `src/` diff was binding)
Most are T5/OPD-4 work that **Wave 3 must now cover**; they are additions to the charter's T5 list:
1. `YearBreakdown.principal_paid` / `.interest_paid` — T5-class recompute-vs-render.
2. `MarketSnapshot.vacancy_rate/cap_rate/rent_growth/expense_growth/interest_rate` — only `.region`
   ever prints; extends the charter's `.notes` finding to the whole snapshot.
3. `ScenarioAnalysis.prior_sum` — computed by `scenario_runner.py`, never referenced in `generator.py`.
4. **`ScenarioAnalysis.notes` whenever `n_accepted > 0` — dropped, but REDUNDANT, not a lost fact.**
   `_render_market_scenarios` prints `analysis.notes` only in the zero-accepted branch, while
   `scenario_runner.py` sets it unconditionally.
   **CORRECTION OF RECORD (guardian M9, 2026-08-03) — my earlier entry here called this "a *current*
   defect, not a rendering nicety". That was an overstatement and is withdrawn.** The guardian traced
   the value end-to-end and I verified it: the note is
   `f"Rejector: in={len(hset.items)}, kept={len(ordered)}"` (`rejector.py:173`), and the header line
   already renders `f"{analysis.n_accepted} of {analysis.n_generated} scenarios admitted under
   guardrails"` (`generator.py:905-907`) where `n_generated = len(generated.items)` **is** `in=` and
   `n_accepted = len(outcomes_tuple)` **is** `kept=` (`scenario_runner.py:147,196`). The dropped note
   carries **zero information the reader does not already have**, in a less legible form. It is a
   redundant field. Deferring it to Wave 3 is correct.
   *(This is the second defect I overstated — the first was the env-vector "even with `--config"` claim
   at Gate 0, also caught by the guardian. Both are now corrected in place. Noting the pattern so the
   remaining waves are read with appropriate scepticism of my severity language.)*
5. `MediaInsights.image_quality` — never referenced in `_render_media_overview`.
6. `MediaCoverage.version` — `_render_photo_coverage` prints `provider` but not `version`, while the
   sibling Media Overview section prints both.
7. `MediaReport.listing_title/source_url/address/defects/quality_flags/parking` — six fields that
   never reach the report at all.

**Also flagged for product review:** `MarketHypothesis.rationale` is excluded as borderline —
defensible, since it is consumed by `.summary()`/CLI rather than that table.

### Newly-discovered defect #4 — logged, NOT fixable in this mission without Roger reopening the carve-out
**The engine's OPEX modifiers test pre-normalization strings while the pipeline emits
post-normalization labels, so both triggers are unreachable from any real run.**

`_apply_insight_modifiers` (`engine.py:64-70`) fires on two literal strings. Orchestrator-verified
that neither can ever arrive:

| Trigger | Why it never matches |
| --- | --- |
| `"old roof" in conds` | **Not in the closed `ConditionTag` set at all** — that set is `renovated_kitchen, updated_bath, well_maintained, new_flooring, natural_light, curb_appeal`. No roof concept exists. |
| `"water stain" in defs` | The string **is** in the vocabulary, but `labels.py:241` normalizes it to `DefectLabel.water_leak_suspected` (value `"water_leak_suspected"`) **before** the engine sees it. The engine's literal check can never match the normalized label. |

Consequence: the engine's OPEX-bump feature is dead on real data, and F3's new "Adjustments
Applied" section can only ever appear from hand-written synthetic JSON. `python main.py` is
byte-identical before and after F3 for exactly this reason. F3 itself is correct — it renders
whatever the engine puts in `notes` — and was verified end-to-end against a synthetic forecast that
does trip the modifiers.

**Why it is not fixed here:** the engine side is inside `src/core/finance/`, where binding
constraint 1 permits **exactly one** diff this mission and it is already spent on F1. The
alternative — changing the normalization map — has its own blast radius across the CV/label layer.
Either way this is a product decision for Roger, not a cleanup. **Recommend a follow-on mission**
covering trigger/label reconciliation, since the same shape may affect the amenity uplifts
(`"in-unit laundry"`, `"parking"`) which are only reachable when `income_is_estimated=True`.

## Wave 2 — CLI honesty + docs
| ID | Task | Finding | Agent → tier | Status |
| --- | --- | --- | --- | --- |
| 2.1 | `ingest_cli` surfaces `result.insights`/`result.photos` (or documents why not) | F10 | python-eng → std (sonnet) | **DONE** `74c985c` — both summarised always; full JSON under `--pretty 1`. |
| 2.2 | Wire `collect_local_assets` into `--file` mode so media flags do something (or reject them with a clear message) | F11 | python-eng → std (sonnet) | **DONE (SCOPED)** `74c985c` — **the charter's framing was wrong.** The flags ARE plumbed into `ingest_listing`; the inertness is downstream (`collect_media` needs a URL/snapshot; `collect_local_assets` is never called from `ingest_listing`). The CLI now explains the limitation instead of silently producing an empty bundle. **Wiring `collect_local_assets` is a `src/core/ingest/` change → moved to Wave 3 / OPD-3**, not smuggled in here. |
| 2.3 | Remove/implement `advisor_cli --debug`; implement or delete | F12 | python-eng → std (sonnet) | **DONE** 2026-08-03 — **implemented, not removed.** The help text already promised "Print ranked/portfolio to stdout"; that promise was simply never honoured. Honouring an existing user-facing contract beats inventing a new knob or silently retracting one. |
| 2.4 | `advisor_cli --markdown` must not clobber the JSON when `--out` ends `.md` | F13 | python-eng → std (sonnet) | **DONE** 2026-08-03 — orchestrator-verified end-to-end: `--out clob.md --markdown` now writes markdown to `clob_report.md`, prints a loud note naming both paths, and the JSON at `--out` still parses. Silent data loss closed. |
| 2.5 | `report_cli --insights` rejects JSON with no recognized fields | F14 | python-eng → std (sonnet) | **DONE** 2026-08-03 — boundary is **"shares ≥1 field name with the model"**, not "complete": `{"totally":"unrelated"}` rejected with a message listing the valid fields; `{"address":"12 Real St"}` still works, because absent facts are legitimate and this project never fabricates listing data. Scoped to `--insights` only — every other `_maybe_load` model has ≥1 *required* field, so unrelated JSON already fails there via pydantic; adding the gate would swap one clear error for another. |
| 2.6 | `ingest_cli --ai` help text (+ honest description) | F15 | python-eng → cheap | **DONE** `74c985c`, then **CORRECTED** `5e85836` — the Wave 2 wording claimed output was unchanged, which was FALSE (Gate 2 blocker V1). Now states the real effect. |
| 2.7 | `ingest_cli --pretty` documented / split dual purpose | F16 | python-eng → cheap | **DONE** `74c985c` — **split**, not merely documented: new `--save-screenshot` (default 1). Turning down console noise must not silently stop persisting an artifact. |
| 2.8 | `advisor_cli --files` error points at a real valid example (add one if none exists) | F17 | python-eng → std (sonnet) | **DONE** 2026-08-03 — new `data/examples/advisor_deal_config.json` with the real `listing_path`/`photos_dir`/`finance_inputs_path` keys. **Orchestrator ran the cited command verbatim → exit 0.** Deliberate check, given Gate 1's M6 blocker was exactly this class (a documented example that crashed). |
| 2.9 | `--media-kinds` invalid → argparse usage error, not a raw traceback; `report_cli` missing-file → clean error; fix `address_struct`→`address_structure` in the CLI print | F18, F19, F20 | python-eng → std | **DONE** `74c985c` — all three. `address_structure` fixed in the CLI **and** in the `listing_text.py`/`listing_html.py` fallback dicts, where `extra=\"ignore\"` was silently discarding it. |
| 2.10 | T6 living-doc reconcile + CHANGELOG:17 **dated note** (not rewrite); **feature→reachable-path test** | T6, root causes 1&4 | docs-maintainer → std (sonnet) + qa → std (sonnet) | **DOCS DONE** 2026-08-03; reachability test in progress. See record below. |

### 2.10 docs — orchestrator verification record, 2026-08-03
Six files reconciled: `README.md` (ingest example corrected — the old one implied media intelligence
works in `--file` mode, which F11 shows it does not), `src/market/README.md` (`build_regional_income`
restated as reachable only from tests, **without** pre-empting Wave 3's OPD-3 wire-or-delete call),
`src/core/reports/README.md` (signatures gain `media_report`/`provenance`; "Adjustments Applied"
added), `src/schemas/README.md` (`ListingInsights` stated facts + the seven `YearBreakdown` fields),
`src/core/README.md` (the OPEX-modifier claim corrected; reachability caveats on `strategist.py`,
`narrative_builder`, `report_builder`, `advisor/scenarios.py`), and `CHANGELOG.md`.

**Guardian M10 satisfied, and proved rather than asserted.** Both README mentions of "Adjustments
Applied" state it cannot appear on real pipeline data today and cite the mechanism. The agent
demonstrated it programmatically:

    Real-path (normalized) Year1 notes:     []
    Hand-constructed unnormalized Year1 notes: ['condition: old roof → reserves +$300/yr',
                                                'defect: water stain → R&M +$200/yr']

**CHANGELOG:17 — dated note appended under `[Unreleased]`, released history NOT rewritten.** It flags
that the "narrative/report builders + scenario what-ifs" clause is contradicted by the T4 reachability
finding, and explicitly notes the rest of that bullet (deal fusion, scoring, ranking, portfolio, risk
flags, CSV/MD exports) is unaffected — so the correction does not overreach.

**Systemic doc defect found and FIXED by the orchestrator (not in the charter's T6 list):** all eight
documented `pytest -q tests/<subset>` commands across `src/*/README.md` **exited non-zero**. Cause:
`pytest.ini`'s global `--cov-fail-under=80` applies to every invocation, and no subset short of the
full suite reaches 80% (`tests/core` alone is 60.39%). Every one now carries `--no-cov`, and **all
eight were executed to exit 0** rather than eyeballed. Same class as Gate 1's M6 blocker — a
documented command that does not work.
*(Orchestrator note: my first check of this used invented paths like `tests/market`, which gave a
misleading exit 4 — "file or directory not found" — rather than the real exit 1. Re-tested against
the actual documented commands before acting.)*

## Wave 3 — Disposition (WIRE-FIRST; OPDs resolved)

### OPD-1 pre-work — threshold audit, orchestrator, 2026-08-03 (step 1 of the binding sequence)
`form_thesis` (`src/core/strategy/strategist.py`) confirmed dead: referenced **only** by
`tests/unit/test_strategist.py`, zero production callers. But the audit turned up something that
changes the disposition — **on one guardrail the dead code is MORE correct than the live one:**

| Guardrail | LIVE `chief_strategist` | DEAD `strategist.py` | Engine warning (`engine.py:301`) |
| --- | --- | --- | --- |
| DSCR Y1 | `MIN_DSCR_Y1 = 1.20` | `dscr < 1.20` | — |
| **Cap-rate spread** | **hardcoded `MIN_SPREAD = 0.015`** | **input `mkt.cap_rate_spread_target`** ✅ | **input `mkt.cap_rate_spread_target`** ✅ |
| IRR 10y | `MIN_IRR_10YR = 0.12` | *(none)* | — |
| **Year-1 CoC** | ***(none — `coc` is never consulted)*** | `coc < 0.03` | — |
| Cash flow | Y1 ≥ 0 required | any year < 0 flagged | any year < 0 warns |

**Two consequences for the OPD-1 sequence:**
1. **This IS guardian M4.** The engine and `strategist.py` both honour the user's
   `cap_rate_spread_target`; only the live `chief_strategist` hardcodes `0.015`. That is precisely
   why a report can print "cap-rate spread below target" in Warnings while its own thesis says
   "meets target". **Deleting `strategist.py` without porting this would discard the correct
   behaviour** — which is exactly what the reconcile-before-delete sequence exists to prevent.
2. **`PurchaseMetrics.coc` is computed and never consulted by the verdict engine at all.** The dead
   code has a Year-1 CoC floor; the live one has none. That is both an OPD-1 question (port it?) and
   a T5-adjacent finding (a computed metric no live decision reads).

**Both are verdict-moving changes**, so per the Gate 0 lesson they go to Roger with generated
before/after artifacts and reproduce commands — not a description. Sequence still binding: audit →
port → **review** → only then delete.
| ID | Task | Finding | Agent → tier | Status |
| --- | --- | --- | --- | --- |
| 3.1a | **OPD-1 sequence (`strategist.py`):** (1) audit its `dscr<1.20`/`coc<0.03` thresholds; (2) port any Roger-preferred values into `chief_strategist`'s tunable constants; (3) review the threshold change (code-reviewer + finance-interp), regenerate any verdict goldens; (4) **only then** delete `strategist.py` + its tests. Delete must not precede the review. **PLUS — guardian M4/M7, a HARD exit criterion, not advice: reconcile `chief_strategist.MIN_SPREAD` (hardcoded `0.015`, `:38`) against the engine's use of the *input* `mkt.cap_rate_spread_target` (`engine.py:301`).** Today a deal can print "cap-rate spread below target" in Warnings while its own thesis says "meets target", verdict BUY, levers empty so the warning is never explained. Same defect class as F1. Also consider the finance-interpreter's materiality recommendation: breach ≥ 25-50 bp **and** `DSCR < 1.00`, since the current 2-input shortcut is near-tautological at every shipped setting. | T4 | python-eng + finance-interp + code-reviewer → capable | TODO |
| 3.1b | **OPD-3 wire-first:** wire each dead module into a live path — `narrative_builder`+`report_builder`→feed the report; `scenarios.py`→advisor what-ifs (CHANGELOG:17 claims they ship); `regional_income`→public entry point per `market/README`; `utils/markdown`→replace inline `advisor_cli.py:391-411`; `utils/serialize`→serialization sites; `photo_tagger`→ingest if a real consumer exists. **Delete only the un-wireable:** `orchestrator.py` (0-byte), `agents/listing_ingest.py` (true duplicate, no consumer), `advisor/__init__.py` (bypassed facade). Each wired item ships a RED-on-regression test. | T4 | python-eng + code-reviewer → std | TODO |
| 3.2 | **OPD-4 populate:** render every computed-then-discarded field into the report. **(a) HARD EXIT CRITERION — guardian M3/M8: the cap-rate FLOOR VALUE must reach the report.** Today a breach prints "Purchase cap rate breaches the configured floor." naming neither the cap nor the floor, while every sibling line names both. House style agreed with founder-proxy: *"Purchase cap rate is 6.35% (≥ the 5.00% floor you set)."* Note this is **not a template edit** — neither `generate_report` (`generator.py:916-926`) nor `synthesize_thesis` receives `FinancialInputs`, so it needs an **additive kwarg**. This also restores the positive claim dropped in `6fce278`. **(b)** charter T5 set: `RefinancePlan.market_cap_rate` (implement the fallback or drop the false docstring — **re-review F1's comparison if the fallback lands, since it changes what the floor is tested against**), `YearBreakdown.{ltv_pct,available_equity,est_value}` (render stored values instead of recomputing at `generator.py:592-596`), `MarketSnapshot.notes`. **(c)** the seven gaps the guard found (see the 1.5 record). **(d) guardian M11:** re-adjudicate — do not inherit — the three uncited `MediaReport.{report_version,ontology_version,provenance}` exclusions; a test author's uncited "not meant to render" must not become the product decision by default, least of all for a field named `provenance`. Additive-only. Each field ships a RED-on-regression test. | T5 | python-eng + finance-interp → std | TODO |

## Wave Validation
| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| V.1 | Full battery (`pytest`, coverage ≥80%, `ruff`, `mypy`, `python main.py`) + byte-identical default-off check | qa + code-reviewer → std | TODO |

## Wave Integrate
| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| I.1 | Re-sync, re-run battery, `--no-ff` merge to `main`, reconcile+push the 7-commit origin delta (Roger's timing); record merge sha | release-coordinator → std | TODO (Roger gate) |

## Gate decision records
- **Gate 0 (Truth):** _in progress 2026-08-03._
  - **code-reviewer → APPROVE, zero blocking findings** (commits `705149c`, `2dd36bc`). Verified
    independently rather than asserted: finance-core diff is exactly 5 insertions and nothing else;
    `models.py` diff empty; **units confirmed consistent** (both sides fractions — no percent-scale
    literal at any call site, the severe-bug candidate); strict `<` correct against the field's own
    "flag deals **below** this threshold" wording; hyphenated neighbour still correctly does not
    match the consumer; `stacklevel=2` correct; `RuntimeWarning` **is** visible by default (not in
    Python's default-ignored set — checked in a fresh interpreter); tests hit no network.
  - **The "re-baselined goldens" review item is RESOLVED, not open** — there are no moved goldens
    (see the 0.2 record). The reviewer re-derived this from the test factory: baseline cap ≈ 7.4-7.5%
    vs the 0.05 default floor, so the suite never crosses the threshold.
  - Two non-blocking follow-ups accepted as backlog, not fixed here (charter YAGNI): the stringly-typed
    warning coupling (2 producers → 1 consumer; a constant/enum is premature at n=3), and the
    `strict_dom` bypass below.
  - **finance-interpreter → PASS on the math, with ONE BLOCKING honesty item (B1, below).** Certified:
    Year-1 vacancy/credit-adjusted NOI over purchase price is the right basis; **units clean at every
    call site** (no percent-valued cap rate anywhere in `src/`, `data/`, `tests/`); strict `<` correct
    and consistent with all four sibling guardrails (`>=`); `None` handled per the field's contract;
    negative cap (−0.27%) compares soundly. Ran a sensitivity sweep — no single perturbation
    (occ −5pts, rent −10%, opex +10%, price +10%) brings 36 Kelly below its 5.00% floor.
  - **founder-proxy (B1 remedy) → DECIDED:** (a) drop the positive floor claim **now**, (b) restore it
    in Wave 3 with OPD-4 in the house style naming both numbers (*"Purchase cap rate is 6.35%
    (≥ the 5.00% floor you set)."*), and invert **both** pinning tests to assert silence rather than a
    string. Grounded in the charter's own statement of F1 (`:75` — *"'respects the floor policy'
    always prints"*), so this **finishes** F1 rather than amending OPD-2. Implemented + verified,
    commit `6fce278`.
  - **guardian VETO → APPROVE WITH MODIFICATIONS (NO VETO)** at `6fce278`. Independently re-derived
    rather than accepting the record: reproduced B1 both pre- and post-remedy; proved **three** of the
    four RED-on-revert claims itself in an isolated worktree (F1 engine hunk, F2 call site, and the B1
    `_flag` line); confirmed the finance diff is 5 insertions and the `src/schemas/` diff is empty;
    confirmed two consecutive `main.py` runs byte-identical with a one-line delta. Ruled B1 **would
    have been a VETO** had `6fce278` not landed — *"aggravated, not mitigated, by F1: wiring the engine
    lent the unconditional claim the appearance of having been checked."* Also cleared licence posture
    (lxml BSD-3, playwright Apache-2.0 — both permissive, compatible with the dual-licence stance).
  - **Roger → ✅ SIGNED OFF 2026-08-03. GATE 0 PASSED.** Roger rejected the abstract sign-off request
    ("How am I supposed to validate that... how am I supposed to reproduce the thing that will
    generate the data to compare?") — a fair challenge, and the orchestrator had been asking him to
    approve a change it had never actually shown him. Remedied by generating both report versions
    plus a no-floor-configured config, and handing him copy-pasteable reproduce commands. **He then
    reproduced the diff independently and got the identical result:**

        $ diff /tmp/before.md /tmp/after.md
        89d88
        <   - Purchase cap rate respects the floor policy.

    Both Gate 0 questions resolved: **lxml floor raised to `>=6.1.0`** (his instruction: "raise it and
    ensure it's secure" — CVE verified closed by canary test, `b2f34f2`), and **the demo report's
    one-line loss confirmed by his own reproduction.**
    **Process lesson for the remaining gates:** never ask Roger to confirm an output change without
    first generating the before/after artifacts *and* the commands to regenerate them. He reads the
    document; a diff hunk quoted in chat is not a reviewable artifact.

**Guardian's binding modifications:**
| # | Condition | Binds | Status |
| --- | --- | --- | --- |
| **M1** | F2 may not be recorded as CLOSED while the env vector reproduces it; scope the closure language | **Gate 0** | ✅ **DONE** — row 0.1 now reads DONE (SCOPED); defect #3 rewritten, including the correction of my own overstatement |
| **M2** | `investment_analysis.md` is untracked *and un-gitignored* and still contains the removed false line — a careless `git add -A` would commit it | **Gate 0** | ✅ **DONE** — added to `.gitignore` |
| **M3** | The floor threshold must reach the report — a **hard Wave 3 exit criterion, not guidance**. The breach line names neither the cap nor the floor while every sibling line names both | Gate 3 / OPD-4 | Carried |
| **M4** | The engine/strategist spread contradiction must close **in this mission**, not slip to a follow-on — OPD-1 already owns the reconciliation | Gate 3 / 3.1a | Carried |
| **M5** | `strict_dom` bypass — keep the logged entry live, *"do not let it decay into folklore"*; timing is Roger's call | Gate 2 or follow-on | Carried |

**Guardian advisories (non-blocking):** F8's warning lead clause always says *"JS rendering failed"*
even in the nested `strict_dom` path where the render **succeeded** and the DOM parse failed (true
cause is still carried via `type(exc).__name__`) — worth a word-change when M5 is addressed. F2's
refusal message names `DEFAULT_INPUTS` before the `.exists()` check, so on a checkout with the bundle
deleted it names a missing file (unreachable in practice, cosmetic).

#### 🔴 B1 — BLOCKING (Gate 0): the false claim is only HALF fixed
`cap_rate_floor` defaults to `None` (`models.py:113`), so any config omitting it still prints
**"Purchase cap rate respects the floor policy."** — a claim about a policy that does not exist.
**Orchestrator-reproduced directly:**

    cap_rate       : 0.01   (a 1% cap rate)
    cap_rate_floor : None   <-- no floor policy configured at all
    rationale      : "Purchase cap rate respects the floor policy."

F1's own finding was *"'respects the floor policy' always prints"*. F1 closed the **configured** case
(all shipped inputs incl. 36 Kelly) and left the **default** case live — and the new test
`tests/integration/test_chief_strategist.py:208-214` now **asserts** the false line, pinning it.

Structural constraint: `synthesize_thesis` receives only `FinancialForecast` and infers the breach
from a substring match on `forecast.warnings`; the forecast does not carry `cap_rate_floor`, so the
strategist **cannot** distinguish "no floor" from "floor respected". Remedy is therefore a product
call — `principal-founder-proxy` is deciding between (a) drop the positive claim, (b) plumb the floor
value through (composes with OPD-4), (c) defer + unpin the test.

#### Finance review — guidance for later waves (recorded, not acted on)
- **For 3.1a — the 2-input DECLINE shortcut is weaker than it looks.** Because
  `DSCR ≈ cap / (LTV × debt_constant)` and the measured annual debt constant is 0.0578–0.0727 at
  4–6%, DSCR ≥ 1.20 requires cap ≥ 5.85% @75% LTV. **Every shipped input sets floor = 0.05**, so any
  deal breaching that floor at ≥70% leverage already fails DSCR — the "AND DSCR" conjunct is
  **near-tautological at shipped settings**, making it behave as a *single*-input DECLINE. Also
  `MIN_DSCR_Y1 = 1.20` is a lender-preference threshold, not the cannot-cover line (1.00), so the
  code comment overstates it. And there is no materiality band: a measured case flips CONDITIONAL →
  DECLINE on a **0.0002 percentage-point** breach despite +$3,385 Y1 CF and 17.37% IRR.
  **Recommendation for 3.1a:** keep the conjunction but make both legs material — breach ≥ 25–50 bp
  **and** `DSCR < 1.00`.
- **For OPD-4 — rendering the floor is NOT a template edit.** `generate_report`
  (`generator.py:916-926`) receives `FinancialForecast` but **not** `FinancialInputs`, and
  `synthesize_thesis` likewise. The floor value is out of scope at *both* render sites, so it needs
  an additive kwarg. Composes with B1 remedy (b).
- **For OPD-4 — `RefinancePlan.market_cap_rate` (`models.py:101-103`) documents a purchase fallback
  the engine does not implement.** If OPD-4 implements it, it silently changes *what the floor is
  tested against* — OPD-4 must re-review the F1 comparison, not just render a field.
- **Negative NOI deserves distinct treatment.** With NOI(Y1) < 0 the engine zeroes `est_value` for
  all 10 years (`engine.py:179`) and `irr()` returns `None` coalesced to `0.0` (`:296`), so the report
  states "Projected IRR (10y) is 0.00%" — reading as *break-even* when it is *undefined*. Pre-existing
  false precision, larger than the cap-rate wording. Recommend a distinct NOI ≤ 0 signal.

### Newly-discovered defect #2 — **MUST CLOSE IN THIS MISSION (guardian M4/M7)**, in row 3.1a
**The engine and the strategist disagree about the spread threshold, and the report can contradict
itself.** The engine warns using the *input* `mkt.cap_rate_spread_target` (`engine.py:302`) while
`chief_strategist.MIN_SPREAD` is **hardcoded 0.015** (`:38`). Finance-interpreter reproduced: with
`cap_rate_spread_target=0.030`, cap 7.0%, rate 5.0% → the Warnings section says *"cap-rate spread
below target"* while the rationale says *"Cap-rate spread meets target at 2.00% (≥ 1.50%)"*, verdict
**BUY** — and because BUY yields empty levers, the warning is never explained. Exactly the F1 class,
still live. Belongs with OPD-1's threshold reconciliation (3.1a).

### Newly-discovered defect #3 — logged, NOT fixed in Mission 2 · **F2 IS THEREFORE NOT FULLY CLOSED**
**`AIREAL_LISTING` / `AIREAL_PHOTOS` reach the same defect F2 closes, through a channel F2's guard
cannot see.** `src/inputs/inputs.py:281-287` sets `updates["listing"]`/`updates["photos"]` inside
`InputsLoader.load`, i.e. **after** `resolve_config_path` has already returned. With no `--config`,
`args.listing is None`, so F2's guard never fires and the run falls through to the demo bundle.

**Orchestrator-reproduced** (`AIREAL_LISTING=<other> python main.py`, no `--config`):

    # Investment Analysis – 12 Elsewhere Street, Moncton NB …
    **As listed:** List price $1,250,000.00 · 3 bd / 2 ba · 4,000 sq ft
    | Inputs file | data/sample_listings/36_kelly_moncton/inputs.json | `--config` |

A $1.25M property underwritten against a $399,900 deal — verbatim the F2 defect.

**Correction of record (guardian, M1).** An earlier revision of this tracker claimed the env vars do
this "even with an explicit `--config`". **That overstated it.** `--config mine.json` +
`AIREAL_LISTING=other.txt` is the same user-chosen pairing that F2 deliberately permits at the CLI
(pinned by `test_listing_with_explicit_config_is_a_legitimate_pairing`) — not a new defect. The real
defect is **env-listing with no `--config`**, which is what reproduces above. Recorded accurately
rather than left overstated, in a mission about not overstating things.

**Partial mitigation, recorded for accuracy:** the Run Provenance appendix *does* name the inputs file
(see the third line above), so the run is partially self-disclosing — unlike the pure-CLI form of F2.

**Consequence for the record (guardian M1, binding):** **F2 must NOT be reported as CLOSED.** Its
closure is scoped to **CLI flags only; the env vector remains open.** Closing the env vector means
constraining a documented env contract (`.env.example:29-30`, `src/inputs/README.md:67-68`,
`src/orchestrators/README.md:58`) pinned by `tests/test_env_example.py`, so it is a deliberate
follow-on, not a silent omission. `python-dotenv` is a declared dependency, so a VS Code `.env` can
set these invisibly.
  - Minor: the `705149c` message says "12 tests"; the true count of *new* test functions is 11
    (12 collected in that file including 1 pre-existing). Noted, not amended — the commit is signed
    and the inaccuracy is immaterial.

### Newly-discovered defect — logged to backlog, NOT fixed in Mission 2
**`strict_dom` is silently bypassed for rendered-HTML DOM-parse failures.**
`src/core/fetch/html_fetcher.py:350-359` (and the identical `:262-271` CAPTCHA branch): the inner
`raise InvalidHtmlError(...)` guarded by `if pol.strict_dom` at `:354-355` is nested **inside** the
outer `try`, whose `except Exception as e` at `:356` catches it — so a caller who set
`strict_dom=True` gets a warning and a raw fallback instead of the error they asked for. The RAW-path
equivalent at `:333-335` is not nested and correctly propagates.

Orchestrator-confirmed by reading the code. **Pre-existing** — F8 did not create it (the outer clause
was previously a bare `except Exception:`), so `2dd36bc`'s "strict_dom behaviour is unchanged" claim
is true. Not fixed here because it is outside the charter's validated finding set and the fix is a
real behaviour change for `strict_dom` users (hard failure where they currently get a fallback), not
a trivial correction. It is the same *class* as this mission's defects, so it belongs in a follow-on.
- **Gate 1 (Wiring + guard):** **PASSED 2026-08-03** — code-reviewer **APPROVE**, guardian **NO VETO
  (approve with modifications)**, QA pending at time of writing. Per the charter, Gate 1 does **not**
  require Roger; he holds the mission gate.
  - Both reviewers re-derived the invariants themselves rather than accepting the record: finance diff
    still exactly F1's 5 lines, `src/schemas/` diff empty, demo report byte-identical against the Wave 0
    tip, 356 passed / 82.68% / ruff + mypy clean. Both independently reproduced the guard's decisive
    root-cause-2 case by injecting a new never-wired `ListingInsights` field (`parking_notes`,
    `hoa_fee_monthly`) and confirming the report guard fails by name.
  - **The `_EXCLUDED` table was audited entry-by-entry against the renderer by both reviewers and found
    HONEST** — no exclusion laundering a live drop. `build_sentinel_model` **raises `TypeError`** on an
    unhandled type rather than skipping, so there are no silent holes structurally.
  - **F6 singled out as the best decision of the wave** — declining to construct `RunProvenance`
    "honours the honesty trigger at the point where it would have been easiest to violate". Verified by
    grep: `RunProvenance(` is constructed in exactly one place in all of `src/`, `main.py:302`.

**Gate 1 HARD BLOCKERS — all closed 2026-08-03 before Wave 2 opened:**
| # | Blocker | Status |
| --- | --- | --- |
| **M6** | `src/cli/README.md` documented a copy-pasteable example referencing `data/examples/media_report.json` and `provenance.json`, **neither of which exists** — a Wave 1 commit turned a working documented example into one that crashes with `FileNotFoundError`, in the mission whose thesis is that docs must not assert what isn't true. **This was an orchestrator verification miss:** I reviewed F6's README prose and never checked the paths resolved. | ✅ **FIXED** — example reduced to files that exist and re-run to exit 0; the two flags stay documented in the bullets with a note that no committed example exists *because a checked-in `provenance.json` would describe a run that never happened*. |
| **M7** | M4 was decaying — defect #2's heading said "NOT fixed in Mission 2" while M4 binds it to close in-mission, and row 3.1a never mentioned `MIN_SPREAD`. | ✅ **FIXED** — heading corrected; `MIN_SPREAD` reconciliation written into row 3.1a as a hard exit criterion. |
| **M8** | M3 lived in three prose records and **no executable row** — an executor working from row 3.2 would have missed a hard exit criterion. | ✅ **FIXED** — the floor value is now criterion (a) of row 3.2, with the additive-kwarg constraint and the agreed house style. |
| **M9** | My own overstatement of `ScenarioAnalysis.notes`. | ✅ **CORRECTED** — see the 1.5 record; the note is redundant, not a lost fact. |

**Process incident, 2026-08-03 — parked WIP nearly lost.** The Gate 1 code-reviewer ran `git stash`
without first running `git stash list`, popping Mission 1's parked media-intelligence refactor WIP
(unrelated to this mission). It re-stashed the content losslessly and **self-reported the near-miss**,
which is the behaviour wanted. But the descriptive stash message was replaced by a generic
auto-message reading `WIP on mission/2-wiring-gaps`, falsely implying it was Mission 2 work — and
`ROADMAP_TRACKER.md §3` points at that stash. **Remediated:** content verified intact (both media
files, matching magnitude), the descriptive message restored, and the commit **additionally tagged
`parked/media-intelligence-refactor`** so it can never be lost to an errant stash command again.
Future agents must not run bare `git stash` in this repo.
- **Gate 2 (CLI + docs):** 🔴 **VETOED 2026-08-03 by principles-guardian.** code-reviewer APPROVE (no
  blocking). Guardian vetoed on four honesty defects, three authored by Wave 2 itself.
  **All four independently reproduced by the orchestrator before escalation.**

**Gate 2 binding modifications — recorded as a TABLE, not prose.** *(The guardian noted M10 decayed
because it lived only in prose — the same M8 pattern. Not repeating it.)*

| # | Blocker | Status |
| --- | --- | --- |
| **V1** | **`--ai`'s new help text is FALSE — a Wave 2 regression I approved.** It claims "output does not change from the default path yet". **Reproduced: `use_ai=1` changes 7 fields** — `amenities, version, image_detections, amenity_counts, parking, detections_total, provenance`. Parking flips from `{'parking_type': 'none'}` to **`{'parking_type': 'street', 'parking_spots': 1}`**, a property claim the `_provider_vision_stub` infers from `aspect == "landscape" and lum >= 0.50` (`amenities_defects.py:296-298`) and stamps `version="ai"`. Wave 2 took a flag with *no* help text and gave it help text asserting an inertness it does not have. | **OPEN** |
| **V2** | The M10 caveats over-claim: "cannot appear on **any** real pipeline run today" is false — see V3's path. | **OPEN** |
| **V3** | 🔴 **ESCALATED TO ROGER — live breach of the deterministic-core invariant.** See below. | **ROGER** |
| **V4** | `src/schemas/README.md:47` is the **only uncaveated** "Adjustments Applied" mention **and is false**: it claims `notes` annotates IO/refi years. Guardian ran a forecast with `interest_only_years=3` and a realized year-5 refi → notes empty in all 10 years. `engine.py:212-215` writes notes **only** from `insight_notes`, **only** at `y == 1`. Claim was copied from `models.py:218`'s stale description — T6 must reconcile docs against *code*, not other docs. | **OPEN** |

**Hard conditions C1-C6:** C1 dangling "charter finding M10" pointer (no such charter text); C2 the cited
mechanism is partial (the live *text* path uses free-string `_CONDITION_KEYWORDS`, `listing_parser.py:37-45`,
not only the closed enum); C3 the `amenities_defects.py:166` docstring fix assigned to 2.10 was not done;
C4 four READMEs edited this wave still carry stale `_Last reconciled` stamps; C5 **the tracker itself
understates what shipped** (Wave 2 row says `10 | 0 | TODO`; actual 391 tests / 83.09%) — in a mission
about documents telling the truth, its own record must; C6 M5's "Gate 2 or follow-on" fork is now due.

**Guardian APPROVED, for the record:** the CHANGELOG dated note (zero deletions, scoping independently
verified accurate), `src/market/README.md` (does not pre-empt OPD-3), the eight `--no-cov` fixes
(pre-fix failure reproduced: `tests/core` → exit 1, 60.39%), the `--pretty`/`--save-screenshot` split,
both scope expansions as **discipline not drift** — and it confirmed the `address_struct` fix was
*inside* the charter all along (charter `:94` names the `:107/:118` fallback dicts; my CLI-only framing
of F20 was what was wrong). **M3, M4, M11 confirmed still carried in executable rows and not decayed.**

**Scope limit of the reachability net, now on record:** it proves a flag is *read*, not that it *does
what its help says*. `--ai` passes the net while its help text is false. Not a defect in the net — but
no one should mistake a green net for verified flag semantics.

### 🔴 V3 — ESCALATED TO ROGER 2026-08-03: an LLM can move the money numbers and author the verdict
**Pre-existing — NOT created by Mission 2.** Orchestrator-verified line by line:

| Claim | Verified |
| --- | --- |
| `crew.kickoff()` is never called | **FALSE** — called at `crewai_components.py:365` and `:495` whenever `_llm_enabled()` |
| Gate | `AIREAL_LLM_MODE` (`:150-152`), documented at `.env.example:69`, `src/agents/README.md:64`, `src/orchestrators/README.md:57`. **No code change needed**; `python-dotenv` is declared, so a `.env` can set it invisibly |
| LLM moves money numbers | `ListingAnalystAgent.run` → LLM-authored `condition_tags`/`defects`/`amenities`, **unnormalized** → `crewai_runner.py:81→84` → `run_financial_model` → `_apply_insight_modifiers` (`engine.py:64-70`) → OPEX/NOI/DSCR/**the very cap rate F1's floor test compares against**. Guardian measured on 36 Kelly: OPEX +$500, NOI −$500, DSCR 0.8960→0.8783, cap 6.345%→6.220% |
| LLM authors the verdict | `ChiefStrategistAgent.run` (`:516-517`) → `_run_llm` → `_parse_json_as(InvestmentThesis, llm_text, …)` — **the BUY/DECLINE verdict itself**, bypassing `synthesize_thesis`'s metrics/thresholds/rules entirely |
| Four docs deny it | `README.md:106` "parity shell … delegates to the same deterministic math"; `CHANGELOG.md:31` "`crew.kickoff()` not yet called"; `src/agents/README.md:56` "a future seam"; `crewai_runner.py:73-77` "not executed here" |

**To be fair to the code:** `FinancialForecasterAgent` is deliberately **not** LLM-backed
(`crewai_components.py:389-391`) — the arithmetic stays deterministic. The breach is at the *inputs*
and the *verdict*, not the formulas.

**Roger's decision (not the proxy's — this is whether the project's core promise is real):**
**(a)** correct the four docs to describe the seam honestly (Wave 2, minimum for Gate 2), or
**(b)** gate `AIREAL_LLM_MODE` off in `crewai_runner` pending a real decision, or **(c)** both.
- **Gate 3 (Disposition):** _pending._ No blockers (OPD-1/3/4 resolved = wire-first; enforce the
  OPD-1 reconcile-before-delete sequence).
- **Mission gate (Roger):** _pending._ Precondition of merge + push; also resolves the
  main-ahead-of-origin-by-7 reconciliation.

## Product decisions — ALL CLOSED (Roger, 2026-08-03)
| ID | Decision (resolved) | Affects | Status |
| --- | --- | --- | --- |
| OPD-1 | **Reconcile then delete** `strategist.py` — port preferred thresholds into `chief_strategist`, review, then delete (sequence enforced in 3.1a) | 3.1a | **CLOSED 2026-08-03** |
| OPD-2 | **Wire the cap-floor warning into the engine** (`run_financial_model`); high-blast, deliberately re-baselines the goldens (regenerate + human-review) | 0.2 | **CLOSED 2026-08-03** |
| OPD-3 | **Wire-first** every Tier-4 dead module into a live path; delete only the un-wireable (`orchestrator.py`, `agents/listing_ingest.py`, `advisor/__init__.py`) | 3.1a/3.1b | **CLOSED 2026-08-03** |
| OPD-4 | **Populate** every Tier-5 unread field into the reports (schema additive-only) | 3.2 | **CLOSED 2026-08-03** |
