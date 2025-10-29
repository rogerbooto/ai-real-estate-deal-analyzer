import json
from pathlib import Path

import pytest

import report_cli


def test_report_cli_missing_forecast_arg_errors(tmp_path: Path):
    """
    Argparse should error when --forecast is missing (required=True),
    raising SystemExit with a non-zero code (typically 2).
    """
    out_md = tmp_path / "report.md"
    argv = [
        # "--forecast" omitted on purpose
        "--out",
        str(out_md),
    ]
    with pytest.raises(SystemExit) as e:
        report_cli.main(argv)
    assert e.value.code != 0


def test_report_cli_invalid_forecast_json_validation_error(tmp_path: Path):
    """
    A syntactically-valid but schema-invalid forecast JSON should raise a Pydantic ValidationError.
    We assert an exception is raised and it's not silently returning 0.
    """
    bad_forecast = tmp_path / "bad_forecast.json"
    bad_forecast.write_text(json.dumps({"not": "a FinancialForecast"}), encoding="utf-8")

    insights = tmp_path / "insights.json"
    insights.write_text(json.dumps({"address": "123 Test Ave"}), encoding="utf-8")

    out_md = tmp_path / "report.md"
    argv = [
        "--forecast",
        str(bad_forecast),
        "--insights",
        str(insights),
        "--out",
        str(out_md),
    ]

    with pytest.raises(Exception) as e:
        report_cli.main(argv)

    # Helpful sanity check: Pydantic validation bubbles up
    msg = str(e.value)
    assert "FinancialForecast" in msg or "ValidationError" in msg
