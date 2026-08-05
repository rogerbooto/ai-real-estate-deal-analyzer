# src/core/cv/amenities_defects.py
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import (
    Any,
    Literal,
    TypeAlias,
    TypedDict,
)

import numpy as np
from PIL import Image, ImageStat

# Enum-aligned labels
from src.schemas.labels import MaterialTag

# `DetectionSource` — how a `DetectedLabel` entry came to exist, and the four epistemic states of
# the rule "a file name may SUGGEST; only a detector that actually looked may CONFIRM". Re-exported
# here under its historical name because every consumer in `core/cv` reads it from this module and
# `runner._augment_from_filename` is the producer that assigns it. The DEFINITION lives in the
# schema layer (with the canonical description of the four states) because the marker now crosses a
# pipeline boundary on `DetectedLabelModel`, and `src/schemas` may not import `src/core` — so only
# one of the two can own it, and it has to be that one.
from src.schemas.models import DetectionSource as DetectionSource

from .ontology import Ontology

ProviderName = Literal["local", "vision", "llm", "onnx"]
RawCandidate: TypeAlias = str | dict[str, object]
ProviderFn: TypeAlias = Callable[[Image.Image], Iterable[RawCandidate]]


class ImageDesc(TypedDict):
    luminance: float  # 0..1
    spread: float  # channel spread across mean RGB
    aspect: Literal["landscape", "portrait", "square"]


#: The value that marks an entry nothing was capable of measuring. Named once so the "keep it out
#: of the money path" checks downstream cannot drift from the producer.
UNCONFIRMED_HINT_SOURCE = "filename_unconfirmed"

#: The value that marks an entry a covering detector examined the pixels for and did NOT report.
CONTESTED_HINT_SOURCE = "filename_contested"

#: Sources whose claim originates in a file name rather than in a provider's own output.
FILENAME_SOURCES: frozenset[str] = frozenset({"filename_confirmed", CONTESTED_HINT_SOURCE, UNCONFIRMED_HINT_SOURCE})


class DetectedLabel(TypedDict, total=False):
    """
    Normalized detection record, strictly within the closed-set ontology.
      - name: canonical label (snake_case)
      - category: "amenity" | "defect"  (from ontology)
      - confidence: float in [0,1]      (ABSENT when nothing measured the label -- see
                                         ``DetectionSource.filename_unconfirmed``)
      - evidence: list[str] | None
      - rationale: str | None
      - source: see :data:`DetectionSource` (optional; absent means "pixels")

    ``source`` exists because a filename inference and a detection are otherwise
    indistinguishable once spliced into one list, and downstream provenance stamped every entry
    ``origin="cv_provider"``. That turned a blank grey image named "mold_basement.jpg" into a
    0.90-confidence "mould suspected" finding attributed to a detector, with no evidence and no
    rationale.
    """

    name: str
    category: Literal["amenity", "defect"]
    confidence: float
    evidence: list[str] | None
    rationale: str | None
    source: DetectionSource


#: The one sentence in this codebase that describes an unconfirmed hint to a reader.
#:
#: Defined next to the state it describes so the module that decides "nothing measured this" also
#: owns how that is said, and every path (the deterministic analyst, the ingest synthesis) says it
#: identically. Wording is deliberate: it names what was inferred, admits nothing looked, and
#: states the consequence — a reader who sees this must not be able to mistake it for a finding.
UNCONFIRMED_HINT_NOTE = (
    "Unconfirmed photo hint: a file name suggests '{label}', but no registered detector can "
    "examine the pixels for it. Recorded as a hint only — it is not counted as an observation "
    "and does not affect any number in this analysis."
)


