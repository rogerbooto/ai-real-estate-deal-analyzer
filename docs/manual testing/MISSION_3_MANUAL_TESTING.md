# Mission 3 — Bring-Your-Own ONNX Model — Manual Testing / Acceptance Handoff

_Author: mission-planner · Written 2026-08-19 against `main @ a00a265` (charter baseline)._

> ## ⚠ Read this first — this is an ACCEPTANCE plan for work NOT YET BUILT
>
> Mission 3 is **chartered, not yet built.** Every test case below currently **FAILS / demonstrates
> the gap** — that is the point. It describes what the shipped mission must make true, and doubles as
> the acceptance checklist you (Roger) tick off at the mission gate. When the mission is built, the
> orchestrator will have re-run every command here and confirmed each produces its stated result;
> your job at the gate is to reproduce them by hand and flip the boxes.
>
> **The gap, stated plainly:** there is a fully-built way to register your own ONNX photo model
> (`register_onnx_provider`), but **no CLI flag or environment variable reaches it**, and even if it
> were registered, the photo-insight builder only ever picks the built-in `local`/`vision` providers —
> never `onnx`. So today, cases W1–W3 and W7 cannot pass at all.

> **Verify the tree before trusting anything below:** you should be on branch
> `mission/3-byo-onnx-provider` with the mission merged, or on `main` after Wave Integrate.
> `git log --oneline | grep -i "Mission 3"` should return the merge commit. If it does not, the work
> is not built yet and every case here is expected to fail.

---

**Overall validation:** ☐ NOT VALIDATED ☐ VALIDATED (Roger, ______) ☐ VALIDATED WITH ISSUES
**Blocking issues found:** ______________________________________________

---

## Prerequisites (do this once)

1. `cd /home/rtokime/projects/Personal/ai-real-estate-deal-analyzer`
2. `source /home/rtokime/anaconda3/etc/profile.d/conda.sh && conda activate airedeal`
3. `which python` → must be `/home/rtokime/anaconda3/envs/airedeal/bin/python`
4. `git status --porcelain` → clean.
5. `mkdir -p /tmp/m3 && export OUT=/tmp/m3`

**The synthetic test model.** These tests need a tiny ONNX classifier and a matching labels file. The
mission ships a committed fixture — expected at **`data/examples/onnx/tiny_amenities.onnx`** and
**`data/examples/onnx/tiny_amenities_labels.json`** (final paths confirmed in the sprint tracker). The
labels file declares the six unlockable labels:

```json
{"labels": ["mold_suspected", "water_leak_suspected", "ev_charger",
            "parking_garage", "parking_driveway", "dishwasher"]}
```

If the committed fixture is not present, build one yourself (needs `onnx` + `numpy`; running it later
needs `onnxruntime`):

```
python - <<'PY'
import numpy as np, onnx
from onnx import helper, TensorProto
K, C = 6, 3
labels = ["mold_suspected","water_leak_suspected","ev_charger",
          "parking_garage","parking_driveway","dishwasher"]
X = helper.make_tensor_value_info("input", TensorProto.FLOAT, [1, C, 224, 224])
Y = helper.make_tensor_value_info("logits", TensorProto.FLOAT, [1, K])
W = helper.make_tensor("W", TensorProto.FLOAT, [K, C], np.zeros((K, C), np.float32).flatten())
B = helper.make_tensor("B", TensorProto.FLOAT, [K], np.full((K,), 5.0, np.float32))  # ~1.0 after sigmoid
n1 = helper.make_node("GlobalAveragePool", ["input"], ["pooled"])
n2 = helper.make_node("Flatten", ["pooled"], ["flat"], axis=1)
n3 = helper.make_node("Gemm", ["flat","W","B"], ["logits"], transB=1)
g = helper.make_graph([n1,n2,n3], "tiny_amenities", [X], [Y], initializer=[W,B])
m = helper.make_model(g, opset_imports=[helper.make_opsetid("", 13)])
onnx.checker.check_model(m)
import os; os.makedirs("data/examples/onnx", exist_ok=True)
onnx.save(m, "data/examples/onnx/tiny_amenities.onnx")
import json; json.dump({"labels": labels}, open("data/examples/onnx/tiny_amenities_labels.json","w"))
print("wrote tiny_amenities.onnx (always-positive on all six labels) + labels")
PY
```

