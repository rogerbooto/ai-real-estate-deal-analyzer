# tests/core/finance/test_golden_forecasts.py
"""
Golden-number regression harness for ``run_financial_model`` (Mission 4, task PV.1).

WHY: the founder has authorized vectorising `src/core/finance/engine.py` for portfolio-scale
performance, and Mission 5 authorized forward-mode (tangent-linear) differentiation, which threads dual numbers through
the same code. Both reorder floating-point arithmetic without changing the underlying math. That
function produces every dollar figure this product ships. This suite pins its output across a
broad input matrix (`tests/core/finance/golden_cases.py`) so a rewrite that changes so much as one
intermediate rounding step cannot land undetected.

============================================================================
TOLERANCE RULE -- 2026-08-31, Mission 5, IT.1 (founder-ratified via PD.1; guardian-conditioned via
GD.1, VETO LIFTED WITH CONDITIONS C1-C7; design in docs/plans/mission-5-discovery/D3_tolerance_rule.md)
============================================================================

THIS SECTION REPLACES THE FORMER "BIT-EXACT, NOT APPROXIMATE" SECTION, WHICH IS NO LONGER TRUE.
`test_forecast_matches_golden_within_tolerance` and `test_sample_deal_matches_golden_within_tolerance`
(formerly `..._bit_exact` -- renamed because a test name is a claim, and "bit_exact" became a false
one, per GD.1 condition C7) now compare via `tests/core/finance/golden_tolerance.py::compare_golden`:
a named, justified, MEASURED relative tolerance (`REL_TOL = 1e-9`), asymmetric
(`abs(actual - expected) <= REL_TOL * abs(expected)`, expected alone in the denominator), with
`abs_tol = 0` (no absolute floor, ever), exact-zero fields still required exact (652 semantic zeros
across 20 field paths), and every non-float field (`bool`, `str`, `None`, `int`) still exact `==`.
See `golden_tolerance.py`'s module docstring for the rule in full, its two measured walls (the
~1.15e-13 floating-point-reordering noise floor and the ~1.35e-5 smallest-defect-class signature),
and everything the rule does NOT permit.

WHY THIS MOVED: Mission 5's forward-mode (tangent-linear) differentiation threads dual numbers through `engine.py` /
`irr.py::_brent_root`. That reorders IEEE-754 operations -- mathematically identical, bit-different
-- so a plain `==` bit-exact comparison against a golden captured by the PRE-AD code path would fail
on every AD landing regardless of correctness. The relaxation is *cross-version* stability
(program version N+1 vs the anchored output of version N), which was always a surplus guarantee
this harness added ahead of the Mission 4 vectorisation, not the deterministic-core invariant
itself. See `test_determinism_repeated_calls_are_identical` below for the invariant that IS still
enforced at `==`, forever, and why.

ANCHORING: comparison is always against the digest-pinned `cases` subtree of this file, pinned in
`tests/data/golden/ANCHOR.json` and enforced by the dedicated `tests/core/finance/test_golden_anchor.py`
(its own file, so an anchor failure is unmistakable and distinct from a tolerance failure).
In-tolerance drift is NEVER a reason to regenerate this golden -- `generate_golden_forecasts.py`'s
safety gate refuses a numeric-only regeneration; only a reviewed `--supersede-anchor --rationale`
run can move the anchor.

APPROACHING-TOLERANCE: a relative drift in `[5e-10, 1e-9)` -- half of `REL_TOL` -- FAILS THE BUILD
unless a scoped, bounded, self-expiring entry exists in `tests/data/golden/DRIFT_LEDGER.json`. It is
not a warning; see `golden_tolerance.py::render_case_result`.

Regenerating `tests/data/golden/finance_engine_forecasts.json` is done ONLY via
`python -m tests.core.finance.generate_golden_forecasts`, and only as a reviewed decision (see the
banner in that script and in the JSON file's `_meta` key). A PR that changes this JSON without
also changing `golden_cases.py` or `engine.py`/`irr.py`/`amortization.py` should be treated as
suspicious on sight -- and, as of this Mission, without a `--supersede-anchor --rationale` run, it
cannot land at all: `test_golden_anchor.py` will fail first.

============================================================================
REGENERATION RECORD -- 2026-08-29, Mission 4, PV.5 (founder-approved on CORRECTNESS grounds, not
performance; see the mission brief and `src/core/finance/irr.py`'s module docstring)
============================================================================

`src/core/finance/irr.py` replaced an unbracketed Newton-Raphson-first solver (correctness
dependent on a hardcoded `r = 0.10` starting guess -- see git history) with a domain-bounded
bracket search + Brent's method (`irr.py::_brent_root`), which cannot return a root outside the
bracket it is given. This regeneration is the one sanctioned side effect of that fix: the two
solvers do not follow identical floating-point paths to the same root, so `irr_10yr` moved by a
tiny amount in every case whose answer wasn't already exact.

Full before/after diff, `irr_10yr` only, all 34 cases (`before` = pre-PV.5 Newton-first solver,
`after` = post-PV.5 Brent solver; `units_1_horizon_10` is the one case that did not move at all):

| case_id | before | after | abs diff |
|---|---|---|---|
| all_cash_deal | 0.07280755207834827 | 0.07280749733910234 | 5.47e-08 |
| amort_years_short | 0.10000804745550437 | 0.10000805116881042 | 3.71e-09 |
| amort_years_zero_io_only | 0.12569499253395203 | 0.1256948356655459 | 1.57e-07 |
| bad_debt_stress | 0.05678167714115953 | 0.056781871884428244 | 1.95e-07 |
| cap_rate_drift_nonzero | 0.029480619956122892 | 0.02948062007366046 | 1.18e-10 |
| cap_rate_floor_breach | 0.11532646845432397 | 0.11532648488549334 | 1.64e-08 |
| cap_rate_purchase_set_explicit | 0.06824441168939613 | 0.06824435742553231 | 5.43e-08 |
| cap_rate_purchase_unset | 0.11532646845432397 | 0.11532648488549334 | 1.64e-08 |
| down_payment_above_mip_trigger | 0.09645423135035393 | 0.09645423396932253 | 2.62e-09 |
| down_payment_at_mip_boundary | 0.11532646845432397 | 0.11532648488549334 | 1.64e-08 |
| down_payment_below_mip_trigger | 0.12361403212273418 | 0.12361407560562299 | 4.35e-08 |
| horizon_1 | 0.054814181818181935 | 0.05481419553550639 | 1.37e-08 |
| horizon_30 | 1.0440965047449926 | 1.0440964963496964 | 8.40e-09 |
| horizon_5 | 1.0459589504775422 | 1.0459589516426375 | 1.17e-09 |
| horizon_50 | 1.044096501916153 | 1.0440964935172514 | 8.40e-09 |
| insight_modifiers_applied | 0.13512024644099777 | 0.13512024763948105 | 1.20e-09 |
| interest_rate_high | -0.1994336827902395 | -0.19943347851510493 | 2.04e-07 |
| interest_rate_zero | 0.2277438241355518 | 0.2277438816597224 | 5.75e-08 |
| io_years_nonzero | 0.12301277917440263 | 0.12301277996105371 | 7.87e-10 |
| io_years_zero | 0.11532646845432397 | 0.11532648488549334 | 1.64e-08 |
| negative_cash_flow_decline_shaped | 0.12631993061036784 | 0.126319969732744 | 3.91e-08 |
| opex_sparse_like_sample_deal | 0.0586937173660657 | 0.05869371733842156 | 2.76e-11 |
| refi_absent | 0.11532646845432397 | 0.11532648488549334 | 1.64e-08 |
| refi_present_default_exit_cap | 0.12700976230059388 | 0.12700973316105954 | 2.91e-08 |
| refi_present_explicit_exit_cap | 0.12090843090375251 | 0.12090860745997326 | 1.77e-07 |
| sample_deal_36_kelly_moncton | 0.12293592888259555 | 0.12293597051187492 | 4.16e-08 |
| spread_below_target | 0.11532646845432397 | 0.11532648488549334 | 1.64e-08 |
| units_12_horizon_10 | 1.0443918694210403 | 1.0443918494049107 | 2.00e-08 |
| units_1_horizon_10 | (unchanged) | (unchanged) | 0 |
| units_2_horizon_10 | 0.16170832216813477 | 0.1617083221658672 | 2.27e-12 |
| units_500_horizon_10 | 0.44679988764731604 | 0.44679988762886014 | 1.85e-11 |
| units_500_horizon_50 | 0.4433676154480451 | 0.44336762004726876 | 4.60e-09 |
| units_50_horizon_10 | 5.753067018492552 | 5.753067018899706 | 4.07e-10 |
| vacancy_high | 0.06188849794401067 | 0.06188850215779614 | 4.21e-09 |

Sanity-checked before regenerating: every field EXCEPT `irr_10yr` was `==` before/after in every
one of the 34 cases -- confirmed programmatically by flattening and diffing the full
`FinancialForecast.model_dump(mode="json")` dict per case, not eyeballed. The largest movement
(2.04e-7, `interest_rate_high`) is still ~5x smaller than this harness's own `1e-6` tolerance
philosophy and three orders of magnitude below the `tol=1e-6` the solver itself is asked to
converge to -- consistent with "two different root-finders converging to the same true root via
different floating-point paths," not a bug.

============================================================================
REGENERATION RECORD -- 2026-08-29, Mission 4, Gate V review (founder-approved: "Option 1 --
apply the fix and regenerate that single golden case")
============================================================================

THE BUG THIS REGENERATION FIXES VISIBILITY FOR: `src/core/finance/engine.py::_forecast_core`
computes `irr_10yr_val = irr(cashflows) or 0.0` -- when the Brent solver above (PV.5) correctly
returns `None` because no single discount rate solves NPV=0 in its search domain, that `None` was
silently coalesced to `0.0`, indistinguishable downstream from a genuinely-computed 0% return. A
guardrail or a rendered thesis reading that `0.0` had no way to tell "the IRR is exactly zero"
from "the IRR is undefined." The fix (same file, same function) is purely additive: when
`irr(cashflows)` is `None`, `warnings` gains one more fixed string --
`"IRR undefined: no single discount rate solves NPV=0 within the search domain; treated as 0.00%
for guardrail purposes."` -- alongside the existing `"cap-rate spread below target"` /
`"negative cash flow in projection"` / `"cap rate below floor"` warnings this suite already pins.
`irr_10yr` itself is UNCHANGED (still `0.0` for this case, still Optional-free per the schema, per
the founder's explicit ruling that made-Optional was out of scope) -- only its visibility changed.

WHY THIS MOVED A GOLDEN CASE, AND WHY THAT IS THE POINT, NOT A REGRESSION: while implementing this
fix (see the finance-engineer's discovery, prior to this record), it was found that
`units_1_horizon_10` -- already committed, already pinned, already passing bit-exact every prior
regeneration including the PV.5 Brent swap above (it is explicitly called out there as "the one
case that did not move at all") -- has cash flows that are NEGATIVE IN EVERY YEAR, including the
terminal year (`[-110000, -39549.66, -39651.98, ..., -40380.07]`, see
`tests/core/finance/golden_cases.py`). NPV(r) is strictly negative for every r > -100%: there is
no IRR root at any rate, by construction, not by tolerance or solver quirk. `irr()` has always
correctly returned `None` for this case; the engine has always silently reported `irr_10yr = 0.0`
for it. That is the guardian's concern realised, already, in a committed golden fixture -- not a
hypothetical. This regeneration turns that fixture into the regression test for the bug: before
this record, `units_1_horizon_10` had 3 warnings; after, it has 4, the 4th being the one above.

Full before/after diff for THIS regeneration, confirmed programmatically (flatten + diff every
field of `FinancialForecast.model_dump(mode="json")` for all 34 cases, not eyeballed):
  - Cases changed: exactly 1 (`units_1_horizon_10`). The other 33: byte-identical.
  - Fields changed within that case: exactly 1 (`warnings`, one entry appended).
  - Numeric fields moved: NONE, in any case -- `irr_10yr`, `equity_multiple_10yr`, every
    `YearBreakdown` row (including `dscr`, `noi`, `cash_flow`, `ending_balance`) are bit-identical
    before/after for all 34 cases.
  - `python main.py` (the committed sample deal) sha256 unchanged:
    `e6451c9af19e491a14495e9055501fff44034040552317325e539ab42b9f9ee9` (its IRR, ~12.29%, is
    well-defined, so the new warning never fires for it).

See `tests/core/finance/test_irr_undefined_warning.py` for the unit coverage (the classic
`[-100, 230, -132]` two-sign-change undefined-IRR shape, a normal well-defined deal producing no
such warning, and the warning reaching the rendered Markdown report) and
`src/core/finance/engine.py::_forecast_core` for the fix itself and its inline rationale.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.core.finance import run_financial_model
from src.schemas.models import FinancialInputs, ListingInsights
from tests.core.finance.golden_cases import CASE_IDS, CASES
from tests.core.finance.golden_tolerance import (
    GOLDEN_PATH,
    compare_golden,
    load_drift_ledger,
    render_case_result,
)

SAMPLE_DEAL_PATH = Path(__file__).resolve().parents[3] / "data" / "sample_listings" / "36_kelly_moncton" / "inputs.json"

_CASES_BY_ID: dict[str, dict[str, Any]] = {c["id"]: c for c in CASES}


@pytest.fixture(scope="module")
def golden() -> dict[str, Any]:
    with GOLDEN_PATH.open("r", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return data


def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    fi = FinancialInputs.model_validate(case["financial_inputs"])
    insights = ListingInsights.model_validate(case["insights"]) if case.get("insights") else None
    forecast = run_financial_model(fi, horizon_years=case["horizon_years"], insights=insights)
    return forecast.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Sanity: the golden file actually covers the matrix we think it does. This
# guards against a stale golden file being left behind after golden_cases.py
# grows (the file would silently be missing coverage for new cases without
# this check turning RED).
# ---------------------------------------------------------------------------


def test_golden_file_covers_every_defined_case(golden: dict[str, Any]) -> None:
    assert set(golden["cases"].keys()) == set(CASE_IDS)


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_forecast_matches_golden_within_tolerance(case_id: str, golden: dict[str, Any]) -> None:
    """
    Renamed from ``test_forecast_matches_golden_bit_exact`` (GD.1 condition C7 -- a test name is a
    claim, and "bit_exact" would be a false one under the tolerance rule). See the module
    docstring's "TOLERANCE RULE" record and ``tests/core/finance/golden_tolerance.py`` for the rule
    itself: structural equality first, then every non-float field exact, every exact-zero field
    exact, and every other float field within ``REL_TOL = 1e-9`` relative of the anchored golden.
    """
    case = _CASES_BY_ID[case_id]
    actual = _run_case(case)
    expected = golden["cases"][case_id]["forecast"]

    report = compare_golden(case_id, actual, expected)
    ledger = load_drift_ledger()
    ok, message = render_case_result(report, ledger)
    assert ok, message


def test_determinism_repeated_calls_are_identical() -> None:
    """
    Same input, run twice in one test -> identical output (no hidden nondeterminism).

    EXCLUDED FROM THE MISSION 5 TOLERANCE RULE, DELIBERATELY (GD.1 condition C1; D.3 section 6.2).
    This compares two runs of the SAME code, on the SAME inputs, in the SAME process. IEEE-754
    arithmetic is deterministic: an identical sequence of operations on identical operands produces
    an identical result, always -- there is no reordering across this boundary (unlike the
    cross-version comparison in ``test_forecast_matches_golden_within_tolerance`` above, where a
    later code version may legitimately reassociate floating-point operations). This test exists to
    catch hidden nondeterminism -- dict/set iteration order leaking into a sum, hash()
    randomisation, wall-clock dependence, uninitialised state -- and those bugs characteristically
    manifest as TINY differences. A tolerance here would hide exactly the class of bug this test
    exists to find; it would not be a weakening of the harness, it would be a deletion of the
    harness's most load-bearing assertion, disguised as consistency. Stays ``==``, forever. Any
    future request to relax this assertion is an automatic escalation to the Founder Proxy, citing
    docs/plans/mission-5-discovery/GD1_veto_review.md condition C1.
    """
    for case_id in ("units_500_horizon_50", "negative_cash_flow_decline_shaped", "insight_modifiers_applied"):
        case = _CASES_BY_ID[case_id]
        first = _run_case(case)
        second = _run_case(case)
        assert first == second, f"non-deterministic output for case '{case_id}'"


# ---------------------------------------------------------------------------
# The real committed sample deal (data/sample_listings/36_kelly_moncton/inputs.json).
# Two layers of protection:
#   1. Within-tolerance pin against the golden file (catches ANY change past REL_TOL, including
#      ones far too small to show up at 4-decimal rounding).
#   2. Human-verified baseline numbers at the stated precision (catches the golden
#      file itself having captured a wrong number in the first place) -- STAYS AS-IS, untouched by
#      the tolerance rule (GD.1 condition C1; D.3 section 6.2: at dscr ~ 0.896, four-decimal
#      rounding is already a ~5.6e-5 relative assertion, four to five orders looser than REL_TOL,
#      so applying the tolerance rule there would be strictly weaker than what it already asserts).
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def sample_deal_forecast() -> Any:
    raw = json.loads(SAMPLE_DEAL_PATH.read_text(encoding="utf-8"))
    fi = FinancialInputs.model_validate(raw["inputs"])
    return run_financial_model(fi, horizon_years=raw["run"]["horizon"])


def test_sample_deal_matches_golden_within_tolerance(golden: dict[str, Any]) -> None:
    """Renamed from ``test_sample_deal_matches_golden_bit_exact`` -- same rule, same rename, same
    reasoning as ``test_forecast_matches_golden_within_tolerance`` above (GD.1 condition C7),
    narrowed to the shipped `36_kelly_moncton` deal."""
    raw = json.loads(SAMPLE_DEAL_PATH.read_text(encoding="utf-8"))
    fi = FinancialInputs.model_validate(raw["inputs"])
    actual = run_financial_model(fi, horizon_years=raw["run"]["horizon"]).model_dump(mode="json")
    expected = golden["cases"]["sample_deal_36_kelly_moncton"]["forecast"]

    report = compare_golden("sample_deal_36_kelly_moncton", actual, expected)
    ledger = load_drift_ledger()
    ok, message = render_case_result(report, ledger)
    assert ok, message


def test_sample_deal_verified_baseline_numbers(sample_deal_forecast: Any) -> None:
    """
    Independently-verified baseline (see Mission 4 PV.1 brief):
      DSCR 0.8960, CoC -6.4066%, Y1 cash flow -$2,946.47, cap rate 6.3454%, spread 0.8454%.
    """
    f = sample_deal_forecast
    assert round(f.purchase.dscr, 4) == 0.8960
    assert round(f.purchase.coc * 100.0, 4) == -6.4066
    assert round(f.years[0].cash_flow, 2) == -2946.47
    assert round(f.purchase.cap_rate * 100.0, 4) == 6.3454
    assert round(f.purchase.spread_vs_rate * 100.0, 4) == 0.8454
    # This is the committed DECLINE-shaped deal: negative Y1 cash flow, negative CoC.
    assert f.purchase.coc < 0.0
    assert f.years[0].cash_flow < 0.0
    assert "negative cash flow in projection" in f.warnings
