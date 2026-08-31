"""
Golden-number regression matrix for ``run_financial_model`` (Mission 4, task PV.1).

WHY THIS FILE EXISTS
---------------------
The founder has authorized vectorising ``src/core/finance/engine.py`` for performance at
portfolio scale. Every dollar figure this product ships comes out of that one function. This
module is the *single source of truth* for the input matrix used to pin its current, bit-exact
output before anyone touches it. Both the regeneration script
(``tests/core/finance/generate_golden_forecasts.py``) and the regression test
(``tests/core/finance/test_golden_forecasts.py``) import ``CASES`` from here — there is
deliberately no second copy of the matrix anywhere, so the goldens and the test that checks them
can never silently drift apart.

Each case is a fully self-contained, JSON-shaped dict (the same shape ``FinancialInputs`` accepts
via ``model_validate``). Cases are written as literal values here — NOT built from
``tests/utils.py`` factories — on purpose: if a shared test factory's defaults ever change, that
must NOT silently reshape what this harness pins. The one exception is the real committed sample
deal, which is loaded from its own file (``data/sample_listings/36_kelly_moncton/inputs.json``)
because pinning *that exact file* is the point.

Coverage (see the mission brief for the full rationale):
  - unit counts:            1, 2, 12, 50, 500
  - horizons:                1, 5, 10, 30, 50
  - interest rates:          0.0 (edge), 0.055 (typical), 0.18 (high)
  - down payment rate:       both sides of the 0.20 MIP trigger (engine.py:107)
  - io_years:                0 and non-zero
  - amort_years:             30 (typical), 15 (short), 0 (interest-only / all-cash)
  - opex shapes:             full (all line items) and sparse (many zeros, like the sample deal)
  - vacancy / bad debt:      baseline and stressed
  - refi:                    present and absent, default exit cap and explicit override
  - market.cap_rate_purchase: set and unset
  - warnings:                cap-rate floor breach, spread-below-target, negative cash flow
  - insight modifiers:       income_is_estimated + condition/defect/amenity tags
  - negative cash flow / negative CoC (DECLINE-shaped deal), incl. the real sample deal

Regenerating goldens is a reviewed decision, not routine maintenance — see the banner in
``generate_golden_forecasts.py`` and ``tests/data/golden/finance_engine_forecasts.json``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_SAMPLE_DEAL_PATH = Path(__file__).resolve().parents[3] / "data" / "sample_listings" / "36_kelly_moncton" / "inputs.json"


def _units(n: int, rent: float = 1200.0, other: float = 50.0, *, vary: bool = True) -> list[dict[str, float]]:
    """
    Build a deterministic, non-random per-unit rent roll of length n.

    When ``vary`` is True, rents cycle through a small fixed pattern so multi-unit cases are not
    all-identical (a real rewrite bug — e.g. summing only unit 0 n times — must be catchable).
    """
    out = []
    for i in range(n):
        r = rent + (10.0 * (i % 3)) if vary else rent
        o = other if (i % 2 == 0) else 0.0
        out.append({"rent_month": r, "other_income_month": o})
    return out


def _financing(
    *,
    purchase_price: float = 500_000.0,
    closing_costs: float = 10_000.0,
    down_payment_rate: float = 0.20,
    interest_rate: float = 0.055,
    amort_years: int = 30,
    io_years: int = 0,
    mortgage_insurance_rate: float = 0.04,
) -> dict[str, Any]:
    return {
        "purchase_price": purchase_price,
        "closing_costs": closing_costs,
        "down_payment_rate": down_payment_rate,
        "interest_rate": interest_rate,
        "amort_years": amort_years,
        "io_years": io_years,
        "mortgage_insurance_rate": mortgage_insurance_rate,
    }


def _opex_full(*, expense_growth: float = 0.02) -> dict[str, Any]:
    return {
        "insurance": 2400.0,
        "taxes": 6000.0,
        "utilities": 3600.0,
        "water_sewer": 1800.0,
        "property_management": 4800.0,
        "repairs_maintenance": 2400.0,
        "trash": 1200.0,
        "landscaping": 800.0,
        "snow_removal": 600.0,
        "hoa_fees": 250.0,
        "reserves": 1500.0,
        "other": 500.0,
        "expense_growth": expense_growth,
    }


def _opex_sparse(*, expense_growth: float = 0.02) -> dict[str, Any]:
    """Mirrors the real sample deal: most OPEX lines legitimately zero."""
    return {
        "insurance": 1026.0,
        "taxes": 4747.0,
        "utilities": 0.0,
        "water_sewer": 920.0,
        "property_management": 0.0,
        "repairs_maintenance": 0.0,
        "trash": 0.0,
        "landscaping": 0.0,
        "snow_removal": 0.0,
        "hoa_fees": 0.0,
        "reserves": 0.0,
        "other": 0.0,
        "expense_growth": expense_growth,
    }


def _income(units: int, *, occupancy: float = 0.95, bad_debt_factor: float = 0.97, rent_growth: float = 0.03) -> dict[str, Any]:
    return {
        "units": _units(units),
        "occupancy": occupancy,
        "bad_debt_factor": bad_debt_factor,
        "rent_growth": rent_growth,
    }


def _refi(
    *,
    do_refi: bool = False,
    year_to_refi: int = 5,
    refi_ltv: float = 0.75,
    exit_cap_rate: float | None = None,
    market_cap_rate: float | None = None,
) -> dict[str, Any]:
    return {
        "do_refi": do_refi,
        "year_to_refi": year_to_refi,
        "refi_ltv": refi_ltv,
        "exit_cap_rate": exit_cap_rate,
        "market_cap_rate": market_cap_rate,
    }


def _market(
    *,
    cap_rate_purchase: float | None = None,
    cap_rate_floor: float | None = 0.05,
    cap_rate_spread_target: float = 0.015,
    cap_rate_drift: float = 0.0,
) -> dict[str, Any]:
    return {
        "cap_rate_purchase": cap_rate_purchase,
        "cap_rate_floor": cap_rate_floor,
        "cap_rate_spread_target": cap_rate_spread_target,
        "cap_rate_drift": cap_rate_drift,
    }


def _case(
    case_id: str,
    description: str,
    *,
    horizon_years: int,
    financing: dict[str, Any],
    opex: dict[str, Any],
    income: dict[str, Any],
    refi: dict[str, Any] | None = None,
    market: dict[str, Any] | None = None,
    capex_reserve_upfront: float = 0.0,
    income_is_estimated: bool = False,
    insights: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": case_id,
        "description": description,
        "horizon_years": horizon_years,
        "insights": insights,
        "financial_inputs": {
            "financing": financing,
            "opex": opex,
            "income": income,
            "refi": refi or _refi(),
            "market": market or _market(),
            "capex_reserve_upfront": capex_reserve_upfront,
            "income_is_estimated": income_is_estimated,
        },
    }


CASES: list[dict[str, Any]] = [
    # --- unit-count sweep (horizon fixed at 10) ---
    _case(
        # NOTE (Mission 4, Gate V review, 2026-08-29): this case's cash flows are negative in
        # EVERY year, including the terminal year -- NPV(r) < 0 for every r > -100%, so no IRR
        # root exists at any rate. `irr()` correctly returns None here; the engine's own warning
        # for that (see engine.py::_forecast_core, "IRR undefined: ...") fires for this case and
        # is pinned in the golden fixture. This is NOT a case that should be "fixed" to have a
        # different shape -- it is the regression test for the undefined-IRR-sentinel bug.
        "units_1_horizon_10",
        "Single unit, baseline horizon.",
        horizon_years=10,
        financing=_financing(),
        opex=_opex_full(),
        income=_income(1),
    ),
    _case(
        "units_2_horizon_10",
        "Two units, baseline horizon.",
        horizon_years=10,
        financing=_financing(),
        opex=_opex_full(),
        income=_income(2),
    ),
    _case(
        "units_12_horizon_10",
        "Twelve units, baseline horizon.",
        horizon_years=10,
        financing=_financing(),
        opex=_opex_full(),
        income=_income(12),
    ),
    _case(
        "units_50_horizon_10",
        "Fifty units, baseline horizon.",
        horizon_years=10,
        financing=_financing(),
        opex=_opex_full(),
        income=_income(50),
    ),
    _case(
        "units_500_horizon_10",
        "Five hundred units (portfolio scale), baseline horizon.",
        horizon_years=10,
        financing=_financing(purchase_price=50_000_000.0, closing_costs=250_000.0),
        opex=_opex_full(),
        income=_income(500),
    ),
    # --- horizon sweep (units fixed at 12) ---
    _case(
        "horizon_1",
        "Minimal one-year horizon (edge; refi year 5 never reached).",
        horizon_years=1,
        financing=_financing(),
        opex=_opex_full(),
        income=_income(12),
    ),
    _case(
        "horizon_5",
        "Five-year horizon, refi lands on the final year.",
        horizon_years=5,
        financing=_financing(),
        opex=_opex_full(),
        income=_income(12),
        refi=_refi(do_refi=True, year_to_refi=5),
    ),
    _case(
        "horizon_30",
        "Thirty-year horizon (amort term reached mid-projection).",
        horizon_years=30,
        financing=_financing(),
        opex=_opex_full(),
        income=_income(12),
    ),
    _case(
        "horizon_50",
        "Fifty-year horizon (well past amort and refi).",
        horizon_years=50,
        financing=_financing(),
        opex=_opex_full(),
        income=_income(12),
    ),
    _case(
        "units_500_horizon_50",
        "Portfolio-scale unit count over a fifty-year horizon.",
        horizon_years=50,
        financing=_financing(purchase_price=50_000_000.0, closing_costs=250_000.0),
        opex=_opex_full(),
        income=_income(500),
    ),
    # --- interest rate edges ---
    _case(
        "interest_rate_zero",
        "Zero interest rate (amortization_payment's rate<=0 branch: principal/years).",
        horizon_years=10,
        financing=_financing(interest_rate=0.0),
        opex=_opex_full(),
        income=_income(4),
    ),
    _case(
        "interest_rate_high",
        "High interest rate (18%).",
        horizon_years=10,
        financing=_financing(interest_rate=0.18),
        opex=_opex_full(),
        income=_income(4),
    ),
    # --- down payment rate, both sides of the 0.20 MIP trigger (engine.py:107) ---
    _case(
        "down_payment_below_mip_trigger",
        "5% down: strictly below 0.20, upfront MIP applies.",
        horizon_years=10,
        financing=_financing(down_payment_rate=0.05, mortgage_insurance_rate=0.04),
        opex=_opex_full(),
        income=_income(4),
    ),
    _case(
        "down_payment_at_mip_boundary",
        "Exactly 0.20 down: NOT strictly less than 0.20, so MIP must NOT apply.",
        horizon_years=10,
        financing=_financing(down_payment_rate=0.20, mortgage_insurance_rate=0.04),
        opex=_opex_full(),
        income=_income(4),
    ),
    _case(
        "down_payment_above_mip_trigger",
        "35% down: above the trigger, no MIP.",
        horizon_years=10,
        financing=_financing(down_payment_rate=0.35, mortgage_insurance_rate=0.04),
        opex=_opex_full(),
        income=_income(4),
    ),
    _case(
        "all_cash_deal",
        "100% down, no amortization, no IO: a free-and-clear purchase (ds=0 branch).",
        horizon_years=10,
        financing=_financing(down_payment_rate=1.0, amort_years=0, io_years=0, mortgage_insurance_rate=0.0),
        opex=_opex_full(),
        income=_income(4),
    ),
    # --- io_years ---
    _case(
        "io_years_zero",
        "No interest-only period (plain amortizing schedule from year 1).",
        horizon_years=10,
        financing=_financing(io_years=0, amort_years=30),
        opex=_opex_full(),
        income=_income(4),
    ),
    _case(
        "io_years_nonzero",
        "Five interest-only years before amortization begins.",
        horizon_years=10,
        financing=_financing(io_years=5, amort_years=25),
        opex=_opex_full(),
        income=_income(4),
    ),
    # --- amort_years variations ---
    _case(
        "amort_years_short",
        "Short 15-year amortization term.",
        horizon_years=10,
        financing=_financing(amort_years=15),
        opex=_opex_full(),
        income=_income(4),
    ),
    _case(
        "amort_years_zero_io_only",
        "amort_years=0 with io_years>0: interest-only for the full modeled schedule.",
        horizon_years=10,
        financing=_financing(amort_years=0, io_years=10),
        opex=_opex_full(),
        income=_income(4),
    ),
    # --- opex shapes ---
    _case(
        "opex_sparse_like_sample_deal",
        "Sparse OPEX (many legitimately-zero lines), mirroring the real sample deal shape.",
        horizon_years=10,
        financing=_financing(purchase_price=399_900.0, closing_costs=10_000.0, down_payment_rate=0.05, interest_rate=0.055, amort_years=25),
        opex=_opex_sparse(),
        income=_income(2, occupancy=0.95, bad_debt_factor=0.97),
        market=_market(cap_rate_floor=0.05),
    ),
    # --- vacancy / bad debt stress ---
    _case(
        "vacancy_high",
        "High vacancy (80% occupancy).",
        horizon_years=10,
        financing=_financing(),
        opex=_opex_full(),
        income=_income(4, occupancy=0.80),
    ),
    _case(
        "bad_debt_stress",
        "Elevated bad-debt loss (80% collections effectiveness).",
        horizon_years=10,
        financing=_financing(),
        opex=_opex_full(),
        income=_income(4, bad_debt_factor=0.80),
    ),
    # --- refi present / absent / overridden ---
    _case(
        "refi_absent",
        "No refi modeled.",
        horizon_years=10,
        financing=_financing(),
        opex=_opex_full(),
        income=_income(4),
        refi=_refi(do_refi=False),
    ),
    _case(
        "refi_present_default_exit_cap",
        "Refi at year 5, exit cap falls back to market/purchase cap rate.",
        horizon_years=10,
        financing=_financing(),
        opex=_opex_full(),
        income=_income(4),
        refi=_refi(do_refi=True, year_to_refi=5, refi_ltv=0.75),
    ),
    _case(
        "refi_present_explicit_exit_cap",
        "Refi at year 7 with an explicit exit cap rate override.",
        horizon_years=10,
        financing=_financing(),
        opex=_opex_full(),
        income=_income(4),
        refi=_refi(do_refi=True, year_to_refi=7, refi_ltv=0.70, exit_cap_rate=0.06),
    ),
    # --- market.cap_rate_purchase set / unset ---
    _case(
        "cap_rate_purchase_unset",
        "market.cap_rate_purchase is None: engine computes NOI_Y1 / purchase_price.",
        horizon_years=10,
        financing=_financing(),
        opex=_opex_full(),
        income=_income(4),
        market=_market(cap_rate_purchase=None),
    ),
    _case(
        "cap_rate_purchase_set_explicit",
        "market.cap_rate_purchase explicitly overridden.",
        horizon_years=10,
        financing=_financing(),
        opex=_opex_full(),
        income=_income(4),
        market=_market(cap_rate_purchase=0.07),
    ),
    _case(
        "cap_rate_drift_nonzero",
        "Cap rate drifts +25 bps/year, affecting est_value/LTV in later years.",
        horizon_years=10,
        financing=_financing(),
        opex=_opex_full(),
        income=_income(4),
        market=_market(cap_rate_drift=0.0025),
    ),
    # --- warnings coverage ---
    _case(
        "cap_rate_floor_breach",
        "Cap rate floor set above the achievable cap rate: 'cap rate below floor' warning.",
        horizon_years=10,
        financing=_financing(),
        opex=_opex_full(),
        income=_income(4),
        market=_market(cap_rate_floor=0.20),
    ),
    _case(
        "spread_below_target",
        "Spread target set unreachable: 'cap-rate spread below target' warning.",
        horizon_years=10,
        financing=_financing(),
        opex=_opex_full(),
        income=_income(4),
        market=_market(cap_rate_spread_target=0.50),
    ),
    _case(
        "negative_cash_flow_decline_shaped",
        "Thin, highly-levered deal producing negative Y1 cash flow (DECLINE-shaped), synthetic "
        "analogue of the real sample deal at a different unit count.",
        horizon_years=10,
        financing=_financing(
            purchase_price=399_900.0 * 6, closing_costs=10_000.0 * 6, down_payment_rate=0.05, interest_rate=0.055, amort_years=25
        ),
        opex=_opex_sparse(expense_growth=0.02),
        income=_income(12, occupancy=0.95, bad_debt_factor=0.97),
        market=_market(cap_rate_floor=0.05),
    ),
    # --- insight modifiers (OPEX bumps + allowed income uplift) ---
    _case(
        "insight_modifiers_applied",
        "income_is_estimated=True with listing insights: OPEX bumps (old roof, water stain) and "
        "an allowed income uplift (in-unit laundry, parking) all apply and must be pinned too.",
        horizon_years=10,
        financing=_financing(),
        opex=_opex_full(),
        income=_income(4),
        income_is_estimated=True,
        insights={
            "address": "123 Test St",
            "amenities": ["in-unit laundry", "parking"],
            "condition_tags": ["old roof"],
            "defects": ["water stain"],
        },
    ),
]


def _sample_deal_case() -> dict[str, Any]:
    """
    The real committed sample deal (data/sample_listings/36_kelly_moncton/inputs.json).

    Loaded from disk rather than hardcoded so this case tracks the actual committed file --
    if someone edits that file, this case (and its golden) changes with it, which is the point.
    Note the JSON nests the payload under an "inputs" key.
    """
    raw = json.loads(_SAMPLE_DEAL_PATH.read_text(encoding="utf-8"))
    return {
        "id": "sample_deal_36_kelly_moncton",
        "description": "The real committed sample deal shipped with the product (DECLINE-shaped: "
        "DSCR 0.8960, CoC -6.4066%, Y1 cash flow -$2,946.47, cap rate 6.3454%, spread 0.8454%).",
        "horizon_years": raw["run"]["horizon"],
        "insights": None,
        "financial_inputs": raw["inputs"],
    }


CASES.append(_sample_deal_case())

CASE_IDS: list[str] = [c["id"] for c in CASES]

assert len(CASE_IDS) == len(set(CASE_IDS)), "duplicate golden case id"
