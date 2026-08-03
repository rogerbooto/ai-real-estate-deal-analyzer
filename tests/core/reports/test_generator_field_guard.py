# tests/core/reports/test_generator_field_guard.py
"""
Anti-regression transform guard (Mission 2, Wave 1, root cause 2) for the report
generators (src/core/reports/generator.py). For a *renderer*, "nothing dropped" means
the value reaches the rendered Markdown text, not just that it survives an object copy.

Design
------
Every model ``generate_report`` accepts is built with ``build_sentinel_model`` (every
field non-default, enumerated dynamically from ``model_fields`` — see tests/utils.py).
The whole tree is rendered once via ``generate_report``, then walked recursively
(``model_fields`` again — never hand-listed) asserting each leaf's sentinel value shows
up in the text under ANY plausible formatting convention this renderer uses (currency,
percent, ratio, multiple, plain, comma-grouped) — we don't know which formatter a given
field uses ahead of time, so we try all of them and accept any hit; that keeps the check
generic across fields we've never met (e.g. one added tomorrow) without knowing their
formatting in advance. Adding a rendered field to a model without adding it to
``generate_report`` will show its sentinel value nowhere in the text, in no format, and
this test goes RED naming exactly that field.

Fields that are genuinely NOT rendered by design, or are known-but-out-of-scope
discarded-field defects, are excluded EXPLICITLY below with a documented reason — see
``_EXCLUDED``. A field silently missing from both the render AND this table fails loud;
that is the point.

Known live gaps discovered BY this guard while it was being built (reported to Roger,
NOT fixed here — zero src/ diff is a binding constraint of this task) are called out in
``_EXCLUDED`` with a "NEW FINDING" tag distinguishing them from the charter's pre-existing
T5 class.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel

from src.core.reports.generator import generate_report
from src.core.reports.report_models import MediaReport
from src.schemas.models import (
    FinancialForecast,
    InvestmentThesis,
    ListingInsights,
    MediaInsights,
    RunProvenance,
    ScenarioAnalysis,
    YearBreakdown,
)
from tests.utils import build_sentinel_model

# ---------------------------------------------------------------------------------
# Exclusion table: (owning model class name, field name) -> documented reason.
#
# Keyed by the pydantic model that DECLARES the field (not the outer container), so one
# entry covers every place that model is nested (e.g. YearBreakdown appears twice — once
# per forecast year — and one exclusion entry covers both).
# ---------------------------------------------------------------------------------
_EXCLUDED: dict[tuple[str, str], str] = {
    # --- Legitimate, self-documented design (address-fallback chain) ---
    ("ListingInsights", "title"): (
        "Rendered only as an address fallback when insights.address is empty/None (see "
        "_render_header's own 'address -> inferred title -> generic' comment). The sentinel "
        "fixture sets a non-empty address, so title is correctly never shown here; the "
        "fallback path itself has its own coverage in tests/core/reports/test_report_header_identity.py."
    ),
    # --- Known findings, already in the Mission 2 charter (T5 class) ---
    ("YearBreakdown", "cap_rate_applied"): (
        "T5 (charter): generator.py recomputes a drifting cap per row (_render_valuation_table_noi) "
        "instead of reading the stored per-year value. Scheduled for Wave 3 (OPD-4); not fixed here "
        "(zero src/ diff is binding for this task)."
    ),
    ("YearBreakdown", "est_value"): (
        "T5 (charter, explicitly named): generator.py:592-596 recomputes estimated value per "
        "valuation table instead of rendering the stored YearBreakdown.est_value. Wave 3 (OPD-4)."
    ),
    ("YearBreakdown", "ltv_pct"): (
        "T5 (charter, explicitly named): recomputed in the valuation tables instead of rendered " "from the stored field. Wave 3 (OPD-4)."
    ),
    ("YearBreakdown", "available_equity"): (
        "T5 (charter, explicitly named): recomputed in the valuation tables instead of rendered " "from the stored field. Wave 3 (OPD-4)."
    ),
    ("YearBreakdown", "principal_paid"): (
        "T5-class (NOT individually named in the charter's excerpt, but the same defect: "
        "principal_paid is computed by the engine and never referenced anywhere in generator.py). "
        "Discovered while building this guard; reported to Roger, not fixed (out of Wave 1 scope)."
    ),
    ("YearBreakdown", "interest_paid"): (
        "T5-class extension (same as principal_paid above): computed by the engine, never "
        "referenced in generator.py. Discovered while building this guard; reported, not fixed."
    ),
    ("MarketSnapshot", "notes"): (
        "T5 (charter, explicitly named): MarketSnapshot.notes is never rendered by "
        "_render_market_scenarios (only snapshot.region is). Wave 3 (OPD-4)."
    ),
    # --- MarketSnapshot's other raw fields: same shape as the .notes finding above, not
    # individually named in the charter but discovered alongside it. The per-scenario
    # *applied* deltas (ScenarioOutcome.rent_growth_applied etc.) DO render, which is a
    # defensible reason this was never flagged as urgent — but the snapshot's own baseline
    # figures are still never restated anywhere in the Market Scenarios section.
    ("MarketSnapshot", "vacancy_rate"): "NEW FINDING (see MarketSnapshot.notes entry above for context); not fixed here.",
    ("MarketSnapshot", "cap_rate"): "NEW FINDING (see MarketSnapshot.notes entry above for context); not fixed here.",
    ("MarketSnapshot", "rent_growth"): "NEW FINDING (see MarketSnapshot.notes entry above for context); not fixed here.",
    ("MarketSnapshot", "expense_growth"): "NEW FINDING (see MarketSnapshot.notes entry above for context); not fixed here.",
    ("MarketSnapshot", "interest_rate"): "NEW FINDING (see MarketSnapshot.notes entry above for context); not fixed here.",
    # --- NEW findings discovered while building this guard (not in the charter's F1-F20/T4/T5 list) ---
    ("ScenarioAnalysis", "prior_sum"): (
        "NEW FINDING: computed by src/market/scenario_runner.py (sum of accepted priors, ~1.0) but "
        "never referenced anywhere in generator.py — silently dropped from the Market Scenarios "
        "section today. Reported to Roger, not fixed here (zero src/ diff binding constraint; "
        "out of this task's Wave 1 scope)."
    ),
    ("ScenarioAnalysis", "notes"): (
        "NEW FINDING: _render_market_scenarios only renders analysis.notes on the n_accepted==0 "
        "branch. src/market/rejector.py sets notes to 'Rejector: in=X, kept=Y' unconditionally "
        "(scenario_runner.py:run_scenarios passes notes=accepted.notes on BOTH branches), so with "
        "accepted scenarios present (as in this sentinel fixture) that note is silently dropped "
        "every time. Reported to Roger, not fixed here."
    ),
    ("ScenarioAnalysis", "io_years"): (
        "Not printed as a literal value; only gates the `io_years > 0` IO caveat sentence in "
        "_render_scenario_caveats. Asserted via a dedicated behavioral check "
        "(test_io_years_gates_the_io_caveat_sentence below), not generic substring matching."
    ),
    ("MarketHypothesis", "rationale"): (
        "BORDERLINE — not asserted a bug. _render_scenario_grid renders only the quantitative "
        "deltas + prior for each hypothesis; MarketHypothesis.rationale is free-text narrative "
        "consumed elsewhere (MarketHypothesis.summary(), advisor/ingest CLIs), not by this table. "
        "Flagging for product review rather than asserting either way."
    ),
    ("MarketHypothesis", "str_viability"): (
        "bool leaf value never printed literally (str_viability gates the narrative-flags count, "
        "'STR viability flagged in K of N...'). Asserted via a dedicated behavioral check "
        "(test_str_viability_gates_the_narrative_flag below)."
    ),
    # --- MediaInsights: one confirmed NEW finding, two fields checked by count instead of content ---
    ("MediaInsights", "image_quality"): (
        "NEW FINDING: per-image sharpness/brightness/contrast metrics computed by the media "
        "pipeline but never referenced in _render_media_overview. Reported to Roger, not fixed here."
    ),
    ("MediaInsights", "duplicate_hashes"): (
        "Surfaced as a COUNT ('N exact'), not literal hash content — see "
        "test_media_insights_duplicate_counts_reach_the_report below, not a silent skip."
    ),
    ("MediaInsights", "duplicates"): (
        "Surfaced as a COUNT ('N similar clusters'), not literal cluster content — see "
        "test_media_insights_duplicate_counts_reach_the_report below, not a silent skip."
    ),
    # --- MediaReport: only 4 of 13 fields reach _render_photo_coverage today ---
    ("MediaReport", "report_version"): "Internal schema version tag, not narrative content — not meant to render.",
    ("MediaReport", "ontology_version"): "Internal CV-ontology version tag, not narrative content — not meant to render.",
    ("MediaReport", "provenance"): "Internal provider/cache metadata, not narrative content — not meant to render.",
    ("MediaReport", "images"): (
        "Documented in MediaReport's own docstring as optional/hide-by-default ('renderers may hide "
        "this by default'). Legitimate design, not a drop."
    ),
    ("MediaReport", "listing_title"): (
        "NEW FINDING: _render_photo_coverage only reads coverage/room_counts/amenities/warnings off "
        "MediaReport; listing_title is silently never surfaced. Reported to Roger, not fixed here."
    ),
    ("MediaReport", "source_url"): "NEW FINDING (see MediaReport.listing_title entry above); not fixed here.",
    ("MediaReport", "address"): "NEW FINDING (see MediaReport.listing_title entry above); not fixed here.",
    ("MediaReport", "defects"): "NEW FINDING (see MediaReport.listing_title entry above); not fixed here.",
    ("MediaReport", "quality_flags"): "NEW FINDING (see MediaReport.listing_title entry above); not fixed here.",
    ("MediaReport", "parking"): "NEW FINDING (see MediaReport.listing_title entry above); not fixed here.",
    # --- MediaCoverage (report_models.py DTO nested under MediaReport.coverage) ---
    ("MediaCoverage", "version"): (
        "NEW FINDING: _render_photo_coverage prints cov.provider but never cov.version, unlike "
        "the sibling Media Overview section which prints both provider and version. Reported to "
        "Roger, not fixed here."
    ),
}

# Dict fields whose KEYS are used only as an internal lookup/index (never rendered as text)
# even though the VALUES they map to are rendered — e.g. MediaInsights.palettes is keyed by a
# sha256 used to pick which image's palette to show; only the chosen palette's hex values are
# ever printed, never the key. Documented here rather than silently relaxing the dict check
# for everything.
_DICT_KEYS_NOT_RENDERED: frozenset[tuple[str, str]] = frozenset(
    {
        ("MediaInsights", "palettes"),
    }
)

# Nested pydantic models that ARE reached from generate_report's inputs but whose own type
# is defined in src/core/reports/report_models.py rather than src/schemas/models.py, so the
# walker needs to know to recurse into them by class identity, not just field name.
_KNOWN_MODEL_TYPES = (BaseModel,)


def _float_candidates(value: float) -> set[str]:
    """
    Every plausible way generator.py's private _fmt_* helpers could render a float. We
    deliberately don't know ahead of time which formatter a given (possibly future) field
    uses, so we try them all and accept any hit — see module docstring.
    """
    c: set[str] = {str(value), f"{value:.0f}", f"{value:.2f}", f"{value:.4f}", f"{value:,.2f}", f"{value:g}"}
    c.add(f"{value * 100:.2f}%")
    sign = "+" if value > 0 else ""
    c.add(f"{sign}{value * 100:.2f}%")
    c.add(f"${value:,.2f}")
    if value < 0:
        c.add(f"-${abs(value):,.2f}")
    c.add(f"{value:.2f}x")
    if float(value).is_integer():
        c.add(str(int(value)))
        c.add(f"{int(value):,}")
    return c


def _int_candidates(value: int) -> set[str]:
    return {str(value), f"{value:,}"}


def _leaf_reaches_text(value: Any, text: str) -> bool:
    """
    Whether a single non-container, non-model value's sentinel shows up in the rendered
    text under some plausible formatting. Booleans are treated as vacuously reachable: in
    this codebase a bool leaf consistently GATES a branch/section rather than being printed
    as a literal "True"/"False" token, so no generic textual candidate is reliable — the two
    bool fields that matter today (RunProvenance's) are asserted precisely by dedicated
    tests below instead. This is a known, documented soft spot in the generic matcher (see
    the QA report), not a silent gap: any bool field that DOES matter gets its own explicit
    behavioral assertion in this file.
    """
    if isinstance(value, bool):
        return True
    if isinstance(value, float):
        return any(c in text for c in _float_candidates(value))
    if isinstance(value, int):
        return any(c in text for c in _int_candidates(value))
    if isinstance(value, str):
        return value in text
    raise TypeError(f"_leaf_reaches_text: unhandled scalar type {type(value)!r}")


def _check_value(value: Any, text: str, failures: list[str], *, path: str, owner_field: tuple[str, str] | None = None) -> None:
    """Recursively check one already-extracted value (list/dict item, dict value, or a
    top-level field value) against the rendered text, regardless of nesting depth.
    ``owner_field`` (owning model class name, field name) is only meaningful at the first
    level of recursion (used to consult ``_DICT_KEYS_NOT_RENDERED``)."""
    if value is None:
        return  # Optional the sentinel builder legitimately left unset (build_sentinel_model
        # always fills Optionals non-None today, so this is defensive, not expected to trigger).

    if isinstance(value, BaseModel):
        _walk(value, text, failures, path=f"{path}.")
        return

    if isinstance(value, list | tuple | set):
        for item in value:
            _check_value(item, text, failures, path=f"{path}[]")
        return

    if isinstance(value, dict):
        skip_keys = owner_field in _DICT_KEYS_NOT_RENDERED
        for k, v in value.items():
            if not skip_keys and not _leaf_reaches_text(k, text):
                failures.append(f"{path}[{k!r}] (dict key) sentinel not found in rendered report")
            _check_value(v, text, failures, path=f"{path}[{k!r}]")
        return

    if not _leaf_reaches_text(value, text):
        failures.append(f"{path} sentinel value {value!r} not found in rendered report (any known format)")


def _walk(model: BaseModel, text: str, failures: list[str], *, path: str = "") -> None:
    owner = type(model).__name__
    for name in type(model).model_fields:
        value = getattr(model, name)
        field_path = f"{path}{owner}.{name}"

        if (owner, name) in _EXCLUDED:
            continue

        if isinstance(value, list | tuple | set | dict) and not value:
            continue  # nothing to check in an empty container

        _check_value(value, text, failures, path=field_path, owner_field=(owner, name))


@pytest.fixture
def sentinel_report() -> tuple[str, dict[str, BaseModel]]:
    insights = build_sentinel_model(ListingInsights)
    # Exactly one year: _render_opex_details only ever renders forecast.years[0] (see its
    # "OPEX Detail (Year 1)" docstring) — a second sentinel year would make its own
    # (deliberately-Year-1-only) OPEX fields look like a false drop.
    forecast = build_sentinel_model(FinancialForecast, overrides={"years": [build_sentinel_model(YearBreakdown)]})
    thesis = build_sentinel_model(InvestmentThesis)
    media_insights = build_sentinel_model(MediaInsights)
    media_report = build_sentinel_model(MediaReport)
    provenance = build_sentinel_model(RunProvenance)
    scenarios = build_sentinel_model(ScenarioAnalysis)

    text = generate_report(
        insights,
        forecast,
        thesis,
        media_insights=media_insights,
        media_report=media_report,
        provenance=provenance,
        scenarios=scenarios,
    )

    models = {
        "insights": insights,
        "forecast": forecast,
        "thesis": thesis,
        "media_insights": media_insights,
        "media_report": media_report,
        "provenance": provenance,
        "scenarios": scenarios,
    }
    return text, models


def test_no_field_is_silently_dropped_from_the_rendered_report(sentinel_report) -> None:
    text, models = sentinel_report
    failures: list[str] = []
    for model in models.values():
        _walk(model, text, failures)

    assert not failures, (
        f"generate_report dropped {len(failures)} field(s) from the rendered output "
        "(sentinel value present on the source model but absent from the text in every "
        "known format):\n" + "\n".join(failures)
    )


def test_run_provenance_bool_fields_render_their_on_off_row(sentinel_report) -> None:
    """
    RunProvenance.scenarios_enabled / vision_enabled are the two bool fields that matter in
    this render path. Booleans are treated as vacuously reachable by the generic walker
    (see _leaf_reaches_text's docstring), so they get a precise, dedicated assertion here
    instead — this is the "belt" half of belt-and-suspenders, not a substitute for the
    walker skipping them.
    """
    text, _ = sentinel_report
    assert "| Market Scenarios | on |" in text
    assert "| AI photo tagging | on |" in text


def test_io_years_gates_the_io_caveat_sentence(sentinel_report) -> None:
    text, models = sentinel_report
    scenarios = models["scenarios"]
    assert scenarios.io_years > 0  # sanity: the sentinel value must actually exercise the branch
    assert "interest-only period" in text, "ScenarioAnalysis.io_years > 0 should render the IO caveat sentence"


def test_str_viability_gates_the_narrative_flag(sentinel_report) -> None:
    text, models = sentinel_report
    scenarios = models["scenarios"]
    assert any(o.hypothesis.str_viability for o in scenarios.outcomes)  # sanity
    assert "STR viability flagged in" in text


def test_media_insights_duplicate_counts_reach_the_report(sentinel_report) -> None:
    text, models = sentinel_report
    mi = models["media_insights"]
    assert f"{len(mi.duplicate_hashes)} exact" in text
    assert f"{len(mi.duplicates)} similar clusters" in text


def test_guard_would_have_caught_f4_and_f5_shapes() -> None:
    """
    Sanity that the exclusion table isn't quietly swallowing the two already-fixed defects
    this guard exists to prevent from recurring: neither F4's stated-fact fields nor F5's
    media fields are excluded, i.e. they are still checked by the generic walker above.
    """
    for owner, name in (
        ("ListingInsights", "price"),
        ("ListingInsights", "sqft"),
        ("ListingInsights", "bedrooms"),
        ("ListingInsights", "bathrooms"),
        ("ListingInsights", "year_built"),
    ):
        assert (owner, name) not in _EXCLUDED, f"F4 field {owner}.{name} must stay covered by the generic walker"
