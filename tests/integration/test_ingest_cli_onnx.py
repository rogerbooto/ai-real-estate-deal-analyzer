# tests/integration/test_ingest_cli_onnx.py
"""
Mission 3 — bring-your-own ONNX provider, `ingest-listing --onnx-model/--onnx-labels`.

Exercises the REAL path end-to-end (real ``onnxruntime.InferenceSession``, no monkeypatched
``_OnnxModel``): CLI flags/env -> ``register_onnx_provider`` -> ``build_photo_insights`` selection
-> ``tag_amenities_and_defects`` -> ``_augment_from_filename``. This is deliberately the FIRST
layer of coverage for the real registration/inference path (the registry-mechanics tests in
``tests/core/cv/test_filename_corroboration.py`` and ``tests/ai/test_ai_onnx_registration.py``
monkeypatch ``_OnnxModel`` -- they prove the *declaration* travels, not that the CLI *selection*
seam wires a real model in).

Guardian Condition 4 (``docs/plans/MISSION_3_GATE_D_GUARDIAN.md``): the six-label unlock is
detector-**adjudicated** -- confirmed OR contested -- never flatly "confirmed". This file proves
BOTH outcomes with fixtures engineered (the biased-output-unit technique,
``tests/core/cv/_onnx_fixtures.py``) to guarantee each one, and names the tests accordingly.

Registry pollution: every test that registers a provider uses ``restore_providers`` (autouse in
this file -- essentially every test here calls ``ingest_cli.main`` with ``--onnx-model``, which
mutates the process-global ``src.core.cv.amenities_defects._PROVIDERS``). Mirrors the pattern
already established in ``tests/core/cv/test_filename_corroboration.py``.

Cache pollution: ``.cache/cv`` is keyed by (provider, capability fingerprint, image sha256), NOT
by filename (``docs/plans/MISSION_3_SPRINT_TRACKER.md``'s I.1 cache-pollution note). Every test
below uses a genuinely distinct synthetic image (varied size/colour) rather than a renamed copy of
another fixture's photo, and relies on ``tests/conftest.py``'s autouse ``_isolate_cv_cache``
fixture for a fresh per-test cache root -- never a scratch dir shared across tests, and never
overridden inside a byte-identity assertion (the cache root is echoed into
``provenance["cache_root"]`` and therefore into report bytes).
"""

from __future__ import annotations

import builtins
import json
import os
import signal
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

import src.cli.ingest_cli as ingest_cli
from src.core.cv import amenities_defects as ad
from src.core.reports.generator import generate_report
from src.core.reports.photo_report import build_media_report
from src.schemas.models import ListingInsights
from tests.core.cv._onnx_fixtures import (
    ONNX_BYO_LABELS,
    write_classifier_onnx,
    write_corrupt_model,
    write_deeply_nested_labels_json,
    write_labels_json,
    write_non_float_classifier_onnx,
    write_oversize_labels_json,
)
from tests.utils import make_minimal_forecast

SAMPLE_LISTING = Path("data/sample_listings/36_kelly_moncton/listing.txt")

pytestmark = pytest.mark.usefixtures("restore_providers", "_clear_onnx_env")


@pytest.fixture
def restore_providers() -> Iterator[None]:
    """Snapshot/restore the provider registry so a real ONNX registration cannot leak."""
    saved = dict(ad._PROVIDERS)
    yield
    ad._PROVIDERS.clear()
    ad._PROVIDERS.update(saved)


