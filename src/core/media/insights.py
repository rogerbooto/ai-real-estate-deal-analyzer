# src/core/media/insights.py

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import cast

from src.schemas.models import MediaAsset, MediaBundle, MediaInsights

from .intelligence import MediaAssetLike, compute_phash, compute_quality, extract_palette, hamming_distance_hex, rank_hero

PHASH_SIZE = 32
PHASH_LOWFREQ = 8
PHASH_THRESHOLD = 10  # hamming distance threshold for near-dup


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


def enrich_with_intelligence(bundle: MediaBundle, insights: MediaInsights, enable: bool = False) -> None:
    if not enable:
        return

    phashes: dict[str, str] = {}
    signals: dict[str, dict[str, object]] = {}

    # 1) Per-image signals
    for a in bundle.images:
        try:
            ph = compute_phash(a.path, size=PHASH_SIZE, lowfreq=PHASH_LOWFREQ)
            q = compute_quality(a.path)
            pal = [c.to_hex() for c in extract_palette(a.path, k=5)]

            phashes[a.sha256] = ph
            insights.image_quality[a.sha256] = q
            insights.palettes[a.sha256] = pal

            w = int(a.width) if a.width else 0
            h = int(a.height) if a.height else 0
            signals[a.sha256] = {
                "size": (w, h),
                "area": float(w * h),
                "is_duplicate": False,  # set after clustering
                "quality": q,
            }
        except Exception as e:
            insights.warnings.append(f"intel-skip:{a.sha256}:{type(e).__name__}")

    # 2) phash clustering
    sha_list = list(phashes.keys())
    used: set[str] = set()
    clusters: list[list[str]] = []

    for i, s1 in enumerate(sha_list):
        if s1 in used:
            continue
        cluster = [s1]
        for j in range(i + 1, len(sha_list)):
            s2 = sha_list[j]
            if s2 in used:
                continue
            if hamming_distance_hex(phashes[s1], phashes[s2]) <= PHASH_THRESHOLD:
                cluster.append(s2)
                used.add(s2)
        if len(cluster) > 1:
            for s in cluster:
                if s in signals:
                    signals[s]["is_duplicate"] = True
            clusters.append(sorted(cluster))
        used.add(s1)

    insights.duplicates = clusters

    # 3) Hero selection (deterministic)
    hero = rank_hero(cast(Sequence[MediaAssetLike], bundle.images), signals)
    if hero is not None:
        insights.hero_sha256 = hero.sha256
