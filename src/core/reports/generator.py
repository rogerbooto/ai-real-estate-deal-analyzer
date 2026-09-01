# src/reports/generator.py

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any, cast, get_args

from src.agents.chief_strategist import MIN_COC_Y1, MIN_DSCR_Y1, MIN_IRR_10YR, spread_target_for
from src.core.cv.amenities_defects import ProviderName, provider_covers
from src.core.cv.ontology import AMENITIES_DEFECTS_V1
from src.core.finance.engine import EQUITY_LTV
from src.schemas.labels import AmenityLabel, ParkingType
from src.schemas.models import (
    AssumptionBreakeven,
    BreakevenAnalysis,
    CombinationAnalysis,
    CombinationLeverMove,
    FinancialForecast,
    InvestmentThesis,
    ListingInsights,
    MarketAssumptions,
    MediaInsights,
    PurchaseMetrics,
    RecourseAnalysis,
    RecourseCombination,
    RecourseLever,
    RefiEvent,
    RejectedCombination,
    RunProvenance,
    ScenarioAnalysis,
    ScenarioMetricBand,
    ScenarioOutcome,
    YearBreakdown,
)

from .baseline import BaselineOutlook
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


def _fmt_delta_currency(x: float) -> str:
    """
    Format a currency delta with an explicit sign, at the report's 2dp dollar precision.

    A delta that rounds to zero at that precision renders unsigned ("$0.00"), so a float
    artifact never shows up as a misleading "-$0.00".

    Example:
        500.0 -> +$500.00
        -500.0 -> -$500.00
        -0.0001 -> $0.00
    """
    body = f"${abs(x):,.2f}"
    if round(x, 2) == 0:
        return body
    return f"{'+' if x > 0 else '-'}{body}"


def _fmt_delta_ratio(x: float) -> str:
    """
    Format a bare-ratio delta (DSCR, equity multiple) with an explicit sign at 2dp.

    Same zero rule as :func:`_fmt_delta_currency`.

    Example:
        -0.02 -> -0.02
        0.0   -> 0.00
    """
    body = f"{abs(x):.2f}"
    if round(x, 2) == 0:
        return body
    return f"{'+' if x > 0 else '-'}{body}"


def _fmt_delta_rate(x: float) -> str:
    """
    Format a rate delta (cap rate, CoC) as a signed percentage at 2dp.

    Wraps :func:`_fmt_delta_pct` with the same round-to-zero rule as the other delta
    formatters: a delta smaller than half of the last displayed digit is snapped to exact
    zero first, so it renders "0.00%" rather than "-0.00%".
    """
    return _fmt_delta_pct(0.0 if round(x * 100, 2) == 0 else x)


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
        "$$Equity_t^{(80\\%)} = \\max(0,\\ 0.80 \\times Value_t - MortgageBalance_t)$$",
        "",
        "**2) Stress-Test (Rate-Anchored, Conservative)**",
        "",
        "Anchors value growth to a fraction of today's debt rate $r$ (stress stance). If the model uses an adjustment "
        "$Adj$ to reflect effective basis (e.g., subtracting certain upfronts), then:",
        "",
        "$$StressValue_t = (PurchasePrice - Adj) \\times (1 + \\tfrac{r}{3})^t$$",
        "$$LTV_t = \\frac{MortgageBalance_t}{StressValue_t}$$",
        "$$Equity_t^{(80\\%)} = \\max(0,\\ 0.80 \\times StressValue_t - MortgageBalance_t)$$",
        "",
        "**3) NOI-Based (Market-Income Approach with Cap Rate Drift)**",
        "",
        "Values are derived from income with a drifting market cap rate:",
        "",
        "$$CapRate_t = CapRate_0 + (drift_{per\\_year} \\times t)$$",
        "$$NOIValue_t = \\frac{NOI_t}{CapRate_t}$$",
        "$$LTV_t = \\frac{MortgageBalance_t}{NOIValue_t}$$",
        "$$Equity_t^{(80\\%)} = \\max(0,\\ 0.80 \\times NOIValue_t - MortgageBalance_t)$$",
        "",
        "**Notes**",
        "- *Seasoning*: refi checks typically begin at Year 1 or later (configurable).",
        "- We use end-of-year balances and values for consistency.",
        "- LTV comparisons use a small epsilon to avoid floating-point edge cases.",
        "- This report shows the full horizon; refi years are marked when available.",
        "- Track 3 is the engine's own valuation, read from the forecast. Tracks 1 and 2 are "
        "report-side sensitivities computed from the same forecast figures.",
        "- *Available Equity @80%* is floored at $0.00 — below the 80% mark there is nothing to "
        "draw. The LTV column beside it shows how far above the mark the loan still sits.",
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

    # Per-image quality metrics, summarized as a range per metric.
    #
    # Rendered as ranges rather than one row per image: the map is keyed by sha256 and holds a
    # metric dict per image, so a 40-photo listing would add 40 unreadable rows of hashes. What
    # an underwriter acts on is whether the SET is sharp and well-lit — a dark or soft range is
    # the signal that the photos may be hiding condition. Metric names are read off the data, so
    # a metric added upstream flows through without touching this function.
    if mi.image_quality:
        metrics: dict[str, list[float]] = {}
        for per_image in mi.image_quality.values():
            for metric, value in per_image.items():
                metrics.setdefault(metric, []).append(value)
        bits = [f"{metric} {min(values):.2f}–{max(values):.2f}" for metric, values in sorted(metrics.items())]
        if bits:
            lines.append(f"- **Image Quality:** {', '.join(bits)} _(range across {len(mi.image_quality)} images)_")

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


def _applied_cap_drift(years: list[YearBreakdown]) -> float | None:
    """
    The cap-rate drift per year actually applied to the rendered NOI table, or None when that
    table fell back to the env-driven recomputation.

    Read off the engine's own cap path rather than from an input, so the provenance row cannot
    claim a drift the table did not apply. A single-year forecast reports 0.0: drift multiplies
    ``(t - 1)``, so no drift can have been applied to the only row on the page.
    """
    if not _forecast_carries_valuation(years):
        return None
    if len(years) < 2:
        return 0.0
    first, second = years[0].cap_rate_applied, years[1].cap_rate_applied
    assert first is not None and second is not None  # narrowed by _forecast_carries_valuation
    return second - first


def _flatten_provenance(prefix: str, value: Any) -> list[tuple[str, str]]:
    """
    Flatten a nested provenance mapping into ``(dotted label, printable value)`` rows.

    Generic on purpose: the CV layer owns the shape of ``MediaReport.provenance`` and adds keys
    to it over time. Hand-picking "interesting" keys here would re-create the drop-a-field-at-
    the-boundary defect this mission exists to close, one curation decision later.
    """
    if isinstance(value, dict):
        rows: list[tuple[str, str]] = []
        for key, sub in value.items():
            rows.extend(_flatten_provenance(f"{prefix}.{key}" if prefix else str(key), sub))
        return rows
    if isinstance(value, list | tuple):
        printable = ", ".join(str(v) for v in value) if value else "(none)"
        return [(prefix, printable)]
    if value is None:
        return [(prefix, "(none)")]
    return [(prefix, str(value))]


