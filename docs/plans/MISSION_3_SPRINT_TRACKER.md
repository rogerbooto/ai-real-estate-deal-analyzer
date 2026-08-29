# Mission 3 Sprint Tracker — Wire the bring-your-own ONNX model provider

_Live tracker. The executing orchestrator keeps this current — full updates only (counts + wave
summary + rows), never partial. Date every gate decision. Carry the suite SHA on every count
(Mission 2's hardest-won lesson: a number typed into a doc is a claim with no test behind it — pin it
to a commit)._

**Charter:** `docs/plans/MISSION_3_byo_onnx_provider.md` · **Handoff:** `docs/plans/MISSION_3_HANDOFF.md`
**Manual tests:** `docs/manual testing/MISSION_3_MANUAL_TESTING.md`
**Baseline:** `main @ 6d9c000` (tree clean) · **Branch:** `mission/3-byo-onnx-provider` (cut
2026-08-20 off freshly-synced `main`)

> **Charter-baseline correction (2026-08-20, orchestrator).** The charter's stated baseline
> `main @ a00a265` with a 1-commit unpushed origin delta was **stale on all three counts**. Verified
> at Wave Sync: `main` was at `5dcdf1a` (three commits ahead of the charter's baseline — `8e3eeed`,
> `c70507c`, `5dcdf1a`), `origin/main` was **in sync** (`git rev-list --left-right --count
> main...origin/main` → `0 0`), and the tree was **not clean** — it carried Roger's uncommitted
> Mission 2 manual-validation record on branch `docs/mission-2-manual-validation`. On Roger's call
> that record was committed (`6d9c000`, SSH-signed) and fast-forwarded into `main`, which is the
> baseline this mission actually builds on. **A 1-commit origin delta now exists again, but it is
> `6d9c000`, not `a00a265`** — see S.1 below. This is the second consecutive mission in which a
> charter `path:line`/baseline claim drifted from HEAD; every anchor in this mission is re-verified
> against the file before use.

