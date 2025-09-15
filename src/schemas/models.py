# src/schemas/models.py
from typing import List, Optional
from pydantic import BaseModel, Field


# =========================
# Core inputs
# =========================

class FinancingTerms(BaseModel):
    """Acquisition and loan parameters. Currency is assumed to be the same across all money fields."""
    purchase_price: float = Field(..., description="Total contract price for the property (currency units).")
    closing_costs: float = Field(0.0, description="One-time buyer costs at closing (title, fees, transfer taxes). Added to initial cash outlay.")
    down_payment_rate: float = Field(..., ge=0, le=1, description="Down payment as a fraction of purchase price (e.g., 0.25 = 25%).")
    interest_rate: float = Field(..., ge=0, le=1, description="Annual interest rate (APR) as a fraction (e.g., 0.043 = 4.3%).")
    amort_years: int = Field(30, description="Amortization term in years for a fully-amortizing schedule (excludes IO period).")
    io_years: int = Field(0, description="Number of initial interest-only years before amortization begins (0 for none).")


class OperatingExpenses(BaseModel):
    """Annual operating expense inputs for Year 1. Growth is applied each year by expense_growth."""
    insurance: float = Field(..., description="Annual property insurance.")
    taxes: float = Field(..., description="Annual property taxes.")
    utilities: float = Field(..., description="Annual utilities paid by owner (electric/gas/common areas if applicable).")
    water_sewer: float = Field(..., description="Annual water and sewer paid by owner.")
    property_management: float = Field(..., description="Annual property management fees (fixed or % of income, entered as currency).")
    repairs_maintenance: float = Field(0.0, description="Annual repairs & maintenance allowance.")
    trash: float = Field(0.0, description="Annual trash/garbage removal.")
    landscaping: float = Field(0.0, description="Annual landscaping/grounds.")
    snow_removal: float = Field(0.0, description="Annual snow removal (if applicable).")
    hoa_fees: float = Field(0.0, description="Annual HOA/condo fees (if applicable).")
    reserves: float = Field(0.0, description="Annual replacement reserves (roof, HVAC, turnover).")
    other: float = Field(0.0, description="Catch-all for any additional recurring OPEX not itemized above.")

    expense_growth: float = Field(0.0, description="Annual growth rate applied to all OPEX line items (e.g., 0.02 = +2%/yr).")


class IncomeModel(BaseModel):
    """Revenue model. Rents and other income are MONTHLY inputs; model annualizes internally."""
    units: int = Field(..., description="Number of rentable units (doors).")
    rent_month: float = Field(..., description="Average monthly rent per occupied unit at Year 1 start.")
    other_income_month: float = Field(0.0, description="Other monthly income (parking, laundry, storage, pet fees).")
    occupancy: float = Field(0.97, ge=0, le=1, description="Economic occupancy fraction (1 - vacancy). 0.97 = 97%.")
    bad_debt_factor: float = Field(0.90, ge=0, le=1, description="Collections effectiveness after bad debt. 0.90 means keep 90% after losses.")
    rent_growth: float = Field(0.03, description="Annual growth rate applied to rent and other monthly income (e.g., 0.03 = +3%/yr).")


class RefinancePlan(BaseModel):
    """Refinance assumptions (optional). If enabled, computes value from NOI and exit cap, then applies refi LTV."""
    do_refi: bool = Field(True, description="Whether to model a refinance event.")
    year_to_refi: int = Field(5, description="Refinance occurs at the END of this year (e.g., 5 = after Year 5 cash flows).")
    refi_ltv: float = Field(0.75, ge=0, le=1, description="Loan-to-Value used at refi to size the new loan.")
    exit_cap_rate: Optional[float] = Field(None, description="Cap rate used to value the asset at refi. If None, falls back to market_cap_rate.")
    market_cap_rate: Optional[float] = Field(None, description="Market cap rate reference. Used if purchase cap not provided or for refi if exit_cap_rate is None.")


class MarketAssumptions(BaseModel):
    """Market / risk guardrails used for purchase metrics and strategist rules."""
    cap_rate_purchase: Optional[float] = Field(None, description="If provided, use this as the purchase cap rate; else compute NOI/P for Year 1.")
    cap_rate_floor: Optional[float] = Field(None, description="Minimum acceptable cap rate; if provided, flag deals below this threshold.")
    cap_rate_spread_target: float = Field(0.015, description="Target spread: cap_rate - interest_rate must be ≥ this value (e.g., 0.015 = 150 bps).")


class FinancialInputs(BaseModel):
    """Top-level input bundle consumed by the financial model tool."""
    financing: FinancingTerms = Field(..., description="Purchase and loan terms.")
    opex: OperatingExpenses = Field(..., description="Year 1 operating expenses with annual growth.")
    income: IncomeModel = Field(..., description="Revenue model (monthly inputs; annualized internally).")
    refi: RefinancePlan = Field(RefinancePlan(), description="Refinance plan. Enabled by default; configurable.")
    market: MarketAssumptions = Field(MarketAssumptions(), description="Market guardrails and cap-rate assumptions.")
    capex_reserve_upfront: float = Field(0.0, description="One-time upfront CapEx/reserves added to initial cash outlay (not recurring OPEX).")


# =========================
# Listing insights (from CV + parser)
# =========================

