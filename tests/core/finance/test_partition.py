# tests/core/finance/test_partition.py
"""
GD3 -- THE LEVER/ASSUMPTION PARTITION (Mission 5, principles-guardian ruling
`docs/plans/mission-5-discovery/GD3_lever_assumption_invariant.md`). Prove-the-test suite: every
test here is RED under the one-line edit it guards (see the docstring on each test for the
captured failure this was verified against).

Covers C1 (partition + drift guards), C3(a)/(b)/(c) (RED tests naming the invariant), C5 (barred
axes recorded and enforced), and the breakeven-shape rule (Ruling 2.4).
"""

from __future__ import annotations

import re
from typing import Any

import pytest
from pydantic import BaseModel

from src.core.finance import jacobian, partition
from src.market.recourse import LeverName
from src.schemas.models import RecourseLever

# ------------------------------------------------------------------------------------------
# C1 -- partition source of truth: shape and content of the two sets.
# ------------------------------------------------------------------------------------------


def test_investor_levers_is_the_closed_four() -> None:
    assert partition.INVESTOR_LEVERS == ("rent_per_unit_month", "purchase_price", "interest_rate", "annual_opex")


def test_model_assumptions_covers_the_guardian_named_minimum() -> None:
    """C1: MODEL_ASSUMPTIONS must cover, at minimum, the guardian's named field paths."""
    required = {
        "income.occupancy",
        "income.bad_debt_factor",
        "income.rent_growth",
        "opex.expense_growth",
        "market.cap_rate_drift",
        "refi.exit_cap_rate",
        "horizon_years",
        "MarketSnapshot.vacancy_rate",
        "MarketSnapshot.rent_growth",
        "MarketSnapshot.expense_growth",
    }
    assert required <= partition.MODEL_ASSUMPTIONS


def test_investor_levers_and_model_assumptions_are_disjoint() -> None:
    assert set(partition.INVESTOR_LEVERS).isdisjoint(partition.MODEL_ASSUMPTIONS)
    assert partition.LEVER_IMAGE.isdisjoint(partition.MODEL_ASSUMPTIONS)


def test_lever_seed_targets_correspondence_is_the_full_lever_image() -> None:
    """The lever -> seed-target correspondence table's union IS partition.LEVER_IMAGE."""
    image = frozenset(t for targets in partition.LEVER_SEED_TARGETS.values() for t in targets)
    assert image == partition.LEVER_IMAGE
    assert frozenset(partition.LEVER_SEED_TARGETS) == frozenset(partition.INVESTOR_LEVERS)


def test_annual_opex_lever_image_is_all_twelve_dollar_lines() -> None:
    opex_image = partition.LEVER_SEED_TARGETS["annual_opex"]
    assert len(opex_image) == 12
    assert all(t.startswith("opex.") for t in opex_image)
    assert "opex.expense_growth" not in opex_image  # a rate, not a lever-perturbable dollar line


# ------------------------------------------------------------------------------------------
# C1 / Ruling 2.2 -- import-time drift guard: jacobian.SeedTarget vs partition.LEVER_IMAGE.
#
# Captured RED (verified this session by literally breaking the invariant and re-importing a
# fresh interpreter -- see the module import-time guard added at jacobian.py, immediately after
# `_SCALAR_TARGETS`):
#
#   $ python -c "
#   import src.core.finance.jacobian as j
#   j._SEED_TARGET_UNIVERSE = j._SEED_TARGET_UNIVERSE | {'income.occupancy'}
#   j.assert_disjoint_from_assumptions({'jacobian._SEED_TARGET_UNIVERSE': j._SEED_TARGET_UNIVERSE})
#   "
#   RuntimeError: GD3 VIOLATION: jacobian._SEED_TARGET_UNIVERSE contains ['income.occupancy'], ...
#   FOUNDER PROXY ESCALATION CITING GD3 -- a rationale string is not a clearance.
# ------------------------------------------------------------------------------------------


