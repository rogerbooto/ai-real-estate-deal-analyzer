# tests/core/reports/test_report_scenarios.py
"""Tests for the opt-in "Market Scenarios" report section (Mission 1, Wave 2, Task 2.4).

Covers:
- DEFAULT-OFF byte-identical guarantee (G2): passing ``scenarios=None`` alters zero bytes.
- Section render: heading, verbatim honesty block (G1), label discipline (G4), caveats (G3),
  cap_rate_purchase_applied visible (G5), str_viability narrative-flag-only (G4).
- IO caveat renders only when io_years > 0 (G3).
- Empty-set state renders the honest "no admissible scenarios" copy, no fabricated bands (§7).
"""

from __future__ import annotations

from src.core.reports.generator import ABOUT_SCENARIOS_BLOCK, generate_report
from src.schemas.models import (
    ScenarioAnalysis,
    ScenarioMetricBand,
    ScenarioOutcome,
)
from tests.utils import make_hypothesis, make_listing_insights, make_minimal_forecast, make_snapshot


def _band() -> ScenarioMetricBand:
    return ScenarioMetricBand(p25=0.81, p50=0.86, mean=0.85, min=0.76, max=0.93)


def _outcome(*, prior: float, str_viability: bool, cap_applied: float | None = 0.0635) -> ScenarioOutcome:
    return ScenarioOutcome(
        hypothesis=make_hypothesis(
            rent_delta=0.01,
            expense_growth_delta=0.0,
            interest_rate_delta=0.0,
            cap_rate_delta=0.0,
            vacancy_delta=0.0,
            str_viability=str_viability,
            prior=prior,
        ),
        rent_growth_applied=0.04,
        expense_growth_applied=0.02,
        interest_rate_applied=0.055,
        occupancy_applied=0.95,
        cap_rate_purchase_applied=cap_applied,
        dscr_y1=0.87,
        coc_y1=-0.1267,
        cash_flow_y1=-3798.94,
        irr_10yr=0.1534,
        equity_multiple_10yr=2.10,
    )


def _analysis(*, io_years: int = 0, str_flag: bool = False, n_accepted: int = 2) -> ScenarioAnalysis:
    outcomes = tuple(_outcome(prior=0.6 - 0.1 * i, str_viability=(str_flag and i == 0)) for i in range(n_accepted))
    return ScenarioAnalysis(
        snapshot=make_snapshot(region="Moncton, NB"),
        seed=42,
        io_years=io_years,
        n_generated=189,
        n_accepted=n_accepted,
        prior_sum=sum(o.hypothesis.prior for o in outcomes),
        outcomes=outcomes,
        dscr=_band(),
        coc=_band(),
        cash_flow_y1=_band(),
        irr_10yr=_band(),
        equity_multiple_10yr=_band(),
        notes=None,
    )


def _empty_analysis() -> ScenarioAnalysis:
    return ScenarioAnalysis(
        snapshot=make_snapshot(region="Moncton, NB"),
        seed=42,
        io_years=0,
        n_generated=243,
        n_accepted=0,
        prior_sum=0.0,
        outcomes=(),
        dscr=None,
        coc=None,
        cash_flow_y1=None,
        irr_10yr=None,
        equity_multiple_10yr=None,
        notes="All generated hypotheses violated the cap-rate guardrail (0.03 <= cap <= 0.12) after applying deltas.",
    )


# ---------------------------------------------------------------------------
# DEFAULT-OFF byte-identical guarantee (C2 / G2)
# ---------------------------------------------------------------------------


def test_scenarios_off_is_byte_identical() -> None:
    insights = make_listing_insights(address="123 Main St")
    forecast = make_minimal_forecast()
    thesis = None

    baseline = generate_report(insights, forecast, thesis)
    with_none = generate_report(insights, forecast, thesis, scenarios=None)

    assert baseline == with_none
    assert "Market Scenarios" not in baseline


# ---------------------------------------------------------------------------
# Section render (G1/G3/G4/G5)
# ---------------------------------------------------------------------------


def test_section_present_and_last() -> None:
    md = generate_report(make_listing_insights(), make_minimal_forecast(), None, scenarios=_analysis())
    assert "## Market Scenarios" in md
    # Section is appended last: nothing but the scenarios heading after the Warnings/Returns block.
    assert md.rstrip().index("## Market Scenarios") > md.index("## Returns Summary")


def test_verbatim_honesty_block_present() -> None:
    md = generate_report(make_listing_insights(), make_minimal_forecast(), None, scenarios=_analysis())
    # Byte-for-byte from the module-level constant.
    assert ABOUT_SCENARIOS_BLOCK in md


def test_band_label_discipline() -> None:
    md = generate_report(make_listing_insights(), make_minimal_forecast(), None, scenarios=_analysis())
    assert "downside (p25)" in md
    assert "median (p50)" in md
    assert "mean (expected)" in md
    # p50 must never be labeled "expected".
    assert "median (expected)" not in md
    assert "p50 (expected)" not in md


def test_provenance_line_seed_is_provenance_only() -> None:
    md = generate_report(make_listing_insights(), make_minimal_forecast(), None, scenarios=_analysis())
    assert "seed 42 (provenance only" in md
    assert "not randomized by the seed" in md


def test_cap_rate_applied_column_visible() -> None:
    md = generate_report(make_listing_insights(), make_minimal_forecast(), None, scenarios=_analysis())
    assert "Cap rate (applied)" in md
    assert "6.35%" in md  # 0.0635 applied cap rendered


def test_always_on_caveats_render() -> None:
    md = generate_report(make_listing_insights(), make_minimal_forecast(), None, scenarios=_analysis())
    assert "**Caveats**" in md
    assert "heuristic penalty weights, not probabilities" in md
    assert "terminal-value / cap-rate dominated" in md
    assert "applied to both the acquisition loan and the year-5 refinance loan" in md


def test_io_caveat_omitted_when_io_zero() -> None:
    md = generate_report(make_listing_insights(), make_minimal_forecast(), None, scenarios=_analysis(io_years=0))
    assert "interest-only period" not in md


def test_io_caveat_present_when_io_positive() -> None:
    md = generate_report(make_listing_insights(), make_minimal_forecast(), None, scenarios=_analysis(io_years=3))
    assert "interest-only period" in md
    assert "understate the debt load once amortization begins" in md


def test_str_viability_narrative_flag_only() -> None:
    # When flagged, it appears in a clearly separated note with the literal label — never as a numeric column.
    md = generate_report(make_listing_insights(), make_minimal_forecast(), None, scenarios=_analysis(str_flag=True))
    assert "**Narrative flags (not modeled)**" in md
    assert "not modeled — narrative flag only" in md


def test_str_viability_note_omitted_when_no_flag() -> None:
    md = generate_report(make_listing_insights(), make_minimal_forecast(), None, scenarios=_analysis(str_flag=False))
    assert "Narrative flags (not modeled)" not in md


# ---------------------------------------------------------------------------
# Empty-set state (§7)
# ---------------------------------------------------------------------------


def test_empty_set_renders_no_admissible_copy() -> None:
    md = generate_report(make_listing_insights(), make_minimal_forecast(), None, scenarios=_empty_analysis())
    assert "## Market Scenarios" in md
    assert ABOUT_SCENARIOS_BLOCK in md  # honesty block still renders
    assert "**No admissible scenarios under the current guardrails.**" in md
    assert "No numbers are fabricated." in md
    assert "cap-rate guardrail" in md  # rejector notes rendered verbatim
    # No bands / grid tables fabricated.
    assert "downside (p25)" not in md
    assert "Scenario grid" not in md
