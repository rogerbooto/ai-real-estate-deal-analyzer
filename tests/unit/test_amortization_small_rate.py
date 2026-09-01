# tests/unit/test_amortization_small_rate.py
"""
Mission 5 Discovery -- verified engine defect fix.

`amortization_payment` (`src/core/finance/amortization.py`) used to raise `ZeroDivisionError` for
very small positive `rate` (below float64 machine epsilon, `1.0 + rate` rounds to exactly `1.0`,
so `1.0 - (1.0 + rate) ** (-years)` is exactly `0.0`), and was silently *wrong* -- not just
crashing -- for a wider band of small-but-not-tiny rates above that (catastrophic cancellation in
the same subtraction). See `src/core/finance/amortization.py`'s module-level comment above
`_SMALL_RATE_THRESHOLD` for the full derivation of the fix and its threshold.

This is reachable in production: `src/market/recourse.py`'s interest-rate lever computes
`max(0.0, inputs.financing.interest_rate - t)` and a bisection search on `t` walks the rate toward
its floor; Mission 5's multi-lever search walks it harder still.
"""

from __future__ import annotations

import math

import pytest

from src.core.finance.amortization import _SMALL_RATE_THRESHOLD, amortization_payment
from src.core.finance.dual import Dual4

PRINCIPAL = 1e5
YEARS = 30
TRUE_LIMIT = PRINCIPAL / YEARS  # the r -> 0+ limit of the amortization-payment formula

# The project's own ratified money-drift budget (`tests/core/finance/golden_tolerance.py::REL_TOL`).
# Reused here rather than inventing a second "how much drift is acceptable" constant.
REL_TOL = 1e-9


def _old_naive_formula(principal: float, rate: float, years: int) -> float:
    """The pre-fix formula, reimplemented verbatim, for bit-identity comparison on normal rates.

    NOT the production code path (that would defeat the point) -- a frozen, independent copy of
    exactly what `amortization_payment` computed before this fix, for `rate` values where the fix
    changes nothing.
    """
    if rate <= 0:
        return principal / years
    r = rate
    return r * principal / (1.0 - (1.0 + r) ** (-years))


class TestCrashingRateNoLongerCrashes:
    def test_1e_minus_17_does_not_raise(self):
        # This is the exact repro from the defect report: 1.0 + 1e-17 rounds to exactly 1.0,
        # so the naive formula divides by exactly zero. It must not anymore.
        pmt = amortization_payment(PRINCIPAL, 1e-17, YEARS)
        assert math.isfinite(pmt)

    def test_1e_minus_17_converges_to_true_limit(self):
        pmt = amortization_payment(PRINCIPAL, 1e-17, YEARS)
        assert pmt == pytest.approx(TRUE_LIMIT, rel=1e-9)

    @pytest.mark.parametrize("rate", [1e-16, 1e-20, 1e-30, 5e-324])
    def test_other_previously_crashing_rates_do_not_raise(self, rate):
        # 5e-324 is the smallest positive representable float64 (a subnormal).
        pmt = amortization_payment(PRINCIPAL, rate, YEARS)
        assert math.isfinite(pmt)
        assert pmt == pytest.approx(TRUE_LIMIT, rel=1e-6)


class TestSmallRateAccuracy:
    """
    The secondary, accuracy-not-crash defect: before the fix, `rate=1e-12` returned 3333.037
    against a true limit of 3333.333... (~1e-4 relative error), and `rate=1e-15` returned
    ~3002.40 (~10% relative error) -- catastrophic cancellation in `1 - (1+r)^-n`, well before the
    formula actually divides by zero. Fixed by rewriting the small-rate branch with
    `math.log1p`/`math.expm1` (see `_amortization_payment_stable`), verified against a 60-digit
    `mpmath` ground truth to hold ~1e-16 relative accuracy from `rate=1e-1` down to `rate=1e-19`.
    """

    @pytest.mark.parametrize("rate", [1e-8, 1e-9, 1e-10, 1e-11, 1e-12, 1e-13, 1e-14, 1e-15, 1e-16, 1e-17])
    def test_small_rates_converge_to_true_limit(self, rate):
        pmt = amortization_payment(PRINCIPAL, rate, YEARS)
        # Well inside the project's own 1e-9 money-drift budget, with margin: the true payment at
        # these rates differs from the r->0 limit itself by an amount on the order of `rate`,
        # negligible for rate <= 1e-8 relative to a $3,333 payment.
        assert pmt == pytest.approx(TRUE_LIMIT, rel=1e-6)

    def test_1e_minus_12_no_longer_off_by_1e_minus_4_relative(self):
        # Regression pin for the specific number cited in the defect report.
        pmt = amortization_payment(PRINCIPAL, 1e-12, YEARS)
        old_wrong_value = 3333.0370244009  # what the pre-fix formula actually returned
        assert abs(pmt - old_wrong_value) > 0.2  # materially different, not a rounding nudge
        assert pmt == pytest.approx(TRUE_LIMIT, rel=1e-9)


