"""
src.core.cv
===========

Public entry points for the Computer Vision (CV) stack (v2).

Exports:
- Ontology + types: AMENITIES_DEFECTS_V1, Ontology, OntologyLabel
- Detection gateway: detect_from_image(), DetectedLabel, register_onnx_provider()
- Runner helpers: tag_images(), tag_amenities_and_defects()
- Photo insights builder: build_photo_insights()  (v2)
  (Optionally also exports build_photo_insights_v2 if present)
"""

from __future__ import annotations

# ---- Detection providers (local / vision / llm / onnx) ----
from .amenities_defects import DetectedLabel, detect_from_image, register_onnx_provider

# ---- Ontology (closed set) ----
from .ontology import AMENITIES_DEFECTS_V1, Ontology, OntologyLabel

# ---- Photo insights ----
from .photo_insights import build_photo_insights

# ---- Runner (batch helpers, caching by sha) ----
from .runner import tag_amenities_and_defects, tag_images

__all__ = [
    # Ontology
    "AMENITIES_DEFECTS_V1",
    "Ontology",
    "OntologyLabel",
    # Detection gateway
    "DetectedLabel",
    "detect_from_image",
    "register_onnx_provider",
    # Runner
    "tag_images",
    "tag_amenities_and_defects",
    # Photo insights
    "build_photo_insights",
]
