from __future__ import annotations

from collections.abc import Iterable

from src.schemas.models import MediaAsset, MediaInsights


def analyze_media(assets: Iterable[MediaAsset]) -> MediaInsights:
    """
    Compute descriptive stats for a set of MediaAsset items.
    - Counts by kind
    - Bytes total
    - Image dimension stats and orientation breakdown
    - Duplicate detection by sha256
    - Best-guess hero image (largest pixel area among images)
    """
    assets_list = list(assets)
    total = len(assets_list)

    image_assets = [a for a in assets_list if a.kind == "image"]
    video_assets = [a for a in assets_list if a.kind == "video"]
    doc_assets = [a for a in assets_list if a.kind == "document"]
    other_assets = [a for a in assets_list if a.kind not in {"image", "video", "document"}]

    bytes_total = sum(a.bytes_size for a in assets_list)

    # Image dimension stats
    widths = [int(a.width) for a in image_assets if a.width]
    heights = [int(a.height) for a in image_assets if a.height]

    min_w = min(widths) if widths else None
    max_w = max(widths) if widths else None
    min_h = min(heights) if heights else None
    max_h = max(heights) if heights else None
    avg_w = (sum(widths) / len(widths)) if widths else None
    avg_h = (sum(heights) / len(heights)) if heights else None

    # Orientation
    portrait = 0
    landscape = 0
    square = 0
    for a in image_assets:
        if a.width and a.height:
            if a.width > a.height:
                landscape += 1
            elif a.height > a.width:
                portrait += 1
            else:
                square += 1

    # Duplicates by sha256 (exact content match)
    seen: dict[str, int] = {}
    dups: list[str] = []
    for a in assets_list:
        cnt = seen.get(a.sha256, 0) + 1
        seen[a.sha256] = cnt
        if cnt == 2:  # only append once for a given digest
            dups.append(a.sha256)

    # Hero: largest pixel area among images (fallback None)
    hero = None
    max_area = -1
    for a in image_assets:
        if a.width and a.height:
            area = a.width * a.height
            if area > max_area:
                max_area = area
                hero = a.sha256

    return MediaInsights(
        total_assets=total,
        image_count=len(image_assets),
        video_count=len(video_assets),
        document_count=len(doc_assets),
        other_count=len(other_assets),
        bytes_total=bytes_total,
        min_width=min_w,
        max_width=max_w,
        min_height=min_h,
        max_height=max_h,
        avg_width=avg_w,
        avg_height=avg_h,
        portrait_count=portrait,
        landscape_count=landscape,
        square_count=square,
        duplicate_hashes=dups,
        hero_sha256=hero,
        warnings=[],
    )
