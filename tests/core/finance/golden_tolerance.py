# tests/core/finance/golden_tolerance.py
"""
The Mission 5 tolerance-comparison helper for the finance golden harness.

WHY THIS MODULE EXISTS
-----------------------
`tests/core/finance/test_golden_forecasts.py` used to compare `run_financial_model` output to the
committed golden with plain `==` on the whole `FinancialForecast.model_dump(mode="json")` dict --
truly BIT-EXACT. Mission 5's forward-mode (tangent-linear) differentiation work reorders floating-point arithmetic
(dual-number threading through `engine.py` / `irr.py::_brent_root`) without changing the *math*,
which makes bit-exact comparison the wrong tool: it cannot distinguish "the answer changed" from
"the answer was computed via a different, still-correct, sequence of IEEE-754 operations."

This module is that distinction, made executable. It implements the comparison rule specified in
`docs/plans/mission-5-discovery/D3_tolerance_rule.md` ("D.3"), as reviewed and conditioned by
`docs/plans/mission-5-discovery/GD1_veto_review.md` ("GD.1", VETO LIFTED WITH CONDITIONS C1-C7),
and ratified by `docs/plans/mission-5-discovery/PD1_product_calls.md` ("PD.1": `REL_TOL = 1e-9`).

THE RULE IS NOT "APPROXIMATE." IT IS A NAMED, JUSTIFIED, MEASURED TOLERANCE.
------------------------------------------------------------------------------
`test_golden_forecasts.py`'s own original docstring (pre-Mission-5) says it best: "If a
genuinely-derived field could not be pinned exactly ... that would be called out explicitly here
with a named, justified tolerance." This module IS that named, justified tolerance -- both walls
(the floating-point reordering noise floor, ~1.15e-13, and the smallest defect class the harness is
contractually required to catch, ~1.35e-5) were measured end-to-end through `run_financial_model`
across the full 34-case golden matrix, reproduced independently three times (design, guardian,
orchestrator; see D.3 section 1.3 and GD.1's "Independent verification performed"), before `1e-9`
-- their geometric midpoint, biased tighter -- was chosen. See
`tests/core/finance/test_golden_tolerance_walls.py` for the in-repo re-derivation (GD.1 condition
C6) that keeps these two numbers live rather than stale prose.

THE COMPARISON RULE (D.3 section 2), exactly
----------------------------------------------
For each leaf field, by path, AFTER a structural check (identical key sets, identical list
lengths, identical leaf types -- D.3 section 2.6):

    bool                                        -> actual == expected  (exact)
    str / None                                  -> actual == expected  (exact)
    int (years[*].year, refi.year)               -> actual == expected  (exact)
    float, expected == 0.0                       -> actual == 0.0       (exact -- 652 semantic
                                                     zeros across 20 field paths: a retired loan,
                                                     an absent expense line, no debt. Not the
                                                     residue of cancellation; exactness costs
                                                     nothing and catches real defects -- D.3
                                                     section 2.4.)
    float, expected != 0.0                       -> abs(actual - expected) <= REL_TOL * abs(expected)

`bool` is tested BEFORE `int`/`float`: `isinstance(True, int)` is `True` in Python, so the type
dispatch below tests `bool` first or a future boolean field would silently enter the numeric path
(D.3 section 2.5, trap 1; no bool field exists in `FinancialForecast` today, this guard is
insurance).

WHAT THIS MODULE DOES **NOT** PERMIT -- stated here so it cannot be cited later to justify a wider
relaxation (D.3 section 6.3, GD.1 condition C6's requirement that these prohibitions live in this
docstring):

  1. NO absolute-tolerance floor, EVER. `abs_tol` does not exist anywhere in this module, as a
     parameter, a constant, or a fallback. The tightest-budget field in the matrix
     (`interest_rate_high::years[0].principal_paid`, a ~$505.72 cancellation of ~$72,500 numbers)
     has a measured noise floor of 5.8e-11 dollars against a 5.06e-7 dollar budget -- it is the
     harness's single most sensitive detector, because catastrophic cancellation
     (`max(0.0, pay - interest)`, `amortization.py:93`) amplifies upstream error ~143x. An
     `abs_tol` of any size would blind exactly that detector (D.3 section 2.3).
  2. NO `math.isclose`. The comparison is the explicit ASYMMETRIC form,
     `abs(actual - expected) <= REL_TOL * abs(expected)` -- the anchored `expected` value is the
     sole authority and belongs in the denominator alone. `math.isclose` scales by
     `max(|a|, |b|)`, making the predicate depend partly on the value under test, which is the
     wrong dependency for an anchor (D.3 section 2.2).
  3. NO per-field, per-case, or per-mission tolerance override mechanism -- not even for
     `irr_10yr`, the one iteratively-solved field, whose condition number was measured at 0.2x-2.3x
     (O(1), no iteration-path discontinuity) across ten orders of magnitude (D.3 section 2.7). A
     per-field override table is itself a per-field ratchet; this module does not build it.
  4. `REL_TOL` is NOT configurable at runtime. Not an environment variable (this project's
     `AIREAL_*` flags gate optional *features*, never the strictness of a correctness check), not a
     CLI flag, not a pytest option, not a fixture parameter. It is a module constant (D.3 section
     6.3, item 6).
  5. NO relaxation anywhere else in the codebase. This module is imported by exactly two
     production-facing test functions (see `test_golden_forecasts.py`). Guardrail thresholds,
     recourse confirm-by-rerun assertions, report rendering, and `chief_strategist` comparisons are
     all untouched and stay bit-exact or as otherwise separately specified.
  6. Regenerating the golden because of in-tolerance drift is not a thing this module enables.
     `generate_golden_forecasts.py`'s safety gate (built alongside this module) refuses a
     numeric-only regeneration; only `--supersede-anchor --rationale "..."` can move the anchor,
     and doing so is a founder-visible, reviewed event, never an automatic response to drift.

THE APPROACHING-TOLERANCE STATE (D.3 section 4)
--------------------------------------------------
A relative drift in `[APPROACHING_LO, REL_TOL)` -- half of tolerance, `5e-10` to `1e-9` --
FAILS THE BUILD, not a warning. It is convertible to PASS only by a scoped, bounded, self-expiring
entry in `tests/data/golden/DRIFT_LEDGER.json` (see `DriftLedgerEntry`, `evaluate_ledger_entry`,
`validate_drift_ledger` below). The threshold is the fraction at which "one more change of this
size would breach" is literally true -- a mechanically meaningful definition of "approaching," not
a round number chosen by taste (D.3 section 4.1). It sits ~4,300x above the measured
floating-point-reordering noise floor, so it cannot fire on legitimate arithmetic reassociation --
anything reaching it is a change in the arithmetic, not a change in the order of the arithmetic.

THE ANCHOR (D.3 section 3)
-----------------------------
Comparison is always against `tests/data/golden/finance_engine_forecasts.json`'s `cases` subtree,
whose SHA-256 digest is pinned in `tests/data/golden/ANCHOR.json::cases_sha256`
(see `canonical_cases_digest` below and `tests/core/finance/test_golden_anchor.py`, its own file,
so an anchor-digest failure is unmistakable and distinct from a tolerance failure). The digest
covers `cases` only, not the whole file -- the `_meta` banner is prose and may improve freely; no
digit in any case may move without a re-anchor. `ANCHOR.json` records carry
`max_rel_drift_vs_previous_anchor` and chain via `supersedes` (a nested previous-anchor record, or
`null` for the first anchor); `cumulative_drift` below walks that chain and
`test_golden_anchor.py` fails the build if the cumulative drift from the first anchor exceeds
`CUMULATIVE_DRIFT_BUDGET` (GD.1 condition C2, MANDATORY). That failure's remedy is independent
human re-verification (in the spirit of `test_sample_deal_verified_baseline_numbers`), never a
budget raise.

WHAT STAYS OUTSIDE THIS RULE (D.3 section 6.2, GD.1 condition C1) -- unchanged by this module:
`test_determinism_repeated_calls_are_identical`, `test_sample_deal_verified_baseline_numbers`,
`tests/core/finance/test_metrics_parity.py`, `tests/core/finance/test_engine_bitexact_refactors.py`.

THE ~9.4e-8 CALIBRATION FIGURE IS A CONTRACT, NOT A MEASUREMENT (GD.1 condition C4(c))
------------------------------------------------------------------------------------------
Mission 5's charter documents cite "~9.4e-8" as the size of an "injected rounding bug" the
tolerance rule must catch. `git log --all -S"9.4e-8"` returns exactly one commit -- the Mission 5
charter itself -- so no earlier measurement of this exact figure exists anywhere in this
repository's history (D.3 section 5.1, independently reconfirmed by GD.1). It is retained here as a
CONTRACT CONSTANT (any value in the open interval `(REL_TOL, 1e-6)` would satisfy the same
acceptance criterion by construction: `1e-9 < 9.4e-8 < 1e-6`), bound to a reproducible recipe that
IS a measurement of a real, reproducible defect class in this codebase:
`amortization.amortization_payment` output rounded to 4 decimal places
(`round(original(...), 4)`) produces a measured max relative deviation of **1.1325e-7** across the
34-case matrix (1,613 of 11,789 fields exceed `REL_TOL`; zero exceed a naive 1e-6 rule -- see
`test_golden_tolerance_walls.py::test_ceiling_round_payment_4_defect_class_exceeds_rel_tol_by_orders_of_magnitude`).
Any calibration test asserting the ~9.4e-8 acceptance criterion should cite THIS status (contract,
not measurement) and THIS recipe in its own docstring, per GD.1 condition C4(c).
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# The constant. Not env-configurable, not CLI-configurable. See module docstring
# prohibition (4). Ratified by PD.1 ("RATIFY 1e-9 relative"), conditioned by GD.1.
# ---------------------------------------------------------------------------
REL_TOL: float = 1e-9

# The fraction of REL_TOL at which a comparison enters the approaching-tolerance band. D.3 section 4.1.
WARN_FRACTION: float = 0.5

# The approaching-tolerance band floor: [APPROACHING_LO, REL_TOL) fails the build unless a
# DRIFT_LEDGER.json entry covers it.
APPROACHING_LO: float = WARN_FRACTION * REL_TOL  # 5e-10

# GD.1 condition C2 (mandatory): cumulative drift across the ANCHOR.json `supersedes` chain, from
# the very first anchor, must not exceed this budget. Exhausting it means independent human
# re-verification -- NEVER a budget raise. D.3 section 3.5.
CUMULATIVE_DRIFT_BUDGET: float = 1e-8

# GD.1 condition C5: a DRIFT_LEDGER.json entry is "over-provisioned" -- and rejected -- if its
# recorded max_rel exceeds the currently-measured drift by more than this fraction. 10%, per C5.
LEDGER_OVER_PROVISION_FACTOR: float = 0.10

# GD.1 condition C6: half a display cent -- the dollar-blindness boundary PD.1 ratified in writing.
# See `test_golden_tolerance_walls.py` for the executable assertion against the shipped deal.
DOLLAR_BLINDNESS_BUDGET: float = 0.005

# Shared path constants -- the single source of truth for where the golden/anchor/ledger live, so
# every consumer (the harness, the anchor test, the generator) agrees without a second copy.
GOLDEN_PATH: Path = Path(__file__).resolve().parents[2] / "data" / "golden" / "finance_engine_forecasts.json"


class DeviationKind(str, Enum):
    """The category of a single leaf-field mismatch. Determines whether it can ever be excused."""

    STRUCTURAL = "structural"  # key set / list length / leaf-type mismatch -- never excusable
    EXACT_MISMATCH = "exact_mismatch"  # bool/str/int/None field that should have been == -- never excusable
    ZERO_VIOLATION = "zero_violation"  # expected == 0.0, actual != 0.0 -- never excusable
    EXCEEDS = "exceeds"  # float, rel_drift >= REL_TOL -- never excusable
    APPROACHING = "approaching"  # float, rel_drift in [APPROACHING_LO, REL_TOL) -- excusable via the ledger


@dataclass(frozen=True)
class Deviation:
    """One leaf-field mismatch, found while comparing a computed forecast to the anchored golden."""

    path: str
    kind: DeviationKind
    expected: Any
    actual: Any
    rel_drift: float | None  # None for non-float kinds
    detail: str


@dataclass
class ComparisonReport:
    """The full result of comparing one case's computed forecast to its anchored golden entry."""

    case_id: str
    total_leaf_count: int
    deviations: list[Deviation] = field(default_factory=list)
    # path -> relative drift, for EVERY nonzero-expected float leaf compared, whether or not it
    # produced a Deviation. Used by drift-ledger reconciliation (stale-entry detection requires
    # knowing the CURRENT drift of a field even when that field currently passes silently).
    float_rel_drift: dict[str, float] = field(default_factory=dict)

    @property
    def structural(self) -> list[Deviation]:
        return [d for d in self.deviations if d.kind is DeviationKind.STRUCTURAL]

    @property
    def exact_mismatches(self) -> list[Deviation]:
        return [d for d in self.deviations if d.kind is DeviationKind.EXACT_MISMATCH]

    @property
    def zero_violations(self) -> list[Deviation]:
        return [d for d in self.deviations if d.kind is DeviationKind.ZERO_VIOLATION]

    @property
    def exceeding(self) -> list[Deviation]:
        return [d for d in self.deviations if d.kind is DeviationKind.EXCEEDS]

    @property
    def approaching(self) -> list[Deviation]:
        return [d for d in self.deviations if d.kind is DeviationKind.APPROACHING]

    @property
    def hard_failures(self) -> list[Deviation]:
        """Deviations that can NEVER be excused by a ledger entry."""
        return self.structural + self.exact_mismatches + self.zero_violations + self.exceeding


