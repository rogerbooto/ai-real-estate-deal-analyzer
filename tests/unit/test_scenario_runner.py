# tests/unit/test_scenario_runner.py

from __future__ import annotations

import pytest

from src.market.scenario_runner import resolve_snapshot, run_scenarios
from src.schemas.models import ScenarioAnalysis
from tests.utils import make_financial_inputs, make_market_assumptions, make_snapshot


def test_run_scenarios_priors_sum_to_one() -> None:
    fi = make_financial_inputs()
    snapshot = make_snapshot(cap_rate=0.065, vacancy_rate=0.05)

    analysis = run_scenarios(fi, snapshot, seed=42)

    assert analysis.n_accepted > 0
    assert analysis.n_accepted == len(analysis.outcomes)
    assert abs(analysis.prior_sum - 1.0) <= 1e-12
    # accepted-set priors as carried on outcomes also sum to 1
    assert abs(sum(o.hypothesis.prior for o in analysis.outcomes) - 1.0) <= 1e-12


def test_run_scenarios_bands_present_and_ordered() -> None:
    fi = make_financial_inputs()
    snapshot = make_snapshot(cap_rate=0.065, vacancy_rate=0.05)

    analysis = run_scenarios(fi, snapshot, seed=42)

    for band in (analysis.dscr, analysis.coc, analysis.cash_flow_y1, analysis.irr_10yr, analysis.equity_multiple_10yr):
        assert band is not None
        # min <= p25 <= max and min <= p50 <= max (inverse-CDF picks an observed value)
        assert band.min <= band.p25 <= band.max
        assert band.min <= band.p50 <= band.max
        assert band.min <= band.mean <= band.max


def test_run_scenarios_determinism() -> None:
    fi = make_financial_inputs()
    snapshot = make_snapshot(cap_rate=0.065, vacancy_rate=0.05)

    a = run_scenarios(fi, snapshot, seed=42)
    b = run_scenarios(fi, snapshot, seed=42)

    assert a.model_dump() == b.model_dump()


def test_run_scenarios_empty_accepted_set() -> None:
    # A cap far above the rejector ceiling (0.12) forces all hypotheses to be rejected.
    fi = make_financial_inputs()
    snapshot = make_snapshot(cap_rate=0.20, vacancy_rate=0.05)

    analysis = run_scenarios(fi, snapshot, seed=42)

    assert analysis.n_accepted == 0
    assert analysis.outcomes == ()
    assert analysis.prior_sum == 0.0
    assert analysis.dscr is None
    assert analysis.coc is None
    assert analysis.cash_flow_y1 is None
    assert analysis.irr_10yr is None
    assert analysis.equity_multiple_10yr is None
    assert analysis.notes is not None
    assert isinstance(analysis, ScenarioAnalysis)


def test_weighted_p25_is_lower_tail() -> None:
    fi = make_financial_inputs()
    snapshot = make_snapshot(cap_rate=0.065, vacancy_rate=0.05)

    analysis = run_scenarios(fi, snapshot, seed=42)

    # downside (p25) must not exceed the median (p50) for a higher-is-better metric
    assert analysis.dscr is not None and analysis.cash_flow_y1 is not None
    assert analysis.dscr.p25 <= analysis.dscr.p50
    assert analysis.cash_flow_y1.p25 <= analysis.cash_flow_y1.p50


def test_run_scenarios_carries_io_years() -> None:
    # io_years is invariant across scenarios (the adapter never perturbs the term); the runner
    # carries the untouched-inputs value so the report can render the interest-only caveat.
    fi = make_financial_inputs()
    snapshot = make_snapshot(cap_rate=0.065, vacancy_rate=0.05)

    analysis = run_scenarios(fi, snapshot, seed=42)
    assert analysis.io_years == fi.financing.io_years

    # with an interest-only period set, the value propagates unchanged (drives §7a #6 IO caveat)
    fi_io = fi.model_copy(update={"financing": fi.financing.model_copy(update={"io_years": 3})})
    analysis_io = run_scenarios(fi_io, snapshot, seed=42)
    assert analysis_io.io_years == 3


def test_resolve_snapshot_explicit_block() -> None:
    fi = make_financial_inputs()
    block = {
        "region": "Moncton, NB",
        "vacancy_rate": 0.06,
        "cap_rate": 0.055,
        "rent_growth": 0.03,
        "expense_growth": 0.02,
        "interest_rate": 0.055,
    }
    snap = resolve_snapshot(fi, market_block=block)
    assert snap.region == "Moncton, NB"
    assert snap.cap_rate == 0.055


def test_resolve_snapshot_fallback_derivation() -> None:
    fi = make_financial_inputs()
    # give a cap so derivation succeeds
    fi = fi.model_copy(update={"market": make_market_assumptions(cap_rate_purchase=0.06)})

    snap = resolve_snapshot(fi)
    assert snap.region == "Unspecified"
    assert snap.cap_rate == 0.06
    assert snap.vacancy_rate == pytest.approx(1.0 - fi.income.occupancy, abs=1e-12)
    assert snap.rent_growth == fi.income.rent_growth
    assert snap.expense_growth == fi.opex.expense_growth
    assert snap.interest_rate == fi.financing.interest_rate


def test_resolve_snapshot_loud_fail_when_cap_underivable() -> None:
    fi = make_financial_inputs()  # market.cap_rate_purchase defaults to None
    assert fi.market.cap_rate_purchase is None
    with pytest.raises(ValueError, match="cap_rate_purchase"):
        resolve_snapshot(fi)
