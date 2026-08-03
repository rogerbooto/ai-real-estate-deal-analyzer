# Mission 2 Handoff — Close the end-to-end wiring gaps

**How to use this prompt:** Open a fresh Claude Code session at the repo root
(`/home/rtokime/projects/Personal/ai-real-estate-deal-analyzer`) and paste everything between the
BEGIN/END markers verbatim. That session becomes the mission orchestrator. Roger has approved the
full mission (Waves 0–3) and resolved all four product decisions (2026-08-03) — there are **zero
open blockers**; the resolved decisions are baked in below. Roger still holds the mission gate
(merge + push); the orchestrator never self-approves.

=== BEGIN MISSION PROMPT ===

You are the orchestrator for **Mission 2 — Close the end-to-end wiring gaps** of the AI Real Estate
Deal Analyzer (deterministic-first real estate underwriting tool; solo developer: Roger).

## Mission identity (one read)

An audit found the report asserts things that are false, silently drops computed artifacts before
they reach the report, ships inert/misleading CLI flags, and carries ~350 LOC reachable only from
tests. The root cause is structural: nothing tests end-to-end reachability, and transforms rebuild
models field-by-field so newly-added fields are silently dropped. You will fix the **validated**
defects behind an anti-regression + reachability safety net, on a dedicated branch, one wave at a
time. Every finding was already re-validated by the planner; you are fixing the surviving set, not
re-auditing — but you still verify each fix yourself and prove each test fails on revert.

## Read these first (canonical, in order)
1. `docs/plans/MISSION_2_wiring_gaps.md` — the charter (baseline, surviving scope, waves, DoD,
   binding constraints, the four open product decisions).
2. `docs/plans/MISSION_2_SPRINT_TRACKER.md` — the live task tracker you keep current.
3. `docs/plans/ROADMAP_TRACKER.md` §1, §3, §5 — current state, blocker ledger, recommendation.
4. `src/schemas/README.md` — the model contracts you must keep additive-only.
5. `src/core/reports/README.md` and `src/core/README.md` — the report + engine seams you compose.

The charter's validation table is authoritative for scope; trust it, but re-read any `path:line`
you touch before changing it.

## Environment (critical — the instructions' conda path is wrong)
Run all project Python in the `airedeal` conda env:
`source /home/rtokime/anaconda3/etc/profile.d/conda.sh; conda activate airedeal`
(NOT `~/miniconda3` — that path does not exist and silently falls back to the wrong interpreter).
Verified baseline in that env: `pytest` green, coverage 81.87%, `ruff` + `mypy` clean.

## Baseline & branch (non-standard — read the charter's Baseline section)
`base = fix/sample-listings-paths @ 0d1b976 + uncommitted working-tree work`, synced 2026-08-03.
Local `main` is **ahead of `origin/main` by 7 commits** (Mission 1, unpushed) and the tree is dirty.
The dirty tree IS the intended baseline (the audit + graph were built against it). Do not discard it.

## What you are building (surviving scope only)
* **Wave 0 (Truth):** F2 config/asset pairing; **F1 — wire the cap-floor breach warning INTO
  `run_financial_model` (`src/core/finance/engine.py`)** so it emits a real "cap rate below floor"
  warning when purchase cap < `cap_rate_floor`, and `chief_strategist` consumes the real signal.
  This is the approved finance-core carve-out; it is HIGH-BLAST (`run_financial_model()`
  reverse-affects 16 prod + 25 test files) and **moves every golden number** — regenerate the
  goldens AND human-review the new values (they must reflect only the added warning), then confirm
  the anti-regression suite still turns RED on true regressions. Also: declare `lxml` (F7); replace
  the silent `--render` swallow with a warning + declare `playwright` optional (F8); doc-note
  `onnxruntime` (F9).
* **Wave 1 (Wiring + guard):** F3 render `YearBreakdown.notes`; F4 stop `synthesize_listing_insights`
  dropping stated facts; F5 `crewai_runner` sets `media_insights`/`media_report`; F6 `report_cli`
  passes `media_report`+`provenance`; **plus the anti-regression guard** — construct each source
  model all-fields-non-default, push through each transform, assert nothing reverts to default.
* **Wave 2 (CLI honesty + docs):** F10–F20 (surviving); reconcile living docs (T6) + a dated note on
  `CHANGELOG.md:17` (never rewrite a released section); **a feature→reachable-path test**.
