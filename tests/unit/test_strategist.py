# tests/unit/test_strategist.py
from __future__ import annotations

from src.core.finance import run_financial_model
from src.core.strategy.strategist import form_thesis
from tests.utils import make_financial_inputs


def test_strategist_verdict_fields_present():
    fin = make_financial_inputs(do_refi=False)
    ff = run_financial_model(fin, insights=None, horizon_years=10)
    thesis = form_thesis(ff, fin.market)
    assert thesis.verdict in {"BUY", "CONDITIONAL", "PASS"}
    assert isinstance(thesis.rationale, list)
