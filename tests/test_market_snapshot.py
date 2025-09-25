from __future__ import annotations

import pytest

from src.market.snapshot import build_snapshot
from src.schemas.models import MarketSnapshot


def test_build_snapshot_valid_nested() -> None:
    inputs = {
        "market": {
            "region": "Metro A",
            "vacancy_rate": 0.06,
            "cap_rate": 0.055,
            "rent_growth": 0.03,
            "expense_growth": 0.025,
            "interest_rate": 0.047,
            "notes": "baseline",
        }
    }

    snap = build_snapshot(inputs)
    assert isinstance(snap, MarketSnapshot)
    assert snap.region == "Metro A"
    assert snap.vacancy_rate == 0.06
    assert snap.cap_rate == 0.055
    assert snap.rent_growth == 0.03
    assert snap.expense_growth == 0.025
    assert snap.interest_rate == 0.047
    assert "Vacancy" in snap.summary()


@pytest.mark.parametrize(
    "bad_key,bad_value,err_msg",
    [
        ("vacancy_rate", 1.2, "vacancy_rate"),
        ("vacancy_rate", -0.1, "vacancy_rate"),
        ("cap_rate", 0.0, "cap_rate"),
        ("cap_rate", -0.01, "cap_rate"),
        ("rent_growth", 1.2, "rent_growth"),
        ("rent_growth", -1.2, "rent_growth"),
        ("expense_growth", 1.5, "expense_growth"),
        ("interest_rate", -0.001, "interest_rate"),
    ],
)
def test_build_snapshot_invalid_values(bad_key: str, bad_value: float, err_msg: str) -> None:
    base = {
        "region": "Metro B",
        "vacancy_rate": 0.05,
        "cap_rate": 0.06,
        "rent_growth": 0.02,
        "expense_growth": 0.02,
        "interest_rate": 0.05,
    }
    base[bad_key] = bad_value
    with pytest.raises(ValueError) as ei:
        build_snapshot(base)
    assert err_msg in str(ei.value)


def test_build_snapshot_missing_key() -> None:
    base = {
        "region": "Metro C",
        "vacancy_rate": 0.05,
        "cap_rate": 0.06,
        "rent_growth": 0.02,
        "expense_growth": 0.02,
        # "interest_rate" missing
    }
    with pytest.raises(ValueError) as ei:
        build_snapshot(base)
    assert "interest_rate" in str(ei.value)
