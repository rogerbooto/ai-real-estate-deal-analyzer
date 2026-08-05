# tests/core/utils/test_serialize.py
"""
Mission 2, Wave 3, task 3.1b (OPD-3 wire-first) — src/core/utils/serialize.py.

Before this task the module had zero production and zero test references. ``advisor_cli.py``'s
``--save-artifacts`` writer hand-rolled the same job with
``d.finance.model_dump() if hasattr(d.finance, "model_dump") else d.finance.__dict__`` -- a
fallback that returns whatever ``__dict__`` holds *verbatim*, so a non-pydantic object with a
*nested* pydantic/dataclass field left that field un-converted. ``to_primitive`` recurses, so it
does not have that hole. These tests pin ``to_primitive`` itself; the RED-on-revert proof that the
CLI actually calls it lives in ``tests/integration/test_advisor_cli_wiring.py``
(``test_save_artifacts_recursively_converts_a_nested_non_pydantic_finance_object``).
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from src.core.utils.serialize import to_primitive


class _NestedModel(BaseModel):
    x: int


def test_to_primitive_passes_through_json_native_scalars() -> None:
    assert to_primitive(1) == 1
    assert to_primitive(1.5) == 1.5
    assert to_primitive("s") == "s"
    assert to_primitive(None) is None
    assert to_primitive(True) is True


def test_to_primitive_recurses_into_mappings() -> None:
    out = to_primitive({"a": _NestedModel(x=1), "b": {"c": _NestedModel(x=2)}})
    assert out == {"a": {"x": 1}, "b": {"c": {"x": 2}}}


def test_to_primitive_recurses_into_lists_and_tuples() -> None:
    assert to_primitive([_NestedModel(x=1), _NestedModel(x=2)]) == [{"x": 1}, {"x": 2}]
    assert to_primitive((_NestedModel(x=1),)) == ({"x": 1},)


def test_to_primitive_converts_a_pydantic_model() -> None:
    assert to_primitive(_NestedModel(x=7)) == {"x": 7}


def test_to_primitive_converts_a_dataclass() -> None:
    @dataclass
    class Point:
        x: int
        y: int

    assert to_primitive(Point(1, 2)) == {"x": 1, "y": 2}


def test_to_primitive_recursively_converts_a_pydantic_field_nested_inside_a_dataclass() -> None:
    """
    The exact shape the old ``advisor_cli.py`` fallback (``d.finance.__dict__``) could not handle:
    a non-pydantic container whose own field is itself a pydantic model. ``dataclasses.asdict``
    (which ``to_primitive`` delegates to for dataclasses) recurses into nested dataclasses AND
    fields on its own, but a nested *pydantic* model is opaque to it unless ``to_primitive``
    itself walks the result -- this is the case that would surface as
    ``TypeError: Object of type _NestedModel is not JSON serializable`` from ``json.dumps`` if the
    module regressed to returning a dataclass's fields without a second pass.
    """

    @dataclass
    class Wrapper:
        label: str
        nested: _NestedModel

    out = to_primitive(Wrapper(label="w", nested=_NestedModel(x=9)))
    assert out == {"label": "w", "nested": {"x": 9}}
    assert isinstance(out["nested"], dict)
