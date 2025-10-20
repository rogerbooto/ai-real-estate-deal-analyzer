# tests/unit/test_market_hypotheses_more_branches.py
from __future__ import annotations

from src.schemas.models import MarketHypothesis


def test_summary_covers_zero_and_negative_arrows() -> None:
    """
    Hit remaining summary formatting branches:
      - zero deltas -> ➝
      - negative deltas -> ▼
      - STR viability False -> N
    """
    h = MarketHypothesis(
        rent_delta=0.0,  # ➝
        expense_growth_delta=-0.01,  # ▼
        interest_rate_delta=0.0,  # ➝
        cap_rate_delta=-0.0015,  # ▼
        vacancy_delta=0.0,  # ➝
        str_viability=False,  # N
        prior=0.075,  # 7.50%
        rationale="branch coverage",
    )
    s = h.summary()
    assert "Rent: ➝ 0.00%" in s
    assert "Opex: ▼ 1.00%" in s
    assert "Rate: ➝ 0.00%" in s
    assert "Cap: ▼ 0.15%" in s
    assert "Vac: ➝ 0.00%" in s
    assert "prior=7.50%" in s
    assert "STR=N" in s

    # Also touch as_dict to cover that path
    d = h.as_dict()
    assert d["prior"] == 0.075 and d["str_viability"] is False
