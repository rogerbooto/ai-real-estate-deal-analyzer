# src/schemas/models.py

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# =========================
# Core inputs
# =========================


class FinancingTerms(BaseModel):
    """
    Acquisition and loan parameters. All money amounts are assumed to use the same currency.
    """

    model_config = ConfigDict(validate_assignment=True)

    purchase_price: float = Field(
        ...,
        gt=0,
        description=(
            "Total contract price for the property (currency units). Must be strictly positive: it is the "
            "denominator of cap_rate, coc and ltv, and the base of the loan, down payment and MIP. Model an "
            "all-cash purchase as down_payment_rate=1.0, never as a zero price."
        ),
    )
    closing_costs: float = Field(
        0.0,
        ge=0,
        description=(
            "One-time buyer costs at closing (title, fees, transfer taxes). Added to initial cash outlay. "
            "Zero is legitimate (seller pays all costs). Model a seller credit as a lower purchase price, "
            "not as negative closing costs -- a negative here would silently change the cap-rate "
            "denominator's meaning."
        ),
    )
    down_payment_rate: float = Field(..., ge=0, le=1, description="Down payment as a fraction of purchase price (e.g., 0.25 = 25%).")
    interest_rate: float = Field(..., ge=0, le=1, description="Annual interest rate (APR) as a fraction (e.g., 0.043 = 4.3%).")
    amort_years: int = Field(30, description="Amortization term in years for a fully-amortizing schedule (excludes IO period).")
    io_years: int = Field(0, description="Number of initial interest-only years before amortization begins (0 for none).")
    mortgage_insurance_rate: float = Field(
        0.04,
        ge=0,
        le=1,
        description=(
            "Upfront mortgage insurance premium applied if down_payment_rate < 0.20. "
            "Computed as purchase_price * mortgage_insurance_rate and added to initial cash outlay."
        ),
    )


class OperatingExpenses(BaseModel):
    """
    Annual operating expense inputs for Year 1. A uniform growth rate (expense_growth) is applied each year.
    """

    model_config = ConfigDict(validate_assignment=True)

    insurance: float = Field(..., ge=0, description="Annual property insurance. Zero means this expense is absent from the model.")
    taxes: float = Field(..., ge=0, description="Annual property taxes. Zero means this expense is absent from the model.")
    utilities: float = Field(
        ...,
        ge=0,
        description=(
            "Annual utilities paid by owner (electric/gas/common areas if applicable). " "Zero means this expense is absent from the model."
        ),
    )
    water_sewer: float = Field(
        ..., ge=0, description="Annual water and sewer paid by owner. Zero means this expense is absent from the model."
    )
    property_management: float = Field(
        ...,
        ge=0,
        description="Annual property management fees (fixed or % of income, entered as currency). Zero is the common self-managed case.",
    )
    repairs_maintenance: float = Field(
        0.0, ge=0, description="Annual repairs & maintenance allowance. Zero means this expense is absent from the model."
    )
    trash: float = Field(0.0, ge=0, description="Annual trash/garbage removal. Zero means this expense is absent from the model.")
    landscaping: float = Field(0.0, ge=0, description="Annual landscaping/grounds. Zero means this expense is absent from the model.")
    snow_removal: float = Field(
        0.0, ge=0, description="Annual snow removal (if applicable). Zero means this expense is absent from the model."
    )
    hoa_fees: float = Field(
        0.0, ge=0, description="Annual HOA/condo fees (if applicable). Zero means this expense is absent from the model."
    )
    reserves: float = Field(
        0.0, ge=0, description="Annual replacement reserves (roof, HVAC, turnover). Zero means this expense is absent from the model."
    )
    other: float = Field(
        0.0,
        ge=0,
        description=(
            "Catch-all for any additional recurring OPEX not itemized above. Zero means this expense is "
            "absent from the model. A negative operating expense is income wearing a costume; it belongs "
            "in other_income_month."
        ),
    )
    expense_growth: float = Field(0.0, description="Annual growth rate applied to all OPEX line items (e.g., 0.02 = +2%/yr).")


# -------------------------
# Per-unit income model
# -------------------------


class UnitIncome(BaseModel):
    """One unit's monthly revenue.

    FROZEN (Mission 5 Gate V, N3 -- supersedes Mission 4 PV.2's validate_assignment-only ruling
    for this model and `IncomeModel`). The engine's income seams (`PrecomputedIncome`,
    `ShiftedIncome`) carry aggregates derived from these fields and re-validate by object
    identity plus unit count; a post-derivation `unit.rent_month += x` used to pass both checks
    and silently reprice the deal. As of the N3 re-review fix, nothing in `src/` mutates an
    `IncomeModel`'s `units` list in place: `engine._apply_insight_modifiers`'s amenity-uplift
    loops (the one path that used to write `inc.units[i] = ...` element by element) now build a
    whole new `units` list and assign it once via `model_copy(update={"units": [...]})`, matching
    the recourse rent lever (`recourse._fast_unit_income`) and the market adapter, which already
    built NEW instances. Immutability is enforced at the schema instead of narrating the threat in
    docstrings. Construction-time validation is unchanged.
    """

    model_config = ConfigDict(frozen=True)

    rent_month: float = Field(
        ...,
        ge=0,
        description=(
            "Monthly rent for this unit at Year 1 start (pre-growth). Zero is legitimate: a vacant unit, a "
            "unit under renovation, or the owner-occupied unit in a house-hack."
        ),
    )
    other_income_month: float = Field(
        0.0, ge=0, description="Other monthly income attributable to this unit (parking, storage, laundry). Zero is legitimate."
    )


class IncomeModel(BaseModel):
    """
    Revenue model with heterogeneous unit rents.
    - 'units' length defines total unit count.
    - Rents and other income are MONTHLY inputs; the model annualizes internally.
    - occupancy and bad_debt_factor reduce GSI to GOI.

    FROZEN (Mission 5 Gate V, N3): see `UnitIncome`'s docstring for the full rationale. Field
    reassignment (including replacing `units` wholesale) raises; derive changed incomes with
    `model_copy(update=...)`. KNOWN RESIDUAL (now hypothetical, not exercised): `frozen=True`
    guards attribute assignment, not the `units` list's own contents -- in-place `append`/`pop`
    (would be caught at use time by the engine's `num_units` re-check) and same-length element
    replacement (caught by neither layer) remain STRUCTURALLY possible in Python. The one call
    site that used to do the latter (`engine._apply_insight_modifiers`'s amenity-uplift loops)
    was rewritten under N3 to build a new list and assign it once, so as of this fix no code in
    `src/` opens the residual; a future author could still reintroduce it by writing
    `income.units[i] = ...` instead of `model_copy`. The engine seams document exactly this
    split; do not claim more than it.
    """

    model_config = ConfigDict(frozen=True)

    units: list[UnitIncome] = Field(..., description="List of units with per-unit monthly rent and other income.")
    occupancy: float = Field(0.97, ge=0, le=1, description="Economic occupancy fraction (1 - vacancy). 0.97 = 97%.")
    bad_debt_factor: float = Field(
        0.90, ge=0, le=1, description="Collections effectiveness after bad debt. 0.90 means keep 90% after losses."
    )
    rent_growth: float = Field(0.03, description="Annual growth rate applied to rent and other monthly income (e.g., 0.03 = +3%/yr).")


class RefinancePlan(BaseModel):
    """
    Refinance assumptions (optional). If enabled, computes value from NOI and exit cap, then applies refi LTV.
    Timing convention: refi occurs at the END of 'year_to_refi' (after that year's cash flows).
    """

    model_config = ConfigDict(validate_assignment=True)

    do_refi: bool = Field(True, description="Whether to model a refinance event.")
    year_to_refi: int = Field(5, description="Refinance occurs at the END of this year (e.g., 5 = after Year 5 cash flows).")
    refi_ltv: float = Field(0.75, ge=0, le=1, description="Loan-to-Value used at refi to size the new loan.")
    exit_cap_rate: float | None = Field(
        None,
        description=(
            "Cap rate used to value the asset at refi. If None, the engine falls back to "
            "market.cap_rate_purchase, then to the computed purchase cap rate."
        ),
    )
    market_cap_rate: float | None = Field(
        None,
        description=(
            "Market cap rate reference. NOT read by any engine or agent — record-keeping only. "
            "Set market.cap_rate_purchase to override the purchase cap rate."
        ),
    )


class MarketAssumptions(BaseModel):
    """Market / risk guardrails used for purchase metrics and strategist rules."""

    model_config = ConfigDict(validate_assignment=True)

    cap_rate_purchase: float | None = Field(
        None, description="If provided, use this as the purchase cap rate; else compute NOI/P for Year 1."
    )
    cap_rate_floor: float | None = Field(None, description="Minimum acceptable cap rate; if provided, flag deals below this threshold.")
    cap_rate_spread_target: float = Field(
        0.015, description="Target spread: cap_rate - interest_rate must be ≥ this value (e.g., 0.015 = 150 bps)."
    )
    cap_rate_drift: float = Field(
        0.0, description="Optional annual drift (absolute, e.g., 0.0025 = +25 bps/year) applied to cap rate over time."
    )


class FinancialInputs(BaseModel):
    """Top-level input bundle consumed by the financial model tool."""

    model_config = ConfigDict(validate_assignment=True)

    financing: FinancingTerms = Field(
        ..., description="Purchase and loan terms (price, down payment, rate, amortization, IO, mortgage insurance)."
    )
    opex: OperatingExpenses = Field(..., description="Year 1 operating expenses with annual growth.")
    income: IncomeModel = Field(..., description="Revenue model (per-unit monthly inputs; annualized internally).")
    refi: RefinancePlan = Field(default_factory=RefinancePlan, description="Refinance plan. Enabled by default; configurable.")
    market: MarketAssumptions = Field(default_factory=MarketAssumptions, description="Market guardrails and cap-rate assumptions.")
    capex_reserve_upfront: float = Field(
        0.0,
        ge=0,
        description=(
            "One-time upfront CapEx/reserves added to initial cash outlay (not recurring OPEX). " "Zero is the default and the common case."
        ),
    )
    income_is_estimated: bool = Field(
        False,
        description=(
            "If True, the engine may apply conservative insight-driven adjustments to income. "
            "Leave False to respect user-provided income verbatim."
        ),
    )


