# tests/core/reports/test_recourse_render.py
"""Mission 4 (task I.3): unit + end-to-end coverage for `_render_recourse` and its helpers
(`src/core/reports/generator.py`). Complements `tests/core/reports/test_report_recourse_seam.py`
(placement/byte-identity) with the copy-level detail: per-guardrail gap headers, per-lever line
formatting, flagged-vs-plausible sorting, structurally-hopeless vs honest-per-row-null wording,
the cheapest-first lead (including its flagged and no-remaining-gaps branches), the whole-analysis
honest-null lead, and determinism.

Fixtures are built directly (never by editing `src/`), mirroring the shape
`tests/unit/test_recourse_decisions.py` already uses for `RecourseLever`/`RecourseAnalysis`.
"""

from __future__ import annotations

from src.core.reports.generator import (
    _recourse_also_closes_clause,
    _recourse_guardrail_current_and_bar,
    _recourse_native_and_companion,
    _recourse_sorted_block_rows,
    _render_recourse,
    _render_recourse_gap_block,
    _render_recourse_lead,
    _render_recourse_lever_line,
    _render_recourse_null_line,
    generate_report,
)
from src.schemas.models import FinancialForecast, RecourseAnalysis, RecourseLever
from tests.utils import make_listing_insights, make_market_assumptions, make_minimal_forecast


def _row(
    *,
    guardrail: str,
    lever: str,
    baseline_value: float,
    target_value: float | None,
    delta: float | None,
    relative_change: float | None,
    closes_guardrail: bool,
    structurally_hopeless: bool = False,
    plausible: bool = True,
    plausibility_reason: str | None = None,
    also_closes: tuple[str, ...] = (),
) -> RecourseLever:
    return RecourseLever(
        guardrail=guardrail,  # type: ignore[arg-type]
        lever=lever,  # type: ignore[arg-type]
        baseline_value=baseline_value,
        target_value=target_value,
        delta=delta,
        relative_change=relative_change,
        closes_guardrail=closes_guardrail,
        structurally_hopeless=structurally_hopeless,
        plausible=plausible,
        plausibility_reason=plausibility_reason,
        also_closes=also_closes,  # type: ignore[arg-type]
    )


def _forecast_with(
    *, dscr: float = 1.5, coc: float = 0.10, cap_rate: float = 0.065, irr: float = 0.15, cf_years: list[float] | None = None
) -> FinancialForecast:
    base = make_minimal_forecast()
    cf_years = cf_years if cf_years is not None else [base.years[0].cash_flow]
    years = []
    for i, cf in enumerate(cf_years, start=1):
        years.append(base.years[0].model_copy(update={"year": i, "cash_flow": cf, "dscr": dscr}))
    purchase = base.purchase.model_copy(update={"dscr": dscr, "coc": coc, "cap_rate": cap_rate})
    return base.model_copy(update={"purchase": purchase, "years": years, "irr_10yr": irr})


# ---------------------------------------------------------------------------
# Gap header: current value + bar, per guardrail.
# ---------------------------------------------------------------------------


def test_gap_header_current_and_bar_for_every_ratio_and_percent_guardrail():
    forecast = _forecast_with(dscr=1.10, coc=0.0277, cap_rate=0.0692, irr=0.1150)
    market = make_market_assumptions(cap_rate_floor=0.05, cap_rate_spread_target=0.015)

    current, bar = _recourse_guardrail_current_and_bar("dscr", forecast, market)
    assert (current, bar) == ("1.10", "1.20")

    current, bar = _recourse_guardrail_current_and_bar("coc", forecast, market)
    assert (current, bar) == ("2.77%", "3.00%")

    current, bar = _recourse_guardrail_current_and_bar("irr", forecast, market)
    assert (current, bar) == ("11.50%", "12.00%")

    current, bar = _recourse_guardrail_current_and_bar("cap_floor", forecast, market)
    assert (current, bar) == ("6.92%", "5.00%")

    # spread reads the purchase's own spread_vs_rate, not a re-derivation.
    current, bar = _recourse_guardrail_current_and_bar("spread", forecast, market)
    assert bar == "1.50%"
    assert current == f"{forecast.purchase.spread_vs_rate * 100:.2f}%"


