# tests/integration/test_cli_reachable_paths.py
"""
Feature -> reachable-path guard (Mission 2, Wave 2, root causes 1 and 4).

The defect class this guards against: a CLI flag that exists (``add_argument`` ran, ``--help``
advertises it, the flag even has a paragraph in ``src/cli/README.md``) but whose value is never
read anywhere -- F12 (``advisor_cli --debug``) was exactly this shape: the flag appeared once, at
its own ``add_argument`` call, and ``args.debug`` was never referenced again. Nothing in the
runtime ever raises on an unread ``argparse`` value, so the flag is silently inert forever; only a
test that ties "flag declared" to "flag consumed" can catch it, and it must catch the *next* one,
not just the one already fixed.

Design
------
1. **Enumerate flags dynamically, via real ``argparse``, not by re-reading source text.**
   Each target module (``main.py``, ``src/cli/ingest_cli.py``, ``src/cli/report_cli.py``,
   ``src/cli/advisor_cli.py``) builds its own ``argparse.ArgumentParser`` inline, inside a
   function, and never exposes the unparsed parser object directly. Reimplementing argparse's own
   "long option -> dest" naming rule here would risk quietly diverging from the interpreter's own
   behaviour (dest overrides, `-x`-only flags, etc.) -- exactly the "hand-listed net has the same
   defect it guards against" trap the assignment calls out. Instead ``_capture_parser`` below
   monkeypatches ``argparse.ArgumentParser.parse_args`` to raise with ``self`` attached the
   instant it is called, then invokes the module's real flag-parsing entry point. The parser that
   comes back is the *actual* object every ``add_argument`` call in the module populated --
   ``action.dest``/``action.option_strings`` are argparse's own answer, not a guess. Adding a new
   flag to any of these four modules requires zero edits here: it appears in ``parser._actions``
   on the next run automatically.
2. **Prove each flag is consumed via AST, on the module's real source.** For every flag, the
   guard confirms the module contains an ``args.<dest>`` (or ``<var>.<dest>`` for whatever name
   the module assigns the parsed ``Namespace`` to -- resolved dynamically, see
   ``_find_namespace_var_names``) attribute access somewhere in the file. This is real syntax
   analysis (``ast``), not a substring search -- see
   ``tests/core/normalize/test_address_structure_fallback.py`` for the precedent and the trap a
   textual search falls into (a comment or docstring mentioning ``args.debug`` would satisfy a
   substring search without a single line of code reading it). An ``ast.Attribute`` node cannot be
   produced by a comment or a string literal, so this check cannot be fooled by prose the way a
   grep could.
3. **No silent skips.** Every discovered flag is either found consumed by the AST walk, listed in
   ``_CONSUMPTION_EXCEPTIONS`` with a written reason, or the test fails naming it. See
   ``_CONSUMPTION_EXCEPTIONS``'s docstring for why it is empty today.
4. **Mirror-image check.** ``test_documented_flags_still_exist_in_the_parsers`` reads
   ``src/cli/README.md`` *at runtime* (never hardcodes its content -- a documentation agent is
   concurrently reconciling that file) and asserts every backtick-wrapped ``--flag`` token it
   finds still exists in one of the three ``src/cli/*.py`` parsers. A flag documented there that
   no longer exists in any parser is the defect's mirror image (F18-20's class, one layer up).

Known limitation (documented, not hidden): the AST consumption check finds an ``args.<dest>``
attribute access anywhere in the module's syntax tree, including inside a branch that can never
execute (e.g. ``if False:``) or a nested function the parsing entry point never calls. All four
target modules are small, flat, single-entry-point scripts with no such dead branches today, so
this is a soft spot the guard inherits rather than one that has ever produced a false pass here --
recorded per the ``test_generator_field_guard.py`` precedent of naming a matcher's known blind
spots rather than silently living with them.
"""

from __future__ import annotations

import argparse
import ast
import inspect
import re
from pathlib import Path
from typing import Any

import pytest

import main as main_module
import src.cli.advisor_cli as advisor_cli
import src.cli.ingest_cli as ingest_cli
import src.cli.report_cli as report_cli

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_README = REPO_ROOT / "src" / "cli" / "README.md"

# ---------------------------------------------------------------------------------
# 1. Capture the real argparse.ArgumentParser each module builds, without letting it
#    actually parse pytest's own sys.argv.
# ---------------------------------------------------------------------------------


class _ParserCaptured(Exception):
    """Raised by the monkeypatched ``parse_args`` to smuggle the live parser out."""

    def __init__(self, parser: argparse.ArgumentParser) -> None:
        super().__init__("parser captured")
        self.parser = parser


