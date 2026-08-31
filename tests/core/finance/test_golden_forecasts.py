# tests/core/finance/test_golden_forecasts.py
"""
Golden-number regression harness for ``run_financial_model`` (Mission 4, task PV.1).

WHY: the founder has authorized vectorising `src/core/finance/engine.py` for portfolio-scale
performance. That function produces every dollar figure this product ships. This suite pins its
CURRENT, bit-exact output across a broad input matrix (`tests/core/finance/golden_cases.py`) so a
later rewrite that changes so much as one intermediate rounding step cannot land undetected.

BIT-EXACT, NOT APPROXIMATE: goldens are compared with plain `==` on the full
`FinancialForecast.model_dump(mode="json")` dict -- never `pytest.approx`. Python's `json`
module formats floats via the same shortest-round-trip algorithm as `repr()`, so a value written
to the golden file and read back reproduces the exact original double: comparing the loaded
golden dict to a freshly computed dict via `==` is a bit-exact comparison, field-by-field,
including every `YearBreakdown` row, not just the headline metrics.

If a genuinely-derived field could not be pinned exactly (e.g. it depended on wall-clock time or
non-deterministic iteration order), that would be called out explicitly here with a named,
justified tolerance. No such field exists in `FinancialForecast` today -- everything in it is a
pure function of the inputs -- so none is used.

Regenerating `tests/data/golden/finance_engine_forecasts.json` is done ONLY via
`python -m tests.core.finance.generate_golden_forecasts`, and only as a reviewed decision (see the
banner in that script and in the JSON file's `_meta` key). A PR that changes this JSON without
also changing `golden_cases.py` or `engine.py`/`irr.py`/`amortization.py` should be treated as
suspicious on sight.

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

GOLDEN_PATH = Path(__file__).resolve().parents[2] / "data" / "golden" / "finance_engine_forecasts.json"
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
def test_forecast_matches_golden_bit_exact(case_id: str, golden: dict[str, Any]) -> None:
    case = _CASES_BY_ID[case_id]
    actual = _run_case(case)
    expected = golden["cases"][case_id]["forecast"]

    # Exact structural + numeric equality: every field of FinancialForecast, every
    # YearBreakdown row, the debt schedule fields folded into each row, IRR, warnings.
    assert actual == expected, f"golden mismatch for case '{case_id}' -- run_financial_model output changed"


def test_determinism_repeated_calls_are_identical() -> None:
    """Same input, run twice in one test -> identical output (no hidden nondeterminism)."""
    for case_id in ("units_500_horizon_50", "negative_cash_flow_decline_shaped", "insight_modifiers_applied"):
        case = _CASES_BY_ID[case_id]
        first = _run_case(case)
        second = _run_case(case)
        assert first == second, f"non-deterministic output for case '{case_id}'"


# ---------------------------------------------------------------------------
# The real committed sample deal (data/sample_listings/36_kelly_moncton/inputs.json).
# Two layers of protection:
#   1. Bit-exact pin against the golden file (catches ANY change, including ones too
#      small to show up at 4-decimal rounding).
#   2. Human-verified baseline numbers at the stated precision (catches the golden
#      file itself having captured a wrong number in the first place).
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def sample_deal_forecast() -> Any:
    raw = json.loads(SAMPLE_DEAL_PATH.read_text(encoding="utf-8"))
    fi = FinancialInputs.model_validate(raw["inputs"])
    return run_financial_model(fi, horizon_years=raw["run"]["horizon"])


def test_sample_deal_matches_golden_bit_exact(golden: dict[str, Any]) -> None:
    raw = json.loads(SAMPLE_DEAL_PATH.read_text(encoding="utf-8"))
    fi = FinancialInputs.model_validate(raw["inputs"])
    actual = run_financial_model(fi, horizon_years=raw["run"]["horizon"]).model_dump(mode="json")
    expected = golden["cases"]["sample_deal_36_kelly_moncton"]["forecast"]
    assert actual == expected


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