This toy model reports **all six labels as present** on any image, which is deliberate: it makes the
"a real model was used" and "the six labels became confirmed" effects visible in a manual run. It is a
test fixture, not a real classifier.

6. A folder of real sample photos to run against: **`data/sample_listings/36_kelly_moncton/photos/`**
   (used by the default demo). Confirm it exists: `ls data/sample_listings/36_kelly_moncton/photos/`.

> **Note on the exact flag / env-var names.** The final names are a bounded founder-proxy product call
> (see the charter). This doc uses placeholder names **`--onnx-model` / `--onnx-labels`** and
> **`AIREAL_ONNX_MODEL` / `AIREAL_ONNX_LABELS`**. If the shipped names differ, the sprint tracker
> records the real ones — substitute them; the behaviour under test is unchanged.

The CLIs are: `ingest-listing` (ingest a listing / tag photos), `deal-report`, `deal-advisor`. All
resolve on `PATH` after `conda activate airedeal`.

---
---

## W1 — A real ONNX model can be registered and used from the CLI (happy path)

**Goal:** Passing the ONNX flags makes `ingest-listing` register the user's model and actually use it
to tag photos, instead of silently ignoring it.

**Current behaviour (before):** there is no such flag; `register_onnx_provider` has zero callers, and
`build_photo_insights` can only pick `local`/`vision`. Supplying a model is impossible.

**Steps to reproduce**
1. Build/confirm the fixture (Prerequisites).
2. Run the ingest CLI with the ONNX flags against the sample photos.

**Command(s)**
```
ingest-listing --file data/sample_listings/36_kelly_moncton/listing.txt \
  --photos data/sample_listings/36_kelly_moncton/photos \
  --onnx-model data/examples/onnx/tiny_amenities.onnx \
  --onnx-labels data/examples/onnx/tiny_amenities_labels.json 2>&1 | grep -E "photo insights:|provider="
```

**Expected result:** the run completes (exit 0) and the photo-insights summary line shows the ONNX
provider was used — e.g. `provider=` reflecting the onnx path and a non-zero detections count driven by
the model, **not** the `vision-stub`/`local` output. Reverting the wiring makes this impossible again
(the flags would be unknown, exit 2).

**Pass/fail criterion:** Does the ONNX model get registered and actually drive the photo tagging?
Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W2 — The report/provenance honestly says a real model was used (`provider_kind = model`)

**Goal:** When a real ONNX model produced the observations, the provenance reads `provider_kind =
model` — distinct from the `heuristic_stub` the built-in stand-ins produce — so a reader can tell a
real model's output from a placeholder's.

**Current behaviour (before):** every run stamps `provider_kind = heuristic_stub`, because only stubs
can ever be selected.

**Command(s)**
```
ingest-listing --file data/sample_listings/36_kelly_moncton/listing.txt \
  --photos data/sample_listings/36_kelly_moncton/photos \
  --onnx-model data/examples/onnx/tiny_amenities.onnx \
  --onnx-labels data/examples/onnx/tiny_amenities_labels.json --pretty 1 2>&1 | grep -i "provider_kind"
```

**Expected result:** the printed provenance contains `provider_kind: model` (or `"provider_kind":
"model"` in the JSON). Run the same command **without** the ONNX flags and confirm it reads
`heuristic_stub` — the difference is the honesty signal.

**Pass/fail criterion:** Does the ONNX run report `provider_kind = model`, and the non-ONNX run
`heuristic_stub`? Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W3 — The six filename-only labels become confirmed observations (no ontology change)

**Goal:** A photo whose file name suggests one of the six labels (e.g. `parking_garage`) — which today
is only ever an unscored hint — becomes a **confirmed** observation once a model that declares that
label is registered, via the existing 70% detector / 30% filename rule. No new label is added to the
program's vocabulary.

