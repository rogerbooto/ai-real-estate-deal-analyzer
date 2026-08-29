# Mission 3 — Gate D Security Review (blocking gate)

_Reviewer: `principal-security-engineer`. Baseline reviewed: `main @ 6d9c000`, branch
`mission/3-byo-onnx-provider`, spec `docs/plans/MISSION_3_DISCOVERY_SPEC.md` read in full.
Every claim below was verified against the actual files at review time; error-class claims were
reproduced empirically in the `airedeal` env (onnxruntime 1.22.0; lockfile pins 1.23.2) in a
session scratchpad — no repro scripts or payloads are committed anywhere in this repo, per
project rule. This document describes classes of risk and their mitigations only._

## Verdict: **PASS WITH REQUIRED CHANGES**

The design is sound and one structural defense carries most of the weight: **the closed-set
ontology is the injection barrier.** A user-supplied `labels.json` string can only ever reach an
artifact, report, or cache path after resolving through `Ontology.lookup()` to a canonical name
(`_normalize_candidates` drops OOD; `_covered_labels` drops OOD; the report negative-findings gate
resolves via ontology; the cache key is a SHA-256 of the declaration, never raw text; the ONNX
provider emits only `{name, confidence}` — no evidence/rationale free text). No path was found by
which model or label content can write prose, markdown, filenames, or numbers into output. The
required changes below close the remaining gaps — all are small, are in code this mission writes
anyway (plus two one-to-three-line diffs in `_OnnxModel.__init__`, explicitly authorized by this
gate), and are **carried into implementation, not deferred**. Each carries a named regression
test; per the purple-team contract, a finding is not closed until its test exists and fails on
revert.

Threat model calibration, stated up front: this is a local, single-user CLI. The realistic
attacker is a **model pack downloaded from somewhere** (a `.onnx` + `labels.json` the user did not
author), not a hostile tenant. There is no privilege boundary between the tool and its user, no
server, and — decisive for several severities below — **no exfiltration channel from the ONNX
path** (no network egress, and output is closed-set labels plus floats). Severities are set
accordingly in both directions.

---

## A. Required changes (blocking — hard gate for merge)

### GD-1 (Medium) — Special files and unbounded reads: both paths must be validated as bounded regular files before use

**Verified:** a FIFO at the labels path hangs `open()` in `_OnnxModel.__init__` indefinitely (the
process had to be killed externally); a character-device path (`/dev/zero` class) gives
`json.load()` an unbounded read; a directory as labels raises `IsADirectoryError` (handled), and
huge-but-valid labels files are memory-bounded only by file size. `Path.is_file()` returns `False`
for FIFOs, devices, and directories (it checks `S_ISREG`, following symlinks), so one guard closes
the whole class. A silent infinite hang is the exact opposite of the DoD's "clean, actionable
messages" promise.

**Defense (CLI-side, in the new `ingest_cli.py` block, before `register_onnx_provider`):**
for each of the two resolved paths: `p = Path(raw)`; if not `p.is_file()` →
`SystemExit(f"--onnx-{model|labels} {raw}: not a regular file (missing, a directory, or a special
file). Check the path.")`. Additionally cap the labels file: `p.stat().st_size > 1_048_576` →
`SystemExit("--onnx-labels {raw}: implausibly large for a labels file (limit 1 MiB).")`. No cap on
the model file (real models are large; ORT streams it). TOCTOU between the check and the open is
**accepted** — there is no privilege boundary a race would cross in a single-user local process.

**Regression tests (`tests/integration/test_ingest_cli.py`):** directory-as-model,
directory-as-labels, missing files, oversize labels file (generated at test time), and — POSIX-only,
`pytest.mark.skipif(os.name != "posix")` — a `mkfifo` labels path, each asserting `SystemExit`
with the clean message and **no hang** (the guard makes the FIFO case return immediately; wrap in
a timeout to make a regression hang fail rather than wedge CI).

### GD-2 (Medium) — labels.json non-dict root: **ruling is option (B), fix it in core** — and then delete the CLI `except AttributeError` clause

**Verified:** a JSON array or string root raises raw `AttributeError` out of
`_OnnxModel.__init__` (`src/core/cv/amenities_defects.py:281`), exactly as the spec's §0.3 states.

