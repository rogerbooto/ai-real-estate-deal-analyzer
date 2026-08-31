# src/core/finance/engine.py
from __future__ import annotations

from dataclasses import dataclass

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

from .amortization import schedule_columns
from .irr import irr

DEFAULT_HORIZON_YEARS = 10
EQUITY_LTV = 0.80


# ----------------------------------------------------------------------------------------------
# PERF (Mission 4, PV.3): validation-free `YearBreakdown` construction.
#
# WHY: the year loop builds one `YearBreakdown` per forecast year. At the portfolio scale this
# engine is now held to (100-year horizon x 432 recourse re-runs = 43,200 rows) pydantic's
# validating `__init__` cost ~3.1 us/row -- ~315 us of a ~1,300 us run, the single largest
# remaining line item after the rent-roll sum. `model_construct()` is NOT the answer: it is
# *slower* here (~5.1 us/row measured), because it re-derives defaults and the fields-set in
# Python. This builds the instance's state directly, which is all `__init__` ultimately does
# once validation has passed.
#
# WHY IT IS SAFE, specifically:
#   * Every value passed in is computed a few lines above by this module out of already-validated
#     `FinancialInputs` floats. There is no external/untrusted input on this path, so validation
#     here can only catch a bug in *this file* -- which the bit-exact golden harness
#     (tests/core/finance/test_golden_forecasts.py, 34 pinned cases) catches far more precisely.
#   * `YearBreakdown` has no validators, no aliases, no computed fields, no private attributes and
#     no custom `__init__`, so a validated instance's state is exactly: `__dict__` = the field
#     values, `__pydantic_fields_set__` = the names passed, and `__pydantic_extra__` /
#     `__pydantic_private__` = None. That equivalence is asserted field-by-field, and on
#     `model_dump()` / `model_dump(mode="json")` / `model_dump_json()` / `==` /
#     `model_dump(exclude_unset=True)`, in tests/core/finance/test_engine_bitexact_refactors.py.
#   * `__pydantic_fields_set__` is a fresh `set` per row (a `.copy()`, not the shared template):
#     pydantic mutates that set on attribute assignment, so sharing one instance across rows would
#     be a real aliasing bug for ~0.16 us/row. Not worth it.
#   * `_YB_FIELDS` is derived from the model itself and cross-checked against the literal key
#     tuple below AT IMPORT TIME, so adding or renaming a `YearBreakdown` field fails loudly on
#     import instead of silently producing a half-built model.
# ----------------------------------------------------------------------------------------------
_YB_FIELDS: tuple[str, ...] = tuple(YearBreakdown.model_fields)
_YB_FIELDS_TEMPLATE: set[str] = set(_YB_FIELDS)
_OBJ_SETATTR = object.__setattr__


def _year_row(
    *,
    year: int,
    gsi: float,
    goi: float,
    insurance: float,
    taxes: float,
    utilities: float,
    water_sewer: float,
    property_management: float,
    repairs_maintenance: float,
    trash: float,
    landscaping: float,
    snow_removal: float,
    hoa_fees: float,
    reserves: float,
    other_expenses: float,
    total_opex: float,
    noi: float,
    debt_service: float,
    principal_paid: float,
    interest_paid: float,
    cash_flow: float,
    dscr: float,
    ending_balance: float,
    cap_rate_applied: float | None,
    est_value: float,
    ltv_pct: float,
    available_equity: float,
    notes: list[str],
) -> YearBreakdown:
    """Build a `YearBreakdown` with every field explicitly supplied, bypassing pydantic validation.

    Equivalent, field-for-field and dump-for-dump, to `YearBreakdown(**kwargs)` -- see the module
    note above for why, and `test_engine_bitexact_refactors.py` for the proof.
    """
    row: YearBreakdown = object.__new__(YearBreakdown)
    _OBJ_SETATTR(
        row,
        "__dict__",
        {
            "year": year,
            "gsi": gsi,
            "goi": goi,
            "insurance": insurance,
            "taxes": taxes,
            "utilities": utilities,
            "water_sewer": water_sewer,
            "property_management": property_management,
            "repairs_maintenance": repairs_maintenance,
            "trash": trash,
            "landscaping": landscaping,
            "snow_removal": snow_removal,
            "hoa_fees": hoa_fees,
            "reserves": reserves,
            "other_expenses": other_expenses,
            "total_opex": total_opex,
            "noi": noi,
            "debt_service": debt_service,
            "principal_paid": principal_paid,
            "interest_paid": interest_paid,
            "cash_flow": cash_flow,
            "dscr": dscr,
            "ending_balance": ending_balance,
            "cap_rate_applied": cap_rate_applied,
            "est_value": est_value,
            "ltv_pct": ltv_pct,
            "available_equity": available_equity,
            "notes": notes,
        },
    )
    _OBJ_SETATTR(row, "__pydantic_fields_set__", _YB_FIELDS_TEMPLATE.copy())
    _OBJ_SETATTR(row, "__pydantic_extra__", None)
    _OBJ_SETATTR(row, "__pydantic_private__", None)
    return row