class ListingInsights(BaseModel):
    """Signals extracted from listing text and photos. Used by Strategist and to adjust OPEX/CapEx if desired."""
    address: Optional[str] = Field(None, description="Human-readable address or short identifier.")
    amenities: List[str] = Field(default_factory=list, description="Recognized amenities (e.g., 'in-unit laundry', 'parking').")
    condition_tags: List[str] = Field(default_factory=list, description="Condition features (e.g., 'renovated kitchen', 'old roof').")
    defects: List[str] = Field(default_factory=list, description="Potential issues (e.g., 'water stain', 'mold', 'foundation crack').")
    notes: List[str] = Field(default_factory=list, description="Free-form additional observations.")


# =========================
# Computed outputs
# =========================

class YearBreakdown(BaseModel):
    """One row per modeled year, after applying rent/expense growth, with detailed OPEX and debt service."""
    year: int = Field(..., description="Year index starting at 1.")
    gsi: float = Field(..., description="Gross Scheduled Income: annualized rent + other income before vacancy/bad debt.")
    goi: float = Field(..., description="Gross Operating Income: GSI after occupancy and bad-debt factors.")

    # Operating expenses (detailed, post-growth for that year)
    insurance: float = Field(..., description="Insurance expense for the year after growth.")
    taxes: float = Field(..., description="Property taxes for the year after growth.")
    utilities: float = Field(..., description="Utilities for the year after growth.")
    water_sewer: float = Field(..., description="Water & sewer for the year after growth.")
    property_management: float = Field(..., description="Property management fees after growth.")
    repairs_maintenance: float = Field(..., description="Repairs & maintenance after growth.")
    trash: float = Field(..., description="Trash/garbage removal after growth.")
    landscaping: float = Field(..., description="Landscaping after growth.")
    snow_removal: float = Field(..., description="Snow removal after growth.")
    hoa_fees: float = Field(..., description="HOA/condo fees after growth.")
    reserves: float = Field(..., description="Replacement reserves after growth.")
    other_expenses: float = Field(..., description="Other recurring OPEX after growth.")
    total_opex: float = Field(..., description="Sum of all OPEX line items above for the year.")

    noi: float = Field(..., description="Net Operating Income: GOI - total OPEX (before debt service).")

    # Debt service
    debt_service: float = Field(..., description="Total annual debt service (interest + principal or IO-only).")
    principal_paid: float = Field(..., description="Principal component of annual debt service.")
    interest_paid: float = Field(..., description="Interest component of annual debt service.")

    # Cash flow and coverage
    cash_flow: float = Field(..., description="Levered cash flow before taxes: NOI - debt_service.")
    dscr: float = Field(..., description="Debt Service Coverage Ratio: NOI / debt_service.")
    ending_balance: float = Field(..., description="Ending loan principal balance after this year's payments.")

    notes: List[str] = Field(default_factory=list, description="Any annotations (IO years, refi year, unusual adjustments).")


class PurchaseMetrics(BaseModel):
    """Point-in-time purchase metrics computed from Year 1 and financing."""
    cap_rate: float = Field(..., description="Purchase cap rate (either provided or computed as NOI_Y1 / purchase_price).")
    coc: float = Field(..., description="Cash-on-Cash return in Year 1: cash_flow_Y1 / acquisition_cash.")
    dscr: float = Field(..., description="Year 1 DSCR: NOI_Y1 / annual_debt_service.")
    annual_debt_service: float = Field(..., description="Annual debt service in Year 1.")
    acquisition_cash: float = Field(..., description="Initial cash outlay: down payment + closing costs + upfront reserves.")
    spread_vs_rate: float = Field(..., description="Cap rate minus interest rate (in fraction terms), used for Cardone-style spread checks.")


class RefiEvent(BaseModel):
    """Details of a refinance event if modeled."""
    year: int = Field(..., description="Year when the refi occurs (end of year timing).")
    value: float = Field(..., description="Implied property value at refi: NOI_refi / exit_cap.")
    new_loan: float = Field(..., description="New loan amount sized by refi LTV.")
    payoff: float = Field(..., description="Outstanding principal balance paid off at refi.")
    cash_out: float = Field(..., description="Cash-out proceeds to equity: max(0, new_loan - payoff).")


class FinancialForecast(BaseModel):
    """Complete financial projection and headline returns."""
    purchase: PurchaseMetrics = Field(..., description="Purchase metrics at close/Year 1.")
    years: List[YearBreakdown] = Field(..., description="Per-year detailed pro forma over the horizon.")
    refi: Optional[RefiEvent] = Field(None, description="Refi details if modeled; None otherwise.")
    irr_10yr: float = Field(..., description="Levered IRR over the 10-year (default) horizon including refi/terminal equity.")
    equity_multiple_10yr: float = Field(..., description="(Total distributions to equity) / (initial equity).")
    warnings: List[str] = Field(default_factory=list, description="Validation/guardrail messages (e.g., spread shortfall, subscale risk).")


# =========================
# Final strategist output
# =========================

class InvestmentThesis(BaseModel):
    """Human-readable decision synthesized by the Chief Strategist."""
    verdict: str = Field(..., description='One of: "BUY", "CONDITIONAL", "PASS".')
    rationale: List[str] = Field(..., description="Bulleted reasons supporting the verdict (market fit, metrics, risks).")
    levers: List[str] = Field(default_factory=list, description='Actions to flip/strengthen the verdict (e.g., "negotiate -$20k", "raise rent 6%").')
