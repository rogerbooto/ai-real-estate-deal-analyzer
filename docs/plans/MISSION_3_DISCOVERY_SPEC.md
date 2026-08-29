# Mission 3 — Wave Discovery Implementation Spec

_Author: `staff-python-engineer` (Wave Discovery). No production code in this document — every
diff below is a **proposed** change for the Implementation wave to apply verbatim or challenge
explicitly. All `path:line` anchors were re-read against the tree at the time this spec was
written: branch `mission/3-byo-onnx-provider`, `HEAD = 6d9c000` (the charter's baseline commit;
`git status --porcelain` shows only `docs/plans/MISSION_3_SPRINT_TRACKER.md` modified, no source
drift since the charter was cut)._

---

## 0. Read this first — findings that change the charter's picture

Four things surfaced during re-verification that Gate D and the implementer must see before
writing code. None of them block the mission; all of them change how a claim in the charter or in
this spec should be read.

### 0.1 `onnxruntime` is **already** a hard, unconditional runtime dependency — not opt-in today

The charter's binding constraint #9 says "`onnxruntime` **stays** an opt-in dependency." That
phrasing implies it currently is opt-in. It is not:

```
requirements.txt:27:  onnxruntime>=1.16.0,<2.0.0
```

added by `66ffacd` ("build: lock dependencies and ceil crewai below the major that broke CI"),
**already on `main`**, with its own comment explaining why: `onnxruntime` was reaching the project
transitively through `crewai`'s dependency tree, so it was declared explicitly "to break that
accidental coupling" — but it was declared as a **plain, unconditional line** in `requirements.txt`,
not as a `[project.optional-dependencies]` extra the way `openai`/`render` are. Every documented
install path (`pip install -r requirements.txt`, `pip install -r requirements.lock`) installs it
unconditionally. `pyproject.toml` has no `[project] dependencies` key at all (runtime deps live
only in `requirements*.txt`/`.lock`, per `README.md:365`), so there is no packaging-level "extra"
today that would make it truly optional.

This directly contradicts `src/core/README.md:196`:

> "The package is intentionally not declared in `requirements.txt` because it is an opt-in
> dependency for advanced users only."

That line is **stale** as of `66ffacd` and should be corrected in the Implementation wave's docs
pass (see §8, files NOT touched by me but flagged for `staff-documentation-maintainer`).

**Consequence for this spec:** the "missing `onnxruntime`" error path (§4, row 1) is dead in
production for every user who followed the documented setup — it can only be exercised by
deliberately breaking the import (monkeypatch), exactly as Fact 9 said, but the *reason* is
stronger than "it happens to be installed in this dev env": the project's own lockfile guarantees
it. The code still treats it as optional at the API boundary (`try: import onnxruntime … except
Exception: raise RuntimeError(...)`), which is the right shape to keep — a future `pyproject.toml`
extras cleanup could make the packaging match the code's intent, but that is out of this mission's
scope and is flagged, not fixed, here.

**Recommendation:** do not silently reconcile this in the Implementation wave. Surface it to
`principal-founder-proxy` at Gate V as a one-line call: leave `requirements.txt` as-is (lowest
blast radius; `onnxruntime` clearly must be present for the new CLI flags to do anything useful
anyway) and only fix the stale doc line, OR move `onnxruntime` into an optional-dependencies extra
now that there's a real caller. I recommend the former (doc fix only) — moving it to an extra
mid-mission would make the *documented* setup path (`pip install -r requirements.txt && python
main.py`) stop providing ONNX support by default, which is a behavior change this mission's DoD
does not ask for and Roger has not requested.

### 0.2 `AIREAL_DEBUG` precedent lives at a different path than the charter states

