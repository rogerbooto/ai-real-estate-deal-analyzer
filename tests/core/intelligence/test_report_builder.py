# tests/intelligence/test_report_builder.py

from __future__ import annotations

from src.core.intelligence.deal_fusion import fuse_deal_intelligence
from src.core.intelligence.report_builder import md_to_html, write_markdown_report


def test_report_builder_writes_md_and_html(tmp_path, listing_fixture, photos_fixture, finance_fixture) -> None:
    # Arrange
    deal = fuse_deal_intelligence(listing_fixture, photos_fixture, finance_fixture)
    out_dir = tmp_path / "reports"
    md_path = out_dir / "deal.md"
    html_path = out_dir / "deal.html"

    # Act
    wrote_md = write_markdown_report(deal, md_path)
    wrote_html = md_to_html(wrote_md, html_path)

    # Assert: files created
    assert wrote_md.exists() and wrote_md.is_file()
    assert wrote_html.exists() and wrote_html.is_file()

    # Assert: MD content has expected bits
    md_text = wrote_md.read_text(encoding="utf-8")
    assert "# Deal Overview — Charming 2BR Near River" in md_text
    assert "**Address:** 123 Main St, Moncton, NB" in md_text

    # Assert: HTML is a wrapped/escaped presentation of the MD
    html_text = wrote_html.read_text(encoding="utf-8")
    assert html_text.lstrip().startswith("<!doctype html>")
    assert "<meta charset='utf-8'>" in html_text
    assert "<pre" in html_text and "</pre>" in html_text
    # Address appears inside the HTML (escaped from MD, but no special chars here)
    assert "123 Main St, Moncton, NB" in html_text
