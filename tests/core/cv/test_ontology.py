# tests/core/cv/test_ontology.py
from __future__ import annotations

from src.core.cv.ontology import AMENITIES_DEFECTS_V1


def test_lookup_by_synonym():
    onto = AMENITIES_DEFECTS_V1
    # synonyms should resolve to canonical entries
    for syn in ["garage", "2-car garage", "on-street parking", "tesla charger"]:
        lbl = onto.lookup(syn)
        assert lbl is not None, f"expected match for synonym: {syn}"
        assert isinstance(lbl, dict)
        assert "name" in lbl
    # spot-check canonical
    assert onto.lookup("parking_garage")["name"] == "parking_garage"


def test_lookup_is_case_insensitive():
    onto = AMENITIES_DEFECTS_V1
    a = onto.lookup("EV CHARGING")
    b = onto.lookup("ev charger")
    c = onto.lookup("ev_charger")
    assert a and b and c
    assert a["name"] == b["name"] == c["name"] == "ev_charger"


def test_confidence_cutoffs_present_and_in_range():
    onto = AMENITIES_DEFECTS_V1
    for name, meta in onto.labels.items():
        assert "confidence_cutoff" in meta, f"missing cutoff for {name}"
        cutoff = meta["confidence_cutoff"]
        assert isinstance(cutoff, float)
        assert 0.0 <= cutoff <= 1.0


def test_categories_valid_only_amenity_or_defect():
    onto = AMENITIES_DEFECTS_V1
    cats = {meta["category"] for meta in onto.labels.values()}
    assert cats.issubset({"amenity", "defect"})


def test_all_names_returns_canonicals_only():
    onto = AMENITIES_DEFECTS_V1
    s = onto.all_names()
    assert "parking_garage" in s
    # Ensure a synonym is NOT treated as a canonical name
    assert "garage" not in s


def test_validate_method_runs_without_error():
    onto = AMENITIES_DEFECTS_V1
    # Should not raise
    onto.validate()
    # Additional sanity checks after validation
    assert isinstance(onto.labels, dict)
    assert len(onto.labels) > 0, "Ontology must contain labels"
    # Ensure categories and cutoffs are within valid ranges
    for meta in onto.labels.values():
        assert meta["category"] in ("amenity", "defect")
        assert 0.0 <= meta["confidence_cutoff"] <= 1.0
