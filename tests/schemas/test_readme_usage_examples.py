# tests/schemas/test_readme_usage_examples.py
"""
Mission 2, Gate 3 VETO remediation — B4.1. **A documented code example must run.**

Gate 2 already bound this file's Usage Example 1 to Gate 3 and it was still broken there:

    pydantic_core._pydantic_core.ValidationError: 2 validation errors for OperatingExpenses
    utilities    Field required
    water_sewer  Field required

``OperatingExpenses.utilities``/``.water_sewer`` are required fields (``Field(...)``, no
default — see ``src/schemas/models.py``); the example never supplied them. This is the second
time a `src/*/README.md` example shipped broken on this branch (M6 — `core/reports/README.md` —
and now this one), so the fix here is not "correct the one snippet" but "never let a fenced
Python example in this file rot silently again": every block is extracted straight from the
committed Markdown and executed as-is. If a future edit reintroduces a broken example — here or
one added later — this test fails naming the block, not a human eyeballing a diff.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
README = REPO_ROOT / "src" / "schemas" / "README.md"

#: Matches a fenced ```python ... ``` block and captures its body.
_PY_BLOCK = re.compile(r"```python\n(.*?)```", re.DOTALL)


def _extract_python_blocks(text: str) -> list[str]:
    # `dedent` because the "Imports (verified)" block is nested inside a Markdown bullet and
    # indented two spaces in the source file -- Python cares, Markdown rendering does not.
    return [textwrap.dedent(m.group(1)) for m in _PY_BLOCK.finditer(text)]


def _usage_examples_section(text: str) -> str:
    start = text.index("## Usage Examples")
    nxt = text.find("\n## ", start + 1)
    return text[start:] if nxt == -1 else text[start:nxt]


@pytest.fixture(scope="module")
def readme_text() -> str:
    assert README.is_file(), f"{README} must exist for this test to mean anything"
    return README.read_text(encoding="utf-8")


def test_readme_has_at_least_the_two_documented_usage_examples(readme_text: str) -> None:
    section = _usage_examples_section(readme_text)
    blocks = _extract_python_blocks(section)
    assert len(blocks) >= 2, "expected Example 1 (FinancialInputs) and Example 2 (Market Snapshot) at minimum"


@pytest.mark.parametrize("block_index", [0, 1])
def test_each_usage_example_executes_without_error(readme_text: str, block_index: int) -> None:
    """RED on revert: this is exactly the failure mode Gate 2/3 both caught -- a documented
    example that raises the moment a reader copies it, verified here rather than eyeballed."""
    section = _usage_examples_section(readme_text)
    blocks = _extract_python_blocks(section)
    code = blocks[block_index]

    # Executed in a throwaway namespace, not exec()'d into this test's own globals, so a name
    # collision between examples (both define `inputs`/`snap`, etc.) cannot mask a real failure.
    namespace: dict[str, object] = {}
    exec(compile(code, f"{README}::UsageExample[{block_index}]", "exec"), namespace)


def test_the_imports_verified_block_also_executes(readme_text: str) -> None:
    """The "Imports (verified)" block under Public APIs / Contracts is a standalone claim too --
    every name it lists must actually import from the module it names."""
    start = readme_text.index("## Public APIs / Contracts")
    nxt = readme_text.find("\n### ", start + 1)
    section = readme_text[start:nxt]
    blocks = _extract_python_blocks(section)
    assert blocks, "the 'Imports (verified)' fenced block went missing"

    namespace: dict[str, object] = {}
    exec(compile(blocks[0], f"{README}::ImportsVerified", "exec"), namespace)


def test_operating_expenses_in_example_1_supplies_every_required_field(readme_text: str) -> None:
    """Direct pin of the Gate 2/3 defect, independent of the regex-extraction machinery above:
    even if the extractor ever breaks, this still catches the exact regression that shipped.
    """
    from src.schemas.models import OperatingExpenses

    required = {name for name, field in OperatingExpenses.model_fields.items() if field.is_required()}
    assert required == {"insurance", "taxes", "utilities", "water_sewer", "property_management"}, (
        "OperatingExpenses' required-field set changed; update Usage Example 1 in "
        "src/schemas/README.md to match, then re-run this test suite before touching the doc again"
    )

    section = _usage_examples_section(readme_text)
    example_1 = _extract_python_blocks(section)[0]
    for field_name in required:
        assert re.search(rf"\b{field_name}\s*=", example_1), f"Example 1 no longer supplies required field {field_name!r}"
