# tests/core/cv/test_onnx_label_injection_barrier.py
"""
GD-7 (docs/plans/MISSION_3_GATE_D_SECURITY.md): pin the ontology closed-set as the injection
barrier for user-supplied ``labels.json`` content.

The security review's threat model: a ``labels.json`` a user downloaded, not authored, may declare
anything as a string -- markdown metacharacters, path separators, control characters, an absurdly
long string. Nothing in this codebase's structural design lets such a string reach an artifact,
report, or cache path except by first resolving through ``Ontology.lookup()`` to a canonical name
(``_normalize_candidates`` drops out-of-distribution names; ``_covered_labels`` drops them too; the
cache key is a SHA-256 digest of the declaration, never raw text). This test PINS that barrier
against a refactor that starts echoing declared-but-unresolved capability strings somewhere new.

Uses the established ``_OnnxModel`` monkeypatch pattern (mirrors
``tests/core/cv/test_filename_corroboration.py::test_an_onnx_labels_file_is_the_capability_declaration``)
rather than a real ``.onnx`` file -- what is under test is the ontology resolution barrier, not
onnxruntime's behaviour, and no real inference is needed to prove it.

No exploitable payloads: every string below is hostile-*shaped* (what an ontology-lookup miss
looks like for markdown/path/control-character/long input), not a real XSS/traversal payload --
per this project's rule against committing repro payloads.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from src.core.cv import amenities_defects as ad
from src.core.cv.ontology import AMENITIES_DEFECTS_V1
from src.core.cv.photo_insights import build_photo_insights

#: Hostile-SHAPED, not hostile: no real payload, just the shapes an ontology miss must swallow.
_HOSTILE_LABELS: tuple[str, ...] = (
    "<script>notarealpayload</script>",
    "../../../not/a/real/traversal",
    "a" * 5000,
    "line1\nline2\x00control\x1b[31m",
    "**markdown** [link](not-a-real-scheme://x)",
)

_CANONICAL_LABEL = "mold_suspected"


@pytest.fixture
def restore_providers() -> Iterator[None]:
    saved = dict(ad._PROVIDERS)
    yield
    ad._PROVIDERS.clear()
    ad._PROVIDERS.update(saved)


@pytest.fixture
def mold_photo(tmp_path: Path) -> Path:
    photos = tmp_path / "photos"
    photos.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (900, 700), color=(128, 128, 128)).save(photos / "mold_basement.jpg", quality=95)
    return photos


def _register_hostile_onnx_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """Monkeypatch ``_OnnxModel`` so its ``labels`` declaration AND every per-image finding
    include both the hostile-shaped strings and one canonical label -- exercising the barrier on
    both the DECLARATION path (``_declare_capabilities``) and the per-image EMISSION path
    (``predict_proba`` -> ``_normalize_candidates``)."""

    class _FakeOnnxModel:
        def __init__(self, model_path: str, labels_path: str, **kwargs: Any) -> None:
            self.labels = [*_HOSTILE_LABELS, _CANONICAL_LABEL]

        def predict_proba(self, img: Image.Image) -> list[tuple[str, float]]:
            return [(name, 0.95) for name in self.labels]

    monkeypatch.setattr(ad, "_OnnxModel", _FakeOnnxModel)
    ad.register_onnx_provider("model.onnx", "labels.json")


def test_hostile_shaped_labels_never_reach_photo_insights_output(
    mold_photo: Path, restore_providers: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _register_hostile_onnx_provider(monkeypatch)

    pi = build_photo_insights(mold_photo)
    serialized = json.dumps(pi.model_dump(mode="json"), default=str)

    for hostile in _HOSTILE_LABELS:
        assert hostile not in serialized, f"hostile-shaped label leaked into PhotoInsights output: {hostile!r}"


def test_every_image_detection_name_is_a_member_of_the_closed_ontology(
    mold_photo: Path, restore_providers: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _register_hostile_onnx_provider(monkeypatch)

    pi = build_photo_insights(mold_photo)
    ontology_names = AMENITIES_DEFECTS_V1.all_names()

    all_detections = [d for dets in pi.image_detections.values() for d in dets]
    assert all_detections, "expected at least the canonical mold_suspected detection to survive normalization"
    for det in all_detections:
        assert det.name in ontology_names

    # The canonical label, declared alongside the hostile ones, still reaches the surface --
    # this is not a test that the barrier over-blocks, only that it blocks what it must.
    assert any(det.name == _CANONICAL_LABEL for det in all_detections)


def test_no_cache_path_created_this_run_contains_a_hostile_shaped_label(
    mold_photo: Path, restore_providers: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cache_root = tmp_path / "cache"
    monkeypatch.setenv("AIREDEAL_CACHE_DIR", str(cache_root))
    _register_hostile_onnx_provider(monkeypatch)

    build_photo_insights(mold_photo)

    assert cache_root.exists(), "expected the provider cache to have been populated this run"
    all_paths = [str(p) for p in cache_root.rglob("*")]
    assert all_paths, "expected at least one cache file/dir to exist"
    for hostile in _HOSTILE_LABELS:
        for p in all_paths:
            assert hostile not in p, f"hostile-shaped label leaked into a cache path: {p!r}"


def test_provider_capabilities_declaration_itself_is_not_yet_ontology_filtered(
    mold_photo: Path, restore_providers: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Documents WHERE the filtering actually happens, so this file cannot be satisfied by
    accident: ``provider_capabilities`` (the raw declaration) legitimately still contains the
    hostile-shaped strings -- ``_declare_capabilities`` stores whatever was declared verbatim
    (lower-cased/stripped). The barrier is ``_covered_labels``/``_normalize_candidates`` resolving
    through ``Ontology.lookup`` downstream, which the other three tests in this file pin. If this
    test ever fails, the other three are no longer testing what this docstring says they test."""
    _register_hostile_onnx_provider(monkeypatch)

    raw_declared = ad.provider_capabilities("onnx")
    assert any(h.lower().strip() in raw_declared for h in _HOSTILE_LABELS)
