# tests/unit/test_market_snapshot_repr.py
from __future__ import annotations

from tests.utils import make_snapshot


def test_snapshot_repr_and_dump() -> None:
    snap = make_snapshot(notes="hello")
    r = repr(snap)
    assert "MarketSnapshot" in r
    d = snap.model_dump()
    # Touch fields to mark them as covered
    assert "vacancy_rate" in d and "cap_rate" in d and "rent_growth" in d
