# tests/integration/test_report_cli_bad_input_guards.py
"""
Prove-the-test for Mission 2 / F14 and F19.

F14 — `--insights` silently accepted meaningless JSON. Every field on `ListingInsights` is
optional, so `{}` (or `{"totally": "unrelated"}`) validated cleanly against it and produced a
report with an empty listing section, with no warning to the caller. `_maybe_load` now rejects
JSON for `ListingInsights` that shares no key with any real field on the model, while a
genuinely sparse-but-real insights file (only a subset of real fields set) still works — absent
facts are legitimate and the pipeline never fabricates listing data.

F19 — a missing/unreadable/malformed `--forecast` file surfaced a raw traceback
(`FileNotFoundError` / `json.JSONDecodeError`) instead of a clean, actionable CLI error, and the
`ap.error("--forecast is required...")` branch that was supposed to catch a bad load could never
actually fire (`_maybe_load` never returned `None` for a real file-loading failure — it either
returned a value or let the underlying exception propagate).

Revert either fix in `src/cli/report_cli.py` and the corresponding test below turns RED (see the
Mission 2 report for the literal revert/run transcript).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError as PydanticValidationError

import src.cli.report_cli as report_cli
from src.schemas.models import ListingInsights
from tests.utils import make_minimal_forecast


def _write_forecast(path: Path) -> None:
    path.write_text(make_minimal_forecast().model_dump_json(indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# F14 — unrecognizable --insights JSON
# ---------------------------------------------------------------------------


def test_insights_empty_object_is_rejected(tmp_path: Path) -> None:
    """`{}` shares no field with ListingInsights and must be rejected, not silently accepted."""
    f_path = tmp_path / "forecast.json"
    i_path = tmp_path / "insights.json"
    out_md = tmp_path / "report.md"

    _write_forecast(f_path)
    i_path.write_text("{}", encoding="utf-8")

    argv = ["--forecast", str(f_path), "--insights", str(i_path), "--out", str(out_md)]

    with pytest.raises(SystemExit) as exc_info:
        report_cli.main(argv)

    msg = str(exc_info.value)
    assert "no recognized ListingInsights field" in msg
    assert not out_md.exists()


def test_insights_unrelated_json_is_rejected(tmp_path: Path) -> None:
    """A JSON object with real content but no field overlap must be rejected too, not just `{}`."""
    f_path = tmp_path / "forecast.json"
    i_path = tmp_path / "insights.json"
    out_md = tmp_path / "report.md"

    _write_forecast(f_path)
    i_path.write_text(json.dumps({"totally": "unrelated", "nonsense": 123}), encoding="utf-8")

    argv = ["--forecast", str(f_path), "--insights", str(i_path), "--out", str(out_md)]

    with pytest.raises(SystemExit) as exc_info:
        report_cli.main(argv)

    assert "no recognized ListingInsights field" in str(exc_info.value)


def test_insights_sparse_but_real_json_still_works(tmp_path: Path) -> None:
    """A sparse-but-real insights file (one real field, absent facts elsewhere) must still work."""
    f_path = tmp_path / "forecast.json"
    i_path = tmp_path / "insights.json"
    out_md = tmp_path / "report.md"

    _write_forecast(f_path)
    i_path.write_text(json.dumps({"address": "123 Main St"}), encoding="utf-8")

    argv = ["--forecast", str(f_path), "--insights", str(i_path), "--out", str(out_md)]

    rc = report_cli.main(argv)
    assert rc == 0
    assert "123 Main St" in out_md.read_text(encoding="utf-8")


def test_insights_omitted_flag_still_optional(tmp_path: Path) -> None:
    """Omitting --insights entirely must remain a no-op (the recognized-field gate is not a
    disguised "insights is now required")."""
    f_path = tmp_path / "forecast.json"
    out_md = tmp_path / "report.md"

    _write_forecast(f_path)

    argv = ["--forecast", str(f_path), "--out", str(out_md)]
    rc = report_cli.main(argv)
    assert rc == 0
    assert out_md.exists()


def test_maybe_load_direct_accepts_sparse_but_real_insights(tmp_path: Path) -> None:
    """Direct unit check on `_maybe_load` for the boundary described in the module docstring."""
    i_path = tmp_path / "insights.json"
    i_path.write_text(json.dumps({"bedrooms": 2}), encoding="utf-8")

    loaded = report_cli._maybe_load(ListingInsights, str(i_path), require_recognized_field=True)
    assert loaded is not None
    assert loaded.bedrooms == 2


def test_maybe_load_direct_rejects_no_recognized_field(tmp_path: Path) -> None:
    i_path = tmp_path / "insights.json"
    i_path.write_text(json.dumps({"unrelated_key": "value"}), encoding="utf-8")

    with pytest.raises(SystemExit):
        report_cli._maybe_load(ListingInsights, str(i_path), require_recognized_field=True)


def test_forecast_bad_schema_json_still_raises_pydantic_error_not_systemexit(tmp_path: Path) -> None:
    """
    The recognized-field gate must stay scoped to ListingInsights: FinancialForecast already has
    required fields, so an unrelated-but-syntactically-valid JSON must still fail via pydantic's
    own ValidationError (unchanged behavior), not the new SystemExit path.
    """
    bad_forecast = tmp_path / "bad_forecast.json"
    bad_forecast.write_text(json.dumps({"not": "a FinancialForecast"}), encoding="utf-8")
    out_md = tmp_path / "report.md"

    with pytest.raises(Exception) as exc_info:
        report_cli.main(["--forecast", str(bad_forecast), "--out", str(out_md)])

    assert not isinstance(exc_info.value, SystemExit)


# ---------------------------------------------------------------------------
# F19 — missing/unreadable/malformed --forecast file
# ---------------------------------------------------------------------------


def test_forecast_missing_file_gives_clean_systemexit_not_traceback(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.json"
    out_md = tmp_path / "report.md"

    with pytest.raises(SystemExit) as exc_info:
        report_cli.main(["--forecast", str(missing), "--out", str(out_md)])

    msg = str(exc_info.value)
    assert "file not found" in msg
    assert str(missing) in msg
    assert not out_md.exists()


def test_forecast_malformed_json_gives_clean_systemexit_not_traceback(tmp_path: Path) -> None:
    bad = tmp_path / "broken.json"
    bad.write_text("{not valid json", encoding="utf-8")
    out_md = tmp_path / "report.md"

    with pytest.raises(SystemExit) as exc_info:
        report_cli.main(["--forecast", str(bad), "--out", str(out_md)])

    msg = str(exc_info.value)
    assert "not valid JSON" in msg
    assert str(bad) in msg


def test_forecast_directory_instead_of_file_gives_clean_systemexit(tmp_path: Path) -> None:
    """A directory (or otherwise unreadable path) must also fail cleanly, not with a raw OSError."""
    a_dir = tmp_path / "a_directory"
    a_dir.mkdir()
    out_md = tmp_path / "report.md"

    with pytest.raises(SystemExit) as exc_info:
        report_cli.main(["--forecast", str(a_dir), "--out", str(out_md)])

    assert "could not be read" in str(exc_info.value)


def test_non_dict_insights_json_raises_pydantic_not_systemexit(tmp_path: Path) -> None:
    """
    Pin the boundary between the two failure modes this CLI deliberately keeps distinct.

    `_read_json` converts *file-level* problems (missing, unreadable, malformed) into a clean
    `SystemExit`, and the recognized-field gate does the same for a dict that shares no key with
    `ListingInsights`. A JSON value of the wrong *shape* -- a list rather than an object -- is
    neither: it is a schema mismatch, and it stays with pydantic's own `ValidationError`, matching
    `test_forecast_bad_schema_json_still_raises_pydantic_error_not_systemexit` above.

    That is a deliberate contract, not an oversight: pydantic's message here names the problem
    precisely ("Input should be a valid dictionary ... input_type=list"), unlike the raw
    `FileNotFoundError` that F19 replaced. This test exists so the boundary is stated and cannot
    drift silently in either direction.
    """
    listish = tmp_path / "insights_list.json"
    listish.write_text("[]", encoding="utf-8")
    forecast = tmp_path / "forecast.json"
    _write_forecast(forecast)
    out_md = tmp_path / "report.md"

    with pytest.raises(PydanticValidationError):
        report_cli.main(["--forecast", str(forecast), "--insights", str(listish), "--out", str(out_md)])
