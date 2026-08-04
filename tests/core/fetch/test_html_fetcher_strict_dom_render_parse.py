# tests/core/fetch/test_html_fetcher_strict_dom_render_parse.py
"""
Regression tests for the M5 "strict_dom silently bypassed" defect.

Prior behaviour: `fetch_html`'s render path nested the strict-mode
`raise InvalidHtmlError(...)` (triggered when a rendered page's DOM failed to
parse) *inside* the same `try` block whose `except Exception` swallows render
failures and falls back to raw HTML. The outer `except` caught the deliberate
`InvalidHtmlError` too, so a caller who set `strict_dom=True` never actually
got the strict failure the flag promises -- it silently degraded to a warning
plus the unrendered snapshot instead, disagreeing with the RAW-path
equivalent (which is not nested, and does propagate).

This defect existed at *two* call sites in `src/core/fetch/html_fetcher.py`:
  - the CAPTCHA/WAF-detection branch (tries a render before deciding whether
    the raw response was actually a CAPTCHA/WAF shell)
  - the "normal" render path (render_js requested outside of any CAPTCHA
    signal)

Fix: `_render_and_parse()` separates the two independent failure domains
(the render itself failing vs. the resulting HTML failing to parse) with a
`try/except/else`, so a strict-mode parse failure raises `InvalidHtmlError`
that is never caught by the render-failure handler, at either call site.

All fixtures are in-memory (fake HTTP response, fake Playwright renderer,
and -- for the "parse failure" tests -- a `BeautifulSoup` stand-in that
raises only for the specific rendered-HTML string under test). No live
network call is made and no real URL is contacted (RFC 2606 `.invalid` TLD).
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import pytest
from bs4 import BeautifulSoup as _RealBeautifulSoup

from src.core.fetch import html_fetcher
from src.core.fetch.cache import cache_paths
from src.core.fetch.errors import InvalidHtmlError
from src.schemas.models import FetchPolicy

_FAKE_URL = "https://listing.example.invalid/456"  # RFC 2606 reserved TLD; never resolved (fully mocked)

# Enough visible text to pass the "looks like real content" heuristic
# (`min_body_text` default is 400 chars) without tripping the CAPTCHA/WAF regex.
_FAKE_BODY_HTML = (
    "<html><body><h1>Sample Listing</h1><p>" + ("Spacious family home with plenty of room to grow. " * 12) + "</p></body></html>"
).encode("utf-8")

_FAKE_RENDERED_HTML = "<html><body><h1>Rendered Listing</h1><p>" + ("JS-rendered content goes here. " * 12) + "</p></body></html>"


def _policy(tmp_path: Path, *, strict_dom: bool, captcha_mode: str = "off") -> FetchPolicy:
    return FetchPolicy(
        allow_network=True,
        allow_non_200=True,
        respect_robots=False,  # avoid a robots.txt fetch; not under test here
        timeout_s=5.0,
        user_agent="AI-REA/0.2 (+tests)",
        cache_dir=tmp_path / "cache",
        render_js=True,
        render_wait_s=0.0,
        render_wait_until="load",
        render_selector=None,
        save_screenshot=False,
        strict_dom=strict_dom,
        captcha_mode=captcha_mode,  # type: ignore[arg-type]
    )


def _soup_that_booms_for_rendered_html(*args: Any, **kwargs: Any) -> Any:
    """
    Drop-in replacement for `bs4.BeautifulSoup` that raises when asked to
    parse `_FAKE_RENDERED_HTML` (simulating a DOM-parse failure of the
    *rendered* page) but parses everything else (e.g. the RAW response body)
    normally, via the real BeautifulSoup.
    """
    markup = args[0] if args else kwargs.get("markup")
    if markup == _FAKE_RENDERED_HTML:
        raise ValueError("simulated lxml parse failure of rendered DOM (fixture)")
    return _RealBeautifulSoup(*args, **kwargs)


def _render_ok(*args: object, **kwargs: object) -> str:
    return _FAKE_RENDERED_HTML


def _render_boom(*args: object, **kwargs: object) -> str:
    raise RuntimeError("simulated Playwright launch failure (fixture)")


# ---------------------------------------------------------------------------
# Behaviour 1: strict_dom=True + rendered-DOM parse failure -> raises,
# and does NOT emit the "falling back" warning (no silent degrade).
# ---------------------------------------------------------------------------


def test_strict_dom_raises_on_rendered_parse_failure_normal_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Normal (non-CAPTCHA) render path: strict_dom=True must actually raise."""
    monkeypatch.setattr(html_fetcher, "_http_get", lambda url, ua, timeout: (200, _FAKE_BODY_HTML))
    monkeypatch.setattr(html_fetcher, "_render_page_with_playwright", _render_ok)
    monkeypatch.setattr(html_fetcher, "BeautifulSoup", _soup_that_booms_for_rendered_html)

    pol = _policy(tmp_path, strict_dom=True)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(InvalidHtmlError, match="Failed to parse/pretty RENDERED HTML"):
            html_fetcher.fetch_html(_FAKE_URL, policy=pol)

    fallback_warnings = [w for w in caught if issubclass(w.category, RuntimeWarning) and "falling back" in str(w.message)]
    assert not fallback_warnings, f"strict_dom=True must not also emit the graceful-degradation warning; got {fallback_warnings}"


