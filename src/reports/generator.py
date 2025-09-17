# src/reports/generator.py
from __future__ import annotations

from typing import List, Optional

from src.schemas.models import (
    ListingInsights,
    FinancialForecast,
    YearBreakdown,
    PurchaseMetrics,
    RefiEvent,
    InvestmentThesis,
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


def _render_header(insights: Optional[ListingInsights]) -> str:
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


def _render_year_table(years: List[YearBreakdown]) -> str:
    """
    Render a compact Markdown table of key annual metrics.

    Columns:
      Year | GSI | GOI | Total OPEX | NOI | Debt Service | Cash Flow | DSCR | Ending Balance
    """
    header = [
        _section("10-Year Pro Forma (Summary)"),
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


def _render_refi(refi: Optional[RefiEvent]) -> str:
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


def _render_warnings(warnings: List[str]) -> str:
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
        f"- **Rationale:**",
    ]
    for r in thesis.rationale:
        lines.append(f"  - {r}")
    if thesis.levers:
        lines.append(f"- **Suggested Levers:**")
        for l in thesis.levers:
            lines.append(f"  - {l}")
    return "\n".join(lines) + "\n"

def generate_report(
    insights: Optional[ListingInsights],
    forecast: FinancialForecast,
    thesis: Optional[InvestmentThesis] = None,
    title_override: Optional[str] = None,
) -> str:
    """
    Generate a professional Markdown report that summarizes the investment analysis.

    Sections:
      - Header: property summary (address, amenities, notes)
      - Purchase Metrics: cap rate, CoC, DSCR, debt service, acquisition cash, spread
      - 10-Year Pro Forma (Summary): annual table of GSI, GOI, OPEX, NOI, DS, CF, DSCR, Ending Balance
      - OPEX Detail (Year 1): line-by-line expense transparency
      - Refinance Event: valuation, new loan, payoff, cash-out (if present)
      - Returns Summary: IRR and Equity Multiple
      - Warnings: underwriting guardrails

    Args:
        insights: ListingInsights or None if not available.
        forecast: FinancialForecast produced by the financial engine.
        title_override: Optional heading to replace the default header title.

    Returns:
        Markdown string suitable for writing to investment_analysis.md.
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
        _render_thesis(thesis) if thesis else "",
        _render_year_table(forecast.years),
        _render_opex_details(forecast.years[0]),
        _render_refi(forecast.refi),
        _render_returns(forecast),
        _render_warnings(forecast.warnings),
    ]
    return "\n".join(part for part in parts if part).strip() + "\n"


def write_report(path: str, insights: Optional[ListingInsights], forecast: FinancialForecast, thesis: Optional[InvestmentThesis] = None) -> None:
    """
    Convenience helper to write the generated report to disk.
    """
    md = generate_report(insights, forecast, thesis=thesis)
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
