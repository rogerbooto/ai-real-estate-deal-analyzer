# Mission 3 — Wire the bring-your-own ONNX model provider to a real user path

_Charter. Owned by the mission-planner; the executing orchestrator keeps the sprint tracker current,
not this file. `path:line` anchors below were verified against the baseline commit named in §Baseline;
re-read any you touch before changing it._

---

## Executive Summary

The provider registry already contains a **fully-built, tested bring-your-own-model path**:
`register_onnx_provider(model_path, labels_path)` (`src/core/cv/amenities_defects.py:382`) binds a
user-supplied ONNX classifier into the `"onnx"` provider slot, declares its label vocabulary from the
`labels_path` (which *is* the capability declaration), and `provider_kind("onnx")`
(`amenities_defects.py:644`) already returns `"model"` for it because the bound function is not one of
the built-in stubs. **It has zero callers.** No CLI flag and no environment variable reaches it — the
`ingest-listing` `--ai` flag only flips `use_ai=True` (`src/cli/ingest_cli.py:151`), and
`build_photo_insights` (`src/core/cv/photo_insights.py:314`) then hard-selects
`provider = "vision" if use_ai else "local"` (`photo_insights.py:324`) — it can never select `"onnx"`.
So the machinery is real, tested, and unreachable.

This mission wires **one** of the three offerings in backlog #3 — **offering 1 of 3: bring-your-own
ONNX model** — to a real, documented user path: a CLI flag + environment variables on `ingest-listing`
that call `register_onnx_provider`, and a provider-selection change in `build_photo_insights` so the
registered `"onnx"` provider is actually used. Because `provider_kind` and the honest provenance
labelling already landed in Mission 2, `provider_kind="model"` and the AI-influence framing surface
end-to-end for free. And because a provider's declared vocabulary is what flips a label from "nothing
can see this" to "something looked" (Mission 2 R-6, 70/30 confirm-don't-fabricate), a user model whose
`labels.json` declares them makes the **six filename-inferred labels** — `mold_suspected`,
`water_leak_suspected`, `ev_charger`, `parking_garage`, `parking_driveway`, `dishwasher` — move from
unscored hints to confirmed observations, **with no ontology change**.

Blast is near-zero: **no `src/core/finance/` diff, no `src/schemas/models.py` diff.** The work is
additive CLI/env wiring plus a provider-selection extension at an existing seam.

---

## Baseline

`base = main @ a00a265, synced 2026-08-19.`

