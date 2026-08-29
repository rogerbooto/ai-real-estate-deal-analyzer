# tests/core/cv/test_onnx_determinism.py
"""
GD-4 (docs/plans/MISSION_3_GATE_D_SECURITY.md): identical inputs must produce identical ONNX-path
artifacts. Reproducibility is an integrity control this project relies on for its
deterministic-core invariant, not a nicety -- a multi-threaded ``InferenceSession`` leaves
floating-point reduction order across threads non-associative, which would make "identical input
-> identical output" not actually hold for a real session.

Two tests, deliberately BOTH required (security's own framing, not redundant):

  1. A BEHAVIOURAL double-run byte-identity check over real inference -- proves the property
     holds for the shipped fixture today.
  2. A ``sess_options``-capture test that monkeypatches ``onnxruntime.InferenceSession`` to
     assert the three pinned fields directly. This is the REVERT-DETECTOR: before the B-1 float32
     fix landed, every real inference call raised and was silently swallowed, so a purely
     behavioural double-run test would have passed VACUOUSLY on empty outputs even with the
     ``SessionOptions`` pin fully reverted (docs/plans/MISSION_3_SPRINT_TRACKER.md's B-2 follow-up
     notes this explicitly). The capture test is the one that actually fails when the pin is
     removed, independent of whether the fixture happens to be thread-insensitive.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import onnxruntime as ort
import pytest
from PIL import Image

from src.core.cv import amenities_defects as ad
from src.core.cv.photo_insights import build_photo_insights
from tests.core.cv._onnx_fixtures import write_classifier_onnx, write_labels_json


@pytest.fixture
def restore_providers() -> Iterator[None]:
    """Snapshot/restore the provider registry so a fake/real ONNX binding cannot leak."""
    saved = dict(ad._PROVIDERS)
    yield
    ad._PROVIDERS.clear()
    ad._PROVIDERS.update(saved)


def _photo(dirpath: Path, name: str, color: tuple[int, int, int]) -> Path:
    dirpath.mkdir(parents=True, exist_ok=True)
    p = dirpath / name
    Image.new("RGB", (900, 700), color=color).save(p, quality=95)
    return p


def test_two_runs_over_the_same_registered_model_produce_byte_identical_detections(tmp_path: Path, restore_providers: None) -> None:
    """Behavioural proof: this genuinely exercises compute now (post B-1), since the fixture
    fires -- a swallowed-and-empty run would not distinguish determinism from a crash."""
    photos_dir = tmp_path / "photos"
    _photo(photos_dir, "mold_basement.jpg", color=(33, 66, 99))
    model_path = write_classifier_onnx(tmp_path / "model.onnx", fire_labels=["mold_suspected"])
    labels_path = write_labels_json(tmp_path / "labels.json")
    ad.register_onnx_provider(str(model_path), str(labels_path))

    pi_first = build_photo_insights(photos_dir)
    pi_second = build_photo_insights(photos_dir)

    dump_first = json.dumps(pi_first.model_dump(), sort_keys=True, default=str)
    dump_second = json.dumps(pi_second.model_dump(), sort_keys=True, default=str)
    assert dump_first == dump_second

    # Not vacuous: real detections were actually produced both times.
    assert pi_first.detections_total > 0
    assert pi_first.detections_total == pi_second.detections_total


def test_the_inference_session_is_constructed_single_threaded_and_sequential(
    tmp_path: Path, restore_providers: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The revert-detector: captures the actual ``sess_options`` object handed to
    ``InferenceSession`` and asserts the three pinned fields, independent of whether the tiny
    fixture model is itself thread-insensitive."""
    model_path = write_classifier_onnx(tmp_path / "model.onnx")
    labels_path = write_labels_json(tmp_path / "labels.json")

    captured: dict[str, Any] = {}
    real_inference_session = ort.InferenceSession

    def _spy_inference_session(path_or_bytes: Any, sess_options: Any = None, **kwargs: Any) -> Any:
        captured["sess_options"] = sess_options
        return real_inference_session(path_or_bytes, sess_options=sess_options, **kwargs)

    monkeypatch.setattr(ort, "InferenceSession", _spy_inference_session)

    ad.register_onnx_provider(str(model_path), str(labels_path))

    assert "sess_options" in captured
    so = captured["sess_options"]
    assert so is not None, "InferenceSession must be constructed with an explicit SessionOptions, not the default"
    assert so.intra_op_num_threads == 1
    assert so.inter_op_num_threads == 1
    assert so.execution_mode == ort.ExecutionMode.ORT_SEQUENTIAL
