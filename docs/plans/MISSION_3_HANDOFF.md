# Mission 3 Handoff — Wire the bring-your-own ONNX model provider to a real user path

**How to use this prompt:** Open a fresh Claude Code session at the repo root
(`/home/rtokime/projects/Personal/ai-real-estate-deal-analyzer`) and paste everything between the
BEGIN/END markers verbatim. That session becomes the mission orchestrator. This mission is **chartered,
not yet built** — no code exists for it. The first concrete action is Wave Sync, then Wave Branch.
Roger holds the mission gate (merge + push); the orchestrator never self-approves.

=== BEGIN MISSION PROMPT ===

You are the orchestrator for **Mission 3 — Wire the bring-your-own ONNX model provider to a real,
documented user path** of the AI Real Estate Deal Analyzer (deterministic-first real estate
underwriting tool; solo developer: Roger).

## Mission identity (one read)

The provider registry already contains a fully-built, tested bring-your-own-model path —
`register_onnx_provider(model_path, labels_path)` (`src/core/cv/amenities_defects.py:382`) — that binds
a user-supplied ONNX classifier into the `"onnx"` provider slot and declares its label vocabulary from
`labels_path`. `provider_kind("onnx")` (`amenities_defects.py:644`) already returns `"model"` for it.
**But it has zero callers.** No CLI flag and no env var reaches it: `ingest-listing`'s `--ai` only sets
`use_ai=True` (`src/cli/ingest_cli.py:151`), and `build_photo_insights`
(`src/core/cv/photo_insights.py:314-324`) then hard-selects `provider = "vision" if use_ai else
"local"` — it can never select `"onnx"`. The machinery is real and unreachable.

You will wire **offering 1 of 3** from backlog #3 — **bring-your-own ONNX model only** — to a real user
path: a CLI flag + `AIREAL_*` env vars on `ingest-listing` that call `register_onnx_provider`, plus a
provider-selection change in `build_photo_insights` so the registered `"onnx"` provider is actually
used. Because honest provenance labelling and the 70/30 confirm-don't-fabricate rule landed in Mission
2, `provider_kind="model"` surfaces for free, and a model whose `labels.json` declares them turns the
six filename-inferred labels (`mold_suspected`, `water_leak_suspected`, `ev_charger`, `parking_garage`,
`parking_driveway`, `dishwasher`) from unscored hints into confirmed observations **with no ontology
change**. Blast is near-zero: no `src/core/finance/`, no `src/schemas/models.py` breaking edit.

This is **not** the hosted-API-key offering and **not** a project-shipped ViT — both are explicitly out
of scope. You are wiring an existing seam, not building new capability. Verify every `path:line` against
the real file before touching it (the graph reflects a snapshot commit, not necessarily HEAD).

## Read these first (canonical, in order)

1. `docs/plans/MISSION_3_byo_onnx_provider.md` — the charter (baseline, branch, in/out of scope, waves,
   DoD, agent roster, binding constraints, gates). Authoritative for scope.
2. `docs/plans/MISSION_3_SPRINT_TRACKER.md` — the live task tracker you keep current.
3. `docs/manual testing/MISSION_3_MANUAL_TESTING.md` — the acceptance/manual-test plan you keep
   accurate as fixes land, and that Roger validates by hand at the mission gate.