def test_gap_header_cash_flow_guardrails_use_zero_dp_currency_and_zero_bar():
    forecast = _forecast_with(cf_years=[3654.55, -100.0])
    market = make_market_assumptions()

    current, bar = _recourse_guardrail_current_and_bar("cf_y1", forecast, market)
    assert current == "$3,655"
    assert bar == "$0"

    current, bar = _recourse_guardrail_current_and_bar("cf_all", forecast, market)
    # Mirrors chief_strategist's own `${y1.cash_flow:,.0f}` convention exactly (see the demo
    # deal's real rendered rationale: "Year-1 cash flow is negative at $-2,946.") -- the same
    # claim about the same kind of number is formatted identically in both sections.
    assert current == "$-100"  # the worst (minimum) year across the whole hold
    assert bar == "$0"


def test_gap_header_cap_floor_degrades_to_na_when_market_is_none():
    """Defensive branch: `market=None` should never crash even though a real pipeline always
    pairs a failing cap_floor guardrail with a real floor (see the function's own docstring)."""
    forecast = _forecast_with()
    current, bar = _recourse_guardrail_current_and_bar("cap_floor", forecast, None)
    assert bar == "N/A"
    assert current == f"{forecast.purchase.cap_rate * 100:.2f}%"


# ---------------------------------------------------------------------------
# Lever line: native-unit-bold-first, companion second, per lever.
# ---------------------------------------------------------------------------


def test_native_and_companion_per_lever_type():
    rent = _row(
        guardrail="coc",
        lever="rent_per_unit_month",
        baseline_value=1412.5,
        target_value=1422.5,
        delta=10.0,
        relative_change=0.0070796,
        closes_guardrail=True,
    )
    native, companion = _recourse_native_and_companion(rent)
    assert native == "**$10.00/unit/month rent increase**"
    assert companion == "$1,422.50/unit/month (0.71% above current)"

    price = _row(
        guardrail="dscr",
        lever="purchase_price",
        baseline_value=605_000.0,
        target_value=552_300.0,
        delta=-52_700.0,
        relative_change=0.0871074,
        closes_guardrail=True,
    )
    native, companion = _recourse_native_and_companion(price)
    assert native == "**$52,700.00 off the purchase price**"
    assert companion == "$552,300.00 (8.71% off)"

    rate = _row(
        guardrail="dscr",
        lever="interest_rate",
        baseline_value=0.068,
        target_value=0.059,
        delta=-0.009,
        relative_change=0.1323529,
        closes_guardrail=True,
    )
    native, companion = _recourse_native_and_companion(rate)
    assert native == "**90 bps rate cut**"
    assert companion == "5.90% rate"

    opex = _row(
        guardrail="coc",
        lever="annual_opex",
        baseline_value=20_600.0,
        target_value=20_250.0,
        delta=-350.0,
        relative_change=0.0169903,
        closes_guardrail=True,
    )
    native, companion = _recourse_native_and_companion(opex)
    assert native == "**$350.00 annual opex cut**"
    assert companion == "1.70% lower operating costs"


def test_also_closes_clause_present_and_absent_and_in_fixed_order():
    assert _recourse_also_closes_clause(()) == ""
    # Fixed guardrail order, not insertion order: coc should print before cf_y1.
    clause = _recourse_also_closes_clause(("cf_y1", "coc"))
    assert clause == " Also closes: Cash-on-cash (Y1), Year-1 cash flow."


# ---------------------------------------------------------------------------
# Flagged vs plausible rendering; structurally-hopeless vs honest-per-row-null wording.
# ---------------------------------------------------------------------------


