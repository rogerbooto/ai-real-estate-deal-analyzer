# src/tools/report_cli.py
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.core.reports.generator import write_report
from src.schemas.models import (
    FinancialForecast,
    InvestmentThesis,
    ListingInsights,
    MediaInsights,
)


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _maybe_load(model_cls, arg: str | None):
    if not arg:
        return None
    data = _read_json(Path(arg))
    return model_cls.model_validate(data)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="report-cli",
        description="Render a markdown investment report from JSON inputs.",
    )
    ap.add_argument("--forecast", required=True, help="Path to FinancialForecast JSON.")
    ap.add_argument("--insights", help="Path to ListingInsights JSON (optional).")
    ap.add_argument("--thesis", help="Path to InvestmentThesis JSON (optional).")
    ap.add_argument("--media-insights", help="Path to MediaInsights JSON (optional).")
    ap.add_argument(
        "--out",
        required=True,
        help="Output markdown path, e.g., ./out/investment_report.md",
    )
    ap.add_argument(
        "--title",
        default=None,
        help="Optional title override for the report H1.",
    )
    args = ap.parse_args(argv)

    # Load required + optional models
    forecast = _maybe_load(FinancialForecast, args.forecast)
    if forecast is None:
        ap.error("--forecast is required and must be valid JSON")
    insights = _maybe_load(ListingInsights, args.insights)
    thesis = _maybe_load(InvestmentThesis, args.thesis)
    media = _maybe_load(MediaInsights, args.media_insights)

    # Write report
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Use the generator's write function (title_override handled inside generate_report)
    # Since write_report doesn’t take title_override directly, we can inject by
    # reusing generate_report if needed. To keep it simple & stable with your codebase,
    # call write_report then (optionally) replace the title if provided.
    write_report(
        path=str(out_path),
        insights=insights,
        forecast=forecast,  # type: ignore[arg-type]
        thesis=thesis,
        media_insights=media,
    )

    if args.title:
        txt = out_path.read_text(encoding="utf-8")
        lines = txt.splitlines()
        if lines:
            lines[0] = f"# {args.title}"
            out_path.write_text("\n".join(lines) + ("\n" if not txt.endswith("\n") else ""), encoding="utf-8")

    print(f"✅ Wrote report → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
