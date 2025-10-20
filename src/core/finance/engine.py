# src/core/finance/engine.py
from __future__ import annotations

from src.schemas.models import (
    FinancialForecast,
    FinancialInputs,
    IncomeModel,
    ListingInsights,
    OperatingExpenses,
    PurchaseMetrics,
    RefiEvent,
    YearBreakdown,
)

from .amortization import amortization_schedule
from .irr import irr

DEFAULT_HORIZON_YEARS = 10
EQUITY_LTV = 0.80


def _annual_income(income: IncomeModel) -> tuple[float, float]:
    """Return (GSI, GOI) on an annual basis from per-unit monthly inputs."""
    gsi_month = sum((u.rent_month or 0.0) + (u.other_income_month or 0.0) for u in income.units)
    gsi = gsi_month * 12.0
    goi = gsi * (income.occupancy or 1.0) * (income.bad_debt_factor or 1.0)
    return gsi, goi


def _grow(val: float, rate: float, years: int) -> float:
    return val * ((1.0 + (rate or 0.0)) ** years)


def _apply_insight_modifiers(
    income: IncomeModel,
    opex: OperatingExpenses,
    insights: ListingInsights | None,
    *,
    allow_income_adjustments: bool = False,
) -> tuple[IncomeModel, OperatingExpenses, list[str]]:
    """
    Deterministic, conservative tweaks from listing insights.

    Rules:
      - Income: **not** modified unless allow_income_adjustments=True.
      - OPEX: conservative bumps with Year 1 notes (carried via `notes`).

    Returns (income', opex', notes)
    """
    if insights is None:
        return income, opex, []

    notes: list[str] = []

    # Start from shallow copies to avoid mutating caller inputs
    inc = income  # unchanged by default
    opx = opex.model_copy(deep=True)

    amens = {a.lower().strip() for a in (insights.amenities or [])}
    conds = {c.lower().strip() for c in (insights.condition_tags or [])}
    defs = {d.lower().strip() for d in (insights.defects or [])}

    # OPEX bumps (conservative; justify with notes)
    if "old roof" in conds:
        opx = opx.model_copy(update={"reserves": (opx.reserves or 0.0) + 300.0})
        notes.append("condition: old roof → reserves +$300/yr")

    if "water stain" in defs:
        opx = opx.model_copy(update={"repairs_maintenance": (opx.repairs_maintenance or 0.0) + 200.0})
        notes.append("defect: water stain → R&M +$200/yr")

    # (Optional) income uplifts are disabled by default to honor investor inputs
    if allow_income_adjustments:
        from copy import deepcopy

        inc = deepcopy(income)
        changed = False
        if "in-unit laundry" in amens:
            for i, u in enumerate(inc.units):
                inc.units[i] = u.model_copy(update={"other_income_month": (u.other_income_month or 0.0) + 25.0})
            notes.append("amenity uplift: in-unit laundry (+$25/mo/unit other income)")
            changed = True
        if "parking" in amens:
            for i, u in enumerate(inc.units):
                inc.units[i] = u.model_copy(update={"other_income_month": (u.other_income_month or 0.0) + 50.0})
            notes.append("amenity uplift: parking (+$50/mo/unit other income)")
            changed = True
        if not changed:
            inc = income  # no-op if nothing applied

    return inc, opx, notes


