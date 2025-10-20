# tests/listing/test_photo_insights_emptydir.py
from src.core.cv.photo_insights import build_photo_insights


def test_photo_insights_empty_dir(tmp_path):
    ins = build_photo_insights(tmp_path)
    assert ins.room_counts == {}
