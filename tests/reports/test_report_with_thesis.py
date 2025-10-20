# tests/reports/test_report_with_thesis.py

from pathlib import Path

from src.reports.generator import write_report


def test_write_report_creates_md_file(
    tmp_path: Path,
    baseline_forecast,
    listing_insights_baseline,
    theses_default,
):
    thesis = theses_default[0] if theses_default else None

    out_file = tmp_path / "investment_analysis.md"

    write_report(path=out_file, insights=listing_insights_baseline, forecast=baseline_forecast(), thesis=thesis)

    # File should exist and be non-empty
    assert out_file.exists()
    text = out_file.read_text(encoding="utf-8")
    assert "# Investment Analysis" in text
    assert "Purchase Metrics" in text
    assert "Pro Forma" in text
    assert "Operating Expenses" in text
    assert "Returns" in text
    assert len(text) > 200  # sanity guard
