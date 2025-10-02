# src/agents/tools/listing_ingest_tool.py

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.schemas.models import FetchPolicy, IngestResult, ListingNormalized, PhotoInsights
from src.tools.listing_ingest import ingest_listing


def _policy_from_dict(d: dict[str, Any] | FetchPolicy | None) -> FetchPolicy:
    """
    Normalize an incoming policy that may be:
      - a FetchPolicy instance,
      - a plain dict of policy fields,
      - or None (use defaults).
    """
    if isinstance(d, FetchPolicy):
        return d
    if not d:
        return FetchPolicy()

    # Only allow known keys; ignore extras defensively.
    return FetchPolicy(
        captcha_mode=d.get("captcha_mode", "soft"),
        min_body_text=int(d.get("min_body_text", 400)),
        allow_network=bool(d.get("allow_network", False)),
        allow_non_200=bool(d.get("allow_non_200", False)),
        respect_robots=bool(d.get("respect_robots", True)),
        timeout_s=float(d.get("timeout_s", 15.0)),
        user_agent=str(d.get("user_agent", "AI-REA/0.2 (+deterministic-ingest)")),
        cache_dir=Path(d.get("cache_dir", "data/raw")),
        render_js=bool(d.get("render_js", False)),
        render_wait_s=float(d.get("render_wait_s", 9.0)),
        render_wait_until=str(d.get("render_wait_until", "networkidle")),
        render_selector=(str(d["render_selector"]) if d.get("render_selector") else None),
        save_screenshot=bool(d.get("save_screenshot", False)),
        strict_dom=bool(d.get("strict_dom", False)),
    )


def run_listing_ingest_tool(
    *,
    url: str | None = None,
    file: str | None = None,
    photos_dir: str | None = None,
    fetch_policy: dict[str, Any] | FetchPolicy | None = None,
    use_ai: bool = False,
) -> tuple[ListingNormalized, PhotoInsights]:
    """
    Agent-callable ingestion entrypoint.

    Returns:
        (ListingNormalized, PhotoInsights)
    """
    pol = _policy_from_dict(fetch_policy)

    result: IngestResult = ingest_listing(
        url=url,
        file=Path(file) if file else None,
        photos_dir=Path(photos_dir) if photos_dir else None,
        policy=pol,
        use_ai=use_ai,
    )

    # Return typed models (callers can .model_dump() if they need dicts)
    return result.listing, result.photos