> Every subagent prompt issued in this mission MUST carry the GRAPHIFY CONTRACT verbatim (see the
> handoff). Any reachability/blast claim citing the graph is confirmed against the file at the graph's
> own `built_at_commit`, never the current tree (Mission 2's trust-boundary incident).

## Cost routing

Invoke `staff-cost-aware-model-router` at kickoff (standing rule §3a.1) to confirm the tiers below
BEFORE the first dispatch batch — not "only when ambiguous." Record the actual dispatch in each row's
"Agent → tier" column, and log any deviation from the confirmed table **at dispatch time**. Tier→model
mapping: **capable = opus · standard = sonnet · cheap = haiku** (router may map `fable` for the
security review).

### Routing confirmed — 2026-08-20, before the first dispatch

`staff-cost-aware-model-router` ran at kickoff and returned the table below. It **held** the planner's
proposal on every tier but made one **structural change** and one **explicit refusal to downgrade**:

1. **Structural change — the founder-proxy call moves before Discovery** (was: Gate V). The flag and
   env-var names are inputs to the spec, not post-hoc validation of it; deciding them at Gate V would
   leave Discovery writing against placeholder names and force rework at Implementation. **Accepted**
   — the charter already permitted this ("at Gate V, or earlier if it blocks Discovery"), and it
   does block Discovery. Tracked as new row PD.1; the old GV.2 row is struck.
2. **Refusal to downgrade — security review stays `fable`.** The router argued the untrusted
   model-file surface (a user-supplied `.onnx` deserialized by `onnxruntime.InferenceSession`, plus
   `labels.json` parsing and path handling) is a false economy at a lower tier, because findings must
   be *carried into* production code and tests rather than reviewed for plausibility. **Accepted.**
3. **Refusal to downgrade — QA (I.2) stays `sonnet`, not `haiku`.** Because `onnxruntime` **is**
   installed in `airedeal` (1.22.0), the missing-dependency error path cannot be tested by absence and
   needs a deliberate monkeypatch/import-shim strategy — a design call, not mechanical test-writing.
   **Accepted.**

The router also independently re-verified all four charter anchors against HEAD and found them
correct: `register_onnx_provider` `amenities_defects.py:382`, `provider_kind` `:644`,
`build_photo_insights` `photo_insights.py:314-324` (confirmed still hardcoding
`provider = "vision" | "local"`), `ingest_cli.py:151`.

| Task | Agent | Tier | Confirmed / deviation |
| --- | --- | --- | --- |
| PD.1 product call | `principal-founder-proxy` | sonnet | **moved** out of Gate V to pre-Discovery |
| D.1 spec | `staff-python-engineer` | sonnet | as proposed |
| GD.1 security | `principal-security-engineer` | **fable** | as proposed; downgrade explicitly refused |
| GD.2 guardian | `principal-principles-guardian` | sonnet | as proposed |
| I.1 wiring | `staff-python-engineer` | sonnet | as proposed |
| I.2 tests + fixture | `staff-qa-test-engineer` | sonnet | as proposed; downgrade explicitly refused |
| I.3 docs | `staff-documentation-maintainer` | haiku | as proposed |
| GV.1 code review | `staff-code-reviewer` | sonnet | as proposed |
| GV.3 guardian re-check | `principal-principles-guardian` | sonnet | as proposed |

No task was merged, split, or dropped. Deviations from this table are logged at dispatch time in the
row itself.

## Status legend

`TODO` · `IN-PROGRESS` · `BLOCKED` (needs a prior gate or a product call) · `REVIEW` (agent says done,
orchestrator verifying) · `DONE` (verified inline) · `DEFERRED`

## Overall progress

- Tasks: **16 / 17 DONE** · 0 IN-PROGRESS · 1 TODO _(17: +2 blocker fixes, +1 guardian-required note, +1 lockfile regen, over the original 13)_ _(15, not 13: blockers B-1 and B-2 added two unplanned fix tasks, both now DONE)_
  _(13, not 12: the bounded founder-proxy product call was promoted out of Gate V into its own
  pre-Discovery gate — see the cost-routing record below.)_
- Suite **NOW (on-branch, 2026-08-20, cold cache, JUnit-verified)**: **684 passed, 0 failed, 0
  skipped**, coverage **87.20%**; also **684 passed in a CI-equivalent clean venv** (regenerated
  `requirements-dev.lock`, numpy 2.2.6, ORT 1.23.2); ruff format/check clean (215 files); `mypy .` clean (213
  files); `python main.py` byte-identical to pre-mission baseline. Branch-point reference below.
- Suite **@ `6d9c000` (branch point, measured 2026-08-20 in `airedeal`)**: **638 passed**, 0 failed
  (`pytest` exit 0), coverage **86.09%** (80% gate met). `ruff format --check` clean (211 files),
  `ruff check` clean, `mypy .` clean (209 source files), `python main.py` exit 0 → verdict `DECLINE`.
  Tests-tree digest `155abcab9887fb22` (sha256 over `tests/**/*.py`). Default-path determinism
  confirmed: two consecutive `python main.py` runs byte-identical
  (`545e22b20b967b37c5b7ba20477f9df7c85f5b5a7c151f2e0d79b543d69d31f0`) — this is the pre-mission
  reference the "default stays byte-identical" constraint is measured against.
- Gates cleared: **4 / 4** — ☑ Pre-D product call · ☑ Gate D pre-impl · ☑ **Gate V post-impl (2026-08-20)** · ☑ **Mission gate — CLEARED 2026-08-29** (Roger's manual pass 9/9, then merged `--no-ff` as **`8b59399`** and pushed to `origin/main` at his instruction). **Mission 3 is SHIPPED.**
- Product calls outstanding: **0** — the one bounded call is **CLOSED**, see the PD.1 decision
  record. It covered flag name(s) / `AIREAL_*` env-var convention /
  whether the offering extends to `main.py`, plus the flag-vs-env precedence rule and the
  half-a-pair (model without labels) behaviour. It was promoted to a pre-Discovery blocking gate on
  the router's recommendation — the names are *inputs* to the Discovery spec, so deciding them at
  Gate V would have forced spec and implementation rework. Locked answers: `--onnx-model` /
  `--onnx-labels`, `AIREAL_ONNX_MODEL` / `AIREAL_ONNX_LABELS`, no `main.py` extension, flag > env
  per-field, half-a-pair is a hard error.
- Manual-testing doc: ☑ **VALIDATED (Roger, 2026-08-29)** — **9 / 9 cases PASS**, 0 FAIL, 0 BLOCKED,
  no blocking issues. Driven by hand in `airedeal` on this branch with `OUT=/tmp/m3`: BYO fixture
  built and run end-to-end, `selected_provider='onnx'` / `provider_kind='model'` observed, **both**
  adjudication branches (confirmed **and** contested) reproduced in one run, flag-over-env precedence
  confirmed per field, ONNX outranking `--ai` confirmed, `main.py` byte-identical
  (`545e22b2…`) with the ONNX env vars set, all 8 error paths clean with `exit=1` and no traceback,
  cold-vs-warm-cache output byte-identical, and the whole suite green (**684 passed**, **87.20%**,
  ruff 216 files + mypy 214 files clean). The DEFERRED table was reviewed and accepted.

## Wave summary

| Wave | Name | Tasks | DONE | Status | Gate |
| --- | --- | --- | --- | --- | --- |
| Sync | Wave Sync (re-sync + Wave 0 housekeeping) | 2 | 2 | **DONE** | — |
| Branch | Wave Branch | 1 | 1 | **DONE** | — |
| PD | Pre-Discovery bounded product call | 1 | 1 | **DONE** | cleared |
| D | Discovery (spec) | 1 | 1 | **DONE** | **Gate D** |
| GD | Gate D (pre-impl: security + guardian) | 2 | 2 | **DONE — CLEARED** | ✅ 2026-08-20 |
| Impl | Implementation (wire + tests + docs) | 3 | 3 | **DONE** (+2 unplanned blocker fixes) | — |
| Val | Validation | 1 | 1 | **DONE** | **Gate V** |
| GV | Gate V (review + guardian) | 2 | 2 | **DONE — CLEARED** | ✅ 2026-08-20 |
| Int | Wave Integrate | 1 | 1 | **DONE 2026-08-29** — merged `8b59399`, pushed | ✅ Mission gate cleared |

## Wave Sync

| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| S.1 | `git fetch`; confirm `main` at canonical latest; surface the origin delta to Roger; run full gate battery green in `airedeal`; pin suite count + SHA in Overall progress | orchestrator (inline) → n/a | **DONE** 2026-08-20 |
| S.2 | **Wave 0 housekeeping (backlog #8):** `pip install -e .` in `airedeal` to refresh stale editable-install metadata (`pip show` `0.1.0` → `0.3.0`); confirm `pip show` reads `0.3.0`. No source change | orchestrator (inline) → n/a **[deviation]** | **DONE** 2026-08-20 |

**S.1 result.** Charter's baseline and origin-delta claims were both wrong — see the correction note
at the top of this tracker. Actual: `main` was at `5dcdf1a`, `origin/main` in sync at `5dcdf1a`, tree
dirty with Roger's Mission 2 validation record. Roger chose to commit that record and merge it to
`main` before the branch cut; done as `6d9c000` (SSH-signed, fast-forwarded into `main`). Battery run
green on `6d9c000` — figures pinned under Overall progress. **Open item for Roger: `main` is now 1
commit ahead of `origin/main` (`6d9c000`, the Mission 2 validation record). Not pushed — push timing
is Roger's call; reconcile at Wave Integrate, never force-push.**

**S.2 result.** Backlog #8 **closed**. `pip install -e .` in `airedeal` rebuilt the editable install;
`pip show ai-real-estate-deal-analyzer` now reads **`0.3.0`** (was `0.1.0`). No source change, no
diff. **Deviation from the routed table, logged at dispatch time:** the router assigned this to
`staff-python-engineer → haiku`; the orchestrator ran it inline instead. Rationale — it is a single
shell command with a single-line verification and zero source diff, so dispatching an agent would
have cost more than the task. Tier intent (cheapest available) is honoured; no capability was
skipped.

**Also verified at S.1, and it changes the QA design.** `onnxruntime` **is** installed in `airedeal`
(**1.22.0**). The charter assumed it might be absent and treated "missing `onnxruntime`" as a state
reachable by simply not installing it. It is not reachable that way here: the
`RuntimeError("onnxruntime not available; install it to use provider=onnx")` path
(`amenities_defects.py:271`) must be tested by monkeypatching or import-shimming. Carried into I.2.

## Wave Branch

| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| B.1 | `git switch main && git switch -c mission/3-byo-onnx-provider` off freshly-synced `main` | orchestrator (inline) → n/a | **DONE** 2026-08-20 |

**B.1 result.** Branch `mission/3-byo-onnx-provider` cut off `main @ 6d9c000`. Working tree clean at
the cut. No commits on the branch yet.

## Pre-Discovery — bounded product call (blocking)

Promoted out of Gate V on the router's recommendation (see the routing record above): the names this
call decides are inputs to the D.1 spec, so Discovery cannot start clean without them.

| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| PD.1 | Bounded founder call — (a) CLI flag name(s) for the model + labels paths on `ingest-listing`; (b) `AIREAL_*` env-var names, matched to the existing convention (`AIREAL_USE_VISION`, `AIREAL_VISION_PROVIDER`, `AIREAL_LLM_MODE`); (c) whether the offering extends beyond `ingest-listing` to `main.py` (charter default: **no**); plus the flag-vs-env **precedence rule** and the behaviour when only one half of the model/labels pair is supplied | principal-founder-proxy → sonnet | **DONE** 2026-08-20 |

### PD.1 decision record — 2026-08-20, `principal-founder-proxy`

**Decided. Nothing escalated to Roger** — the agent reported no HALT-CONSULT trigger: the change is
additive CLI/env wiring, reversible, does not touch `FinancialInputs`/`FinancialForecast`, and stays
inside the documented `AIREAL_*` convention. Every clause below traces to a `file:line` the agent
read or to the charter's own text.

| | Decision |
| --- | --- |
| **(a) CLI flags** | **two** flags: `--onnx-model` (str, default `None`) and `--onnx-labels` (str, default `None`) on `ingest-listing` |
| **(b) Env vars** | `AIREAL_ONNX_MODEL` and `AIREAL_ONNX_LABELS` — **no** `_PATH` suffix |
| **(c) Extends to `main.py`** | **☑ no** (charter default confirmed) |
| **Precedence** | per-field, independent: CLI flag > env var > unset |
| **Half-a-pair** | **hard config error** — non-zero exit naming the missing half; never a silent fallback |
| **Escalated to Roger** | ☐ (not required) |

**Reasoning worth carrying forward:**

- **Two flags, not one combined `--onnx-provider "model:labels"`.** `register_onnx_provider` takes
  two required paths, and every existing path flag on this CLI (`--url`, `--file`, `--photos`,
  `--out-cache`) is a single-purpose string with no `-path` suffix. A combined flag would also make
  the supply-one-forget-the-other error harder to catch at the argparse layer.
- **`--ai` is NOT required to activate ONNX.** Pointing at a model file is already the deliberate,
  explicit signal; requiring three flags to turn on one thing is redundant ceremony. The charter
  itself frames the trigger as "an ONNX provider has been registered," not "the AI flag is also set."
  **Resulting selection precedence: `onnx` (if registered) > `vision` (if `--ai`) > `local`.** `--ai`
  keeps its present meaning standalone.
- **Env vars read by bare `os.getenv()` at the point of use — NOT via `InputsLoader`.** The loader's
  `AIREAL_*` list (`src/inputs/inputs.py:31-44`) serves `AppInputs.run.*` for `main.py`'s pipeline,
  and `ingest_cli.py` never touches it. The real precedent for a standalone module reading its own
  `AIREAL_*` var directly is `AIREAL_USE_VISION` (`cv_tagging_orchestrator.py:19`) and `AIREAL_DEBUG`
  (`crewai_components.py:118`). Routing through `InputsLoader` was rejected because it would quietly
  widen scope toward the `main.py` pipeline, which (c) rules out.
- **Precedence mirrors `--scenarios`** (`main.py:227-228`, "explicit CLI flag > env > default") — the
  only existing flag-vs-env precedent in the repo, so it is matched rather than reinvented.
- **Loud fail on misconfig.** A half-registered model path falling silently back to a stub is exactly
  the untraceable-number risk this project exists to prevent.

### Orchestrator verification of PD.1 (inline, 2026-08-20)

The agent's load-bearing scope claim was **independently confirmed before acceptance**, because
decision (c) rests entirely on it: `main.py`'s pipeline reaches CV through
`src/agents/listing_analyst.py:104` → `CvTaggingOrchestrator.analyze_paths`
(`src/orchestrators/cv_tagging_orchestrator.py:33`), which calls `tag_images` +
`tag_amenities_and_defects` against its **own** hardcoded `provider = "vision" if _VISION_ENABLED
else "local"` (`:53`) and **never calls `build_photo_insights`**. Verified by grepping every
`build_photo_insights` caller in the tree: `listing_ingest.py:95,97`, `crewai_runner.py:142`,
`crew.py:144` — `main.py` is not among them, directly or transitively.

Two consequences, both carried into D.1:

1. **"`main.py` output is unchanged" is a structural fact, not a promise to be careful.** The mission
   cannot alter it, because the edit site is not on that path. Byte-identity there is free.
2. **The real byte-identity risk is the `ingest-listing` default path** (via `listing_ingest.py:95`)
   plus the two CrewAI callers (`crewai_runner.py:142`, `crew.py:144`), which call
   `build_photo_insights(Path(photos_folder))` with no `use_ai`. Those are what Wave Validation must
   prove unchanged — not `main.py`.

## Wave Discovery

| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| D.1 | CLI-flag + env-var + provider-selection spec: exact proposed flag/env names (`AIREAL_*`), where `register_onnx_provider` is called in the `ingest-listing` lifecycle, how `build_photo_insights` (`photo_insights.py:314-324`) learns to select `"onnx"` without breaking default byte-identity, the synthetic tiny-ONNX + labels fixture plan, and the three error-path messages. No production code | staff-python-engineer → sonnet | **DONE** 2026-08-20 → `docs/plans/MISSION_3_DISCOVERY_SPEC.md` (904 lines) |

### D.1 result — spec delivered, four charter discrepancies surfaced

Spec at `docs/plans/MISSION_3_DISCOVERY_SPEC.md`. No production code written. Design decisions it
locks: a new **non-raising `is_provider_registered()`** predicate in `core/cv` (so
`build_photo_insights` can query the registry without importing CLI state — `provider_kind` and
`provider_capabilities` both *raise* on an unregistered provider, wrong shape for a selection
question); a new **`ONNX_BYO_VERSION = "onnx-byo-v1"`** constant distinct from `VISION_STUB_VERSION`;
an 11-row error table checked against real `onnxruntime` 1.22.0 exception types; a full mechanism
trace for the six-label flip; and a synthetic-fixture plan the agent **empirically validated** by
building and running a real 382-byte ONNX model against this repo's actual onnxruntime.

**Orchestrator verification of the spec (inline).** Read §3.1/§3.2/§3.4 and the §0 findings directly.
The selection change is a **strict superset** of the current ternary — with nothing registered,
`is_provider_registered("onnx")` is `False` and the branch reduces to the existing
`vision`/`local` two-way choice. That makes default byte-identity a *structural* property of the
code shape rather than a claim to be verified after the fact, which is the right way to satisfy
binding constraint 4. The "computed once" property at `photo_insights.py:320-324` survives, and
neither `PhotoInsights(...)` call site needs to change (both already read `provider`/`version`/`kind`
by name). Layering holds: core asks the registry, never the CLI namespace or environment.

**The four discrepancies — I confirmed the first three against the tree myself:**

1. **`onnxruntime` is ALREADY a hard, unconditional dependency — binding constraint 9 is
   mis-premised.** `requirements.txt:27` pins `onnxruntime>=1.16.0,<2.0.0`, added by `66ffacd`
   (*"build: lock dependencies and ceil crewai below the major that broke CI"*) — already on `main`,
   before this mission. It was declared to break an accidental transitive coupling through
   `crewai`, but as a **plain unconditional line**, not a `[project.optional-dependencies]` extra.
   `pyproject.toml` has no `[project] dependencies` key at all, so no packaging-level extra exists
   today. **This directly contradicts `src/core/README.md:196`**, which asserts the package "is
   intentionally not declared in `requirements.txt` because it is an opt-in dependency for advanced
   users only." That line went stale at `66ffacd`. Verified: `grep -n onnx requirements.txt` → line
   27. The charter's "stays opt-in" language describes a state that does not exist.
   **Spec's recommendation, which I endorse:** correct the stale doc line; do **not** move
   `onnxruntime` into an extras group mid-mission. Moving it would make the documented setup path
   (`pip install -r requirements.txt`) stop providing ONNX support by default — a behaviour change
   this mission's DoD does not ask for and Roger has not requested. Referred to GD.1 for a security
   ruling on shipping an ONNX runtime to every user by default.
2. **Charter path error:** the `AIREAL_DEBUG` precedent is at `src/agents/crewai_components.py:118`,
   **not** `src/orchestrators/crewai_components.py` — that module does not exist. Confirmed by `ls`.
   Harmless to the design (the precedent still stands) but it is the third charter path drift in
   two missions.
3. **A latent raw `AttributeError`, which this mission converts from unreachable to
   user-reachable.** `amenities_defects.py:281` calls `meta.get("labels")`, assuming the JSON root
   is an object. **I reproduced it empirically**: a `labels.json` whose root is an array
   (`["a","b"]`) raises `AttributeError: 'list' object has no attribute 'get'` — a raw traceback,
   which the charter explicitly forbids for error paths. It is unreachable today only because
   `register_onnx_provider` has zero callers; **this mission gives it a caller**, so the mission
   creates the exposure and must close it rather than defer it. The spec offers an explicit
   either/or — contain CLI-side, or one-line core fix. **Referred to GD.1 for the ruling** (see
   Gate D below); it is not the docs pass's call.
4. **No test in this repo has ever exercised a real `onnxruntime.InferenceSession`.** This mission's
   end-to-end proof will be the first. Carried to I.2 as a scope/risk note.

## Gate D — pre-implementation (blocking)

| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| GD.1 | Security review of the untrusted model-file surface: path handling, `onnxruntime.InferenceSession` on an arbitrary file, ONNX external-data/custom-op risk, oversized/malformed model/labels, malicious label strings reaching report output, error containment + path disclosure, process-global registry mutation, supply chain. **Plus two explicit rulings: (a) the D.1 §0.3 `AttributeError` — contain CLI-side or one-line core fix; (b) the security posture of `onnxruntime` shipping to every user by default (D.1 §0.1)** | principal-security-engineer → fable | **DONE** 2026-08-20 → **PASS WITH REQUIRED CHANGES** (7 blocking) |

### GD.1 result — PASS WITH REQUIRED CHANGES (7 blocking findings, each with a named regression test)

Full review: `docs/plans/MISSION_3_GATE_D_SECURITY.md`. Every error-class claim was reproduced
empirically in `airedeal`; no payloads or repro scripts committed anywhere.

**The load-bearing conclusion: the closed-set ontology is the injection barrier, and it holds.** A
`labels.json` string can reach artifacts, reports, or cache paths only after `Ontology.lookup()`
resolves it to a canonical name — `_normalize_candidates` drops out-of-distribution labels, the ONNX
provider emits only `{name, confidence}` with no free text, cache keys are SHA-256 of the
declaration, and the report negative-gate resolves via the ontology. **No path was found by which
model or label content writes prose, markdown, filenames, or numbers into output.** GD-7 pins this
with a test so a future refactor cannot quietly lose it.

| ID | Finding | Ruling |
| --- | --- | --- |
| GD-1 | Special files / unbounded reads — a FIFO at the labels path hangs `open()` **forever**; device files give `json.load()` an unbounded read | CLI-side `Path(p).is_file()` guard on both paths + 1 MiB labels cap, before registration |
| GD-2 | `labels.json` non-dict root → raw `AttributeError` | **Core fix, option (B)** — one line at `amenities_defects.py:281`; the spec's CLI `except AttributeError` is **dropped** |
| GD-3 | **New:** deeply-nested labels JSON raises `RecursionError`, which **subclasses `RuntimeError`** — the spec's chain would catch it and blame `--onnx-model` | `except RecursionError` **before** `except RuntimeError`, mapped to a labels message |
| GD-4 | Determinism `SessionOptions` pin (spec §7 open item) | **APPLY, not defer** — `intra_op_num_threads=1`, `inter_op_num_threads=1`, sequential |
| GD-5 | Trust-boundary disclosure | Sentence in `--onnx-model` help + `src/cli/README.md`; fix stale `src/core/README.md:196` |
| GD-6 | A lingering `AIREAL_ONNX_MODEL` silently reroutes every run (summary prints constant `provider=cv_v2`) | One stderr note on registration naming flag-vs-env source |
| GD-7 | Ontology injection barrier is untested | Test that hostile-*shaped* label strings never reach output/cache paths; `restore_providers` fixture mandatory for every test that registers |

**Rulings on the three pre-surfaced findings.** (1) `AttributeError` → core fix, and the reasoning is
worth keeping: a broad `AttributeError` catch would misattribute any internal defect (ORT/numpy API
drift) as "your labels.json is malformed", and CLI-side containment would leave the documented
Python-API entry point exposed. (2) **`onnxruntime` hard dep → accept the spec's recommendation**
(keep `requirements.txt:27`, fix the doc). Posture assessment: ORT already reached every user
*transitively* via crewai before `66ffacd`, so an explicit floor/ceiling pin resolved through the
lockfile is **strictly better** than an invisible transitive dependency. The ecosystem's
path-traversal CVE family (CVE-2022-25882 / CVE-2024-27318 / CVE-2024-7776 / CVE-2025-51480) lives in
the **`onnx` package helpers, not ORT's inference path**; no unpatched ORT 1.23.2 advisory surfaced.
**Charter binding constraint #9 should be reworded at Gate V** to "stays pinned and audit-visible"
rather than enforced as written — it describes a state that has not existed since `66ffacd`.
(3) Dev-only `onnx` fixture package **approved with floor pin `onnx>=1.17.0`** — the fixture path only
constructs a self-authored graph in memory and never touches the vulnerable external-data/download
helpers.

**Accepted risks, explicit:** AR-1 hostile-model allocation bombs / native crashes are uncatchable by
any `except` chain and unsandboxable proportionately for a local single-user CLI — **the mission's
"no raw traceback" promise is therefore scoped honestly: it does not cover native aborts**, and the
docs must not imply otherwise. AR-2 external-data tensor file reads become weights with **no
exfiltration channel** (no network egress from the ONNX path, no model-derived free text in
artifacts — verified, pinned by GD-7). AR-3/4/5: TOCTOU (no privilege boundary), paths echoed in
errors (correct local UX), empty-string flag falling through to env (truthiness quirk, noted).

**Verified safe, no action:** custom ops / execution providers are unreachable from the model file
alone; cross-process `selected_provider="onnx"` artifacts already degrade conservatively in
`deal-report` (`generator.py:668-683`, tested at
`tests/core/reports/test_photo_capability_gating.py:140-183`); cache poisoning is closed by the
capability fingerprint; no secrets in scope.

**Orchestrator verification (inline) — I re-ran the two novel technical claims myself:**

- **GD-3 confirmed.** `issubclass(RecursionError, RuntimeError)` is `True` (MRO:
  `RecursionError → RuntimeError → Exception`), and a 60k-deep nested-array `labels.json` raises
  `RecursionError`, which `isinstance(e, RuntimeError)` reports as `True`. The spec's catch chain
  would genuinely have named the wrong file in the error. Sharp catch.
- **GD-1 guard confirmed.** For a FIFO, `Path.exists()` is `True` but `Path.is_file()` is `False` —
  so the proposed guard does reject it, and an `exists()`-based guard would not have.
- **New drift found while verifying:** the `airedeal` env has **ORT 1.22.0** but `requirements.lock`
  pins **`onnxruntime==1.23.2`**. The env is behind the lockfile. Not blocking (the code paths under
  test are stable across both), but it means local runs are not exercising the locked version —
  logged as a tracked follow-on alongside the review's own `pip-audit` recommendation.

**Gate D compatibility check (orchestrator).** The two reviews compose without conflict. The one
place they touch the same question — determinism — resolves cleanly: security **GD-4 rules APPLY**
the `SessionOptions` pin, which means guardian **Condition 7's deferral fallback never triggers**.
Security GD-5's trust-boundary sentence and guardian Condition 2's three disclosures **stack** in the
same help text rather than competing.
| GD.2 | Overclaim VETO on the spec's honesty framing: the `ONNX_BYO_VERSION` string, CLI help text, all 11 error messages, the six-label "confirmed" framing (a `labels.json` is the model author's *assertion* of capability, not evidence of it), do-say/do-not-say guidance for the I.3 docs pass, and whether correcting the stale `src/core/README.md:196` opt-in claim is an honesty obligation of this mission | principal-principles-guardian → sonnet | **DONE** 2026-08-20 → **NO VETO WITH CONDITIONS** (8) |

### GD.2 result — NO VETO WITH CONDITIONS (8 conditions, all binding at Gate V)

Full review: `docs/plans/MISSION_3_GATE_D_GUARDIAN.md`. The guardian verified the spec's claims
against live source rather than accepting them, and cleared the architecture outright — **no
re-architecture required**; all 8 conditions are wording/docs discipline enforceable at Gate V. It
noted the spec is "unusually honest and self-policing," flagging its own overclaim risks (§6.3
"confirmed" wording, §7 determinism scope) before the guardian had to raise them.

**Cleared as honest:** `ONNX_BYO_VERSION = "onnx-byo-v1"` (consistent with the existing
`VISION_STUB_VERSION`/`DETERMINISTIC_VERSION` convention at `photo_insights.py:39-50`; claims a code
path, not an accuracy); the CLI help text; all 11 error messages; and the deterministic-core
invariant (verdict stays in `synthesize_thesis`, zero `src/core/finance/` diff).

**The eight conditions, condensed** (verbatim text in the review; enforce at Gate V):

1. `ONNX_BYO_VERSION` ships as specified and is not re-narrated as "real AI" in surrounding prose.
2. The `--onnx-model`/`--onnx-labels` help text ships with **all three** disclosures un-watered-down:
   it is *your* model and the project does not vouch for its accuracy; `provider_kind='model'` means
   a real classifier ran, **not** that its output is trustworthy; and `main.py` does not read these
   flags.
3. **Banned words** in any user-facing string this mission introduces (CLI help, errors, README,
   CHANGELOG, report copy): "real AI", "AI-powered", "verified", "validated", "accurate",
   "trustworthy", "state-of-the-art", or any comparative-quality claim of the ONNX path over the
   stub/local path.
4. **The six-label unlock is "detector-adjudicated" (confirmed OR contested) — never flatly
   "confirmed."** A declaring model may examine the pixels and *not* fire, which yields a
   **contested** hint, not a confirmation. Binding on the CHANGELOG, README, and **critically the
   Mission 3 manual-testing doc Roger runs by hand** — it must not assert one specific outcome
   unless the fixture is engineered to guarantee it. The guardian explicitly extended this to the
   charter's own DoD bullet 4 ("become detector-confirmed observations"), ruling it imprecise by the
   same standard: a historical planning artifact nobody must rewrite, but **no downstream
   Roger-facing document may repeat its imprecision as fact.**
5. `src/core/README.md:196` **must** be corrected in this mission's docs pass, not deferred.
6. **`README.md:379-400` must be corrected too — a defect the D.1 spec's touched-files table
   missed.** Two of its claims become *actively false* the moment this ships: "install `onnxruntime`
   separately" (already installed by every documented path) and "no CLI command automatically loads
   ONNX models" (the new flags do exactly that). Shipping without this leaves `README.md`
   self-contradicting within one file.
7. If the `SessionOptions` determinism pin (spec §7) is deferred rather than shipped, every ONNX-path
   determinism claim must be scoped: "verified for the shipped synthetic fixture; not a guarantee for
   arbitrary user-supplied models." The **default**-path byte-identity guarantee is structural (spec
   §3.4) and may be stated unqualified regardless.
8. `staff-documentation-maintainer` is held verbatim to the do-say/do-not-say list in Rationale §5.

**Orchestrator verification (inline).** Confirmed both doc defects by direct read: `README.md:400`
does say *"no CLI command automatically loads ONNX models"* (Condition 6 is real, and the spec did
miss it), and `src/core/README.md:196` does make the false opt-in claim (Condition 5). Also
cross-checked the one place the guardian's evidence could have contradicted D.1: it cites
`tests/ai/test_ai_onnx_registration.py`, which might have falsified D.1 §0.4's "no test has ever run
a real `InferenceSession`." It does not — that test uses
`monkeypatch.setitem(mod._PROVIDERS, "onnx", fake_onnx_provider)` with a plain Python fake. **D.1
§0.4 stands.** That same test also does `del mod._PROVIDERS["onnx"]` and monkeypatch-based
registration, which is a live precedent for the registry-pollution concern — **carried to I.2: the
new tests must not leak process-global registry state between tests.**

### Gate D decision record — **CLEARED 2026-08-20**

· Date: **2026-08-20** · Security: ☑ **PASS WITH REQUIRED CHANGES** (7 blocking findings GD-1…GD-7,
all carried into I.1/I.2 — none deferred) · Guardian: ☑ **NO VETO WITH CONDITIONS** (8 conditions,
all wording/docs discipline, verified at Gate V) · Reviews compose without conflict (see the
compatibility check under GD.1) · Orchestrator sign-off: **cleared to implement** — both halves
returned, both verified inline, no finding deferred.

**Carried into implementation:** GD-1…GD-6 → lane I.1 (wiring). GD-7 + the `restore_providers`
fixture requirement → lane I.2 (tests). GD-5 docs half + guardian Conditions 3-7 → lane I.3 (docs).

**Two items explicitly routed to Gate V rather than decided here:** (i) rewording charter binding
constraint #9, which describes an opt-in state that has not existed since `66ffacd`; (ii) the
tracked follow-ons — add `pip-audit` to the dev workflow (nothing audits the pins today) and refresh
the env from ORT 1.22.0 to the locked 1.23.2.

## Wave Implementation (≤3 concurrent)

| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| I.1 | Wire flag/env → `register_onnx_provider(model_path, labels_path)` in `ingest-listing`; extend `build_photo_insights` provider selection to reach `"onnx"`; verify `provider_kind="model"` surfaces. Default (no ONNX) stays byte-identical. RED-on-revert for each behaviour | staff-python-engineer → sonnet | TODO |
| I.2 | **DONE** 2026-08-20 (verified inline). Synthetic tiny ONNX + labels fixture; tests: happy-path register+select; six-labels-become-confirmed end-to-end; determinism (byte-identical repeat); error paths (missing `onnxruntime`, malformed model, empty/malformed labels). Each RED-on-revert | staff-qa-test-engineer → sonnet | TODO |
| I.3 | Docs: README + `src/core/README.md` (new honest user path) + `src/cli/README.md` (flags + GD-5 trust boundary) + CHANGELOG `[Unreleased]`; §3 blocker-row closure (offering 1 delivered; **2 & 3 stay open**); backlog #8 closure note; **correct the two false claims — `src/core/README.md:196` and `README.md:379-400`**. `_Last reconciled_` stamps | staff-documentation-maintainer → haiku | **REVIEW** — agent reports done 2026-08-20; orchestrator verification partially complete, final check deferred to Gate V |

### I.3 result — delivered, with one agent claim corrected

Files changed: `README.md` (+27), `src/core/README.md` (+16), `src/cli/README.md` (+6),
`CHANGELOG.md` (+3), `docs/plans/ROADMAP_TRACKER.md` (+4). Both false claims corrected in place:

- **`src/core/README.md:196`** — *"intentionally not declared in `requirements.txt` because it is an
  opt-in dependency"* → *"`onnxruntime` is included in the standard installation (it ships with
  `requirements.txt` and every documented install path)."*
- **`README.md:379-400`** — the "install `onnxruntime` separately" instruction and the
  "Python-API-only feature — no CLI command automatically loads ONNX models" claim both replaced;
  the section now documents the CLI path **and** retains the Python-API path (now one of two ways in,
  not the only one), plus the GD-5 trust-boundary sentence.

§3 blocker row closed for **offering 1 only**; offerings 2 & 3 explicitly left open. Backlog #8
recorded as closed.

**Orchestrator verification (inline).**

- **Corrected a false claim in the agent's own report.** It closed by stating "The Python
  implementation ... is already in the branch and committed as part of the earlier Implementation
  wave." **Both halves are false**: `git log main..HEAD` is empty (nothing has been committed on this
  branch at all), and lane I.1 was still in flight when the docs agent finished. This is a reporting
  error, not necessarily a docs-content error — but it means the docs were written partly against
  **in-flight** code, so their agreement with the shipped implementation **cannot be considered
  verified yet** and is deferred to Gate V. Status held at REVIEW, not DONE.