def _capture_parser(entry_point: Any, *args: Any, **kwargs: Any) -> argparse.ArgumentParser:
    """
    Run ``entry_point`` (a module's ``main``/``parse_args`` function) with
    ``argparse.ArgumentParser.parse_args`` replaced so it never actually consumes argv --
    it just raises with ``self`` (the fully-built parser) attached. Every ``add_argument``
    call the entry point makes before reaching ``parse_args`` still runs for real, so the
    returned parser's ``_actions`` are the interpreter's own answer, not a re-derivation.
    """

    def _fake_parse_args(self: argparse.ArgumentParser, *_a: Any, **_kw: Any) -> Any:
        raise _ParserCaptured(self)

    original = argparse.ArgumentParser.parse_args
    argparse.ArgumentParser.parse_args = _fake_parse_args  # type: ignore[assignment,method-assign]
    try:
        entry_point(*args, **kwargs)
    except _ParserCaptured as captured:
        return captured.parser
    else:
        raise AssertionError(
            f"{entry_point!r} returned without ever calling ArgumentParser.parse_args() -- "
            "this guard could not capture a parser to enumerate flags from. Either the "
            "module's flag-parsing entry point changed shape (update the call site below) "
            "or it no longer parses flags at all."
        )
    finally:
        argparse.ArgumentParser.parse_args = original  # type: ignore[method-assign]


def _discovered_flags(parser: argparse.ArgumentParser) -> list[tuple[str, tuple[str, ...]]]:
    """``[(dest, option_strings), ...]`` for every user-declared flag, excluding the
    ``-h``/``--help`` action argparse injects automatically (never a hand-written
    ``add_argument`` call, so it is outside this guard's "declared but unconsumed" premise)."""
    return [(a.dest, tuple(a.option_strings)) for a in parser._actions if a.dest != "help"]  # noqa: SLF001


# ---------------------------------------------------------------------------------
# 2. Prove consumption via AST on the module's real source.
# ---------------------------------------------------------------------------------


