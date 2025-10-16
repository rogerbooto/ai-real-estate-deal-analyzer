# src/ingest_cli.py

from __future__ import annotations

import argparse
from pathlib import Path

from src.schemas.models import FetchPolicy, MediaKind
from src.tools.listing_ingest import ingest_listing


def _parse_media_kinds(val: str | None) -> set[MediaKind] | None:
    if not val:
        return None
    items = [v.strip().lower() for v in val.split(",") if v.strip()]
    valid: set[MediaKind] = {"image", "video", "floorplan", "document", "other"}
    out: set[MediaKind] = set()
    for it in items:
        if it not in valid:
            raise argparse.ArgumentTypeError(f"invalid media kind: {it!r}")
        out.add(it)
    return out or None


def main() -> int:
    p = argparse.ArgumentParser(description="Listing ingest")
    p.add_argument("--url", type=str, default=None)
    p.add_argument("--file", type=str, default=None)
    p.add_argument("--photos", type=str, default=None, help="Optional directory of images for photo insights")
    p.add_argument("--out-cache", type=str, default="data/cache")
    p.add_argument("--online", type=int, default=0)
    p.add_argument("--ai", type=int, default=0)
    p.add_argument("--render", type=int, default=0)
    p.add_argument("--pretty", type=int, default=1)
    p.add_argument("--download-media", type=int, choices=(0, 1), default=1, help="Enable media discovery & download")
    p.add_argument("--max-media", type=int, default=64, help="Max media assets to fetch")
    p.add_argument("--media-intel", type=int, default=0, help="Enable media intelligence (phash/quality/palette/hero)")
    p.add_argument(
        "--media-kinds",
        type=str,
        default=None,
        help="Comma-separated kinds: image,video,floorplan,document,other",
    )

    args = p.parse_args()

    policy = FetchPolicy(
        allow_network=bool(args.online),
        allow_non_200=False,
        respect_robots=True,
        timeout_s=20.0,
        user_agent="AI-REA/0.2 (+deterministic-ingest)",
        cache_dir=Path(args.out_cache),
        render_js=bool(args.render),
        render_wait_s=20.0,
        render_wait_until="networkidle",
        render_selector=None,
        save_screenshot=bool(args.pretty),
        strict_dom=False,
    )

    media_kinds = _parse_media_kinds(args.media_kinds)

    result = ingest_listing(
        url=args.url,
        file=Path(args.file) if args.file else None,
        photos_dir=Path(args.photos) if args.photos else None,
        policy=policy,
        use_ai=bool(args.ai),
        download_media=bool(args.download_media),
        media_max_items=int(args.max_media),
        media_kinds=media_kinds,
        media_intel=bool(args.media_intel),
    )

    # Minimal console summary
    images = sum(1 for a in result.media.assets if a.kind == "image")
    total = len(result.media.assets)
    print(f"media: {total} assets (images: {images})")

    # Media insights summary
    mi = result.media_insights
    if mi:
        print(
            "media insights: \n"
            f"total={mi.total_assets}, images={mi.image_count}, videos={mi.video_count}, "
            f"docs={mi.document_count}, bytes={mi.bytes_total}, "
            f"w[{mi.min_width}..{mi.max_width}] h[{mi.min_height}..{mi.max_height}] "
            f"avg=({mi.avg_width}x{mi.avg_height}), "
            f"orientations: L={mi.landscape_count} P={mi.portrait_count} S={mi.square_count}, "
            f"dups={len(mi.duplicate_hashes)}, hero={mi.hero_sha256}"
        )

    if args.pretty:
        from pprint import pprint

        pprint(result.listing.model_dump(), indent=2, width=120, compact=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
