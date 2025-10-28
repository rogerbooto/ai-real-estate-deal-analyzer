# src/tools/__init__.py
"""
AI Real Estate Deal Analyzer — tools package

Exports only modules that live under `src/tools`:
  - parse_listing_text/str     (from .listing_parser)
  - run_listing_ingest_tool    (from .listing_ingest, if present)
  - vision (subpackage)        (from .vision)

Anything outside `src/tools` (e.g., core finance) should be imported directly
from its own package, not re-exported here.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeAlias

from src.schemas.models import ListingInsights, ListingNormalized, PhotoInsights

JSONDict: TypeAlias = dict[str, Any]

# Optional exports default to None if unavailable so the package can be imported
# even when optional dependencies/providers aren’t installed.
parse_listing_text: Callable[[str], ListingInsights] | None = None
parse_listing_string: Callable[[str], ListingInsights] | None = None
run_listing_ingest_tool: Callable[..., tuple[ListingNormalized, PhotoInsights]] | None = None

# --- Soft imports for tools that live in this folder ---


# Listing text parser
try:  # pragma: no cover
    from .listing_parser import (
        parse_listing_string,
        parse_listing_text,
    )
except Exception:  # pragma: no cover
    parse_listing_text = None
    parse_listing_string = None

# Optional ingest tool
try:  # pragma: no cover
    from .listing_ingest import run_listing_ingest_tool
except Exception:  # pragma: no cover
    run_listing_ingest_tool = None

__all__ = ["parse_listing_text", "parse_listing_string", "run_listing_ingest_tool"]
