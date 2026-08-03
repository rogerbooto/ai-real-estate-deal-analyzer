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

## Status legend
`TODO` · `IN-PROGRESS` · `BLOCKED` (needs an OPD or a prior gate) · `REVIEW` (agent says done,
orchestrator verifying) · `DONE` (verified inline) · `DEFERRED`

## Overall progress
- Tasks: 3 / 28 DONE · 0 IN-PROGRESS · 0 BLOCKED · 25 TODO
- Gates cleared: 0 / 5 (Gate 0, 1, 2, 3, Mission)
- Open product decisions outstanding: **0** — all four CLOSED by Roger 2026-08-03 (see ledger below)

## Wave summary

| Wave | Name | Tasks | DONE | Status | Gate |
| --- | --- | --- | --- | --- | --- |
| Sync | Wave Sync (mission-zero commit) | 2 | 2 | **DONE** 2026-08-03 (mission-zero = `6147839`, already landed) | — |
| Branch | Wave Branch | 1 | 1 | **DONE** 2026-08-03 | — |
| 0 | Truth (Tier 0 + deps) | 5 | 0 | TODO (F1 = wire into engine, re-baselines goldens) | Gate 0 |
| 1 | Wiring + anti-regression guard | 5 | 0 | TODO | Gate 1 |
| 2 | CLI honesty + docs | 10 | 0 | TODO | Gate 2 |
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
| 0.1 | Fix config/asset pairing so a lone `--listing`/`--photos` cannot inherit the default bundle's financials (loud-fail or explicit pairing) + RED-on-revert test | F2 | python-eng + finance-interp → capable | TODO |
| 0.2 | **F1 (OPD-2 = WIRE):** emit a real "cap rate below floor" warning in `run_financial_model` when purchase cap < `cap_rate_floor`; `chief_strategist` consumes the real signal (its `no_cap_floor_breach` DECLINE input goes live). **Finance-core carve-out — 16 prod + 25 test blast; MOVES every golden number.** Regenerate goldens + **human-review** the new values (must reflect only the added warning); confirm anti-regression tests still RED on true regressions. + RED-on-revert test | F1 | python-eng + finance-interp → capable | TODO |
| 0.3 | Declare `lxml` in `requirements.txt` (belt-and-suspenders; severity downgraded) | F7 | security-eng → std | TODO |
| 0.4 | Replace the silent render swallow (`html_fetcher.py:336-337`) with a warning/signal; declare `playwright` as optional | F8 | security-eng → std | TODO |
| 0.5 | Doc-note `onnxruntime` as an optional opt-in provider dep (no code change) | F9 | docs-maintainer → cheap | TODO |

## Wave 1 — Wiring + anti-regression guard
| ID | Task | Finding | Agent → tier | Status |
| --- | --- | --- | --- | --- |
| 1.1 | Render `YearBreakdown.notes` (OPEX-mutation explanations) in the report + RED-on-revert test | F3 | report-designer → std | TODO |
| 1.2 | Make `synthesize_listing_insights` carry all stated facts (`title/price/sqft/bedrooms/bathrooms/year_built`) + RED-on-revert test | F4 | python-eng + qa → std | TODO |
| 1.3 | `crewai_runner` sets `media_insights`/`media_report` on `OrchestrationResult` + RED-on-revert test | F5 | python-eng → std | TODO |
| 1.4 | `report_cli` passes `media_report` + `provenance` to `write_report` + RED-on-revert test | F6 | python-eng + report-designer → std | TODO |
| 1.5 | **Anti-regression guard:** construct each source model all-fields-non-default, push through each transform, assert no field reverts to default | root cause 2 | qa → std | TODO |

