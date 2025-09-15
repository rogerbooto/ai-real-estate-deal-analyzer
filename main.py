# main.py
"""
Entry point for The AI Real Estate Deal Analyzer (V1).

This script:
  1. Defines sample financial inputs (hardcoded for now).
  2. Runs the financial forecasting engine.
  3. Generates a Markdown investment analysis report.
  4. Writes the report to investment_analysis.md in the project root.

Usage:
    python main.py

Future V2+ will replace hardcoded inputs with:
  - File ingestion for listings (text + photos).
  - User-provided financial assumptions.
  - Agent orchestration for automated insights.
"""

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
from src.reports.generator import write_report


def build_sample_inputs() -> FinancialInputs:
    """Return baseline FinancialInputs for demo purposes."""
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


def main():
    """Run demo analysis and write investment_analysis.md."""
    print("Running AI Real Estate Deal Analyzer (V1 demo)...")

    inputs = build_sample_inputs()
    insights = ListingInsights(
        address="123 Main St",
        amenities=["Parking", "Laundry"],
        notes=["Sample property for demo run"],
    )

    forecast = run(inputs, insights, horizon_years=10)

    out_file = "investment_analysis.md"
    write_report(out_file, insights, forecast)

    print(f"Report written to {out_file}")


if __name__ == "__main__":
    main()