#: The sibling sentence, for the OTHER half of the rule: something WAS able to look, looked, and
#: did not see it. Deliberately not a variant of the wording above — "nothing could check this" and
#: "a detector checked and disagreed" are different facts, and a reader told the second must not
#: come away believing the first. The corroboration score is deliberately NOT quoted here: it is
#: 0.30 by construction for every contested entry (see ``runner.corroborated_confidence``), it is
#: not a safety property, and printing it invites a reader to take it as a partial endorsement of a
#: claim a detector rejected. The consequence is stated instead, because that is what is actionable.
CONTESTED_HINT_NOTE = (
    "Contested photo hint: a file name suggests '{label}', but a detector able to recognise it "
    "examined the pixels and did not report it. Recorded as a hint only — it is not counted as an "
    "observation and does not affect any number in this analysis."
)


def unconfirmed_hint_note(label: str) -> str:
    """Render :data:`UNCONFIRMED_HINT_NOTE` for one label."""
    return UNCONFIRMED_HINT_NOTE.format(label=label)


def contested_hint_note(label: str) -> str:
    """Render :data:`CONTESTED_HINT_NOTE` for one label."""
    return CONTESTED_HINT_NOTE.format(label=label)


def is_unconfirmed_hint(det: Mapping[str, Any]) -> bool:
    """True when nothing examined the pixels for this label, so it carries no confidence.

    The single predicate every consumer uses to answer "may this entry influence a number?".
    Answer: no. It is a hint the reader is shown, not an observation anything measured.
    """
    return str(det.get("source", "pixels")) == UNCONFIRMED_HINT_SOURCE


def is_contested_hint(det: Mapping[str, Any]) -> bool:
    """True when a detector that COVERS this label examined the image and did not report it.

    Same answer as :func:`is_unconfirmed_hint` to the question "may this entry influence a
    number?" — no — and for a stronger reason: there, nothing measured the claim; here, something
    measured it and disagreed. The claim is scoreable (it has a corroboration score) but a score
    is not a licence, because the consumers that select OPEX and income rules read MEMBERSHIP and
    never a confidence.
    """
    return str(det.get("source", "pixels")) == CONTESTED_HINT_SOURCE


def is_filename_derived(det: Mapping[str, Any]) -> bool:
    """True when the *claim* originated in a file name (whether or not a detector corroborated it)."""
    return str(det.get("source", "pixels")) in FILENAME_SOURCES


#: The only two ``source`` values that positively mean "a detector emitted this label itself" --
#: either it looked directly (``"pixels"``, the default) or its own emission was independently
#: corroborated by a matching file name (``"filename_confirmed"``). This is an ALLOW-list, not a
#: deny-list, on purpose: :func:`is_uncorroborated_filename_claim` used to be written as "value is
#: in ``FILENAME_SOURCES`` and is not ``filename_confirmed``" -- a deny-list keyed on
#: ``FILENAME_SOURCES``, a hardcoded three-element ``frozenset``. A ``source`` value that predicate
#: had never seen (a fifth state added later, or a typo, or a producer from outside this module)
#: was, by construction, NOT a member of that set, so the deny-list read it as "not a filename
#: claim" and let it through unwithheld -- silently promoting an unrecognised state to a detector's
#: finding, exactly the failure this function exists to prevent. Reproduced directly: feed
#: ``"filename_llm_guessed"`` to the old body and it returns ``False``. Flipping the polarity to an
#: allow-list closes that: only a value proven to mean "a detector emitted this" is trusted;
#: everything else -- known-withheld, unknown, or not-yet-invented -- is withheld by default.
_DETECTOR_EMITTED_SOURCES: frozenset[str] = frozenset({"pixels", "filename_confirmed"})


def is_uncorroborated_filename_claim(source: str | None) -> bool:
    """True unless ``source`` positively means a detector emitted the label itself.

    Takes the raw ``source`` VALUE rather than a record, because the two holders of that value have
    different shapes: ``core/cv`` and ``orchestrators`` hold raw ``DetectedLabel`` mappings, while
    ``core.insights.synthesis`` holds a validated :class:`~src.schemas.models.DetectedLabelModel`.
    One rule, two access shapes, no second copy of the rule.

    Written as "NOT positively a detector's own emission" -- an allow-list of the two values that
    mean that (see :data:`_DETECTOR_EMITTED_SOURCES`) -- rather than "is contested or unconfirmed",
    so that a source value this function has never seen lands in the cautious branch by default: an
    unrecognised filename state must never be promoted to a detector's finding by omission.
    """
    value = str(source or "pixels")
    return value not in _DETECTOR_EMITTED_SOURCES