**Current behaviour (before):** all six (`mold_suspected`, `water_leak_suspected`, `ev_charger`,
`parking_garage`, `parking_driveway`, `dishwasher`) stay unconfirmed hints — nothing can look for them,
so a filename claim never gets corroborated and never counts.

**Steps to reproduce**
1. Create a photo whose name is one of the six labels:
   `cp data/sample_listings/36_kelly_moncton/photos/*.jpg $OUT/parking_garage.jpg 2>/dev/null || \
    python -c "from PIL import Image; Image.new('RGB',(400,300),(180,180,180)).save('$OUT/parking_garage.jpg')"`
2. Run ingest with the ONNX model registered, pointed at a folder containing that photo.

**Command(s)**
```
mkdir -p $OUT/photos && cp $OUT/parking_garage.jpg $OUT/photos/
ingest-listing --file data/sample_listings/36_kelly_moncton/listing.txt \
  --photos $OUT/photos \
  --onnx-model data/examples/onnx/tiny_amenities.onnx \
  --onnx-labels data/examples/onnx/tiny_amenities_labels.json --pretty 1 2>&1 | grep -iE "parking_garage|confirmed|amenit"
```

**Expected result:** with the model registered (and, in this fixture, reporting the label present),
`parking_garage` appears as a **confirmed** observation (a real amenity, corroborated), not a bare
"contested/unconfirmed hint." Run the same without the ONNX flags: `parking_garage` stays an unscored
hint that does not become a confirmed amenity. The program's label set is unchanged either way.

**Pass/fail criterion:** Does a declared+detected label graduate from hint to confirmed observation
only when the model is registered, with no vocabulary change? Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W4 — Environment variables register the model (parity with the flags)

**Goal:** The `AIREAL_*` environment variables register the model exactly as the flags do, matching the
existing env convention (`AIREAL_USE_VISION`, etc.).

**Current behaviour (before):** no such env vars exist.

**Command(s)**
```
AIREAL_ONNX_MODEL=data/examples/onnx/tiny_amenities.onnx \
AIREAL_ONNX_LABELS=data/examples/onnx/tiny_amenities_labels.json \
ingest-listing --file data/sample_listings/36_kelly_moncton/listing.txt \
  --photos data/sample_listings/36_kelly_moncton/photos --pretty 1 2>&1 | grep -i "provider_kind"
```

**Expected result:** `provider_kind: model` — the env vars register the model with no flags passed. If
both env vars and flags are set, the documented precedence (recorded in the tracker) applies
consistently.

**Pass/fail criterion:** Do the env vars register the model like the flags? Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W5 — Missing `onnxruntime` fails with a clean message, not a traceback

**Goal:** If `onnxruntime` is not installed, registering an ONNX model gives a clear, actionable
message instead of a raw import traceback.

**Current behaviour (before):** unreachable — the code raises `RuntimeError("onnxruntime not
available; install it to use provider=onnx")` at registration, but nothing calls it.

**Steps to reproduce** (only meaningful if `onnxruntime` is NOT installed in the env; check with
`python -c "import onnxruntime" 2>&1 | tail -1`):
```
ingest-listing --file data/sample_listings/36_kelly_moncton/listing.txt \
  --photos data/sample_listings/36_kelly_moncton/photos \
  --onnx-model data/examples/onnx/tiny_amenities.onnx \
  --onnx-labels data/examples/onnx/tiny_amenities_labels.json 2>&1 | tail -3 ; echo "exit=$?"
```

**Expected result:** a clean one-line message telling the user `onnxruntime` is required and how to
install it (surfacing the existing `RuntimeError` text), exit non-zero — **no** Python traceback dumped
at the user. (If `onnxruntime` IS installed, this case is not reproducible in this env; mark BLOCKED and
rely on the automated test, which forces the missing-dependency condition.)

**Pass/fail criterion:** Clean actionable message, no raw traceback? Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W6 — A bad model file or bad labels file fails cleanly

**Goal:** Pointing the flags at a nonexistent/garbage model, or at a malformed/empty labels file,
produces a clean message — not a raw traceback.

