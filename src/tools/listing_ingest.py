# src/tools/listing_ingest.py
"""
Listing ingest tool (URL or local file) → normalized contracts + synthesized insights.

Pipeline (deterministic, offline-first by default):
  1) If URL is provided: core.fetch.fetch_html(policy) → cached HTML/DOM paths
  2) core.normalize.parse_any_to_normalized(path) → ListingNormalized
  3) (optional) Discover & download media to cache/<hash>/media
  4) core.cv.build_photo_insights(photo_dir or media_dir, use_ai=...) → PhotoInsights
  5) core.insights.synthesize_listing_insights(listing, photos) → ListingInsights

This tool is the single integration point for agents/orchestrators and the CLI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.core.cv.photo_insights import build_photo_insights
from src.core.fetch import fetch_html
from src.core.fetch.cache import cache_paths
from src.core.insights import synthesize_listing_insights
from src.core.media.insights import analyze_media
from src.core.media.pipeline import collect_media
from src.core.normalize import parse_any_to_normalized
from src.schemas.models import (
    FetchPolicy,
    IngestResult,
    ListingInsights,
    ListingNormalized,
    MediaBundle,
    MediaInsights,
    MediaKind,
    PhotoInsights,
)


def ingest_listing(
    *,
    url: str | None = None,
    file: Path | None = None,
    photos_dir: Path | None = None,
    policy: FetchPolicy | None = None,
    use_ai: bool = False,
    download_media: bool = True,
    media_max_items: int = 64,
    media_kinds: set[MediaKind] | None = None,  # <- set (matches collect_media)
) -> IngestResult:
    """
    Ingest a listing's artifacts and return durable models.
    """
    if not url and not file:
        raise ValueError("Either `url` or `file` must be provided.")

    pol = policy or FetchPolicy()

    snapshot = None
    listing: ListingNormalized

    if url:
        # Fetch (offline-first by policy), then parse normalized facts
        snapshot = fetch_html(url, policy=pol)
        doc_path = snapshot.tree_path or snapshot.html_path
        listing = parse_any_to_normalized(doc_path).model_copy(update={"source_url": url})
    else:
        assert file is not None
        listing = parse_any_to_normalized(file)

    # Media: discover & download to cache/<hash>/media
    cache_root = cache_paths(url or str(file), pol.cache_dir)
    media_bundle: MediaBundle = MediaBundle()
    if download_media:
        media_bundle = collect_media(
            url=listing.source_url or (url or ""),
            snapshot=snapshot,
            media_dir=cache_root["media_dir"],
            policy=pol,
            allowed_kinds=media_kinds,  # already a set or None
            max_items=media_max_items,
            referer=listing.source_url or url,
            min_width=150,  # skip tiny images
            min_height=150,  # skip tiny images
            min_width_hint=150,  # prefer at least 150px wide if available
            min_height_hint=150,  # prefer at least 150px high if available
        )

    # Photo insights: prefer explicit photos_dir, else use downloaded images if any
    photos_path = photos_dir
    if photos_path is None and any(a.kind == "image" for a in media_bundle.assets):
        photos_path = cache_root["media_dir"]

    if photos_path is not None:
        photos = build_photo_insights(photos_path, use_ai=use_ai)
    else:
        photos = build_photo_insights(Path("__no_images__"), use_ai=use_ai)

    insights: ListingInsights = synthesize_listing_insights(listing, photos)

    media_insights: MediaInsights | None = analyze_media(media_bundle.assets) if media_bundle.assets else None

    return IngestResult(listing=listing, photos=photos, insights=insights, media=media_bundle, media_insights=media_insights)


# ---------------------------
# Agent-facing wrapper
# ---------------------------


def _policy_from_dict(d: dict[str, Any] | FetchPolicy | None) -> FetchPolicy:
    """
    Normalize an incoming policy that may be:
      - a FetchPolicy instance,
      - a plain dict of policy fields,
      - or None (use defaults).
    """
    if isinstance(d, FetchPolicy):
        return d
    if not d:
        return FetchPolicy()

    return FetchPolicy(
        captcha_mode=d.get("captcha_mode", "soft"),
        min_body_text=int(d.get("min_body_text", 400)),
        allow_network=bool(d.get("allow_network", False)),
        allow_non_200=bool(d.get("allow_non_200", False)),
        respect_robots=bool(d.get("respect_robots", True)),
        timeout_s=float(d.get("timeout_s", 15.0)),
        user_agent=str(d.get("user_agent", "AI-REA/0.2 (+deterministic-ingest)")),
        cache_dir=Path(d.get("cache_dir", "data/raw")),
        render_js=bool(d.get("render_js", False)),
        render_wait_s=float(d.get("render_wait_s", 9.0)),
        render_wait_until=str(d.get("render_wait_until", "networkidle")),
        render_selector=(str(d["render_selector"]) if d.get("render_selector") else None),
        save_screenshot=bool(d.get("save_screenshot", False)),
        strict_dom=bool(d.get("strict_dom", False)),
    )


def run_listing_ingest_tool(
    *,
    url: str | None = None,
    file: str | None = None,
    photos_dir: str | None = None,
    fetch_policy: dict[str, Any] | FetchPolicy | None = None,
    use_ai: bool = False,
) -> tuple[ListingNormalized, PhotoInsights]:
    """
    Agent-callable ingestion entrypoint.
    Returns the typed models (callers can .model_dump() for dicts if needed).
    """
    pol = _policy_from_dict(fetch_policy)
    result = ingest_listing(
        url=url,
        file=Path(file) if file else None,
        photos_dir=Path(photos_dir) if photos_dir else None,
        policy=pol,
        use_ai=use_ai,
        # agent path uses defaults for media flags; CLI exposes them explicitly
    )
    return result.listing, result.photos