* **Wave 3 (Disposition — WIRE-FIRST):** **prefer wiring dead code into live paths over deleting.**
  `strategist.py` = **reconcile then delete** (audit its `dscr<1.20`/`coc<0.03` thresholds → port
  any Roger-preferred values into `chief_strategist`'s tunable constants → review → **only then**
  delete it + its tests). Wire the other Tier-4 modules (`narrative`/`report_builder`→report;
  `scenarios.py`→advisor what-ifs; `regional_income`→public entry point; `utils/markdown`→replace
  inline `advisor_cli.py:391-411`; `utils/serialize`→serialization sites; `photo_tagger`→ingest if a
  real consumer exists). **Delete only the un-wireable:** `orchestrators/orchestrator.py` (0-byte),
  `agents/listing_ingest.py` (true duplicate, no consumer), `core/advisor/__init__.py` (bypassed
  facade). Tier-5: **populate every unread field into the reports** (schema additive-only). Each
  wired/populated item ships its own RED-on-regression test.

## Waves & gates
Wave Sync (mission-zero commit; surface the origin divergence to Roger) → Wave Branch
(`mission/2-wiring-gaps`) → Wave 0 → **Gate 0** (F1 review must include the re-baselined goldens) →
Wave 1 → **Gate 1** → Wave 2 → **Gate 2** → Wave 3 → **Gate 3** → Wave Validation →
**Mission gate (Roger)** → Wave Integrate. Check every DoD box in the charter before requesting the
mission gate.

## Binding constraints (non-negotiable)
1. **Deterministic core — one approved carve-out:** the ONLY permitted diff inside
   `src/core/finance/` is F1's cap-floor breach warning in `run_financial_model` (Roger approved it
   under OPD-2). It is a pure, deterministic comparison (purchase cap vs `cap_rate_floor`), no
   network; its golden impact is re-baselined + human-reviewed. No other finance-core edits.
2. **Schema additive-only:** `src/schemas/models.py` — nothing renamed, retyped, or removed.
3. **Determinism:** same input ⇒ byte-identical output; `--scenarios` off stays byte-identical to
   pre-mission.
4. **Prove-the-test:** every fix ships a test that turns RED when you revert the fix — demonstrate
   it, do not assume it.
5. **Quality gate:** `ruff format` + `ruff check` + `mypy` clean; coverage ≥80%.
6. **Deps:** new declarations justified in the commit; no new runtime-required dep without
   `principal-security-engineer` sign-off.
7. **Git:** branch off the post-mission-zero tip; no PRs; merge to `main` only after Roger's mission
   gate; never force-push `main` — reconcile the 7-commit origin delta, do not overwrite it.

## Resolved product decisions (Roger, 2026-08-03 — baked in, no action needed)
- **OPD-1 (`strategist.py`) = RECONCILE THEN DELETE.** Enforce the sequence in Wave 3: audit its
  thresholds → port preferred values into `chief_strategist`'s tunable constants → review the
  threshold change → **only then** delete `strategist.py` + tests. Never delete before the review.
- **OPD-2 (F1) = WIRE THE WARNING INTO THE ENGINE.** See Wave 0 above — high-blast, re-baselines the
  goldens deliberately (regenerate + human-review; anti-regression tests still RED on true
  regressions).
- **OPD-3 (Tier 4) = WIRE-FIRST.** Wire dead modules into live paths; delete only the un-wireable
  (`orchestrator.py`, `agents/listing_ingest.py`, `advisor/__init__.py`). Growing surface → each
  wired item ships a RED-on-regression test.
- **OPD-4 (Tier 5) = POPULATE INTO REPORTS.** Render every unread field (additive-only); each ships
  a RED-on-regression test.
Kept out of active scope (do not touch): `income_is_estimated` (REFUTED — it is read at
`engine.py:98`) and F9 `onnxruntime` (deliberate opt-in provider, no CLI path — doc-note only).

## Orchestration protocol
* **Agents (fleet in `.claude/agents/`; ≤3 concurrent):** `staff-release-coordinator` (mission-zero
  commit, integrate), `staff-python-engineer` (fixes), `staff-financial-result-interpreter` (F1/F2
  semantics), `staff-report-experience-designer` (F3/F6 rendering), `staff-qa-test-engineer`
  (guard + reachability tests), `staff-documentation-maintainer` (T6 docs),
  `principal-security-engineer` (F7/F8/F9 deps), `staff-code-reviewer` (all reviews),
  `principal-founder-proxy` (OPD product calls), `principal-principles-guardian` (VETO at every
  gate). Roger holds the mission gate.
