# tests/core/test_runtime_flags.py
"""
S4: ``AIREAL_LLM_MODE`` parsing must be case-insensitive and agree with the sibling flag
``AIREAL_USE_VISION`` (``cv_tagging_orchestrator._VISION_ENABLED``), which already lowercases.

Before the fix, ``llm_mode_enabled()`` compared the raw (non-lowercased) env value against
``_TRUTHY``, so ``AIREAL_LLM_MODE=TRUE`` silently evaluated to ``False`` while
``AIREAL_LLM_MODE=true`` evaluated to ``True`` -- a wrong-way default (opted-in feature reads as
off) on a flag the run-provenance appendix uses to say whether a model authored the observations.
That is exactly backwards for a provenance-bearing flag under the project's loud-fail-on-misconfig
rule: silently treating "TRUE" as "off" is worse than the reverse, because a reader trusts the
provenance line without knowing the model call never happened.
"""

from __future__ import annotations

import pytest

from src.core.runtime_flags import llm_mode_enabled

# Every case-variant spelling exercised by the S4 report, and what it must resolve to. This is the
# same truthy vocabulary the sibling flag `cv_tagging_orchestrator._VISION_ENABLED` accepts
# ("1", "true", "yes", "on"), plus their upper/mixed-case forms.
_TRUTHY_CASES = [
    "1",
    "true",
    "TRUE",
    "True",
    "yes",
    "Yes",
    "YES",
    "on",
    "ON",
    "On",
]

_FALSY_CASES = [
    "0",
    "false",
    "FALSE",
    "no",
    "No",
    "off",
    "OFF",
    "",
    "  ",
    "maybe",
]


@pytest.mark.parametrize("value", _TRUTHY_CASES)
def test_llm_mode_enabled_true_for_every_case_variant(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("AIREAL_LLM_MODE", value)
    assert llm_mode_enabled() is True, f"AIREAL_LLM_MODE={value!r} must enable LLM mode regardless of case"


@pytest.mark.parametrize("value", _FALSY_CASES)
def test_llm_mode_enabled_false_for_non_truthy_values(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("AIREAL_LLM_MODE", value)
    assert llm_mode_enabled() is False


def test_llm_mode_enabled_false_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AIREAL_LLM_MODE", raising=False)
    assert llm_mode_enabled() is False


def test_llm_mode_enabled_agrees_with_lowercase_and_uppercase_spelling_of_same_intent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The literal S4 repro: 'true' and 'TRUE' must not disagree with each other."""
    monkeypatch.setenv("AIREAL_LLM_MODE", "true")
    lower_result = llm_mode_enabled()
    monkeypatch.setenv("AIREAL_LLM_MODE", "TRUE")
    upper_result = llm_mode_enabled()
    assert lower_result == upper_result is True
