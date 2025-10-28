# tests/ai/test_ai_stubs_behavior.py
from __future__ import annotations

from PIL import Image

from src.core.cv.amenities_defects import detect_from_image
from src.core.cv.ontology import AMENITIES_DEFECTS_V1


def test_bright_landscape_triggers_expected_labels():
    # Bright + landscape should trigger natural_light_high (and maybe street_parking) in stubs
    img = Image.new("RGB", (96, 64), color=(250, 250, 250))  # landscape & bright

    out_vision = detect_from_image(img, provider="vision", ontology=AMENITIES_DEFECTS_V1)
    out_llm = detect_from_image(img, provider="llm", ontology=AMENITIES_DEFECTS_V1)

    names_v = [d["name"] for d in out_vision]
    names_l = [d["name"] for d in out_llm]

    # Closed set
    assert all(n in AMENITIES_DEFECTS_V1.labels for n in names_v)
    assert all(n in AMENITIES_DEFECTS_V1.labels for n in names_l)

    # Expect bright cue to surface natural_light_high at least for LLM stub
    assert "natural_light_high" in names_l

    # Vision stub may also yield it; allow either natural_light_high or street_parking
    assert ("natural_light_high" in names_v) or ("street_parking" in names_v)
