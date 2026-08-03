"""
F20 (one layer below the CLI): the normalize fallback paths must carry the structured address.

Both `listing_text.parse_text_to_normalized` and `listing_html.parse_html_to_normalized` build
`ListingNormalized` directly and, on `ValidationError`, fall back to assembling a dict and
re-validating it. Those fallback dicts used the key `"address_struct"`, but the model's field is
`address_structure` -- and `ListingNormalized` sets `extra="ignore"`, so the key was silently
discarded rather than raising. Every fallback therefore lost the parsed structured address with no
signal at all.

These tests assert the fallback dicts use a key the model actually accepts. They turn RED if either
key regresses to `address_struct`, because the round-trip through `model_validate` would drop it.
"""

from __future__ import annotations

import ast
import inspect

import pytest

from src.core.normalize import listing_html, listing_text
from src.schemas.models import ListingNormalized


def _dict_literal_keys(module: object) -> set[str]:
    """
    Every string key used in a dict literal in `module`.

    Deliberately AST-based rather than a substring search over the source: the fix's own
    explanatory comments mention the bad key by name, and a text search cannot tell code from
    prose. Parsing gets the keys the interpreter will actually use.
    """
    tree = ast.parse(inspect.getsource(module))
    return {
        k.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Dict)
        for k in node.keys
        if isinstance(k, ast.Constant) and isinstance(k.value, str)
    }


def test_listing_normalized_silently_ignores_unknown_keys() -> None:
    """The premise: an unknown key is dropped, not rejected -- which is why this bug was silent."""
    assert ListingNormalized.model_config.get("extra", "ignore") == "ignore"
    assert "address_structure" in ListingNormalized.model_fields
    assert "address_struct" not in ListingNormalized.model_fields

    m = ListingNormalized.model_validate({"address": "1 X St", "address_struct": {"city": "Moncton"}})
    assert m.address_structure is None  # silently lost, no error raised


@pytest.mark.parametrize("module", [listing_text, listing_html], ids=["listing_text", "listing_html"])
def test_fallback_dicts_only_use_keys_the_model_accepts(module: object) -> None:
    """
    EVERY dict-literal key in these parsers must be a real `ListingNormalized` field.

    Constructing input that actually trips the `except ValidationError` branch would mean
    fabricating something the parsers are specifically written to tolerate, pinning parser quirks
    rather than the contract under test. The contract is narrow and exact: because the model sets
    `extra="ignore"`, any key that is not a real field is discarded in silence.

    The check is the unrestricted `keys <= fields`. An earlier version filtered to keys that were
    already valid or began with "address" before comparing, which made it vacuous for exactly the
    typos it most needed to catch: `"postal_cod"` or `"bedroom"` is neither a valid field nor
    address-prefixed, so it was excluded from the comparison and would have sailed through. Both
    modules use only real field names today, so no carve-out is needed — and if one ever is, it
    should be argued in a comment rather than hidden in a filter expression.
    """
    keys = _dict_literal_keys(module)
    fields = set(ListingNormalized.model_fields)

    assert "address_struct" not in keys, (
        f"{module.__name__} builds its fallback dict with 'address_struct', which is not a "
        f"ListingNormalized field. extra='ignore' means the structured address is silently "
        f"dropped rather than raising. Use 'address_structure'."
    )
    assert "address_structure" in keys, f"{module.__name__} no longer carries the structured address through its fallback path"
    assert keys <= fields, f"{module.__name__} uses dict keys the model will silently ignore (extra='ignore'): {sorted(keys - fields)}"
