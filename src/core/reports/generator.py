# src/reports/generator.py

from __future__ import annotations

import os
from pathlib import Path

from src.schemas.models import (
    FinancialForecast,
    InvestmentThesis,
    ListingInsights,
    MediaInsights,
    PurchaseMetrics,
    RefiEvent,
    RunProvenance,
    ScenarioAnalysis,
    ScenarioMetricBand,
    ScenarioOutcome,
    YearBreakdown,
)

from .report_models import MediaReport


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


def _fmt_delta_pct(x: float) -> str:
    """
    Format a delta fraction as a signed percentage with two decimals.

    Explicit sign so a delta (Δ) is never confused with an applied level.
    Reuses the existing 2dp percent convention; 0.0 renders as "0.00%".

    Example:
        0.02 -> +2.00%
        -0.02 -> -2.00%
        0.0  -> 0.00%
    """
    return f"{'+' if x > 0 else ''}{x * 100:.2f}%"


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
    # address → inferred title → generic. The title fallback keeps a report identifiable when the
    # listing's street line has no street type (e.g. "36 Kelly") and no address could be parsed.
    addr = "Subject Property"
    if insights:
        addr = insights.address or insights.title or addr

    body = [f"# Investment Analysis – {addr}", ""]

    # Stated facts from the listing copy. Rendered as a single line so a listing that states
    # nothing adds nothing — these are the seller's claims, not computed figures, and every
    # money number in the sections below comes from the finance engine instead.
    if insights:
        facts: list[str] = []
        if insights.price is not None:
            facts.append(f"List price {_fmt_currency(insights.price)}")
        if insights.bedrooms is not None or insights.bathrooms is not None:
            beds = f"{insights.bedrooms:g}" if insights.bedrooms is not None else "?"
            baths = f"{insights.bathrooms:g}" if insights.bathrooms is not None else "?"
            facts.append(f"{beds} bd / {baths} ba")
        if insights.sqft is not None:
            facts.append(f"{insights.sqft:,} sq ft")
            if insights.price is not None and insights.sqft > 0:
                facts.append(_glossary_link("ppsf", f"{_fmt_currency(insights.price / insights.sqft)}/sq ft"))
        if insights.year_built is not None:
            facts.append(f"built {insights.year_built}")
        if facts:
            body.append(f"**As listed:** {' · '.join(facts)}")
            body.append("")

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
        f"- **{_glossary_link('cap', 'Cap Rate')} (Y1):** {_fmt_pct(p.cap_rate)}",
        f"- **{_glossary_link('coc', 'Cash-on-Cash')} (Y1):** {_fmt_pct(p.coc)}",
        f"- **{_glossary_link('dscr', 'DSCR')} (Y1):** {p.dscr:.2f}",
        f"- **Annual {_glossary_link('ds', 'Debt Service')} (Y1):** {_fmt_currency(p.annual_debt_service)}",
        f"- **{_glossary_link('acq', 'Acquisition Cash Outlay')}:** {_fmt_currency(p.acquisition_cash)}",
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
# Media section
# -----------------------


