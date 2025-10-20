# tests/reports/test_report_generator.py

from src.reports.generator import generate_report, write_report


def test_generate_report_contains_key_sections(
    tmp_path,
    baseline_forecast,
    listing_insights_baseline,
    theses_default,
):
    # Use ONE thesis (generator expects a single InvestmentThesis, not a list)
    thesis = theses_default[0] if theses_default else None

    base_forcast = baseline_forecast()

    # Generate markdown using (insights, forecast, thesis)
    md = generate_report(listing_insights_baseline, base_forcast, thesis)

    # Core sections / wording-safe checks
    assert isinstance(md, str) and md.strip()
    assert "# Investment Analysis" in md
    assert "Purchase Metrics" in md  # allows "## Purchase Metrics"
    assert "Pro Forma" in md  # allows "10-Year Pro Forma (Summary)"
    assert "Operating Expenses" in md
    assert "Returns" in md

    # If the forecast includes a refi, ensure the section appears
    if base_forcast.refi is not None:
        assert "Refinance" in md

    # Year markers commonly present in pro-forma tables
    assert " | 1 " in md or "| 1 |" in md
    assert " | 10 " in md or "| 10 |" in md

    # Persist the report via the API: write_report(insights, path, forecast, thesis=?)
    out_path = tmp_path / "investment_analysis.md"
    write_report(path=out_path, insights=listing_insights_baseline, forecast=base_forcast, thesis=thesis)
    assert out_path.exists() and out_path.read_text(encoding="utf-8").strip()