def test_plausible_closing_row_renders_one_bullet_no_flag():
    row = _row(
        guardrail="coc",
        lever="purchase_price",
        baseline_value=605_000.0,
        target_value=600_500.0,
        delta=-4_500.0,
        relative_change=0.00744,
        closes_guardrail=True,
    )
    lines = _render_recourse_lever_line(row, "3.00%")
    assert len(lines) == 1
    assert lines[0].startswith("- **$4,500.00 off the purchase price**")
    assert "Flagged" not in lines[0]


def test_flagged_closing_row_leads_with_flagged_and_carries_nested_italic_reason():
    row = _row(
        guardrail="spread",
        lever="purchase_price",
        baseline_value=605_000.0,
        target_value=504_500.0,
        delta=-100_500.0,
        relative_change=0.1661,
        closes_guardrail=True,
        plausible=False,
        plausibility_reason="a price cut of 16.6% is larger than the 15% this project treats as a realistic single ask.",
    )
    lines = _render_recourse_lever_line(row, "1.50%")
    assert len(lines) == 2
    assert lines[0].startswith("- Flagged — **$100,500.00 off the purchase price**")
    assert lines[1] == "  _a price cut of 16.6% is larger than the 15% this project treats as a realistic single ask._"


def test_flagged_row_with_no_reason_string_still_renders_a_caveat_never_crashes():
    row = _row(
        guardrail="spread",
        lever="interest_rate",
        baseline_value=0.068,
        target_value=0.054,
        delta=-0.014,
        relative_change=0.2059,
        closes_guardrail=True,
        plausible=False,
        plausibility_reason=None,
    )
    lines = _render_recourse_lever_line(row, "1.50%")
    assert len(lines) == 2
    assert lines[1].startswith("  _")  # never a blank/crashing reason line


def test_structurally_hopeless_row_wording_names_the_mechanism_not_implausibility():
    row = _row(
        guardrail="cap_floor",
        lever="interest_rate",
        baseline_value=0.068,
        target_value=None,
        delta=None,
        relative_change=None,
        closes_guardrail=False,
        structurally_hopeless=True,
    )
    line = _render_recourse_null_line(row)
    assert line.startswith("_A rate cut cannot move this guardrail at all")
    assert "flagged" not in line.lower()  # never the flagged treatment


def test_honest_per_row_null_wording_differs_from_hopeless():
    row = _row(
        guardrail="spread",
        lever="annual_opex",
        baseline_value=20_600.0,
        target_value=None,
        delta=None,
        relative_change=None,
        closes_guardrail=False,
        structurally_hopeless=False,
    )
    line = _render_recourse_null_line(row)
    assert line.startswith("_An opex cut alone, up to the largest change checked, does not close this gap")
    assert "cannot move this guardrail at all" not in line


def test_null_line_article_agreement_a_vs_an():
    for lever, expected_start in (
        ("rent_per_unit_month", "_A rent increase"),
        ("purchase_price", "_A price cut"),
        ("interest_rate", "_A rate cut"),
        ("annual_opex", "_An opex cut"),
    ):
        row = _row(
            guardrail="spread",
            lever=lever,
            baseline_value=1.0,
            target_value=None,
            delta=None,
            relative_change=None,
            closes_guardrail=False,
            structurally_hopeless=False,
        )
        assert _render_recourse_null_line(row).startswith(expected_start)


def test_block_sorting_plausible_then_flagged_then_null_on_fixed_lever_order():
    flagged = _row(
        guardrail="spread",
        lever="rent_per_unit_month",
        baseline_value=1.0,
        target_value=2.0,
        delta=1.0,
        relative_change=1.0,
        closes_guardrail=True,
        plausible=False,
        plausibility_reason="x",
    )
    plausible = _row(
        guardrail="spread",
        lever="purchase_price",
        baseline_value=1.0,
        target_value=2.0,
        delta=1.0,
        relative_change=1.0,
        closes_guardrail=True,
    )
    null_row = _row(
        guardrail="spread",
        lever="interest_rate",
        baseline_value=1.0,
        target_value=None,
        delta=None,
        relative_change=None,
        closes_guardrail=False,
    )
    hopeless = _row(
        guardrail="spread",
        lever="annual_opex",
        baseline_value=1.0,
        target_value=None,
        delta=None,
        relative_change=None,
        closes_guardrail=False,
        structurally_hopeless=True,
    )

    ordered = _recourse_sorted_block_rows((flagged, null_row, hopeless, plausible))
    assert [r.lever for r in ordered] == ["purchase_price", "rent_per_unit_month", "interest_rate", "annual_opex"]


