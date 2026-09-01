# tests/core/finance/test_jacobian.py
"""
The AD-checkpoint suite for `src/core/finance/jacobian.py` (Mission 5, IA.1a).

Pins the four properties the D.1 §3 go/no-go checkpoint names -- with them green, an optimizer
producing a wrong answer on top of this seam has nowhere to hide in the derivatives:

  (i)   PRIMAL BIT-IDENTITY: `MetricsJacobian.metrics` == `forecast_metrics(fi, ...)` on raw
        IEEE-754 bytes, across the same 34-case golden matrix `test_metrics_parity` uses.
  (ii)  DERIVATIVE CORRECTNESS: every partial vs central finite differences of the REAL engine
        (not a slice, not a formula) within measured, FD-noise-aware bands. THIS IS THE
        PROVE-THE-TEST: sabotage any Dual4 tangent rule or any engine dual path and
        `test_partials_match_central_fd_of_real_engine` goes red (demonstrated in the IA.1a
        report with a captured failure).
  (iii) NONE-PROPAGATION: IRR-undefined deals report `partials["irr_10yr"] is None` -- never
        0.0, which would silently claim "no lever can ever move IRR".
  (iv)  DETERMINISM: two calls, identical object contents, bit for bit.

BAND DISCIPLINE (D.1 §2 -- do not "fix" by loosening):
  * non-IRR rows: <= 1e-6 relative vs central FD (measured worst 1.9e-8 across three deal
    shapes; the band is FD-truncation headroom, not AD slack).
  * the IRR row: <= 1e-5 relative vs central FD of a TIGHT-tolerance (1e-13) re-root of the
    same equity cash flows (measured worst 2.7e-6). Against a default-tolerance root the FD
    baseline itself carries O(1e-4) Brent noise -- that is the resolved D.5 "1.3e-3" story --
    so the tight-tol baseline is the honest comparison, and the residual ~1e-6 is the
    documented O(tol) error the IFT inherits from the production root.
"""

from __future__ import annotations

import math
import struct
from dataclasses import fields
from typing import Any

import pytest

from src.core.finance.amortization import _SMALL_RATE_THRESHOLD
from src.core.finance.engine import (
    ForecastMetrics,
    _CoreOverrides,
    _forecast_core,
    forecast_metrics,
    precompute_income,
)
from src.core.finance.irr import irr
from src.core.finance.jacobian import (
    _METRIC_NAMES,
    MetricsJacobian,
    TangentDirection,
    forecast_metrics_with_jacobian,
)
from src.schemas.models import FinancialInputs
from tests.core.finance.golden_cases import CASE_IDS, CASES

_CASES_BY_ID: dict[str, dict[str, Any]] = {c["id"]: c for c in CASES}

#: Real-engine FD step per direction (same magnitudes D.1/D.5 validated with).
_FD_STEPS = {"rent": 1.0, "price": 50.0, "rate": 1e-5, "taxes": 5.0}

_NON_IRR_BAND = 1e-6
_IRR_BAND = 1e-5


def _bits(value: object) -> object:
    if isinstance(value, float):
        return struct.pack("<d", value)
    return value


def _fingerprint(metrics: ForecastMetrics) -> tuple[tuple[str, object], ...]:
    return tuple((f.name, _bits(getattr(metrics, f.name))) for f in fields(metrics))


def _inputs_for(case_id: str) -> tuple[FinancialInputs, int]:
    case = _CASES_BY_ID[case_id]
    return FinancialInputs.model_validate(case["financial_inputs"]), case["horizon_years"]


def _standard_directions(fi: FinancialInputs) -> list[TangentDirection]:
    """The four recourse-lever-shaped directions, in the semantics `_perturb` uses."""
    n_units = len(fi.income.units)
    return [
        TangentDirection("rent", (("income.gsi_annual", 12.0 * n_units),)),
        TangentDirection("price", (("financing.purchase_price", -1.0),)),
        TangentDirection("rate", (("financing.interest_rate", -1.0),)),
        TangentDirection("taxes", ((("opex", "taxes"), -1.0),)),
    ]


