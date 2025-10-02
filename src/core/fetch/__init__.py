# src/core/fetch/__init__.py
from .cache import _sha256, cache_paths
from .errors import (
    FETCHER_ERRORS,
    CaptchaBlockedError,
    DisallowedByRobotsError,
    HtmlFetcherError,
    InvalidHtmlError,
    NetworkError,
    OfflineRequiredError,
    classify_fetcher_error,
    fetcher_error_guard,
)
from .html_fetcher import fetch_html
from .robots import is_allowed

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
    "is_allowed",
    "cache_paths",
    "_sha256",
    "fetch_html",
]
