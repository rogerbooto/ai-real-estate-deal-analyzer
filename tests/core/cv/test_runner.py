# tests/core/cv/test_runner.py
from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image

from src.core.cv import runner as cv_runner


def _sha256_of_path(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def test_tag_images_returns_per_sha_labels(tmp_path: Path, make_gradient_img):
    # Create two tiny images
    p1 = tmp_path / "a.png"
    p2 = tmp_path / "b.png"
    make_gradient_img(p1, (32, 24), delta=1)
    make_gradient_img(p2, (28, 28), delta=2)

    out = cv_runner.tag_images([p1, p2], use_ai=True)
    assert isinstance(out, dict)
    assert set(out.keys()) == {_sha256_of_path(p1), _sha256_of_path(p2)}
    # Each value is a list (empty for now; Step 9 will populate)
    assert all(isinstance(v, list) for v in out.values())


def test_cache_directory_layout(tmp_path: Path, monkeypatch):
    # Point cache to a temp dir so we can assert filesystem layout
    monkeypatch.setenv("AIREDEAL_CACHE_DIR", str(tmp_path / "cache"))

    # Build a bright, landscape image to trigger some stub detections
    img_path = tmp_path / "land.png"
    Image.new("RGB", (96, 64), color=(245, 245, 245)).save(img_path)

    sha = _sha256_of_path(img_path)
    # First run: should write a cache file
    res1 = cv_runner.tag_amenities_and_defects([img_path], provider="vision", use_cache=True)
    assert sha in res1
    cache_file = tmp_path / "cache" / "providers" / "vision" / f"{sha}.json"
    assert cache_file.exists(), "Expected provider cache file to be created"

    # Second run: should load from cache (behavioral: same output)
    res2 = cv_runner.tag_amenities_and_defects([img_path], provider="vision", use_cache=True)
    assert res1[sha] == res2[sha], "Cache read should reproduce identical results"
