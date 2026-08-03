# tests/integration/test_report_cli_minimal.py

from pathlib import Path

import src.cli.report_cli as report_cli
from src.schemas.models import InvestmentThesis, ListingInsights
from tests.utils import make_minimal_forecast


def test_report_cli_minimal(tmp_path: Path):
    """End-to-end test: forecast + insights + thesis → report.md"""
    forecast = make_minimal_forecast()
    insights = ListingInsights(address="123 Test Ave", amenities=[], condition_tags=[], defects=[], notes=["note a"])
    thesis = InvestmentThesis(verdict="DECLINE", rationale=["r1", "r2"], levers=[])

    f_path = tmp_path / "forecast.json"
    i_path = tmp_path / "insights.json"
    t_path = tmp_path / "thesis.json"
    out_md = tmp_path / "report.md"

    f_path.write_text(forecast.model_dump_json(indent=2), encoding="utf-8")
    i_path.write_text(insights.model_dump_json(indent=2), encoding="utf-8")
    t_path.write_text(thesis.model_dump_json(indent=2), encoding="utf-8")

    argv = [
        "--forecast",
        str(f_path),
        "--insights",
        str(i_path),
        "--thesis",
        str(t_path),
        "--out",
        str(out_md),
        "--title",
        "My E2E Report Test",
    ]

    # Run the CLI directly
    rc = report_cli.main(argv)
    assert rc == 0
    text = out_md.read_text(encoding="utf-8")

    # Core content checks
    assert text.startswith("# My E2E Report Test")
    assert "**Amenities:**" in text
    assert "## Purchase Metrics" in text
    assert "## Returns Summary (10-Year)" in text