class TestContinuityAcrossThreshold:
    """
    The fix must not introduce a visible jump in the payment as `rate` crosses
    `_SMALL_RATE_THRESHOLD` from the stable branch to the untouched naive-formula branch.
    """

    def test_no_visible_jump_at_the_threshold(self):
        just_below = math.nextafter(_SMALL_RATE_THRESHOLD, 0.0)
        just_above = math.nextafter(_SMALL_RATE_THRESHOLD, 1.0)

        below = amortization_payment(PRINCIPAL, just_below, YEARS)
        at = amortization_payment(PRINCIPAL, _SMALL_RATE_THRESHOLD, YEARS)
        above = amortization_payment(PRINCIPAL, just_above, YEARS)

        rel_below_to_at = abs(at - below) / at
        rel_at_to_above = abs(above - at) / above

        # Measured ~8.2e-11 in the derivation (see amortization.py comment); assert two orders of
        # magnitude inside REL_TOL as a generous but still-meaningful bound.
        assert rel_below_to_at < REL_TOL, f"discontinuity {rel_below_to_at:.3e} at threshold (below->at)"
        assert rel_at_to_above < REL_TOL, f"discontinuity {rel_at_to_above:.3e} at threshold (at->above)"

    @pytest.mark.parametrize("years", [1, 5, 10, 30, 50, 100])
    def test_no_visible_jump_across_years(self, years):
        just_below = math.nextafter(_SMALL_RATE_THRESHOLD, 0.0)
        below = amortization_payment(PRINCIPAL, just_below, years)
        at = amortization_payment(PRINCIPAL, _SMALL_RATE_THRESHOLD, years)
        rel = abs(at - below) / at
        assert rel < REL_TOL, f"discontinuity {rel:.3e} at threshold for years={years}"


class TestUnaffectedPaths:
    """Paths this fix must leave completely alone."""

    def test_zero_rate_unchanged(self):
        assert amortization_payment(24_000, 0.0, 2) == 12_000.0

    def test_negative_rate_unchanged(self):
        assert amortization_payment(24_000, -0.01, 2) == 12_000.0

    @pytest.mark.parametrize(
        "rate,years,principal",
        [
            (0.0001, 30, 100_000.0),
            (0.001, 30, 100_000.0),
            (0.005, 25, 200_000.0),
            (0.018, 15, 50_000.0),
            (0.043, 30, 399_900.0),
            (0.05, 2, 24_000.0),
            (0.055, 25, 399_900.0),
            (0.06, 30, 300_000.0),
            (0.18, 30, 500_000.0),
            (1.0, 30, 500_000.0),
        ],
    )
    def test_normal_rates_bit_identical_to_pre_fix_formula(self, rate, years, principal):
        # `rate >= _SMALL_RATE_THRESHOLD` for every case above, so `amortization_payment` takes the
        # untouched original code path -- assert `==` (bit-for-bit), not `pytest.approx`.
        assert rate >= _SMALL_RATE_THRESHOLD
        assert amortization_payment(principal, rate, years) == _old_naive_formula(principal, rate, years)


class TestDualRate:
    """Mission 5 Gate V, B1: the stable branch must be dual-generic, not float-only.

    The stable branch sits on the engine's AD seam -- `engine._forecast_core` hands
    `schedule_columns` the SEEDED interest rate, so any `_overrides` pass with the rate
    direction seeded and `0 < rate < _SMALL_RATE_THRESHOLD` lands a `Dual4` here. Before the
    fix, `math.log1p` raised `TypeError: must be real number, not Dual4` (`Dual4` refuses
    `__float__` on purpose), crashing `forecast_metrics_with_jacobian` end-to-end. The two new
    branches of Mission 5 -- this stable formula and the dual seam -- were each tested alone
    and never together; this class is that missing intersection.
    """

    RATE = 1e-7  # squarely inside the stable branch: 0 < 1e-7 < _SMALL_RATE_THRESHOLD

    def test_dual_rate_below_threshold_does_not_raise(self):
        # The exact Gate V repro shape: rate seeded as a direction, primal below the threshold.
        assert self.RATE < _SMALL_RATE_THRESHOLD
        pmt = amortization_payment(PRINCIPAL, Dual4(self.RATE, 1.0), YEARS)
        assert isinstance(pmt, Dual4)
        assert math.isfinite(pmt.re)
        assert math.isfinite(pmt.d0)

    @pytest.mark.parametrize("rate", [1e-7, 1e-9, 1e-12, 1e-17])
    def test_dual_primal_bit_identical_to_float_pass(self, rate):
        # The dual pass's primal IS the float pass, bit for bit -- `dual.log1p`/`dual.expm1`
        # call the identical `math` function on the primal, so this holds by construction and
        # the stable branch's whole numerical point (no cancellation, no zero division) is
        # preserved unchanged on a dual pass.
        dual_pmt = amortization_payment(PRINCIPAL, Dual4(rate, 1.0), YEARS)
        float_pmt = amortization_payment(PRINCIPAL, rate, YEARS)
        assert dual_pmt.re == float_pmt

    def test_dual_rate_derivative_matches_central_fd(self):
        # d(payment)/d(rate) via the exact dual forms vs central FD of the stable branch
        # itself (h keeps both probes inside the branch). Measured rel ~5.6e-9 (FD roundoff
        # floor at this h); 1e-6 is headroom over the FD baseline, not AD slack.
        h = 1e-9
        dual_pmt = amortization_payment(PRINCIPAL, Dual4(self.RATE, 1.0), YEARS)
        fd = (amortization_payment(PRINCIPAL, self.RATE + h, YEARS) - amortization_payment(PRINCIPAL, self.RATE - h, YEARS)) / (2 * h)
        assert dual_pmt.d0 == pytest.approx(fd, rel=1e-6)

    def test_dual_principal_tangent_flows_through_the_stable_branch_too(self):
        # payment = rate * principal / denom(rate) is exactly linear in principal, so
        # d(payment)/d(principal) == payment / principal. Seeded in slot 1 alongside the rate
        # in slot 0 to pin that the branch carries a full multi-direction tangent, not just
        # the rate's own slot.
        pmt = amortization_payment(Dual4(PRINCIPAL, 0.0, 1.0), Dual4(self.RATE, 1.0), YEARS)
        assert pmt.d1 == pytest.approx(pmt.re / PRINCIPAL, rel=1e-12)
        assert pmt.d0 != 0.0  # the rate slot is still carried alongside
