from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image

from src.core.cv import runner as cv_runner


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def test_tag_images_keys_are_sha(tmp_path: Path):
    p = tmp_path / "kitchen_updated_dishwasher.jpg"
    Image.new("RGB", (16, 16), color=(245, 245, 245)).save(p)
    out = cv_runner.tag_images([p])
    assert set(out.keys()) == {_sha(p)}
    assert isinstance(next(iter(out.values())), list)


def test_tag_amenities_cache_layout(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AIREDEAL_CACHE_DIR", str(tmp_path / "cache"))
    p = tmp_path / "bright.png"
    Image.new("RGB", (96, 64), color=(245, 245, 245)).save(p)
    sha = _sha(p)
    res = cv_runner.tag_amenities_and_defects([p], provider="local", use_cache=True)
    assert sha in res
    cache_file = tmp_path / "cache" / "providers" / "local" / f"{sha}.json"
    assert cache_file.exists()