def test_gap_block_never_omits_a_row_flagged_rows_stay_in_the_same_block():
    plausible = _row(
        guardrail="dscr",
        lever="purchase_price",
        baseline_value=605_000.0,
        target_value=552_300.0,
        delta=-52_700.0,
        relative_change=0.0871,
        closes_guardrail=True,
    )
    flagged = _row(
        guardrail="dscr",
        lever="rent_per_unit_month",
        baseline_value=1412.5,
        target_value=1602.5,
        delta=190.0,
        relative_change=0.1345,
        closes_guardrail=True,
        plausible=False,
        plausibility_reason="too big",
    )
    forecast = _forecast_with(dscr=1.10)
    market = make_market_assumptions()

    lines = _render_recourse_gap_block("dscr", (plausible, flagged), forecast, market)
    text = "\n".join(lines)
    assert "$52,700.00 off the purchase price" in text
    assert "Flagged — **$190.00/unit/month rent increase**" in text
    # Flagged sorts BELOW the plausible row, in the same block -- never a separate list.
    assert text.index("$52,700.00") < text.index("Flagged")


# ---------------------------------------------------------------------------
# The cheapest-first lead: plausible / flagged / no-remaining-gaps / honest-null branches.
# ---------------------------------------------------------------------------


def _analysis(
    *, cheapest: RecourseLever | None, failing: tuple[str, ...], remaining: tuple[str, ...] = (), levers: tuple[RecourseLever, ...] = ()
) -> RecourseAnalysis:
    return RecourseAnalysis(
        verdict="DECLINE",
        failing_guardrails=failing,  # type: ignore[arg-type]
        levers=levers or ((cheapest,) if cheapest else ()),
        cheapest=cheapest,
        remaining_after_cheapest=remaining,  # type: ignore[arg-type]
        honest_null=cheapest is None,
    )


def test_lead_plausible_cheapest_with_remaining_gaps_bold_and_adjacent():
    cheapest = _row(
        guardrail="coc",
        lever="rent_per_unit_month",
        baseline_value=1412.5,
        target_value=1422.5,
        delta=10.0,
        relative_change=0.00708,
        closes_guardrail=True,
    )
    analysis = _analysis(cheapest=cheapest, failing=("dscr", "spread", "coc"), remaining=("dscr", "spread"))
    forecast = _forecast_with(coc=0.0277)
    lines = _render_recourse_lead(analysis, forecast, make_market_assumptions())
    text = "\n".join(lines)
    assert "**Cheapest single fix:**" in text
    assert "Flagged" not in text
    assert "**Other gaps remain: DSCR (Y1), Cap-rate spread would still not clear their own bars.**" in text
    # Bold and IMMEDIATELY adjacent: only a blank-line separator between the two, no other content.
    idx_cheapest = next(i for i, line in enumerate(lines) if line.startswith("**Cheapest"))
    idx_remaining = next(i for i, line in enumerate(lines) if line.startswith("**Other gaps remain"))
    assert idx_remaining - idx_cheapest <= 2


