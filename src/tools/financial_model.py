# src/tools/financial_model.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from src.schemas.models import (
    FinancialInputs,
    ListingInsights,
    YearBreakdown,
    PurchaseMetrics,
    RefiEvent,
    FinancialForecast,
)
from src.tools.amortization import (
    monthly_payment,  # Note: exposed for completeness; generate_schedule() uses it internally.
    generate_schedule,
    annual_debt_service_and_split,
    balance_after_years,
    remaining_term_years,
)


# ============================
# Internal utilities
# ============================

def _pow_growth(base: float, rate: float, year_index: int) -> float:
    """
    Apply compound growth to a base value using a simple rule:
      Year 1: no growth
      Year N: base * (1 + rate)^(N - 1)

    Args:
        base: Year 1 value.
        rate: Annual growth rate as a fraction (e.g., 0.03 for 3%).
        year_index: 1-based year index.

    Returns:
        The grown value for the requested year.
    """
    if base == 0:
        return 0.0
    if year_index <= 1 or rate == 0.0:
        return base
    return base * ((1.0 + rate) ** (year_index - 1))


def _irr(cash_flows: List[float], tol: float = 1e-6, max_iter: int = 200) -> float:
    """
    Compute IRR for a series of annual cash flows using bisection over NPV(rate) = 0.

    Conventions:
      - cash_flows[0] is the initial equity outlay (negative).
      - Subsequent entries are annual net cash flows to equity (positive or negative).
      - Returns a fraction (e.g., 0.12 for 12%). Returns 0.0 for degenerate cases.

    Args:
        cash_flows: List of yearly cash flows, beginning with initial outlay.
        tol: Convergence tolerance on NPV.
        max_iter: Maximum bisection iterations.

    Returns:
        IRR as a fraction, or 0.0 if not solvable within the bracket.

    Notes:
        - If all cash flows are non-negative, IRR is undefined in practice; returns 0.0.
        - Bisection bracket starts wide to handle extreme cases.
    """
    if not cash_flows or all(abs(x) < 1e-12 for x in cash_flows):
        return 0.0
    if all(cf >= 0 for cf in cash_flows):
        return 0.0

    def npv(rate: float) -> float:
        acc = 0.0
        denom = 1.0
        for t, cf in enumerate(cash_flows):
            if t == 0:
                acc += cf
            else:
                denom *= (1.0 + rate)
                acc += cf / denom
        return acc

    low, high = -0.9999, 10.0
    npv_low = npv(low)
    npv_high = npv(high)

    tries = 0
    while npv_low * npv_high > 0 and tries < 10:
        high *= 2
        npv_high = npv(high)
        tries += 1

    if npv_low * npv_high > 0:
        return 0.0

    for _ in range(max_iter):
        mid = (low + high) / 2.0
        v = npv(mid)
        if abs(v) < tol:
            return mid
        if npv_low * v < 0:
            high = mid
            npv_high = v
        else:
            low = mid
            npv_low = v
    return (low + high) / 2.0


# ============================
# Core engine
# ============================

