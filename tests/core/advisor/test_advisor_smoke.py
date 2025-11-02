# tests/core/advisor/test_advisor_smoke.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.cli.advisor_cli import main as advisor_main
from tests.utils import _patched_argv_and_syspath, repo_root  # shared helpers


def _write_json(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def _write_minimal_jpeg(p: Path) -> None:
    """
    Write a minimal (non-displayable) JPEG: SOI + EOI markers.
    Sufficient for discovery without image libs.
    """
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\xff\xd8\xff\xd9")


@pytest.mark.integration
@pytest.mark.parametrize("use_dir_mode", [True, False])
def test_advisor_cli_smoke_module(tmp_path: Path, capsys, use_dir_mode: bool):
    """
    Smoke test: run advisor_main() in-process (no stubs).
    Creates a real deal folder (or config JSON) and asserts output shape.
    """
    deal_dir = tmp_path / "dealA"
    photos_dir = deal_dir / "photos"
    listing_path = deal_dir / "listing.txt"
    finance_json = deal_dir / "finance.json"

    # Ensure at least one discoverable image exists
    _write_minimal_jpeg(photos_dir / "1.jpg")

    # Lightweight listing body that normalizers can parse
    listing_body = (
        "47 Perrot Street, Shediac, NB E4P 0H3\n" "Price: $219,900 | 3 bed | 1 bath | 1016 sqft\n" "Heating: baseboard | Cooling: ac"
    )
    listing_path.parent.mkdir(parents=True, exist_ok=True)
    listing_path.write_text(listing_body, encoding="utf-8")

    # Simple finance input for the real loader
    _write_json(
        finance_json,
        {
            "irr": 0.10,
            "cashflow_monthly": 300,
            "price_per_sqft": 200,
            "market_ppsf": 210,
            "purchase_price": 300000,
            "area_safety_index": 0.60,
        },
    )

    out_path = tmp_path / "advisor_output.json"

    if use_dir_mode:
        # Directory discovery mode
        argv = ["advisor_cli.py", "--files", str(deal_dir), "--out", str(out_path)]
    else:
        # Explicit config JSON (real modules still used)
        cfg = {
            "listing_path": str(listing_path),
            "photos_dir": str(photos_dir),
            "finance_inputs_path": str(finance_json),
            "title": "Deal A",
        }
        cfg_path = tmp_path / "dealA.json"
        _write_json(cfg_path, cfg)
        argv = ["advisor_cli.py", "--files", str(cfg_path), "--out", str(out_path)]

    # Run the CLI in-process with proper PYTHONPATH
    with _patched_argv_and_syspath(argv, str(repo_root())):
        advisor_main()

    captured = capsys.readouterr()
    assert "Wrote" in captured.out
    assert out_path.exists()

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert "ranked" in payload and isinstance(payload["ranked"], list)
    assert len(payload["ranked"]) == 1
    item = payload["ranked"][0]
    assert "composite_score" in item
    assert "cashflow_monthly" in item
