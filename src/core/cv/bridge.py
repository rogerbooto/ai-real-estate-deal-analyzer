# src/core/cv/bridge.py
"""
Thin bridge over the project CV tagging orchestrator.

We intentionally centralize the vision logic in `src/tools/cv_tagging` and call
its public API `tag_photos(photo_paths: list[str], *, use_ai: bool|None)` here.

This keeps a single source of truth for tagging/merging, while the core layer
just adapts the results to higher-level normalized contracts.
"""

from __future__ import annotations

from typing import Any

JSONDict = dict[str, Any]


def run_cv_tagging(photo_paths: list[str], *, use_ai: bool = False) -> JSONDict:
    """
    Invoke the project CV tagging orchestrator.

    Returns:
        Dict with keys:
          - "images": list[{ "image_id", "tags": [...], "derived_amenities": [...], ...}]
          - "rollup": { "amenities": [...], "condition_tags": [...], "defects": [...], "warnings": [...] }
    """
    try:
        # Single point of integration with the app's CV pipeline:
        from src.tools.cv_tagging import tag_photos
    except Exception as e:  # pragma: no cover - import errors exercised in integration tests
        # Fallback predictable shape
        return {
            "images": [],
            "rollup": {"amenities": [], "condition_tags": [], "defects": [], "warnings": [f"import_error:{type(e).__name__}"]},
        }

    out: JSONDict = tag_photos(photo_paths, use_ai=use_ai)
    # Ensure minimal keys exist
    out.setdefault("images", [])
    out.setdefault("rollup", {}).setdefault("amenities", [])
    out["rollup"].setdefault("condition_tags", [])
    out["rollup"].setdefault("defects", [])
    out["rollup"].setdefault("warnings", [])
    return out