# =========================
# Listing insights
# =========================


class ListingInsights(BaseModel):
    """Signals extracted from listing text and photos. Used by Strategist and to adjust OPEX/CapEx if desired."""

    address: str | None = Field(None, description="Human-readable address or short identifier.")
    title: str | None = Field(
        None,
        description="Inferred listing title, used to name the report when no address could be parsed.",
    )
    # --- Stated facts, parsed from the listing copy (all optional; None = not stated/parsed) ---
    price: float | None = Field(None, description="List price as stated in the listing copy.")
    sqft: int | None = Field(None, description="Finished floor area in square feet.")
    bedrooms: float | None = Field(None, description="Bedroom count (float to allow half-counts in some feeds).")
    bathrooms: float | None = Field(None, description="Bathroom count (e.g., 1.5).")
    year_built: int | None = Field(None, description="Year the property was built.")

    amenities: list[str] = Field(default_factory=list, description="Recognized amenities (e.g., 'in-unit laundry', 'parking').")
    condition_tags: list[str] = Field(default_factory=list, description="Condition features (e.g., 'renovated kitchen', 'old roof').")
    defects: list[str] = Field(default_factory=list, description="Potential issues (e.g., 'water stain', 'mold', 'foundation crack').")
    notes: list[str] = Field(default_factory=list, description="Free-form additional observations.")

    # ADDITIVE (Mission 2): per-tag provenance. The three tag lists above remain the contract --
    # every existing consumer keeps reading them unchanged and this field defaults to empty, so a
    # producer that has not been taught to populate it is not a validation error. It is a parallel
    # ledger, not a replacement: see ObservationProvenance for why it is a list and not a dict.
    observations: list[ObservationProvenance] = Field(
        default_factory=list,
        description=(
            "Per-observation provenance for the amenities/condition_tags/defects above. Zero or "
            "more records per tag (a tag observed by both the listing copy and a photo yields one "
            "record each). Advisory: may be empty even when the tag lists are not."
        ),
    )


# =========================
# Computed outputs
# =========================


class YearBreakdown(BaseModel):
    """
    One row per modeled year, after applying rent/expense growth, with detailed OPEX, debt service, and valuation metrics.
    """

    year: int = Field(..., description="Year index starting at 1.")
    gsi: float = Field(..., description="Gross Scheduled Income: annualized rent + other income before vacancy/bad debt.")
    goi: float = Field(..., description="Gross Operating Income: GSI after occupancy and bad-debt factors.")

    # Operating expenses (post-growth for that year)
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

    # Cash flow
    cash_flow: float = Field(..., description="Levered cash flow before taxes: NOI - debt_service.")
    dscr: float = Field(..., description="Debt Service Coverage Ratio: NOI / debt_service.")
    ending_balance: float = Field(..., description="Ending loan principal balance after this year's payments.")

    # Valuation/equity metrics
    cap_rate_applied: float | None = Field(
        None, description="Cap rate applied for valuation in this year (purchase cap ± drift if not overridden)."
    )
    est_value: float = Field(0.0, description="Estimated property value in this year, typically NOI / cap_rate_applied.")
    ltv_pct: float = Field(0.0, description="Loan-to-Value ratio in percent: ending_balance / est_value.")
    available_equity: float = Field(0.0, description="Available equity at 80% LTV: (0.8 × est_value) − ending_balance, floored at 0.")

    notes: list[str] = Field(default_factory=list, description="Any annotations (IO years, refi year, unusual adjustments).")


class PurchaseMetrics(BaseModel):
    """Point-in-time purchase metrics computed from Year 1 and financing."""

    cap_rate: float = Field(..., description="Purchase cap rate (either provided or computed as NOI_Y1 / purchase_price).")
    coc: float = Field(..., description="Cash-on-Cash return in Year 1: cash_flow_Y1 / acquisition_cash.")
    dscr: float = Field(..., description="Year 1 DSCR: NOI_Y1 / annual_debt_service.")
    annual_debt_service: float = Field(..., description="Annual debt service in Year 1.")
    acquisition_cash: float = Field(
        ...,
        description="Initial cash outlay: down payment + closing costs + upfront reserves (+ mortgage insurance if applicable).",
    )
    spread_vs_rate: float = Field(..., description="Cap rate minus interest rate (fraction terms), used for spread checks.")


class RefiEvent(BaseModel):
    """Details of a refinance event if modeled."""

    year: int = Field(..., description="Year when the refi occurs (end-of-year timing).")
    value: float = Field(..., description="Implied property value at refi: NOI_refi / exit_cap.")
    new_loan: float = Field(..., description="New loan amount sized by refi LTV.")
    payoff: float = Field(..., description="Outstanding principal balance paid off at refi.")
    cash_out: float = Field(..., description="Cash-out proceeds to equity: max(0, new_loan - payoff).")


class FinancialForecast(BaseModel):
    """Complete financial projection and headline returns."""

    purchase: PurchaseMetrics = Field(..., description="Purchase metrics at close/Year 1.")
    years: list[YearBreakdown] = Field(..., description="Per-year detailed pro forma over the horizon.")
    refi: RefiEvent | None = Field(None, description="Refi details if modeled; None otherwise.")
    irr_10yr: float = Field(..., description="Levered IRR over the 10-year horizon including refi/terminal equity.")
    equity_multiple_10yr: float = Field(..., description="(Total distributions to equity) / (initial equity).")
    warnings: list[str] = Field(default_factory=list, description="Guardrail messages (spread shortfall, subscale risk, negative CF).")


# =========================
# Final strategist output
# =========================


class InvestmentThesis(BaseModel):
    """Human-readable decision synthesized by the Chief Strategist."""

    verdict: str = Field(..., description='One of: "BUY" (proceed), "CONDITIONAL" (proceed with fixes), or "DECLINE" (walk away).')
    rationale: list[str] = Field(..., description="Bulleted reasons supporting the verdict.")
    levers: list[str] = Field(
        default_factory=list, description="Suggested actions to strengthen the deal (e.g., negotiate, increase rents)."
    )


# =========================
# Market insights
# =========================


class MarketSnapshot(BaseModel):
    """
    Point-in-time market context used by scenario generation and guardrails.

    This is descriptive (not prescriptive) data you might source from public
    reports or internal research. Values are expressed as *fractions* (e.g.,
    0.05 for 5%) to match the rest of the codebase.
    """

    region: str = Field(..., description="Market/geographic region name (e.g., 'Moncton, NB').")
    vacancy_rate: float = Field(..., ge=0, le=1, description="Vacancy rate as a fraction (e.g., 0.05 for 5%).")
    cap_rate: float = Field(..., ge=0, description="Market capitalization rate as a fraction.")
    rent_growth: float = Field(..., description="Expected annual rent growth as a fraction.")
    expense_growth: float = Field(..., description="Expected annual OPEX growth as a fraction.")
    interest_rate: float = Field(..., ge=0, description="Prevailing interest rate (APR) as a fraction.")
    notes: str | None = Field(None, description="Optional commentary or source notes.")

    model_config = ConfigDict(frozen=True, extra="ignore")

    def summary(self) -> str:
        return (
            f"[MarketSnapshot] {self.region} | "
            f"Vacancy: {self.vacancy_rate:.2%}, Cap: {self.cap_rate:.2%}, "
            f"Rent↑: {self.rent_growth:.2%}, Opex↑: {self.expense_growth:.2%}, "
            f"Rate: {self.interest_rate:.2%}" + (f" | Notes: {self.notes}" if self.notes else "")
        )

    def __str__(self) -> str:
        return self.summary()


class RegionalIncomeTable(BaseModel):
    """
    Reference rent & turnover table for a specific bedroom count in a region.

    Used to sanity-check underwriting and to seed scenario analysis. All money
    values should be in the same implicit currency for your project.
    """

    region: str = Field(..., description="Market/geographic region name.")
    bedrooms: int = Field(..., ge=0, description="Bedroom count (0 = studio).")
    median_rent: float = Field(..., ge=0, description="Median monthly rent for this unit type.")
    p25_rent: float = Field(..., ge=0, description="25th percentile monthly rent.")
    p75_rent: float = Field(..., ge=0, description="75th percentile monthly rent.")
    turnover_cost: float = Field(
        ...,
        ge=0,
        description=(
            "NOT an observed average. Its only producer (`market.regional_income`) writes "
            "`median_rent * 0.5`, an uncited rule of thumb -- the previous wording, 'Average "
            "turnover cost for this unit type', asserted a measurement nothing took. Withheld from "
            "`summary()` and from the advisor's JSON at Gate 3 (2026-08-05) so it reaches no "
            "reader; the field itself stays only because removing a required field is a breaking "
            "change and that call is Roger's. Do not render it or feed it to a calculation."
        ),
    )
    str_multiplier: float | None = Field(
        None,
        ge=0,
        description=(
            "Optional STR uplift (multiplier) relative to LTR baseline. Always `None` since Gate 3 "
            "(2026-08-05): it was a hardcoded 1.5x gated by a policy hook whose entire body was "
            "`return True`, so it printed for every region on earth about an activity many "
            "municipalities regulate. It stays `None` until a real regional policy lookup exists."
        ),
    )

    model_config = ConfigDict(frozen=True, extra="ignore")

    def summary(self) -> str:
        # Mission 2, Gate 3 (2026-08-05): dropped the "[RegionalIncomeTable]" class-name prefix and
        # the turnover_cost/STR-multiplier figures from this string -- both were found fabricated
        # (turnover_cost is an uncited "median rent * 0.5" rule of thumb; str_multiplier was a
        # hardcoded 1.5x gated by a policy hook that always returned True) and this method's output
        # reaches the CLI page. The fields themselves stay on the model (removing them would touch
        # this file's field declarations, which this project treats as additive-only, and no other
        # code depends on them); only what this method renders changed. See CHANGELOG.md "Removed".
        return (
            f"{self.region} | {self.bedrooms}BR | "
            f"P25: ${self.p25_rent:,.0f}, Median: ${self.median_rent:,.0f}, P75: ${self.p75_rent:,.0f}"
        )

    def __str__(self) -> str:
        return self.summary()


