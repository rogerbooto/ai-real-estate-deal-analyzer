# src/cli/advisor_cli.py
from __future__ import annotations

import argparse
import csv
import glob as _glob
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

import src.core.finance.adapters as fin_adapters
import src.core.ingest as ingest_mod
from src.core.advisor.portfolio import portfolio_summary
from src.core.advisor.recommender import rank_deals
from src.core.intelligence.deal_fusion import fuse_deal_intelligence

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".heic", ".bmp")


def _is_textlike(x: Any) -> bool:
    # Avoid tuple in isinstance() to keep Ruff happy and keep runtime safe
    return isinstance(x, str) or isinstance(x, bytes)


def _coerce_candidates(val: Any) -> list[str]:
    if val is None:
        return []
    if _is_textlike(val):
        return [str(val)]
    if isinstance(val, Sequence):
        return [str(v) for v in val]
    return [str(val)]


def _looks_like_image(p: Path) -> bool:
    return p.suffix.lower() in IMAGE_EXTS


def normalize_input(d: dict[str, Any]) -> dict[str, Any]:
    out = dict(d)
    if "listing_path" not in out and "listing_text_path" in out:
        out["listing_path"] = out["listing_text_path"]

    required = ("listing_path", "photos_dir", "finance_inputs_path")
    missing = [k for k in required if k not in out or not out[k]]
    if missing:
        raise SystemExit(
            f"Input is missing required key(s): {', '.join(missing)}. "
            "A --files config JSON needs listing_path, photos_dir, and finance_inputs_path "
            "(optional title) -- see data/examples/advisor_deal_config.json for a working example "
            "(run: python -m src.cli.advisor_cli --files data/examples/advisor_deal_config.json), "
            "or point --files/--dir at a bundle directory (e.g. data/sample_listings/36_kelly_moncton) "
            "for auto-discovery instead."
        )
    return out


def _discover_listing_file(deal_dir: Path) -> Path | None:
    candidates = [
        deal_dir / "listing.txt",
        deal_dir / "listing.md",
        deal_dir / "listing.html",
    ]
    if not any(c.exists() for c in candidates):
        candidates.extend(deal_dir.glob("*.txt"))
        candidates.extend(deal_dir.glob("*.md"))
        candidates.extend(deal_dir.glob("*.html"))
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    return None


def discover_deal_in_dir(deal_dir: Path) -> dict[str, Any]:
    if not deal_dir.is_dir():
        raise SystemExit(f"{deal_dir} is not a directory")

    listing_path = _discover_listing_file(deal_dir)
    photos_dir = deal_dir / "photos"
    finance_json = deal_dir / "finance.json"

    cfg_override: dict[str, Any] = {}
    override_path = deal_dir / "inputs.json"
    if override_path.exists():
        cfg_override = json.loads(override_path.read_text(encoding="utf-8"))

    cfg: dict[str, Any] = {
        "listing_path": cfg_override.get("listing_path") or (str(listing_path) if listing_path else None),
        "photos_dir": cfg_override.get("photos_dir") or (str(photos_dir) if photos_dir.exists() else None),
        "finance_inputs_path": cfg_override.get("finance_inputs_path") or (str(finance_json) if finance_json.exists() else None),
        "title": cfg_override.get("title") or deal_dir.name.replace("_", " ").title(),
    }

    if cfg["photos_dir"] and Path(cfg["photos_dir"]).is_dir():
        pdir = Path(cfg["photos_dir"])
        if not any(_looks_like_image(p) for p in pdir.iterdir() if p.is_file()):
            pass

    return normalize_input(cfg)


def load_deal_from_config(config_path: Path) -> Any:
    cfg = json.loads(Path(config_path).read_text(encoding="utf-8"))
    cfg = normalize_input(cfg)

    listing_path = Path(cfg["listing_path"])
    photos_dir = Path(cfg["photos_dir"])
    finance_inputs_path = Path(cfg["finance_inputs_path"])

    ingest_result = ingest_mod.run_ingest(file=listing_path, photos_dir=photos_dir)

    if ingest_result is None:
        raise SystemExit(f"Ingest failed for listing at {listing_path}")

    finance_summary = fin_adapters.finance_summary_from_json(finance_inputs_path)

    deal = fuse_deal_intelligence(
        ingest_result.listing,
        ingest_result.photos,
        finance_summary,
    )
    return deal


