# tests/ai/test_ai_runner_roundtrip.py
from __future__ import annotations

from pathlib import Path

from PIL import Image

from src.core.cv import runner as cv_runner


def test_roundtrip_generic_and_ai_share_keys(tmp_path: Path):
    p = tmp_path / "kitchen_photo.png"
    Image.new("RGB", (64, 64), color=(240, 240, 240)).save(p)

    # Generic labels (v2 deterministic)
    generic = cv_runner.tag_images([p])
    assert isinstance(generic, dict) and generic

    # Amenities/defects via vision stub
    dets = cv_runner.tag_amenities_and_defects([p], provider="vision", use_cache=False)
    assert isinstance(dets, dict) and dets

    # Keys (sha256) must match for the same asset
    assert set(generic.keys()) == set(dets.keys())