def _module_functions(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    return {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}


def _is_parse_args_call(call: ast.Call, funcs: dict[str, ast.FunctionDef], *, _depth: int = 0) -> bool:
    """
    Whether ``call`` is (possibly transitively, through a same-module helper function) a call
    to ``some_parser.parse_args(...)``. Handles both the direct shape (``ap.parse_args()``,
    used by ingest_cli/report_cli/advisor_cli) and the one-level-indirect shape (``main.py``'s
    module-level ``parse_args()`` helper, whose only ``return`` is ``p.parse_args()``).
    ``_depth`` bounds the recursion so a pathological call graph cannot spin forever.
    """
    if _depth > 4:
        return False
    if isinstance(call.func, ast.Attribute) and call.func.attr == "parse_args":
        return True
    if isinstance(call.func, ast.Name) and call.func.id in funcs:
        fn = funcs[call.func.id]
        for node in ast.walk(fn):
            if (
                isinstance(node, ast.Return)
                and isinstance(node.value, ast.Call)
                and _is_parse_args_call(node.value, funcs, _depth=_depth + 1)
            ):
                return True
    return False


def _find_namespace_var_names(tree: ast.Module) -> set[str]:
    """Every variable name that is ever assigned the result of a ``parse_args()`` call
    (directly or through the one-level-indirect helper shape), anywhere in the module."""
    funcs = _module_functions(tree)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and _is_parse_args_call(node.value, funcs):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


def _consumed_dests(tree: ast.Module, namespace_vars: set[str]) -> set[str]:
    """Every attribute name read off any of ``namespace_vars`` anywhere in the module --
    i.e. every ``<namespace_var>.<attr>`` access, regardless of which function it lives in
    (F12's fix, and this guard's own coverage of it, both live in the same module as the
    ``add_argument`` call but a different function -- ``main`` -- so this must be a
    whole-module search, not scoped to one function)."""
    consumed: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in namespace_vars:
            consumed.add(node.attr)
    return consumed


# ---------------------------------------------------------------------------------
# 3. Exceptions table -- flags proven consumed by means this guard's AST walk cannot see
#    (e.g. ``getattr(args, ...)``, or the Namespace threaded into a helper under a renamed
#    parameter). Keyed by (module label, dest). Empty today: every flag across all four
#    target modules is consumed by a direct ``<namespace_var>.<dest>`` attribute access in
#    the SAME module the flag is declared in (verified by this guard passing without any
#    entries here -- see test_no_stale_exceptions_remain below, which keeps this table
#    honest the same way test_guard_would_have_caught_f4_and_f5_shapes keeps the Wave 1
#    guard's exclusion table honest). If a future flag's only consumer is a helper that
#    receives the Namespace under a different parameter name (``_collect_input_paths``'s
#    ``args: argparse.Namespace`` parameter today happens to keep the name ``args``, which
#    is why it needs no entry), add it HERE with a reason -- never widen the AST walk to
#    "any attribute access with this name anywhere in the file" as a workaround, since that
#    would blur the guard back towards a substring search.
# ---------------------------------------------------------------------------------
_CONSUMPTION_EXCEPTIONS: dict[tuple[str, str], str] = {}


# ---------------------------------------------------------------------------------
# Target modules. Named directly per the mission's own instruction (the four listed CLI
# entry points), not discovered via a directory scan -- there is no reliable way to tell
# "this .py file under src/cli/ is a CLI entry point with its own argparse.ArgumentParser"
# from "this one is a shared helper" without already knowing which files those are.
# ---------------------------------------------------------------------------------
_TARGETS: dict[str, tuple[Any, tuple[Any, ...], dict[str, Any]]] = {
    "main": (main_module.parse_args, (), {}),
    "src.cli.ingest_cli": (ingest_cli.main, ([],), {}),
    "src.cli.report_cli": (report_cli.main, ([],), {}),
    "src.cli.advisor_cli": (advisor_cli.main, (), {}),
}

_MODULE_OBJECTS: dict[str, Any] = {
    "main": main_module,
    "src.cli.ingest_cli": ingest_cli,
    "src.cli.report_cli": report_cli,
    "src.cli.advisor_cli": advisor_cli,
}


def _flags_and_consumption(label: str) -> tuple[list[tuple[str, tuple[str, ...]]], set[str]]:
    entry_point, args, kwargs = _TARGETS[label]
    parser = _capture_parser(entry_point, *args, **kwargs)
    flags = _discovered_flags(parser)

    module = _MODULE_OBJECTS[label]
    tree = ast.parse(inspect.getsource(module))
    namespace_vars = _find_namespace_var_names(tree)
    assert namespace_vars, (
        f"{label}: could not find a variable assigned from an ArgumentParser.parse_args() call "
        "(directly, or one level of indirection through a same-module helper). This guard's "
        "consumption check has nothing to search from -- either the module's structure changed "
        "in a way _find_namespace_var_names must be taught, or the module no longer parses args."
    )
    consumed = _consumed_dests(tree, namespace_vars)
    return flags, consumed


@pytest.mark.parametrize("label", sorted(_TARGETS))
def test_every_discovered_flag_is_consumed(label: str) -> None:
    flags, consumed = _flags_and_consumption(label)
    assert flags, f"{label}: discovered zero flags -- the parser-capture mechanism itself is broken, this test is vacuous until fixed"

    unconsumed = []
    for dest, option_strings in flags:
        if (label, dest) in _CONSUMPTION_EXCEPTIONS:
            continue
        if dest not in consumed:
            unconsumed.append((dest, option_strings))

    assert not unconsumed, (
        f"{label}: {len(unconsumed)} flag(s) declared via add_argument() but never read via "
        f"the parsed Namespace anywhere in the module (F12's exact shape -- the flag exists, "
        f"argparse will accept it, but its value is discarded): "
        + ", ".join(f"{opts[0]} (dest={dest!r})" for dest, opts in unconsumed)
        + ". Either wire it in, remove the add_argument() call, or add "
        "(module_label, dest) to _CONSUMPTION_EXCEPTIONS with a written reason."
    )


def test_no_stale_exceptions_remain() -> None:
    """
    Every entry in ``_CONSUMPTION_EXCEPTIONS`` must name a flag that ACTUALLY exists and is
    ACTUALLY unconsumed by the plain AST walk today -- an exception that no longer applies
    (the flag was removed, or someone wired it in directly without deleting the entry) is
    exactly the kind of stale carve-out that would silently widen this guard's blind spot
    over time. Mirrors test_guard_would_have_caught_f4_and_f5_shapes in the Wave 1 field
    guard: an exclusion table is only trustworthy if something keeps checking it stays
    minimal and accurate.
    """
    for label, dest in _CONSUMPTION_EXCEPTIONS:
        flags, consumed = _flags_and_consumption(label)
        flag_dests = {d for d, _ in flags}
        assert (
            dest in flag_dests
        ), f"_CONSUMPTION_EXCEPTIONS names {label}.{dest}, but no such flag exists anymore -- remove the stale entry"
        assert dest not in consumed, (
            f"_CONSUMPTION_EXCEPTIONS carves out {label}.{dest} as 'consumed only indirectly', "
            "but the plain AST walk now finds a direct <namespace_var>.<dest> access -- the "
            "exception is stale. Remove it; the flag no longer needs one."
        )


# ---------------------------------------------------------------------------------
# 4. Mirror-image check: a flag documented in src/cli/README.md that no longer exists in
#    any of the three src/cli/*.py parsers.
# ---------------------------------------------------------------------------------

#: Matches a backtick-wrapped, single-token CLI-flag-shaped string, e.g. `--out-cache`. Requires
#: the backtick to sit immediately before the `--`, so a phrase like `` `ingest-listing --help` ``
#: (the flag as part of a longer backtick-wrapped command example) is deliberately NOT matched --
#: it documents a literal shell invocation, not a claim that `--help` is one of this module's own
#: `add_argument()` flags (argparse injects `-h`/`--help` on every parser automatically).
_DOC_FLAG_RE = re.compile(r"`(--[A-Za-z][A-Za-z0-9-]*)`")


# Flags that legitimately appear in src/cli/README.md but belong to OTHER tools, so they will
# never be found on this project's parsers. Each needs a reason; an unexplained entry here would
# let a genuinely missing project flag hide behind it.
#
# This table exists because the doc-mirror check found `--no-cov` after the Wave 2 docs pass added
# it to the documented `pytest` subset commands (those commands exit non-zero without it, since
# pytest.ini applies --cov-fail-under=80 to every invocation). That was the guard working
# correctly on an ambiguity, not a false alarm to be suppressed -- so it is recorded, not skipped.
_THIRD_PARTY_DOC_FLAGS: dict[str, str] = {
    "--no-cov": "pytest-cov, used in this file's documented subset-test commands; not a project CLI flag",
}


def test_documented_flags_still_exist_in_the_parsers() -> None:
    """
    Mirror image of the main guard: every ``--flag`` token backtick-documented in
    ``src/cli/README.md`` must still be an actual flag on the ingest/report/advisor
    parsers. Read at runtime (never hardcoded) so edits from the concurrent docs
    reconciliation pass do not need to touch this test -- only a flag actually disappearing
    from a parser (or a genuinely new, wrong doc reference) can turn this RED.

    Scoped to ``src/cli/README.md`` and its three CLIs (not ``main.py``/root ``README.md``):
    that file is a single, structured, exhaustively-flagged reference for exactly these three
    parsers. The root ``README.md`` intermixes CLI flags with pytest/pip flags
    (``--cov``, ``--strict``, etc.) in prose and code fences with no reliable structural
    marker to tell them apart, so checking it here would risk false RUNs on unrelated
    documentation edits rather than on a real defect -- out of scope for this guard, noted
    for whoever next revises the root README's structure.
    """
    assert CLI_README.is_file(), f"{CLI_README} not found -- this guard's doc-mirror check has nothing to read"
    text = CLI_README.read_text(encoding="utf-8")
    documented = set(_DOC_FLAG_RE.findall(text))
    assert documented, f"{CLI_README}: found zero backtick-wrapped --flag references -- the extraction regex or the doc's own formatting changed; this check is vacuous until fixed"

    actual: set[str] = set()
    for label in ("src.cli.ingest_cli", "src.cli.report_cli", "src.cli.advisor_cli"):
        flags, _ = _flags_and_consumption(label)
        for _dest, option_strings in flags:
            actual.update(option_strings)

    missing = documented - actual - set(_THIRD_PARTY_DOC_FLAGS)
    assert not missing, (
        f"{CLI_README} documents {sorted(missing)} as CLI flag(s), but none of "
        "ingest_cli/report_cli/advisor_cli's actual argparse parsers declare them anymore. "
        "Either the parser lost the flag (fix the code) or the doc is stale (fix the doc)."
    )


# ---------------------------------------------------------------------------------
# Sanity: importing this module a second time (e.g. pytest-xdist worker reuse) must not
# leave argparse.ArgumentParser.parse_args monkeypatched. _capture_parser restores it in a
# finally block; this asserts that promise held for every capture already run above.
# ---------------------------------------------------------------------------------


def test_parse_args_monkeypatch_is_always_restored() -> None:
    assert argparse.ArgumentParser.parse_args.__module__ == "argparse", (
        "argparse.ArgumentParser.parse_args is not the real library method after this guard's "
        "captures ran -- _capture_parser's finally block failed to restore it, which would leak "
        "the monkeypatch into every other test that runs argparse in this process."
    )
    assert argparse.ArgumentParser.parse_args.__name__ == "parse_args"


if __name__ == "__main__":
    # Manual smoke run: print every discovered flag and its consumption status, useful when
    # extending this guard to a fifth CLI.
    for _label in sorted(_TARGETS):
        _flags, _consumed = _flags_and_consumption(_label)
        print(f"== {_label} ==")
        for _dest, _opts in _flags:
            status = "OK" if _dest in _consumed or (_label, _dest) in _CONSUMPTION_EXCEPTIONS else "**UNCONSUMED**"
            print(f"  {_opts} dest={_dest} -> {status}")
