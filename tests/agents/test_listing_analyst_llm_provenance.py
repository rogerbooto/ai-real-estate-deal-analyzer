# tests/agents/test_listing_analyst_llm_provenance.py
"""
An LLM-authored ``ListingInsights`` says so, per tag.

``ListingAnalystAgent._run_llm`` is the one place in this codebase where a model actually writes
observations. Before per-tag provenance existed, its output was a list of bare strings
indistinguishable from the deterministic parser's -- so no consumer could honestly attribute a
tag to AI, and the report had to hedge with a blanket "AI photo tagging is on" caveat.

These tests turn RED if that stamping is reverted. They mock at the established seam
(``src.agents.crewai_components.Crew``, as in tests/agents/test_crewai_verdict_is_deterministic.py):
no network, no API key spend.

The fallback case is asserted just as hard: when the model call fails and the deterministic
analyst answers instead, those tags must NOT be labelled ``llm``. Overwriting real provenance with
an "AI wrote this" stamp would be a worse lie than having none.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from src.agents import crewai_components as cc

_LLM_OUTPUT: dict[str, Any] = {
    "address": "5 Elm St",
    "amenities": ["rooftop deck"],
    "notes": [],
    "condition_tags": ["old roof"],
    "defects": ["cracked foundation"],
}


class _Crew:
    """Stand-in for ``crewai.Crew`` whose ``kickoff()`` writes ``payload`` to every task output."""

    payload: Any = _LLM_OUTPUT

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    def kickoff(self) -> str:
        for task in self.kwargs.get("tasks", []):
            task.output = json.dumps(type(self).payload)
        return json.dumps(type(self).payload)


class _BrokenCrew(_Crew):
    """A model call that fails -- the analyst falls back to the deterministic path."""

    def kickoff(self) -> str:
        raise RuntimeError("model unavailable")


@pytest.fixture
def llm_mode(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AIREAL_LLM_MODE", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("CREWAI_MODEL", "test-model-x")
    monkeypatch.setattr(cc, "_CREW_AVAILABLE", True, raising=False)
    monkeypatch.setattr(cc, "Crew", _Crew, raising=False)
    monkeypatch.setattr(cc, "Process", type("_P", (), {"sequential": "sequential"}), raising=False)
    return monkeypatch


def _run(listing_path: str | None = None) -> Any:
    return cc.ListingAnalystAgent().run(listing_txt_path=listing_path, photos_folder=None)


def test_every_llm_authored_tag_is_recorded_as_llm_authored(llm_mode) -> None:
    got = _run()

    assert got.condition_tags == ["old roof"], "sanity: the model's output must be what reached the object"
    assert got.observations, "an LLM-authored ListingInsights shipped with no provenance at all"

    by_tag = {o.tag: o for o in got.observations}
    for tag in ("rooftop deck", "old roof", "cracked foundation"):
        assert tag in by_tag, f"model-authored tag {tag!r} has no provenance record"
        assert by_tag[tag].origin == "llm", f"{tag!r} was not attributed to the model"

    assert {o.kind for o in got.observations} == {"amenity", "condition", "defect"}


def test_llm_records_name_the_model_and_declare_it_a_model_not_a_stub(llm_mode) -> None:
    """``provider_kind='model'`` is what licenses a caller to say "AI observed X"."""
    got = _run()

    # Without this the loop below passes vacuously on an empty ledger -- i.e. it would stay GREEN
    # on exactly the revert it exists to catch.
    assert got.observations, "an LLM-authored ListingInsights shipped with no provenance at all"
    for obs in got.observations:
        assert obs.provider == "test-model-x", "the model that authored the tag was not recorded"
        assert obs.provider_kind == "model", "an LLM is a model, not a heuristic stub"


def test_deterministic_fallback_is_not_mislabelled_as_llm_authored(llm_mode, tmp_path) -> None:
    """RED on revert: a failed model call must not stamp the deterministic parser's tags as AI."""
    listing = tmp_path / "listing.txt"
    listing.write_text("11 Spruce Road. Recently renovated with in-unit laundry.", encoding="utf-8")

    llm_mode.setattr(cc, "Crew", _BrokenCrew, raising=False)
    got = _run(str(listing))

    assert "renovated" in got.condition_tags, "sanity: the deterministic parser must have answered"
    assert got.observations, "the fallback lost its own provenance"
    assert all(o.origin != "llm" for o in got.observations), f"deterministic tags were stamped as model-authored: {got.observations}"
    assert any(o.origin == "listing_text" for o in got.observations)


def test_unparseable_model_output_also_falls_back_without_an_llm_stamp(llm_mode, tmp_path) -> None:
    """Same guarantee via the other fallback door: valid call, unusable JSON."""
    listing = tmp_path / "listing.txt"
    listing.write_text("11 Spruce Road. Recently renovated with in-unit laundry.", encoding="utf-8")

    class _GarbageCrew(_Crew):
        def kickoff(self) -> str:
            for task in self.kwargs.get("tasks", []):
                task.output = "I am not JSON at all."
            return ""

    llm_mode.setattr(cc, "Crew", _GarbageCrew, raising=False)
    got = _run(str(listing))

    assert "renovated" in got.condition_tags
    assert all(o.origin != "llm" for o in got.observations), "unparseable model output was still credited to the model"


def test_llm_mode_off_never_produces_an_llm_origin(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("AIREAL_LLM_MODE", raising=False)
    listing = tmp_path / "listing.txt"
    listing.write_text("11 Spruce Road. Recently renovated with in-unit laundry.", encoding="utf-8")

    got = cc.ListingAnalystAgent().run(listing_txt_path=str(listing), photos_folder=None)

    assert got.observations
    assert all(o.origin == "listing_text" for o in got.observations)
