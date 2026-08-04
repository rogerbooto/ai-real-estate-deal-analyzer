"""
A deterministic run must not load the LLM SDK tree.

The project's rule is that heavy AI SDKs are lazily imported and AI features default OFF, so the
ordinary `python main.py` stays cheap. That was quietly broken: recording whether a language model
authored the listing observations needs an `AIREAL_LLM_MODE` check on *every* run, and reading it
from ``src.agents.crewai_components`` — where it used to live — made ``main.py`` import that module
unconditionally, dragging in ``crewai`` and ``litellm``. Measured at ~2.9s and both packages
resident, on a run with AI entirely off.

Nothing failed. The report was correct, the tests were green, and the only symptom was that every
invocation had quietly become several times more expensive. That is exactly the kind of regression
no assertion in this suite was watching for, which is why this file exists.

The check itself is two lines of ``os.getenv`` with no dependency on crewai at all — the cost came
purely from which module it sat in. It now lives in ``src.core.runtime_flags``, and
``crewai_components._llm_enabled`` delegates there so there is still one implementation.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Import-cost offenders that must stay out of a deterministic run. `crewai` pulls `litellm` with
# it; both are named so a failure message points at whichever actually leaked.
_HEAVY_SDKS = ("crewai", "litellm")


def _modules_after_importing(module: str) -> set[str]:
    """Import `module` in a clean interpreter and report what ended up in sys.modules.

    A subprocess, not an in-process import: by the time this test runs, the suite has already
    imported half the codebase, so `sys.modules` here says nothing about what a real CLI
    invocation loads.
    """
    code = f"import {module}, sys; print('\\n'.join(sorted(sys.modules)))"
    proc = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT, capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, f"importing {module} failed:\n{proc.stderr}"
    return set(proc.stdout.split())


@pytest.mark.parametrize("sdk", _HEAVY_SDKS)
def test_importing_main_does_not_load_the_llm_sdk(sdk: str) -> None:
    """`python main.py` on the default deterministic path must not pay for the LLM stack."""
    loaded = _modules_after_importing("main")
    assert sdk not in loaded, (
        f"importing main.py loaded '{sdk}'. Something in main.py's import graph now reaches "
        f"src.agents.crewai_components (or another crewai-importing module) at module scope. The "
        f"AIREAL_LLM_MODE check belongs in src.core.runtime_flags, which has no heavy imports; "
        f"engine-specific modules stay behind the `if engine == 'crewai':` deferral."
    )


def test_the_flag_module_itself_stays_dependency_free() -> None:
    """`runtime_flags` is only useful if importing it stays cheap — pin that directly."""
    loaded = _modules_after_importing("src.core.runtime_flags")
    for sdk in _HEAVY_SDKS:
        assert sdk not in loaded, f"src.core.runtime_flags pulled in '{sdk}'; it exists precisely to avoid that"


def test_crewai_components_still_shares_the_one_implementation() -> None:
    """
    Guard the other half: the flag must not get re-implemented next to its consumers.

    Two copies of an env check drift, and a provenance record that disagrees with the branch the
    run actually took is the defect this area was fixed for.
    """
    from src.agents import crewai_components
    from src.core import runtime_flags

    src = Path(crewai_components.__file__).read_text(encoding="utf-8")
    assert "AIREAL_LLM_MODE" not in src.split('"""')[0] + "".join(src.split('"""')[2::2]), (
        "crewai_components appears to read AIREAL_LLM_MODE in code again rather than delegating "
        "to runtime_flags.llm_mode_enabled — that is a second source of truth"
    )
    assert crewai_components._llm_enabled() == runtime_flags.llm_mode_enabled()