def run(
    inputs: FinancialInputs,
    insights: Optional[ListingInsights] = None,
    horizon_years: int = 10,
) -> FinancialForecast:
    """
    Build a levered financial forecast with optional refinance over a fixed horizon.

    Pipeline:
      1) Size the loan and compute acquisition cash (equity + closing + upfront reserves).
      2) Generate the full amortization schedule for the original loan (with IO support).
      3) For each year:
         - Annualize income (monthly to annual) and apply rent growth and occupancy/bad-debt.
         - Apply expense growth to each OPEX line; compute NOI.
         - Pull annual debt service, interest, principal from the current schedule.
         - Compute cash flow and DSCR; store the ending balance.
      4) If refi is enabled:
         - Value the property at end of refi year from that year's NOI and cap rate.
         - Size the new loan at LTV, pay off the old balance, record any cash-out.
         - Build a new amortization schedule for the remaining term.
      5) Compute purchase metrics (cap rate, CoC, DSCR) from Year 1.
      6) Build equity cash flows to compute 10-year IRR and Equity Multiple.
      7) Emit warnings (cap floor, spread shortfall, subscale, negative CF years).

    Args:
        inputs: FinancialInputs bundle (financing, opex, income, refi, market, upfront reserves).
        insights: ListingInsights (unused in V1 math; reserved for future OPEX/CapEx adjustments).
        horizon_years: Number of years to model (default 10).

    Returns:
        FinancialForecast with purchase metrics, year-by-year breakdowns, optional refi event,
        10-year IRR, equity multiple, and guardrail warnings.

    Notes:
        - Rates are fractions (e.g., 0.05 for 5%).
        - Income fields are monthly; model annualizes internally.
        - Refinance timing is end of year_to_refi.
        - monthly_payment() is re-exported by amortization and is kept for completeness,
          but this function uses generate_schedule() which calls monthly_payment() internally.
    """
    f = inputs.financing
    o = inputs.opex
    inc = inputs.income
    refi = inputs.refi
    mkt = inputs.market

    # ---- Loan sizing / acquisition cash ----
    equity = f.purchase_price * f.down_payment_rate
    loan_amt = max(0.0, f.purchase_price - equity)
    acquisition_cash = equity + f.closing_costs + inputs.capex_reserve_upfront

    # Debt schedules
    sched_pre = generate_schedule(
        principal=loan_amt,
        annual_rate=f.interest_rate,
        amort_years=f.amort_years,
        io_years=f.io_years,
    )
    sched_post = None  # created only if/when refi happens

    # ---- Per-year pro forma ----
    years: List[YearBreakdown] = []
    warnings: List[str] = []

    def opex_for_year(y: int) -> Tuple[float, dict]:
        """
        Compute grown OPEX for year y and return (total, parts dict).
        Each line item grows by expense_growth using the same rule as income growth.
        """
        growth = o.expense_growth
        parts = {
            "insurance": _pow_growth(o.insurance, growth, y),
            "taxes": _pow_growth(o.taxes, growth, y),
            "utilities": _pow_growth(o.utilities, growth, y),
            "water_sewer": _pow_growth(o.water_sewer, growth, y),
            "property_management": _pow_growth(o.property_management, growth, y),
            "repairs_maintenance": _pow_growth(o.repairs_maintenance, growth, y),
            "trash": _pow_growth(o.trash, growth, y),
            "landscaping": _pow_growth(o.landscaping, growth, y),
            "snow_removal": _pow_growth(o.snow_removal, growth, y),
            "hoa_fees": _pow_growth(o.hoa_fees, growth, y),
            "reserves": _pow_growth(o.reserves, growth, y),
            "other_expenses": _pow_growth(o.other, growth, y),
        }
        total = sum(parts.values())
        return total, parts

    # tiny holders for refi artifacts produced inside the loop (initialized lazily)
    _refi_event_holder: List[Optional[RefiEvent]] = [None]
    _cash_out_holder: List[float] = [0.0]

    for y in range(1, horizon_years + 1):
        # Income (monthly -> annual), with growth applied from Year 2 onward
        rent_mo_y = _pow_growth(inc.rent_month, inc.rent_growth, y)
        other_mo_y = _pow_growth(inc.other_income_month, inc.rent_growth, y)

        gsi = 12.0 * (rent_mo_y * inc.units + other_mo_y)
        goi = gsi * inc.occupancy * inc.bad_debt_factor

        total_opex, opex_break = opex_for_year(y)
        noi = goi - total_opex

        # Debt Service: read from pre- or post-refi schedules
        debt_service = interest_paid = principal_paid = 0.0
        end_balance = 0.0

        if (not refi.do_refi) or (y <= refi.year_to_refi):
            # pre-refi year
            ds, interest, principal = annual_debt_service_and_split(sched_pre, y)
            debt_service, interest_paid, principal_paid = ds, interest, principal
            end_balance = balance_after_years(sched_pre, y)
        else:
            # post-refi years; initialize schedule on first post-refi year
            if sched_post is None:
                # Value at refi based on refi-year NOI and chosen cap rate
                noi_refi = noi_at_year(year=refi.year_to_refi, income=inc, opex=o)
                refi_cap = pick_cap_rate(mkt, default_interest=f.interest_rate)
                if refi.exit_cap_rate is not None:
                    refi_cap = refi.exit_cap_rate
                value_at_refi = (noi_refi / refi_cap) if refi_cap > 0 else 0.0

                payoff = balance_after_years(sched_pre, refi.year_to_refi)
                new_loan = max(0.0, value_at_refi * refi.refi_ltv)
                cash_out = max(0.0, new_loan - payoff)

                # Remaining term: use remaining years from original schedule; fallback to original term if zero
                rem_years = remaining_term_years(sched_pre, refi.year_to_refi)
                rem_years = rem_years if rem_years > 0 else f.amort_years

                sched_post = generate_schedule(
                    principal=new_loan,
                    annual_rate=f.interest_rate,
                    amort_years=rem_years,
                    io_years=0,
                )

                _refi_event_holder[0] = RefiEvent(
                    year=refi.year_to_refi,
                    value=value_at_refi,
                    new_loan=new_loan,
                    payoff=payoff,
                    cash_out=cash_out,
                )
                _cash_out_holder[0] = cash_out

            year_on_new = y - refi.year_to_refi
            ds, interest, principal = annual_debt_service_and_split(sched_post, year_on_new)
            debt_service, interest_paid, principal_paid = ds, interest, principal
            end_balance = balance_after_years(sched_post, year_on_new)

        cash_flow = noi - debt_service
        dscr = (noi / debt_service) if debt_service > 0 else 0.0

        years.append(
            YearBreakdown(
                year=y,
                gsi=gsi,
                goi=goi,
                insurance=opex_break["insurance"],
                taxes=opex_break["taxes"],
                utilities=opex_break["utilities"],
                water_sewer=opex_break["water_sewer"],
                property_management=opex_break["property_management"],
                repairs_maintenance=opex_break["repairs_maintenance"],
                trash=opex_break["trash"],
                landscaping=opex_break["landscaping"],
                snow_removal=opex_break["snow_removal"],
                hoa_fees=opex_break["hoa_fees"],
                reserves=opex_break["reserves"],
                other_expenses=opex_break["other_expenses"],
                total_opex=total_opex,
                noi=noi,
                debt_service=debt_service,
                principal_paid=principal_paid,
                interest_paid=interest_paid,
                cash_flow=cash_flow,
                dscr=dscr,
                ending_balance=end_balance,
                notes=[],
            )
        )

    # ---- Purchase metrics (Year 1) ----
    y1 = years[0]
    cap_rate_purchase = (
        mkt.cap_rate_purchase
        if mkt.cap_rate_purchase is not None
        else ((y1.noi / f.purchase_price) if f.purchase_price > 0 else 0.0)
    )
    annual_debt_service_y1 = y1.debt_service
    coc_y1 = (y1.cash_flow / acquisition_cash) if acquisition_cash > 0 else 0.0
    dscr_y1 = y1.dscr
    spread_vs_rate = cap_rate_purchase - f.interest_rate

    purchase = PurchaseMetrics(
        cap_rate=cap_rate_purchase,
        coc=coc_y1,
        dscr=dscr_y1,
        annual_debt_service=annual_debt_service_y1,
        acquisition_cash=acquisition_cash,
        spread_vs_rate=spread_vs_rate,
    )

    # ---- Refi details (compute if not created in-loop) ----
    refi_event: Optional[RefiEvent] = None
    if refi.do_refi:
        if _refi_event_holder[0] is None:
            noi_refi = noi_at_year(refi.year_to_refi, inc, o)
            refi_cap = pick_cap_rate(mkt, default_interest=f.interest_rate)
            if refi.exit_cap_rate is not None:
                refi_cap = refi.exit_cap_rate
            value_at_refi = (noi_refi / refi_cap) if refi_cap > 0 else 0.0
            payoff = balance_after_years(sched_pre, refi.year_to_refi)
            new_loan = max(0.0, value_at_refi * refi.refi_ltv)
            cash_out = max(0.0, new_loan - payoff)
            refi_event = RefiEvent(
                year=refi.year_to_refi,
                value=value_at_refi,
                new_loan=new_loan,
                payoff=payoff,
                cash_out=cash_out,
            )
            _cash_out_holder[0] = cash_out
        else:
            refi_event = _refi_event_holder[0]

    # ---- IRR & Equity Multiple ----
    irr_10, em_10 = compute_returns(
        years=years,
        acquisition_cash=acquisition_cash,
        market=mkt,
        interest_rate=f.interest_rate,
        refi_year=refi.year_to_refi if refi.do_refi else None,
        cash_out_at_refi=_cash_out_holder[0],
    )

    # ---- Warnings ----
    if mkt.cap_rate_floor is not None and cap_rate_purchase < mkt.cap_rate_floor:
        warnings.append(f"Purchase cap rate {cap_rate_purchase:.3%} below floor {mkt.cap_rate_floor:.3%}.")
    if spread_vs_rate < mkt.cap_rate_spread_target:
        warnings.append(f"Cap-rate spread {spread_vs_rate:.3%} below target {mkt.cap_rate_spread_target:.3%}.")
    if inc.units < 4:
        warnings.append("Subscale risk: fewer than 4 units.")
    if any(y.cash_flow < 0 for y in years):
        warnings.append("Negative cash flow in one or more years.")

    return FinancialForecast(
        purchase=purchase,
        years=years,
        refi=refi_event,
        irr_10yr=irr_10,
        equity_multiple_10yr=em_10,
        warnings=warnings,
    )


