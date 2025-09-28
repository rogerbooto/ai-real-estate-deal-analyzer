# tests/unit/test_rejector.py
import math

from src.market.hypotheses import generate_hypotheses
from src.market.rejector import reject_unrealistic
from tests import make_hypothesis, make_hypothesis_set, make_snapshot


def test_hard_rejections_rate_cap_and_vacancy_bounds():
    snap = make_snapshot(region="UnitTest-Region")

    bad_spread = make_hypothesis(
        # interest_rate_delta - cap_rate_delta = 0.03 - 0.00 = 0.03 > 0.02 → reject
        interest_rate_delta=0.03,
        cap_rate_delta=0.00,
        rent_delta=0.00,
        expense_growth_delta=0.00,
        vacancy_delta=0.00,
        str_viability=False,
        prior=0.5,
        rationale="bad spread",
    )
    bad_vacancy = make_hypothesis(
        # snapshot.vacancy_rate ~0.05, add 0.16 → 0.21 > 0.20 → reject
        vacancy_delta=0.16,
        interest_rate_delta=0.00,
        cap_rate_delta=0.00,
        rent_delta=0.00,
        expense_growth_delta=0.00,
        str_viability=False,
        prior=0.5,
        rationale="vacancy out of bounds",
    )
    hs = make_hypothesis_set(region=snap.region, seed=1, n=0)
    hs = type(hs)(snapshot_region=hs.snapshot_region, seed=hs.seed, items=(bad_spread, bad_vacancy))

    out = reject_unrealistic(hs, snap)
    assert len(out.items) == 0
    assert "All hypotheses rejected" in (out.notes or "")


def test_rent_vs_vacancy_rejection():
    snap = make_snapshot(region="UnitTest-Region")
    bad = make_hypothesis(
        rent_delta=0.03,  # +300 bps
        vacancy_delta=0.02,  # +200 bps > 0.015 limit when rent >= +0.03 → reject
        expense_growth_delta=0.00,
        interest_rate_delta=0.00,
        cap_rate_delta=0.00,
        str_viability=True,
        prior=1.0,
        rationale="rent up, too much vacancy",
    )
    hs = make_hypothesis_set(region=snap.region, seed=2, n=0)
    hs = type(hs)(snapshot_region=hs.snapshot_region, seed=hs.seed, items=(bad,))
    out = reject_unrealistic(hs, snap)
    assert len(out.items) == 0


def test_str_viability_flips_false_when_incoherent():
    snap = make_snapshot(region="UnitTest-Region")
    incoherent = make_hypothesis(
        # Flag says True but violates coherence: interest_rate_delta > +0.015
        interest_rate_delta=0.02,
        cap_rate_delta=0.01,
        rent_delta=0.00,
        expense_growth_delta=0.00,
        vacancy_delta=0.00,  # vacancy total OK
        str_viability=True,
        prior=1.0,
        rationale="incoherent STR",
    )
    hs = make_hypothesis_set(region=snap.region, seed=3, n=0)
    hs = type(hs)(snapshot_region=hs.snapshot_region, seed=hs.seed, items=(incoherent,))

    out = reject_unrealistic(hs, snap)
    assert len(out.items) == 1
    h = out.items[0]
    assert h.str_viability is False  # flipped to False, not rejected


def test_soft_penalty_and_renormalization():
    snap = make_snapshot(region="UnitTest-Region")
    # h_good: expense_growth_delta - rent_delta = 0.01 - 0.01 = 0.00 → no penalty
    h_good = make_hypothesis(
        rent_delta=0.01,
        expense_growth_delta=0.01,
        interest_rate_delta=0.00,
        cap_rate_delta=0.00,
        vacancy_delta=0.00,
        str_viability=True,
        prior=0.5,
        rationale="good spread",
    )
    # h_bad: 0.05 - 0.01 = 0.04 > 0.02 → 20% prior penalty
    h_bad = make_hypothesis(
        rent_delta=0.01,
        expense_growth_delta=0.05,
        interest_rate_delta=0.00,
        cap_rate_delta=0.00,
        vacancy_delta=0.00,
        str_viability=True,
        prior=0.5,
        rationale="bad spread",
    )
    hs = make_hypothesis_set(region=snap.region, seed=4, n=0)
    hs = type(hs)(snapshot_region=hs.snapshot_region, seed=hs.seed, items=(h_good, h_bad))

    out = reject_unrealistic(hs, snap)
    assert len(out.items) == 2

    # After penalty, h_bad prior < h_good prior
    good = next(h for h in out.items if h.rationale == "good spread")
    bad = next(h for h in out.items if h.rationale == "bad spread")
    assert bad.prior < good.prior

    # Sum to exactly 1.0
    assert math.isclose(sum(h.prior for h in out.items), 1.0, rel_tol=0.0, abs_tol=1e-12)


def test_integration_with_generator_invariants():
    snap = make_snapshot(region="UnitTest-Region")
    gen = generate_hypotheses(snap, seed=42)
    out = reject_unrealistic(gen, snap)

    # Survivors satisfy bounds
    for h in out.items:
        assert (h.interest_rate_delta - h.cap_rate_delta) <= 0.02 + 1e-12
        cap_total = snap.cap_rate + h.cap_rate_delta
        assert 0.03 - 1e-12 <= cap_total <= 0.12 + 1e-12
        vac_total = snap.vacancy_rate + h.vacancy_delta
        assert 0.00 - 1e-12 <= vac_total <= 0.20 + 1e-12
        if h.rent_delta >= 0.03 - 1e-12:
            assert h.vacancy_delta <= 0.015 + 1e-12

    # Priors renormalized
    assert math.isclose(sum(h.prior for h in out.items), 1.0, abs_tol=1e-12)

    # Deterministic ordering (lexicographic)
    ordered = tuple(
        sorted(
            out.items,
            key=lambda x: (x.rent_delta, x.expense_growth_delta, x.interest_rate_delta, x.cap_rate_delta, x.vacancy_delta, x.str_viability),
        )
    )
    assert out.items == ordered