def test_seed_target_universe_matches_lever_image_exactly() -> None:
    """RED on revert: if jacobian.py's SeedTarget universe drifts from partition.LEVER_IMAGE,
    this fails -- and, independently, the import-time guard in jacobian.py would already have
    raised RuntimeError before this test body ever ran."""
    assert jacobian._SEED_TARGET_UNIVERSE == partition.LEVER_IMAGE


def test_widening_seed_target_universe_with_an_assumption_is_rejected_at_the_guard() -> None:
    """C3(a)-adjacent: simulate the exact one-line edit the guardian named ('add
    income.occupancy as a seed target') and prove the disjointness guard -- the mechanism
    jacobian.py itself calls at import time -- rejects it loudly, naming Founder Proxy + GD3."""
    widened = jacobian._SEED_TARGET_UNIVERSE | {"income.occupancy"}
    with pytest.raises(RuntimeError, match=r"FOUNDER PROXY ESCALATION CITING GD3"):
        partition.assert_disjoint_from_assumptions({"jacobian._SEED_TARGET_UNIVERSE (widened)": widened})


# ------------------------------------------------------------------------------------------
# C3(a) -- seeding a MODEL_ASSUMPTIONS path as a TangentDirection target raises ValueError.
# ------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "assumption_path",
    sorted(partition.MODEL_ASSUMPTIONS - {"horizon_years"}),  # horizon_years is not seedable shape at all (not even a float target)
)
def test_seeding_a_model_assumption_path_raises(assumption_path: str) -> None:
    """C3(a): every MODEL_ASSUMPTIONS field path is REJECTED by the engine's own seed-target
    validation -- it is not a member of `jacobian.SeedTarget`'s universe, so `_validated_directions`
    raises `ValueError` (the existing runtime guard, now enforcement of GD3, per Ruling 2's last
    paragraph). Captured RED (this exact call, this session):

        _validated_directions([TangentDirection("bad", (("income.occupancy", 1.0),))])
        -> ValueError: direction 'bad' has unknown seed target 'income.occupancy'; scalar
           targets are ['financing.interest_rate', 'financing.purchase_price', 'income.gsi_annual']
    """
    direction = jacobian.TangentDirection("bad", ((assumption_path, 1.0),))
    with pytest.raises(ValueError, match=re.escape(assumption_path)):
        jacobian._validated_directions([direction])


# ------------------------------------------------------------------------------------------
# C3(b) -- the disjointness assertion (Ruling 2.3) exists and its failure message names the
# Founder Proxy escalation and cites GD3.
# ------------------------------------------------------------------------------------------


def test_disjointness_assertion_names_founder_proxy_and_gd3() -> None:
    with pytest.raises(RuntimeError) as exc_info:
        partition.assert_disjoint_from_assumptions({"fake_investor_lever_set": ("income.occupancy",)})
    message = str(exc_info.value)
    assert "FOUNDER PROXY ESCALATION" in message
    assert "GD3" in message
    assert "income.occupancy" in message


def test_disjointness_assertion_is_a_noop_on_a_clean_state() -> None:
    """No exception when the caller-supplied surfaces are genuinely lever-only."""
    partition.assert_disjoint_from_assumptions({"clean_surface": partition.LEVER_IMAGE})


# ------------------------------------------------------------------------------------------
# C3(c) -- RecourseLever.lever's Literal args == INVESTOR_LEVERS, and (substitute enforcement
# for the market-layer half of C1, which this session's ownership boundary keeps out of
# `src/market/recourse.py` -- see the handoff report) LeverName's args == INVESTOR_LEVERS too.
# ------------------------------------------------------------------------------------------


def test_recourse_lever_literal_matches_investor_levers() -> None:
    from typing import get_args as _get_args

    annotation = RecourseLever.model_fields["lever"].annotation
    assert _get_args(annotation) == partition.INVESTOR_LEVERS