4. `docs/plans/ROADMAP_TRACKER.md` §1, §3, §4 (backlog #3 detail), §5 — current state, blocker ledger,
   the ONNX offering breakdown, current recommendation.
5. `src/core/README.md` (Optional Providers / ONNX section) and `src/schemas/README.md` — the seams you
   compose; keep the schema additive-only.

Re-read any `path:line` you touch before changing it — Mission 2 found repeated charter path drift.

## Environment (critical — the common conda path is wrong)

Run all project Python in the `airedeal` conda env:
`source /home/rtokime/anaconda3/etc/profile.d/conda.sh && conda activate airedeal`
(NOT `~/miniconda3` — that path does not exist and silently falls back to the wrong interpreter).
Confirm `which python` → `/home/rtokime/anaconda3/envs/airedeal/bin/python`. Note: `onnxruntime` is an
**opt-in** dependency and may not be installed in the env; the missing-`onnxruntime` error path is a
real, testable state, and the synthetic-fixture tests must account for whether it is present.

## Baseline & branch

`base = main @ a00a265, synced 2026-08-19.` Tree clean. **Local `main` is 1 commit ahead of
`origin/main @ 0ea42fd`** — the unpushed docs backfill `a00a265`. Roger controls the push; surface the
delta at Wave Sync and reconcile (never force-push) at Wave Integrate. Branch:
`mission/3-byo-onnx-provider`, cut off freshly-synced `main`.

## What you are building (scope)

* **CLI flag + env → `register_onnx_provider`.** A flag pair (model path + labels path) and matching
  `AIREAL_*` env vars on `ingest-listing`; invoking them calls `register_onnx_provider(model_path,
  labels_path)` before photo insights are built. Exact names are the bounded founder-proxy call below.
* **Provider selection reaches `"onnx"`.** Extend `build_photo_insights`
  (`src/core/cv/photo_insights.py:314-324`) so a registered ONNX provider is selected; default (none
  registered) stays **byte-identical**.
* **`provider_kind="model"` end-to-end.** Verify, don't reinvent — it exists. Confirm provenance +
  report rows reflect `"model"` vs `"heuristic_stub"`.
* **Six labels become confirmable — no ontology change.** A model declaring them flips them to
  detector-confirmed under the existing 70/30 rule. Prove end-to-end; touch no ontology/schema.
* **Error paths** clean (not raw tracebacks): missing `onnxruntime` (`RuntimeError("onnxruntime not
  available; install it to use provider=onnx")`, `amenities_defects.py:271`); malformed model
  (`onnxruntime.InferenceSession` raise, `:288`); malformed/empty labels
  (`ValueError("labels.json must contain a non-empty 'labels' list")`, `:283`).
* **Docs + §3 blocker-row closure** (offering 1 delivered; 2 & 3 open).
* **Wave 0 housekeeping:** `pip install -e .` to refresh stale editable-install metadata (backlog #8).

## Waves & gates

Wave Sync (re-sync + surface origin delta + `pip install -e .` #8; battery green) → Wave Branch
(`mission/3-byo-onnx-provider`) → Wave Discovery (spec) → **Gate D** (security review + guardian
overclaim VETO — both blocking) → Wave Implementation (≤3 concurrent: wiring · tests+fixture · docs) →
Wave Validation (full battery + default byte-identity + every manual-test command runs) → **Gate V**
(code review + bounded founder call + guardian VETO) → **Mission gate (Roger)** → Wave Integrate.
Check every DoD box in the charter before requesting the mission gate.

## Binding constraints (non-negotiable)

1. **Zero `src/core/finance/` diff.** AI produces observations only; the verdict stays in
   `synthesize_thesis` — a model may never author it.
2. **Schema additive-only** (`src/schemas/models.py`) — prefer no change; `provider_kind`/provenance
   already exist.
3. **No ontology change** — the six labels already exist; unlock by declaration, not by editing the set.
4. **Determinism** — same input ⇒ byte-identical output; default (no ONNX) output byte-identical to
   pre-mission.
5. **Honesty** — no "real AI"/"AI-powered" claim beyond "the user supplied their own model, which the
   project does not vouch for." Guardian VETO enforces this.
6. **Security** — `principal-security-engineer` reviews the untrusted model-file surface before impl;
   findings carried, not deferred.
7. **Prove-the-test** — every fix ships a test that turns RED on revert; demonstrate it.
8. **Quality gate** — `ruff format --check` + `ruff check` + `mypy .` clean; coverage ≥80%.
9. **Deps** — `onnxruntime` stays opt-in (not runtime-required); any new declaration justified in the
   commit; runtime-required deps need security sign-off.
10. **Git** — branch off freshly-synced `main`; no PRs; merge only after Roger's mission gate; never
    force-push `main`; reconcile the 1-commit origin delta; push only at Roger's instruction.

## Bounded product call (founder-proxy)

One decision, bounded — do not let it sprawl: (a) the flag name(s) for the model + labels paths;
(b) the `AIREAL_*` env-var names (align with the existing convention — `AIREAL_USE_VISION`,
`AIREAL_VISION_PROVIDER`, `AIREAL_LLM_MODE` are the neighbours); (c) whether the offering extends beyond
`ingest-listing` to `main.py`'s pipeline path (default: no — `ingest-listing` is where `--ai` already
lives). Route to `principal-founder-proxy` at Gate V, or earlier if it blocks Discovery.

## Orchestration protocol

* **Agents (fleet in `.claude/agents/`; ≤3 concurrent):** `staff-python-engineer` (Discovery spec;
  wiring; Wave 0 `pip install -e .`), `principal-security-engineer` (model-file surface review, Gate D),
  `principal-principles-guardian` (overclaim VETO, Gate D + Gate V), `staff-qa-test-engineer`
  (synthetic ONNX fixture + RED-on-regression tests), `staff-documentation-maintainer` (README /
  `src/core/README.md` / CHANGELOG; §3 blocker-row closure), `staff-code-reviewer` (Gate V review),
  `principal-founder-proxy` (bounded naming call). Roger holds the mission gate.
* **Cost routing:** **invoke `staff-cost-aware-model-router` at kickoff** to confirm tiers BEFORE the
  first dispatch batch (standing rule — not "only when ambiguous"). Planner proposal: Discovery/wiring/
  tests/reviews/founder → standard (sonnet); security review → fable; docs + `pip install -e .` → cheap
  (haiku). Record `task → agent → tier` in the tracker and log any deviation at dispatch time.
* **Verify inline:** never trust an agent's "done" — re-run its tests, re-read its diff, revert-check
  each RED test, and tick the DoD yourself before marking DONE.
* **Branch-and-integrate:** Wave Sync = `git fetch`, confirm canonical latest, surface the 1-commit
  origin delta to Roger, `pip install -e .`, re-run the battery green. Wave Branch =
  `git switch main && git switch -c mission/3-byo-onnx-provider`. Wave Integrate (after Validation GREEN
  **and** Roger's mission gate) = `git fetch`, rebase/merge onto latest, re-run the **full** battery
  post-rebase (a pre-rebase green does not count), `git merge --no-ff`, reconcile+push the origin delta
  only at Roger's instruction, record the merge sha. Never self-approve; never force-push `main`.
* **Tracker discipline:** update `docs/plans/MISSION_3_SPRINT_TRACKER.md` after every state change —
  full updates (counts + wave summary + rows), never partial; carry the suite SHA on every count; date
  every gate record.
* **Manual-testing discipline:** keep `docs/manual testing/MISSION_3_MANUAL_TESTING.md` accurate as
  fixes land — every command in it must actually run and produce the stated result by the time the
  mission gate is requested. The boxes are Roger's to flip; the mission gate is not clear until the
  document-level box reads VALIDATED.
* **Research-first + YAGNI:** read the seam before changing it; build only what the charter scopes. Do
  NOT build offering 2 (hosted API key) or offering 3 (shipped ViT), and do NOT add any ontology label.

## GRAPHIFY CONTRACT — every subagent prompt you issue MUST carry this block verbatim

--- BEGIN GRAPHIFY CONTRACT (paste verbatim into the handoff and every subagent prompt) ---
A knowledge graph of this repo lives at `graphify-out/graph.json`. Prefer it over blind Grep sweeps when you need to locate a symbol, trace what calls what, find which module owns a concern, or work out what a change would break.
Useful commands (all read the graph; none need an API key):
    graphify affected "<symbol>" --depth 3    # reverse traversal: what depends on this
    graphify path "<A>" "<B>"                 # shortest path between two nodes
    graphify explain "<node>"                 # plain-language node + neighbours
    graphify god-nodes --top 10               # most-connected architectural hubs
TOKEN DISCIPLINE: NEVER cat/Read graph.json whole (~1600 nodes). NEVER run bare `graphify query` (pass --budget N). For bulk analysis filter the JSON programmatically and print only what you need. Schema: nodes[]={label, source_file, source_location, community}; links[]={relation, source, target, confidence}; plus hyperedges[], built_at_commit. Community names in graphify-out/.graphify_labels.json.
TRUST BOUNDARY: the graph is a snapshot (built_at_commit). If it disagrees with git log, or a source_file no longer exists, treat the graph as a LEAD and confirm against the actual file. Never cite a graph edge without opening what it points at. Do NOT run `graphify update` yourself.
--- END GRAPHIFY CONTRACT ---

## First concrete action

Execute **Wave Sync**: run `git fetch`, `git status --porcelain` (expect clean), and
`git rev-list --left-right --count main...origin/main` (expect `1 0` — the unpushed docs backfill
`a00a265`); confirm `main` is the canonical latest and tell Roger about the 1-commit origin delta so he
decides push timing. Then run the Wave 0 housekeeping (`pip install -e .` in the `airedeal` env; confirm
`pip show ai-real-estate-deal-analyzer` reads `0.3.0`), and run the full gate battery
(`pytest`, `ruff format --check`, `ruff check`, `mypy .`, `python main.py`) green — pin the suite count
+ SHA in the tracker. Then execute **Wave Branch**: `git switch main && git switch -c
mission/3-byo-onnx-provider`. Update the sprint tracker after each step.

=== END MISSION PROMPT ===
