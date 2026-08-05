# tests/intelligence/test_imports_alias.py

from __future__ import annotations


def test_intelligence_imports():
    # Modules load without side effects or runtime errors.
    import src.core.intelligence as _pkg  # noqa:F401
    from src.core.intelligence import deal_fusion, scoring  # noqa:F401

    # Key symbols resolve
    assert hasattr(deal_fusion, "DealIntelligence")
    assert hasattr(deal_fusion, "ScoreComponents")
    assert hasattr(scoring, "compute_composite_score")