**Current behaviour (before):** unreachable; internally a bad labels file raises `ValueError("labels.json
must contain a non-empty 'labels' list")` and a bad model raises inside `onnxruntime.InferenceSession`.

**Command(s)**
```
# bad model path
ingest-listing --file data/sample_listings/36_kelly_moncton/listing.txt \
  --photos data/sample_listings/36_kelly_moncton/photos \
  --onnx-model /tmp/does_not_exist.onnx \
  --onnx-labels data/examples/onnx/tiny_amenities_labels.json 2>&1 | tail -3 ; echo "exit=$?"
# empty/malformed labels
echo '{"labels": []}' > $OUT/bad_labels.json
ingest-listing --file data/sample_listings/36_kelly_moncton/listing.txt \
  --photos data/sample_listings/36_kelly_moncton/photos \
  --onnx-model data/examples/onnx/tiny_amenities.onnx \
  --onnx-labels $OUT/bad_labels.json 2>&1 | tail -3 ; echo "exit=$?"
```

**Expected result:** each run exits non-zero with a clean message naming the problem (missing model
file / labels file must contain a non-empty `labels` list) — no raw traceback.

**Pass/fail criterion:** Both bad-input runs fail cleanly with actionable messages? Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W7 — Determinism: same input ⇒ byte-identical output; default path unchanged

**Goal:** Two runs with the same model and same photos produce byte-identical photo-insight output; and
a run with **no** ONNX flags is byte-identical to the pre-mission default (the mission must not change
existing behaviour when the feature is unused).

**Current behaviour (before):** n/a (feature does not exist).

**Command(s)**
```
# determinism of the ONNX path
ingest-listing --file data/sample_listings/36_kelly_moncton/listing.txt \
  --photos data/sample_listings/36_kelly_moncton/photos \
  --onnx-model data/examples/onnx/tiny_amenities.onnx \
  --onnx-labels data/examples/onnx/tiny_amenities_labels.json --pretty 1 > $OUT/onnx_a.txt 2>&1
ingest-listing --file data/sample_listings/36_kelly_moncton/listing.txt \
  --photos data/sample_listings/36_kelly_moncton/photos \
  --onnx-model data/examples/onnx/tiny_amenities.onnx \
  --onnx-labels data/examples/onnx/tiny_amenities_labels.json --pretty 1 > $OUT/onnx_b.txt 2>&1
diff $OUT/onnx_a.txt $OUT/onnx_b.txt && echo "IDENTICAL"
# default path unchanged: main.py demo report byte-identical to pre-mission
python main.py --out $OUT/rep.md && echo "demo report generated"
```

**Expected result:** the two ONNX runs are `IDENTICAL`; `python main.py` still produces the demo report
exactly as before the mission (no ONNX registered ⇒ no behaviour change). The whole-suite check below
should also be green.

**Pass/fail criterion:** ONNX runs identical AND the default path unchanged? Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W8 — Docs tell the truth (honest framing, no overclaim)

**Goal:** The README / `src/core/README.md` describe the new user path and clearly state that the model
is **the user's own**, and that the project does not vouch for its accuracy — no "AI-powered" overclaim.

**Command(s)**
```
grep -n -iE "onnx|bring your own|your own model|does not vouch|user-supplied" README.md src/core/README.md
grep -n -i "onnx" CHANGELOG.md
```

**Expected result:** prose documenting the flags/env vars and the honest caveat; a CHANGELOG
`[Unreleased]` entry for the new path. No claim that the program itself is now an accurate AI photo
analyzer.

**Pass/fail criterion:** Do the docs describe the path honestly, with the "your own model" caveat?
Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---
---

## Whole-suite sanity (optional, ~minutes)

```
python -m pytest -q
```
**Expected:** all tests pass, coverage ≥ 80% (the mission adds the ONNX-path + error-path + determinism
tests and must not drop coverage below the gate). Pin the exact count + SHA in the sprint tracker.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______

---

_End of Mission 3 manual testing / acceptance handoff._
