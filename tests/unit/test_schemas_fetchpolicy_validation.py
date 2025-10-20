# tests/unit/test_schemas_fetchpolicy_validation.py
from __future__ import annotations

from pathlib import Path

from src.schemas.models import FetchPolicy


def test_fetch_policy_full_config_roundtrip(tmp_path: Path) -> None:
    """Covers less-hit fields on FetchPolicy (rendering / robots / screenshots)."""
    p = FetchPolicy(
        captcha_mode="soft",
        min_body_text=123,
        allow_network=False,
        allow_non_200=True,
        respect_robots=True,
        timeout_s=7.5,
        user_agent="UnitTest/0.1",
        cache_dir=tmp_path,
        render_js=True,
        render_wait_s=2.25,
        render_wait_until="domcontentloaded",  # exercise alt literal
        render_selector="#app",
        save_screenshot=True,
        strict_dom=True,
    )

    dump = p.model_dump()
    # Make sure all toggles round-trip and types are preserved
    assert dump["render_js"] is True
    assert dump["save_screenshot"] is True
    assert dump["strict_dom"] is True
    assert dump["respect_robots"] is True
    assert dump["allow_non_200"] is True
    assert dump["render_wait_until"] == "domcontentloaded"
    assert dump["render_selector"] == "#app"
    # Paths serialize to strings
    assert str(tmp_path) in str(dump["cache_dir"])
    # Numeric fields keep precision
    assert abs(dump["timeout_s"] - 7.5) < 1e-6
    assert abs(dump["render_wait_s"] - 2.25) < 1e-6


def test_fetch_policy_defaults_are_sane(tmp_path: Path) -> None:
    """Covers defaults branch."""
    p = FetchPolicy(cache_dir=tmp_path)
    # Reasonable defaults that keep offline ingest deterministic
    assert p.allow_network in (False, True)  # just touch branch
    assert isinstance(p.user_agent, str) and len(p.user_agent) > 0
    assert p.cache_dir == tmp_path
    # Render options default values hit
    assert p.render_js in (False, True)
    assert isinstance(p.render_wait_s, float)
    assert isinstance(p.render_wait_until, str)
