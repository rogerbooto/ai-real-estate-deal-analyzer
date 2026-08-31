# tests/core/finance/test_irr_undefined_warning.py
"""
Mission 4, Gate V review: `src/core/finance/engine.py::_forecast_core` computes
``irr_10yr_val = irr(cashflows) or 0.0`` -- when the Brent solver (`irr.py`) correctly returns
``None`` because no single discount rate solves NPV=0 within its search domain, that `None` was
silently coalesced to `0.0`, indistinguishable from a genuinely-computed 0% return. A guardrail
reading that `0.0` (or a rendered thesis quoting it) had no way to tell "the IRR is exactly zero"
from "the IRR is undefined" -- see the Gate V ruling quoted in
`tests/core/finance/test_golden_forecasts.py`'s REGENERATION RECORD for 2026-08-29.

THE FIX (same file, same function, purely additive): when `irr(cashflows)` is `None`, `warnings`
gains one more fixed string -- see `_EXPECTED_WARNING` below -- alongside whatever other
guardrail warnings the engine already emits. `irr_10yr` itself, the schema, and the guardrail
logic are UNCHANGED: `irr_10yr` is still a plain, non-Optional float; a guardrail reading `0.0`
still fails on it, which is the conservative direction. Only the substitution's visibility
changed.

DELIBERATELY NOT NARROWED: the warning fires for EVERY cash-flow shape `irr()` cannot solve --
both the "all cash flows have the same sign, no root exists at any rate" shape
(`units_1_horizon_10`, a REAL, already-committed golden case -- see below) and the classic
"multiple sign changes, more than one mathematically valid root" shape (`[-100, 230, -132]`,
already pinned as `None` by `tests/core/finance/test_irr_brent_solver.py`). Treating one
undefined-IRR shape differently from another would recreate the exact inconsistency the Gate V
ruling closes.
"""

from __future__ import annotations

from src.core.finance.engine import run_financial_model
from src.core.finance.irr import irr
from src.core.reports.generator import generate_report
from src.schemas.models import FinancialInputs
from tests.core.finance.golden_cases import CASES
from tests.utils import make_minimal_forecast

_EXPECTED_WARNING = (
    "IRR undefined: no single discount rate solves NPV=0 within the search domain; " "treated as 0.00% for guardrail purposes."
)

_CASES_BY_ID = {c["id"]: c for c in CASES}


def _run(case_id: str):
    case = _CASES_BY_ID[case_id]
    fi = FinancialInputs.model_validate(case["financial_inputs"])
    return run_financial_model(fi, horizon_years=case["horizon_years"])


# ---------------------------------------------------------------------------------------------
# 1. The classic multiple-IRR shape: [-100, 230, -132] genuinely zeroes NPV at BOTH r=10% and
#    r=20% (Descartes' rule of signs: 2 sign changes -> up to 2 positive real roots), so no
#    SINGLE discount rate solves it and the domain-bounded bracket search correctly reports
#    `None` (pinned independently at the `irr()` level by
#    `test_irr_brent_solver.py::test_multiple_irr_cashflow_returns_defined_answer_not_an_arbitrary_pick`).
#    Re-asserted here, self-contained, as the fixture this module's docstring and the golden
#    REGENERATION RECORD both cite.
# ---------------------------------------------------------------------------------------------


def test_classic_multiple_irr_shape_is_undefined_not_arbitrary() -> None:
    cf = [-100.0, 230.0, -132.0]
    for r in (0.10, 0.20):
        npv = sum(a / (1.0 + r) ** t for t, a in enumerate(cf))
        assert abs(npv) < 1e-9, f"r={r} should genuinely zero NPV for this fixture"
    assert irr(cf) is None


# ---------------------------------------------------------------------------------------------
# 2. Engine integration: a REAL, already-committed golden case (`units_1_horizon_10`) has cash
#    flows that are negative in EVERY year, including the terminal year -- NPV(r) < 0 for every
#    r > -100%, so no IRR root exists at any rate, by construction (not a tolerance artifact).
#    This is the exact fixture the Gate V review's discovery turned up: the sentinel bug was
#    already live in pinned, committed reference data.
# ---------------------------------------------------------------------------------------------


def test_engine_warns_and_zeroes_irr_for_a_real_no_root_cashflow() -> None:
    forecast = _run("units_1_horizon_10")

    # Independent, golden-number-style proof the underlying cash flow truly has no root: rebuild
    # the SAME equity cash-flow sequence `_forecast_core` builds, from nothing but this module's
    # own public-field reading of the forecast (initial equity, each year's cash flow, refi
    # cash-out in the refi year, terminal equity in the final year) and confirm `irr()` -- called
    # directly, independent of the engine's own internal state -- agrees it is undefined.
    cashflows = [-forecast.purchase.acquisition_cash]
    refi_year = forecast.refi.year if forecast.refi else 0
    for idx, yr in enumerate(forecast.years, start=1):
        cf = yr.cash_flow
        if forecast.refi and idx == refi_year:
            cf += forecast.refi.cash_out
        cashflows.append(cf)
    assert all(cf < 0 for cf in cashflows), "fixture sanity check: every cash flow must be negative"
    assert irr(cashflows) is None, "fixture sanity check: this shape must have no IRR root at any rate"

    assert forecast.irr_10yr == 0.0
    assert _EXPECTED_WARNING in forecast.warnings


def test_engine_produces_no_undefined_irr_warning_for_a_well_defined_deal() -> None:
    """The sample deal's IRR (~12.29%) is well-defined -- the warning must never fire for it."""
    forecast = _run("sample_deal_36_kelly_moncton")

    assert forecast.irr_10yr != 0.0
    assert _EXPECTED_WARNING not in forecast.warnings
    assert not any(w.startswith("IRR undefined") for w in forecast.warnings)


# ---------------------------------------------------------------------------------------------
# 3. The warning must reach the rendered report, not just the model -- assert against real
#    generated Markdown, not a mocked renderer.
# ---------------------------------------------------------------------------------------------


def test_undefined_irr_warning_reaches_the_rendered_report_for_a_real_deal() -> None:
    forecast = _run("units_1_horizon_10")
    report = generate_report(None, forecast)

    assert "## Warnings" in report
    assert _EXPECTED_WARNING in report
    # It must render alongside the engine's other warnings for this deal, not instead of them.
    assert "cap-rate spread below target" in report
    assert "negative cash flow in projection" in report
    assert "cap rate below floor" in report


def test_undefined_irr_warning_renders_correctly_in_isolation() -> None:
    """A minimal, hand-built forecast (isolated from any particular engine cash-flow shape)
    with ONLY the undefined-IRR warning set still renders the Warnings section correctly --
    pins the render path itself, independent of which engine case happens to trigger it."""
    forecast = make_minimal_forecast().model_copy(update={"irr_10yr": 0.0, "warnings": [_EXPECTED_WARNING]})
    report = generate_report(None, forecast)

    assert "## Warnings" in report
    assert f"- {_EXPECTED_WARNING}" in report


def test_report_carries_no_irr_undefined_warning_for_a_well_defined_deal() -> None:
    """The sample deal DOES have other warnings (cap-rate spread, negative Y1 cash flow) --
    this asserts specifically that the NEW warning does not appear among them."""
    forecast = _run("sample_deal_36_kelly_moncton")
    report = generate_report(None, forecast)

    assert "## Warnings" in report
    assert "IRR undefined" not in report
