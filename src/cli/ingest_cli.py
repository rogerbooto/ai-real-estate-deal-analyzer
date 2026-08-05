# src/ingest_cli.py

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from pprint import pprint
from typing import Final, cast

from src.core.ingest.listing_ingest import ingest_listing
from src.schemas.models import FetchPolicy, MediaKind

#: Media-discovery flags that only have an effect when the pipeline has an HTML source
#: (a `--url` fetch, with or without `--render`) to scan for `<img>`/`og:image`/JSON-LD
#: media references. `--file` input alone has no HTML snapshot, and `collect_local_assets`
#: (the local-folder media walker used by the orchestrators) is not wired into
#: `ingest_listing`, so these flags cannot discover anything in that mode. See F11 in
#: docs/plans/MISSION_2_wiring_gaps.md.
_MEDIA_FLAG_NAMES: Final[str] = "--download-media/--max-media/--media-kinds/--media-intel"


def _parse_media_kinds(val: str) -> set[MediaKind] | None:
    """argparse ``type=`` callable: comma-separated media kinds -> a validated set.

    Raising ``argparse.ArgumentTypeError`` here (instead of after ``parse_args()`` returns)
    lets argparse turn an invalid value into a clean usage error (exit code 2) rather than an
    unhandled traceback.
    """
    if not val:
        return None
    items = [v.strip().lower() for v in val.split(",") if v.strip()]
    VALID_MEDIA_KIND_STRS: Final[set[str]] = {"image", "video", "floorplan", "document", "other"}
    out: set[MediaKind] = set()
    for it in items:
        if it not in VALID_MEDIA_KIND_STRS:
            raise argparse.ArgumentTypeError(f"invalid media kind: {it!r} (choose from: {sorted(VALID_MEDIA_KIND_STRS)})")
        out.add(cast(MediaKind, it))
    return out or None


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ingest-listing", description="Listing ingest")
    p.add_argument("--url", type=str, default=None, help="Listing URL to fetch (mutually exclusive intent with --file).")
    p.add_argument("--file", type=str, default=None, help="Local listing file (.txt/.md/.html) to parse instead of a URL.")
    p.add_argument("--photos", type=str, default=None, help="Optional directory of images for photo insights")
    p.add_argument("--out-cache", type=str, default="data/cache")
    p.add_argument("--online", type=int, default=0, help="Allow network fetch when --url is used (robots.txt respected).")
    p.add_argument(
        "--ai",
        type=int,
        default=0,
        help=(
            "Switch the photo-insight detection provider from 'local' to 'vision' "
            "(core.cv.build_photo_insights(use_ai=True)). This DOES change the output: "
            "image_detections, amenity_counts, detections_total, version and provenance all "
            "differ from the default path, and derived fields (the amenities booleans, the "
            "parking summary) can move with them. It is NOT a model call -- the 'vision' slot "
            "currently holds a hand-written threshold over image brightness, colour spread and "
            "aspect ratio, so results are stamped version='vision-stub-v1' with "
            "provenance.provider_kind='heuristic_stub'. Treat its labels as a placeholder, not "
            "as observations. The flag exists so a real classifier can be registered behind "
            "that seam later; provider_kind flips to 'model' when one is."
        ),
    )
    p.add_argument("--render", type=int, default=0, help="Render JS via a headless browser before parsing (requires --url).")
    p.add_argument(
        "--pretty",
        type=int,
        default=1,
        help=(
            "Pretty-print the full listing/insights/photos JSON to the console. Purely a console "
            "formatting knob -- it does NOT affect what gets written to --out-cache. To control "
            "whether a render screenshot is saved to disk, use --save-screenshot."
        ),
    )
    p.add_argument(
        "--save-screenshot",
        type=int,
        choices=(0, 1),
        default=1,
        help=(
            "Save a screenshot artifact when --render is used (FetchPolicy.save_screenshot). "
            "Previously this was silently tied to --pretty; it is now its own flag. Default 1 "
            "matches the historical --pretty-driven behavior."
        ),
    )
    p.add_argument(
        "--download-media",
        type=int,
        choices=(0, 1),
        default=1,
        help=(
            "Enable media discovery & download. Only has an effect when there is an HTML source "
            "to scan (--url, with or without --render); it is inert with --file alone -- a "
            "warning is printed in that case. Use --photos for a local photo directory."
        ),
    )
    p.add_argument("--max-media", type=int, default=64, help=f"Max media assets to fetch. Same {_MEDIA_FLAG_NAMES} caveat applies.")
    p.add_argument(
        "--media-intel",
        type=int,
        default=0,
        help=f"Enable media intelligence (phash/quality/palette/hero). Same {_MEDIA_FLAG_NAMES} caveat applies.",
    )
    p.add_argument(
        "--media-kinds",
        type=_parse_media_kinds,
        default=None,
        help=("Comma-separated kinds: image,video,floorplan,document,other. " f"Same {_MEDIA_FLAG_NAMES} caveat applies."),
    )
    return p


def main(argv: list[str] | None = None) -> int:
    p = _build_parser()
    args = p.parse_args(argv)

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
        save_screenshot=bool(args.save_screenshot),
        strict_dom=False,
    )

    # F11: --download-media (and its dependents) need an HTML source to scan for media
    # references. `--file` alone never produces one (no url/snapshot reaches collect_media,
    # and the local-folder walker collect_local_assets is not wired into ingest_listing), so
    # tell the user why instead of silently returning an empty media bundle.
    if args.file and not args.url and bool(args.download_media):
        print(
            f"note: {_MEDIA_FLAG_NAMES} require an HTML source (--url) to scan for media links; "
            "--file input alone yields an empty media bundle. Use --photos for a local photo "
            "directory instead.",
            file=sys.stderr,
        )

    result = ingest_listing(
        url=args.url,
        file=Path(args.file) if args.file else None,
        photos_dir=Path(args.photos) if args.photos else None,
        policy=policy,
        use_ai=bool(args.ai),
        download_media=bool(args.download_media),
        media_max_items=int(args.max_media),
        media_kinds=args.media_kinds,
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

    # F10: surface the computed insights/photos instead of discarding them silently.
    li = result.insights
    print(
        "listing insights: \n"
        f"address={li.address!r}, title={li.title!r}, price={li.price}, sqft={li.sqft}, "
        f"bedrooms={li.bedrooms}, bathrooms={li.bathrooms}, year_built={li.year_built}, "
        f"amenities={len(li.amenities)}, condition_tags={len(li.condition_tags)}, "
        f"defects={len(li.defects)}, notes={len(li.notes)}"
    )

    ph = result.photos
    print(
        "photo insights: \n"
        f"provider={ph.provider}, version={ph.version}, images_total={ph.images_total}, "
        f"detections_total={ph.detections_total}, room_counts={ph.room_counts}, "
        f"amenities={ph.amenities}, amenity_counts={ph.amenity_counts}, defect_counts={ph.defect_counts}"
    )

    if args.pretty:
        listing_dump = result.listing.model_dump()
        # F20: the model field is `address_structure` (src/schemas/models.py), not
        # `address_struct` -- the old key here meant this block never printed.
        if listing_dump.get("address_structure"):
            print("address_structure:", listing_dump["address_structure"])
        pprint(listing_dump, indent=2, width=120, compact=True)

        print("insights (full):")
        pprint(li.model_dump(), indent=2, width=120, compact=True)

        print("photos (full):")
        pprint(ph.model_dump(), indent=2, width=120, compact=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
