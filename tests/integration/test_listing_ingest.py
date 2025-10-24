# tests/integration/test_listing_ingest.py

from __future__ import annotations

from pathlib import Path

from src.schemas.models import FetchPolicy
from src.tools.listing_ingest import ingest_listing


def _write_html(tmp_path: Path, html: str = None) -> Path:
    body = (
        html
        or """<!doctype html>
<html>
  <head><title>Test Listing</title></head>
  <body>
    <h1>Unit</h1>
    <img src="/a.jpg" alt="front">
    <a href="/doc.pdf">Download</a>
  </body>
</html>
"""
    )
    p = tmp_path / "listing.html"
    p.write_text(body, encoding="utf-8")
    return p


def _offline_policy(tmp_path: Path) -> FetchPolicy:
    return FetchPolicy(
        allow_network=False,
        allow_non_200=False,
        respect_robots=True,
        timeout_s=5.0,
        user_agent="AI-REA/0.2 (+tests)",
        cache_dir=tmp_path / "cache",
        render_js=False,
        render_wait_s=0.0,
        render_wait_until="load",
        render_selector=None,
        save_screenshot=False,
        strict_dom=False,
    )


def test_ingest_from_html_file_offline_no_download(tmp_path: Path):
    """Ingest from a local HTML file without downloading media."""
    html_file = _write_html(tmp_path)
    policy = _offline_policy(tmp_path)

    result = ingest_listing(
        url=None,
        file=html_file,
        photos_dir=None,
        policy=policy,
        use_ai=False,
        download_media=False,
        media_max_items=16,
        media_kinds=None,
        media_intel=False,
    )

    # Basic listing normalization should populate title
    assert result.listing is not None
    assert (result.listing.title or "").lower().strip() == "test listing"

    # When download_media is off, no assets are stored
    assert len(result.media.assets) == 0
    # No media insights computed without assets
    assert result.media_insights is None


def test_ingest_from_html_file_with_kinds_filter_offline(tmp_path: Path):
    """Ingest with a media kinds filter; still offline and no download."""
    html_file = _write_html(tmp_path)
    policy = _offline_policy(tmp_path)

    result = ingest_listing(
        url=None,
        file=html_file,
        photos_dir=None,
        policy=policy,
        use_ai=False,
        download_media=False,
        media_max_items=4,
        media_kinds={"image", "document"},  # ensure parser accepts filter param
        media_intel=False,
    )

    # Again, no downloads in offline mode + download_media=False
    assert len(result.media.assets) == 0
    # Listing still parsed
    assert (result.listing.title or "").lower().strip() == "test listing"
