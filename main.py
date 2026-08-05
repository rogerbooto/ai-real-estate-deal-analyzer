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
    python main.py --config data/sample_listings/36_kelly_moncton/inputs.json --out out.md --horizon 10 \
                   --listing data/sample_listings/36_kelly_moncton/listing.txt --photos data/sample_listings/36_kelly_moncton/photos

`--listing`/`--photos` require `--config` (see `resolve_config_path`): an asset without
financials would otherwise be underwritten against the demo deal's numbers.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from src.core.reports.generator import write_report
from src.core.runtime_flags import llm_mode_enabled
from src.inputs.inputs import AppInputs, InputsLoader
from src.orchestrators import crew as deterministic_orchestrator
from src.orchestrators.cv_tagging_orchestrator import vision_enabled
from src.schemas.models import (
    FinancialInputs,
    FinancingTerms,
    IncomeModel,
    MarketAssumptions,
    OperatingExpenses,
    RefinancePlan,
    RunProvenance,
    UnitIncome,
)

#: Committed demo bundle (listing + photos + inputs.json) used when no paths are supplied.
DEFAULT_BUNDLE = Path("data/sample_listings/36_kelly_moncton")
DEFAULT_INPUTS = DEFAULT_BUNDLE / "inputs.json"


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
    p.add_argument(
        "--listing",
        type=str,
        default=None,
        help="Path to listing .txt (overrides config). Requires --config describing the same property.",
    )
    p.add_argument(
        "--photos",
        type=str,
        default=None,
        help="Path to photos folder (overrides config). Requires --config describing the same property.",
    )
    p.add_argument(
        "--engine",
        type=str,
        default=None,
        choices=["deterministic", "crewai"],
        help='Orchestration engine: "deterministic" or "crewai" (overrides config).',
    )
    p.add_argument(
        "--scenarios",
        action="store_true",
        default=False,
        help="Opt-in: append a 'Market Scenarios' what-if overlay (default OFF). Requires a market "
        "block in the inputs (or market.cap_rate_purchase set) or it loud-fails by design.",
    )
    return p.parse_args()


def ensure_sample_assets(listing_txt_path: str | None, photos_dir_path: str | None) -> tuple[str, str]:
    """
    Resolve demo assets, defaulting to the committed sample bundle.

    Unfilled paths fall back to DEFAULT_BUNDLE. Nothing is fabricated: the bundle ships
    with the repo, so a missing asset is a real problem worth surfacing rather than one
    to paper over with placeholder stubs that produce a report about nothing.
    """
    if listing_txt_path and photos_dir_path:
        return listing_txt_path, photos_dir_path

    listing_txt = Path(listing_txt_path) if listing_txt_path else DEFAULT_BUNDLE / "listing.txt"
    photos_dir = Path(photos_dir_path) if photos_dir_path else DEFAULT_BUNDLE / "photos"

    missing = [str(p) for p in (listing_txt, photos_dir) if not p.exists()]
    if missing:
        raise SystemExit(
            f"Demo assets not found: {', '.join(missing)}. "
            "Pass --listing/--photos explicitly, or restore the sample bundle under data/sample_listings/."
        )

    return str(listing_txt), str(photos_dir)


def resolve_config_path(config: str | None, listing: str | None, photos: str | None) -> str | None:
    """
    Decide which financial config the run uses, refusing to pair an asset with foreign numbers.

    ``--listing``/``--photos`` say *which property* to report on; the config says *what the
    money looks like*. They are only meaningful together. Supplying an asset without a config
    used to fall through to the committed demo bundle, so the report described the caller's
    address against 36 Kelly's purchase price, rent roll, and financing — silently, with no
    line in the output admitting the mismatch. That is a report asserting something false, so
    it fails loudly instead of guessing which of the two properties the reader meant.

    Args:
        config: ``--config`` path, if given.
        listing: ``--listing`` path, if given.
        photos: ``--photos`` path, if given.

    Returns:
        The config path to load, or None when there is nothing to load (no ``--config`` and no
        committed demo bundle) and the caller should fall back to ``build_sample_inputs``.

    Raises:
        SystemExit: an asset flag was supplied without ``--config``.
    """
    if config:
        return config

    supplied = [flag for flag, value in (("--listing", listing), ("--photos", photos)) if value]
    if supplied:
        raise SystemExit(
            f"{' and '.join(supplied)} supplied without --config. The financials would then come from the "
            f"built-in demo deal ({DEFAULT_INPUTS}) rather than from your property, and the report would "
            "pair your address with another property's purchase price, rent roll, and financing without "
            "saying so. Pass --config pointing at a JSON that describes the same property (see "
            f"{DEFAULT_INPUTS} for the shape), or run `python main.py` with no arguments to underwrite "
            "the demo bundle."
        )

    # Nothing supplied: the zero-argument demo underwrites one coherent deal (listing, photos,
    # and financials all 36 Kelly) rather than reporting a real address against unrelated numbers.
    return str(DEFAULT_INPUTS) if DEFAULT_INPUTS.exists() else None


