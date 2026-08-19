# Mission 3 Sprint Tracker — Wire the bring-your-own ONNX model provider

_Live tracker. The executing orchestrator keeps this current — full updates only (counts + wave
summary + rows), never partial. Date every gate decision. Carry the suite SHA on every count
(Mission 2's hardest-won lesson: a number typed into a doc is a claim with no test behind it — pin it
to a commit)._

**Charter:** `docs/plans/MISSION_3_byo_onnx_provider.md` · **Handoff:** `docs/plans/MISSION_3_HANDOFF.md`
**Manual tests:** `docs/manual testing/MISSION_3_MANUAL_TESTING.md`
**Baseline:** `main @ a00a265` (tree clean; local `main` 1 ahead of `origin/main @ 0ea42fd` — the
unpushed docs backfill; Roger controls the push) · **Branch:** `mission/3-byo-onnx-provider`

> Every subagent prompt issued in this mission MUST carry the GRAPHIFY CONTRACT verbatim (see the
> handoff). Any reachability/blast claim citing the graph is confirmed against the file at the graph's
> own `built_at_commit`, never the current tree (Mission 2's trust-boundary incident).

## Cost routing

Invoke `staff-cost-aware-model-router` at kickoff (standing rule §3a.1) to confirm the tiers below
BEFORE the first dispatch batch — not "only when ambiguous." Record the actual dispatch in each row's
"Agent → tier" column, and log any deviation from the confirmed table **at dispatch time**. Tier→model
mapping: **capable = opus · standard = sonnet · cheap = haiku** (router may map `fable` for the
security review).

## Status legend

`TODO` · `IN-PROGRESS` · `BLOCKED` (needs a prior gate or a product call) · `REVIEW` (agent says done,
orchestrator verifying) · `DONE` (verified inline) · `DEFERRED`

## Overall progress

- Tasks: **0 / 12 DONE** · 0 IN-PROGRESS · 0 BLOCKED · 12 TODO
- Suite **@ `a00a265` (baseline)**: not yet re-measured on-branch — run `pytest` in `airedeal` at Wave
  Sync and pin the count here with its SHA. Mission-start reference (from the roadmap): 630+ tests,
  coverage ≥80%, ruff + mypy clean.
- Gates cleared: **0 / 3** (Gate D pre-impl · Gate V post-impl · Mission gate Roger)
- Product calls outstanding: **1** — flag name / `AIREAL_*` env-var convention / whether the offering
  extends to `main.py` (bounded; `principal-founder-proxy` at Gate V, or earlier if it blocks Discovery)
- Manual-testing doc: **NOT VALIDATED** (authored as an acceptance plan; Roger validates by hand at the
  mission gate — every box currently unchecked)

## Wave summary

| Wave | Name | Tasks | DONE | Status | Gate |
| --- | --- | --- | --- | --- | --- |
| Sync | Wave Sync (re-sync + Wave 0 housekeeping) | 2 | 0 | TODO | — |
| Branch | Wave Branch | 1 | 0 | TODO | — |
| D | Discovery (spec) | 1 | 0 | TODO | **Gate D** |
| GD | Gate D (pre-impl: security + guardian) | 2 | 0 | TODO | blocking |
| Impl | Implementation (wire + tests + docs) | 3 | 0 | TODO | — |
| Val | Validation | 1 | 0 | TODO | **Gate V** |
| GV | Gate V (review + founder call + guardian) | 1 | 0 | TODO | blocking |
| Int | Wave Integrate | 1 | 0 | TODO | Mission gate: Roger |

## Wave Sync

| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| S.1 | `git fetch`; confirm `main` at canonical latest; re-confirm local `main` is 1 ahead of `origin/main` (unpushed `a00a265`) and surface to Roger; run full gate battery green in `airedeal`; pin suite count + SHA in Overall progress | orchestrator (inline) → n/a | TODO |
| S.2 | **Wave 0 housekeeping (backlog #8):** `pip install -e .` in `airedeal` to refresh stale editable-install metadata (`pip show` `0.1.0` → `0.3.0`); confirm `pip show` reads `0.3.0`. No source change | staff-python-engineer → haiku | TODO |

## Wave Branch

| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| B.1 | `git switch main && git switch -c mission/3-byo-onnx-provider` off freshly-synced `main` | orchestrator (inline) → n/a | TODO |

## Wave Discovery

| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| D.1 | CLI-flag + env-var + provider-selection spec: exact proposed flag/env names (`AIREAL_*`), where `register_onnx_provider` is called in the `ingest-listing` lifecycle, how `build_photo_insights` (`photo_insights.py:314-324`) learns to select `"onnx"` without breaking default byte-identity, the synthetic tiny-ONNX + labels fixture plan, and the three error-path messages. No production code | staff-python-engineer → sonnet | TODO |

## Gate D — pre-implementation (blocking)

| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| GD.1 | Security review of the untrusted model-file surface: path handling, `onnxruntime.InferenceSession` on an arbitrary file, oversized/malformed model/labels, error containment. Findings carried into Impl, not deferred | principal-security-engineer → fable | TODO |
| GD.2 | Overclaim VETO on the spec's honesty framing: no "real AI" claim beyond "user-supplied model, project does not vouch for accuracy" | principal-principles-guardian → sonnet | TODO |

### Gate D decision record
_(stub — fill at the gate)_ · Date: ______ · Security: ☐ PASS ☐ CHANGES-REQUIRED · Guardian:
☐ NO VETO ☐ VETO (conditions: ______) · Orchestrator sign-off: ______

## Wave Implementation (≤3 concurrent)

| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| I.1 | Wire flag/env → `register_onnx_provider(model_path, labels_path)` in `ingest-listing`; extend `build_photo_insights` provider selection to reach `"onnx"`; verify `provider_kind="model"` surfaces. Default (no ONNX) stays byte-identical. RED-on-revert for each behaviour | staff-python-engineer → sonnet | TODO |
| I.2 | Synthetic tiny ONNX + labels fixture (committed); tests: happy-path register+select; six-labels-become-confirmed end-to-end; determinism (byte-identical repeat); error paths (missing `onnxruntime`, malformed model, empty/malformed labels). Each RED-on-revert | staff-qa-test-engineer → sonnet | TODO |
| I.3 | Docs: README + `src/core/README.md` (new honest user path) + CHANGELOG `[Unreleased]`; draft §3 "No real AI provider" blocker-row closure (offering 1 delivered; 2 & 3 open). `_Last reconciled_` stamps on living docs | staff-documentation-maintainer → haiku | TODO |

## Wave Validation

| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| V.1 | Full battery in `airedeal`: `pytest` green + coverage ≥80%; `ruff format --check` + `ruff check` clean; `mypy .` clean; `python main.py` + default `ingest-listing` byte-identical to pre-mission (no ONNX registered); re-run every command in the manual-testing doc and confirm each produces its stated result | orchestrator (inline) → n/a | TODO |

## Gate V — post-implementation (blocking)

| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| GV.1 | Code review of the full diff (blast confined to CLI + provider selection; no finance/schema/ontology drift) | staff-code-reviewer → sonnet | TODO |
| GV.2 | Bounded product call: final flag name / `AIREAL_*` env convention / whether the offering extends to `main.py` | principal-founder-proxy → sonnet | TODO |
| GV.3 | Overclaim VETO re-check against the shipped strings/docs | principal-principles-guardian → sonnet | TODO |

### Gate V decision record
_(stub — fill at the gate)_ · Date: ______ · Code review: ☐ APPROVE ☐ CHANGES · Founder call:
______ · Guardian: ☐ NO VETO ☐ VETO · Orchestrator sign-off: ______

## Mission gate (Roger) + Wave Integrate

| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| INT.1 | **Precondition:** Roger runs `docs/manual testing/MISSION_3_MANUAL_TESTING.md`; document-level box reads VALIDATED. Then: `git fetch`; rebase/merge onto latest `main`; re-run full battery post-rebase; `git merge --no-ff mission/3-byo-onnx-provider`; push at Roger's instruction (reconcile the 1-commit origin delta; never force-push). Record merge sha + push result | orchestrator (inline) + Roger → n/a | TODO |

### Mission gate decision record
_(stub)_ · Manual-testing doc VALIDATED by Roger: ☐ · Date: ______ · Merge sha: ______ ·
Pushed: ☐ yes ☐ no (Roger deferred) · Notes: ______
