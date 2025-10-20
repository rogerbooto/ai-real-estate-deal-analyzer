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
    make_gradient_img as _make_gradient_img,
    make_html_snapshot,
    make_hypothesis,
    make_hypothesis_set,
    make_listing_insights,
    make_market_assumptions,
    make_snapshot,
    png_bytes as _make_png,
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
    """Factory for canonical baseline inputs (no refi)."""

    def _factory(**overrides):
        # allow optional overrides if a test wants to tweak something
        fi = make_financial_inputs(do_refi=False, num_units=4)
        return fi.model_copy(update=overrides) if overrides else fi

    return _factory


@pytest.fixture
def baseline_forecast():
    """Factory to run the financial model on provided inputs."""

    def _factory(fi=None, *, insights=None, horizon_years=None):
        # If not provided, build a default inputs bundle
        if fi is None:
            fi = make_financial_inputs(do_refi=False, num_units=4)
        if horizon_years is None:
            return run_financial_model(fi, insights=insights)
        return run_financial_model(fi, insights=insights, horizon_years=horizon_years)

    return _factory


@pytest.fixture
def market_assumptions_baseline():
    """Factory for baseline market assumptions (overridable)."""

    def _factory(**overrides):
        return make_market_assumptions(**overrides)

    return _factory


@pytest.fixture
def theses_default():
    return default_theses()


@pytest.fixture
def listing_insights_baseline():
    return make_listing_insights()


@pytest.fixture
def html_snapshot_factory(tmp_path: Path):
    """
    Callable factory to create HtmlSnapshot files in a test's tmp path.

    Usage:
        snap = html_snapshot_factory(html="<html>...</html>", url="https://x/y")
        snap = html_snapshot_factory(html="<html>...</html>", url="https://x/y", base_dir=some_tmp_path)
    """

    def _factory(
        html: str = DEFAULT_LISTING_HTML,
        url: str = "https://example.com/listing/123",
        *,
        base_dir: Path | None = None,
    ):
        target_dir = base_dir or tmp_path
        return make_html_snapshot(target_dir, html=html, url=url)

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


@pytest.fixture
def png_bytes():
    """
    Fixture that returns a callable to generate PNG bytes with low compression.
    Usage:
        data = png_bytes(64, 64)
    """
    return _make_png


@pytest.fixture
def make_gradient_img():
    """
    Fixture that returns a callable to generate gradient images at a given path.
    Usage:
        make_gradient_img(path, (w, h), delta=0)
    """

    def _factory(path: Path, size: tuple[int, int], delta: int = 0) -> None:
        _make_gradient_img(path=path, size=size, delta=delta)

    return _factory


# -------- Pytest markers --------
def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks integration tests")