# =========================
# Provider capability declarations
# =========================

#: What each provider FUNCTION declares it can detect, keyed by the function object itself and
#: NOT by the slot name. That is the whole auto-upgrade mechanism: overwrite a slot with a
#: different function and the capabilities travel with the new function automatically, so the day
#: a classifier covering ``mold_suspected`` is bound in, that label stops being "nothing measured
#: it" with no code change anywhere. It mirrors ``provider_kind``'s identity check for the same
#: reason -- a list keyed by slot name would need a human to remember to update it.
#:
#: Entries outlive any one binding: a function's vocabulary is a property of the function, not of
#: the slot it happens to occupy, so re-registering it elsewhere keeps its declaration. The
#: retention is bounded by the number of distinct providers a process ever registers (realistically
#: one), which is why this is a plain dict and not a weak-keyed one -- weak keys would silently
#: drop the declaration of a provider passed as a bound method, and "silently covers nothing" is
#: the one failure mode this whole mechanism exists to avoid.
_PROVIDER_CAPABILITIES: dict[ProviderFn, frozenset[str]] = {}


def _declare_capabilities(fn: ProviderFn, labels: Iterable[str]) -> None:
    """Record the label vocabulary ``fn`` is able to emit. Idempotent; last declaration wins."""
    _PROVIDER_CAPABILITIES[fn] = frozenset(str(x).strip().lower() for x in labels if str(x).strip())


def provider_capabilities(provider: ProviderName) -> frozenset[str]:
    """Labels the function CURRENTLY bound to ``provider`` declares it can detect.

    Names are returned as declared (lower-cased, stripped) and may be ontology synonyms; the
    caller resolves them against whichever ontology it is running, because the ontology is
    injected at detection time (see :func:`detect_from_image`) rather than owned by this module.

    Returns an EMPTY set for a provider whose function never declared anything -- e.g. one poked
    straight into ``_PROVIDERS``. Empty means "declares no coverage", never "covers everything":
    silence is not evidence that something looked. Raises ``ValueError`` for an unregistered
    provider, matching :func:`detect_from_image` and :func:`provider_kind`.
    """
    fn = _PROVIDERS.get(provider)
    if fn is None:
        raise ValueError(f"Unknown provider: {provider}")
    return _PROVIDER_CAPABILITIES.get(fn, frozenset())


def provider_covers(provider: ProviderName, *canonical_labels: str, ontology: Ontology) -> bool:
    """True when the function bound to ``provider`` declares a synonym for any of ``canonical_labels``.

    Answers the question a report has to ask before it may print a NEGATIVE finding ("no EV
    charging observed", "parking: none"): was anything even capable of looking for this? A default
    value on a schema (e.g. ``ParkingSummary.ev_charging = False``) and a real negative observation
    are indistinguishable once printed, and on every shipped provider today (see the "Built-in
    capability declarations" block below -- exhaustively ``{natural_light_high,
    stainless_appliances}`` plus synonyms) the default is what actually reaches the reader; nothing
    built in declares any parking or EV-charging label. Printing that default as a sighting is R-6
    inverted: the same "nothing looked" vs. "something looked and disagreed" distinction that keeps
    a file name from asserting a defect applies just as much to a report asserting an absence.

    ``provider_capabilities(provider)`` may return synonyms rather than canonical ontology names
    (an ONNX labels file is whatever the model's author wrote), so each declared name is resolved
    through ``ontology`` before comparing -- the same resolution
    :func:`~src.core.cv.runner._covered_labels` performs for filename corroboration, exposed here
    publicly because a reporting consumer needs the identical answer and lives outside ``core/cv``.

    Raises ``ValueError`` for an unregistered ``provider``, matching :func:`provider_capabilities`.
    """
    wanted = {lab.strip().lower() for lab in canonical_labels if lab and lab.strip()}
    if not wanted:
        return False
    for raw in provider_capabilities(provider):
        meta = ontology.lookup(raw)
        if meta is not None and meta["name"] in wanted:
            return True
    return False


