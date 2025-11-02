# tests/core/advisor/test_discovery.py
from __future__ import annotations

import json
from pathlib import Path

from src.cli.advisor_cli import discover_deal_in_dir


def test_discover_minimal_dir(tmp_path: Path, document_factory, photo_dir: Path):
    """
    Use existing fixtures to emulate a deal directory with:
      - listing.txt (from document_factory)
      - photos/ (from photo_dir, copied under deal dir)
      - finance.json (tiny inline)
    Then assert discovery returns normalized keys.
    """
    deal_dir = tmp_path / "20_gallagher"
    deal_dir.mkdir(parents=True, exist_ok=True)

    # listing.txt via factory
    listing_path = document_factory(text="Charming duplex", filename="listing.txt")
    listing_target = deal_dir / "listing.txt"
    listing_target.write_text(listing_path.read_text(encoding="utf-8"), encoding="utf-8")

    # photos/: copy fixture files into the new location
    photos_target = deal_dir / "photos"
    photos_target.mkdir(parents=True, exist_ok=True)
    for p in photo_dir.iterdir():
        (photos_target / p.name).write_bytes(p.read_bytes())

    # finance.json (minimal)
    (deal_dir / "finance.json").write_text(
        json.dumps(
            {
                "irr": 0.10,
                "cashflow_monthly": 300,
                "price_per_sqft": 200,
                "market_ppsf": 210,
                "purchase_price": 300000,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    cfg = discover_deal_in_dir(deal_dir)
    assert cfg["listing_path"].endswith("listing.txt")
    assert cfg["photos_dir"].endswith("photos")
    assert cfg["finance_inputs_path"].endswith("finance.json")
    assert "title" in cfg and isinstance(cfg["title"], str)


def test_discover_with_overrides_inputs_json(tmp_path: Path, document_factory, photo_dir: Path):
    """
    Provide inputs.json to override title and ensure discovery respects it.
    """
    deal_dir = tmp_path / "sample_deal"
    deal_dir.mkdir(parents=True, exist_ok=True)

    # listing.md to exercise alternate extension
    listing_md = document_factory(text="# Modern loft", filename="listing.md")
    (deal_dir / "listing.md").write_text(listing_md.read_text(encoding="utf-8"), encoding="utf-8")

    # photos
    photos_target = deal_dir / "photos"
    photos_target.mkdir(parents=True, exist_ok=True)
    for p in photo_dir.iterdir():
        (photos_target / p.name).write_bytes(p.read_bytes())

    # finance.json
    (deal_dir / "finance.json").write_text(
        json.dumps(
            {
                "irr": 0.12,
                "cashflow_monthly": 350,
                "price_per_sqft": 220,
                "market_ppsf": 240,
                "purchase_price": 350000,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    # inputs.json override
    (deal_dir / "inputs.json").write_text(json.dumps({"title": "Custom Title"}, indent=2), encoding="utf-8")

    cfg = discover_deal_in_dir(deal_dir)
    assert cfg["listing_path"].endswith("listing.md")
    assert cfg["title"] == "Custom Title"
