import os
from pathlib import Path

import pytest

from src.schemas.models import (
    FinancingTerms,
    OperatingExpenses,
    IncomeModel,
    UnitIncome,
    RefinancePlan,
    MarketAssumptions,
    FinancialInputs,
)
from src.orchestrators.crewai_runner import run_orchestration as run_crewai
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
            units=[
                UnitIncome(rent_month=1200.0, other_income_month=50.0),
                UnitIncome(rent_month=1200.0, other_income_month=50.0),
                UnitIncome(rent_month=1200.0, other_income_month=0.0),
                UnitIncome(rent_month=1200.0, other_income_month=0.0),
            ],
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
            cap_rate_spread_target=0.015,
            cap_rate_floor=None,
        ),
    )


def _sample_assets(tmp_path: Path) -> tuple[str, str]:
    listing_txt = tmp_path / "listing.txt"
    listing_txt.write_text("Charming triplex at 123 Main St. Parking and laundry.", encoding="utf-8")
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()
    (photos_dir / "kitchen.jpg").write_bytes(b"")
    return str(listing_txt), str(photos_dir)


def test_crewai_orchestrator_runs_offline(monkeypatch, tmp_path):
    # Provide a dummy provider key so the env guard passes; no network is used.
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    inputs = _inputs()
    listing_txt, photos_dir = _sample_assets(tmp_path)

    result = run_crewai(
        inputs=inputs,
        listing_txt_path=listing_txt,
        photos_folder=photos_dir,
        horizon_years=10,
    )

    # Structure checks
    assert result.insights is not None
    assert result.forecast is not None
    assert result.thesis.verdict in {"BUY", "CONDITIONAL", "PASS"}

    # A real report is produced and writes cleanly
    out_file = tmp_path / "investment_analysis.md"
    write_report(str(out_file), result.insights, result.forecast, result.thesis)
    assert out_file.exists()
    assert "# Investment Analysis" in out_file.read_text(encoding="utf-8")


def test_crewai_missing_env_fails_friendly(monkeypatch, tmp_path):
    # Ensure common provider envs are absent
    for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(k, raising=False)

    with pytest.raises(ValueError) as e:
        run_crewai(inputs=_inputs())
    msg = str(e.value).lower()
    assert "engine='crewai' requested" in msg
    assert "openai_api_key" in msg or "provider api key" in msg
