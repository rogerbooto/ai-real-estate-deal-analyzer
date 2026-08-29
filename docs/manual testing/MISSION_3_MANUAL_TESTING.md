# Mission 3 — Bring-Your-Own ONNX Model — Manual Testing Handoff

_Author: `staff-qa-test-engineer` · Rewritten & spot-run 2026-08-20 against branch
`mission/3-byo-onnx-provider`, working tree on top of `main @ 6d9c000` (Mission 2's validated base)._

> ## ⚠ Read this first — the mission's status changed since this doc was requested
>
> This doc was originally commissioned as an **acceptance test plan for work not yet built**
> ("every case below currently FAILS"). **That premise is out of date.** Ground truth on the
> `mission/3-byo-onnx-provider` branch today: the CLI wiring, the two blocker fixes (B-1 float32
> preprocessing, B-2 the false "a detector examined this and disagreed" claim), the test suite,
> and the docs pass are all **built and green**. Every command below was run by hand, once, on
> this tree, before this doc was handed to you — see "How this doc was produced" below.
>
> **What is still open, honestly:** `docs/plans/MISSION_3_SPRINT_TRACKER.md`'s Gate V (code review
> + guardian re-check of the shipped diff) was still in progress at the time this doc was written.
> Gate V and this manual-testing pass are independent gates — this doc validates *behaviour*; Gate V
> validates the *diff*. Both must clear before the Mission Gate. If you want the very latest Gate V
> verdict, read the tracker before you start; it does not change anything below, because every
> command here was re-verified directly against the running code, not against a report of it.
>
> **A parallel, unrelated change may be present on this branch when you run these commands.** A
> small additive fix — a one-line note printed only when a photo provider *fails* mid-run (crashes)
> while examining an image — was landing on this branch concurrently with this doc's authoring. The
> synthetic model this doc has you build never fails (it always returns a score for every label), so
> that note will **not** appear in any command below. If you ever see a line starting `Note: a
> registered detector failed to examine N photo(s) during this run...`, it is that unrelated
> mechanism firing on something outside this doc's scope — not a defect in the ONNX path.

> **Verify the tree before trusting anything below:**
> `git branch --show-current` → `mission/3-byo-onnx-provider` (or, once merged, `main` with the
> merge commit in `git log`). If neither, you may be on the wrong tree.

### How this doc was produced

Every command in every case below was executed, once, on `mission/3-byo-onnx-provider` in the
`airedeal` conda env, and the output shown is real, transcribed output — not a prediction. Two
things worth knowing before you start:

1. **The exact confidence numbers you see (e.g. `0.9996...`) will match yours to several decimal
   places**, because the fixture generator in Case 1 seeds its random weights (`np.random.default_rng(1337)`)
   and the sample photos it runs against (`data/sample_listings/36_kelly_moncton/photos/`) are
   tracked in git, so their bytes are fixed. Do not worry if the last couple of digits differ by a
   hair depending on your machine's floating-point library — the ontology cutoffs this mechanism
   depends on (0.60–0.70) have wide margin against the fixture's saturated ~0.9997 / ~0.0003 values,
   so the *outcome* (confirmed vs. contested vs. absent) will not change.
2. **`.cache/cv` is keyed by image content hash, not filename or provider.** Several cases below
   tell you to `rm -rf .cache/cv` before running. Do it — skipping it can serve a stale answer
   computed under a different provider/filename and make a case look like it failed when it did
   not (this is a real trap the mission's own implementation lane hit; see the sprint tracker's
   "cache-pollution trap" note).

---

**Overall validation:** ☐ NOT VALIDATED ☑ **VALIDATED** (Roger, 2026-08-29) ☐ VALIDATED WITH ISSUES
**Blocking issues found:** **None.** All 9 cases PASS, 0 FAIL, 0 BLOCKED. Whole suite green
(**684 passed**, coverage **87.20%** against the 80% gate), `ruff format --check` clean (216 files),
`ruff check` clean, `mypy .` clean (214 source files). The DEFERRED table at the end of this doc —
including `main.py` structurally not reading the ONNX flags/env vars — was reviewed and accepted.

> ## ✅ Mission 3 is manually validated
>
> Every command in this doc was driven by hand by Roger on 2026-08-29 in the `airedeal` conda env on
> branch `mission/3-byo-onnx-provider` (working tree on top of `main @ 6d9c000`), and every case
> passed. Case 6's `IDENTICAL -- main.py ignores the ONNX env vars entirely` is the **expected**
> outcome, not a defect — see the DEFERRED section at the end of this doc.

### Validation record — 2026-08-29

| | |
| --- | --- |
| **Validated by** | Roger Booto Tokime, driving every command manually |
| **Date** | 2026-08-29 |
| **Tree** | `mission/3-byo-onnx-provider`, uncommitted working tree on top of `main @ 6d9c000` |
| **Environment** | conda env `airedeal` (`/home/rtokime/anaconda3/envs/airedeal/bin/python`), `OUT=/tmp/m3` |
| **Result** | **9 / 9 cases PASS**, 0 FAIL, 0 BLOCKED |
| **Whole-suite sanity** | **684 passed**, 0 failed, coverage **87.20%**; ruff format (216 files) + ruff check + mypy (214 files) all clean |
| **DEFERRED table** | Reviewed and accepted; offerings 2 (hosted API key) and 3 (project-trained model) remain deliberately unbuilt |