def test_strict_dom_raises_on_rendered_parse_failure_captcha_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CAPTCHA/WAF-detection render path: strict_dom=True must actually raise."""
    monkeypatch.setattr(html_fetcher, "_http_get", lambda url, ua, timeout: (403, b"access denied"))
    monkeypatch.setattr(html_fetcher, "_render_page_with_playwright", _render_ok)
    monkeypatch.setattr(html_fetcher, "BeautifulSoup", _soup_that_booms_for_rendered_html)

    pol = _policy(tmp_path, strict_dom=True, captcha_mode="off")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(InvalidHtmlError, match="Failed to parse/pretty RENDERED HTML"):
            html_fetcher.fetch_html(_FAKE_URL, policy=pol)

    fallback_warnings = [w for w in caught if issubclass(w.category, RuntimeWarning) and "falling back" in str(w.message)]
    assert not fallback_warnings, f"strict_dom=True must not also emit the graceful-degradation warning; got {fallback_warnings}"


# ---------------------------------------------------------------------------
# Behaviour 2: strict_dom=False + the SAME rendered-DOM parse failure ->
# warns (accurately -- parse failed, not "JS rendering") and falls back to
# the raw snapshot. Never raises.
# ---------------------------------------------------------------------------


def test_non_strict_dom_warns_but_keeps_the_render_on_parse_failure_normal_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    A parse failure must NOT discard a successful render.

    The guarded block parses the DOM and writes a pretty-printed *debug artifact*. The render
    itself already succeeded and its bytes are on disk, so falling back to raw here would throw
    away every bit of JS-rendered content because a cosmetic side-file could not be written --
    which a full disk alone is enough to cause. Warn loudly, keep the data, and leave
    ``tree_path`` unset so the missing artifact is visible rather than implied.
    """
    monkeypatch.setattr(html_fetcher, "_http_get", lambda url, ua, timeout: (200, _FAKE_BODY_HTML))
    monkeypatch.setattr(html_fetcher, "_render_page_with_playwright", _render_ok)
    monkeypatch.setattr(html_fetcher, "BeautifulSoup", _soup_that_booms_for_rendered_html)

    pol = _policy(tmp_path, strict_dom=False)

    with pytest.warns(RuntimeWarning, match=r"rendered page's HTML could not be parsed into a DOM"):
        snap = html_fetcher.fetch_html(_FAKE_URL, policy=pol)

    paths = cache_paths(_FAKE_URL, pol.cache_dir)
    assert snap.html_path == paths["html_rendered"], "a parse failure must not discard the successful render"
    assert snap.tree_path is None, "the pretty-tree artifact failed, so it must not be advertised"


def test_non_strict_dom_warns_but_keeps_the_render_on_parse_failure_captcha_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Same contract on the CAPTCHA/WAF branch: warn, keep the render, no tree artifact."""
    monkeypatch.setattr(html_fetcher, "_http_get", lambda url, ua, timeout: (403, b"access denied"))
    monkeypatch.setattr(html_fetcher, "_render_page_with_playwright", _render_ok)
    monkeypatch.setattr(html_fetcher, "BeautifulSoup", _soup_that_booms_for_rendered_html)

    pol = _policy(tmp_path, strict_dom=False, captcha_mode="off")

    with pytest.warns(RuntimeWarning, match=r"rendered page's HTML could not be parsed into a DOM"):
        snap = html_fetcher.fetch_html(_FAKE_URL, policy=pol)

    paths = cache_paths(_FAKE_URL, pol.cache_dir)
    assert snap.html_path == paths["html_rendered"], "a parse failure must not discard the successful render"
    assert snap.tree_path is None, "the pretty-tree artifact failed, so it must not be advertised"


# ---------------------------------------------------------------------------
# Behaviour 3: a genuine render failure (Playwright itself never produced a
# page -- not a DOM-parse failure) must still warn and fall back to raw,
# regardless of strict_dom. There is no rendered DOM to be strict about.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("strict_dom", [True, False], ids=["strict_dom=True", "strict_dom=False"])
def test_genuine_render_failure_warns_and_falls_back_regardless_of_strict_dom(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, strict_dom: bool
) -> None:
    monkeypatch.setattr(html_fetcher, "_http_get", lambda url, ua, timeout: (200, _FAKE_BODY_HTML))
    monkeypatch.setattr(html_fetcher, "_render_page_with_playwright", _render_boom)

    pol = _policy(tmp_path, strict_dom=strict_dom)

    with pytest.warns(RuntimeWarning, match=r"--render requested but JS rendering failed"):
        snap = html_fetcher.fetch_html(_FAKE_URL, policy=pol)

    paths = cache_paths(_FAKE_URL, pol.cache_dir)
    assert snap.html_path == paths["html_raw"]
    assert not paths["html_rendered"].exists()