def _perturbed(fi: FinancialInputs, direction: str, h: float) -> FinancialInputs:
    """Real perturbed inputs for FD -- through the pydantic models, like any real caller."""
    if direction == "rent":
        inc = fi.income.model_copy(update={"units": [u.model_copy(update={"rent_month": u.rent_month + h}) for u in fi.income.units]})
        return fi.model_copy(update={"income": inc})
    if direction == "price":
        return fi.model_copy(update={"financing": fi.financing.model_copy(update={"purchase_price": fi.financing.purchase_price - h})})
    if direction == "rate":
        return fi.model_copy(update={"financing": fi.financing.model_copy(update={"interest_rate": fi.financing.interest_rate - h})})
    if direction == "taxes":
        return fi.model_copy(update={"opex": fi.opex.model_copy(update={"taxes": fi.opex.taxes - h})})
    raise ValueError(direction)


def _tight_irr(fi: FinancialInputs, horizon_years: int) -> float | None:
    """The production root re-solved at tol=1e-13 over the engine's own equity cash flows."""
    core = _forecast_core(fi, horizon_years=horizon_years, insights=None, precomputed_income=None, want_rows=False)
    return irr(core.equity_cash_flows, tol=1e-13)


# ---------------------------------------------------------------------------------------------
# (i) primal bit-identity across the golden matrix
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_primal_metrics_bit_identical_to_forecast_metrics(case_id: str) -> None:
    """The dual pass' primal IS the float pass, byte for byte, on every golden-matrix case.

    (The jacobian seam takes no insights -- by design -- so the reference call passes none
    either; the insights-bearing cases still contribute their input shapes.)
    """
    fi, horizon = _inputs_for(case_id)
    jac = forecast_metrics_with_jacobian(fi, _standard_directions(fi), horizon_years=horizon)
    ref = forecast_metrics(fi, horizon_years=horizon)
    assert _fingerprint(jac.metrics) == _fingerprint(ref)


# ---------------------------------------------------------------------------------------------
# (ii) partials vs central FD of the real engine -- THE prove-the-test
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case_id",
    [
        "sample_deal_36_kelly_moncton",  # the committed demo deal
        "refi_present_default_exit_cap",  # exercises the dual refi block + schedule splice
        "io_years_nonzero",  # IO-then-amortizing schedule shape
        "units_12_horizon_10",  # multi-unit roll: pins the 12*N aggregate rent seed vs a REAL perturbed roll
        "negative_cash_flow_decline_shaped",  # negative-CF branch shapes
    ],
)
def test_partials_match_central_fd_of_real_engine(case_id: str) -> None:
    fi, horizon = _inputs_for(case_id)
    jac = forecast_metrics_with_jacobian(fi, _standard_directions(fi), horizon_years=horizon)

    for j, direction in enumerate(("rent", "price", "rate", "taxes")):
        h = _FD_STEPS[direction]
        fi_p, fi_m = _perturbed(fi, direction, h), _perturbed(fi, direction, -h)
        mp, mm = forecast_metrics(fi_p, horizon_years=horizon), forecast_metrics(fi_m, horizon_years=horizon)

        for metric in _METRIC_NAMES:
            row = jac.partials[metric]
            assert row is not None, f"{case_id}: unexpected degraded row {metric}: {jac.degraded}"
            ad = row[j]
            if metric == "irr_10yr":
                rp, rm = _tight_irr(fi_p, horizon), _tight_irr(fi_m, horizon)
                assert rp is not None and rm is not None, f"{case_id}: IRR vanished under the FD step"
                fd = (rp - rm) / (2 * h)
                band = _IRR_BAND
            else:
                fd = (getattr(mp, metric) - getattr(mm, metric)) / (2 * h)
                band = _NON_IRR_BAND
            scale = max(abs(ad), abs(fd))
            if scale <= 1e-9:
                # both a true (near-)zero: e.g. cap_rate w.r.t. interest_rate
                assert abs(ad - fd) <= 1e-9, (case_id, metric, direction, ad, fd)
                continue
            rel = abs(ad - fd) / scale
            assert rel <= band, f"{case_id}: d({metric})/d({direction}) AD={ad!r} FD={fd!r} rel={rel:.3e} > {band:g}"


