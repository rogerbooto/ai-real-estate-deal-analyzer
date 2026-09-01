# tests/unit/test_recourse_r2_reason_exhaustiveness.py
"""
Mission 5 Gate V re-review, N4: `_r2_reason`'s docstring claims mypy proves the `if`-chain
exhaustive over `HardRule` and that "a new `HardRule` member turns into a 'missing return' error
here." That was FALSE as originally written: the function ended in `raise AssertionError(...)`,
and a bare raise satisfies any declared return type on every code path -- so mypy accepted the
chain whether or not it actually covered every `HardRule` member. The fix replaces the raise with
`typing_extensions.assert_never(rule)`, whose parameter type is `Never`; mypy only accepts that
call if every other branch has narrowed `rule`'s type to nothing, so an unhandled member surfaces
as a real type error, not a runtime-only backstop.

These tests prove the MECHANISM directly (not just that `src/market/recourse.py` currently type-
checks): each spins up a minimal, self-contained module -- structurally identical to `_r2_reason`
-- and runs the project's own mypy config (`mypy.ini`: `python_version = 3.10`, `strict = True`)
against it via subprocess, exactly as CI does. `test_raise_assertionerror_hides_a_missing_case`
is the reviewer's minimal repro for the pre-fix bug (RED against the OLD pattern, to show what the
false claim was actually built on); `test_assert_never_catches_a_missing_case` is RED against the
NEW pattern with an unhandled member added, proving the corrected claim is true.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

MYPY_INI = Path(__file__).resolve().parents[2] / "mypy.ini"

_ASSERT_NEVER_IMPORT = "from typing_extensions import assert_never"


def _run_mypy(tmp_path: Path, module_source: str) -> subprocess.CompletedProcess[str]:
    """Run the project's own mypy config against a single standalone module, isolated in its
    own directory so mypy's module-discovery doesn't pick up anything else."""
    mod_dir = tmp_path / "mod"
    mod_dir.mkdir()
    mod_path = mod_dir / "probe.py"
    mod_path.write_text(module_source)
    return subprocess.run(
        [sys.executable, "-m", "mypy", "--config-file", str(MYPY_INI), str(mod_path)],
        capture_output=True,
        text=True,
        check=False,
    )


def _source(*, members: str, covered: str, backstop: str, import_assert_never: bool) -> str:
    """The exact shape `_r2_reason` sits on: a closed `Literal` alias with an `if` chain over
    `covered` members (a subset of, or equal to, `members`) and a final catch-all call --
    parameterized on member count, coverage, and backstop style so the only thing that differs
    between test cases is the one line under test.

    `covered == members`: the chain is genuinely exhaustive (matches `_r2_reason` today).
    `covered` a strict subset of `members`: the chain has a real gap (a future `HardRule`
    member added without a matching branch)."""
    lines = ["from typing import Literal"]
    if import_assert_never:
        lines.append(_ASSERT_NEVER_IMPORT)
    lines.append("")
    lines.append(f"Rule = Literal[{', '.join(f'{m!r}' for m in members)}]")
    lines.append("")
    lines.append("")
    lines.append("def f(rule: Rule) -> str:")
    for m in covered:
        lines.append(f'    if rule == "{m}":')
        lines.append(f'        return "{m.upper()}"')
    lines.append(f"    {backstop}")
    lines.append("")
    return "\n".join(lines)


def test_raise_assertionerror_hides_a_missing_case(tmp_path: Path) -> None:
    """RED (documents the false claim's actual behaviour): `raise AssertionError(...)` type-
    checks as returning `str` on EVERY path -- it satisfies any declared return type -- so mypy
    reports success even when the `if` chain is missing a case for a real `Rule` member ('d').
    This is the reviewer's minimal repro and exactly why the pre-fix docstring's "mypy proves the
    chain exhaustive" was false: the old backstop could not have produced a "missing return" error
    for any new member, because it makes every path return."""
    source = _source(
        members="abcd",
        covered="abc",
        backstop='raise AssertionError(f"unhandled {rule!r}")',
        import_assert_never=False,
    )
    result = _run_mypy(tmp_path, source)
    assert result.returncode == 0, f"expected mypy to (wrongly) accept the gap:\n{result.stdout}\n{result.stderr}"
    assert "Success" in result.stdout, result.stdout


def test_assert_never_accepts_a_genuinely_exhaustive_chain(tmp_path: Path) -> None:
    """GREEN control: `assert_never` is not merely stricter for its own sake -- when the chain
    truly is exhaustive, mypy still reports success, matching `_r2_reason`'s current (post-fix)
    state against today's four `HardRule` members."""
    source = _source(members="abc", covered="abc", backstop="assert_never(rule)", import_assert_never=True)
    result = _run_mypy(tmp_path, source)
    assert result.returncode == 0, f"expected a genuinely exhaustive chain to type-check clean:\n{result.stdout}\n{result.stderr}"
    assert "Success" in result.stdout, result.stdout


def test_assert_never_catches_a_missing_case(tmp_path: Path) -> None:
    """RED, post-fix: with `assert_never(rule)` as the backstop (what `_r2_reason` now uses),
    adding a fourth `Rule` member ('d') without a matching `if` branch is a real mypy error --
    `assert_never`'s parameter type is `Never`, and the un-narrowed 'd' branch is still
    `Literal['d']` when it reaches the call, which is not assignable to `Never`. This proves the
    corrected docstring's claim: a new `HardRule` member with no matching branch now fails
    type-check, not just at runtime."""
    source = _source(members="abcd", covered="abc", backstop="assert_never(rule)", import_assert_never=True)
    result = _run_mypy(tmp_path, source)
    assert result.returncode != 0, f"expected mypy to catch the missing case, got:\n{result.stdout}\n{result.stderr}"
    assert "assert_never" in result.stdout or "Never" in result.stdout, result.stdout
