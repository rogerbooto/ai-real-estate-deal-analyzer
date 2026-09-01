# tests/core/finance/test_golden_tolerance_walls.py
"""
GD.1 condition C6 -- "Walls re-derived in-repo": this file re-derives, in the suite, the two
measured numbers `REL_TOL = 1e-9` (`tests/core/finance/golden_tolerance.py`) rests on, so a future
change to the engine that moves either wall turns the tolerance's justification RED rather than
leaving it stale prose (D.3 section 6.3, item 8: "widening 1e-9 requires redoing the two
measurements, in the repo, in a test").

  - THE FLOOR: the largest relative deviation a *legitimate* floating-point reassociation can
    produce, measured by injecting a single ULP into `amortization.amortization_payment` (the
    most-amplified intermediate in the engine, per D.3 section 1.4) and propagating it through
    `run_financial_model` across the full 34-case golden matrix. Design measured 1.151e-13; the
    guardian independently reproduced 1.1510e-13. This is the class AD's dual-number threading
    belongs to: reordered, not different, arithmetic.
  - THE CEILING: the smallest defect class the harness is contractually required to catch --
    `round(payment, 4)`, an entirely ordinary "someone rounded a money figure" bug. Design measured
    1.133e-7 (1,613 of 11,789 fields moved past 1e-9); the guardian independently reproduced
    1.1325e-7, 1,613 fields.

THE EXECUTABLE C6 DOLLAR-BLINDNESS BOUNDARY -- PD.1's ratification is conditional on this staying
true: `REL_TOL * max(|shipped-deal golden field|) < 0.005` (half a display cent). If this product
ever underwrites at a scale where this assertion goes RED, the tolerance comes back to the founder;
it does not get widened by whoever is on shift (PD.1, "(a) Tolerance value").

SCOPE NOTE (division of labour with IT.2): this file re-derives the two WALLS and the dollar
boundary only. It does not implement the acceptance-criterion calibration recipes (the ~9.4e-8
contract figure catching the defect class end-to-end, the AD-scale-drift-must-pass case, or the
anchor-cannot-be-silently-moved case) -- those are THIS file (the calibration walls) and
`tests/core/finance/test_golden_anchor.py`,
owned by IT.2, per D.3 section 7's implementation table.

WHY THIS PASSES CLEANLY ON THE MISSION'S OWN ORCHESTRATOR FINDING: the mission will shortly land an
aggregate-shift seam (`gsi = gsi_base + 12*n*t` in closed form, replacing a rebuilt rent roll) that
is mathematically exact but not bit-exact -- summation order differs. Its measured worst-case
relative drift (3.893e-15 at 500 units, 3.456e-14 at 5,000 units) is itself a *legitimate floating-
point-reassociation* class, the same class the floor test below re-derives generically via the
1-ULP injection. `compare_golden` is agnostic to WHICH code path produced a deviation -- it only
measures magnitude -- so this file does not need a seam-specific test to accommodate that finding;
the floor test already covers the class. (The seam itself does not exist in this codebase as of
this task -- IT.1 is test-harness-only and does not touch `src/`.)
"""

from __future__ import annotations

import json
import math
from typing import Any
from unittest import mock

import pytest

import src.core.finance.amortization as amortization
from src.core.finance import run_financial_model
from src.schemas.models import FinancialInputs, ListingInsights
from tests.core.finance.golden_cases import CASES
from tests.core.finance.golden_tolerance import APPROACHING_LO, DOLLAR_BLINDNESS_BUDGET, GOLDEN_PATH, REL_TOL, compare_golden

_CASES_BY_ID: dict[str, dict[str, Any]] = {c["id"]: c for c in CASES}