def test_directional_derivative_is_linear_in_seeds() -> None:
    """A combined direction's column == the same linear combination of single-seed columns
    (directional derivatives are linear in the direction; the dual tangent rules are too)."""
    fi, horizon = _inputs_for("sample_deal_36_kelly_moncton")
    singles = forecast_metrics_with_jacobian(
        fi,
        [
            TangentDirection("price", (("financing.purchase_price", 1.0),)),
            TangentDirection("rate", (("financing.interest_rate", 1.0),)),
        ],
        horizon_years=horizon,
    )
    a, b = -12_500.0, 0.0025
    combo = forecast_metrics_with_jacobian(
        fi,
        [TangentDirection("combo", (("financing.purchase_price", a), ("financing.interest_rate", b)))],
        horizon_years=horizon,
    )
    for metric in _METRIC_NAMES:
        p = singles.partial(metric, "price")
        r = singles.partial(metric, "rate")
        c = combo.partial(metric, "combo")
        assert p is not None and r is not None and c is not None
        expected = a * p + b * r
        assert c == pytest.approx(expected, rel=1e-9, abs=1e-15), metric


# ---------------------------------------------------------------------------------------------
# (iii) honest degradation: None is None, zero is zero
# ---------------------------------------------------------------------------------------------


def test_irr_undefined_reports_none_partials_not_zero() -> None:
    """`units_1_horizon_10` is the golden matrix's known IRR-undefined deal (engine coalesces
    the metric to 0.0 + warning). Its IRR row must be None with a reason -- a 0.0 row would
    silently tell a search 'no lever can ever fix IRR'."""
    fi, horizon = _inputs_for("units_1_horizon_10")
    jac = forecast_metrics_with_jacobian(fi, _standard_directions(fi), horizon_years=horizon)

    assert jac.metrics.irr_10yr == 0.0  # the engine's coalesced-0.0 contract, untouched
    assert any("IRR undefined" in w for w in jac.metrics.warnings)
    assert jac.partials["irr_10yr"] is None
    assert jac.partial("irr_10yr", "rent") is None
    assert any(d.startswith("irr_10yr:") for d in jac.degraded)
    # every OTHER row still carries real derivatives
    for metric in _METRIC_NAMES:
        if metric != "irr_10yr":
            assert jac.partials[metric] is not None, metric


def test_ift_degrades_to_none_on_ill_conditioned_root() -> None:
    """When |dNPV/dr| is cancellation noise, the IFT must refuse to divide by it: None with a
    reason, never a confident-looking garbage slope (D.1 §2's floor-check)."""
    from src.core.finance.dual import Dual4
    from src.core.finance.jacobian import _irr_partials_ift

    # dfdr = -(1*2.1*b^-2 + 2*(-1.1)*b^-3) == 0 exactly at b = 22/21; scale stays O(1).
    r_hat = 22.0 / 21.0 - 1.0
    cfs = [-1.0, Dual4(2.1, d0=1.0), Dual4(-1.1, d0=1.0)]
    row, reason = _irr_partials_ift(cfs, r_hat, 1)
    assert row is None
    assert reason is not None and "ill-conditioned" in reason


def test_ift_degrades_to_none_on_overflow_and_non_finite() -> None:
    from src.core.finance.dual import Dual4
    from src.core.finance.jacobian import _irr_partials_ift

    # discount base (1+r_hat) ~ 1e-6: base**-(t+1) overflows within ~52 periods
    cfs_overflow: list[float] = [-1.0] + [1.0] * 60
    row, reason = _irr_partials_ift(cfs_overflow, -0.999999, 1)
    assert row is None and reason is not None and "overflow" in reason

    # a nan tangent must surface as an honest None, not propagate into a partial
    cfs_nan = [-1.0, Dual4(2.0, d0=math.nan)]
    row, reason = _irr_partials_ift(cfs_nan, 0.05, 1)
    assert row is None and reason is not None and "non-finite" in reason


