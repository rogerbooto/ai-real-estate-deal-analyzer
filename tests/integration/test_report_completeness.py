# tests/integration/test_report_completeness.py
"""Everything the pipeline extracts must actually reach the report.

The failure mode these guard is not "the renderer is wrong" — each renderer was already
correct and tested. It is that nothing *fed* them:

  * ``OrchestrationResult`` carried no media, so ``_render_media_overview`` (and the whole
    ``photo_report`` module) were unreachable from ``main.py`` despite being tested;
  * ``analyze_listing`` rebuilt ``ListingInsights`` field by field, silently dropping every
    field added to the model later;
  * condition tags were sourced from photos alone, so with deterministic CV stubs the field
    was structurally always empty;
  * the CV rollup's amenity labels were computed and then discarded.

So these tests assert on the OUTPUT of a real pipeline run, not on renderers in isolation.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from src.core.reports.generator import generate_report
from src.orchestrators.crew import run_orchestration
from tests.utils import make_financial_inputs

_LISTING = """36 Kelly
Moncton, New Brunswick E1C 2R7
Price: $399,900
Square Feet: 1,936
Bedrooms: 3
Bathrooms: 1
Year built: 1975
Type: Duplex
Recently renovated, move-in ready.
Separate laundry for both units. Driveway: Paved.
"""


@pytest.fixture()
def bundle(tmp_path: Path) -> tuple[str, str]:
    listing = tmp_path / "listing.txt"
    listing.write_text(_LISTING, encoding="utf-8")
    photos = tmp_path / "photos"
    photos.mkdir()
    for name in ("kitchen.jpg", "bathroom.jpg", "bedroom.jpg"):
        Image.new("RGB", (800, 600), "white").save(photos / name)
    return str(listing), str(photos)


def _run(listing: str, photos: str | None):
    return run_orchestration(
        inputs=make_financial_inputs(),
        listing_txt_path=listing,
        photos_folder=photos,
        horizon_years=5,
    )


# ---------------------------------------------------------------------------
# The pipeline carries media at all
# ---------------------------------------------------------------------------


def test_orchestrator_returns_media_when_photos_are_supplied(bundle: tuple[str, str]) -> None:
    listing, photos = bundle
    result = _run(listing, photos)

    assert result.media_insights is not None, "photos supplied but no MediaInsights produced"
    assert result.media_insights.image_count == 3
    assert result.media_report is not None, "photos supplied but no MediaReport produced"


def test_orchestrator_returns_no_media_without_photos(bundle: tuple[str, str]) -> None:
    listing, _ = bundle
    result = _run(listing, None)

    assert result.media_insights is None
    assert result.media_report is None


# ---------------------------------------------------------------------------
# Stated facts survive the analyst merge and reach the rendered report
# ---------------------------------------------------------------------------


def test_analyst_merge_preserves_every_text_derived_field(bundle: tuple[str, str]) -> None:
    listing, photos = bundle
    insights = _run(listing, photos).insights

    # Named individually on purpose: a field-by-field rebuild in the analyst drops these
    # one at a time, and a generic "not None" sweep would not say which.
    assert insights.address is not None
    assert insights.title is not None
    assert insights.price == 399900.0
    assert insights.sqft == 1936
    assert insights.bedrooms == 3
    assert insights.bathrooms == 1
    assert insights.year_built == 1975


def test_stated_facts_are_rendered(bundle: tuple[str, str]) -> None:
    listing, photos = bundle
    result = _run(listing, photos)
    md = generate_report(result.insights, result.forecast, result.thesis)

    assert "**As listed:**" in md
    assert "$399,900.00" in md
    assert "1,936 sq ft" in md
    assert "3 bd / 1 ba" in md
    assert "built 1975" in md


# ---------------------------------------------------------------------------
# Extraction gaps that made fields structurally empty
# ---------------------------------------------------------------------------


def test_text_contributes_condition_tags_even_with_stub_cv(bundle: tuple[str, str]) -> None:
    listing, photos = bundle
    tags = _run(listing, photos).insights.condition_tags

    assert "renovated" in tags
    assert "move-in ready" in tags


def test_multi_unit_laundry_phrasing_is_recognized(bundle: tuple[str, str]) -> None:
    listing, photos = bundle
    amenities = _run(listing, photos).insights.amenities

    assert "in_unit_laundry" in amenities, "'Separate laundry for both units' was not recognized"
    assert "parking" in amenities


# ---------------------------------------------------------------------------
# Media sections actually appear in the rendered document
# ---------------------------------------------------------------------------


def test_media_sections_render_from_a_real_run(bundle: tuple[str, str]) -> None:
    listing, photos = bundle
    r = _run(listing, photos)
    md = generate_report(
        r.insights,
        r.forecast,
        r.thesis,
        media_insights=r.media_insights,
        media_report=r.media_report,
    )

    assert "## Media Overview" in md
    assert "(images: 3" in md
    assert "## Photo Coverage" in md
    assert "provider" in md


def test_media_sections_absent_when_no_photos(bundle: tuple[str, str]) -> None:
    listing, _ = bundle
    r = _run(listing, None)
    md = generate_report(r.insights, r.forecast, r.thesis, media_insights=r.media_insights, media_report=r.media_report)

    assert "## Media Overview" not in md
    assert "## Photo Coverage" not in md


def test_report_is_byte_identical_across_runs(bundle: tuple[str, str]) -> None:
    listing, photos = bundle

    def render() -> str:
        r = _run(listing, photos)
        return generate_report(r.insights, r.forecast, r.thesis, media_insights=r.media_insights, media_report=r.media_report)

    assert render() == render()