# =========================
# ONNX provider components
# =========================


class _OnnxModel:
    """
    Lightweight wrapper around onnxruntime.Session for single-image multi-label classification.
    Lazily imports onnxruntime and stays CPU-only. Not used by tests unless explicitly registered.
    """

    def __init__(
        self,
        model_path: str,
        labels_path: str,
        *,
        input_name: str | None = None,
        image_size: tuple[int, int] = (224, 224),
        mean: tuple[float, float, float] = (0.485, 0.456, 0.406),
        std: tuple[float, float, float] = (0.229, 0.224, 0.225),
    ) -> None:
        try:
            import onnxruntime as ort
        except Exception as e:  # pragma: no cover
            raise RuntimeError("onnxruntime not available; install it to use provider=onnx") from e

        import json

        self.image_size = image_size
        self.mean = mean
        self.std = std

        with open(labels_path, encoding="utf-8") as f:
            meta = json.load(f)
        labels = meta.get("labels")
        if not isinstance(labels, list) or not labels:
            raise ValueError("labels.json must contain a non-empty 'labels' list")
        self.labels: list[str] = [str(x) for x in labels]

        # init session (CPU-only)
        self._ort = ort
        self.sess = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])

        # Detect input
        inputs = self.sess.get_inputs()
        if not inputs:
            raise RuntimeError("ONNX model has no inputs")
        self.input_name = input_name or inputs[0].name
        ishape = inputs[0].shape
        # ishape could be [1, 3, H, W] or [1, H, W, 3]
        self.nchw = False
        try:
            if ishape[-1] == 3:
                self.nchw = False  # NHWC
            elif ishape[1] == 3:
                self.nchw = True  # NCHW
        except Exception:
            # default to NCHW if ambiguous
            self.nchw = True

        # Detect output
        outs = self.sess.get_outputs()
        if not outs:
            raise RuntimeError("ONNX model has no outputs")
        self.output_name = outs[0].name

    def _preprocess(self, img: Image.Image) -> Any:
        img = img.convert("RGB").resize(self.image_size)
        arr = np.asarray(img).astype("float32") / 255.0  # HWC
        # normalize
        arr = (arr - self.mean) / self.std
        if self.nchw:
            arr = arr.transpose(2, 0, 1)  # CHW
        # add batch dim
        arr = arr[None, ...]
        return arr

    def predict_proba(self, img: Image.Image) -> list[tuple[str, float]]:
        import numpy as np

        x = self._preprocess(img)
        pred = self.sess.run([self.output_name], {self.input_name: x})[0]
        pred = np.asarray(pred)

        # Expect [1, K]
        if pred.ndim != 2 or pred.shape[0] != 1:
            # Flatten if needed
            pred = pred.reshape(1, -1)
        vec = pred[0]

        # If values not in [0,1], assume logits → sigmoid
        if (vec < 0).any() or (vec > 1).any():
            vec = 1.0 / (1.0 + np.exp(-vec))

        K = min(len(self.labels), vec.shape[0])
        out = [(self.labels[i], float(vec[i])) for i in range(K)]
        return out


def make_onnx_provider(
    model_path: str,
    labels_path: str,
    **kwargs: Any,
) -> ProviderFn:
    mdl = _OnnxModel(model_path, labels_path, **kwargs)

    def _fn(img: Image.Image) -> Iterable[RawCandidate]:
        # Convert probabilities into RawCandidates
        return [{"name": name, "confidence": prob} for name, prob in mdl.predict_proba(img)]

    # The labels file IS this model's capability declaration -- it is exactly the vocabulary the
    # network has an output unit for. Declaring it here means an ONNX model registered through
    # either entry point below is self-describing without the caller repeating itself.
    _declare_capabilities(_fn, mdl.labels)
    return _fn