def test_recourse_lever_name_literal_matches_investor_levers() -> None:
    """Pin for `src.market.recourse.LeverName` -- the market-layer half of C1's mirrored pair.
    RED on revert: if `LeverName` gains/loses a member without updating
    `partition.INVESTOR_LEVERS` (or vice versa), this fails."""
    from typing import get_args as _get_args

    assert _get_args(LeverName) == partition.INVESTOR_LEVERS


def test_combination_lever_move_literal_matches_investor_levers() -> None:
    """C6, at the schema boundary: `CombinationLeverMove.lever` (Mission 5 Half B, landed in
    `src/schemas/models.py` concurrently with this work) is the multi-lever combination
    optimizer's own per-move lever field -- it must stay closed to exactly `INVESTOR_LEVERS`,
    the same pin `RecourseLever.lever` gets above. If this schema class does not exist yet in a
    given checkout, the test is skipped rather than failed (the Half-B schema is Mission 5 WIP,
    landed by a concurrent work item, not by this session)."""
    from typing import get_args as _get_args

    try:
        from src.schemas.models import CombinationLeverMove
    except ImportError:
        pytest.skip("CombinationLeverMove not yet defined in this checkout")
    annotation = CombinationLeverMove.model_fields["lever"].annotation
    assert _get_args(annotation) == partition.INVESTOR_LEVERS


# ------------------------------------------------------------------------------------------
# C5 -- barred axes (Ruling 3): recorded, and no seed target / _CoreOverrides field / breakeven
# surface exists for them.
# ------------------------------------------------------------------------------------------


def test_barred_axes_are_recorded() -> None:
    assert partition.BARRED_ASSUMPTION_AXES == {"market.cap_rate_drift", "refi.exit_cap_rate", "horizon_years"}
    assert partition.BARRED_ASSUMPTION_AXES <= partition.MODEL_ASSUMPTIONS


def test_no_seed_target_exists_for_any_barred_axis() -> None:
    assert partition.BARRED_ASSUMPTION_AXES.isdisjoint(partition.LEVER_IMAGE)
    assert partition.BARRED_ASSUMPTION_AXES.isdisjoint(jacobian._SEED_TARGET_UNIVERSE)


def test_no_core_overrides_field_exists_for_any_barred_axis() -> None:
    from dataclasses import fields as _dataclass_fields

    from src.core.finance.engine import _CoreOverrides

    override_fields = {f.name for f in _dataclass_fields(_CoreOverrides)}
    assert partition.BARRED_ASSUMPTION_AXES.isdisjoint(override_fields)


def test_no_breakeven_surface_exists_for_any_barred_axis() -> None:
    """Ruling 3: barred axes may not carry ANY breakeven surface until the terminal-model
    prerequisite chain is complete. An earlier form of this test pinned the total ABSENCE of a
    breakeven surface "so a future addition is a deliberate, reviewed act" -- that act happened
    (the Mission 5 breakeven analysis, guardian-cleared under Rulings 1/2.4, shipped
    `AssumptionBreakeven`/`BreakevenAnalysis` via `src/market/breakeven.py`), so this test now
    pins the stronger, still-true property: the ONLY breakeven surface is the sanctioned pair,
    both obey the shape rule, and NO barred axis (exit cap, cap drift, horizon) is expressible
    on it -- the closed `assumption` Literal carries the three permitted axes and nothing else."""
    from typing import get_args

    import src.schemas.models as models_module
    from src.schemas.models import AssumptionBreakeven, BreakevenAnalysis

    breakeven_like_names = {name for name in dir(models_module) if "breakeven" in name.lower()}
    assert breakeven_like_names == {"AssumptionBreakeven", "BreakevenAnalysis"}
    partition.assert_breakeven_shape(AssumptionBreakeven)
    partition.assert_breakeven_shape(BreakevenAnalysis)
    axes = get_args(AssumptionBreakeven.model_fields["assumption"].annotation)
    assert axes == ("occupancy", "rent_growth", "expense_growth")
    axis_paths = {"occupancy": "income.occupancy", "rent_growth": "income.rent_growth", "expense_growth": "opex.expense_growth"}
    assert partition.BARRED_ASSUMPTION_AXES.isdisjoint(axis_paths[a] for a in axes)


