# src/reports/generator.py
from __future__ import annotations

import os

from src.schemas.models import (
    FinancialForecast,
    InvestmentThesis,
    ListingInsights,
    PurchaseMetrics,
    RefiEvent,
    YearBreakdown,
)


def _fmt_currency(x: float) -> str:
    """
    Format a float as USD-style currency with thousands separators and no trailing .0.

    Example:
        123456.789 -> $123,456.79
        -2000 -> -$2,000.00
    """
    sign = "-" if x < 0 else ""
    return f"{sign}${abs(x):,.2f}"


def _fmt_pct(x: float) -> str:
    """
    Format a fraction as a percentage with two decimals.

    Example:
        0.065 -> 6.50%
    """
    return f"{x * 100:.2f}%"


def _section(title: str) -> str:
    """
    Render a level-2 heading for Markdown sections.
    """
    return f"\n## {title}\n"


# -----------------------
# Env “knobs” for valuations
# -----------------------


def _cap_drift_per_year() -> float:
    """
    Cap-rate drift per year (fraction). Defaults to 0.0.
    Override via env var AIREAL_CAP_DRIFT_BPS (integer basis points per year).
    Example: AIREAL_CAP_DRIFT_BPS=5 -> 0.0005 drift per year.
    """
    try:
        bps = int(os.getenv("AIREAL_CAP_DRIFT_BPS", "0").strip() or "0")
    except Exception:
        bps = 0
    return bps / 10_000.0


def _appreciation_rate() -> float:
    """
    Baseline appreciation rate (fraction). Defaults to 3%/yr.
    Override via AIREAL_APPRECIATION_PCT (e.g., 0.03 for 3%).
    """
    try:
        return float(os.getenv("AIREAL_APPRECIATION_PCT", "0.03"))
    except Exception:
        return 0.03


def _stress_adj() -> float:
    """
    Stress “basis” adjustment subtracted from purchase price before compounding.
    Defaults to 0.0. Override via AIREAL_STRESS_ADJ.
    """
    try:
        return float(os.getenv("AIREAL_STRESS_ADJ", "0.0"))
    except Exception:
        return 0.0


# -----------------------
# Header & top sections
# -----------------------


def _render_header(insights: ListingInsights | None) -> str:
    """
    Render the report header with subject property summary.
    """
    addr = insights.address if insights and insights.address else "Subject Property"

    body = [f"# Investment Analysis – {addr}", ""]

    # Amenities
    if insights and insights.amenities:
        body.append("**Amenities:**")
        for item in insights.amenities:
            body.append(f"- {item}")
    else:
        body.append("**Amenities:** N/A")

    # Notes
    if insights and insights.notes:
        body.append("")
        body.append("**Notes:**")
        for note in insights.notes:
            body.append(f"- {note}")

    # Condition & Defects
    if (insights and insights.condition_tags) or (insights and insights.defects):
        body.append("")
        body.append("**Condition & Defects:**")
        if insights and insights.condition_tags:
            for tag in insights.condition_tags:
                body.append(f"- {tag}")
        if insights and insights.defects:
            for defect in insights.defects:
                body.append(f"- {defect}")

    return "\n".join(body) + "\n"


def _render_purchase_metrics(p: PurchaseMetrics) -> str:
    """
    Render purchase metrics as a bullet list for quick scanning.
    """
    lines = [
        _section("Purchase Metrics"),
        f"- **Cap Rate (Y1):** {_fmt_pct(p.cap_rate)}",
        f"- **Cash-on-Cash (Y1):** {_fmt_pct(p.coc)}",
        f"- **DSCR (Y1):** {p.dscr:.2f}",
        f"- **Annual Debt Service (Y1):** {_fmt_currency(p.annual_debt_service)}",
        f"- **Acquisition Cash Outlay:** {_fmt_currency(p.acquisition_cash)}",
        f"- **Cap Rate – Interest Spread:** {_fmt_pct(p.spread_vs_rate)}",
    ]
    return "\n".join(lines) + "\n"


