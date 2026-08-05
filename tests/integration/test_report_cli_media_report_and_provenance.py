# tests/integration/test_report_cli_media_report_and_provenance.py
"""
Prove-the-test for Mission 2 / F6: `deal-report` (report_cli) must be able to produce a
report comparable to `main.py`'s — i.e. it must be able to render the Photo Coverage section
(from a MediaReport) and the Run Provenance appendix (from a RunProvenance), not just the
Media Overview section (from MediaInsights).

Before the fix, `write_report` accepted `media_report=` and `provenance=` kwargs but
`report_cli.main()` never sourced or passed them, so `deal-report` output silently omitted
both sections even when `main.py`'s output (for the same underlying run) would include them.

This test is written so that reverting the `--media-report`/`--provenance` wiring in
`src/cli/report_cli.py` turns it RED (see MISSION_2 report for the literal revert/run
transcript).
"""

from __future__ import annotations

import json
from pathlib import Path

import src.cli.report_cli as report_cli
from src.core.reports.report_models import MediaCoverage, MediaReport, ParkingSummary
from src.schemas.models import ListingInsights, RunProvenance
from tests.utils import make_minimal_forecast


def _write_json(path: Path, model) -> None:  # type: ignore[no-untyped-def]
    path.write_text(model.model_dump_json(indent=2), encoding="utf-8")


def _make_media_report() -> MediaReport:
    return MediaReport(
        room_counts={"kitchen": 1, "bath": 2},
        amenities={"garage": True, "fireplace": False},
        defects={},
        quality_flags={},
        parking=ParkingSummary(parking_type="driveway", parking_spots=2, ev_charging=False),
        coverage=MediaCoverage(images_total=12, images_readable=11, detections_total=30, provider="cv_v2", version="1.0"),
        ontology_version="amenities_defects_v1",
        provenance={"source": "test-fixture"},
    )


def _make_provenance() -> RunProvenance:
    return RunProvenance(
        engine="deterministic",
        scenarios_enabled=False,
        vision_enabled=True,
        config_path="data/sample_listings/36_kelly_moncton/inputs.json",
    )


def test_media_report_and_provenance_render_when_supplied(tmp_path: Path) -> None:
    """Photo Coverage and pipeline-facts rows appear when --media-report/--provenance are given."""
    forecast = make_minimal_forecast()
    insights = ListingInsights(address="36 Kelly")

    f_path = tmp_path / "forecast.json"
    i_path = tmp_path / "insights.json"
    mr_path = tmp_path / "media_report.json"
    prov_path = tmp_path / "provenance.json"
    out_md = tmp_path / "report.md"

    _write_json(f_path, forecast)
    _write_json(i_path, insights)
    _write_json(mr_path, _make_media_report())
    _write_json(prov_path, _make_provenance())

    argv = [
        "--forecast",
        str(f_path),
        "--insights",
        str(i_path),
        "--media-report",
        str(mr_path),
        "--provenance",
        str(prov_path),
        "--out",
        str(out_md),
    ]

    rc = report_cli.main(argv)
    assert rc == 0
    text = out_md.read_text(encoding="utf-8")

    # Photo Coverage section is only emitted when a MediaReport is supplied.
    assert "## Photo Coverage" in text
    assert "Rooms Documented" in text
    assert "kitchen 1" in text

    # Run Provenance appendix's pipeline-facts rows are only emitted when a RunProvenance is supplied.
    assert "## Appendix — Run Provenance" in text
    assert "| Orchestration engine | deterministic |" in text
    assert "data/sample_listings/36_kelly_moncton/inputs.json" in text
    assert "| AI photo tagging | on |" in text


def test_media_report_and_provenance_absent_by_default(tmp_path: Path) -> None:
    """Without the new flags, the sections must be absent, not fabricated — and nothing crashes."""
    forecast = make_minimal_forecast()
    insights = ListingInsights(address="36 Kelly")

    f_path = tmp_path / "forecast.json"
    i_path = tmp_path / "insights.json"
    out_md = tmp_path / "report.md"

    _write_json(f_path, forecast)
    _write_json(i_path, insights)

    argv = [
        "--forecast",
        str(f_path),
        "--insights",
        str(i_path),
        "--out",
        str(out_md),
    ]

    rc = report_cli.main(argv)
    assert rc == 0
    text = out_md.read_text(encoding="utf-8")

    assert "## Photo Coverage" not in text
    # The appendix header itself is always emitted (valuation knobs apply to every run), but
    # the pipeline-facts rows must not appear absent a supplied RunProvenance.
    assert "## Appendix — Run Provenance" in text
    assert "Orchestration engine" not in text
    assert "Inputs file" not in text


def test_media_report_json_round_trips_via_model_validate(tmp_path: Path) -> None:
    """Sanity: the fixture MediaReport JSON is valid input for MediaReport.model_validate."""
    mr_path = tmp_path / "media_report.json"
    _write_json(mr_path, _make_media_report())
    data = json.loads(mr_path.read_text(encoding="utf-8"))
    # Round trip through the real model to ensure the fixture matches the schema report_cli loads against.
    assert MediaReport.model_validate(data).room_counts == {"kitchen": 1, "bath": 2}
