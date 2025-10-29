# tests/reports/test_report_generator.py

import re

from src.core.reports.generator import generate_report, write_report
from src.schemas.models import MediaInsights


def test_generate_report_contains_key_sections(
    tmp_path,
    baseline_forecast,
    listing_insights_baseline,
    theses_default,
):
    # Use ONE thesis (generator expects a single InvestmentThesis, not a list)
    thesis = theses_default[0] if theses_default else None

    base_forcast = baseline_forecast()

    # Minimal media insights sample
    mi = MediaInsights(
        total_assets=0,
        image_count=0,
        video_count=0,
        document_count=0,
        other_count=0,
        bytes_total=0,
    )

    # Generate markdown using (insights, forecast, thesis, media_insights)
    md = generate_report(listing_insights_baseline, base_forcast, thesis, media_insights=mi)

    # Core sections / wording-safe checks
    assert isinstance(md, str) and md.strip()
    assert "# Investment Analysis" in md
    assert "Purchase Metrics" in md  # allows "## Purchase Metrics"
    assert "Forecasting Methodology" in md
    assert "Media Overview" in md  # Ensure media section is rendered
    assert "Pro Forma" in md  # allows "10-Year Pro Forma (Summary)"
    assert "Operating Expenses" in md
    assert "Returns" in md

    # If the forecast includes a refi, ensure the section appears
    if base_forcast.refi is not None:
        assert "Refinance" in md

    # Year markers commonly present in pro-forma tables
    assert " | 1 " in md or "| 1 |" in md
    assert " | 10 " in md or "| 10 |" in md

    # Persist the report via the API
    out_path = tmp_path / "investment_analysis.md"
    write_report(
        path=out_path,
        insights=listing_insights_baseline,
        forecast=base_forcast,
        thesis=thesis,
        media_insights=mi,  # NEW
    )
    assert out_path.exists() and out_path.read_text(encoding="utf-8").strip()


def test_write_report_creates_parent_dirs(
    tmp_path,
    baseline_forecast,
    listing_insights_baseline,
    theses_default,
):
    """
    write_report should create parent directories if they don't exist.
    """
    thesis = theses_default[0] if theses_default else None
    nested_dir = tmp_path / "deep" / "nested" / "path"
    out_path = nested_dir / "analysis.md"

    mi = MediaInsights(
        total_assets=0,
        image_count=0,
        video_count=0,
        document_count=0,
        other_count=0,
        bytes_total=0,
    )

    write_report(
        path=out_path,
        insights=listing_insights_baseline,
        forecast=baseline_forecast(),
        thesis=thesis,
        media_insights=mi,
    )

    assert out_path.exists()
    # sanity: file is UTF-8 text and non-empty
    content = out_path.read_text(encoding="utf-8")
    assert isinstance(content, str) and content.strip()
    assert "Investment Analysis" in content


def test_generate_report_without_thesis_renders(
    baseline_forecast,
    listing_insights_baseline,
):
    """
    generate_report should work when thesis is None (no Staff Strategist verdict yet).
    """
    mi = MediaInsights(
        total_assets=1,
        image_count=1,
        video_count=0,
        document_count=0,
        other_count=0,
        bytes_total=1024,
    )

    md = generate_report(
        listing_insights_baseline,
        baseline_forecast(),
        thesis=None,  # explicitly no thesis
        media_insights=mi,
    )

    assert isinstance(md, str) and md.strip()
    assert "# Investment Analysis" in md
    # Still includes core computed sections
    assert "Purchase Metrics" in md
    assert "Media Overview" in md


def test_generate_report_media_counts_are_reflected(
    baseline_forecast,
    listing_insights_baseline,
    theses_default,
):
    """
    The Media Overview section should reflect non-zero counts in a wording-safe way.
    We only assert that the numbers appear near the media section.
    """
    thesis = theses_default[0] if theses_default else None

    mi = MediaInsights(
        total_assets=7,
        image_count=3,
        video_count=2,
        document_count=1,
        other_count=1,
        bytes_total=123456,
    )

    md = generate_report(
        listing_insights_baseline,
        baseline_forecast(),
        thesis,
        media_insights=mi,
    )

    assert "Media Overview" in md

    # Look within a small window after the "Media Overview" heading to find the counts.
    # This avoids relying on exact phrasing/formatting.
    start = md.find("Media Overview")
    window = md[start : start + 800] if start != -1 else md

    # Ensure the expected numbers are present somewhere in the media section window
    for n in (str(mi.image_count), str(mi.video_count), str(mi.document_count), str(mi.total_assets)):
        assert n in window

    # Also ensure bytes_total is present as a number (no strict formatting expectations)
    assert re.search(r"\b123456\b", window) is not None