def test_true_zero_sensitivity_is_a_real_zero_not_none() -> None:
    """cap_rate does not depend on the interest rate (this independently re-derives the
    `_STATICALLY_HOPELESS` data-flow fact): the partial is exactly 0.0 -- present, finite,
    and NOT None -- while the same row's price partial is nonzero."""
    fi, horizon = _inputs_for("sample_deal_36_kelly_moncton")
    jac = forecast_metrics_with_jacobian(fi, _standard_directions(fi), horizon_years=horizon)
    assert jac.partial("cap_rate", "rate") == 0.0
    assert jac.partial("cap_rate", "price") != 0.0


def test_both_dscr_rows_are_carried_and_agree() -> None:
    """`purchase_dscr` and `year1_dscr` are the same engine float (documented consumer split);
    the Jacobian carries BOTH rows, identical."""
    fi, horizon = _inputs_for("sample_deal_36_kelly_moncton")
    jac = forecast_metrics_with_jacobian(fi, _standard_directions(fi), horizon_years=horizon)
    assert jac.partials["purchase_dscr"] == jac.partials["year1_dscr"]
    assert jac.metrics.purchase_dscr == jac.metrics.year1_dscr


# ---------------------------------------------------------------------------------------------
# (iv) determinism
# ---------------------------------------------------------------------------------------------


def test_two_calls_identical_bit_for_bit() -> None:
    fi, horizon = _inputs_for("sample_deal_36_kelly_moncton")
    a = forecast_metrics_with_jacobian(fi, _standard_directions(fi), horizon_years=horizon)
    b = forecast_metrics_with_jacobian(fi, _standard_directions(fi), horizon_years=horizon)
    assert _fingerprint(a.metrics) == _fingerprint(b.metrics)
    assert a.directions == b.directions
    assert a.degraded == b.degraded
    assert set(a.partials) == set(b.partials)
    for metric in a.partials:
        ra, rb = a.partials[metric], b.partials[metric]
        if ra is None or rb is None:
            assert ra is rb
        else:
            assert tuple(map(_bits, ra)) == tuple(map(_bits, rb)), metric


# ---------------------------------------------------------------------------------------------
# API contract: named access, loud misuse, read-only result
# ---------------------------------------------------------------------------------------------


def _any_jacobian() -> MetricsJacobian:
    fi, horizon = _inputs_for("units_2_horizon_10")
    return forecast_metrics_with_jacobian(fi, _standard_directions(fi), horizon_years=horizon)


def test_named_accessors_and_loud_unknowns() -> None:
    jac = _any_jacobian()
    assert jac.value("coc") == jac.metrics.coc
    assert jac.partial("coc", "price") == jac.partials["coc"][1]  # type: ignore[index]
    with pytest.raises(ValueError, match="unknown direction"):
        jac.partial("coc", "nope")
    with pytest.raises(KeyError):
        jac.partial("not_a_metric", "price")  # type: ignore[arg-type]
    with pytest.raises(KeyError):
        jac.value("not_a_metric")  # type: ignore[arg-type]


def test_partials_mapping_is_read_only() -> None:
    jac = _any_jacobian()
    with pytest.raises(TypeError):
        jac.partials["coc"] = None  # type: ignore[index]


def test_rows_are_exactly_forecast_metrics_float_fields() -> None:
    jac = _any_jacobian()
    float_fields = tuple(f.name for f in fields(ForecastMetrics) if f.type in ("float", float))
    assert tuple(jac.partials) == float_fields == _METRIC_NAMES


