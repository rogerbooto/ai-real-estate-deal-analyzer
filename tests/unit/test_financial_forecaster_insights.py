# tests/unit/test_financial_forecaster_insights.py
from __future__ import annotations

import math

from src.agents.financial_forecaster import forecast_financials
from src.core.ingest.listing_parser import parse_listing_string
from tests.utils import (
    make_financial_inputs,
    make_listing_insights,
)


def test_expense_bumps_and_notes_from_insights():
    fin = make_financial_inputs()
    # Trigger expense bumps: reserves (+$300) and R&M (+$200)
    insights = make_listing_insights(
        condition_tags=["old roof"],
        defects=["water stain"],
    )
    out = forecast_financials(fin, insights=insights, horizon_years=10)

    y1 = out.years[0]
    # Notes should carry explanatory strings
    assert any("old roof" in n.lower() for n in y1.notes)
    assert any("water stain" in n.lower() for n in y1.notes)

    # Reserves and R&M should be higher than base due to bumps
    assert y1.reserves >= fin.opex.reserves + 300.0 - 1e-9
    assert y1.repairs_maintenance >= fin.opex.repairs_maintenance + 200.0 - 1e-9


def test_income_not_adjusted_when_not_estimated():
    fin = make_financial_inputs()
    # Baseline (no insights)
    base = forecast_financials(fin, insights=None, horizon_years=5)

    # Provide income-boosting amenities, but *without* income_is_estimated flag → ignore uplifts
    insights = make_listing_insights(amenities=["in-unit laundry", "parking"])
    out = forecast_financials(fin, insights=insights, horizon_years=5)

    # Compare Year 1 GSI; should be identical (within epsilon)
    assert math.isclose(out.years[0].gsi, base.years[0].gsi, rel_tol=1e-9, abs_tol=1e-6)
    # And no "amenity uplift" notes should appear
    assert not any("amenity uplift" in n.lower() for n in out.years[0].notes)


def test_income_adjusted_when_estimated_flag_true():
    fin = make_financial_inputs()
    # Turn on income estimation flag so insight uplift is allowed
    fin = fin.model_copy(update={"income_is_estimated": True})  # relies on your new field

    insights = make_listing_insights(amenities=["in-unit laundry", "parking"])
    out = forecast_financials(fin, insights=insights, horizon_years=5)

    # Baseline for comparison: same inputs but with the flag off and no insights
    base = forecast_financials(
        fin.model_copy(update={"income_is_estimated": False}),
        insights=None,
        horizon_years=5,
    )

    # With amenities and estimated flag, GSI should increase vs. the no-insights case
    assert out.years[0].gsi > base.years[0].gsi
    # And Year 1 should record a note explaining the uplift
    assert any("amenity uplift" in n.lower() for n in out.years[0].notes)


# ---------------------------------------------------------------------------
# CV/label-normalization reconciliation (backlog #7 / Mission 2 "defect #4").
#
# The engine's OPEX modifier tests the literal, pre-normalization phrase "water stain"
# (`core/finance/engine.py::_apply_insight_modifiers`), but the real CV/label layer normalizes
# that phrase to the closed-set `DefectLabel.water_leak_suspected` *before* the engine ever sees
# it (`schemas/labels.py` DEFECT_TOKEN_ALIASES). `test_expense_bumps_and_notes_from_insights`
# above only proves the engine's own trigger works when handed the raw, unnormalized string
# directly -- it does NOT prove the trigger is reachable from real listing data, which is exactly
# what silently broke. These tests use the label the real pipeline actually emits.
# ---------------------------------------------------------------------------


def test_normalized_water_leak_label_still_trips_the_engines_opex_trigger():
    """RED on revert: a real (post-normalization) defect label must still reach the engine."""
    fin = make_financial_inputs()
    # This is what the CV/label layer actually emits for "water stain" -- see
    # `schemas/labels.py` DEFECT_TOKEN_ALIASES["water stain"] -> DefectLabel.water_leak_suspected.
    insights = make_listing_insights(defects=["water_leak_suspected"])

    out = forecast_financials(fin, insights=insights, horizon_years=10)
    y1 = out.years[0]

    assert any(
        "water stain" in n.lower() for n in y1.notes
    ), f"engine's OPEX-insight trigger did not fire for the normalized defect label; notes={y1.notes!r}"
    assert y1.repairs_maintenance >= fin.opex.repairs_maintenance + 200.0 - 1e-9


def test_reconciliation_does_not_mutate_the_callers_insights_or_add_a_duplicate_defect():
    """The translation is scoped to the engine call; the report-facing insights stay untouched."""
    fin = make_financial_inputs()
    insights = make_listing_insights(defects=["water_leak_suspected"])

    forecast_financials(fin, insights=insights, horizon_years=10)

    # No duplicate "water stain" bullet leaks into the object the report renders.
    assert insights.defects == ["water_leak_suspected"]


def test_real_listing_text_reaches_the_engine_trigger_end_to_end():
    """The exact reproduction: real listing copy -> the real parser -> the real engine."""
    fin = make_financial_inputs()
    listing_text = "123 Example Street, Anytown\n" "Condition: recently renovated; inspector noted a water stain on the basement ceiling.\n"
    insights = parse_listing_string(listing_text)
    # Confirms the parser really did normalize away the literal trigger phrase (sanity check on
    # the premise, not the fix itself).
    assert insights.defects == ["water_leak_suspected"]
    assert "water stain" not in insights.defects

    out = forecast_financials(fin, insights=insights, horizon_years=10)
    y1 = out.years[0]

    assert any("water stain" in n.lower() for n in y1.notes), (
        "the report's 'Adjustments Applied' section renders YearBreakdown.notes -- an empty list "
        "here means it silently disappears on real pipeline data (backlog #7)"
    )
