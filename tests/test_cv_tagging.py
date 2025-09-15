# tests/test_cv_tagging.py
from pathlib import Path

from src.tools.cv_tagging import tag_images_in_folder, summarize_cv_tags


def test_tagging_and_summary(tmp_path: Path):
    # Create fake images with informative filenames
    (tmp_path / "kitchen_updated.jpg").write_bytes(b"")
    (tmp_path / "basement_mold.png").write_bytes(b"")
    (tmp_path / "roof_leak.JPG").write_bytes(b"")
    (tmp_path / "README.txt").write_text("ignore")  # non-image, ignored

    tags_by_file = tag_images_in_folder(str(tmp_path))

    # We should only tag the 3 images
    assert set(tags_by_file.keys()) == {"basement_mold.png", "kitchen_updated.jpg", "roof_leak.JPG"}

    # Spot-check individual files
    assert "kitchen" in tags_by_file["kitchen_updated.jpg"]
    assert "cond:updated kitchen" in tags_by_file["kitchen_updated.jpg"]

    assert "basement" in tags_by_file["basement_mold.png"]
    assert "defect:mold" in tags_by_file["basement_mold.png"]

    assert "roof" in tags_by_file["roof_leak.JPG"]
    assert "defect:roof leak" in tags_by_file["roof_leak.JPG"]

    # Aggregate into condition/defects buckets
    summary = summarize_cv_tags(tags_by_file)
    assert "updated kitchen" in summary["condition_tags"]
    assert "mold" in summary["defects"]
    assert "roof leak" in summary["defects"]


def test_empty_folder_returns_empty(tmp_path: Path):
    # No images -> empty results
    tags_by_file = tag_images_in_folder(str(tmp_path))
    assert tags_by_file == {}

    summary = summarize_cv_tags(tags_by_file)
    assert summary["condition_tags"] == set()
    assert summary["defects"] == set()
