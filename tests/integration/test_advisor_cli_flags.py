# tests/integration/test_advisor_cli_flags.py
"""
Mission 2, Wave 2 — advisor_cli flag honesty (F12, F13, F17).

F12: --debug used to be dead (parsed but never read). It now prints the full
     ranked/portfolio JSON payload to stdout, on top of the compact table that
     is always printed.
F13: --markdown used to clobber the JSON artifact whenever --out already ended
     in .md (md_path = out_path.with_suffix(".md") == out_path). It must now
     write the Markdown summary to a distinct file and leave the JSON intact.
F17: the "missing required key(s)" error used to point at
     data/sample_listings/36_kelly_moncton/inputs.json "as an example" -- a
     file whose top-level keys (inputs/run/market) don't match what --files
     config JSONs need (listing_path/photos_dir/finance_inputs_path). It now
     points at a real, working example.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.cli.advisor_cli import main as advisor_main, normalize_input
from tests.utils import _patched_argv_and_syspath, repo_root


def _write_json(p: Path, obj: object) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def _build_deal_dir(deal_dir: Path, *, cashflow: float = 300.0) -> None:
    photos_dir = deal_dir / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)
    (photos_dir / "1.jpg").write_bytes(b"\xff\xd8\xff\xd9")  # minimal JPEG (SOI+EOI)

    (deal_dir / "listing.txt").write_text(
        "47 Perrot Street, Shediac, NB E4P 0H3\nPrice: $219,900 | 3 bed | 1 bath | 1016 sqft\nHeating: baseboard | Cooling: ac",
        encoding="utf-8",
    )
    _write_json(
        deal_dir / "finance.json",
        {
            "irr": 0.10,
            "cashflow_monthly": cashflow,
            "price_per_sqft": 200,
            "market_ppsf": 210,
            "purchase_price": 300000,
            "area_safety_index": 0.60,
        },
    )


# ---------------------------------------------------------------------------
# F12 — --debug prints the full ranked/portfolio payload to stdout
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_debug_flag_prints_full_payload_to_stdout(tmp_path: Path, capsys):
    deal_dir = tmp_path / "dealA"
    _build_deal_dir(deal_dir)
    out_path = tmp_path / "advisor_output.json"

    argv = ["advisor_cli.py", "--files", str(deal_dir), "--out", str(out_path), "--debug"]
    with _patched_argv_and_syspath(argv, str(repo_root())):
        advisor_main()

    captured = capsys.readouterr()
    file_payload = json.loads(out_path.read_text(encoding="utf-8"))

    # The full payload (as written to --out) must appear verbatim in stdout.
    assert json.dumps(file_payload, indent=2) in captured.out
    # Sanity: it's genuinely the full structure, not just the compact table
    # (which never prints raw JSON keys like "composite_score").
    assert '"composite_score"' in captured.out
    assert '"portfolio"' in captured.out


@pytest.mark.integration
def test_without_debug_flag_full_payload_is_not_printed(tmp_path: Path, capsys):
    deal_dir = tmp_path / "dealA"
    _build_deal_dir(deal_dir)
    out_path = tmp_path / "advisor_output.json"

    argv = ["advisor_cli.py", "--files", str(deal_dir), "--out", str(out_path)]
    with _patched_argv_and_syspath(argv, str(repo_root())):
        advisor_main()

    captured = capsys.readouterr()
    # No --debug -> no raw JSON payload dump (the compact table has no quoted keys).
    assert '"composite_score"' not in captured.out
    assert '"portfolio"' not in captured.out


# ---------------------------------------------------------------------------
# F13 — --markdown must never clobber the JSON when --out ends in .md
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_markdown_does_not_clobber_json_when_out_ends_in_md(tmp_path: Path, capsys):
    deal_dir = tmp_path / "dealA"
    _build_deal_dir(deal_dir)
    out_path = tmp_path / "advisor_output.md"  # deliberately ends in .md

    argv = ["advisor_cli.py", "--files", str(deal_dir), "--out", str(out_path), "--markdown"]
    with _patched_argv_and_syspath(argv, str(repo_root())):
        advisor_main()

    # The JSON artifact at --out must still be valid JSON, not overwritten by Markdown.
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert "ranked" in payload and "portfolio" in payload

    # The Markdown summary must have been written to a *different* file.
    md_path = out_path.with_name(out_path.stem + "_report.md")
    assert md_path.exists()
    assert md_path != out_path
    md_text = md_path.read_text(encoding="utf-8")
    assert md_text.startswith("# Deal Advisor Report")

    # The clobber must be surfaced, not silent.
    captured = capsys.readouterr()
    assert "Note:" in captured.out


@pytest.mark.integration
def test_markdown_normal_case_out_is_json(tmp_path: Path):
    """When --out doesn't end in .md, behavior is unchanged: sibling <stem>.md file."""
    deal_dir = tmp_path / "dealA"
    _build_deal_dir(deal_dir)
    out_path = tmp_path / "advisor_output.json"

    argv = ["advisor_cli.py", "--files", str(deal_dir), "--out", str(out_path), "--markdown"]
    with _patched_argv_and_syspath(argv, str(repo_root())):
        advisor_main()

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert "ranked" in payload

    md_path = out_path.with_suffix(".md")
    assert md_path.exists()
    assert md_path.read_text(encoding="utf-8").startswith("# Deal Advisor Report")


# ---------------------------------------------------------------------------
# F17 — the --files error message points at a real, working example
# ---------------------------------------------------------------------------


def test_missing_keys_error_cites_a_real_example_file():
    with pytest.raises(SystemExit) as exc_info:
        normalize_input({"listing_path": "x"})

    message = str(exc_info.value)
    assert "photos_dir" in message and "finance_inputs_path" in message

    # Extract the cited example path and confirm it exists and has the keys
    # --files config JSONs actually require (not inputs.json's inputs/run/market shape).
    example_path = repo_root() / "data" / "examples" / "advisor_deal_config.json"
    assert str(example_path.relative_to(repo_root())).replace("\\", "/") in message
    assert example_path.exists(), f"cited example {example_path} does not exist"

    cited = json.loads(example_path.read_text(encoding="utf-8"))
    for key in ("listing_path", "photos_dir", "finance_inputs_path"):
        assert key in cited and cited[key]


@pytest.mark.integration
def test_cited_example_command_actually_runs(tmp_path: Path):
    """
    Reproduce the exact command the error message tells the user to run, verbatim,
    and confirm it succeeds end-to-end (Gate-1-blocker class: a documented example
    must actually work).
    """
    out_path = tmp_path / "advisor_output.json"
    argv = [
        "advisor_cli.py",
        "--files",
        "data/examples/advisor_deal_config.json",
        "--out",
        str(out_path),
    ]
    with _patched_argv_and_syspath(argv, str(repo_root())):
        import os

        old_cwd = os.getcwd()
        os.chdir(str(repo_root()))
        try:
            advisor_main()
        finally:
            os.chdir(old_cwd)

    assert out_path.exists()
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert len(payload["ranked"]) == 1
