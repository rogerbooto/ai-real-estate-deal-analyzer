# src/tools/financial_model.py
from __future__ import annotations

from src.schemas.models import (
    FinancialForecast,
    FinancialInputs,
    ListingInsights,
    PurchaseMetrics,
    RefiEvent,
    YearBreakdown,
    IncomeModel,
    OperatingExpenses
)
from src.tools.amortization import (
    annual_debt_service_and_split,
    balance_after_years,
    generate_schedule,
    remaining_term_years,
)

from typing import Any

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


def _irr(cash_flows: list[float], tol: float = 1e-6, max_iter: int = 200) -> float:
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
                denom *= 1.0 + rate
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


# Helpers for valuation tracks / refi heuristics


def _safe_div(n: float, d: float) -> float:
    """Safe division for LTV/value math; returns +inf if denominator is 0 and numerator > 0, else 0."""
    if d == 0:
        return float("inf") if n > 0 else 0.0
    return n / d


def _first_refi_year_at_or_below_80_ltv(ltv_by_year: list[float], seasoning_min_years: int) -> int | None:
    """
    Return the first 1-based year where LTV ≤ 0.80, respecting seasoning_min_years.
    """
    eps = 1e-9
    s = max(1, int(seasoning_min_years or 1))
    for i, ltv in enumerate(ltv_by_year, start=1):
        if i >= s and ltv <= 0.80 + eps:
            return i
    return None


# ============================
# Core engine
# ============================


