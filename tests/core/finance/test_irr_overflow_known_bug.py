# tests/core/finance/test_irr_overflow_known_bug.py
"""
IRR OVERFLOW FIX — regression pins (Mission 4, PV.2).

HISTORY: this file used to pin an ``OverflowError`` as a KNOWN, reproducible bug (Mission 4,
PV.1) in ``run_financial_model`` for some large-unit-count / long-horizon deals.

Root cause was ``src/core/finance/irr.py``, `(1.0 + rate) ** t` inside the Newton-Raphson `npv`.
For some cashflow shapes Newton probes a large trial `rate` before converging/aborting, and once
`(1 + rate)` is large enough, raising it to `t` (up to `horizon_years`) exceeded the float range
and CPython raised ``OverflowError: (34, 'Numerical result out of range')``. This was reachable in
shipped code: `main.py --horizon` is threaded straight through to `run_financial_model` as
`horizon_years`.

THE FIX: ``src/core/finance/irr.py`` now computes the discount base ``(1 + rate) ** t`` through a
saturating helper (``_discount_base``) that returns ``math.inf`` instead of raising when the true
value exceeds float range — the mathematically correct limit (a cash flow discounted at an
astronomically large trial rate is worth ~0 today), not an approximation. No currently-converging
IRR value changes: the helper only engages once ``(1 + rate) ** t`` would already have overflowed,
i.e. exactly the case that used to crash.

WHY THIS FILE STILL EXISTS: the crash-pinning tests below have flipped from
``pytest.raises(OverflowError)`` (PASS = bug still there) to asserting a defined, finite
``irr_10yr`` (PASS = bug is fixed). If this file goes RED again, the overflow has come back --
whether from a revert of ``irr.py`` or a regression introduced elsewhere -- and that is the
signal, not a surprise to be silently patched around.

TWO INDEPENDENT TRIGGERS, BOTH COVERED:
  (a) **Zero-rate trigger** (PV.1's own fixture): zero interest rate, thin (5%) down, no refi.
      Boundary ~4,539 units at horizon=100 for this exact fixture shape (shape-dependent).
  (b) **Realistic-rate trigger** (the orchestrator's, found independently, more concerning because
      it is a plausible real deal, not an edge case): replicate the real committed sample deal's
      `units[0]` (rent_month=1600) N times, rate 5.5%, 5% down, refi PRESENT. Crashed at 3000u and
      5000u at horizon=100 (and, confirmed while building this fix, from horizon=95 onward at
      5000u -- 95, 98, 99, 100 all crashed pre-fix); 2000u/100y was fine. The 99-year case is
      called out explicitly because 99-year ground leases are a real financial instrument, not a
      synthetic edge case.
"""

from __future__ import annotations

from src.core.finance import run_financial_model
from src.schemas.models import FinancialInputs, FinancingTerms, IncomeModel, MarketAssumptions, OperatingExpenses, RefinancePlan, UnitIncome

# ----------------------------------------------------------------------------------------------
# Trigger (a): zero interest rate, thin down payment, no refi (PV.1's fixture)
# ----------------------------------------------------------------------------------------------


def _crash_shaped_inputs(units: int) -> FinancialInputs:
    """
    A deal shape confirmed to trigger the irr.py OverflowError (pre-fix) at large unit counts and
    long horizons: zero interest rate, thin (5%) down payment, no refi. Kept deliberately separate
    from `golden_cases.py` -- this fixture exists to pin a former crash, not to be pinned as a
    golden numeric output.
    """
    units_list = [UnitIncome(rent_month=1200.0 + (10.0 * (i % 3)), other_income_month=50.0 if i % 2 == 0 else 0.0) for i in range(units)]
    return FinancialInputs(
        financing=FinancingTerms(
            purchase_price=500_000.0,
            closing_costs=10_000.0,
            down_payment_rate=0.05,
            interest_rate=0.0,
            amort_years=30,
            io_years=0,
        ),
        opex=OperatingExpenses(
            insurance=2400.0,
            taxes=6000.0,
            utilities=3600.0,
            water_sewer=1800.0,
            property_management=4800.0,
            repairs_maintenance=2400.0,
            trash=1200.0,
            landscaping=800.0,
            snow_removal=600.0,
            hoa_fees=0.0,
            reserves=1500.0,
            other=500.0,
            expense_growth=0.02,
        ),
        income=IncomeModel(units=units_list, occupancy=0.95, bad_debt_factor=0.97, rent_growth=0.03),
        refi=RefinancePlan(do_refi=False),
        market=MarketAssumptions(),
        capex_reserve_upfront=0.0,
    )


def test_formerly_crashed_5000_units_horizon_100() -> None:
    """Formerly-known-bug: used to raise OverflowError. Now must converge to a defined IRR."""
    result = run_financial_model(_crash_shaped_inputs(5000), horizon_years=100)
    assert result.irr_10yr is not None
    assert result.irr_10yr >= -1.0


def test_formerly_crashed_5000_units_horizon_99() -> None:
    """The crash boundary used to sit at horizon=99 for this fixture at 5,000 units."""
    result = run_financial_model(_crash_shaped_inputs(5000), horizon_years=99)
    assert result.irr_10yr is not None
    assert result.irr_10yr >= -1.0