def load_deal_from_dir(deal_dir: Path) -> Any:
    cfg = discover_deal_in_dir(deal_dir)

    listing_path = Path(cfg["listing_path"])
    photos_dir = Path(cfg["photos_dir"])
    finance_inputs_path = Path(cfg["finance_inputs_path"])

    ingest_result = ingest_mod.run_ingest(file=listing_path, photos_dir=photos_dir)
    finance_summary = fin_adapters.finance_summary_from_json(finance_inputs_path)

    deal = fuse_deal_intelligence(
        ingest_result.listing,
        ingest_result.photos,
        finance_summary,
    )
    return deal


def _write_csvs(out_path: Path, ranked: list[tuple[Any, float]], portfolio: dict[str, Any]) -> None:
    """Write <out>_deals.csv and <out>_portfolio.csv next to the JSON output."""
    deals_csv = out_path.with_name(out_path.stem + "_deals.csv")
    port_csv = out_path.with_name(out_path.stem + "_portfolio.csv")

    # Deals CSV
    with deals_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "rank",
                "title",
                "address",
                "postal_code",
                "score",
                "cashflow_monthly",
                "price",
                "title_confidence",
                "title_source",
                "title_candidates",
                "city",
                "state_province",
                "source_url",
                "risk_flags",
            ]
        )
        for idx, (d, score) in enumerate(ranked, start=1):
            ln = d.listing
            adr = getattr(ln, "address_structure", None)
            flags = getattr(d, "risk_flags", []) or []
            if _is_textlike(flags):
                risk_flags_str = str(flags)
            elif isinstance(flags, Sequence):
                risk_flags_str = ";".join(str(f) for f in flags)
            else:
                risk_flags_str = str(flags or "")

            raw_cands = getattr(ln, "title_candidates", None) if ln else None
            cand_list = _coerce_candidates(raw_cands)
            title_candidates_str = " | ".join(cand_list) if cand_list else None

            w.writerow(
                [
                    idx,
                    getattr(ln, "title", None),
                    getattr(ln, "address", None),
                    getattr(ln, "postal_code", None),
                    float(score),
                    float(getattr(d.finance, "cashflow_monthly", 0.0)),
                    getattr(ln, "price", None),
                    getattr(ln, "title_confidence", None),
                    getattr(ln, "title_source", None),
                    title_candidates_str,
                    getattr(adr, "city", None) if adr else None,
                    getattr(adr, "state_province", None) if adr else None,
                    getattr(ln, "source_url", None),
                    risk_flags_str,
                ]
            )

    # Portfolio CSV
    with port_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        keys = ["avg_score", "total_cashflow", "risk_items"]
        w.writerow(keys)
        w.writerow([portfolio.get(k) for k in keys])

    print(f"Wrote {deals_csv}")
    print(f"Wrote {port_csv}")


def _expand_globs(patterns: list[str]) -> list[Path]:
    out: list[Path] = []
    for pat in patterns:
        for m in _glob.iglob(pat, recursive=True):
            out.append(Path(m))
    return out


def _collect_input_paths(args: argparse.Namespace) -> list[Path]:
    """
    Combine --files, --dir, and --glob into a single list of paths.
    - Directories are kept as-is (bundle discovery).
    - Files are kept as-is (config JSON path).
    - Globs are expanded and filtered to dirs or *.json files.
    """
    paths: list[Path] = []

    # --files (existing behavior)
    for p in args.files or []:
        paths.append(Path(p))

    # --dir (one or more directories)
    for d in args.dir or []:
        paths.append(Path(d))

    # --glob (expand shell patterns)
    for p in _expand_globs(args.glob or []):
        if p.is_dir() or p.suffix.lower() == ".json":
            paths.append(p)

    # de-dup while preserving order
    seen: set[Path] = set()
    uniq: list[Path] = []
    for p in paths:
        if p not in seen:
            uniq.append(p)
            seen.add(p)
    return uniq


