# tests/agents/test_deterministic_path_needs_no_llm.py
"""**Instantiating an agent must never construct an LLM client.**

The project's load-bearing promise is that the deterministic path needs no model and no API
key. It was broken in a way no local run could see:

``ListingAnalystAgent.__init__`` (and the two deterministic agents) built a crewai ``Agent``
unconditionally at construction. crewai backfills a default model when ``llm`` is ``None`` --
the old constructor comment said so out loud -- and newer crewai *validates*
``OPENAI_API_KEY`` at construction rather than at call time. So merely creating the object
raised without a key.

Why the suite stayed green anyway: a local ``.env`` supplies a key, and ``requirements.txt``
pins only ``crewai>=0.28.0``, so CI installed a newer release than the developer machine had.
The failing test in CI was ``test_llm_mode_off_never_produces_an_llm_origin`` -- a test whose
entire premise is that no model is involved.

These tests pin the invariant itself rather than the symptom, so they hold on any crewai
version: construction must not touch a provider, and the deterministic path must work with
every provider key absent from the environment.
"""

from __future__ import annotations

import pytest

from src.agents import crewai_components as cc

_PROVIDER_KEYS = ("OPENAI_API_KEY", "OPENAI_MODEL", "CREWAI_MODEL", "ANTHROPIC_API_KEY")


@pytest.fixture
def no_provider_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every provider credential absent -- CI's environment, not the developer's."""
    for key in _PROVIDER_KEYS:
        monkeypatch.delenv(key, raising=False)


@pytest.mark.parametrize(
    "factory",
    [cc.ListingAnalystAgent, cc.FinancialForecasterAgent, cc.ChiefStrategistAgent],
    ids=["analyst", "forecaster", "strategist"],
)
def test_constructing_an_agent_never_needs_a_provider_key(factory, no_provider_env: None) -> None:
    """RED on revert: restore the eager `Agent(...)` in `__init__` and this raises on a
    crewai new enough to validate the key at construction -- which is precisely the version
    CI installs and the developer machine does not."""
    factory()


def test_the_two_deterministic_agents_build_no_crewai_shell_at_all(no_provider_env: None) -> None:
    """The forecaster and strategist never call `kickoff()`, so the shell was decorative.

    Asserted as an absence rather than "it didn't raise": a shell that cannot run is exactly
    what turned a dependency bump into a broken deterministic path, so it must stay gone.
    """
    for agent in (cc.FinancialForecasterAgent(), cc.ChiefStrategistAgent()):
        assert getattr(agent, "_agent", None) is None
        assert "agent" not in vars(agent), f"{type(agent).__name__} rebuilt a crewai shell at construction"


def test_the_analyst_defers_its_shell_until_the_llm_path_runs(no_provider_env: None) -> None:
    """The analyst legitimately needs an Agent -- but only inside `_run_llm`, which is
    already gated on `_ensure_crewai_ready()`. Nothing is built before then."""
    analyst = cc.ListingAnalystAgent()

    assert analyst._agent is None, "the analyst built its crewai shell eagerly again"