def test_no_crash_5000_units_horizon_50_boundary_guard() -> None:
    """
    Regression/boundary guard: at 5,000 units the same fixture is fine through horizon=50. If a
    rewrite makes the crash appear earlier (a REGRESSION, distinct from the already-fixed bug),
    this test is what catches it.
    """
    result = run_financial_model(_crash_shaped_inputs(5000), horizon_years=50)
    assert result.irr_10yr is not None


def test_no_crash_500_units_horizon_100_boundary_guard() -> None:
    """
    Mission brief's claim, confirmed against this fixture: at 500 units, every horizon up to 100
    is fine. If a rewrite makes small-portfolio deals start crashing, this is what catches it.
    """
    result = run_financial_model(_crash_shaped_inputs(500), horizon_years=100)
    assert result.irr_10yr is not None


def test_no_crash_2000_units_horizon_100_boundary_guard() -> None:
    """A second safety-margin data point below the (former) crash boundary, at horizon=100."""
    result = run_financial_model(_crash_shaped_inputs(2000), horizon_years=100)
    assert result.irr_10yr is not None


# ----------------------------------------------------------------------------------------------
# Trigger (b): realistic-rate deal -- replicated sample-deal units[0], refi present (the
# orchestrator's fixture; NOT covered by trigger (a) above; the more concerning trigger because
# it is a plausible real deal shape, not a synthetic edge case)
# ----------------------------------------------------------------------------------------------


def _realistic_rate_inputs(units: int) -> FinancialInputs:
    """
    Replicates the real committed sample deal's `units[0]` (rent_month=1600,
    other_income_month=0) N times, keeping the sample deal's rate (5.5%), thin (5%) down payment,
    and (unlike the sample deal's own JSON) turning refi ON -- the shape confirmed to trigger the
    irr.py OverflowError (pre-fix) at 3,000 and 5,000 units at horizon=100, and at 5,000 units from
    horizon=95 onward (95, 98, 99, 100 all crashed pre-fix). 2,000 units at horizon=100 never
    crashed and is kept below as a boundary guard.
    """
    units_list = [UnitIncome(rent_month=1600.0, other_income_month=0.0) for _ in range(units)]
    return FinancialInputs(
        financing=FinancingTerms(
            purchase_price=399_900.0,
            closing_costs=10_000.0,
            down_payment_rate=0.05,
            interest_rate=0.055,
            amort_years=25,
            io_years=0,
            mortgage_insurance_rate=0.04,
        ),
        opex=OperatingExpenses(
            insurance=1026.0,
            taxes=4747.0,
            utilities=0.0,
            water_sewer=920.0,
            property_management=0.0,
            repairs_maintenance=0.0,
            trash=0.0,
            landscaping=0.0,
            snow_removal=0.0,
            hoa_fees=0.0,
            reserves=0.0,
            other=0.0,
            expense_growth=0.02,
        ),
        income=IncomeModel(units=units_list, occupancy=0.95, bad_debt_factor=0.97, rent_growth=0.03),
        refi=RefinancePlan(do_refi=True, year_to_refi=10, refi_ltv=0.8),
        market=MarketAssumptions(cap_rate_purchase=None, cap_rate_floor=0.05, cap_rate_spread_target=0.015),
        capex_reserve_upfront=0.0,
    )


def test_formerly_crashed_realistic_rate_3000_units_horizon_100() -> None:
    """Formerly-known-bug (orchestrator's trigger): used to raise OverflowError at 3,000 units."""
    result = run_financial_model(_realistic_rate_inputs(3000), horizon_years=100)
    assert result.irr_10yr is not None
    assert result.irr_10yr >= -1.0


def test_formerly_crashed_realistic_rate_5000_units_horizon_100() -> None:
    """Formerly-known-bug (orchestrator's trigger): used to raise OverflowError at 5,000 units."""
    result = run_financial_model(_realistic_rate_inputs(5000), horizon_years=100)
    assert result.irr_10yr is not None
    assert result.irr_10yr >= -1.0


def test_formerly_crashed_realistic_rate_5000_units_horizon_99() -> None:
    """
    99-year horizon, called out explicitly: 99-year ground leases are a real financial
    instrument, not a synthetic edge case, and this exact shape used to crash at horizon=99.
    """
    result = run_financial_model(_realistic_rate_inputs(5000), horizon_years=99)
    assert result.irr_10yr is not None
    assert result.irr_10yr >= -1.0


def test_formerly_crashed_realistic_rate_5000_units_horizon_95() -> None:
    """The realistic-rate crash boundary at 5,000 units used to start at horizon=95, not 100."""
    result = run_financial_model(_realistic_rate_inputs(5000), horizon_years=95)
    assert result.irr_10yr is not None
    assert result.irr_10yr >= -1.0


def test_no_crash_realistic_rate_2000_units_horizon_100_boundary_guard() -> None:
    """
    Boundary guard: 2,000 units at horizon=100 never crashed under the realistic-rate trigger. If
    a rewrite makes the crash appear at a smaller unit count, this is what catches it.
    """
    result = run_financial_model(_realistic_rate_inputs(2000), horizon_years=100)
    assert result.irr_10yr is not None
