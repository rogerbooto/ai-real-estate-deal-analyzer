from pathlib import Path

from src.schemas.models import (
    FinancingTerms,
    OperatingExpenses,
    IncomeModel,
    UnitIncome,
    RefinancePlan,
    MarketAssumptions,
    FinancialInputs,
)
from src.orchestrator.crew import run_orchestration
from src.reports.generator import write_report


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
            units=[UnitIncome(rent_month=1200.0, other_income_month=100.0) for _ in range(4)],
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


def test_orchestrator_runs_end_to_end_and_writes_report(tmp_path: Path):
    # Prepare minimal text + photos (optional)
    listing_txt = tmp_path / "listing.txt"
    listing_txt.write_text("Charming triplex at 123 Main St. Parking and laundry.", encoding="utf-8")
    (tmp_path / "photos").mkdir()
    (tmp_path / "photos" / "kitchen_updated.jpg").write_bytes(b"")

    result = run_orchestration(
        inputs=_inputs(),
        listing_txt_path=str(listing_txt),
        photos_folder=str(tmp_path / "photos"),
        horizon_years=10,
    )

    # Structure checks
    assert result.insights is not None
    assert result.forecast is not None
    assert result.thesis.verdict in {"BUY", "CONDITIONAL", "PASS"}

    # Write a real report to disk via the report generator
    out_file = tmp_path / "investment_analysis.md"
    write_report(str(out_file), result.insights, result.forecast)
    assert out_file.exists()
    assert "# Investment Analysis" in out_file.read_text(encoding="utf-8")