# ============================
# Helpers (exposed for testing)
# ============================

def noi_at_year(year: int, income, opex) -> float:
    """
    Compute NOI for a specified year using the same growth rules as the main run() loop.

    Args:
        year: 1-based year index.
        income: IncomeModel instance (monthly rents/other income, growth, occupancy, bad-debt).
        opex: OperatingExpenses instance (annual amounts with expense growth).

    Returns:
        NOI for the requested year.
    """
    rent_mo = _pow_growth(income.rent_month, income.rent_growth, year)
    other_mo = _pow_growth(income.other_income_month, income.rent_growth, year)
    gsi = 12.0 * (rent_mo * income.units + other_mo)
    goi = gsi * income.occupancy * income.bad_debt_factor
    growth = opex.expense_growth
    total_opex = sum(
        _pow_growth(v, growth, year)
        for v in [
            opex.insurance,
            opex.taxes,
            opex.utilities,
            opex.water_sewer,
            opex.property_management,
            opex.repairs_maintenance,
            opex.trash,
            opex.landscaping,
            opex.snow_removal,
            opex.hoa_fees,
            opex.reserves,
            opex.other,
        ]
    )
    return goi - total_opex


def pick_cap_rate(market, default_interest: float) -> float:
    """
    Choose a cap rate when not explicitly provided elsewhere.

    Rule:
      - Prefer market.cap_rate_purchase if provided.
      - Else use a conservative fallback: interest rate + spread target (default 150 bps).

    Args:
        market: MarketAssumptions.
        default_interest: Interest rate used as a base for fallback.

    Returns:
        Cap rate as a fraction.
    """
    if market.cap_rate_purchase is not None:
        return market.cap_rate_purchase
    return max(1e-6, default_interest + (market.cap_rate_spread_target or 0.015))