def main() -> None:
    """Run end-to-end analysis and write investment_analysis.md (or chosen output)."""
    print("Running AI Real Estate Deal Analyzer (V2)...")
    args = parse_args()

    loader = InputsLoader()

    # Zero arguments → the committed sample bundle. An asset flag without --config loud-fails
    # rather than borrowing the demo deal's financials (see resolve_config_path).
    config_path = resolve_config_path(args.config, args.listing, args.photos)

    if config_path:
        # Load AppInputs (FinancialInputs + run options) and apply CLI overrides if provided.
        # Precedence for `scenarios`: explicit CLI flag > env (applied in load) > JSON > default False.
        # `--scenarios` is store_true (False when absent) → pass True only when set, None otherwise,
        # so an unset flag defers to env/JSON.
        cfg: AppInputs = loader.load(config_path)
        cfg = loader.with_overrides(
            cfg,
            out=args.out,
            horizon=args.horizon,
            listing=args.listing,
            photos=args.photos,
            engine=args.engine,
            scenarios=True if args.scenarios else None,
        )
        inputs = cfg.inputs
        out_path = cfg.run.out
        horizon = cfg.run.horizon
        listing_arg = cfg.run.listing
        photos_arg = cfg.run.photos
        engine = (cfg.run.engine or "deterministic").strip().lower()
        run_scenarios_flag = cfg.run.scenarios
        # The market-snapshot block is carried alongside the frozen FinancialInputs (see AppInputs.market).
        market_block = cfg.market
    else:
        # Neither --config nor the sample bundle → fall back to hardcoded demo inputs.
        # resolve_config_path guarantees no asset flag reached here, so these are both None
        # and ensure_sample_assets will report the missing bundle rather than pair an asset
        # with the hardcoded numbers.
        inputs = build_sample_inputs()
        out_path = args.out or "investment_analysis.md"
        horizon = args.horizon or 10
        listing_arg = args.listing
        photos_arg = args.photos
        engine = (args.engine or "deterministic").strip().lower()
        env_scenarios = os.getenv("AIREAL_SCENARIOS", "").strip().lower() in ("1", "true", "yes", "on")
        run_scenarios_flag = args.scenarios or env_scenarios
        market_block = None  # no JSON → no market block; the resolver loud-fails by design (§5)

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

        # Opt-in Market Scenarios overlay (default OFF). All snapshot build, scenario runs, and the
        # market imports live strictly inside this branch → with scenarios OFF the hot path adds zero
        # scenario/market imports and write_report produces byte-identical output (§6 / C2 / G2).
        scenarios_analysis = None
        if run_scenarios_flag:
            from src.market.scenario_runner import resolve_snapshot, run_scenarios

            snapshot = resolve_snapshot(inputs, market_block=market_block)
            scenarios_analysis = run_scenarios(inputs, snapshot)

        # Record how this report was produced. Env knobs silently change the figures, and a
        # gitignored .env means another machine can disagree with no evidence of why.
        provenance = RunProvenance(
            engine=engine,
            scenarios_enabled=bool(run_scenarios_flag),
            vision_enabled=vision_enabled(),
            # Report what ACTUALLY happened, not merely what the env asked for. AIREAL_LLM_MODE
            # is only consulted by the crewai engine, and even there the LLM call can fail and
            # fall back to the deterministic path -- so the env var alone would claim
            # "LLM-authored observations: on" for runs where nothing was LLM-authored. That is
            # the same over-claim as M12 in the opposite direction. The per-tag provenance ledger
            # (R-4) is the ground truth: an observation carries origin="llm" only if a model
            # really wrote it.
            llm_mode_enabled=llm_mode_enabled() and any(o.origin == "llm" for o in (getattr(result.insights, "observations", None) or [])),
            config_path=config_path,
        )

        write_report(
            out_path,
            result.insights,
            result.forecast,
            result.thesis,
            media_insights=getattr(result, "media_insights", None),
            media_report=getattr(result, "media_report", None),
            provenance=provenance,
            scenarios=scenarios_analysis,
            # None unless a listing observation actually moved a number, in which case the
            # report shows the same deal with and without those observations. getattr keeps
            # third-party/older OrchestrationResult shapes working, as the media fields do.
            baseline=getattr(result, "baseline", None),
        )

        print(f"Report written to {out_path}")
        print(f"Thesis verdict: {result.thesis.verdict}")
    except Exception as e:
        print(f"Error during orchestration: {e}")
        raise


if __name__ == "__main__":
    main()
