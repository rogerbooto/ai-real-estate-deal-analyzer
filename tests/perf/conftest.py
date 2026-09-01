# tests/perf/conftest.py
"""Collection hooks for the perf gate -- keeps `no_cover` honest under `pytest --no-cov`.

BUG THIS WORKS AROUND (pytest-cov 7.0.0, `pytest_cov/plugin.py::CovPlugin.pytest_runtest_call`):

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item):
        if item.get_closest_marker('no_cover') or 'no_cover' in getattr(item, 'fixturenames', ()):
            self.cov_controller.pause()   # <-- AttributeError under --no-cov
            yield
            self.cov_controller.resume()
        else:
            yield

`CovPlugin.__init__` sets `self.cov_controller = None` and returns immediately when
`options.no_cov` is set (`--no-cov` was passed), so `cov_controller` is *never* created for that
session. But `pytest_runtest_call` above still fires for every item and still dereferences
`cov_controller` the moment it sees the `no_cover` marker -- there is no `is None` guard. A test
statically decorated with `@pytest.mark.no_cover` therefore turns `pytest --no-cov` into a hard
`AttributeError` crash, not the no-op it should be (there is no tracer running to pause).

FIX CHOSEN (over excluding `tests/perf/` from `.coveragerc`'s `omit` list): the modules being
timed here -- `src/market/recourse.py`, `src/core/finance/*` -- are exercised by hundreds of
*other* tests across the suite whose coverage must still count toward the 80% gate. Omitting
them from tracing to protect three perf tests would silently zero out their coverage contribution
project-wide, trading an honest crash for a silent coverage hole -- worse than the bug it fixes.
Marker-gating keeps the omission scoped to exactly the three timed tests, exactly when coverage
is live to be paused.

So: apply `no_cover` to the timed class dynamically, and only when `--no-cov` was NOT passed
(i.e. only when there is a real `cov_controller` for pytest-cov to dereference). When `--no-cov`
IS passed, the tests run with no marker at all -- coverage was already off, so there is nothing
to pause, and pytest-cov's hook never touches `cov_controller`. Timing stays honest either way:
traced runs pause the tracer for the timed class (preserving the ~5x-inflation-free measurement
documented in `test_perf_gates.py`); `--no-cov` runs are already untraced process-wide.
"""

from __future__ import annotations

import pytest

from tests.perf.test_perf_gates import TestRecourseLoopBudgets


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Mark `TestRecourseLoopBudgets` tests `no_cover`, but only when coverage is actually live."""
    if config.getoption("no_cov", default=False):
        return
    for item in items:
        if getattr(item, "cls", None) is TestRecourseLoopBudgets:
            item.add_marker(pytest.mark.no_cover)
