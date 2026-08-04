# tests/core/reports/test_report_observation_impact.py
"""
The two-picture "Adjustments Applied" section: baseline vs observation-influenced.

Listing observations (condition tags, defects, amenities) reach the numbers only through the
engine's fixed insight modifiers — an observation selects a rule, it never computes anything. Once
applied, the adjustment is baked into every downstream figure with nothing on the page to compare
it against. This section renders the same deal re-run with those observations suppressed, plus the
engine's own per-line attribution for each one.

The tests below pin the three designed states:

* observations fired **and** a baseline is available -> the full comparison,
* observations fired with **no** baseline (e.g. ``report_cli``, which holds a forecast but not the
  inputs behind it) -> exactly the pre-existing notes list, byte for byte,
* **no** observations fired -> nothing at all, which is what keeps the default report unchanged.
"""

from __future__ import annotations

import pytest

from src.core.reports.baseline import BaselineOutlook
from src.core.reports.generator import generate_report
from src.schemas.models import InvestmentThesis, ListingInsights, RunProvenance

OBSERVED_INSIGHTS = ListingInsights(
    address="123 Test St",
    condition_tags=["old roof"],
    defects=["water stain"],
)


def _provenance(*, vision: bool) -> RunProvenance:
    return RunProvenance(engine="deterministic", scenarios_enabled=False, vision_enabled=vision, config_path=None)


@pytest.fixture
def observed_and_baseline(baseline_forecast):
    """A forecast whose Year 1 carries real modifier notes, plus its observation-free counterpart."""
    observed = baseline_forecast(insights=OBSERVED_INSIGHTS)
    base = baseline_forecast()  # insights=None -> no modifier fires
    # Fails loudly (not silently) if the engine's modifier vocabulary ever changes underneath this.
    assert observed.years[0].notes, "fixture no longer trips the insight modifiers - update the test"
    assert not base.years[0].notes
    return observed, base


def test_section_shows_both_pictures_with_per_line_attribution(observed_and_baseline, listing_insights_baseline):
    """
    RED on revert: without the baseline wiring the report shows only the adjusted figures and the
    reader has no way to see what the observations cost, or to separate the observation-dependent
    part of the analysis from the rest.
    """
    observed, base = observed_and_baseline
    md = generate_report(
        listing_insights_baseline,
        observed,
        baseline=BaselineOutlook(forecast=base),
    )

    # Both columns are named, and the sign convention for the third is stated rather than assumed.
    assert "| Metric | Baseline | With observations | Change |" in md
    assert "**Year 1 impact** _(Change = with observations − baseline.)_" in md

    b1, o1 = base.years[0], observed.years[0]
    # Every figure an investor acts on, each traceable to the two forecasts it came from.
    assert f"| Total OPEX | ${b1.total_opex:,.2f} | ${o1.total_opex:,.2f} | +$500.00 |" in md
    assert f"| NOI | ${b1.noi:,.2f} | ${o1.noi:,.2f} | -$500.00 |" in md
    assert f"| Cash flow | ${b1.cash_flow:,.2f} | ${o1.cash_flow:,.2f} | -$500.00 |" in md
    # GOI closes NOI = GOI - OPEX on the page: no OPEX rule touches income, so it moves by zero here.
    assert f"| GOI | ${b1.goi:,.2f} | ${o1.goi:,.2f} | $0.00 |" in md
    for label in ("| Cap rate |", "| DSCR |", "| Cash-on-cash |"):
        assert label in md

    # Per-line attribution: each delta names the observation that caused it, verbatim from the engine.
    assert "**What moved each figure**" in md
    assert "- Year 1: condition: old roof → reserves +$300/yr" in md
    assert "- Year 1: defect: water stain → R&M +$200/yr" in md

    # The standing caveat travels with the comparison, not as a footnote somewhere else.
    assert "**About these observations.**" in md
    assert "an observation can be wrong" in md
    assert "not a quote or a measured cost" in md


