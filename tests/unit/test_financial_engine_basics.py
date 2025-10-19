# tests/unit/test_financial_engine_basics.py

from __future__ import annotations

import pytest

from src.core.finance import run_financial_model
from tests.utils import make_financial_inputs


def test_engine_baseline_no_refi():
    fin = make_financial_inputs(do_refi=False)
    # Sanity: keep defaults; no insights
    out = run_financial_model(fin, insights=None, horizon_years=10)

    # Purchase metrics computed
    assert out.purchase.annual_debt_service > 0
    assert out.purchase.cap_rate > 0
    assert out.purchase.spread_vs_rate == pytest.approx(out.purchase.cap_rate - fin.financing.interest_rate, abs=1e-12)

    # Year 1 exists and DSCR, CoC are sensible numbers
    y1 = out.years[0]
    assert y1.debt_service == pytest.approx(out.purchase.annual_debt_service, rel=1e-9)
    assert y1.dscr >= 0
    # CoC should be CF/Acq cash (can be small but defined)
    assert out.purchase.coc == pytest.approx(
        y1.cash_flow / out.purchase.acquisition_cash if out.purchase.acquisition_cash else 0.0, rel=1e-9
    )

    # Terminal equity included in final year cash flow (positive or zero)
    assert out.years[-1].ending_balance >= 0
    assert out.irr_10yr >= -1.0  # bounded
    assert out.equity_multiple_10yr >= 0.0
