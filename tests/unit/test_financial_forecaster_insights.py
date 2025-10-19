# tests/unit/test_financial_forecaster_insights.py
from __future__ import annotations

import math

from src.agents.financial_forecaster import forecast_financials
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
