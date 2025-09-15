# src/agents/listing_analyst.py
"""
Listing Analyst (V1)

Purpose
-------
Deterministically extract high-signal insights from the local listing assets:
  - Parse the text file for address, amenities, and notes.
  - Tag property photos using the CV tagging stub.
  - Merge results into a single ListingInsights object.

Design
------
- Pure Python, no network calls, fully testable.
- Accepts paths so it can be used by CLI/main.py and by agents/orchestrator later.
- Conservative merge: text-derived condition/defect tags are optional; in V1 we only
  map photo-derived tags into condition/defects, while text contributes address,
  amenities, and notes.

Public API
----------
analyze_listing(listing_txt_path: str | None, photos_folder: str | None) -> ListingInsights
"""

from __future__ import annotations

from typing import Optional, Set

from src.schemas.models import ListingInsights
from src.tools.listing_parser import parse_listing_text, parse_listing_string
from src.tools.cv_tagging import tag_images_in_folder, summarize_cv_tags


def analyze_listing(
    listing_txt_path: Optional[str] = None,
    photos_folder: Optional[str] = None,
    *,
    fallback_text: Optional[str] = None,
) -> ListingInsights:
    """
    Build a ListingInsights object from local assets.

    Args:
        listing_txt_path: Path to a .txt file with listing description (optional).
        photos_folder: Path to a folder with property images (optional).
        fallback_text: If listing_txt_path is None, use this raw text string instead.

    Returns:
        ListingInsights with:
          - address / amenities / notes from text (if available)
          - condition_tags / defects aggregated from photo tags (if available)

    Behavior:
        - If a source is missing, fields gracefully default to empty.
        - No exceptions are raised for missing files or folders; this agent is
          deliberately forgiving in V1 so downstream agents can still operate.
    """
    # --- Text parsing ---
    text_insights = ListingInsights()
    try:
        if listing_txt_path:
            text_insights = parse_listing_text(listing_txt_path)
        elif fallback_text:
            text_insights = parse_listing_string(fallback_text)
    except Exception:
        # Defensive: never crash the pipeline due to a bad text file in V1.
        text_insights = ListingInsights()

    # --- Photo tagging ---
    photo_condition: Set[str] = set()
    photo_defects: Set[str] = set()
    try:
        if photos_folder:
            tags_by_file = tag_images_in_folder(photos_folder)
            agg = summarize_cv_tags(tags_by_file)
            photo_condition = agg["condition_tags"]
            photo_defects = agg["defects"]
    except Exception:
        # Defensive: never crash due to image folder issues.
        photo_condition = set()
        photo_defects = set()

    # --- Merge ---
    # Address, amenities, notes come from text. Condition/defects from photos (V1).
    combined = ListingInsights(
        address=text_insights.address,
        amenities=sorted(set(text_insights.amenities)),
        condition_tags=sorted(photo_condition),
        defects=sorted(photo_defects),
        notes=sorted(set(text_insights.notes)),
    )
    return combined