def _render_media_overview(mi: MediaInsights | None) -> str:
    """
    Render a concise summary of downloaded media and derived analytics.
    """
    if not mi:
        return ""

    lines: list[str] = [
        _section("Media Overview"),
        f"- **Total Assets:** {mi.total_assets} &nbsp;&nbsp;"
        f"(images: {mi.image_count}, videos: {mi.video_count}, docs: {mi.document_count}, other: {mi.other_count})",
        # Show both a human-friendly number and the raw integer to satisfy tests.
        f"- **Total Size:** {mi.bytes_total:,} B ({mi.bytes_total} bytes)",
    ]

    if mi.image_count > 0:
        dims = []
        if mi.min_width is not None and mi.max_width is not None:
            dims.append(f"width {int(mi.min_width)}–{int(mi.max_width)}")
        if mi.min_height is not None and mi.max_height is not None:
            dims.append(f"height {int(mi.min_height)}–{int(mi.max_height)}")
        if mi.avg_width is not None and mi.avg_height is not None:
            dims.append(f"avg ≈ {mi.avg_width:.0f}×{mi.avg_height:.0f}")
        if dims:
            lines.append(f"- **Image Dimensions:** {', '.join(dims)}")
        lines.append(f"- **Orientation:** landscape {mi.landscape_count}, portrait {mi.portrait_count}, square {mi.square_count}")

    # Duplicates / near-duplicates
    dup_exact = len(mi.duplicate_hashes)
    dup_clusters = len(mi.duplicates)
    if dup_exact or dup_clusters:
        bits = []
        if dup_exact:
            bits.append(f"{dup_exact} exact")
        if dup_clusters:
            bits.append(f"{dup_clusters} similar clusters")
        lines.append(f"- **Duplicates:** {', '.join(bits)}")

    # Hero
    if mi.hero_sha256:
        lines.append(f"- **Hero Image:** `{mi.hero_sha256}`")

    # Palette (prefer hero’s palette if present)
    palette_samples: list[str] = []
    if mi.palettes:
        if mi.hero_sha256 and mi.hero_sha256 in mi.palettes:
            palette_samples = mi.palettes[mi.hero_sha256][:5]
        else:
            # take the first palette available
            first_key = next(iter(mi.palettes.keys()))
            palette_samples = mi.palettes[first_key][:5]
    if palette_samples:
        swatches = " ".join(f"`{hx}`" for hx in palette_samples)
        lines.append(f"- **Color Palette:** {swatches}")

    # Warnings
    if mi.warnings:
        lines.append("- **Media Warnings:**")
        for w in mi.warnings[:8]:  # keep tidy
            lines.append(f"  - {w}")
        if len(mi.warnings) > 8:
            lines.append(f"  - (+{len(mi.warnings) - 8} more)")

    return "\n".join(lines) + "\n"


# -----------------------
# Pro forma (horizon-aware)
# -----------------------


#: Glossary entries: (anchor id, term, expansion, definition-as-implemented).
#
# Each definition states what THIS engine computes, not the textbook general case — the two
# diverge (see the amortization note), and a reader reconciling a number against the tables
# needs the implemented formula. Keep in sync with src/core/finance/engine.py.
_GLOSSARY: tuple[tuple[str, str, str, str], ...] = (
    (
        "gsi",
        "GSI",
        "Gross Scheduled Income",
        "Annualized rent plus other income for every unit at full occupancy, before any vacancy or collection loss.",
    ),
    (
        "goi",
        "GOI",
        "Gross Operating Income",
        "GSI after economic vacancy and bad debt: `GOI = GSI × occupancy × bad_debt_factor`.",
    ),
    (
        "opex",
        "OPEX",
        "Operating Expenses",
        "The sum of all itemized annual operating costs. Excludes debt service, income tax, and capital expenditure.",
    ),
    ("noi", "NOI", "Net Operating Income", "`NOI = GOI − OPEX`. The property's income before financing — the basis for cap rate and DSCR."),
    (
        "ds",
        "Debt Service",
        "Annual principal + interest",
        "Annual mortgage payment. Computed on **annual** periods (`payment = r × P ÷ (1 − (1+r)^−n)`, r annual, n in years), "
        "which runs slightly above a real monthly-pay loan of the same rate and term.",
    ),
    (
        "dscr",
        "DSCR",
        "Debt Service Coverage Ratio",
        "`DSCR = NOI ÷ Debt Service`. Below 1.00 the property does not cover its own mortgage from operations.",
    ),
    (
        "cap",
        "Cap Rate",
        "Capitalization Rate",
        "`Cap Rate = NOI (Year 1) ÷ purchase price`, unless a cap rate is supplied explicitly in the inputs.",
    ),
    (
        "coc",
        "CoC",
        "Cash-on-Cash Return",
        "`CoC = Year 1 cash flow ÷ acquisition cash outlay`. Unlike cap rate, it is net of financing.",
    ),
    (
        "acq",
        "Acquisition Cash Outlay",
        "Total cash to close",
        "`down payment + closing costs + upfront CapEx reserve + mortgage insurance premium` "
        "(the premium applies only when the down payment is below 20%).",
    ),
    (
        "ltv",
        "LTV",
        "Loan-to-Value",
        "`LTV = mortgage balance ÷ estimated value`. The 80% threshold is the conventional refinance-ready mark.",
    ),
    (
        "irr",
        "IRR",
        "Internal Rate of Return",
        "The discount rate at which the projected cash flows net to zero. The series is the acquisition cash outlay "
        "(negative), each year's cash flow, any refinance cash-out, and terminal equity in the final year.",
    ),
    (
        "em",
        "Equity Multiple",
        "Total return multiple",
        "`sum of all cash returned ÷ acquisition cash outlay`, including terminal equity. Undiscounted — unlike IRR it ignores timing.",
    ),
    (
        "te",
        "Terminal Equity",
        "Modeled exit proceeds",
        "`max(0, 0.80 × final-year value − mortgage balance)`. A proxy for sale proceeds to the owner; no sale costs are modeled.",
    ),
    ("io", "IO", "Interest-Only", "A front period during which payments cover interest only and the balance does not amortize."),
    (
        "ppsf",
        "$/sq ft",
        "Price per square foot",
        "List price ÷ stated finished area. Taken from the listing copy, not computed by the engine.",
    ),
)


