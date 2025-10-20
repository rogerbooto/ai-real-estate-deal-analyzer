# tests/utils.py
"""
Single source of truth for test data, factories, and canonical payloads.
Update values here to cascade across the test suite.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Project models
from src.schemas.models import (
    # Financial model types
    FinancialInputs,
    FinancingTerms,
    HtmlSnapshot,
    HypothesisSet,
    IncomeModel,
    InvestmentThesis,
    ListingInsights,
    MarketAssumptions,
    MarketHypothesis,
    MarketSnapshot,
    OperatingExpenses,
    RefinancePlan,
    UnitIncome,
)

# -----------------------------
# Global defaults (edit once)
# -----------------------------

DEFAULT_REGION = "TestRegion"
DEFAULT_VACANCY = 0.05
DEFAULT_CAP_RATE = 0.065
DEFAULT_RENT_GROWTH = 0.03
DEFAULT_EXPENSE_GROWTH = 0.02
DEFAULT_MARKET_RATE = 0.045

# Refi defaults
DEFAULT_REFI = RefinancePlan(
    do_refi=True,
    year_to_refi=5,
    refi_ltv=0.75,
    exit_cap_rate=None,
    market_cap_rate=None,
)

# Market policy defaults
DEFAULT_MARKET_ASSUMPTIONS = MarketAssumptions(
    cap_rate_purchase=None,
    cap_rate_floor=0.05,
    cap_rate_spread_target=0.015,
)

# Listing insights defaults
DEFAULT_LISTING_INSIGHTS = ListingInsights(address=None, amenities=[], condition_tags=[], defects=[], notes=[])

DEFAULT_THESES: list[InvestmentThesis] = [
    InvestmentThesis(
        title="Cashflow First",
        body="Prioritize DSCR >= 1.2",
        verdict="PASS",
        rationale=[
            "Ensures the property comfortably covers debt service",
            "Builds resilience against minor shocks",
        ],
    ),
    InvestmentThesis(
        title="Value-Add",
        body="Budget light renovations for rent lift",
        verdict="CONSIDER",
        rationale=[
            "Upside depends on local comp premiums",
            "Execution risk on timeline and scope",
        ],
    ),
]

# -----------------------------
# Snapshot/Hypotheses factories
# -----------------------------


def make_snapshot(
    region: str = DEFAULT_REGION,
    vacancy_rate: float = DEFAULT_VACANCY,
    cap_rate: float = DEFAULT_CAP_RATE,
    rent_growth: float = DEFAULT_RENT_GROWTH,
    expense_growth: float = DEFAULT_EXPENSE_GROWTH,
    interest_rate: float = DEFAULT_MARKET_RATE,
    notes: str | None = None,
) -> MarketSnapshot:
    return MarketSnapshot(
        region=region,
        vacancy_rate=vacancy_rate,
        cap_rate=cap_rate,
        rent_growth=rent_growth,
        expense_growth=expense_growth,
        interest_rate=interest_rate,
        notes=notes,
    )


def make_hypothesis(
    rent_delta: float = 0.01,
    expense_growth_delta: float = 0.005,
    interest_rate_delta: float = 0.0,
    cap_rate_delta: float = 0.0025,
    vacancy_delta: float = 0.0,
    str_viability: bool = True,
    prior: float = 0.25,
    rationale: str = "Factory default hypothesis",
) -> MarketHypothesis:
    return MarketHypothesis(
        rent_delta=rent_delta,
        expense_growth_delta=expense_growth_delta,
        interest_rate_delta=interest_rate_delta,
        cap_rate_delta=cap_rate_delta,
        vacancy_delta=vacancy_delta,
        str_viability=str_viability,
        prior=prior,
        rationale=rationale,
    )


def make_hypothesis_set(
    region: str = DEFAULT_REGION,
    seed: int = 42,
    n: int = 3,
    base_rationale: str = "Hypothesis",
) -> HypothesisSet:
    items: tuple[MarketHypothesis, ...] = tuple(make_hypothesis(rationale=f"{base_rationale} {i + 1}") for i in range(n))
    return HypothesisSet(snapshot_region=region, seed=seed, items=items)


# -----------------------------
# Financial factories
# -----------------------------


def make_financing_terms(
    purchase_price: float = 500_000.0,
    closing_costs: float = 10_000.0,
    down_payment_rate: float = 0.20,
    interest_rate: float = 0.055,
    amort_years: int = 30,
    io_years: int = 0,
    mortgage_insurance_rate: float = 0.0,
) -> FinancingTerms:
    return FinancingTerms(
        purchase_price=purchase_price,
        closing_costs=closing_costs,
        down_payment_rate=down_payment_rate,
        interest_rate=interest_rate,
        amort_years=amort_years,
        io_years=io_years,
        mortgage_insurance_rate=mortgage_insurance_rate,
    )


def make_opex(
    insurance: float = 2000.0,
    taxes: float = 5000.0,
    utilities: float = 3000.0,
    water_sewer: float = 1500.0,
    property_management: float = 3600.0,
    repairs_maintenance: float = 1800.0,
    trash: float = 900.0,
    landscaping: float = 600.0,
    snow_removal: float = 400.0,
    hoa_fees: float = 0.0,
    reserves: float = 1000.0,
    other: float = 500.0,
    expense_growth: float = 0.02,
) -> OperatingExpenses:
    return OperatingExpenses(
        insurance=insurance,
        taxes=taxes,
        utilities=utilities,
        water_sewer=water_sewer,
        property_management=property_management,
        repairs_maintenance=repairs_maintenance,
        trash=trash,
        landscaping=landscaping,
        snow_removal=snow_removal,
        hoa_fees=hoa_fees,
        reserves=reserves,
        other=other,
        expense_growth=expense_growth,
    )


def make_income_model(
    num_units: int = 4,
    rent_month: float = 1200.0,
    other_income_month: float = 100.0,
    occupancy: float = 0.95,
    bad_debt_factor: float = 0.97,
    rent_growth: float = 0.03,
) -> IncomeModel:
    units = [UnitIncome(rent_month=rent_month, other_income_month=other_income_month) for _ in range(num_units)]
    return IncomeModel(
        units=units,
        occupancy=occupancy,
        bad_debt_factor=bad_debt_factor,
        rent_growth=rent_growth,
    )


def make_refi_plan(**overrides: Any) -> RefinancePlan:
    base = DEFAULT_REFI
    return RefinancePlan(
        do_refi=overrides.get("do_refi", base.do_refi),
        year_to_refi=overrides.get("year_to_refi", base.year_to_refi),
        refi_ltv=overrides.get("refi_ltv", base.refi_ltv),
        exit_cap_rate=overrides.get("exit_cap_rate", base.exit_cap_rate),
        market_cap_rate=overrides.get("market_cap_rate", base.market_cap_rate),
    )


def make_market_assumptions(**overrides: Any) -> MarketAssumptions:
    base = DEFAULT_MARKET_ASSUMPTIONS
    return MarketAssumptions(
        cap_rate_purchase=overrides.get("cap_rate_purchase", base.cap_rate_purchase),
        cap_rate_floor=overrides.get("cap_rate_floor", base.cap_rate_floor),
        cap_rate_spread_target=overrides.get("cap_rate_spread_target", base.cap_rate_spread_target),
    )


def make_listing_insights(**overrides: Any) -> ListingInsights:
    return ListingInsights(
        address=overrides.get("address"),
        amenities=overrides.get("amenities", []),
        condition_tags=overrides.get("condition_tags", []),
        defects=overrides.get("defects", []),
        notes=overrides.get("notes", []),
    )


def make_financial_inputs(
    do_refi: bool = False,
    num_units: int = 4,
) -> FinancialInputs:
    return FinancialInputs(
        financing=make_financing_terms(),
        opex=make_opex(),
        income=make_income_model(num_units=num_units),
        refi=make_refi_plan(do_refi=do_refi),
        market=make_market_assumptions(),
    )


# -----------------------------
# Report helpers
# -----------------------------


def default_theses() -> list[InvestmentThesis]:
    return list(DEFAULT_THESES)


def make_document(
    tmp_dir: Path,
    *,
    html: str | None = None,
    text: str | None = None,
    filename: str | None = None,
) -> Path:
    """
    Create a simple document in tmp_dir and return its Path.

    - If `html` is provided, writes an .html file (unless a custom filename is given).
    - Else if `text` is provided, writes a .txt file (unless a custom filename is given).
    - Exactly one of `html` or `text` should be provided.
    """
    if (html is None) and (text is None):
        raise ValueError("Provide exactly one of `html` or `text`.")

    if html is not None:
        name = filename or "doc.html"
        content = html
    else:
        name = filename or "doc.txt"
        content = text or ""

    tmp_dir.mkdir(parents=True, exist_ok=True)
    path = tmp_dir / name
    path.write_text(content, encoding="utf-8")
    return path


# -----------------------------
# HTML snapshot helpers
# -----------------------------

DEFAULT_LISTING_HTML = """<!doctype html>
<html>
  <head><title>Test Listing</title></head>
  <body><img src="/img.jpg" alt="front"></body>
</html>
"""


def make_html_snapshot(
    tmp_dir: Path,
    *,
    html: str = DEFAULT_LISTING_HTML,
    url: str = "https://example.com/listing/123",
    filename: str = "index.raw.html",
) -> HtmlSnapshot:
    """
    Write `html` to tmp_dir/filename and return a HtmlSnapshot pointing to it.
    Useful for media finders and DOM parsers.
    """
    tmp_dir.mkdir(parents=True, exist_ok=True)
    html_path = tmp_dir / filename
    html_bytes = html.encode("utf-8")
    html_path.write_bytes(html_bytes)

    return HtmlSnapshot(
        url=url,
        fetched_at=datetime.now(timezone.utc),
        status_code=200,
        html_path=html_path,
        tree_path=None,
        bytes_size=len(html_bytes),
        sha256="deadbeef",  # tests don't rely on this; fine to keep static
    )
