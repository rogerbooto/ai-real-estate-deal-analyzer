# src/core/fetch/cache.py
"""
Deterministic on-disk cache layout for fetched HTML artifacts.
"""

from __future__ import annotations

from hashlib import sha256 as _sha256lib
from pathlib import Path


def _sha256(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8", errors="ignore")
    return _sha256lib(data).hexdigest()


def cache_paths(url: str, base_dir: Path) -> dict[str, Path]:
    """
    Build a stable cache directory based on sha256(url) prefix.

    Layout (under base/<hash16>/):
      - index.raw.html
      - tree.raw.html
      - index.rendered.html
      - tree.rendered.html
      - page.png
      - meta.json
    """
    h = _sha256(url)[:16]
    root = (base_dir / h).resolve()
    return {
        "root": root,
        "html_raw": root / "index.raw.html",
        "tree_raw": root / "tree.raw.html",
        "html_rendered": root / "index.rendered.html",
        "tree_rendered": root / "tree.rendered.html",
        "screenshot": root / "page.png",
        "meta": root / "meta.json",
    }
