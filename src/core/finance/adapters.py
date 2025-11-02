# src/core/finance/adapters.py


from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class FinanceSummary(BaseModel):
    irr: float
    cashflow_monthly: float
    price_per_sqft: float
    market_ppsf: float
    purchase_price: float
    area_safety_index: float


def finance_summary_from_json(path: str | Path) -> FinanceSummary:
    p = Path(path)
    data: dict[str, Any] = json.loads(p.read_text())
    # Accept both flat and nested under "forecast"
    src = data.get("forecast", data)
    return FinanceSummary(
        irr=float(src["irr"]),
        cashflow_monthly=float(src["cashflow_monthly"]),
        price_per_sqft=float(src["price_per_sqft"]),
        market_ppsf=float(src["market_ppsf"]),
        purchase_price=float(src["purchase_price"]),
        area_safety_index=float(src.get("area_safety_index", 0.5)),
    )
