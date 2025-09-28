# tests/unit/test_hypotheses_generation.py
import math
import time

import pytest

from src.market.hypotheses import generate_hypotheses, prior_mass
from tests import make_snapshot


def test_default_count_and_lexicographic_ordering():
    snap = make_snapshot()
    hset = generate_hypotheses(snap, seed=42)

    # With correlations:
    # - interest_rate_delta values: [-0.01, 0.00, 0.02]
    #   * for 0.02 => cap_rate_delta restricted to >= +0.0025 -> only 0.01 survives
    #   * for others => cap has 3 values
    # - rent_delta values: [-0.01, 0.00, 0.03]
    #   * for 0.03 => vacancy top extends to 0.025 (still 3 values total)
    #
    # Count = rents(3) * expense(3) * rates(2) * cap(3) * vac(3)  +  rents(3)*expense(3)*rates(1)*cap(1)*vac(3)
    #       = 3*3*2*3*3 + 3*3*1*1*3 = 162 + 27 = 189
    assert len(hset.items) == 189

    # Check deterministic first/last elements (lexicographic by fields)
    first = hset.items[0]
    assert (first.rent_delta, first.expense_growth_delta, first.interest_rate_delta, first.cap_rate_delta, first.vacancy_delta) == (
        -0.01,
        0.00,
        -0.01,
        -0.005,
        0.00,
    )

    last = hset.items[-1]
    # For rate=+0.02, cap must be >= +0.0025 -> only +0.01 from default bands, and
    # for rent=+0.03 the extended vacancy top is +0.025
    assert (last.rent_delta, last.expense_growth_delta, last.interest_rate_delta, last.cap_rate_delta, last.vacancy_delta) == (
        0.03,
        0.03,
        0.02,
        0.01,
        0.025,
    )


def test_priors_sum_to_one_and_are_non_negative():
    snap = make_snapshot()
    hset = generate_hypotheses(snap, seed=42)

    s = prior_mass(hset)
    assert math.isclose(s, 1.0, rel_tol=0.0, abs_tol=1e-12)

    # No negative priors
    assert all(h.prior >= 0.0 for h in hset.items)

    # Joint-extremes get penalized vs a mid-grid baseline
    # Baseline mid combo (no extremes): rent=0.00, expense=0.01, rate=0.00, cap=0.00, vac=0.005
    baseline = next(
        h
        for h in hset.items
        if (h.rent_delta, h.expense_growth_delta, h.interest_rate_delta, h.cap_rate_delta, h.vacancy_delta)
        == (0.00, 0.01, 0.00, 0.00, 0.005)
    )
    # A jointly extreme combo (respecting correlations): rent=-0.01 (min), expense=0.00 (min),
    # rate=+0.02 (max) -> cap must be +0.01 (max), vacancy=+0.02 (max)
    extreme = next(
        h
        for h in hset.items
        if (h.rent_delta, h.expense_growth_delta, h.interest_rate_delta, h.cap_rate_delta, h.vacancy_delta)
        == (-0.01, 0.00, 0.02, 0.01, 0.02)
    )
    assert extreme.prior < baseline.prior


def test_correlations_enforced():
    snap = make_snapshot()
    hset = generate_hypotheses(snap, seed=42)

    # If interest_rate_delta >= +0.01 → cap_rate_delta must be >= +0.0025
    for h in hset.items:
        if h.interest_rate_delta >= 0.01:
            assert h.cap_rate_delta >= 0.0025

    # If rent_delta >= +0.02 → vacancy top should include 0.025 in the set
    vac_when_rent_high = {h.vacancy_delta for h in hset.items if h.rent_delta >= 0.02}
    assert 0.025 in vac_when_rent_high

    # When rent_delta < +0.02, vacancy should NOT include 0.025
    vac_when_rent_low = {h.vacancy_delta for h in hset.items if h.rent_delta < 0.02}
    assert 0.025 not in vac_when_rent_low


def test_str_viability_rule_of_thumb():
    # Baseline snapshot satisfies cap<=7.5% and vacancy<=8%.
    snap = make_snapshot()

    hset = generate_hypotheses(snap, seed=42)
    # Pick a low-rate-delta item (<= +0.01) -> should be STR viable (True)
    low_rate_item = next(h for h in hset.items if h.interest_rate_delta == 0.00)
    assert low_rate_item.str_viability is True

    # Pick a high-rate-delta item (>= +0.01, actually +0.02 is the only one) -> should be False
    high_rate_item = next(h for h in hset.items if h.interest_rate_delta == 0.02)
    assert high_rate_item.str_viability is False


def test_determinism_same_seed_same_output():
    snap = make_snapshot()
    a = generate_hypotheses(snap, seed=42)
    b = generate_hypotheses(snap, seed=42)

    assert len(a.items) == len(b.items)
    for x, y in zip(a.items, b.items, strict=False):
        assert (x.rent_delta, x.expense_growth_delta, x.interest_rate_delta, x.cap_rate_delta, x.vacancy_delta, x.str_viability) == (
            y.rent_delta,
            y.expense_growth_delta,
            y.interest_rate_delta,
            y.cap_rate_delta,
            y.vacancy_delta,
            y.str_viability,
        )
        assert math.isclose(x.prior, y.prior, rel_tol=0.0, abs_tol=1e-15)


@pytest.mark.timeout(1.0)
def test_performance_default_grid_under_200ms():
    snap = make_snapshot()
    t0 = time.perf_counter()
    _ = generate_hypotheses(snap, seed=42)
    dt_ms = (time.perf_counter() - t0) * 1000.0
    assert dt_ms < 200.0, f"Generation took {dt_ms:.2f} ms, expected < 200 ms"
