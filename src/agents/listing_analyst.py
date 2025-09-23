# src/agents/listing_analyst.py
"""
Listing Analyst (V2)

Purpose
-------
Extract high-signal insights from local listing assets with the updated CV pipeline:
  - Parse the text file for address, amenities, and notes.
  - Tag property photos via the centralized CV orchestration entrypoint.
  - Merge results into a single ListingInsights object.

Design
------
- Pure Python, no network assumptions in this module.
- Uses the new CV Tagging Orchestrator which honors feature flags:
    * AIREAL_PHOTO_AGENT=1 → PhotoTaggerAgent (delegates to batch-aware cv_tagging)
    * AIREAL_USE_VISION=1  → AI path enabled (provider chosen by AIREAL_VISION_PROVIDER)
- Conservative merge: text-derived condition/defect tags remain optional; we map
  **photo-derived** signals into condition/defects while text contributes address,
  amenities, and notes. (Same behavior as V1 for consistency.)

Public API
----------
analyze_listing(listing_txt_path: str | None, photos_folder: str | None) -> ListingInsights

Migration Notes
---------------
- Replaces deprecated calls to `tag_images_in_folder` and `summarize_cv_tags`
  with the orchestrator’s strict-schema output.
- The orchestrator is the *single door* for CV tagging and handles AI/deterministic
  selection, batching, thresholds, ontology, and rollups.
"""

from __future__ import annotations

from src.orchestrators.cv_tagging_orchestrator import CvTaggingOrchestrator
from src.schemas.models import ListingInsights
from src.tools.listing_parser import parse_listing_string, parse_listing_text


def analyze_listing(
    listing_txt_path: str | None = None,
    photos_folder: str | None = None,
    *,
    fallback_text: str | None = None,
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
          deliberately forgiving so downstream agents can still operate.
    """
    # --- Text parsing ---
    text_insights = ListingInsights()
    try:
        if listing_txt_path:
            text_insights = parse_listing_text(listing_txt_path)
        elif fallback_text:
            text_insights = parse_listing_string(fallback_text)
    except Exception:
        # Defensive: never crash the pipeline due to a bad text file.
        text_insights = ListingInsights()

    # --- Photo tagging via orchestrator ---
    photo_condition: set[str] = set()
    photo_defects: set[str] = set()
    try:
        if photos_folder:
            cv = CvTaggingOrchestrator()
            cv_out = cv.analyze_folder(photos_folder, recursive=True)
            rollup = cv_out.get("rollup", {}) if isinstance(cv_out, dict) else {}
            photo_condition = set(rollup.get("condition_tags", []) or [])
            photo_defects = set(rollup.get("defects", []) or [])
    except Exception:
        # Defensive: never crash due to image folder issues.
        photo_condition = set()
        photo_defects = set()

    # --- Merge ---
    # Address, amenities, notes come from text. Condition/defects from photos.
    combined = ListingInsights(
        address=text_insights.address,
        amenities=sorted(set(text_insights.amenities)),
        condition_tags=sorted(photo_condition),
        defects=sorted(photo_defects),
        notes=sorted(set(text_insights.notes)),
    )
    return combined