# =========================
# Market hypotheses
# =========================


class MarketHypothesis(BaseModel):
    """
    A single “what-if” market hypothesis (deltas relative to a snapshot).

    All deltas are absolute (e.g., +0.02 == +200 bps). These are used to
    perturb a baseline `MarketSnapshot` for scenario analysis.
    """

    rent_delta: float = Field(..., description="Absolute change to rent growth (e.g., +0.02 = +200 bps).")
    expense_growth_delta: float = Field(..., description="Absolute change to OPEX growth (fraction).")
    interest_rate_delta: float = Field(..., description="Absolute change to interest rate (fraction).")
    cap_rate_delta: float = Field(..., description="Absolute change to cap rate (fraction).")
    vacancy_delta: float = Field(..., description="Absolute change to vacancy rate (fraction).")
    str_viability: bool = Field(..., description="Whether STR operation is viable under this hypothesis.")
    prior: float = Field(..., ge=0, le=1, description="Prior probability weight (normalized across a set).")
    rationale: str = Field(..., description="Short explanation for the hypothesis.")

    model_config = ConfigDict(frozen=True, extra="ignore")

    def as_dict(self) -> dict[str, object]:
        return self.model_dump()

    def summary(self) -> str:
        def fmt_pct(x: float) -> str:
            sym = "▲" if x > 0 else "▼" if x < 0 else "➝"
            return f"{sym} {abs(x) * 100:.2f}%"

        parts = [
            f"Rent: {fmt_pct(self.rent_delta)}",
            f"Opex: {fmt_pct(self.expense_growth_delta)}",
            f"Rate: {fmt_pct(self.interest_rate_delta)}",
            f"Cap: {fmt_pct(self.cap_rate_delta)}",
            f"Vac: {fmt_pct(self.vacancy_delta)}",
        ]
        prior_pct = f"{self.prior * 100:.2f}%"
        str_flag = "Y" if self.str_viability else "N"
        return "  ".join(parts) + f" | STR={str_flag} | prior={prior_pct} | {self.rationale}"

    def __str__(self) -> str:
        return self.summary()


class HypothesisSet(BaseModel):
    """
    Immutable collection of `MarketHypothesis` items tied to a region and seed.

    `prior` values inside `items` should typically be normalized to sum to 1.0,
    but the set doesn’t enforce that to keep scenarios flexible.
    """

    snapshot_region: str = Field(..., description="Region associated with this hypothesis set.")
    seed: int = Field(..., description="Random seed used for reproducibility.")
    items: tuple[MarketHypothesis, ...] = Field(..., description="Tuple of market hypotheses.")
    notes: str | None = Field(None, description="Optional notes about this set.")

    model_config = ConfigDict(frozen=True, extra="ignore")

    def as_dict(self) -> dict[str, object]:
        return self.model_dump()

    def summary(self, top_n: int = 5) -> str:
        n = len(self.items)
        if n == 0:
            return f"[HypothesisSet] {self.snapshot_region} | seed={self.seed} | 0 items"
        top = sorted(
            self.items,
            key=lambda h: (-h.prior, h.rent_delta, h.expense_growth_delta, h.interest_rate_delta, h.cap_rate_delta, h.vacancy_delta),
        )[:top_n]
        prior_sum = sum(h.prior for h in self.items)
        lines = [f"[HypothesisSet] {self.snapshot_region} | seed={self.seed} | count={n} | prior_sum={prior_sum:.6f}"]
        for i, h in enumerate(top, 1):
            lines.append(f"  #{i}: {h.summary()}")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


# =========================
# Listings
# =========================


class ListingNormalized(BaseModel):
    """Normalized facts parsed from listing HTML or text."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    source_url: str | None = None
    title: str | None = None
    title_confidence: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Confidence score for the inferred title (if applicable)."
    )
    title_source: Literal["html", "text", "user"] | None = Field(
        default=None, description="Source of the title: HTML title tag, text-inferred, or user-provided."
    )
    title_candidates: list[str] | None = Field(
        default=None, description="Alternative title candidates (if applicable), ordered by confidence."
    )
    price: float | None = Field(default=None, ge=0, description="Monthly rent or list price; currency-agnostic float.")
    address: str | None = None  # keept for backward compatibility (single-line summary)

    bedrooms: float | None = Field(default=None, ge=0, description="Allow 0 for studio; 0.5 for den/loft if detected.")
    bathrooms: float | None = Field(default=None, ge=0)
    sqft: int | None = Field(default=None, ge=0)
    year_built: int | None = Field(default=None, ge=1700, le=datetime.now().year)

    parking: bool | None = None
    laundry: str | None = Field(default=None, description="One of: in-unit / on-site / none")
    heating: str | None = None
    cooling: str | None = None
    hoa_fee: float | None = Field(default=None, ge=0)
    notes: str | None = None

    postal_code: str | None = Field(
        None,
        description="Postal/ZIP code derived from listing text/HTML when available.",
    )

    address_structure: AddressResult | None = Field(
        None,
        description="Structured address components parsed via usaddress or postal libraries.",
    )

    def summary(self) -> str:
        bits: list[str] = []
        if self.title:
            bits.append(self.title)
        if self.price is not None:
            bits.append(f"price: {self.price:,.0f}")

        # Prefer structured fragments if present
        if self.address_structure and (self.address_structure.city or self.address_structure.state_province):
            city = self.address_structure.city or ""
            st = self.address_structure.state_province or ""
            pc = self.address_structure.postal_code or ""
            loc = " ".join(x for x in [city, st, pc] if x)
            if loc:
                bits.append(loc)

        # Fall back to flat address if no struct info
        if self.address and not any(" " in s for s in bits[-1:]):  # avoid duplicating location-ish tokens
            bits.append(self.address)

        # existing bedroom/bath/sqft/etc
        if self.bedrooms is not None:
            bits.append(f"{self.bedrooms} bd")
        if self.bathrooms is not None:
            bits.append(f"{self.bathrooms} ba")
        if self.sqft is not None:
            bits.append(f"{self.sqft} sqft")
        return " | ".join(bits) if bits else "ListingNormalized: (no key facts)"


class ParkingType(str, Enum):
    garage = "garage"
    driveway = "driveway"
    street = "street"
    none = "none"
    unknown = "unknown"


#: How a detection record came to exist — **a file name may SUGGEST; only a detector that
#: actually looked may CONFIRM.** These four values are the four epistemic states that rule
#: produces, and consumers branch on them:
#:
#:   pixels               — a provider examined the image and emitted the label. Its own
#:                          confidence, evidence and rationale are the record.
#:   filename_confirmed   — a provider that CAN detect this label did detect it, AND the file name
#:                          independently says the same thing. Two agreeing signals, so the
#:                          confidence is the corroborated blend.
#:   filename_contested   — a provider that CAN detect this label examined the image and did NOT
#:                          emit it, while the file name says it is there. A genuine
#:                          disagreement: something measured it, so the claim is scoreable, and
#:                          the blend scores it deliberately weakly.
#:   filename_unconfirmed — NO registered provider declares the ability to detect this label, so
#:                          nothing measured it. Carries no confidence at all and must be kept out
#:                          of every path that can move a number.
#:
#: Absent means ``pixels``: a record that never went through the filename pass is a detection,
#: which is what it is.
#:
#: Defined HERE rather than in ``core.cv`` because it crosses the schema boundary on
#: :class:`DetectedLabelModel`, and the schema layer may not import ``core``.
#: ``core.cv.amenities_defects`` re-exports this name, with the producer-side notes, so existing
#: importers are unaffected and there is exactly one definition to drift from.
DetectionSource = Literal["pixels", "filename_confirmed", "filename_contested", "filename_unconfirmed"]


class DetectedLabelModel(BaseModel):
    """Closed-set amenity/defect detection for a single image."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    name: str = Field(..., description="Canonical ontology label.")
    category: Literal["amenity", "defect"] = Field(..., description="Closed-set type.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence in [0,1].")
    evidence: list[str] | None = Field(default=None, description="Optional textual/visual evidence ids.")
    rationale: str | None = Field(default=None, description="Short model rationale (if available).")

    # ADDITIVE (Mission 2, G2-N2). The producer has always set this on the raw ``DetectedLabel``
    # mapping; this model did not declare it and ``extra="ignore"`` therefore DELETED it at the
    # validation boundary. Downstream, `core.insights.synthesis` had nothing left to branch on and
    # stamped every surviving record `origin="cv_provider", provider_kind="model"` — asserting a
    # detector found what it had explicitly reported it did NOT find. Carrying the marker on the
    # model is what makes refusing that stamp possible at all.
    source: DetectionSource = Field(
        default="pixels",
        description=(
            "How this record came to exist; see DetectionSource. Default 'pixels' matches the "
            "producer's contract that an absent marker means a provider emitted the label itself."
        ),
    )


