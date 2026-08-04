"""
The Run Provenance appendix must report what a run actually DID, not what its env asked for.

Background. Gate 2 was vetoed because on `--engine crewai` with `AIREAL_LLM_MODE=1` a language
model authored every listing observation while the report's only AI fact read
``| AI photo tagging | off |`` -- under a heading promising the table is enough to reproduce the
run. The fix added an ``LLM-authored observations`` row.

Wiring that row straight to the env var would have introduced the *mirror* over-claim, which is
what this file pins. ``AIREAL_LLM_MODE`` is consulted only by the crewai engine, and even there
the LLM call can fail and fall back to the deterministic path -- so on a deterministic run with
the variable set, "on" would announce an LLM that never ran. Over-claiming AI is not a safer
error than under-claiming it; it is the same defect pointed the other way.

The per-tag provenance ledger (``ListingInsights.observations``) is the ground truth: a record
carries ``origin="llm"`` only if a model really wrote it. The row is derived from that.

Run as a subprocess rather than by importing ``main``: the honest value depends on env read at
import time in more than one module, and an in-process ``monkeypatch.setenv`` after those imports
would test a state the real CLI can never be in -- exactly the class of vacuous test this mission
has been removing.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
_ROW = "| LLM-authored observations |"


def _run_main(out_path: Path, env_overrides: dict[str, str]) -> str:
    env = {**os.environ, **env_overrides}
    proc = subprocess.run(
        [sys.executable, "main.py", "--out", str(out_path)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert proc.returncode == 0, f"main.py failed:\n{proc.stdout}\n{proc.stderr}"
    return out_path.read_text(encoding="utf-8")


def _row_value(report: str) -> str:
    line = next((ln for ln in report.splitlines() if ln.startswith(_ROW)), None)
    assert line is not None, f"the provenance appendix lost its {_ROW.strip()} row entirely"
    # "| LLM-authored observations | off | `AIREAL_LLM_MODE` |" -> "off"
    return line.split("|")[2].strip()


@pytest.mark.parametrize(
    ("env", "case"),
    [
        ({}, "env unset"),
        ({"AIREAL_LLM_MODE": "1"}, "env SET, but the deterministic engine never consults it"),
    ],
    ids=["env-unset", "env-set-deterministic-engine"],
)
def test_row_reports_actual_authorship_not_the_env_var(tmp_path: Path, env: dict[str, str], case: str) -> None:
    """
    Both cases must read "off", including the one where the variable IS set.

    The default engine is deterministic and never reaches the LLM path, so no observation can
    carry ``origin="llm"`` and nothing was LLM-authored. A row reading "on" here would be a
    false claim about how the numbers above it were produced.
    """
    report = _run_main(tmp_path / "report.md", env)
    assert _row_value(report) == "off", f"the row over-claims on a run where nothing was LLM-authored ({case})"


def test_the_row_exists_at_all(tmp_path: Path) -> None:
    """
    Guards the original Gate 2 blocker in the other direction.

    If this row is ever dropped, the appendix goes back to offering ``AI photo tagging`` as its
    only AI fact while claiming to be sufficient for reproduction -- which is what was vetoed.
    """
    report = _run_main(tmp_path / "report.md", {})
    assert _ROW in report
    assert "`AIREAL_LLM_MODE`" in report, "the row must name the variable, or the table cannot be used to reproduce a run"
