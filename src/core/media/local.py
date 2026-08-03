# src/core/media/local.py

"""
Build :class:`MediaAsset` records from a local folder of images.

The download pipeline (``src.core.media.downloader``) produces ``MediaAsset`` records from
remote URLs. The deterministic ``main.py`` path has no download step — it is handed a folder
of photos that already exist on disk — so ``analyze_media`` had no way to see them and the
report's Media Overview section was unreachable outside ``deal-report --media-insights``.

This module closes that gap: it walks a folder, probes each image, and emits the same
``MediaAsset`` shape the downloader produces.

Determinism
-----------
Files are visited in sorted path order and every reported value is content-derived (sha256,
byte size, pixel dimensions), so two runs over the same folder yield identical output. The
``created_at`` timestamp comes from the file's mtime — it is metadata the report never
renders, and using a real mtime is honest where a synthetic constant would not be.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from src.schemas.models import MediaAsset

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}

_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}

_CHUNK = 1 << 20  # 1 MiB


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(_CHUNK):
            h.update(chunk)
    return h.hexdigest()


def _dimensions(path: Path) -> tuple[int | None, int | None, list[str]]:
    """Return (width, height, warnings). Unreadable images are reported, never raised."""
    try:
        with Image.open(path) as im:
            w, h = im.size
        return int(w), int(h), []
    except (UnidentifiedImageError, OSError, ValueError):
        return None, None, [f"unreadable image: {path.name}"]


def collect_local_assets(folder: str | Path, *, recursive: bool = True) -> list[MediaAsset]:
    """
    Walk ``folder`` and return a ``MediaAsset`` per readable image, in sorted path order.

    A missing folder yields an empty list rather than raising: the photo folder is optional
    on every entry point that calls this, and a missing one must not kill an analysis run.
    """
    root = Path(folder)
    if not root.is_dir():
        return []

    paths = sorted(p for p in (root.rglob("*") if recursive else root.glob("*")) if p.is_file() and p.suffix.lower() in _IMAGE_EXTS)

    assets: list[MediaAsset] = []
    for p in paths:
        stat = p.stat()
        if stat.st_size == 0:
            # Zero-byte placeholders carry no signal and would skew size/dimension stats.
            continue
        width, height, warnings = _dimensions(p)
        assets.append(
            MediaAsset(
                local_path=p.resolve(),
                url=p.resolve().as_uri(),
                kind="image",
                source="manual",
                content_type=_CONTENT_TYPES.get(p.suffix.lower()),
                bytes_size=stat.st_size,
                sha256=_sha256(p),
                width=width,
                height=height,
                created_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                warnings=warnings,
            )
        )
    return assets