Each case below now carries its **Actual result observed**, transcribed from that session.

---

## What this mission is, precisely (read before testing)

You supply your own trained ONNX image classifier. The project registers it, runs it against your
photos, and reports what it returned — honestly labelled as **your** model's output, not the
project's. `provenance.provider_kind` flips to `"model"` to say *a real classifier ran*, not that
its output is correct. **The project does not vouch for the accuracy of any model you point it
at** — that is not a hedge, it is the actual scope of what shipped. This is **offering 1 of 3** on
the "no real AI provider" backlog item (`docs/plans/ROADMAP_TRACKER.md` backlog #3) — see
"Deferred / out of scope" at the end of this doc for what offerings 2 and 3 are and why they are
not covered here.

---

## Prerequisites (do this once)

1. `cd /home/rtokime/projects/Personal/ai-real-estate-deal-analyzer`
2. `source /home/rtokime/anaconda3/etc/profile.d/conda.sh && conda activate airedeal`
3. `which python` → must be `/home/rtokime/anaconda3/envs/airedeal/bin/python`
4. `git branch --show-current` → `mission/3-byo-onnx-provider`
5. `mkdir -p /tmp/m3 && export OUT=/tmp/m3`
6. Confirm the sample photos this doc runs against exist:
   `ls data/sample_listings/36_kelly_moncton/photos/` (should list 12 files).

The CLIs are: `ingest-listing` (ingest a listing / tag photos), `deal-report`, `deal-advisor`, and
`python main.py` (the deterministic default pipeline). All resolve on `PATH` after
`conda activate airedeal`.

---
---

## Case 1 — Generate the ONNX model + labels fixture you'll use for every later case

**Goal:** You have no `.onnx` file lying around, and this mission's own test fixture is generated
*inside the test suite*, not shipped as a file you can point at. This case builds you one — a real,
valid, tiny ONNX classifier plus its `labels.json` — so every case after this one has something to
register.

**What it is, honestly:** a ~365-byte model with almost no real "vision" in it (`GlobalAveragePool →
Reshape → Gemm → Sigmoid`) whose per-label output is deliberately biased far into `Sigmoid`'s
saturation range so that one label (`mold_suspected`) always fires (~0.9997) and the other five
always stay silent (~0.0003), regardless of what is actually in the photo. This is the same
"biased-output-unit" technique the mission's own automated tests use
(`tests/core/cv/_onnx_fixtures.py`) — it is not cheating on the CLI wiring under test, it is what
makes the fired/not-fired outcome depend on the file name (what this mission is actually about),
not on pixel content, so both outcomes in Case 3 can be demonstrated on purpose rather than hoped
for.

**Command**
```bash
mkdir -p $OUT/onnx
python - <<'PY'
import json
import numpy as np
import onnx
from onnx import TensorProto, helper

LABELS = ["mold_suspected", "water_leak_suspected", "ev_charger",
          "parking_garage", "parking_driveway", "dishwasher"]
FIRE = {"mold_suspected"}  # this label always fires; the other five always decline to fire
K = len(LABELS)
BIAS_FIRE, BIAS_SILENT, SEED = 8.0, -8.0, 1337

input_tensor = helper.make_tensor_value_info("pixels", TensorProto.FLOAT, [1, 3, "H", "W"])
output_tensor = helper.make_tensor_value_info("scores", TensorProto.FLOAT, [1, K])

nodes = [helper.make_node("GlobalAveragePool", ["pixels"], ["pooled"])]
reshape_shape = helper.make_tensor("reshape_shape", TensorProto.INT64, [2], [1, 3])
nodes.append(helper.make_node("Reshape", ["pooled", "reshape_shape"], ["flat"]))

rng = np.random.default_rng(SEED)
weight = (rng.standard_normal((3, K)) * 0.01).astype(np.float32)
bias = np.full((K,), BIAS_SILENT, dtype=np.float32)
for i, name in enumerate(LABELS):
    if name in FIRE:
        bias[i] = BIAS_FIRE
w_init = helper.make_tensor("W", TensorProto.FLOAT, [3, K], weight.flatten().tolist())
b_init = helper.make_tensor("B", TensorProto.FLOAT, [K], bias.tolist())

nodes.append(helper.make_node("Gemm", ["flat", "W", "B"], ["logits"]))
nodes.append(helper.make_node("Sigmoid", ["logits"], ["scores"]))

graph = helper.make_graph(nodes, "roger_fixture", [input_tensor], [output_tensor],
                           initializer=[w_init, b_init, reshape_shape])
model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
model.ir_version = 8
onnx.checker.check_model(model)

with open("/tmp/m3/onnx/model.onnx", "wb") as f:
    f.write(model.SerializeToString())
with open("/tmp/m3/onnx/labels.json", "w") as f:
    json.dump({"labels": LABELS}, f)

print("wrote model.onnx (", len(model.SerializeToString()), "bytes) + labels.json")
print("fires on:", sorted(FIRE))
PY
```

**Expected result**
```
wrote model.onnx ( 365 bytes) + labels.json
fires on: ['mold_suspected']
```
and `ls -la $OUT/onnx/` shows `model.onnx` and `labels.json`.

**Confirm it actually works end to end** (this is the whole point — a model that only loads but
never runs is worthless for this doc):
```bash
ingest-listing --file data/sample_listings/36_kelly_moncton/listing.txt \
  --photos data/sample_listings/36_kelly_moncton/photos \
  --onnx-model $OUT/onnx/model.onnx \
  --onnx-labels $OUT/onnx/labels.json 2>&1 | grep -E "provider=|note:"
```
**Expected result:**
```
note: onnx provider registered (model: --onnx-model, labels: --onnx-labels)
note: --download-media/--max-media/--media-kinds/--media-intel require an HTML source (--url) to scan for media links; --file input alone yields an empty media bundle. Use --photos for a local photo directory instead.
provider=cv_v2, version=onnx-byo-v1, images_total=12, detections_total=12, ..., defect_counts={'mold_suspected': 12}
```
(the second `note:` line is unrelated F11 media-flag behaviour from Mission 2 — ignore it, it is
not part of this mission)

**Pass/fail criterion:** Does the generator produce a 2-file fixture, and does registering it
against the real sample photos exit 0 with `version=onnx-byo-v1` and a non-zero
`defect_counts={'mold_suspected': ...}`? Yes = PASS. (If this case fails, every later case is
BLOCKED — stop and report it.)

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-08-29
**Actual result observed:** Fixture built: `model.onnx` (365 bytes) + `labels.json`, fires on `mold_suspected`. Run printed `note: onnx provider registered (model: --onnx-model, labels: --onnx-labels)` and `provider=cv_v2, version=onnx-byo-v1, images_total=12, detections_total=12, defect_counts={'mold_suspected': 12}`.

---

## Case 2 — Happy path: registering a real ONNX model and seeing it actually used

**Goal:** Passing the two ONNX flags makes `ingest-listing` register your model and actually route
photo tagging through it — and the run honestly reports that a real classifier (not a stub) ran.

**Command**
```bash
rm -rf .cache/cv
ingest-listing --file data/sample_listings/36_kelly_moncton/listing.txt \
  --photos data/sample_listings/36_kelly_moncton/photos \
  --onnx-model $OUT/onnx/model.onnx \
  --onnx-labels $OUT/onnx/labels.json --pretty 1 2>&1 | \
  grep -E "note:|version=onnx-byo-v1|'selected_provider'|'provider_kind': 'model'"
```

**Expected result:**
```
note: onnx provider registered (model: --onnx-model, labels: --onnx-labels)
note: --download-media/--max-media/--media-kinds/--media-intel require an HTML source (--url) to scan for media links; --file input alone yields an empty media bundle. Use --photos for a local photo directory instead.
provider=cv_v2, version=onnx-byo-v1, images_total=12, detections_total=12, ...
                  'provider_kind': 'model',
                  'selected_provider': 'onnx',
```

**Where exactly to look, if you want to see it without `--pretty 1`'s wall of JSON:** the console
summary line always starts `photo insights: \nprovider=cv_v2, version=...` — `provider=` is a fixed
schema constant (`cv_v2`) and does **not** change; the field that tells you the ONNX path was used
is `version=onnx-byo-v1`. The full `provenance.selected_provider`/`provenance.provider_kind` pair
only appears with `--pretty 1` (or by reading the cached JSON under `.cache/cv`).

**Pass/fail criterion:** Does the run exit 0, print `version=onnx-byo-v1`, and (in `--pretty 1`
output) show `'selected_provider': 'onnx'` and `'provider_kind': 'model'`? Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-08-29
**Actual result observed:** On a cold `.cache/cv`, the `--pretty 1` payload showed `'selected_provider': 'onnx'` and `'provider_kind': 'model'`, alongside `version=onnx-byo-v1` on the summary line.

---

## Case 3 — The six-label unlock is detector-adjudicated: confirmed **or** contested, not always confirmed

**Goal — read this carefully, it is the most easily-overclaimed part of this mission.** Six labels
(`mold_suspected`, `water_leak_suspected`, `ev_charger`, `parking_garage`, `parking_driveway`,
`dishwasher`) can be *suggested* by a photo's file name today, but with no registered detector that
covers them, a file-name-only suggestion stays an unscored hint — nothing has looked, so nothing can
agree or disagree. Registering an ONNX model that **declares** one of these labels in its
`labels.json` changes that: for **any image where a filename rule matches**, the label becomes one
of two things, **and both are legitimate, honest outcomes**:

- **`filename_confirmed`** — the model's own per-image inference *also* reported the label for that
  image. The file name and a real detector agree. Confidence is a blended `0.70 × (the model's own
  confidence) + 0.30` (the documented 70/30 split).
- **`filename_contested`** — the model declares it can recognise the label, was actually run on
  that image, and did **not** report it there. The file name and the detector *disagree*. This is
  scored at a flat `0.30` and is explicitly withheld from every money-affecting count — a contested
  claim never moves a number.

**This case's fixture is deliberately rigged (per this mission's own guardian ruling) so both
branches can be demonstrated in one run**, using the biased model from Case 1: it always fires on
`mold_suspected` and never fires on any of the other five. **Do not read this as "registering any
ONNX model always confirms a filename match" — that is not true in general.** A real user's model
looking at a real photo may legitimately disagree with a filename, and when it does, the honest
result is `filename_contested`, not a failure of the mechanism.

