# ingest_cli.py
"""
CLI: Ingest a listing from URL or local file → ListingNormalized + PhotoInsights + ListingInsights.

Examples
--------
# Offline (cache-only) parse from URL (will error on cache miss):
python ingest_cli.py --url "https://example.com/listing/123" --online 0 --out-cache data/raw --pretty 1

# Online, respect robots, render JS, and save JSON:
python ingest_cli.py --url "https://example.com/listing/123" --online 1 --render 1 --json-out /tmp/listing.json

# Local file + photos, deterministic CV:
python ingest_cli.py --file tests/listing/fixtures/sample1.html --photos ./photos

JSON schema
-----------
{
  "listing": <ListingNormalized.model_dump()>,
  "photo_insights": <PhotoInsights.model_dump()>,
  "listing_insights": <ListingInsights.model_dump()>
}
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.core.fetch.errors import fetcher_error_guard
from src.schemas.models import FetchPolicy
from src.tools.listing_ingest import ingest_listing


def _print_header(title: str) -> None:
    print("=" * 80)
    print(title)
    print("=" * 80)


def main() -> None:
    p = argparse.ArgumentParser(description="Ingest listing → normalized models + insights.")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="Listing page URL to fetch (cache-first).")
    src.add_argument("--file", type=Path, help="Path to local HTML/TXT file.")

    p.add_argument("--photos", type=Path, default=None, help="Directory of listing photos (optional).")

    # Fetch policy
    p.add_argument("--online", type=int, default=0, help="Allow networking (1) vs offline-only (0). Default 0.")
    p.add_argument("--no-robots", type=int, default=0, help="Disable robots.txt check if 1 (use with care).")
    p.add_argument("--out-cache", type=Path, default=Path("data/raw"), help="Cache directory for fetched HTML.")
    p.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout in seconds.")
    p.add_argument("--ua", default="AI-REA/0.2 (+deterministic-ingest)", help="User-Agent string.")
    p.add_argument("--render", type=int, default=0, help="Render JS via Playwright (1) else raw only (0).")
    p.add_argument("--wait", type=float, default=8.0, help="Max seconds to wait after navigation (render mode).")
    p.add_argument("--wait-until", default="networkidle", help="load|domcontentloaded|networkidle (render mode).")
    p.add_argument("--selector", default=None, help="Optional CSS selector to wait for (render mode).")
    p.add_argument("--screenshot", type=int, default=0, help="Save PNG screenshot in cache if 1.")
    p.add_argument("--strict-dom", type=int, default=0, help="Raise on DOM parse errors if 1.")

    # CV mode
    p.add_argument("--ai", type=int, default=0, help="Enable AI pass in cv_tagging (1) else deterministic-only (0).")

    # Output
    p.add_argument("--json-out", type=Path, default=None, help="Optional path to write combined JSON output.")
    p.add_argument("--pretty", type=int, default=1, help="Pretty-print summaries (1) or quiet (0).")

    args = p.parse_args()

    policy = FetchPolicy(
        allow_network=bool(args.online),
        respect_robots=not bool(args.no_robots),
        timeout_s=float(args.timeout),
        user_agent=str(args.ua),
        cache_dir=args.out_cache,
        render_js=bool(args.render),
        render_wait_s=float(args.wait),
        render_wait_until=str(args.wait_until),
        render_selector=str(args.selector) if args.selector else None,
        save_screenshot=bool(args.screenshot),
        strict_dom=bool(args.strict_dom),
    )

    with fetcher_error_guard():
        result = ingest_listing(
            url=args.url,
            file=args.file,
            photos_dir=args.photos,
            policy=policy,
            use_ai=bool(args.ai),
        )

    if args.pretty:
        _print_header("ListingNormalized")
        print(result.listing.summary())
        _print_header("PhotoInsights")
        print(result.photos.summary())
        _print_header("ListingInsights")
        # Construct a compact readout
        print(
            f"Address: {result.insights.address}\n"
            f"Amenities: {', '.join(result.insights.amenities) or '—'}\n"
            f"Condition: {', '.join(result.insights.condition_tags) or '—'}\n"
            f"Defects: {', '.join(result.insights.defects) or '—'}\n"
            f"Notes: {', '.join(result.insights.notes) or '—'}"
        )

    payload = {
        "listing": result.listing.model_dump(),
        "photo_insights": result.photos.model_dump(),
        "listing_insights": result.insights.model_dump(),
    }

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        if args.pretty:
            _print_header("JSON written")
            print(str(args.json_out))

    if not args.pretty and not args.json_out:
        print(json.dumps(payload))


if __name__ == "__main__":
    main()
