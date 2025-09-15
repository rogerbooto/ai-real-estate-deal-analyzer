# tests/test_report_with_thesis.py
from pathlib import Path

from src.schemas.models import (
    FinancingTerms, OperatingExpenses, IncomeModel, RefinancePlan, MarketAssumptions,
    FinancialInputs, ListingInsights, InvestmentThesis
)
from src.tools.financial_model import run
from src.reports.generator import write_report

def test_report_includes_thesis(tmp_path: Path):
    inputs = FinancialInputs(
        financing=FinancingTerms(
            purchase_price=400_000.0, closing_costs=8_000.0,
            down_payment_rate=0.25, interest_rate=0.05, amort_years=30, io_years=0
        ),
        opex=OperatingExpenses(
            insurance=2000.0, taxes=5000.0, utilities=3000.0, water_sewer=1500.0,
            property_management=3600.0, repairs_maintenance=1800.0, trash=900.0,
            landscaping=600.0, snow_removal=400.0, hoa_fees=0.0, reserves=1200.0,
            other=300.0, expense_growth=0.02,
        ),
        income=IncomeModel(
            units=5, rent_month=1200.0, other_income_month=100.0,
            occupancy=0.95, bad_debt_factor=0.97, rent_growth=0.03
        ),
        refi=RefinancePlan(do_refi=False),
        market=MarketAssumptions(cap_rate_purchase=None, cap_rate_floor=0.05, cap_rate_spread_target=0.015),
        capex_reserve_upfront=0.0,
    )
    forecast = run(inputs, insights=None, horizon_years=10)
    thesis = InvestmentThesis(
        verdict="CONDITIONAL",
        rationale=["Cap-rate spread is thin.", "DSCR acceptable."],
        levers=["Negotiate price -$15k", "Trim PM fee to 7%"]
    )
    out = tmp_path / "analysis_with_thesis.md"
    write_report(str(out), ListingInsights(address="123 Main St"), forecast, thesis)
    text = out.read_text(encoding="utf-8")

    assert "## Investment Thesis" in text
    assert "**Verdict:** CONDITIONAL" in text
    assert "Negotiate price" in text
