# src/core/intelligence/report_builder.py

from __future__ import annotations

from html import escape
from pathlib import Path

from .deal_fusion import DealIntelligence
from .narrative_builder import build_narrative_md


def write_markdown_report(deal: DealIntelligence, out_md: Path) -> Path:
    """
    Write a deterministic Markdown report for a fused deal.

    - Creates parent directories as needed.
    - Overwrites existing files (idempotent for the same input).
    """
    out_md.parent.mkdir(parents=True, exist_ok=True)
    content = build_narrative_md(deal)
    out_md.write_text(content, encoding="utf-8")
    return out_md


def md_to_html(md_path: Path, html_path: Path) -> Path:
    """
    Zero-dependency Markdown → HTML fallback.

    We intentionally do *not* interpret Markdown; we present it in a <pre>
    block with HTML-escaped content. This keeps CI deterministic and avoids
    runtime dependencies. (Pretty rendering can be added behind an optional
    flag later using a real MD renderer.)

    - Adds UTF-8 meta.
    - Uses white-space: pre-wrap to preserve line breaks and wrapping.
    """
    md = md_path.read_text(encoding="utf-8")
    # Escape HTML-sensitive characters safely
    md_escaped = escape(md, quote=False)

    html = (
        "<!doctype html>"
        "<html lang='en'>"
        "<head>"
        "<meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>Deal Report</title>"
        "</head>"
        "<body>"
        "<pre style='white-space:pre-wrap;margin:1.5rem;font-family:ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "
        "Liberation Mono, monospace;'>"
        f"{md_escaped}"
        "</pre>"
        "</body>"
        "</html>"
    )

    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html, encoding="utf-8")
    return html_path
