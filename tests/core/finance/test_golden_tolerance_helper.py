# tests/core/finance/test_golden_tolerance_helper.py
"""
Unit coverage for `tests/core/finance/golden_tolerance.py` itself -- the comparison predicate, the
drift-ledger validation logic (GD.1 condition C5), and the anchor digest/cumulative-drift helpers
(GD.1 condition C2) -- exercised directly against small, synthetic dicts, with no dependency on
`run_financial_model` or the committed golden matrix.

SCOPE NOTE: this is IT.1's own unit coverage of the module it built, matching the project's
standard "unit tests for logic, golden-number tests for finance" split. It is distinct from
`test_golden_tolerance_walls.py` (which re-derives the two measured walls end-to-end through the
engine, GD.1 condition C6) and from IT.2's calibration RED suite
(`test_golden_tolerance_walls.py`, which re-derives both walls in-repo and carries the
calibration recipes).
"""

from __future__ import annotations

import json
import math

import pytest

from tests.core.finance.golden_tolerance import (
    APPROACHING_LO,
    REL_TOL,
    DeviationKind,
    DriftLedgerEntry,
    LedgerStatus,
    canonical_cases_digest,
    compare_golden,
    cumulative_drift,
    evaluate_ledger_entry,
    render_case_result,
)

# ---------------------------------------------------------------------------
# The comparison predicate.
# ---------------------------------------------------------------------------


def test_exact_match_is_a_clean_pass() -> None:
    expected = {"a": 1, "b": 1.5, "c": "x", "d": None, "e": True, "f": [1, 2, {"g": 0.0}]}
    actual = {"a": 1, "b": 1.5, "c": "x", "d": None, "e": True, "f": [1, 2, {"g": 0.0}]}
    report = compare_golden("case", actual, expected)
    assert report.deviations == []


def test_bool_is_dispatched_before_int_even_though_isinstance_true_int_is_true() -> None:
    """The D.3 section 2.5 trap, verified directly: isinstance(True, int) is True in Python, so
    the leaf dispatch must check bool FIRST or a bool field would silently enter the int/float
    tolerance path."""
    assert isinstance(True, int)  # the trap, restated as a fact
    report = compare_golden("case", {"flag": False}, {"flag": True})
    assert len(report.deviations) == 1
    assert report.deviations[0].kind is DeviationKind.EXACT_MISMATCH
    assert report.deviations[0].path == "flag"


def test_bool_type_mismatch_against_int_is_structural() -> None:
    report = compare_golden("case", {"flag": 1}, {"flag": True})
    assert len(report.deviations) == 1
    assert report.deviations[0].kind is DeviationKind.STRUCTURAL


def test_int_leaf_type_mismatch_against_float_is_structural() -> None:
    """D.3 section 2.6: 'a float where an int was anchored is a FAIL with a structural message'."""
    report = compare_golden("case", {"year": 1.0}, {"year": 1})
    assert len(report.deviations) == 1
    assert report.deviations[0].kind is DeviationKind.STRUCTURAL


def test_int_exact_mismatch() -> None:
    report = compare_golden("case", {"year": 2}, {"year": 1})
    assert len(report.deviations) == 1
    assert report.deviations[0].kind is DeviationKind.EXACT_MISMATCH


def test_string_order_and_value_sensitive() -> None:
    report = compare_golden("case", {"warnings": ["a", "c"]}, {"warnings": ["a", "b"]})
    assert len(report.deviations) == 1
    assert report.deviations[0].path == "warnings[1]"
    assert report.deviations[0].kind is DeviationKind.EXACT_MISMATCH


def test_exact_zero_requires_exact_zero_actual() -> None:
    """D.3 section 2.4: 652 semantic zeros -- expected == 0.0 requires actual == 0.0 exactly."""
    report = compare_golden("case", {"ending_balance": 6.31}, {"ending_balance": 0.0})
    assert len(report.deviations) == 1
    assert report.deviations[0].kind is DeviationKind.ZERO_VIOLATION