def _fmt_path(base: str, key: Any) -> str:
    if isinstance(key, int):
        return f"{base}[{key}]"
    return f"{base}.{key}" if base else str(key)


def _leaf(
    out: list[Deviation],
    path: str,
    kind: DeviationKind,
    expected: Any,
    actual: Any,
    rel_drift: float | None,
    detail: str,
) -> None:
    out.append(Deviation(path=path, kind=kind, expected=expected, actual=actual, rel_drift=rel_drift, detail=detail))


def _compare_leaf(
    path: str,
    actual: Any,
    expected: Any,
    out: list[Deviation],
    float_rel_drift: dict[str, float],
    leaf_counter: list[int],
) -> None:
    leaf_counter[0] += 1

    # Trap 1 (D.3 section 2.5): isinstance(True, int) is True in Python. Test bool BEFORE
    # int/float or a future boolean field silently enters the numeric path.
    if isinstance(expected, bool):
        if not isinstance(actual, bool):
            _leaf(out, path, DeviationKind.STRUCTURAL, expected, actual, None, f"expected bool, got {type(actual).__name__}")
        elif actual != expected:
            _leaf(out, path, DeviationKind.EXACT_MISMATCH, expected, actual, None, "bool field mismatch")
        return

    if expected is None:
        if actual is not None:
            _leaf(out, path, DeviationKind.STRUCTURAL, expected, actual, None, "expected None, got a value")
        return

    if isinstance(expected, str):
        if not isinstance(actual, str):
            _leaf(out, path, DeviationKind.STRUCTURAL, expected, actual, None, f"expected str, got {type(actual).__name__}")
        elif actual != expected:
            _leaf(out, path, DeviationKind.EXACT_MISMATCH, expected, actual, None, "str field mismatch (order/value-sensitive)")
        return

    if isinstance(expected, int):  # bool already excluded above
        if isinstance(actual, bool) or not isinstance(actual, int):
            _leaf(out, path, DeviationKind.STRUCTURAL, expected, actual, None, f"expected int, got {type(actual).__name__}")
        elif actual != expected:
            _leaf(out, path, DeviationKind.EXACT_MISMATCH, expected, actual, None, "int field mismatch (a counter, not a measurement)")
        return

    if isinstance(expected, float):
        if isinstance(actual, bool) or not isinstance(actual, int | float):
            _leaf(out, path, DeviationKind.STRUCTURAL, expected, actual, None, f"expected float, got {type(actual).__name__}")
            return
        actual_f = float(actual)

        # NaN: fail closed. `abs(nan - x) <= t` is False, which is the right direction, but a
        # naive rel-drift computation would silently fall through neither EXCEEDS nor APPROACHING.
        # Make the fail-closed behaviour explicit rather than accidental (D.3 section 2.4).
        if math.isnan(expected) or math.isnan(actual_f):
            _leaf(
                out,
                path,
                DeviationKind.EXCEEDS,
                expected,
                actual,
                None,
                "NaN encountered -- comparison fails closed, never silently passes",
            )
            return

        if actual_f == expected:  # covers equal finite values and equal signed infinities
            if expected != 0.0:
                float_rel_drift[path] = 0.0
            return

        if expected == 0.0:
            _leaf(
                out,
                path,
                DeviationKind.ZERO_VIOLATION,
                expected,
                actual,
                None,
                "652-class semantic zero (retired loan / absent expense / no debt) violated by a nonzero actual",
            )
            return

        abs_diff = abs(actual_f - expected)
        rel = abs_diff / abs(expected)
        float_rel_drift[path] = rel
        # D.3 section 2.2: "<=" not "<" -- a deviation of EXACTLY REL_TOL * |expected| PASSES.
        # D.3 section 4.1: the approaching-tolerance band is the HALF-OPEN interval
        # [APPROACHING_LO, REL_TOL) -- it excludes REL_TOL itself, which is a full silent pass.
        #
        # The PASS/EXCEEDS decision uses the module docstring's documented EXPLICIT ASYMMETRIC
        # FORM, `abs(actual - expected) <= REL_TOL * abs(expected)` (prohibition (2): NO
        # `math.isclose`), not `rel > REL_TOL` -- dividing by `abs(expected)` to get `rel`
        # introduces a rounding step the multiplication form does not have, so the two forms can
        # disagree by a ULP exactly at the boundary. `rel` is retained only as the diagnostic
        # relative-drift value for the approaching-tolerance band and for reporting; it never
        # drives the EXCEEDS decision itself.
        if abs_diff > REL_TOL * abs(expected):
            _leaf(out, path, DeviationKind.EXCEEDS, expected, actual, rel, f"{rel:.4e} relative drift > REL_TOL {REL_TOL:.1e}")
        elif APPROACHING_LO <= rel < REL_TOL:
            _leaf(
                out,
                path,
                DeviationKind.APPROACHING,
                expected,
                actual,
                rel,
                f"{rel:.4e} relative drift ({rel / REL_TOL:.0%} of tolerance) -- in the approaching-tolerance band",
            )
        # else: silent pass -- covers `rel < APPROACHING_LO` AND `rel == REL_TOL` exactly.
        # else: silently passes. Recorded in float_rel_drift for ledger stale-detection, but no
        # Deviation is created -- this is the "no band entries" PASS D.3 section 5.3 Test B expects.
        return

    # A leaf type outside {bool, None, str, int, float} should not occur in a JSON-shaped
    # FinancialForecast.model_dump(mode="json"). Fail closed rather than silently skip it.
    _leaf(out, path, DeviationKind.STRUCTURAL, expected, actual, None, f"unrecognised leaf type {type(expected).__name__}")


