# main.py
"""
Entry Point — AI Real Estate Deal Analyzer (V2)

Purpose
-------
Run the full analysis pipeline end-to-end and emit a Markdown report:
  1) Load financial inputs (sample defaults or --config JSON).
  2) Orchestrate agents:
       - Listing Analyst (text + photos → insights)
         * Uses the new CV Tagging Orchestrator (single door to deterministic/AI).
         * Honors flags:
             - AIREAL_PHOTO_AGENT=1  → route via PhotoTaggerAgent
             - AIREAL_USE_VISION=1   → always run AI on all readable images (batch-first)
       - Financial Forecaster (10-year pro forma & purchase metrics)
       - Chief Strategist (investment thesis)
  3) Generate a Markdown investment report.

Design
------
- CLI-friendly; pure Python. Heavy lifting is delegated to orchestrators/agents.
- Backwards compatible: deterministic pipeline remains the default.
- AI behavior is configuration-driven, not hardcoded here.

Usage
-----
    python main.py
    python main.py --config data/sample/inputs.json --out out.md --horizon 10 \
                   --listing data/sample/listing.txt --photos data/sample/photos
"""

from __future__ import annotations

from pathlib import Path
import argparse

from src.schemas.models import (
    FinancingTerms,
    OperatingExpenses,
    IncomeModel,
    UnitIncome,
    RefinancePlan,
    MarketAssumptions,
    FinancialInputs,
)
from src.inputs.inputs import InputsLoader, AppInputs
from src.orchestrators import crew as deterministic_orchestrator
from src.reports.generator import write_report


def build_sample_inputs() -> FinancialInputs:
    """Return baseline FinancialInputs for demo purposes (per-unit income)."""
    return FinancialInputs(
        financing=FinancingTerms(
            purchase_price=500_000.0,
            closing_costs=10_000.0,
            down_payment_rate=0.25,
            interest_rate=0.055,
            amort_years=30,
            io_years=0,
            # mortgage_insurance_rate kept default (0.04) and won't apply since DP ≥ 20%
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
            cap_rate_purchase=None,
            cap_rate_floor=0.05,
            cap_rate_spread_target=0.015,
        ),
        capex_reserve_upfront=0.0,
    )


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for configurable runs."""
    p = argparse.ArgumentParser(description="AI Real Estate Deal Analyzer (V2)")
    p.add_argument("--config", type=str, default=None, help="Path to JSON config (FinancialInputs or AppInputs).")
    p.add_argument("--out", type=str, default=None, help="Output Markdown path (overrides config).")
    p.add_argument("--horizon", type=int, default=None, help="Forecast horizon in years (overrides config).")
    p.add_argument("--listing", type=str, default=None, help="Path to listing .txt (overrides config).")
    p.add_argument("--photos", type=str, default=None, help="Path to photos folder (overrides config).")
    p.add_argument(
        "--engine",
        type=str,
        default=None,
        choices=["deterministic", "crewai"],
        help='Orchestration engine: "deterministic" or "crewai" (overrides config).',
    )
    return p.parse_args()


def ensure_sample_assets(listing_txt_path: str | None, photos_dir_path: str | None) -> tuple[str, str]:
    """
    Ensure there are usable assets for a demo run.
    If paths are not provided, create sample files under data/sample/.
    """
    if listing_txt_path and photos_dir_path:
        return listing_txt_path, photos_dir_path

    sample_dir = Path("data/sample")
    sample_dir.mkdir(parents=True, exist_ok=True)

    listing_txt = Path(listing_txt_path) if listing_txt_path else sample_dir / "listing.txt"
    if not listing_txt.exists():
        listing_txt.write_text("Charming triplex at 123 Main St. Parking and laundry.", encoding="utf-8")

    photos_dir = Path(photos_dir_path) if photos_dir_path else sample_dir / "photos"
    photos_dir.mkdir(exist_ok=True)

    # Minimal photo seed: deterministic path will use filename heuristics,
    # AI path will analyze pixels (mock/real provider). We include names that
    # exercise common tags.
    (photos_dir / "kitchen_island_stainless.jpg").write_bytes(b"")
    (photos_dir / "bath_double_vanity.jpg").write_bytes(b"")

    return str(listing_txt), str(photos_dir)


def main():
    """Run end-to-end analysis and write investment_analysis.md (or chosen output)."""
    print("Running AI Real Estate Deal Analyzer (V2)...")
    args = parse_args()

    loader = InputsLoader()

    if args.config:
        # Load AppInputs (FinancialInputs + run options) and apply CLI overrides if provided
        cfg: AppInputs = loader.load(args.config)
        cfg = loader.with_overrides(
            cfg,
            out=args.out,
            horizon=args.horizon,
            listing=args.listing,
            photos=args.photos,
            engine=args.engine,
        )
        inputs = cfg.inputs
        out_path = cfg.run.out
        horizon = cfg.run.horizon
        listing_arg = cfg.run.listing
        photos_arg = cfg.run.photos
        engine = (cfg.run.engine or "deterministic").strip().lower()
    else:
        # No config file → use demo inputs and CLI flags (if any)
        inputs = build_sample_inputs()
        out_path = args.out or "investment_analysis.md"
        horizon = args.horizon or 10
        listing_arg = args.listing
        photos_arg = args.photos
        engine = (args.engine or "deterministic").strip().lower()

    # Select high-level orchestration engine (full pipeline)
    if engine == "crewai":
        try:
            from src.orchestrators.crewai_runner import run_orchestration as run_selected
        except ImportError as e:
            raise ImportError(
                "engine='crewai' requested but the 'crewai' package is not available. "
                "Install it (e.g., `pip install crewai[tools]`) or use --engine deterministic."
            ) from e
    else:
        # Default deterministic pipeline (already uses the updated Listing Analyst,
        # which calls the CV Tagging Orchestrator under the hood)
        run_selected = deterministic_orchestrator.run_orchestration

    # Ensure demo/sample assets exist if not provided
    listing_txt, photos_dir = ensure_sample_assets(listing_arg, photos_arg)

    # Run pipeline
    try:
        result = run_selected(
            inputs=inputs,
            listing_txt_path=listing_txt,
            photos_folder=photos_dir,
            horizon_years=horizon,
        )

        write_report(out_path, result.insights, result.forecast, result.thesis)

        print(f"Report written to {out_path}")
        print(f"Thesis verdict: {result.thesis.verdict}")
    except Exception as e:
        print(f"Error during orchestration: {e}")
        raise


if __name__ == "__main__":
    main()