def _render_provenance(
    pipeline: RunProvenance | None,
    *,
    market: MarketAssumptions | None = None,
    media_report: MediaReport | None = None,
    applied_cap_drift: float | None = None,
) -> str:
    """
    Record the settings that shaped the numbers above.

    Closes a real reproducibility gap: ``.env`` is gitignored and VS Code auto-loads it, so two
    runs of the same command on the same inputs could disagree with nothing in either report
    explaining why. A reader comparing two reports can now diff this block first.

    The valuation knobs are read from the SAME source that produced the valuation tables — the
    forecast's own cap path when the NOI table renders the engine's track, the env accessors
    when it falls back to recomputing — so this block cannot drift out of sync with the figures
    it describes. Everything the generator cannot observe for itself arrives via ``pipeline``,
    ``market`` and ``media_report``.

    ``market`` carries the underwriting guardrails the verdict was judged against. The cap-rate
    floor in particular decided a rationale line and a DECLINE input, and until Mission 2 it
    appeared nowhere in the document — a reader could not tell a cleared floor from an absent
    one. It is stated here as well as in the thesis because ``deal-report`` can render a report
    with no thesis at all.

    ``media_report``'s three version/provenance fields are recorded here rather than in the
    narrative. They are metadata — but they are metadata about *who made the photo claims*, and
    the Photo Coverage section above prints observations that reach the engine's OPEX/income
    rules. "Provider `cv_v2`" reads like a model; ``provenance.provider_kind`` is what says
    whether it was one, and dropping it while printing its output is precisely the over-claim
    this mission removes.
    """
    if applied_cap_drift is not None:
        drift_value, drift_source = f"{round(applied_cap_drift * 10_000)} bps/yr", "market.cap_rate_drift"
    else:
        drift_value, drift_source = f"{round(_cap_drift_per_year() * 10_000)} bps/yr", "AIREAL_CAP_DRIFT_BPS"
    rows: list[tuple[str, str, str]] = [
        ("Cap-rate drift", drift_value, drift_source),
        ("Baseline appreciation", _fmt_pct(_appreciation_rate()), "AIREAL_APPRECIATION_PCT"),
        ("Stress basis adjustment", _fmt_currency(_stress_adj()), "AIREAL_STRESS_ADJ"),
    ]
    if market is not None:
        rows.extend(
            [
                (
                    "Cap-rate floor",
                    _fmt_pct(market.cap_rate_floor) if market.cap_rate_floor is not None else "(no floor policy set)",
                    "market.cap_rate_floor",
                ),
                ("Cap-rate spread target", _fmt_pct(market.cap_rate_spread_target), "market.cap_rate_spread_target"),
            ]
        )
    if pipeline is not None:
        rows.extend(
            [
                ("Orchestration engine", pipeline.engine, "AIREAL_ENGINE / --engine"),
                ("Market Scenarios", "on" if pipeline.scenarios_enabled else "off", "AIREAL_SCENARIOS / --scenarios"),
                ("AI photo tagging", "on" if pipeline.vision_enabled else "off", "AIREAL_USE_VISION"),
                # Without this row, an --engine crewai + AIREAL_LLM_MODE run where a model authored
                # every observation showed "AI photo tagging: off" as its ONLY AI fact -- under a
                # heading promising this table is enough to reproduce the run.
                ("LLM-authored observations", "on" if pipeline.llm_mode_enabled else "off", "AIREAL_LLM_MODE"),
                ("Inputs file", pipeline.config_path or "(hardcoded demo inputs)", "--config"),
            ]
        )
    if media_report is not None:
        rows.append(("Media report schema", media_report.report_version, "MediaReport.report_version"))
        rows.append(("CV ontology", media_report.ontology_version, "MediaReport.ontology_version"))
        rows.extend(
            (f"Photo pipeline — {label}", value, "MediaReport.provenance")
            for label, value in _flatten_provenance("", media_report.provenance)
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


#: Canonical ontology labels the "Parking (from photos)" line reports on jointly. A "none" is only
#: a real negative finding when at least one of these was something a provider could actually look
#: for -- see :func:`_photo_capability_covers`.
_PARKING_TYPE_LABELS: tuple[str, ...] = (
    AmenityLabel.parking_garage.value,
    AmenityLabel.parking_driveway.value,
    AmenityLabel.street_parking.value,
)

#: `ProviderName`'s member values, read off the type rather than re-typed here so a provider added
#: to the `Literal` later does not silently fall through `_photo_capability_covers`'s runtime check
#: to "unrecognised provider -> treat as nothing looked" without anyone noticing the mismatch.
_KNOWN_PROVIDER_NAMES: frozenset[str] = frozenset(get_args(ProviderName))


def _photo_capability_covers(report: MediaReport, *canonical_labels: str) -> bool:
    """Was the CV provider that produced ``report`` even capable of looking for any of these labels?

    Every negative fact this section states about parking/EV charging is only true because
    something looked. `ParkingSummary.ev_charging` defaults to `False` and `parking_type` defaults
    to `"none"` on a schema built with no detections at all -- and every provider shipped with this
    codebase declares only `{natural_light_high, stainless_appliances}` (plus synonyms), no parking
    or EV-charger label at all (see `core.cv.amenities_defects`'s "Built-in capability
    declarations"). So on every default configuration, printing that default as "no EV charging
    observed" states a sighting nothing was capable of making -- R-6 (the filename-hint rule) run
    in reverse, on an absence instead of a presence. This is the single check both call sites use
    to tell "nothing could look" from "something looked and found none", so the two can never drift
    apart.

    Reads `report.provenance["selected_provider"]` because that -- not `report.coverage.provider`,
    which is the constant `"cv_v2"` report-schema tag -- is the actual CV provider slot
    (`"local"`/`"vision"`/`"llm"`/`"onnx"`) that produced the underlying detections; see
    `core.cv.photo_insights.build_photo_insights`, the sole producer of that key. A missing or
    unrecognised value is treated the same as "nothing looked": conservative, and the same reading
    `provider_capabilities` documents for a provider that declared nothing at all.
    """
    raw_provider = report.provenance.get("selected_provider")
    if not isinstance(raw_provider, str) or raw_provider not in _KNOWN_PROVIDER_NAMES:
        return False
    try:
        return provider_covers(cast(ProviderName, raw_provider), *canonical_labels, ontology=AMENITIES_DEFECTS_V1)
    except ValueError:
        # A NAMED but UNBOUND provider slot. `"onnx"` is a member of `ProviderName`, so it clears
        # the check above, but it has no default registration -- it only exists once a caller runs
        # the documented `register_onnx_provider` path. Rendering a report is a *different process*
        # from producing one, so `deal-report` reading an artifact from an onnx run finds the name
        # in the artifact and no binding in its own registry, and `provider_capabilities` raises.
        #
        # Falling back to False is what the docstring above already promises ("a missing or
        # unrecognised value is treated the same as 'nothing looked'") and is the conservative
        # direction: without the registration we genuinely cannot know what that provider declared,
        # so claiming it looked would be the same unfounded negative this whole check exists to
        # stop. Letting it raise instead crashed `deal-report` with a bare traceback -- the class
        # F19 closed in Wave 2 for a missing forecast file.
        return False


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

    # What the photo set is *of*. The media report carries its own listing identity, captured
    # when the photos were gathered; the report header's address comes from the listing text.
    # When both exist and disagree, the reader can see it instead of assuming they match.
    subject = [bit for bit in (report.listing_title, report.address, report.source_url) if bit]
    if subject:
        lines.append(f"- **Subject:** {' · '.join(subject)}")

    cov = report.coverage
    lines.append(
        f"- **Images:** {cov.images_readable} readable of {cov.images_total} · "
        f"{cov.detections_total} detections · provider `{cov.provider}` version `{cov.version}`"
    )

    if report.room_counts:
        rooms = ", ".join(f"{room} {count}" for room, count in sorted(report.room_counts.items()))
        lines.append(f"- **Rooms Documented:** {rooms}")
    else:
        lines.append("- **Rooms Documented:** none identified")

    detected = sorted(name for name, present in report.amenities.items() if present)
    if detected:
        lines.append(f"- **Amenities Seen in Photos:** {', '.join(detected)}")

    # Defects the CV pass flagged, with how many images carry each. An observation, not an
    # inspection — the same caveat the Adjustments section states at length.
    if report.defects:
        flagged = ", ".join(f"{label} ({count} image{'s' if count != 1 else ''})" for label, count in sorted(report.defects.items()))
        lines.append(f"- **Defects Seen in Photos:** {flagged}")

    # Scored proxies (0-1, higher = the trait shows up more consistently across the photos that
    # were checked). The scale is stated here because nowhere else in the report defines it. A
    # score of exactly 0.00 is what an UNMATCHED proxy also produces (mean of an empty list), so it
    # is rendered as "not measured" rather than as a number — a genuine low score and "nothing in
    # this photo set matched this trait" are different facts, and a bare 0.00 does not say which.
    if report.quality_flags:
        rendered_flags = [
            f"{name} not measured" if score <= 0.0 else f"{name} {score:.2f}" for name, score in sorted(report.quality_flags.items())
        ]
        lines.append(f"- **Quality Proxies (0-1 scale):** {', '.join(rendered_flags)}")

    # Parking type/spots and EV charging are each gated on whether the CV provider that produced
    # this report ever declared it could look for the corresponding label at all (see
    # `_photo_capability_covers`). Every provider shipped with this codebase declares neither, so
    # both defaults ("none" / False) are schema defaults, not sightings, and the report says so
    # instead of stating a negative nothing was capable of observing.
    parking = report.parking
    if parking.parking_type == ParkingType.none.value and not _photo_capability_covers(report, *_PARKING_TYPE_LABELS):
        parking_bits = ["not checked — no photo check in this run looks for parking"]
    else:
        parking_bits = [parking.parking_type]
        if parking.parking_spots is not None:
            parking_bits.append(f"{parking.parking_spots} spot{'s' if parking.parking_spots != 1 else ''}")

    if _photo_capability_covers(report, AmenityLabel.ev_charger.value):
        parking_bits.append("EV charging observed" if parking.ev_charging else "no EV charging observed")
    else:
        parking_bits.append("EV charging not checked — no photo check in this run looks for chargers")

    lines.append(f"- **Parking (from photos):** {' · '.join(parking_bits)}")

    if report.warnings:
        lines.append("- **Coverage Warnings:**")
        for w in report.warnings[:6]:
            lines.append(f"  - {w}")

    return "\n".join(lines) + "\n"


def _render_year_table(years: list[YearBreakdown]) -> str:
    """
    Render a compact Markdown table of key annual metrics.

    Columns:
      Year | GSI | GOI | Total OPEX | NOI | Debt Service | Principal | Interest | Cash Flow | DSCR | Ending Balance

    ``principal_paid``/``interest_paid`` are split out beside the debt-service total they sum
    to. The engine computes both per year (``amortization_schedule``) and the report used to
    drop them, leaving the reader with one lump payment: nothing on the page said how much of
    it bought equity (principal, which is why Ending Balance falls) versus how much was the
    cost of the money (interest, the deductible half). Both are already-computed engine
    figures — this renders them, it does not derive them.
    """
    horizon = len(years)
    header = [
        _section(f"{horizon}-Year Pro Forma (Summary)"),
        f"| Year | {_glossary_link('gsi', 'GSI')} | {_glossary_link('goi', 'GOI')} "
        f"| Total {_glossary_link('opex', 'OPEX')} | {_glossary_link('noi', 'NOI')} "
        f"| {_glossary_link('ds', 'Debt Service')} | Principal | Interest "
        f"| Cash Flow | {_glossary_link('dscr', 'DSCR')} | Ending Balance |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
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
            f"| {_fmt_currency(y.principal_paid)} "
            f"| {_fmt_currency(y.interest_paid)} "
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


def _available_equity_at_80(est_value: float, ending_balance: float) -> float:
    """
    Equity available at the 80% refinance mark: ``max(0, 0.80 × value − mortgage balance)``.

    The floor at zero is the engine's own definition (``YearBreakdown.available_equity``,
    ``src/core/finance/engine.py``, and the same rule it uses for terminal equity in the IRR
    series). The two report-side tracks below (baseline appreciation, stress-test) model values
    the engine does not, so they need the rule restated here — but they must mean the same thing
    by "Available Equity @80%" as the NOI table, which now renders the engine's stored figure.
    Before this, a year above 80% LTV printed a *negative* "available" equity in two of the three
    tables and 0.00 in the third, under one shared column heading and one shared formula.
    """
    return max(0.0, EQUITY_LTV * est_value - ending_balance)


# -----------------------
# Three separate valuation tables
# -----------------------


def _forecast_carries_valuation(years: list[YearBreakdown]) -> bool:
    """
    Whether every year carries the engine's own NOI-track valuation (``cap_rate_applied``).

    ``cap_rate_applied`` is Optional in the schema: ``run_financial_model`` always sets it, but
    ``deal-report`` renders whatever ``FinancialForecast`` JSON it is handed, which may predate
    the field. All-or-nothing on purpose — a table mixing engine rows with recomputed rows would
    be unreadable and unauditable.
    """
    return bool(years) and all(y.cap_rate_applied is not None for y in years)


def _render_valuation_table_noi(years: list[YearBreakdown], purchase: PurchaseMetrics) -> str:
    """
    NOI-based table — **the engine's own valuation track, rendered, not recomputed**.

    ``run_financial_model`` already computes and stores this exact track on every
    ``YearBreakdown`` (``src/core/finance/engine.py``)::

        cap_rate_applied_t = cap_purchase + market.cap_rate_drift * (t - 1)
        est_value_t        = NOI_t / cap_rate_applied_t   (0.0 when NOI_t < 0)
        ltv_pct_t          = EndingBalance_t / est_value_t * 100      # PERCENT, not a fraction
        available_equity_t = max(0, 0.80 * est_value_t - EndingBalance_t)

    This function used to re-derive all four from ``purchase.cap_rate`` plus an env knob, which
    made the report disagree with the forecast in two live ways: an input ``market.cap_rate_drift``
    moved the stored values but not this table, and a negative-NOI year rendered a *negative*
    estimated value where the engine stores 0.00. Both are gone now that the numbers are read.

    Note ``ltv_pct`` is stored in percent (0-100), unlike every rate elsewhere in the schema, so
    it is formatted directly rather than through :func:`_fmt_pct`.

    Falls back to the historical recomputation only for a forecast that carries no stored cap
    path at all (see :func:`_forecast_carries_valuation`).
    """
    if not years:
        return ""

    header = [
        _section("Valuation – NOI-Based (with Cap Drift)"),
        f"| Year | {_glossary_link('cap', 'Cap Rate')} (applied) | Estimated Value "
        f"| {_glossary_link('ltv', 'LTV')} % | Available {_glossary_link('te', 'Equity')} @80% |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ]
    rows = []

    if _forecast_carries_valuation(years):
        for y in years:
            assert y.cap_rate_applied is not None  # narrowed by _forecast_carries_valuation
            rows.append(
                f"| {y.year} | {_fmt_pct(y.cap_rate_applied)} | {_fmt_currency(y.est_value)} "
                f"| {y.ltv_pct:.2f}% | {_fmt_currency(y.available_equity)} |"
            )
        return "\n".join(header + rows) + "\n"

    base_cap = max(1e-6, float(purchase.cap_rate))
    drift = _cap_drift_per_year()
    for y in years:
        cap_t = max(1e-6, base_cap + drift * (y.year - 1))
        est_value = (y.noi / cap_t) if cap_t > 0 else 0.0
        ltv = (y.ending_balance / est_value) if est_value > 0 else 0.0
        rows.append(
            f"| {y.year} | {_fmt_pct(cap_t)} | {_fmt_currency(est_value)} "
            f"| {_fmt_pct(ltv)} | {_fmt_currency(_available_equity_at_80(est_value, y.ending_balance))} |"
        )
    return "\n".join(header + rows) + "\n"


def _render_valuation_table_baseline(years: list[YearBreakdown], forecast: FinancialForecast) -> str:
    """
    Baseline appreciation table:
      - PurchasePrice inferred from Y1 NOI / cap.
      - Value_t = PurchasePrice * (1 + g)^t, g from env (default 3%).
      - LTV_t = EndingBalance_t / Value_t
      - Equity80_t = max(0, 0.80 * Value_t - EndingBalance_t)  (see _available_equity_at_80)

    This is a report-side sensitivity track: the engine models the NOI track only, so these
    values are computed here from the forecast's own figures.
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
        avail_eq = _available_equity_at_80(est_value, y.ending_balance)
        rows.append(f"| {y.year} | {_fmt_currency(est_value)} | {_fmt_pct(ltv)} | {_fmt_currency(avail_eq)} |")
    return "\n".join(header + rows) + "\n"


def _render_valuation_table_stress(years: list[YearBreakdown], forecast: FinancialForecast) -> str:
    """
    Stress-test table (rate-anchored):
      - r = interest rate ≈ purchase.cap_rate - spread
      - basis = max(0, PurchasePrice - Adj); Adj via env AIREAL_STRESS_ADJ (default 0)
      - Value_t = basis * (1 + r/3)^t
      - LTV_t = EndingBalance_t / Value_t
      - Equity80_t = max(0, 0.80 * Value_t - EndingBalance_t)  (see _available_equity_at_80)

    Report-side sensitivity track, like the baseline one above.
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
        avail_eq = _available_equity_at_80(est_value, y.ending_balance)
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


# FIXED VERBATIM honesty block for the observation comparison. Rendered byte-for-byte with no
# per-run interpolation, for the same reason as ABOUT_SCENARIOS_BLOCK: fixed text cannot drift
# out of step with the numbers, and it only appears when observations actually moved something.
#
# Descriptive, never prescriptive — it states what an observation *is* and what it is not. It
# does not tell the reader what to do about it.
ABOUT_OBSERVATIONS_BLOCK = (
    "> **About these observations.** Condition tags, defects and amenities are *observations* — what\n"
    "> the pipeline read in the listing copy and the photo set. Nothing was inspected or measured, and\n"
    "> an observation can be wrong: a feature can be missed, or a label attached to something it does\n"
    "> not describe. Each adjustment below is a fixed engine rule applied to an observation — a\n"
    "> modeling allowance, not a quote or a measured cost. The baseline column is the same deal with\n"
    "> none of them applied, so the observation-dependent part of this analysis can be read apart from\n"
    "> the part that does not depend on any observation."
)

# Emitted only when provenance records that the AI photo path was actually active. With it off we
# say nothing about models: the report cannot tell an LLM-authored tag from a keyword match, so a
# blanket "no AI was involved" would be a claim it has no standing to make.
_AI_OBSERVATION_SOURCE_LINE = (
    "_AI photo tagging was on for this run (`AIREAL_USE_VISION`): the photo-derived observations are "
    "model output, so they carry a model's error rate on top of everything noted above._"
)


def _model_was_involved(provenance: RunProvenance | None) -> bool:
    """Whether ANY model produced observations on this run -- vision OR language.

    Gating AI attribution on `vision_enabled` alone hid the one path where a model authored
    everything: with `--engine crewai` and `AIREAL_LLM_MODE` set but vision off, an LLM wrote every
    condition tag, defect and amenity, moved GOI/NOI/cash flow/cap rate -- and the report rendered
    the neutral "With observations" header, suppressed the model-error caveat, and told the reader
    the tags came from "the listing copy and the photo set". Two accurate flags, one false picture.
    """
    if provenance is None:
        return False
    return bool(provenance.vision_enabled or provenance.llm_mode_enabled)


def _render_observation_impact(
    forecast: FinancialForecast,
    baseline: BaselineOutlook,
    thesis: InvestmentThesis | None,
    provenance: RunProvenance | None,
) -> list[str]:
    """
    Render the baseline-vs-observed comparison table for Year 1.

    One table, metrics as rows, so the "Change" column reads as a single vertical strip — the
    answer to "did anything I act on actually move?" in one scan. Metrics-as-columns would need
    seven columns of three different units and overflow in PDF export.

    Row order is decision-first then causal: the verdict (does this change the answer?), then the
    path the adjustment actually travels — GOI, OPEX, NOI, cash flow — then the ratios computed
    from them. GOI is carried even though no OPEX rule touches it because an amenity uplift moves
    income, not expense: without that row a reader sees OPEX rise and NOI rise with nothing on the
    page to explain it. With it, ``NOI = GOI − OPEX`` closes on both sides of the table.

    ``Change`` is always *observed minus baseline*, stated in the lead-in so the sign is never
    ambiguous. The verdict row compares strings, so its change cell reads unchanged/**changed**.
    """
    base_y1 = baseline.forecast.years[0]
    obs_y1 = forecast.years[0]
    base_p = baseline.forecast.purchase
    obs_p = forecast.purchase

    observed_header = "With observations (AI-assisted)" if _model_was_involved(provenance) else "With observations"

    lines: list[str] = [
        "**Year 1 impact** _(Change = with observations − baseline.)_",
        "",
        f"| Metric | Baseline | {observed_header} | Change |",
        "| :--- | ---: | ---: | ---: |",
    ]

    # Verdict first: the only row that can change the decision rather than a figure behind it.
    # Omitted rather than guessed when the caller supplied no baseline verdict to compare against.
    if baseline.thesis is not None and thesis is not None:
        moved = "**changed**" if baseline.thesis.verdict != thesis.verdict else "unchanged"
        lines.append(f"| Verdict | {baseline.thesis.verdict} | {thesis.verdict} | {moved} |")

    lines.extend(
        [
            f"| GOI | {_fmt_currency(base_y1.goi)} | {_fmt_currency(obs_y1.goi)} | {_fmt_delta_currency(obs_y1.goi - base_y1.goi)} |",
            f"| Total OPEX | {_fmt_currency(base_y1.total_opex)} | {_fmt_currency(obs_y1.total_opex)} "
            f"| {_fmt_delta_currency(obs_y1.total_opex - base_y1.total_opex)} |",
            f"| NOI | {_fmt_currency(base_y1.noi)} | {_fmt_currency(obs_y1.noi)} | {_fmt_delta_currency(obs_y1.noi - base_y1.noi)} |",
            f"| Cash flow | {_fmt_currency(base_y1.cash_flow)} | {_fmt_currency(obs_y1.cash_flow)} "
            f"| {_fmt_delta_currency(obs_y1.cash_flow - base_y1.cash_flow)} |",
            f"| Cap rate | {_fmt_pct(base_p.cap_rate)} | {_fmt_pct(obs_p.cap_rate)} "
            f"| {_fmt_delta_rate(obs_p.cap_rate - base_p.cap_rate)} |",
            f"| DSCR | {base_p.dscr:.2f} | {obs_p.dscr:.2f} | {_fmt_delta_ratio(obs_p.dscr - base_p.dscr)} |",
            f"| Cash-on-cash | {_fmt_pct(base_p.coc)} | {_fmt_pct(obs_p.coc)} | {_fmt_delta_rate(obs_p.coc - base_p.coc)} |",
        ]
    )
    return lines


def _render_year_adjustments(
    forecast: FinancialForecast,
    *,
    thesis: InvestmentThesis | None = None,
    baseline: BaselineOutlook | None = None,
    provenance: RunProvenance | None = None,
) -> str:
    """
    Render the engine's per-year adjustment notes (``YearBreakdown.notes``) — the traceability
    trail for why the OPEX/income figures above differ from the raw listing inputs (e.g. a
    condition tag adding to reserves, a defect adding to repairs & maintenance, an amenity
    uplifting other income). In practice only Year 1 carries these (the insight modifiers are
    applied once, at the top of the model), but every year is checked so the section stays
    correct if that ever changes.

    Notes render verbatim — they are machine-generated traceability strings, not prose to be
    softened or rewritten. Each one already *is* the per-line attribution ("condition: old roof →
    reserves +$300/yr"): the observation that fired, and the rule it fired. Reformatting them here
    would mean parsing engine-authored strings in the renderer, which breaks the first time the
    engine words one differently.

    Three designed states:

    * **No notes** — returns "". A run with no listing insights (or insights that trip no
      modifier) adds no empty heading. This is the default path, and it is what keeps
      ``python main.py`` byte-identical.
    * **Notes, no baseline** — the notes list exactly as before. Callers that hold a forecast but
      not the inputs behind it (``report_cli``) cannot re-run the engine, so they get the
      traceability trail without a comparison rather than a fabricated one.
    * **Notes and a baseline** — the full two-picture section: the honesty block, the Year-1
      comparison table, and the notes as the per-line attribution beneath it.
    """
    by_year = [(y.year, y.notes) for y in forecast.years if y.notes]
    if not by_year:
        return ""

    show_comparison = baseline is not None and bool(baseline.forecast.years) and bool(forecast.years)

    if not show_comparison:
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

    assert baseline is not None  # narrowed by show_comparison
    lines = [
        _section("Adjustments Applied"),
        "Observations from the listing copy and photos moved some of the figures above. This section "
        "shows both pictures — the same deal with those observations and without them — and names the "
        "observation behind every change.",
        "",
        ABOUT_OBSERVATIONS_BLOCK,
        "",
    ]
    if _model_was_involved(provenance):
        lines.append(_AI_OBSERVATION_SOURCE_LINE)
        lines.append("")

    lines.extend(_render_observation_impact(forecast, baseline, thesis, provenance))
    lines.append("")
    lines.append("**What moved each figure**")
    lines.append("")
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

    ``thesis.levers`` (``_levers_for``, ``src/agents/chief_strategist.py``) is pattern-matched,
    free-text advice -- it is never re-run against the model and is a different, older concept
    from the structured, engine-verified ``RecourseAnalysis`` rendered by ``_render_recourse``
    below (Mission 4). Left unmarked, a report showing both would give a reader two lever lists
    with no way to tell which one was actually checked against the numbers. The heading below
    marks this list as qualitative UNCONDITIONALLY -- not only on reports where a computed
    alternative also happens to render -- because "this list is heuristic" is true of every
    report that shows it, independent of what else is on the page.
    """
    lines = [
        _section("Investment Thesis"),
        f"- **Verdict:** {thesis.verdict}",
        "- **Rationale:**",
    ]
    for r in thesis.rationale:
        lines.append(f"  - {r}")
    if thesis.levers:
        lines.append(
            "- **Suggested Levers** _(qualitative — pattern-matched from the numbers above, not verified by re-running the model)._"
        )
        for lever in thesis.levers:
            lines.append(f"  - {lever}")
    return "\n".join(lines) + "\n"


# -----------------------
# "What would have to change?" (Mission 4 — actionable recourse)
# -----------------------
#
# Placement (Roger's decision, overriding the founder-proxy's original append-after-Warnings call):
# adjacent to the Investment Thesis (see the `parts` list in `generate_report`), never appended
# after Warnings — a section answering "what would have to change about THAT verdict" has to sit
# near the verdict, not ~115 lines and five tables below it.
#
# A note on where this copy DIVERGED from the founder-proxy's PD.1 template (flagged per this
# task's own instructions, not silently improvised): the template's per-lever line names the
# post-fix metric value ("{metric} lands at {value}"). `RecourseLever` (src/schemas/models.py)
# carries no such field -- only `target_value`/`delta` for the LEVER and a `closes_guardrail`
# boolean, never the guardrail's own metric at that target. Deriving it here would mean
# recomputing a guardrail metric from a perturbed lever value BY FORMULA in the report layer --
# exactly the non-independence trap `src/market/recourse.py` exists to prevent (Gate V condition
# 1: the trap is a real mechanism, not merely undesirable for one unlucky pair). So every lever
# line below asserts only what the shipped data actually proves: the re-run at `target_value`
# clears the guardrail's own bar (a fact `compute_recourse` already confirmed by re-running the
# engine once more at the rounded ask) -- never a specific resulting number the re-run was not
# asked to report.

#: Fixed lexicographic order (mirrors `src/market/recourse.py`'s own `_GUARDRAIL_ORDER`) used
#: everywhere a guardrail set is iterated here, so block order never depends on dict/set iteration.
_RECOURSE_GUARDRAIL_ORDER: tuple[str, ...] = ("dscr", "spread", "irr", "coc", "cf_y1", "cf_all", "cap_floor")

#: Display labels mirroring the exact wording `chief_strategist.synthesize_thesis` already uses in
#: its own rationale bullets (Investment Thesis section, directly above this one) -- the same claim
#: about the same guardrail is worded identically in both places.
_RECOURSE_GUARDRAIL_LABEL: dict[str, str] = {
    "dscr": "DSCR (Y1)",
    "spread": "Cap-rate spread",
    "irr": "Projected IRR (10y)",
    "coc": "Cash-on-cash (Y1)",
    "cf_y1": "Year-1 cash flow",
    "cf_all": "Cash flow (all years)",
    "cap_floor": "Purchase cap rate",
}

#: Fixed lexicographic order over the four levers (mirrors `src/market/recourse.py`'s own
#: `_LEVER_ORDER`), used both to sort a gap block's rows and as the null/hopeless-line noun map key.
_RECOURSE_LEVER_ORDER: tuple[str, ...] = ("rent_per_unit_month", "purchase_price", "interest_rate", "annual_opex")

_RECOURSE_LEVER_NOUN: dict[str, str] = {
    "rent_per_unit_month": "rent increase",
    "purchase_price": "price cut",
    "interest_rate": "rate cut",
    "annual_opex": "opex cut",
}

#: Indefinite article per lever noun ("an opex cut", "a rent increase") -- a fixed lookup rather
#: than vowel-sniffing, since the vocabulary is fixed and "opex" is spelled with a vowel but the
#: general rule would need to know it is pronounced "OH-pex" to get this right anyway.
_RECOURSE_LEVER_ARTICLE: dict[str, str] = {
    "rent_per_unit_month": "a",
    "purchase_price": "a",
    "interest_rate": "a",
    "annual_opex": "an",
}

# FIXED VERBATIM honesty block (mirrors ABOUT_SCENARIOS_BLOCK's own precedent below): rendered
# byte-for-byte, no per-run interpolation. Carries the shared "would, not will" / non-independence
# caveat ONCE, so no per-lever line has to repeat it (the gap header's own trailing clause, "with
# everything else held as modeled," is the only per-block reminder -- never a fourth repetition).
ABOUT_RECOURSE_BLOCK = (
    "> **About this section.** Each gap below is the smallest single change to ONE input that WOULD\n"
    "> close it — a real re-run of the underwriting model on a copy of your inputs, never a guardrail\n"
    '> formula solved backward for the unknown lever value. **"Would," not "will":** every line holds\n'
    "> every OTHER assumption exactly as modeled, and the levers are not independent — a change large\n"
    "> enough to close one gap does not, by itself, guarantee the others close too. Combinations of\n"
    "> levers (e.g. a smaller rent bump together with a smaller price cut) were never searched. See\n"
    '> "How these numbers were produced" below for the exact ranges checked and the realism\n'
    "> thresholds applied, with their numbers."
)

_RECOURSE_METHODOLOGY_LINES: tuple[str, ...] = (
    "**How these numbers were produced**",
    "",
    "- Every number above comes from a full re-run of the underwriting model on a copy of your "
    "inputs with exactly one lever changed — never a guardrail formula solved backward for the "
    "unknown lever value. The one guardrail/lever pair in this engine where that shortcut gives a "
    "wrong answer (cash-on-cash via purchase price — a price cut changes both the cash flow AND "
    "the cash invested at once) is why this discipline is never optional: the shortcut is not "
    "reliably conservative, it is simply wrong, and which way it errs depends on which variable "
    "the shortcut freezes.",
    "- **Ranges searched, per lever, from your current numbers:** rent — 0% to +100% of the current "
    "average rent/unit/month; purchase price — 0% to −40% off the current price; interest rate — 0 "
    "to −300 bps, floored at 0%; annual opex — 0% to −40% off the current total. A lever with no "
    "closing row under a gap below was searched across that full range and never crossed the "
    "guardrail's bar — that is a real, reported result, not an omission.",
    "- **Every ask is rounded away from zero** — a required cut rounds to a LARGER cut, a required "
    "increase to a LARGER increase, never a number that would undershoot the bar — and then "
    "re-run once more at that rounded figure to reconfirm it still clears the bar before being "
    "shown.",
    '- **Realism thresholds, so "closes it" is not automatically "a reasonable ask":** a rent '
    "increase above 10%, a price cut above 15%, or an opex cut above 20% of your current numbers is "
    "flagged (never removed); a rate cut is flagged above 100 bps and, separately, whenever it "
    "would push the implied cap rate outside the 3.00%–12.00% range this project treats as a "
    "realistic market cap rate. Flagged rows keep their exact numbers — a flag is a caution, not a "
    "hidden result.",
    "- **Combinations of levers were never searched.** Every row above changes exactly one input at "
    "a time; a smaller combined move (e.g. a modest rent increase together with a modest price cut) "
    "may exist and was not checked.",
)


# -----------------------
# Multi-lever combinations (Mission 5, Half B) -- a SECOND section beside the single-lever menu
# -----------------------
#
# WHY A SECOND SECTION AND NOT A REPLACEMENT (founder, PD.2 / Mission 5): "we do not know if the
# investor can act on one or multiple levers at the same time." Both ship. The single-lever menu
# above is untouched -- every row, every flag, every null line renders exactly as it did before.
#
# WHAT THIS BLOCK MAY AND MAY NOT DO:
#   * It renders `CombinationAnalysis` and NOTHING ELSE. Every ask, every margin, every count
#     below is read straight off a field the search already filled from a real, un-differentiated
#     `run_financial_model` re-run. This module derives no financial quantity of its own -- a
#     number computed here would be a number with no engine behind it (the same discipline the
#     single-lever block's own module note above spells out, for the same reason).
#   * NO RANKING. `combinations` arrives in the search's own subset-enumeration order and is
#     rendered in that order, complete: never sorted, never truncated, never a "top N". The
#     founder's earlier top-3 / parsimony-then-leximin ordering is superseded and shelved. Exactly
#     one row carries a LABEL -- `cheapest_total_index`, a pure argmin over a column the reader
#     can see and re-add for themselves -- and the copy beside it says in so many words that it
#     is not a ranking and not a recommendation.
#   * THREE OUTCOMES, RENDERED DISTINGUISHABLY. `found` / `proven_null` / `undetermined` each get
#     their own lead sentence, and the outcome is read from `outcome` / `honest_null` /
#     `subsets_exhausted` -- NEVER inferred from `combinations` being empty. An `undetermined`
#     rendered as a null would tell an investor "nothing can save this deal" when the truth is
#     "we ran out of probe budget"; that is the one mistake this whole section exists to avoid,
#     and `test_recourse_combination_render.py` pins it.
#   * GD3. Only the four `LeverName` values can appear as an ask, because `CombinationLeverMove`
#     has no field a model assumption could live in. The honesty block below states that in the
#     report itself, so a reader can hold the tool to it.
#
# TYPOGRAPHY. This block introduces no new heading level: the report has no `###` anywhere, and
# the enclosing section already marks its own sub-parts with a bold lead line ("How these numbers
# were produced"). One more bold lead line keeps the document's outline unchanged on GitHub, in
# VS Code preview and in PDF export.

#: The bold lead line that opens this sub-part, and the exact string the amended single-lever
#: honesty block and methodology bullet point at -- kept in one constant so the pointer and the
#: target can never drift apart.
_COMBINATIONS_HEADING_TEXT: str = "If more than one input can move at once"

#: Column header per lever for the asks table, naming each lever's native unit ONCE in the header
#: so no cell has to repeat it. Mirrors `_RECOURSE_LEVER_ORDER`; a lever no combination moves gets
#: no column at all, so a two-lever answer is not padded out to a four-column table.
_COMBINATION_LEVER_COLUMN: dict[str, str] = {
    "rent_per_unit_month": "Rent ($/unit/month)",
    "purchase_price": "Purchase price",
    "interest_rate": "Interest rate",
    "annual_opex": "Annual opex",
}

# FIXED VERBATIM honesty block (same precedent as ABOUT_RECOURSE_BLOCK above): rendered
# byte-for-byte, no per-run interpolation. Carries the four claims a reader needs before the first
# table -- what question these answer, that every one was confirmed by a real re-run, "would not
# will", and the GD3 lever/assumption partition stated in the report itself.
ABOUT_COMBINATIONS_BLOCK = (
    "> **About these combinations.** The menu above changes exactly ONE input at a time. This part\n"
    "> changes two or more together, and answers a stricter question: what would clear EVERY guardrail\n"
    "> this deal is judged against at once — including the ones that already pass. Each combination\n"
    "> shown was confirmed by its own full re-run of the underwriting model on a copy of your inputs,\n"
    '> at the exact asks shown — never a guardrail formula solved backward. **"Would," not "will":**\n'
    "> each one holds every OTHER assumption exactly as modeled. Only the four inputs an investor can\n"
    "> act on are ever moved — rent, purchase price, interest rate, operating expenses. No modeling\n"
    "> assumption (vacancy, rent or expense growth, exit cap rate, hold period) is ever presented here\n"
    "> as something to change."
)

#: Extra "How these numbers were produced" bullets, appended after the single-lever ones whenever
#: this sub-part renders. They exist so a sceptical reader can reconstruct every number above:
#: where the bracketed share comes from, what the total-ask budget is, what the joint realism check
#: tests that the per-input one does not, and what each of the three outcomes actually claims.
_RECOURSE_COMBINATION_METHODOLOGY_LINES: tuple[str, ...] = (
    "- **The bracketed share beside each combination ask** is that ask divided by the per-input realism "
    "threshold named two bullets above (rent 10%, purchase price 15%, interest rate 100 bps, annual opex "
    "20% of your current numbers). A rent ask reading (64%) is 64% of the largest single rent move this "
    "project treats as realistic. The shares are per input and never added across different units — "
    '"Total ask" adds the shares themselves, so 1.00 means one input moved all the way to its own '
    "threshold. No combination is shown whose total exceeds 2.00: the budget applied is the smallest "
    "combination this part will ever show — two inputs, each at its own limit.",
    "- **A combination is checked jointly, not input by input.** On top of the per-input thresholds, a "
    "combination is rejected when the moves do not hang together as one market story — the same "
    "realism check the rest of this project uses, applied to the combination's own re-run: rates and "
    "the deal's implied cap rate diverging by more than 200 bps, or an implied cap rate outside the "
    "3.00%–12.00% band. Where that check fired, its reason is quoted above in its own words.",
    "- **The search enumerates every grouping of two, three and four inputs** and solves each one "
    "separately, so the answers stay distinct rather than collapsing onto a single optimum. Each "
    "grouping gets a fixed budget of model re-runs; a grouping that uses that budget up is reported as "
    'stopped early, never as proof that nothing exists. "No combination clears the guardrails" and '
    '"the search did not finish" are reported as different results above, because they are different '
    "results.",
)

#: The single-lever honesty block, amended for the case where this sub-part also renders. Spelled
#: out in full rather than patched by string surgery, so both variants are readable and diffable:
#: the ONLY difference from `ABOUT_RECOURSE_BLOCK` is the combinations sentence, which in the
#: original says combinations "were never searched" -- true before Mission 5 and false the moment
#: this sub-part appears below it. `ABOUT_RECOURSE_BLOCK` is still emitted verbatim whenever no
#: combination analysis is supplied, so an older payload's report is byte-identical.
ABOUT_RECOURSE_BLOCK_WITH_COMBINATIONS = (
    "> **About this section.** Each gap below is the smallest single change to ONE input that WOULD\n"
    "> close it — a real re-run of the underwriting model on a copy of your inputs, never a guardrail\n"
    '> formula solved backward for the unknown lever value. **"Would," not "will":** every line holds\n'
    "> every OTHER assumption exactly as modeled, and the levers are not independent — a change large\n"
    "> enough to close one gap does not, by itself, guarantee the others close too. Combinations of\n"
    "> levers (e.g. a smaller rent bump together with a smaller price cut) are searched separately,\n"
    f'> under "{_COMBINATIONS_HEADING_TEXT}" below. See\n'
    '> "How these numbers were produced" below for the exact ranges checked and the realism\n'
    "> thresholds applied, with their numbers."
)

#: The single-lever methodology bullet that says combinations "were never searched", replaced for
#: the case where they were. `_RECOURSE_METHODOLOGY_LINES[-1]` is that bullet; the slice below
#: swaps exactly it and nothing else, and `test_recourse_combination_render.py` pins that the last
#: element really is the combinations bullet so a future append cannot silently drop a real one.
_RECOURSE_COMBINATION_MENU_BULLET: str = (
    "- **Every row in the menu above changes exactly one input at a time.** Combinations of two or "
    f'more inputs are a separate search, reported under "{_COMBINATIONS_HEADING_TEXT}" above — '
    "including the ones this one would call a smaller combined move."
)


def _fmt_delta_bps(x: float) -> str:
    """Format a rate delta in basis points with an explicit sign, at the 0dp precision the
    single-lever block already uses for rate asks ("90 bps rate cut"). Signed rather than paired
    with a direction word because this one renders inside a table cell, where the sign is the only
    thing carrying the direction."""
    bps = x * 10_000
    body = f"{abs(bps):,.0f} bps"
    if round(bps) == 0:
        return body
    return f"{'+' if bps > 0 else '-'}{body}"


def _combination_move_cell(move: CombinationLeverMove) -> str:
    """One lever's ask as a table cell: the signed delta in the lever's OWN native unit, then that
    ask as a share of the lever's own single-ask realism threshold.

    `fraction_of_cap` is rendered at 0dp deliberately. It is a share of a soft flagging threshold,
    not a financial quantity: 2dp would imply a precision the threshold itself does not have, and
    would widen every cell in a table whose whole job is side-by-side comparison. The underlying
    delta is shown at full report precision in the same cell, and the threshold it is divided by is
    named in the methodology, so the share is reconstructible either way."""
    share = f"({move.fraction_of_cap * 100:.0f}%)"
    if move.lever == "interest_rate":
        return f"{_fmt_delta_bps(move.delta)} {share}"
    return f"{_fmt_delta_currency(move.delta)} {share}"


#: Prose phrasing per lever, for the one place a combination is written as a sentence rather than
#: a table row (the rejected exemplar on a null). The table can name each unit once in a column
#: header; a sentence cannot, so these carry the full native unit inline -- the same units the
#: single-lever bullets above already use ("$/unit/month", "the purchase price", "bps").
_COMBINATION_LEVER_PHRASE: dict[str, str] = {
    "rent_per_unit_month": "{ask}/unit/month on rent",
    "purchase_price": "{ask} on the purchase price",
    "interest_rate": "{ask} on the interest rate",
    "annual_opex": "{ask} on annual opex",
}


def _combination_move_phrase(move: CombinationLeverMove) -> str:
    """One lever's ask written out in prose, in its own full native unit, with the same bracketed
    share the table cells carry. Used only by the rejected-exemplar bullet."""
    ask = _fmt_delta_bps(move.delta) if move.lever == "interest_rate" else _fmt_delta_currency(move.delta)
    return f"{_COMBINATION_LEVER_PHRASE[move.lever].format(ask=ask)} ({move.fraction_of_cap * 100:.0f}%)"


def _combination_lever_columns(combinations: tuple[RecourseCombination, ...]) -> list[str]:
    """The levers any of these combinations actually moves, in the fixed `_RECOURSE_LEVER_ORDER`
    -- so a set of answers that never touches the interest rate gets no interest-rate column, and
    the table stays as narrow as the answers allow."""
    moved = {move.lever for combo in combinations for move in combo.moves}
    return [lever for lever in _RECOURSE_LEVER_ORDER if lever in moved]


def _render_combination_asks_table(combinations: tuple[RecourseCombination, ...]) -> list[str]:
    """The asks table: one row per combination, one column per lever any of them moves, plus the
    total. A lever this combination leaves alone renders as an em dash — visually unmistakable
    against a cell that carries an ask, and never a blank a reader could read as "zero" or as
    "not reported"."""
    levers = _combination_lever_columns(combinations)
    header = ["#"] + [_COMBINATION_LEVER_COLUMN[lever] for lever in levers] + ["Total ask"]
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---:"] * len(header)) + " |"]
    for i, combo in enumerate(combinations, start=1):
        by_lever: dict[str, CombinationLeverMove] = {move.lever: move for move in combo.moves}
        cells = [str(i)]
        for lever in levers:
            move = by_lever.get(lever)
            cells.append(_combination_move_cell(move) if move is not None else "—")
        cells.append(f"{combo.total_fraction_of_caps:.2f}")
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def _render_combination_margins_table(combinations: tuple[RecourseCombination, ...]) -> list[str]:
    """The receipts: every live guardrail's value at each combination's OWN confirming re-run,
    beside the bar it is judged against.

    Both the column set and the bars come from `confirmed_margins` itself (the search read them
    off the same runs), so this table cannot quote a bar the confirming run did not test. Values
    are formatted by `_recourse_fmt_metric`, the same helper the single-lever gap headers and the
    Investment Thesis rationale use -- the same guardrail is never shown at two precisions in one
    report."""
    order = [margin.guardrail for margin in combinations[0].confirmed_margins]
    bars = {margin.guardrail: margin.bar for margin in combinations[0].confirmed_margins}
    header = ["#"] + [f"{_RECOURSE_GUARDRAIL_LABEL[g]} ≥ {_recourse_fmt_metric(g, bars[g])}" for g in order]
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---:"] * len(header)) + " |"]
    for i, combo in enumerate(combinations, start=1):
        values = {margin.guardrail: margin.value for margin in combo.confirmed_margins}
        cells = [str(i)]
        for g in order:
            cells.append(_recourse_fmt_metric(g, values[g]) if g in values else "—")
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def _render_combination_accounting(analysis: CombinationAnalysis) -> list[str]:
    """Where the search went: every combination it enumerated, in exactly one bucket, adding up to
    the total.

    Rendered on ALL THREE outcomes and with every counter shown, zeros included. A zero that is
    printed is a reported zero; a zero that is suppressed is indistinguishable from a count nobody
    looked at. It is also the only place `subsets_exhausted` can be checked against the lead
    paragraph's claim, which is the whole `undetermined`-is-not-a-null guarantee made auditable."""
    rows = [
        ("Cleared every guardrail, confirmed by its own re-run", len(analysis.combinations)),
        ("Proven empty: every input in it at its realism limit at once, and a guardrail still fails", analysis.subsets_infeasible),
        ("Reached the edge of the search range along its own direction without clearing them", analysis.subsets_edge_infeasible),
        ("Cleared the guardrails, but the joint realism check rejected the asks", analysis.subsets_gate_rejected),
        ("Rounded down to a single input — the menu above already covers it", analysis.subsets_collapsed),
        (f"Stopped early: the budget of {analysis.max_iter} model re-runs for that combination ran out", analysis.subsets_exhausted),
        ("The confirming re-run failed", analysis.confirm_failed),
    ]
    lines = [
        "**Where the search went.** Every combination of two, three and four inputs that was enumerated, " "in exactly one bucket each:",
        "",
        "| What happened to it | Count |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {label} | {count} |" for label, count in rows)
    lines.append(f"| **Total combinations tried** | **{analysis.subsets_searched}** |")
    return lines


def _render_combination_gate_reasons(reasons: tuple[str, ...], *, exclude: str | None = None) -> list[str]:
    """The deduped reasons the joint realism check gave, in the search's own first-occurrence
    order. Rendered on every outcome where any fired -- a rule that fired is an assumption that
    fired, and a count with no "why" beside it is silence with a receipt (PD.2 call 4)."""
    remaining = [reason for reason in reasons if reason != exclude]
    if not remaining:
        return []
    lead = "Why the joint realism check rejected combinations that did clear every guardrail:"
    if exclude is not None:
        lead = "The joint realism check also gave these reasons:"
    return [lead, ""] + [f"- _{reason}_" for reason in remaining]


def _render_combination_exemplar(exemplar: RejectedCombination) -> list[str]:
    """The one gate-rejected, re-run-confirmed candidate shipped on a proven null (PD.2 call 4).

    Its reason is INSEPARABLE from the row by construction: the row opens with the literal word
    "Rejected" and the reason is the nested italic line directly under it -- the exact two-line
    idiom `_render_recourse_lever_line` already uses for a flagged single-lever row, so the report
    speaks with one voice about a caveated number. It is shown only here, on a null, where it
    competes with nothing: beside real answers it would read as a fourth answer.

    Its margins render as one sentence rather than the receipts table above. A one-row six-column
    table on a page that has just said "no combination clears the guardrails" is heavier than the
    fact it carries, and the fact is the same either way -- every figure comes from this
    candidate's own confirming re-run."""
    combo = exemplar.combination
    asks = "; ".join(f"**{_combination_move_phrase(move)}**" for move in combo.moves)
    margins = ", ".join(
        f"{_RECOURSE_GUARDRAIL_LABEL[m.guardrail]} {_recourse_fmt_metric(m.guardrail, m.value)} "
        f"against a bar of {_recourse_fmt_metric(m.guardrail, m.bar)}"
        for m in combo.confirmed_margins
    )
    return [
        "**The closest thing to an answer, and why it is not shown as one.** One combination did clear every "
        'guardrail on its own confirming re-run, and the joint realism check rejected it. "Nothing was found" '
        'and "something was found and it does not qualify" are different answers, so it is shown here with the '
        "reason attached. The bracketed figure beside each ask is that ask as a share of the largest single move "
        'of that input this project treats as realistic (see "How these numbers were produced" below):',
        "",
        f"- Rejected — {asks} — total ask {combo.total_fraction_of_caps:.2f}.",
        f"  _Rejected because {exemplar.reason}_",
        f"  _Its confirming re-run measured: {margins}._",
    ]


def _render_combinations_lead(analysis: CombinationAnalysis) -> list[str]:
    """The one paragraph that has to be right.

    The outcome is read from `analysis.outcome` -- never inferred from `combinations` being empty,
    because empty is true of BOTH a proven null and an unfinished search, and the two say opposite
    things to an investor. Each branch is worded so it cannot be mistaken for another:

      * `found`        -- a count, and an explicit "this is not a ranking".
      * `proven_null`  -- "no combination ... clears", plus "ran every one of them to a conclusion".
      * `undetermined` -- "did not finish", "stopped looking", and an explicit denial that this is
                          a finding that nothing exists. The words "no combination" never appear
                          in this branch except inside that denial.
    """
    if analysis.outcome == "found":
        n = len(analysis.combinations)
        lines = [
            f"**{n} combination{'s' if n != 1 else ''} of two or more inputs would clear every guardrail this "
            "deal is judged against — not only the failing ones — with everything else held as modeled.** They "
            "are listed in the order the search enumerated them. This is **not a ranking**: each of these "
            "inputs is a different conversation with a different party, and this tool has no way to know which "
            "of them is open to you, so it does not order them for you.",
        ]
        if analysis.subsets_exhausted:
            lines.extend(
                [
                    "",
                    f"**This list is not complete.** {analysis.subsets_exhausted} of the {analysis.subsets_searched} "
                    f"combinations tried used up their budget of {analysis.max_iter} model re-runs before reaching a "
                    "conclusion, so combinations beyond the ones below may exist. The table at the end of this part "
                    "accounts for every one.",
                ]
            )
        return lines

    if analysis.outcome == "proven_null":
        return [
            "**No combination of two or more of these inputs clears every guardrail, within the ranges "
            "searched and the realism limits this project applies.** The search enumerated all "
            f"{analysis.subsets_searched} combinations of two, three and four inputs and ran every one of them "
            "to a conclusion. This is a completed search that came up empty — not a search that stopped early.",
        ]

    # `undetermined`. This branch is the reason the whole three-outcome contract exists: an
    # exhausted probe budget rendered as a null would tell an investor "nothing can save this deal"
    # when the truth is "we ran out of budget". It never states, or implies, that none exists.
    return [
        "**The combination search did not finish — this run stopped looking, and that is not a finding that "
        f"nothing exists.** Each combination gets a fixed budget of {analysis.max_iter} model re-runs to locate "
        f"its crossing point; {analysis.subsets_exhausted} of the {analysis.subsets_searched} combinations tried "
        "used that budget up before either clearing every guardrail or being proven empty. A combination that "
        "would clear every guardrail may well exist — this run did not establish it either way, and nothing in "
        "this part should be read as saying that none does.",
    ]


def _render_combinations(analysis: CombinationAnalysis | None) -> list[str]:
    """Render the multi-lever sub-part, or nothing at all.

    Nothing is rendered when `analysis` is None (an older payload, or the feature absent) or when
    `attempted` is False. `attempted` is False exactly when no live guardrail is failing, in which
    case the enclosing section has no gap blocks either and there is no gap for a combination to
    close: a paragraph explaining that nothing was searched because nothing is broken would be
    noise under a heading that already asks "what would have to change?".
    """
    if analysis is None or not analysis.attempted or analysis.outcome is None:
        return []

    lines: list[str] = [f"**{_COMBINATIONS_HEADING_TEXT}**", "", ABOUT_COMBINATIONS_BLOCK, ""]
    lines.extend(_render_combinations_lead(analysis))
    lines.append("")

    if analysis.combinations:
        lines.append(
            "Each ask below is in its own unit, with the bracketed figure showing that ask as a share of the "
            "largest single move of that input this project treats as realistic — the same per-input thresholds "
            'listed under "How these numbers were produced" below. An input a combination leaves alone shows an '
            "em dash."
        )
        lines.append("")
        lines.extend(_render_combination_asks_table(analysis.combinations))
        lines.append("")

        # The cheapest-total LABEL. `cheapest_total_index` is an argmin over a column the reader
        # can see and re-add, not a search and not an ordering -- and the copy says so, because a
        # single highlighted row is exactly what a reader would otherwise read as "the answer".
        if analysis.cheapest_total_index is not None:
            idx = analysis.cheapest_total_index
            total = analysis.combinations[idx].total_fraction_of_caps
            lines.extend(
                [
                    f"**Combination {idx + 1} has the smallest total ask, at {total:.2f}.** That is the arithmetic "
                    'minimum of the "Total ask" column above — not a ranking of the others, and not a '
                    'recommendation. "Total ask" adds up the bracketed shares: 1.00 is one input moved all the way '
                    "to its own realism limit, so a total of "
                    f"{total:.2f} spread across {len(analysis.combinations[idx].moves)} inputs is a smaller ask on "
                    "each of them than any one input taken to its limit alone.",
                    "",
                ]
            )

        lines.extend(
            [
                "**What the confirming re-runs measured.** One row per combination above, read off that "
                "combination's own re-run of the underwriting model — never a guardrail formula solved backward. "
                "Every column is a bar this deal is judged against, at the same value the Investment Thesis above "
                "tests it at.",
                "",
            ]
        )
        lines.extend(_render_combination_margins_table(analysis.combinations))
        lines.append("")

    exemplar = analysis.rejected_exemplar
    if exemplar is not None:
        lines.extend(_render_combination_exemplar(exemplar))
        lines.append("")

    reason_lines = _render_combination_gate_reasons(analysis.gate_reasons, exclude=exemplar.reason if exemplar is not None else None)
    if reason_lines:
        lines.extend(reason_lines)
        lines.append("")

    lines.extend(_render_combination_accounting(analysis))
    return lines


def _recourse_fmt_metric(guardrail: str, value: float) -> str:
    """Format one guardrail's own metric at its own native precision -- mirrors exactly how
    `chief_strategist.synthesize_thesis` already formats the same guardrail in its rationale
    bullets (Investment Thesis section, directly above this one): dscr as a bare 2dp ratio, cash
    flow guardrails as 0dp currency (chief_strategist's own `${y1.cash_flow:,.0f}` convention),
    every other guardrail as a 2dp percentage."""
    if guardrail == "dscr":
        return f"{value:.2f}"
    if guardrail in ("cf_y1", "cf_all"):
        return f"${value:,.0f}"
    return _fmt_pct(value)


def _recourse_guardrail_current_and_bar(guardrail: str, forecast: FinancialForecast, market: MarketAssumptions | None) -> tuple[str, str]:
    """The guardrail's OWN current value and the bar it is judged against -- read straight off the
    already-computed baseline `forecast` and the run's `market` guardrails (never a new engine
    call, never a value computed by this module): the exact numbers `chief_strategist` already
    tested when it produced the verdict this section is attached to."""
    y1 = forecast.years[0]
    purchase = forecast.purchase
    if guardrail == "dscr":
        return _recourse_fmt_metric("dscr", y1.dscr), _recourse_fmt_metric("dscr", MIN_DSCR_Y1)
    if guardrail == "spread":
        target = spread_target_for(market)
        return _recourse_fmt_metric("spread", purchase.spread_vs_rate), _recourse_fmt_metric("spread", target)
    if guardrail == "irr":
        return _recourse_fmt_metric("irr", forecast.irr_10yr), _recourse_fmt_metric("irr", MIN_IRR_10YR)
    if guardrail == "coc":
        return _recourse_fmt_metric("coc", purchase.coc), _recourse_fmt_metric("coc", MIN_COC_Y1)
    if guardrail == "cf_y1":
        return _recourse_fmt_metric("cf_y1", y1.cash_flow), _recourse_fmt_metric("cf_y1", 0.0)
    if guardrail == "cf_all":
        worst = min(y.cash_flow for y in forecast.years)
        return _recourse_fmt_metric("cf_all", worst), _recourse_fmt_metric("cf_all", 0.0)
    # cap_floor. A floor of None should not occur for a FAILING cap_floor guardrail (recourse's own
    # `_live_guardrails` only ever makes cap_floor live when `market.cap_rate_floor is not None`),
    # but the report layer accepts `market` independently of `recourse` (an additive, optional
    # kwarg) -- so this degrades honestly to "N/A" instead of crashing on a mismatched caller.
    floor = market.cap_rate_floor if market is not None else None
    bar = _recourse_fmt_metric("cap_floor", floor) if floor is not None else "N/A"
    return _recourse_fmt_metric("cap_floor", purchase.cap_rate), bar


def _recourse_also_closes_clause(also_closes: tuple[str, ...]) -> str:
    if not also_closes:
        return ""
    labels = ", ".join(_RECOURSE_GUARDRAIL_LABEL[g] for g in _RECOURSE_GUARDRAIL_ORDER if g in also_closes)
    return f" Also closes: {labels}."


def _recourse_native_and_companion(row: RecourseLever) -> tuple[str, str]:
    """(bolded native-unit clause, companion clause) for one closing lever row.

    Per-lever unit pairing (founder-proxy PD.1, implemented as specified): rent in $/unit/month +
    %; price in $ off + resulting level and %; rate in bps + resulting rate level; opex in $ + %.
    """
    assert row.target_value is not None and row.delta is not None  # guaranteed by closes_guardrail=True
    pct = f"{row.relative_change:.2%}" if row.relative_change is not None else "n/a"
    if row.lever == "rent_per_unit_month":
        native = f"**{_fmt_currency(row.delta)}/unit/month rent increase**"
        companion = f"{_fmt_currency(row.target_value)}/unit/month ({pct} above current)"
    elif row.lever == "purchase_price":
        native = f"**{_fmt_currency(abs(row.delta))} off the purchase price**"
        companion = f"{_fmt_currency(row.target_value)} ({pct} off)"
    elif row.lever == "interest_rate":
        native = f"**{abs(row.delta) * 10_000:.0f} bps rate cut**"
        companion = f"{_fmt_pct(row.target_value)} rate"
    else:  # annual_opex
        native = f"**{_fmt_currency(abs(row.delta))} annual opex cut**"
        companion = f"{pct} lower operating costs"
    return native, companion


def _render_recourse_lever_line(row: RecourseLever, bar: str) -> list[str]:
    """One closing lever's bullet (native unit bold first, companion currency, then the bar it
    clears — never a fabricated post-fix metric value, see this section's own module note above).
    Flagged rows (plausible=False) lead with the literal word "Flagged" (never a glyph — glyphs
    break in PDF export) and carry a nested italic reason naming the number that tripped; the row
    keeps its full numbers either way — flagging is an annotation, never a removal."""
    native, companion = _recourse_native_and_companion(row)
    label = _RECOURSE_GUARDRAIL_LABEL[row.guardrail]
    also = _recourse_also_closes_clause(row.also_closes)
    body = f"{native} → {companion} — clears the {label} bar of {bar}.{also}"
    if row.plausible:
        return [f"- {body}"]
    reason = row.plausibility_reason or "flagged by this project's plausibility guardrails."
    return [f"- Flagged — {body}", f"  _{reason}_"]


def _render_recourse_null_line(row: RecourseLever) -> str:
    """Structurally-hopeless and honest-per-row-null rows both collapse to ONE italic line —
    deliberately NOT the flagged treatment (structurally-hopeless levers provably cannot move the
    metric at all, which is a different, stronger claim than "implausible"), and worded so a
    per-row null (searched, found nothing within the bound) is never confused with a hopeless one
    (provably cannot move the metric at all)."""
    noun = _RECOURSE_LEVER_NOUN[row.lever]
    article = _RECOURSE_LEVER_ARTICLE[row.lever].capitalize()
    if row.structurally_hopeless:
        return f"_{article} {noun} cannot move this guardrail at all, for this deal — it never enters the calculation being tested._"
    return f"_{article} {noun} alone, up to the largest change checked, does not close this gap — another lever, or a combination, might._"


def _recourse_sorted_block_rows(rows: tuple[RecourseLever, ...]) -> list[RecourseLever]:
    """Cheapest/plausible-first within a block (discovery spec §4.2's tier ordering, applied per
    guardrail rather than analysis-wide): plausible-closing rows first, then flagged-closing rows
    ("flagged rows sort below unflagged within their block — never into a separate, collapsed, or
    footnoted list"), then non-closing (null/hopeless) informational lines last. Ties within a tier
    break on the fixed lever order — deterministic, never dict/insertion order."""

    def _key(row: RecourseLever) -> tuple[int, int]:
        if row.closes_guardrail:
            tier = 0 if row.plausible else 1
        else:
            tier = 2
        return (tier, _RECOURSE_LEVER_ORDER.index(row.lever))

    return sorted(rows, key=_key)


def _render_recourse_gap_block(
    guardrail: str, rows: tuple[RecourseLever, ...], forecast: FinancialForecast, market: MarketAssumptions | None
) -> list[str]:
    current, bar = _recourse_guardrail_current_and_bar(guardrail, forecast, market)
    label = _RECOURSE_GUARDRAIL_LABEL[guardrail]
    lines = [
        f"**{label} — {current} against a bar of {bar}.** Any ONE of these would close it, on its "
        "own, with everything else held as modeled:",
        "",
    ]
    for row in _recourse_sorted_block_rows(rows):
        if row.closes_guardrail:
            lines.extend(_render_recourse_lever_line(row, bar))
        else:
            lines.append(f"- {_render_recourse_null_line(row)}")
    return lines


def _render_recourse_lead(analysis: RecourseAnalysis, forecast: FinancialForecast, market: MarketAssumptions | None) -> list[str]:
    """The cheapest-first lead (discovery spec §4.3 / decision 2): the single cheapest fix, with
    the "other gaps remain" line BOLD and IMMEDIATELY adjacent — never below the fold, never
    omitted when `remaining_after_cheapest` is non-empty (Gate V condition 2) — so a reader who
    stops after two lines cannot mistake the lead for sufficiency. Honest-null (decision 3) says so
    plainly here, with no "maybe"/"however"/"consider" hedging."""
    if analysis.honest_null:
        labels = ", ".join(_RECOURSE_GUARDRAIL_LABEL[g] for g in _RECOURSE_GUARDRAIL_ORDER if g in analysis.failing_guardrails)
        return [
            f"**Nothing found within the ranges checked would close this on its own.** {labels} "
            "remain outside the bars this deal is judged against. No single lever — rent, price, "
            "rate, or opex, alone — closed any of them within the ranges searched. The breakdown "
            "below shows exactly what was tried for each; the footer names the ranges themselves."
        ]

    cheapest = analysis.cheapest
    assert cheapest is not None  # honest_null is False, so `_pick_cheapest` found a row
    _, bar = _recourse_guardrail_current_and_bar(cheapest.guardrail, forecast, market)
    native, companion = _recourse_native_and_companion(cheapest)
    label = _RECOURSE_GUARDRAIL_LABEL[cheapest.guardrail]
    also = _recourse_also_closes_clause(cheapest.also_closes)
    flagged_prefix = "Flagged — " if not cheapest.plausible else ""
    lines = [f"**Cheapest single fix:** {flagged_prefix}{native} → {companion} — clears the {label} bar of {bar}.{also}"]
    if not cheapest.plausible:
        reason = cheapest.plausibility_reason or "flagged by this project's plausibility guardrails."
        lines.append(f"_{reason}_")

    # A blank-line paragraph break (not a bare "\n") guarantees this renders as its own visually
    # distinct line on every target (GitHub, VS Code preview, PDF export) -- a single trailing
    # newline is a "soft break" that some renderers collapse to a plain space, which would make
    # the two lines run together as one sentence and defeat "bold and immediately adjacent" (Gate
    # V condition 2: this line must never be less visible than the lead it follows).
    lines.append("")
    if analysis.remaining_after_cheapest:
        remaining_labels = ", ".join(
            _RECOURSE_GUARDRAIL_LABEL[g] for g in _RECOURSE_GUARDRAIL_ORDER if g in analysis.remaining_after_cheapest
        )
        lines.append(f"**Other gaps remain: {remaining_labels} would still not clear their own bars.**")
    else:
        lines.append("**This single change would close every currently-failing guardrail below — no other gaps remain.**")
    return lines


def _render_recourse(analysis: RecourseAnalysis, forecast: FinancialForecast, market: MarketAssumptions | None) -> str:
    """
    Render the "What would have to change?" section (Mission 4).

    Rendered ONLY when the orchestrator supplied a `RecourseAnalysis` (the pre-computation
    `is_genuinely_close` gate already decided whether one exists at all — see `generate_report`'s
    own call site) — a deal whose gate never opened gets no section, byte-identical to a run with
    no recourse feature at all. Once supplied, EVERY guardrail in `analysis.failing_guardrails` is
    rendered, including an honest_null analysis (Roger's Gate D ruling: a computed "nothing
    realistic closes this" is never discarded post-hoc — see `src/market/recourse.py`'s own
    module docstring and the Gate D decision record in `docs/plans/MISSION_4_SPRINT_TRACKER.md`).
    """
    # Mission 5, Half B. Rendered ONLY when there is a combination analysis with something in it
    # to report; computed once here because it decides two things at once -- whether the sub-part
    # renders at all, and which variant of the section's own honesty block and closing methodology
    # bullet is true. With no combination analysis both fall back to their pre-Mission-5 wording
    # and the whole section is byte-identical to what an older payload produced.
    combination_lines = _render_combinations(analysis.combinations)
    about = ABOUT_RECOURSE_BLOCK_WITH_COMBINATIONS if combination_lines else ABOUT_RECOURSE_BLOCK

    lines: list[str] = [_section("What would have to change?"), about, ""]
    lines.extend(_render_recourse_lead(analysis, forecast, market))
    lines.append("")

    by_guardrail: dict[str, list[RecourseLever]] = {}
    for row in analysis.levers:
        by_guardrail.setdefault(row.guardrail, []).append(row)

    for guardrail in _RECOURSE_GUARDRAIL_ORDER:
        if guardrail not in analysis.failing_guardrails:
            continue
        rows = tuple(by_guardrail.get(guardrail, ()))
        lines.extend(_render_recourse_gap_block(guardrail, rows, forecast, market))
        lines.append("")

    if combination_lines:
        lines.extend(combination_lines)
        lines.append("")
        # The single-lever menu's closing bullet asserts combinations "were never searched"; that
        # sentence is false the moment the sub-part above renders, so this swaps exactly that one
        # bullet (the last) and leaves every other one untouched, then adds the combination
        # search's own method. `_RECOURSE_METHODOLOGY_LINES[-1]` being that bullet is pinned by
        # `tests/core/reports/test_recourse_combination_render.py`.
        lines.extend(_RECOURSE_METHODOLOGY_LINES[:-1])
        lines.append(_RECOURSE_COMBINATION_MENU_BULLET)
        lines.extend(_RECOURSE_COMBINATION_METHODOLOGY_LINES)
    else:
        lines.extend(_RECOURSE_METHODOLOGY_LINES)
    return "\n".join(lines) + "\n"


# -----------------------
# "How wrong can these guesses be?" (Mission 5 -- assumption breakeven / margin of safety)
# -----------------------
#
# THE SIBLING OF "What would have to change?" ABOVE, and deliberately its mirror image. That
# section solves to a guardrail's bar along an INVESTOR LEVER -- rent, price, rate, opex -- and
# reads the answer as an action. This one performs the same kind of solve along a MODEL ASSUMPTION
# -- vacancy, rent growth, expense growth -- and reads it the only way it may be read: as breakeven
# / margin of safety, a fact about how fragile the deal is. "This clears DSCR until vacancy hits
# 9.4%; you assumed 5%" is a measurement. "Raise your vacancy assumption to 8% and the deal passes"
# is an instruction to edit an input until the model reports a PASS that no real-world action could
# produce, and it is the one sentence this section exists never to write. GD3
# (`src/core/finance/partition.py`) makes it inexpressible upstream -- `AssumptionBreakeven` has no
# target/delta/ask field for it to live in -- and the honesty block below states that in the report
# itself, so a reader can hold the tool to it.
#
# WHAT THIS BLOCK MAY AND MAY NOT DO:
#   * It renders `BreakevenAnalysis` and NOTHING ELSE. Every value, bar and metric below is read
#     straight off a field the search filled from a real, un-differentiated `run_financial_model`
#     re-run. The two derivations this module does perform are DISPLAY-ONLY, and both are stated in
#     the section's own methodology: vacancy = 1 - occupancy (investors think in vacancy), and the
#     displayed crossing = displayed assumption +/- displayed room, so the three numbers on a line
#     always reconcile to the digit a reader can see.
#   * ROUNDING IS TOWARD THE ASSUMPTION, ALWAYS. `margin` is TRUNCATED toward zero at the 0.1
#     percentage-point display step that `src/market/breakeven.py` sized `_BREAKEVEN_TOL` (5e-4)
#     to stay finer than -- never rounded to nearest. Rounding 0.046 pp of room up to "0.05 pp", or
#     a 0.65 pp margin to "0.7 pp", would tell an investor they have room the search never
#     measured. A margin too small to show at that step renders as "less than 0.1 percentage
#     points" -- never "0.0", which reads as a rounding artifact rather than as the razor margin it
#     is, and never omitted.
#   * THREE OUTCOMES, RENDERED DISTINGUISHABLY, BRANCHED ON `outcome` AND NOTHING ELSE.
#     `breakeven_found` / `never_breaks_in_range` / `undetermined` each get their own sentence
#     shape, and the outcome is NEVER inferred from `breakeven_value`/`margin` being None -- None
#     is true of BOTH a proven "never breaks in this range" and a search that ran out of budget,
#     and those two say opposite things to an investor. An `undetermined` rendered as safety would
#     report "this guess has room" when the truth is "we stopped looking";
#     `tests/core/reports/test_breakeven_render.py` pins that it never does.
#   * "NEVER BREAKS" IS ALWAYS SCOPED BY `searched_to`. Vacancy's and rent growth's adverse edges
#     are the genuine ends of what those assumptions can be; expense growth's +100%/yr is a search
#     CEILING this project chose, and the block lead says which of the two it is rather than
#     letting one strong result quietly borrow the other's authority.
#   * FAILING GUARDRAILS GET NO LINE, and the lead says so in words. A guardrail already under its
#     bar has no margin of safety to measure, and solving it along an assumption axis in the
#     FAVOURABLE direction ("it would pass if vacancy were 1%") is the forbidden reading in
#     disguise. `failing_guardrails` ships as a fact and is rendered as one.
#
# TYPOGRAPHY. Same as the section above: no new heading level (this report has no `###` anywhere),
# a bold lead line per sub-part, bullets for rows, and no glyph that breaks in PDF export.

#: Fixed enumeration order for the assumption blocks -- mirrors `src/market/breakeven.py`'s own
#: `_ASSUMPTION_ORDER`, so block order never depends on the order rows happen to arrive in.
_BREAKEVEN_ASSUMPTION_ORDER: tuple[str, ...] = ("occupancy", "rent_growth", "expense_growth")

#: The noun each assumption is DISPLAYED under. `occupancy` is shown as VACANCY throughout (the
#: display transform is `1 - occupancy`, declared in this section's own methodology): investors
#: think and negotiate in vacancy, and "occupancy 0.9495" is a number nobody says out loud.
_BREAKEVEN_ASSUMPTION_NOUN: dict[str, str] = {
    "occupancy": "vacancy",
    "rent_growth": "rent growth",
    "expense_growth": "operating-expense growth",
}

#: Sentence-initial form of the same noun, for the block lead line.
_BREAKEVEN_ASSUMPTION_TITLE: dict[str, str] = {
    "occupancy": "Vacancy",
    "rent_growth": "Rent growth",
    "expense_growth": "Operating-expense growth",
}

#: The verb for the adverse direction IN DISPLAY SPACE. Note `occupancy`: the schema's
#: `adverse_direction` for it is "down" (less occupancy never helps), which is UP once the number
#: is flipped into vacancy. Reading the direction word straight off `adverse_direction` here would
#: therefore print exactly the wrong verb, which is why this is a display-space table.
_BREAKEVEN_ADVERSE_VERB: dict[str, str] = {
    "occupancy": "reaches",
    "rent_growth": "falls to",
    "expense_growth": "reaches",
}

#: True when the adverse direction points UP in display space -- the sign that places the displayed
#: crossing relative to the displayed assumption, and the same flip as `_BREAKEVEN_ADVERSE_VERB`.
_BREAKEVEN_ADVERSE_IS_UP: dict[str, bool] = {"occupancy": True, "rent_growth": False, "expense_growth": True}

#: What the adverse move MEANS, one clause per assumption, for the block lead. These are engine
#: data-flow facts (see `src/market/breakeven.py`'s module docstring), not per-deal estimates.
_BREAKEVEN_ADVERSE_CLAUSE: dict[str, str] = {
    "occupancy": "More empty units never helps this deal",
    "rent_growth": "Slower rent growth never helps this deal",
    "expense_growth": "Faster-growing operating costs never help this deal",
}

#: What the far edge of each search IS -- a plain-language gloss of `searched_to` and, crucially,
#: whether it is a real end of the assumption or a ceiling this project chose. Vacancy and rent
#: growth bottom out for arithmetic reasons; operating-expense growth has no natural ceiling at
#: all, so a "never breaks" out to +100%/yr is a statement about the SEARCH and not about reality.
#: The copy says which, rather than letting the weaker claim borrow the stronger one's authority.
_BREAKEVEN_EDGE_GLOSS: dict[str, str] = {
    "occupancy": "every unit empty. That is the whole range this assumption has, not a limit of the search",
    "rent_growth": "rents falling to nothing after year 1. That is the arithmetic floor of this assumption, not a limit of the search",
    "expense_growth": "operating costs doubling every year. **That is where this search stopped, not where reality stops** — "
    "a faster cost spiral is possible and was not checked",
}

#: The NOMINAL adverse edge per assumption, in the assumption's own (not display) units -- the
#: value `src/market/breakeven.py` aims its search at. Mirrored here rather than imported, exactly
#: as `_RECOURSE_LEVER_ORDER` mirrors the search's own lever order: `src/core/reports` does not
#: depend on `src/market`. `tests/core/reports/test_breakeven_render.py` pins all three against the
#: search's own constants, so the mirror cannot silently drift.
#:
#: WHY THE REPORT NEEDS THESE AT ALL: a row's `searched_to` is CLIPPED IN from the nominal edge
#: whenever the engine refuses to model the deal that far out -- a refinancing deal's NOI goes
#: negative deep in the adverse range, and the engine declines to amortize the negative loan that
#: implies. "We searched this assumption to the end of its range" and "we searched as far as this
#: deal could be modeled" are different claims, and a "never breaks" is only ever as strong as
#: whichever of the two is true. Without this the section would quietly report the weaker result in
#: the stronger result's words.
_BREAKEVEN_NOMINAL_EDGE: dict[str, float] = {
    "occupancy": 1e-6,
    "rent_growth": -1.0,
    "expense_growth": 1.0,
}

#: The gloss used INSTEAD of `_BREAKEVEN_EDGE_GLOSS` when a block's edge was clipped in. It names
#: no cause: the row carries the value the search reached, not the reason the engine stopped, and
#: a report layer that guessed at the reason would be inventing exactly the kind of confident
#: sentence this section exists to avoid.
_BREAKEVEN_CLIPPED_EDGE_GLOSS: str = (
    "as far as this deal can be modeled along this assumption. Past that point the underwriting model declines "
    "to produce a forecast at all, so the search stopped there rather than guess at what it would have said"
)

# FIXED VERBATIM honesty block (same precedent as ABOUT_RECOURSE_BLOCK / ABOUT_COMBINATIONS_BLOCK
# above): rendered byte-for-byte, no per-run interpolation. It carries the four claims a reader
# needs before the first bullet -- what a "guess" is and why it gets its own section, that every
# figure came from a real re-run, that the answer is fragility and never advice, and the GD3 line
# itself, quoted concretely enough that a reader can hold the section to it.
ABOUT_BREAKEVEN_BLOCK = (
    "> **About this section.** How full the building stays, how fast rents rise, how fast costs rise —\n"
    "> these are not things you can act on. They are things you had to guess, and every number in this\n"
    "> report rests on them. This section measures how wrong one of those guesses could be before a\n"
    "> guardrail that currently passes stops passing. Each figure comes from moving ONE guess in the\n"
    "> direction that hurts and re-running the whole underwriting model on a copy of your inputs at\n"
    "> each step, until the guardrail stopped clearing — never a guardrail formula solved backward,\n"
    "> and never a number read off anything but a confirming re-run. **Nothing here is a target.**\n"
    '> "This clears until vacancy reaches 9.4%" is a measurement of how fragile the deal is. "Assume\n'
    '> 9% vacancy instead" would be an instruction to edit an input until the model reports a pass —\n'
    "> a pass nothing you could do in the real world would produce. This section never says the\n"
    "> second thing, and has no field it could say it in."
)

#: The section's own heading, kept in one constant so the lead's cross-reference and the heading
#: itself can never drift apart.
_BREAKEVEN_HEADING_TEXT: str = "How wrong can these guesses be?"

#: Decimal places for every assumption figure in this section: 1, i.e. a 0.1 percentage-point
#: display step. Chosen by `src/market/breakeven.py`, not here -- its `_BREAKEVEN_TOL` (5e-4, or
#: 0.05 pp) is deliberately sized finer than this step, so no digit rendered here is finer than
#: what the bisection actually resolved.
_BREAKEVEN_DISPLAY_DP: int = 1


def _breakeven_display_value(assumption: str, value: float) -> float:
    """One assumption value in DISPLAY space, as a fraction: the identity, except `occupancy`,
    which is shown as vacancy (`1 - occupancy`). The single place that transform happens."""
    return 1.0 - value if assumption == "occupancy" else value


def _fmt_breakeven_level(assumption: str, value: float) -> str:
    """One assumption LEVEL, in display space, at this section's 0.1 percentage-point step.

    Growth rates carry "a year" because a growth rate and a vacancy share are different kinds of
    number, and a bare "2.0%" beside a bare "5.0%" invites reading them as the same kind."""
    body = f"{_breakeven_display_value(assumption, value) * 100:.{_BREAKEVEN_DISPLAY_DP}f}%"
    return body if assumption == "occupancy" else f"{body} a year"


def _breakeven_margin_pp(margin: float) -> float:
    """The room in percentage points, TRUNCATED TOWARD ZERO at the 0.1 pp display step.

    THE HONESTY-CRITICAL FUNCTION OF THIS SECTION. `margin` is non-negative (it is an absolute
    distance), so truncation toward zero is a floor, and a floor is the only rounding that cannot
    tell an investor they have room the search did not measure: 0.6494 pp of room shows as 0.6 pp,
    never 0.65 and never 0.7. `math.floor` rather than `round(..., 1)` is the entire point --
    `round` would take a 0.65 pp margin UP to 0.7 pp, which is 0.05 pp of room nobody measured."""
    return math.floor(margin * 100.0 * 10.0) / 10.0


def _fmt_breakeven_margin(margin: float) -> str:
    """The room as prose, sentence-cased because it always opens a sentence on the rendered line.

    A margin that truncates to zero at the display step renders as "Less than 0.1 percentage
    points" -- never "0.0 percentage points", which reads as a rounding artifact instead of as the
    razor-thin margin it actually is, and never as nothing at all. The margin is always strictly
    positive: `breakeven_value` is by construction a value the engine observed FAILING, which the
    assumed value (a passing one) is not."""
    pp = _breakeven_margin_pp(margin)
    if pp <= 0.0:
        return "Less than 0.1 percentage points of room"
    return f"{pp:.{_BREAKEVEN_DISPLAY_DP}f} percentage points of room"


def _fmt_breakeven_crossing(row: AssumptionBreakeven) -> str:
    """The crossing LEVEL as displayed: the displayed assumption moved by the displayed room, in
    the adverse direction.

    Derived from the two figures already on the line rather than formatted independently off
    `breakeven_value`, so the three numbers a reader sees always reconcile — and, because the room
    is truncated toward the assumption, the displayed crossing always sits on the assumed side of
    the measured one. It is never further from your assumption than what was actually measured."""
    assert row.margin is not None  # guaranteed by outcome == "breakeven_found"
    assumed_pp = _breakeven_display_value(row.assumption, row.assumed_value) * 100.0
    room_pp = _breakeven_margin_pp(row.margin)
    shown = assumed_pp + room_pp if _BREAKEVEN_ADVERSE_IS_UP[row.assumption] else assumed_pp - room_pp
    body = f"{shown:.{_BREAKEVEN_DISPLAY_DP}f}%"
    return body if row.assumption == "occupancy" else f"{body} a year"


def _breakeven_guardrail_label(row: AssumptionBreakeven) -> str:
    """`"<Guardrail> >= <bar>"` -- the same label and the same per-guardrail precision the
    combination margins table and the Investment Thesis rationale already use, so one guardrail is
    never shown at two precisions, or under two names, in one report."""
    return f"{_RECOURSE_GUARDRAIL_LABEL[row.guardrail]} ≥ {_recourse_fmt_metric(row.guardrail, row.bar)}"


def _render_breakeven_row(row: AssumptionBreakeven, *, max_iter: int) -> str:
    """One (assumption, currently-passing guardrail) bullet, branched on `outcome` and on nothing
    else.

    The three shapes are deliberately not interchangeable:
      * `breakeven_found`       -- "clears until X", the room, and what the confirming re-run found
                                   on the far side of the bar: the measured metric ("just below the
                                   bar" when the two round equal at this guardrail's display
                                   precision — N1), or, on an IRR cliff (`metric_at_breakeven` is
                                   None — N-B1), the statement that no IRR was computable there at
                                   all, never the engine's coalesced-0.0 sentinel as a number.
      * `never_breaks_in_range` -- "still clears at every X searched, out to <edge>", scoped by
                                   this row's OWN `searched_to`; or, when `metric_moves` is False,
                                   the different and stronger claim that the guardrail does not
                                   depend on this assumption at all.
      * `undetermined`          -- "not determined within budget", plus an explicit denial that
                                   this means room. The words "clears until" and "still clears"
                                   never appear in this branch.
    """
    label = _breakeven_guardrail_label(row)
    noun = _BREAKEVEN_ASSUMPTION_NOUN[row.assumption]

    if row.outcome == "undetermined":
        # The reason the three-outcome contract exists at all. An exhausted probe budget rendered
        # as room would tell an investor a guess is safe when the truth is that this run stopped
        # looking -- the one mistake this section, like the combinations section above, exists to
        # avoid.
        return (
            f"- **{label}** — **not determined within budget.** This line used up its budget of {max_iter} model "
            f"re-run{'s' if max_iter != 1 else ''} before it could locate the point where {noun} breaks this "
            "guardrail, so this run does not know how much room there is. That is not a finding that there is "
            "room to spare."
        )

    if row.outcome == "never_breaks_in_range":
        if row.searched_to == row.assumed_value:
            # Degenerate bracket: the assumed value already sits at or past the adverse edge, so
            # there was no adverse room to search. Reported as the ABSENCE of a measurement -- the
            # one thing it must never be reported as is a margin.
            return (
                f"- **{label}** — your assumed {noun} already sits at the far edge of the range this search can "
                "probe, so there was no adverse room left to search and no margin of safety was measured."
            )
        if not row.metric_moves:
            return (
                f"- **{label}** — this guardrail does not depend on {noun} at all: its number is identical at your "
                f"assumed {_fmt_breakeven_level(row.assumption, row.assumed_value)} and at "
                f"{_fmt_breakeven_level(row.assumption, row.searched_to)}, the far edge searched."
            )
        return (
            f"- **{label}** — still clears at every {noun} searched, out to "
            f"{_fmt_breakeven_level(row.assumption, row.searched_to)}. A real re-run at that far edge still cleared "
            "the bar, so nothing in the range searched breaks it."
        )

    # `breakeven_found`.
    assert row.margin is not None  # guaranteed by the outcome
    head = (
        f"- **{label}** — clears until {noun} {_BREAKEVEN_ADVERSE_VERB[row.assumption]} "
        f"{_fmt_breakeven_crossing(row)}; you assumed {_fmt_breakeven_level(row.assumption, row.assumed_value)}. "
        f"**{_fmt_breakeven_margin(row.margin)}**"
    )
    if row.metric_at_breakeven is None:
        # The IRR cliff (Gate V re-review, N-B1). None here means the confirming run's IRR was
        # the engine's coalesced-0.0 sentinel, not a computed return (`src/market/breakeven.py`
        # degrades it, mirroring `jacobian.py`'s posture for the same value). The crossing is
        # real and confirmed — the guardrail genuinely stops clearing there — but there is no
        # metric to quote: quoting the sentinel as "measured 0.00%" told a reader the return
        # decayed gently to the bar when it actually stayed computable and then stopped being so.
        # Only the words below make the crossing claim; the room figure keeps its floor-rounding.
        return head + (
            " — but this room does not end with the return easing down to the bar: the confirming re-run there "
            "could not compute an IRR at all. At that point the deal's projected cash flows no longer admit any "
            "rate of return, and the model counts that against this guardrail. The room shown is the distance "
            "to where the return stops being computable — not to a measured crossing of the bar."
        )
    measured = _recourse_fmt_metric(row.guardrail, row.metric_at_breakeven)
    if measured == _recourse_fmt_metric(row.guardrail, row.bar):
        # N1: at this guardrail's own display precision the confirming metric rounds to the bar
        # itself, and "≥ 1.20 … measured 1.20, below the bar" is a sentence at war with its own
        # numbers. The words carry the fact instead; the metric is deliberately NOT re-rendered
        # one digit finer, so one guardrail never appears at two precisions in one report.
        return head + " — the confirming re-run there measured just below the bar, within one display step of it."
    return head + f" — the confirming re-run there measured {measured}, below the bar."


def _render_breakeven_block(assumption: str, rows: list[AssumptionBreakeven], *, max_iter: int) -> list[str]:
    """One assumption's block: a lead naming the guess, the value you gave it, which way it hurts
    and how far the search went, then one bullet per currently-passing guardrail.

    The lead carries the range ONCE for the whole block, which is where `searched_to` belongs: it
    is a property of the assumption, not of the guardrail. The far edge quoted is the adverse-most
    `searched_to` a row in this block actually reached -- never a module constant this layer
    assumes on the search's behalf. A degenerate row (no adverse room at all) says so on its own
    line and is excluded from that maximum, so one such row cannot silently shrink the range the
    other rows really were searched across."""
    title = _BREAKEVEN_ASSUMPTION_TITLE[assumption]
    assumed = rows[0].assumed_value
    searched = [row.searched_to for row in rows if row.searched_to != row.assumed_value]
    lead = f"**{title} — you assumed {_fmt_breakeven_level(assumption, assumed)}.** "
    if not searched:
        lead += (
            f"{_BREAKEVEN_ADVERSE_CLAUSE[assumption]}, but your assumed value already sits at the far edge of the "
            "range this search can probe, so there was no adverse room left to search."
        )
    else:
        # Every non-degenerate row in a block shares one `searched_to` by construction: the edge
        # the search reaches depends on the assumption and the deal, never on which guardrail the
        # row measures. `max`/`min` is belt and braces, and picks the adverse-most either way.
        edge = max(searched) if _BREAKEVEN_ADVERSE_IS_UP[assumption] else min(searched)
        gloss = _BREAKEVEN_EDGE_GLOSS[assumption] if edge == _BREAKEVEN_NOMINAL_EDGE[assumption] else _BREAKEVEN_CLIPPED_EDGE_GLOSS
        lead += (
            f"{_BREAKEVEN_ADVERSE_CLAUSE[assumption]}, so each guardrail below was re-tested against it moving the "
            f"wrong way, out to {_fmt_breakeven_level(assumption, edge)} — {gloss}."
        )
    return [lead, ""] + [_render_breakeven_row(row, max_iter=max_iter) for row in rows]


def _render_breakeven_lead(analysis: BreakevenAnalysis, *, recourse_rendered: bool) -> list[str]:
    """The lead: which guardrails have a margin measured and -- said plainly, never by omission --
    which have none, and why.

    A currently-FAILING guardrail gets no line in this section BY DESIGN, and a reader who is not
    told that will read its absence as an oversight or, worse, as a pass. So the failing set is
    named here with its reason (a guardrail already under its bar has no room left to lose), and
    with a pointer to the section that does own it -- but only when that section actually rendered
    on this report, since recourse runs behind its own near-miss gate and is frequently absent."""
    n_live = len(analysis.passing_guardrails) + len(analysis.failing_guardrails)
    passing = ", ".join(_RECOURSE_GUARDRAIL_LABEL[g] for g in _RECOURSE_GUARDRAIL_ORDER if g in analysis.passing_guardrails)
    lines = [
        f"**{len(analysis.passing_guardrails)} of the {n_live} guardrails this deal is judged against clear their bars "
        f"at the values you assumed: {passing}.** Each line below is how far ONE of your modeling assumptions can "
        "drift the wrong way before that guardrail stops clearing — with everything else held exactly as modeled, "
        "and one assumption moving at a time."
    ]
    if analysis.failing_guardrails:
        failing = ", ".join(_RECOURSE_GUARDRAIL_LABEL[g] for g in _RECOURSE_GUARDRAIL_ORDER if g in analysis.failing_guardrails)
        where = (
            'What would have to change about them is a different question, answered under "What would have to ' 'change?" above.'
            if recourse_rendered
            else "What would have to change about them is a different question, and this section does not answer it."
        )
        lines.append("")
        lines.append(
            f"**{failing} do not appear below, and their absence is not a pass.** They are already under their bars "
            "at these same assumed values, so there is no margin of safety to measure for them: a guardrail that is "
            f"already failing has no room left to lose. {where}"
        )
    return lines


#: Closing methodology, mirroring `_RECOURSE_METHODOLOGY_LINES` above. `{max_iter_reruns}` is the
#: ONLY interpolated token in the whole block, substituted by `_breakeven_methodology_lines` --
#: every other word is fixed, so the block is diffable and cannot drift per run.
_BREAKEVEN_METHODOLOGY_LINES: tuple[str, ...] = (
    "**How these numbers were produced**",
    "",
    "- **Every crossing above was confirmed by a full re-run of the underwriting model at exactly that value, "
    "with the guardrail observed failing there** — never a guardrail formula solved backward for the assumption, "
    "and never a figure read off an intermediate search step. The search moves one assumption at a time toward "
    "the far edge of its range and halves in on the crossing; only the confirming re-run's numbers are reported.",
    "- **Every figure is rounded to 0.1 of a percentage point, always toward your own assumption and never away "
    "from it.** The room shown is never more than the room measured: 0.65 points of room is reported as 0.6, not "
    "0.7. Each crossing was located to within 0.05 of a percentage point, so a margin too small to show at that "
    'step is reported as "less than 0.1 percentage points" rather than as zero. On every line the crossing shown '
    "is the assumption you gave, moved by the room shown, so the three numbers reconcile.",
    "- **Only guardrails that currently pass get a line.** A guardrail already under its bar has no margin of "
    "safety to measure, and running the same search on it in the favourable direction would produce a sentence "
    'like "it would pass if vacancy were 1%" — a suggestion to change an assumption until the model reports a '
    "pass, which is the one thing this section will not do.",
    "- **Three different results, kept apart, because they mean different things.** A crossing found; a guardrail "
    "that still cleared at the far edge of the range searched — a real, proven result, and one that claims "
    "nothing beyond that range; and one the search could not settle inside its budget of {max_iter_reruns} per "
    'line, reported as not determined. The third is "we stopped looking", never "there is room", and it is '
    "labelled that way above.",
    "- **Vacancy is shown as vacancy.** The model's own input is economic occupancy; vacancy is 1 minus that, so "
    "an occupancy of 0.95 is the 5.0% vacancy quoted above. Rent growth and operating-expense growth are annual "
    "rates, shown as given.",
    "- **The exit cap rate, cap-rate drift and the hold period are modeling assumptions too, and are deliberately "
    "not measured here.** All three act mainly through this engine's terminal-equity figure, which is a "
    "simplified placeholder (80% of the final-year value less the mortgage balance, with no sale costs modeled — "
    "see Terminal Equity in the definitions appendix). A precise breakeven of a placeholder would be a confident "
    "number about nothing.",
)


def _breakeven_methodology_lines(max_iter: int) -> list[str]:
    """`_BREAKEVEN_METHODOLOGY_LINES` with its one token filled in, pluralized. `str.replace`
    rather than `str.format` because a formatting call over fixed prose is a footgun waiting for
    the first bullet that mentions a literal brace."""
    budget = f"{max_iter} model re-run{'s' if max_iter != 1 else ''}"
    return [line.replace("{max_iter_reruns}", budget) for line in _BREAKEVEN_METHODOLOGY_LINES]


def _render_breakeven(analysis: BreakevenAnalysis | None, *, recourse_rendered: bool) -> str:
    """
    Render the "How wrong can these guesses be?" section (Mission 5 — assumption breakeven).

    Renders nothing when `analysis` is None (an older payload, or the feature absent) or when
    `attempted` is False. `attempted` is False exactly when NO live guardrail currently passes:
    every one of them is already failing, not one of them has a margin of safety, and a section
    whose only content would be a paragraph explaining that there was nothing to measure is noise
    on a report that has already said so louder elsewhere. That is the report layer's call to make,
    and it is deliberately made here rather than in `src/market/breakeven.py`, which always returns
    the complete analysis (see its `compute_breakevens` docstring).

    Args:
        analysis: The computed margin-of-safety analysis, or None.
        recourse_rendered: Whether "What would have to change?" is on this same report. It decides
            one clause only — whether the lead can point a reader at that section by name for the
            failing guardrails it deliberately omits — and never what is measured or reported.
    """
    if analysis is None or not analysis.attempted or not analysis.rows:
        return ""

    lines: list[str] = [_section(_BREAKEVEN_HEADING_TEXT), ABOUT_BREAKEVEN_BLOCK, ""]
    lines.extend(_render_breakeven_lead(analysis, recourse_rendered=recourse_rendered))
    lines.append("")

    by_assumption: dict[str, list[AssumptionBreakeven]] = {}
    for row in analysis.rows:
        by_assumption.setdefault(row.assumption, []).append(row)

    for assumption in _BREAKEVEN_ASSUMPTION_ORDER:
        rows = by_assumption.get(assumption)
        if not rows:
            continue
        lines.extend(_render_breakeven_block(assumption, rows, max_iter=analysis.max_iter))
        lines.append("")

    lines.extend(_breakeven_methodology_lines(analysis.max_iter))
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
        f"scenarios admitted under guardrails · admitted priors sum to {analysis.prior_sum:.2f}._",
        "",
    ]
    # The snapshot the whole grid is perturbations OF. Only its region used to be shown, so the
    # deltas below ("Δ Rent growth +1.00%") were quoted against a baseline the reader could not
    # see. These are the descriptive figures the run started from — not live market data.
    lines.extend(
        [
            "**Market snapshot** _(the baseline every scenario perturbs)._",
            "",
            "| Vacancy | Cap rate | Rent growth | Opex growth | Interest rate |",
            "| ---: | ---: | ---: | ---: | ---: |",
            f"| {_fmt_pct(snapshot.vacancy_rate)} | {_fmt_pct(snapshot.cap_rate)} | {_fmt_pct(snapshot.rent_growth)} "
            f"| {_fmt_pct(snapshot.expense_growth)} | {_fmt_pct(snapshot.interest_rate)} |",
            "",
        ]
    )
    if snapshot.notes:
        lines.append(f"_Snapshot notes: {snapshot.notes}_")
        lines.append("")

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
    baseline: BaselineOutlook | None = None,
    market: MarketAssumptions | None = None,
    recourse: RecourseAnalysis | None = None,
    breakeven: BreakevenAnalysis | None = None,
) -> str:
    """
    Generate a professional Markdown report that summarizes the investment analysis.

    Sections:
      - Header: property summary (address, amenities, notes)
      - Purchase Metrics: cap rate, CoC, DSCR, debt service, acquisition cash, spread
      - Forecasting Methodology: baseline, stress-test, NOI-based formulas and refi rule
      - Media Overview (if available)
      - Photo Coverage (if a MediaReport is supplied)
      - Investment Thesis: verdict, rationale, qualitative levers
      - What would have to change? (Mission 4; only when ``recourse`` is supplied — placed
        immediately adjacent to the Investment Thesis, never appended after Warnings, so the
        section explaining a verdict sits next to that verdict)
      - How wrong can these guesses be? (Mission 5; only when ``breakeven`` is supplied and it
        measured something — the sibling of the section above, immediately after it, so "what you
        could change" and "how much room your guesses have" are read together)
      - Pro Forma (Summary): annual table of GSI, GOI, OPEX, NOI, DS, CF, DSCR, Ending Balance (horizon-aware title)
      - Valuation – Baseline table
      - Valuation – Stress-Test table
      - Valuation – NOI-Based table
      - OPEX Detail (Year 1)
      - Adjustments Applied (if any year carries YearBreakdown.notes — usually Year 1 only).
        When ``baseline`` is also supplied this becomes the two-picture section: the honesty
        block, a Year-1 baseline-vs-observed comparison table (verdict included), and the notes
        as per-line attribution.
      - Refinance Event (if present)
      - Returns Summary
      - Warnings
      - Market Scenarios (opt-in overlay; only when ``scenarios`` is supplied)
      - Appendix — Run Provenance (always emitted)
      - Appendix — Definitions (always emitted, last)

    Args:
        market: The run's underwriting guardrails (``FinancialInputs.market``), when the caller
            has them. Additive and optional so existing callers keep working, and deliberately
            the same narrow type ``chief_strategist.synthesize_thesis`` takes — the report and
            the thesis must quote the same floor and the same spread target or they can
            contradict each other. Supplied, the Run Provenance appendix names them; omitted,
            those rows are absent rather than guessed.
        recourse: "What would have to change?" (Mission 4), when the orchestrator computed one
            (see ``src/market/recourse.py``). Rendered immediately adjacent to the Investment
            Thesis (see ``_render_recourse``) whenever supplied; the pre-computation
            ``is_genuinely_close`` gate the orchestrator runs before ever calling
            ``compute_recourse`` is what decides whether a caller has a non-``None`` analysis to
            pass in at all — with no near-miss (``BUY``, or a deal too far gone to be "genuinely
            close"), ``recourse`` stays ``None`` and this function's output is byte-identical to
            pre-Mission-4 output.
        breakeven: The assumption margin-of-safety analysis (Mission 5), when the orchestrator
            computed one (see ``src/market/breakeven.py``). Rendered directly after "What would
            have to change?" — the two are siblings under the lever/assumption partition and are
            meant to be read as one document: that section answers "what could you do", this one
            answers "how much room do the things you guessed at have". Unlike ``recourse`` it runs
            behind no near-miss gate, because a deal whose guardrails all pass is exactly the deal
            whose margins of safety matter most; ``_render_breakeven`` renders nothing when no live
            guardrail passes, which is the only case with nothing to measure.
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
    ]
    # Mission 4 placement (Roger's decision, overriding the founder-proxy's original
    # append-after-Warnings call): immediately adjacent to the Investment Thesis, never appended
    # after Warnings — the section explaining "what would have to change about THAT verdict" has
    # to sit next to the verdict, not ~115 lines and five tables below it. With no near-miss
    # (`recourse is None`), this branch never fires and output is byte-identical to pre-Mission-4.
    if recourse is not None:
        parts.append(_render_recourse(recourse, forecast, market))
    # Mission 5, and the same placement argument one step further: "how wrong can these guesses
    # be?" is the mirror of "what would have to change?", so it sits directly under it, above the
    # pro forma. The two answer the two halves of one question about the verdict just above them —
    # what an investor could ACT on, and how much room the things they had to GUESS have — and a
    # reader who sees only one of them is reading half the answer. `_render_breakeven` returns ""
    # when there is nothing to measure, so a deal with no passing guardrail gets no section.
    parts.append(_render_breakeven(breakeven, recourse_rendered=recourse is not None))
    parts.extend(
        [
            _render_year_table(forecast.years),
            _render_valuation_table_baseline(forecast.years, forecast),
            _render_valuation_table_stress(forecast.years, forecast),
            _render_valuation_table_noi(forecast.years, forecast.purchase),
            _render_opex_details(forecast.years[0]),
            _render_year_adjustments(forecast, thesis=thesis, baseline=baseline, provenance=provenance),
            _render_refi(forecast.refi),
            _render_returns(forecast),
            _render_warnings(forecast.warnings),
        ]
    )
    if scenarios is not None:
        parts.append(_render_market_scenarios(scenarios))

    # Appendices last: reference material a reader returns to, not something between them and
    # the numbers. Provenance precedes definitions so 'why do these differ?' is answered first.
    parts.append(
        _render_provenance(
            provenance,
            market=market,
            media_report=media_report,
            applied_cap_drift=_applied_cap_drift(forecast.years),
        )
    )
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
    baseline: BaselineOutlook | None = None,
    market: MarketAssumptions | None = None,
    recourse: RecourseAnalysis | None = None,
    breakeven: BreakevenAnalysis | None = None,
) -> None:
    """
    Convenience helper to write the generated report to disk.
    Ensures parent directories exist.

    ``recourse`` is an additive Mission 4 kwarg, forwarded to ``generate_report`` unchanged; see
    that function's docstring for when supplying it renders a "What would have to change?" section.
    ``breakeven`` is its Mission 5 sibling, forwarded the same way.
    """
    md = generate_report(
        insights,
        forecast,
        thesis=thesis,
        media_insights=media_insights,
        media_report=media_report,
        provenance=provenance,
        scenarios=scenarios,
        baseline=baseline,
        market=market,
        recourse=recourse,
        breakeven=breakeven,
    )

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    with p.open("w", encoding="utf-8") as f:
        f.write(md)