## Wave 2 — CLI honesty + docs
| ID | Task | Finding | Agent → tier | Status |
| --- | --- | --- | --- | --- |
| 2.1 | `ingest_cli` surfaces `result.insights`/`result.photos` (or documents why not) | F10 | python-eng → std | TODO |
| 2.2 | Wire `collect_local_assets` into `--file` mode so media flags do something (or reject them with a clear message) | F11 | python-eng → std | TODO |
| 2.3 | Remove/implement `advisor_cli --debug`; implement or delete | F12 | python-eng → cheap | TODO |
| 2.4 | `advisor_cli --markdown` must not clobber the JSON when `--out` ends `.md` | F13 | python-eng → std | TODO |
| 2.5 | `report_cli --insights` rejects JSON with no recognized fields | F14 | python-eng → std | TODO |
| 2.6 | `ingest_cli --ai` help text (+ honest description) | F15 | python-eng → cheap | TODO |
| 2.7 | `ingest_cli --pretty` documented / split dual purpose | F16 | python-eng → cheap | TODO |
| 2.8 | `advisor_cli --files` error points at a real valid example (add one if none exists) | F17 | python-eng → cheap | TODO |
| 2.9 | `--media-kinds` invalid → argparse usage error, not a raw traceback; `report_cli` missing-file → clean error; fix `address_struct`→`address_structure` in the CLI print | F18, F19, F20 | python-eng → std | TODO |
| 2.10 | T6 living-doc reconcile (README:46-47, market/README:22,86, reports/README) + CHANGELOG:17 **dated note** (not rewrite); **feature→reachable-path test** | T6, root causes 1&4 | docs-maintainer + qa → cheap/std | TODO |

## Wave 3 — Disposition (WIRE-FIRST; OPDs resolved)
| ID | Task | Finding | Agent → tier | Status |
| --- | --- | --- | --- | --- |
| 3.1a | **OPD-1 sequence (`strategist.py`):** (1) audit its `dscr<1.20`/`coc<0.03` thresholds; (2) port any Roger-preferred values into `chief_strategist`'s tunable constants; (3) review the threshold change (code-reviewer + finance-interp), regenerate any verdict goldens; (4) **only then** delete `strategist.py` + its tests. Delete must not precede the review. | T4 | python-eng + finance-interp + code-reviewer → capable | TODO |
| 3.1b | **OPD-3 wire-first:** wire each dead module into a live path — `narrative_builder`+`report_builder`→feed the report; `scenarios.py`→advisor what-ifs (CHANGELOG:17 claims they ship); `regional_income`→public entry point per `market/README`; `utils/markdown`→replace inline `advisor_cli.py:391-411`; `utils/serialize`→serialization sites; `photo_tagger`→ingest if a real consumer exists. **Delete only the un-wireable:** `orchestrator.py` (0-byte), `agents/listing_ingest.py` (true duplicate, no consumer), `advisor/__init__.py` (bypassed facade). Each wired item ships a RED-on-regression test. | T4 | python-eng + code-reviewer → std | TODO |
| 3.2 | **OPD-4 populate:** render every computed-then-discarded field into the report — `RefinancePlan.market_cap_rate` (implement fallback or drop the false docstring), `YearBreakdown.{ltv_pct,available_equity,est_value}` (render stored values instead of recompute at `generator.py:592-596`), `MarketSnapshot.notes`, and the rest. Additive-only. Each field ships a RED-on-regression test. | T5 | python-eng + finance-interp → std | TODO |

## Wave Validation
| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| V.1 | Full battery (`pytest`, coverage ≥80%, `ruff`, `mypy`, `python main.py`) + byte-identical default-off check | qa + code-reviewer → std | TODO |

## Wave Integrate
| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| I.1 | Re-sync, re-run battery, `--no-ff` merge to `main`, reconcile+push the 7-commit origin delta (Roger's timing); record merge sha | release-coordinator → std | TODO (Roger gate) |

## Gate decision records
- **Gate 0 (Truth):** _pending._ No blockers (OPD-2 resolved = wire F1 into engine; Gate 0 review
  must include the re-baselined golden numbers).
- **Gate 1 (Wiring + guard):** _pending._
- **Gate 2 (CLI + docs):** _pending._
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
