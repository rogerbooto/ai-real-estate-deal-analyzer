# src/schemas/models.py

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# =========================
# Core inputs
# =========================


class FinancingTerms(BaseModel):
    """
    Acquisition and loan parameters. All money amounts are assumed to use the same currency.
    """

    purchase_price: float = Field(..., description="Total contract price for the property (currency units).")
    closing_costs: float = Field(
        0.0, description="One-time buyer costs at closing (title, fees, transfer taxes). Added to initial cash outlay."
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


# -------------------------
# Per-unit income model
# -------------------------


class UnitIncome(BaseModel):
    """One unit's monthly revenue."""

    rent_month: float = Field(..., description="Monthly rent for this unit at Year 1 start (pre-growth).")
    other_income_month: float = Field(0.0, description="Other monthly income attributable to this unit (parking, storage, laundry).")


class IncomeModel(BaseModel):
    """
    Revenue model with heterogeneous unit rents.
    - 'units' length defines total unit count.
    - Rents and other income are MONTHLY inputs; the model annualizes internally.
    - occupancy and bad_debt_factor reduce GSI to GOI.
    """

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

    do_refi: bool = Field(True, description="Whether to model a refinance event.")
    year_to_refi: int = Field(5, description="Refinance occurs at the END of this year (e.g., 5 = after Year 5 cash flows).")
    refi_ltv: float = Field(0.75, ge=0, le=1, description="Loan-to-Value used at refi to size the new loan.")
    exit_cap_rate: float | None = Field(
        None,
        description="Cap rate used to value the asset at refi. If None, falls back to market_cap_rate or heuristic.",
    )
    market_cap_rate: float | None = Field(
        None, description="Market cap rate reference; also used for purchase if cap_rate_purchase is not provided."
    )


class MarketAssumptions(BaseModel):
    """Market / risk guardrails used for purchase metrics and strategist rules."""

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

    financing: FinancingTerms = Field(
        ..., description="Purchase and loan terms (price, down payment, rate, amortization, IO, mortgage insurance)."
    )
    opex: OperatingExpenses = Field(..., description="Year 1 operating expenses with annual growth.")
    income: IncomeModel = Field(..., description="Revenue model (per-unit monthly inputs; annualized internally).")
    refi: RefinancePlan = Field(default_factory=RefinancePlan, description="Refinance plan. Enabled by default; configurable.")
    market: MarketAssumptions = Field(default_factory=MarketAssumptions, description="Market guardrails and cap-rate assumptions.")
    capex_reserve_upfront: float = Field(
        0.0, description="One-time upfront CapEx/reserves added to initial cash outlay (not recurring OPEX)."
    )


# =========================
# Listing insights
# =========================


class ListingInsights(BaseModel):
    """Signals extracted from listing text and photos. Used by Strategist and to adjust OPEX/CapEx if desired."""

    address: str | None = Field(None, description="Human-readable address or short identifier.")
    amenities: list[str] = Field(default_factory=list, description="Recognized amenities (e.g., 'in-unit laundry', 'parking').")
    condition_tags: list[str] = Field(default_factory=list, description="Condition features (e.g., 'renovated kitchen', 'old roof').")
    defects: list[str] = Field(default_factory=list, description="Potential issues (e.g., 'water stain', 'mold', 'foundation crack').")
    notes: list[str] = Field(default_factory=list, description="Free-form additional observations.")


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

    verdict: str = Field(..., description='One of: "BUY", "CONDITIONAL", or "PASS".')
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
    turnover_cost: float = Field(..., ge=0, description="Average turnover cost for this unit type.")
    str_multiplier: float | None = Field(None, ge=0, description="Optional STR uplift (multiplier) relative to LTR baseline.")

    model_config = ConfigDict(frozen=True, extra="ignore")

    def summary(self) -> str:
        base = (
            f"[RegionalIncomeTable] {self.region} | {self.bedrooms}BR | "
            f"P25: ${self.p25_rent:,.0f}, Median: ${self.median_rent:,.0f}, "
            f"P75: ${self.p75_rent:,.0f} | Turnover: ${self.turnover_cost:,.0f}"
        )
        if self.str_multiplier is not None:
            base += f" | STRx: {self.str_multiplier:.2f}"
        return base

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
    price: float | None = Field(default=None, ge=0, description="Monthly rent or list price; currency-agnostic float.")
    address: str | None = None

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

    def summary(self) -> str:
        bits: list[str] = []
        if self.title:
            bits.append(self.title)
        if self.price is not None:
            bits.append(f"price={self.price:,.0f}")
        if self.bedrooms is not None:
            bits.append(f"{self.bedrooms} bd")
        if self.bathrooms is not None:
            bits.append(f"{self.bathrooms} ba")
        if self.sqft is not None:
            bits.append(f"{self.sqft} sqft")
        if self.address:
            bits.append(self.address)
        if self.parking is not None:
            bits.append(f"parking={'Y' if self.parking else 'N'}")
        if self.laundry:
            bits.append(f"laundry={self.laundry}")
        return " | ".join(bits) if bits else "ListingNormalized: (no key facts)"


class PhotoInsights(BaseModel):
    """Deterministic CV-derived insights from a folder of photos."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    room_counts: dict[str, int] = Field(default_factory=dict, description="Counts per room type (kitchen, bath, etc.).")
    amenities: dict[str, bool] = Field(default_factory=dict, description="Amenity presence flags.")
    quality_flags: dict[str, float] = Field(default_factory=dict, description="Quality scores in [0,1].")
    provider: str = Field(..., description="CV provider name.")
    version: str = Field(..., description="Provider/model version string.")

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
    postal_code: str | None = Field(
        None,
        description="Canonicalized postal/ZIP code if detected (e.g., 'H2X 1Y4', '02139', 'SW1A 1AA', '1234 AB').",
    )
    country_hint: Literal["CA", "US", "UK", "NL", "EU"] | None = Field(
        None,
        description="Heuristic hint based on the postal pattern (Canada/US/UK/NL or generic EU 5-digit).",
    )