def test_exact_zero_matched_by_exact_zero_passes() -> None:
    report = compare_golden("case", {"ending_balance": 0.0}, {"ending_balance": 0.0})
    assert report.deviations == []


def test_exact_zero_matched_by_negative_zero_passes() -> None:
    """D.3 section 2.4: `-0.0 == 0.0` is True in Python; this rule accepts it deliberately."""
    report = compare_golden("case", {"ending_balance": -0.0}, {"ending_balance": 0.0})
    assert report.deviations == []


def test_asymmetric_denominator_uses_expected_not_actual() -> None:
    """
    D.3 section 2.2: `abs(actual - expected) <= REL_TOL * abs(expected)` -- expected alone is the
    denominator, NOT `max(|a|, |b|)` as `math.isclose` would use. Construct a case where the two
    forms disagree and confirm this module takes the anchored (expected) side.

    Note: `rel_tol=1e-6`, not tighter, on the `isclose` check below is deliberate and NOT a
    contradiction of this module's own `abs_tol=0` policy -- it is test-construction slack. Adding
    a ~1e-9-relative delta to a magnitude-1.0 float and reading it back loses precision at roughly
    that same relative scale (the sum's own ULP, ~2.2e-16 absolute, is ~2e-7 relative to a 1e-9-
    sized delta) -- an unavoidable property of IEEE-754 addition, not of the code under test.
    """
    expected = 1.0
    actual = 1.0 + REL_TOL * 2  # drift is ~2x REL_TOL relative to `expected`
    report = compare_golden("case", {"x": actual}, {"x": expected})
    assert len(report.deviations) == 1
    assert report.deviations[0].kind is DeviationKind.EXCEEDS
    rel = report.deviations[0].rel_drift
    assert rel is not None
    assert math.isclose(rel, 2 * REL_TOL, rel_tol=1e-6)


def test_drift_just_below_approaching_floor_passes_silently() -> None:
    expected = 1.0
    actual = 1.0 + (APPROACHING_LO * 0.5)
    report = compare_golden("case", {"x": actual}, {"x": expected})
    assert report.deviations == []
    assert report.float_rel_drift["x"] > 0.0


def test_drift_in_approaching_band_is_flagged_not_hard_failed() -> None:
    expected = 1.0
    actual = 1.0 + (APPROACHING_LO * 1.5)
    report = compare_golden("case", {"x": actual}, {"x": expected})
    assert len(report.deviations) == 1
    assert report.deviations[0].kind is DeviationKind.APPROACHING
    assert report.hard_failures == []


