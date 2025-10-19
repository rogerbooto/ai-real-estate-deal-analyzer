# tests/unit/test_cache_media_dir.py
from __future__ import annotations

from pathlib import Path

from src.core.fetch.cache import cache_paths


def test_cache_paths_creates_media_dir(tmp_path: Path) -> None:
    base_dir = tmp_path / "cache"
    url = "https://example.com/listing/123"

    paths = cache_paths(url, base_dir)

    # media_dir should be present and a directory
    assert "media_dir" in paths
    assert paths["media_dir"].exists()
    assert paths["media_dir"].is_dir()

    # root should exist; media_dir must be inside root
    assert paths["root"].exists()
    assert paths["media_dir"].parent == paths["root"]

    # deterministic: same URL -> same media_dir
    paths2 = cache_paths(url, base_dir)
    assert paths2["media_dir"] == paths["media_dir"]

    # different URL -> different media_dir
    paths_other = cache_paths("https://example.com/listing/456", base_dir)
    assert paths_other["media_dir"] != paths["media_dir"]
