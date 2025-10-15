# src/tools/__init__.py
"""
AI Real Estate Deal Analyzer — tools package

Purpose
-------
Provide a **stable facade** over the tools used by agents/orchestrators/tests.
This file is careful to:
  • Re-export the public, stable callables most people need.
  • Avoid hard failures when optional modules/providers aren’t installed.
  • Offer a small registry dict for easy agent/tool wiring.

Re-exports (when present)
-------------------------
- tag_photos                        : from .cv_tagging
- parse_listing_text                : from .listing_parser
- parse_listing_string              : from .listing_parser
- run_financial_model               : alias to .financial_model.run
- amortization (module)             : from .amortization  (contains helpers)

Optional (present if file exists in your tree)
----------------------------------------------
- run_listing_ingest_tool           : from .listing_ingest_tool
- listing_ingest (module)           : from .listing_ingest

Tip: use `get_tools_registry()` to register agent-callable functions.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeAlias

from src.schemas.models import FinancialForecast, FinancialInputs, ListingInsights, ListingNormalized, PhotoInsights

JSONDict: TypeAlias = dict[str, Any]

# Looser callables to avoid kw-only / param drift issues
tag_photos: Callable[..., JSONDict] | None = None
parse_listing_text: Callable[[str], ListingInsights] | None = None
parse_listing_string: Callable[[str], ListingInsights] | None = None
_financial_model: Any = None
run_financial_model: Callable[[FinancialInputs, ListingInsights | None, int], FinancialForecast] | None = None
amortization: Any = None
run_listing_ingest_tool: Callable[..., tuple[ListingNormalized, PhotoInsights]] | None = None
_listing_ingest_mod: Any = None

# --- Strict but safe imports (soft-fail to keep CLI/CI happy) ---

# CV tagging orchestrator
try:
    from .cv_tagging import tag_photos  # noqa: F401
except Exception:  # pragma: no cover
    tag_photos = None

# Simple listing text parser (legacy/simple path)
try:
    from .listing_parser import (  # noqa: F401
        parse_listing_string,
        parse_listing_text,
    )
except Exception:  # pragma: no cover
    parse_listing_text = None
    parse_listing_string = None

# Financial model: expose primary entrypoint under a clear alias
try:
    # Import module so advanced users can still reach internal helpers if needed.
    from . import financial_model as _financial_model  # noqa: F401

    run_financial_model = _financial_model.run
except Exception:  # pragma: no cover
    _financial_model = None
    run_financial_model = None

# Amortization helpers (module export; functions live inside)
try:
    from . import amortization  # noqa: F401
except Exception:  # pragma: no cover
    amortization = None

# Optional new ingest tool (only if present in your working tree)
try:
    from .listing_ingest import run_listing_ingest_tool  # noqa: F401
except Exception:  # pragma: no cover
    run_listing_ingest_tool = None

# Optional ingest module (expose module if available)
try:
    from . import listing_ingest as _listing_ingest_mod  # noqa: F401
except Exception:  # pragma: no cover
    _listing_ingest_mod = None


__all__ = [
    # Primary callables
    "tag_photos",
    "parse_listing_text",
    "parse_listing_string",
    "run_financial_model",
    "run_listing_ingest_tool",
    # Modules for power users
    "amortization",
    "_financial_model",
    "_listing_ingest_mod",
    # Registry helper
    "get_tools_registry",
]


def get_tools_registry() -> dict[str, object]:
    """
    Return a minimal registry of agent-callable tool functions.

    Keys (included only if available at runtime):
      - "listing_ingest"     → run_listing_ingest_tool(url|file, photos_dir, fetch_policy, use_ai)
      - "tag_photos"         → tag_photos(photo_paths, use_ai=?)
      - "parse_listing_text" → parse_listing_text(path)
      - "parse_listing_str"  → parse_listing_string(text)
      - "financial_model"    → run_financial_model(FinancialInputs)

    Example:
        from src.tools import get_tools_registry
        TOOLS = get_tools_registry()
        insights = TOOLS["listing_ingest"](url="...", photos_dir="...")

    This keeps agents/orchestrators decoupled from internal layout.
    """
    reg: dict[str, object] = {}

    if callable(run_listing_ingest_tool):
        reg["listing_ingest"] = run_listing_ingest_tool

    if callable(tag_photos):
        reg["tag_photos"] = tag_photos

    if callable(parse_listing_text):
        reg["parse_listing_text"] = parse_listing_text
    if callable(parse_listing_string):
        reg["parse_listing_str"] = parse_listing_string

    if callable(run_financial_model):
        reg["financial_model"] = run_financial_model

    return reg