#: Which ``ListingInsights`` list an observation belongs to.
ObservationKind = Literal["condition", "defect", "amenity"]

#: What class of producer authored an observation. Deliberately about the *producer*, not the
#: confidence: ``cv_provider`` says "a detector looked at the pixels", it does NOT say the
#: detector was a model — read ``ObservationProvenance.provider_kind`` for that.
#:
#:   listing_text   — a keyword/regex match over the listing copy, or a normalized listing fact.
#:   photo_filename — derived from an image's FILE NAME, not its pixels (e.g. "kitchen_island.jpg").
#:   cv_provider    — a detector in ``core/cv`` ran over the image.
#:   llm            — authored by a language model (``agents/crewai_components``' V2 path).
#:   unknown        — the tag is present but this pipeline genuinely cannot attribute it. Recorded
#:                    rather than guessed; a consumer must not upgrade it to any of the above.
ObservationOrigin = Literal["listing_text", "photo_filename", "cv_provider", "llm", "unknown"]


class ObservationProvenance(BaseModel):
    """Where ONE observation on ``ListingInsights`` came from, and what evidence backs it.

    Exists because ``condition_tags`` / ``defects`` / ``amenities`` are bare strings: nothing in
    them distinguishes an LLM-authored tag from a regex keyword match from a CV detection, so a
    report cannot honestly say "AI observed 'old roof'". This record carries the origin alongside
    the tag.

    Metadata is present only where it genuinely exists. A keyword match has no confidence, so
    ``detection`` stays ``None`` for text origins -- a fabricated confidence would be worse than
    no number at all.

    ``detection`` reuses :class:`DetectedLabelModel` rather than restating confidence/evidence/
    rationale, so the CV pipeline's own record travels intact. ``detection.name`` is the raw
    ontology label; ``tag`` is the string as it appears in the ``ListingInsights`` list, which can
    differ (surface mapping, e.g. ontology ``stainless_appliances`` -> surface ``stainless_kitchen``).
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    tag: str = Field(..., description="The observation string exactly as it appears in the ListingInsights list named by `kind`.")
    kind: ObservationKind = Field(..., description="Which ListingInsights list this tag lives in.")
    origin: ObservationOrigin = Field(..., description="Producer class that authored the tag; see ObservationOrigin.")
    detail: str | None = Field(
        default=None,
        description=(
            "The single free-text 'what fired' slot: the matched listing phrase (listing_text), the "
            "filename token (photo_filename), or the threshold that tripped (derived cv_provider tags). "
            "None when the producer offers no such handle."
        ),
    )
    provider: str | None = Field(default=None, description="Producer identity, e.g. 'vision' | 'local' | an LLM model name.")
    provider_kind: Literal["heuristic_stub", "model"] | None = Field(
        default=None,
        description=(
            "Whether `provider` is a real model or a hand-written heuristic standing in for one "
            "(see core.cv.amenities_defects.provider_kind). This is the field a caller must read "
            "before claiming a tag was AI-observed. None when no provider was involved."
        ),
    )
    provider_version: str | None = Field(default=None, description="Version string of the producer, e.g. 'vision-stub-v1'.")
    source_image_sha: str | None = Field(default=None, description="sha256 of the image this observation came from, when it came from one.")
    detection: DetectedLabelModel | None = Field(
        default=None,
        description="The CV pipeline's own detection record (confidence/evidence/rationale). None for non-detector origins.",
    )


class ParkingSummary(BaseModel):
    """Listing-level parking inference derived from image detections."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    parking_type: Literal["garage", "driveway", "street", "none", "unknown"] | None = Field(
        default=None, description="Best guess of primary parking type."
    )
    parking_spots: int | None = Field(default=None, ge=0, description="Conservative spot estimate, capped at 3.")
    ev_charging: bool = Field(default=False, description="EV charging likely present.")
    rationale: str | None = Field(default=None, description="One-line reason for the above.")


class PhotoInsights(BaseModel):
    """Deterministic CV-derived insights from a folder of photos."""

    model_config = ConfigDict(frozen=False, extra="ignore")

    room_counts: dict[str, int] = Field(default_factory=dict, description="Counts per room type (kitchen, bath, etc.).")
    amenities: dict[str, bool] = Field(default_factory=dict, description="Amenity presence flags.")
    quality_flags: dict[str, float] = Field(default_factory=dict, description="Quality scores in [0,1].")
    provider: str = Field(..., description="CV provider name.")
    version: str = Field(..., description="Provider/model version string.")

    image_index: dict[str, str] = Field(default_factory=dict, description="Map sha256 → absolute path for every processed image.")
    image_labels: dict[str, list[str]] = Field(default_factory=dict, description="Generic room/material labels per image sha256.")
    image_detections: dict[str, list[DetectedLabelModel]] = Field(
        default_factory=dict, description="Amenities/defects detections per image sha256."
    )
    amenity_counts: dict[str, int] = Field(default_factory=dict, description="How many distinct images exhibited each amenity label.")
    defect_counts: dict[str, int] = Field(default_factory=dict, description="How many distinct images exhibited each defect label.")

    # ADDITIVE (Mission 2, M17/R-6). Deliberately a THIRD roll-up rather than more entries in the
    # two above: those count things a detector reported, and this counts things a file name
    # suggested that NO registered provider is able to look for (see
    # core.cv.amenities_defects.DetectionSource). The distinction is load-bearing -- amenity_counts
    # and defect_counts flow into ListingInsights and from there into the deterministic OPEX/income
    # rules, so an unmeasured claim mixed into them lets a file name move a number. These carry no
    # confidence for the same reason: nothing measured them, and any number would be invented.
    # A label listed here moves into defect_counts/amenity_counts automatically, with no code
    # change, the day a provider declaring it is registered.
    unconfirmed_hint_counts: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "How many images had a FILE NAME suggesting each label that no registered provider "
            "declares it can detect. Advisory only: unscored, and never an input to any number."
        ),
    )

    # ADDITIVE (Mission 2, G2-N1). The sibling of the field above, for the OTHER half of the same
    # rule. `unconfirmed_hint_counts` holds claims nothing was able to check; this holds claims a
    # detector that CAN see the label checked and CONTRADICTED. Deliberately a separate roll-up
    # rather than an entry in `amenity_counts`/`defect_counts`, because those two feed
    # `ListingInsights` and from there `finance.engine._apply_insight_modifiers`, which selects
    # rules by MEMBERSHIP and never reads a confidence — so a contested label sitting in them let a
    # file name a detector had contradicted move Y1 cash flow by $1,105.80. Merging the two hint
    # roll-ups would be a lie in the other direction: "nothing looked" and "something looked and
    # disagreed" are different facts and are reported with different words.
    contested_hint_counts: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "How many images had a FILE NAME suggesting each label that a covering detector "
            "examined the pixels for and did not report. Advisory only: never an input to any number."
        ),
    )
    parking: ParkingSummary | None = Field(default=None, description="Derived listing-level parking summary.")
    ontology_version: str | None = Field(default=None, description="Ontology version string used for closed-set labels.")

    images_total: int = Field(
        default=0,
        ge=0,
        description="Number of processed images.",
    )
    detections_total: int = Field(
        default=0,
        ge=0,
        description="Total number of detections across images.",
    )
    provenance: dict[str, Any] = Field(
        default_factory=dict,
        description="Provider/params/cache metadata for reproducibility.",
    )

    # ---- validators ----
    @field_validator("room_counts")
    @classmethod
    def _non_negative_counts(cls, v: dict[str, int]) -> dict[str, int]:
        for k, val in v.items():
            if val < 0:
                raise ValueError(f"room_counts[{k}] must be >= 0")
        return v

    @field_validator("quality_flags")
    @classmethod
    def _quality_0_1(cls, v: dict[str, float]) -> dict[str, float]:
        for k, val in v.items():
            if not (0.0 <= val <= 1.0):
                raise ValueError(f"quality_flags[{k}] must be in [0,1]")
        return v

    # ---- new validators ----
    @field_validator("amenity_counts", "defect_counts")
    @classmethod
    def _non_negative_label_counts(cls, v: dict[str, int]) -> dict[str, int]:
        for k, val in v.items():
            if val < 0:
                raise ValueError(f"label_counts[{k}] must be >= 0")
        return v

    def summary(self) -> str:
        rooms = ", ".join(f"{k}:{v}" for k, v in sorted(self.room_counts.items()))
        ams = ", ".join(k for k, v in sorted(self.amenities.items()) if v)
        q = ", ".join(f"{k}:{v:.2f}" for k, v in sorted(self.quality_flags.items()))
        return f"Rooms[{rooms}] | Amenities[{ams}] | Quality[{q}] via {self.provider}@{self.version}"


# ============================================================
# Fetch/cache models
# ============================================================