def _print_compact_table(ranked: list[tuple[Any, float]]) -> None:
    """
    Print a tiny, dependency-free table with key fields.
    Columns: Rank | Title | Score | Cashflow/mo | Flags
    """
    rows: list[tuple[str, str, str, str, str]] = []
    for idx, (d, score) in enumerate(ranked, start=1):
        title = (getattr(d.listing, "title", None) or getattr(d, "shortname", "") or "")[:54]
        score_s = f"{float(score):.2f}"
        cf_s = f"{float(getattr(d.finance, 'cashflow_monthly', 0.0)):.2f}"
        flags = getattr(d, "risk_flags", []) or []
        flags_s = ",".join(flags)[:28]
        rows.append((str(idx), title, score_s, cf_s, flags_s))

    headers = ("#", "Title", "Score", "Cash/mo", "Flags")
    data = [headers, *rows]
    widths = [max(len(str(r[i])) for r in data) for i in range(len(headers))]

    def _fmt(row: tuple[str, str, str, str, str]) -> str:
        cells = []
        for i, v in enumerate(row):
            align = "<" if i in (1, 4) else ">"
            cells.append(f"{v:{align}{widths[i]}}")
        return "  ".join(cells)

    if rows:
        print(_fmt(headers))
        print("  ".join("-" * w for w in widths))
        for r in rows:
            print(_fmt(r))