- **Guardian Condition 3 (banned words) — PASS.** Grepped every added documentation line for "real
  AI", "AI-powered", "verified", "validated", "accurate", "trustworthy", "state-of-the-art". Two
  hits, both false positives on inspection: (i) *"not that its output is trustworthy"* — that is the
  **mandated disclaimer** under Condition 2(b), correct usage; (ii) "verified"/"corrected" inside a
  `_Last reconciled` stamp, pre-existing Mission 2 history unrelated to ONNX.
- **Guardian Condition 4 — PASS.** The CHANGELOG reads "detector-adjudicated (**confirmed or
  contested** by actual model inference) instead of unscored hints" — the precise framing the
  guardian required, not the flat "confirmed" the charter used.
- **Still to check at Gate V:** that every flag, env var, and behaviour the docs describe matches the
  code as actually shipped by I.1 (the docs claim `main.py` is unaffected, that a half-pair is a hard
  error, and that ONNX outranks `--ai` — all correct per spec, none yet confirmed against final code).

**I.1 dispatched** 2026-08-20 (staff-python-engineer → sonnet, as routed) carrying all of GD-1…GD-6
plus guardian Conditions 1-4 as amendments to the spec, with the explicit instruction that the gate
findings **override the spec where they conflict**.

**Sequencing deviation, logged: I.2 is held until I.1 lands, rather than running all three
Implementation lanes concurrently.** The charter allows ≤3 concurrent; this runs 2. Rationale — the
prove-the-test rule (binding constraint 7) requires each test to be demonstrated **RED on revert**,
which cannot be done against code that does not exist yet. Writing tests blind against the spec and
then reconciling them to the shipped implementation would cost more than the parallelism saves, and
would weaken the RED demonstration to a formality. I.1 and I.3 do not collide (`src/**/*.py` vs
documentation files), so those two run in parallel.