class HtmlSnapshot(BaseModel):
    """
    Cached, offline-first HTML snapshot.

    Used as the hand-off contract from the fetcher to the parsers. Paths point
    to files within the stable cache directory for the URL.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="ignore")

    url: str = Field(..., description="Original URL of the snapshot.")
    fetched_at: datetime = Field(..., description="UTC timestamp when the snapshot was last fetched.")
    status_code: int = Field(..., description="HTTP status code returned at fetch time.")
    html_path: Path = Field(..., description="Filesystem path to the raw HTML file.")
    tree_path: Path | None = Field(None, description="Path to pretty-printed DOM tree, if available.")
    bytes_size: int = Field(..., ge=0, description="Size of the raw HTML in bytes.")
    sha256: str = Field(..., description="SHA-256 digest of the raw HTML bytes.")


class FetchPolicy(BaseModel):
    """
    Deterministic fetch policy for `html_fetcher` (offline-first).

    Defines how the HTML fetcher behaves with respect to networking,
    robots.txt, rendering, caching, and error handling.

    Designed to keep ingestion reproducible and testable while still
    allowing controlled overrides (e.g., enabling headless rendering).
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="ignore")

    captcha_mode: Literal["strict", "soft", "off"] = Field(
        "soft",
        description=(
            "Captcha/WAF handling mode:\n"
            " - 'strict': raise an exception immediately\n"
            " - 'soft': log a warning and continue if possible\n"
            " - 'off': ignore captcha/WAF signals"
        ),
    )

    min_body_text: int = Field(
        400,
        ge=0,
        description="Minimum number of text characters required to consider a page 'real'. " "Helps detect placeholder or blocked pages.",
    )

    allow_network: bool = Field(
        False,
        description="If False, enforce offline-only (cache must already exist).",
    )
    allow_non_200: bool = Field(
        False,
        description="If False, raise on any HTTP status >= 400. " "If True, allow snapshot even with non-200 status codes.",
    )
    respect_robots: bool = Field(
        True,
        description="Whether to respect robots.txt before fetching online.",
    )
    timeout_s: float = Field(
        15.0,
        gt=0,
        description="HTTP timeout in seconds for online fetches.",
    )
    user_agent: str = Field(
        "AI-REA/0.2 (+deterministic-ingest)",
        description="User-Agent string used in HTTP requests.",
    )
    cache_dir: Path = Field(
        default=Path("data/cache"),
        description="Directory where cached HTML and metadata files are stored.",
    )

    render_js: bool = Field(
        False,
        description="If True, attempt headless JS rendering with Playwright/Chromium.",
    )
    render_wait_s: float = Field(
        8.0,
        ge=0,
        description="Maximum seconds to wait after navigation in render mode.",
    )
    render_wait_until: str = Field(
        "networkidle",
        description="Event to wait for in render mode. " "Valid values: 'load', 'domcontentloaded', 'networkidle'.",
    )
    render_selector: str | None = Field(
        None,
        description="Optional CSS selector to wait for in render mode before snapshot.",
    )
    save_screenshot: bool = Field(
        False,
        description="If True, save a PNG screenshot of the rendered page in the cache directory.",
    )

    strict_dom: bool = Field(
        False,
        description="If True, raise exceptions on DOM parse errors instead of ignoring them.",
    )


# =========================
# Media (public contracts)
# =========================

# Canonical media type classification used across the app.
MediaKind = Literal["image", "video", "floorplan", "document", "other"]

# Where a media reference was discovered (for provenance & debugging).
MediaSource = Literal["html", "mls_api", "feed", "manual", "unknown"]


class MediaCandidate(BaseModel):
    """
    A discovered media reference BEFORE download.

    Typical producers:
      - HTML/DOM scanners (img/src, srcset, JSON-LD, OpenGraph)
      - Site-specific script blobs (e.g., realtor.ca metadata)
      - External feeds / MLS APIs

    Notes:
      - This object is purely a *pointer* with lightweight hints; it never holds file bytes.
      - The downloader resolves, dedupes, and persists candidates to disk as MediaAsset.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    url: str = Field(..., description="Absolute (preferred) or page-relative URL to the media.")
    kind: MediaKind = Field(..., description='Media type, e.g., "image" or "video".')
    source: MediaSource = Field("unknown", description="Provenance of the reference (html|mls_api|feed|manual|unknown).")

    # Hints from the page to improve selection & ordering
    mime_hint: str | None = Field(None, description="Best-effort MIME hint if present (e.g., 'image/jpeg').")
    width_hint: int | None = Field(None, ge=1, description="Pixel width hint if advertised.")
    height_hint: int | None = Field(None, ge=1, description="Pixel height hint if advertised.")
    bytes_hint: int | None = Field(None, ge=1, description="Approximate bytes size hint if advertised.")
    priority: float = Field(
        0.0,
        description=("Relative selection priority (higher is better). " "Finders may compute this from position, size, or site cues."),
    )
    alt_text: str | None = Field(None, description="Alt/title text associated with the media, if any.")
    page_index: int | None = Field(None, ge=0, description="Page index in a multi-page gallery when known (0-based).")
    referer_url: str | None = Field(None, description="The page URL that referenced this media (for polite fetching).")
    attributes: dict[str, str] = Field(
        default_factory=dict,
        description="Arbitrary extra attributes captured at discovery time (e.g., data-*).",
    )

    # Define equality/hash by stable identity (url, kind, source)
    def __hash__(self) -> int:
        return hash((self.url, self.kind, self.source))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MediaCandidate):
            return NotImplemented
        return (self.url, self.kind, self.source) == (other.url, other.kind, other.source)


class MediaAsset(BaseModel):
    """
    A persisted media file on disk AFTER download.

    This represents the offline-first, canonical record of a media item:
      - A stable local path in the cache
      - Metadata for content type, size, image dimensions, and integrity hash
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="ignore")

    local_path: Path = Field(..., description="Absolute path to the downloaded media under the cache media directory.")
    url: str = Field(..., description="Original source URL used to fetch this asset.")
    kind: MediaKind = Field(..., description='Media type, e.g., "image" or "video".')
    source: MediaSource = Field(..., description="Provenance of the reference that produced this asset.")

    content_type: str | None = Field(None, description="HTTP Content-Type (e.g., 'image/jpeg') if available.")
    bytes_size: int = Field(..., ge=0, description="Size in bytes of the stored file.")
    sha256: str = Field(..., min_length=32, max_length=128, description="Integrity hash of the stored file (hex).")

    # Optional image metadata (None for non-images)
    width: int | None = Field(None, ge=1, description="Pixel width if detectable (images only).")
    height: int | None = Field(None, ge=1, description="Pixel height if detectable (images only).")

    created_at: datetime = Field(..., description="Timestamp when this asset was saved to disk (UTC).")
    warnings: list[str] = Field(default_factory=list, description="Non-fatal issues encountered during download or probing.")

    @property
    def path(self) -> Path:
        """Path property for easy consumption by media intelligence"""
        return self.local_path


class MediaFinderResult(BaseModel):
    """
    Output of a MediaFinder: candidates discovered on a page/feed plus coarse flags.

    Consumers (downloader/ingest) decide which candidates to fetch based on policy
    (max items, types allowed) and heuristics (priority, dimensions).
    """

    model_config = ConfigDict(
        frozen=True,  # makes model hashable (so sets/dicts work)
        extra="ignore",
    )

    has_media: bool = Field(
        False,
        description="True if the page/feed indicates the presence of media.",
    )
    photo_count_hint: int | None = Field(
        None,
        ge=0,
        description="If available, a count from site metadata (e.g., 'photos: 39').",
    )
    candidates: set[MediaCandidate] = Field(
        default_factory=set,
        description="Unique discovered media pointers (pre-download).",
    )
    notes: list[str] = Field(
        default_factory=list,
        description="Free-form notes for debugging or provenance.",
    )

    def merge(self, other: MediaFinderResult) -> MediaFinderResult:
        """
        Merge another MediaFinderResult into this one, deduplicating candidates.
        Notes are concatenated.
        """
        merged_candidates = set(self.candidates) | set(other.candidates)
        merged_notes = list({*self.notes, *other.notes})
        return MediaFinderResult(
            has_media=self.has_media or other.has_media,
            photo_count_hint=self.photo_count_hint or other.photo_count_hint,
            candidates=merged_candidates,
            notes=merged_notes,
        )


class MediaBundle(BaseModel):
    """
    The final, offline-ready collection of media for a listing.

    Produced after running the downloader on a set of MediaCandidates.
    May be empty when a page has no media or fetching is disabled/offline.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="ignore")

    assets: list[MediaAsset] = Field(default_factory=list, description="Downloaded media assets stored locally.")
    warnings: list[str] = Field(default_factory=list, description="Non-fatal issues during discovery or download.")

    @property
    def images(self) -> list[MediaAsset]:
        return [a for a in self.assets if a.kind == "image"]

    @property
    def videos(self) -> list[MediaAsset]:
        return [a for a in self.assets if a.kind == "video"]

    @property
    def floorplans(self) -> list[MediaAsset]:
        return [a for a in self.assets if a.kind == "floorplan"]


# ============================================================
# Ingestion result (normalized outputs)
# ============================================================


class IngestResult(BaseModel):
    """
    Aggregated result from the listing ingest pipeline.

    Contains:
      - listing: normalized facts parsed from HTML or text
      - photos: deterministic CV-derived insights from the photo set
      - insights: human-readable signals for the strategist (address, amenities, etc.)
      - media: downloaded media assets (if any)
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    listing: ListingNormalized = Field(..., description="Normalized listing facts parsed from HTML/text.")
    photos: PhotoInsights = Field(..., description="Deterministic CV-derived insights from photos.")
    insights: ListingInsights = Field(..., description="Signals extracted from listing text and photos.")
    media: MediaBundle = Field(default_factory=MediaBundle, description="Downloaded media assets (if any).")

    media_insights: MediaInsights | None = Field(None, description="Summary analytics computed from downloaded media assets.")


# ============================================================
# Address parsing result
# ============================================================


