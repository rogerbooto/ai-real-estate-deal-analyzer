# tests/core/finance/test_cap_rate_floor_warning.py
"""
Engine contract for the cap-rate-floor guardrail (Mission 2 / F1).

`MarketAssumptions.cap_rate_floor` is an underwriting policy floor: the purchase
cap rate (NOI_Y1 / purchase price, or the explicit `cap_rate_purchase` override)
must be at least the floor. `run_financial_model` emits the warning
"cap rate below floor" when it is strictly below; `src/agents/chief_strategist.py`
matches that warning on the tokens "cap rate" + "below floor".

These tests pin the three arms of the policy (breach / at-or-above / no floor) and
the exact warning token the consumer greps for. They turn RED if the engine stops
emitting the warning, changes its wording so the consumer no longer matches, or
starts firing on a `None` floor.
"""

from __future__ import annotations

import pytest

from src.core.finance import run_financial_model
from src.schemas.models import FinancialInputs
from tests.utils import make_financial_inputs, make_market_assumptions

CAP_FLOOR_WARNING = "cap rate below floor"


def _inputs_with(*, cap_rate_purchase: float | None, cap_rate_floor: float | None) -> FinancialInputs:
    """Deterministic inputs with a pinned purchase cap and floor policy."""
    fin = make_financial_inputs(do_refi=False, num_units=4)
    return fin.model_copy(
        update={
            "market": make_market_assumptions(
                cap_rate_purchase=cap_rate_purchase,
                cap_rate_floor=cap_rate_floor,
            )
        }
    )


def test_purchase_cap_below_floor_emits_warning():
    """4.00% purchase cap against a 5.00% floor is a breach."""
    out = run_financial_model(_inputs_with(cap_rate_purchase=0.04, cap_rate_floor=0.05))

    assert out.purchase.cap_rate == pytest.approx(0.04)
    assert CAP_FLOOR_WARNING in out.warnings
    # The consumer (chief_strategist) greps for these two lowercase tokens.
    matched = [w for w in out.warnings if "cap rate" in w.lower() and "below floor" in w.lower()]
    assert matched == [CAP_FLOOR_WARNING]


@pytest.mark.parametrize(
    ("cap_rate_purchase", "cap_rate_floor", "case"),
    [
        (0.05, 0.05, "exactly at the floor is NOT a breach (strict <)"),
        (0.06, 0.05, "above the floor is not a breach"),
        (0.04, None, "no floor policy configured -> never a breach"),
        (0.00, None, "no floor policy configured, even at a zero cap"),
    ],
)
def test_no_warning_when_floor_is_respected_or_unset(cap_rate_purchase: float, cap_rate_floor: float | None, case: str):
    out = run_financial_model(_inputs_with(cap_rate_purchase=cap_rate_purchase, cap_rate_floor=cap_rate_floor))

    assert CAP_FLOOR_WARNING not in out.warnings, case
    assert not any("below floor" in w.lower() for w in out.warnings), case


def test_computed_purchase_cap_breaches_floor_without_explicit_override():
    """
    The guardrail reads the *effective* purchase cap, so it also fires when the cap
    is derived from NOI_Y1 / purchase price rather than pinned via `cap_rate_purchase`.
    """
    fin = _inputs_with(cap_rate_purchase=None, cap_rate_floor=0.99)
    out = run_financial_model(fin)

    assert out.purchase.cap_rate < 0.99
    assert CAP_FLOOR_WARNING in out.warnings


def test_existing_warnings_are_untouched_and_ordering_is_deterministic():
    """
    The hyphenated "cap-rate spread below target" must keep its wording (it must NOT
    match the consumer's "cap rate"/"below floor" grep) and its leading position; the
    floor warning is appended last.
    """
    fin = _inputs_with(cap_rate_purchase=0.04, cap_rate_floor=0.05)
    first = run_financial_model(fin)
    second = run_financial_model(fin)

    assert first.warnings == second.warnings  # same input -> same output
    assert first.warnings[0] == "cap-rate spread below target"
    assert first.warnings[-1] == CAP_FLOOR_WARNING
    assert not ("cap rate" in first.warnings[0].lower() and "below floor" in first.warnings[0].lower())
