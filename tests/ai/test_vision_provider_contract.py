# tests/test_vision_provider_contract.py
from src.tools.vision.ontology import CONF_THRESHOLD, derive_amenities, in_ontology, map_raw_tags


def test_map_filters_threshold_and_ontology():
    raw = [
        {"label": "kitchen", "category": "room_type", "confidence": CONF_THRESHOLD, "evidence": "sink visible"},
        {"label": "kitchen", "category": "room_type", "confidence": 0.2, "evidence": "low conf"},
        {"label": "non_ontology_label", "category": "feature", "confidence": 0.9, "evidence": "nope"},
        {"label": "kitchen_island", "category": "feature", "confidence": 0.8, "evidence": "central counter"},
        {"label": "kitchen_island", "category": "feature", "confidence": 0.85, "evidence": "better conf"},
        {"label": "mold_suspected", "category": "issue", "confidence": 0.41, "evidence": "spots on caulk"},
    ]
    mapped = map_raw_tags(raw)
    labels = {(t["category"], t["label"]) for t in mapped}
    assert ("room_type", "kitchen") in labels
    assert ("feature", "kitchen_island") in labels
    assert ("issue", "mold_suspected") in labels
    assert all(t["confidence"] >= CONF_THRESHOLD for t in mapped)

    ams = derive_amenities(mapped)
    assert "kitchen_island" in ams
    extra = map_raw_tags([{"label": "stainless_appliances", "category": "feature", "confidence": 0.9, "evidence": "steel"}])
    ams2 = derive_amenities(extra)
    assert "stainless_kitchen" in ams2


def test_in_ontology_strictness():
    assert in_ontology("kitchen", "room_type")
    assert not in_ontology("kitchens", "room_type")