def _glossary_link(anchor: str, text: str) -> str:
    """Link a term to its glossary entry. Anchors are explicit so links survive PDF export."""
    return f"[{text}](#g-{anchor})"


def _render_provenance(pipeline: RunProvenance | None) -> str:
    """
    Record the settings that shaped the numbers above.

    Closes a real reproducibility gap: ``.env`` is gitignored and VS Code auto-loads it, so two
    runs of the same command on the same inputs could disagree with nothing in either report
    explaining why. A reader comparing two reports can now diff this block first.

    The three valuation knobs are read from the SAME accessors that produced the valuation
    tables, so this block cannot drift out of sync with the figures it describes. Everything the
    generator cannot observe for itself arrives via ``pipeline``.
    """
    drift_bps = round(_cap_drift_per_year() * 10_000)
    rows: list[tuple[str, str, str]] = [
        ("Cap-rate drift", f"{drift_bps} bps/yr", "AIREAL_CAP_DRIFT_BPS"),
        ("Baseline appreciation", _fmt_pct(_appreciation_rate()), "AIREAL_APPRECIATION_PCT"),
        ("Stress basis adjustment", _fmt_currency(_stress_adj()), "AIREAL_STRESS_ADJ"),
    ]
    if pipeline is not None:
        rows.extend(
            [
                ("Orchestration engine", pipeline.engine, "AIREAL_ENGINE / --engine"),
                ("Market Scenarios", "on" if pipeline.scenarios_enabled else "off", "AIREAL_SCENARIOS / --scenarios"),
                ("AI photo tagging", "on" if pipeline.vision_enabled else "off", "AIREAL_USE_VISION"),
                ("Inputs file", pipeline.config_path or "(hardcoded demo inputs)", "--config"),
            ]
        )

    lines = [
        _section("Appendix — Run Provenance"),
        "The settings this report was generated under. Environment variables silently change the "
        "figures above, so reproducing a report means matching this table — see `.env.example` for "
        "the defaults.",
        "",
        "| Setting | Value | Source |",
        "| :--- | :--- | :--- |",
    ]
    lines.extend(f"| {label} | {value} | `{source}` |" for label, value, source in rows)
    return "\n".join(lines) + "\n"


def _render_glossary() -> str:
    """
    Render the definitions appendix.

    Placed last and always emitted: a reader hitting "DSCR 0.90" needs somewhere to land, and
    an appendix that appears only sometimes is worse than one that is always in the same place.
    """
    lines = [
        _section("Appendix — Definitions"),
        "Every term below is defined **as this engine computes it**. Where a convention differs from the "
        "textbook form, the difference is stated rather than glossed over.",
        "",
        "| Term | Stands for | Definition |",
        "| :--- | :--- | :--- |",
    ]
    for anchor, term, expansion, definition in _GLOSSARY:
        lines.append(f'| <a id="g-{anchor}"></a>**{term}** | {expansion} | {definition} |')
    return "\n".join(lines) + "\n"


