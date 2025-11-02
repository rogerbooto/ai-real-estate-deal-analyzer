# src/core/utils/serialize.py
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
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

    # Dataclasses
    if is_dataclass(x) and not isinstance(x, type):
        return asdict(x)

    # Fallback: return as-is
    return x