def _walk(
    path: str,
    actual: Any,
    expected: Any,
    out: list[Deviation],
    float_rel_drift: dict[str, float],
    leaf_counter: list[int],
) -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            _leaf(out, path, DeviationKind.STRUCTURAL, expected, actual, None, f"expected object, got {type(actual).__name__}")
            return
        ek, ak = set(expected.keys()), set(actual.keys())
        if ek != ak:
            missing = sorted(ek - ak)
            extra = sorted(ak - ek)
            _leaf(out, path, DeviationKind.STRUCTURAL, expected, actual, None, f"key-set mismatch: missing={missing} extra={extra}")
            return
        for k in sorted(ek):
            _walk(_fmt_path(path, k), actual[k], expected[k], out, float_rel_drift, leaf_counter)
        return

    if isinstance(expected, list):
        if not isinstance(actual, list):
            _leaf(out, path, DeviationKind.STRUCTURAL, expected, actual, None, f"expected list, got {type(actual).__name__}")
            return
        if len(actual) != len(expected):
            _leaf(
                out,
                path,
                DeviationKind.STRUCTURAL,
                expected,
                actual,
                None,
                f"list length mismatch: expected {len(expected)}, got {len(actual)}",
            )
            return
        for i, (a, e) in enumerate(zip(actual, expected, strict=True)):
            _walk(_fmt_path(path, i), a, e, out, float_rel_drift, leaf_counter)
        return

    _compare_leaf(path, actual, expected, out, float_rel_drift, leaf_counter)