def register_provider(name: ProviderName, fn: ProviderFn, *, detects: Iterable[str]) -> None:
    """
    Bind ``fn`` into the provider slot ``name`` and declare the label vocabulary it can emit.

    ``detects`` is the provider's **capability declaration**: the set of labels this provider is
    able to produce from pixels, whether or not it produces them for any given image. It is not a
    claim about one image; it answers the prior question "is anything here even *able* to look for
    this?", which is what separates "a detector looked and disagreed" from "nothing measured it"
    (see :data:`DetectionSource`).

    A provider bound directly into ``_PROVIDERS`` without going through here declares nothing and
    is therefore treated as covering no labels -- the conservative reading, and the honest one: an
    undeclared vocabulary is not evidence of coverage.
    """
    _declare_capabilities(fn, detects)
    _PROVIDERS[name] = fn


def register_onnx_provider(
    model_path: str,
    labels_path: str,
    **kwargs: Any,
) -> None:
    """
    Runtime registration for provider='onnx'.

    Python-API opt-in hook only: nothing in the shipped CLIs (`ingest-listing`,
    `deal-report`, `deal-advisor`) or `main.py` calls this. A caller that wants
    an ONNX-backed detector must invoke it explicitly before requesting
    provider='onnx' (e.g. from a notebook, script, or a future user-supplied
    model integration -- see roadmap backlog).

    ``labels_path`` doubles as the capability declaration; see :func:`register_provider`.
    """
    _PROVIDERS["onnx"] = make_onnx_provider(model_path, labels_path, **kwargs)


# --- Provider registry -------------------------------------------------------


def _provider_local(img: Image.Image) -> Iterable[RawCandidate]:
    """
    Very lightweight, deterministic heuristics.
    Intent: provide a sensible baseline without external models.

    Heuristics:
      - natural_light_high: high average luminance
      - stainless_appliances: many near-gray pixels at mid-high brightness
    """
    # Work on a small thumbnail for speed
    thumb = img.convert("RGB").copy()
    thumb.thumbnail((128, 128))

    # Stats
    stat = ImageStat.Stat(thumb)
    mean_r, mean_g, mean_b = stat.mean  # 0..255
    # Perceived luminance (Rec. 601)
    luminance = (0.299 * mean_r + 0.587 * mean_g + 0.114 * mean_b) / 255.0  # 0..1

    out: list[RawCandidate] = []

    # Heuristic 1: very bright overall image → "natural_light_high"
    if luminance >= 0.78:
        # Map luminance → confidence in [0.60, 0.90]
        conf = 0.60 + min(0.30, max(0.0, (luminance - 0.78) / 0.22 * 0.30))
        out.append(
            {
                "name": "natural_light_high",
                "confidence": float(conf),
                "evidence": [f"avg_luminance={luminance:.3f}"],
                "rationale": "Image is very bright overall, suggesting strong natural light.",
            }
        )

    # Heuristic 2: stainless_appliances proxy via 'grayness' at mid-high brightness
    # Measure channel variance across RGB means to approximate "gray"
    mean_vals = [mean_r, mean_g, mean_b]
    mean_avg = sum(mean_vals) / 3.0
    spread = max(mean_vals) - min(mean_vals)  # channel spread
    brightness_ok = 120.0 <= mean_avg <= 210.0  # mid-high brightness band
    grayish = spread <= 12.0  # channels close → gray/silver look
    if brightness_ok and grayish:
        out.append(
            {
                "name": MaterialTag.stainless_appliances.value,
                "confidence": 0.65,  # conservative
                "evidence": [f"channel_spread={spread:.1f}", f"mean_avg={mean_avg:.1f}"],
                "rationale": "Low channel spread at mid-high brightness approximates stainless finish.",
            }
        )

    return out