# ------------------------------------------------------------------------------------------
# Ruling 2.4 -- the breakeven shape rule: rejects a type carrying an ask/delta/target field.
# ------------------------------------------------------------------------------------------


def test_breakeven_shape_rejects_target_value_field() -> None:
    class _BadBreakeven(BaseModel):
        guardrail: str
        assumption_path: str
        target_value: float

    with pytest.raises(RuntimeError, match=r"FOUNDER PROXY ESCALATION CITING GD3"):
        partition.assert_breakeven_shape(_BadBreakeven)


def test_breakeven_shape_rejects_delta_field() -> None:
    class _BadBreakeven(BaseModel):
        guardrail: str
        delta: float

    with pytest.raises(RuntimeError, match=r"delta"):
        partition.assert_breakeven_shape(_BadBreakeven)


def test_breakeven_shape_rejects_ask_field() -> None:
    class _BadBreakeven(BaseModel):
        guardrail: str
        recommended_ask: float

    with pytest.raises(RuntimeError, match=r"recommended_ask"):
        partition.assert_breakeven_shape(_BadBreakeven)


def test_breakeven_shape_accepts_the_honest_reading() -> None:
    class _GoodBreakeven(BaseModel):
        guardrail: str
        assumption_path: str
        assumed_value: float
        breakeven_value: float
        margin: float
        direction_of_failure: str

    partition.assert_breakeven_shape(_GoodBreakeven)  # must not raise


def test_breakeven_shape_rejects_non_model() -> None:
    with pytest.raises(TypeError):
        partition.assert_breakeven_shape(int)  # type: ignore[arg-type]


# ------------------------------------------------------------------------------------------
# C6 (partial -- see handoff report: no Half-B combination-search code exists in this
# codebase yet, D4_halfb_design.md §0 is design-only). Pins the mechanism the guardian's
# Ruling 4 mandates any future combination search MUST use to build its candidate space.
# ------------------------------------------------------------------------------------------


def test_investor_lever_combinations_enumerates_only_investor_levers() -> None:
    combos = partition.investor_lever_combinations()
    flat = {lever for combo in combos for lever in combo}
    assert flat <= set(partition.INVESTOR_LEVERS)
    assert flat.isdisjoint(partition.MODEL_ASSUMPTIONS)
    # every non-empty subset of 4 levers = 2**4 - 1 = 15
    assert len(combos) == 15


def test_investor_lever_combinations_is_red_if_an_assumption_axis_is_injected() -> None:
    """C6's RED proof: simulate the future combination search drawing from a POISONED lever
    tuple (an assumption injected into INVESTOR_LEVERS, the only way Ruling 4 permits a search
    space to be built) and confirm the resulting candidate space would carry the assumption --
    demonstrating why INVESTOR_LEVERS itself, not the combination code, is the enforcement
    point, and why extending it is a Founder Proxy escalation (see test_disjointness_assertion_*
    above for the guard that fires on exactly this poisoning)."""
    poisoned_levers: tuple[Any, ...] = (*partition.INVESTOR_LEVERS, "income.occupancy")
    from itertools import combinations

    poisoned_combos = [c for size in range(1, len(poisoned_levers) + 1) for c in combinations(poisoned_levers, size)]
    flat = {lever for combo in poisoned_combos for lever in combo}
    assert not flat.isdisjoint(partition.MODEL_ASSUMPTIONS)  # the poisoning is present...
    with pytest.raises(RuntimeError, match=r"FOUNDER PROXY ESCALATION CITING GD3"):
        # ...and is exactly what the guard this session added would reject at import time.
        partition.assert_disjoint_from_assumptions({"poisoned INVESTOR_LEVERS": poisoned_levers})
