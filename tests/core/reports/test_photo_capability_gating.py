# tests/core/reports/test_photo_capability_gating.py
"""
Mission 2, Gate 3 VETO remediation — B3. **A report must not assert an observation nothing was
capable of making.**

The defect
----------
``generator._render_photo_coverage`` used to print two facts unconditionally:

    - **Quality Proxies:** curb_appeal_score 0.00, natural_light_score 0.00, renovated_score 0.00
    - **Parking (from photos):** none · no EV charging observed

``ParkingSummary.ev_charging`` defaults to ``False`` and ``parking_type`` defaults to ``"none"``
on a ``PhotoInsights`` built from zero detections, and **no built-in CV provider declares any
parking or EV-charger label at all** — the exhaustive declarations are
``{natural_light_high, stainless_appliances}`` plus two synonyms
(``core.cv.amenities_defects``'s "Built-in capability declarations" block). So on every shipped
configuration those two sentences printed the schema DEFAULT as a SIGHTING — R-6 (the
filename-hint rule: "a file name may suggest; only a detector that actually looked may confirm")
run in reverse, on an absence instead of a presence.

The fix, and what these tests pin
----------------------------------
``_photo_capability_covers`` (generator.py) gates every negative claim on
``core.cv.amenities_defects.provider_covers`` — the same "was anything even able to look"
question the filename-hint machinery already answers, applied to a schema default instead of a
filename guess. Both facts (parking overall, EV charging specifically) are gated independently,
because a provider can cover one without the other.

Each test below turns RED if the unconditional wording is restored, on EITHER branch:
  * "nothing could look" — the default, every built-in provider, must say so plainly instead of
    printing "none" / "no EV charging observed" as if they were findings.
  * "a covering detector looked and found none" — a REAL negative, once something declares the
    label, must still be stated (this is not "always hedge"; it is "state the true branch").
A test that only covered the first branch would let a regression that always prints "not checked"
— never a real negative even when one is available — pass silently, which is its own dishonesty.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

import src.core.cv.amenities_defects as ad
from src.core.reports.generator import generate_report
from src.core.reports.report_models import MediaCoverage, MediaReport, ParkingSummary
from src.schemas.models import ListingInsights
from tests.utils import make_minimal_forecast

pytestmark = pytest.mark.usefixtures("_restore_providers")


@pytest.fixture(name="_restore_providers")
def _restore_providers_fixture() -> Iterator[None]:
    """Snapshot/restore the provider registry so a fake binding cannot leak between tests."""
    saved = dict(ad._PROVIDERS)
    yield
    ad._PROVIDERS.clear()
    ad._PROVIDERS.update(saved)


def _media_report(**overrides: object) -> MediaReport:
    defaults: dict[str, object] = {
        "listing_title": "36 Kelly",
        "room_counts": {"kitchen": 1},
        "amenities": {},
        "defects": {},
        "quality_flags": {},
        "parking": ParkingSummary(parking_type="none", parking_spots=None, ev_charging=False),
        "coverage": MediaCoverage(images_total=4, images_readable=4, detections_total=0, provider="cv_v2", version="deterministic"),
        "warnings": [],
        "ontology_version": "amenities_defects_v1",
        "provenance": {"selected_provider": "local"},
    }
    defaults.update(overrides)
    return MediaReport(**defaults)  # type: ignore[arg-type]


def _render(report: MediaReport) -> str:
    return generate_report(ListingInsights(address="36 Kelly"), make_minimal_forecast(), None, media_report=report)


def _dummy_provider(_img: object) -> list[object]:
    """A provider function used only to CARRY a capability declaration in these tests.

    Deliberately NOT ``ad._provider_local`` (or any other built-in provider function): capability
    declarations are keyed by FUNCTION IDENTITY in ``_PROVIDER_CAPABILITIES``
    (``amenities_defects._declare_capabilities``'s docstring: "last declaration wins"), not by
    slot name, and ``_restore_providers`` only snapshots/restores the SLOT mapping
    (``_PROVIDERS``). Registering a built-in function under a fake slot with a fake ``detects=``
    would permanently overwrite that function's real declaration — corrupting the actual "local"
    provider for every test that runs afterwards in the same process, which is exactly what
    happened the first time this file used ``ad._provider_local`` here.
    """
    return []


# ---------------------------------------------------------------------------------
# Branch 1 — nothing could look (every built-in provider, i.e. the shipped default)
# ---------------------------------------------------------------------------------


@pytest.mark.parametrize("provider", ["local", "vision", "llm"])
def test_no_builtin_provider_lets_the_report_assert_a_parking_finding(provider: str) -> None:
    """RED on revert: the old code printed "none" here unconditionally, on every provider."""
    md = _render(_media_report(provenance={"selected_provider": provider}))

    assert "**Parking (from photos):** not checked" in md
    assert "no photo check in this run looks for parking" in md
    # The negative claim from the reverted wording must never appear standing alone.
    assert "**Parking (from photos):** none ·" not in md


@pytest.mark.parametrize("provider", ["local", "vision", "llm"])
def test_no_builtin_provider_lets_the_report_assert_ev_charging_was_checked(provider: str) -> None:
    """RED on revert: the old code printed "no EV charging observed" unconditionally."""
    md = _render(_media_report(provenance={"selected_provider": provider}))

    assert "EV charging not checked" in md
    assert "no photo check in this run looks for chargers" in md
    assert "no EV charging observed" not in md
    assert "EV charging observed" not in md


def test_an_unrecognised_or_missing_provider_also_fails_safe() -> None:
    """Conservative default: an absent/garbled provenance key must not be read as "something
    looked". Mirrors `provider_capabilities`'s own documented reading of an undeclared provider:
    empty means "declares no coverage", never "covers everything"."""
    md = _render(_media_report(provenance={}))
    assert "**Parking (from photos):** not checked" in md

    md_bad = _render(_media_report(provenance={"selected_provider": "not-a-real-provider"}))
    assert "**Parking (from photos):** not checked" in md_bad


# ---------------------------------------------------------------------------------
# Branch 2 — something covers the label, looked, and found none: a REAL negative
# ---------------------------------------------------------------------------------


def test_a_covering_provider_that_finds_no_parking_states_a_real_negative() -> None:
    """Once a provider DECLARES it can see parking, "none" is a finding, not a default, and the
    report must say so — the opposite regression from B3 (always hedging) is just as dishonest."""
    ad.register_provider("onnx", _dummy_provider, detects=["parking_garage", "parking_driveway", "street_parking"])

    md = _render(_media_report(provenance={"selected_provider": "onnx"}))

    assert "**Parking (from photos):** none" in md
    # EV charging is a SEPARATE gate (this provider declares only the parking labels), so its own
    # "not checked" is expected on the same line -- what must be absent is the PARKING one.
    assert "not checked — no photo check in this run looks for parking" not in md


def test_a_covering_provider_that_finds_no_ev_charging_states_a_real_negative() -> None:
    ad.register_provider("onnx", _dummy_provider, detects=["ev_charger"])

    md = _render(_media_report(provenance={"selected_provider": "onnx"}))

    assert "no EV charging observed" in md
    assert "EV charging not checked" not in md


def test_a_covering_provider_that_finds_ev_charging_still_states_it() -> None:
    ad.register_provider("onnx", _dummy_provider, detects=["ev_charger"])

    md = _render(
        _media_report(
            provenance={"selected_provider": "onnx"},
            parking=ParkingSummary(parking_type="garage", parking_spots=1, ev_charging=True),
        )
    )

    assert "**Parking (from photos):** garage · 1 spot · EV charging observed" in md


# ---------------------------------------------------------------------------------
# Quality Proxies — 0.00 must not read as a measured score
# ---------------------------------------------------------------------------------


def test_a_zero_quality_score_reads_as_not_measured_not_as_a_finding() -> None:
    """RED on revert: the old code printed a bare "0.00", indistinguishable from a genuinely
    low (but measured) score. `_quality_scores` only ever produces exactly 0.0 when nothing in
    the photo set matched the trait's predicate at all (mean of an empty bucket)."""
    md = _render(_media_report(quality_flags={"curb_appeal_score": 0.0}))

    assert "curb_appeal_score not measured" in md
    assert "curb_appeal_score 0.00" not in md


def test_a_nonzero_quality_score_still_prints_as_a_number_with_its_scale_stated() -> None:
    md = _render(_media_report(quality_flags={"natural_light_score": 0.62}))

    assert "- **Quality Proxies (0-1 scale):** natural_light_score 0.62" in md
