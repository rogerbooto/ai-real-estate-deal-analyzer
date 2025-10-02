# src/core/fetch/html_fetcher.py
"""
Offline-first HTML fetcher with robots.txt awareness, optional JS rendering,
and deterministic caching.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

import requests
from bs4 import BeautifulSoup

from src.schemas.models import FetchPolicy, HtmlSnapshot

from .cache import _sha256, cache_paths
from .errors import (
    _CAPTCHA_WAF_PATTERN as _CAPTCHA_PAT,
    CaptchaBlockedError,
    DisallowedByRobotsError,
    InvalidHtmlError,
    NetworkError,
    OfflineRequiredError,
    fetcher_error_guard,
)
from .robots import is_allowed

# -------------------------
# Internal HTTP helpers
# -------------------------


def _http_get(url: str, ua: str, timeout: float) -> tuple[int, bytes]:
    try:
        resp = requests.get(url, headers={"User-Agent": ua}, timeout=timeout)
        return resp.status_code, resp.content
    except requests.RequestException as e:  # pragma: no cover
        raise NetworkError(str(e)) from e


def _fetch_for_robots(url: str, ua: str, timeout: float) -> tuple[int, str]:
    code, b = _http_get(url, ua, timeout)
    try:
        return code, b.decode("utf-8", errors="ignore")
    except Exception:
        return code, ""


def _render_page_with_playwright(
    url: str,
    ua: str,
    wait_until: str,
    wait_s: float,
    selector: str | None,
    screenshot_path: Path | None,
) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:  # pragma: no cover
        raise ImportError("playwright not installed") from e

    wait_until = wait_until if wait_until in {"load", "domcontentloaded", "networkidle"} else "networkidle"
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=ua)
        page = ctx.new_page()
        page.set_default_timeout(int(wait_s * 1000))
        page.goto(url, wait_until=wait_until)
        if selector:
            try:
                page.wait_for_selector(selector, timeout=int(wait_s * 1000))
            except Exception:
                pass
        if screenshot_path:
            try:
                page.screenshot(path=str(screenshot_path))
            except Exception:
                pass
        html = page.content()
        ctx.close()
        browser.close()
    return str(html)


# -------------------------
# Public API
# -------------------------


def fetch_html(url: str, *, policy: FetchPolicy | None = None) -> HtmlSnapshot:
    """
    Cache-first fetch of HTML with optional JS rendering.
    Returns an HtmlSnapshot with paths and metadata persisted to meta.json.

    CAPTCHA/WAF handling:
      - If raw fetch looks like a WAF/CAPTCHA, we try JS render first (if enabled).
      - If the rendered page looks like real content (min text length), we use it.
      - Else:
          captcha_mode=="strict" -> raise CaptchaBlockedError
          captcha_mode=="soft"   -> annotate meta and continue with RAW (best-effort)
          captcha_mode=="off"    -> ignore and continue
    """
    pol = policy or FetchPolicy()
    paths = cache_paths(url, pol.cache_dir)
    paths["root"].mkdir(parents=True, exist_ok=True)

    def _return_snapshot(
        mode: str,
        status_code: int,
        html_file: Path,
        tree_file: Path | None,
        raw_bytes: bytes,
    ) -> HtmlSnapshot:
        now = datetime.now(timezone.utc).isoformat()
        meta = {
            "last_fetched_at": now,
            "status_code": status_code,
            "mode": mode,
            "tree_path": str(tree_file) if tree_file else None,
        }
        if paths["meta"].exists():
            try:
                prev = json.loads(paths["meta"].read_text())
                if "first_fetched_at" not in prev:
                    prev["first_fetched_at"] = now
                prev.update(meta)
                meta = prev
            except Exception:
                pass
        else:
            meta["first_fetched_at"] = now

        paths["meta"].write_text(json.dumps(meta), encoding="utf-8")
        return HtmlSnapshot(
            url=url,
            fetched_at=datetime.fromisoformat(cast(str, meta["last_fetched_at"])),
            status_code=status_code,
            html_path=html_file,
            tree_path=tree_file,
            bytes_size=len(raw_bytes),
            sha256=_sha256(raw_bytes),
        )

    def _looks_like_real_content(html: str) -> bool:
        """Heuristic: enough visible text to consider page 'real' content."""
        try:
            s = BeautifulSoup(html, "lxml")
            txt = s.get_text(" ", strip=True)
            return len(txt) >= getattr(pol, "min_body_text", 400)
        except Exception:
            return False

    with fetcher_error_guard(strict_dom=pol.strict_dom):
        # Cache-first: rendered if asked, otherwise raw
        if pol.render_js and paths["html_rendered"].exists():
            raw = paths["html_rendered"].read_bytes()
            tree = paths["tree_rendered"] if paths["tree_rendered"].exists() else None
            status = 200
            try:
                status = int(json.loads(paths["meta"].read_text()).get("status_code", 200))
            except Exception:
                pass
            return _return_snapshot("rendered", status, paths["html_rendered"], tree, raw)

        if paths["html_raw"].exists():
            raw = paths["html_raw"].read_bytes()
            tree = paths["tree_raw"] if paths["tree_raw"].exists() else None
            status = 200
            try:
                status = int(json.loads(paths["meta"].read_text()).get("status_code", 200))
            except Exception:
                pass
            return _return_snapshot("raw", status, paths["html_raw"], tree, raw)

        # Offline guard
        if not pol.allow_network:
            raise OfflineRequiredError("Cache miss and networking is disabled by policy.")

        # robots.txt
        if pol.respect_robots:
            allowed = is_allowed(url, pol.user_agent, lambda r: _fetch_for_robots(r, pol.user_agent, pol.timeout_s))
            if not allowed:
                raise DisallowedByRobotsError(f"robots.txt disallows fetching {url}")

        # Online fetch (always save RAW)
        status, content = _http_get(url, pol.user_agent, pol.timeout_s)
        paths["html_raw"].write_bytes(content)

        # Optionally enforce 2xx
        if not pol.allow_non_200 and status >= 400:
            raise NetworkError(f"HTTP {status} for {url}")

        # Early WAF/CAPTCHA detection (RAW)
        try:
            body_txt = content.decode("utf-8", errors="ignore")
        except Exception:
            body_txt = ""

        bad_status = (401, 403, 429, 451, 503, 520, 521, 522, 523, 524, 525, 526)
        raw_looks_captcha = (status in bad_status) or _CAPTCHA_PAT.search(body_txt)

        rendered_bytes: bytes | None = None

        if raw_looks_captcha:
            rendered_html: str | None = None

            # Try JS render before deciding (if enabled)
            if pol.render_js:
                try:
                    rendered_html = _render_page_with_playwright(
                        url,
                        pol.user_agent,
                        pol.render_wait_until,
                        pol.render_wait_s,
                        pol.render_selector,
                        paths["screenshot"] if pol.save_screenshot else None,
                    )
                    rendered_bytes = rendered_html.encode("utf-8", errors="ignore")
                    paths["html_rendered"].write_bytes(rendered_bytes)
                    try:
                        soup_r = BeautifulSoup(rendered_html, "lxml")
                        paths["tree_rendered"].write_text(soup_r.prettify(), encoding="utf-8")
                    except Exception as e:
                        if pol.strict_dom:
                            raise InvalidHtmlError(f"Failed to parse/pretty RENDERED HTML for {url}: {type(e).__name__}") from e
                except Exception:
                    rendered_bytes = None
                    rendered_html = None

                # If rendered looks like real content, prefer and return it
                if rendered_html and _looks_like_real_content(rendered_html):
                    # also pretty-print RAW for debugging if possible
                    try:
                        soup_tmp = BeautifulSoup(content, "lxml")
                        paths["tree_raw"].write_text(soup_tmp.prettify(), encoding="utf-8")
                    except Exception:
                        pass
                    return _return_snapshot(
                        "rendered",
                        status,
                        paths["html_rendered"],
                        paths["tree_rendered"] if paths["tree_rendered"].exists() else None,
                        rendered_bytes or b"",
                    )

            # If we're here, raw looked like captcha and render didn't help (or not enabled)
            mode = getattr(pol, "captcha_mode", "soft")  # "strict" | "soft" | "off"
            if mode == "strict":
                # pretty-print RAW for debugging, then raise
                try:
                    soup_tmp = BeautifulSoup(content, "lxml")
                    paths["tree_raw"].write_text(soup_tmp.prettify(), encoding="utf-8")
                except Exception:
                    pass
                raise CaptchaBlockedError(f"WAF/CAPTCHA suspected for {url} (status={status})")
            elif mode == "soft":
                # annotate meta and proceed (best-effort)
                try:
                    meta = json.loads(paths["meta"].read_text()) if paths["meta"].exists() else {}
                except Exception:
                    meta = {}
                meta["captcha_suspected"] = True
                paths["meta"].write_text(json.dumps(meta), encoding="utf-8")
                # fall through to RAW parse
            else:
                # "off" → ignore entirely
                pass

        # Pretty-print RAW DOM
        try:
            soup = BeautifulSoup(content, "lxml")
            paths["tree_raw"].write_text(soup.prettify(), encoding="utf-8")
        except Exception as e:
            if pol.strict_dom:
                raise InvalidHtmlError(f"Failed to parse/pretty RAW HTML for {url}: {type(e).__name__}") from e

        # Optional JS render (normal path, when not already done above)

        if pol.render_js:
            try:
                rendered_html = _render_page_with_playwright(
                    url,
                    pol.user_agent,
                    pol.render_wait_until,
                    pol.render_wait_s,
                    pol.render_selector,
                    paths["screenshot"] if pol.save_screenshot else None,
                )
                rendered_bytes = rendered_html.encode("utf-8", errors="ignore")
                paths["html_rendered"].write_bytes(rendered_bytes)
                try:
                    soup_r = BeautifulSoup(rendered_html, "lxml")
                    paths["tree_rendered"].write_text(soup_r.prettify(), encoding="utf-8")
                except Exception as e:
                    if pol.strict_dom:
                        raise InvalidHtmlError(f"Failed to parse/pretty RENDERED HTML for {url}: {type(e).__name__}") from e
            except Exception:
                rendered_bytes = None

        # Choose snapshot
        if pol.render_js and rendered_bytes is not None:
            return _return_snapshot(
                "rendered",
                status,
                paths["html_rendered"],
                paths["tree_rendered"] if paths["tree_rendered"].exists() else None,
                rendered_bytes,
            )
        return _return_snapshot(
            "raw",
            status,
            paths["html_raw"],
            paths["tree_raw"] if paths["tree_raw"].exists() else None,
            content,
        )


# -------------------------
# Optional CLI (dev aid)
# -------------------------

if __name__ == "__main__":  # pragma: no cover
    import argparse

    p = argparse.ArgumentParser(description="Deterministic, cached HTML fetcher (raw and rendered).")
    p.add_argument("--url", required=True)
    p.add_argument("--out", default="data/raw")
    p.add_argument("--online", type=int, default=0)
    p.add_argument("--no-robots", type=int, default=0)
    p.add_argument("--timeout", type=float, default=15.0)
    p.add_argument("--ua", default="AI-REA/0.2 (+deterministic-ingest)")

    p.add_argument("--render", type=int, default=0)
    p.add_argument("--wait", type=float, default=6.0)
    p.add_argument("--wait-until", default="networkidle")
    p.add_argument("--selector", default=None)
    p.add_argument("--screenshot", type=int, default=0)
    p.add_argument("--strict-dom", type=int, default=0)
    args = p.parse_args()

    policy = FetchPolicy(
        allow_network=bool(args.online),
        respect_robots=not bool(args.no_robots),
        timeout_s=float(args.timeout),
        user_agent=str(args.ua),
        cache_dir=Path(args.out),
        render_js=bool(args.render),
        render_wait_s=float(args.wait),
        render_wait_until=str(args.wait_until),
        render_selector=str(args.selector) if args.selector else None,
        save_screenshot=bool(args.screenshot),
        strict_dom=bool(args.strict_dom),
    )

    snap = fetch_html(args.url, policy=policy)
    print(str(snap.html_path))
    if snap.tree_path:
        print(str(snap.tree_path))
