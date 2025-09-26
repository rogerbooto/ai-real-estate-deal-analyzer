# tests/unit/test_market_hypotheses.py
from dataclasses import FrozenInstanceError

import pytest

from src.schemas.models import HypothesisSet
from tests.utils import make_hypothesis, make_hypothesis_set


def test_market_hypothesis_summary_triangles_and_percentages():
    h = make_hypothesis(
        rent_delta=0.02,
        expense_growth_delta=-0.005,
        interest_rate_delta=0.0,
        cap_rate_delta=0.001,
        vacancy_delta=0.0,
        str_viability=True,
        prior=0.1234,
    )
    s = h.summary()
    assert "Rent: ▲ 2.00%" in s
    assert "Opex: ▼ 0.50%" in s
    assert "Rate: ➝ 0.00%" in s
    assert "Cap: ▲ 0.10%" in s
    assert "Vac: ➝ 0.00%" in s
    assert "prior=12.34%" in s
    assert "STR=Y" in s


def test_market_hypothesis_as_dict_and_immutability():
    h = make_hypothesis(
        rent_delta=0.01,
        expense_growth_delta=0.0,
        interest_rate_delta=0.0,
        cap_rate_delta=0.0,
        vacancy_delta=0.0,
        str_viability=False,
        prior=0.5,
    )
    d = h.as_dict()
    assert d["prior"] == 0.5 and d["str_viability"] is False

    with pytest.raises(FrozenInstanceError):
        h.prior = 0.6


def test_hypothesis_set_prob_sum_and_repr():
    hs = make_hypothesis_set(n=3)
    assert isinstance(hs, HypothesisSet)
    r = repr(hs)
    assert "HypothesisSet" in r and "items=" in r