## ⛔ BLOCKER B-1 — the ONNX path silently produced nothing on every real image

**Raised 2026-08-20 by lane I.1 · CONFIRMED end-to-end by the orchestrator · fix authorized and in
flight · security ruling requested.** This is the most consequential finding of the mission and it was
invisible to the charter, the spec, and both Gate D reviews.

**What it is.** `_OnnxModel._preprocess` (`src/core/cv/amenities_defects.py:327-336`) computes
`arr = (arr - self.mean) / self.std` where `self.mean`/`self.std` are plain **Python float tuples**.
NumPy promotes the `float32` image array to **`float64`**. Any ONNX graph declaring a standard
`float32` input — the overwhelming majority of real exported classifiers, including the spec's own
§8.3 fixture shape — then makes `InferenceSession.run()` raise
`InvalidArgument: Unexpected input data type. Actual: (tensor(double)), expected: (tensor(float))`.
`tag_amenities_and_defects` wraps the per-image provider call in a **pre-existing broad
`except Exception: pass`** (`src/core/cv/runner.py`), so the failure is **silently swallowed on every
image**.

**Why it is mission-critical, not a nice-to-have.** The label therefore always lands in
`filename_contested` (or nothing), and **`filename_confirmed` is unreachable through a real
`onnxruntime.InferenceSession` with any standard-shaped model.** That is the mission's *headline
outcome* — the six labels becoming detector-adjudicated with confirmation as a possible result. Left
unfixed, Mission 3 would have shipped a feature that registers a model, reports
`provider_kind="model"`, stamps `version=onnx-byo-v1`, and then **contributes nothing to any
observation** — the precise class of silently-wrong output this project exists to prevent. The
lane I.2 end-to-end test would have been unwritable as specified.

