# tests/unit/test_media_intelligence_basic.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from src.core.media.intelligence import (
    PaletteColor,
    compute_phash,
    extract_palette,
    hamming_distance_hex,
    load_bounded_thumbnail,
    rank_hero,
)


def test_load_bounded_thumbnail_and_phash(tmp_path: Path, make_gradient_img):
    p = tmp_path / "a.png"
    make_gradient_img(p, (1024, 768), delta=0)

    # Thumbnail should respect max_side and be RGB
    thumb = load_bounded_thumbnail(p, max_side=256)
    assert isinstance(thumb, Image.Image)
    assert max(thumb.size) <= 256
    assert thumb.mode == "RGB"

    # pHash should be deterministic for identical image
    h1 = compute_phash(p)
    h2 = compute_phash(p)
    assert isinstance(h1, str) and isinstance(h2, str)
    assert len(h1) == len(h2) and hamming_distance_hex(h1, h2) == 0

    p2 = tmp_path / "b.png"
    make_gradient_img(p2, (1024, 768), delta=3)

    # Nudge low frequencies: darken a small block so the DCT low band changes
    im = Image.open(p2).convert("RGB")
    draw = ImageDraw.Draw(im)
    draw.rectangle([0, 0, 200, 200], fill=(0, 0, 0))  # 201x201 block in top-left
    im.save(p2)

    h3 = compute_phash(p2)
    assert hamming_distance_hex(h1, h3) >= 1


def test_extract_palette_and_to_hex(tmp_path: Path):
    # Build a simple 2-color image, ensure palette returns k colors
    p = tmp_path / "palette.png"
    arr = np.zeros((40, 40, 3), dtype=np.uint8)
    arr[:20, :, :] = (255, 0, 0)  # red
    arr[20:, :, :] = (0, 0, 255)  # blue
    Image.fromarray(arr, mode="RGB").save(p, format="PNG")

    palette = extract_palette(p, k=3, thumb_side=64, max_iter=10)
    assert len(palette) == 3
    assert all(isinstance(c, PaletteColor) for c in palette)
    assert all(isinstance(c.to_hex(), str) and c.to_hex().startswith("#") for c in palette)


def test_rank_hero_scoring_and_tie_break(tmp_path: Path):
    @dataclass
    class DummyAsset:
        sha256: str
        path: Path
        width: int | None
        height: int | None

    a1 = DummyAsset("aaa", tmp_path / "a.png", 800, 600)
    a2 = DummyAsset("bbb", tmp_path / "b.png", 400, 300)
    a3 = DummyAsset("ccc", tmp_path / "c.png", 800, 600)

    # Signals: a1 and a3 same area; a1 gets higher sharpness, a3 marked duplicate penalty
    signals = {
        "aaa": {
            "size": (800, 600),
            "area": 800 * 600,
            "is_duplicate": False,
            "quality": {"sharpness": 10.0, "brightness": 120.0, "contrast": 30.0},
        },
        "bbb": {
            "size": (400, 300),
            "area": 400 * 300,
            "is_duplicate": False,
            "quality": {"sharpness": 5.0, "brightness": 100.0, "contrast": 20.0},
        },
        "ccc": {
            "size": (800, 600),
            "area": 800 * 600,
            "is_duplicate": True,  # duplicate penalty
            "quality": {"sharpness": 9.0, "brightness": 110.0, "contrast": 25.0},
        },
    }

    hero = rank_hero([a1, a2, a3], signals)
    assert hero is not None
    assert hero.sha256 == "aaa"
