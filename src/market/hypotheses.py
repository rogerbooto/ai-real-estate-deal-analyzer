# src/market/hypotheses.py

from __future__ import annotations

from src.schemas.models import HypothesisSet, MarketHypothesis, MarketSnapshot

# Fixed field order for deterministic grids and sorting
_ORDER: tuple[str, ...] = (
    "rent_delta",
    "expense_growth_delta",
    "interest_rate_delta",
    "cap_rate_delta",
    "vacancy_delta",
)

# Default bands (min, base, max) in absolute percentage points (e.g., 0.02 == +200 bps)
DEFAULT_BANDS: dict[str, tuple[float, float, float]] = {
    "rent_delta": (-0.01, 0.00, 0.03),
    "expense_growth_delta": (0.00, 0.01, 0.03),
    "interest_rate_delta": (-0.01, 0.00, 0.02),
    "cap_rate_delta": (-0.005, 0.00, 0.01),
    "vacancy_delta": (0.00, 0.005, 0.02),
}

# Default grid steps (all 3 = min/base/max)
DEFAULT_GRID_STEPS: dict[str, int] = {k: 3 for k in _ORDER}


def _grid_values(band: tuple[float, float, float], steps: int) -> list[float]:
    """
    Deterministic values per axis. For steps==3, we return [min, base, max].
    (Hook left here if extended to 5/7 point grids later.)
    """
    if steps != 3:
        raise ValueError("Only 3-step grids are supported in Milestone B (min/base/max).")
    lo, mid, hi = band
    if not (lo <= mid <= hi):
        raise ValueError(f"Invalid band ordering: {(lo, mid, hi)}")
    return [lo, mid, hi]


def _is_extreme(value: float, band: tuple[float, float, float], tol: float = 1e-12) -> bool:
    lo, _, hi = band
    return abs(value - lo) <= tol or abs(value - hi) <= tol


def _bucket(x: float) -> str:
    if x > 0:
        return "up"
    if x < 0:
        return "down"
    return "flat"


def _rationale(rd: float, ed: float, ir: float, cr: float, vd: float, str_ok: bool) -> str:
    base = f"Rent { _bucket(rd) }, Opex { _bucket(ed) }, Rates { _bucket(ir) }, " f"Cap { _bucket(cr) }, Vac { _bucket(vd) }"
    if str_ok:
        return base + "; STR viable due to low cap & vacancy."
    return base + "; STR less attractive (rates/vacancy)."


def generate_hypotheses(
    snapshot: MarketSnapshot,
    *,
    seed: int = 42,  # kept for future tie-breaking / stable randomization if needed
    bands: dict[str, tuple[float, float, float]] | None = None,
    grid_steps: dict[str, int] | None = None,
) -> HypothesisSet:
    """
    Deterministically build a small Cartesian grid of market deltas, apply simple correlations,
    compute priors with joint-extremes penalty, and return an immutable HypothesisSet.

    Correlations enforced at generation-time:
      - If interest_rate_delta >= +0.01 → cap_rate_delta must be >= +0.0025.
      - If rent_delta >= +0.02 → extend the vacancy_delta top value by +0.005 (capped at +0.025),
        keeping exactly 3 grid values.
    """
    b = dict(DEFAULT_BANDS if bands is None else bands)
    gs = dict(DEFAULT_GRID_STEPS if grid_steps is None else grid_steps)

    # Precompute axis values (vacancy handled specially when rent interacts)
    axis_vals: dict[str, list[float]] = {}
    for key in _ORDER:
        axis_vals[key] = _grid_values(b[key], gs[key])

    # Build combinations with correlations
    combos: list[tuple[float, float, float, float, float]] = []
    rent_vals = axis_vals["rent_delta"]
    expense_vals = axis_vals["expense_growth_delta"]
    rate_vals = axis_vals["interest_rate_delta"]
    cap_vals_base = axis_vals["cap_rate_delta"]
    vac_band = b["vacancy_delta"]

    for rent_delta in rent_vals:
        # Correlation: extend permissible vacancy top by up to +0.005 (cap at 0.025)
        if rent_delta >= 0.02:
            lo, mid, hi = vac_band
            hi_ext = min(0.025, hi + 0.005)
            vacancy_values = [lo, mid, hi_ext]
        else:
            vacancy_values = axis_vals["vacancy_delta"]

        for expense_growth_delta in expense_vals:
            for interest_rate_delta in rate_vals:
                # Correlation: high rates require cap expansion >= +0.0025
                if interest_rate_delta >= 0.01:
                    cap_values = [v for v in cap_vals_base if v >= 0.0025]
                    if not cap_values:
                        # If all cap deltas are below threshold, skip row entirely
                        continue
                else:
                    cap_values = cap_vals_base

                for cap_rate_delta in cap_values:
                    for vacancy_delta in vacancy_values:
                        combos.append(
                            (
                                rent_delta,
                                expense_growth_delta,
                                interest_rate_delta,
                                cap_rate_delta,
                                vacancy_delta,
                            )
                        )

    # Compute raw weights (priors before normalization) with joint-extremes penalty
    raw_weights: list[float] = []
    items: list[MarketHypothesis] = []

    # Rebuild bands per key for extreme detection
    band_map = {k: b[k] for k in _ORDER}

    # STR viability rule-of-thumb
    def _str_ok(ir_delta: float) -> bool:
        return snapshot.cap_rate <= 0.075 and snapshot.vacancy_rate <= 0.08 and ir_delta <= 0.01

    for rd, ed, ir, cr, vd in combos:
        extreme_count = 0
        for key, val in zip(_ORDER, (rd, ed, ir, cr, vd), strict=False):
            if _is_extreme(val, band_map[key]):
                extreme_count += 1
        # Penalty only when jointly extreme (>=2 axes at extremes)
        if extreme_count >= 2:
            penalty = max(0.60, 1.0 - 0.05 * (extreme_count - 1))
        else:
            penalty = 1.0

        raw_weights.append(penalty)

        str_ok = _str_ok(ir)
        rationale = _rationale(rd, ed, ir, cr, vd, str_ok)

        # Prior temporarily set to 0; we normalize after we know the total mass
        items.append(
            MarketHypothesis(
                rent_delta=rd,
                expense_growth_delta=ed,
                interest_rate_delta=ir,
                cap_rate_delta=cr,
                vacancy_delta=vd,
                str_viability=str_ok,
                prior=0.0,
                rationale=rationale,
            )
        )

    # Normalize priors to sum to 1.0
    total = float(sum(raw_weights)) if raw_weights else 1.0
    if total == 0.0:
        # Defensive: if everything somehow penalized to zero, distribute uniformly.
        n = max(1, len(items))
        priors = [1.0 / n] * n
    else:
        priors = [w / total for w in raw_weights]

    normalized_items = tuple(
        MarketHypothesis(
            rent_delta=it.rent_delta,
            expense_growth_delta=it.expense_growth_delta,
            interest_rate_delta=it.interest_rate_delta,
            cap_rate_delta=it.cap_rate_delta,
            vacancy_delta=it.vacancy_delta,
            str_viability=it.str_viability,
            prior=priors[i],
            rationale=it.rationale,
        )
        for i, it in enumerate(items)
    )

    # Deterministic ordering (lexicographic on fields)
    sorted_items = tuple(
        sorted(
            normalized_items,
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
        snapshot_region=snapshot.region,
        seed=seed,
        items=sorted_items,
        notes=None,
    )


def prior_mass(hset: HypothesisSet) -> float:
    """Utility: sum of priors; should be very close to 1.0."""
    return float(sum(h.prior for h in hset.items))
