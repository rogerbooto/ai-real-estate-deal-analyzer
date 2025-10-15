# src/core/media/downloader.py
from __future__ import annotations

import mimetypes
import tempfile
from collections.abc import Iterable as _Iterable  # for mypy clarity
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

from src.core.fetch.cache import _sha256
from src.schemas.models import FetchPolicy, MediaAsset, MediaCandidate, MediaKind

# ---------------------------
# Helpers / knobs
# ---------------------------

_IMAGE_KINDS: tuple[MediaKind, ...] = ("image",)
_DEFAULT_ALLOWED: tuple[MediaKind, ...] = ("image", "floorplan", "document", "video")
_SMALL_FILE_THRESHOLD = 24 * 1024 * 1024  # 24 MiB
_STREAM_CHUNK = 1024 * 1024  # 1 MiB
_DEFAULT_MAX_ITEMS = 64

# URL/path patterns that are almost always icons/logos/sprites
_ICON_SUBSTRINGS = (
    "favicon",
    "sprite",
    "logo",
    "brandmark",
    "glyph",
    "icon-",
    "/icons/",
    "/sprites/",
    "/logos/",
    "social-",
    "facebook",
    "twitter",
    "linkedin",
    "instagram",
    "pinterest",
    "youtube",
    "ytimg",
)
# File extensions that are often decorative (still allow if big)
_ICON_EXTS = {"ico", "svg"}

# Common image file extensions (for guessing)
_IMAGE_EXTS = {"jpg", "jpeg", "png", "webp", "gif", "bmp", "tif", "tiff"}


def _guess_ext(content_type: str | None, url_path: str) -> str:
    if content_type:
        ext = mimetypes.guess_extension(content_type.split(";", 1)[0].strip())
        if ext:
            return ext.lstrip(".").lower()
    parsed = urlparse(url_path)
    suf = Path(parsed.path).suffix.lower().lstrip(".")
    return suf or "bin"


def _kind_from_content_type(default: MediaKind, content_type: str | None) -> MediaKind:
    if not content_type:
        return default
    ct = content_type.split(";", 1)[0].strip().lower()
    if ct.startswith("image/"):
        return "image"
    if ct.startswith("video/"):
        return "video"
    if ct in {"application/pdf"}:
        return "document"
    return default


