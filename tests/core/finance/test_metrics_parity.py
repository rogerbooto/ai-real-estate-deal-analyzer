# tests/core/finance/test_metrics_parity.py
"""
LIGHT-PATH PARITY — the safety net for `engine.forecast_metrics` (Mission 4, task PV.3).

WHY THIS FILE IS NON-NEGOTIABLE
-------------------------------
`src/market/recourse.py` re-runs the engine hundreds of times per analysis and reads a handful of
scalars off each result. Building the ~100 fully-populated `YearBreakdown` objects for every one
of those probes is, once the rent-roll sum is hoisted, the single largest cost in the run. So the
engine now has a second entry point, `forecast_metrics`, which runs the SAME forecast and returns
only those scalars.

Two entry points that both answer "what is this deal's DSCR?" is exactly the failure shape this
codebase has already been bitten by twice and ruled on twice (see `spread_target_for` and the
cap-floor comment block in `chief_strategist.synthesize_thesis`): two computations that agree
today and quietly stop agreeing later. The structural defence is that there is only ONE
implementation -- `engine._forecast_core` -- and `want_rows` gates a single `list.append`, no
arithmetic. THIS FILE is the executable proof of that, and the alarm if anyone ever forks it.

BIT-FOR-BIT, NOT `approx`
-------------------------
Floats are compared through `struct.pack("<d", ...)`, i.e. on their raw IEEE-754 bytes. That is
strictly stronger than `==`: it also distinguishes `0.0` from `-0.0` (which compare equal) and
does not silently pass `nan`. If the light path ever differs from the full path in the 17th
significant digit, this file goes red.

MATRIX
------
The same 34 `CASES` the bit-exact golden harness pins (`tests/core/finance/golden_cases.py`),
reused deliberately rather than re-invented: whatever input diversity is good enough to pin the
shipped numbers is good enough to pin the two paths against each other.
"""

from __future__ import annotations

import struct
from dataclasses import fields
from typing import Any

import pytest

from src.agents.chief_strategist import guardrail_checks, guardrail_checks_from_metrics
from src.core.finance.engine import ForecastMetrics, forecast_metrics, metrics_of, precompute_income, run_financial_model
from src.schemas.models import FinancialInputs, ListingInsights, MarketAssumptions
from tests.core.finance.golden_cases import CASE_IDS, CASES

_CASES_BY_ID: dict[str, dict[str, Any]] = {c["id"]: c for c in CASES}


def _bits(value: object) -> object:
    """Raw IEEE-754 bytes for a float; the value itself for anything else.

    Stronger than `==`: `0.0 == -0.0` is True but their bytes differ, and `nan != nan` while
    their bytes match. Either divergence would be a real change in a shipped number.
    """
    if isinstance(value, float):
        return struct.pack("<d", value)
    return value


def _fingerprint(metrics: ForecastMetrics) -> tuple[tuple[str, object], ...]:
    return tuple((f.name, _bits(getattr(metrics, f.name))) for f in fields(metrics))


def _inputs_for(case: dict[str, Any]) -> tuple[FinancialInputs, ListingInsights | None, int]:
    fi = FinancialInputs.model_validate(case["financial_inputs"])
    insights = ListingInsights.model_validate(case["insights"]) if case.get("insights") else None
    return fi, insights, case["horizon_years"]


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_light_path_matches_full_path_bit_for_bit(case_id: str) -> None:
    """`forecast_metrics(...)` == `metrics_of(run_financial_model(...))`, on the raw float bytes."""
    fi, insights, horizon = _inputs_for(_CASES_BY_ID[case_id])

    full = metrics_of(run_financial_model(fi, horizon_years=horizon, insights=insights))
    light = forecast_metrics(fi, horizon_years=horizon, insights=insights)

    assert _fingerprint(light) == _fingerprint(full)


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_light_path_matches_full_path_with_precomputed_income(case_id: str) -> None:
    """The rent-roll precompute is a performance hint only: it must not move a single bit, on
    either path. (Cases whose insights rebuild income internally cannot take a precompute at all --
    the engine raises for those, which is itself the guarantee, so they are skipped here.)"""
    fi, insights, horizon = _inputs_for(_CASES_BY_ID[case_id])
    pre = precompute_income(fi.income)

    baseline = metrics_of(run_financial_model(fi, horizon_years=horizon, insights=insights))
    try:
        light = forecast_metrics(fi, horizon_years=horizon, insights=insights, precomputed_income=pre)
        full = metrics_of(run_financial_model(fi, horizon_years=horizon, insights=insights, precomputed_income=pre))
    except ValueError as exc:  # insight-driven income uplift rebuilt the IncomeModel
        assert "different IncomeModel" in str(exc)
        pytest.skip("insights rebuild income internally; a precompute is correctly refused here")

    assert _fingerprint(light) == _fingerprint(baseline)
    assert _fingerprint(full) == _fingerprint(baseline)


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_guardrail_booleans_agree_on_both_paths(case_id: str) -> None:
    """The seven guardrail booleans -- the thing the recourse search actually branches on -- are
    identical whether they came off a full forecast or off the light path."""
    fi, insights, horizon = _inputs_for(_CASES_BY_ID[case_id])
    market: MarketAssumptions = fi.market

    forecast = run_financial_model(fi, horizon_years=horizon, insights=insights)
    light = forecast_metrics(fi, horizon_years=horizon, insights=insights)

    assert guardrail_checks_from_metrics(light, market) == guardrail_checks(forecast, market)


def test_metrics_carries_every_scalar_the_guardrail_layer_reads() -> None:
    """Drift guard on the CONTRACT, not the values: if a new guardrail starts reading a number
    that `ForecastMetrics` does not carry, the light path would have to grow a second way of
    getting it -- which is the thing this whole design exists to prevent. Pin the field set so
    that addition is a deliberate, reviewed edit rather than an accident.
    """
    assert {f.name for f in fields(ForecastMetrics)} == {
        "cap_rate",
        "coc",
        "purchase_dscr",
        "year1_dscr",
        "spread_vs_rate",
        "irr_10yr",
        "cash_flow_y1",
        "min_cash_flow",
        "all_cash_flows_nonneg",
        "warnings",
    }
