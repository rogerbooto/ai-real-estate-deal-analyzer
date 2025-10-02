# src/core/normalize/__init__.py
from __future__ import annotations

from pathlib import Path

from src.schemas.models import ListingNormalized

from .listing_html import parse_listing_from_tree
from .listing_text import parse_listing_from_text

PathLike = str | Path

__all__ = [
    "parse_listing_from_tree",
    "parse_listing_from_text",
    "parse_any_to_normalized",
]


def parse_any_to_normalized(doc: PathLike) -> ListingNormalized:
    """
    Convenience facade:
      - .html/.htm/.xml → parse_listing_from_tree
      - else           → parse_listing_from_text
    """
    p = Path(doc)
    if p.suffix.lower() in {".html", ".htm", ".xml"}:
        return parse_listing_from_tree(p)
    return parse_listing_from_text(p)
