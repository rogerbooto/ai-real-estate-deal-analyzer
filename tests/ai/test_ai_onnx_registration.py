# tests/ai/test_ai_onnx_registration.py
from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from src.core.cv import amenities_defects as mod  # access _PROVIDERS
from src.core.cv.amenities_defects import detect_from_image
from src.core.cv.ontology import AMENITIES_DEFECTS_V1


def _img() -> Image.Image:
    buf = BytesIO()
    Image.new("RGB", (32, 32), color=(240, 240, 240)).save(buf, format="PNG")
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def test_onnx_provider_unregistered_raises_valueerror():
    # Ensure no ONNX provider is registered
    if "onnx" in mod._PROVIDERS:
        del mod._PROVIDERS["onnx"]

    with pytest.raises(ValueError):
        detect_from_image(_img(), provider="onnx", ontology=AMENITIES_DEFECTS_V1)


def test_onnx_provider_registered_via_monkeypatch(monkeypatch):
    def fake_onnx_provider(_: Image.Image):
        # includes a synonym that must map to parking_garage
        return [
            {"name": "garage", "confidence": 0.83},
            {"name": "unknown_label", "confidence": 0.99},  # OOD → drop
        ]

    monkeypatch.setitem(mod._PROVIDERS, "onnx", fake_onnx_provider)

    out = detect_from_image(_img(), provider="onnx", ontology=AMENITIES_DEFECTS_V1)
    names = [d["name"] for d in out]
    assert "parking_garage" in names
    assert all(n in AMENITIES_DEFECTS_V1.labels for n in names)
