# tests/integration/test_ai_claims_are_truthful.py
"""Documentation-vs-behaviour guards for the AI-adjacent claims.

Both claims pinned here were verified FALSE against the code they described:

* `ingest_cli --ai` help said output "does not change from the default path yet".
  `use_ai=1` demonstrably changes `version`, `image_detections`, `amenity_counts`,
  `detections_total` and `provenance`.
* `crewai_runner.run_orchestration` said the Agent/Task shells are "not executed here"
  and work is delegated "to local deterministic functions for identical math". Both are
  false when `AIREAL_LLM_MODE` is set: the listing analyst runs a real `crew.kickoff()`.

Each test turns RED if the old wording comes back, and the first one turns RED if the
wording stays but the behaviour changes underneath it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from src.cli.ingest_cli import _build_parser
from src.core.cv.photo_insights import build_photo_insights
from src.orchestrators import crewai_runner


def _ai_help() -> str:
    for action in _build_parser()._actions:
        if "--ai" in action.option_strings:
            return action.help or ""
    raise AssertionError("--ai flag is gone from ingest_cli")


#: The fields the `--ai` help text and the README row promise will differ. Measured against
#: the committed demo listing; keep the docs and this set in lockstep.
_DOCUMENTED_AI_DIFF_FIELDS = {"version", "image_detections", "amenity_counts", "detections_total", "provenance"}


def test_ai_flag_does_change_the_output_synthetic(tmp_path, monkeypatch) -> None:
    """The premise of the old help text, measured on a synthetic folder.

    If this ever goes GREEN-by-equality the help text must be rewritten again -- it is only
    honest while the outputs differ.
    """
    monkeypatch.setenv("AIREDEAL_CACHE_DIR", str(tmp_path / "cvcache"))
    photos = tmp_path / "photos"
    photos.mkdir()
    for i, shade in enumerate((255, 180, 90)):
        Image.new("RGB", (800, 600), (shade, shade, shade)).save(photos / f"room_{i}.jpg")

    default = build_photo_insights(photos, use_ai=False).model_dump()
    ai = build_photo_insights(photos, use_ai=True).model_dump()

    changed = {k for k in default if default[k] != ai[k]}
    assert changed, "--ai no longer changes anything; the help text now overclaims"
    assert {"version", "image_detections", "provenance"} <= changed


def test_ai_flag_changes_exactly_the_documented_fields_on_the_demo_listing(tmp_path, monkeypatch) -> None:
    """RED if the documented `--ai` diff drifts from the measured one, in either direction.

    Also pins the Task-2 outcome: `amenities` and `parking` must NOT be in the diff any more,
    because the fabricated street-parking detection that used to move them is gone.
    """
    photos = Path("data/sample_listings/36_kelly_moncton/photos")
    if not photos.is_dir():
        pytest.skip("demo photo bundle not present")
    monkeypatch.setenv("AIREDEAL_CACHE_DIR", str(tmp_path / "cvcache"))

    default = build_photo_insights(photos, use_ai=False).model_dump()
    ai = build_photo_insights(photos, use_ai=True).model_dump()

    changed = {k for k in default if default[k] != ai[k]}
    assert changed == _DOCUMENTED_AI_DIFF_FIELDS, f"documented --ai effect drifted; measured {sorted(changed)}"
    assert "amenities" not in changed
    assert "parking" not in changed


def test_ai_help_text_does_not_claim_output_is_unchanged() -> None:
    """RED on revert: the old wording is a verified-false claim."""
    help_text = _ai_help().lower()
    assert "does not change from the default path" not in help_text
    assert "output is unchanged" not in help_text


def test_ai_help_text_states_the_real_effect_and_does_not_overclaim() -> None:
    help_text = _ai_help().lower()
    # says what actually changes
    assert "image_detections" in help_text
    assert "amenity_counts" in help_text
    assert "provenance" in help_text
    # and does not sell a stub as a model
    assert "not a model call" in help_text or "not a model" in help_text
    assert "heuristic_stub" in help_text


def test_cli_readme_ai_row_matches_the_help_text() -> None:
    readme = Path("src/cli/README.md")
    if not readme.is_file():
        pytest.skip("src/cli/README.md not present")
    text = readme.read_text(encoding="utf-8")
    assert "output is unchanged from the default path" not in text
    assert "vision-stub-v1" in text
    assert "heuristic_stub" in text


def test_crewai_runner_docstrings_do_not_claim_the_shells_are_unexecuted() -> None:
    """RED on revert: `run_orchestration`'s docstring claimed no LLM ever runs here."""
    doc = (crewai_runner.run_orchestration.__doc__ or "").lower()
    module_doc = (crewai_runner.__doc__ or "").lower()

    assert "not executed here" not in doc
    assert "identical math" not in doc or "forecaster and strategist" in doc
    assert "kickoff" in doc, "the docstring must disclose that the analyst can run a real crew"
    # the module docstring must name where the LLM may and may not act
    assert "airealllm_mode" in module_doc.replace("_", "") or "aireal_llm_mode" in module_doc
    assert "verdict" in module_doc
