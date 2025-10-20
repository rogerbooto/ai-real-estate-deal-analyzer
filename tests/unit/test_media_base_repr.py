# tests/unit/test_media_base_repr.py
from datetime import datetime, timezone
from pathlib import Path

from src.schemas.models import MediaAsset


def test_mediaasset_repr_and_equality(tmp_path: Path):
    p = tmp_path / "a.png"
    p.write_bytes(b"1234" * 300)
    a = MediaAsset(
        local_path=p,
        url="u",
        kind="image",
        source="html",
        content_type="image/png",
        bytes_size=p.stat().st_size,
        sha256="a" * 64,
        width=None,
        height=None,
        created_at=datetime.now(timezone.utc),
        warnings=[],
    )
    r = repr(a)
    assert "MediaAsset" in r and "image" in r
