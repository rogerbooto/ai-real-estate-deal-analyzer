# tests/orchestrators/test_baseline_outlook.py
"""
``build_baseline_outlook`` — the second engine run that gives the report its "before" column.

The engine is deterministic and cheap, so the honest way to produce an observation-free picture is
to run it again with ``insights=None`` rather than to reverse the modifiers arithmetically. This
module pins the two things that matter about that: it produces a genuinely different forecast when
an observation fired, and it produces **nothing at all** when none did — the second half is what
keeps every existing report byte-identical and what stops the pipeline paying for a redundant run.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from src.agents.chief_strategist import synthesize_thesis
from src.agents.financial_forecaster import forecast_financials
from src.orchestrators.crew import build_baseline_outlook, run_orchestration as run_deterministic
from src.orchestrators.crewai_runner import run_orchestration as run_crewai
from src.schemas.models import ListingInsights
from tests.utils import make_financial_inputs

OBSERVED_INSIGHTS = ListingInsights(condition_tags=["old roof"], defects=["water stain"])


def test_returns_none_when_no_observation_fired():
    """No note means ``insights=None`` would reproduce the forecast exactly — so no second run."""
    inputs = make_financial_inputs()
    forecast = forecast_financials(inputs=inputs, insights=None, horizon_years=10)

    assert build_baseline_outlook(inputs, forecast, horizon_years=10) is None


def test_returns_none_when_insights_exist_but_trip_no_modifier():
    """Observations that match no engine rule change no number, so there is nothing to compare."""
    inputs = make_financial_inputs()
    insights = ListingInsights(condition_tags=["updated kitchen"], amenities=["balcony"])
    forecast = forecast_financials(inputs=inputs, insights=insights, horizon_years=10)

    assert not any(y.notes for y in forecast.years)
    assert build_baseline_outlook(inputs, forecast, horizon_years=10) is None


def test_builds_the_observation_free_counterpart_when_a_modifier_fired():
    """
    RED on revert: the returned forecast must be the *same deal without the observations*, i.e.
    exactly what the engine produces for ``insights=None`` — not a copy of the observed one.
    """
    inputs = make_financial_inputs()
    observed = forecast_financials(inputs=inputs, insights=OBSERVED_INSIGHTS, horizon_years=10)
    assert observed.years[0].notes

    outlook = build_baseline_outlook(inputs, observed, horizon_years=10)

    assert outlook is not None
    expected = forecast_financials(inputs=inputs, insights=None, horizon_years=10)
    assert outlook.forecast == expected
    assert outlook.thesis == synthesize_thesis(expected)
    # The two OPEX rules add exactly $500/yr in Year 1; the baseline must not carry it.
    assert not outlook.forecast.years[0].notes
    assert round(observed.years[0].total_opex - outlook.forecast.years[0].total_opex, 2) == 500.00


def test_horizon_is_carried_so_the_two_pictures_are_comparable():
    inputs = make_financial_inputs()
    observed = forecast_financials(inputs=inputs, insights=OBSERVED_INSIGHTS, horizon_years=5)

    outlook = build_baseline_outlook(inputs, observed, horizon_years=5)

    assert outlook is not None
    assert len(outlook.forecast.years) == len(observed.years) == 5


def _assets(tmp_path: Path) -> tuple[str, str]:
    listing = tmp_path / "listing.txt"
    # "Parking" normalizes to the ``parking`` amenity, one of the literal tags the engine matches.
    listing.write_text("Charming triplex at 123 Main St. Parking and laundry.", encoding="utf-8")
    photos = tmp_path / "photos"
    photos.mkdir()
    Image.new("RGB", (640, 480), "white").save(photos / "kitchen.jpg")
    return str(listing), str(photos)


@pytest.mark.parametrize("run_orchestration", [run_deterministic, run_crewai], ids=["deterministic", "crewai"])
def test_both_engines_reach_the_report_with_a_baseline(monkeypatch, tmp_path, run_orchestration):
    """
    End-to-end reachability. ``income_is_estimated=True`` makes the amenity-uplift rules live, so a
    real listing parse produces a real observation and both orchestrators must carry the resulting
    baseline out to the caller. Without it the report's comparison section is unreachable in
    production no matter how well the renderer works.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")  # only read by the crewai engine's env guard
    inputs = make_financial_inputs().model_copy(update={"income_is_estimated": True})
    listing, photos = _assets(tmp_path)

    result = run_orchestration(inputs=inputs, listing_txt_path=listing, photos_folder=photos, horizon_years=10)

    assert result.forecast.years[0].notes, "listing no longer trips a modifier - update the fixture"
    assert result.baseline is not None
    assert not result.baseline.forecast.years[0].notes
    assert result.baseline.thesis is not None


@pytest.mark.parametrize("run_orchestration", [run_deterministic, run_crewai], ids=["deterministic", "crewai"])
def test_both_engines_leave_baseline_none_when_nothing_fired(monkeypatch, tmp_path, run_orchestration):
    """The default path: no observation, no baseline, no new section in the report."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    inputs = make_financial_inputs()  # income_is_estimated defaults False -> amenity rules inert
    listing, photos = _assets(tmp_path)

    result = run_orchestration(inputs=inputs, listing_txt_path=listing, photos_folder=photos, horizon_years=10)

    assert not any(y.notes for y in result.forecast.years)
    assert result.baseline is None
