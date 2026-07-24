# tests/integration/test_scenarios_e2e.py
"""End-to-end integration for the Market Scenarios overlay (Mission 1 DoD).

Unlike ``tests/core/reports/test_report_scenarios.py`` (which renders a *hand-built*
``ScenarioAnalysis``), these tests drive the **actual pipeline path**:

    FinancialInputs -> resolve_snapshot -> run_scenarios -> generate_report / write_report

so a regression anywhere along the runner -> aggregator -> renderer chain turns them RED.

Covers two DoD items that had no coupling test:
  1. An end-to-end test through ``run_scenarios`` into the report, asserting the rendered
     "Market Scenarios" section is present with sane, *traceable* content.
  2. Determinism on the RENDERED report bytes (not just the model dump): a fixed seed yields
     byte-identical report output across two independent full runs.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from src.core.finance import run_financial_model
from src.core.reports.generator import ABOUT_SCENARIOS_BLOCK, generate_report, write_report
from src.market.scenario_runner import resolve_snapshot, run_scenarios
from tests.utils import make_financial_inputs, make_listing_insights

_MARKET_BLOCK: Mapping[str, Any] = {
    "region": "Moncton, NB",
    "vacancy_rate": 0.06,
    "cap_rate": 0.065,
    "rent_growth": 0.03,
    "expense_growth": 0.02,
    "interest_rate": 0.055,
}


def _render_full_path(*, seed: int = 42) -> str:
    """Run the real pipeline path once and return the rendered Markdown report."""
    fi = make_financial_inputs()
    snapshot = resolve_snapshot(fi, market_block=_MARKET_BLOCK)
    analysis = run_scenarios(fi, snapshot, seed=seed)
    forecast = run_financial_model(fi)
    insights = make_listing_insights(address="123 Main St")
    return generate_report(insights, forecast, None, scenarios=analysis)


# ---------------------------------------------------------------------------
# (1) End-to-end: run_scenarios -> report, with traceable content
# ---------------------------------------------------------------------------


def test_e2e_run_scenarios_renders_section_with_traceable_content() -> None:
    fi = make_financial_inputs()
    snapshot = resolve_snapshot(fi, market_block=_MARKET_BLOCK)
    analysis = run_scenarios(fi, snapshot, seed=42)

    # Precondition: this drove a real, non-empty analysis (not the empty-set path).
    assert analysis.n_accepted > 0
    assert analysis.dscr is not None
    assert abs(analysis.prior_sum - 1.0) <= 1e-12

    forecast = run_financial_model(fi)
    md = generate_report(make_listing_insights(address="123 Main St"), forecast, None, scenarios=analysis)

    # Section is present and the honesty block is verbatim.
    assert "## Market Scenarios" in md
    assert ABOUT_SCENARIOS_BLOCK in md

    # Snapshot provenance from the resolved snapshot flows into the rendered report.
    assert "Moncton, NB" in md
    assert "seed 42 (provenance only" in md

    # Traceable numbers: the admitted/generated counts AND a band value produced by the
    # aggregator must appear verbatim. If the renderer fabricated or mislabeled numbers,
    # or the runner produced a different analysis, these break.
    assert f"{analysis.n_accepted} of {analysis.n_generated} " in md
    assert f"{analysis.dscr.p50:.2f}" in md

    # Non-empty analysis renders the band grid, not the empty-set copy.
    assert "downside (p25)" in md
    assert "No admissible scenarios under the current guardrails." not in md


def test_e2e_write_report_file_matches_generate_report(tmp_path: Path) -> None:
    fi = make_financial_inputs()
    snapshot = resolve_snapshot(fi, market_block=_MARKET_BLOCK)
    analysis = run_scenarios(fi, snapshot, seed=42)
    forecast = run_financial_model(fi)
    insights = make_listing_insights(address="123 Main St")

    expected = generate_report(insights, forecast, None, scenarios=analysis)

    out = tmp_path / "report.md"
    write_report(out, insights, forecast, scenarios=analysis)

    # write_report must persist exactly what generate_report produces, byte for byte.
    assert out.read_text(encoding="utf-8") == expected
    assert "## Market Scenarios" in out.read_text(encoding="utf-8")


def test_e2e_fallback_snapshot_path_also_renders() -> None:
    # Exercise the resolve_snapshot FALLBACK derivation (no market block): requires a
    # derivable cap on the inputs. This is the second production entry into run_scenarios.
    fi = make_financial_inputs()
    fi = fi.model_copy(update={"market": fi.market.model_copy(update={"cap_rate_purchase": 0.06})})

    snapshot = resolve_snapshot(fi)  # derived, region "Unspecified"
    analysis = run_scenarios(fi, snapshot, seed=42)
    forecast = run_financial_model(fi)
    md = generate_report(make_listing_insights(), forecast, None, scenarios=analysis)

    assert "## Market Scenarios" in md
    assert "Unspecified" in md
    assert f"{analysis.n_accepted} of {analysis.n_generated} " in md


# ---------------------------------------------------------------------------
# (2) Determinism on the RENDERED report bytes (fixed seed, two full runs)
# ---------------------------------------------------------------------------


def test_e2e_report_bytes_deterministic_across_two_runs() -> None:
    md1 = _render_full_path(seed=42)
    md2 = _render_full_path(seed=42)

    # Byte-identical rendered report across two independent full pipeline runs.
    assert md1 == md2
    assert md1.encode("utf-8") == md2.encode("utf-8")

    # Guard against a trivially-empty section masking the determinism claim.
    assert "## Market Scenarios" in md1
    assert "downside (p25)" in md1


def test_e2e_report_file_bytes_deterministic(tmp_path: Path) -> None:
    fi = make_financial_inputs()
    snapshot = resolve_snapshot(fi, market_block=_MARKET_BLOCK)
    forecast = run_financial_model(fi)
    insights = make_listing_insights(address="123 Main St")

    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    write_report(a, insights, forecast, scenarios=run_scenarios(fi, snapshot, seed=42))
    write_report(b, insights, forecast, scenarios=run_scenarios(fi, snapshot, seed=42))

    assert a.read_bytes() == b.read_bytes()


@pytest.mark.parametrize("seed", [1, 7, 42, 1000])
def test_e2e_determinism_holds_for_multiple_seeds(seed: int) -> None:
    # The seed is provenance-only (fixed deterministic grid), so the report must be identical
    # for repeated runs at ANY seed value, not just the default.
    assert _render_full_path(seed=seed) == _render_full_path(seed=seed)