def run(
    inputs: FinancialInputs,
    insights: ListingInsights | None = None,
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
    down_payment = f.purchase_price * f.down_payment_rate

    # Upfront mortgage insurance (applies if DP < 20%)
    insurance_premium = f.purchase_price * f.mortgage_insurance_rate if f.down_payment_rate < 0.20 else 0.0

    loan_amt = max(0.0, f.purchase_price - down_payment) + insurance_premium

    acquisition_cash = down_payment + f.closing_costs + inputs.capex_reserve_upfront

    if acquisition_cash <= 0.0:
        raise ValueError("Acquisition cash must be positive. Check purchase price, down payment rate, closing costs, and upfront reserves.")

    # Debt schedules
    sched_pre = generate_schedule(
        principal=loan_amt,
        annual_rate=f.interest_rate,
        amort_years=f.amort_years,
        io_years=f.io_years,
    )
    sched_post = None  # created only if/when refi happens

    # ---- Per-year pro forma ----
    years: list[YearBreakdown] = []
    warnings: list[str] = []

    def opex_for_year(y: int) -> tuple[float, dict]:
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
    _refi_event_holder: list[RefiEvent | None] = [None]
    _cash_out_holder: list[float] = [0.0]

    for y in range(1, horizon_years + 1):
        # Income (monthly -> annual), with growth applied from Year 2 onward
        total_rent_mo_y = sum(_pow_growth(u.rent_month, inc.rent_growth, y) for u in inc.units)

        total_other_mo_y = sum(_pow_growth(u.other_income_month, inc.rent_growth, y) for u in inc.units)

        gsi = 12.0 * (total_rent_mo_y + total_other_mo_y)
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

    # Valuation tracks & refi heuristics
    # Pull market knobs with safe defaults to keep this block deterministic
    baseline_appreciation = getattr(mkt, "baseline_appreciation_rate", 0.03) or 0.0
    stress_price_adjustment = getattr(mkt, "stress_price_adjustment", 0.0) or 0.0
    cap_rate_drift_per_year = getattr(mkt, "cap_rate_drift", 0.0) or 0.0
    seasoning_min_years = int(getattr(mkt, "seasoning_min_years", 1) or 1)

    n = len(years)
    purchase_price = f.purchase_price
    interest_rate = f.interest_rate

    # Baseline (appreciation-based) values
    property_value_baseline: list[float] = [purchase_price * ((1.0 + baseline_appreciation) ** (y - 1)) for y in range(1, n + 1)]

    # Stress (rate-anchored) values
    stress_basis = max(0.0, purchase_price - stress_price_adjustment)
    stress_growth = 1.0 + (interest_rate / 3.0) if interest_rate is not None else 1.0
    property_value_stress: list[float] = [stress_basis * (stress_growth ** (y - 1)) for y in range(1, n + 1)]

    # NOI-based values with cap-rate drift
    # Start cap: use purchase cap if present; else back into it via NOI_Y1 / purchase_price
    first_year_noi = years[0].noi if years else 0.0
    cap_rate_start = getattr(mkt, "cap_rate_purchase", None)
    if not cap_rate_start or cap_rate_start <= 0:
        cap_rate_start = (first_year_noi / purchase_price) if purchase_price > 0 else 0.0

    property_value_noi: list[float] = []
    for idx, year in enumerate(years):
        cap_t = cap_rate_start + cap_rate_drift_per_year * idx  # linear drift per year index
        if cap_t <= 0:
            property_value_noi.append(0.0)
        else:
            property_value_noi.append(_safe_div(year.noi, cap_t))

    # LTV and Equity (80% basis) for each track
    end_balances = [year.ending_balance for year in years]

    ltv_baseline = [_safe_div(end_balances[i], max(1e-12, property_value_baseline[i])) for i in range(n)]
    equity_baseline = [max(0.0, 0.80 * property_value_baseline[i] - end_balances[i]) for i in range(n)]

    ltv_stress = [_safe_div(end_balances[i], max(1e-12, property_value_stress[i])) for i in range(n)]
    equity_stress = [max(0.0, 0.80 * property_value_stress[i] - end_balances[i]) for i in range(n)]

    ltv_noi = [_safe_div(end_balances[i], max(1e-12, property_value_noi[i])) for i in range(n)]
    equity_noi = [max(0.0, 0.80 * property_value_noi[i] - end_balances[i]) for i in range(n)]

    # Suggested refi years for each track (first ≤ 80% LTV, after seasoning)
    suggested_refi_year_baseline = _first_refi_year_at_or_below_80_ltv(ltv_baseline, seasoning_min_years)
    suggested_refi_year_stress = _first_refi_year_at_or_below_80_ltv(ltv_stress, seasoning_min_years)
    suggested_refi_year_noi = _first_refi_year_at_or_below_80_ltv(ltv_noi, seasoning_min_years)

    # ---- Purchase metrics (Year 1) ----
    y1 = years[0]
    cap_rate_purchase = (
        mkt.cap_rate_purchase if mkt.cap_rate_purchase is not None else ((y1.noi / f.purchase_price) if f.purchase_price > 0 else 0.0)
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
    refi_event: RefiEvent | None = None
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
    if len(inc.units) < 4:
        warnings.append("Subscale risk: fewer than 4 units.")
    if any(year.cash_flow < 0 for year in years):
        warnings.append("Negative cash flow in one or more years.")

    return FinancialForecast(
        purchase=purchase,
        years=years,
        refi=refi_event,
        irr_10yr=irr_10,
        equity_multiple_10yr=em_10,
        warnings=warnings,
        # valuation tracks & suggested refi years
        property_value_baseline=property_value_baseline,
        ltv_baseline=ltv_baseline,
        equity_baseline=equity_baseline,
        suggested_refi_year_baseline=suggested_refi_year_baseline,
        property_value_stress=property_value_stress,
        ltv_stress=ltv_stress,
        equity_stress=equity_stress,
        suggested_refi_year_stress=suggested_refi_year_stress,
        property_value_noi=property_value_noi,
        ltv_noi=ltv_noi,
        equity_noi=equity_noi,
        suggested_refi_year_noi=suggested_refi_year_noi,
    )


# ============================
# Helpers (exposed for testing)
# ============================


def noi_at_year(year: int, income: IncomeModel, opex: OperatingExpenses) -> float:
    """
    Compute NOI for a specified year using the same growth rules as the main run() loop.

    Args:
        year: 1-based year index.
        income: IncomeModel instance (monthly rents/other income, growth, occupancy, bad-debt).
        opex: OperatingExpenses instance (annual amounts with expense growth).

    Returns:
        NOI for the requested year.
    """
    total_rent_mo = sum(_pow_growth(u.rent_month, income.rent_growth, year) for u in income.units)

    total_other_mo = sum(_pow_growth(u.other_income_month, income.rent_growth, year) for u in income.units)

    gsi = 12.0 * (total_rent_mo + total_other_mo)
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


def pick_cap_rate(market: Any, default_interest: float) -> float:
    """
    Choose a cap rate when not explicitly provided elsewhere.

    Rule:
      - Prefer market.cap_rate_purchase if provided.
      - Else use a conservative fallback: interest rate + spread target (default 150 bps).
    """
    try:
        cap_rate = getattr(market, "cap_rate_purchase", None)
        if cap_rate is not None:
            return float(cap_rate)
    except (TypeError, ValueError):
        # TODO: Log or warn here
        pass

    spread = getattr(market, "cap_rate_spread_target", 0.015) or 0.015
    return max(1e-6, default_interest + float(spread))


def compute_returns(
    years: list[YearBreakdown],
    acquisition_cash: float,
    market: Any,
    interest_rate: float,
    refi_year: int | None,
    cash_out_at_refi: float,
) -> tuple[float, float]:
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
    for year in years:
        cf = year.cash_flow
        if refi_year is not None and year.year == refi_year and cash_out_at_refi > 0:
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