* **Cost routing:** confirm tiers with `staff-cost-aware-model-router` at kickoff. Planner proposal:
  docs/mechanical → cheap; CLI/wiring/tests/reviews → standard; F1 finance logic, OPD product
  calls, guardian VETO → capable. Record `task → agent → tier` in the tracker.
* **Verify inline:** never trust an agent's "done" — re-run its tests, re-read its diff, revert-check
  each RED test, and tick DoD yourself before marking DONE.
* **Branch-and-integrate:** Wave Sync = commit the pending work as a mission-zero commit and re-run
  the battery green; Wave Branch = `git switch -c mission/2-wiring-gaps`; Wave Integrate (after
  validation GREEN **and** Roger's mission gate) = `git fetch`, rebase/merge onto latest, re-run the
  full battery post-rebase, `git merge --no-ff`, reconcile+push the origin delta at Roger's
  instruction, record the merge sha. Never self-approve; never force-push `main`.
* **Tracker discipline:** update `docs/plans/MISSION_2_SPRINT_TRACKER.md` after every state change —
  full updates (counts + wave summary + rows), never partial; date every gate record.
* **Research-first + YAGNI:** read the seam before changing it; build only what the charter scopes.
  Do NOT add cross-input building-mismatch validation (root cause 3) — it is a backlog feature, not
  this mission.

## GRAPHIFY CONTRACT — every subagent prompt you issue MUST carry this block verbatim

--- BEGIN GRAPHIFY CONTRACT (paste verbatim into every subagent prompt) ---

A knowledge graph of this repo lives at `graphify-out/graph.json`. Prefer it over blind
Grep sweeps when you need to locate a symbol, trace what calls what, find which module
owns a concern, or work out what a change would break.

Useful commands (all read the graph; none need an API key):
    graphify affected "<symbol>" --depth 3    # reverse traversal: what depends on this
    graphify path "<A>" "<B>"                 # shortest path between two nodes
    graphify explain "<node>"                 # plain-language node + neighbours
    graphify god-nodes --top 10               # most-connected architectural hubs

TOKEN DISCIPLINE — this is a standing repo preference, follow it:
  - NEVER `cat` or Read `graph.json` whole (~1500 nodes, ~3700 edges).
  - NEVER run bare `graphify query` — it emits unranked output that floods context.
    If you must use it, always pass `--budget N`.
  - For bulk analysis, filter the JSON programmatically and print only what you need:

        python -c "
        import json; g=json.load(open('graphify-out/graph.json'))
        for n in g['nodes']:
            if 'dscr' in n['label'].lower():
                print(n['label'], n['source_file'], n['source_location'])
        "

    Schema: nodes[] = label, source_file, source_location, community.
            links[] = relation, source, target, confidence.
            plus hyperedges[] and built_at_commit.
    Community names: graphify-out/.graphify_labels.json

TRUST BOUNDARY: the graph is a snapshot, and `built_at_commit` records when. If it
disagrees with `git log`, or a `source_file` no longer exists, treat the graph as a LEAD
and confirm against the actual file. Never cite a graph edge as evidence for a claim
without opening what it points at. Do not run `graphify update` yourself — the mission
planner refreshes it once; concurrent rebuilds corrupt the output.

--- END GRAPHIFY CONTRACT ---

Note: the graph is currently built at the working tree (`built_at_commit 0d1b976`), so it reflects
current files. Trust file contents over graph metadata.

## First concrete action
Run `git status` and `git log --oneline -3` and confirm the working tree matches the charter's
Baseline section (modified README/CHANGELOG/main.py/schemas/agents/CLIs; untracked
`data/sample_listings/36_kelly_moncton/`, `src/core/media/local.py`, the new tests). Then execute
**Wave Sync**: with `staff-release-coordinator` + `staff-code-reviewer`, review the pending diff,
run the full gate battery in the `airedeal` env, commit it as the mission-zero commit, re-run the
battery green, and tell Roger that local `main` is ahead of `origin/main` by 7 so he can decide push
timing. Then **Wave Branch**: `git switch -c mission/2-wiring-gaps`. Update the sprint tracker after
each step.

=== END MISSION PROMPT ===
