from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.schemas.models import MarketSnapshot


def _get(m: Mapping[str, Any], key: str) -> Any:
    if key not in m:
        raise ValueError(f"Missing required market key: '{key}'")
    return m[key]


def _validate_snapshot(
    *,
    region: str,
    vacancy_rate: float,
    cap_rate: float,
    rent_growth: float,
    expense_growth: float,
    interest_rate: float,
) -> None:
    if not region or not isinstance(region, str):
        raise ValueError("region must be a non-empty string")

    if not (0.0 <= vacancy_rate <= 1.0):
        raise ValueError("vacancy_rate must be in [0, 1]")

    if cap_rate <= 0.0:
        raise ValueError("cap_rate must be > 0")

    # Allow negative growth for downturn scenarios, but bound for sanity.
    if not (-1.0 <= rent_growth <= 1.0):
        raise ValueError("rent_growth must be between -1 and 1 (i.e., -100%..100%)")

    if not (-1.0 <= expense_growth <= 1.0):
        raise ValueError("expense_growth must be between -1 and 1 (i.e., -100%..100%)")

    if interest_rate < 0.0:
        raise ValueError("interest_rate must be ≥ 0")


def build_snapshot(user_inputs: Mapping[str, Any]) -> MarketSnapshot:
    """
    Deterministically construct a MarketSnapshot from structured inputs.

    Expected structure (either top-level or under 'market'):
    {
      "region": "Metro A",
      "vacancy_rate": 0.06,
      "cap_rate": 0.055,
      "rent_growth": 0.03,
      "expense_growth": 0.025,
      "interest_rate": 0.047,
      "notes": "from inputs.json"
    }
    """
    market: Mapping[str, Any]
    if "market" in user_inputs and isinstance(user_inputs["market"], Mapping):
        market = user_inputs["market"]  # nested form
    else:
        market = user_inputs  # flat form

    region = str(_get(market, "region"))
    vacancy_rate = float(_get(market, "vacancy_rate"))
    cap_rate = float(_get(market, "cap_rate"))
    rent_growth = float(_get(market, "rent_growth"))
    expense_growth = float(_get(market, "expense_growth"))
    interest_rate = float(_get(market, "interest_rate"))
    notes_val = market.get("notes")
    notes: str | None = str(notes_val) if notes_val is not None else None

    _validate_snapshot(
        region=region,
        vacancy_rate=vacancy_rate,
        cap_rate=cap_rate,
        rent_growth=rent_growth,
        expense_growth=expense_growth,
        interest_rate=interest_rate,
    )

    return MarketSnapshot(
        region=region,
        vacancy_rate=vacancy_rate,
        cap_rate=cap_rate,
        rent_growth=rent_growth,
        expense_growth=expense_growth,
        interest_rate=interest_rate,
        notes=notes,
    )
