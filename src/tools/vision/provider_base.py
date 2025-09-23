# src/tools/vision/provider_base.py
"""
Vision Provider Interface (V1.1) — Adds batch analysis helper

Purpose
-------
Define a minimal, provider-agnostic contract for image analysis and provide a
standard helper to run providers in batch. If a provider implements a native
`analyze_batch`, we use it. Otherwise we gracefully fall back to per-image calls.

Design
------
- Protocol `VisionProvider` keeps single-image `analyze(path)`.
- Optional duck-typed `analyze_batch(paths)` is supported if present.
- Public helper `run_batch(provider, paths)` guarantees stable output shape.

Public API
----------
class VisionProvider(Protocol):
    def analyze(self, path: str) -> list[RawTag]
    # Optional (duck-typed):
    # def analyze_batch(self, paths: list[str]) -> list[list[RawTag]]

def run_batch(provider: VisionProvider, paths: list[str]) -> list[list[RawTag]]

Invariants & Guardrails
-----------------------
- Output of `run_batch` aligns 1:1 with `paths` order.
- No best-effort reordering; callers rely on positional mapping.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, Protocol, TypedDict

Category = Literal["room_type", "feature", "condition", "issue"]


class RawTag(TypedDict, total=False):
    label: str
    category: Category
    confidence: float
    evidence: str
    bbox: list[int]


class VisionProvider(Protocol):
    def analyze(self, path: str) -> list[RawTag]: ...

    # NOTE: Providers may optionally implement this for efficiency.
    # def analyze_batch(self, paths: List[str]) -> List[List[RawTag]]:
    #     ...


def run_batch(provider: VisionProvider, paths: Sequence[str]) -> list[list[RawTag]]:
    """
    Execute analysis for a batch of images, preserving input order.
    If provider exposes `analyze_batch`, use it; otherwise loop over `analyze`.
    """
    # Try native batch if present (duck typing)
    analyze_batch = getattr(provider, "analyze_batch", None)
    if callable(analyze_batch):
        out = analyze_batch(list(paths))  # type: ignore[misc]
        # Validate shape: list[list[RawTag]] with same length
        if not isinstance(out, list) or len(out) != len(paths):
            raise ValueError("Provider analyze_batch returned invalid shape.")
        return out
    # Fallback: per-image calls
    return [provider.analyze(p) for p in paths]
