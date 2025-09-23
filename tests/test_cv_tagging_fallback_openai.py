# tests/test_cv_tagging_fallback_openai.py
"""
cv_tagging fallback when OpenAI provider is selected but not configured.

Purpose
-------
- Selecting AIREAL_VISION_PROVIDER=openai without OPENAI_API_KEY should NOT
  break tagging; it should fall back to deterministic and issue a warning.
- No network calls are made.
"""

from src.tools.cv_tagging import tag_photos


def test_fallback_to_deterministic_when_openai_unconfigured(tmp_path, monkeypatch):
    # Select openai provider but remove key
    monkeypatch.setenv("AIREAL_VISION_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AIREAL_USE_VISION", raising=False)  # We'll pass use_ai=True explicitly

    img = tmp_path / "kitchen_island.jpg"
    img.write_text("stub")

    out = tag_photos([str(img)], use_ai=True)

    # Should produce results with a warning in rollup
    assert "rollup" in out
    assert any("Vision provider unavailable" in w for w in out["rollup"]["warnings"])

    # Schema sanity
    assert "images" in out and len(out["images"]) == 1
    tags = out["images"][0]["tags"]
    assert isinstance(tags, list)
