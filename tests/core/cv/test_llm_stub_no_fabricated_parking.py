# tests/core/cv/test_llm_stub_no_fabricated_parking.py
"""
Mission 2, task 3.3 (M14 / M22): ``_provider_llm_stub`` must not invent a parking claim.

The defect
----------
The stub emitted ``{"name": "on-street parking", "confidence": 0.61}`` whenever
``aspect == "landscape" and luminance >= 0.55`` — a *property attribute* asserted from a photo
being wide and not dark. It is the identical fabrication already removed from
``_provider_vision_stub``, which survived in the sibling slot because ``build_photo_insights``
only ever selects ``vision`` or ``local`` and so nothing reached it in production.

Why "unreachable" stopped being an answer
-----------------------------------------
R-6 gave every provider a declared capability list, and this one declared ``"on-street parking"``.
A declaration is a promise that something is ABLE to look. Registering the stub would therefore
have turned a matching file name from ``filename_unconfirmed`` ("nothing could check this") into
``filename_confirmed`` ("a detector agreed") — making the fabrication *corroborating evidence*.

And the claim is one hop from money: ``"on-street parking"`` resolves to
``AmenityLabel.street_parking``, which ``to_photoinsights_amenities_surface`` folds into the
``parking`` surface, which ``synthesis`` emits as the literal tag ``"parking"``, which
``finance.engine._apply_insight_modifiers`` reads by MEMBERSHIP to add $50/month/unit.

Every test below is RED on revert of the emission.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from PIL import Image

from src.core.cv import amenities_defects as ad
from src.core.cv.amenities_defects import detect_from_image, provider_capabilities
from src.core.cv.ontology import AMENITIES_DEFECTS_V1
from src.schemas.labels import PARKING_SPECIFIC_AMENITIES, AmenityLabel

#: Every ontology label that reaches the ``parking`` amenity surface, and therefore the engine's
#: ``"parking"`` income rule. Derived from the ontology rather than hand-listed so a parking label
#: added later is covered without editing this file.
_PARKING_LABELS = {a.value for a in PARKING_SPECIFIC_AMENITIES} | {AmenityLabel.parking.value}


@pytest.fixture
def restore_providers() -> Iterator[None]:
    """Snapshot/restore the provider registry so a test's binding cannot leak."""
    saved = dict(ad._PROVIDERS)
    yield
    ad._PROVIDERS.clear()
    ad._PROVIDERS.update(saved)


def _sweep_images() -> Iterator[Image.Image]:
    """The input space the stub actually branches on: orientation, brightness, channel spread.

    Landscape frames at luminance >= 0.55 are the exact trigger the removed threshold used, so the
    sweep is built to contain many of them rather than to hope one turns up.
    """
    for size in ((192, 96), (96, 192), (128, 128)):
        for shade in (0, 60, 140, 180, 200, 245, 255):
            for tint in ((0, 0, 0), (30, 0, 0), (0, 0, 30), (10, 10, 0)):
                colour = tuple(min(255, shade + t) for t in tint)
                yield Image.new("RGB", size, color=colour)  # type: ignore[arg-type]


def test_the_llm_stub_never_emits_a_parking_label() -> None:
    """RED on revert: a wide bright photo used to yield ``street_parking`` at 0.61."""
    offenders: list[tuple[tuple[int, int], set[str]]] = []
    for img in _sweep_images():
        names = {d["name"] for d in detect_from_image(img, provider="llm", ontology=AMENITIES_DEFECTS_V1)}
        parking = names & _PARKING_LABELS
        if parking:
            offenders.append((img.size, parking))

    assert not offenders, f"the llm stub invented a parking claim from image geometry: {offenders[:5]}"


def test_the_exact_trigger_geometry_still_produces_no_parking() -> None:
    """The specific input the removed threshold fired on: landscape frame, luminance ~0.78.

    Named separately from the sweep so a future reader can see the reproduction rather than trust
    that the sweep covered it.
    """
    img = Image.new("RGB", (256, 128), color=(200, 200, 200))  # landscape, lum ~= 0.78 >= 0.55
    names = {d["name"] for d in detect_from_image(img, provider="llm", ontology=AMENITIES_DEFECTS_V1)}

    assert "natural_light_high" in names, "sanity: the stub's legitimate thresholds still fire on this image"
    assert not (names & _PARKING_LABELS), f"parking invented from a wide, bright frame: {sorted(names)}"


def test_the_capability_declaration_no_longer_claims_parking() -> None:
    """A declaration is a promise something is ABLE to look. Removing the emission without
    removing the promise would be worse than leaving both: the stub would then tell every
    ``garage.jpg`` "a detector covers you", scoring a claim nothing can even express."""
    declared = provider_capabilities("llm")

    assert not (declared & {"on-street parking", "street parking", "curbside parking"})
    resolved = {meta["name"] for raw in declared if (meta := AMENITIES_DEFECTS_V1.lookup(raw)) is not None}
    assert not (resolved & _PARKING_LABELS), f"llm still declares parking coverage: {sorted(resolved)}"


def test_registering_the_stub_cannot_make_a_filename_parking_claim_confirmable(
    tmp_path: Any,
    restore_providers: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The reason "unreachable in production" was not a sufficient defence.

    Bind the real stub into a live slot — the documented ``register_provider`` action R-6
    deliberately makes a zero-code-change upgrade — point it at a wide bright ``garage.jpg``, and
    assert the file name gets no corroboration out of it.
    """
    from src.core.cv.runner import tag_amenities_and_defects

    monkeypatch.setenv("AIREDEAL_CACHE_DIR", str(tmp_path / "cache"))
    photos = tmp_path / "photos"
    photos.mkdir()
    # Wide and bright: precisely the geometry the fabricated threshold keyed on.
    Image.new("RGB", (900, 500), color=(210, 210, 210)).save(photos / "garage.jpg", quality=95)

    ad.register_provider("onnx", ad._provider_llm_stub, detects=provider_capabilities("llm"))
    dets = tag_amenities_and_defects([photos / "garage.jpg"], provider="onnx", use_cache=False)

    entries = [d for per_img in dets.values() for d in per_img]
    parking = [d for d in entries if d.get("name") in _PARKING_LABELS]
    assert len(parking) == 1, f"expected exactly the file name's own garage claim, got {entries}"
    assert parking[0]["name"] == AmenityLabel.parking_garage.value
    assert parking[0]["source"] == "filename_unconfirmed", "the stub corroborated a file name it has no ability to check: " f"{parking[0]}"
    assert "confidence" not in parking[0], "an unconfirmed hint was given a score"
