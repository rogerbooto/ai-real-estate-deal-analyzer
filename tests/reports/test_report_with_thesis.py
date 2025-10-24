# tests/reports/test_report_with_thesis.py

from pathlib import Path

from src.reports.generator import write_report
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