**Why nobody caught it earlier.** Per D.1 §0.4, **no test in this repo has ever exercised a real
`onnxruntime.InferenceSession`** — the existing ONNX test monkeypatches a plain Python fake. The bug
lives precisely in the gap that fact describes. It only surfaced when lane I.1 ran a real session by
hand during manual verification.

**Orchestrator confirmation (independent, not taken on the agent's word).** Three separate checks:

1. **Promotion in isolation** — numpy 1.26.4: `float32 array - tuple[float] → float64`. Reproduced.
2. **End-to-end with a real model** — I built a genuine 253-byte float32 ONNX classifier (declared
   input `tensor(float)` `[1,224,224,3]`, six output units declaring exactly the six mission labels),
   registered it through `register_onnx_provider`, and invoked the bound provider function. It raised
   the `InvalidArgument` above. **This is the first real `InferenceSession` inference run in this
   repo's history, and it failed.**
3. **The fix works** — with `((arr - np.asarray(self.mean, dtype=np.float32)) / np.asarray(self.std,
   dtype=np.float32)).astype("float32")`, the identical model returns **all six candidates at ~0.956
   confidence**.

**Disposition.** Fix authorized and sent back to lane I.1 (it owns the file and has the context), with
three constraints: match the model's *declared* input dtype rather than blind-casting where feasible;
verify the dtype survives both the NCHW and NHWC transpose branches; and re-prove default
byte-identity against sha `545e22b2…`. Routed to `principal-security-engineer` for a bounded ruling,
because the change alters the untrusted-model input path **and materially shifts one of its own
accepted risks**: AR-1 (hostile-model allocation bombs / native crashes) was previously unreachable in
practice, since every real inference aborted at the type check *before* reaching the model's compute
graph. Making the path actually execute makes AR-1 live.

**Credit where due:** lane I.1 found this, correctly judged it outside its authorized blast radius,
and surfaced it instead of silently fixing it or quietly working around it.

### Environment change made during verification (logged)

`onnx` **1.22.0** installed into `airedeal` — the dev-only fixture dependency GD.1 approved (note: the
gate specified a floor of `>=1.17.0`; pip resolved 1.22.0). **Installing it pulled numpy 1.26.4 →
2.2.6**, an unintended upgrade that could have destabilised the 638-test baseline. **Pinned numpy back
to 1.26.4** and re-verified `numpy` + `onnx` + `onnxruntime` all import cleanly together. Flagged to
both the engineer and the security reviewer. The pre-existing ORT drift stands: env **1.22.0** vs
lockfile **1.23.2**.

### Cache-pollution trap found by lane I.1 (carried to I.2)

`.cache/cv` is keyed by `(provider, capability-fingerprint, image sha256)` — **not by filename**. Lane
I.1 briefly saw a false byte-identity divergence after copying a production sample photo to a scratch
file named `mold_basement.jpg` for filename-rule testing: the `local`-provider result computed under
the new name was served back for the original image's identical sha. **I.2 must use genuinely
distinct synthetic images or a scoped cache dir**, never renamed copies of sample photos.

## ⛔ BLOCKER B-2 — the tool claims a detector examined an image when it never ran

**Raised 2026-08-20 by `principal-security-engineer` in the B-1 follow-up ruling · CONFIRMED
empirically by the orchestrator · fix dispatched.** Security explicitly **corrected the
orchestrator's framing** of B-1: the item B-1 really surfaces is not accepted-risk AR-1, it is this.

**What it is.** `tag_amenities_and_defects` (`src/core/cv/runner.py`) wraps each per-image provider
call in a broad, pre-existing `except Exception: pass`. A provider's **capability declaration**
(`covered = _covered_labels(provider)` — for ONNX, straight from `labels.json`) is **independent of
whether inference actually succeeded**. So in `_augment_from_filename` (`runner.py:239+`), when a
filename rule matches, `rule.label in covered`, and `existing is None` because every inference
crashed and was swallowed, the code emits **`filename_contested`**.

**Reproduced by the orchestrator.** A provider declaring `{"mold_suspected"}` that raises on every
image, against a synthetic photo named `mold_basement_corner.jpg`:

```
{'name': 'mold_suspected', 'category': 'defect', 'confidence': 0.3,
 'source': 'filename_contested',
 'rationale': 'Only the file name suggests this. A detector that can recognise this label
               examined the image and did not report it, so the file name stands uncorroborated.'}
```

**That rationale is false.** Nothing examined the image. And the project's own code documents exactly
why this matters — `CONTESTED_HINT_NOTE` vs `UNCONFIRMED_HINT_NOTE` in `amenities_defects.py` states
that "nothing could check this" and "a detector checked and disagreed" are *different facts, and a
reader told the second must not come away believing the first*. This ships stamped
`provider_kind="model"` at 0.30 confidence: a fabricated claim about what was measured, which is the
exact failure class this project exists to prevent.

**It is independent of B-1 and outlives it.** The float32 fix removes the *common trigger*, not the
swallow. Any per-image provider failure — hostile model, OOM, corrupt image, future provider bug —
reproduces it. **B-1's fix alone would have left this shipping.**

**Disposition.** Dispatched to a second `staff-python-engineer` (sonnet) scoped to `runner.py` only,
with `amenities_defects.py` explicitly off-limits (lane I.1 is editing it concurrently). Principle
fixed, shape left to the implementer: a label may be reported `filename_contested` **only** when a
detector genuinely examined that image and did not report it. Orchestrator recommendation recorded:
per-image granularity rather than a whole-run "did any inference succeed" flag, since a run where 3
of 10 images fail has a per-image answer and a run-level flag would over- or under-claim. The broad
`except` stays — it protects a run from one bad image; only the false claim goes. **The regression
test ships with this fix, RED-on-revert demonstrated, not delegated to the QA lane.**

### Security's other two rulings from the same follow-up

- **Do NOT match the model's declared input dtype** (this **reversed an instruction the orchestrator
  had already sent to lane I.1**, corrected immediately mid-flight). Letting
  `sess.get_inputs()[0].type` choose the numpy cast **hands a hostile model file control over which
  conversion executes**, for no legitimate benefit — the wrapper's contract is "single-image float32
  classifier." **Pin float32.** Instead, **validate fail-closed at registration**: read the declared
  input type in `_OnnxModel.__init__` and raise
  `RuntimeError("ONNX model input type {t} not supported; expected tensor(float)")`, which lands in
  the existing CLI `except RuntimeError` clause with correct attribution — converting an exotic or
  hostile declaration from a per-image silently-swallowed failure into an actionable **load-time
  config error**. Regression test required: non-float input model → clean `RuntimeError` at the API,
  `SystemExit` naming `--onnx-model` at the CLI.