def compare_golden(case_id: str, actual: dict[str, Any], expected: dict[str, Any]) -> ComparisonReport:
    """
    Compare a freshly-computed ``FinancialForecast.model_dump(mode="json")`` dict (``actual``) to
    its anchored golden entry (``expected``), per the rule documented at the top of this module.

    Structural checks (key sets, list lengths, leaf types) come first and short-circuit further
    recursion into a mismatched subtree, per D.3 section 2.6.
    """
    deviations: list[Deviation] = []
    float_rel_drift: dict[str, float] = {}
    leaf_counter = [0]
    _walk("", actual, expected, deviations, float_rel_drift, leaf_counter)
    return ComparisonReport(case_id=case_id, total_leaf_count=leaf_counter[0], deviations=deviations, float_rel_drift=float_rel_drift)


# ---------------------------------------------------------------------------
# The drift ledger (D.3 section 4.3, GD.1 condition C5).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DriftLedgerEntry:
    case: str
    field_path: str
    max_rel: float
    reason: str
    mission: str
    date: str


DRIFT_LEDGER_PATH: Path = Path(__file__).resolve().parents[2] / "data" / "golden" / "DRIFT_LEDGER.json"


def load_drift_ledger(path: Path = DRIFT_LEDGER_PATH) -> dict[tuple[str, str], DriftLedgerEntry]:
    """Load ``DRIFT_LEDGER.json`` into a ``(case, field) -> DriftLedgerEntry`` lookup."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: dict[tuple[str, str], DriftLedgerEntry] = {}
    for e in raw.get("entries", []):
        key = (str(e["case"]), str(e["field"]))
        out[key] = DriftLedgerEntry(
            case=str(e["case"]),
            field_path=str(e["field"]),
            max_rel=float(e["max_rel"]),
            reason=str(e["reason"]),
            mission=str(e.get("mission", "")),
            date=str(e.get("date", "")),
        )
    return out


class LedgerStatus(str, Enum):
    COVERED = "covered"
    MISSING = "missing"
    OUT_OF_RANGE = "out_of_range"
    OVER_PROVISIONED = "over_provisioned"
    UNDERCOVERED = "undercovered"
    STALE = "stale"
    UNKNOWN_FIELD = "unknown_field"


def evaluate_ledger_entry(entry: DriftLedgerEntry | None, measured_rel_drift: float | None) -> tuple[LedgerStatus, str]:
    """
    Decide whether ``entry`` legitimately covers a currently-measured relative drift.

    ``measured_rel_drift`` is ``None`` when the entry's ``(case, field)`` does not correspond to a
    nonzero-expected float leaf in the current forecast at all (a stronger form of staleness: the
    field itself is gone, not just the drift).
    """
    if entry is None:
        return LedgerStatus.MISSING, "no DRIFT_LEDGER.json entry for this (case, field)"

    # Out-of-range: rejected regardless of what is currently measured. GD.1 condition C5.
    if entry.max_rel >= REL_TOL:
        return (
            LedgerStatus.OUT_OF_RANGE,
            f"ledger max_rel {entry.max_rel:.4e} >= REL_TOL {REL_TOL:.1e} -- an in-tolerance ledger cannot record an out-of-tolerance value",
        )

    if measured_rel_drift is None:
        return (
            LedgerStatus.UNKNOWN_FIELD,
            "ledger entry references a field path that is not currently a nonzero-expected float leaf; remove it",
        )

    if measured_rel_drift < APPROACHING_LO:
        return (
            LedgerStatus.STALE,
            f"measured drift {measured_rel_drift:.4e} has fallen below the approaching-tolerance floor "
            f"{APPROACHING_LO:.4e} -- this ledger entry no longer applies; remove it",
        )

    # Over-provisioned: rejected if the recorded budget pre-authorizes more than 10% headroom
    # above what is actually happening today. GD.1 condition C5.
    if entry.max_rel > measured_rel_drift * (1.0 + LEDGER_OVER_PROVISION_FACTOR):
        return (
            LedgerStatus.OVER_PROVISIONED,
            f"ledger max_rel {entry.max_rel:.4e} is more than {LEDGER_OVER_PROVISION_FACTOR:.0%} above the "
            f"currently-measured drift {measured_rel_drift:.4e} -- this pre-authorizes future growth; "
            "tighten max_rel to the measured value",
        )

    if measured_rel_drift > entry.max_rel:
        return (
            LedgerStatus.UNDERCOVERED,
            f"measured drift {measured_rel_drift:.4e} exceeds the ledger's recorded max_rel "
            f"{entry.max_rel:.4e} -- the entry no longer covers this drift; write a fresh entry with "
            "the new measured value and a fresh justification",
        )

    return LedgerStatus.COVERED, f"covered (max_rel={entry.max_rel:.4e}, measured={measured_rel_drift:.4e})"


def validate_drift_ledger(
    reports_by_case: dict[str, ComparisonReport],
    ledger: dict[tuple[str, str], DriftLedgerEntry],
) -> list[str]:
    """
    Validate every entry in ``ledger`` against the freshly-measured drift in ``reports_by_case``.

    Returns one human-readable problem string per invalid entry (empty list = ledger is clean).
    This is checked independently of whether a given (case, field) currently produces an
    APPROACHING deviation, because a STALE entry (drift has fallen back below the band, or the
    field no longer exists as a nonzero-expected float) would otherwise never be re-examined.
    """
    problems: list[str] = []
    for (case_id, path), entry in sorted(ledger.items()):
        report = reports_by_case.get(case_id)
        if report is None:
            problems.append(f"{case_id}/{path}: ledger entry references a case not present in this run's report set")
            continue
        measured = report.float_rel_drift.get(path)
        status, detail = evaluate_ledger_entry(entry, measured)
        if status is not LedgerStatus.COVERED:
            problems.append(f"{case_id}/{path}: {status.value.upper()} -- {detail}")
    return problems


# ---------------------------------------------------------------------------
# Failure-message rendering (D.3 section 4.4 / 4.5).
# ---------------------------------------------------------------------------


def _fmt_number(x: Any) -> str:
    if isinstance(x, float):
        return repr(x)
    return str(x)


def render_case_result(
    report: ComparisonReport,
    ledger: dict[tuple[str, str], DriftLedgerEntry],
) -> tuple[bool, str]:
    """
    Decide PASS/FAIL for one case's ``ComparisonReport`` and render the failure message if FAIL.

    Hard failures (structural, exact-mismatch, zero-violation, exceeds-tolerance) always fail the
    build. APPROACHING deviations fail the build UNLESS a DRIFT_LEDGER.json entry legitimately
    covers them (``evaluate_ledger_entry`` -> ``LedgerStatus.COVERED``).
    """
    hard = report.hard_failures
    unresolved: list[tuple[Deviation, LedgerStatus, str]] = []
    covered: list[tuple[Deviation, str]] = []
    for dev in report.approaching:
        entry = ledger.get((report.case_id, dev.path))
        status, detail = evaluate_ledger_entry(entry, dev.rel_drift)
        if status is LedgerStatus.COVERED:
            covered.append((dev, detail))
        else:
            unresolved.append((dev, status, detail))

    if not hard and not unresolved:
        return True, ""

    lines: list[str] = [f"GOLDEN DRIFT -- case '{report.case_id}'", ""]

    ranked = sorted(hard, key=lambda d: (d.rel_drift is None, -(d.rel_drift or 0.0)))
    if ranked:
        lines.append(f"  {len(ranked)} field(s) exceed tolerance or fail structurally (worst {min(10, len(ranked))} shown):")
        for d in ranked[:10]:
            drift_str = f"{d.rel_drift:.4e} relative" if d.rel_drift is not None else "n/a"
            lines.append(
                f"    [{d.kind.value}] {d.path}: anchored={_fmt_number(d.expected)} computed={_fmt_number(d.actual)} drift={drift_str}"
            )
            lines.append(f"        {d.detail}")
        lines.append("")
        lines.append("  EXCEEDS TOLERANCE -- this is a finding, not a chore. The number this product ships moved.")
        lines.append("")

    if unresolved:
        lines.append(f"  {len(unresolved)} field(s) APPROACHING TOLERANCE, unjustified or invalidly ledgered:")
        for d, status, detail in sorted(unresolved, key=lambda t: -(t[0].rel_drift or 0.0)):
            lines.append(
                f"    case: {report.case_id}\n"
                f"    field: {d.path}\n"
                f"    anchored: {_fmt_number(d.expected)}\n"
                f"    computed: {_fmt_number(d.actual)}\n"
                f"    drift: {d.rel_drift:.4e} relative ({d.rel_drift / REL_TOL:.0%} of the {REL_TOL:.2e} tolerance)\n"
                f"    band: [{APPROACHING_LO:.2e}, {REL_TOL:.2e}) -> written justification required\n"
                f"    ledger status: {status.value} -- {detail}\n"
                "    This is well above the measured floating-point reordering noise floor "
                "(1.15e-13). It is therefore NOT reordering: something in the arithmetic changed.\n"
                "    To proceed, add (or correct) an entry in tests/data/golden/DRIFT_LEDGER.json:\n"
                f'      {{"case": "{report.case_id}", "field": "{d.path}",\n'
                f'       "max_rel": {d.rel_drift:.4e}, "reason": "<why this drift is legitimate>",\n'
                '       "mission": "5", "date": "YYYY-MM-DD"}\n'
                "\n"
                "    DO NOT REGENERATE THE GOLDEN. In-tolerance drift is never a reason to re-anchor.\n"
                "    See docs/plans/mission-5-discovery/D3_tolerance_rule.md section 3."
            )
        lines.append("")

    if covered:
        lines.append(f"  ({len(covered)} approaching-tolerance field(s) covered by DRIFT_LEDGER.json and passing)")

    return False, "\n".join(lines)


# ---------------------------------------------------------------------------
# The anchor (D.3 section 3): digesting the `cases` subtree canonically, and walking the
# `supersedes` chain to enforce the cumulative-drift budget (GD.1 condition C2, MANDATORY).
# ---------------------------------------------------------------------------

ANCHOR_PATH: Path = Path(__file__).resolve().parents[2] / "data" / "golden" / "ANCHOR.json"


def canonical_cases_digest(cases: dict[str, Any]) -> str:
    """
    SHA-256 of the ``cases`` subtree, canonicalised (``sort_keys=True``,
    ``separators=(",", ":")``) so re-indentation is not a false alarm while any numeric change
    still is. Deliberately excludes ``_meta`` -- prose may improve freely; no digit in ``cases``
    may move without a re-anchor. D.3 section 3.3, Part 2.
    """
    blob = json.dumps(cases, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def load_anchor(path: Path = ANCHOR_PATH) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def cumulative_drift(anchor: dict[str, Any]) -> float:
    """
    Walk the ``supersedes`` chain from ``anchor`` (the current/most-recent record) back to the
    first anchor, summing each hop's ``max_rel_drift_vs_previous_anchor`` (``None`` -> 0.0, which
    is always true of the first/oldest anchor in the chain).

    This is a deliberately conservative upper bound (composing per-hop *max* drifts is not a true
    error-propagation calculation -- different hops may move different fields), per D.3 section 3.5.
    """
    total = 0.0
    node: dict[str, Any] | None = anchor
    while node is not None:
        drift = node.get("max_rel_drift_vs_previous_anchor")
        if drift is not None:
            total += float(drift)
        node = node.get("supersedes")
    return total
