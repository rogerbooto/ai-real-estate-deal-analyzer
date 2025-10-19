# src/tools/vision/__init__.py
"""
Vision tools package

Re-exports the provider interfaces/implementations and the ontology helpers,
so callers can do:

    from src.tools.vision import (
        VisionProvider,
        MockProvider,
        OpenAIProvider,
        map_raw_tags,
        derive_amenities,
        in_ontology,
    )
"""

from __future__ import annotations

# Concrete providers
from .mock_provider import MockVisionProvider

# Ontology helpers
from .ontology import (
    derive_amenities,
    in_ontology,
    map_raw_tags,
)
from .openai_provider import OpenAIProvider

# Provider protocol / base
from .provider_base import VisionProvider

__all__ = [
    "VisionProvider",
    "MockVisionProvider",
    "OpenAIProvider",
    "in_ontology",
    "map_raw_tags",
    "derive_amenities",
]
