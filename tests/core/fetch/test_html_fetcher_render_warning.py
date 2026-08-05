# tests/core/fetch/test_html_fetcher_render_warning.py
"""
Regression test for the F8 "silent render swallow" defect.

Prior behaviour: when `FetchPolicy.render_js=True` (the `--render` CLI flag)
and the headless Playwright render failed for any reason, `fetch_html`
silently caught the exception, set `rendered_bytes = None`, and continued
with the unrendered (raw) HTML -- with *no* signal to the caller that the
requested render never happened.

Fix: `_warn_render_fallback()` emits a visible `RuntimeWarning` naming the
failure and stating that the run is falling back to the unrendered fetch.

This test uses only mock data (an in-memory fake HTTP response and a fake
Playwright renderer that always raises) -- no live network call is made and
no real URL is contacted.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.fetch import html_fetcher
from src.core.fetch.cache import cache_paths
from src.schemas.models import FetchPolicy

_FAKE_URL = "https://listing.example.invalid/123"  # RFC 2606 reserved TLD; never resolved (fully mocked)

# Enough visible text to pass the "looks like real content" heuristic
# (`min_body_text` default is 400 chars) without tripping the CAPTCHA/WAF regex.
_FAKE_BODY_HTML = (
    "<html><body><h1>Sample Listing</h1><p>" + ("Spacious family home with plenty of room to grow. " * 12) + "</p></body></html>"
).encode("utf-8")


def _policy(tmp_path: Path) -> FetchPolicy:
    return FetchPolicy(
        allow_network=True,
        allow_non_200=False,
        respect_robots=False,  # avoid a robots.txt fetch; not under test here
        timeout_s=5.0,
        user_agent="AI-REA/0.2 (+tests)",
        cache_dir=tmp_path / "cache",
        render_js=True,
        render_wait_s=0.0,
        render_wait_until="load",
        render_selector=None,
        save_screenshot=False,
        strict_dom=False,
    )


def test_render_failure_emits_visible_warning_and_falls_back_to_raw(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Non-CAPTCHA path (the charter-cited `html_fetcher.py:336-338` swallow):
    a plain 200 response, then Playwright raises -> must warn, not stay silent.
    """
    monkeypatch.setattr(html_fetcher, "_http_get", lambda url, ua, timeout: (200, _FAKE_BODY_HTML))

    def _boom(*args: object, **kwargs: object) -> str:
        raise RuntimeError("simulated Playwright launch failure (fixture)")

    monkeypatch.setattr(html_fetcher, "_render_page_with_playwright", _boom)

    pol = _policy(tmp_path)

    with pytest.warns(RuntimeWarning, match=r"--render requested but JS rendering failed"):
        snap = html_fetcher.fetch_html(_FAKE_URL, policy=pol)

    # Degrades, does not crash, and genuinely falls back to the RAW snapshot.
    paths = cache_paths(_FAKE_URL, pol.cache_dir)
    assert snap.html_path == paths["html_raw"]
    assert not paths["html_rendered"].exists()


def test_render_failure_in_captcha_branch_also_emits_warning(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Same defect class, reached via the WAF/CAPTCHA-detection branch
    (`html_fetcher.py` around line ~249) which attempts a render *before*
    deciding whether the raw response was actually a CAPTCHA/WAF shell.
    """
    monkeypatch.setattr(html_fetcher, "_http_get", lambda url, ua, timeout: (403, b"access denied"))

    def _boom(*args: object, **kwargs: object) -> str:
        raise RuntimeError("simulated Playwright launch failure (fixture)")

    monkeypatch.setattr(html_fetcher, "_render_page_with_playwright", _boom)

    pol = _policy(tmp_path)
    # allow_non_200: a 403 is how this branch's CAPTCHA/WAF heuristic gets triggered at all.
    # captcha_mode="off": don't raise on the unresolved CAPTCHA signal; just verify the warning fires.
    pol = pol.model_copy(update={"captcha_mode": "off", "allow_non_200": True})

    with pytest.warns(RuntimeWarning, match=r"--render requested but JS rendering failed"):
        html_fetcher.fetch_html(_FAKE_URL, policy=pol)
