# src/market/rejector.py
from __future__ import annotations

from src.schemas.models import HypothesisSet, MarketHypothesis, MarketSnapshot


def _rates_vs_cap_ok(interest_rate_delta: float, cap_rate_delta: float) -> bool:
    # Hard: interest_rate_delta - cap_rate_delta <= 0.02
    return (interest_rate_delta - cap_rate_delta) <= 0.02 + 1e-12


def _cap_bounds_ok(snapshot_cap: float, cap_rate_delta: float) -> bool:
    # Hard: (snapshot.cap_rate + cap_rate_delta) in [0.03, 0.12]
    cap = snapshot_cap + cap_rate_delta
    return 0.03 - 1e-12 <= cap <= 0.12 + 1e-12


def _vacancy_bounds_ok(snapshot_vac: float, vacancy_delta: float) -> bool:
    # Hard: (snapshot.vacancy_rate + vacancy_delta) in [0.00, 0.20]
    vac = snapshot_vac + vacancy_delta
    return 0.00 - 1e-12 <= vac <= 0.20 + 1e-12


def _rent_vs_vacancy_ok(rent_delta: float, vacancy_delta: float) -> bool:
    # Hard: if rent_delta ≥ +0.03 then vacancy_delta ≤ +0.015
    if rent_delta >= 0.03 - 1e-12:
        return vacancy_delta <= 0.015 + 1e-12
    return True


def _cohere_str_flag(snap: MarketSnapshot, h: MarketHypothesis) -> MarketHypothesis:
    """
    STR viability coherence (not a rejection): if flag is True, also require:
      - (snapshot.vacancy_rate + vacancy_delta) ≤ 0.12
      - interest_rate_delta ≤ +0.015
    If violated, flip str_viability to False.
    """
    if h.str_viability:
        vac_total = snap.vacancy_rate + h.vacancy_delta
        if vac_total > 0.12 + 1e-12 or h.interest_rate_delta > 0.015 + 1e-12:
            return MarketHypothesis(
                rent_delta=h.rent_delta,
                expense_growth_delta=h.expense_growth_delta,
                interest_rate_delta=h.interest_rate_delta,
                cap_rate_delta=h.cap_rate_delta,
                vacancy_delta=h.vacancy_delta,
                str_viability=False,  # flip off
                prior=h.prior,
                rationale=h.rationale,
            )
    return h


def reject_unrealistic(hset: HypothesisSet, snapshot: MarketSnapshot) -> HypothesisSet:
    """
    Enforce hard constraints (reject) and a soft prior penalty (keep but down-weight).
    Then renormalize priors and return a deterministically ordered HypothesisSet.

    Hard rejections:
      - Rates vs Cap: interest_rate_delta - cap_rate_delta <= 0.02
      - Cap floors/ceilings: (snapshot.cap_rate + cap_rate_delta) in [0.03, 0.12]
      - Vacancy bounds: (snapshot.vacancy_rate + vacancy_delta) in [0.00, 0.20]
      - Rent vs Vacancy: if rent_delta ≥ +0.03 then vacancy_delta ≤ +0.015

    STR coherence (not rejection):
      - If str_viability is True, also require:
        (snapshot.vacancy_rate + vacancy_delta) ≤ 0.12 and interest_rate_delta ≤ +0.015.
        If not, flip str_viability to False.

    Soft penalty (not rejection):
      - If (expense_growth_delta - rent_delta) > +0.02, reduce prior by 20%.

    Finally:
      - Renormalize priors to sum exactly 1.0.
      - Preserve deterministic lexicographic ordering on fields.
    """
    survivors: list[MarketHypothesis] = []

    # First pass: filter out hard violations, and fix STR flag coherence
    for h in hset.items:
        if not _rates_vs_cap_ok(h.interest_rate_delta, h.cap_rate_delta):
            continue
        if not _cap_bounds_ok(snapshot.cap_rate, h.cap_rate_delta):
            continue
        if not _vacancy_bounds_ok(snapshot.vacancy_rate, h.vacancy_delta):
            continue
        if not _rent_vs_vacancy_ok(h.rent_delta, h.vacancy_delta):
            continue

        survivors.append(_cohere_str_flag(snapshot, h))

    if not survivors:
        # If everything gets rejected, return an empty set with notes.
        return HypothesisSet(
            snapshot_region=hset.snapshot_region,
            seed=hset.seed,
            items=tuple(),
            notes="All hypotheses rejected by guardrails.",
        )

    # Second pass: apply soft prior penalty
    adjusted: list[MarketHypothesis] = []
    for h in survivors:
        penalized_prior = h.prior
        if (h.expense_growth_delta - h.rent_delta) > 0.02 + 1e-12:
            penalized_prior *= 0.8  # reduce by 20%

        adjusted.append(
            MarketHypothesis(
                rent_delta=h.rent_delta,
                expense_growth_delta=h.expense_growth_delta,
                interest_rate_delta=h.interest_rate_delta,
                cap_rate_delta=h.cap_rate_delta,
                vacancy_delta=h.vacancy_delta,
                str_viability=h.str_viability,
                prior=penalized_prior,
                rationale=h.rationale,
            )
        )

    # Renormalize priors
    total = float(sum(h.prior for h in adjusted))
    if total <= 0.0:
        # Defensive: if all priors went to 0 by penalties, distribute uniformly.
        n = len(adjusted)
        adjusted = [
            MarketHypothesis(
                rent_delta=h.rent_delta,
                expense_growth_delta=h.expense_growth_delta,
                interest_rate_delta=h.interest_rate_delta,
                cap_rate_delta=h.cap_rate_delta,
                vacancy_delta=h.vacancy_delta,
                str_viability=h.str_viability,
                prior=1.0 / n,
                rationale=h.rationale,
            )
            for h in adjusted
        ]
    else:
        adjusted = [
            MarketHypothesis(
                rent_delta=h.rent_delta,
                expense_growth_delta=h.expense_growth_delta,
                interest_rate_delta=h.interest_rate_delta,
                cap_rate_delta=h.cap_rate_delta,
                vacancy_delta=h.vacancy_delta,
                str_viability=h.str_viability,
                prior=h.prior / total,
                rationale=h.rationale,
            )
            for h in adjusted
        ]

    # Deterministic order (lexicographic on fields)
    ordered = tuple(
        sorted(
            adjusted,
            key=lambda h: (
                h.rent_delta,
                h.expense_growth_delta,
                h.interest_rate_delta,
                h.cap_rate_delta,
                h.vacancy_delta,
                h.str_viability,
            ),
        )
    )

    return HypothesisSet(
        snapshot_region=hset.snapshot_region,
        seed=hset.seed,
        items=ordered,
        notes=f"Rejector: in={len(hset.items)}, kept={len(ordered)}",
    )
