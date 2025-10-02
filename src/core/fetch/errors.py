# src/core/fetch/errors.py
"""
Typed errors + utilities for the offline-first HTML fetcher.

Exports
-------
- HtmlFetcherError, OfflineRequiredError, DisallowedByRobotsError,
  NetworkError, InvalidHtmlError, CaptchaBlockedError
- FETCHER_ERRORS
- classify_fetcher_error(exc, strict_dom=False)
- fetcher_error_guard(strict_dom=False)
- _CAPTCHA_WAF_PATTERN   (shared regex for WAF/CAPTCHA detection)
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import requests  # noqa: F401

# =========================
# Exception types
# =========================


class HtmlFetcherError(RuntimeError):
    """Base class for HTML fetcher-related failures."""


class OfflineRequiredError(HtmlFetcherError):
    """Cache miss occurred but policy forbids network access."""


class DisallowedByRobotsError(HtmlFetcherError):
    """robots.txt explicitly disallows fetching the requested URL."""


class NetworkError(HtmlFetcherError):
    """HTTP/transport failure while attempting to fetch a resource."""


class InvalidHtmlError(HtmlFetcherError):
    """Fetched HTML could not be parsed into a DOM (strict mode only)."""


class CaptchaBlockedError(HtmlFetcherError):
    """A CAPTCHA or WAF (Incapsula/Akamai/Cloudflare) blocked access."""


# Selector tuple for grouped exception handling
FETCHER_ERRORS = (
    OfflineRequiredError,
    DisallowedByRobotsError,
    NetworkError,
    InvalidHtmlError,
    CaptchaBlockedError,
)

# Common WAF/CAPTCHA markers found in bodies/messages/headers
_CAPTCHA_WAF_PATTERN = re.compile(
    r"(captcha|cf-chl|cloudflare|hcaptcha|recaptcha|akamai|incapsula|imperva|robot\s*check|access\s*denied)",
    re.IGNORECASE,
)

# =========================
# Classification helpers
# =========================


def classify_fetcher_error(exc: Exception, *, strict_dom: bool = False) -> HtmlFetcherError:
    """
    Map arbitrary exceptions raised inside the fetcher to a typed HtmlFetcherError subclass.

    Heuristics:
      - requests.* errors → NetworkError
      - Playwright import/launch/nav errors:
          - If related to DOM parse/render and strict_dom=True → InvalidHtmlError
          - Otherwise → HtmlFetcherError
      - Messages hinting at CAPTCHA/WAF blocks → CaptchaBlockedError
      - lxml/BeautifulSoup parse failures (strict_dom=True) → InvalidHtmlError
      - Any HtmlFetcherError subclass → passed through
      - Fallback → HtmlFetcherError
    """
    # Already ours
    if isinstance(exc, HtmlFetcherError):
        return exc

    # requests.* → NetworkError
    try:
        import requests

        if isinstance(
            exc,
            (requests.Timeout | requests.ConnectionError | requests.HTTPError | requests.RequestException),
        ):
            return NetworkError(str(exc))
    except Exception:
        pass

    msg = f"{type(exc).__name__}: {exc}"

    # WAF/CAPTCHA
    if _CAPTCHA_WAF_PATTERN.search(msg):
        return CaptchaBlockedError(msg)

    # Playwright
    if "playwright" in msg.lower():
        import re as _re

        if strict_dom and _re.search(r"(parse|content|dom|renderer|navigation|timeout)", msg, flags=_re.I):
            return InvalidHtmlError(msg)
        return HtmlFetcherError(msg)

    # Parser failures → InvalidHtmlError when strict
    if strict_dom and any(k in msg.lower() for k in ("parser", "parse", "lxml", "beautifulsoup", "bs4")):
        return InvalidHtmlError(msg)

    return HtmlFetcherError(msg)


@contextmanager
def fetcher_error_guard(*, strict_dom: bool = False) -> Iterator[None]:
    """Context manager to normalize unexpected exceptions from fetcher internals."""
    try:
        yield
    except FETCHER_ERRORS:
        raise
    except Exception as exc:  # noqa: BLE001
        raise classify_fetcher_error(exc, strict_dom=strict_dom) from exc


__all__ = [
    "HtmlFetcherError",
    "OfflineRequiredError",
    "DisallowedByRobotsError",
    "NetworkError",
    "InvalidHtmlError",
    "CaptchaBlockedError",
    "FETCHER_ERRORS",
    "classify_fetcher_error",
    "fetcher_error_guard",
    "_CAPTCHA_WAF_PATTERN",
]