- Tree clean at charter time (`git status --porcelain` empty).
- **Local `main` is 1 commit ahead of `origin/main`** (`origin/main @ 0ea42fd`): the unpushed docs
  backfill commit `a00a265` ("docs(missions): backfill Roger-facing manual-test + plain-English docs;
  reconcile roadmap ledger to as-shipped v0.3.0"). Roger controls the push. Wave Sync must re-check
  this and surface it; Wave Integrate must account for it (do **not** push without Roger).
- Verified env: `airedeal` conda env at `/home/rtokime/anaconda3` (NOT `~/miniconda3`).
- Every `path:line` in this charter was read against `a00a265`. The graphify graph is a lead only;
  confirm against the file at its own `built_at_commit`.

**Carried-forward blocker (does NOT gate this mission):** the GitHub SSH **signing** key is still
unregistered (§3 ledger) — commits SSH-sign locally but show Unverified. Unchanged by this work.

---

## Branch

`mission/3-byo-onnx-provider` — cut off freshly-synced `main` in Wave Branch. All mission work commits
here; nothing lands on `main` until Roger's mission gate, then Wave Integrate merges `--no-ff`.

---

## In scope

1. **CLI flag + env var → `register_onnx_provider`.** Add a real, documented way to register a
   user-supplied ONNX model on the `ingest-listing` CLI: a flag pair (model path + labels path) and
   matching `AIREAL_*` environment variables. Calling it invokes `register_onnx_provider(model_path,
   labels_path)` before photo insights are built. The exact flag name and env-var names are a **bounded
   founder-proxy product call** (see Waves / roster) — align with the existing `AIREAL_*` convention.
2. **Provider selection reaches `"onnx"`.** Extend `build_photo_insights`
   (`src/core/cv/photo_insights.py:314-324`) so that when an ONNX provider has been registered it is the
   selected provider, instead of the current binary `"vision" | "local"`. This is the crux seam; keep it
   minimal and explicit. Default behaviour (no ONNX registered) stays **byte-identical**.
3. **`provider_kind="model"` surfaces end-to-end.** Verify (do not re-implement — it exists from
   Mission 2) that a registered ONNX model stamps `provenance.provider_kind="model"` through
   `PhotoInsights` and any report/appendix rows, distinct from the `"heuristic_stub"` the stubs produce.
4. **The six filename labels become confirmable — no ontology change.** With a model whose `labels.json`
   declares them, `mold_suspected`, `water_leak_suspected`, `ev_charger`, `parking_garage`,
   `parking_driveway`, `dishwasher` move from unscored filename hints (case 2) to detector-confirmed
   observations (case 1) via the existing 70/30 corroboration rule. Prove this end-to-end; change **no**
   ontology or schema file to achieve it.
5. **Security review of the user-supplied model-file surface.** Loading an arbitrary ONNX file path
   from the CLI/env is untrusted input reaching `onnxruntime.InferenceSession`. `principal-security-engineer`
   reviews the surface (path handling, error containment, what a malicious/oversized/malformed model or
   labels file can do) as a pre-implementation gate, and the implementation carries its findings.
6. **Honest framing.** Every user-facing string, help text, and doc line must not overclaim: this is the
   **user's own model**, and the project does not vouch for its accuracy. "Real AI provider" language is
   only honest to the extent that it says *the user supplied it*. `principal-principles-guardian` holds
   an overclaim VETO as a pre-implementation gate and at validation.
7. **Tests.** Every shipped behaviour ships a RED-on-regression test (revert the fix → the test fails).
   Includes: a synthetic tiny ONNX model + labels fixture, the happy-path registration/selection, the
   six-labels-become-confirmed path, determinism (same input ⇒ byte-identical output), and the error
   paths (missing `onnxruntime`; malformed model; malformed/empty labels).
8. **Docs.** README / `src/core/README.md` / CHANGELOG `[Unreleased]` updated to describe the new user
   path honestly; close the §3 "No real AI provider" blocker row's ONNX slice (offering 1) with the
   caveat that offerings 2 (hosted API key) and 3 (shipped ViT) remain open.
9. **Wave 0 housekeeping (one line, not a headline):** re-run `pip install -e .` in the `airedeal` env
   to refresh the stale editable-install metadata (backlog #8 — `pip show` reads `0.1.0` vs pyproject
   `0.3.0`). Cosmetic; no source change.

## Out of scope (explicitly)

- **Offering 2 — user-supplied hosted-API-key vision model.** Needs the cost / non-determinism /
  key-hygiene policy and a caching story; not this mission.
- **Offering 3 — a project-shipped fine-tuned real-estate ViT.** Training data, licensing, model
  distribution, and an accuracy claim the project would own; not this mission.
- **Any ontology change.** The six labels already exist in the closed set; do not add, rename, or retype
  any label. If a label seems to need adding, stop — that is a signal the approach drifted.
- **Any `src/core/finance/` edit.** Zero finance-core diff. The AI layer produces observations only;
  the BUY/CONDITIONAL/DECLINE verdict stays in the deterministic `synthesize_thesis` — a model may
  observe, it may never author the verdict.
- **Any `src/schemas/models.py` breaking change.** Schema edits, if any, are strictly **additive** and
  must be justified; prefer none. `provider_kind`/provenance already exist — reuse them.
- **`main.py`'s pipeline provider path**, unless the founder-proxy product call explicitly extends the
  offering there. Default scope is the `ingest-listing` CLI seam where `--ai` already lives.

---

## Waves & gates

`Wave Sync → Wave Branch → Wave Discovery → Gate D (pre-impl: security + guardian) → Wave
Implementation → Wave Validation → Gate V (code review + bounded founder call + guardian) → Mission
gate (Roger) → Wave Integrate.`

| Wave | What happens |
| --- | --- |
| **Sync** | Phase 0 re-sync: `git fetch`; confirm `main` fast-forwards to canonical latest; re-confirm the 1-commit-ahead-of-origin state and surface it to Roger. Do **not** push. Also Wave 0 housekeeping: `pip install -e .` (backlog #8). Re-run the gate battery green in `airedeal`. |
| **Branch** | `git switch main && git switch -c mission/3-byo-onnx-provider`. |
| **Discovery** | `staff-python-engineer` produces a short CLI-flag + env-var + provider-selection spec: exact flag/env names (proposed), where `register_onnx_provider` is called in the CLI lifecycle, how `build_photo_insights` learns to select `"onnx"`, and the synthetic-fixture plan. No production code yet. |
| **Gate D (pre-impl)** | `principal-security-engineer` reviews the untrusted-model-file surface; `principal-principles-guardian` reviews the honesty/overclaim framing of the spec. Both are **blocking**. The guardian holds a VETO. |
| **Implementation** | ≤3 concurrent: (a) `staff-python-engineer` wires flag/env → `register_onnx_provider` and extends provider selection; (b) `staff-qa-test-engineer` writes the synthetic ONNX fixture + RED-on-regression tests (happy path, six-labels-confirmed, determinism, error paths); (c) `staff-documentation-maintainer` updates README/`src/core/README.md`/CHANGELOG and drafts the §3 blocker-row closure. |
| **Validation** | Full battery in `airedeal`: `pytest` green + coverage ≥80%; `ruff format --check` + `ruff check` clean; `mypy .` clean; default `python main.py` and default `ingest-listing` byte-identical to pre-mission (no ONNX registered). Refresh the manual-testing doc so **every command in it actually runs and produces the stated result**. |
| **Gate V** | `staff-code-reviewer` reviews the diff; `principal-founder-proxy` makes the bounded product call (flag name / `AIREAL_*` env convention / whether the offering extends to `main.py`); `principal-principles-guardian` re-checks overclaim (VETO). |
| **Mission gate (Roger)** | Roger runs `docs/manual testing/MISSION_3_MANUAL_TESTING.md` by hand and flips the boxes. Not clear until the document-level box reads VALIDATED. Roger holds this gate; the orchestrator never self-approves. |
| **Integrate** | Only after Validation GREEN **and** Roger's mission gate: `git fetch`; rebase/merge onto latest `main`; re-run the **full** battery post-rebase (a pre-rebase green does not count); `git switch main && git merge --no-ff mission/3-byo-onnx-provider`; **push only at Roger's instruction** (remember the pre-existing 1-commit origin delta — reconcile, never force-push). Record the merge sha + push result in the tracker. |

---

## Definition of Done

- [ ] `ingest-listing` exposes a documented flag pair + `AIREAL_*` env vars that register a
      user-supplied ONNX model, and calling them invokes `register_onnx_provider(model_path,
      labels_path)` before photo insights are built.
- [ ] `build_photo_insights` selects the registered `"onnx"` provider when one is registered; with none
      registered, default output is **byte-identical** to pre-mission.
- [ ] `provenance.provider_kind` reads `"model"` end-to-end for a registered ONNX model, distinct from
      `"heuristic_stub"`, and any report/appendix provenance row reflects it.
- [ ] With a model declaring them, the six labels (`mold_suspected`, `water_leak_suspected`,
      `ev_charger`, `parking_garage`, `parking_driveway`, `dishwasher`) become detector-confirmed
      observations under the existing 70/30 rule — proven end-to-end, with **zero** ontology/schema change.
- [ ] The three error paths return clean, actionable messages (not raw tracebacks): missing
      `onnxruntime`; malformed/unreadable model file; malformed/empty labels file.
- [ ] Every shipped behaviour has a RED-on-regression test, demonstrated (revert → RED → restore →
      GREEN), including a committed synthetic tiny ONNX + labels fixture.
- [ ] `pytest` green, coverage ≥80%; `ruff format --check` + `ruff check` clean; `mypy .` clean.
- [ ] **No** `src/core/finance/` diff; **no** breaking `src/schemas/models.py` diff (additive-only if any).
- [ ] `principal-security-engineer` signed off on the model-file surface; `principal-principles-guardian`
      lifted its overclaim VETO; `principal-founder-proxy` made the bounded naming call.
- [ ] README / `src/core/README.md` / CHANGELOG `[Unreleased]` describe the new path honestly; the §3
      "No real AI provider" blocker row records offering 1 (ONNX) as delivered, offerings 2 & 3 open.
- [ ] Backlog #8 (`pip install -e .` reinstall) done in Wave Sync.
- [ ] **NON-NEGOTIABLE:** The manual tests in `docs/manual testing/MISSION_3_MANUAL_TESTING.md` have
      been conducted and validated by Roger — **every** test case marked VALIDATED in its status box, and
      the document-level box reading VALIDATED. **This is a precondition of the founder gate; the mission
      gate cannot be requested until this line is satisfiable.**

---

## Agent roster (task → agent → model tier; ≤3 concurrent per wave)

> `staff-cost-aware-model-router` **must be invoked at dispatch time** (standing rule §3a.1) to confirm
> the tier assignments below before the first batch. Record `task → agent → tier` and any deviation at
> dispatch time, not in a post-mortem. Tier→model mapping used by prior missions: capable=opus ·
> standard=sonnet · cheap=haiku (the router may map the `fable` tier for the security review).

| Wave | Task | Agent | Tier |
| --- | --- | --- | --- |
| Discovery | CLI-flag + env + provider-selection spec, synthetic-fixture plan | `staff-python-engineer` | sonnet |
| Gate D | Security review of the untrusted ONNX-file-path surface | `principal-security-engineer` | fable |
| Gate D | Honesty / overclaim VETO on the spec framing | `principal-principles-guardian` | sonnet |
| Impl | Wire flag/env → `register_onnx_provider`; extend `build_photo_insights` selection; surface `provider_kind` | `staff-python-engineer` | sonnet |
| Impl (parallel) | pytest incl. synthetic ONNX fixture, six-labels-confirmed, error paths, determinism | `staff-qa-test-engineer` | sonnet |
| Impl (parallel) | Docs (README / `src/core/README.md` / CHANGELOG); close §3 blocker row's ONNX slice | `staff-documentation-maintainer` | haiku |
| Sync (Wave 0) | `pip install -e .` reinstall (backlog #8 housekeeping) | `staff-python-engineer` | haiku |
| Gate V | Code review of the full diff | `staff-code-reviewer` | sonnet |
| Gate V | Bounded product call (flag name / `AIREAL_*` env convention / `main.py` extent) | `principal-founder-proxy` | sonnet |

Roger holds the mission gate (merge + push). No agent self-approves it.

---

## Binding constraints (non-negotiable)

1. **Deterministic core untouched.** Zero diff inside `src/core/finance/`. The AI layer produces
   **observations only**; the BUY/CONDITIONAL/DECLINE verdict comes from `synthesize_thesis` and a model
   may never author it.
2. **Schema additive-only.** No rename/retype/removal in `src/schemas/models.py`; prefer no change at
   all — `provider_kind` and provenance already exist.
3. **No ontology change.** The six labels already exist in the closed set; the mission unlocks them by
   *declaration*, not by editing the vocabulary.
4. **Determinism.** Same input ⇒ byte-identical output. Default (no ONNX registered) output stays
   byte-identical to pre-mission.
5. **Honesty.** No "real AI" / "AI-powered" claim beyond "the user supplied their own model, which the
   project does not vouch for." Guardian VETO enforces this.
6. **Security.** The user-supplied model-file surface is reviewed by `principal-security-engineer` before
   implementation; findings are carried, not deferred.
7. **Prove-the-test.** Every fix ships a test that turns RED on revert — demonstrated, not assumed.
8. **Quality gate.** `ruff format --check` + `ruff check` + `mypy .` clean; coverage ≥80%.
9. **Deps.** `onnxruntime` stays an opt-in dependency (do not make it runtime-required). Any new
   declaration is justified in the commit and, if runtime-required, needs security sign-off.
10. **Git.** Branch off freshly-synced `main`; no PRs; merge to `main` only after Roger's mission gate;
    never force-push `main`; reconcile the 1-commit origin delta rather than overwrite it; push only at
    Roger's instruction.

---

## Gates summary

- **Gate D (pre-implementation):** security review (surface) + guardian overclaim VETO — both blocking.
- **Gate V (post-implementation):** code review + bounded founder-proxy naming call + guardian
  overclaim VETO.
- **Mission gate (Roger only):** manual-testing doc fully VALIDATED by Roger; then merge; then push at
  Roger's instruction. The orchestrator never self-approves.
