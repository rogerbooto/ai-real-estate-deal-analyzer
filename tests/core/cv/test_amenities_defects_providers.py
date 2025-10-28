# tests/core/cv/test_amenities_defects_providers.py
from __future__ import annotations

from PIL import Image

from src.core.cv.amenities_defects import detect_from_image
from src.core.cv.ontology import AMENITIES_DEFECTS_V1


def test_vision_stub_is_closed_set_and_deterministic():
    # bright, landscape image should trigger natural_light_high (+ maybe street_parking)
    img = Image.new("RGB", (96, 64), color=(245, 245, 245))  # landscape & bright
    out1 = detect_from_image(img, provider="vision", ontology=AMENITIES_DEFECTS_V1)
    out2 = detect_from_image(img, provider="vision", ontology=AMENITIES_DEFECTS_V1)

    names1 = [d["name"] for d in out1]
    names2 = [d["name"] for d in out2]

    # deterministic
    assert names1 == names2
    # closed set
    for n in names1:
        assert n in AMENITIES_DEFECTS_V1.labels


def test_llm_stub_respects_ontology_and_cutoffs():
    # bright portrait → at least natural_light_high via caption path
    img = Image.new("RGB", (64, 96), color=(250, 250, 250))  # portrait & very bright
    out = detect_from_image(img, provider="llm", ontology=AMENITIES_DEFECTS_V1)
    names = [d["name"] for d in out]

    # Since cutoff for natural_light_high is 0.70 and stub emits 0.70 → it should be present
    assert "natural_light_high" in names
    # ensure all labels belong to ontology
    for n in names:
        assert n in AMENITIES_DEFECTS_V1.labels
