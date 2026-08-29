# tests/core/cv/_onnx_fixtures.py
"""
Synthetic ONNX model/labels fixtures for Mission 3 (bring-your-own ONNX provider) tests.

NOT a test file itself (no ``test_*`` functions, not collected by pytest) — a shared builder
imported by the test files under ``tests/core/cv`` and ``tests/integration`` that need a real
``.onnx`` file on disk. Generated at test time rather than committed as a binary blob, per
``docs/plans/MISSION_3_DISCOVERY_SPEC.md`` §8.2 Option A (gate-approved,
``docs/plans/MISSION_3_GATE_D_SECURITY.md`` ruling B-4): this repo's own precedent for "we need a
small synthetic binary asset for a test" is "generate it in Python, at test time" (see
``tests/core/cv/test_filename_corroboration.py``'s ``_photo()`` helper for photos; this is the
same idea for ``.onnx`` files) — auditable in the diff, no opaque blob in git history.

Graph shape (spec §8.3's verified minimal shape, re-verified against this repo's actual
``onnxruntime`` 1.22.0 during this lane's own manual verification pass before any test was
written):

    input "pixels": tensor(float) [1, 3, "H", "W"]   (NCHW, symbolic spatial dims)
        -> GlobalAveragePool                          [1, 3, 1, 1]
        -> Reshape([1, 3])                             [1, 3]
        -> Gemm(W: [3, 6] float32, B: [6] float32)      [1, 6]  (logits)
        -> Sigmoid                                      [1, 6]  (output "scores", in [0, 1])

``_OnnxModel`` (``src/core/cv/amenities_defects.py``) auto-detects NCHW because ``ishape[1] == 3``
(``ishape[-1]`` is the symbolic string ``"W"``, so ``"W" == 3`` is False) — confirmed empirically,
not assumed. The only learned weight is the ``[3, 6]`` Gemm matrix, so the whole model is a few
hundred bytes regardless of the real image size ``_preprocess`` resizes to (224x224 by default) --
declaring the graph's spatial dims symbolic instead of baking 224x224 into the weights is what
keeps it tiny (spec §8.3: hardcoding 224x224 would need a ``3*224*224 x 6`` matrix, ~3.6 MB as
float32).

The "biased-output-unit" technique (spec §8.3, last paragraph): each output unit's Gemm bias is
set far into ``Sigmoid``'s saturation range (+8.0 -> sigmoid ≈ 0.9997, -8.0 -> sigmoid ≈ 0.0003)
BEFORE any pixel content is added by the tiny random Gemm weight (~N(0, 0.01)). This makes the
fired/not-fired outcome a property of the fixture a test chooses, independent of the input image's
actual pixels -- exactly what proving BOTH ``filename_confirmed`` and ``filename_contested``
(Guardian Condition 4) needs: the point under test is the FILE NAME, not the pixels, mirroring
``test_filename_corroboration.py``'s own blank-grey-image convention.

Both saturated values clear (or fail to clear) every ontology confidence cutoff in
``src/core/cv/ontology.py`` (0.60-0.70 across all six mission labels) with wide margin -- 0.9997
comfortably above the strictest cutoff (mold_suspected, 0.70), 0.0003 comfortably below the
loosest (0.60) -- so the outcome is not cutoff-sensitive.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

import numpy as np
import onnx
from onnx import TensorProto, helper

#: The six labels the ``_FILENAME_RULES`` table (``src/core/cv/runner.py``) knows how to suggest
#: from a file name. Order matters here only in that it fixes each label's output-unit INDEX in
#: the synthetic graph below (index 0 == mold_suspected, etc.) -- it carries no meaning to
#: production code, which reads labels.json's declared list by name via ``_OnnxModel``.
ONNX_BYO_LABELS: tuple[str, ...] = (
    "mold_suspected",
    "water_leak_suspected",
    "ev_charger",
    "parking_garage",
    "parking_driveway",
    "dishwasher",
)

_BIAS_FIRE: float = 8.0
_BIAS_SILENT: float = -8.0
_SEED: int = 1337


def _classifier_graph(
    *,
    input_elem_type: int,
    fire_indices: frozenset[int],
    cast_to_float: bool,
) -> onnx.ModelProto:
    """Build the graph described in this module's docstring.

    ``cast_to_float``: when the declared input type is not ``tensor(float)``, every downstream op
    must still be internally type-consistent for ``onnxruntime`` to construct a session at all
    (verified empirically: a bare double input feeding a float32 ``Gemm`` fails at SESSION
    CONSTRUCTION with a type-mismatch error, before ``_OnnxModel.__init__`` ever reads
    ``inputs[0].type`` -- that would test the wrong thing, onnxruntime's own type checker, not
    this project's fail-closed guard). A leading ``Cast`` node makes the graph load successfully
    with a non-float DECLARED input while every op after it stays float32, so the fail-closed
    check in ``_OnnxModel.__init__`` is what actually fires.
    """
    K = len(ONNX_BYO_LABELS)
    input_tensor = helper.make_tensor_value_info("pixels", input_elem_type, [1, 3, "H", "W"])
    output_tensor = helper.make_tensor_value_info("scores", TensorProto.FLOAT, [1, K])

    nodes = []
    pool_input = "pixels"
    if cast_to_float:
        nodes.append(helper.make_node("Cast", ["pixels"], ["pixels_f32"], to=TensorProto.FLOAT))
        pool_input = "pixels_f32"

    nodes.append(helper.make_node("GlobalAveragePool", [pool_input], ["pooled"]))
    reshape_shape = helper.make_tensor("reshape_shape", TensorProto.INT64, [2], [1, 3])
    nodes.append(helper.make_node("Reshape", ["pooled", "reshape_shape"], ["flat"]))

    rng = np.random.default_rng(_SEED)
    weight = (rng.standard_normal((3, K)) * 0.01).astype(np.float32)
    bias = np.full((K,), _BIAS_SILENT, dtype=np.float32)
    for i in fire_indices:
        bias[i] = _BIAS_FIRE
    w_init = helper.make_tensor("W", TensorProto.FLOAT, [3, K], weight.flatten().tolist())
    b_init = helper.make_tensor("B", TensorProto.FLOAT, [K], bias.tolist())

    nodes.append(helper.make_node("Gemm", ["flat", "W", "B"], ["logits"]))
    nodes.append(helper.make_node("Sigmoid", ["logits"], ["scores"]))

    graph = helper.make_graph(
        nodes,
        "onnx_byo_fixture",
        [input_tensor],
        [output_tensor],
        initializer=[w_init, b_init, reshape_shape],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    model.ir_version = 8
    onnx.checker.check_model(model)
    return model


def write_classifier_onnx(path: Path, *, fire_labels: Iterable[str] = ()) -> Path:
    """Write the tiny float32 six-label classifier fixture to ``path``.

    ``fire_labels``: which of ``ONNX_BYO_LABELS`` should fire (sigmoid ≈ 0.9997) regardless of
    input pixels -- the biased-output-unit technique (module docstring). Every label NOT named
    here is biased silent (sigmoid ≈ 0.0003). Declaring a label in ``fire_labels`` that is not a
    member of ``ONNX_BYO_LABELS`` is a test-authoring bug and raises ``ValueError`` immediately
    rather than silently building a model that can never fire on the intended label.
    """
    fire_set = frozenset(fire_labels)
    unknown = fire_set - set(ONNX_BYO_LABELS)
    if unknown:
        raise ValueError(f"fire_labels contains labels outside ONNX_BYO_LABELS: {sorted(unknown)}")
    fire_indices = frozenset(ONNX_BYO_LABELS.index(name) for name in fire_set)
    model = _classifier_graph(input_elem_type=TensorProto.FLOAT, fire_indices=fire_indices, cast_to_float=False)
    path.write_bytes(model.SerializeToString())
    return path


def write_non_float_classifier_onnx(path: Path) -> Path:
    """Write a structurally VALID (loads fine) classifier that declares a ``tensor(double)``
    input -- exercises the security-mandated fail-closed input-type validation in
    ``_OnnxModel.__init__`` (a non-float declared input is rejected at REGISTRATION time with a
    clean ``RuntimeError``, converting what used to be a silently-swallowed per-image inference
    failure into a loud, actionable config error; see
    ``docs/plans/MISSION_3_SPRINT_TRACKER.md`` BLOCKER B-1's follow-up ruling).
    """
    model = _classifier_graph(input_elem_type=TensorProto.DOUBLE, fire_indices=frozenset(), cast_to_float=True)
    path.write_bytes(model.SerializeToString())
    return path


def write_labels_json(path: Path, labels: Iterable[str] = ONNX_BYO_LABELS) -> Path:
    """Write a well-formed ``{"labels": [...]}`` labels.json declaring ``labels``."""
    path.write_text(json.dumps({"labels": list(labels)}), encoding="utf-8")
    return path


def write_corrupt_model(path: Path) -> Path:
    """Write bytes that are not a valid ONNX protobuf at all (error-path row 2)."""
    path.write_bytes(b"not a real onnx file, just plain garbage bytes\x00\x01\x02")
    return path


def write_deeply_nested_labels_json(path: Path, *, depth: int = 100_000) -> Path:
    """A syntactically-valid-if-parseable-at-all labels.json nested far past Python's default
    recursion limit -- ``json.load`` raises ``RecursionError`` on this (GD-3)."""
    path.write_text("[" * depth + "]" * depth, encoding="utf-8")
    return path


def write_oversize_labels_json(path: Path, *, min_bytes: int = 1_048_577) -> Path:
    """A well-formed-shaped but implausibly large labels.json (> the GD-1 1 MiB cap)."""
    names = [f"padding_label_{i}" for i in range(min_bytes // 16 + 1000)]
    path.write_text(json.dumps({"labels": names}), encoding="utf-8")
    assert path.stat().st_size > min_bytes - 1, "fixture did not exceed the intended size floor"
    return path
