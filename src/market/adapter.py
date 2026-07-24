# src/market/adapter.py
"""Delta -> FinancialInputs perturbation adapter (Mission 1, Wave 2).

Produces a perturbed **deep copy** of ``FinancialInputs`` from a ``MarketHypothesis``
plus a precomputed ``base_cap``. The original inputs are never mutated, so the frozen
finance engine can be re-run on the copy without side effects.

Mapping (design note §1/§1b/§2/§3; deltas and fields are all fractions [0-1], no unit
conversion anywhere except the single vacancy sign flip):

- ``income.rent_growth      += rent_delta``
- ``opex.expense_growth     += expense_growth_delta``
- ``financing.interest_rate  = clamp(rate + interest_rate_delta, 0.0, 1.0)``
- ``income.occupancy         = clamp(occupancy - vacancy_delta, 0.0, 1.0)``  (SIGN FLIP:
  occupancy = 1 - vacancy, so a positive vacancy_delta lowers occupancy)
- ``market.cap_rate_purchase = clamp(base_cap + cap_rate_delta, floor=0.03)``

``str_viability`` has no clean engine target and is intentionally NOT applied here; it is
carried on the hypothesis for downstream narration only.
"""

from __future__ import annotations

from src.schemas.models import FinancialInputs, MarketHypothesis

# Concrete cap-rate floor (matches the rejector lower bound, design note §1b). A cap at or
# near 0 would make est_value = NOI / cap explode in the engine, so this is the honest guard.
CAP_RATE_FLOOR = 0.03


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def perturb_inputs(fi: FinancialInputs, hypothesis: MarketHypothesis, *, base_cap: float) -> FinancialInputs:
    """Return a perturbed deep copy of ``fi`` for the given ``hypothesis``.

    ``base_cap`` is the engine-derived purchase cap from the untouched inputs
    (``market.cap_rate_purchase`` if set, else ``NOI_Y1 / purchase_price``); the runner
    reads it once off a baseline ``run_financial_model`` call. The delta is added to that
    anchor and floored at ``CAP_RATE_FLOOR`` (design note §1b).

    The original ``fi`` (and every nested submodel) is left untouched.
    """
    base = fi.model_copy(deep=True)

    new_income = base.income.model_copy(
        update={
            "rent_growth": base.income.rent_growth + hypothesis.rent_delta,
            "occupancy": _clamp(base.income.occupancy - hypothesis.vacancy_delta, 0.0, 1.0),
        }
    )
    new_opex = base.opex.model_copy(update={"expense_growth": base.opex.expense_growth + hypothesis.expense_growth_delta})
    new_financing = base.financing.model_copy(
        update={"interest_rate": _clamp(base.financing.interest_rate + hypothesis.interest_rate_delta, 0.0, 1.0)}
    )
    new_cap = max(CAP_RATE_FLOOR, base_cap + hypothesis.cap_rate_delta)
    new_market = base.market.model_copy(update={"cap_rate_purchase": new_cap})

    return base.model_copy(
        update={
            "income": new_income,
            "opex": new_opex,
            "financing": new_financing,
            "market": new_market,
        }
    )