#: Import-time drift guard for `_year_row`'s literal key list (see the note above).
_YEAR_ROW_KEYS: frozenset[str] = frozenset(_year_row.__kwdefaults__ or {}) | frozenset(
    _year_row.__code__.co_varnames[: _year_row.__code__.co_kwonlyargcount]
)
if _YEAR_ROW_KEYS != frozenset(_YB_FIELDS):
    raise RuntimeError(
        "engine._year_row is out of sync with schemas.YearBreakdown: "
        f"missing={sorted(frozenset(_YB_FIELDS) - _YEAR_ROW_KEYS)} "
        f"extra={sorted(_YEAR_ROW_KEYS - frozenset(_YB_FIELDS))}"
    )


def _annual_income(income: IncomeModel) -> tuple[float, float]:
    """Return (GSI, GOI) on an annual basis from per-unit monthly inputs."""
    gsi_month = sum((u.rent_month or 0.0) + (u.other_income_month or 0.0) for u in income.units)
    gsi = gsi_month * 12.0
    goi = gsi * (income.occupancy or 1.0) * (income.bad_debt_factor or 1.0)
    return gsi, goi


@dataclass(frozen=True)
class PrecomputedIncome:
    """The one O(units) aggregate `run_financial_model` needs, computed once and reused.

    BUILD THE CURVE ONCE, REPRICE MANY TIMES. A recourse analysis re-runs the engine hundreds of
    times over the SAME rent roll, moving only the purchase price, the interest rate, or the OPEX
    line -- none of which touch income. Recomputing the rent-roll aggregate on every one of those
    re-runs is the single most expensive thing the engine does at portfolio scale (~269 us of a
    ~770 us run on a 5,000-unit roll, measured). This is the same idea a rates desk applies when
    it bootstraps a yield curve once and then prices a whole book off it, rather than rebuilding
    the curve per bond.

    BIT-EXACTNESS IS BY CONSTRUCTION, NOT BY ARGUMENT. There is no alternative formula here and no
    re-derivation: `precompute_income` calls the very same `_annual_income` the engine would have
    called, and the engine then uses the resulting floats directly. The reused value is not
    "equal to" what the engine would have computed -- it is literally the same `float` object.

    MISUSE IS MADE IMPOSSIBLE, NOT MERELY DISCOURAGED. `income` holds a reference to the exact
    `IncomeModel` these figures were derived from, and `run_financial_model` refuses (raises) if
    that is not the identical object it is about to model. A stale or mismatched precompute is a
    silently-wrong dollar figure -- far worse than a slow one -- so it is a hard error, not a
    quiet fallback. Note that this also correctly rejects the one legitimate mismatch: insight
    income uplifts (`income_is_estimated=True` + amenity tags) build a NEW `IncomeModel` inside
    the engine, so a precompute must not be supplied alongside them.
    """

    income: IncomeModel
    gsi_annual: float
    goi_annual: float