def test_direction_validation_is_loud() -> None:
    fi, horizon = _inputs_for("units_2_horizon_10")
    d = TangentDirection("ok", (("financing.purchase_price", 1.0),))
    with pytest.raises(ValueError, match="1..4"):
        forecast_metrics_with_jacobian(fi, [], horizon_years=horizon)
    with pytest.raises(ValueError, match="1..4"):
        forecast_metrics_with_jacobian(
            fi, [TangentDirection(f"d{i}", (("financing.purchase_price", 1.0),)) for i in range(5)], horizon_years=horizon
        )
    with pytest.raises(ValueError, match="unique"):
        forecast_metrics_with_jacobian(fi, [d, TangentDirection("ok", (("financing.interest_rate", 1.0),))], horizon_years=horizon)
    with pytest.raises(ValueError, match="no seeds"):
        forecast_metrics_with_jacobian(fi, [TangentDirection("empty", ())], horizon_years=horizon)
    with pytest.raises(ValueError, match="twice"):
        forecast_metrics_with_jacobian(
            fi,
            [TangentDirection("dup", (("financing.purchase_price", 1.0), ("financing.purchase_price", 2.0)))],
            horizon_years=horizon,
        )
    with pytest.raises(ValueError, match="unknown seed target"):
        forecast_metrics_with_jacobian(fi, [TangentDirection("bad", (("financing.llama_count", 1.0),))], horizon_years=horizon)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="unknown seed target"):
        forecast_metrics_with_jacobian(fi, [TangentDirection("bad", ((("opex", "llamas"), 1.0),))], horizon_years=horizon)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="non-finite"):
        forecast_metrics_with_jacobian(fi, [TangentDirection("inf", (("financing.purchase_price", math.inf),))], horizon_years=horizon)


def test_precomputed_income_identity_checked_and_bit_neutral() -> None:
    fi, horizon = _inputs_for("units_12_horizon_10")
    dirs = _standard_directions(fi)
    pre = precompute_income(fi.income)
    with_pre = forecast_metrics_with_jacobian(fi, dirs, horizon_years=horizon, precomputed_income=pre)
    without = forecast_metrics_with_jacobian(fi, dirs, horizon_years=horizon)
    assert _fingerprint(with_pre.metrics) == _fingerprint(without.metrics)
    assert dict(with_pre.partials) == dict(without.partials)

    stale = precompute_income(fi.income.model_copy(deep=True))  # equal values, different object
    with pytest.raises(ValueError, match="different IncomeModel"):
        forecast_metrics_with_jacobian(fi, dirs, horizon_years=horizon, precomputed_income=stale)


def test_engine_refuses_overrides_misuse() -> None:
    """The `_forecast_core` loud-fail guards (invariant 5): a dual pass can never silently
    combine with insights, a precompute, or row materialisation."""
    fi, horizon = _inputs_for("units_2_horizon_10")
    ov = _CoreOverrides(gsi_annual=1.0, goi_annual=1.0)
    with pytest.raises(ValueError, match="want_rows"):
        _forecast_core(fi, horizon_years=horizon, insights=None, precomputed_income=None, want_rows=True, _overrides=ov)
    with pytest.raises(ValueError, match="precomputed_income"):
        _forecast_core(
            fi,
            horizon_years=horizon,
            insights=None,
            precomputed_income=precompute_income(fi.income),
            want_rows=False,
            _overrides=ov,
        )
    from src.schemas.models import ListingInsights

    with pytest.raises(ValueError, match="insights"):
        _forecast_core(
            fi,
            horizon_years=horizon,
            insights=ListingInsights(),
            precomputed_income=None,
            want_rows=False,
            _overrides=ov,
        )


def test_jacobian_does_not_mutate_inputs() -> None:
    fi, horizon = _inputs_for("sample_deal_36_kelly_moncton")
    before = fi.model_dump_json()
    forecast_metrics_with_jacobian(fi, _standard_directions(fi), horizon_years=horizon)
    assert fi.model_dump_json() == before


