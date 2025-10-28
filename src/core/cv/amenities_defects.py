# src/core/cv/amenities_defects.py
from __future__ import annotations

from collections.abc import Callable, Iterable
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

from .ontology import Ontology

ProviderName = Literal["local", "vision", "llm", "onnx"]
RawCandidate: TypeAlias = str | dict[str, object]
ProviderFn: TypeAlias = Callable[[Image.Image], Iterable[RawCandidate]]


class ImageDesc(TypedDict):
    luminance: float  # 0..1
    spread: float  # channel spread across mean RGB
    aspect: Literal["landscape", "portrait", "square"]


class DetectedLabel(TypedDict, total=False):
    """
    Normalized detection record, strictly within the closed-set ontology.
      - name: canonical label (snake_case)
      - category: "amenity" | "defect"  (from ontology)
      - confidence: float in [0,1]      (optional for early scaffolding)
      - evidence: list[str] | None
      - rationale: str | None
    """

    name: str
    category: Literal["amenity", "defect"]
    confidence: float
    evidence: list[str] | None
    rationale: str | None


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

    return _fn


def register_onnx_provider(
    model_path: str,
    labels_path: str,
    **kwargs: Any,
) -> None:
    """
    Runtime registration for provider='onnx'. Call once during app/CLI init.
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
    Deterministic *vision stub* provider used when no real computer-vision model is loaded.

    Purpose
    -------
    Simulates basic visual tagging behavior using simple image statistics
    (brightness, color spread, and aspect ratio) as low-cost proxies for
    higher-level semantic concepts such as lighting quality or materials.

    Method
    -------
    1. Calls `_describe_image(img)` to extract:
       • luminance (float, [0-1]) — average brightness
       • spread (float) — RGB channel variance proxy (low spread ≈ gray/metallic)
       • aspect ("landscape" | "portrait" | "square") — image orientation
    2. Generates heuristic tags based on thresholds:
       • High luminance (≥ 0.75) → `"natural light"` (proxy for well-lit room)
       • Medium luminance and low spread → `"stainless appliances"` (proxy for stainless steel kitchen)
       • Landscape + moderate brightness → `"street parking"` (proxy for exterior/driveway scenes)
    3. Returns a list of raw candidate detections with structure:
       {"name": str, "confidence": float, "rationale": str}

    Notes
    -----
    - This stub is *deterministic* and purely heuristic; it introduces no ML randomness.
    - Used during offline tests or deterministic CV runs to ensure consistent outputs.
    """
    description = _describe_image(img)
    lum = description["luminance"]
    spr = description["spread"]
    asp = description["aspect"]

    out: list[RawCandidate] = []

    # bright image → natural_light_high
    if lum >= 0.75:
        out.append({"name": "natural light", "confidence": 0.72, "rationale": "vision_stub: high luminance"})

    # gray-ish mid-high brightness → stainless_appliances proxy
    if 115.0 <= (lum * 255.0) <= 210.0 and spr <= 14.0:
        out.append({"name": "stainless appliances", "confidence": 0.66, "rationale": "vision_stub: low channel spread"})

    # landscape aspect → weak hint of outdoor/parking
    if asp == "landscape" and lum >= 0.50:
        out.append({"name": "street parking", "confidence": 0.62, "rationale": "vision_stub: landscape & bright"})

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
       • If landscape + luminance ≥ 0.55 → `"on-street parking"`
    4. Each output candidate includes:
       {
         "name": <ontology tag>,
         "confidence": float,
         "evidence": [<caption>],
         "rationale": "caption-><trigger>"
       }

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
    cap = f"Photo, {brightness} lighting, {asp} frame, spread={spr:.1f}"

    out: list[RawCandidate] = []
    if "bright" in cap:
        out.append({"name": "natural_light_high", "confidence": 0.70, "evidence": [cap], "rationale": "caption->bright"})

    if spr <= 12.0 and lum >= 0.45:
        out.append({"name": "stainless steel appliances", "confidence": 0.64, "evidence": [cap], "rationale": "caption->grayish"})

    if asp == "landscape" and lum >= 0.55:
        out.append({"name": "on-street parking", "confidence": 0.61, "evidence": [cap], "rationale": "caption->landscape"})

    return out


_PROVIDERS: dict[ProviderName, ProviderFn] = {
    "local": _provider_local,
    "vision": _provider_vision_stub,
    "llm": _provider_llm_stub,
}


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