def _describe_image(img: Image.Image) -> ImageDesc:
    """
    Return simple, deterministic descriptors used by stubs:
      - luminance [0..1]
      - gray_spread (channel spread across means)
      - aspect ('landscape'/'portrait'/'square')
    """
    im = img.convert("RGB").copy()
    im.thumbnail((128, 128))  # bound runtime
    stat = ImageStat.Stat(im)
    mr, mg, mb = stat.mean
    luminance = (0.299 * mr + 0.587 * mg + 0.114 * mb) / 255.0
    spread = max(mr, mg, mb) - min(mr, mg, mb)
    w, h = im.size
    if w > h:
        aspect: Literal["landscape", "portrait", "square"] = "landscape"
    elif h > w:
        aspect = "portrait"
    else:
        aspect = "square"

    return {"luminance": float(luminance), "spread": float(spread), "aspect": aspect}


def _provider_vision_stub(img: Image.Image) -> Iterable[RawCandidate]:
    """
    Placeholder occupying the ``"vision"`` provider slot until a real model is wired in.

    THIS IS NOT A MODEL. It is a hand-written threshold over three image statistics.
    Callers that surface its output must label it as such — see ``provider_kind()``
    and the ``version`` / ``provenance`` fields set by
    ``src.core.cv.photo_insights.build_photo_insights``.

    Method
    ------
    1. `_describe_image(img)` yields:
       • luminance (float, [0-1]) — average brightness
       • spread (float) — RGB channel spread (low spread ≈ gray/metallic)
       • aspect ("landscape" | "portrait" | "square") — image orientation
    2. Two thresholds fire:
       • High luminance (≥ 0.75) → `"natural light"` (proxy for a well-lit room)
       • Mid-high luminance and low channel spread → `"stainless appliances"`
         (proxy for a stainless finish)
    3. Returns raw candidates: {"name": str, "confidence": float, "rationale": str}

    What it deliberately does NOT emit
    ----------------------------------
    A parking label. This stub used to emit `"street parking"` for any landscape-
    oriented image at luminance ≥ 0.50 — i.e. it asserted a *property attribute*
    from the photo being wide and not dark. On the committed demo listing that fired
    on 8 of 12 photos and drove `parking={"parking_type": "street", "parking_spots": 1}`
    plus `amenities["parking"]=True` in the report. Those roll-ups carry no room for
    a caveat, so the guess could not be labelled at the point a user reads it. A
    fabricated parking claim on a real listing is worse than saying nothing, so the
    threshold is removed rather than annotated. A real classifier registered into
    this slot may of course emit `street_parking`; the ontology entry and the
    `_parking_summary` roll-up that consume it are untouched.

    Notes
    -----
    - Deterministic and purely heuristic; no ML, no randomness.
    """
    description = _describe_image(img)
    lum = description["luminance"]
    spr = description["spread"]

    out: list[RawCandidate] = []

    # bright image → natural_light_high
    if lum >= 0.75:
        out.append({"name": "natural light", "confidence": 0.72, "rationale": "vision_stub: high luminance"})

    # gray-ish mid-high brightness → stainless_appliances proxy
    if 115.0 <= (lum * 255.0) <= 210.0 and spr <= 14.0:
        out.append({"name": "stainless appliances", "confidence": 0.66, "rationale": "vision_stub: low channel spread"})

    return out