def test_float_path_unaffected_by_jacobian_calls() -> None:
    """Calling the seam must leave the plain engine's output untouched (no shared state)."""
    fi, horizon = _inputs_for("sample_deal_36_kelly_moncton")
    ref_before = _fingerprint(forecast_metrics(fi, horizon_years=horizon))
    forecast_metrics_with_jacobian(fi, _standard_directions(fi), horizon_years=horizon)
    assert _fingerprint(forecast_metrics(fi, horizon_years=horizon)) == ref_before


# ---------------------------------------------------------------------------------------------
# Gate V B1: the dual pass through the stable small-rate amortization branch
# ---------------------------------------------------------------------------------------------


def test_sub_threshold_rate_dual_pass_walks_the_stable_amortization_branch() -> None:
    """Mission 5's stable small-rate branch and Mission 5's dual seam, TOGETHER (Gate V, B1).

    `interest_rate` in (0, `amortization._SMALL_RATE_THRESHOLD`) is schema-legal (ge=0, le=1)
    and routes `schedule_columns` -- which receives the SEEDED rate on any dual pass -- into
    `_amortization_payment_stable`. Before the fix, that branch's bare `math.log1p` raised
    `TypeError: must be real number, not Dual4` (Dual4 refuses `__float__` on purpose), so
    `forecast_metrics_with_jacobian` crashed from the public API while the float path sailed
    through. Each half had its own suite (`test_amortization_small_rate.py` all-float; this
    file with no sub-threshold rate); this test is the missing intersection, end to end.

    Bands are this file's own (`_NON_IRR_BAND`/`_IRR_BAND`); measured worst here is 1.7e-10
    non-IRR and 2.7e-9 on the IRR row (2026-08-31), so they hold with orders of headroom.
    The FD step is 1e-8, not `_FD_STEPS["rate"]`: both probes must stay inside (0, threshold)
    so FD differentiates the stable branch itself, and 1e-7 +/- 1e-5 would go negative.
    """
    sub_threshold_rate = 1e-7
    assert 0.0 < sub_threshold_rate < _SMALL_RATE_THRESHOLD
    fi, horizon = _inputs_for("sample_deal_36_kelly_moncton")
    fi = fi.model_copy(update={"financing": fi.financing.model_copy(update={"interest_rate": sub_threshold_rate})})

    # THE B1 REPRO: this call is exactly what used to raise TypeError.
    jac = forecast_metrics_with_jacobian(fi, _standard_directions(fi), horizon_years=horizon)

    # No dishonest fallback either: every row carries a real derivative at this point.
    assert jac.degraded == ()
    # Primal bit-identity holds at this rate exactly as on the golden matrix.
    assert _fingerprint(jac.metrics) == _fingerprint(forecast_metrics(fi, horizon_years=horizon))

    h = 1e-8  # keeps 1e-7 +/- h inside the stable branch AND above the schema's ge=0 floor
    fi_p, fi_m = _perturbed(fi, "rate", h), _perturbed(fi, "rate", -h)
    mp, mm = forecast_metrics(fi_p, horizon_years=horizon), forecast_metrics(fi_m, horizon_years=horizon)
    j = ("rent", "price", "rate", "taxes").index("rate")
    for metric in _METRIC_NAMES:
        row = jac.partials[metric]
        assert row is not None, f"unexpected degraded row {metric}: {jac.degraded}"
        ad = row[j]
        if metric == "irr_10yr":
            rp, rm = _tight_irr(fi_p, horizon), _tight_irr(fi_m, horizon)
            assert rp is not None and rm is not None, "IRR vanished under the FD step"
            fd = (rp - rm) / (2 * h)
            band = _IRR_BAND
        else:
            fd = (getattr(mp, metric) - getattr(mm, metric)) / (2 * h)
            band = _NON_IRR_BAND
        scale = max(abs(ad), abs(fd))
        if scale <= 1e-9:
            assert abs(ad - fd) <= 1e-9, (metric, ad, fd)
            continue
        rel = abs(ad - fd) / scale
        assert rel <= band, f"d({metric})/d(rate) AD={ad!r} FD={fd!r} rel={rel:.3e} > {band:g}"