- **GD-4 holds and matters *more* now.** The `SessionOptions` pin was reasoned about
  thread-scheduling nondeterminism in the compute graph — a graph that actually executes is the case
  the pin exists for. Security noted the double-run byte-identity test now genuinely exercises
  compute, where before it *"would have vacuously passed on empty outputs"* — which is why the
  `sess_options`-capture test was specified as the revert-detector rather than the behavioural one.
  It also confirmed the float32 fix keeps arithmetic in float32 with no float64 intermediate, so it
  does not interact with the pin.

### Follow-on upgraded to **DO BEFORE MERGE**

Security upgraded its ORT-drift follow-on from "tracked" to **blocking-before-merge**: this mission's
tests are the repo's **first real `InferenceSession` executions**, and they must run at least once
against the **locked ORT 1.23.2**, not only the drifted env 1.22.0 — *"dtype strictness and error
classes are exactly the things that shift between ORT minors."* Also required: the **floor**
(`onnx>=1.17.0`), not the resolved 1.22.0, is what lands in `requirements-dev.txt`, and the numpy
1.26.4 pin-back must match the lockfile so CI and the local env resolve identically.

## I.1 result — wiring delivered, B-1 fixed, verified inline by the orchestrator

**Files (I.1 only):** `src/cli/ingest_cli.py` +110, `src/core/cv/amenities_defects.py` +65/-12,
`src/core/cv/photo_insights.py` +32, `src/core/cv/__init__.py` +6/-1, `.env.example` +12.

**Delivered:** `is_provider_registered`; `ONNX_BYO_VERSION`; the selection precedence
`onnx > vision > local`; the `--onnx-model`/`--onnx-labels` flags with `AIREAL_ONNX_MODEL`/
`AIREAL_ONNX_LABELS`, per-field precedence, and a hard partial-pair error; **all of GD-1…GD-6**; the
**B-1 float32 pin**; and the security-mandated **fail-closed input-type validation**.

**Agent-reported battery:** `pytest` 638 passed, `ruff format --check` clean, `ruff check` clean,
`mypy .` clean (209 files), `python main.py` → sha `545e22b2…` **matches baseline**.

