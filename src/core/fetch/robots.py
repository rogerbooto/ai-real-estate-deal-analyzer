# src/core/fetch/robots.py
"""
robots.txt helper using urllib.robotparser with pluggable fetch.
"""

from __future__ import annotations

from collections.abc import Callable
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

# Fetch signature: (url) -> (status_code, body_text)
FetchFn = Callable[[str], tuple[int, str]]


def is_allowed(url: str, ua: str, fetch: FetchFn) -> bool:
    """
    Return True if the given user-agent is allowed to fetch `url` per robots.txt.
    If robots.txt cannot be retrieved, we default to True (best-effort).
    """
    parsed = urlparse(url)
    robots_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")

    status, text = fetch(robots_url)
    if status >= 400 or not text:
        # best-effort: if robots is unavailable, allow
        return True

    rp = RobotFileParser()
    rp.parse(text.splitlines())
    try:
        return rp.can_fetch(ua, url)
    except Exception:
        return True