def test_lead_flagged_cheapest_still_shows_flagged_prefix_and_reason():
    cheapest = _row(
        guardrail="spread",
        lever="purchase_price",
        baseline_value=605_000.0,
        target_value=504_500.0,
        delta=-100_500.0,
        relative_change=0.1661,
        closes_guardrail=True,
        plausible=False,
        plausibility_reason="a price cut of 16.6% is larger than the 15% this project treats as a realistic single ask.",
    )
    analysis = _analysis(cheapest=cheapest, failing=("spread",), remaining=())
    forecast = _forecast_with()
    lines = _render_recourse_lead(analysis, forecast, make_market_assumptions())
    text = "\n".join(lines)
    assert "**Cheapest single fix:** Flagged —" in text
    assert "_a price cut of 16.6%" in text
    assert "no other gaps remain" in text.lower()


def test_lead_honest_null_states_plainly_with_no_hedging_language():
    analysis = _analysis(cheapest=None, failing=("dscr", "coc"), levers=())
    forecast = _forecast_with()
    lines = _render_recourse_lead(analysis, forecast, make_market_assumptions())
    text = "\n".join(lines)
    assert "Nothing found within the ranges checked would close this on its own." in text
    for hedge in ("maybe", "however", "consider", "Maybe", "However", "Consider"):
        assert hedge not in text


# ---------------------------------------------------------------------------
# Full section, determinism, and the demo/sample deals.
# ---------------------------------------------------------------------------


def test_full_render_recourse_is_byte_identical_across_two_calls():
    cheapest = _row(
        guardrail="coc",
        lever="rent_per_unit_month",
        baseline_value=1412.5,
        target_value=1422.5,
        delta=10.0,
        relative_change=0.00708,
        closes_guardrail=True,
    )
    other = _row(
        guardrail="dscr",
        lever="purchase_price",
        baseline_value=605_000.0,
        target_value=552_300.0,
        delta=-52_700.0,
        relative_change=0.0871,
        closes_guardrail=True,
        also_closes=("coc",),
    )
    analysis = _analysis(cheapest=cheapest, failing=("dscr", "coc"), remaining=("dscr",), levers=(cheapest, other))
    forecast = _forecast_with(dscr=1.10, coc=0.0277)
    market = make_market_assumptions()

    first = _render_recourse(analysis, forecast, market)
    second = _render_recourse(analysis, forecast, market)
    assert first == second


def test_82_champlain_sample_deal_end_to_end_report_is_deterministic_and_renders_all_three_shapes():
    """The Mission 4 sample deal (data/sample_listings/82_champlain_dieppe): a realistic 4-unit
    near-miss that genuinely opens the recourse gate and exercises a plausible closing lever, a
    flagged closing lever, and a multi-guardrail 'cheapest fix, other gaps remain' case -- see the
    directory's own README.md for why these specific numbers were chosen."""
    from src.core.finance.engine import run_financial_model
    from src.inputs.inputs import load_inputs
    from src.market.recourse import compute_recourse, is_genuinely_close

    app = load_inputs("data/sample_listings/82_champlain_dieppe/inputs.json")
    inputs = app.inputs
    assert is_genuinely_close(inputs)

    forecast = run_financial_model(inputs)
    analysis = compute_recourse(inputs)
    assert analysis.honest_null is False
    assert set(analysis.failing_guardrails) == {"dscr", "spread", "coc"}
    assert analysis.cheapest is not None and analysis.cheapest.plausible is True
    assert analysis.remaining_after_cheapest != ()

    # At least one plausible AND one flagged closing row somewhere in the analysis.
    assert any(r.closes_guardrail and r.plausible for r in analysis.levers)
    assert any(r.closes_guardrail and not r.plausible for r in analysis.levers)

    insights = make_listing_insights(address="82 Champlain Street")
    from src.agents.chief_strategist import synthesize_thesis

    thesis = synthesize_thesis(forecast, market=inputs.market)

    first = generate_report(insights, forecast, thesis, market=inputs.market, recourse=analysis)
    second = generate_report(insights, forecast, thesis, market=inputs.market, recourse=analysis)
    assert first == second
    assert "## What would have to change?" in first
    assert "Flagged —" in first
    assert "**Other gaps remain:" in first
