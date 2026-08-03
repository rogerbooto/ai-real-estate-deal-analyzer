# tests/orchestrators/test_orchestration_result_field_guard.py
"""
Anti-regression transform guard (Mission 2, Wave 1, root cause 2) for the
orchestration-result assembly in BOTH engines: src/orchestrators/crew.py (deterministic)
and src/orchestrators/crewai_runner.py (crewai seam). Both build the same ``OrchestrationResult``
dataclass at the end of ``run_orchestration``.

F5 (fixed in commit 821cdac) was this defect class's second instance: ``crewai_runner``'s
``run_orchestration`` returned ``OrchestrationResult(insights=..., forecast=..., thesis=...)``
without ``media_insights``/``media_report`` even though photos were supplied, so both fields
silently defaulted to ``None`` and the report lost its Media Overview / Photo Coverage
sections.

Unlike ``synthesize_listing_insights`` (a same-named-field passthrough) or ``analyze_listing``
(a ``model_copy`` merge), ``OrchestrationResult`` is an AGGREGATE assembled from several
independently-computed artifacts (insights/forecast/thesis/media_insights/media_report) —
there is no single source model to sentinel-fill and diff field-by-field. The general
"nothing reverts to default" invariant is enforced here differently but no less
generically: ``dataclasses.fields(OrchestrationResult)`` is enumerated DYNAMICALLY (never
hand-listed), the pipeline is run for real (with real, decodable photos so every
photo-dependent field has genuine content to carry), and every field with a declared
default is asserted to have moved away from that default. A field added to
``OrchestrationResult`` tomorrow is picked up automatically — no edit to this file
required — and if a future engine's constructor call forgets to pass it, this test goes
RED without anyone updating a hand-list of "the fields we currently know about".
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest
from PIL import Image

from src.orchestrators.crew import OrchestrationResult, run_orchestration as run_deterministic
from src.orchestrators.crewai_runner import run_orchestration as run_crewai
from tests.utils import make_financial_inputs


def _sample_assets_with_real_photos(tmp_path: Path) -> tuple[str, str]:
    """
    Real, decodable images (not the zero-byte fixture used elsewhere in the crewai
    integration tests) so ``collect_local_assets``/``build_photo_insights`` have something
    genuine to analyze — a zero-byte ``.jpg`` is filtered out as unreadable and would make
    ``media_insights``/``media_report`` spuriously ``None`` regardless of whether the
    transform under test actually wires them through.
    """
    listing_txt = tmp_path / "listing.txt"
    listing_txt.write_text("Charming triplex at 123 Main St. Parking and laundry.", encoding="utf-8")
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()
    for name in ("kitchen.jpg", "bathroom.jpg"):
        Image.new("RGB", (800, 600), "white").save(photos_dir / name)
    return str(listing_txt), str(photos_dir)


def _assert_no_field_reverted_to_default(result: OrchestrationResult, *, engine_label: str) -> None:
    failures: list[str] = []
    for f in dataclasses.fields(OrchestrationResult):
        if f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING:  # type: ignore[misc]
            continue  # required field; nothing to "revert to"
        value = getattr(result, f.name)
        default = f.default if f.default is not dataclasses.MISSING else f.default_factory()  # type: ignore[misc]
        if value == default:
            failures.append(
                f"[{engine_label}] OrchestrationResult.{f.name} is still at its default ({default!r}) "
                "despite the pipeline being run with real listing text AND real, decodable photos "
                "that should have produced real content for every field"
            )
    assert not failures, "\n".join(failures)


@pytest.mark.parametrize("run_orchestration", [run_deterministic, run_crewai], ids=["deterministic", "crewai"])
def test_orchestration_result_drops_no_field_with_photos_supplied(monkeypatch, tmp_path, run_orchestration) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")  # only read by the crewai engine's env guard

    inputs = make_financial_inputs()
    listing_txt, photos_dir = _sample_assets_with_real_photos(tmp_path)

    result = run_orchestration(
        inputs=inputs,
        listing_txt_path=listing_txt,
        photos_folder=photos_dir,
        horizon_years=10,
    )

    _assert_no_field_reverted_to_default(result, engine_label=run_orchestration.__module__)


def test_both_engines_agree_field_for_field_on_the_optional_media_fields(monkeypatch, tmp_path) -> None:
    """
    Parity check, generalized: enumerate OrchestrationResult's fields dynamically and assert
    the two engines produce equal values for every field that is defined to be
    engine-independent (both engines delegate media derivation to the same plain functions —
    see the "Mirrors src/orchestrators/crew.py's derivation exactly" comment in
    crewai_runner.py). insights/forecast/thesis are engine-specific objects (crewai's agents
    wrap the same math but aren't guaranteed to produce byte-identical intermediate reprs in
    every field), so only the two media fields are asserted for equality here; that is a
    deliberate, documented exclusion, not a silent one.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    inputs = make_financial_inputs()
    listing_txt, photos_dir = _sample_assets_with_real_photos(tmp_path)

    det = run_deterministic(inputs=inputs, listing_txt_path=listing_txt, photos_folder=photos_dir, horizon_years=10)
    crew = run_crewai(inputs=inputs, listing_txt_path=listing_txt, photos_folder=photos_dir, horizon_years=10)

    media_fields = {"media_insights", "media_report"}
    for f in dataclasses.fields(OrchestrationResult):
        if f.name not in media_fields:
            continue
        assert getattr(det, f.name) == getattr(crew, f.name), f"engines disagree on OrchestrationResult.{f.name}"
