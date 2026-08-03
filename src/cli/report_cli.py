# src/tools/report_cli.py
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, TypeVar, cast

from pydantic import BaseModel

from src.core.reports.generator import write_report
from src.core.reports.report_models import MediaReport
from src.schemas.models import (
    FinancialForecast,
    InvestmentThesis,
    ListingInsights,
    MediaInsights,
    RunProvenance,
)


def _read_json(path: Path) -> dict[str, Any]:
    """
    Load and parse a JSON artifact, failing with a clear, actionable message.

    A bad path here is user error (typo, wrong flag) rather than a programming error, so it
    is reported the way this CLI reports other bad input (``raise SystemExit`` — see
    ``advisor_cli.py``'s ``discover_deal_in_dir``/``main``), not as a raw traceback surfacing
    ``FileNotFoundError``/``json.JSONDecodeError`` from deep inside ``json``/``pathlib``.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise SystemExit(f"{path}: file not found. Check the path passed to this flag.") from e
    except OSError as e:
        raise SystemExit(f"{path}: could not be read ({e}).") from e

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise SystemExit(f"{path}: not valid JSON ({e}).") from e

    return cast(dict[str, Any], data)


T = TypeVar("T", bound=BaseModel)


def _maybe_load(model_cls: type[T], arg: str | None, *, require_recognized_field: bool = False) -> T | None:
    """
    Load ``arg`` as JSON and validate it against ``model_cls``.

    ``require_recognized_field`` guards models where *every* field is optional (currently only
    ``ListingInsights``): for those, ``{}`` or JSON with no overlapping keys validates cleanly
    and silently produces a report section built from nothing. Models with at least one
    required field (``InvestmentThesis``, ``MediaInsights``, ``MediaReport``, ``RunProvenance``,
    ``FinancialForecast``) already reject unrelated JSON via that required field, so they do not
    need — and must not get — this extra gate: it would preempt their normal
    ``pydantic.ValidationError`` with a different message for no behavioral gain.

    A file that is sparse-but-real (e.g. only ``{"address": "..."}``) still shares at least one
    key with the model and is unaffected; absent facts are legitimate and must keep working.
    """
    if not arg:
        return None
    path = Path(arg)
    data = _read_json(path)

    if require_recognized_field and isinstance(data, dict):
        recognized = model_cls.model_fields.keys()
        if recognized.isdisjoint(data):
            raise SystemExit(
                f"{path}: no recognized {model_cls.__name__} field found among {sorted(data)!r}. "
                f"Expected at least one of {sorted(recognized)!r}. Refusing to build a report "
                "section from unrelated JSON."
            )

    # pydantic v2: model_validate is the canonical classmethod. With `T` bound to `BaseModel`,
    # the pydantic mypy plugin already resolves this to `T` — no cast needed.
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
        "--media-report",
        help="Path to MediaReport JSON (optional). Renders the Photo Coverage section.",
    )
    # Deliberately loaded, never constructed here: RunProvenance asserts which engine ran, whether
    # scenarios/vision were on, and which config was used. This CLI renders already-computed JSON
    # and makes none of those choices, so a self-constructed one would describe *this* process
    # while claiming to describe the run that produced the artifacts. Full rationale in
    # src/cli/README.md; the help text stays short because it lands in `--help` output.
    ap.add_argument(
        "--provenance",
        help=(
            "Path to RunProvenance JSON (optional), from the run that produced the other "
            "artifacts. Renders the Run Provenance pipeline rows."
        ),
    )
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

    # Load required + optional models.
    # `--forecast` is declared `required=True` above, so argparse itself rejects an omitted
    # flag before this line ever runs; the only way `args.forecast` could still be falsy here
    # is an explicit `--forecast ""`, which argparse allows (required means "present", not
    # "non-empty"). Guard that narrow case with the same accurate message before attempting
    # to read a path that isn't really there, rather than after loading — where the old check
    # lived and could never actually fire (`_read_json` now raises `SystemExit` directly on any
    # missing/unreadable/malformed file instead of returning, so `_maybe_load` never silently
    # produced a `None` for a real file-loading failure).
    if not args.forecast:
        ap.error("--forecast is required and must be valid JSON")
    forecast = _maybe_load(FinancialForecast, args.forecast)
    # Pure mypy narrowing: genuinely unreachable given the guard above, kept so
    # `write_report`'s required `forecast: FinancialForecast` parameter below type-checks.
    assert forecast is not None
    insights = _maybe_load(ListingInsights, args.insights, require_recognized_field=True)
    thesis = _maybe_load(InvestmentThesis, args.thesis)
    media = _maybe_load(MediaInsights, args.media_insights)
    media_report = _maybe_load(MediaReport, args.media_report)
    provenance = _maybe_load(RunProvenance, args.provenance)

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
        forecast=forecast,
        thesis=thesis,
        media_insights=media,
        media_report=media_report,
        provenance=provenance,
    )

    if args.title:
        txt = out_path.read_text(encoding="utf-8")
        lines = txt.splitlines()
        if lines:
            lines[0] = f"# {args.title}"
            out_path.write_text("\n".join(lines) + ("\n" if not txt.endswith("\n") else ""), encoding="utf-8")

    print(f"Wrote report → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
