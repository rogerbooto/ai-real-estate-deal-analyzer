# tests/core/finance/test_income_shift.py
"""The aggregate-shift seam (`engine.ShiftedIncome`, Mission 5 acceleration): exactness,
tolerance, and -- above all -- that it did NOT weaken `PrecomputedIncome`'s safety invariant.

The invariant under test, verbatim from `PrecomputedIncome`: "MISUSE IS MADE IMPOSSIBLE, NOT
MERELY DISCOURAGED... a stale or mismatched precompute is a silently-wrong dollar figure -- far
worse than a slow one -- so it is a hard error, not a quiet fallback." The seam lets a
DELIBERATELY shifted aggregate through; every route by which a STALE or DOUBLE-APPLIED one
could sneak in must still be a loud ValueError, and each of those routes is pinned here.

Tolerance context (D.3 / PD.1): the shift is mathematically exact but not bit-exact against a
materialised roll (summation order differs). The golden rule is REL_TOL = 1e-9 with an
approaching-tolerance band at [5e-10, 1e-9); the drift tests below pin the measured drift a
comfortable four orders of magnitude BELOW the band floor, so the seam cannot even enter the
band, let alone the tolerance. Measured on 2026-08-31: worst 7.04e-15 at 500u/30y, 4.67e-14 at
5,000u/100y across all eight float metrics and a seven-point t grid.
"""

from __future__ import annotations

import inspect
from dataclasses import fields as dataclass_fields

import pytest
from pydantic import ValidationError as PydanticValidationError

from src.core.finance.engine import (
    _CoreOverrides,
    _forecast_core,
    forecast_metrics,
    precompute_income,
    run_financial_model,
    shift_income,
)
from src.market.recourse import _perturb
from tests.core.finance.golden_tolerance import APPROACHING_LO
from tests.perf.bench_finance_engine import build_inputs

#: Shift magnitudes for the drift grid: sub-dollar, typical asks, and absurdly large, so the
#: linearity claim is exercised across the whole plausible (and implausible) range.
_T_GRID = (0.01, 1.0, 5.0, 37.5, 123.456, 500.0, 1207.9)


def _worst_rel_drift(units: int, horizon: int) -> float:
    """Worst relative drift, shifted vs materialised, across all float metrics and `_T_GRID`."""
    fi = build_inputs(units)
    pre = precompute_income(fi.income)
    worst = 0.0
    for t in _T_GRID:
        shifted = forecast_metrics(fi, horizon_years=horizon, income_shift=shift_income(pre, rent_shift_month=t))
        materialised = forecast_metrics(_perturb(fi, "rent_per_unit_month", t, total_opex_y1=0.0), horizon_years=horizon)
        for f in dataclass_fields(shifted):
            a, b = getattr(shifted, f.name), getattr(materialised, f.name)
            if isinstance(a, float) and isinstance(b, float):
                worst = max(worst, abs(a - b) / abs(b) if b != 0.0 else (0.0 if a == b else float("inf")))
    return worst


class TestExactness:
    def test_shift_formula_is_the_documented_linearity(self) -> None:
        """gsi = base + 12*N*t and goi = gsi*occ*bdf, exactly -- the D.1 par.1a formula."""
        fi = build_inputs(97)
        pre = precompute_income(fi.income)
        t = 42.75
        s = shift_income(pre, rent_shift_month=t)
        assert s.num_units == 97
        assert s.rent_shift_month == t
        assert s.gsi_annual == pre.gsi_annual + 12.0 * 97 * t
        assert s.goi_annual == s.gsi_annual * (fi.income.occupancy or 1.0) * (fi.income.bad_debt_factor or 1.0)
        assert s.base is pre  # provenance: the shift carries WHICH precompute produced it

    def test_zero_shift_is_bit_exact_against_the_precompute_path(self) -> None:
        """t=0 must not merely be close: metric-for-metric identical to the unshifted pass."""
        fi = build_inputs(500)
        pre = precompute_income(fi.income)
        s0 = shift_income(pre, rent_shift_month=0.0)
        assert s0.gsi_annual == pre.gsi_annual
        assert s0.goi_annual == pre.goi_annual
        assert forecast_metrics(fi, horizon_years=30, income_shift=s0) == forecast_metrics(fi, horizon_years=30, precomputed_income=pre)


#: The measured worst drifts (2026-08-31, re-confirmed at Gate V: 7.03e-15 / 4.66e-14), pinned
#: with ~4x headroom for platform/libm variance. These are what keep `ShiftedIncome`'s
#: "measured worst relative drift is 7.04e-15 / 4.67e-14" docstring LIVE rather than prose:
#: the band-floor assertion alone (5e-10) would let the drift grow four orders of magnitude
#: while the docstring still claimed e-14s. If one of these trips, either a real regression
#: landed in the shift/aggregate arithmetic or the measurement genuinely moved -- re-measure,
#: update the docstring AND these pins together, and say so in the commit.
_MEASURED_DRIFT_PIN_500U = 3e-14
_MEASURED_DRIFT_PIN_5000U = 2e-13


