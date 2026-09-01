# src/market/rejector.py
from __future__ import annotations

from typing import Literal

from src.schemas.models import HypothesisSet, MarketHypothesis, MarketSnapshot

# ---------------------------------------------------------------------------
# Hard-rule thresholds — named ONCE, here, and imported by anything that talks about them
# (Mission 5 Gate V B2: `recourse.judge_combination`'s R2 messages used to re-state 0.02 / 0.03 /
# 0.12 as literals, so the decision and the message could drift silently; now the message layer
# imports these and drift is impossible without a diff on this block).
# ---------------------------------------------------------------------------

#: Float guard band used by every hard-rule comparison below (inclusive bounds, tolerant of
#: representation error). One constant so every rule is tolerant by exactly the same amount.
EPSILON: float = 1e-12

#: Rates vs Cap: |interest_rate_delta - cap_rate_delta| must stay within this band (two-sided).
RATES_VS_CAP_MAX_DIVERGENCE: float = 0.02

#: Cap floors/ceilings: (snapshot.cap_rate + cap_rate_delta) must stay inside [MIN, MAX].
CAP_RATE_MIN: float = 0.03
CAP_RATE_MAX: float = 0.12

#: Vacancy bounds: (snapshot.vacancy_rate + vacancy_delta) must stay inside [MIN, MAX].
VACANCY_MIN: float = 0.00
VACANCY_MAX: float = 0.20

#: Rent vs Vacancy: a rent_delta at/above the trigger requires vacancy_delta at/below the cap.
RENT_VS_VACANCY_RENT_TRIGGER: float = 0.03
RENT_VS_VACANCY_VACANCY_CAP: float = 0.015

#: The four hard-rejection rules, by name, in evaluation order. `violated_hard_rules` returns a
#: subset of these; `reject_unrealistic`'s hard-rejection pass IS `violated_hard_rules` (one
#: implementation), so "which rule fired" can never disagree with "was it rejected".
HardRule = Literal["rates_vs_cap", "cap_bounds", "vacancy_bounds", "rent_vs_vacancy"]

HARD_RULES: tuple[HardRule, ...] = ("rates_vs_cap", "cap_bounds", "vacancy_bounds", "rent_vs_vacancy")


def _rates_vs_cap_ok(interest_rate_delta: float, cap_rate_delta: float) -> bool:
    # Hard, two-sided: |interest_rate_delta - cap_rate_delta| <= RATES_VS_CAP_MAX_DIVERGENCE.
    #
    # Mission 4 Gate D fix (2026-08-29): the original one-sided `(delta - cap_delta) <= 0.02` never
    # bounded a rate CUT. A cut makes `interest_rate_delta` negative, so the expression only gets
    # MORE negative and the `<= 0.02` test passes trivially at any magnitude -- e.g. a -280 bps cut
    # with cap_rate_delta=0 satisfies `-0.028 <= 0.02` regardless of how implausible a 280 bps cut
    # is. Two independent Mission 4 agents found this hole (it is what forced recourse's
    # interest_rate lever to carry its own, separate 100 bps magnitude fallback -- see
    # `src/market/recourse.py` -- since this rejector rule alone never flagged a large cut).
    #
    # Symmetric bound closes it without moving the upper bound any previously-accepted hypothesis
    # relied on: `generate_hypotheses`' own DEFAULT_BANDS grid (`hypotheses.py`) never produces an
    # `interest_rate_delta` below -0.01, and its most negative combination against the
    # `cap_rate_delta` band (rate=-0.01, cap=+0.01 -> diff=-0.02) lands EXACTLY on the new lower
    # bound, so nothing the generator already produced is newly rejected by this change.
    return abs(interest_rate_delta - cap_rate_delta) <= RATES_VS_CAP_MAX_DIVERGENCE + EPSILON