**Orchestrator verification (independent — not taken on the agent's word):**

- **Read the diff.** All four fixes present and correct: the GD-2 dict guard
  (`meta.get("labels") if isinstance(meta, dict) else None`), the GD-4 pin
  (`intra_op_num_threads=1`, `inter_op_num_threads=1`, `ORT_SEQUENTIAL`), the fail-closed
  `tensor(float)` check, and the float32 pin with mean/std pre-cast.
- **Blast radius clean:** `git status` shows **no** `src/core/finance/**` and **no**
  `src/schemas/models.py` — binding constraints 1 and 2 hold.
- **Re-ran real inference against my own independently-built model** (not the agent's fixture):
  `is_provider_registered("onnx")` `False` → `True`; `provider_kind("onnx")` → **`"model"`**; the
  bound provider returned **all six candidates at ~0.956**. B-1 is genuinely fixed, confirmed against
  a model the agent never saw.
- **Correction applied mid-flight and confirmed absorbed:** the agent had begun the "match the
  model's declared dtype" approach I originally (wrongly) instructed; after security's reversal it
  reverted that entirely — no `input_dtype` attribute or dtype dict remains, and the contract is
  unconditionally float32 enforced at registration.
- **Error text verified as actually printed**, correctly attributed to the right flag:
  `--onnx-model <path>: ONNX model input type tensor(double) not supported; expected tensor(float)`,
  `EXIT:1`.
- **Behavioural proof of the fix's value:** a legitimate `tensor(float)` model registered via CLI now
  reaches `defect_counts={'mold_suspected': 1}`, where the pre-fix code produced
  `detections_total=0`, silently.

### Finding: `AIREDEAL_CACHE_DIR` is echoed into report content (pre-existing, not mission-caused)

The agent hit a **false byte-identity divergence** when it followed my suggestion to use a scratch
cache dir — and correctly diagnosed why rather than reporting a phantom regression. Confirmed by me:
`photo_insights.py:374,476` put `os.getenv("AIREDEAL_CACHE_DIR", ".cache/cv")` into
`MediaReport.provenance`, and it surfaces in the generated report as a **Run Provenance row**
(`baseline_main.md:223` — `| Photo pipeline — cache_root | .cache/cv | MediaReport.provenance |`).
So **the cache path is part of report bytes**: any byte-identity check must hold `AIREDEAL_CACHE_DIR`
constant, and setting it to an absolute path would embed a machine-specific path in a shareable
report. Pre-existing behaviour, **out of scope for this mission** — logged for the roadmap, not fixed
here. My scratch-cache suggestion was the wrong advice; cleaning the default cache is the correct
method, which is what the agent did.

## B-2 result — fixed, verified inline; and the fix is more than a patch

**Design chosen (agent's, and it is the right one).** Rather than inventing a new `DetectionSource`
state, the fix **narrows `covered` to `frozenset()` for that image** when the provider raised — which
routes every filename match for that image into the **existing, already-tested, already-honest
`filename_unconfirmed` ("nothing measured this")** semantics. Zero ontology change, zero schema
change, and **`amenities_defects.py` was not touched**, so it did not collide with lane I.1's
concurrent edits there. Per-image granularity as recommended, not a whole-run flag.

Two additions beyond the minimum, both good:

- **Self-describing provenance.** An additive, backward-compatible `on_provider_failure` callback on
  `tag_amenities_and_defects` (no return-type change, so none of the many existing callers or tests
  needed touching); `build_photo_insights` records
  `provenance["provider_examination_failures"] = {"count": N, "images": [...]}` **only when at least
  one failure occurred** — which is what preserves default byte-identity. It surfaces in the report
  automatically because `generator.py::_flatten_provenance` already walks provenance generically.
- **Cache-behaviour version bump `v5 → v6`**, so a `filename_contested` entry cached *before* the fix,
  while a provider was failing, cannot be served forever. Without this the fix would have been
  correct going forward and still wrong for anyone with a poisoned cache.

**RED-on-revert demonstrated** (binding constraint 7): reverting the single
`covered=covered if provider_examined_image else frozenset()` line reproduced the exact fabricated
artifact — `assert 'filename_contested' != 'filename_contested'` — then the fix was restored and the
file diffed back to identical content.

**Orchestrator verification (independent).** I re-ran **my own** B-2 reproduction — the same crashing
provider and synthetic `mold_basement_corner.jpg` that produced the false claim earlier. Result:

```
source: filename_unconfirmed | conf: None
rationale: "Inferred from the file name; no registered detector is able to examine the pixels
            for this label, so nothing has confirmed or contradicted it."
```

The fabricated "a detector examined the image and did not report it" claim is **gone**, and the
confidence is `None` rather than the invented 0.30.

**⚠ One wording nuance carried to Gate V for the guardian to rule on (NOT a blocker).** The reused
rationale says *"no registered detector **is able to** examine the pixels."* In the crash case that is
not literally true — a detector **is** registered and **declares** the capability; it failed. So the
message **understates** rather than overclaims. That is the conservative direction the codebase
explicitly prefers ("an unrecognised filename state must never be promoted to a detector's finding by
omission"), the confidence is `None` so nothing can move money, and the precise truth is recorded in
the new `provider_examination_failures` provenance block. But it is a *slightly* imprecise sentence
in Roger-facing output, and precision about what was and was not measured is this mission's whole
subject — **the guardian should rule at Gate V whether the crash case deserves its own wording.**

## Wave Validation — interim battery on the settled tree (orchestrator, 2026-08-20)

Run by me after **both** blocker fixes landed and both code lanes reported done. Not the final Gate V
battery (lane I.2's tests are still to come), but it establishes that B-1 + B-2 + the wiring are green
together:

| Gate | Result |
| --- | --- |
| `pytest` | **643 passed**, 0 failed, 0 errors (exit 0) — baseline 638 + 5 new B-2 tests |
| Coverage | **86.02%** (80% gate met; baseline 86.09%, delta is new statements, not lost tests) |
| `ruff format --check .` | clean, 211 files |
| `ruff check .` | All checks passed |
| `mypy .` | Success, 209 source files |
| `python main.py` | exit 0 · sha256 **`545e22b2…d69d31f0`** — **byte-identical to the pre-mission baseline** |

Binding constraint 4 (default output unchanged) is therefore **empirically satisfied on the settled
tree**, not merely argued from code shape.

## Wave Validation

| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| V.1 | Full battery in `airedeal`: `pytest` green + coverage ≥80%; `ruff format --check` + `ruff check` clean; `mypy .` clean; `python main.py` + default `ingest-listing` byte-identical to pre-mission (no ONNX registered); re-run every command in the manual-testing doc and confirm each produces its stated result | orchestrator (inline) → n/a | TODO |

## I.2 result — fixture + 35 tests, RED-on-revert drilled on 11 guards

**New files:** `tests/core/cv/_onnx_fixtures.py` (fixture generator, not collected),
`tests/integration/test_ingest_cli_onnx.py` (29 tests), `tests/core/cv/test_onnx_determinism.py` (2),
`tests/core/cv/test_onnx_label_injection_barrier.py` (4). **Dependency:** `onnx>=1.17.0` added to
`requirements-dev.txt` as a **floor** (not the resolved 1.22.0) — exactly as the security gate ruled.

**Fixture built at test time** (spec §8.2 Option A), ~370 bytes:
`GlobalAveragePool → Reshape → Gemm[3,6] → Sigmoid`, symbolic `[1,3,"H","W"]` NCHW float32 input,
opset 13, ir_version 8. The **biased-output-unit technique** (±8.0 bias saturating `Sigmoid` to
~0.9997 / ~0.0003 regardless of pixels) is what makes the fired / not-fired outcome deterministic per
label — which is what lets Condition 4 be proven in **both** directions rather than asserted.

**A subtle fixture insight worth keeping.** The non-float test model declares `tensor(double)` via a
leading `Cast` so the session actually *loads* and the fail-closed dtype guard is what fires. A naive
double-input graph fails at **session construction** instead — which would have tested ORT's loader,
not our guard. The agent verified this empirically rather than assuming.

**RED-on-revert drilled on 11 guards** (each reverted, run, captured, restored). Two results are
worth recording beyond the pass/fail:

- **GD-4 (`SessionOptions` pin):** reverting it turned the **capture test RED while the behavioural
  double-run test still PASSED** — empirically confirming the security reviewer's own prediction that
  the capture test is the real revert-detector and the behavioural one can pass vacuously. The gate
  called this in advance; the drill proved it.
- **GD-7 (cache-path hashing):** reverting `_capability_fingerprint` to embed raw capability text made
  the path so long it raised `OSError: File name too long` — a visceral demonstration of why the
  fingerprint must stay hashed.

**Orchestrator verification (independent).**

- **No production code touched by this lane:** `git status` shows exactly the I.1/B-2 production files
  and nothing more; grepped `src/` for leftover drill markers (`DRILL`/`REVERTED`/`TEMP-revert`) —
  **CLEAN**.
- **Full battery re-run by me: 678 passed, 34 skipped, 0 failed** (exit 0), coverage **87.18%**,
  `ruff format --check` clean (215 files), `ruff check` clean, `mypy .` clean (213 files).
- **I drilled one RED-on-revert myself rather than trusting the report** — the GD-2 core dict guard.
  Reverting `labels = meta.get("labels") if isinstance(meta, dict) else None` to the unguarded form
  turned **4 tests RED** with exactly the misattribution D.1 §0.3 predicted:
  `--onnx-model <path>: failed to load ONNX model ('list' object has no attribute 'get')` — the
  *labels* defect blamed on the *model* flag. Restored; `diff` clean.

## ✅ Security's "do before merge" item — DISCHARGED (orchestrator, 2026-08-20)

The security gate upgraded this from follow-on to blocking: this mission's tests are the repo's first
real `InferenceSession` executions and had only ever run against the **drifted env ORT 1.22.0**, never
the **locked 1.23.2** — *"dtype strictness and error classes are exactly the things that shift between
ORT minors."*

Upgraded the `airedeal` env to the locked **`onnxruntime==1.23.2`** and re-ran:

| Check under locked ORT 1.23.2 | Result |
| --- | --- |
| ONNX-specific suites (66 tests across 5 files) | **all passed** |
| Full suite | **678 passed**, 0 failed (exit 0), coverage **87.18%** |
| `python main.py` byte-identity | sha **`545e22b2…d69d31f0`** — **still exact** |

**The env/lockfile drift is now corrected** (env `1.23.2` == lockfile `1.23.2`), and the ONNX path is
proven on the version CI would actually resolve. numpy held at **1.26.4** throughout.

## Gate V — post-implementation (blocking)

| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| GV.1 | Code review of the full diff (blast confined to CLI + provider selection; no finance/schema/ontology drift; **plus: is the B-1/B-2-expanded blast radius still justified, is the `on_provider_failure` seam over-built, and does the shipped code match the docs** — the docs lane wrote partly against in-flight code and that match is **not yet verified**) | staff-code-reviewer → sonnet | **DONE** 2026-08-20 → **CHANGES REQUIRED**, since **RESOLVED** |
| ~~GV.2~~ | ~~Bounded product call~~ — **moved to PD.1 (pre-Discovery)**, see the routing record. Not re-run at Gate V; GV.1 and GV.3 verify the shipped code and copy actually match the PD.1 decision | — | **MOVED** |
| GV.3 | Overclaim VETO re-check against the shipped strings/docs; condition-by-condition PASS/FAIL on all 8 Gate D conditions; **plus the escalated B-2 wording ruling** (is "no registered detector **is able to** examine the pixels" acceptable for the crash case, where a detector *is* registered and *did* fail?) and **explicit guidance for the manual-testing doc rewrite** | principal-principles-guardian → sonnet | **DONE** 2026-08-20 → **APPROVE WITH MODIFICATIONS** (all 8 conditions PASS) |

### GV.3 result — guardian: APPROVE WITH MODIFICATIONS, all 8 conditions PASS

Every Gate D condition verified against shipped code with `file:line` citations. Deterministic-core
invariant re-confirmed independently (`git diff main -- src/core/finance/ src/schemas/models.py`
empty). The guardian **required one production change** and gave binding guidance for the
manual-testing doc.

**The escalated B-2 wording ruling — it ruled against the shipped text**, and held the mission to its
own standard rather than waving it through late:

> "No registered detector can examine the pixels for it" reads to a plain-language user as "there is
> no capability for this," which is false when a detector was registered, declared the capability,
> and failed at inference.

It scoped the remedy tightly, having verified (as I did, at `runner.py:464`) that `covered` is
resolved **once per call** outside the per-image loop — so within a run a label's unconfirmed entries
are all-uncovered or all-crashed, never mixed. That let it **reject per-label/per-image plumbing as
scope creep** and **forbid rewording the base `UNCONFIRMED_HINT_NOTE`**, requiring instead a single
additive run-level note with deliberately hedged wording ("**may** reflect a detector that could not
be run"). It cleared the `provider_examination_failures` provenance block as honest and correctly
shaped. **Implemented and verified** — see below.

### GV.1 result — code reviewer: CHANGES REQUIRED (1 blocking), now RESOLVED

Architecture, culture, over-engineering sentinel, and output-compliance all **pass**. It confirmed the
six-label unlock is by declaration with **zero `ontology.py` diff**, that every subclass precedes its
superclass in the CLI except-chain, and that `restore_providers` is used in **every** test that
registers a provider. It judged the test suite strong on quality, not just count — singling out that
the determinism claim correctly ships **two** tests (behavioural + revert-detector) and that the
injection-barrier file includes a test documenting *where* the barrier is so the others cannot pass
by accident.

**⛔ The blocking finding, which my own green battery had HIDDEN.** `requirements-dev.txt` gained
`onnx>=1.17.0`, but **`requirements-dev.lock` was never regenerated** — and CI installs from the lock
(`.github/workflows/ci.yml:56`). I reproduced it exactly: a clean venv installing from the lock
succeeds, then `import onnx` → `ModuleNotFoundError`, and the ONNX test files **collection-error,
which interrupts the entire pytest session**. My 684-passing runs were all in the hand-tuned
`airedeal` env where I had manually `pip install`-ed `onnx` during the B-1 investigation and never
captured it in a lockfile. This is precisely the "green numbers are not evidence" trap, and I walked
into it.

**Resolved by me:** regenerated **both** lockfiles with the `uv pip compile` command CI's own comment
documents (regenerating them together, per CONTRIBUTING, so they cannot disagree). `requirements-dev.lock`
gained exactly `onnx==1.22.0` + transitive `ml-dtypes` — a two-package diff. `requirements.lock`
regenerated with **zero package-set change** and correctly **excludes `onnx`**, confirming it stays
dev-only as GD.1 required.

**On the blast radius into `main.py`'s path** (which I flagged to the reviewer as a possible scope
violation): it ruled **necessary, not scope creep**, and drew a distinction worth preserving — the
charter's actual invariant was *"`main.py` never reaches the ONNX path,"* and that **still holds**:
`CvTaggingOrchestrator` still only selects `"vision"`/`"local"` (`:53`), with no `onnx` branch. What
changed is the **B-2 honesty fix**, which was *already* universal the moment `runner.py` shipped,
because both producers call `tag_amenities_and_defects`. Threading the count through the orchestrator
only adds *diagnostic-note symmetry*; without it, `main.py` users would get the correct finding with
the staler explanation while `ingest-listing` users got the precise one — "two producers, two truths",
the exact pattern this codebase exists to prevent. Confirmed minimal: the count must originate where
the runner is actually called, and the alternative (module global / threadlocal) would be strictly
worse.

It also confirmed **no partially-applied or duplicated edits** after the mid-session revert/reapply
incident (single definitions of every new constant and function; all four files `ast.parse` cleanly).

## ⚠ Correction to previously-recorded suite figures (orchestrator error)

**The "678 passed / 34 skipped" and "684 passed / 34 skipped" figures recorded earlier in this tracker
were wrong on the skip count, and the error was mine.** I was counting characters in pytest's progress
dots, which is unreliable — coverage output interleaves with progress lines and my regex both missed
and mis-attributed characters (one run I counted as 648 was actually 684). The code reviewer disputed
the skip figure; it was right and I was wrong.

**Authoritative count, via `--junitxml` rather than dot-counting:**

```
collected=684  passed=684  failed=0  errors=0  skipped=0
```

There are **no skipped tests** in this suite. All previously-recorded skip counts in this document
should be read as **0**.

## ✅ Wave Validation — FINAL battery (orchestrator, 2026-08-20)

Run on the fully-settled tree, **cold `.cache/cv`**, after both lockfiles were regenerated:

| Gate | Result |
| --- | --- |
| `pytest` (JUnit-verified) | **684 collected, 684 passed**, 0 failed, 0 errors, **0 skipped** (exit 0) |
| Coverage | **87.20%** (80% gate met; mission start 86.09%) |
| `ruff format --check .` | clean, 216 files |
| `ruff check .` | All checks passed |
| `mypy .` | Success, 214 source files |
| `python main.py` | exit 0 · sha **`545e22b2…d69d31f0`** — **byte-identical to pre-mission baseline** |
| **CI-equivalent clean venv** | **684 passed, 0 failed** — installed from the regenerated `requirements-dev.lock`, on **numpy 2.2.6** and **ORT 1.23.2** (what CI actually resolves), cold cache |

### A test-isolation finding, chased down and cleared

The CI-equivalent venv initially produced **10 failures** — all of the shape "a provider that ran
successfully was reported as not having examined the image." I isolated it rather than assuming:
the failing tests **passed alone in both environments**; a cold-cache run in `airedeal` passed; and a
cold-cache run in the clean venv passed. **The cause was a stale local `.cache/cv`** left by my own
earlier manual experiments, not numpy 2.x, not the lockfile, and not a code defect.

**CI cannot hit this**: `.cache` is gitignored (`.gitignore:44`) and untracked, so a fresh checkout
always starts cold — verified. Logged as a **test-hygiene finding for the roadmap, not a mission
blocker**: the suite can be perturbed by a stale repo-local CV cache carrying entries written under
different provider bindings, and `pytest` alone does not clear it.

### Gate V decision record
**CLEARED 2026-08-20.** · Code review: ☑ **CHANGES REQUIRED → all resolved** (the blocking
`requirements-dev.lock`/`onnx` gap regenerated and re-verified in a clean CI-equivalent venv; the
non-blocking CHANGELOG gap closed) · Guardian: ☑ **NO VETO** (APPROVE WITH MODIFICATIONS — the one
required production change shipped and was verified; all 8 conditions PASS) · Shipped code matches
the PD.1 decision: ☑ (flags `--onnx-model`/`--onnx-labels`, env `AIREAL_ONNX_MODEL`/
`AIREAL_ONNX_LABELS`, per-field flag>env, half-a-pair a hard error, no `main.py` extension) ·
Orchestrator sign-off: **cleared — pending Roger's mission gate only.**

Non-blocking item deliberately **not** actioned (recorded, not silently dropped): a one-line mention
of the new `provider_examination_failures` shape in `src/orchestrators/README.md` /
`src/agents/README.md`. The reviewer marked it optional; it is an internal producer-shape note, not a
new public flag or env var. Logged for the next docs pass.

## Definition of Done — orchestrator verification (2026-08-20)

Every box checked by me against the tree, not against an agent's report.

| # | DoD item | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Documented flag pair + `AIREAL_*` env vars invoke `register_onnx_provider` before photo insights | ☑ | `--onnx-model`/`--onnx-labels` + `AIREAL_ONNX_MODEL`/`AIREAL_ONNX_LABELS`, `src/cli/ingest_cli.py`; exercised end-to-end in `tests/integration/test_ingest_cli_onnx.py` |
| 2 | `build_photo_insights` selects `"onnx"`; default byte-identical | ☑ | Precedence `onnx > vision > local`; `main.py` sha **`545e22b2…`** unchanged, re-verified on cold cache and in a CI-equivalent venv |
| 3 | `provider_kind="model"` end-to-end incl. provenance rows | ☑ | `test_ingest_cli_onnx.py:140,148,199`; verified independently by me against a model no agent built |
| 4 | Six labels adjudicated by a declaring model, **zero** ontology/schema change | ☑ | `..._confirms_a_filename_hint_end_to_end` **and** `..._contests_a_filename_hint_end_to_end` (both branches); `test_six_labels_declared_are_exactly_the_filename_rule_set`; zero `ontology.py` diff |
| 5 | Three error paths clean, no raw tracebacks | ☑ | **Exceeded** — 11+ paths tested incl. missing `onnxruntime` (monkeypatched), corrupt model, invalid JSON, empty labels, non-dict root, deep nesting, FIFO/dir, oversize, non-`tensor(float)` |
| 6 | RED-on-regression demonstrated + committed synthetic fixture | ☑ | 11 guards drilled revert→RED→restore; `tests/core/cv/_onnx_fixtures.py` (9.4 KB, generates at test time); I re-drilled GD-2 myself |
| 7 | `pytest` green ≥80% cov; ruff + mypy clean | ☑ | **684/684**, 0 skipped (JUnit-verified), **87.20%**; ruff clean (216 files); mypy clean (214 files) |
| 8 | No `src/core/finance/` diff; no breaking schema diff | ☑ | `git diff --stat` empty for both — confirmed by me and independently by both Gate V reviewers |
| 9 | Security sign-off · guardian VETO lifted · founder naming call | ☑ | GD.1 PASS-with-changes (all 7 implemented) · GD.2 + GV.3 NO VETO, 8/8 conditions PASS · PD.1 decided pre-Discovery |
| 10 | Docs honest; §3 row records offering 1 delivered, 2 & 3 open | ☑ | README / `src/core/README.md` / `src/cli/README.md` / CHANGELOG; §3 row reads "**Partially closed**… Offerings 2 and 3 remain OPEN" |
| 11 | Backlog #8 (`pip install -e .`) done in Wave Sync | ☑ | Metadata `0.1.0` → **`0.3.0`** |
| 12 | **Manual tests validated by Roger** | ☑ **2026-08-29** | **9 / 9 PASS**, 0 FAIL, 0 BLOCKED, no blocking issues; transcript recorded case-by-case in `docs/manual testing/MISSION_3_MANUAL_TESTING.md` |

### Charter language correction, recorded rather than silently applied

**DoD item 4 says the six labels "become detector-confirmed observations." That wording is
imprecise, and the Gate V guardian ruled on it.** A declaring model may examine the pixels and **not**
fire, which yields a **contested** hint — not a confirmation. The honest description is
**detector-adjudicated (confirmed OR contested)**. The guardian explicitly declined to ask anyone to
rewrite the charter (a historical planning artifact) but bound **every downstream Roger-facing
document** not to repeat the imprecision as fact. The implementation proves **both** branches, so the
DoD's *intent* is met and exceeded; only its phrasing was loose. Item 4 is ticked on that basis, with
the discrepancy recorded here rather than quietly reconciled.

## Mission gate (Roger) + Wave Integrate

| ID | Task | Agent → tier | Status |
| --- | --- | --- | --- |
| INT.1 | **DONE 2026-08-29** — merge **`8b59399`**, pushed to `origin/main` (`5dcdf1a..8b59399`), which also carried the previously-unpushed `6d9c000`; `origin/main...main` now `0 0`. Post-merge battery re-run on `main` in `airedeal`: **684 passed / 0 failed / 0 skipped** (JUnit-verified), coverage **87.20%**, `ruff format --check` 216 files clean, `ruff check` clean, `mypy .` clean (214 files), and `python main.py` on a cold `.cache/cv` still hashes **`545e22b2…`**. Never force-pushed. _Original task text:_ **Precondition:** Roger runs `docs/manual testing/MISSION_3_MANUAL_TESTING.md`; document-level box reads VALIDATED. Then: `git fetch`; rebase/merge onto latest `main`; re-run full battery post-rebase; `git merge --no-ff mission/3-byo-onnx-provider`; push at Roger's instruction (reconcile the origin delta — as of the branch cut that is **`6d9c000`**, the Mission 2 validation record, **not** the `a00a265` the charter named; never force-push). Record merge sha + push result | orchestrator (inline) + Roger → n/a | TODO |

### Mission gate decision record

**Status: CLEARED 2026-08-29 — Mission 3 is SHIPPED.** All 12 DoD boxes ticked: the 11
orchestrator-owned ones verified against the tree, and box 12 flipped by Roger's own 9/9 manual pass.

· Manual-testing doc VALIDATED by Roger: ☑ · Date: **2026-08-29** · Mission commit: **`bfb9cc2`** ·
Merge sha: **`8b59399`** (`--no-ff` into `main`) · Pushed: ☑ **yes** (`5dcdf1a..8b59399`, at Roger's
instruction; no force-push) · Notes: validation ran against the uncommitted working tree, as designed —
Roger validated exactly the tree that was then committed and merged, unchanged. The push also carried
the previously-unpushed `6d9c000` (Mission 2's validation record), so `origin/main` and `main` are now
in sync (`0 0`). The Mission 4 planning artifacts in the working tree were deliberately left
untracked and are **not** part of this merge.

**Committed and shipped 2026-08-29.** _(Historical: the entire mission sat uncommitted in the working
tree by design, so Roger validated exactly what he would merge — that held right up to the commit.)_
Mission commit `bfb9cc2` on `mission/3-byo-onnx-provider`, merged `--no-ff` as `8b59399`, pushed at
Roger's instruction. Both previously-outstanding `main` pushes are now closed: `6d9c000` (Mission 2's
validation record) rode along with this push, and `origin/main...main` is `0 0`.
