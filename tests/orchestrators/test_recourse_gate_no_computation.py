# tests/orchestrators/test_recourse_gate_no_computation.py
"""Mission 4 (task I.2): the pre-computation gate does not merely return `None` for a not-close
deal -- it must never CALL `compute_recourse` at all. This is the operational form of Roger's
Gate D veto against "compute it, then discard it post-hoc" (see `src/market/recourse.py`'s module
docstring and `docs/plans/MISSION_4_SPRINT_TRACKER.md`'s Gate D record): a spy that counts calls
to `compute_recourse`, not just an assertion on `build_recourse`'s return value, is the only way
to actually distinguish "never computed" from "computed and silently thrown away".

Complements (never duplicates) `tests/orchestrators/test_build_recourse.py`, which already pins
the return-value contract on the same fixtures.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.inputs.inputs import load_inputs
from src.orchestrators import crew as crew_mod
from src.orchestrators.crew import build_recourse
from tests.utils import make_financial_inputs

_DEMO_DEAL_PATH = "data/sample_listings/36_kelly_moncton/inputs.json"


def _good_buy_inputs():
    good = make_financial_inputs(num_units=6)
    return good.model_copy(
        update={
            "financing": good.financing.model_copy(update={"purchase_price": 380_000.0, "down_payment_rate": 0.30}),
            "income": good.income.model_copy(update={"occupancy": 0.97, "bad_debt_factor": 0.98}),
        }
    )


def _conditional_near_miss_inputs():
    conditional = make_financial_inputs(num_units=4)
    return conditional.model_copy(
        update={
            "financing": conditional.financing.model_copy(
                update={"purchase_price": 540_000.0, "down_payment_rate": 0.20, "interest_rate": 0.058}
            ),
        }
    )


def test_compute_recourse_is_never_called_for_a_buy(monkeypatch: pytest.MonkeyPatch):
    spy = MagicMock(wraps=crew_mod.compute_recourse)
    monkeypatch.setattr(crew_mod, "compute_recourse", spy)

    result = build_recourse(_good_buy_inputs(), horizon_years=10)

    assert result is None
    spy.assert_not_called()


def test_compute_recourse_is_never_called_for_a_deep_decline_beyond_the_fail_bound(monkeypatch: pytest.MonkeyPatch):
    """The committed sample deal: 4 fails > GENUINELY_CLOSE_MAX_FAILS (3). The gate must close
    BEFORE any recourse computation is attempted -- not compute it and discard the result."""
    spy = MagicMock(wraps=crew_mod.compute_recourse)
    monkeypatch.setattr(crew_mod, "compute_recourse", spy)

    inputs = load_inputs(_DEMO_DEAL_PATH).inputs
    result = build_recourse(inputs, horizon_years=10)

    assert result is None
    spy.assert_not_called()


def test_compute_recourse_is_called_exactly_once_for_a_genuine_near_miss(monkeypatch: pytest.MonkeyPatch):
    spy = MagicMock(wraps=crew_mod.compute_recourse)
    monkeypatch.setattr(crew_mod, "compute_recourse", spy)

    result = build_recourse(_conditional_near_miss_inputs(), horizon_years=10)

    assert result is not None
    spy.assert_called_once()


def test_would_go_red_against_the_vetoed_compute_then_discard_shape(monkeypatch: pytest.MonkeyPatch):
    """Demonstrates the exact anti-pattern Gate D vetoed: a `build_recourse` stand-in that always
    computes, then discards the result when the gate says no, instead of never computing at all.
    The spy-based assertion above would fail against this shape (the whole reason a spy, not just
    a return-value check, is needed)."""
    spy = MagicMock(wraps=crew_mod.compute_recourse)
    monkeypatch.setattr(crew_mod, "compute_recourse", spy)

    def vetoed_build_recourse(inputs, *, horizon_years):
        # THE VETOED SHAPE: compute unconditionally, THEN gate on whether to keep it.
        analysis = crew_mod.compute_recourse(inputs, horizon_years=horizon_years)
        if not crew_mod.is_genuinely_close(inputs, horizon_years=horizon_years):
            return None
        return analysis

    result = vetoed_build_recourse(_good_buy_inputs(), horizon_years=10)

    assert result is None  # the return-value contract alone still looks satisfied...
    with pytest.raises(AssertionError):
        spy.assert_not_called()  # ...but the vetoed shape computed it anyway.
