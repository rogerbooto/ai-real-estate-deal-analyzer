# tests/conftest.py
from __future__ import annotations

import os
import random
from pathlib import Path

import pytest

from src.core.finance import run_financial_model
from src.core.finance.adapters import FinanceSummary
from src.schemas.models import ListingNormalized, PhotoInsights
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
    make_photo_insights,
    make_photo_insights_from_photo_dir,
    make_snapshot,
    png_bytes as _make_png,
)


# -------- Global deterministic seed --------
@pytest.fixture(autouse=True, scope="session")
def _seed_session():
    random.seed(1337)
    os.environ.setdefault("PYTHONHASHSEED", "0")
    yield


# -------- CV tag-cache isolation --------
@pytest.fixture(autouse=True)
def _isolate_cv_cache(tmp_path_factory, monkeypatch):
    """
    Point the CV tag cache at a per-test temp dir instead of the repo root.

    `src/core/cv/runner.py` defaults `AIREDEAL_CACHE_DIR` to `./.cache/cv` and keys entries by
    **content sha256 alone**, ignoring filename. Test fixtures across the suite generate
    byte-identical images (`Image.new("RGB", (800, 600), "white")`), so they all collide on one
    cache slot that persists on disk between runs — this checkout had entries dated October 2025.
    Combined with `_augment_from_filename`'s augment-on-cache-hit behaviour, a detection earned by
    one fixture's filename can be served to a later, differently-named fixture with the same
    content. That is the most plausible mechanism for the one-off, non-reproducing parity-test
    flake seen during Wave 1 (stale *local* state a fresh CI checkout would never carry).

    Autouse rather than per-file `monkeypatch.setenv` calls: three files needed it and the next
    media test would have to remember. Tests that deliberately exercise caching set
    `AIREDEAL_CACHE_DIR` themselves inside the test body, which still wins over this.
    """
    monkeypatch.setenv("AIREDEAL_CACHE_DIR", str(tmp_path_factory.mktemp("cv_cache")))
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
def photo_dir(tmp_path: Path, make_gradient_img) -> Path:
    """
    Creates real (uncompressed) PNGs so the photo quality filter keeps them.
      - kitchen_updated_dishwasher.png → room:kitchen, amenity:dishwasher, quality:renovated_kitchen
      - bathroom_1.png                 → room:bathroom
      - kitchen_2.png                  → room:kitchen
    """
    pdir = tmp_path / "photos"
    pdir.mkdir(parents=True, exist_ok=True)

    make_gradient_img(pdir / "kitchen_updated_dishwasher.png", (64, 64), delta=1)
    make_gradient_img(pdir / "bathroom_1.png", (64, 64), delta=2000)
    make_gradient_img(pdir / "kitchen_2.png", (64, 64), delta=300000)

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


@pytest.fixture
def photo_insights_factory():
    """
    Factory fixture to build PhotoInsights from arbitrary image paths and maps.

    Usage:
        photos = photo_insights_factory(
            [img1_path, img2_path],
            amenities={"dishwasher": True},
            defects={"mold_suspected": 1},
            labels_by_sha={...},  # optional
            detections_by_sha={...},  # optional
        )
    """

    def _factory(
        image_paths: list[Path],
        **kwargs,
    ):
        return make_photo_insights(image_paths, **kwargs)

    return _factory


@pytest.fixture
def sample_photo_insights(photo_dir: Path):
    """
    Ready-to-use PhotoInsights matching the deterministic `photo_dir` fixture
    (kitchen_updated_dishwasher, bathroom_1, kitchen_2).
    """
    return make_photo_insights_from_photo_dir(photo_dir)


# -------- Pytest markers --------
def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks integration tests")


@pytest.fixture
def listing_fixture() -> ListingNormalized:
    """Normalized listing sample with stable fields and short notes."""
    return ListingNormalized(
        title="Charming 2BR Near River",
        address="123 Main St, Moncton, NB",
        bedrooms=2,
        bathrooms=1,
        sqft=900,
        notes="Walkable to trails; South-facing windows",
    )


@pytest.fixture
def photos_fixture() -> PhotoInsights:
    """
    Deterministic photo insights fixture:
    - two quality scores (0.80, 0.60)
    - two distinct defect labels for penalty computation
    """
    return PhotoInsights(
        provider="stub-cv",
        version="1.0.0",
        quality_flags={"natural_light_score": 0.80, "renovated_score": 0.60},
        defect_counts={"paint_peel": 2, "crack": 1},
        room_counts={},
        amenities={},
        image_index={},
        image_labels={},
        image_detections={},
        amenity_counts={},
        parking=None,
        ontology_version=None,
        images_total=10,
        detections_total=5,
        provenance={},
    )


@pytest.fixture
def finance_fixture() -> FinanceSummary:
    """Finance summary fixture for deterministic scoring."""
    return FinanceSummary(
        irr=0.55,
        cashflow_monthly=125.0,
        price_per_sqft=210.0,
        market_ppsf=200.0,
        purchase_price=350000.0,
        area_safety_index=0.70,
    )