def test_verdict_row_reports_whether_the_decision_moved(observed_and_baseline, listing_insights_baseline):
    """The one row that can change the answer rather than a figure behind it."""
    observed, base = observed_and_baseline
    unchanged = generate_report(
        listing_insights_baseline,
        observed,
        InvestmentThesis(verdict="DECLINE", rationale=["r"], levers=[]),
        baseline=BaselineOutlook(forecast=base, thesis=InvestmentThesis(verdict="DECLINE", rationale=["r"], levers=[])),
    )
    assert "| Verdict | DECLINE | DECLINE | unchanged |" in unchanged

    changed = generate_report(
        listing_insights_baseline,
        observed,
        InvestmentThesis(verdict="DECLINE", rationale=["r"], levers=[]),
        baseline=BaselineOutlook(forecast=base, thesis=InvestmentThesis(verdict="CONDITIONAL", rationale=["r"], levers=[])),
    )
    assert "| Verdict | CONDITIONAL | DECLINE | **changed** |" in changed


def test_verdict_row_omitted_when_no_baseline_verdict_was_computed(observed_and_baseline, listing_insights_baseline):
    """Designed state, not a gap: no baseline thesis means no verdict row rather than an invented one."""
    observed, base = observed_and_baseline
    md = generate_report(
        listing_insights_baseline,
        observed,
        InvestmentThesis(verdict="DECLINE", rationale=["r"], levers=[]),
        baseline=BaselineOutlook(forecast=base, thesis=None),
    )
    assert "| Metric | Baseline | With observations | Change |" in md
    assert "| Verdict |" not in md


@pytest.mark.parametrize("vision", [True, False], ids=["vision-on", "vision-off"])
def test_ai_is_named_only_when_provenance_says_it_ran(observed_and_baseline, listing_insights_baseline, vision):
    """
    The report cannot tell an LLM-authored tag from a keyword match, so it claims AI involvement
    exactly when provenance records the AI photo path was active — and stays silent about models
    otherwise rather than asserting "no AI was involved", which it has no standing to say.
    """
    observed, base = observed_and_baseline
    md = generate_report(
        listing_insights_baseline,
        observed,
        baseline=BaselineOutlook(forecast=base),
        provenance=_provenance(vision=vision),
    )

    if vision:
        assert "| Metric | Baseline | With observations (AI-assisted) | Change |" in md
        assert "AI photo tagging was on for this run (`AIREAL_USE_VISION`)" in md
    else:
        assert "| Metric | Baseline | With observations | Change |" in md
        assert "AI-assisted" not in md
        # Scoped to the section: the Run Provenance appendix always names the env var (as "off").
        section = md[md.index("## Adjustments Applied") :].split("\n## ")[0]
        assert "AIREAL_USE_VISION" not in section


def test_no_baseline_renders_exactly_the_pre_existing_notes_section(observed_and_baseline, listing_insights_baseline):
    """
    Byte-level guarantee for callers that cannot produce a baseline (``report_cli`` holds a
    forecast but not the inputs behind it). They get the traceability trail unchanged — not a
    fabricated comparison, and not a silently different section.
    """
    observed, _ = observed_and_baseline
    md = generate_report(listing_insights_baseline, observed)

    expected = (
        "## Adjustments Applied\n"
        "\n"
        "Notes below explain why a year's OPEX or income differs from the raw inputs — each line "
        "names the condition tag, defect, or amenity that triggered it. These are already reflected "
        "in the figures above; nothing here changes a number, it only explains one.\n"
        "\n"
        "- Year 1: condition: old roof → reserves +$300/yr\n"
        "- Year 1: defect: water stain → R&M +$200/yr\n"
    )
    assert expected in md
    assert "About these observations" not in md
    assert "| Metric | Baseline |" not in md


def test_no_observations_emits_nothing_even_when_a_baseline_is_supplied(baseline_forecast, listing_insights_baseline):
    """
    The default path, and the hard requirement: with no observation in play the report must be what
    it was before this feature existed. Supplying a baseline anyway must not conjure a section
    comparing a deal to itself.
    """
    forecast = baseline_forecast()
    assert all(not y.notes for y in forecast.years)

    without = generate_report(listing_insights_baseline, forecast, provenance=_provenance(vision=True))
    with_baseline = generate_report(
        listing_insights_baseline,
        forecast,
        baseline=BaselineOutlook(forecast=forecast, thesis=InvestmentThesis(verdict="DECLINE", rationale=["r"], levers=[])),
        provenance=_provenance(vision=True),
    )

    assert without == with_baseline
    assert "Adjustments Applied" not in with_baseline