class AddressResult(BaseModel):
    """Best-effort structured postal address extracted from text/HTML."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    address_line: str | None = Field(
        None,
        description="Single-line street/city line if detected (e.g., '123 Main St, Springfield').",
    )
    civic_number: str | None = Field(None, description="Detected civic number")
    unit_suite: str | None = Field(
        None,
        description="Detected unit, apartment, or suite number/designator (e.g., '601', 'Apt 12').",
    )
    city: str | None = Field(
        None,
        description="Detected city or locality name if available (e.g., 'Toronto', 'Springfield').",
    )
    state_province: str | None = Field(
        None,
        description="Two-letter state/province/territory code when present (e.g., 'IL', 'BC').",
    )
    postal_code: str | None = Field(
        None,
        description="Canonicalized postal/ZIP code if detected (e.g., 'H2X 1Y4', '02139', 'SW1A 1AA', '1234 AB').",
    )
    country_hint: Literal["CA", "US", "UK", "NL", "EU"] | None = Field(
        None,
        description="Heuristic hint based on the postal pattern (Canada/US/UK/NL or generic EU 5-digit).",
    )


# =========================
# Media insights (derived)
# =========================


class MediaInsights(BaseModel):
    """
    Descriptive analytics and derived information for a set of downloaded media assets.

    This class provides summary statistics, dimensional ranges, and quality
    indicators (like duplicates and warnings) to facilitate quick quality assurance
    and aid in subsequent asset selection (e.g., choosing a hero image).
    """

    model_config = ConfigDict(frozen=False, extra="ignore")

    # ---------------------------
    # Totals and Volume
    # ---------------------------
    total_assets: int = Field(..., ge=0, description="Total count of all successfully downloaded media assets.")
    image_count: int = Field(..., ge=0, description="Count of assets identified as images.")
    video_count: int = Field(..., ge=0, description="Count of assets identified as videos.")
    document_count: int = Field(..., ge=0, description="Count of assets identified as documents (e.g., PDF).")
    other_count: int = Field(..., ge=0, description="Count of assets with kinds not covered by the standard types.")
    bytes_total: int = Field(..., ge=0, description="Total aggregate size of all downloaded assets in bytes.")

    # ---------------------------
    # Image-only Dimensional Stats
    # ---------------------------
    min_width: int | None = Field(None, ge=1, description="Minimum width observed across all image assets.")
    max_width: int | None = Field(None, ge=1, description="Maximum width observed across all image assets.")
    min_height: int | None = Field(None, ge=1, description="Minimum height observed across all image assets.")
    max_height: int | None = Field(None, ge=1, description="Maximum height observed across all image assets.")
    avg_width: float | None = Field(None, description="Average width of all image assets.")
    avg_height: float | None = Field(None, description="Average height of all image assets.")

    # ---------------------------
    # Image Orientation
    # ---------------------------
    portrait_count: int = Field(0, description="Count of images where height > width.")
    landscape_count: int = Field(0, description="Count of images where width > height.")
    square_count: int = Field(0, description="Count of images where width is approximately equal to height.")

    # ---------------------------
    # Quality and Selection
    # ---------------------------
    duplicate_hashes: list[str] = Field(
        default_factory=list,
        description="List of SHA256 hashes corresponding to assets that are exact duplicates (first hash seen is not included).",
    )

    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal issues discovered while analyzing, such as skipped files due to small size, aspect ratio issues etc.",
    )

    duplicates: list[list[str]] = Field(
        default_factory=list,
        description="Lists of SHA256 hashes that are visually similar (near-duplicates) based on perceptual hashing.",
    )

    image_quality: dict[str, dict[str, float]] = Field(
        default_factory=dict,
        description="Per-image quality metrics, including sharpness, brightness, and contrast.",
    )

    palettes: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Color palettes extracted from images, represented as lists of hex color strings.",
    )

    hero_sha256: str | None = Field(
        None, description="The SHA256 hash of the best-guess 'hero' image, typically chosen based on the largest area (width * height)."
    )


# ============================================================
# Scenario intelligence (Mission 1 — additive result models)
# ============================================================


class ScenarioMetricBand(BaseModel):
    """Prior-weighted distribution summary for ONE metric across accepted scenarios.

    All five values are heuristic-prior-weighted what-if quantiles/moments over a
    rule-based grid, NOT statistical percentiles/means of real-world outcomes.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    p25: float = Field(..., description="Prior-weighted 25th quantile (the DOWNSIDE for higher-is-better metrics).")
    p50: float = Field(..., description="Prior-weighted MEDIAN (NOT 'expected').")
    mean: float = Field(..., description="Prior-weighted mean == the EXPECTED value.")
    min: float = Field(..., description="Absolute worst accepted (context/transparency).")
    max: float = Field(..., description="Absolute best accepted.")


class ScenarioOutcome(BaseModel):
    """One accepted hypothesis + the engine metrics it produced (fractions unless noted)."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    hypothesis: MarketHypothesis = Field(..., description="Carries the deltas + prior + rationale + str_viability.")

    # Applied engine inputs, for transparent audit of the perturbation (all fractions):
    rent_growth_applied: float = Field(..., description="income.rent_growth after the rent_delta was applied.")
    expense_growth_applied: float = Field(..., description="opex.expense_growth after the expense_growth_delta was applied.")
    interest_rate_applied: float = Field(..., description="financing.interest_rate after interest_rate_delta was applied (clamped 0..1).")
    occupancy_applied: float = Field(..., description="income.occupancy after subtracting vacancy_delta (clamped 0..1).")
    cap_rate_purchase_applied: float | None = Field(
        None,
        description="base_cap + cap_rate_delta, clamped to floor 0.03; populated on every scenario run.",
    )

    # Engine outputs (money = currency units; ratios/returns = fractions):
    dscr_y1: float = Field(..., description="Year-1 DSCR from the perturbed run.")
    coc_y1: float = Field(..., description="Year-1 cash-on-cash from the perturbed run.")
    cash_flow_y1: float = Field(..., description="Year-1 levered cash flow (currency units).")
    irr_10yr: float = Field(..., description="Levered 10-year IRR (fraction).")
    equity_multiple_10yr: float = Field(..., description="10-year equity multiple (x).")


class RunProvenance(BaseModel):
    """
    Pipeline-level facts about how a report was produced.

    Exists because environment knobs silently change reported numbers: ``.env`` is gitignored
    and VS Code's Python extension auto-loads it, so two people running the same command on the
    same inputs can get different reports with nothing in either one explaining the difference.

    Carries only what the report generator cannot observe for itself. The valuation knobs
    (cap drift, appreciation, stress adjustment) are read by the generator from the same
    accessors that produced the tables, so they can never disagree with the numbers above them.
    """

    engine: str = Field(..., description='Orchestration engine actually used: "deterministic" or "crewai".')
    scenarios_enabled: bool = Field(..., description="Whether the Market Scenarios overlay was run.")
    vision_enabled: bool = Field(
        ...,
        description="Whether the AI photo-tagging path was active (AIREAL_USE_VISION). Changes which amenities appear.",
    )
    llm_mode_enabled: bool = Field(
        False,
        description=(
            "Whether a language model ACTUALLY authored observations in this run -- not merely "
            "whether AIREAL_LLM_MODE was requested. `main.py` writes `llm_mode_enabled() and "
            "any(o.origin == 'llm' ...)`, so a run with the flag set whose model call fell back to "
            "the deterministic path records False, which is the honest answer. When true, a model "
            "authored the listing observations (condition tags, defects, amenities) that feed the "
            "deterministic insight modifiers, so it changes the reported figures. Distinct from "
            "vision_enabled, which covers photo tagging only: on an LLM run with vision off, "
            "vision_enabled=False alone would leave the report implying no model was involved. "
            "The verdict is never LLM-authored in any mode (see chief_strategist.synthesize_thesis)."
        ),
    )
    config_path: str | None = Field(
        None,
        description="Inputs file used, exactly as supplied. None when the run fell back to hardcoded demo inputs.",
    )


class ScenarioAnalysis(BaseModel):
    """Aggregate prior-weighted result for a run; rendered only when scenarios are ON."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    snapshot: MarketSnapshot = Field(..., description="Market snapshot the hypotheses were generated from.")
    seed: int = Field(..., description="Seed threaded to generate_hypotheses (provenance; generator RNG is inert).")
    io_years: int = Field(
        ...,
        ge=0,
        description=(
            "financing.io_years from the untouched inputs (invariant across scenarios; the adapter "
            "never perturbs the term). The report renders an interest-only caveat when > 0, because "
            "Year-1 DSCR/CoC/CF are IO-flattered and understate the post-IO amortizing debt load."
        ),
    )
    n_generated: int = Field(..., ge=0, description="Number of hypotheses before the rejector.")
    n_accepted: int = Field(..., ge=0, description="Number of hypotheses after the rejector (== len(outcomes)).")
    prior_sum: float = Field(..., description="Sum of accepted priors (~1.0 ±1e-12; 0.0 if none accepted).")
    outcomes: tuple[ScenarioOutcome, ...] = Field(default_factory=tuple, description="Deterministic lexicographic order.")
    dscr: ScenarioMetricBand | None = Field(None, description="Prior-weighted DSCR band; None iff n_accepted == 0.")
    coc: ScenarioMetricBand | None = Field(None, description="Prior-weighted CoC band; None iff n_accepted == 0.")
    cash_flow_y1: ScenarioMetricBand | None = Field(None, description="Prior-weighted Y1 cash-flow band; None iff n_accepted == 0.")
    irr_10yr: ScenarioMetricBand | None = Field(None, description="Prior-weighted IRR band; None iff n_accepted == 0.")
    equity_multiple_10yr: ScenarioMetricBand | None = Field(None, description="Prior-weighted equity-multiple band; None if 0 accepted.")
    notes: str | None = Field(None, description="Rejector notes / 'no admissible scenarios'.")


