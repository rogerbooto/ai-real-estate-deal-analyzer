# src/core/utils/serialize.py
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from typing import Any

_PYDANTIC_TYPE: type[Any] | None = None
_HAVE_PYDANTIC: bool = False

try:
    # pydantic v2
    from pydantic import BaseModel

    _HAVE_PYDANTIC = True
    _PYDANTIC_TYPE = BaseModel
except Exception:  # pragma: no cover
    pass


def to_primitive(x: Any) -> Any:
    # Mappings first
    if isinstance(x, Mapping):
        return {k: to_primitive(v) for k, v in x.items()}

    # Sequences (handle list/tuple explicitly to keep types stable)
    if isinstance(x, list):
        return [to_primitive(v) for v in x]
    if isinstance(x, tuple):
        return tuple(to_primitive(v) for v in x)

    # Pydantic (v2 preferred, v1 fallback)
    if _HAVE_PYDANTIC and _PYDANTIC_TYPE is not None and isinstance(x, _PYDANTIC_TYPE):
        try:
            return x.model_dump()
        except Exception:
            try:
                return x.dict()
            except Exception:
                pass

    # Dataclasses. Deliberately NOT `dataclasses.asdict(x)`: asdict() only recurses into fields
    # that are themselves dataclasses/lists/tuples/dicts -- a field holding a pydantic model (or
    # any other non-dataclass object) is returned as-is (via a plain `copy.deepcopy`), which is
    # exactly the JSON-unsafe shape this function exists to eliminate. Recursing through
    # `to_primitive` itself, field by field, gives every field the same conversion this function
    # gives everything else.
    if is_dataclass(x) and not isinstance(x, type):
        return {f.name: to_primitive(getattr(x, f.name)) for f in fields(x)}

    # Fallback: return as-is
    return x