def compute_returns(
    years: List[YearBreakdown],
    acquisition_cash: float,
    market,
    interest_rate: float,
    refi_year: Optional[int],
    cash_out_at_refi: float,
) -> Tuple[float, float]:
    """
    Build annual levered cash flows and compute 10-year IRR and Equity Multiple.

    Cash flow construction:
      - t0: negative initial equity outlay (acquisition_cash).
      - t1..tN: yearly cash_flow from YearBreakdown.
      - At refi year (if any): add cash_out to that year's cash flow.
      - At final year: add terminal equity = terminal value - ending balance.

    Terminal value rule:
      terminal value = NOI_last_year / terminal_cap
      terminal_cap is chosen via pick_cap_rate() using market assumptions,
      falling back to interest rate + spread target.

    Args:
        years: Year-by-year breakdown (must be non-empty).
        acquisition_cash: Initial equity outlay.
        market: MarketAssumptions for cap rate selection.
        interest_rate: Interest rate used in fallback terminal cap logic.
        refi_year: Year index for refi or None.
        cash_out_at_refi: Cash-out amount realized at refi (0 if none).

    Returns:
        (IRR as fraction, Equity Multiple).
    """
    if not years:
        return 0.0, 0.0

    cfs = [-acquisition_cash]
    for y in years:
        cf = y.cash_flow
        if refi_year is not None and y.year == refi_year and cash_out_at_refi > 0:
            cf += cash_out_at_refi
        cfs.append(cf)

    last = years[-1]
    terminal_cap = pick_cap_rate(market, default_interest=interest_rate)
    terminal_value = (last.noi / terminal_cap) if terminal_cap > 0 else 0.0
    terminal_equity = terminal_value - last.ending_balance
    cfs[-1] += terminal_equity

    total_in = -cfs[0]
    total_out = sum(cf for cf in cfs[1:])
    equity_multiple = (total_out / total_in) if total_in > 0 else 0.0

    irr = _irr(cfs)
    return irr, equity_multiple