**Ruling, on security grounds:** apply the one-line core fix —
`labels = meta.get("labels") if isinstance(meta, dict) else None` — so every root shape funnels
into the existing clean `ValueError`. The spec's option (A) (`except AttributeError` at the CLI)
is rejected: (i) it is a **broad-class catch that misattributes any internal `AttributeError`**
(onnxruntime API drift, numpy changes, a future refactor typo) to "your labels.json is malformed"
— masking real defects as user error is an anti-diagnostic pattern this codebase's own error
philosophy forbids; (ii) the CLI is not the only caller — `register_onnx_provider` is a documented
Python-API entry point, and containment at one caller leaves every other caller exposed; (iii)
input validation belongs in the function that reads the input. The charter's "core/cv is out of
scope" is a process constraint; this gate explicitly authorizes this one-line validation fix in the
exact function this mission makes reachable. With (B) applied, the spec's §4.3 `except
AttributeError` clause must **not** be added (error-table row 6 collapses into row 7).

**Regression tests:** unit test on `register_onnx_provider` with array/string/number roots →
`ValueError` with the canonical message (fails on revert of the core line); CLI test asserting
`SystemExit`, non-zero exit, message names `--onnx-labels`, no traceback.

### GD-3 (Low, but fix now — it is the same catch chain) — Deeply-nested labels JSON is misattributed to `--onnx-model`

**Verified:** a deeply-nested labels file raises `RecursionError` from `json.load()`, and
`RecursionError` **subclasses `RuntimeError`** — so the spec's §4.3 chain catches it in the
`except RuntimeError` clause, whose message is prefixed `--onnx-model {path}: ...`. Clean exit,
but the diagnostic points the user at the wrong file with a bewildering "maximum recursion depth
exceeded" tail.

**Defense:** add `except RecursionError` **before** `except RuntimeError` in the `ingest_cli.py`
chain, mapped to a labels-file message ("`--onnx-labels {path}: nested too deeply to be a labels
file.`"). (The GD-1 size cap does not close this — 1 MiB of open-brackets still recurses.)

**Regression test:** labels file of deeply nested arrays generated at test time → `SystemExit`,
message names `--onnx-labels`, no traceback.

### GD-4 (Medium) — Determinism `SessionOptions` pin: **ruling on spec §7 open item 3 is APPLY, not defer**

Reproducibility is an integrity control in this project, not a nicety — the honesty stance
("identical inputs produce identical artifacts") is what makes the deterministic-core invariant
auditable, and this mission's DoD claims determinism for the new path. `_OnnxModel.__init__`
currently constructs `InferenceSession` with default (multi-threaded) options; float reduction
order across threads is not associative. Pinning also modestly bounds thread fan-out from a
hostile graph.

**Defense (in `_OnnxModel.__init__`, authorized core diff, ~3 lines):** construct
`ort.SessionOptions()` with `intra_op_num_threads = 1`, `inter_op_num_threads = 1`,
`execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL`, and pass it to `InferenceSession`.

**Regression tests:** (1) run the synthetic fixture model twice over the same photo dir and assert
byte-identical detection payloads; (2) the pin itself: monkeypatch `onnxruntime.InferenceSession`
to capture the `sess_options` argument and assert the three fields — this is the test that fails
if the pin is reverted, independent of whether the tiny fixture happens to be thread-insensitive.

### GD-5 (Medium) — Trust-boundary warning + stale doc claim (docs, one pass)

A model file is not passive data: loading it drives a native protobuf deserializer and executes
the graph it declares. A small hostile file can, at minimum, allocate enormous memory or crash the
process natively (see D-2). The user must be told the file is trusted-by-choice.

**Defense:** one sentence in the `--onnx-model` help text and `src/cli/README.md`: "Only load
model files from sources you trust — a model file is executed by a native runtime; a malicious
one can exhaust memory or crash the process." In the same docs pass, fix the **stale claim at
`src/core/README.md:196`** ("intentionally not declared in `requirements.txt`") — it has been
false since `66ffacd` and a wrong security-posture statement in docs is itself a finding.
No test possible; gate check is review (Gate V).

### GD-6 (Low effort, Medium value) — Announce env-driven activation

A lingering `AIREAL_ONNX_MODEL`/`AIREAL_ONNX_LABELS` in the shell silently reroutes **every**
subsequent `ingest-listing` run through the user's model, outranking `--ai`, and the default
console summary's `provider=` field prints the constant `"cv_v2"` — only `version=onnx-byo-v1`
and the `--pretty` provenance dump reveal it. Silent env-driven provider substitution is exactly
the kind of ambient behavior this project's honesty posture exists to prevent.

**Defense:** on successful registration in `ingest_cli.main()`, print one stderr line naming the
resolved source per field, e.g.
`note: onnx provider registered (model: --onnx-model, labels: AIREAL_ONNX_LABELS)`.

**Regression test:** CLI run with env vars set (monkeypatched) asserts the note names the env
var; run with flags asserts it names the flags; run with neither asserts the note is absent.

### GD-7 (test-only, blocking with the rest of the suite) — Pin the label-injection barrier

The ontology closed-set defense (preamble) is real and verified, but nothing currently *pins* it
against a refactor that, e.g., starts echoing declared capabilities into provenance or report
text.

**Regression test (new, `tests/core/cv/`):** register an ONNX provider (monkeypatched
`_OnnxModel`, existing pattern) whose `labels.json` declares hostile-*shaped* strings —
markdown-metacharacter strings, control characters, an absurdly long string; placeholder-shaped,
no real payloads — plus one canonical label. Assert: (a) `build_photo_insights` output
(`model_dump()` serialized) contains none of the hostile strings anywhere; (b) every
`image_detections` name is a member of the ontology; (c) no cache file or directory created under
the cache root contains any hostile string in its path. Use the established `restore_providers`
snapshot fixture (`tests/core/cv/test_filename_corroboration.py:96`) — mandatory for every test
that registers a provider (spec §4.5 concurs).

---

## B. Rulings on the pre-surfaced findings

1. **`labels.json` `AttributeError` (spec §0.3):** ruled — **option (B), core fix**, CLI
   `except AttributeError` clause dropped. Full rationale and tests in GD-2.
2. **`onnxruntime` already a hard dependency (spec §0.1, charter constraint #9):** ruled —
   **accept the spec's recommendation**: keep `requirements.txt:27` as-is, fix the stale doc line
   (GD-5). Security-posture assessment: shipping ORT by default is *not* a regression introduced
   by that pin — ORT was already reaching every user transitively through `crewai` before
   `66ffacd`; an explicit, floor-and-ceiling-pinned, lockfile-resolved declaration
   (`>=1.16.0,<2.0.0`, lock `1.23.2`) is a strictly **better** posture than an unpinned
   transitive: it is visible to audit, upgradable deliberately, and cannot be silently dropped or
   downgraded by an agent-framework bump. The known path-traversal CVE family in the ONNX
   ecosystem (CVE-2022-25882, CVE-2024-27318, CVE-2024-7776, CVE-2025-51480 lineage) lives in the
   **`onnx` Python package's helper functions**, not in `onnxruntime`'s inference path; no
   unpatched advisory against ORT 1.23.2 surfaced in this review. Moving ORT to an extras group
   mid-mission would change the documented install behavior for zero security gain; charter
   constraint #9 should be reworded at Gate V to match reality ("stays pinned and
   audit-visible"), not enforced as written. Tracked follow-on: T-1 below.
3. **First real `InferenceSession` in the test suite (spec §0.4):** acknowledged; this is the
   coverage the mission needs. The determinism tests in GD-4 and the fixture plan ruling (B-4)
   govern how it lands. Test-pollution control is GD-7's fixture requirement.
4. **Dev-only `onnx` fixture dependency (spec §8, Option A):** ruled — **approved, with a floor
   pin `onnx>=1.17.0`** in `requirements-dev.txt` (clears the CVE-2024-7776 and
   CVE-2024-27318/CVE-2022-25882 fix lines). Exposure analysis: the fixture path uses only
   in-memory graph construction (`onnx.helper.make_*`) of a self-authored model — it never parses
   an untrusted model and never touches the vulnerable external-data/download helpers; dev/CI-only
   footprint; shares its `protobuf` dependency with already-required ORT. Option A also keeps the
   fixture auditable in the diff, which this gate values over Option B's opaque committed binary
   (an unauditable binary blob in a security-sensitive test is its own smell).

---

## C. Accepted risks (explicit, with rationale)

- **AR-1 — Hostile model resource exhaustion / native crash (allocation bomb).** A tiny `.onnx`
  can declare tensors or graph expansions that allocate arbitrary memory at load or first run;
  ORT failures at that depth can be native (abort/OOM-kill), which **no Python `except` chain can
  catch**. There is no practical cap short of subprocess sandboxing, which is disproportionate
  for a local single-user tool loading a user-chosen file against the user's own machine.
  Accepted; compensating control is the GD-5 trust warning. The catch-chain's guarantees are
  hereby scoped honestly: "no raw *traceback*" is promised; "no native crash on a hostile model"
  is not.
- **AR-2 — External-data tensor file reads.** An ONNX model may reference sibling files by
  relative location, resolved against the model's directory; directory containment is not a
  guarantee this mission relies on. Impact here: file content becomes tensor weights, and the
  ONNX path's only outputs are closed-set label names and floats read by the same local user —
  **no exfiltration channel exists** (no network egress from this path; no model-derived free
  text in any artifact — verified, and pinned by GD-7). Residual: a hostile model could vary six
  confidences with file content — a few bits per run, visible only to the user who ran it.
  Accepted; compensating controls are GD-5 and GD-7.
- **AR-3 — TOCTOU between the GD-1 validation and the open.** No privilege boundary to cross in
  a single-user local process. Accepted.
- **AR-4 — User-supplied paths echoed in error messages.** Correct UX for a local CLI (the person
  reading the terminal chose the path); no secret material is in scope. A path containing
  control/ANSI characters could style the author's own terminal — accepted.
- **AR-5 — `--onnx-model ""` (empty string) falls through to the env var** under the spec's
  `args.onnx_model or os.getenv(...)` resolution — an empty flag cannot mask a set env var.
  Harmless quirk of truthiness-based precedence; accepted and noted so a future reader knows it
  was seen.

## D. Verified-safe (no action; noted so they are not re-litigated)

- **Prompt-injection / report-injection via labels or model output:** structurally closed by the
  ontology barrier (preamble); pinned by GD-7. The LLM never sees ONNX output as free text, and
  the deterministic finance core is untouched (spec §9 confirms zero `core/finance` diff).
- **Custom operators / execution providers:** ORT cannot be made to load a custom-op shared
  library or non-CPU execution provider *by the model file alone*; both require explicit
  `SessionOptions`/`providers` arguments the code pins (`CPUExecutionProvider` only, and after
  GD-4, explicit `SessionOptions` the CLI never exposes). The CLI passes no `**kwargs` through to
  `register_onnx_provider`.
- **Cross-process artifact seam:** `deal-report` rendering an artifact stamped
  `selected_provider="onnx"` in a process with no registration already degrades conservatively
  ("not checked", never a fabricated negative) — `src/core/reports/generator.py:668-683`, already
  regression-tested at `tests/core/reports/test_photo_capability_gating.py:140-183`.
- **Cache poisoning across registrations:** cache key includes a SHA-256 capability fingerprint
  (`runner.py:69-80`); different `labels.json` → different namespace; already tested.
- **Process-global registry:** fresh process per real CLI invocation; in-suite pollution is
  governed by the mandatory `restore_providers` fixture (GD-7). `_PROVIDER_CAPABILITIES` grows
  one entry per registration (new closure each time) — bounded in practice, documented behavior,
  no action.
- **Secrets:** the two new env vars carry paths, not credentials; nothing in this mission touches
  `OPENAI_API_KEY` handling.
- **NaN/Inf/`>1` model outputs:** traced through `predict_proba` → `_normalize_candidates`; NaN
  fails every cutoff comparison and is dropped; out-of-range triggers the sigmoid fallback.
  Bounded confidences reach output.

## E. Tracked follow-ons (not blocking this mission)

- **T-1:** add `pip-audit` (dev-only) against `requirements.lock`/`requirements-dev.lock` to the
  dev workflow — nothing in the toolchain audits pins today, and this mission's ruling B-2 leans
  on "no known unpatched advisory," which should be a checked fact, not a point-in-time one.
- **T-2:** the local `airedeal` env runs ORT 1.22.0 while the lockfile pins 1.23.2 — refresh the
  env from the lock so tests exercise the pinned version.
- **T-3 (Gate V wording):** charter constraint #9 ("stays opt-in") should be restated to match
  reality per ruling B-2.

## F. Invariant matrix delta (the running scorecard)

| Invariant | Status after this mission (with GD-1..GD-7 applied) |
| --- | --- |
| LLM never computes/overrides financial numbers | Unchanged — ONNX path emits closed-set labels only; zero `core/finance` diff |
| Fetcher refuses non-HTTP(S)/private/unbounded | Unchanged — no new network path (ONNX path has none) |
| Media downloads cannot escape `dest_dir` | Unchanged |
| robots.txt consulted on every remote fetch | Unchanged |
| No secrets in logs/reports/artifacts/cache | Unchanged — new env vars are paths |
| **New:** model/label content cannot reach output except through the ontology closed set | GD-7 test pins it |
| **New:** every `--onnx-*` error path exits cleanly, correctly attributed, without hanging | GD-1/GD-2/GD-3 tests pin it |
| **New:** ONNX inference is single-threaded-deterministic | GD-4 tests pin it |