def main() -> None:
    ap = argparse.ArgumentParser(description="Rank multiple deals and summarize a portfolio.")
    ap.add_argument(
        "--urls",
        nargs="*",
        help=(
            "Listing URLs to ingest (offline-first if cached). " "Note: URL mode requires a finance mapping; not supported in this build."
        ),
    )
    ap.add_argument(
        "--files",
        nargs="*",
        help=(
            "Paths to per-deal DIRECTORIES (auto-discovery: listing, photos/, finance.json, optional inputs.json) "
            "or per-deal CONFIG JSONs (listing_path|listing_text_path, photos_dir, finance_inputs_path, optional title)."
        ),
    )
    ap.add_argument(
        "--dir",
        nargs="*",
        help="One or more bundle directories to ingest (each should contain photos/, listing.(txt|md|html), finance.json).",
    )
    ap.add_argument(
        "--glob",
        nargs="*",
        help='One or more patterns to expand (e.g., "data/sample_listings/*" or "**/*.json").',
    )
    ap.add_argument(
        "--out",
        default="advisor_output.json",
        help="Output JSON artifact path (default: advisor_output.json).",
    )
    ap.add_argument(
        "--export-csv",
        action="store_true",
        help="Also export CSV summaries next to --out.",
    )
    ap.add_argument(
        "--debug",
        action="store_true",
        help="Print the full ranked/portfolio JSON payload to stdout, in addition to the compact table.",
    )
    ap.add_argument(
        "--save-artifacts",
        action="store_true",
        help="Dump intermediate artifacts (per-deal JSON) next to --out.",
    )
    ap.add_argument(
        "--markdown",
        action="store_true",
        help="Emit a Markdown summary next to --out.",
    )
    args = ap.parse_args()

    if args.urls:
        raise SystemExit(
            "URL mode is not supported without a finance mapping. " "Use --files/--dir/--glob with per-deal directories or config JSONs."
        )

    input_paths = _collect_input_paths(args)
    deals: list[Any] = []
    for p in input_paths:
        if p.is_dir():
            deal = load_deal_from_dir(p)
        else:
            deal = load_deal_from_config(p)
        deals.append(deal)

    if not deals:
        raise SystemExit("No deals provided. Use --files/--dir/--glob to specify one or more inputs.")

    ranked: list[tuple[Any, float]] = rank_deals(deals)
    _print_compact_table(ranked)

    ranked_payload: list[dict[str, Any]] = []
    for d, score in ranked:
        ln = getattr(d, "listing", None)
        addr_struct = getattr(ln, "address_structure", None)
        ranked_payload.append(
            {
                "title": getattr(ln, "title", None) or getattr(d, "shortname", None),
                "address": getattr(ln, "address", None),
                "composite_score": float(score),
                "cashflow_monthly": float(getattr(d.finance, "cashflow_monthly", 0.0)),
                "risk_flags": getattr(d, "risk_flags", []),
                "summary": getattr(ln, "summary", lambda: "")() if hasattr(ln, "summary") else None,
                "title_confidence": getattr(ln, "title_confidence", None),
                "title_source": getattr(ln, "title_source", None),
                "title_candidates": _coerce_candidates(getattr(ln, "title_candidates", None)),
                "address_structure": (addr_struct.model_dump() if addr_struct else None),
                "postal_code": getattr(ln, "postal_code", None),
                "source_url": getattr(ln, "source_url", None),
            }
        )

    payload: dict[str, Any] = {
        "ranked": ranked_payload,
        "portfolio": portfolio_summary([d for d, _ in ranked]),
    }

    if args.debug:
        # The compact table above is a summary; --debug dumps the exact
        # ranked/portfolio structure that will be written to --out, so it's
        # useful for troubleshooting without opening the output file.
        print(json.dumps(payload, indent=2))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")

    if args.export_csv:
        _write_csvs(out_path, ranked, cast(dict[str, Any], payload["portfolio"]))

    if args.markdown:
        md_path = out_path.with_suffix(".md")
        if md_path == out_path:
            # --out already ends in .md, so out_path *is* the JSON artifact we
            # just wrote above. Deriving the Markdown path with with_suffix()
            # would resolve to the same file and overwrite that JSON with the
            # Markdown summary -- silent data loss. Use a distinct filename
            # instead, and say so loudly rather than clobbering quietly.
            md_path = out_path.with_name(out_path.stem + "_report.md")
            print(f"Note: --out ends in .md, so writing Markdown to {md_path} instead, to avoid overwriting the JSON at {out_path}.")
        lines = ["# Deal Advisor Report", ""]

        ranked_list = cast(list[dict[str, Any]], payload["ranked"])
        for i, item in enumerate(ranked_list, start=1):
            lines.append(f"## {i}. {item['title'] or '(untitled)'}")
            lines.append(f"- Address: {item['address']}")
            lines.append(f"- Score: **{item['composite_score']:.2f}**")
            lines.append(f"- Cashflow (monthly): **{item['cashflow_monthly']:.2f}**")
            if item.get("title_confidence") is not None:
                lines.append(f"- Title Confidence: {item['title_confidence']:.2f} ({item.get('title_source')})")
            if item.get("summary"):
                lines.append(f"- Summary: {item['summary']}")
            lines.append("")
        lines.append("## Portfolio")
        portfolio_dict = cast(dict[str, Any], payload["portfolio"])
        lines.append(f"- Average Score: **{float(portfolio_dict['avg_score']):.2f}**")
        lines.append(f"- Total Cashflow: **{float(portfolio_dict['total_cashflow']):.2f}**")
        lines.append(f"- Risk Items: **{float(portfolio_dict['risk_items']):.2f}**")
        md_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"Wrote {md_path}")

    if args.save_artifacts:
        art_dir = out_path.with_suffix("").with_name(out_path.stem + "_artifacts")
        art_dir.mkdir(parents=True, exist_ok=True)
        for idx, (d, score) in enumerate(ranked, start=1):
            (art_dir / f"deal_{idx:02d}.json").write_text(
                json.dumps(
                    {
                        "score": float(score),
                        "listing": d.listing.model_dump(),
                        "finance": d.finance.model_dump() if hasattr(d.finance, "model_dump") else d.finance.__dict__,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        print(f"Wrote artifacts to {art_dir}")


if __name__ == "__main__":
    main()