@pytest.fixture(scope="module")
def golden() -> dict[str, Any]:
    with GOLDEN_PATH.open("r", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return data


# The floor and ceiling this repo has actually measured (D.3 section 1.3, reproduced by GD.1,
# reproduced again here). These are NOT asserted to microsecond-precision -- floating-point
# reordering noise is platform/BLAS/allocator sensitive at the last couple of significant digits --
# but the ORDER OF MAGNITUDE and the ordering FLOOR << REL_TOL << CEILING is exactly what the
# tolerance's justification depends on, and that is what is pinned here.
_FLOOR_UPPER_BOUND = 1e-11  # 1-ULP-induced max relative deviation must stay far below this
_CEILING_LOWER_BOUND = 1e-7  # round(payment, 4) must produce a max relative deviation at least this large


def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    fi = FinancialInputs.model_validate(case["financial_inputs"])
    insights = ListingInsights.model_validate(case["insights"]) if case.get("insights") else None
    forecast = run_financial_model(fi, horizon_years=case["horizon_years"], insights=insights)
    return forecast.model_dump(mode="json")


def _max_rel_drift_and_exceed_counts(patched_payment: Any, golden_cases: dict[str, Any]) -> tuple[float, int, int]:
    """
    Run every golden case with `amortization.amortization_payment` monkeypatched to
    `patched_payment`, compare each to the anchored golden, and return
    (max relative drift observed, fields exceeding REL_TOL, fields that would exceed a 1e-6 rule).
    """
    max_rel = 0.0
    exceeds_1e9 = 0
    exceeds_1e6 = 0
    with mock.patch.object(amortization, "amortization_payment", side_effect=patched_payment):
        for case_id, case in _CASES_BY_ID.items():
            actual = _run_case(case)
            expected = golden_cases[case_id]["forecast"]
            report = compare_golden(case_id, actual, expected)
            for rel in report.float_rel_drift.values():
                if rel > max_rel:
                    max_rel = rel
                if rel >= REL_TOL:
                    exceeds_1e9 += 1
                if rel >= 1e-6:
                    exceeds_1e6 += 1
    return max_rel, exceeds_1e9, exceeds_1e6


def test_floor_one_ulp_reordering_noise_stays_far_below_rel_tol(golden: dict[str, Any]) -> None:
    """
    THE FLOOR (D.3 section 1.3): a single ULP injected into the most-amplified intermediate
    (`amortization_payment`) is the largest deviation a *legitimate* floating-point reassociation
    can produce end-to-end through `run_financial_model`. This is exactly AD's dual-number-
    threading class. It must land far below `REL_TOL`, and specifically below `APPROACHING_LO`, so
    AD landings pass cleanly and never even enter the approaching-tolerance band.
    """
    original = amortization.amortization_payment

    def one_ulp(principal: float, rate: float, years: int) -> float:
        return math.nextafter(original(principal, rate, years), math.inf)

    max_rel, exceeds_1e9, _ = _max_rel_drift_and_exceed_counts(one_ulp, golden["cases"])

    assert 0.0 < max_rel < _FLOOR_UPPER_BOUND, f"1-ULP floor moved: max_rel={max_rel:.4e}, expected in (0, {_FLOOR_UPPER_BOUND:.0e})"
    assert (
        max_rel < APPROACHING_LO
    ), "the reordering floor must sit below the approaching-tolerance band, or AD's own arithmetic would trip a FAIL"
    assert exceeds_1e9 == 0, "a legitimate 1-ULP reassociation must never exceed REL_TOL"


def test_ceiling_round_payment_4_defect_class_exceeds_rel_tol_by_orders_of_magnitude(golden: dict[str, Any]) -> None:
    """
    THE CEILING (D.3 section 5.2): `round(payment, 4)` is an ordinary "someone rounded a money
    figure" bug, reproducible in this repo. It is the smallest defect class the harness is
    contractually required to catch. It must clear REL_TOL by orders of magnitude AND -- this is
    the calibration argument's whole point -- be invisible to a naive 1e-6 rule.
    """
    original = amortization.amortization_payment

    def rounded_to_cents_squared(principal: float, rate: float, years: int) -> float:
        return round(original(principal, rate, years), 4)

    max_rel, exceeds_1e9, exceeds_1e6 = _max_rel_drift_and_exceed_counts(rounded_to_cents_squared, golden["cases"])

    assert max_rel > _CEILING_LOWER_BOUND, f"round(payment, 4) ceiling moved: max_rel={max_rel:.4e}, expected > {_CEILING_LOWER_BOUND:.0e}"
    assert exceeds_1e9 > 0, "the defect class the harness exists to catch must exceed REL_TOL somewhere in the matrix"
    assert exceeds_1e6 == 0, "the defect class must be INVISIBLE to a naive 1e-6 rule -- this is precisely why REL_TOL is 1e-9, not 1e-6"


def test_floor_and_ceiling_bracket_rel_tol_with_wide_margin(golden: dict[str, Any]) -> None:
    """
    The load-bearing structural claim of the whole design (D.3 section 1.3): `REL_TOL` sits
    thousands of times above the measured reordering floor and thousands of times below the
    measured defect signature. Re-derives both walls (the SAME two experiments D.3 section 1.3
    reports: a 1-ULP injection for the floor, a direct 9.4e-8 RELATIVE injection -- not
    `round(payment, 4)`, which is a different, "invisible at 1e-6" recipe covered separately above
    -- for the ceiling) and checks the bracket directly, rather than trusting the two tests above
    ran in the same session.
    """
    original = amortization.amortization_payment

    def one_ulp(principal: float, rate: float, years: int) -> float:
        return math.nextafter(original(principal, rate, years), math.inf)

    def relative_9_4e_minus_8(principal: float, rate: float, years: int) -> float:
        return original(principal, rate, years) * (1.0 + 9.4e-8)

    floor, _, _ = _max_rel_drift_and_exceed_counts(one_ulp, golden["cases"])
    ceiling, _, _ = _max_rel_drift_and_exceed_counts(relative_9_4e_minus_8, golden["cases"])

    assert floor > 0.0
    assert ceiling > floor
    assert REL_TOL / floor > 1_000, f"REL_TOL is not comfortably above the measured floor: REL_TOL/floor = {REL_TOL / floor:.1f}"
    assert ceiling / REL_TOL > 1_000, f"REL_TOL is not comfortably below the measured ceiling: ceiling/REL_TOL = {ceiling / REL_TOL:.1f}"


def test_dollar_blindness_boundary_on_the_shipped_deal(golden: dict[str, Any]) -> None:
    """
    GD.1 condition C6, the executable form (not prose): `REL_TOL * max(|field|) < 0.005` (half a
    display cent) over the shipped deal's own golden entry (`36_kelly_moncton`) -- the deal this
    product actually ships, not the synthetic 500-unit/50-year matrix extreme. PD.1's ratification
    of `REL_TOL = 1e-9` is conditional on this staying true: "the day `REL_TOL * |field|` reaches
    half the display quantum of a rendered, decision-bearing surface" is the day the tolerance
    becomes unacceptable and must return to the founder, not be widened by whoever is on shift.
    """
    forecast = golden["cases"]["sample_deal_36_kelly_moncton"]["forecast"]

    def _max_abs_float(node: Any) -> float:
        if isinstance(node, bool):
            return 0.0
        if isinstance(node, int | float):
            return abs(float(node))
        if isinstance(node, dict):
            return max((_max_abs_float(v) for v in node.values()), default=0.0)
        if isinstance(node, list):
            return max((_max_abs_float(v) for v in node), default=0.0)
        return 0.0

    largest_field = _max_abs_float(forecast)
    assert largest_field > 0.0, "sanity: the shipped deal's forecast must contain at least one nonzero numeric field"

    blindness = REL_TOL * largest_field
    assert blindness < DOLLAR_BLINDNESS_BUDGET, (
        f"DOLLAR-BLINDNESS BOUNDARY BREACHED: REL_TOL * max(|shipped-deal field|) = {blindness:.6f} "
        f">= {DOLLAR_BLINDNESS_BUDGET} (half a display cent). PD.1's ratification of REL_TOL=1e-9 is "
        "conditional on this staying true -- this is a founder decision now, not an engineering one. "
        "See docs/plans/mission-5-discovery/PD1_product_calls.md section (a) and "
        "docs/plans/mission-5-discovery/GD1_veto_review.md condition C6."
    )


def test_shipped_deal_dollar_blindness_matches_measured_figure() -> None:
    """
    Pins the specific measured figure PD.1 ratified in writing ($0.00053 on `36_kelly_moncton`'s
    largest field, `years[9].est_value`), so a change to this number is visible in a diff rather
    than only in a passing inequality.
    """
    with GOLDEN_PATH.open("r", encoding="utf-8") as f:
        golden_data = json.load(f)
    forecast = golden_data["cases"]["sample_deal_36_kelly_moncton"]["forecast"]
    est_values = [y["est_value"] for y in forecast["years"]]
    largest = max(est_values)
    assert (
        largest == forecast["years"][9]["est_value"]
    ), "PD.1's cited largest field is years[9].est_value -- re-confirm if golden_cases.py or the sample deal changed"
    blindness = REL_TOL * largest
    assert round(blindness, 6) == 0.000533, f"measured dollar-blindness on the shipped deal moved: {blindness:.6f} (PD.1 cited $0.00053)"