class RecourseLever(BaseModel):
    """
    One candidate single-lever fix for one currently-failing guardrail (Mission 4 —
    "What would have to change?"), found by re-running ``run_financial_model`` on a perturbed
    deep copy of ``FinancialInputs`` -- NEVER by inverting the guardrail's own formula.

    The levers are not independent (a price cut shrinks the loan, lifts the cap rate, and changes
    cash-in all at once), so every ``target_value``/``delta`` here is read off a real engine
    re-run, never solved for algebraically. See ``src/market/recourse.py`` module docstring for
    the concrete trap case (the CoC guardrail via the purchase-price lever) this discipline
    guards against.
    """

    guardrail: Literal["dscr", "spread", "irr", "coc", "cf_y1", "cf_all", "cap_floor"] = Field(
        ...,
        description=(
            "Which of the (at most six) live chief_strategist.py guardrails this row targets. "
            "cf_all is never live (REQUIRE_POSITIVE_CF_ALL is False), so a seventh guardrail is "
            "unreachable in current configuration; cap_floor is live only when the deal sets a "
            "cap_rate_floor."
        ),
    )
    lever: Literal["rent_per_unit_month", "purchase_price", "interest_rate", "annual_opex"] = Field(
        ..., description="Which investor-movable input this row perturbs, holding all others fixed."
    )
    baseline_value: float = Field(..., description="The lever's current value before perturbation, in its own native unit.")
    target_value: float | None = Field(
        None,
        description="The lever's value at the flip point, rounded away from zero to a human-facing "
        "step and re-confirmed by one more engine re-run at that rounded value. None when no flip "
        "was found within the search bound (honest-null for this row).",
    )
    delta: float | None = Field(None, description="target_value - baseline_value, signed. None alongside target_value.")
    relative_change: float | None = Field(
        None,
        ge=0,
        description="abs(delta) / abs(baseline_value) -- the cross-currency cheapness score. "
        "None when delta is None or baseline_value is 0.",
    )
    closes_guardrail: bool = Field(..., description="True iff a flip point was found within this lever's search bound.")
    structurally_hopeless: bool = Field(
        ...,
        description="True iff the reachability probe found this guardrail's underlying metric does not move at "
        "all with this lever, for this deal (e.g. interest_rate vs. cap_floor, always; or any lever vs. "
        "spread/cap_floor when market.cap_rate_purchase is overridden).",
    )
    plausible: bool = Field(..., description="True iff the plausibility check raised no flag. Always True when closes_guardrail is False.")
    plausibility_reason: str | None = Field(None, description="Human-readable reason when plausible is False. None otherwise.")
    also_closes: tuple[Literal["dscr", "spread", "irr", "coc", "cf_y1", "cf_all", "cap_floor"], ...] = Field(
        default_factory=tuple,
        description="Other currently-failing guardrails also closed by this same target_value, read off the "
        "same re-run at zero extra engine-call cost.",
    )

    model_config = ConfigDict(frozen=True, extra="ignore")


class CombinationLeverMove(BaseModel):
    """
    One lever's ask inside one multi-lever combination (Mission 5, Half B).

    GD3 (the lever/assumption partition) is load-bearing here: ``lever`` is closed to the four
    ``INVESTOR_LEVERS`` — quantities an investor can act on in the world. No model assumption
    (vacancy/occupancy, rent growth, expense growth, exit cap, cap drift, hold horizon) can ever
    be expressed by this type, so "raise your vacancy assumption" has no field to live in.
    """

    lever: Literal["rent_per_unit_month", "purchase_price", "interest_rate", "annual_opex"] = Field(
        ..., description="Which investor-movable input this move perturbs (GD3: never a model assumption)."
    )
    baseline_value: float = Field(..., description="The lever's current value before the ask, in its own native unit.")
    target_value: float = Field(..., description="baseline_value + delta — the value the ask lands on, confirmed by a real engine re-run.")
    delta: float = Field(..., description="target_value - baseline_value, signed, exactly as shipped (rent increases are +, cuts are -).")
    relative_change: float = Field(
        ..., ge=0, description="abs(delta) / abs(baseline_value) — same field semantics as RecourseLever.relative_change."
    )
    fraction_of_cap: float = Field(
        ...,
        gt=0,
        description="abs(delta) / this lever's own single-ask plausibility cap — the own-axis unit every "
        "combination is judged and compared in (never a cross-lever dollar/bps mix).",
    )

    model_config = ConfigDict(frozen=True, extra="ignore")


class GuardrailMargin(BaseModel):
    """One live guardrail's (bar, value) pair read off a combination's confirming engine re-run."""

    guardrail: Literal["dscr", "spread", "irr", "coc", "cf_y1", "cf_all", "cap_floor"] = Field(
        ..., description="Which live guardrail this margin belongs to."
    )
    bar: float = Field(..., description="The guardrail's own inclusive >= bar, exactly as the thesis tests it.")
    value: float = Field(..., description="The guardrail's metric at the confirmed combination, from THE confirming run and no other.")

    model_config = ConfigDict(frozen=True, extra="ignore")


class RecourseCombination(BaseModel):
    """
    One multi-lever negotiation that closes EVERY live guardrail at once (Mission 5, Half B),
    confirmed by one real, un-differentiated ``run_financial_model`` re-run at the shipped asks.
    AD proposes; the engine confirms — no dual number, gradient, or bisection iterate ever
    reaches this model.
    """

    moves: tuple[CombinationLeverMove, ...] = Field(
        ..., min_length=2, description="The per-lever asks, >= 2 of them, in the fixed _LEVER_ORDER."
    )
    closes_all_live_guardrails: bool = Field(
        ...,
        description="Always True for a shipped combination — the confirming re-run checked ALL live guardrails, not only the failing ones.",
    )
    confirmed_margins: tuple[GuardrailMargin, ...] = Field(
        ..., description="(guardrail, bar, value) for every live guardrail, read off the confirming run, in the fixed guardrail order."
    )
    rounded: bool = Field(
        ...,
        description="True when the asks are the human-facing rounded-away-from-zero values; False only on the "
        "fallback path where the exact bisection crossing shipped instead (Mission 4's own fallback rule).",
    )
    total_fraction_of_caps: float = Field(
        ...,
        gt=0,
        description="Sum of moves[].fraction_of_cap — the combination's total ask in units of maxed-out single "
        "asks (the R3 budget unit, and the 'cheapest total negotiation' comparison unit).",
    )

    model_config = ConfigDict(frozen=True, extra="ignore")


class RejectedCombination(BaseModel):
    """
    The one gate-rejected exemplar shipped ONLY on an honest null (PD.2 call 4): the reason is
    adjacent and inseparable — this model cannot exist without it. Its combination went through
    the same confirm-by-rerun as a shipped one; nothing unconfirmed ever ships.
    """

    combination: RecourseCombination = Field(
        ..., description="The rejected-but-engine-confirmed combination (it DOES close the guardrails)."
    )
    reason: str = Field(..., min_length=1, description="Why the plausibility gate rejected it — names the numbers and the bound.")

    model_config = ConfigDict(frozen=True, extra="ignore")


class CombinationAnalysis(BaseModel):
    """
    The multi-lever recourse section (Mission 5, Half B) — additive beside Mission 4's
    single-lever menu, never replacing it (the investor may be able to act on one lever or many).

    THREE OUTCOMES, NEVER TWO (the mission's honesty core): ``found`` — at least one plausible
    combination, confirmed by a real engine re-run; ``proven_null`` — the search completed and no
    feasible, plausible combination exists; ``undetermined`` — the per-subset probe budget
    (``max_iter``) was exhausted before the search completed: we stopped looking, which is NOT
    evidence that nothing exists. An UNDETERMINED must never be rendered as a null.
    """

    attempted: bool = Field(
        ..., description="False iff there was nothing to search (no failing live guardrail) — outcome is None exactly then."
    )
    outcome: Literal["found", "proven_null", "undetermined"] | None = Field(
        ...,
        description="The three-way search outcome. None iff attempted is False. 'undetermined' means the probe "
        "budget ran out — structurally distinct from 'proven_null', never collapsed into it.",
    )
    combinations: tuple[RecourseCombination, ...] = Field(
        ...,
        description="ALL surviving propositions (at most one per lever subset), in the fixed subset enumeration "
        "order — deliberately NOT ranked (founder call superseding the earlier top-3 ordering).",
    )
    cheapest_total_index: int | None = Field(
        None,
        ge=0,
        description="Index into `combinations` of the smallest total_fraction_of_caps — the 'cheapest total "
        "negotiation' label. An argmin over the set already computed, never a separate search. None iff empty.",
    )
    honest_null: bool = Field(
        ...,
        description="True iff outcome == 'proven_null'. NEVER True on 'undetermined' — reporting an exhausted "
        "budget as a proven null would tell an investor 'nothing can save this deal' when the truth is 'we "
        "ran out of budget'.",
    )
    subsets_searched: int = Field(..., ge=0, description="How many lever subsets (|S| >= 2) were enumerated.")
    subsets_infeasible: int = Field(
        ..., ge=0, description="Subsets whose full-cap corner probe fails a live guardrail — proven empty within the plausibility box."
    )
    subsets_edge_infeasible: int = Field(
        ..., ge=0, description="Subsets whose budget-clipped ray edges do not close the deal — honest counted exit, not a box-wide proof."
    )
    subsets_gate_rejected: int = Field(..., ge=0, description="Subsets whose confirmed crossing the joint plausibility gate rejected.")
    subsets_collapsed: int = Field(
        ...,
        ge=0,
        description="Subsets whose crossing rounded to fewer than two levers (single-lever territory — Mission 4's menu owns it).",
    )
    subsets_exhausted: int = Field(..., ge=0, description="Subsets stopped by max_iter — the counter that drives 'undetermined'.")
    gate_reasons: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Deduped gate-rejection reasons in first-occurrence (deterministic) order — the WHY behind a null.",
    )
    confirm_failed: int = Field(..., ge=0, description="Candidates dropped because their confirming re-run failed (defensive; expected 0).")
    rejected_exemplar: RejectedCombination | None = Field(
        None,
        description="Populated iff honest_null is True and a gate-rejected, rerun-confirmed candidate exists: the "
        "minimal-total-ask rejected candidate with its reason (PD.2 call 4). None otherwise.",
    )
    max_iter: int = Field(..., gt=0, description="The per-subset engine-probe budget that was in force (provenance for 'undetermined').")

    model_config = ConfigDict(frozen=True, extra="ignore")