def run_financial_model(
    fi: FinancialInputs, *, horizon_years: int = DEFAULT_HORIZON_YEARS, insights: ListingInsights | None = None
) -> FinancialForecast:
    # Apply insight-aware adjustments (non-destructive copies)
    inc_adj, o_adj, insight_notes = _apply_insight_modifiers(fi.income, fi.opex, insights, allow_income_adjustments=fi.income_is_estimated)

    f = fi.financing
    mkt = fi.market
    refi = fi.refi

    # Loan sizing
    down = f.purchase_price * f.down_payment_rate
    loan0 = f.purchase_price - down
    upfront_mip = f.purchase_price * (f.mortgage_insurance_rate if f.down_payment_rate < 0.20 else 0.0)
    acquisition_cash = down + f.closing_costs + fi.capex_reserve_upfront + upfront_mip

    # Debt schedule (annual cadence; IO first, then amortization), padded to horizon
    sched = amortization_schedule(
        loan0,
        rate=f.interest_rate,
        amort_years=f.amort_years,
        io_years=f.io_years,
        horizon_years=horizon_years,
    )

    # Year 1 income & purchase cap (using adjusted income/opex)
    _, goi_y1 = _annual_income(inc_adj)
    noi_y1 = goi_y1 - (
        o_adj.insurance
        + o_adj.taxes
        + o_adj.utilities
        + o_adj.water_sewer
        + o_adj.property_management
        + o_adj.repairs_maintenance
        + o_adj.trash
        + o_adj.landscaping
        + o_adj.snow_removal
        + o_adj.hoa_fees
        + o_adj.reserves
        + o_adj.other
    )
    cap_rate_purchase = (
        mkt.cap_rate_purchase if mkt.cap_rate_purchase is not None else (noi_y1 / f.purchase_price if f.purchase_price else 0.0)
    )
    spread_vs_rate = cap_rate_purchase - f.interest_rate

    purchase_metrics = PurchaseMetrics(
        cap_rate=cap_rate_purchase,
        coc=0.0,  # filled after Y1 cash flow
        dscr=0.0,  # filled after Y1
        annual_debt_service=sched[0].payment if sched else 0.0,
        acquisition_cash=acquisition_cash,
        spread_vs_rate=spread_vs_rate,
    )

    years: list[YearBreakdown] = []
    cap_base = cap_rate_purchase
    refi_event: RefiEvent | None = None

    for y in range(1, horizon_years + 1):
        # Income growth (adjusted)
        gsi = (sum((u.rent_month or 0.0) + (u.other_income_month or 0.0) for u in inc_adj.units) * 12.0) * (
            (1 + (inc_adj.rent_growth or 0.0)) ** (y - 1)
        )
        goi = gsi * (inc_adj.occupancy or 1.0) * (inc_adj.bad_debt_factor or 1.0)

        # OPEX growth (per-line, uniform rate) — bind loop var via default arg to avoid B023
        def og(v: float, _y: int = y) -> float:
            return _grow(v, o_adj.expense_growth, _y - 1)

        insurance = og(o_adj.insurance)
        taxes = og(o_adj.taxes)
        utilities = og(o_adj.utilities)
        water_sewer = og(o_adj.water_sewer)
        pm = og(o_adj.property_management)
        rnm = og(o_adj.repairs_maintenance)
        trash = og(o_adj.trash)
        landscaping = og(o_adj.landscaping)
        snow = og(o_adj.snow_removal)
        hoa = og(o_adj.hoa_fees)
        reserves = og(o_adj.reserves)
        other = og(o_adj.other)

        total_opex = sum(
            [
                insurance,
                taxes,
                utilities,
                water_sewer,
                pm,
                rnm,
                trash,
                landscaping,
                snow,
                hoa,
                reserves,
                other,
            ]
        )

        noi = goi - total_opex

        # Cap-rate path
        cap_applied = cap_base + (mkt.cap_rate_drift or 0.0) * (y - 1)
        est_value = (noi / cap_applied) if cap_applied and noi >= 0 else 0.0

        # Debt service from schedule
        sd = sched[y - 1]
        ds = sd.payment
        principal = sd.principal
        interest = sd.interest
        ending_bal = sd.ending_balance

        cash_flow = noi - ds
        dscr = (noi / ds) if ds > 0 else 0.0
        ltv_pct = (ending_bal / est_value * 100.0) if est_value > 0 else 0.0
        available_equity = max(0.0, EQUITY_LTV * est_value - ending_bal)

        # Build notes (first year includes insight notes for traceability)
        year_notes = []
        if y == 1 and insight_notes:
            year_notes.extend(insight_notes)

        years.append(
            YearBreakdown(
                year=y,
                gsi=gsi,
                goi=goi,
                insurance=insurance,
                taxes=taxes,
                utilities=utilities,
                water_sewer=water_sewer,
                property_management=pm,
                repairs_maintenance=rnm,
                trash=trash,
                landscaping=landscaping,
                snow_removal=snow,
                hoa_fees=hoa,
                reserves=reserves,
                other_expenses=other,
                total_opex=total_opex,
                noi=noi,
                debt_service=ds,
                principal_paid=principal,
                interest_paid=interest,
                cash_flow=cash_flow,
                dscr=dscr,
                ending_balance=ending_bal,
                cap_rate_applied=cap_applied,
                est_value=est_value,
                ltv_pct=ltv_pct,
                available_equity=available_equity,
                notes=year_notes,
            )
        )

        # Refi event at end of specified year
        if refi.do_refi and refi_event is None and y == refi.year_to_refi:
            exit_cap = refi.exit_cap_rate or mkt.cap_rate_purchase or cap_rate_purchase
            refi_value = (noi / exit_cap) if exit_cap else 0.0
            new_loan = refi.refi_ltv * refi_value
            payoff = ending_bal
            cash_out = max(0.0, new_loan - payoff)
            refi_event = RefiEvent(year=y, value=refi_value, new_loan=new_loan, payoff=payoff, cash_out=cash_out)

            # Rebuild debt schedule for remaining years (starting next year) with the new loan.
            remaining_years = horizon_years - y
            if remaining_years > 0:
                new_sched = amortization_schedule(
                    new_loan,
                    rate=f.interest_rate,
                    amort_years=f.amort_years,
                    io_years=0,
                    horizon_years=remaining_years,
                )
                # splice old prefix + new loan schedule
                sched = sched[:y] + new_sched

    # Fill purchase metrics using Y1
    if years:
        y1 = years[0]
        purchase_metrics = purchase_metrics.model_copy(
            update={
                "coc": (y1.cash_flow / acquisition_cash) if acquisition_cash > 0 else 0.0,
                "dscr": y1.dscr,
            }
        )

    # Equity cash flows for IRR: initial equity negative, annual CF,
    # add refi cash-out in the refi year and terminal equity proxy in the final year.
    cashflows = [-acquisition_cash]
    for year_row in years:
        cf = year_row.cash_flow
        if refi_event and year_row.year == refi_event.year:
            cf += refi_event.cash_out
        cashflows.append(cf)

    # Terminal equity at final year: 80% LTV value minus ending balance (proxy for sale proceeds to equity)
    term = years[-1]
    terminal_equity = max(0.0, EQUITY_LTV * term.est_value - term.ending_balance)
    cashflows[-1] += terminal_equity

    irr_10yr_val = irr(cashflows) or 0.0  # <- coalesce None to 0.0
    equity_multiple_10yr = (sum(cf for cf in cashflows[1:]) / (-cashflows[0])) if cashflows[0] < 0 else 0.0

    # Warnings
    warnings: list[str] = []
    if purchase_metrics.spread_vs_rate < (mkt.cap_rate_spread_target or 0.0):
        warnings.append("cap-rate spread below target")
    if years and any(r.cash_flow < 0 for r in years):
        warnings.append("negative cash flow in projection")

    return FinancialForecast(
        purchase=purchase_metrics,
        years=years,
        refi=refi_event,
        irr_10yr=irr_10yr_val,  # <- use the coalesced value
        equity_multiple_10yr=equity_multiple_10yr,
        warnings=warnings,
    )
