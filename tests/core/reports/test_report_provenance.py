# tests/core/reports/test_report_provenance.py
"""The Run Provenance appendix — the report's record of how it was produced.

`.env` is gitignored and VS Code's Python extension auto-loads it, so two people running the
same command on the same inputs could get different reports with nothing in either one saying
why. This block is the fix, so the load-bearing property is that it CANNOT disagree with the
figures above it: the valuation knobs are read from the same accessors that produced the
valuation tables, never from a value passed in alongside.
"""

from __future__ import annotations

import pytest

from src.core.finance import run_financial_model
from src.core.reports.generator import generate_report
from src.schemas.models import FinancialInputs, ListingInsights, RunProvenance
from tests.utils import make_financial_inputs, make_market_assumptions

_PIPELINE = RunProvenance(
    engine="deterministic",
    scenarios_enabled=False,
    vision_enabled=False,
    config_path="data/sample_listings/36_kelly_moncton/inputs.json",
)


def _render(provenance: RunProvenance | None = _PIPELINE) -> str:
    forecast = run_financial_model(make_financial_inputs())
    return generate_report(ListingInsights(address="36 Kelly"), forecast, None, provenance=provenance)


def _render_for(inputs: FinancialInputs, provenance: RunProvenance | None = _PIPELINE) -> str:
    """Render a report from specific inputs, threading the same market block the run used."""
    return generate_report(
        ListingInsights(address="36 Kelly"),
        run_financial_model(inputs),
        None,
        provenance=provenance,
        market=inputs.market,
    )


def _provenance_block(md: str) -> str:
    start = md.index("## Appendix — Run Provenance")
    return md[start : md.index("## Appendix — Definitions", start)]


def test_section_is_always_present_even_without_pipeline_facts() -> None:
    # The valuation knobs apply to every run, so the block is emitted even when the caller
    # supplies no RunProvenance (e.g. deal-report rendering from JSON artifacts).
    assert "## Appendix — Run Provenance" in _render(provenance=None)


def test_pipeline_facts_are_rendered_when_supplied() -> None:
    block = _provenance_block(_render())
    assert "deterministic" in block
    assert "data/sample_listings/36_kelly_moncton/inputs.json" in block


def test_hardcoded_inputs_are_labelled_rather_than_left_blank() -> None:
    p = _PIPELINE.model_copy(update={"config_path": None})
    assert "(hardcoded demo inputs)" in _provenance_block(_render(p))


@pytest.mark.parametrize(("enabled", "expected"), [(True, "on"), (False, "off")])
def test_boolean_knobs_render_as_on_off(enabled: bool, expected: bool) -> None:
    p = _PIPELINE.model_copy(update={"scenarios_enabled": enabled, "vision_enabled": enabled})
    block = _provenance_block(_render(p))
    assert f"| Market Scenarios | {expected} |" in block
    assert f"| AI photo tagging | {expected} |" in block


# ---------------------------------------------------------------------------
# The property that makes this block trustworthy
# ---------------------------------------------------------------------------


def test_cap_drift_reported_matches_the_drift_actually_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    """A reported knob that disagrees with the tables would be worse than no block at all.

    Mission 2 / 3.2: the NOI table now renders the engine's own cap path, so the drift that
    applies is ``market.cap_rate_drift``, and this block reports the drift read back off that
    path. Pinned against BOTH numbers — the previous version of this test compared against a
    cap rate the fixture never produced, so it passed vacuously and would not have caught the
    live disagreement it existed to catch (env said 0 bps while the engine drifted 300).
    """
    monkeypatch.setenv("AIREAL_CAP_DRIFT_BPS", "5")  # must NOT win over the applied drift
    inputs = make_financial_inputs().model_copy(update={"market": make_market_assumptions(cap_rate_drift=0.01)})
    md = _render_for(inputs)

    assert "| Cap-rate drift | 100 bps/yr | `market.cap_rate_drift` |" in _provenance_block(md)

    # ...and the claimed 100 bps/yr is visible in the NOI table's own cap-rate column.
    noi_table = md[md.index("Valuation – NOI-Based") :]
    year1_cap = run_financial_model(inputs).years[0].cap_rate_applied
    assert year1_cap is not None
    assert f"| 1 | {year1_cap * 100:.2f}%" in noi_table
    assert f"| 2 | {(year1_cap + 0.01) * 100:.2f}%" in noi_table


def test_env_drift_is_reported_only_when_the_forecast_carries_no_cap_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """`deal-report` can be handed forecast JSON that predates the stored cap path.

    That is the one case where the env knob still drives the NOI table, so it is also the one
    case where the block may cite it.
    """
    monkeypatch.setenv("AIREAL_CAP_DRIFT_BPS", "5")
    forecast = run_financial_model(make_financial_inputs())
    legacy = forecast.model_copy(update={"years": [y.model_copy(update={"cap_rate_applied": None}) for y in forecast.years]})
    md = generate_report(ListingInsights(address="36 Kelly"), legacy, None, provenance=_PIPELINE)

    assert "| Cap-rate drift | 5 bps/yr | `AIREAL_CAP_DRIFT_BPS` |" in _provenance_block(md)


def test_appreciation_reported_matches_the_baseline_heading(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIREAL_APPRECIATION_PCT", "0.05")
    md = _render()

    assert "| Baseline appreciation | 5.00% |" in _provenance_block(md)
    assert "g = 5.00%" in md, "appreciation claimed in provenance but not used by the baseline track"


def test_defaults_are_reported_when_no_env_is_set(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("AIREAL_CAP_DRIFT_BPS", "AIREAL_APPRECIATION_PCT", "AIREAL_STRESS_ADJ"):
        monkeypatch.delenv(var, raising=False)
    block = _provenance_block(
        _render_for(make_financial_inputs().model_copy(update={"market": make_market_assumptions(cap_rate_drift=0.0)}))
    )

    assert "| Cap-rate drift | 0 bps/yr |" in block
    assert "| Baseline appreciation | 3.00% |" in block
    assert "| Stress basis adjustment | $0.00 |" in block


def test_provenance_precedes_definitions() -> None:
    md = _render()
    assert md.index("## Appendix — Run Provenance") < md.index("## Appendix — Definitions")
