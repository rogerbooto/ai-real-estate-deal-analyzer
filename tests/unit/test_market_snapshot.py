# tests/unit/test_market_snapshot.py

from __future__ import annotations

import pytest

from src.market.snapshot import build_snapshot
from src.schemas.models import MarketSnapshot
from tests.utils import make_snapshot  # central source


def test_build_snapshot_valid_nested() -> None:
    inputs = {
        "market": {
            "region": "Metro A",
            "vacancy_rate": 0.06,
            "cap_rate": 0.055,
            "rent_growth": 0.03,
            "expense_growth": 0.02,
            "interest_rate": 0.045,
        }
    }
    snap = build_snapshot(inputs)
    assert isinstance(snap, MarketSnapshot)
    assert snap.region == "Metro A"
    assert snap.vacancy_rate == 0.06
    assert snap.cap_rate == 0.055
    assert snap.rent_growth == 0.03
    assert snap.expense_growth == 0.02
    assert snap.interest_rate == 0.045

    # round-trip via factory for equality of core fields
    ref = make_snapshot(
        region="Metro A",
        vacancy_rate=0.06,
        cap_rate=0.055,
        rent_growth=0.03,
        expense_growth=0.02,
        interest_rate=0.045,
    )
    assert snap.region == ref.region
    assert snap.cap_rate == ref.cap_rate


def test_build_snapshot_validation_errors() -> None:
    with pytest.raises(ValueError):
        build_snapshot({"market": {"region": "", "vacancy_rate": 0.05}})
    with pytest.raises(ValueError):
        build_snapshot({"market": {"region": "A", "cap_rate": -0.01}})