def _render_methodology() -> str:
    """
    Explain the three parallel valuation forecasts and the refi marker rule.
    Note: purely descriptive; does not depend on extra schema fields.
    """
    lines = [
        _section("Forecasting Methodology"),
        "We produce **three parallel valuation tracks** and mark the first year where the loan-to-value (LTV) "
        "reaches **≤ 80%** (standard refi-ready threshold). All math is deterministic.",
        "",
        "**1) Baseline (Appreciation-Based)**",
        "",
        "Property value grows at an assumed annual appreciation rate $g$:",
        "",
        "$$Value_t = PurchasePrice \\times (1 + g)^t$$",
        "$$LTV_t = \\frac{MortgageBalance_t}{Value_t}$$",
        "$$Equity_t^{(80\\%)} = 0.80 \\times Value_t - MortgageBalance_t$$",
        "",
        "**2) Stress-Test (Rate-Anchored, Conservative)**",
        "",
        "Anchors value growth to a fraction of today's debt rate $r$ (stress stance). If the model uses an adjustment "
        "$Adj$ to reflect effective basis (e.g., subtracting certain upfronts), then:",
        "",
        "$$StressValue_t = (PurchasePrice - Adj) \\times (1 + \\tfrac{r}{3})^t$$",
        "$$LTV_t = \\frac{MortgageBalance_t}{StressValue_t}$$",
        "$$Equity_t^{(80\\%)} = 0.80 \\times StressValue_t - MortgageBalance_t$$",
        "",
        "**3) NOI-Based (Market-Income Approach with Cap Rate Drift)**",
        "",
        "Values are derived from income with a drifting market cap rate:",
        "",
        "$$CapRate_t = CapRate_0 + (drift_{per\\_year} \\times t)$$",
        "$$NOIValue_t = \\frac{NOI_t}{CapRate_t}$$",
        "$$LTV_t = \\frac{MortgageBalance_t}{NOIValue_t}$$",
        "$$Equity_t^{(80\\%)} = 0.80 \\times NOIValue_t - MortgageBalance_t$$",
        "",
        "**Notes**",
        "- *Seasoning*: refi checks typically begin at Year 1 or later (configurable).",
        "- We use end-of-year balances and values for consistency.",
        "- LTV comparisons use a small epsilon to avoid floating-point edge cases.",
        "- This report shows the full horizon; refi years are marked when available.",
    ]
    return "\n".join(lines) + "\n"


# -----------------------
# Pro forma (horizon-aware)
# -----------------------