**Command**
```bash
rm -rf .cache/cv $OUT/photos_confirm
mkdir -p $OUT/photos_confirm
python - <<'PY'
from PIL import Image
Image.new("RGB", (400, 300), (150, 150, 150)).save("/tmp/m3/photos_confirm/mold_basement.jpg")
Image.new("RGB", (400, 300), (170, 170, 170)).save("/tmp/m3/photos_confirm/parking_garage_view.jpg")
PY
ingest-listing --file data/sample_listings/36_kelly_moncton/listing.txt \
  --photos $OUT/photos_confirm \
  --onnx-model $OUT/onnx/model.onnx \
  --onnx-labels $OUT/onnx/labels.json --pretty 1 2>&1 | \
  grep -E "filename_confirmed|Contested photo hint|contested_hint_counts|defect_counts"
```

**Expected result:**
```
provider=cv_v2, version=onnx-byo-v1, images_total=2, detections_total=2, ..., defect_counts={'mold_suspected': 2}
             "Contested photo hint: a file name suggests 'parking_garage', but a detector able to recognise it "
  'contested_hint_counts': {'parking_garage': 1},
  'defect_counts': {'mold_suspected': 2},
                                                                                                'source': 'filename_confirmed'}],
```
- `mold_basement.jpg` (filename matches the `mold_suspected` rule, and the model fires on
  `mold_suspected` for every image) → `source: 'filename_confirmed'`.
