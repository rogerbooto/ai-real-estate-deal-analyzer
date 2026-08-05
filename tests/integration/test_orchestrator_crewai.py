from pathlib import Path

import pytest
from PIL import Image

from src.core.reports.generator import write_report
from src.orchestrators.crew import run_orchestration as run_deterministic
from src.orchestrators.crewai_runner import run_orchestration as run_crewai
from src.schemas.models import (
    FinancialInputs,
    FinancingTerms,
    IncomeModel,
    MarketAssumptions,
    OperatingExpenses,
    RefinancePlan,
    UnitIncome,
)


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
    assert result.thesis.verdict in {"BUY", "CONDITIONAL", "DECLINE"}

    # A real report is produced and writes cleanly
    out_file = tmp_path / "investment_analysis.md"
    write_report(str(out_file), result.insights, result.forecast, result.thesis)
    assert out_file.exists()
    assert "# Investment Analysis" in out_file.read_text(encoding="utf-8")


def _sample_assets_with_real_photos(tmp_path: Path) -> tuple[str, str]:
    """Like ``_sample_assets`` but with decodable images, so ``collect_local_assets``
    and ``build_photo_insights`` have something real to analyze (the zero-byte fixture
    used elsewhere is fine for structure-only checks, but ``collect_local_assets``
    filters out unreadable files, which would make media_insights spuriously None on
    both engines and defeat the parity assertion below).
    """
    listing_txt = tmp_path / "listing.txt"
    listing_txt.write_text("Charming triplex at 123 Main St. Parking and laundry.", encoding="utf-8")
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()
    for name in ("kitchen.jpg", "bathroom.jpg"):
        Image.new("RGB", (800, 600), "white").save(photos_dir / name)
    return str(listing_txt), str(photos_dir)


def test_crewai_media_fields_reach_parity_with_deterministic(monkeypatch, tmp_path):
    """F5: --engine crewai must populate media_insights/media_report like --engine
    deterministic, or the report silently loses its Media Overview / Photo Coverage
    sections. This test turns RED if crewai_runner.run_orchestration ever goes back
    to returning OrchestrationResult(insights, forecast, thesis) with the media
    fields defaulted away.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    inputs = _inputs()
    listing_txt, photos_dir = _sample_assets_with_real_photos(tmp_path)

    det_result = run_deterministic(
        inputs=inputs,
        listing_txt_path=listing_txt,
        photos_folder=photos_dir,
        horizon_years=10,
    )
    crew_result = run_crewai(
        inputs=inputs,
        listing_txt_path=listing_txt,
        photos_folder=photos_dir,
        horizon_years=10,
    )

    # The defect (F5) manifested as both fields silently defaulting to None on the
    # crewai path even though photos were supplied. Assert they are populated...
    assert crew_result.media_insights is not None
    assert crew_result.media_report is not None

    # ...and that they agree with the deterministic engine run over the same inputs
    # (parity, not just "truthy").
    assert crew_result.media_insights == det_result.media_insights
    assert crew_result.media_report == det_result.media_report


def test_crewai_missing_env_fails_friendly(monkeypatch, tmp_path):
    # Ensure common provider envs are absent
    for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(k, raising=False)

    with pytest.raises(ValueError) as e:
        run_crewai(inputs=_inputs())
    msg = str(e.value).lower()
    assert "engine='crewai' requested" in msg
    assert "openai_api_key" in msg or "provider api key" in msg
