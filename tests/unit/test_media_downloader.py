# tests/unit/test_media_downloader.py
from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from src.core.fetch.cache import _sha256
from src.core.media.downloader import download_media
from src.schemas.models import (
    FetchPolicy,  # use real policy to drive UA/timeout/allow_non_200
    MediaCandidate,
)


class _FakeResp:
    def __init__(self, *, status: int, headers: dict[str, str], body: bytes, chunk: int = 1024):
        self.status_code = status
        self.headers = headers
        self._body = body
        self._chunk = chunk
        self._idx = 0

    def iter_content(self, chunk_size: int = 1024) -> Iterable[bytes]:
        # Stream body in chunks to exercise streaming path
        sz = max(chunk_size, self._chunk)
        for i in range(0, len(self._body), sz):
            yield self._body[i : i + sz]

    def close(self) -> None:  # requests API compat
        pass

    def raise_for_status(self) -> None:
        # real downloader only uses this when policy.allow_non_200 = False
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(f"HTTP {self.status_code}")


def test_download_image_success(monkeypatch, tmp_path: Path, png_bytes) -> None:
    # --- Arrange: fake PNG response and capture headers
    png = png_bytes(64, 64)
    content_type = "image/png"
    digest = _sha256(png)
    seen_headers: dict[str, str] | None = None

    def fake_get(url: str, *, headers: dict[str, str], timeout: float, stream: bool):
        nonlocal seen_headers
        seen_headers = dict(headers)
        assert stream is True
        assert "User-Agent" in headers
        return _FakeResp(status=200, headers={"Content-Type": content_type}, body=png, chunk=2)

    monkeypatch.setattr("src.core.media.downloader.requests.get", fake_get)

    # Candidate + policy + media dir
    cand = MediaCandidate(
        url="https://cdn.example.com/a.png",
        kind="image",
        source="html",
        mime_hint=None,
        referer_url="https://example.com/listing/123",
    )
    media_dir = tmp_path / "media"
    policy = FetchPolicy(
        allow_network=True,
        allow_non_200=False,
        timeout_s=7.5,
        user_agent="TestAgent/1.0",
        cache_dir=tmp_path,  # not used directly by downloader, but required by model
    )

    # --- Act
    assets = download_media(
        candidates=[cand],
        media_dir=media_dir,
        policy=policy,
        # leave allowed_kinds=None to use defaults that include images
    )

    # --- Assert
    assert seen_headers is not None
    assert seen_headers.get("Referer") == "https://example.com/listing/123"
    assert (media_dir).exists()

    # exactly one asset
    assert len(assets) == 1
    a = assets[0]

    # content-addressed filename + metadata
    assert a.local_path.exists()
    assert a.local_path.parent == media_dir
    assert a.local_path.name.startswith(digest)
    assert a.local_path.suffix == ".png"
    assert a.sha256 == digest
    assert a.bytes_size == a.local_path.stat().st_size
    assert a.content_type == "image/png"
    assert a.kind == "image"
    assert a.width == 64 and a.height == 64
    # timestamp sanity (UTC-ish)
    assert isinstance(a.created_at, datetime)


def test_coercion_pre_request_filters_declared_kind(monkeypatch, tmp_path: Path, png_bytes) -> None:
    """
    PRE-REQUEST filter: If the candidate's *declared* kind is not in allowed_kinds,
    the downloader must NOT issue any HTTP request.
    """
    # Any fake image; we should never download it
    png = png_bytes(64, 64)

    called = {"get": False}

    def fake_get(*args, **kwargs):
        called["get"] = True
        # If code mistakenly calls, return a valid response anyway
        return _FakeResp(status=200, headers={"Content-Type": "image/png"}, body=png, chunk=1)

    monkeypatch.setattr("src.core.media.downloader.requests.get", fake_get)

    candidate = MediaCandidate(
        url="https://cdn.example.com/declared-document.jpg",
        kind="document",  # DECLARED kind (pre-filter should reject)
        source="html",
    )
    media_dir = tmp_path / "media"
    policy = FetchPolicy(
        allow_network=True,
        allow_non_200=True,
        timeout_s=5.0,
        user_agent="Test/1.0",
        cache_dir=tmp_path,
    )

    # Exclude the declared "document" (and image); only allow videos to ensure pre-filter blocks
    assets = download_media(
        candidates=[candidate],
        media_dir=media_dir,
        policy=policy,
        allowed_kinds={"video"},  # "document" is NOT allowed -> no request should happen
        referer="https://example.com/fallback",
    )

    assert assets == []
    assert called["get"] is False, "HTTP request should not have been made due to pre-request filtering"
    assert not media_dir.exists() or not any(media_dir.iterdir()), "No files should have been created"


