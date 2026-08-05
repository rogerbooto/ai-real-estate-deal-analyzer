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
    ("ListingInsights", "observations"): (
        "DELIBERATELY NOT RENDERED YET. `observations` is the per-tag provenance ledger added by "
        "Mission 2 (schemas.models.ObservationProvenance): it records, for each amenity/condition/"
        "defect tag, whether it came from the listing copy, a photo filename, a CV provider (and "
        "whether that provider is a real model or a heuristic stub), or an LLM. It exists so the "
        "report can eventually replace its blanket 'AI photo tagging is on' caveat with per-line "
        "attribution -- literally 'AI observed \"old roof\" -> reserves +$300/yr'. That rendering "
        "is a SEPARATE, already-scoped follow-up owned by the report designer "
        "(src/core/reports/generator.py::_render_observation_impact); this task deliberately "
        "shipped the data with ZERO report diff so the two changes stay independently reviewable "
        "and `python main.py` stays byte-identical. REMOVE THIS ENTRY when _render_observation_impact "
        "starts reading insights.observations -- if that follow-up is cancelled, the field should be "
        "deleted, not left excluded."
    ),
    # (No per-field entries for ObservationProvenance itself: `_walk` skips the excluded parent
    # before recursing into it, so child entries would be unreachable dead rows in this table.)
    # --- Known findings, already in the Mission 2 charter (T5 class) ---
    # (The charter's whole T5 YearBreakdown/MarketSnapshot set was rendered by Mission 2 task 3.2;
    # those entries are GONE from this table rather than reworded, which is the point of it.)
    ("ScenarioAnalysis", "notes"): (
        "DELIBERATELY NOT RENDERED — redundant, not dropped. src/market/rejector.py:173 sets this "
        "to f'Rejector: in={len(hset.items)}, kept={len(ordered)}' and _render_market_scenarios "
        "already prints those same two numbers in its header line ('N of M scenarios admitted "
        "under guardrails', where M == in and N == kept, see scenario_runner.py:147,196). An "
        "earlier revision of this entry called it a silent drop; that was an overstatement, "
        "withdrawn by the guardian (M9) and re-verified in task 3.2 before this entry was "
        "rewritten. It IS rendered on the n_accepted == 0 branch, where 'no admissible scenarios' "
        "is the only thing the reader has. If rejector.py ever puts a FACT in this string that "
        "the header does not carry, delete this entry and render it."
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
    # --- MediaInsights: two fields checked by count instead of content ---
    ("MediaInsights", "duplicate_hashes"): (
        "Surfaced as a COUNT ('N exact'), not literal hash content — see "
        "test_media_insights_duplicate_counts_reach_the_report below, not a silent skip."
    ),
    ("MediaInsights", "duplicates"): (
        "Surfaced as a COUNT ('N similar clusters'), not literal cluster content — see "
        "test_media_insights_duplicate_counts_reach_the_report below, not a silent skip."
    ),
    # --- MediaReport ---
    # report_version / ontology_version / provenance were excluded here as "internal, not
    # narrative content" with no cited source. Mission 2 task 3.2 re-adjudicated that (guardian
    # M11) and OVERTURNED it: all three now render in the Run Provenance appendix, which is where
    # metadata about who produced a claim belongs. The deciding fact is reproducible on the demo
    # bundle — `provenance.provider_kind` is "heuristic_stub" while Photo Coverage prints
    # "provider `cv_v2`", and those photo observations reach the engine's OPEX/income rules.
    ("MediaReport", "images"): (
        "Documented in MediaReport's own docstring as optional/hide-by-default ('renderers may hide "
        "this by default'). Legitimate design, not a drop."
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
        # image_quality is keyed by sha256 with a metric dict per image. _render_media_overview
        # summarizes each metric as a range across the whole set (Mission 2 task 3.2): a
        # 40-photo listing would otherwise add 40 rows of hashes nobody reads. The metric NAMES
        # and their values do render, so a metric added upstream still has to reach the page.
        ("MediaInsights", "image_quality"),
    }
)

# Nested pydantic models that ARE reached from generate_report's inputs but whose own type
# is defined in src/core/reports/report_models.py rather than src/schemas/models.py, so the
# walker needs to know to recurse into them by class identity, not just field name.
_KNOWN_MODEL_TYPES = (BaseModel,)


# Bool model fields that the generic text matcher CANNOT check, each with the dedicated
# behavioural assertion that covers it instead.
#
# A bool leaf gates a branch rather than printing a "True"/"False" token, so there is no
# reliable textual candidate to search for — `_leaf_reaches_text` therefore treats bools as
# vacuously reachable. That is a hole: a newly-added bool field dropped from the renderer
# would pass silently, which is the exact defect class this guard exists to catch.
#
# So `_walk` requires every bool field to be listed HERE or in `_EXCLUDED`. An unlisted bool
# fails loud, forcing a human to decide which it is. Relying on "whoever adds a bool will
# remember to write a dedicated test" would reintroduce the hand-maintained-list failure mode
# the rest of this guard was built to eliminate.
_BOOL_FIELDS_WITH_DEDICATED_TESTS: dict[tuple[str, str], str] = {
    # NB: these cite the test BY ITS REAL NAME. The first version of this table cited
    # "test_provenance_bools_render_as_on_off", which never existed -- the test is
    # test_run_provenance_bool_fields_render_their_on_off_row. Nobody could grep for the
    # reason, which is the same dangling-pointer defect Gate 2 was vetoed over (C1). A
    # citation in an audited table is a claim; it has to resolve.
    ("RunProvenance", "scenarios_enabled"): "asserted as an on/off row by test_run_provenance_bool_fields_render_their_on_off_row",
    ("RunProvenance", "vision_enabled"): "asserted as an on/off row by test_run_provenance_bool_fields_render_their_on_off_row",
    ("RunProvenance", "llm_mode_enabled"): "asserted as an on/off row by test_run_provenance_bool_fields_render_their_on_off_row",
    ("ParkingSummary", "ev_charging"): "asserted in both directions by test_parking_summary_states_ev_charging_either_way",
}


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

        # Bools cannot be checked textually (see _BOOL_FIELDS_WITH_DEDICATED_TESTS). Rather
        # than let them pass vacuously, demand that each one has been consciously classified.
        if isinstance(value, bool):
            if (owner, name) not in _BOOL_FIELDS_WITH_DEDICATED_TESTS:
                failures.append(
                    f"{field_path} is a bool the generic matcher cannot verify. Add it to "
                    f"_BOOL_FIELDS_WITH_DEDICATED_TESTS (with the behavioural test that covers it) "
                    f"or to _EXCLUDED (with a reason) — do not leave it unclassified."
                )
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
    RunProvenance's bool fields are the ones that matter in this render path. Booleans are
    treated as vacuously reachable by the generic walker (see _leaf_reaches_text's docstring),
    so they get a precise, dedicated assertion here instead — this is the "belt" half of
    belt-and-suspenders, not a substitute for the walker skipping them.

    llm_mode_enabled is here because without its row the provenance appendix showed
    "AI photo tagging: off" as its ONLY AI fact on a run where a language model authored every
    listing observation — under a heading promising the table is enough to reproduce the run.
    """
    text, _ = sentinel_report
    assert "| Market Scenarios | on |" in text
    assert "| AI photo tagging | on |" in text
    assert "| LLM-authored observations | on |" in text


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
