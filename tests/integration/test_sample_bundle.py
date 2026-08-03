# tests/integration/test_sample_bundle.py
"""The committed demo bundle must stay runnable and coherent.

``python main.py`` with no arguments underwrites ``data/sample_listings/36_kelly_moncton/``.
That bundle is the project's front door, so these tests pin the properties a reader would
otherwise discover only by running it:

  * the three files exist and the config points *inside* the bundle (a stale path here is
    exactly the regression that left ``main.py`` fabricating placeholder assets);
  * the listing parses to a real address — it previously carried the postal code "U1C 2R7",
    which is not a valid Canadian code (they never begin with U), so address parsing declined
    and the report was titled "Subject Property";
  * the listing's stated area is read as an area, not as its price.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.core.ingest.listing_parser import parse_listing_text
from src.core.normalize.listing_text import parse_listing_from_text

BUNDLE = Path("data/sample_listings/36_kelly_moncton")


def test_bundle_files_exist() -> None:
    assert (BUNDLE / "listing.txt").is_file()
    assert (BUNDLE / "inputs.json").is_file()
    assert (BUNDLE / "finance.json").is_file()
    assert list((BUNDLE / "photos").glob("*.jpeg")), "bundle ships no photos"


def test_config_paths_point_inside_the_bundle() -> None:
    cfg = json.loads((BUNDLE / "inputs.json").read_text(encoding="utf-8"))
    run = cfg["run"]
    assert Path(run["listing"]) == BUNDLE / "listing.txt"
    assert Path(run["photos"]) == BUNDLE / "photos"
    # Both must resolve, or the zero-argument demo dies on a stale path.
    assert Path(run["listing"]).is_file()
    assert Path(run["photos"]).is_dir()


def test_market_block_present_so_scenarios_flag_works() -> None:
    # `--scenarios` loud-fails without a market block or a derivable cap rate.
    market = json.loads((BUNDLE / "inputs.json").read_text(encoding="utf-8")).get("market")
    assert market is not None
    for key in ("region", "vacancy_rate", "cap_rate", "rent_growth", "expense_growth", "interest_rate"):
        assert key in market, f"market block missing {key!r}"


def test_listing_yields_an_address_not_a_generic_placeholder() -> None:
    insights = parse_listing_text(str(BUNDLE / "listing.txt"))
    assert insights.address, "address failed to parse — check the postal code in listing.txt"
    assert "36 Kelly" in insights.address


def test_listing_area_is_not_the_purchase_price() -> None:
    listing = parse_listing_from_text((BUNDLE / "listing.txt").read_text(encoding="utf-8"))
    assert listing.sqft == 1936
    assert listing.price == 399900.0
    assert listing.sqft != listing.price