# --- LLM stub: caption → forced-choice keyword matching ----------------------
def _provider_llm_stub(img: Image.Image) -> Iterable[RawCandidate]:
    """
    Deterministic *LLM stub* provider: simulates text-based vision captioning.

    Purpose
    -------
    Mimics the behavior of a large-language-model (LLM) vision backend by
    transforming simple visual descriptors into textual "captions" and
    performing forced-choice keyword mapping to ontology tags.

    Method
    -------
    1. Uses `_describe_image(img)` to extract:
       • luminance (float) — overall brightness
       • spread (float) — RGB channel variance (proxy for material texture)
       • aspect ("landscape" | "portrait" | "square") — image orientation
    2. Builds a pseudo-caption string:
       `"Photo, {brightness} lighting, {aspect} frame, spread={spread:.1f}"`
       where brightness ∈ {"bright", "normal", "dim"}.
    3. Applies rule-based keyword matching:
       • If caption mentions "bright" → `"natural_light_high"`
       • If spread ≤ 12.0 and luminance ≥ 0.45 → `"stainless steel appliances"`
    4. Each output candidate includes:
       {
         "name": <ontology tag>,
         "confidence": float,
         "evidence": [<caption>],
         "rationale": "caption-><trigger>"
       }

    What it deliberately does NOT emit
    ----------------------------------
    A parking label — the same removal already made to ``_provider_vision_stub``, which this stub
    outlived by one release. It used to emit `"on-street parking"` at 0.61 whenever
    `aspect == "landscape" and luminance >= 0.55`: a *property attribute* asserted from a photo
    being wide and not dark. `"on-street parking"` resolves to `AmenityLabel.street_parking`, which
    `to_photoinsights_amenities_surface` folds into the `parking` surface, which
    `synthesis._amenities_from` emits as the literal tag `"parking"`, which
    `finance.engine._apply_insight_modifiers` reads by MEMBERSHIP to add $50/month/unit of other
    income. So the claim was one registration away from moving money, and no roll-up on that route
    has room for the caveat "we guessed this because the photo is wide".

    It was left in place once, when this slot was unreachable from `build_photo_insights`. That
    stopped being the whole story when the provider gained a declared capability list: declaring
    `"on-street parking"` would have made the fabrication *confirmable* by a matching file name and
    let it score. Removed rather than annotated, and the declaration below shrinks with it — a real
    classifier registered into this slot may of course emit `street_parking`; the ontology entry and
    the `_parking_summary` roll-up that consume it are untouched.

    Notes
    -----
    - This stub stands in for an LLM-based captioning model.
    - Provides deterministic, explainable outputs for integration tests.
    - Produces realistic structures compatible with `detect_from_image()` expectations.
    """
    description = _describe_image(img)
    lum = description["luminance"]
    spr = description["spread"]
    asp = description["aspect"]

    brightness = "bright" if lum >= 0.75 else ("dim" if lum < 0.35 else "normal")
    # `asp` still appears in the caption: it is a true statement about the image, and the caption is
    # the stub's evidence string. What was removed is the inference FROM it to a property claim.
    cap = f"Photo, {brightness} lighting, {asp} frame, spread={spr:.1f}"

    out: list[RawCandidate] = []
    if "bright" in cap:
        out.append({"name": "natural_light_high", "confidence": 0.70, "evidence": [cap], "rationale": "caption->bright"})

    if spr <= 12.0 and lum >= 0.45:
        out.append({"name": "stainless steel appliances", "confidence": 0.64, "evidence": [cap], "rationale": "caption->grayish"})

    return out


_PROVIDERS: dict[ProviderName, ProviderFn] = {
    "local": _provider_local,
    "vision": _provider_vision_stub,
    "llm": _provider_llm_stub,
}

# --- Built-in capability declarations ----------------------------------------
#
# Each entry is the EXHAUSTIVE vocabulary of the function above it -- every `out.append` in that
# function and nothing else. They are short because the stubs are: three hand-written thresholds
# over image statistics can look for light and for grey, and that is all. Writing the honest small
# set is the point. Declaring the full ontology here would tell every filename hint "a detector
# covers you and disagreed", which is the precise lie this declaration exists to prevent.
#
# tests/core/cv/test_filename_corroboration.py holds these to their functions: anything a stub
# actually emits must be declared, so a threshold added without updating its declaration fails.
# (The path in this comment used to name a file that does not exist -- corrected in Mission 2.)
_declare_capabilities(_provider_local, {"natural_light_high", MaterialTag.stainless_appliances.value})
_declare_capabilities(_provider_vision_stub, {"natural light", "stainless appliances"})
_declare_capabilities(_provider_llm_stub, {"natural_light_high", "stainless steel appliances"})

ProviderKind = Literal["heuristic_stub", "model"]