def precompute_income(income: IncomeModel) -> PrecomputedIncome:
    """Compute the reusable income aggregate for `income`. See `PrecomputedIncome`."""
    gsi, goi = _annual_income(income)
    return PrecomputedIncome(income=income, gsi_annual=gsi, goi_annual=goi)


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


@dataclass(frozen=True)
class ForecastMetrics:
    """The scalars every underwriting guardrail is tested against -- and nothing else.

    Deliberately a small, closed, frozen record rather than "a forecast without the rows": it is
    the explicit contract between the engine's light search path (`forecast_metrics`) and the
    guardrail layer (`src.agents.chief_strategist.guardrail_checks`), so what the search path
    must produce is a list you can read, not a shape you have to infer.

    `warnings` is carried verbatim (as a tuple) rather than pre-digested into booleans because the
    cap-rate-floor guardrail is defined by the engine's own warning STRING -- see the cap-floor
    comment block in `synthesize_thesis`: "the breach/clear decision always comes from the
    engine's warning, never from a comparison re-done here". Reducing it here would be re-doing
    exactly the comparison that ruling forbids.
    """

    cap_rate: float
    coc: float
    #: `PurchaseMetrics.dscr` and `years[0].dscr` are carried SEPARATELY, on purpose. The engine
    #: sets them from the same float, but the two consumers historically read different fields --
    #: `guardrail_checks` tests `years[0].dscr`, `recourse._metric` reports `purchase.dscr` -- and
    #: a hand-built `FinancialForecast` (there are some in the test suite) can have them differ.
    #: Collapsing them here would silently change behaviour for those. Keeping both makes
    #: `metrics_of` a faithful projection of any forecast, not just one this engine produced.
    purchase_dscr: float
    year1_dscr: float
    spread_vs_rate: float
    irr_10yr: float
    cash_flow_y1: float
    min_cash_flow: float
    all_cash_flows_nonneg: bool
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class _Core:
    """Internal result of `_forecast_core`, before it is shaped for either public entry point.

    `rows` is empty when the caller asked for the light path; `year_cash_flows` is always
    populated, because every path needs it (IRR, the `cf_all` guardrail, the negative-cash-flow
    warning).
    """

    cap_rate: float
    coc: float
    dscr_y1: float
    annual_debt_service: float
    acquisition_cash: float
    spread_vs_rate: float
    rows: list[YearBreakdown]
    year_cash_flows: list[float]
    refi_event: RefiEvent | None
    irr_10yr: float
    equity_multiple_10yr: float
    warnings: list[str]


