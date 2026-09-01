# tests/perf/test_perf_gates.py
"""The perf GATE (Mission 5 acceleration): the suite now fails when the loop gets slow.

Before this file existed the project measured beautifully and gated nothing on the measurement:
`BUDGET_MS` had no reader outside `bench_finance_engine.py`, that file defines no `test_*`, and
CI had no perf step. These tests are collected by the default `pytest` run (and therefore by
CI's `pytest -q`), so a performance regression on the production recourse loop is now a red
build, not a footnote in a benchmark nobody re-ran.

TIMING DISCIPLINE (the rules that keep a timed assertion honest instead of flaky):

  * BEST-OF-N, NEVER MEDIAN. The best sample is the least-contaminated estimate of the code's
    cost; the median measures the machine. Asserting on it means a busy box has N chances to
    produce one clean sample.
  * BUDGETS CARRY HEADROOM, DELIBERATELY, and each one documents its derivation next to the
    constant. Dev-box measured spread is ~+/-12% and CI hardware is slower still; a budget set
    at the measurement (e.g. Roger's 30 ms TARGET for the ceiling row) would gate noise, not
    regressions. What these budgets actually guard is the acceleration itself: losing the
    `engine.ShiftedIncome` O(1) rent path puts the ceiling row from ~65 ms back above 400 ms --
    1.6x over even the generous budget -- loudly.
  * THE WORKLOAD IS THE PRODUCTION LOOP. Same `build_gate_limit_inputs` deal at the gate's
    limit, same real `compute_recourse`, same committed sample deals as the benchmark's PRIMARY
    table. No synthetic slice is ever the thing gated.
  * COVERAGE TRACING IS DISABLED FOR THE TIMED TESTS (`no_cover`, pytest-cov's own marker). The
    suite runs with `--cov` in `addopts`, and line tracing inflates this loop ~5x (measured:
    ceiling row 65 ms -> 386 ms under the tracer) -- a gate that times instrumented code times
    the instrumentation. Production runs untraced; the gate must too. The marker is applied
    dynamically by `tests/perf/conftest.py::pytest_collection_modifyitems`, not statically here
    with `@pytest.mark.no_cover` -- see that module's docstring for why: pytest-cov 7.0.0's own
    `no_cover` hook unconditionally dereferences `self.cov_controller`, which is permanently
    `None` under `pytest --no-cov`, so a static decorator turns "coverage is already off" into
    an `AttributeError` crash instead of a no-op.
"""

from __future__ import annotations

import gc

import pytest

from src.market.recourse import _SEARCH_GC_THRESHOLD, _search_gc_tuned, compute_recourse
from src.schemas.models import FinancialInputs
from tests.perf.bench_finance_engine import (
    BUDGET_MS,
    SAMPLE_DEALS,
    SAMPLE_HORIZON,
    build_gate_limit_inputs,
    load_sample_deal,
    time_analysis,
)

#: Timing repeats per gated row: enough chances for one clean sample on a busy box, few enough
#: that the whole gate stays in single-digit seconds.
_REPEATS = 5

#: Budget for each committed real deal at its 10y horizon, in milliseconds -- the blast-radius
#: gate: no projection moves these rows, so a breach here means the ENGINE or the probe loop
#: itself regressed, not a workload change.
#:
#: DERIVATION (2026-08-31, dev box, post-acceleration): 36_kelly_moncton best 9.7 ms,
#: 82_champlain_dieppe best 16.8 ms (engine-pass-bound: ~499 probes at ~34 us each -- at 6
#: units the rent seam barely moves this deal). 40 ms is ~2.4x the worst measured best, sized
#: for slower CI hardware. NOTE, HONESTLY: the mission charter proposed 15 ms here, but that
#: figure predates the Half B combination search, which roughly tripled champlain's probe count
#: (135 -> ~499); 16.8 ms is the measured post-acceleration reality on the calibration box, so
#: a 15 ms gate would fail deterministically today. Tightening this budget requires an engine
#: per-pass win, not harness tuning.
REAL_DEAL_BUDGET_MS = 40.0

#: The institutional-ceiling workload, built once per session (the price scan behind
#: `build_gate_limit_inputs` is itself many full 5,000u/100y engine runs).
_CEILING_UNITS = 5_000
_CEILING_HORIZON = 100


@pytest.fixture(scope="module")
def ceiling_deal() -> FinancialInputs:
    fi, failing = build_gate_limit_inputs(_CEILING_UNITS, _CEILING_HORIZON)
    assert len(failing) > 0  # a deal that fires no probes would gate nothing
    return fi


#: Applied dynamically by `tests/perf/conftest.py::pytest_collection_modifyitems`, not here --
#: see that module's docstring for why a static `@pytest.mark.no_cover` crashes `--no-cov`.
class TestRecourseLoopBudgets:
    def test_ceiling_row_within_budget(self, ceiling_deal: FinancialInputs) -> None:
        """The 5,000u/100y row -- the standard Roger set -- against `BUDGET_MS`, best-of-N."""
        best, median = time_analysis(ceiling_deal, _CEILING_HORIZON, repeats=_REPEATS)
        assert best <= BUDGET_MS, (
            f"ceiling recourse row: best {best:.1f} ms > budget {BUDGET_MS:.0f} ms "
            f"(median {median:.1f} ms; if median >> best the box was busy -- re-run before hunting a regression)"
        )

    @pytest.mark.parametrize(("name", "path"), SAMPLE_DEALS)
    def test_real_deal_row_within_budget(self, name: str, path: str) -> None:
        """The committed sample deals -- what an actual analysis costs -- best-of-N."""
        deal = load_sample_deal(path)
        if deal is None:
            pytest.skip(f"{path} not on disk")
        best, median = time_analysis(deal, SAMPLE_HORIZON, repeats=_REPEATS)
        assert best <= REAL_DEAL_BUDGET_MS, (
            f"{name}: best {best:.2f} ms > budget {REAL_DEAL_BUDGET_MS:.0f} ms "
            f"(median {median:.2f} ms; if median >> best the box was busy -- re-run before hunting a regression)"
        )


class TestSearchGcScope:
    """`recourse._search_gc_tuned` is explicit and restorable -- never a hidden global."""

    def test_tunes_inside_and_restores_after(self) -> None:
        before = gc.get_threshold()
        with _search_gc_tuned():
            assert gc.get_threshold() == _SEARCH_GC_THRESHOLD
        assert gc.get_threshold() == before

    def test_restores_on_exception(self) -> None:
        before = gc.get_threshold()
        with pytest.raises(RuntimeError, match="boom"), _search_gc_tuned():
            raise RuntimeError("boom")
        assert gc.get_threshold() == before

    def test_compute_recourse_leaves_no_gc_side_effect(self) -> None:
        """End to end: the public entry point must hand the process back exactly as it found it."""
        deal = load_sample_deal(SAMPLE_DEALS[0][1])
        if deal is None:
            pytest.skip(f"{SAMPLE_DEALS[0][1]} not on disk")
        before = gc.get_threshold()
        compute_recourse(deal, horizon_years=SAMPLE_HORIZON)
        assert gc.get_threshold() == before

    def test_does_not_touch_enable_disable(self) -> None:
        """Only thresholds are scoped; a host that disabled GC must stay disabled."""
        assert gc.isenabled()
        gc.disable()
        try:
            with _search_gc_tuned():
                assert not gc.isenabled()
            assert not gc.isenabled()
        finally:
            gc.enable()