Fact/precedent list says `crewai_components.py:118`. The actual file is
**`src/agents/crewai_components.py:118`** (not `src/orchestrators/crewai_components.py` — that
module doesn't exist). Confirmed:

```
src/agents/crewai_components.py:118:    return os.getenv("AIREAL_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}
```

Doesn't change the precedent's validity (bare `os.getenv` at point of use is still the right
pattern to follow), just the citation. Use `src/agents/crewai_components.py:118` and
`src/orchestrators/cv_tagging_orchestrator.py:19` (`_VISION_ENABLED = os.getenv("AIREAL_USE_VISION", ...)`,
confirmed correct) as the two precedents in any commit message or doc update.

### 0.3 A latent bug in `_OnnxModel.__init__` produces a raw `AttributeError`, not a clean message, for one shape of malformed `labels.json`

`_OnnxModel.__init__` (`src/core/cv/amenities_defects.py:279-284`):

```python
with open(labels_path, encoding="utf-8") as f:
    meta = json.load(f)
labels = meta.get("labels")
if not isinstance(labels, list) or not labels:
    raise ValueError("labels.json must contain a non-empty 'labels' list")
```

This assumes `meta` is a `dict`. Verified empirically against this exact code path
(`register_onnx_provider("nonexistent.onnx", <path>)`, so the failure is isolated to the labels
step):

| `labels.json` contents | Result |
| --- | --- |
| `{}` (dict, no `"labels"` key) | clean `ValueError("labels.json must contain a non-empty 'labels' list")` — as documented |
| `["mold_suspected"]` (bare list at JSON root) | **unhandled `AttributeError: 'list' object has no attribute 'get'`** |
| `"oops"` (bare string at JSON root) | **unhandled `AttributeError: 'str' object has no attribute 'get'`** |

A `labels.json` that is valid JSON but not object-rooted is a plausible user mistake (e.g. they
pasted just the array). Today it produces a raw traceback out of `_OnnxModel.__init__`, which
`register_onnx_provider` does not catch (fact 2 confirmed: no try/except anywhere in
`register_onnx_provider` → `make_onnx_provider` → `_OnnxModel.__init__`). This is **pre-existing**,
not introduced by this mission, but this mission is what makes `register_onnx_provider` reachable
from a shipped CLI for the first time, so it's the first time a real user can hit it.

**Two ways to close it — flagging, not deciding:**

- **(A) CLI-side containment (recommended, in §4):** add `except AttributeError` to the
  `ingest_cli.py` catch chain, mapped to the same "malformed `labels.json`" message as the
  `ValueError` case. Zero core diff; matches "seams over surgery" — the mission's contract is CLI
  wiring, not a `core/cv` bugfix.
- **(B) Core fix (better long-term, out of this mission's stated scope):** one line,
  `labels = meta.get("labels") if isinstance(meta, dict) else None`, in `_OnnxModel.__init__`. Closes
  the gap for every caller of `register_onnx_provider`/`_OnnxModel`, not just the CLI. Low risk,
  but it is a `core/cv` behavior change to code the charter describes as "fully-built, tested" and
  out of scope to modify.

I specify (A) in §4 as the shipped behavior for this mission, and note (B) as a candidate
fast-follow for Gate D/`staff-code-reviewer` to decide whether to bundle. Do not silently do (B)
without a reviewer call — it's a real (if small) core/cv diff outside the charter's stated blast
radius.

### 0.4 No test in this repo has ever run a real `onnxruntime.InferenceSession`

Confirmed by grep: every existing ONNX-adjacent test (`tests/core/cv/test_filename_corroboration.py`,
`tests/ai/test_ai_onnx_registration.py`, `tests/ai/test_vision_stub_provenance_honesty.py`) either
monkeypatches `_OnnxModel` itself or pokes a fake function directly into `_PROVIDERS`. Mission 3's
end-to-end CLI proof (§6) will be the **first** test in this codebase to load and run a genuine
`.onnx` file through `onnxruntime`. That is exactly the coverage the mission needs, but it also
means the determinism properties of a real session (§7) have never been exercised or pinned before
— there is no prior art to lean on inside this repo.

---

## 1. Exact anchors (re-verified against `6d9c000`)

All confirmed by direct read; no other drift found beyond §0.2.

| Symbol | File:line | Current content (quoted) |
| --- | --- | --- |
| `ProviderName` | `src/core/cv/amenities_defects.py:27` | `ProviderName = Literal["local", "vision", "llm", "onnx"]` |
| `_PROVIDERS` default | `src/core/cv/amenities_defects.py:613-617` | `_PROVIDERS: dict[ProviderName, ProviderFn] = {"local": _provider_local, "vision": _provider_vision_stub, "llm": _provider_llm_stub}` — no `"onnx"` key |
| `_OnnxModel.__init__` | `src/core/cv/amenities_defects.py:258-311` | see §0.3, §4 |
| — onnxruntime import guard | `amenities_defects.py:270-271` | `except Exception as e:  # pragma: no cover` / `raise RuntimeError("onnxruntime not available; install it to use provider=onnx") from e` |
| — labels validation | `amenities_defects.py:279-284` | see §0.3 |
| — `InferenceSession` call | `amenities_defects.py:288` | `self.sess = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])` |
| — no-inputs guard | `amenities_defects.py:292-293` | `if not inputs: raise RuntimeError("ONNX model has no inputs")` |
| — no-outputs guard | `amenities_defects.py:309-310` | `if not outs: raise RuntimeError("ONNX model has no outputs")` |
| `make_onnx_provider` | `amenities_defects.py:346-361` | eager `mdl = _OnnxModel(model_path, labels_path, **kwargs)` at :351; `_declare_capabilities(_fn, mdl.labels)` at :360 |
| `register_onnx_provider` | `amenities_defects.py:382-398` | body: `_PROVIDERS["onnx"] = make_onnx_provider(model_path, labels_path, **kwargs)` at :398 |
| `provider_kind` | `amenities_defects.py:644-654` | `return "heuristic_stub" if fn in _BUILTIN_STUB_FNS else "model"` at :654 — identity check, no `onnx`-specific code needed |
| `provider_capabilities` | `amenities_defects.py:198-213` | raises `ValueError` for unregistered provider |
| `_covered_labels` / `_augment_from_filename` / `_FILENAME_RULES` | `src/core/cv/runner.py:223-236`, `:239-307`, `:213-219` | the corroboration mechanism; see §6 |
| `build_photo_insights` | `src/core/cv/photo_insights.py:314-457` | selection at :322-324, see §3 |
| — imports from `amenities_defects` | `photo_insights.py:12-18` | `ProviderName, is_contested_hint, is_unconfirmed_hint, is_uncorroborated_filename_claim, provider_kind` |
| — version constants | `photo_insights.py:39-50` | `VISION_STUB_VERSION = "vision-stub-v1"`, `DETERMINISTIC_VERSION = "deterministic"` |
| `ingest_cli._build_parser` | `src/cli/ingest_cli.py:42-112` | `--ai` at :49-65; `--render` immediately follows at :66 |
| `ingest_cli.main` | `src/cli/ingest_cli.py:115-208` | `args = p.parse_args(argv)` at :117; `policy = FetchPolicy(` starts :119; `ingest_listing(...)` call at :146 |
| `ingest_listing` | `src/core/ingest/listing_ingest.py:39-107` | calls `build_photo_insights(photos_path, use_ai=use_ai)` at :95 and `build_photo_insights(Path("__no_images__"), use_ai=use_ai)` at :97 — **no `provider` param exists or is added**; selection must happen inside `build_photo_insights` itself |
| `CvTaggingOrchestrator.analyze_paths` | `src/orchestrators/cv_tagging_orchestrator.py:33-54` | `_VISION_ENABLED` captured at import (`:19`); `provider: ProviderName = "vision" if _VISION_ENABLED else "local"` at `:54`, **hardcoded independently of `build_photo_insights`**; never calls `build_photo_insights` — confirmed by grep, no call site in this file |
| `crewai_runner.py` caller | `src/orchestrators/crewai_runner.py:142` | `media_report = build_media_report(build_photo_insights(Path(photos_folder)))` — no `use_ai` kwarg |
| `crew.py` caller | `src/orchestrators/crew.py:144` | identical call, same signature |
| `listing_analyst.py` CV path | `src/agents/listing_analyst.py:104` | `cv = CvTaggingOrchestrator(); cv_out = cv.analyze_folder(...)` — routes through the orchestrator above, **not** `build_photo_insights` |
| `AIREAL_USE_VISION` precedent | `src/orchestrators/cv_tagging_orchestrator.py:19` | `_VISION_ENABLED = os.getenv("AIREAL_USE_VISION", "0").lower() in ("1", "true", "yes", "on")` |
| `AIREAL_DEBUG` precedent | `src/agents/crewai_components.py:118` | **corrected from charter** — see §0.2 |
| `main.py` scenarios precedence comment | `main.py:224` | `# Precedence for scenarios: explicit CLI flag > env (applied in load) > JSON > default False.` |
| `SystemExit` clean-error precedent | `main.py:164-167`, `main.py:200-207`, `src/cli/report_cli.py:22-41`, `src/cli/advisor_cli.py:250-273` | every CLI-boundary "bad user input" failure in this codebase is `raise SystemExit(f"...")`, never a bare `return 1` or a caught-and-reprinted traceback |
| `InputsLoader` / `AppInputs.run.*` env vars | `src/inputs/inputs.py:33-37` | `AIREAL_OUT`, `AIREAL_HORIZON`, `AIREAL_LISTING`, `AIREAL_PHOTOS`, `AIREAL_SCENARIOS` — all routed through `InputsLoader`, which serves `main.py` only; `ingest_cli.py` never imports `src.inputs` |

Fact 7 (main.py cannot change) reconfirmed exactly as charter states, with the precise reason
being the orchestrator-level call graph: `main.py` → `deterministic_orchestrator`/`crewai_runner`
→ `listing_analyst.analyze_listing` → `CvTaggingOrchestrator.analyze_paths`, which computes its
own `provider` from `_VISION_ENABLED` (import-time env capture) at `cv_tagging_orchestrator.py:54`
and never calls `build_photo_insights`. Extending Mission 3's selection change to affect `main.py`
would require also changing `cv_tagging_orchestrator.py` — a second, separate seam with its own
hardcoded selection line and its own import-time env-capture pattern. That is real, additional
work with its own blast radius (`main.py`'s report output, `RunProvenance.vision_enabled`,
`crewai_components.py`'s LLM-mode gating) and is correctly out of scope per the founder-proxy lock.

---

## 2. Product decisions, restated for implementation (verbatim from the lock — not relitigated)

- Flags: `--onnx-model` (`str`, default `None`), `--onnx-labels` (`str`, default `None`).
- Env: `AIREAL_ONNX_MODEL`, `AIREAL_ONNX_LABELS`, read via bare `os.getenv()` in `ingest_cli.py`
  at point of use — **not** via `InputsLoader`.
- Precedence per field, independently: CLI flag (if passed) > env var (if set) > unset.
- Selection precedence in `build_photo_insights`: `onnx` (if registered) > `vision` (if `use_ai`)
  > `local`. Registering ONNX does **not** require `--ai`.
- Partial pair (`model` set, `labels` unset, or vice versa) is a hard config error: non-zero exit,
  clean message naming which flag/env supplies the missing half. No silent fallback.
- Neither set ⇒ byte-identical to pre-mission.
- Does not extend to `main.py`. Help text must say so.

---

## 3. `build_photo_insights` selection change

### 3.1 The registry needs a non-raising "is this bound?" predicate

`provider_kind`/`provider_capabilities` both `raise ValueError` for an unregistered provider —
correct for "tell me about a provider I already believe exists," wrong for "should I select this
provider at all," which is exactly what `build_photo_insights` needs to ask without a
try/except at every call site. Add one function, mirroring the identity-check style already used
by `provider_kind`:

**File:** `src/core/cv/amenities_defects.py`
**Insert immediately before `def provider_kind(...)` at line 644** (i.e., directly after the
`_BUILTIN_STUB_FNS` block that currently ends at line 641):

```python
def is_provider_registered(provider: ProviderName) -> bool:
    """True when ``provider`` is currently bound in the registry.

    The non-raising sibling of :func:`provider_kind`/:func:`provider_capabilities` (both raise
    ``ValueError`` for an unregistered provider -- correct when a caller already believes the
    provider exists and wants to know about it). A caller that needs to ASK whether a slot is
    bound at all -- e.g. :func:`~src.core.cv.photo_insights.build_photo_insights` deciding whether
    a registered ONNX provider should outrank ``vision``/``local`` -- needs a predicate that never
    raises, so selection logic can read it as an ordinary boolean.

    Queries in-process registry state only (the same ``_PROVIDERS`` dict every other function in
    this module reads/writes). No network call, no filesystem access, no CLI/env awareness --
    this keeps ``core/cv`` from depending on how a provider *got* registered, only on whether it
    is.
    """
    return provider in _PROVIDERS
```

This satisfies the layering rule ("core must not depend on CLI layering"): `build_photo_insights`
asks the *registry*, not the CLI's `argparse.Namespace` or environment. Whatever caller registered
`"onnx"` (the CLI today; conceivably a notebook or future caller tomorrow) is invisible to this
function.

### 3.2 New version constant

**File:** `src/core/cv/photo_insights.py`, immediately after `DETERMINISTIC_VERSION` (line 50):

```python
#: `PhotoInsights.version` for a registered `"onnx"` provider (a user-supplied bring-your-own
#: model; see `core.cv.amenities_defects.register_onnx_provider`). Deliberately NOT
#: `VISION_STUB_VERSION` -- that name says "stub", and a registered ONNX provider is a real model
#: (`provenance["provider_kind"] == "model"`, computed by `provider_kind`, unaffected by this
#: constant). Also deliberately NOT a per-model fingerprint (no hash of the `.onnx` file, no
#: path) -- `version` here names WHICH CODE PATH produced the artifact, the same coarse
#: producer-TYPE meaning `VISION_STUB_VERSION`/`DETERMINISTIC_VERSION` already carry. A
#: per-model identifier would be new information, not a repurposing of this field, and is out of
#: this mission's scope (no schema change; `provenance` already carries `selected_provider` and
#: is the right place for that if a future mission wants it).
ONNX_BYO_VERSION = "onnx-byo-v1"
```

Naming rationale for the guardian review: `"onnx-byo-v1"` says two true things and claims nothing
else — (1) the code path is the ONNX bring-your-own-model seam, (2) `v1` names *this wiring's*
version, not the model's accuracy or provenance. It does not say "AI", "real", or "verified".

### 3.3 Import addition

**File:** `src/core/cv/photo_insights.py:12-18`, current:

```python
from src.core.cv.amenities_defects import (
    ProviderName,
    is_contested_hint,
    is_unconfirmed_hint,
    is_uncorroborated_filename_claim,
    provider_kind,
)
```

Add `is_provider_registered` to this import block (alphabetical, matching existing style):

```python
from src.core.cv.amenities_defects import (
    ProviderName,
    is_contested_hint,
    is_provider_registered,
    is_unconfirmed_hint,
    is_uncorroborated_filename_claim,
    provider_kind,
)
```

### 3.4 Selection logic

**File:** `src/core/cv/photo_insights.py:320-324`, current:

```python
    # Provider selection and its provenance labels are computed once so the empty-folder
    # early return and the main path can never disagree about what produced the artifact.
    provider: ProviderName = "vision" if use_ai else "local"
    version = VISION_STUB_VERSION if use_ai else DETERMINISTIC_VERSION
    kind = provider_kind(provider)
```

Replace with:

```python
    # Provider selection and its provenance labels are computed once so the empty-folder
    # early return and the main path can never disagree about what produced the artifact.
    # Precedence: a registered "onnx" provider outranks "vision" (--ai), which outranks the
    # "local" default. Registration is a process-global side effect performed by a caller BEFORE
    # this function runs (today: ingest_cli.py's --onnx-model/--onnx-labels or
    # AIREAL_ONNX_MODEL/AIREAL_ONNX_LABELS, via register_onnx_provider); is_provider_registered
    # is how this module learns about it without importing CLI state -- see
    # amenities_defects.is_provider_registered. With nothing registered, is_provider_registered
    # is False and this reduces to the original two-way choice unchanged.
    provider: ProviderName
    if is_provider_registered("onnx"):
        provider = "onnx"
        version = ONNX_BYO_VERSION
    elif use_ai:
        provider = "vision"
        version = VISION_STUB_VERSION
    else:
        provider = "local"
        version = DETERMINISTIC_VERSION
    kind = provider_kind(provider)
```

**Why this preserves every property the charter requires:**

- **"Computed once" survives:** still one block, computed before the `if not paths:` early
  return (line 326 today), still feeding both the empty-folder branch (`PhotoInsights(...,
  version=version, ..., provenance={"selected_provider": provider, "provider_kind": kind, ...})`)
  and the main path lower in the function. No change to either `PhotoInsights(...)` call site
  needed — both already read `provider`/`version`/`kind` by name.
- **Default path byte-identical:** `_PROVIDERS` starts with no `"onnx"` key (§1); no caller in
  scope calls `register_onnx_provider` except the new CLI path. For every existing caller
  (`ingest_listing` without CLI ONNX flags, `run_listing_ingest_tool`, `crewai_runner.py:142`,
  `crew.py:144`), `is_provider_registered("onnx")` is `False`, so the `if` falls through to the
  *exact* `elif use_ai / else` structure the ternary expressed today. This is a structural
  guarantee, not a claim to be verified after the fact — the new code is a strict superset of a
  branch that reduces to the old ternary when the new condition is false.
- **Version stamp is honest:** `ONNX_BYO_VERSION` names the wiring, not a stub, and not an
  unearned "real AI" claim (§3.2 rationale, checked at Gate D/V by the guardian).

No other line in `build_photo_insights` needs to change. `tag_amenities_and_defects(...,
provider=provider, ...)` at line 388 already accepts `"onnx"` as a valid `ProviderName` — no
change needed there either.

---

## 4. `ingest_cli.py` wiring

### 4.1 New imports

**File:** `src/cli/ingest_cli.py`, current imports (lines 1-12):

```python
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from pprint import pprint
from typing import Final, cast

from src.core.ingest.listing_ingest import ingest_listing
from src.schemas.models import FetchPolicy, MediaKind
```

Add `json`, `os`, and `register_onnx_provider`:

```python
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from pprint import pprint
from typing import Final, cast

from src.core.cv.amenities_defects import register_onnx_provider
from src.core.ingest.listing_ingest import ingest_listing
from src.schemas.models import FetchPolicy, MediaKind
```

CLI → `core/cv` direct import is an established pattern in this file already (`ingest_listing` is
itself a `core` function); no layering violation.

### 4.2 New argparse flags

**File:** `src/cli/ingest_cli.py:65-66`, current (end of `--ai`'s `add_argument`, immediately
followed by `--render`):

```python
    p.add_argument("--render", type=int, default=0, help="Render JS via a headless browser before parsing (requires --url).")
```

Insert two new flags between `--ai` and `--render`:

```python
    p.add_argument(
        "--onnx-model",
        type=str,
        default=None,
        help=(
            "Path to a user-supplied ONNX classifier to register as the photo-insight detection "
            "provider (core.cv.amenities_defects.register_onnx_provider). Must be paired with "
            "--onnx-labels (or set AIREAL_ONNX_MODEL and AIREAL_ONNX_LABELS) -- supplying only "
            "one half is a configuration error and exits non-zero. Pointing at a model is itself "
            "the activation signal: this does NOT require --ai, and when both --onnx-model/"
            "--onnx-labels resolve, the onnx provider is selected ahead of vision/local. This is "
            "YOUR OWN model -- the project does not vouch for its accuracy. "
            "provenance.provider_kind is stamped 'model' to say a real classifier ran, not that "
            "its output is trustworthy. Applies to `ingest-listing` only: `python main.py`'s "
            "pipeline reaches photo tagging through a separate seam and does not read this flag."
        ),
    )
    p.add_argument(
        "--onnx-labels",
        type=str,
        default=None,
        help=(
            "Path to the labels.json declaring --onnx-model's label vocabulary -- this file IS "
            "the provider's capability declaration (see register_onnx_provider), not optional "
            "metadata. Must be paired with --onnx-model (or AIREAL_ONNX_MODEL/AIREAL_ONNX_LABELS). "
            "Same `python main.py` caveat as --onnx-model: this flag has no effect there."
        ),
    )
    p.add_argument("--render", type=int, default=0, help="Render JS via a headless browser before parsing (requires --url).")
```

### 4.3 Resolution, partial-pair check, and registration in `main()`

**File:** `src/cli/ingest_cli.py:115-119`, current:

```python
def main(argv: list[str] | None = None) -> int:
    p = _build_parser()
    args = p.parse_args(argv)

    policy = FetchPolicy(
```

Insert a new block between `args = p.parse_args(argv)` and `policy = FetchPolicy(` — **before**
any other startup work (no network, no cache-dir touch, no media note), so a misconfigured ONNX
pair fails as loudly and as early as possible (invariant #5):

```python
def main(argv: list[str] | None = None) -> int:
    p = _build_parser()
    args = p.parse_args(argv)

    # --onnx-model/--onnx-labels (or AIREAL_ONNX_MODEL/AIREAL_ONNX_LABELS): per-field precedence,
    # CLI flag > env > unset. Resolved and registered here, before any other startup work, so a
    # misconfigured pair fails loudly before a network fetch or cache directory is touched.
    onnx_model: str | None = args.onnx_model or os.getenv("AIREAL_ONNX_MODEL")
    onnx_labels: str | None = args.onnx_labels or os.getenv("AIREAL_ONNX_LABELS")

    if bool(onnx_model) != bool(onnx_labels):
        if onnx_model:
            present, missing_flag, missing_env = "--onnx-model/AIREAL_ONNX_MODEL", "--onnx-labels", "AIREAL_ONNX_LABELS"
        else:
            present, missing_flag, missing_env = "--onnx-labels/AIREAL_ONNX_LABELS", "--onnx-model", "AIREAL_ONNX_MODEL"
        raise SystemExit(
            f"{present} was supplied but {missing_flag} (or {missing_env}) was not. A "
            "bring-your-own ONNX model needs BOTH the model file and its labels.json -- the "
            "labels file is the model's capability declaration, not optional metadata. Pass "
            f"{missing_flag} (or set {missing_env}), or omit both to use the default local/"
            "vision provider."
        )

    if onnx_model and onnx_labels:
        try:
            register_onnx_provider(onnx_model, onnx_labels)
        except FileNotFoundError as e:
            raise SystemExit(f"--onnx-labels {onnx_labels}: file not found. Check the path passed to this flag.") from e
        except OSError as e:
            raise SystemExit(f"--onnx-labels {onnx_labels}: could not be read ({e}).") from e
        except json.JSONDecodeError as e:
            raise SystemExit(f"--onnx-labels {onnx_labels}: not valid JSON ({e}).") from e
        except AttributeError as e:
            # labels.json parsed as JSON but its root isn't an object (e.g. a bare list or
            # string) -- see docs/plans/MISSION_3_DISCOVERY_SPEC.md §0.3. _OnnxModel.__init__
            # calls meta.get("labels") assuming a dict; a non-dict root raises AttributeError
            # instead of the clean ValueError a dict-with-missing-key root gets. Contained here,
            # at the CLI boundary, rather than patched in core/cv (see §0.3 for the trade-off).
            raise SystemExit(f"--onnx-labels {onnx_labels}: must contain a JSON object with a 'labels' list, e.g. {{\"labels\": [...]}} ({e}).") from e
        except ValueError as e:
            raise SystemExit(f"--onnx-labels {onnx_labels}: {e}") from e
        except RuntimeError as e:
            # Covers both "onnxruntime not available" and "ONNX model has no inputs/outputs" --
            # the underlying message from _OnnxModel already says which; see §4.4.
            raise SystemExit(f"--onnx-model {onnx_model}: {e}") from e
        except Exception as e:
            # onnxruntime raises its own exception hierarchy for a missing/corrupt model file
            # (onnxruntime.capi.onnxruntime_pybind11_state.NoSuchFile/InvalidProtobuf/Fail/...),
            # none of which subclass RuntimeError/ValueError/OSError -- confirmed empirically
            # against onnxruntime 1.22.0, see §4.4. This is the only reliable way to guarantee no
            # raw traceback reaches the user for a bad --onnx-model path.
            raise SystemExit(f"--onnx-model {onnx_model}: failed to load ONNX model ({e}).") from e

    policy = FetchPolicy(
```

**Ordering note:** `json.JSONDecodeError` is a `ValueError` subclass and **must** stay listed
before the bare `except ValueError` (it is, above) or it will never be reached — same for
`FileNotFoundError` before `OSError`. Mirrors the exact ordering `report_cli.py:33-41` already
uses for the same reason.

### 4.4 Why the catch chain is shaped this way (verified against real `onnxruntime` 1.22.0)

Empirically confirmed in this environment (not from documentation — onnxruntime's Python error
hierarchy is not publicly stable):

```
>>> ort.InferenceSession("/tmp/does_not_exist.onnx", providers=["CPUExecutionProvider"])
onnxruntime.capi.onnxruntime_pybind11_state.NoSuchFile: ...
>>> ort.InferenceSession(<garbage bytes file>, providers=["CPUExecutionProvider"])
onnxruntime.capi.onnxruntime_pybind11_state.InvalidProtobuf: ...
>>> type(e).__mro__ == (NoSuchFile/InvalidProtobuf, Exception, BaseException, object)
```

Both subclass `Exception` **directly** — not `OSError`, not `ValueError`, not `RuntimeError`. A
catch chain that stopped at `RuntimeError`/`ValueError`/`OSError` would let a bad `--onnx-model`
path (missing file, corrupt file, non-ONNX file) leak a raw `onnxruntime.capi...` traceback,
violating DoD bullet 5 ("clean, actionable messages... not raw tracebacks"). The final
`except Exception` is therefore load-bearing, not defensive habit — it is the only clause that can
catch these. No narrower exception type is available to target without inspecting
`onnxruntime`-internal, undocumented classes, which would be a fragile thing to import/reference
directly.

### 4.5 Registration and global state — one caveat for QA

`register_onnx_provider` mutates the module-global `_PROVIDERS` dict in `amenities_defects.py`.
For `ingest-listing` run as `python -m src.cli.ingest_cli` or the installed console script, this
is a fresh process per invocation — no cross-invocation leakage is possible. It matters only
**within one process that calls `ingest_cli.main()` more than once** — i.e., the test suite.
`tests/integration/test_ingest_cli.py` already calls `ingest_cli.main(argv)` directly, in-process,
across many test functions in the same pytest session; any test that exercises `--onnx-model`
will leave `"onnx"` registered in `_PROVIDERS` for every test that runs after it in the same
session unless it is undone. **Use the same pattern `tests/core/cv/test_filename_corroboration.py`
already established** (`restore_providers` fixture, snapshot/restore `ad._PROVIDERS`) — do not
invent a second mechanism. This is not a new risk this mission introduces; it is the existing
"registry is global mutable state" property gaining one more caller.

---

## 5. Error paths — full table

| # | Trigger | Exception raised (verified) | Caught where | User-facing message (exact) | Exit code |
| --- | --- | --- | --- | --- | --- |
| 1 | `onnxruntime` not importable (only reachable via monkeypatch in this env — see §0.1) | `_OnnxModel.__init__` → `RuntimeError("onnxruntime not available; install it to use provider=onnx")` | `ingest_cli.main`, `except RuntimeError` | `--onnx-model {path}: onnxruntime not available; install it to use provider=onnx` | 1 (`SystemExit(str)`) |
| 2 | `--onnx-model` path doesn't exist / is corrupt / not a valid ONNX protobuf | `onnxruntime.capi.onnxruntime_pybind11_state.{NoSuchFile,InvalidProtobuf,Fail,...}` (direct `Exception` subclasses) | `ingest_cli.main`, final `except Exception` | `--onnx-model {path}: failed to load ONNX model ({e}).` | 1 |
| 3 | `--onnx-labels` path doesn't exist | `open()` → `FileNotFoundError` | `ingest_cli.main`, `except FileNotFoundError` | `--onnx-labels {path}: file not found. Check the path passed to this flag.` | 1 |
| 4 | `--onnx-labels` exists but unreadable (permissions, is a directory) | `open()` → `OSError`/`PermissionError`/`IsADirectoryError` | `ingest_cli.main`, `except OSError` | `--onnx-labels {path}: could not be read ({e}).` | 1 |
| 5 | `--onnx-labels` is not valid JSON | `json.load()` → `json.JSONDecodeError` | `ingest_cli.main`, `except json.JSONDecodeError` | `--onnx-labels {path}: not valid JSON ({e}).` | 1 |
| 6 | `--onnx-labels` is valid JSON but root isn't an object (bare list/string/number) — §0.3 | `meta.get("labels")` → `AttributeError` | `ingest_cli.main`, `except AttributeError` | `--onnx-labels {path}: must contain a JSON object with a 'labels' list, e.g. {"labels": [...]} ({e}).` | 1 |
| 7 | `--onnx-labels` is `{}` or `{"labels": []}` or `{"labels": "not-a-list"}` | `_OnnxModel.__init__` → `ValueError("labels.json must contain a non-empty 'labels' list")` | `ingest_cli.main`, `except ValueError` | `--onnx-labels {path}: labels.json must contain a non-empty 'labels' list` | 1 |
| 8 | ONNX model declares zero graph inputs | `_OnnxModel.__init__` → `RuntimeError("ONNX model has no inputs")` | `ingest_cli.main`, `except RuntimeError` (same clause as #1) | `--onnx-model {path}: ONNX model has no inputs` | 1 |
| 9 | ONNX model declares zero graph outputs | `_OnnxModel.__init__` → `RuntimeError("ONNX model has no outputs")` | same as #8 | `--onnx-model {path}: ONNX model has no outputs` | 1 |
| 10 | Only `--onnx-model` (or only `AIREAL_ONNX_MODEL`) resolves; labels half unset | (no exception — checked before registration) | `ingest_cli.main`, explicit `if bool(a) != bool(b)` check, before `register_onnx_provider` is ever called | `--onnx-model/AIREAL_ONNX_MODEL was supplied but --onnx-labels (or AIREAL_ONNX_LABELS) was not. ...` | 1 |
| 11 | Only `--onnx-labels` (or only `AIREAL_ONNX_LABELS`) resolves | same mechanism, mirrored | same as #10, mirrored wording | `--onnx-labels/AIREAL_ONNX_LABELS was supplied but --onnx-model (or AIREAL_ONNX_MODEL) was not. ...` | 1 |

Rows 1, 8, 9 share one `except RuntimeError` clause — not split further, because the underlying
exception's own message text already names the specific failure precisely (`"onnxruntime not
available..."` vs. `"ONNX model has no inputs"` vs. `"...no outputs"`), and the CLI message is
`f"--onnx-model {onnx_model}: {e}"`, which composes cleanly with all three without needing to
distinguish them structurally.

Rows 10/11 are checked **before** `register_onnx_provider` is ever called (no partial state to
unwind), which is why they need no try/except — they're a plain `if` guard.

---

## 6. The six-label unlock — mechanism trace and the exact assertions that prove it

### 6.1 Mechanism, traced end-to-end (no ontology change anywhere in this path)

1. `_FILENAME_RULES` (`src/core/cv/runner.py:213-219`) is the closed table of six filename → label
   rules, already shipped, already using the canonical ontology names directly (not synonyms):
   `mold_suspected`, `water_leak_suspected`, `ev_charger`, `parking_garage`, `parking_driveway`,
   `dishwasher`. This table is not touched by this mission.
2. `tag_amenities_and_defects` (`runner.py:420-484`) computes `covered = _covered_labels(provider)`
   **once per call** (`runner.py:440`), then for every image calls `_augment_from_filename(dets,
   lname=..., covered=covered)` (`runner.py:478`).
3. `_covered_labels(provider)` (`runner.py:223-236`) reads `provider_capabilities(provider)` —
   the label vocabulary declared for whatever function is **currently** bound to that provider
   slot — and resolves each declared string through `AMENITIES_DEFECTS_V1.lookup()`
   (case-insensitive, synonym-aware) into canonical ontology names.
4. `make_onnx_provider` (`amenities_defects.py:346-361`) declares capabilities from
   **`mdl.labels`** — i.e., directly from `labels.json`'s `"labels"` array — via
   `_declare_capabilities(_fn, mdl.labels)` at `:360`. If `labels.json` is
   `{"labels": ["mold_suspected", "water_leak_suspected", "ev_charger", "parking_garage",
   "parking_driveway", "dishwasher"]}`, then after `register_onnx_provider(model_path,
   labels_path)` runs, `provider_capabilities("onnx")` returns exactly that six-element set (all
   already canonical ontology names — `Ontology.lookup` is case-insensitive but these need no
   synonym resolution at all), so `_covered_labels("onnx")` returns all six canonical names.
5. `_augment_from_filename` (`runner.py:239-307`) branches per rule on `rule.label in covered`:
   - **Before** ONNX registration: `covered` for `"local"`/`"vision"`/`"llm"` never contains any of
     the six (`test_every_builtin_declares_a_vocabulary_and_it_is_small_and_honest`, already
     shipped, asserts this explicitly: `assert not (_covered_labels(provider) & suggestible)` for
     all three built-ins). Every filename match on e.g. `mold_basement.jpg` hits the "nothing
     registered can look for this label" branch (`runner.py:290-305`) → `source:
     "filename_unconfirmed"`, **no `confidence` key at all**.
   - **After** ONNX registration with a `local`/whatever slot rebound to a function whose
     declared vocabulary includes the label (this mission: the `"onnx"` slot specifically, since
     `--onnx-model` registers into `"onnx"`, and `build_photo_insights`'s new selection logic
     (§3.4) is what makes `provider="onnx"` actually get called for the images): if the ONNX
     model's own `predict_proba` **fires** on the label, `_augment_from_filename` finds an
     `existing` detection for that name (`runner.py:258-269`) and blends it —
     `source: "filename_confirmed"`, `confidence = corroborated_confidence(cv_conf)` (the
     documented 70/30 split, `CV_CONFIRMATION_WEIGHT=0.70` / `FILENAME_CORROBORATION_BONUS=0.30`,
     `runner.py:161-193`). If the model **doesn't** fire on that image but declares coverage
     (`rule.label in covered` and no `existing` entry), it's `source: "filename_contested"`,
     `confidence = corroborated_confidence(0.0) == 0.30` exactly (`runner.py:271-288`).
   - Either way, the label moves from `filename_unconfirmed` (case 2: unscored hint, withheld from
     every money-affecting list by `is_uncorroborated_filename_claim` /
     `_split_measured_and_hints`) to `filename_confirmed` or `filename_contested` (case 1: a real
     detector's answer, present in the record with a score — `filename_contested` still withheld
     from `amenities`/`defects`/`amenity_counts`/`defect_counts` per the R-6/G2-N1 rule, but no
     longer "nothing could check this").
6. **No file in this chain is edited by this mission.** The whole upgrade is `_declare_capabilities`
   being keyed by *function identity*, not by slot name (`amenities_defects.py:181-192`'s own
   comment already documents this as "the whole auto-upgrade mechanism"). This mission's job is
   only to make `provider="onnx"` reachable and *selected* — the auto-upgrade itself pre-exists
   and is already tested against a directly-registered fake provider
   (`test_registering_a_covering_provider_moves_the_same_input_from_case_2_to_case_1`,
   `tests/core/cv/test_filename_corroboration.py:472-489`).

### 6.2 Assertions that prove the flip, end-to-end through the new CLI seam

This mission's new end-to-end test (QA, Implementation wave) must exercise the **real** path —
CLI flags → `register_onnx_provider` → `build_photo_insights` selection → `tag_amenities_and_defects`
→ `_augment_from_filename` — not just the registry mechanics already covered by
`test_an_onnx_labels_file_is_the_capability_declaration` (which monkeypatches `_OnnxModel`, so it
proves the *declaration* travels but not that the *selection* seam wires it in). Minimum shape:

```python
def test_ingest_cli_onnx_registration_confirms_a_filename_hint_end_to_end(...):
    # Arrange: a photo directory with an image named to trigger one of the six rules, e.g.
    # "mold_basement.jpg" (a blank/synthetic image is fine -- the point is the FILE NAME, exactly
    # as tests/core/cv/test_filename_corroboration.py's `mold_photo` fixture already does).
    #
    # A tiny real .onnx file + labels.json declaring at least "mold_suspected" (see §6.3 fixture
    # plan) -- NOT monkeypatched, so this proves the wiring, not just the declaration mechanic.

    rc, out, err = _run(["--file", str(listing), "--photos", str(photos_dir),
                          "--onnx-model", str(model_path), "--onnx-labels", str(labels_path),
                          "--pretty", "0"], capsys)

    assert rc == 0
    # 1) provider selection actually reached "onnx", not "vision"/"local":
    #    read back from the printed "photo insights: provider=... version=..." line, or (better,
    #    less string-fragile) call build_photo_insights directly after the same registration and
    #    assert result.photos.provenance["selected_provider"] == "onnx"
    #    and result.photos.provenance["provider_kind"] == "model"
    #    and result.photos.version == "onnx-byo-v1"

    # 2) the six-label flip itself -- BEFORE/AFTER shape, mirroring
    #    test_registering_a_covering_provider_moves_the_same_input_from_case_2_to_case_1:
    #    - image_detections for the mold_basement.jpg sha contains an entry named
    #      "mold_suspected" with source in {"filename_confirmed", "filename_contested"}
    #      (never "filename_unconfirmed") -- this is the case-2 -> case-1 flip itself.
    #    - unconfirmed_hint_counts no longer contains "mold_suspected" for this image
    #      (or the image's contribution moved to contested_hint_counts if the model didn't fire).

    # 3) no ontology/schema change was needed to observe this -- implicit in the fact the test
    #    imports nothing new from src.schemas.models or src.core.cv.ontology.
```

A second, narrower unit-level test (not requiring the CLI or a real onnxruntime session) should
also assert the six labels are exactly what a `labels.json` needs to declare — no synonym
resolution required, since `_FILENAME_RULES` already uses the canonical names:

```python
from src.core.cv.runner import _FILENAME_RULES
assert {r.label for r in _FILENAME_RULES} == {
    "mold_suspected", "water_leak_suspected", "ev_charger",
    "parking_garage", "parking_driveway", "dishwasher",
}
```

This pins the six-label set itself against silent drift (if a future change to `_FILENAME_RULES`
added/removed a rule, this test would flag that the "six labels" claim in the charter/DoD needs
re-verification) without touching the ontology.

### 6.3 One clarification the charter's wording invites a misreading of

The charter says the six labels "move from unscored filename hints (case 2) to detector-confirmed
observations (case 1)." Precisely: they move to `filename_confirmed` **only if the registered
ONNX model's `predict_proba` actually reports the label for that image**; if it doesn't (a
plausible outcome — a real user's model looking at a real photo and disagreeing with the
filename), the label lands in `filename_contested`, not `filename_confirmed` — still case-1
territory (something looked), still correctly withheld from every money-moving list by the same
R-6 rule, but a different one of the three `source` values. The DoD bullet ("become
detector-confirmed observations") should be read as "become detector-**adjudicated**
observations" — either confirmed or contested, both are the honest outcome of "something looked."
Flag this wording precisely at Gate V so the manual-testing doc doesn't assert a specific one of
the two outcomes without controlling the synthetic model's output to guarantee it.

---

## 7. Determinism

**What must hold, and what's new risk vs. what's pre-existing:**

- **Default path (nothing registered):** unaffected by this mission — `is_provider_registered("onnx")`
  is `False`, selection reduces structurally to the pre-mission ternary (§3.4). Byte-identical
  claim is a structural guarantee, not something that needs a new regression test to hold (though
  the existing `python main.py` sha-comparison in the validation battery should still be re-run
  post-implementation as a smoke check).
- **ONNX path — model inference itself:** `onnxruntime.InferenceSession.run()` on
  `CPUExecutionProvider`, given a fixed model file and fixed input tensor, is deterministic for a
  single call. Verified empirically for the synthetic fixture design in §6.3/§8 (two consecutive
  `sess.run()` calls on identical input produced bit-identical output arrays). **Risk:** for
  larger/more complex user-supplied models, `onnxruntime`'s default session options allow
  multi-threaded intra-op parallelism, and floating-point reduction order across threads is not
  guaranteed associative — this is a documented, general property of multi-threaded numeric
  execution, not specific to this project. `_OnnxModel.__init__` (`amenities_defects.py:288`)
  constructs `InferenceSession` with **no `SessionOptions`** today — thread count and execution
  mode are left at `onnxruntime`'s defaults.
  - **Mitigation, flagged not applied by me:** pin
    `sess_options.intra_op_num_threads = 1` and `sess_options.execution_mode =
    ort.ExecutionMode.ORT_SEQUENTIAL` when constructing the session in `_OnnxModel.__init__`. One
    line, safe, and directly serves this mission's own binding determinism constraint. This is a
    `core/cv` diff, not just CLI wiring — flag it to Gate D/`staff-code-reviewer` as a
    recommended addition rather than applying it silently; if it's deferred, the mission's
    "byte-identical" claim for the ONNX path should be scoped explicitly to "verified for the
    shipped synthetic fixture; not a guarantee for arbitrary user-supplied models," which is an
    honest, defensible scope (bring-your-own-model inherently cannot guarantee bit-exact
    reproducibility of someone else's graph across arbitrary hardware/thread counts — that's a
    property of the user's model, not of this wiring).
- **Cache interaction:** `tag_amenities_and_defects`'s cache key already includes
  `_capability_fingerprint(provider)` (`runner.py:69-80`, a hash of `provider_capabilities(provider)`),
  so a different `labels.json` (different declared vocabulary) lands in a different cache
  namespace automatically — already covered by
  `test_a_warm_cache_cannot_serve_a_pre_registration_answer`. No new cache-key work needed for
  this mission.
- **Process-global registry state (§4.5):** not a determinism risk for a single CLI invocation
  (fresh process); is a **test-isolation** risk within one pytest session. Mitigation: reuse
  `restore_providers` (§4.5).
- **`os.getenv` read timing:** `AIREAL_ONNX_MODEL`/`AIREAL_ONNX_LABELS` are read once, at the top
  of `main()`, before registration — same "read once, don't re-read mid-run" discipline
  `cv_tagging_orchestrator.py`'s `_VISION_ENABLED` already uses (module-import-time there vs.
  call-time here; call-time is correct for a CLI `main()` that may be invoked multiple times
  in-process during tests, per §4.5's caveat — import-time capture would be wrong here for exactly
  that reason).

---

## 8. Synthetic ONNX fixture plan (for QA to execute, not built here)

### 8.1 What's available in the `airedeal` env today (verified)

| Package | Status | Usable for building a `.onnx` file? |
| --- | --- | --- |
| `onnxruntime` 1.22.0 | hard runtime dependency (§0.1) | No — inference only; does not bundle the ONNX protobuf message classes (`ModelProto` etc. are not importable from it — verified: `onnxruntime.capi.onnx_pb` does not exist) |
| `onnx` (the model/IR package) | **not installed**, not a declared dependency anywhere | Yes — this is the standard tool for constructing an ONNX graph by hand |
| `torch` 2.9.0+cu128 | installed in this specific conda env, but **not a declared project dependency** (absent from `requirements*.txt`/`pyproject.toml`) — appears to be incidental to this machine, not guaranteed on CI or another dev's machine | Not usable/relyable-on for this purpose regardless of technical feasibility — see below |
| `google.protobuf` 5.29.5 | present, transitively required by `onnxruntime` itself (`pip show protobuf` lists `onnxruntime` under `Required-by`) | Present but insufficient alone — no ONNX-specific compiled message classes without the `onnx` package |

Verified empirically: `torch.onnx.export(..., dynamo=False)` (the legacy exporter) still requires
the `onnx` package to be importable (`torch.onnx.OnnxExporterError: Module onnx is not
installed!`); the newer `dynamo=True` path requires `onnxscript`, also absent. **`torch` cannot be
used to produce the fixture without also installing `onnx`, so it adds no capability over
installing `onnx` directly and should not be relied on at all** — it is not a declared dependency
and its presence in this one env is not a guarantee for CI or another contributor's machine.

### 8.2 Two options, with trade-offs

**Option A — generate the fixture at test time, add `onnx` to `requirements-dev.txt`.**

- Verified feasible: `pip install onnx` (in an isolated throwaway venv, not the project's `airedeal`
  env) pulled cleanly and produced a working, tiny (382-byte) model via `onnx.helper.make_node` /
  `make_graph` / `make_model`, loadable and runnable by the project's actual `onnxruntime==1.22.0`
  with correct shape/`nchw` auto-detection by `_OnnxModel.__init__`.
- Pro: matches the repo's dominant test-fixture idiom — every other synthetic binary test asset in
  this suite (photos, in particular `tests/core/cv/test_filename_corroboration.py`'s `_photo()`
  helper) is generated in Python at test time via a library already in the dependency graph
  (Pillow), not committed as an opaque blob. `onnx` shares its `protobuf` dependency with the
  already-hard-required `onnxruntime`, so there is no realistic version-conflict risk. The graph
  shape stays in the diff, auditable and trivially adjustable (e.g. a reviewer wanting a
  "zero-outputs" variant for error-path row 9 can read exactly how it's built).
- Con: it is a genuinely new dependency (dev-only, but new) that CI and every contributor's local
  test run must install; this is the **first** time this repo's tooling would depend on `onnx`
  itself (as opposed to `onnxruntime`, which arrived via a different, already-justified path).

**Option B — commit a prebuilt tiny binary `.onnx` fixture, generated once outside the normal
dev/test toolchain, plus a documented (not-CI-invoked) regeneration script.**

- Pro: zero new dependency footprint anywhere — CI and the test suite need only `onnxruntime`
  (already required). 382 bytes is negligible size-wise, in the same category as the JPEG photos
  already committed under `data/sample_listings/` (though those are product demo data, not pytest
  fixtures — there is no existing precedent for a committed *test* fixture binary in `tests/`).
- Con: opaque, non-diffable binary in git history; regenerating it later (different label set,
  different shape, a deliberately-defective variant) requires `onnx` installed **outside** the
  declared toolchain, which can bit-rot; less self-documenting than Option A.

**Recommendation: Option A.** The deciding factor is precedent consistency, not size or
dependency-count alone — this codebase's own established pattern for "we need a small synthetic
binary asset for a test" is "generate it in Python, at test time, in the test file," and `onnx`
is the narrowly-scoped, dev-only tool that lets this fixture follow that pattern rather than being
the one exception. `staff-qa-test-engineer` and Gate D/V hold the final call; if Option B is
preferred for dependency-count discipline, the 382-byte model shape in §8.3 below is directly
portable to a one-time generation script either way.

**Note, independent of A/B:** the "malformed/unreadable model file" error-path test (row 2, §5)
needs **no** generation tooling regardless of which option is chosen — `open(p,
"wb").write(b"not a real onnx file")` is sufficient and was the exact input used to verify the
`InvalidProtobuf` exception path in §4.4.

### 8.3 Exact minimal graph shape (verified against real `onnxruntime` 1.22.0 in this repo's target version range)

Constraints the fixture must satisfy, derived from `_OnnxModel`'s actual behavior when
`register_onnx_provider(model_path, labels_path)` is called with **no extra kwargs** (the CLI
wiring in §4 never passes `image_size`/`input_name`/`mean`/`std` — only two flags exist per the
product lock):

- Input must accept `_OnnxModel`'s default `image_size=(224, 224)` after `_preprocess` resizes and
  transposes to NCHW (`amenities_defects.py:313-322`) — i.e. shape `[1, 3, 224, 224]` at inference
  time. **Do not hardcode 224×224 into the graph's weights** (that would need a `3*224*224 × K`
  weight matrix, ~3.6 MB as float32 — defeats "tiny"). Declare the spatial dims **symbolic**
  (`"H"`, `"W"`) and reduce with `GlobalAveragePool` before the classifier head, so the only
  learned weight is a `[3, K]` matrix regardless of input size.
- Output must be `[1, K]` where `K == len(labels)` in the paired `labels.json`, values in `[0, 1]`
  (apply `Sigmoid` in-graph, or leave logits and let `_OnnxModel.predict_proba`'s auto-sigmoid
  fallback handle it — either is fine; in-graph `Sigmoid` is simpler to reason about and was what
  was verified).
- `K = 6`, and `labels.json` declares exactly:
  `["mold_suspected", "water_leak_suspected", "ev_charger", "parking_garage", "parking_driveway", "dishwasher"]`
  (no synonyms needed — these are already the canonical ontology names, per §6.1).

Verified graph (`onnx.helper`, opset 13): `GlobalAveragePool(input) → Reshape([1,3]) →
Gemm(W:[3,6], B:[6]) → Sigmoid → output:[1,6]`. Result: **382 bytes**, `onnx.checker.check_model`
passes, loads and runs correctly under this repo's actual `onnxruntime`, `_OnnxModel` correctly
auto-detects NCHW (`ishape[1] == 3` branch, since `ishape[-1]` is the symbolic string `"W"` and
`"W" == 3` is `False`), and two consecutive `sess.run()` calls on identical input produced
bit-identical output arrays (determinism check for §7).

For a fixture that needs to *fire* on a specific label (to test the `filename_confirmed` branch of
§6.2 rather than only `filename_contested`), bias that output unit's bias term (`B[i]`) positive
enough that `Sigmoid` clears whatever threshold the test asserts against, independent of the
random input pixels — do not rely on the actual image content to produce a specific score, since
the point of these tests (mirroring `test_registering_a_covering_provider_moves_the_same_input_from_case_2_to_case_1`)
is that the *file name*, not the pixels, is what's under test.

---

## 9. Files touched / NOT touched

### Touched (this mission)

| File | Why |
| --- | --- |
| `src/core/cv/amenities_defects.py` | Add `is_provider_registered` (§3.1). Optionally (flagged, not decided by me): pin `SessionOptions` for determinism (§7) inside `_OnnxModel.__init__`. |
| `src/core/cv/photo_insights.py` | New `ONNX_BYO_VERSION` constant, new import, selection logic change (§3.2-3.4). |
| `src/cli/ingest_cli.py` | New imports, two new argparse flags, resolution/precedence/registration/error-handling block in `main()` (§4). |
| `tests/integration/test_ingest_cli.py` | New CLI-flag tests (happy path, partial-pair, each error row) — existing file, existing `_run()` harness, no new test file needed for this slice. |
| `tests/core/cv/*` (new or extended) | Six-label end-to-end proof (§6.2), synthetic fixture (§8), determinism repeat-run check (§7). |
| `src/core/README.md` | **Flagged for `staff-documentation-maintainer`, not edited here:** correct the stale "not declared in requirements.txt" claim at line 196 (§0.1); document the new CLI path per §2. |
| `src/cli/README.md` | **Flagged, not edited here:** add `--onnx-model`/`--onnx-labels` rows to the flag table (same shape as the existing `--ai` row), with the `main.py` caveat. |
| `CHANGELOG.md` `[Unreleased]` | **Flagged, not edited here:** describe the new path per the DoD's honesty requirement; close backlog §3's "No real AI provider" row for offering 1 only. |

### NOT touched (confirmed, and must stay that way)

- `src/core/finance/**` — zero diff. Nothing in this spec reads or writes a `FinancialInputs`,
  `FinancialForecast`, or `InvestmentThesis` field, or calls into `src/core/finance/engine.py`,
  `amortization.py`, or `xirr.py`.
- `src/schemas/models.py` — zero diff. `PhotoInsights.provenance` is already `dict[str, Any]`
  (`src/schemas/models.py:744-747`) and absorbs `selected_provider="onnx"`/`provider_kind="model"`
  with no field addition. `ProviderName` (a `Literal` type alias in `core/cv`, not a schema model)
  already includes `"onnx"` (§1) — no schema-layer change needed there either.
- Ontology / label set (`src/core/cv/ontology.py`, `src/schemas/labels.py`) — zero diff. The six
  labels already exist in the closed set (§6.1); this mission changes only which `source`/
  `confidence` a matching filename record gets, never the set of labels the ontology recognizes.
- `main.py`, `src/orchestrators/cv_tagging_orchestrator.py`, `src/agents/listing_analyst.py` —
  zero diff (§1, Fact 7 reconfirmed). The `--onnx-model`/`--onnx-labels` help text explicitly says
  so (§4.2) so a `main.py`-only user isn't left wondering why the flags seem inert there.
- `src/core/ingest/listing_ingest.py` — zero diff. `ingest_listing`'s signature is unchanged;
  `build_photo_insights(photos_path, use_ai=use_ai)` calls it exactly as today. Selection reaches
  `"onnx"` purely through the registry query inside `build_photo_insights` itself (§3.1, §3.4) —
  no new parameter threading required through this function or its agent-facing wrapper
  `run_listing_ingest_tool`.
- `src/orchestrators/crewai_runner.py`, `src/orchestrators/crew.py` — zero diff. Both call
  `build_photo_insights(Path(photos_folder))` with no `use_ai` kwarg; unaffected by default
  (§3.4's structural byte-identical guarantee applies to them too, automatically, without any
  change on their part).
- `requirements.txt` — zero diff (§0.1's finding is flagged for a Gate V product call, not applied
  here; my recommendation is to leave it as-is and only fix the stale doc claim).

---

## 10. Open items for the next gates (not decided here)

1. **§0.1** — `onnxruntime`'s packaging (hard dep vs. extra): recommend leave as-is, fix the stale
   doc line only. Founder-proxy call at Gate V.
2. **§0.3** — `_OnnxModel.__init__`'s `AttributeError` gap: recommend CLI-side containment (A) for
   this mission; core one-line fix (B) as an optional fast-follow bundled at reviewer discretion.
3. **§7** — `SessionOptions` determinism pin in `_OnnxModel.__init__`: recommended, not applied;
   flagged as a `core/cv` diff for Gate D/`staff-code-reviewer` to accept or defer (with an honest
   scope-narrowing of the "byte-identical" claim if deferred).
4. **§8.2** — fixture generation strategy (Option A, add `onnx` to `requirements-dev.txt`, vs.
   Option B, commit a prebuilt binary): recommend A; `staff-qa-test-engineer` implements and Gate V
   reviews.
5. **§6.3** — the DoD's "detector-confirmed observations" wording should be read as
   "detector-adjudicated" (confirmed OR contested); flagging so the manual-testing doc and Gate V
   sign-off don't assert a specific one of the two outcomes without a fixture engineered to
   guarantee it (§8.3's biased-output-unit technique).
