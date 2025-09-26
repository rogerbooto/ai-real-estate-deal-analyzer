# tests/conftest.py
from __future__ import annotations

import os
import random

import pytest

from src.tools.financial_model import run
from tests.utils import (
    default_theses,
    # Financial factories
    make_financial_inputs,
    make_hypothesis,
    make_hypothesis_set,
    make_listing_insights,
    make_market_assumptions,
    make_snapshot,
)


# -------- Global deterministic seed --------
@pytest.fixture(autouse=True, scope="session")
def _seed_session():
    random.seed(1337)
    os.environ.setdefault("PYTHONHASHSEED", "0")
    yield


# -------- Domain fixtures (snapshots & hypotheses) --------
@pytest.fixture
def sample_snapshot():
    return make_snapshot()


@pytest.fixture
def sample_hypothesis():
    return make_hypothesis()


@pytest.fixture
def sample_hypothesis_set():
    return make_hypothesis_set(n=3)


# -------- Financial fixtures --------
@pytest.fixture
def baseline_financial_inputs():
    """Canonical baseline inputs used in financial tests (no refi)."""
    return make_financial_inputs(do_refi=False, num_units=4)


@pytest.fixture
def refi_financial_inputs():
    """Same as baseline but with a refinance enabled."""
    return make_financial_inputs(do_refi=True, num_units=4)


@pytest.fixture
def listing_insights_baseline():
    return make_listing_insights()


@pytest.fixture
def market_assumptions_baseline():
    return make_market_assumptions()


@pytest.fixture
def theses_default():
    return default_theses()


@pytest.fixture
def baseline_forecast(baseline_financial_inputs):
    """Run the financial model once for reuse in report tests."""
    return run(baseline_financial_inputs)


# -------- Pytest markers --------
def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks integration tests")