def _compute_sha256_file(path: Path) -> str:
    size = path.stat().st_size
    if size <= _SMALL_FILE_THRESHOLD:
        with path.open("rb") as f:
            return _sha256(f.read())
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(_STREAM_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def _headers_for(candidate: MediaCandidate, user_agent: str) -> dict[str, str]:
    hdrs = {"User-Agent": user_agent, "Accept": "*/*", "Connection": "close"}
    if candidate.referer_url:
        hdrs["Referer"] = candidate.referer_url
    return hdrs


def _should_keep(kind: MediaKind, allowed: set[MediaKind] | None) -> bool:
    return allowed is None or kind in allowed


def _looks_like_icon_or_logo(url: str) -> bool:
    low = url.lower()
    if any(s in low for s in _ICON_SUBSTRINGS):
        return True
    parsed = urlparse(low)
    suf = Path(parsed.path).suffix.lstrip(".")
    return suf in _ICON_EXTS


def _prefilter_candidate(
    c: MediaCandidate, allowed: set[MediaKind] | None, min_w_hint: int | None, min_h_hint: int | None, min_bytes_hint: int | None
) -> bool:
    """Cheap pre-download heuristics to avoid obvious junk."""
    if not _should_keep(c.kind, allowed):
        return False

    # If site gave us size hints, use them
    if min_w_hint is not None and c.width_hint is not None and c.width_hint < min_w_hint:
        return False
    if min_h_hint is not None and c.height_hint is not None and c.height_hint < min_h_hint:
        return False
    if min_bytes_hint is not None and c.bytes_hint is not None and c.bytes_hint < min_bytes_hint:
        return False

    # If it looks like an icon/logo and we have no counter-signal, skip
    if _looks_like_icon_or_logo(c.url):
        # Determine the effective hint values, defaulting to 0 if the user supplied None.
        # This is for the *counter-signal* part (e.g., if size hint is large enough to override icon-skip).
        effective_min_w_hint = min_w_hint or 0
        effective_min_h_hint = min_h_hint or 0
        effective_min_bytes_hint = min_bytes_hint or 0

        if not (
            (c.page_index is not None)
            or (c.priority >= 0.5)
            # Use effective hints for comparison against (width_hint or 0) * 2
            or ((c.width_hint or 0) >= (effective_min_w_hint * 2))
            or ((c.height_hint or 0) >= (effective_min_h_hint * 2))
            or ((c.bytes_hint or 0) >= (effective_min_bytes_hint * 2))
        ):
            return False

    return True


def _postfilter_image(
    width: int | None,
    height: int | None,
    bytes_size: int | None,
    *,
    min_w: int | None,
    min_h: int | None,
    min_area: int | None,
    max_aspect: float | None,
) -> bool:
    """
    Return True if the image looks like a real photo (not a tiny icon).
    Only applied when we know it's an image.
    """

    # Default for min_w/min_h is 0 if not specified
    effective_min_w = min_w if min_w is not None else 0
    effective_min_h = min_h if min_h is not None else 0

    if min_area is None:
        min_area = effective_min_w * effective_min_h

    if max_aspect is None or max_aspect < 1.0:
        max_aspect = 4.0

    # If we have dimensions, enforce them
    if width is not None and height is not None:
        if width < effective_min_w or height < effective_min_h:
            return False
        if width * height < min_area:
            return False
        w, h = float(width), float(height)
        ar = max(w, h) / max(1.0, min(w, h))
        if ar > max_aspect:
            return False
        return True
    # No dimensions — fall back to byte size
    return bytes_size >= 30 * 1024 if bytes_size is not None else False


# ---------------------------
# Public API
# ---------------------------


def download_media(
    *,
    candidates: _Iterable[MediaCandidate],
    media_dir: Path,
    policy: FetchPolicy,
    referer: str | None = None,
    # Override policy defaults if desired:
    user_agent: str | None = None,
    timeout_s: float | None = None,
    max_items: int = _DEFAULT_MAX_ITEMS,
    allowed_kinds: set[MediaKind] | None = None,
    # Selection knobs (prefilter based on hints):
    min_width_hint: int | None = None,
    min_height_hint: int | None = None,
    min_bytes_hint: int | None = None,
    # Post-download quality gates (images only):
    min_width: int | None = None,
    min_height: int | None = None,
    min_area: int | None = None,  # ~800x400
    max_aspect_ratio: float = 4.0,
) -> list[MediaAsset]:
    """
    Download media candidates into a deterministic cache directory, respecting FetchPolicy.

    Heuristics to reduce logos/icons:
      - Prefilter by URL (favicon/logo/sprite) unless priority/page_index/size hints say otherwise.
      - Enforce min width/height/area/aspect after probing image dimensions.

    Policy usage:
      - allow_network=False → no downloads (return []).
      - user_agent / timeout_s from `policy` unless overridden.
      - allow_non_200=False → skip saving HTTP >= 400.
    """
    if not policy.allow_network:
        return []

    ua = user_agent or policy.user_agent
    to = float(timeout_s if timeout_s is not None else policy.timeout_s)
    if allowed_kinds is None:
        allowed_kinds = set(_DEFAULT_ALLOWED)

    media_dir.mkdir(parents=True, exist_ok=True)

    # Pre-normalize and keep only allowed kinds, up to max_items
    selected: set[MediaCandidate] = set()
    for c in candidates:
        if _prefilter_candidate(c, allowed_kinds, min_width_hint, min_height_hint, min_bytes_hint):
            selected.add(
                MediaCandidate(
                    url=c.url,
                    kind=c.kind,
                    source=c.source,
                    mime_hint=c.mime_hint,
                    width_hint=c.width_hint,
                    height_hint=c.height_hint,
                    bytes_hint=c.bytes_hint,
                    priority=c.priority,
                    alt_text=c.alt_text,
                    page_index=c.page_index,
                    referer_url=c.referer_url or referer,
                    attributes=c.attributes,
                )
            )
        if len(selected) >= max_items:
            break

    assets: list[MediaAsset] = []

    for cand in selected:
        warnings: list[str] = []
        try:
            resp = requests.get(
                cand.url,
                headers=_headers_for(cand, ua),
                timeout=to,
                stream=True,
            )

            ok = 200 <= resp.status_code < 400
            if not ok and not policy.allow_non_200:
                resp.close()
                continue  # don’t call raise_for_status when allow_non_200=True

            content_type = resp.headers.get("Content-Type")
            final_kind: MediaKind = _kind_from_content_type(cand.kind, content_type)

            if not _should_keep(final_kind, allowed_kinds):
                resp.close()
                continue

            ext = _guess_ext(content_type, cand.url)

            with tempfile.NamedTemporaryFile(prefix="dl_", suffix=".part", delete=False, dir=str(media_dir)) as tf:
                tmp_path = Path(tf.name)
                for chunk in resp.iter_content(chunk_size=_STREAM_CHUNK):
                    if chunk:
                        tf.write(chunk)

            digest = _compute_sha256_file(tmp_path)
            final_path = media_dir / f"{digest}.{ext}"

            if final_path.exists():
                tmp_path.unlink(missing_ok=True)
            else:
                tmp_path.replace(final_path)

            # Optional: drop empty files
            if final_path.stat().st_size < 1024:  # 1 KiB floor
                warnings.append("empty_file")
                try:
                    final_path.unlink(missing_ok=True)
                except Exception as e:
                    warnings.append(f"empty_file_unlink_error:{type(e).__name__}")
                continue

            width = height = None

            is_ct_image = bool(content_type and content_type.split(";", 1)[0].strip().lower().startswith("image/"))
            looks_like_image_ext = ext in _IMAGE_EXTS

            if final_kind in _IMAGE_KINDS and (is_ct_image or looks_like_image_ext):
                try:
                    from PIL import Image  # optional

                    with Image.open(final_path) as im:
                        width, height = int(im.width), int(im.height)
                except Exception as e:
                    warnings.append(f"image_probe_error:{type(e).__name__}")

                # Post-download filtering for images
                if not _postfilter_image(
                    width,
                    height,
                    final_path.stat().st_size,
                    min_w=min_width,
                    min_h=min_height,
                    min_area=min_area,
                    max_aspect=max_aspect_ratio,
                ):
                    # Too small / weird aspect → drop on the floor
                    try:
                        final_path.unlink(missing_ok=True)
                    except Exception as e:
                        warnings.append(f"final_path_unlink_error:{type(e).__name__}")
                    continue

            assets.append(
                MediaAsset(
                    local_path=final_path.resolve(),
                    url=cand.url,
                    kind=final_kind,
                    source=cand.source,
                    content_type=(content_type.split(";", 1)[0].strip() if content_type else None),
                    bytes_size=final_path.stat().st_size,
                    sha256=digest,
                    width=width,
                    height=height,
                    created_at=datetime.now(timezone.utc),
                    warnings=warnings,
                )
            )
        except requests.RequestException:
            continue
        except Exception:
            continue

    resp.close()  # defensive, should be closed by context manager

    return assets
