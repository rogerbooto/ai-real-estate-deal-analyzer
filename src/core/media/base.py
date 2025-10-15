# src/core/media/base.py
"""
Cross-layer contracts for media discovery and downloading.

This module defines:
- `MediaFinder` Protocol: how any media finder (HTML, MLS API, feeds, etc.)
  should expose discovery of media candidates.
- `download_media` public API signature: how callers request that candidates be
  persisted offline into the cache and receive `MediaAsset` records.

These contracts are the **single source of truth (SOT)** for media across layers.
Concrete implementations should live in separate modules (e.g.,
`html_finder.py`, `downloader.py`) and import these types.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from src.schemas.models import (
    HtmlSnapshot,
    MediaAsset,
    MediaCandidate,
    MediaFinderResult,
)


@runtime_checkable
class MediaFinder(Protocol):
    """
    Protocol for media discovery.

    Implementations should be pure (no network I/O) and operate on already-fetched
    artifacts (e.g., HtmlSnapshot) or lightweight page-level hints. They should
    *not* persist files; only return `MediaFinderResult` containing `MediaCandidate`s.

    Examples of implementers:
      - HtmlMediaFinder (parses DOM, JSON-LD, OpenGraph, site-specific blobs)
      - MlsApiMediaFinder (wraps an MLS/partner API)
      - FeedMediaFinder (reads a partner CSV/JSON feed)
    """

    def find(self, *, url: str, snapshot: HtmlSnapshot | None = None) -> MediaFinderResult:
        """
        Discover media candidates for a listing.

        Args:
            url:      The canonical page URL for the listing (used for provenance and resolving relative links).
            snapshot: Optional HTML snapshot with cached DOM/metadata. If None, the finder may still
                      emit candidates using lightweight signals (e.g., known URL patterns) but must not fetch.

        Returns:
            MediaFinderResult with flags (e.g., has_media, photo_count_hint) and a list of MediaCandidate items.
        """
        ...


def download_media(
    *,
    candidates: Sequence[MediaCandidate],
    dest_dir: Path,
    allow_network: bool,
    user_agent: str | None = None,
    timeout_s: float = 15.0,
    max_items: int | None = None,
) -> list[MediaAsset]:
    """
    Public API for downloading media candidates into an offline cache.

    This function is intentionally defined here (interface only) to stabilize
    the callsite contract. Provide the concrete implementation in a separate
    module (e.g., `src/core/media/downloader.py`) and re-export it if desired.

    Args:
        candidates:  Ordered set of MediaCandidate items (callers may pre-rank/filter).
        dest_dir:    Destination folder (e.g., cache_paths(url)["media_dir"]). Must exist.
        allow_network: If False, skip any candidate that is not already cached locally.
        user_agent:  Optional UA header for polite fetching.
        timeout_s:   Per-request timeout in seconds.
        max_items:   Optional cap on number of items to fetch (post-filter).

    Returns:
        A list of MediaAsset records representing the files persisted in `dest_dir`.

    Notes:
        - Implementations SHOULD dedupe by URL/hash and skip already-present files.
        - Implementations SHOULD populate `content_type`, `bytes_size`, `sha256`,
          and image dimensions when applicable.
        - Non-fatal issues should be recorded on each `MediaAsset.warnings`.
    """
    raise NotImplementedError("Interface-only declaration. Provide a concrete implementation (e.g., core/media/downloader.py).")


__all__ = [
    "MediaFinder",
    "download_media",
]
