# src/tools/vision/mock_provider.py
"""
Mock Vision Provider (V1)

Purpose
-------
Provide a deterministic, zero-dependency provider for the AI path that
returns plausible raw detections for known filename patterns. This lets us:
  - Enable the "vision" branch in tests and local dev without network.
  - Validate the ontology mapping, thresholding, and rollup logic end-to-end.
  - Keep CI stable and fast.

Design
------
- Pure string-pattern rules over the image *filename* (not pixels).
- Returns provider-native `RawTag` items aligned to our ontology.
- Confidence values are realistic but deterministic (e.g., 0.82, 0.9).
- Coverage focuses on kitchens/baths/exterior and common features.

Public API
----------
class MockVisionProvider(VisionProvider):
    def analyze(self, path: str) -> list[RawTag]

Notes
-----
- This provider *does not* read image bytes; it’s intentionally a stub.
- The real provider (OpenAI, etc.) can be swapped in without touching callers.

Usage
-----
from src.tools.vision.mock_provider import MockVisionProvider
prov = MockVisionProvider()
raw = prov.analyze("/path/to/kitchen_island_stainless.jpg")  # deterministic tags

Testing
-------
- Used by `tests/test_cv_tagging_ai_mock.py` to validate the AI path
  (mapping, thresholds, dedupe, rollup).
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from .provider_base import RawTag, VisionProvider


class MockVisionProvider(VisionProvider):
    """Deterministic, filename-based mock provider."""

    def analyze(self, path: str) -> List[RawTag]:
        name = Path(path).name.lower()
        out: List[RawTag] = []

        # --- Room type cues ---
        if any(k in name for k in ("kitchen", "ktn")):
            out.append(_rt("kitchen", 0.95, "sink, cabinets cues"))
        if any(b in name for b in ("bath", "bathroom", "bth")):
            out.append(_rt("bathroom", 0.94, "vanity, mirror cues"))
        if "bed" in name or "bedroom" in name:
            out.append(_rt("bedroom", 0.90, "bed frame visible"))
        if "living" in name:
            out.append(_rt("living_room", 0.88, "sofa, tv console"))
        if "exterior" in name or "front" in name or "curb" in name:
            out.append(_rt("exterior_front", 0.87, "façade view"))

        # --- Features ---
        if "island" in name:
            out.append(_ft("kitchen_island", 0.9, "central counter"))
        if "stainless" in name:
            out.append(_ft("stainless_appliances", 0.92, "steel range/fridge"))
        if "backsplash" in name or "tile" in name and "kitchen" in name:
            out.append(_ft("tile_backsplash", 0.82, "tiles behind counters"))
        if "dishwasher" in name:
            out.append(_ft("dishwasher", 0.85, "handle near sink"))
        if "recessed" in name or "canlight" in name:
            out.append(_ft("recessed_lighting", 0.8, "ceiling cans"))
        if "doublevanity" in name or "double_vanity" in name:
            out.append(_ft("double_vanity", 0.86, "two sinks"))

        # --- Conditions ---
        if "renovated" in name or "updated" in name:
            # Bias condition to the detected room if present, else generic well_maintained
            if any(t["label"] == "kitchen" and t["category"] == "room_type" for t in out):
                out.append(_cd("renovated_kitchen", 0.8, "modern finishes"))
            elif any(t["label"] == "bathroom" and t["category"] == "room_type" for t in out):
                out.append(_cd("updated_bath", 0.78, "new vanity/tiles"))
            else:
                out.append(_cd("well_maintained", 0.7, "clean finishes"))

        # --- Issues ---
        if "mold" in name:
            out.append(_is("mold_suspected", 0.6, "dark spots grout"))
        if "waterstain" in name or "water_stain" in name:
            out.append(_is("water_stain_ceiling", 0.62, "brown ring"))
        if "peeling" in name:
            out.append(_is("peeling_paint", 0.65, "flaking paint"))
        if "crackedtile" in name or "cracked_tile" in name:
            out.append(_is("cracked_tile", 0.6, "visible crack line"))

        return out


def _rt(label: str, conf: float, ev: str) -> RawTag:
    return {"label": label, "category": "room_type", "confidence": conf, "evidence": ev}


def _ft(label: str, conf: float, ev: str) -> RawTag:
    return {"label": label, "category": "feature", "confidence": conf, "evidence": ev}


def _cd(label: str, conf: float, ev: str) -> RawTag:
    return {"label": label, "category": "condition", "confidence": conf, "evidence": ev}


def _is(label: str, conf: float, ev: str) -> RawTag:
    return {"label": label, "category": "issue", "confidence": conf, "evidence": ev}