def _render_photo_coverage(report: MediaReport | None) -> str:
    """
    Render which rooms the photo set actually documents.

    Complements Media Overview: that section describes the *files* (counts, dimensions,
    duplicates); this one describes what they *show*. Gaps matter to an underwriter — a
    listing with no mechanical-room or basement photo is withholding something.
    """
    if not report:
        return ""

    lines: list[str] = [_section("Photo Coverage")]

    cov = report.coverage
    lines.append(
        f"- **Images:** {cov.images_readable} readable of {cov.images_total} · "
        f"{cov.detections_total} detections · provider `{cov.provider}`"
    )

    if report.room_counts:
        rooms = ", ".join(f"{room} {count}" for room, count in sorted(report.room_counts.items()))
        lines.append(f"- **Rooms Documented:** {rooms}")
    else:
        lines.append("- **Rooms Documented:** none identified")

    detected = sorted(name for name, present in report.amenities.items() if present)
    if detected:
        lines.append(f"- **Amenities Seen in Photos:** {', '.join(detected)}")

    if report.warnings:
        lines.append("- **Coverage Warnings:**")
        for w in report.warnings[:6]:
            lines.append(f"  - {w}")

    return "\n".join(lines) + "\n"


def _render_year_table(years: list[YearBreakdown]) -> str:
    """
    Render a compact Markdown table of key annual metrics.

    Columns:
      Year | GSI | GOI | Total OPEX | NOI | Debt Service | Cash Flow | DSCR | Ending Balance
    """
    horizon = len(years)
    header = [
        _section(f"{horizon}-Year Pro Forma (Summary)"),
        f"| Year | {_glossary_link('gsi', 'GSI')} | {_glossary_link('goi', 'GOI')} "
        f"| Total {_glossary_link('opex', 'OPEX')} | {_glossary_link('noi', 'NOI')} "
        f"| {_glossary_link('ds', 'Debt Service')} | Cash Flow | {_glossary_link('dscr', 'DSCR')} | Ending Balance |",
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
        f"| Year | {_glossary_link('cap', 'Cap Rate')} (applied) | Estimated Value "
        f"| {_glossary_link('ltv', 'LTV')} % | Available {_glossary_link('te', 'Equity')} @80% |",
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
        f"| Year | Estimated Value | {_glossary_link('ltv', 'LTV')} % | Available {_glossary_link('te', 'Equity')} @80% |",
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
        f"| Year | Estimated Value | {_glossary_link('ltv', 'LTV')} % | Available {_glossary_link('te', 'Equity')} @80% |",
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


def _render_year_adjustments(years: list[YearBreakdown]) -> str:
    """
    Render the engine's per-year adjustment notes (``YearBreakdown.notes``) — the traceability
    trail for why the OPEX/income figures above differ from the raw listing inputs (e.g. a
    condition tag adding to reserves, a defect adding to repairs & maintenance, an amenity
    uplifting other income). In practice only Year 1 carries these (the insight modifiers are
    applied once, at the top of the model), but every year is checked so the section stays
    correct if that ever changes.

    Notes render verbatim — they are machine-generated traceability strings, not prose to be
    softened or rewritten. Degrades to "" when no year has notes, so a run with no listing
    insights (or insights that trip no modifier) adds no empty heading to the report.
    """
    by_year = [(y.year, y.notes) for y in years if y.notes]
    if not by_year:
        return ""

    lines = [
        _section("Adjustments Applied"),
        "Notes below explain why a year's OPEX or income differs from the raw inputs — each line "
        "names the condition tag, defect, or amenity that triggered it. These are already reflected "
        "in the figures above; nothing here changes a number, it only explains one.",
        "",
    ]
    for year, notes in by_year:
        for note in notes:
            lines.append(f"- Year {year}: {note}")
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
        f"- **{_glossary_link('irr', 'IRR')}:** {_fmt_pct(forecast.irr_10yr)}",
        f"- **{_glossary_link('em', 'Equity Multiple')}:** {forecast.equity_multiple_10yr:.2f}x",
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
# Market Scenarios (opt-in overlay — Mission 1)
# -----------------------

# FIXED VERBATIM honesty block (Wave 1 note §0 / Wave 2 spec §2, guardian G1). Rendered
# byte-for-byte, no per-run interpolation. Because it is fixed text it never threatens the
# default-off byte-identical guarantee (it only appears when scenarios are ON).
ABOUT_SCENARIOS_BLOCK = (
    "> **About these scenarios.** These are deterministic what-if calculations over your own market and\n"
    "> financing assumptions — the same underwriting math re-run on perturbed copies of your inputs. They\n"
    '> are **not** predictions, forecasts, or live market data. The scenario weights ("priors") are\n'
    "> **heuristic penalty weights**, not calibrated probabilities, so the weighted figures are what-if\n"
    "> quantiles over a rule-based grid — not statistical percentiles of real-world outcomes. Every number\n"
    "> here is exactly reproducible from your inputs and the fixed seed."
)

_SCENARIOS_LEAD_IN = (
    "A what-if overlay on the base underwriting above — the same math re-run on perturbed copies of your "
    "inputs. This is not part of the headline forecast."
)


def _scenario_hyp_key(o: ScenarioOutcome) -> tuple[float, float, float, float, float, bool]:
    """Lexicographic hypothesis key (Wave 1 note §4) used as the deterministic tie-break."""
    h = o.hypothesis
    return (h.rent_delta, h.expense_growth_delta, h.interest_rate_delta, h.cap_rate_delta, h.vacancy_delta, h.str_viability)


def _render_scenario_grid(outcomes: tuple[ScenarioOutcome, ...], n_accepted: int) -> list[str]:
    """Render the two linked top-5-by-prior tables (Wave 2 spec §3)."""
    # Top-5 by prior descending; ties broken by the deterministic lexicographic hypothesis key.
    top = sorted(outcomes, key=lambda o: (-o.hypothesis.prior, _scenario_hyp_key(o)))[:5]

    lines: list[str] = [
        f"**Scenario grid — top 5 by prior weight** _(of {n_accepted} admitted; the bands below summarize all of them)._",
        "_Priors are heuristic penalty weights, not probabilities (see the note above)._",
        "",
        "| # | Prior | Δ Rent growth | Δ Opex growth | Δ Interest rate | Δ Cap rate | Δ Vacancy |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for i, o in enumerate(top, start=1):
        h = o.hypothesis
        lines.append(
            f"| {i} | {_fmt_pct(h.prior)} | {_fmt_delta_pct(h.rent_delta)} | {_fmt_delta_pct(h.expense_growth_delta)} "
            f"| {_fmt_delta_pct(h.interest_rate_delta)} | {_fmt_delta_pct(h.cap_rate_delta)} | {_fmt_delta_pct(h.vacancy_delta)} |"
        )

    lines.append("")
    lines.append(
        "| # | Rent growth | Opex growth | Interest rate | Occupancy | Cap rate (applied) "
        "| DSCR (Y1) | CoC (Y1) | Cash flow (Y1) | IRR (10yr) | Equity × |"
    )
    lines.append("| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for i, o in enumerate(top, start=1):
        cap_applied = _fmt_pct(o.cap_rate_purchase_applied) if o.cap_rate_purchase_applied is not None else "N/A"
        lines.append(
            f"| {i} | {_fmt_pct(o.rent_growth_applied)} | {_fmt_pct(o.expense_growth_applied)} "
            f"| {_fmt_pct(o.interest_rate_applied)} | {_fmt_pct(o.occupancy_applied)} | {cap_applied} "
            f"| {o.dscr_y1:.2f} | {_fmt_pct(o.coc_y1)} | {_fmt_currency(o.cash_flow_y1)} "
            f"| {_fmt_pct(o.irr_10yr)} | {o.equity_multiple_10yr:.2f}x |"
        )
    return lines


def _render_scenario_bands(analysis: ScenarioAnalysis) -> list[str]:
    """Render the prior-weighted bands table (Wave 2 spec §4, label discipline G4)."""
    lines: list[str] = [
        f"**Prior-weighted bands** _(across all {analysis.n_accepted} admitted scenarios; weighted by heuristic prior)._",
        "",
        "| Metric | downside (p25) | median (p50) | mean (expected) | min | max |",
        "| :--- | ---: | ---: | ---: | ---: | ---: |",
    ]

    def _row(label: str, band: ScenarioMetricBand | None, fmt: str) -> str:
        assert band is not None  # only called on the non-empty path
        if fmt == "currency":
            cells = [_fmt_currency(v) for v in (band.p25, band.p50, band.mean, band.min, band.max)]
        elif fmt == "pct":
            cells = [_fmt_pct(v) for v in (band.p25, band.p50, band.mean, band.min, band.max)]
        elif fmt == "mult":
            cells = [f"{v:.2f}x" for v in (band.p25, band.p50, band.mean, band.min, band.max)]
        else:  # ratio
            cells = [f"{v:.2f}" for v in (band.p25, band.p50, band.mean, band.min, band.max)]
        return f"| {label} | " + " | ".join(cells) + " |"

    lines.append(_row("DSCR (Y1)", analysis.dscr, "ratio"))
    lines.append(_row("CoC (Y1)", analysis.coc, "pct"))
    lines.append(_row("Cash flow (Y1)", analysis.cash_flow_y1, "currency"))
    lines.append(_row("IRR (10yr)", analysis.irr_10yr, "pct"))
    lines.append(_row("Equity multiple (10yr)", analysis.equity_multiple_10yr, "mult"))
    return lines


def _render_scenario_caveats(analysis: ScenarioAnalysis) -> list[str]:
    """Render caveats; bullets 1-3 always, IO bullet only when io_years > 0 (Wave 2 spec §5, G3)."""
    lines: list[str] = [
        "**Caveats**",
        "- The bands are weighted by heuristic penalty weights, not probabilities — read them as what-if "
        "quantiles over a rule-based grid, not statistical percentiles.",
        "- IRR (10yr) and the equity multiple are terminal-value / cap-rate dominated. The scenario base "
        "reproduces the headline purchase cap exactly, so these two move only with the modeled cap-rate "
        "delta — treat their spread as cap sensitivity, not a forecast.",
        "- An interest-rate delta is applied to both the acquisition loan and the year-5 refinance loan and "
        "holds for the full hold period — a rate shock here is a permanent, whole-deal shock, not a temporary one.",
    ]
    if analysis.io_years > 0:
        lines.append(
            "- One or more scenarios use an interest-only period, so their Year-1 DSCR, CoC, and cash flow are "
            "interest-only-flattered and understate the debt load once amortization begins. Read the Year-1 "
            "downside as optimistic for those scenarios."
        )
    return lines


def _render_market_scenarios(analysis: ScenarioAnalysis) -> str:
    """
    Render the opt-in "Market Scenarios" overlay section (Wave 2 spec).

    A structurally separate what-if section rendered last. Emitted ONLY when a
    ``ScenarioAnalysis`` is supplied; with scenarios OFF this is never called and the
    report is byte-identical to today (guardian G2).
    """
    snapshot = analysis.snapshot
    lines: list[str] = [
        _section("Market Scenarios"),
        _SCENARIOS_LEAD_IN,
        "",
        ABOUT_SCENARIOS_BLOCK,
        "",
        f"_Region: {snapshot.region} · seed {analysis.seed} (provenance only — the grid is a fixed "
        f"deterministic set, not randomized by the seed) · {analysis.n_accepted} of {analysis.n_generated} "
        f"scenarios admitted under guardrails._",
        "",
    ]

    if analysis.n_accepted == 0:
        lines.append("**No admissible scenarios under the current guardrails.**")
        lines.append("")
        lines.append(f"None of the {analysis.n_generated} generated hypotheses passed the rejector, so there are no prior-weighted")
        lines.append("outcomes to report. No numbers are fabricated.")
        if analysis.notes:
            lines.append("")
            lines.append(analysis.notes)
        return "\n".join(lines) + "\n"

    lines.extend(_render_scenario_grid(analysis.outcomes, analysis.n_accepted))
    lines.append("")
    lines.extend(_render_scenario_bands(analysis))
    lines.append("")
    lines.extend(_render_scenario_caveats(analysis))

    # str_viability — narrative flag only (Wave 2 spec §6, G4). Omitted from numeric tables above;
    # surfaced here only when at least one admitted scenario flags it, with the literal label.
    k = sum(1 for o in analysis.outcomes if o.hypothesis.str_viability)
    if k > 0:
        lines.append("")
        lines.append("**Narrative flags (not modeled)**")
        lines.append(
            f"- STR viability flagged in {k} of {analysis.n_accepted} admitted scenarios — not modeled — "
            "narrative flag only. It did not move any number above."
        )

    return "\n".join(lines) + "\n"


# -----------------------
# Orchestration
# -----------------------


def generate_report(
    insights: ListingInsights | None,
    forecast: FinancialForecast,
    thesis: InvestmentThesis | None = None,
    title_override: str | None = None,
    *,
    media_insights: MediaInsights | None = None,
    media_report: MediaReport | None = None,
    provenance: RunProvenance | None = None,
    scenarios: ScenarioAnalysis | None = None,
) -> str:
    """
    Generate a professional Markdown report that summarizes the investment analysis.

    Sections:
      - Header: property summary (address, amenities, notes)
      - Purchase Metrics: cap rate, CoC, DSCR, debt service, acquisition cash, spread
      - Forecasting Methodology: baseline, stress-test, NOI-based formulas and refi rule
      - Media Overview (if available)
      - Photo Coverage (if a MediaReport is supplied)
      - Pro Forma (Summary): annual table of GSI, GOI, OPEX, NOI, DS, CF, DSCR, Ending Balance (horizon-aware title)
      - Valuation – Baseline table
      - Valuation – Stress-Test table
      - Valuation – NOI-Based table
      - OPEX Detail (Year 1)
      - Adjustments Applied (if any year carries YearBreakdown.notes — usually Year 1 only)
      - Refinance Event (if present)
      - Returns Summary
      - Warnings
      - Market Scenarios (opt-in overlay; only when ``scenarios`` is supplied)
      - Appendix — Run Provenance (always emitted)
      - Appendix — Definitions (always emitted, last)
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
        _render_media_overview(media_insights),
        _render_photo_coverage(media_report),
        _render_thesis(thesis) if thesis else "",
        _render_year_table(forecast.years),
        _render_valuation_table_baseline(forecast.years, forecast),
        _render_valuation_table_stress(forecast.years, forecast),
        _render_valuation_table_noi(forecast.years, forecast.purchase),
        _render_opex_details(forecast.years[0]),
        _render_year_adjustments(forecast.years),
        _render_refi(forecast.refi),
        _render_returns(forecast),
        _render_warnings(forecast.warnings),
    ]
    if scenarios is not None:
        parts.append(_render_market_scenarios(scenarios))

    # Appendices last: reference material a reader returns to, not something between them and
    # the numbers. Provenance precedes definitions so 'why do these differ?' is answered first.
    parts.append(_render_provenance(provenance))
    parts.append(_render_glossary())
    return "\n".join(part for part in parts if part).strip() + "\n"


def write_report(
    path: str | Path,
    insights: ListingInsights | None,
    forecast: FinancialForecast,
    thesis: InvestmentThesis | None = None,
    *,
    media_insights: MediaInsights | None = None,
    media_report: MediaReport | None = None,
    provenance: RunProvenance | None = None,
    scenarios: ScenarioAnalysis | None = None,
) -> None:
    """
    Convenience helper to write the generated report to disk.
    Ensures parent directories exist.
    """
    md = generate_report(
        insights,
        forecast,
        thesis=thesis,
        media_insights=media_insights,
        media_report=media_report,
        provenance=provenance,
        scenarios=scenarios,
    )

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    with p.open("w", encoding="utf-8") as f:
        f.write(md)
