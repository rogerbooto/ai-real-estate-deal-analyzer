# tests/reports/test_report_with_thesis.py
from pathlib import Path

from src.core.reports.generator import write_report
from src.schemas.models import MediaInsights


def test_write_report_creates_md_file(
    tmp_path: Path,
    baseline_forecast,
    listing_insights_baseline,
    theses_default,
):
    thesis = theses_default[0] if theses_default else None

    out_file = tmp_path / "investment_analysis.md"

    # Minimal media insights sample
    mi = MediaInsights(
        total_assets=0,
        image_count=0,
        video_count=0,
        document_count=0,
        other_count=0,
        bytes_total=0,
    )

    write_report(
        path=out_file,
        insights=listing_insights_baseline,
        forecast=baseline_forecast(),
        thesis=thesis,
        media_insights=mi,  # NEW
    )

    # File should exist and be non-empty
    assert out_file.exists()
    text = out_file.read_text(encoding="utf-8")
    assert "# Investment Analysis" in text
    assert "Purchase Metrics" in text
    assert "Forecasting Methodology" in text
    assert "Media Overview" in text  # NEW: verify media section
    assert "Pro Forma" in text
    assert "Operating Expenses" in text
    assert "Returns" in text
    assert len(text) > 200  # sanity guard


def test_report_includes_thesis_section_when_present(
    tmp_path: Path,
    baseline_forecast,
    listing_insights_baseline,
    theses_default,
):
    """
    If a thesis is provided, the report should include the 'Investment Thesis' section
    and the verdict line.
    """
    thesis = theses_default[0] if theses_default else None
    out_file = tmp_path / "analysis_with_thesis.md"

    mi = MediaInsights(
        total_assets=1,
        image_count=1,
        video_count=0,
        document_count=0,
        other_count=0,
        bytes_total=512,
    )

    write_report(
        path=out_file,
        insights=listing_insights_baseline,
        forecast=baseline_forecast(),
        thesis=thesis,
        media_insights=mi,
    )

    text = out_file.read_text(encoding="utf-8")
    assert "Investment Thesis" in text
    # Verdict line should be rendered with the thesis verdict value
    assert "- **Verdict:**" in text
    assert thesis.verdict in text


def test_report_without_thesis_omits_thesis_section(
    tmp_path: Path,
    baseline_forecast,
    listing_insights_baseline,
):
    """
    If no thesis is provided, there should be no 'Investment Thesis' section.
    """
    out_file = tmp_path / "analysis_no_thesis.md"

    mi = MediaInsights(
        total_assets=2,
        image_count=2,
        video_count=0,
        document_count=0,
        other_count=0,
        bytes_total=1024,
    )

    write_report(
        path=out_file,
        insights=listing_insights_baseline,
        forecast=baseline_forecast(),
        thesis=None,
        media_insights=mi,
    )

    text = out_file.read_text(encoding="utf-8")
    assert "Investment Thesis" not in text


def test_media_bytes_raw_number_is_present(
    tmp_path: Path,
    baseline_forecast,
    listing_insights_baseline,
    theses_default,
):
    """
    The Media Overview should include both the formatted size and the raw integer (e.g., '(123456 bytes)').
    """
    thesis = theses_default[0] if theses_default else None
    out_file = tmp_path / "analysis_media_bytes.md"

    mi = MediaInsights(
        total_assets=7,
        image_count=3,
        video_count=2,
        document_count=1,
        other_count=1,
        bytes_total=123456,
    )

    write_report(
        path=out_file,
        insights=listing_insights_baseline,
        forecast=baseline_forecast(),
        thesis=thesis,
        media_insights=mi,
    )

    text = out_file.read_text(encoding="utf-8")
    assert "Media Overview" in text
    # human-friendly number
    assert "123,456 B" in text
    # raw integer included as "(123456 bytes)"
    assert "(123456 bytes)" in text
