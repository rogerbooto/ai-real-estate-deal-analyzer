# tests/conftest.py
from __future__ import annotations

import os
import random
from pathlib import Path

import pytest

from src.core.finance import run_financial_model
from tests.utils import (
    DEFAULT_LISTING_HTML,
    default_theses,
    make_document,
    # Financial factories
    make_financial_inputs,
    make_html_snapshot,
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
    return run_financial_model(baseline_financial_inputs)


@pytest.fixture
def html_snapshot_factory(tmp_path: Path):
    """
    Callable factory to create HtmlSnapshot files in a test's tmp path.

    Usage:
        snap = html_snapshot_factory("<html>...</html>", url="https://x/y")
    """

    def _factory(html: str = DEFAULT_LISTING_HTML, url: str = "https://example.com/listing/123"):
        return make_html_snapshot(tmp_path, html=html, url=url)

    return _factory


@pytest.fixture
def sample_html_snapshot(html_snapshot_factory):
    """Convenience: default listing HTML snapshot."""
    return html_snapshot_factory(DEFAULT_LISTING_HTML)


@pytest.fixture
def document_factory(tmp_path: Path):
    """
    Callable factory to create a simple HTML or text document in tmp_path.

    Usage:
        html_doc = document_factory(html="<html>...</html>")
        txt_doc  = document_factory(text="hello", filename="notes.txt")
    """

    def _factory(*, html: str | None = None, text: str | None = None, filename: str | None = None) -> Path:
        return make_document(tmp_path, html=html, text=text, filename=filename)

    return _factory


@pytest.fixture
def photo_dir(tmp_path: Path) -> Path:
    """
    Fixture that creates a deterministic photo directory with filenames
    recognized by the heuristic tagger (for consistent test results).

    Files created:
      - kitchen_updated_dishwasher.jpg  → room:kitchen, amenity:dishwasher, quality:renovated_kitchen
      - bathroom_1.jpg                  → room:bathroom
      - kitchen_2.jpg                   → room:kitchen
    """
    pdir = tmp_path / "photos"
    pdir.mkdir(parents=True, exist_ok=True)

    (pdir / "kitchen_updated_dishwasher.jpg").write_bytes(b"\x00")
    (pdir / "bathroom_1.jpg").write_bytes(b"\x00")
    (pdir / "kitchen_2.jpg").write_bytes(b"\x00")

    return pdir


# -------- Pytest markers --------
def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks integration tests")