#: Every provider function defined in this module is a hand-written threshold over image
#: statistics, not a trained model. Anything bound into `_PROVIDERS` at runtime -- e.g. by
#: `register_onnx_provider`, or by a future fine-tuned ViT / hosted-API provider -- is a real
#: model. Membership is checked by identity against the *current* binding, so a slot that gets
#: overwritten reports "model" from that moment on without anyone remembering to update a list.
_BUILTIN_STUB_FNS: frozenset[ProviderFn] = frozenset({_provider_local, _provider_vision_stub, _provider_llm_stub})


def provider_kind(provider: ProviderName) -> ProviderKind:
    """Report whether the function currently bound to ``provider`` is a stub or a real model.

    Exists so that artifacts produced by a placeholder are identifiable as such and are never
    indistinguishable from a future real classifier's output. Raises ``ValueError`` for an
    unregistered provider, matching ``detect_from_image``.
    """
    fn = _PROVIDERS.get(provider)
    if fn is None:
        raise ValueError(f"Unknown provider: {provider}")
    return "heuristic_stub" if fn in _BUILTIN_STUB_FNS else "model"


# --- Normalization helpers ---------------------------------------------------


def _as_name_conf(candidate: RawCandidate) -> tuple[str | None, float, list[str] | None, str | None]:
    """
    Accepts either a raw string (label/synonym) or a dict with optional fields.
    Returns (raw_name_or_synonym, confidence, evidence, rationale).

    Defensive conversion ensures confidence is always a float in [0, 1],
    even if the source type is unexpected (e.g., string or None).
    """
    if isinstance(candidate, str):
        return candidate, 0.0, None, None  # confidence unknown at this stage

    if isinstance(candidate, dict):
        name = str(candidate.get("name") or "").strip() or None

        raw_conf = candidate.get("confidence", 0.0)
        if isinstance(raw_conf, (int | float)):
            conf = float(raw_conf)
        else:
            try:
                conf = float(str(raw_conf).strip()) if raw_conf is not None else 0.0
            except Exception:
                conf = 0.0

        evidence = candidate.get("evidence")
        if evidence is not None and not isinstance(evidence, list):
            evidence = None

        rationale_obj = candidate.get("rationale")
        rationale = str(rationale_obj) if rationale_obj is not None else None

        return name, conf, evidence, rationale

    return None, 0.0, None, None


def _normalize_candidates(
    candidates: Iterable[RawCandidate],
    ontology: Ontology,
) -> list[DetectedLabel]:
    """
    Map provider outputs to canonical ontology labels; drop OOD; merge dups by max confidence;
    and enforce per-label confidence cutoffs from the ontology.
    """
    best: dict[str, DetectedLabel] = {}

    for cand in candidates:
        raw_name, conf, evidence, rationale = _as_name_conf(cand)
        if not raw_name:
            continue
        meta = ontology.lookup(raw_name)
        if meta is None:
            # OOD → drop
            continue
        canon = meta["name"]
        # Merge by maximum confidence
        entry = best.get(canon)
        if entry is None or conf > entry.get("confidence", 0.0):
            best[canon] = DetectedLabel(
                name=canon,
                category=meta["category"],  # from ontology
                confidence=float(conf),
                evidence=evidence if evidence else None,
                rationale=rationale,
            )

    # Enforce per-label cutoffs (drop below cutoff)
    pruned: dict[str, DetectedLabel] = {}
    for canon, rec in best.items():
        cutoff = float(ontology.labels[canon]["confidence_cutoff"])
        if rec.get("confidence", 0.0) >= cutoff:
            pruned[canon] = rec

    # Stable alphabetical order
    return [pruned[k] for k in sorted(pruned.keys())]


# --- Public API --------------------------------------------------------------


def detect_from_image(
    img: Image.Image,
    *,
    provider: ProviderName,
    ontology: Ontology,
) -> list[DetectedLabel]:
    """
    Provider-agnostic gateway. Calls the selected provider, then normalizes to the closed set.
    """
    fn = _PROVIDERS.get(provider)
    if fn is None:
        raise ValueError(f"Unknown provider: {provider}")
    raw = fn(img)
    return _normalize_candidates(raw, ontology)