def test_drift_at_exactly_rel_tol_passes_le_not_lt(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    D.3 section 2.2: '<=' not '<' -- a deviation of exactly REL_TOL * |expected| passes.

    A naive construction (`actual = 1.0 + REL_TOL`) cannot reliably hit the exact boundary: adding
    a ~1e-9-relative delta to 1.0 and reading the difference back loses precision at roughly that
    same relative scale (IEEE-754 addition, not a defect in the code under test -- see the
    docstring on `test_asymmetric_denominator_uses_expected_not_actual` above). This test instead
    monkeypatches `REL_TOL`/`APPROACHING_LO` to an EXACTLY representable power-of-two value for the
    duration of the test, so `expected + delta - expected` recovers `delta` bit-for-bit and the
    boundary is genuinely exact, not approximately exact.
    """
    import tests.core.finance.golden_tolerance as gt

    patched_rel_tol = 2.0**-30  # exactly representable; close to the real REL_TOL's order of magnitude
    monkeypatch.setattr(gt, "REL_TOL", patched_rel_tol)
    monkeypatch.setattr(gt, "APPROACHING_LO", patched_rel_tol * 0.5)

    expected = 1.0
    delta = patched_rel_tol  # 2**-30, exactly representable relative to 1.0's mantissa
    at_boundary = expected + delta  # exact: no rounding, well within 1.0's 52-bit mantissa
    assert (at_boundary - expected) == delta, "test construction must be bit-exact or this test proves nothing"

    report = gt.compare_golden("case", {"x": at_boundary}, {"x": expected})
    assert (
        report.deviations == []
    ), f"a deviation of EXACTLY REL_TOL*|expected| must pass (D.3 section 2.2 '<=' not '<'): {report.deviations}"

    just_over = expected + delta * 1.0001
    report_over = gt.compare_golden("case", {"x": just_over}, {"x": expected})
    assert len(report_over.deviations) == 1
    assert report_over.deviations[0].kind is gt.DeviationKind.EXCEEDS


def test_drift_exceeding_rel_tol_is_a_hard_failure() -> None:
    expected = 1.0
    actual = 1.0 + REL_TOL * 1.0001
    report = compare_golden("case", {"x": actual}, {"x": expected})
    assert len(report.deviations) == 1
    assert report.deviations[0].kind is DeviationKind.EXCEEDS


def test_nan_fails_closed() -> None:
    report = compare_golden("case", {"x": float("nan")}, {"x": 1.0})
    assert len(report.deviations) == 1
    assert report.deviations[0].kind is DeviationKind.EXCEEDS
    assert "NaN" in report.deviations[0].detail


def test_equal_infinities_pass() -> None:
    report = compare_golden("case", {"x": float("inf")}, {"x": float("inf")})
    assert report.deviations == []


def test_structural_key_set_mismatch() -> None:
    report = compare_golden("case", {"a": 1}, {"a": 1, "b": 2})
    assert len(report.deviations) == 1
    assert report.deviations[0].kind is DeviationKind.STRUCTURAL


def test_structural_list_length_mismatch() -> None:
    report = compare_golden("case", {"years": [1, 2]}, {"years": [1, 2, 3]})
    assert len(report.deviations) == 1
    assert report.deviations[0].kind is DeviationKind.STRUCTURAL


def test_structural_mismatch_short_circuits_recursion_into_the_bad_subtree() -> None:
    """A key-set mismatch inside a nested object must not also enumerate every leaf beneath it."""
    expected = {"purchase": {"dscr": 1.0, "coc": 0.5}}
    actual = {"purchase": {"dscr": 1.0}}
    report = compare_golden("case", actual, expected)
    assert len(report.deviations) == 1
    assert report.deviations[0].path == "purchase"
    assert report.deviations[0].kind is DeviationKind.STRUCTURAL


def test_none_vs_object_is_structural() -> None:
    report = compare_golden("case", {"refi": {"year": 1}}, {"refi": None})
    assert len(report.deviations) == 1
    assert report.deviations[0].kind is DeviationKind.STRUCTURAL


# ---------------------------------------------------------------------------
# The drift ledger (GD.1 condition C5).
# ---------------------------------------------------------------------------


def _entry(max_rel: float) -> DriftLedgerEntry:
    return DriftLedgerEntry(case="c", field_path="f", max_rel=max_rel, reason="test", mission="5", date="2026-08-31")


def test_ledger_missing_entry() -> None:
    status, _ = evaluate_ledger_entry(None, 6.0e-10)
    assert status is LedgerStatus.MISSING


def test_ledger_out_of_range_rejected_regardless_of_measurement() -> None:
    status, _ = evaluate_ledger_entry(_entry(REL_TOL), 6.0e-10)
    assert status is LedgerStatus.OUT_OF_RANGE


def test_ledger_over_provisioned_rejected() -> None:
    """C5: reject an entry whose max_rel exceeds the currently-measured drift by more than 10%."""
    measured = 6.1e-10
    over_provisioned = measured * 1.25  # 25% headroom > the 10% allowance
    status, _ = evaluate_ledger_entry(_entry(over_provisioned), measured)
    assert status is LedgerStatus.OVER_PROVISIONED


def test_ledger_within_10_percent_headroom_is_covered() -> None:
    measured = 6.1e-10
    within_budget = measured * 1.09
    status, _ = evaluate_ledger_entry(_entry(within_budget), measured)
    assert status is LedgerStatus.COVERED


def test_ledger_stale_entry_rejected_when_drift_has_fallen_below_the_band() -> None:
    """C5: 'if the drift disappears ... the entry becomes stale and the suite fails until removed'."""
    status, detail = evaluate_ledger_entry(_entry(9.0e-10), APPROACHING_LO * 0.1)
    assert status is LedgerStatus.STALE
    assert "remove it" in detail


def test_ledger_undercovered_when_drift_grew_past_recorded_max_rel() -> None:
    status, detail = evaluate_ledger_entry(_entry(6.0e-10), 8.0e-10)
    assert status is LedgerStatus.UNDERCOVERED
    assert "fresh entry" in detail


def test_ledger_unknown_field_when_measurement_is_none() -> None:
    status, _ = evaluate_ledger_entry(_entry(6.0e-10), None)
    assert status is LedgerStatus.UNKNOWN_FIELD


def test_render_case_result_covered_approaching_deviation_passes() -> None:
    expected = 1.0
    actual = 1.0 + (APPROACHING_LO * 1.5)
    report = compare_golden("interest_rate_high", {"x": actual}, {"x": expected})
    measured = report.approaching[0].rel_drift
    assert measured is not None
    ledger = {("interest_rate_high", "x"): _entry(measured * 1.05)}
    ok, message = render_case_result(report, ledger)
    assert ok, message


def test_render_case_result_uncovered_approaching_deviation_fails_with_do_not_regenerate_text() -> None:
    expected = 1.0
    actual = 1.0 + (APPROACHING_LO * 1.5)
    report = compare_golden("interest_rate_high", {"x": actual}, {"x": expected})
    ok, message = render_case_result(report, ledger={})
    assert not ok
    assert "DO NOT REGENERATE THE GOLDEN" in message
    assert "In-tolerance drift is never a reason to re-anchor" in message


def test_render_case_result_hard_failure_names_the_finding_not_a_chore() -> None:
    report = compare_golden("case", {"x": 999.0}, {"x": 1.0})
    ok, message = render_case_result(report, ledger={})
    assert not ok
    assert "EXCEEDS TOLERANCE" in message
    assert "not a chore" in message


# ---------------------------------------------------------------------------
# The anchor digest and cumulative-drift chain (GD.1 condition C2).
# ---------------------------------------------------------------------------


def test_canonical_digest_is_stable_under_reindentation() -> None:
    a = {"case1": {"forecast": {"x": 1.0, "y": 2.0}}}
    pretty = json.dumps(a, indent=8, sort_keys=False)
    reparsed = json.loads(pretty)
    assert canonical_cases_digest(a) == canonical_cases_digest(reparsed)


def test_canonical_digest_changes_when_a_number_moves() -> None:
    a = {"case1": {"forecast": {"x": 1.0}}}
    b = {"case1": {"forecast": {"x": 1.0000001}}}
    assert canonical_cases_digest(a) != canonical_cases_digest(b)


def test_cumulative_drift_first_anchor_is_zero() -> None:
    anchor = {"max_rel_drift_vs_previous_anchor": None, "supersedes": None}
    assert cumulative_drift(anchor) == 0.0


def test_cumulative_drift_sums_across_the_chain() -> None:
    anchor = {
        "max_rel_drift_vs_previous_anchor": 3.0e-9,
        "supersedes": {
            "max_rel_drift_vs_previous_anchor": 2.0e-9,
            "supersedes": {
                "max_rel_drift_vs_previous_anchor": None,
                "supersedes": None,
            },
        },
    }
    assert math.isclose(cumulative_drift(anchor), 5.0e-9, rel_tol=1e-12)


def test_cumulative_drift_budget_can_be_exceeded_by_many_small_hops() -> None:
    """Ten hops at full REL_TOL exhausts the 1e-8 budget, per D.3 section 3.5's own framing."""
    from tests.core.finance.golden_tolerance import CUMULATIVE_DRIFT_BUDGET

    node: dict[str, object] | None = None
    for _ in range(10):
        node = {"max_rel_drift_vs_previous_anchor": REL_TOL, "supersedes": node}
    assert node is not None
    total = cumulative_drift(node)
    assert math.isclose(total, 10 * REL_TOL, rel_tol=1e-9)
    assert total >= CUMULATIVE_DRIFT_BUDGET
