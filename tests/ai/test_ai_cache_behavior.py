# tests/ai/test_ai_cache_behavior.py
from __future__ import annotations

from pathlib import Path

from PIL import Image

from src.core.cv import amenities_defects as mod, runner as cv_runner


def test_cache_hits_reduce_calls(tmp_path: Path, monkeypatch):
    # Route cache to temp dir
    monkeypatch.setenv("AIREDEAL_CACHE_DIR", str(tmp_path / "cache"))

    # Make an image
    p = tmp_path / "land.png"
    Image.new("RGB", (96, 64), color=(245, 245, 245)).save(p)

    # Counting fake provider for "vision"
    calls = {"n": 0}

    def fake_vision(_img):
        calls["n"] += 1
        return [{"name": "garage", "confidence": 0.80}]

    monkeypatch.setitem(mod._PROVIDERS, "vision", fake_vision)

    # First call should invoke provider and create cache
    r1 = cv_runner.tag_amenities_and_defects([p], provider="vision", use_cache=True)
    assert calls["n"] == 1
    assert r1

    # Second call should load from cache; no additional provider call
    r2 = cv_runner.tag_amenities_and_defects([p], provider="vision", use_cache=True)
    assert calls["n"] == 1
    assert r2 == r1