@pytest.fixture
def _clear_onnx_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test starts with neither AIREAL_ONNX_MODEL nor AIREAL_ONNX_LABELS set, regardless of
    what a developer's shell happens to export -- precedence tests then set exactly what they
    need."""
    monkeypatch.delenv("AIREAL_ONNX_MODEL", raising=False)
    monkeypatch.delenv("AIREAL_ONNX_LABELS", raising=False)


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    rc = ingest_cli.main(argv)
    captured = capsys.readouterr()
    return rc, captured.out, captured.err


def _photo(dirpath: Path, name: str, color: tuple[int, int, int]) -> Path:
    """A distinctly-coloured synthetic image, large enough to survive the photo sanity filters.

    Blank on purpose (mirrors ``tests/core/cv/test_filename_corroboration.py``'s ``_photo()``):
    the point of every test in this file is the FILE NAME plus the fixture's engineered
    fire/silent bias, never the pixel content -- and a distinct colour per test keeps images from
    two different tests from ever sharing a sha256 (the cache key), even though
    ``_isolate_cv_cache`` already gives each test its own cache root.
    """
    dirpath.mkdir(parents=True, exist_ok=True)
    p = dirpath / name
    Image.new("RGB", (900, 700), color=color).save(p, quality=95)
    return p


# ---------------------------------------------------------------------------
# Six-label unlock, end-to-end through the real CLI seam (Guardian Condition 4:
# detector-ADJUDICATED -- both outcomes proven, neither asserted as the only one)
# ---------------------------------------------------------------------------


def test_onnx_registration_via_cli_confirms_a_filename_hint_end_to_end(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A model whose labels.json declares mold_suspected AND whose output unit for it is biased
    to fire (regardless of pixels) moves the filename hint from `filename_unconfirmed` to
    `filename_confirmed` -- a real per-image inference result, not just a declaration."""
    photos_dir = tmp_path / "photos"
    _photo(photos_dir, "mold_basement.jpg", color=(10, 10, 10))
    model_path = write_classifier_onnx(tmp_path / "model.onnx", fire_labels=["mold_suspected"])
    labels_path = write_labels_json(tmp_path / "labels.json")

    rc, out, err = _run(
        [
            "--file",
            str(SAMPLE_LISTING),
            "--photos",
            str(photos_dir),
            "--onnx-model",
            str(model_path),
            "--onnx-labels",
            str(labels_path),
            "--pretty",
            "0",
        ],
        capsys,
    )
    assert rc == 0
    assert "note: onnx provider registered" in err

    # 1) selection actually reached "onnx", not "vision"/"local":
    assert ad.is_provider_registered("onnx")
    assert ad.provider_kind("onnx") == "model"

    # 2) the flip itself: import fresh so we read exactly what the CLI produced, not a stale
    # in-process object.
    from src.core.cv.photo_insights import ONNX_BYO_VERSION, build_photo_insights

    pi = build_photo_insights(photos_dir)
    assert pi.provenance["selected_provider"] == "onnx"
    assert pi.provenance["provider_kind"] == "model"
    assert pi.version == ONNX_BYO_VERSION

    mold_dets = [d for dets in pi.image_detections.values() for d in dets if d.name == "mold_suspected"]
    assert len(mold_dets) == 1
    assert mold_dets[0].source == "filename_confirmed"
    assert mold_dets[0].confidence is not None
    assert mold_dets[0].confidence > 0.9  # 0.7 * (~0.9997 fired) + 0.3

    # Never "unconfirmed" for this image once a covering detector actually fired.
    assert "mold_suspected" not in pi.unconfirmed_hint_counts
    assert "mold_suspected" not in pi.contested_hint_counts

    # 3) no ontology/schema change was needed -- implicit: nothing above imported anything new
    # from src.schemas.models or src.core.cv.ontology.


def test_onnx_registration_via_cli_contests_a_filename_hint_end_to_end(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A model whose labels.json declares mold_suspected but whose output unit for it is biased
    SILENT (never fires, regardless of pixels) moves the filename hint from
    `filename_unconfirmed` to `filename_contested` -- the OTHER honest outcome of "something
    looked": a real detector examined the image and disagreed with the file name. This is the
    branch Guardian Condition 4 forbids omitting: declaring coverage alone must never be
    indistinguishable from a real "confirmed" finding."""
    photos_dir = tmp_path / "photos"
    _photo(photos_dir, "mold_basement_corner.jpg", color=(220, 220, 220))
    model_path = write_classifier_onnx(tmp_path / "model.onnx", fire_labels=[])  # every unit silent
    labels_path = write_labels_json(tmp_path / "labels.json")

    rc, _out, err = _run(
        [
            "--file",
            str(SAMPLE_LISTING),
            "--photos",
            str(photos_dir),
            "--onnx-model",
            str(model_path),
            "--onnx-labels",
            str(labels_path),
            "--pretty",
            "0",
        ],
        capsys,
    )
    assert rc == 0
    assert "note: onnx provider registered" in err

    from src.core.cv.photo_insights import ONNX_BYO_VERSION, build_photo_insights

    pi = build_photo_insights(photos_dir)
    assert pi.provenance["selected_provider"] == "onnx"
    assert pi.provenance["provider_kind"] == "model"
    assert pi.version == ONNX_BYO_VERSION

    # A contested claim never reaches image_detections/defect_counts (R-6/G2-N1: it still moves
    # no money) -- it surfaces only in contested_hint_counts.
    mold_dets = [d for dets in pi.image_detections.values() for d in dets if d.name == "mold_suspected"]
    assert mold_dets == []
    assert pi.defect_counts.get("mold_suspected", 0) == 0
    assert pi.contested_hint_counts.get("mold_suspected") == 1
    assert "mold_suspected" not in pi.unconfirmed_hint_counts


def test_six_labels_declared_are_exactly_the_filename_rule_set() -> None:
    """Pins the six-label set itself against silent drift (spec §6.2's narrower unit-level
    check): if a future edit to `_FILENAME_RULES` added/removed a rule, this fails, flagging that
    the "six labels" claim needs re-verification -- independent of any CLI/ONNX machinery."""
    from src.core.cv.runner import _FILENAME_RULES

    assert {r.label for r in _FILENAME_RULES} == set(ONNX_BYO_LABELS)


# ---------------------------------------------------------------------------
# Provenance end-to-end: reaches the generated report, not just the in-memory object
# ---------------------------------------------------------------------------


def test_onnx_provenance_reaches_the_generated_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    photos_dir = tmp_path / "photos"
    _photo(photos_dir, "dishwasher_kitchen.jpg", color=(40, 90, 140))
    model_path = write_classifier_onnx(tmp_path / "model.onnx", fire_labels=["dishwasher"])
    labels_path = write_labels_json(tmp_path / "labels.json")

    rc, _out, _err = _run(
        [
            "--file",
            str(SAMPLE_LISTING),
            "--photos",
            str(photos_dir),
            "--onnx-model",
            str(model_path),
            "--onnx-labels",
            str(labels_path),
            "--pretty",
            "0",
        ],
        capsys,
    )
    assert rc == 0

    from src.core.cv.photo_insights import build_photo_insights

    pi = build_photo_insights(photos_dir)
    media_report = build_media_report(pi)
    md = generate_report(ListingInsights(address="36 Kelly"), make_minimal_forecast(), None, media_report=media_report)

    assert "| Photo pipeline — selected_provider | onnx |" in md
    assert "| Photo pipeline — provider_kind | model |" in md
    assert "version `onnx-byo-v1`" in md


# ---------------------------------------------------------------------------
# Error paths -- clean SystemExit, no raw traceback, correct attribution
# ---------------------------------------------------------------------------


def test_missing_onnxruntime_is_a_clean_error_not_a_traceback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`onnxruntime` IS installed in this environment (a hard, unconditional runtime dependency
    per docs/plans/MISSION_3_DISCOVERY_SPEC.md §0.1) -- its absence is only reachable by shimming
    the import itself, not by uninstalling anything."""
    model_path = write_classifier_onnx(tmp_path / "model.onnx")
    labels_path = write_labels_json(tmp_path / "labels.json")

    real_import = builtins.__import__

    def _fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "onnxruntime":
            raise ImportError("simulated missing onnxruntime")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    with pytest.raises(SystemExit) as excinfo:
        ingest_cli.main(
            ["--file", str(SAMPLE_LISTING), "--onnx-model", str(model_path), "--onnx-labels", str(labels_path), "--pretty", "0"]
        )
    assert excinfo.value.code != 0
    msg = str(excinfo.value.code)
    assert "--onnx-model" in msg
    assert "onnxruntime not available" in msg


def test_corrupt_model_file_is_a_clean_error_not_a_traceback(tmp_path: Path) -> None:
    model_path = write_corrupt_model(tmp_path / "corrupt.onnx")
    labels_path = write_labels_json(tmp_path / "labels.json")

    with pytest.raises(SystemExit) as excinfo:
        ingest_cli.main(
            ["--file", str(SAMPLE_LISTING), "--onnx-model", str(model_path), "--onnx-labels", str(labels_path), "--pretty", "0"]
        )
    assert excinfo.value.code != 0
    msg = str(excinfo.value.code)
    assert "--onnx-model" in msg
    assert "failed to load ONNX model" in msg


def test_labels_json_not_valid_json_is_a_clean_error(tmp_path: Path) -> None:
    model_path = write_classifier_onnx(tmp_path / "model.onnx")
    labels_path = tmp_path / "labels.json"
    labels_path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(SystemExit) as excinfo:
        ingest_cli.main(
            ["--file", str(SAMPLE_LISTING), "--onnx-model", str(model_path), "--onnx-labels", str(labels_path), "--pretty", "0"]
        )
    assert excinfo.value.code != 0
    msg = str(excinfo.value.code)
    assert "--onnx-labels" in msg
    assert "not valid JSON" in msg


def test_labels_json_empty_object_is_a_clean_error(tmp_path: Path) -> None:
    model_path = write_classifier_onnx(tmp_path / "model.onnx")
    labels_path = tmp_path / "labels.json"
    labels_path.write_text("{}", encoding="utf-8")

    with pytest.raises(SystemExit) as excinfo:
        ingest_cli.main(
            ["--file", str(SAMPLE_LISTING), "--onnx-model", str(model_path), "--onnx-labels", str(labels_path), "--pretty", "0"]
        )
    assert excinfo.value.code != 0
    msg = str(excinfo.value.code)
    assert "--onnx-labels" in msg
    assert "non-empty 'labels' list" in msg


@pytest.mark.parametrize("root", [["mold_suspected"], "oops", 42])
def test_labels_json_non_dict_root_is_a_clean_error_not_an_attributeerror(tmp_path: Path, root: object) -> None:
    """GD-2: a labels.json that parses as JSON but isn't object-rooted must funnel into the same
    clean ValueError-derived message as an empty dict, never a raw AttributeError from
    `.get()` on a non-dict (docs/plans/MISSION_3_DISCOVERY_SPEC.md §0.3,
    docs/plans/MISSION_3_GATE_D_SECURITY.md GD-2 — fixed in `_OnnxModel.__init__` itself, so no
    CLI `except AttributeError` clause exists to bypass)."""
    model_path = write_classifier_onnx(tmp_path / "model.onnx")
    labels_path = tmp_path / "labels.json"
    labels_path.write_text(json.dumps(root), encoding="utf-8")

    with pytest.raises(SystemExit) as excinfo:
        ingest_cli.main(
            ["--file", str(SAMPLE_LISTING), "--onnx-model", str(model_path), "--onnx-labels", str(labels_path), "--pretty", "0"]
        )
    assert excinfo.value.code != 0
    msg = str(excinfo.value.code)
    assert "--onnx-labels" in msg
    assert "non-empty 'labels' list" in msg


def test_register_onnx_provider_rejects_non_dict_labels_root_at_the_api(tmp_path: Path) -> None:
    """The core-level fix (GD-2 ruling B): every caller of `register_onnx_provider`, not just the
    CLI, must get a clean ValueError -- this is the API-level regression test the ruling requires,
    independent of ingest_cli's error-message wrapping."""
    model_path = write_classifier_onnx(tmp_path / "model.onnx")
    labels_path = tmp_path / "labels.json"
    labels_path.write_text(json.dumps(["mold_suspected"]), encoding="utf-8")

    with pytest.raises(ValueError, match="non-empty 'labels' list"):
        ad.register_onnx_provider(str(model_path), str(labels_path))


def test_deeply_nested_labels_names_the_labels_file_not_the_model(tmp_path: Path) -> None:
    """GD-3: RecursionError subclasses RuntimeError, so it must be caught BEFORE the broad
    `except RuntimeError` clause or a deeply-nested labels.json gets misattributed to
    --onnx-model."""
    model_path = write_classifier_onnx(tmp_path / "model.onnx")
    labels_path = write_deeply_nested_labels_json(tmp_path / "nested.json")
    assert labels_path.stat().st_size < 1_048_576  # must clear the GD-1 size gate to reach GD-3

    with pytest.raises(SystemExit) as excinfo:
        ingest_cli.main(
            ["--file", str(SAMPLE_LISTING), "--onnx-model", str(model_path), "--onnx-labels", str(labels_path), "--pretty", "0"]
        )
    assert excinfo.value.code != 0
    msg = str(excinfo.value.code)
    assert "--onnx-labels" in msg
    assert "--onnx-model" not in msg
    assert "nested too deeply" in msg


def test_oversize_labels_file_is_rejected_before_it_is_opened(tmp_path: Path) -> None:
    """GD-1: a labels.json over 1 MiB is implausible and rejected by a cheap stat() check, before
    `open()`/`json.load()` ever run on it."""
    model_path = write_classifier_onnx(tmp_path / "model.onnx")
    labels_path = write_oversize_labels_json(tmp_path / "big_labels.json")

    with pytest.raises(SystemExit) as excinfo:
        ingest_cli.main(
            ["--file", str(SAMPLE_LISTING), "--onnx-model", str(model_path), "--onnx-labels", str(labels_path), "--pretty", "0"]
        )
    assert excinfo.value.code != 0
    msg = str(excinfo.value.code)
    assert "--onnx-labels" in msg
    assert "implausibly large" in msg


@pytest.mark.parametrize("flag_name", ["--onnx-model", "--onnx-labels"])
def test_a_directory_is_rejected_as_not_a_regular_file(tmp_path: Path, flag_name: str) -> None:
    """GD-1: Path.is_file() (unlike .exists()) is False for a directory -- closes this class
    before either path is ever opened."""
    model_path = write_classifier_onnx(tmp_path / "model.onnx")
    labels_path = write_labels_json(tmp_path / "labels.json")
    a_directory = tmp_path / "a_directory"
    a_directory.mkdir()

    argv = ["--file", str(SAMPLE_LISTING), "--pretty", "0"]
    if flag_name == "--onnx-model":
        argv += ["--onnx-model", str(a_directory), "--onnx-labels", str(labels_path)]
    else:
        argv += ["--onnx-model", str(model_path), "--onnx-labels", str(a_directory)]

    with pytest.raises(SystemExit) as excinfo:
        ingest_cli.main(argv)
    assert excinfo.value.code != 0
    msg = str(excinfo.value.code)
    assert flag_name in msg
    assert "not a regular file" in msg


@pytest.mark.skipif(os.name != "posix", reason="mkfifo is a POSIX-only mechanism")
def test_a_fifo_labels_path_is_rejected_without_hanging(tmp_path: Path) -> None:
    """GD-1: a FIFO at the labels path used to hang `open()` in `_OnnxModel.__init__`
    indefinitely. `Path.is_file()` returns False for a FIFO (checks S_ISREG), closing the whole
    class before either path is opened. Wrapped in a real wall-clock timeout (SIGALRM) so a
    regression that reintroduces the hang fails this test instead of wedging CI."""
    model_path = write_classifier_onnx(tmp_path / "model.onnx")
    fifo_path = tmp_path / "labels_fifo"
    os.mkfifo(fifo_path)

    def _on_alarm(signum: int, frame: Any) -> None:
        raise TimeoutError("ingest_cli.main hung on a FIFO labels path -- the GD-1 guard regressed")

    old_handler = signal.signal(signal.SIGALRM, _on_alarm)
    signal.alarm(5)
    try:
        with pytest.raises(SystemExit) as excinfo:
            ingest_cli.main(
                ["--file", str(SAMPLE_LISTING), "--onnx-model", str(model_path), "--onnx-labels", str(fifo_path), "--pretty", "0"]
            )
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

    assert excinfo.value.code != 0
    msg = str(excinfo.value.code)
    assert "--onnx-labels" in msg
    assert "not a regular file" in msg


@pytest.mark.parametrize("flag_name", ["--onnx-model", "--onnx-labels"])
def test_a_missing_path_is_rejected_as_not_a_regular_file(tmp_path: Path, flag_name: str) -> None:
    model_path = write_classifier_onnx(tmp_path / "model.onnx")
    labels_path = write_labels_json(tmp_path / "labels.json")
    missing = tmp_path / "does_not_exist"

    argv = ["--file", str(SAMPLE_LISTING), "--pretty", "0"]
    if flag_name == "--onnx-model":
        argv += ["--onnx-model", str(missing), "--onnx-labels", str(labels_path)]
    else:
        argv += ["--onnx-model", str(model_path), "--onnx-labels", str(missing)]

    with pytest.raises(SystemExit) as excinfo:
        ingest_cli.main(argv)
    assert excinfo.value.code != 0
    assert flag_name in str(excinfo.value.code)


def test_non_float_input_model_is_a_clean_runtimeerror_at_the_api(tmp_path: Path) -> None:
    """B-1 follow-up security ruling: a hostile/exotic declared input type must never be handed
    to the float32 preprocessing pipeline -- fail closed, loudly, at registration."""
    model_path = write_non_float_classifier_onnx(tmp_path / "double.onnx")
    labels_path = write_labels_json(tmp_path / "labels.json")

    with pytest.raises(RuntimeError, match=r"tensor\(double\) not supported; expected tensor\(float\)"):
        ad.register_onnx_provider(str(model_path), str(labels_path))


def test_non_float_input_model_is_a_clean_systemexit_naming_onnx_model_at_the_cli(tmp_path: Path) -> None:
    model_path = write_non_float_classifier_onnx(tmp_path / "double.onnx")
    labels_path = write_labels_json(tmp_path / "labels.json")

    with pytest.raises(SystemExit) as excinfo:
        ingest_cli.main(
            ["--file", str(SAMPLE_LISTING), "--onnx-model", str(model_path), "--onnx-labels", str(labels_path), "--pretty", "0"]
        )
    assert excinfo.value.code != 0
    msg = str(excinfo.value.code)
    assert "--onnx-model" in msg
    assert "tensor(double) not supported" in msg


# ---------------------------------------------------------------------------
# Partial pair -- hard config error, names the missing half
# ---------------------------------------------------------------------------


def test_model_flag_without_labels_names_the_missing_labels_flag(tmp_path: Path) -> None:
    model_path = write_classifier_onnx(tmp_path / "model.onnx")

    with pytest.raises(SystemExit) as excinfo:
        ingest_cli.main(["--file", str(SAMPLE_LISTING), "--onnx-model", str(model_path), "--pretty", "0"])
    assert excinfo.value.code != 0
    msg = str(excinfo.value.code)
    assert "--onnx-labels" in msg
    assert "AIREAL_ONNX_LABELS" in msg


def test_labels_flag_without_model_names_the_missing_model_flag(tmp_path: Path) -> None:
    labels_path = write_labels_json(tmp_path / "labels.json")

    with pytest.raises(SystemExit) as excinfo:
        ingest_cli.main(["--file", str(SAMPLE_LISTING), "--onnx-labels", str(labels_path), "--pretty", "0"])
    assert excinfo.value.code != 0
    msg = str(excinfo.value.code)
    assert "--onnx-model" in msg
    assert "AIREAL_ONNX_MODEL" in msg


# ---------------------------------------------------------------------------
# Precedence: flag beats env per-field; onnx outranks --ai; env-only activation works
# ---------------------------------------------------------------------------


def test_cli_flag_model_beats_env_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    photos_dir = tmp_path / "photos"
    _photo(photos_dir, "mold_basement.jpg", color=(5, 5, 5))
    labels_path = write_labels_json(tmp_path / "labels.json")
    wrong_env_model = write_classifier_onnx(tmp_path / "env_model.onnx", fire_labels=[])  # would NOT fire
    right_flag_model = write_classifier_onnx(tmp_path / "flag_model.onnx", fire_labels=["mold_suspected"])  # WOULD fire

    monkeypatch.setenv("AIREAL_ONNX_MODEL", str(wrong_env_model))

    rc, _out, err = _run(
        [
            "--file",
            str(SAMPLE_LISTING),
            "--photos",
            str(photos_dir),
            "--onnx-model",
            str(right_flag_model),
            "--onnx-labels",
            str(labels_path),
            "--pretty",
            "0",
        ],
        capsys,
    )
    assert rc == 0
    assert "model: --onnx-model" in err

    from src.core.cv.photo_insights import build_photo_insights

    pi = build_photo_insights(photos_dir)
    mold_dets = [d for dets in pi.image_detections.values() for d in dets if d.name == "mold_suspected"]
    assert len(mold_dets) == 1 and mold_dets[0].source == "filename_confirmed"  # proves the FLAG model ran, not env's


def test_cli_flag_labels_beats_env_labels(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    photos_dir = tmp_path / "photos"
    _photo(photos_dir, "mold_basement.jpg", color=(6, 6, 6))
    model_path = write_classifier_onnx(tmp_path / "model.onnx", fire_labels=["mold_suspected"])
    labels_without_mold = write_labels_json(tmp_path / "env_labels.json", labels=["water_leak_suspected"])
    labels_with_mold = write_labels_json(tmp_path / "flag_labels.json")  # declares all six, incl. mold

    monkeypatch.setenv("AIREAL_ONNX_LABELS", str(labels_without_mold))

    rc, _out, err = _run(
        [
            "--file",
            str(SAMPLE_LISTING),
            "--photos",
            str(photos_dir),
            "--onnx-model",
            str(model_path),
            "--onnx-labels",
            str(labels_with_mold),
            "--pretty",
            "0",
        ],
        capsys,
    )
    assert rc == 0
    assert "labels: --onnx-labels" in err

    from src.core.cv.photo_insights import build_photo_insights

    pi = build_photo_insights(photos_dir)
    mold_dets = [d for dets in pi.image_detections.values() for d in dets if d.name == "mold_suspected"]
    # If the env labels (no mold declared) had won, mold_suspected would not even be covered,
    # landing filename_unconfirmed -- confirmed proves the FLAG labels (which declare it) won.
    assert len(mold_dets) == 1 and mold_dets[0].source == "filename_confirmed"


def test_env_only_activation_registers_onnx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    model_path = write_classifier_onnx(tmp_path / "model.onnx")
    labels_path = write_labels_json(tmp_path / "labels.json")
    monkeypatch.setenv("AIREAL_ONNX_MODEL", str(model_path))
    monkeypatch.setenv("AIREAL_ONNX_LABELS", str(labels_path))

    rc, _out, err = _run(["--file", str(SAMPLE_LISTING), "--pretty", "0"], capsys)
    assert rc == 0
    assert ad.is_provider_registered("onnx")
    assert "model: AIREAL_ONNX_MODEL" in err
    assert "labels: AIREAL_ONNX_LABELS" in err


def test_onnx_outranks_the_ai_flag(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Registering ONNX does NOT require --ai, and when both resolve, onnx is selected ahead of
    vision (spec §2/§3.4's selection precedence)."""
    photos_dir = tmp_path / "photos"
    _photo(photos_dir, "plain.jpg", color=(77, 88, 99))
    model_path = write_classifier_onnx(tmp_path / "model.onnx")
    labels_path = write_labels_json(tmp_path / "labels.json")

    rc, out, _err = _run(
        [
            "--file",
            str(SAMPLE_LISTING),
            "--photos",
            str(photos_dir),
            "--ai",
            "1",
            "--onnx-model",
            str(model_path),
            "--onnx-labels",
            str(labels_path),
            "--pretty",
            "0",
        ],
        capsys,
    )
    assert rc == 0
    assert "version=onnx-byo-v1" in out


# ---------------------------------------------------------------------------
# GD-6 -- the stderr note names the flag-vs-env source
# ---------------------------------------------------------------------------


def test_note_absent_when_neither_flag_nor_env_is_set(capsys: pytest.CaptureFixture[str]) -> None:
    rc, _out, err = _run(["--file", str(SAMPLE_LISTING), "--pretty", "0"], capsys)
    assert rc == 0
    assert "onnx provider registered" not in err


# ---------------------------------------------------------------------------
# Default byte-identity: with nothing registered, output is unchanged
# ---------------------------------------------------------------------------


def test_default_output_is_unaffected_by_the_onnx_wiring(capsys: pytest.CaptureFixture[str]) -> None:
    """Two consecutive runs with no --onnx-* flag/env produce byte-identical stdout, and select
    the pre-mission provider -- the structural guarantee (`is_provider_registered("onnx")` is
    False, spec §3.4) holds empirically, not just by code-shape argument."""
    argv = ["--file", str(SAMPLE_LISTING), "--pretty", "0"]
    rc1, out1, _err1 = _run(argv, capsys)
    assert not ad.is_provider_registered("onnx")
    rc2, out2, _err2 = _run(argv, capsys)

    assert rc1 == 0 and rc2 == 0
    assert out1 == out2
    assert "provider=cv_v2, version=deterministic" in out1
    assert "onnx" not in out1
