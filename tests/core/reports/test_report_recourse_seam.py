# tests/core/reports/test_report_recourse_seam.py
"""Mission 4 (task I.3): the report's `recourse` seam now RENDERS (`_render_recourse`,
`src/core/reports/generator.py`) -- this file was I.2's "accept-and-ignore" pin and is updated
here to match. The half that still must never move a single byte: `recourse` OMITTED vs explicit
`None` (both mean "the pre-computation `is_genuinely_close` gate never opened for this deal") are
byte-identical to each other and never contain the section at all. The half that is NEW here: a
fully-populated `RecourseAnalysis` DOES move bytes -- it renders "What would have to change?"
immediately adjacent to the Investment Thesis (Roger's placement decision), never appended after
Warnings.
"""

from __future__ import annotations

from src.core.reports.generator import generate_report
from src.schemas.models import RecourseAnalysis, RecourseLever
from tests.utils import make_listing_insights, make_minimal_forecast


def _a_full_recourse_analysis() -> RecourseAnalysis:
    """A representative, fully-populated analysis (never blanked, never partial) -- shaped like
    what `compute_recourse` actually returns, not a minimal stub."""
    closing_row = RecourseLever(
        guardrail="coc",
        lever="purchase_price",
        baseline_value=399_900.0,
        target_value=341_000.0,
        delta=-58_900.0,
        relative_change=0.1473,
        closes_guardrail=True,
        structurally_hopeless=False,
        plausible=True,
        plausibility_reason=None,
        also_closes=(),
    )
    null_row = RecourseLever(
        guardrail="dscr",
        lever="interest_rate",
        baseline_value=0.055,
        target_value=None,
        delta=None,
        relative_change=None,
        closes_guardrail=False,
        structurally_hopeless=False,
        plausible=True,
        plausibility_reason=None,
        also_closes=(),
    )
    return RecourseAnalysis(
        verdict="DECLINE",
        failing_guardrails=("dscr", "coc"),
        levers=(closing_row, null_row),
        cheapest=closing_row,
        remaining_after_cheapest=("dscr",),
        honest_null=False,
    )


def test_recourse_omitted_and_explicit_none_are_byte_identical_and_absent() -> None:
    """The gate-closed half: omitted vs explicit `None` never differ, and neither ever contains
    the section -- a deal whose `is_genuinely_close` gate never opened gets no section at all."""
    insights = make_listing_insights(address="123 Main St")
    forecast = make_minimal_forecast()

    omitted = generate_report(insights, forecast, None)
    explicit_none = generate_report(insights, forecast, None, recourse=None)

    assert omitted == explicit_none
    assert "What would have to change?" not in omitted


def test_recourse_populated_renders_adjacent_to_the_investment_thesis() -> None:
    """The gate-open half: a real, fully-populated analysis DOES move bytes, and lands right
    after the Investment Thesis section -- not appended after Warnings (Roger's placement
    decision, overriding the founder-proxy's original append-after-Warnings call)."""
    insights = make_listing_insights(address="123 Main St")
    forecast = make_minimal_forecast()

    from src.schemas.models import InvestmentThesis

    thesis = InvestmentThesis(verdict="DECLINE", rationale=["DSCR (Y1) is weak at 0.90 (< 1.20)."], levers=[])
    without = generate_report(insights, forecast, thesis)
    populated = generate_report(insights, forecast, thesis, recourse=_a_full_recourse_analysis())

    assert without != populated
    assert "What would have to change?" in populated

    thesis_idx = populated.index("## Investment Thesis")
    recourse_idx = populated.index("## What would have to change?")
    warnings_idx = populated.find("## Warnings")
    pro_forma_idx = populated.index("Pro Forma (Summary)")

    # Adjacent to the thesis: the recourse heading is the very next `##` heading after it, and it
    # comes BEFORE the Pro Forma table / Warnings section, never appended after them.
    assert thesis_idx < recourse_idx < pro_forma_idx
    if warnings_idx != -1:
        assert recourse_idx < warnings_idx


def test_would_go_red_if_the_section_were_appended_after_warnings_instead() -> None:
    """Demonstrates the placement revert this pins against: appending the section at the END
    (mirroring the founder-proxy's original, overridden call) would still contain the same text
    but in the WRONG position relative to the thesis it explains. Built locally (never by editing
    `src/`) to prove the position assertion above is not vacuous."""
    insights = make_listing_insights(address="123 Main St")
    forecast = make_minimal_forecast()

    from src.schemas.models import InvestmentThesis

    thesis = InvestmentThesis(verdict="DECLINE", rationale=["DSCR (Y1) is weak at 0.90 (< 1.20)."], levers=[])
    base = generate_report(insights, forecast, thesis)
    vetoed_appended_at_end = base.rstrip("\n") + "\n\n## What would have to change?\n(vetoed placement)\n"

    real_populated = generate_report(insights, forecast, thesis, recourse=_a_full_recourse_analysis())

    # In the vetoed shape the section comes AFTER everything, including the appendices.
    vetoed_recourse_idx = vetoed_appended_at_end.index("## What would have to change?")
    vetoed_appendix_idx = vetoed_appended_at_end.index("## Appendix — Definitions")
    assert vetoed_recourse_idx > vetoed_appendix_idx  # THE BUG the real placement avoids

    # ...whereas the REAL renderer (tested above) puts it right after the thesis, well before any
    # appendix.
    real_recourse_idx = real_populated.index("## What would have to change?")
    real_appendix_idx = real_populated.index("## Appendix — Definitions")
    assert real_recourse_idx < real_appendix_idx
