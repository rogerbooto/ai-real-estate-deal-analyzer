# tests/core/media/test_local_assets.py
"""``collect_local_assets`` — the bridge that let local photo folders reach the media layer.

``analyze_media`` consumes ``MediaAsset`` records, which previously only the downloader could
produce. The deterministic ``main.py`` path has no download step, so its photo folder was
invisible to the media layer and the report's Media Overview was unreachable.

Determinism matters here: the report embeds sha256 and pixel stats, so these must be stable
and content-derived.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from src.core.media.local import collect_local_assets


def _write_image(path: Path, size: tuple[int, int], colour: str = "red") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, colour).save(path)


def test_missing_folder_yields_no_assets_rather_than_raising(tmp_path: Path) -> None:
    # The photo folder is optional on every caller; a missing one must not kill a run.
    assert collect_local_assets(tmp_path / "nope") == []


def test_empty_folder_yields_no_assets(tmp_path: Path) -> None:
    assert collect_local_assets(tmp_path) == []


def test_collects_images_with_content_derived_metadata(tmp_path: Path) -> None:
    _write_image(tmp_path / "a.jpg", (640, 480))
    _write_image(tmp_path / "b.png", (100, 200))

    assets = collect_local_assets(tmp_path)

    assert [a.local_path.name for a in assets] == ["a.jpg", "b.png"], "not in sorted path order"
    by_name = {a.local_path.name: a for a in assets}
    assert (by_name["a.jpg"].width, by_name["a.jpg"].height) == (640, 480)
    assert (by_name["b.png"].width, by_name["b.png"].height) == (100, 200)
    assert by_name["a.jpg"].content_type == "image/jpeg"
    assert by_name["b.png"].content_type == "image/png"
    for a in assets:
        assert a.kind == "image"
        assert a.bytes_size > 0
        assert len(a.sha256) == 64


def test_non_images_and_zero_byte_placeholders_are_skipped(tmp_path: Path) -> None:
    _write_image(tmp_path / "real.jpg", (10, 10))
    (tmp_path / "notes.txt").write_text("not an image", encoding="utf-8")
    (tmp_path / "placeholder.jpg").write_bytes(b"")  # zero-byte stub carries no signal

    names = [a.local_path.name for a in collect_local_assets(tmp_path)]
    assert names == ["real.jpg"]


def test_unreadable_image_is_warned_not_dropped(tmp_path: Path) -> None:
    (tmp_path / "broken.jpg").write_bytes(b"definitely not a jpeg")

    assets = collect_local_assets(tmp_path)

    assert len(assets) == 1
    assert assets[0].width is None and assets[0].height is None
    assert any("unreadable" in w for w in assets[0].warnings)


def test_recursion_can_be_disabled(tmp_path: Path) -> None:
    _write_image(tmp_path / "top.jpg", (10, 10))
    _write_image(tmp_path / "sub" / "nested.jpg", (10, 10))

    assert len(collect_local_assets(tmp_path, recursive=True)) == 2
    assert [a.local_path.name for a in collect_local_assets(tmp_path, recursive=False)] == ["top.jpg"]


def test_repeat_calls_are_identical(tmp_path: Path) -> None:
    _write_image(tmp_path / "a.jpg", (32, 32))
    _write_image(tmp_path / "b.jpg", (64, 64))

    first = collect_local_assets(tmp_path)
    second = collect_local_assets(tmp_path)

    assert [(a.local_path, a.sha256, a.width, a.height) for a in first] == [(a.local_path, a.sha256, a.width, a.height) for a in second]