def _forecast_core(
    fi: FinancialInputs,
    *,
    horizon_years: int,
    insights: ListingInsights | None,
    precomputed_income: PrecomputedIncome | None,
    want_rows: bool,
) -> _Core:
    """THE forecast. Every dollar figure this product ships is computed here, exactly once.

    `want_rows` is the ONLY behavioural difference between the full path (`run_financial_model`,
    which needs the hundred `YearBreakdown` objects for the report) and the light path
    (`forecast_metrics`, which needs seven scalars for a guardrail test and would otherwise build
    and immediately discard 43,200 of them across a recourse analysis). It gates ONE statement --
    the `years.append(...)` at the bottom of the year loop. It gates no arithmetic whatsoever.

    That is deliberate and it is the whole safety argument. The alternative -- a second,
    "simplified" metrics implementation -- is exactly the drift risk the Gate D ruling on
    `guardrail_checks` was written about: two functions computing the same money number that agree
    today and quietly stop agreeing in eighteen months. Here there is nothing to drift, because
    there is only one implementation; `tests/core/finance/test_metrics_parity.py` pins that
    property bit-for-bit across the full golden matrix so a future fork fails loudly.
    """
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

    # Debt schedule (annual cadence; IO first, then amortization), padded to horizon.
    # Column-oriented (`schedule_columns`) rather than a list of `YearDebt` objects: this loop
    # only ever reads four floats per year, and wrapping each year in a frozen dataclass purely
    # to unwrap it again was ~53 us per run at portfolio scale. Same function, same arithmetic --
    # `amortization_schedule` is now a thin wrapper over this same call.
    sched = schedule_columns(
        loan0,
        rate=f.interest_rate,
        amort_years=f.amort_years,
        io_years=f.io_years,
        horizon_years=horizon_years,
    )
    sched_payment, sched_principal, sched_interest, sched_balance = sched

    # Year 1 income & purchase cap (using adjusted income/opex).
    #
    # PERF (Mission 4, PV.3): this single O(units) pass over the rent roll is the ONLY one in the
    # function. It used to be computed twice -- once here via `_annual_income` and again below as
    # the year-loop's hoisted `gsi_base` -- over the identical expression, for the identical
    # result. On a 5,000-unit rent roll that duplicate pass cost ~266 us, ~20% of the whole run.
    # `gsi_base` is now this same `gsi_y1` value reused, so the numbers are not merely equal, they
    # are the same float object: bit-exactness here is by construction, not by argument.
    if precomputed_income is None:
        gsi_y1, goi_y1 = _annual_income(inc_adj)
    elif precomputed_income.income is inc_adj:
        gsi_y1, goi_y1 = precomputed_income.gsi_annual, precomputed_income.goi_annual
    else:
        raise ValueError(
            "precomputed_income was derived from a different IncomeModel than the one being "
            "modelled. Rebuild it with precompute_income(fi.income) for this exact input, or "
            "pass precomputed_income=None. (If insights are applying income uplifts, the engine "
            "builds a new IncomeModel internally and a precompute cannot be used at all.)"
        )
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

    annual_debt_service = sched_payment[0] if sched_payment else 0.0

    years: list[YearBreakdown] = []
    # Always collected (plain floats, ~8 bytes each): the IRR cash-flow vector, the `cf_all`
    # guardrail and the "negative cash flow in projection" warning all need every year's cash
    # flow, on BOTH paths. What the light path skips is the `YearBreakdown` objects, not the math.
    year_cash_flows: list[float] = []
    # The three values the tail of this function used to read back off `years[0]` / `years[-1]`.
    # Tracked as the loop goes so the tail never has to index a list of objects that the light
    # path does not build.
    dscr_y1 = 0.0
    term_est_value = 0.0
    term_ending_balance = 0.0
    cap_base = cap_rate_purchase
    refi_event: RefiEvent | None = None

    # Loop-invariant: the rent roll does not change across forecast years, only the growth factor
    # does. Summing it inside the year loop made income projection O(units x years); hoisting it
    # makes it O(units + years). Multiplication order is preserved exactly, so results are
    # bit-identical to the per-year form (pinned by the finance-engine golden fixtures).
    # It is now also the SAME value already computed for Year 1 above -- see the note there.
    gsi_base = gsi_y1

    # ------------------------------------------------------------------------------------------
    # PERF (Mission 4, PV.3) -- loop-invariant hoisting. Everything below is read once here
    # instead of once per year (x100 years x 432 recourse re-runs). Every hoisted name holds the
    # SAME expression the loop body used to evaluate inline, so the arithmetic the loop performs
    # is unchanged operation-for-operation:
    #   * `_rent_base` / `_exp_base` are the `(1 + rate)` bases, previously rebuilt 1x and 12x
    #     per year respectively (`_grow` recomputed `(1.0 + rate) ** e` for all 12 OPEX lines).
    #     They are now raised to the year exponent ONCE per year and the 12 lines share that one
    #     factor: `v * factor` is the identical multiply `_grow` did, so this is bit-exact.
    #   * the 12 OPEX base amounts and the income/market scalars are plain attribute reads.
    # ------------------------------------------------------------------------------------------
    _rent_base = 1 + (inc_adj.rent_growth or 0.0)
    _exp_base = 1.0 + (o_adj.expense_growth or 0.0)
    _occ = inc_adj.occupancy or 1.0
    _bdf = inc_adj.bad_debt_factor or 1.0
    _drift = mkt.cap_rate_drift or 0.0
    _insurance0 = o_adj.insurance
    _taxes0 = o_adj.taxes
    _utilities0 = o_adj.utilities
    _water_sewer0 = o_adj.water_sewer
    _pm0 = o_adj.property_management
    _rnm0 = o_adj.repairs_maintenance
    _trash0 = o_adj.trash
    _landscaping0 = o_adj.landscaping
    _snow0 = o_adj.snow_removal
    _hoa0 = o_adj.hoa_fees
    _reserves0 = o_adj.reserves
    _other0 = o_adj.other

    for y in range(1, horizon_years + 1):
        e = y - 1

        # Income growth (adjusted)
        gsi = gsi_base * (_rent_base**e)
        goi = gsi * _occ * _bdf

        # OPEX growth (per-line, uniform rate). One `**` per year, twelve multiplies -- formerly
        # twelve `**` per year via `_grow`. `v * xg` is `_grow`'s own multiply, unchanged.
        xg = _exp_base**e
        insurance = _insurance0 * xg
        taxes = _taxes0 * xg
        utilities = _utilities0 * xg
        water_sewer = _water_sewer0 * xg
        pm = _pm0 * xg
        rnm = _rnm0 * xg
        trash = _trash0 * xg
        landscaping = _landscaping0 * xg
        snow = _snow0 * xg
        hoa = _hoa0 * xg
        reserves = _reserves0 * xg
        other = _other0 * xg

        # Unrolled `sum([...])`. CPython's `sum` seeds with int 0 and switches to a float
        # accumulator on the first float, i.e. it computes exactly `0.0 + a + b + ...` in list
        # order -- so this chain is the same additions in the same order, with no list to build.
        # Verified empirically over 214,641 twelve-term vectors (uniform randoms across the full
        # exponent range plus signed zeros, infinities and subnormals): zero mismatches, signed
        # zero included. See tests/core/finance/test_engine_bitexact_refactors.py.
        total_opex = 0.0 + insurance + taxes + utilities + water_sewer + pm + rnm + trash + landscaping + snow + hoa + reserves + other

        noi = goi - total_opex

        # Cap-rate path
        cap_applied = cap_base + _drift * e
        est_value = (noi / cap_applied) if cap_applied and noi >= 0 else 0.0

        # Debt service from schedule
        ds = sched_payment[e]
        principal = sched_principal[e]
        interest = sched_interest[e]
        ending_bal = sched_balance[e]

        cash_flow = noi - ds
        dscr = (noi / ds) if ds > 0 else 0.0
        ltv_pct = (ending_bal / est_value * 100.0) if est_value > 0 else 0.0
        available_equity = max(0.0, EQUITY_LTV * est_value - ending_bal)

        year_cash_flows.append(cash_flow)
        if y == 1:
            dscr_y1 = dscr
        term_est_value = est_value
        term_ending_balance = ending_bal

        if want_rows:
            # Build notes (first year includes insight notes for traceability)
            year_notes: list[str] = []
            if y == 1 and insight_notes:
                year_notes.extend(insight_notes)

            years.append(
                _year_row(
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
                new_sched = schedule_columns(
                    new_loan,
                    rate=f.interest_rate,
                    amort_years=f.amort_years,
                    io_years=0,
                    horizon_years=remaining_years,
                )
                # splice old prefix + new loan schedule (column-wise; same rows, same order)
                sched_payment = sched_payment[:y] + new_sched.payment
                sched_principal = sched_principal[:y] + new_sched.principal
                sched_interest = sched_interest[:y] + new_sched.interest
                sched_balance = sched_balance[:y] + new_sched.ending_balance

    # Fill purchase metrics using Y1
    coc = 0.0
    if year_cash_flows:
        coc = (year_cash_flows[0] / acquisition_cash) if acquisition_cash > 0 else 0.0

    # Equity cash flows for IRR: initial equity negative, annual CF,
    # add refi cash-out in the refi year and terminal equity proxy in the final year.
    cashflows = [-acquisition_cash]
    refi_year = refi_event.year if refi_event else 0
    for idx, cf in enumerate(year_cash_flows, start=1):
        if refi_event and idx == refi_year:
            cf += refi_event.cash_out
        cashflows.append(cf)

    # Terminal equity at final year: 80% LTV value minus ending balance (proxy for sale proceeds
    # to equity). A zero-year horizon used to reach `years[-1]` on an empty list; that IndexError
    # is preserved deliberately rather than quietly given new behaviour by this refactor.
    if not year_cash_flows:
        raise IndexError("list index out of range")
    terminal_equity = max(0.0, EQUITY_LTV * term_est_value - term_ending_balance)
    cashflows[-1] += terminal_equity

    irr_raw = irr(cashflows)
    irr_10yr_val = irr_raw or 0.0  # <- coalesce None to 0.0
    equity_multiple_10yr = (sum(cf for cf in cashflows[1:]) / (-cashflows[0])) if cashflows[0] < 0 else 0.0

    # Warnings
    warnings: list[str] = []
    if spread_vs_rate < (mkt.cap_rate_spread_target or 0.0):
        warnings.append("cap-rate spread below target")
    if year_cash_flows and any(cf < 0 for cf in year_cash_flows):
        warnings.append("negative cash flow in projection")
    # Cap-rate floor policy: purchase cap rate = NOI(Y1) / purchase price (or the
    # explicit `market.cap_rate_purchase` override). A floor of None means "no floor
    # policy configured" and is never a breach; a breach is strictly below the floor.
    if mkt.cap_rate_floor is not None and cap_rate_purchase < mkt.cap_rate_floor:
        warnings.append("cap rate below floor")
    # `irr()` returns None -- not a valid discount rate -- when no single rate solves
    # NPV = 0 within its domain-bounded search (e.g. cash flows with multiple sign changes,
    # or cash flows that never cross zero at all, as in `units_1_horizon_10` in the golden
    # matrix). `irr_10yr_val` above coalesces that to 0.0 so every downstream consumer (schema,
    # guardrails, report) keeps a plain float -- deliberately NOT made Optional (Mission 4,
    # Gate V ruling; making `irr_10yr` optional through the schema/thesis/report was explicitly
    # ruled out). That coalescing must not be silent: 0.0 looks like a computed 0% return, not
    # "undefined", and a guardrail reading it cannot tell the difference on its own. Surfacing
    # it here, in the same `warnings` list the report already renders, makes the substitution
    # visible without changing what the guardrail decides -- it still sees 0.0 and still fails
    # on it, which is the conservative direction. Fires for EVERY shape of undefined IRR, not
    # just the two-sign-change classic: narrowing this to one shape and not another would
    # recreate exactly the inconsistency the ruling closes.
    if irr_raw is None:
        warnings.append(
            "IRR undefined: no single discount rate solves NPV=0 within the search domain; " "treated as 0.00% for guardrail purposes."
        )

    return _Core(
        cap_rate=cap_rate_purchase,
        coc=coc,
        dscr_y1=dscr_y1,
        annual_debt_service=annual_debt_service,
        acquisition_cash=acquisition_cash,
        spread_vs_rate=spread_vs_rate,
        rows=years,
        year_cash_flows=year_cash_flows,
        refi_event=refi_event,
        irr_10yr=irr_10yr_val,
        equity_multiple_10yr=equity_multiple_10yr,
        warnings=warnings,
    )


def run_financial_model(
    fi: FinancialInputs,
    *,
    horizon_years: int = DEFAULT_HORIZON_YEARS,
    insights: ListingInsights | None = None,
    precomputed_income: PrecomputedIncome | None = None,
) -> FinancialForecast:
    """Run the deterministic forecast for `fi` and return the full, report-ready projection.

    `precomputed_income` is a purely additive performance hint (default `None` => the function
    behaves exactly as it always has, computing everything itself). Pass one -- built by
    `precompute_income()` from the SAME `IncomeModel` object -- when re-running the engine many
    times over an unchanged rent roll; see `PrecomputedIncome`. It is validated by object
    identity and raises on a mismatch rather than silently falling back.
    """
    core = _forecast_core(fi, horizon_years=horizon_years, insights=insights, precomputed_income=precomputed_income, want_rows=True)
    return FinancialForecast(
        purchase=PurchaseMetrics(
            cap_rate=core.cap_rate,
            coc=core.coc,
            dscr=core.dscr_y1,
            annual_debt_service=core.annual_debt_service,
            acquisition_cash=core.acquisition_cash,
            spread_vs_rate=core.spread_vs_rate,
        ),
        years=core.rows,
        refi=core.refi_event,
        irr_10yr=core.irr_10yr,  # <- use the coalesced value
        equity_multiple_10yr=core.equity_multiple_10yr,
        warnings=core.warnings,
    )


def forecast_metrics(
    fi: FinancialInputs,
    *,
    horizon_years: int = DEFAULT_HORIZON_YEARS,
    insights: ListingInsights | None = None,
    precomputed_income: PrecomputedIncome | None = None,
) -> ForecastMetrics:
    """The SEARCH path: the same forecast, returning only the numbers a guardrail test reads.

    A LIGHT PATH FOR SEARCH, THE FULL PATH FOR THE REPORT. A recourse analysis re-runs the engine
    hundreds of times and reads about seven scalars off each result -- then throws away a hundred
    fully-populated `YearBreakdown` objects it never looked at. Materialising those objects is not
    a rounding error in the cost, it IS the cost: measured at ~1.9 us each, 100 per run, they are
    the largest single line item in a portfolio-scale re-run once the rent-roll sum is hoisted.
    This entry point runs the identical `_forecast_core` with `want_rows=False` and builds none of
    them.

    It is NOT a simplified model and NOT an approximation: it is the same function, the same
    arithmetic, the same order of operations, differing only in whether the per-year rows are
    materialised. `metrics_of(run_financial_model(...)) == forecast_metrics(...)` holds
    bit-for-bit and is pinned as such (`tests/core/finance/test_metrics_parity.py`).

    Use it to SEARCH. Do not use it to REPORT: any number shown to an investor should come from
    `run_financial_model`, so that what is displayed and what was tested came off the same object.
    """
    core = _forecast_core(fi, horizon_years=horizon_years, insights=insights, precomputed_income=precomputed_income, want_rows=False)
    cash_flows = core.year_cash_flows
    return ForecastMetrics(
        cap_rate=core.cap_rate,
        coc=core.coc,
        purchase_dscr=core.dscr_y1,
        year1_dscr=core.dscr_y1,
        spread_vs_rate=core.spread_vs_rate,
        irr_10yr=core.irr_10yr,
        cash_flow_y1=cash_flows[0],
        min_cash_flow=min(cash_flows),
        all_cash_flows_nonneg=all(cf >= 0.0 for cf in cash_flows),
        warnings=tuple(core.warnings),
    )


def metrics_of(forecast: FinancialForecast) -> ForecastMetrics:
    """Read the same `ForecastMetrics` off an already-computed full `FinancialForecast`.

    The bridge that makes the two paths comparable -- and testable -- rather than merely similar.
    Every field is a plain read or the identical reduction `forecast_metrics` performs over the
    same values, so the two agree bit-for-bit (pinned by `test_metrics_parity.py`).
    """
    years = forecast.years
    return ForecastMetrics(
        cap_rate=forecast.purchase.cap_rate,
        coc=forecast.purchase.coc,
        purchase_dscr=forecast.purchase.dscr,
        year1_dscr=years[0].dscr,
        spread_vs_rate=forecast.purchase.spread_vs_rate,
        irr_10yr=forecast.irr_10yr,
        cash_flow_y1=years[0].cash_flow,
        min_cash_flow=min(y.cash_flow for y in years),
        all_cash_flows_nonneg=all(y.cash_flow >= 0.0 for y in years),
        warnings=tuple(forecast.warnings),
    )