def _render_year_table(years: list[YearBreakdown]) -> str:
    """
    Render a compact Markdown table of key annual metrics.

    Columns:
      Year | GSI | GOI | Total OPEX | NOI | Debt Service | Cash Flow | DSCR | Ending Balance
    """
    horizon = len(years)
    header = [
        _section(f"{horizon}-Year Pro Forma (Summary)"),
        "| Year | GSI | GOI | Total OPEX | NOI | Debt Service | Cash Flow | DSCR | Ending Balance |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    rows = []
    for y in years:
        rows.append(
            f"| {y.year} "
            f"| {_fmt_currency(y.gsi)} "
            f"| {_fmt_currency(y.goi)} "
            f"| {_fmt_currency(y.total_opex)} "
            f"| {_fmt_currency(y.noi)} "
            f"| {_fmt_currency(y.debt_service)} "
            f"| {_fmt_currency(y.cash_flow)} "
            f"| {y.dscr:.2f} "
            f"| {_fmt_currency(y.ending_balance)} |"
        )
    return "\n".join(header + rows) + "\n"


# -----------------------
# Valuation helpers
# -----------------------


def _estimate_purchase_price_from_y1(forecast: FinancialForecast) -> float:
    """
    We don't carry purchase price in the forecast schema, so infer it from:
      PurchasePrice ≈ NOI_Y1 / CapRate_Y1
    using Year 1 NOI and purchase cap.
    """
    if not forecast.years:
        return 0.0
    y1_noi = forecast.years[0].noi
    cap0 = max(1e-6, forecast.purchase.cap_rate)
    return y1_noi / cap0


def _interest_rate_from_purchase(purchase: PurchaseMetrics) -> float:
    """
    Recover the interest rate used at purchase from: cap = rate + spread  =>  rate = cap - spread.
    """
    rate = purchase.cap_rate - purchase.spread_vs_rate
    return max(0.0, rate)


# -----------------------
# Three separate valuation tables
# -----------------------


def _render_valuation_table_noi(years: list[YearBreakdown], purchase: PurchaseMetrics) -> str:
    """
    NOI-based table with drifting cap:
      - Cap_t = Cap_0 + drift * (t-1)
      - Value_t = NOI_t / Cap_t
      - LTV_t = EndingBalance_t / Value_t
      - Equity80_t = 0.80 * Value_t - EndingBalance_t
    """
    if not years:
        return ""

    base_cap = max(1e-6, float(purchase.cap_rate))
    drift = _cap_drift_per_year()

    header = [
        _section("Valuation – NOI-Based (with Cap Drift)"),
        "| Year | Cap Rate (applied) | Estimated Value | LTV % | Available Equity @80% |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ]
    rows = []
    for y in years:
        cap_t = max(1e-6, base_cap + drift * (y.year - 1))
        est_value = (y.noi / cap_t) if cap_t > 0 else 0.0
        ltv = (y.ending_balance / est_value) if est_value > 0 else 0.0
        avail_eq = 0.80 * est_value - y.ending_balance
        rows.append(f"| {y.year} | {_fmt_pct(cap_t)} | {_fmt_currency(est_value)} | {_fmt_pct(ltv)} | {_fmt_currency(avail_eq)} |")
    return "\n".join(header + rows) + "\n"


def _render_valuation_table_baseline(years: list[YearBreakdown], forecast: FinancialForecast) -> str:
    """
    Baseline appreciation table:
      - PurchasePrice inferred from Y1 NOI / cap.
      - Value_t = PurchasePrice * (1 + g)^t, g from env (default 3%).
      - LTV_t = EndingBalance_t / Value_t
      - Equity80_t = 0.80 * Value_t - EndingBalance_t
    """
    if not years:
        return ""

    g = _appreciation_rate()
    p0 = _estimate_purchase_price_from_y1(forecast)

    header = [
        _section(f"Valuation – Baseline Appreciation (g = {_fmt_pct(g)})"),
        "| Year | Estimated Value | LTV % | Available Equity @80% |",
        "| ---: | ---: | ---: | ---: |",
    ]
    rows = []
    for y in years:
        est_value = p0 * ((1.0 + g) ** y.year)
        ltv = (y.ending_balance / est_value) if est_value > 0 else 0.0
        avail_eq = 0.80 * est_value - y.ending_balance
        rows.append(f"| {y.year} | {_fmt_currency(est_value)} | {_fmt_pct(ltv)} | {_fmt_currency(avail_eq)} |")
    return "\n".join(header + rows) + "\n"


def _render_valuation_table_stress(years: list[YearBreakdown], forecast: FinancialForecast) -> str:
    """
    Stress-test table (rate-anchored):
      - r = interest rate ≈ purchase.cap_rate - spread
      - basis = max(0, PurchasePrice - Adj); Adj via env AIREAL_STRESS_ADJ (default 0)
      - Value_t = basis * (1 + r/3)^t
      - LTV_t = EndingBalance_t / Value_t
      - Equity80_t = 0.80 * Value_t - EndingBalance_t
    """
    if not years:
        return ""

    r = _interest_rate_from_purchase(forecast.purchase)
    growth = 1.0 + (r / 3.0)
    p0 = _estimate_purchase_price_from_y1(forecast)
    basis = max(0.0, p0 - _stress_adj())

    header = [
        _section(f"Valuation – Stress-Test (rate-anchored: r/3 = {_fmt_pct(r / 3 if r else 0.0)}, adj = {_fmt_currency(_stress_adj())})"),
        "| Year | Estimated Value | LTV % | Available Equity @80% |",
        "| ---: | ---: | ---: | ---: |",
    ]
    rows = []
    for y in years:
        est_value = basis * (growth**y.year)
        ltv = (y.ending_balance / est_value) if est_value > 0 else 0.0
        avail_eq = 0.80 * est_value - y.ending_balance
        rows.append(f"| {y.year} | {_fmt_currency(est_value)} | {_fmt_pct(ltv)} | {_fmt_currency(avail_eq)} |")
    return "\n".join(header + rows) + "\n"


# -----------------------
# Other sections
# -----------------------


def _render_opex_details(year1: YearBreakdown) -> str:
    """
    Render Year 1 OPEX detail lines for transparency.
    """
    lines = [
        _section("Operating Expenses - Year 1 Detail"),
        f"- Insurance: {_fmt_currency(year1.insurance)}",
        f"- Taxes: {_fmt_currency(year1.taxes)}",
        f"- Utilities: {_fmt_currency(year1.utilities)}",
        f"- Water & Sewer: {_fmt_currency(year1.water_sewer)}",
        f"- Property Management: {_fmt_currency(year1.property_management)}",
        f"- Repairs & Maintenance: {_fmt_currency(year1.repairs_maintenance)}",
        f"- Trash: {_fmt_currency(year1.trash)}",
        f"- Landscaping: {_fmt_currency(year1.landscaping)}",
        f"- Snow Removal: {_fmt_currency(year1.snow_removal)}",
        f"- HOA Fees: {_fmt_currency(year1.hoa_fees)}",
        f"- Reserves: {_fmt_currency(year1.reserves)}",
        f"- Other: {_fmt_currency(year1.other_expenses)}",
        f"- **Total OPEX (Y1):** {_fmt_currency(year1.total_opex)}",
    ]
    return "\n".join(lines) + "\n"


def _render_refi(refi: RefiEvent | None) -> str:
    """
    Render the refinance card if present.
    """
    if not refi:
        return ""
    lines = [
        _section("Refinance Event"),
        f"- **Year:** {refi.year}",
        f"- **Valuation at Refi:** {_fmt_currency(refi.value)}",
        f"- **New Loan:** {_fmt_currency(refi.new_loan)}",
        f"- **Payoff:** {_fmt_currency(refi.payoff)}",
        f"- **Cash-Out:** {_fmt_currency(refi.cash_out)}",
    ]
    return "\n".join(lines) + "\n"


def _render_returns(forecast: FinancialForecast) -> str:
    """
    Render IRR and Equity Multiple summary.
    """
    lines = [
        _section("Returns Summary (10-Year)"),
        f"- **IRR:** {_fmt_pct(forecast.irr_10yr)}",
        f"- **Equity Multiple:** {forecast.equity_multiple_10yr:.2f}x",
    ]
    return "\n".join(lines) + "\n"


def _render_warnings(warnings: list[str]) -> str:
    """
    Render guardrail warnings, if any.
    """
    if not warnings:
        return ""
    lines = [_section("Warnings")]
    for w in warnings:
        lines.append(f"- {w}")
    return "\n".join(lines) + "\n"


def _render_thesis(thesis: InvestmentThesis) -> str:
    """
    Render the Chief Strategist's verdict with rationale and levers.
    """
    lines = [
        _section("Investment Thesis"),
        f"- **Verdict:** {thesis.verdict}",
        "- **Rationale:**",
    ]
    for r in thesis.rationale:
        lines.append(f"  - {r}")
    if thesis.levers:
        lines.append("- **Suggested Levers:**")
        for lever in thesis.levers:
            lines.append(f"  - {lever}")
    return "\n".join(lines) + "\n"


# -----------------------
# Orchestration
# -----------------------


def generate_report(
    insights: ListingInsights | None,
    forecast: FinancialForecast,
    thesis: InvestmentThesis | None = None,
    title_override: str | None = None,
) -> str:
    """
    Generate a professional Markdown report that summarizes the investment analysis.

    Sections:
      - Header: property summary (address, amenities, notes)
      - Purchase Metrics: cap rate, CoC, DSCR, debt service, acquisition cash, spread
      - Forecasting Methodology: baseline, stress-test, NOI-based formulas and refi rule
      - Pro Forma (Summary): annual table of GSI, GOI, OPEX, NOI, DS, CF, DSCR, Ending Balance (horizon-aware title)
      - Valuation – Baseline table
      - Valuation – Stress-Test table
      - Valuation – NOI-Based table
      - OPEX Detail (Year 1)
      - Refinance Event (if present)
      - Returns Summary
      - Warnings
    """
    header = _render_header(insights)
    if title_override:
        # Replace the first line heading if a custom title is provided
        header_lines = header.splitlines()
        if header_lines:
            header_lines[0] = f"# {title_override}"
            header = "\n".join(header_lines) + "\n"

    parts = [
        header,
        _render_purchase_metrics(forecast.purchase),
        _render_methodology(),
        _render_thesis(thesis) if thesis else "",
        _render_year_table(forecast.years),
        _render_valuation_table_baseline(forecast.years, forecast),
        _render_valuation_table_stress(forecast.years, forecast),
        _render_valuation_table_noi(forecast.years, forecast.purchase),
        _render_opex_details(forecast.years[0]),
        _render_refi(forecast.refi),
        _render_returns(forecast),
        _render_warnings(forecast.warnings),
    ]
    return "\n".join(part for part in parts if part).strip() + "\n"


def write_report(path: str, insights: ListingInsights | None, forecast: FinancialForecast, thesis: InvestmentThesis | None = None) -> None:
    """
    Convenience helper to write the generated report to disk.
    """
    md = generate_report(insights, forecast, thesis=thesis)
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
