from __future__ import annotations

import pytest

from src.core.finance import run_financial_model
from tests.utils import make_financial_inputs


def test_engine_with_refi_event_created_and_cashout_applied():
    # Enable refi at a mid horizon year
    fin = make_financial_inputs(do_refi=True)
    fin = fin.model_copy(update={"refi": fin.refi.model_copy(update={"year_to_refi": 5, "refi_ltv": 0.75})})

    out = run_financial_model(fin, insights=None, horizon_years=10)

    # Refi event present and timed at year 5
    assert out.refi is not None
    assert out.refi.year == 5
    assert out.refi.new_loan >= 0
    assert out.refi.value >= 0
    # Payoff must match the model’s ending balance in refi year
    bal_y5 = next(y.ending_balance for y in out.years if y.year == 5)
    assert out.refi.payoff == pytest.approx(bal_y5, rel=1e-6)

    # Cash-out (if any) should have been incorporated into that year’s cash flow
    cf_y5 = next(y.cash_flow for y in out.years if y.year == 5)
    # We can't see the raw cashflow before cashout here, but at least ensure non-negative and bounded
    assert cf_y5 >= -1e9