def test_coercion_post_response_skips_after_content_type_coercion(monkeypatch, tmp_path: Path, png_bytes) -> None:
    """
    POST-RESPONSE coercion: If the server returns Content-Type that coerces the kind
    to a disallowed category, the downloader should make the request (pre-filter passes)
    but skip creating an asset AFTER coercion.
    """
    png = png_bytes(64, 64)
    last_headers: dict[str, str] | None = None

    def fake_get(url: str, *, headers: dict[str, str], timeout: float, stream: bool):
        nonlocal last_headers
        last_headers = dict(headers)
        return _FakeResp(status=200, headers={"Content-Type": "image/png"}, body=png, chunk=1)

    monkeypatch.setattr("src.core.media.downloader.requests.get", fake_get)

    candidate = MediaCandidate(
        url="https://cdn.example.com/coerced-from-doc.jpg",
        kind="document",  # allowed initially...
        source="html",
    )

    media_dir = tmp_path / "media"
    policy = FetchPolicy(
        allow_network=True,
        allow_non_200=True,
        timeout_s=5.0,
        user_agent="Test/1.0",
        cache_dir=tmp_path,
    )

    # Allow 'document' so the HTTP request occurs, but NOT 'image'.
    # Response returns Content-Type image/png -> coerces to 'image' -> disallowed -> skip.
    assets = download_media(
        candidates=[candidate],
        media_dir=media_dir,
        policy=policy,
        allowed_kinds={"video", "document"},
        referer="https://example.com/fallback",
    )

    # Asset skipped after coercion
    assert assets == []

    # Request WAS made; fallback referer applied (candidate had none)
    assert last_headers is not None
    assert last_headers.get("Referer") == "https://example.com/fallback"
    assert last_headers.get("User-Agent") == "Test/1.0"

    # No files created
    assert not media_dir.exists() or not any(media_dir.iterdir()), "No files should have been created"


def test_skip_small_file_after_download(monkeypatch, tmp_path: Path):
    # Return a <1KiB body to trigger "empty_file" drop
    body = b"x" * 512

    class _R:
        status_code = 200
        headers = {"Content-Type": "image/png"}

        def iter_content(self, chunk_size=1024):
            yield body

        def close(self):
            pass

    monkeypatch.setattr("src.core.media.downloader.requests.get", lambda *a, **k: _R())
    assets = download_media(
        candidates=[MediaCandidate(url="u", kind="image", source="html")],
        media_dir=tmp_path / "m",
        policy=FetchPolicy(allow_network=True, timeout_s=1.0, user_agent="t", cache_dir=tmp_path),
    )
    assert assets == []


def test_network_disabled_skips_requests(monkeypatch, tmp_path: Path):
    called = {"get": False}

    def fake_get(*a, **k):
        called["get"] = True
        return _FakeResp(200, {"Content-Type": "image/png"})

    monkeypatch.setattr("src.core.media.downloader.requests.get", fake_get)

    cand = MediaCandidate(url="https://x/img.png", kind="image", source="html")
    assets = download_media(
        candidates=[cand],
        media_dir=tmp_path / "m",
        policy=FetchPolicy(allow_network=False, allow_non_200=False, timeout_s=3.0, user_agent="UA", cache_dir=tmp_path),
    )
    assert assets == []
    assert called["get"] is False


def test_non_200_with_allow_non_200_true(monkeypatch, tmp_path: Path):
    def fake_get(*a, **k):
        return _FakeResp(404, {"Content-Type": "image/png"})

    monkeypatch.setattr("src.core.media.downloader.requests.get", fake_get)

    cand = MediaCandidate(url="https://x/miss.png", kind="image", source="html")
    assets = download_media(
        candidates=[cand],
        media_dir=tmp_path / "m",
        policy=FetchPolicy(allow_network=True, allow_non_200=True, timeout_s=3.0, user_agent="UA", cache_dir=tmp_path),
    )
    # Should be skipped (no crash) when 404 allowed
    assert assets == []


def test_content_type_filtered_post_response(monkeypatch, tmp_path: Path):
    # Response advertises video, while only images allowed -> must skip
    def fake_get(*a, **k):
        return _FakeResp(200, {"Content-Type": "video/mp4"})

    monkeypatch.setattr("src.core.media.downloader.requests.get", fake_get)

    cand = MediaCandidate(url="https://x/a.mp4", kind="document", source="html")  # declared doc, coerces to video
    assets = download_media(
        candidates=[cand],
        media_dir=tmp_path / "m",
        policy=FetchPolicy(allow_network=True, allow_non_200=True, timeout_s=3.0, user_agent="UA", cache_dir=tmp_path),
        allowed_kinds={"image"},  # images only
    )
    assert assets == []  # skipped after coercion