def _cap_bounds_ok(snapshot_cap: float, cap_rate_delta: float) -> bool:
    # Hard: (snapshot.cap_rate + cap_rate_delta) in [CAP_RATE_MIN, CAP_RATE_MAX]
    cap = snapshot_cap + cap_rate_delta
    return CAP_RATE_MIN - EPSILON <= cap <= CAP_RATE_MAX + EPSILON


def _vacancy_bounds_ok(snapshot_vac: float, vacancy_delta: float) -> bool:
    # Hard: (snapshot.vacancy_rate + vacancy_delta) in [VACANCY_MIN, VACANCY_MAX]
    vac = snapshot_vac + vacancy_delta
    return VACANCY_MIN - EPSILON <= vac <= VACANCY_MAX + EPSILON


def _rent_vs_vacancy_ok(rent_delta: float, vacancy_delta: float) -> bool:
    # Hard: if rent_delta >= +RENT_VS_VACANCY_RENT_TRIGGER
    #       then vacancy_delta <= +RENT_VS_VACANCY_VACANCY_CAP
    if rent_delta >= RENT_VS_VACANCY_RENT_TRIGGER - EPSILON:
        return vacancy_delta <= RENT_VS_VACANCY_VACANCY_CAP + EPSILON
    return True


def violated_hard_rules(h: MarketHypothesis, snapshot: MarketSnapshot) -> tuple[HardRule, ...]:
    """Which of the four hard-rejection rules `h` violates, by name, in evaluation order.

    THE hard-rejection decision, as a diagnosable value: `reject_unrealistic`'s first pass keeps
    exactly the hypotheses for which this returns `()` — it delegates here, so the boolean
    decision and the named diagnosis are one implementation and cannot drift apart (Mission 5
    Gate V B2: `judge_combination` used to re-derive "which rule fired" from duplicated literals,
    reproduced only 2 of the 4 rules, and shipped an EMPTY reason tuple — a pipeline-reachable
    `ValidationError` — whenever the un-reproduced vacancy-bounds rule fired alone, which any
    deal with occupancy < 0.80 triggers via `recourse._derive_snapshot`).

    Note the rules judge the hypothesis AGAINST the snapshot: `vacancy_bounds` (and `cap_bounds`)
    can fire on a zero delta when the snapshot's own baseline sits outside the band. That is a
    fact about the deal, not the hypothesis — callers composing reasons must say so honestly.
    """
    violated: list[HardRule] = []
    if not _rates_vs_cap_ok(h.interest_rate_delta, h.cap_rate_delta):
        violated.append("rates_vs_cap")
    if not _cap_bounds_ok(snapshot.cap_rate, h.cap_rate_delta):
        violated.append("cap_bounds")
    if not _vacancy_bounds_ok(snapshot.vacancy_rate, h.vacancy_delta):
        violated.append("vacancy_bounds")
    if not _rent_vs_vacancy_ok(h.rent_delta, h.vacancy_delta):
        violated.append("rent_vs_vacancy")
    return tuple(violated)


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

    Hard rejections (exactly `violated_hard_rules` — the first pass delegates to it, so callers
    that need "which rule fired" ask that function and can never disagree with this decision):
      - Rates vs Cap: |interest_rate_delta - cap_rate_delta| <= RATES_VS_CAP_MAX_DIVERGENCE
        (two-sided; see `_rates_vs_cap_ok` for why a one-sided bound was a bug, not a design
        choice)
      - Cap floors/ceilings: (snapshot.cap_rate + cap_rate_delta) in [CAP_RATE_MIN, CAP_RATE_MAX]
      - Vacancy bounds: (snapshot.vacancy_rate + vacancy_delta) in [VACANCY_MIN, VACANCY_MAX]
      - Rent vs Vacancy: if rent_delta ≥ +RENT_VS_VACANCY_RENT_TRIGGER
        then vacancy_delta ≤ +RENT_VS_VACANCY_VACANCY_CAP

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

    # First pass: filter out hard violations (delegated to `violated_hard_rules`, THE one
    # implementation of the hard-rejection decision), and fix STR flag coherence
    for h in hset.items:
        if violated_hard_rules(h, snapshot):
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
