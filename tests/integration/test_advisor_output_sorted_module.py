# tests/integration/test_advisor_output_sorted_module.py
from __future__ import annotations

import json
from pathlib import Path

from src.cli.advisor_cli import main as advisor_main
from tests.utils import _patched_argv_and_syspath, repo_root


def _write_json(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def test_output_sorted_desc_module(tmp_path: Path):
    """
    Integration test: verify that advisor_cli correctly ranks multiple deals
    in descending order by composite score using real ingestion.
    """

    # ---- Build two deal directories
    deal_low = tmp_path / "deal_low"
    deal_high = tmp_path / "deal_high"

    for deal_dir, cashflow in [(deal_low, 200), (deal_high, 500)]:
        photos_dir = deal_dir / "photos"
        photos_dir.mkdir(parents=True, exist_ok=True)
        (photos_dir / "1.jpg").write_bytes(b"\xff\xd8\xff\xd9")  # minimal JPEG
        listing_path = deal_dir / "listing.txt"
        listing_path.write_text(
            "47 Perrot Street, Shediac, NB E4P 0H3\n" "Price: $219,900 | 3 bed | 1 bath | 1016 sqft\n" "Heating: baseboard | Cooling: ac",
            encoding="utf-8",
        )

        # Distinct finance inputs control ranking
        finance_json = deal_dir / "finance.json"
        _write_json(
            finance_json,
            {
                "irr": 0.10 if cashflow == 200 else 0.16,
                "cashflow_monthly": cashflow,
                "price_per_sqft": 200,
                "market_ppsf": 210,
                "purchase_price": 300000,
                "area_safety_index": 0.6,
            },
        )

    # ---- Build CLI args (use directory mode)
    out_path = tmp_path / "advisor_output.json"
    argv = [
        "advisor_cli.py",
        "--files",
        str(deal_low),
        str(deal_high),
        "--out",
        str(out_path),
    ]

    # ---- Run the CLI in-process
    with _patched_argv_and_syspath(argv, str(repo_root())):
        advisor_main()

    # ---- Validate ranked output
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    ranked = payload["ranked"]
    scores = [item["composite_score"] for item in ranked]

    # Highest cashflow should yield the highest score
    assert scores == sorted(scores, reverse=True)
    assert len(ranked) == 2
