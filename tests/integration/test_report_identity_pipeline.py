# tests/integration/test_report_identity_pipeline.py
"""Report identity must survive the WHOLE pipeline, not just the renderer.

``tests/core/reports/test_report_header_identity.py`` proves the generator prefers
address → title → "Subject Property". That is not enough: ``analyze_listing`` rebuilds
``ListingInsights`` field by field when merging text and photo signals, so a field it
forgets to copy is silently dropped before the renderer ever sees it — which is exactly
what happened to ``title``.

These tests drive the real orchestrator path (text → analyst → generator) so a dropped
field turns them RED.
"""

from __future__ import annotations

from pathlib import Path

from src.agents.listing_analyst import analyze_listing
from src.core.finance import run_financial_model
from src.core.reports.generator import generate_report
from tests.utils import make_financial_inputs

# A street line with no street type ("Kelly" carries no St/Ave/Dr), so address parsing
# declines and only the inferred title can name the report.
_UNPARSEABLE_ADDRESS = "36 Kelly\nBright duplex with parking and a finished basement.\n"


def _report_title(listing_text: str, tmp_path: Path) -> str:
    p = tmp_path / "listing.txt"
    p.write_text(listing_text, encoding="utf-8")
    insights = analyze_listing(listing_txt_path=str(p), photos_folder=None)
    forecast = run_financial_model(make_financial_inputs())
    return generate_report(insights, forecast, None).splitlines()[0]


def test_analyst_preserves_title_through_the_merge(tmp_path: Path) -> None:
    p = tmp_path / "listing.txt"
    p.write_text(_UNPARSEABLE_ADDRESS, encoding="utf-8")
    insights = analyze_listing(listing_txt_path=str(p), photos_folder=None)

    assert insights.address is None, "fixture no longer exercises the unparseable-address path"
    assert insights.title, "analyze_listing dropped `title` while merging text and photo signals"


def test_report_is_named_even_when_the_address_cannot_be_parsed(tmp_path: Path) -> None:
    assert _report_title(_UNPARSEABLE_ADDRESS, tmp_path) != "# Investment Analysis – Subject Property"


def test_parseable_address_still_wins(tmp_path: Path) -> None:
    text = "36 Kelly\nMoncton, New Brunswick E1C 2R7\nPrice: $399,900\n"
    assert _report_title(text, tmp_path) == "# Investment Analysis – 36 Kelly"
