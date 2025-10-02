# src/tools/listing_ingest.py
"""
Listing ingest tool (URL or local file) → normalized contracts + synthesized insights.

Pipeline (deterministic, offline-first by default):
  1) If URL is provided: core.fetch.fetch_html(policy) → cached HTML/DOM paths
  2) core.normalize.parse_any_to_normalized(path) → ListingNormalized
  3) core.cv.build_photo_insights(photo_dir, use_ai=...) → PhotoInsights
  4) core.insights.synthesize_listing_insights(listing, photos) → ListingInsights

This tool is the single integration point for agents/orchestrators and the CLI.
"""

from __future__ import annotations

from pathlib import Path

from src.core.cv import build_photo_insights
from src.core.fetch import fetch_html
from src.core.insights import synthesize_listing_insights
from src.core.normalize import parse_any_to_normalized
from src.schemas.models import FetchPolicy, IngestResult


def ingest_listing(
    *,
    url: str | None = None,
    file: Path | None = None,
    photos_dir: Path | None = None,
    policy: FetchPolicy | None = None,
    use_ai: bool = False,
) -> IngestResult:
    """
    Ingest a listing's artifacts and return durable models.

    Args:
        url: Optional URL to fetch (cache-first according to `policy`).
        file: Optional local file path (HTML/XML/TXT). Used if `url` is None.
        photos_dir: Optional directory of images for photo insights.
        policy: FetchPolicy controlling offline/robots/rendering behavior.
        use_ai: If True, request AI pass from the cv_tagging orchestrator.

    Returns:
        IngestResult(listing=ListingNormalized, photos=PhotoInsights, insights=ListingInsights)

    Raises:
        HtmlFetcherError and its subclasses for fetch errors (when url is provided).
        File I/O exceptions if `file` cannot be read.
    """
    if url:
        pol = policy or FetchPolicy()
        snap = fetch_html(url, policy=pol)
        # Prefer rendered tree if available, else raw tree, else raw html
        doc_path = snap.tree_path or snap.html_path
        listing = parse_any_to_normalized(doc_path)
        listing = listing.model_copy(update={"source_url": url})
    else:
        if not file:
            raise ValueError("Either `url` or `file` must be provided.")
        listing = parse_any_to_normalized(file)

    # Photo insights (safe defaults when no photos_dir)
    if photos_dir and photos_dir.exists():
        photos = build_photo_insights(photos_dir, use_ai=use_ai)
    else:
        photos = build_photo_insights(Path("__no_images__"), use_ai=use_ai)

    # Synthesize ListingInsights (guaranteed non-empty address)
    insights = synthesize_listing_insights(listing, photos)

    return IngestResult(listing=listing, photos=photos, insights=insights)