class RecourseAnalysis(BaseModel):
    """
    Recourse ("what would have to change?") attached to a near-miss ``InvestmentThesis``.
    Additive: lives beside ``InvestmentThesis``, never inside it; ``InvestmentThesis.levers``
    (free-text) is unchanged and is a different, pre-existing concept from the structured levers
    here.
    """

    verdict: str = Field(..., description="The InvestmentThesis.verdict this analysis is attached to (BUY never gets one).")
    failing_guardrails: tuple[Literal["dscr", "spread", "irr", "coc", "cf_y1", "cf_all", "cap_floor"], ...] = Field(
        ...,
        description="Machine names of the guardrails that failed on this forecast, in the fixed lexicographic "
        "order of the live-guardrail table, and for which recourse was attempted.",
    )
    levers: tuple[RecourseLever, ...] = Field(
        ..., description="Every (lever, guardrail) row attempted, including structurally-hopeless and honest-null rows."
    )
    cheapest: RecourseLever | None = Field(None, description="The single lead recommendation. None iff honest_null is True.")
    remaining_after_cheapest: tuple[Literal["dscr", "spread", "irr", "coc", "cf_y1", "cf_all", "cap_floor"], ...] = Field(
        default_factory=tuple,
        description="failing_guardrails minus {cheapest.guardrail} minus cheapest.also_closes. Empty tuple when "
        "cheapest is None or fixes everything.",
    )
    honest_null: bool = Field(
        ...,
        description="True iff no row in `levers` has closes_guardrail=True -- nothing realistic (within the "
        "search bounds) closes any failing guardrail.",
    )
    combinations: CombinationAnalysis | None = Field(
        None,
        description="Mission 5 Half B: the multi-lever combination section, additive beside the single-lever "
        "menu above (flag-don't-remove: both ship). None = feature absent (old payloads validate unchanged).",
    )

    model_config = ConfigDict(frozen=True, extra="ignore")


class AssumptionBreakeven(BaseModel):
    """
    One MODEL ASSUMPTION axis x one currently-PASSING live guardrail: the margin of safety —
    "how wrong can this guess be before the deal fails?" (Mission 5, breakeven analysis).

    GD3 (the lever/assumption partition, ``src/core/finance/partition.py``) is load-bearing on
    this type's SHAPE: a solve to a guardrail boundary along an assumption axis may only ever be
    read as breakeven / margin of safety, never as a recourse ask ("raise your vacancy assumption
    to 8% and the deal passes" is an instruction to fudge an input until the model returns PASS).
    The recourse reading is made inexpressible by construction — no ``target_value``/``delta``/
    ``ask`` field exists here, so the harmful sentence has no field to live in.
    ``partition.assert_breakeven_shape`` is called against this class at import time by
    ``src/market/breakeven.py`` (Ruling 2.4) and pinned by test.

    Every ``breakeven_value`` here was confirmed by one real, un-differentiated
    ``run_financial_model`` re-run at that exact value (the guardrail observed FAILING there),
    never solved algebraically and never read off a search probe.
    """

    guardrail: Literal["dscr", "spread", "irr", "coc", "cf_y1", "cf_all", "cap_floor"] = Field(
        ..., description="Which live, currently-PASSING guardrail this row measures the margin of safety for."
    )
    assumption: Literal["occupancy", "rent_growth", "expense_growth"] = Field(
        ...,
        description="Which model assumption (a quantity the investor GUESSES, never acts on — GD3) this row "
        "erodes. Closed to the three in-scope axes: exit cap / cap drift / hold horizon are BARRED "
        "(partition.BARRED_ASSUMPTION_AXES, GD3 Ruling 3) until a real terminal sale model exists.",
    )
    assumed_value: float = Field(..., description="The value the user assumed for this axis (a fraction, e.g. occupancy 0.95).")
    adverse_direction: Literal["down", "up"] = Field(
        ...,
        description="Which way the guess erodes the deal: 'down' for occupancy and rent_growth (less income "
        "never helps), 'up' for expense_growth (faster-growing costs never help) — engine data-flow facts, "
        "not per-deal estimates.",
    )
    searched_to: float = Field(
        ...,
        description="The adverse domain edge the search actually probed (occupancy: just above 0; rent_growth: "
        "-1.0, where the annual growth factor reaches zero; expense_growth: +1.0, a stated search ceiling). "
        "Every 'never breaks' claim is scoped to [assumed_value, searched_to] — never beyond it.",
    )
    outcome: Literal["breakeven_found", "never_breaks_in_range", "undetermined"] = Field(
        ...,
        description="THREE OUTCOMES, NEVER TWO: 'breakeven_found' — a confirmed flip point exists; "
        "'never_breaks_in_range' — a real engine run at searched_to still passes (a PROVEN, strong result "
        "within the stated range, not a failure to compute); 'undetermined' — the probe budget ran out: we "
        "stopped looking, which is NOT evidence the deal is safe. An undetermined must never render as proven.",
    )
    breakeven_value: float | None = Field(
        None,
        description="The first adverse value at which a full run_financial_model re-run observed this guardrail "
        "FAILING — a fact about fragility, never a suggestion. The true flip lies within `resolution` of it on "
        "the assumed side. None unless outcome == 'breakeven_found'.",
    )
    margin: float | None = Field(
        None,
        ge=0,
        description="abs(breakeven_value - assumed_value) — how much room the guess has before this guardrail "
        "breaks, in the assumption's own units (a fraction). None unless outcome == 'breakeven_found'.",
    )
    metric_at_breakeven: float | None = Field(
        None,
        description="The guardrail's metric read off THE confirming run at breakeven_value (just below `bar`). "
        "None unless outcome == 'breakeven_found'.",
    )
    bar: float = Field(..., description="The guardrail's own inclusive >= bar, exactly as the thesis tests it.")
    metric_moves: bool = Field(
        ...,
        description="False when the guardrail's metric is numerically identical at the adverse edge — this "
        "guardrail is structurally independent of this assumption for this deal (e.g. Year-1 DSCR never reads "
        "rent_growth). Always paired with outcome == 'never_breaks_in_range'.",
    )
    resolution: float = Field(
        ...,
        gt=0,
        description="The bisection tolerance in the assumption's own units: the true flip point lies within "
        "this distance of breakeven_value, on the assumed side. Display rounding of `margin` should be "
        "TOWARD zero (never overstate the room).",
    )
    probes_used: int = Field(
        ..., ge=0, description="Engine runs this row consumed (edge probe + bisection + confirm) — provenance for 'undetermined'."
    )

    model_config = ConfigDict(frozen=True, extra="ignore")


class BreakevenAnalysis(BaseModel):
    """
    The assumption breakeven / margin-of-safety section (Mission 5): for each in-scope model
    assumption and each live, currently-PASSING guardrail, how far the guess can erode before
    that guardrail flips — "clears DSCR until vacancy hits 9.4%; you assumed 5%."

    The mirror image of ``RecourseAnalysis`` under GD3: recourse answers "what would have to
    change" over INVESTOR LEVERS (things the investor acts on); this answers "how much room do I
    have" over MODEL ASSUMPTIONS (things the investor guesses). Currently-FAILING guardrails get
    no row here on purpose — they have no margin of safety (they are already failing at the
    assumed values, which `failing_guardrails` records as a fact), and solving them in the
    FAVORABLE direction would be the forbidden recourse reading in disguise.

    Deliberately NO cross-axis ranking field: margins on different assumption axes are not
    commensurable without a probability model this pipeline does not have, and inventing one
    would violate the deterministic-core line. The report layer renders rows; it does not rank.
    """

    attempted: bool = Field(
        ...,
        description="False iff no live guardrail is currently passing — there is no margin of safety to measure. "
        "Rows is empty exactly then.",
    )
    passing_guardrails: tuple[Literal["dscr", "spread", "irr", "coc", "cf_y1", "cf_all", "cap_floor"], ...] = Field(
        ...,
        description="The live guardrails currently passing at the assumed values, in the fixed guardrail order — "
        "the rows' guardrail universe.",
    )
    failing_guardrails: tuple[Literal["dscr", "spread", "irr", "coc", "cf_y1", "cf_all", "cap_floor"], ...] = Field(
        ...,
        description="The live guardrails already failing at the assumed values, in the fixed guardrail order. "
        "Recorded as a FACT for context (no margin of safety exists for these); recourse — not breakeven — "
        "owns what to do about them.",
    )
    rows: tuple[AssumptionBreakeven, ...] = Field(
        ...,
        description="One row per (assumption, passing guardrail) pair, in fixed (assumption-major, guardrail "
        "order) enumeration order — deterministic, byte-identical for identical inputs.",
    )
    max_iter: int = Field(..., gt=0, description="The per-row engine-probe budget that was in force (provenance for 'undetermined').")

    model_config = ConfigDict(frozen=True, extra="ignore")


# =========================
# Deferred forward references
# =========================
#
# ListingInsights.observations is annotated `list[ObservationProvenance]`, but
# ObservationProvenance is declared further down (next to DetectedLabelModel, which it reuses).
# With `from __future__ import annotations` every annotation is a string, so ListingInsights is
# left with an unresolved reference at class-creation time. Pydantic would resolve it lazily on
# first use; rebuilding explicitly here makes the failure loud at import if the reference ever
# breaks, instead of at whichever call site happens to validate first.
ListingInsights.model_rebuild()