class TestDriftStaysFarBelowTheApproachingBand:
    """The seam must pass the golden posture CLEANLY: not just under REL_TOL, but below the
    approaching band's floor entirely, at both scales that were measured -- and, tighter, it
    must stay at the MEASURED e-14 magnitude the `ShiftedIncome` docstring claims."""

    def test_500_units(self) -> None:
        worst = _worst_rel_drift(500, 30)
        assert worst < APPROACHING_LO, f"shifted-aggregate drift {worst:.3e} entered the approaching band"
        assert (
            worst < _MEASURED_DRIFT_PIN_500U
        ), f"shifted-aggregate drift {worst:.3e} grew past the measured 7.04e-15 magnitude (pin {_MEASURED_DRIFT_PIN_500U:g})"

    def test_5000_units_100y_ceiling(self) -> None:
        worst = _worst_rel_drift(5_000, 100)
        assert worst < APPROACHING_LO, f"shifted-aggregate drift {worst:.3e} entered the approaching band"
        assert (
            worst < _MEASURED_DRIFT_PIN_5000U
        ), f"shifted-aggregate drift {worst:.3e} grew past the measured 4.67e-14 magnitude (pin {_MEASURED_DRIFT_PIN_5000U:g})"


class TestInvariantIsNoWeaker:
    """Every stale/mismatched/double-applied route is still a hard error -- pinned one by one."""

    def test_shift_from_a_different_income_model_is_a_hard_error(self) -> None:
        fi_a, fi_b = build_inputs(10), build_inputs(10)
        stale = shift_income(precompute_income(fi_b.income), rent_shift_month=5.0)
        with pytest.raises(ValueError, match="different IncomeModel"):
            forecast_metrics(fi_a, horizon_years=5, income_shift=stale)

    def test_double_application_on_a_materialised_perturbation_is_a_hard_error(self) -> None:
        """A materialised rent perturbation builds a NEW IncomeModel; layering a shift on top
        would double-count the rent move -- the identity check makes that impossible."""
        fi = build_inputs(10)
        shift = shift_income(precompute_income(fi.income), rent_shift_month=5.0)
        perturbed = _perturb(fi, "rent_per_unit_month", 5.0, total_opex_y1=0.0)
        with pytest.raises(ValueError, match="different IncomeModel"):
            forecast_metrics(perturbed, horizon_years=5, income_shift=shift)

    def test_shift_alongside_precomputed_income_is_a_hard_error(self) -> None:
        fi = build_inputs(10)
        pre = precompute_income(fi.income)
        with pytest.raises(ValueError, match="cannot be combined with precomputed_income"):
            forecast_metrics(fi, horizon_years=5, precomputed_income=pre, income_shift=shift_income(pre, rent_shift_month=1.0))

    def test_in_place_units_mutation_is_a_hard_error(self) -> None:
        """Identity alone cannot see an in-place length change of the units list (same
        IncomeModel object); the belt-and-braces unit-count re-check catches it loudly.

        Since Gate V N3, `IncomeModel` is frozen, so REASSIGNING `units` raises at the schema.
        The list's own contents are still mutable -- `pop()` here is exactly the residual route
        the engine's `num_units` re-check exists for (see `ShiftedIncome`'s docstring)."""
        fi = build_inputs(10)
        shift = shift_income(precompute_income(fi.income), rent_shift_month=1.0)
        fi.income.units.pop()  # in-place: frozen=True guards fields, not the list's contents
        with pytest.raises(ValueError, match="mutated in place"):
            forecast_metrics(fi, horizon_years=5, income_shift=shift)

    def test_frozen_schema_blocks_the_field_level_mutation_routes(self) -> None:
        """Gate V N3: the routes `num_units` CANNOT see -- a unit's own rent edit, or wholesale
        `units` reassignment -- are blocked upstream by `frozen=True` on `UnitIncome` and
        `IncomeModel`. Before the freeze, `units[0].rent_month += 1000` after `shift_income`
        passed both the identity check and the count re-check and silently repriced the deal."""
        fi = build_inputs(10)
        shift_income(precompute_income(fi.income), rent_shift_month=1.0)
        with pytest.raises(PydanticValidationError, match="frozen"):
            fi.income.units[0].rent_month += 1000.0
        with pytest.raises(PydanticValidationError, match="frozen"):
            fi.income.units = list(fi.income.units[:-1])

    def test_non_finite_shift_is_a_hard_error(self) -> None:
        pre = precompute_income(build_inputs(3).income)
        with pytest.raises(ValueError, match="finite"):
            shift_income(pre, rent_shift_month=float("nan"))

    def test_run_financial_model_structurally_refuses_shifts(self) -> None:
        """SEARCH ONLY, BY CONSTRUCTION: the full/report path has no income_shift parameter at
        all, so a shifted number can never be the one shown to an investor."""
        assert "income_shift" not in inspect.signature(run_financial_model).parameters

    def test_forecast_core_refuses_shift_with_want_rows(self) -> None:
        fi = build_inputs(3)
        shift = shift_income(precompute_income(fi.income), rent_shift_month=1.0)
        with pytest.raises(ValueError, match="want_rows"):
            _forecast_core(fi, horizon_years=5, insights=None, precomputed_income=None, want_rows=True, income_shift=shift)

    def test_forecast_core_refuses_shift_alongside_overrides(self) -> None:
        """The AD seam resolves its own aggregate; two sources for the same number is exactly
        what `_CoreOverrides`' contract forbids."""
        fi = build_inputs(3)
        pre = precompute_income(fi.income)
        shift = shift_income(pre, rent_shift_month=1.0)
        overrides = _CoreOverrides(gsi_annual=pre.gsi_annual, goi_annual=pre.goi_annual)
        with pytest.raises(ValueError, match="income_shift"):
            _forecast_core(
                fi,
                horizon_years=5,
                insights=None,
                precomputed_income=None,
                want_rows=False,
                income_shift=shift,
                _overrides=overrides,
            )
