# tests/test_report_generator.py
from src.schemas.models import (
    FinancingTerms,
    OperatingExpenses,
    IncomeModel,
    RefinancePlan,
    MarketAssumptions,
    FinancialInputs,
    ListingInsights,
)
from src.tools.financial_model import run
from src.reports.generator import generate_report, write_report


def _inputs() -> FinancialInputs:
    return FinancialInputs(
        financing=FinancingTerms(
            purchase_price=500_000.0,
            closing_costs=10_000.0,
            down_payment_rate=0.25,
            interest_rate=0.055,
            amort_years=30,
            io_years=0,
        ),
        opex=OperatingExpenses(
            insurance=2400.0,
            taxes=6000.0,
            utilities=3600.0,
            water_sewer=1800.0,
            property_management=4800.0,
            repairs_maintenance=2400.0,
            trash=1200.0,
            landscaping=800.0,
            snow_removal=600.0,
            hoa_fees=0.0,
            reserves=1500.0,
            other=500.0,
            expense_growth=0.02,
        ),
        income=IncomeModel(
            units=4,
            rent_month=1200.0,
            other_income_month=100.0,
            occupancy=0.95,
            bad_debt_factor=0.97,
            rent_growth=0.03,
        ),
        refi=RefinancePlan(
            do_refi=True,
            year_to_refi=5,
            refi_ltv=0.75,
        ),
        market=MarketAssumptions(
            cap_rate_purchase=None,
            cap_rate_floor=0.05,
            cap_rate_spread_target=0.015,
        ),
        capex_reserve_upfront=0.0,
    )


def test_generate_report_contains_key_sections():
    inputs = _inputs()
    forecast = run(inputs, insights=None, horizon_years=10)
    insights = ListingInsights(address="123 Main St", amenities=["Parking", "Laundry"], notes=["Great curb appeal"])

    md = generate_report(insights, forecast)

    # Basic sanity: headers present
    assert "# Investment Analysis" in md
    assert "## Purchase Metrics" in md
    assert "## 10-Year Pro Forma (Summary)" in md
    assert "## Operating Expenses - Year 1 Detail" in md
    assert "## Returns Summary (10-Year)" in md

    # Table has at least 10 rows for 10 years
    assert md.count("| 1 |") >= 1
    assert md.count("| 10 |") >= 1

    # If refi enabled, refi section appears
    assert "## Refinance Event" in md

def test_write_report_creates_md_file(tmp_path):
    inputs = _inputs()
    forecast = run(inputs, insights=None, horizon_years=10)
    insights = ListingInsights(address="456 Elm St", amenities=["Garage"], notes=["Needs roof repair"])

    out_file = tmp_path / "investment_analysis.md"
    write_report(str(out_file), insights, forecast)

    # File should exist and be non-empty
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "# Investment Analysis" in content
    assert "## Purchase Metrics" in content
    assert "## 10-Year Pro Forma" in content
    assert len(content) > 200  # sanity check: not just a stub