# tests/unit/test_scenario_adapter.py

from __future__ import annotations

import pytest

from src.core.finance import run_financial_model
from src.market.adapter import CAP_RATE_FLOOR, perturb_inputs
from tests.utils import make_financial_inputs, make_hypothesis


def _zero_hypothesis(**overrides: float | bool) -> object:
    """A hypothesis with all deltas zeroed unless overridden."""
    base: dict[str, float | bool] = {
        "rent_delta": 0.0,
        "expense_growth_delta": 0.0,
        "interest_rate_delta": 0.0,
        "cap_rate_delta": 0.0,
        "vacancy_delta": 0.0,
        "str_viability": False,
    }
    base.update(overrides)
    return make_hypothesis(**base)  # type: ignore[arg-type]


def test_vacancy_sign_flip_golden() -> None:
    # occupancy 0.95, vacancy_delta +0.02 -> occupancy 0.93 (design note §2 golden).
    fi = make_financial_inputs()
    assert fi.income.occupancy == pytest.approx(0.95)

    hyp = _zero_hypothesis(vacancy_delta=0.02)
    perturbed = perturb_inputs(fi, hyp, base_cap=0.06)  # type: ignore[arg-type]

    assert perturbed.income.occupancy == pytest.approx(0.93, abs=1e-12)
    # original untouched
    assert fi.income.occupancy == pytest.approx(0.95)


def test_vacancy_reduces_noi_vs_baseline() -> None:
    fi = make_financial_inputs()
    baseline = run_financial_model(fi)
    base_cap = baseline.purchase.cap_rate

    hyp = _zero_hypothesis(vacancy_delta=0.02)
    perturbed = perturb_inputs(fi, hyp, base_cap=base_cap)  # type: ignore[arg-type]
    shocked = run_financial_model(perturbed)

    assert shocked.years[0].noi < baseline.years[0].noi


def test_cap_anchoring_delta_zero_reproduces_headline() -> None:
    # cap_rate_delta = 0 with all other deltas 0 => applied cap == baseline PurchaseMetrics.cap_rate,
    # and Year-1 est_value == purchase_price (design note §1b).
    fi = make_financial_inputs()
    baseline = run_financial_model(fi)
    base_cap = baseline.purchase.cap_rate
    assert base_cap > CAP_RATE_FLOOR  # sanity: floor not biting

    hyp = _zero_hypothesis()
    perturbed = perturb_inputs(fi, hyp, base_cap=base_cap)  # type: ignore[arg-type]

    assert perturbed.market.cap_rate_purchase == base_cap  # exact anchor

    shocked = run_financial_model(perturbed)
    assert shocked.years[0].est_value == pytest.approx(fi.financing.purchase_price, rel=1e-9)


def test_interest_rate_additive() -> None:
    fi = make_financial_inputs()
    hyp = _zero_hypothesis(interest_rate_delta=0.01)
    perturbed = perturb_inputs(fi, hyp, base_cap=0.06)  # type: ignore[arg-type]

    assert perturbed.financing.interest_rate == pytest.approx(fi.financing.interest_rate + 0.01, abs=1e-12)


def test_rent_growth_additive() -> None:
    fi = make_financial_inputs()
    hyp = _zero_hypothesis(rent_delta=0.02)
    perturbed = perturb_inputs(fi, hyp, base_cap=0.06)  # type: ignore[arg-type]

    assert perturbed.income.rent_growth == pytest.approx(fi.income.rent_growth + 0.02, abs=1e-12)


def test_expense_growth_additive() -> None:
    fi = make_financial_inputs()
    hyp = _zero_hypothesis(expense_growth_delta=0.015)
    perturbed = perturb_inputs(fi, hyp, base_cap=0.06)  # type: ignore[arg-type]

    assert perturbed.opex.expense_growth == pytest.approx(fi.opex.expense_growth + 0.015, abs=1e-12)


def test_cap_floor_clamp() -> None:
    # base_cap 0.05, cap_rate_delta -0.10 -> -0.05 -> clamp up to floor 0.03.
    fi = make_financial_inputs()
    hyp = _zero_hypothesis(cap_rate_delta=-0.10)
    perturbed = perturb_inputs(fi, hyp, base_cap=0.05)  # type: ignore[arg-type]

    assert perturbed.market.cap_rate_purchase == pytest.approx(CAP_RATE_FLOOR, abs=1e-12)


def test_original_inputs_never_mutated() -> None:
    fi = make_financial_inputs()
    snapshot_rate = fi.financing.interest_rate
    snapshot_occ = fi.income.occupancy
    snapshot_rent = fi.income.rent_growth
    snapshot_exp = fi.opex.expense_growth
    snapshot_cap = fi.market.cap_rate_purchase

    hyp = make_hypothesis(
        rent_delta=0.02,
        expense_growth_delta=0.01,
        interest_rate_delta=0.01,
        cap_rate_delta=0.005,
        vacancy_delta=0.02,
    )
    _ = perturb_inputs(fi, hyp, base_cap=0.06)

    assert fi.financing.interest_rate == snapshot_rate
    assert fi.income.occupancy == snapshot_occ
    assert fi.income.rent_growth == snapshot_rent
    assert fi.opex.expense_growth == snapshot_exp
    assert fi.market.cap_rate_purchase == snapshot_cap
