# src/core/media/pipeline.py
from __future__ import annotations

from pathlib import Path

from src.core.media.base import MediaFinder
from src.core.media.downloader import download_media
from src.core.media.html_finder import HtmlMediaFinder
from src.schemas.models import (
    FetchPolicy,
    HtmlSnapshot,
    MediaBundle,
    MediaCandidate,
    MediaKind,
)


def _pick_finders() -> list[MediaFinder]:
    # For now we only have the HTML finder. Later we can append MLS/API finders.
    return [HtmlMediaFinder()]


def find_media_candidates(
    *,
    url: str,
    snapshot: HtmlSnapshot | None,
) -> set[MediaCandidate]:
    """
    Fan out across all registered finders and merge unique candidates.
    Defensive: a bad finder should not break the ingest pipeline.
    """
    all_candidates: set[MediaCandidate] = set()

    for finder in _pick_finders():
        try:
            res = finder.find(url=url, snapshot=snapshot)
            all_candidates |= set(res.candidates)
        except Exception:
            continue  # skip bad finder, maintain robustness

    return all_candidates


def collect_media(
    *,
    url: str,
    snapshot: HtmlSnapshot | None,
    media_dir: Path,
    policy: FetchPolicy,
    allowed_kinds: set[MediaKind] | None = None,
    max_items: int = 64,
    referer: str | None = None,
    min_width: int | None = None,
    min_height: int | None = None,
    min_area: int | None = None,
    min_width_hint: int | None = None,
    min_height_hint: int | None = None,
    min_bytes_hint: int | None = None,
) -> MediaBundle:
    """
    High-level media pipeline:
      1) find candidates
      2) download (respecting FetchPolicy)
      3) return MediaBundle
    """
    candidates = find_media_candidates(url=url, snapshot=snapshot)
    assets = download_media(
        candidates=candidates,
        media_dir=media_dir,
        policy=policy,
        allowed_kinds=allowed_kinds,
        max_items=max_items,
        referer=referer or (snapshot.url if snapshot else None),
        min_width=min_width,
        min_height=min_height,
        min_area=min_area,
        min_width_hint=min_width_hint,
        min_height_hint=min_height_hint,
        min_bytes_hint=min_bytes_hint,
    )
    return MediaBundle(assets=assets, warnings=[])
