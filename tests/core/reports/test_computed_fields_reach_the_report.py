# tests/core/reports/test_computed_fields_reach_the_report.py
"""Mission 2, task 3.2 (OPD-4) — every computed-then-discarded field must reach the reader.

These are the RED-on-revert pins for the fields the report used to compute (or receive) and then
drop. Each test names the number it expects and where it comes from, so reverting the render puts
the test RED with a message a reviewer can act on, rather than a diff of two blobs.

The load-bearing distinction throughout: the **engine** computes money numbers, the report
**renders** them. Where this file asserts an exact figure, that figure is read off the forecast in
the test rather than recomputed, so the test cannot drift away from the engine either.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

import src.core.cv.amenities_defects as ad
from src.core.finance import run_financial_model
from src.core.reports.generator import generate_report
from src.core.reports.report_models import MediaCoverage, MediaReport, ParkingSummary
from src.schemas.models import FinancialInputs, ListingInsights, MediaInsights, RunProvenance
from tests.utils import make_financial_inputs, make_financing_terms, make_market_assumptions, make_minimal_forecast

# ---------------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------------


def _inputs(**market_overrides: float | None) -> FinancialInputs:
    base = make_financial_inputs()
    if not market_overrides:
        return base
    return base.model_copy(update={"market": make_market_assumptions(**market_overrides)})


def _render(inputs: FinancialInputs, **kwargs: object) -> str:
    forecast = run_financial_model(inputs)
    return generate_report(ListingInsights(address="36 Kelly"), forecast, None, market=inputs.market, **kwargs)  # type: ignore[arg-type]


def _section(md: str, heading: str) -> str:
    start = md.index(f"## {heading}")
    nxt = md.find("\n## ", start + 1)
    return md[start:] if nxt == -1 else md[start:nxt]


def _media_report(**overrides: object) -> MediaReport:
    defaults: dict[str, object] = {
        "listing_title": "Duplex on Kelly",
        "source_url": "https://example.invalid/36-kelly",
        "address": "36 Kelly St, Moncton NB",
        "room_counts": {"kitchen": 2},
        "amenities": {"stainless_kitchen": True},
        "defects": {"water_leak_suspected": 3},
        "quality_flags": {"natural_light_score": 0.42},
        "parking": ParkingSummary(parking_type="garage", parking_spots=2, ev_charging=True),
        "coverage": MediaCoverage(images_total=4, images_readable=4, detections_total=9, provider="cv_v2", version="onnx-2024.11"),
        "warnings": [],
        "ontology_version": "amenities_defects_v1",
        "provenance": {"selected_provider": "local", "provider_kind": "heuristic_stub", "filtered": {"dropped_count": 1}},
    }
    defaults.update(overrides)
    return MediaReport(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------------
# (a) HARD EXIT CRITERION — the cap-rate floor VALUE reaches the report
# ---------------------------------------------------------------------------------


def test_cap_rate_floor_value_reaches_the_report_when_cleared() -> None:
    """The floor a deal cleared is a number the reader can act on; "the configured floor" is not."""
    inputs = _inputs(cap_rate_floor=0.05, cap_rate_purchase=0.0635)
    md = _render(inputs)

    assert "| Cap-rate floor | 5.00% | `market.cap_rate_floor` |" in md


def test_cap_rate_floor_row_says_so_when_no_floor_policy_exists() -> None:
    """Absent is not the same as cleared, and the appendix must not let them look alike."""
    md = _render(_inputs(cap_rate_floor=None))

    assert "| Cap-rate floor | (no floor policy set) | `market.cap_rate_floor` |" in md


def test_spread_target_reaches_the_report() -> None:
    """The other guardrail quoted in the thesis, for a report rendered without a thesis."""
    md = _render(_inputs(cap_rate_spread_target=0.02))

    assert "| Cap-rate spread target | 2.00% | `market.cap_rate_spread_target` |" in md


def test_guardrail_rows_are_absent_rather_than_guessed_when_no_market_is_supplied() -> None:
    forecast = run_financial_model(make_financial_inputs())
    md = generate_report(ListingInsights(address="36 Kelly"), forecast, None)

    assert "Cap-rate floor" not in md
    assert "Cap-rate spread target" not in md


# ---------------------------------------------------------------------------------
# (b) YearBreakdown — the engine's own figures, rendered instead of recomputed
# ---------------------------------------------------------------------------------


def test_principal_and_interest_split_reaches_the_pro_forma() -> None:
    inputs = make_financial_inputs()
    forecast = run_financial_model(inputs)
    y1 = forecast.years[0]
    md = generate_report(ListingInsights(address="36 Kelly"), forecast, None, market=inputs.market)

    pro_forma = _section(md, f"{len(forecast.years)}-Year Pro Forma (Summary)")
    assert "| Principal | Interest |" in pro_forma.replace(" Cash Flow ", " ")  # header order
    assert f"${y1.principal_paid:,.2f}" in pro_forma
    assert f"${y1.interest_paid:,.2f}" in pro_forma
    # The split must be the engine's, i.e. it reconciles with the total beside it.
    assert round(y1.principal_paid + y1.interest_paid, 2) == round(y1.debt_service, 2)


def test_noi_table_renders_the_engines_stored_valuation_not_a_recomputation() -> None:
    """The engine drifts the cap by ``market.cap_rate_drift``; the table used to ignore that.

    Reproduces the live disagreement task 3.2 found: with the repo's own test factory
    (``cap_rate_drift=0.03``) the stored cap path ran 7.44% -> 13.44% over ten years while the
    report printed a flat 7.44% and a value derived from it, for every row.
    """
    inputs = _inputs(cap_rate_drift=0.03, cap_rate_floor=0.05, cap_rate_spread_target=0.015)
    forecast = run_financial_model(inputs)
    md = _render(inputs)
    noi = _section(md, "Valuation – NOI-Based (with Cap Drift)")

    for y in forecast.years:
        assert y.cap_rate_applied is not None
        assert (
            f"| {y.year} | {y.cap_rate_applied * 100:.2f}% | ${y.est_value:,.2f} | {y.ltv_pct:.2f}% | ${y.available_equity:,.2f} |" in noi
        )

    # Sanity that this fixture actually exercises drift (else the assertion above is vacuous).
    assert forecast.years[0].cap_rate_applied != forecast.years[-1].cap_rate_applied


def test_ltv_is_rendered_from_the_stored_percent_field_without_a_second_scaling() -> None:
    """``ltv_pct`` is stored in PERCENT while every other rate in the schema is a fraction.

    Formatting it through the fraction formatter would print 9314.00%. This pins the unit.
    """
    inputs = make_financial_inputs()
    forecast = run_financial_model(inputs)
    md = _render(inputs)
    noi = _section(md, "Valuation – NOI-Based (with Cap Drift)")

    assert f"{forecast.years[0].ltv_pct:.2f}%" in noi
    assert 0.0 <= forecast.years[0].ltv_pct <= 200.0  # a percent, not a fraction


def test_available_equity_is_floored_at_zero_in_every_valuation_track() -> None:
    """One column heading, one meaning. Below the 80% mark there is nothing to draw.

    Deliberately a HIGH-LEVERAGE deal (5% down, like the demo bundle): at 20% down the loan is
    under the 80% mark from Year 1 and none of the three tracks would ever exercise the floor, so
    a well-capitalised fixture would make this test pass whether or not the floor exists.
    """
    inputs = make_financial_inputs().model_copy(
        update={
            "financing": make_financing_terms(down_payment_rate=0.05, mortgage_insurance_rate=0.04),
            "market": make_market_assumptions(cap_rate_drift=0.0),
        }
    )
    forecast = run_financial_model(inputs)
    md = _render(inputs)

    # Both halves must be exercised, or the assertions below are vacuous.
    assert any(y.available_equity == 0.0 and y.ltv_pct > 80.0 for y in forecast.years), "engine track must hit the floor"
    assert any(0.80 * y.est_value - y.ending_balance < 0 for y in forecast.years), "unfloored figure must be negative somewhere"

    for heading in (
        "Valuation – NOI-Based (with Cap Drift)",
        "Valuation – Baseline Appreciation",
        "Valuation – Stress-Test",
    ):
        table = next(sec for sec in md.split("\n## ") if sec.startswith(heading))
        assert "-$" not in table, f"{heading} still prints a negative 'available' equity"
        assert "$0.00" in table, f"{heading} never reaches the floored state this fixture was built for"


def test_a_forecast_without_a_stored_cap_path_still_renders_the_noi_table() -> None:
    """``deal-report`` accepts forecast JSON that predates the stored valuation fields."""
    forecast = run_financial_model(make_financial_inputs())
    legacy = forecast.model_copy(update={"years": [y.model_copy(update={"cap_rate_applied": None}) for y in forecast.years]})
    md = generate_report(ListingInsights(address="36 Kelly"), legacy, None)

    noi = _section(md, "Valuation – NOI-Based (with Cap Drift)")
    assert len([line for line in noi.splitlines() if line.startswith("| ")]) == len(forecast.years) + 2  # header + separator


# ---------------------------------------------------------------------------------
# (c) MediaInsights / MediaReport / MediaCoverage
# ---------------------------------------------------------------------------------


def test_image_quality_metrics_reach_the_media_overview() -> None:
    mi = MediaInsights(
        total_assets=2,
        image_count=2,
        video_count=0,
        document_count=0,
        other_count=0,
        bytes_total=2048,
        image_quality={"aaa": {"sharpness": 12.5, "brightness": 0.4}, "bbb": {"sharpness": 88.25, "brightness": 0.9}},
    )
    md = generate_report(None, make_minimal_forecast(), None, media_insights=mi)

    assert "- **Image Quality:** brightness 0.40–0.90, sharpness 12.50–88.25 _(range across 2 images)_" in md


def test_photo_coverage_names_the_provider_version_as_well_as_the_provider() -> None:
    md = generate_report(None, make_minimal_forecast(), None, media_report=_media_report())

    assert "provider `cv_v2` version `onnx-2024.11`" in md


def test_photo_coverage_states_what_the_photo_set_is_of() -> None:
    md = generate_report(None, make_minimal_forecast(), None, media_report=_media_report())

    assert "- **Subject:** Duplex on Kelly · 36 Kelly St, Moncton NB · https://example.invalid/36-kelly" in md


def test_photo_coverage_renders_defects_and_quality_proxies() -> None:
    md = generate_report(None, make_minimal_forecast(), None, media_report=_media_report())

    assert "- **Defects Seen in Photos:** water_leak_suspected (3 images)" in md
    assert "- **Quality Proxies (0-1 scale):** natural_light_score 0.42" in md


def _dummy_ev_provider(_img: object) -> list[object]:
    """Carries a fake EV-charger capability declaration only — never a real provider function.

    Capability declarations are keyed by FUNCTION IDENTITY (``_PROVIDER_CAPABILITIES``), not by
    slot name, and never restored by ``ev_capable_provider``'s snapshot/restore below (which only
    restores the slot mapping, ``_PROVIDERS``). Registering a built-in function (e.g.
    ``ad._provider_local``) here under a fake ``detects=`` would permanently overwrite that
    function's REAL declaration for the rest of the test process, corrupting every later test that
    relies on the real "local" provider covering nothing parking/EV-related.
    """
    return []


@pytest.fixture
def ev_capable_provider() -> Iterator[None]:
    """Register a stand-in provider that DECLARES EV-charger coverage.

    Every built-in provider declares no parking/EV label at all (see B3 remediation,
    ``generator._photo_capability_covers``), so a report built with the default fixture
    provenance always lands on the "nothing could look" branch. This test's whole point is the
    OTHER branch — a covering provider looked and the result (True/False) is a real
    observation — so it needs a provider on record that actually declares the label.
    Snapshot/restore mirrors ``tests/core/cv/test_filename_corroboration.py``'s
    ``restore_providers`` fixture so the fake binding cannot leak into other tests.
    """
    saved = dict(ad._PROVIDERS)
    ad.register_provider("onnx", _dummy_ev_provider, detects=["ev_charger"])
    yield
    ad._PROVIDERS.clear()
    ad._PROVIDERS.update(saved)


@pytest.mark.parametrize(
    ("ev_charging", "expected"),
    [(True, "EV charging observed"), (False, "no EV charging observed")],
)
def test_parking_summary_states_ev_charging_either_way(ev_charging: bool, expected: str, ev_capable_provider: None) -> None:
    """Cited by _BOOL_FIELDS_WITH_DEDICATED_TESTS in the field guard — keep the name in sync."""
    report = _media_report(
        parking=ParkingSummary(parking_type="garage", parking_spots=2, ev_charging=ev_charging),
        provenance={"selected_provider": "onnx"},
    )
    md = generate_report(None, make_minimal_forecast(), None, media_report=report)

    assert f"- **Parking (from photos):** garage · 2 spots · {expected}" in md


def test_media_report_versions_and_provenance_reach_the_provenance_appendix() -> None:
    """Guardian M11, re-adjudicated: metadata about WHO made a claim is not "internal".

    ``provider_kind: heuristic_stub`` beside a section that prints "provider `cv_v2`" is the
    whole reason this was overturned — the photo observations above it reach engine rules.
    """
    md = generate_report(None, make_minimal_forecast(), None, media_report=_media_report())

    assert "| Media report schema | media_report_v1 | `MediaReport.report_version` |" in md
    assert "| CV ontology | amenities_defects_v1 | `MediaReport.ontology_version` |" in md
    assert "| Photo pipeline — selected_provider | local | `MediaReport.provenance` |" in md
    assert "| Photo pipeline — provider_kind | heuristic_stub | `MediaReport.provenance` |" in md
    # Nested provenance is flattened rather than curated: a key added upstream still reaches here.
    assert "| Photo pipeline — filtered.dropped_count | 1 | `MediaReport.provenance` |" in md


def test_media_provenance_rows_are_absent_when_no_media_report_is_supplied() -> None:
    provenance = RunProvenance(engine="deterministic", scenarios_enabled=False, vision_enabled=False)
    md = generate_report(None, make_minimal_forecast(), None, provenance=provenance)

    assert "Photo pipeline" not in md
    assert "CV ontology" not in md
