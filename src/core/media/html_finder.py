# src/core/media/html_finder.py
"""
HTML-backed MediaFinder.

Scans a rendered or raw HTML snapshot for media references and returns
MediaFinderResult with MediaCandidates. This finder is conservative:
- It never downloads bytes.
- It only outputs normalized candidates (kind, url, source=html, hints).

Priority heuristics (highest first):
  1000: OpenGraph images (og:image)
   900: JSON-LD ImageObject(s)
   800: <img srcset> largest
   700: <img src>
   600: <source srcset> (e.g., <picture>)
   500: inline CSS background-image
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Iterator
from html import unescape
from pathlib import Path
from typing import cast
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.schemas.models import (
    HtmlSnapshot,
    MediaCandidate,
    MediaFinderResult,
    MediaKind,
    MediaSource,
)

# -----------------------
# Utilities
# -----------------------

_IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
_VIDEO_EXTS = {".mp4", ".webm", ".ogg", ".mov", ".m4v"}
_BG_URL_RE = re.compile(r"url\((['\"]?)(?P<u>[^)'\"]+)\1\)", re.IGNORECASE)
# Heuristic site blob for hints like hasphoto/photos: '39'
_REALTOR_BLOB_RE = re.compile(r"property\s*:\s*\{(?P<obj>[^}]+)\}", re.IGNORECASE | re.DOTALL)
_KV_RE = re.compile(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*('|\")?(.*?)\2?(?=,|\n|$)")


def _absolutize(u: str | None, base: str) -> str | None:
    if not u:
        return None
    return urljoin(base, u.strip())


def _guess_kind_from_ext(url: str) -> MediaKind:
    p = Path(url.split("?", 1)[0])
    sfx = p.suffix.lower()
    if sfx in _IMG_EXTS:
        return "image"
    if sfx in _VIDEO_EXTS:
        return "video"
    return "other"


def _dedupe_urls(urls: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _parse_srcset(srcset: str) -> list[str]:
    # Simple parse: split by comma, take URL part before size descriptor
    out: list[str] = []
    for part in srcset.split(","):
        url = part.strip().split(" ", 1)[0]
        if url:
            out.append(url)
    return out


def _json_safe_loads(s: str) -> object | None:
    try:
        return cast(object, json.loads(s))
    except Exception:
        return None


def _extract_realtor_photo_hints(html: str) -> tuple[bool, int | None]:
    """
    Looks for a block like:
      property: { hasphoto: 'yes', photos: '39', ... }
    Returns: (has_media_hint, photo_count_hint)
    """
    m = _REALTOR_BLOB_RE.search(html)
    if not m:
        return False, None

    blob = m.group("obj")
    kvs: dict[str, str] = {}
    for km in _KV_RE.finditer(blob):
        key, _q, val = km.group(1), km.group(2), km.group(3)
        kvs[key.lower()] = unescape(str(val)).strip()

    hasphoto = kvs.get("hasphoto", "").lower() in ("yes", "y", "true", "1")
    count = None
    photos_val = kvs.get("photos")
    if photos_val and photos_val.isdigit():
        count = int(photos_val)
    return hasphoto, count


# -----------------------
# Finder
# -----------------------


class HtmlMediaFinder:
    """
    Concrete MediaFinder for HTML. Read-only; returns pre-download candidates.
    """

    SOURCE: MediaSource = "html"

    def find(self, *, url: str, snapshot: HtmlSnapshot | None = None) -> MediaFinderResult:
        # Load HTML content
        html_text = ""
        if snapshot and snapshot.html_path and Path(snapshot.html_path).exists():
            html_text = Path(snapshot.html_path).read_text(encoding="utf-8", errors="ignore")

        has_media_hint, photo_count_hint = _extract_realtor_photo_hints(html_text)
        soup = BeautifulSoup(html_text or "", "html.parser")

        candidates: list[MediaCandidate] = []
        base_url = url

        # 1) OpenGraph images
        for meta in soup.find_all("meta", attrs={"property": "og:image"}):
            u = _absolutize(meta.get("content"), base_url)
            if u:
                candidates.append(
                    MediaCandidate(
                        url=u,
                        kind="image",
                        source=self.SOURCE,
                        mime_hint=None,
                        priority=1000.0,
                        attributes={"og": "image"},
                        referer_url=base_url,
                    )
                )

        # 2) JSON-LD (image / ImageObject)
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            data = _json_safe_loads(script.string or "")
            if not data:
                continue
            urls = self._image_urls_from_jsonld(data)
            for u in urls:
                au = _absolutize(u, base_url)
                if au:
                    candidates.append(
                        MediaCandidate(
                            url=au,
                            kind=_guess_kind_from_ext(au),
                            source=self.SOURCE,
                            priority=900.0,
                            attributes={"jsonld": "1"},
                            referer_url=base_url,
                        )
                    )

        # 3) <img srcset> (push all; downloader can filter)
        for img in soup.find_all("img"):
            # srcset
            srcset = img.get("srcset")
            if srcset:
                for u in _parse_srcset(srcset):
                    au = _absolutize(u, base_url)
                    if au:
                        candidates.append(
                            MediaCandidate(
                                url=au,
                                kind="image",
                                source=self.SOURCE,
                                priority=800.0,
                                alt_text=img.get("alt"),
                                referer_url=base_url,
                            )
                        )
            # fallback src
            src = img.get("src")
            if src:
                au = _absolutize(src, base_url)
                if au:
                    candidates.append(
                        MediaCandidate(
                            url=au,
                            kind="image",
                            source=self.SOURCE,
                            priority=700.0,
                            alt_text=img.get("alt"),
                            referer_url=base_url,
                        )
                    )

        # 4) <source> in <picture>/<video>
        for src in soup.find_all("source"):
            srcset = src.get("srcset")
            if srcset:
                for u in _parse_srcset(srcset):
                    au = _absolutize(u, base_url)
                    if au:
                        candidates.append(
                            MediaCandidate(
                                url=au,
                                kind=_guess_kind_from_ext(au),
                                source=self.SOURCE,
                                priority=600.0,
                                referer_url=base_url,
                            )
                        )
            s = src.get("src")
            if s:
                au = _absolutize(s, base_url)
                if au:
                    candidates.append(
                        MediaCandidate(
                            url=au,
                            kind=_guess_kind_from_ext(au),
                            source=self.SOURCE,
                            priority=600.0,
                            referer_url=base_url,
                        )
                    )

        # 5) background-image in inline style
        for el in soup.find_all(True, attrs={"style": True}):
            style = el.get("style") or ""
            for m in _BG_URL_RE.finditer(style):
                au = _absolutize(m.group("u"), base_url)
                if au:
                    candidates.append(
                        MediaCandidate(
                            url=au,
                            kind=_guess_kind_from_ext(au),
                            source=self.SOURCE,
                            priority=500.0,
                            referer_url=base_url,
                        )
                    )

        # Deduplicate by URL: keep the HIGHEST priority per URL
        best_by_url: dict[str, MediaCandidate] = {}
        for c in candidates:
            prev = best_by_url.get(c.url)
            if prev is None or c.priority > prev.priority:
                best_by_url[c.url] = c

        unique_candidates: set[MediaCandidate] = set(best_by_url.values())
        has_media = has_media_hint or bool(unique_candidates)

        return MediaFinderResult(
            has_media=has_media,
            photo_count_hint=photo_count_hint,
            candidates=unique_candidates,  # set
            notes=(["site_hint:hasphoto"] if has_media_hint else []),
        )

    # -------- JSON-LD helpers --------
    def _image_urls_from_jsonld(self, data: object) -> list[str]:
        out: list[str] = []
        for node in self._walk(data):
            if isinstance(node, dict):
                # image as string or list
                img = node.get("image")
                if isinstance(img, str):
                    out.append(img)
                elif isinstance(img, list):
                    out.extend([x for x in img if isinstance(x, str)])
                elif isinstance(img, dict):
                    u = img.get("url") or img.get("contentUrl")
                    if isinstance(u, str):
                        out.append(u)
                # ImageObject explicitly
                if node.get("@type") == "ImageObject":
                    u = node.get("url") or node.get("contentUrl")
                    if isinstance(u, str):
                        out.append(u)
        return _dedupe_urls(out)

    def _walk(self, obj: object) -> Iterator[object]:
        yield obj
        if isinstance(obj, dict):
            for v in obj.values():
                yield from self._walk(v)
        elif isinstance(obj, list):
            for v in obj:
                yield from self._walk(v)
