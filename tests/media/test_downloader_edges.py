# tests/media/test_downloader_edges.py

import io
from pathlib import Path

import requests

from src.core.media.downloader import download_media
from src.schemas.models import FetchPolicy, MediaCandidate

# Minimal valid 1x1 PNG (RGBA). Pillow can open this.
_MINI_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\x0f\x00\x01\x01\x01\x00"
    b"\x18\xdd\x8d\xe1\x00\x00\x00\x00IEND\xaeB`\x82"
)

# Pad to > 30 KiB so _postfilter_image passes even if PIL can't read dimensions
_BIG_PNG = _MINI_PNG + (b"0" * (128 * 128))


class _FakeResp:
    def __init__(self, content: bytes, status: int = 200, headers: dict | None = None):
        self.status_code = status
        self.headers = headers or {}
        self._buf = io.BytesIO(content)

    def iter_content(self, chunk_size=8192):
        while True:
            chunk = self._buf.read(chunk_size)
            if not chunk:
                break
            yield chunk

    def close(self):
        pass


def _mk_candidate(url: str, *, kind: str = "image", bytes_hint: int | None = None):
    # MediaKind is a Literal[str], so pass plain strings like "image"
    return MediaCandidate(url=url, kind=kind, bytes_hint=bytes_hint, referer_url=None)


def test_prefilter_skips_small_files(tmp_path: Path, monkeypatch):
    """
    bytes_hint below min_bytes_hint is skipped before any HTTP call.
    Only the 'big' candidate should be requested and saved.
    """
    cands = [
        _mk_candidate("https://example.com/small.png", bytes_hint=500),
        _mk_candidate("https://example.com/big.png", bytes_hint=5000),
    ]

    def fake_get(url, *a, **k):
        # Should only be called for the big one
        assert url.endswith("big.png")
        return _FakeResp(_BIG_PNG, headers={"Content-Type": "image/png"})

    monkeypatch.setattr(requests, "get", fake_get)

    assets = download_media(
        candidates=cands,
        media_dir=tmp_path,
        policy=FetchPolicy(allow_network=True),
        min_bytes_hint=1000,  # skip 'small.png'
    )

    assert len(assets) == 1
    assert assets[0].url.endswith("big.png")
    assert assets[0].kind == "image"
    assert assets[0].content_type == "image/png"
    assert assets[0].path.exists()


def test_bad_content_type_is_rejected(tmp_path: Path, monkeypatch):
    """
    A clearly non-media content-type (text/html) with small bytes should be dropped
    by image postfilter (no dimensions, <30 KiB fallback).
    """
    cands = [_mk_candidate("https://example.com/notmedia.jpg", bytes_hint=5000)]

    def fake_get(url, *a, **k):
        return _FakeResp(b"<html>oops</html>", headers={"Content-Type": "text/html"})

    monkeypatch.setattr(requests, "get", fake_get)

    assets = download_media(
        candidates=cands,
        media_dir=tmp_path,
        policy=FetchPolicy(allow_network=True),
    )
    assert len(assets) == 0


def test_duplicate_url_dedupes(tmp_path: Path, monkeypatch):
    """
    Two identical URLs with different hints are deduped at the candidate set level
    (MediaCandidate.__hash__/__eq__ is based on (url, kind, source)).
    """
    url = "https://example.com/dup.png"
    cands = [_mk_candidate(url, bytes_hint=5000), _mk_candidate(url, bytes_hint=6000)]

    def fake_get(u, *a, **k):
        return _FakeResp(_BIG_PNG, headers={"Content-Type": "image/png"})

    monkeypatch.setattr(requests, "get", fake_get)

    assets = download_media(
        candidates=cands,
        media_dir=tmp_path,
        policy=FetchPolicy(allow_network=True),
    )
    assert len(assets) == 1
    assert assets[0].url == url
    assert assets[0].path.exists()
