# Tests: tests/core/media/test_intelligence.py

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from src.core.media.intelligence import compute_phash, compute_quality, extract_palette, hamming_distance_hex, rank_hero


def _make_img(path: Path, color: tuple[int, int, int], size=(256, 256)):
    img = Image.new("RGB", size, color)
    img.save(path)


def test_phash_similarity_thresholds(tmp_path: Path):
    p1 = tmp_path / "a.jpg"
    p2 = tmp_path / "b.jpg"
    _make_img(p1, (200, 180, 50))
    # slightly darker crop
    img = Image.open(p1)
    img = img.crop((16, 16, 240, 240)).resize((256, 256))
    img = Image.fromarray((np.asarray(img) * 0.98).astype(np.uint8))
    img.save(p2)

    h1 = compute_phash(p1)
    h2 = compute_phash(p2)
    dist = hamming_distance_hex(h1, h2)
    assert dist <= 10


def test_quality_metrics_nonnegative(tmp_path: Path):
    p = tmp_path / "q.jpg"
    _make_img(p, (128, 128, 128))
    q = compute_quality(p)
    assert set(q.keys()) == {"sharpness", "brightness", "contrast"}
    assert all(v >= 0 for v in q.values())


def test_palette_size_and_format(tmp_path: Path):
    p = tmp_path / "c.jpg"
    # draw two colors to avoid k identical centroids
    img = Image.new("RGB", (200, 200), (255, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([100, 0, 199, 199], fill=(0, 0, 255))
    img.save(p)
    pal = extract_palette(p, k=5)
    assert len(pal) == 5
    hexes = [c.to_hex() for c in pal]
    assert all(h.startswith("#") and len(h) == 7 for h in hexes)


def test_hero_selection_deterministic(tmp_path: Path):
    # create three images of different sizes
    paths = []
    sizes = [(200, 200), (300, 200), (400, 300)]
    for i, sz in enumerate(sizes):
        p = tmp_path / f"img{i}.jpg"
        Image.new("RGB", sz, (10 + i * 20, 100, 150)).save(p)
        paths.append(p)

    class A:
        def __init__(self, path):
            self.path = path
            self.sha256 = path.stem  # fake stable id for test
            self.width, self.height = Image.open(path).size

    assets = [A(p) for p in paths]
    signals = {}
    for a in assets:
        q = compute_quality(a.path)
        area = a.width * a.height
        signals[a.sha256] = {"size": (a.width, a.height), "area": area, "is_duplicate": False, "quality": q}

    h1 = rank_hero(assets, signals)
    h2 = rank_hero(assets, signals)
    assert h1 is not None and h2 is not None
    assert h1.sha256 == h2.sha256  # deterministic