- `parking_garage_view.jpg` (filename matches the `parking_garage` rule, but the model declares and
  never fires on `parking_garage`) → routed to `contested_hint_counts`, not to `amenity_counts` — no
  dollar figure anywhere in a report can move because of it.

**Pass/fail criterion:** Does the same run produce **both** a `filename_confirmed` entry **and** a
contested/withheld entry, with the contested one absent from every counted total? Yes = PASS. (If
every filename match came back confirmed with no contested case reachable, that would indicate the
mechanism can't actually disagree with a filename — report it, do not mark PASS.)

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-08-29
**Actual result observed:** Both branches demonstrated in one run over the two synthetic photos: `mold_basement.jpg` confirmed (`'source': 'filename_confirmed'`, `defect_counts={'mold_suspected': 2}`), while `parking_garage_view.jpg` was **contested** — `'contested_hint_counts': {'parking_garage': 1}` plus the “Contested photo hint…” line, and `parking` stayed `False` in `amenities` with `amenity_counts={}`, i.e. absent from every counted total.

---

## Case 4 — Environment variables register the model, and a CLI flag always wins over its env var

**Goal:** `AIREAL_ONNX_MODEL`/`AIREAL_ONNX_LABELS` work exactly like the flags (matching the
existing `AIREAL_*` convention), and **per field**, a CLI flag beats its own env var if both are
set — never the other way around.

**Command — env vars alone**
```bash
rm -rf .cache/cv
AIREAL_ONNX_MODEL=$OUT/onnx/model.onnx \
AIREAL_ONNX_LABELS=$OUT/onnx/labels.json \
ingest-listing --file data/sample_listings/36_kelly_moncton/listing.txt \
  --photos data/sample_listings/36_kelly_moncton/photos --pretty 0 2>&1 | grep -E "note:|provider="
```
**Expected:** `note: onnx provider registered (model: AIREAL_ONNX_MODEL, labels: AIREAL_ONNX_LABELS)`
and `version=onnx-byo-v1` in the summary line.

**Command — flag beats env (both env vars point at bogus nonexistent paths; the flags point at the
real fixture)**
```bash
rm -rf .cache/cv
AIREAL_ONNX_MODEL=/tmp/does_not_exist_model.onnx \
AIREAL_ONNX_LABELS=/tmp/does_not_exist_labels.json \
ingest-listing --file data/sample_listings/36_kelly_moncton/listing.txt \
  --photos data/sample_listings/36_kelly_moncton/photos \
  --onnx-model $OUT/onnx/model.onnx \
  --onnx-labels $OUT/onnx/labels.json --pretty 0 2>&1 | grep -E "note:|provider="
```
**Expected:** `note: onnx provider registered (model: --onnx-model, labels: --onnx-labels)` and the
run **succeeds** (exit 0) — proving the flags, not the bogus env paths, were used.

**Command — per-field mix (only `--onnx-model` given as a flag; `--onnx-labels` resolved from env)**
```bash
rm -rf .cache/cv
AIREAL_ONNX_LABELS=$OUT/onnx/labels.json \
ingest-listing --file data/sample_listings/36_kelly_moncton/listing.txt \
  --photos data/sample_listings/36_kelly_moncton/photos \
  --onnx-model $OUT/onnx/model.onnx --pretty 0 2>&1 | grep -E "note:|provider="
```
**Expected:** `note: onnx provider registered (model: --onnx-model, labels: AIREAL_ONNX_LABELS)` —
the note names the resolved *source* of each field independently, proving precedence is per-field,
not all-or-nothing.

**Pass/fail criterion:** Do all three runs succeed, and does the `note:` line correctly name which
source (flag vs. env) won for each field? Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-08-29
**Actual result observed:** Env-only run printed `note: onnx provider registered (model: AIREAL_ONNX_MODEL, labels: AIREAL_ONNX_LABELS)` and ran the model. With bogus env paths plus valid flags, the note read `(model: --onnx-model, labels: --onnx-labels)` and the run succeeded — flags won per field, the bad env paths were never touched. The mixed case (model by flag, labels by env) reported `(model: --onnx-model, labels: AIREAL_ONNX_LABELS)`. All three ran `version=onnx-byo-v1`.

---

## Case 5 — A registered ONNX model outranks `--ai`

**Goal:** `--ai` is **not** required to activate the ONNX path — pointing at a model is itself the
activation signal. When both are supplied, ONNX wins.

**Command**
```bash
rm -rf .cache/cv
ingest-listing --file data/sample_listings/36_kelly_moncton/listing.txt \
  --photos data/sample_listings/36_kelly_moncton/photos \
  --ai 1 \
  --onnx-model $OUT/onnx/model.onnx \
  --onnx-labels $OUT/onnx/labels.json --pretty 0 2>&1 | grep -E "provider="

# control: --ai 1 alone (no ONNX flags) selects the vision stub, not ONNX
rm -rf .cache/cv
ingest-listing --file data/sample_listings/36_kelly_moncton/listing.txt \
  --photos data/sample_listings/36_kelly_moncton/photos \
  --ai 1 --pretty 0 2>&1 | grep -E "provider="
```

**Expected result:** the first run reads `version=onnx-byo-v1` (ONNX won despite `--ai 1`); the
second (control) run reads `version=vision-stub-v1` (the heuristic stub, exactly what `--ai` alone
has always done — see Mission 2's W2.6).

**Pass/fail criterion:** Does `--onnx-model`/`--onnx-labels` win over `--ai 1` when both are
present, and does `--ai 1` alone still fall back to `vision-stub-v1`? Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-08-29
**Actual result observed:** `--ai 1` **with** the ONNX flags → `version=onnx-byo-v1`, `defect_counts={'mold_suspected': 12}`. `--ai 1` alone → `version=vision-stub-v1`, `detections_total=6`, `amenity_counts={'stainless_appliances': 6}`. ONNX outranks `--ai`; removing it falls back.

---

## Case 6 — With no ONNX flags, output is byte-identical to before this mission

**Goal:** This mission must not change anything for a run that doesn't use it. Prove it two ways:
the demo report's sha256 matches the pinned pre-mission baseline, and `python main.py` ignores the
ONNX env vars entirely even when they're set to a real, working model (because `main.py` reaches
photo tagging through a different seam — see "Deferred / out of scope" below).

**Command**
```bash
rm -rf .cache/cv
python main.py --out $OUT/rep1.md
python main.py --out $OUT/rep2.md
sha256sum $OUT/rep1.md $OUT/rep2.md

# main.py ignores the ONNX env vars even when they point at a real, working model
AIREAL_ONNX_MODEL=$OUT/onnx/model.onnx \
AIREAL_ONNX_LABELS=$OUT/onnx/labels.json \
python main.py --out $OUT/rep_onnx_env.md
diff $OUT/rep1.md $OUT/rep_onnx_env.md && echo "IDENTICAL -- main.py ignores the ONNX env vars entirely"
```

**Expected result:**
```
545e22b20b967b37c5b7ba20477f9df7c85f5b5a7c151f2e0d79b543d69d31f0  /tmp/m3/rep1.md
545e22b20b967b37c5b7ba20477f9df7c85f5b5a7c151f2e0d79b543d69d31f0  /tmp/m3/rep2.md
...
IDENTICAL -- main.py ignores the ONNX env vars entirely
```
That sha is the exact pre-mission baseline recorded in the sprint tracker
(`docs/plans/MISSION_3_SPRINT_TRACKER.md`) — it should match yours exactly, byte for byte.

**Pass/fail criterion:** Do both `main.py` runs match that sha, and does setting the ONNX env vars
make zero difference to `main.py`'s output? Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-08-29
**Actual result observed:** Two baseline `python main.py` runs produced identical sha256 `545e22b20b967b37c5b7ba20477f9df7c85f5b5a7c151f2e0d79b543d69d31f0` (verdict `DECLINE`), and a third run with `AIREAL_ONNX_MODEL`/`AIREAL_ONNX_LABELS` set to the real working fixture `diff`ed clean against it — `IDENTICAL -- main.py ignores the ONNX env vars entirely`. This is the documented, intended scope boundary (see DEFERRED below).

---

## Case 7 — Error paths: every bad input fails cleanly, never with a raw traceback

Each of the eight sub-cases below was run and produced a clean, actionable, non-zero-exit message —
no Python traceback in any of them.

### 7a — Partial pair: only `--onnx-model` given
```bash
ingest-listing --file data/sample_listings/36_kelly_moncton/listing.txt \
  --photos data/sample_listings/36_kelly_moncton/photos \
  --onnx-model $OUT/onnx/model.onnx 2>&1 ; echo "exit=$?"
```
**Expected:**
```
--onnx-model/AIREAL_ONNX_MODEL was supplied but --onnx-labels (or AIREAL_ONNX_LABELS) was not. A bring-your-own ONNX model needs BOTH the model file and its labels.json -- the labels file is the model's capability declaration, not optional metadata. Pass --onnx-labels (or set AIREAL_ONNX_LABELS), or omit both to use the default local/vision provider.
exit=1
```

### 7b — Partial pair: only `--onnx-labels` given
```bash
ingest-listing --file data/sample_listings/36_kelly_moncton/listing.txt \
  --photos data/sample_listings/36_kelly_moncton/photos \
  --onnx-labels $OUT/onnx/labels.json 2>&1 ; echo "exit=$?"
```
**Expected:** the mirror-image message naming `--onnx-model`/`AIREAL_ONNX_MODEL` as the missing
half, `exit=1`.

### 7c — Nonexistent `--onnx-model` path
```bash
ingest-listing --file data/sample_listings/36_kelly_moncton/listing.txt \
  --photos data/sample_listings/36_kelly_moncton/photos \
  --onnx-model $OUT/does_not_exist.onnx \
  --onnx-labels $OUT/onnx/labels.json 2>&1 ; echo "exit=$?"
```
**Expected:**
```
--onnx-model /tmp/m3/does_not_exist.onnx: not a regular file (missing, a directory, or a special file). Check the path.
exit=1
```

### 7d — A directory passed as the path (either flag)
```bash
ingest-listing --file data/sample_listings/36_kelly_moncton/listing.txt \
  --photos data/sample_listings/36_kelly_moncton/photos \
  --onnx-model $OUT/onnx \
  --onnx-labels $OUT/onnx/labels.json 2>&1 ; echo "exit=$?"
```
**Expected:**
```
--onnx-model /tmp/m3/onnx: not a regular file (missing, a directory, or a special file). Check the path.
exit=1
```
(the same check applies symmetrically to `--onnx-labels` — a directory there is rejected before
either file is opened, closing off both a directory-read surprise and, per the mission's security
review, an indefinite hang if a FIFO were passed instead of a directory.)

### 7e — `--onnx-labels` is not valid JSON
```bash
echo '{not valid json' > $OUT/bad_syntax.json
ingest-listing --file data/sample_listings/36_kelly_moncton/listing.txt \
  --photos data/sample_listings/36_kelly_moncton/photos \
  --onnx-model $OUT/onnx/model.onnx \
  --onnx-labels $OUT/bad_syntax.json 2>&1 ; echo "exit=$?"
```
**Expected:**
```
--onnx-labels /tmp/m3/bad_syntax.json: not valid JSON (Expecting property name enclosed in double quotes: line 1 column 2 (char 1)).
exit=1
```

### 7f — `--onnx-labels`'s root is valid JSON but not an object (a bare list)
```bash
echo '["mold_suspected", "ev_charger"]' > $OUT/bad_root.json
ingest-listing --file data/sample_listings/36_kelly_moncton/listing.txt \
  --photos data/sample_listings/36_kelly_moncton/photos \
  --onnx-model $OUT/onnx/model.onnx \
  --onnx-labels $OUT/bad_root.json 2>&1 ; echo "exit=$?"
```
**Expected:**
```
--onnx-labels /tmp/m3/bad_root.json: labels.json must contain a non-empty 'labels' list
exit=1
```
**Note for the record, not a defect:** an earlier draft of this mission's own design spec expected
a different message here (something naming the file as needing to "contain a JSON object with a
'labels' list"), reasoning from a raw `AttributeError` the code used to be able to raise for this
exact input. The mission's security review (Gate D, finding GD-2) changed the fix to a one-line
core guard instead, which routes a non-object root through the *same* "non-empty labels list"
message an empty `{"labels": []}` produces — verified above to be the message actually shipped.
Either message would have been "clean, no traceback"; this is simply which one is real.

### 7g — A corrupt `.onnx` file (not a valid protobuf at all)
```bash
printf 'not a real onnx file, just plain garbage bytes\x00\x01\x02' > $OUT/corrupt.onnx
ingest-listing --file data/sample_listings/36_kelly_moncton/listing.txt \
  --photos data/sample_listings/36_kelly_moncton/photos \
  --onnx-model $OUT/corrupt.onnx \
  --onnx-labels $OUT/onnx/labels.json 2>&1 ; echo "exit=$?"
```
**Expected:**
```
--onnx-model /tmp/m3/corrupt.onnx: failed to load ONNX model ([ONNXRuntimeError] : 7 : INVALID_PROTOBUF : Load model from /tmp/m3/corrupt.onnx failed:Protobuf parsing failed.).
exit=1
```
(the exact `onnxruntime` error text inside the parentheses is the real underlying exception message
— it will read exactly like this on the locked `onnxruntime==1.23.2`.)

### 7h — A model whose declared input type is not `tensor(float)`
This one needs a second small ONNX file — a model that declares a `tensor(double)` input (still a
structurally valid, loadable graph, so the *declared type* is what gets rejected, not a load
failure):
```bash
python - <<'PY'
import numpy as np, onnx
from onnx import TensorProto, helper
LABELS = ["mold_suspected", "water_leak_suspected", "ev_charger",
          "parking_garage", "parking_driveway", "dishwasher"]
K = len(LABELS)
input_tensor = helper.make_tensor_value_info("pixels", TensorProto.DOUBLE, [1, 3, "H", "W"])
output_tensor = helper.make_tensor_value_info("scores", TensorProto.FLOAT, [1, K])
nodes = [helper.make_node("Cast", ["pixels"], ["pixels_f32"], to=TensorProto.FLOAT)]
nodes.append(helper.make_node("GlobalAveragePool", ["pixels_f32"], ["pooled"]))
reshape_shape = helper.make_tensor("reshape_shape", TensorProto.INT64, [2], [1, 3])
nodes.append(helper.make_node("Reshape", ["pooled", "reshape_shape"], ["flat"]))
rng = np.random.default_rng(1337)
weight = (rng.standard_normal((3, K)) * 0.01).astype(np.float32)
bias = np.full((K,), -8.0, dtype=np.float32)
w_init = helper.make_tensor("W", TensorProto.FLOAT, [3, K], weight.flatten().tolist())
b_init = helper.make_tensor("B", TensorProto.FLOAT, [K], bias.tolist())
nodes.append(helper.make_node("Gemm", ["flat", "W", "B"], ["logits"]))
nodes.append(helper.make_node("Sigmoid", ["logits"], ["scores"]))
graph = helper.make_graph(nodes, "non_float_fixture", [input_tensor], [output_tensor],
                           initializer=[w_init, b_init, reshape_shape])
model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
model.ir_version = 8
onnx.checker.check_model(model)
with open("/tmp/m3/onnx/non_float_model.onnx", "wb") as f:
    f.write(model.SerializeToString())
print("wrote non_float_model.onnx")
PY
ingest-listing --file data/sample_listings/36_kelly_moncton/listing.txt \
  --photos data/sample_listings/36_kelly_moncton/photos \
  --onnx-model $OUT/onnx/non_float_model.onnx \
  --onnx-labels $OUT/onnx/labels.json 2>&1 ; echo "exit=$?"
```
**Expected:**
```
--onnx-model /tmp/m3/onnx/non_float_model.onnx: ONNX model input type tensor(double) not supported; expected tensor(float)
exit=1
```
**Why this one exists, plainly:** early in the mission, a non-float-declaring model didn't fail
loudly here — it loaded, then silently produced **zero** detections on every real photo (a type
promotion bug swallowed by a pre-existing broad exception handler). This check converts what used
to be a silent, empty-handed run into a loud, attributable configuration error at registration
time, before any photo is touched.

**Pass/fail criterion (all eight sub-cases):** Does every one exit non-zero with a specific,
readable message naming the actual problem — and does none of them dump a raw Python traceback?
Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-08-29
**Actual result observed:** All eight sub-cases failed cleanly with `exit=1` and a single explanatory line, **no raw traceback anywhere**: 7a/7b half-a-pair (each naming the missing half and both the flag and env-var form), 7c nonexistent path and 7d a directory (both “not a regular file (missing, a directory, or a special file)”), 7e invalid JSON (with the parser's position), 7f a bare-list root (“must contain a non-empty 'labels' list”), 7g a corrupt `.onnx` (ORT `INVALID_PROTOBUF` surfaced inside a framed message), 7h a `tensor(double)` input (“not supported; expected tensor(float)”).

---

## Case 8 — Determinism: the same input, run twice, produces byte-identical output

**Goal, scoped honestly.** This proves the same model + same photos + a cleared cache produces
byte-identical output twice in a row, for the specific synthetic fixture this doc has you build. It
does **not** prove — and this doc does not claim — that *any* ONNX model you might supply is
guaranteed deterministic. The wiring pins `onnxruntime`'s session to single-threaded, sequential
execution (`intra_op_num_threads=1`, `inter_op_num_threads=1`, `ORT_SEQUENTIAL`) specifically to
close off one real, general source of nondeterminism — floating-point reduction order varying
across threads — but that pin cannot make an arbitrary user-supplied graph deterministic if the
graph itself contains a genuinely nondeterministic op, and it makes no promise at all about a model
that crashes, hangs, or exhausts memory (that class of failure is explicitly out of scope for any
"no raw traceback" guarantee — see the sprint tracker's Gate D security review, accepted risk AR-1).
What's provable, and is proven below: for a well-behaved model like this doc's fixture, two runs
agree byte for byte.

**Command**
```bash
rm -rf .cache/cv
ingest-listing --file data/sample_listings/36_kelly_moncton/listing.txt \
  --photos data/sample_listings/36_kelly_moncton/photos \
  --onnx-model $OUT/onnx/model.onnx \
  --onnx-labels $OUT/onnx/labels.json --pretty 1 > $OUT/det_a.txt 2>$OUT/det_a.err
rm -rf .cache/cv
ingest-listing --file data/sample_listings/36_kelly_moncton/listing.txt \
  --photos data/sample_listings/36_kelly_moncton/photos \
  --onnx-model $OUT/onnx/model.onnx \
  --onnx-labels $OUT/onnx/labels.json --pretty 1 > $OUT/det_b.txt 2>$OUT/det_b.err
diff $OUT/det_a.txt $OUT/det_b.txt && echo "STDOUT IDENTICAL"
diff $OUT/det_a.err $OUT/det_b.err && echo "STDERR IDENTICAL"
```

**Expected result:** `STDOUT IDENTICAL` and `STDERR IDENTICAL` — the cache is cleared between runs
specifically so this proves the *model's own determinism*, not merely that a warm cache served the
same cached answer twice (that would prove nothing about the model).

**Pass/fail criterion:** Are both diffs clean (no output) and both `IDENTICAL` lines printed?
Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-08-29
**Actual result observed:** Run once warm, then again after `rm -rf .cache/cv`: `diff` reported **STDOUT IDENTICAL** and **STDERR IDENTICAL**. Cache state changes nothing about the output.

---

## Case 9 — Whole-suite sanity: tests, formatting, linting, typing

```bash
python -m pytest -q
ruff format --check .
ruff check .
mypy .
```

**Expected result — the real numbers observed on this tree, 2026-08-20:**
- `pytest`: **684 tests, 0 failed, 0 errors, 0 skipped** (exit 0), coverage **87.20%** against the
  80% gate ("Required test coverage of 80% reached. Total coverage: 87.20%"). If your number differs
  slightly, that is expected only if the tree has moved since this doc was written (check
  `git log` for new commits) — a *lower* pass count or any failure is not expected and should be
  reported.
- `ruff format --check .`: **216 files already formatted**, exit 0.
- `ruff check .`: **All checks passed!**, exit 0.
- `mypy .`: **Success: no issues found in 214 source files**, exit 0.

> **A note on how these were measured, for transparency.** In this sandboxed shell, `pytest -q`'s
> final one-line summary (the usual `"N passed in X.XXs"`) did not print to the terminal even
> though the run completed cleanly — a display quirk of this particular non-interactive shell, not
> a test failure. The **684 / 0 failed / 0 skipped** figures above were confirmed two independent
> ways: `--junitxml` output (machine-readable, unambiguous) and `--collect-only -q`'s per-file
> counts summing to the same 684. If your terminal shows the normal summary line, trust it — it
> should read `684 passed in ~14-28s`.

**Pass/fail criterion:** Do all four commands exit 0 with no failures/errors and no regressions
below the 80% coverage gate? Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-08-29
**Actual result observed:** `python -m pytest -q` → **684 passed**, 0 failed, coverage **87.20%** (80% gate met; the only warnings are pre-existing coverage `module-not-imported` / `couldnt-parse` notices). `ruff format --check .` → 216 files already formatted. `ruff check .` → All checks passed. `mypy .` → Success: no issues found in 214 source files.

---
---

## Deferred / out of scope — read before filing anything below as a defect

This mission ships **exactly one** of three ways the "no real AI provider" backlog item
(`docs/plans/ROADMAP_TRACKER.md` backlog #3) could eventually be closed:

| Offering | What it is | This mission? |
| --- | --- | --- |
| **1 — Bring-your-own ONNX model** | You supply a trained `.onnx` classifier; the project registers and runs it, unmodified, and does not vouch for its output. | **✅ Shipped, this doc.** |
| **2 — Hosted API key** (e.g. a paid vision API) | The project calls out to a third-party hosted model on your behalf. | **Not built.** No flag, no env var, no code path. Do not expect one. |
| **3 — Project-shipped, project-trained model** | A model the project itself trains/ships and stands behind (a real accuracy claim would become possible here — it isn't, for offering 1). | **Not built.** No flag, no env var, no code path. Do not expect one. |

**`main.py`'s pipeline does not read `--onnx-model`/`--onnx-labels`/`AIREAL_ONNX_MODEL`/
`AIREAL_ONNX_LABELS` at all — not "reads them but ignores them," but structurally does not touch
them.** `main.py` reaches photo tagging through `src/agents/listing_analyst.py` →
`CvTaggingOrchestrator.analyze_paths`, which hardcodes its own provider choice
(`"vision" if AIREAL_USE_VISION else "local"`) and never calls the function this mission's
selection logic lives in (`build_photo_insights`). This is why Case 6 above sets the ONNX env vars
and still gets the byte-identical baseline report — it isn't a coincidence or an oversight, it's a
structural fact about which code path `main.py` uses. If you want the ONNX path, use
`ingest-listing` (directly, or via one of the CrewAI-backed callers that do call
`build_photo_insights`) — not `python main.py`.

**Do not read any of the above as "less finished" or "a smaller version of" offerings 2/3.**
Offering 1 is a complete, honestly-scoped feature on its own terms: you bring a real model, it
really runs, and the project is honest that it never evaluated that model's accuracy. That is the
whole offering — not a placeholder for a future one.

---

_End of Mission 3 manual testing handoff._
