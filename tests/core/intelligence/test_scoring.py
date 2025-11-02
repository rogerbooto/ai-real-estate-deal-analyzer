# tests/intelligence/test_scoring.py

from __future__ import annotations

from src.core.intelligence.deal_fusion import ScoreComponents
from src.core.intelligence.scoring import DEFAULT_WEIGHTS, compute_composite_score


def test_compute_composite_score_exact():
    """
    Exact numeric check with hand-verified math:

    s = 0.40*0.70 + 0.30*0.55 + 0.20*0.70 + (-0.10)*0.25
      = 0.28       + 0.165       + 0.14        - 0.025
      = 0.56  → clamp[0,1] = 0.56
    """
    c = ScoreComponents(
        media_quality=0.70,
        roi_index=0.55,
        neighborhood_safety=0.70,
        defect_penalty=0.25,
    )
    got = compute_composite_score(c, DEFAULT_WEIGHTS)
    assert abs(got - 0.56) < 1e-12


def test_compute_composite_score_clamping():
    """Scores below 0 clamp to 0.0; above 1 clamp to 1.0."""
    low = ScoreComponents(
        media_quality=0.0,
        roi_index=0.0,
        neighborhood_safety=0.0,
        defect_penalty=10.0,
    )  # large penalty pushes negative
    high = ScoreComponents(
        media_quality=10.0,
        roi_index=10.0,
        neighborhood_safety=10.0,
        defect_penalty=0.0,
    )  # huge positives push >1

    assert compute_composite_score(low, DEFAULT_WEIGHTS) == 0.0
    assert compute_composite_score(high, DEFAULT_WEIGHTS) == 1.0
