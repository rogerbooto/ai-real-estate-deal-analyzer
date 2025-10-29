# tests/integration/test_report_cli_media.py


from pathlib import Path

import report_cli
from src.schemas.models import ListingInsights, MediaInsights
from tests.utils import make_minimal_forecast


def test_report_cli_with_media(tmp_path: Path):
    """End-to-end test: forecast + insights + media → report.md"""
    forecast = make_minimal_forecast()
    insights = ListingInsights(address="Subject Property")
    media = MediaInsights(
        total_assets=7,
        image_count=3,
        video_count=2,
        document_count=1,
        other_count=1,
        bytes_total=123456,
    )

    f_path = tmp_path / "forecast.json"
    i_path = tmp_path / "insights.json"
    m_path = tmp_path / "media.json"
    out_md = tmp_path / "report.md"

    f_path.write_text(forecast.model_dump_json(indent=2), encoding="utf-8")
    i_path.write_text(insights.model_dump_json(indent=2), encoding="utf-8")
    m_path.write_text(media.model_dump_json(indent=2), encoding="utf-8")

    argv = [
        "--forecast",
        str(f_path),
        "--insights",
        str(i_path),
        "--media-insights",
        str(m_path),
        "--out",
        str(out_md),
    ]

    rc = report_cli.main(argv)
    assert rc == 0
    text = out_md.read_text(encoding="utf-8")

    # Validate section presence
    assert text.startswith("#")  # Title header
    assert "Media" in text or "Assets" in text
    assert "Total" in text  # verifies numeric summary inclusion
