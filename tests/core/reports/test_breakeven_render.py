# tests/core/reports/test_breakeven_render.py
"""
Mission 5 (task N2): rendering coverage for "How wrong can these guesses be?" — the assumption
breakeven / margin-of-safety section (`_render_breakeven` and friends in
`src/core/reports/generator.py`).

Two tests in this file are load-bearing and everything else supports them.

`test_undetermined_never_renders_as_safety` is the first. An `undetermined` row means the probe
budget ran out — *we stopped looking* — and rendering it as room would tell an investor a guess is
safe when the truth is that this run never established anything about it. It is pinned three ways:
the bullet must state the exhaustion, it must carry the explicit denial, and it must contain none
of the vocabulary the other two outcomes use. A fourth test proves the renderer BRANCHES ON
`outcome` rather than inferring it from `margin`/`breakeven_value` being None — None is true of
BOTH an `undetermined` and a proven `never_breaks_in_range`, and that inference is exactly the
shortcut that would produce the lie.

`test_displayed_margin_never_rounds_away_from_zero` is the second. `margin` is truncated toward
zero at the 0.1 percentage-point display step, never rounded to nearest: a rendered margin that is
larger than the measured one is room nobody measured, and on the razor-thin real rows this section
produces (82 Champlain's IRR-vs-occupancy row has 0.046 pp of it) the difference between a floor
and a round is the difference between "essentially none" and "some".

Fixtures are the two committed sample deals plus one refinancing deal, so the rendered copy is
verified against real engine numbers rather than hand-typed payloads — plus small hand-built
`AssumptionBreakeven` rows for the states production does not currently exhibit at its default
budget.
"""

from __future__ import annotations

import math
import re

import pytest

from src.core.finance.engine import run_financial_model
from src.core.reports.generator import (
    _BREAKEVEN_HEADING_TEXT,
    _BREAKEVEN_NOMINAL_EDGE,
    ABOUT_BREAKEVEN_BLOCK,
    _breakeven_margin_pp,
    _fmt_breakeven_margin,
    _render_breakeven,
    _render_breakeven_row,
    generate_report,
)
from src.inputs.inputs import load_inputs
from src.market.breakeven import compute_breakevens
from src.market.recourse import compute_recourse
from src.schemas.models import (
    AssumptionBreakeven,
    BreakevenAnalysis,
    FinancialInputs,
    FinancingTerms,
    IncomeModel,
    MarketAssumptions,
    OperatingExpenses,
    RefinancePlan,
    UnitIncome,
)

_CHAMPLAIN = "data/sample_listings/82_champlain_dieppe/inputs.json"
_KELLY = "data/sample_listings/36_kelly_moncton/inputs.json"

#: Vocabulary that asserts, in one form or another, that there IS room. No `undetermined` bullet
#: may contain any of it: that outcome establishes nothing about how much room a guess has.
_SAFETY_WORDS = ("clears until", "still clears", "does not depend", "of room", "never breaks", "cleared the bar")

#: Imperative / advisory verbs. GD3 forbids this section from ever asking a reader to change an
#: assumption, so none of these may appear anywhere in the rendered section.
_ASK_WORDS = ("assume ", "raise your", "lower your", "increase your", "reduce your", "set your", "you should", "consider ")


def _champlain() -> FinancialInputs:
    return load_inputs(_CHAMPLAIN).inputs


def _kelly() -> FinancialInputs:
    return load_inputs(_KELLY).inputs


def _refi_deal() -> FinancialInputs:
    """A refinancing deal — the case where the engine REFUSES to model the nominal adverse edge
    (deep enough adversity drives year-5 NOI negative, so the NOI-based refi valuation implies a
    negative loan and `amortization.schedule_columns` raises). The search clips its edge in to the
    adverse-most modelable value; this file pins that the copy stops claiming the nominal range
    when it does. Mirrors `tests/integration/test_orchestrator_crewai.py`'s own fixture."""
    return FinancialInputs(
        financing=FinancingTerms(
            purchase_price=500_000.0, closing_costs=10_000.0, down_payment_rate=0.25, interest_rate=0.055, amort_years=30, io_years=0
        ),
        opex=OperatingExpenses(
            insurance=2400.0,
            taxes=6000.0,
            utilities=3600.0,
            water_sewer=1800.0,
            property_management=4800.0,
            repairs_maintenance=2400.0,
            trash=1200.0,
            landscaping=800.0,
            snow_removal=600.0,
            hoa_fees=0.0,
            reserves=1500.0,
            other=500.0,
            expense_growth=0.02,
        ),
        income=IncomeModel(
            units=[UnitIncome(rent_month=1200.0, other_income_month=50.0)] * 2
            + [UnitIncome(rent_month=1200.0, other_income_month=0.0)] * 2,
            occupancy=0.95,
            bad_debt_factor=0.97,
            rent_growth=0.03,
        ),
        refi=RefinancePlan(do_refi=True, year_to_refi=5, refi_ltv=0.75),
        market=MarketAssumptions(cap_rate_spread_target=0.015, cap_rate_floor=None),
    )


@pytest.fixture(scope="module")
def champlain_breakeven() -> BreakevenAnalysis:
    return compute_breakevens(_champlain())


@pytest.fixture(scope="module")
def kelly_breakeven() -> BreakevenAnalysis:
    return compute_breakevens(_kelly())


@pytest.fixture(scope="module")
def undetermined_breakeven() -> BreakevenAnalysis:
    """Real 82 Champlain numbers with the per-row budget cut to one probe — the honest way to
    force `undetermined` without hand-typing a payload the search would never emit."""
    return compute_breakevens(_champlain(), max_iter=1)


@pytest.fixture(scope="module")
def refi_breakeven() -> BreakevenAnalysis:
    return compute_breakevens(_refi_deal())


def _text(analysis: BreakevenAnalysis, *, recourse_rendered: bool = True) -> str:
    return _render_breakeven(analysis, recourse_rendered=recourse_rendered)


def _row(**overrides: object) -> AssumptionBreakeven:
    """A hand-built row, defaulted to a plausible `breakeven_found` occupancy/DSCR shape."""
    base: dict[str, object] = {
        "guardrail": "dscr",
        "assumption": "occupancy",
        "assumed_value": 0.95,
        "adverse_direction": "down",
        "searched_to": 1e-6,
        "outcome": "breakeven_found",
        "breakeven_value": 0.906,
        "margin": 0.044,
        "metric_at_breakeven": 1.19,
        "bar": 1.20,
        "metric_moves": True,
        "resolution": 5e-4,
        "probes_used": 13,
    }
    base.update(overrides)
    return AssumptionBreakeven(**base)  # type: ignore[arg-type]


def _analysis(*rows: AssumptionBreakeven, **overrides: object) -> BreakevenAnalysis:
    base: dict[str, object] = {
        "attempted": True,
        "passing_guardrails": ("dscr",),
        "failing_guardrails": (),
        "rows": rows,
        "max_iter": 24,
    }
    base.update(overrides)
    return BreakevenAnalysis(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# THE HONESTY CORE: an `undetermined` never renders as safety
# ---------------------------------------------------------------------------


def test_undetermined_never_renders_as_safety(undetermined_breakeven: BreakevenAnalysis) -> None:
    """The load-bearing test of this file. `undetermined` means the budget ran out — this run
    established NOTHING about how much room the guess has — and every one of its bullets has to
    say so and carry the denial, without borrowing a word from the outcomes that did establish
    something."""
    rows = [r for r in undetermined_breakeven.rows if r.outcome == "undetermined"]
    assert rows, "max_iter=1 must produce at least one undetermined row for this fixture"

    for row in rows:
        bullet = _render_breakeven_row(row, max_iter=undetermined_breakeven.max_iter)
        assert "**not determined within budget.**" in bullet
        assert "does not know how much room there is" in bullet
        assert "That is not a finding that there is room to spare." in bullet
        for word in _SAFETY_WORDS:
            assert word not in bullet.lower(), f"undetermined bullet borrowed safety language {word!r}: {bullet}"


def test_undetermined_and_never_breaks_share_no_language(undetermined_breakeven: BreakevenAnalysis) -> None:
    """The two outcomes that both carry `margin=None` must not be confusable at a glance."""
    undet = next(r for r in undetermined_breakeven.rows if r.outcome == "undetermined")
    never = next(r for r in undetermined_breakeven.rows if r.outcome == "never_breaks_in_range")

    a = _render_breakeven_row(undet, max_iter=1)
    b = _render_breakeven_row(never, max_iter=1)
    assert a != b
    assert "not determined" in a and "not determined" not in b
    assert "not determined" not in b.lower()


def test_row_reads_the_outcome_field_and_never_infers_it_from_a_missing_margin() -> None:
    """Two rows identical in EVERY field but `outcome` (and the `metric_moves` the schema pairs
    with it) must render as different claims. `breakeven_value` and `margin` are None on both, so a
    renderer that inferred the outcome from their absence — the shortcut that would report "we
    stopped looking" as "nothing breaks it" — would collapse these two into one sentence."""
    common = dict(breakeven_value=None, margin=None, metric_at_breakeven=None, searched_to=1e-6, probes_used=1)
    never = _row(outcome="never_breaks_in_range", metric_moves=True, **common)
    undet = _row(outcome="undetermined", metric_moves=True, **common)

    rendered_never = _render_breakeven_row(never, max_iter=24)
    rendered_undet = _render_breakeven_row(undet, max_iter=24)
    assert rendered_never != rendered_undet
    assert "still clears at every vacancy searched" in rendered_never
    assert "not determined within budget" in rendered_undet


def test_undetermined_section_states_the_budget_it_ran_out_of(undetermined_breakeven: BreakevenAnalysis) -> None:
    """Provenance for the claim: a reader must be able to see WHAT budget was exhausted, and the
    closing methodology must agree with the bullets rather than quoting a different number."""
    text = _text(undetermined_breakeven)
    assert "budget of 1 model re-run before" in text
    assert "budget of 1 model re-run per line" in text
    assert "model re-runs per line" not in text, "the budget bullet must pluralize with max_iter"


# ---------------------------------------------------------------------------
# THE OTHER HONESTY CORE: the displayed margin never rounds away from zero
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("margin", "expected"),
    [
        (0.0065, "0.6 percentage points of room"),  # 0.65 pp: `round` would say 0.7 — room nobody measured
        (0.0069999, "0.6 percentage points of room"),
        (0.006494133789062495, "0.6 percentage points of room"),  # 36 Kelly, occupancy x IRR, measured
        (0.15957014453125007, "15.9 percentage points of room"),  # 36 Kelly, occupancy x cap floor, measured
        (0.055664003906249926, "5.5 percentage points of room"),  # 82 Champlain, occupancy x Y1 cash flow
        (0.0004638666992187179, "Less than 0.1 percentage points of room"),  # the razor-thin real row
        (0.0009999, "Less than 0.1 percentage points of room"),
        (0.001, "0.1 percentage points of room"),
    ],
)
def test_displayed_margin_never_rounds_away_from_zero(margin: float, expected: float) -> None:
    """The second load-bearing test. The displayed room is a FLOOR of the measured room, at the
    0.1 percentage-point step: never larger than what the search actually measured, in any case."""
    assert _fmt_breakeven_margin(margin) == expected
    assert _breakeven_margin_pp(margin) <= margin * 100.0 + 1e-12


@pytest.mark.parametrize("scale", [1, 3, 7, 11, 23, 97, 331, 1009])
def test_displayed_margin_is_a_floor_across_the_whole_range(scale: int) -> None:
    """Property form of the same rule, swept across the range a real margin can occupy: the
    rendered figure is never above the measured one, and never negative."""
    for i in range(1, 200):
        margin = (i * scale) / 100_000.0
        shown = _breakeven_margin_pp(margin)
        assert 0.0 <= shown <= margin * 100.0 + 1e-12
        assert math.isclose(shown, round(shown, 1), abs_tol=1e-9)


def test_a_margin_too_small_to_show_never_renders_as_zero(champlain_breakeven: BreakevenAnalysis) -> None:
    """82 Champlain's IRR-vs-occupancy row has 0.046 pp of room. "0.0 percentage points" reads as
    a rounding artifact; the truth is a razor margin, and the copy has to say that in words."""
    row = next(r for r in champlain_breakeven.rows if r.assumption == "occupancy" and r.guardrail == "irr")
    assert row.outcome == "breakeven_found" and row.margin is not None and row.margin < 0.001
    bullet = _render_breakeven_row(row, max_iter=champlain_breakeven.max_iter)
    assert "**Less than 0.1 percentage points of room**" in bullet
    assert "0.0 percentage points" not in bullet


def test_displayed_crossing_never_sits_beyond_the_measured_one(
    champlain_breakeven: BreakevenAnalysis, kelly_breakeven: BreakevenAnalysis
) -> None:
    """Every rendered crossing is on the ASSUMED side of the value the engine actually confirmed
    failing — the same never-overstate rule applied to the level rather than the distance."""
    for analysis in (champlain_breakeven, kelly_breakeven):
        for row in analysis.rows:
            if row.outcome != "breakeven_found":
                continue
            assert row.breakeven_value is not None
            bullet = _render_breakeven_row(row, max_iter=analysis.max_iter)
            match = re.search(r"(?:reaches|falls to) (-?\d+\.\d)%", bullet)
            assert match is not None, bullet
            shown = float(match.group(1)) / 100.0
            true_display = 1.0 - row.breakeven_value if row.assumption == "occupancy" else row.breakeven_value
            assumed_display = 1.0 - row.assumed_value if row.assumption == "occupancy" else row.assumed_value
            # "On the assumed side" = no further from the assumption than the measured crossing.
            assert abs(shown - assumed_display) <= abs(true_display - assumed_display) + 1e-9, bullet


# ---------------------------------------------------------------------------
# Scoping: a "never breaks" is only as strong as the range it was searched over
# ---------------------------------------------------------------------------


def test_never_breaks_names_its_own_searched_edge() -> None:
    """A `never_breaks_in_range` whose metric DOES move is the strong result — and it is only as
    strong as the range it covered, so the bullet has to carry that range itself rather than lean
    on the block lead a screenshot might crop out."""
    row = _row(
        outcome="never_breaks_in_range",
        metric_moves=True,
        breakeven_value=None,
        margin=None,
        metric_at_breakeven=None,
        probes_used=1,
    )
    bullet = _render_breakeven_row(row, max_iter=24)
    assert "still clears at every vacancy searched, out to 100.0%." in bullet
    assert "of room" not in bullet
    assert "not determined" not in bullet


def test_expense_growth_edge_is_named_a_search_ceiling_and_the_others_are_not(champlain_breakeven: BreakevenAnalysis) -> None:
    """The binding scoping rule. Vacancy's and rent growth's edges are the genuine ends of what
    those assumptions can be; operating-expense growth's +100%/yr is a ceiling this project chose,
    and the copy must not let the weaker result borrow the stronger one's authority."""
    text = _text(champlain_breakeven)
    ceiling = "**That is where this search stopped, not where reality stops**"
    assert ceiling in text
    assert text.count(ceiling) == 1, "only the operating-expense-growth block may carry the ceiling caveat"

    expense_block = text.split("**Operating-expense growth —")[1]
    assert ceiling in expense_block
    vacancy_block = text.split("**Vacancy —")[1].split("**Rent growth —")[0]
    assert "the whole range this assumption has, not a limit of the search" in vacancy_block
    rent_block = text.split("**Rent growth —")[1].split("**Operating-expense growth —")[0]
    assert "the arithmetic floor of this assumption, not a limit of the search" in rent_block


def test_a_clipped_edge_never_claims_the_nominal_range(refi_breakeven: BreakevenAnalysis) -> None:
    """On a refinancing deal the engine refuses to model the nominal adverse edge, so the search
    clips in. The copy must then stop claiming "the arithmetic floor" / "the whole range" and say
    what it actually did — otherwise a narrower search would ship in a wider search's words."""
    clipped = [r for r in refi_breakeven.rows if r.searched_to != _BREAKEVEN_NOMINAL_EDGE[r.assumption]]
    assert clipped, "the refi fixture must produce at least one clipped edge"

    text = _text(refi_breakeven, recourse_rendered=False)
    assert "as far as this deal can be modeled along this assumption" in text
    assert "the arithmetic floor of this assumption" not in text
    # The clipped edge itself is on the page, so the scope is a number a reader can check.
    for row in clipped:
        display = row.searched_to if row.assumption != "occupancy" else 1.0 - row.searched_to
        assert f"{display * 100:.1f}%" in text


def test_nominal_edge_mirror_matches_the_search() -> None:
    """Drift guard for `_BREAKEVEN_NOMINAL_EDGE`. `src/core/reports` does not import
    `src/market`, so the report mirrors the search's three adverse edges — and this test is what
    stops the mirror going stale, which would make every clipped edge render as a nominal one."""
    from src.market.breakeven import (
        _EXPENSE_GROWTH_ADVERSE_EDGE,
        _OCCUPANCY_ADVERSE_EDGE,
        _RENT_GROWTH_ADVERSE_EDGE,
    )

    assert _BREAKEVEN_NOMINAL_EDGE == {
        "occupancy": _OCCUPANCY_ADVERSE_EDGE,
        "rent_growth": _RENT_GROWTH_ADVERSE_EDGE,
        "expense_growth": _EXPENSE_GROWTH_ADVERSE_EDGE,
    }


def test_metric_moves_false_says_the_guardrail_does_not_depend_on_the_assumption(champlain_breakeven: BreakevenAnalysis) -> None:
    row = next(r for r in champlain_breakeven.rows if not r.metric_moves)
    bullet = _render_breakeven_row(row, max_iter=champlain_breakeven.max_iter)
    assert "does not depend on" in bullet and " at all:" in bullet
    assert "still clears at every" not in bullet


def test_a_degenerate_bracket_reports_no_measurement_rather_than_a_margin() -> None:
    """An assumed value already at the adverse edge leaves nothing to search. That is the absence
    of a measurement, and must never be dressed up as a margin."""
    row = _row(
        assumption="expense_growth",
        assumed_value=1.0,
        adverse_direction="up",
        searched_to=1.0,
        outcome="never_breaks_in_range",
        metric_moves=False,
        breakeven_value=None,
        margin=None,
        metric_at_breakeven=None,
        probes_used=0,
    )
    text = _text(_analysis(row))
    block = text.split("**Operating-expense growth —")[1].split("**How these numbers were produced**")[0]
    assert "there was no adverse room left to search" in block
    assert "of room" not in block
    assert "still clears at every" not in block


# ---------------------------------------------------------------------------
# GD3: a fragility, never an ask
# ---------------------------------------------------------------------------


def test_no_assumption_is_ever_presented_as_something_to_change(
    champlain_breakeven: BreakevenAnalysis, kelly_breakeven: BreakevenAnalysis, undetermined_breakeven: BreakevenAnalysis
) -> None:
    """GD3. The section may report that a guess is fragile; it may never ask a reader to move one.
    The honesty block quotes the forbidden sentence in order to disown it, so it is excluded from
    the scan and checked separately below."""
    for analysis in (champlain_breakeven, kelly_breakeven, undetermined_breakeven):
        body = _text(analysis).replace(ABOUT_BREAKEVEN_BLOCK, "")
        # The methodology quotes the forbidden shape once, also to disown it.
        body = body.replace('"it would pass if vacancy were 1%"', "")
        for word in _ASK_WORDS:
            assert word not in body.lower(), f"advisory language {word!r} reached the section: {body}"


def test_the_honesty_block_disowns_the_forbidden_sentence_in_the_report_itself() -> None:
    assert "**Nothing here is a target.**" in ABOUT_BREAKEVEN_BLOCK
    assert "a measurement of how fragile the deal is" in ABOUT_BREAKEVEN_BLOCK
    assert "has no field it could say it in" in ABOUT_BREAKEVEN_BLOCK


def test_failing_guardrails_are_named_as_absent_and_get_no_row(champlain_breakeven: BreakevenAnalysis) -> None:
    """A failing guardrail has no margin of safety, so it gets no line — and the lead has to say
    that in words, or a reader will read the silence as a pass."""
    assert champlain_breakeven.failing_guardrails
    text = _text(champlain_breakeven)
    assert "do not appear below, and their absence is not a pass." in text
    assert "a guardrail that is already failing has no room left to lose" in text
    for row in champlain_breakeven.rows:
        assert row.guardrail in champlain_breakeven.passing_guardrails


def test_barred_axes_are_named_as_excluded_and_never_measured(champlain_breakeven: BreakevenAnalysis) -> None:
    """Exit cap, cap drift and the hold horizon are barred from this surface. Saying so is what
    keeps their absence from reading as "these do not matter"."""
    text = _text(champlain_breakeven)
    assert "The exit cap rate, cap-rate drift and the hold period are modeling assumptions too" in text
    assert "deliberately\nnot measured here" in text or "deliberately not measured here" in text
    assert all(row.assumption in ("occupancy", "rent_growth", "expense_growth") for row in champlain_breakeven.rows)


# ---------------------------------------------------------------------------
# Display transforms, states and placement
# ---------------------------------------------------------------------------


def test_vacancy_is_displayed_as_one_minus_occupancy(champlain_breakeven: BreakevenAnalysis) -> None:
    text = _text(champlain_breakeven)
    assert "**Vacancy — you assumed 5.0%.**" in text  # inputs.json carries occupancy 0.95
    assert "an occupancy of 0.95 is the 5.0% vacancy quoted above" in text  # the transform, stated and checkable
    assert "**Occupancy — you assumed" not in text


def test_not_attempted_and_absent_analyses_render_nothing() -> None:
    assert _render_breakeven(None, recourse_rendered=True) == ""
    empty = _analysis(attempted=False, passing_guardrails=(), failing_guardrails=("dscr",), rows=())
    assert _render_breakeven(empty, recourse_rendered=True) == ""


def test_render_is_byte_identical_across_two_calls(champlain_breakeven: BreakevenAnalysis) -> None:
    assert _text(champlain_breakeven) == _text(champlain_breakeven)


def test_the_lead_points_at_the_recourse_section_only_when_it_rendered(champlain_breakeven: BreakevenAnalysis) -> None:
    with_recourse = _text(champlain_breakeven, recourse_rendered=True)
    without = _text(champlain_breakeven, recourse_rendered=False)
    assert 'answered under "What would have to change?" above' in with_recourse
    assert "What would have to change" not in without.replace("What would have to change about them", "")
    assert "this section does not answer it" in without


def test_the_section_sits_directly_after_what_would_have_to_change() -> None:
    """Placement. The two sections are the two halves of one question about the verdict above them
    — what you could act on, and how much room the things you guessed at have — and a reader who
    sees only one of them is reading half the answer."""
    fi = _champlain()
    forecast = run_financial_model(fi)
    md = generate_report(
        None,
        forecast,
        market=fi.market,
        recourse=compute_recourse(fi),
        breakeven=compute_breakevens(fi),
    )
    recourse_at = md.index("## What would have to change?")
    breakeven_at = md.index(f"## {_BREAKEVEN_HEADING_TEXT}")
    proforma_at = md.index("## 10-Year Pro Forma")
    assert recourse_at < breakeven_at < proforma_at
    assert "## " not in md[recourse_at + 5 : breakeven_at].replace("## What would have to change?", "")


def test_the_section_renders_without_a_recourse_section(kelly_breakeven: BreakevenAnalysis) -> None:
    """36 Kelly is not a near-miss, so recourse never runs — and the margin-of-safety question is
    still worth answering. This section is deliberately not behind that gate."""
    fi = _kelly()
    md = generate_report(None, run_financial_model(fi), market=fi.market, recourse=None, breakeven=kelly_breakeven)
    assert "## What would have to change?" not in md
    assert f"## {_BREAKEVEN_HEADING_TEXT}" in md


def test_no_exotic_markdown_and_no_new_heading_level(champlain_breakeven: BreakevenAnalysis) -> None:
    """The report renders on GitHub, in VS Code preview and in PDF export. It has no `###`
    anywhere, and this section introduces none."""
    text = _text(champlain_breakeven)
    assert "###" not in text
    assert text.count(f"## {_BREAKEVEN_HEADING_TEXT}") == 1
    for line in text.splitlines():
        assert not line.startswith("|"), "this section is deliberately bullets, not tables"


# ---------------------------------------------------------------------------
# The IRR cliff (Gate V re-review, N-B1) and the same-precision metric (N1)
# ---------------------------------------------------------------------------


def _golden_deal(case_id: str) -> FinancialInputs:
    """One unmodified deal from the project's own golden matrix -- the fixtures the Gate V
    re-review reproduced N-B1 on, used here so the rendered copy is pinned against real engine
    numbers rather than a hand-typed payload."""
    from tests.core.finance.golden_cases import CASES

    case = next(c for c in CASES if c["id"] == case_id)
    return FinancialInputs.model_validate(case["financial_inputs"])


def test_irr_cliff_row_names_the_cliff_and_never_quotes_the_sentinel() -> None:
    """N-B1, the hand-built shape: `metric_at_breakeven is None` on a `breakeven_found` IRR row
    means the confirming run's IRR was the engine's coalesced-0.0 sentinel (`breakeven.py`
    degrades it, mirroring `jacobian.py`). RED before the fix: the sentinel shipped as a number
    and this bullet read "the confirming re-run there measured 0.00%, below the bar" -- a
    fabricated measurement implying the return decayed gently to the bar, when it sat healthy
    and fell off a cliff. The margin stays (it is the measured distance to where the return
    stops being computable), but only under cliff wording, never under IRR-crossing wording."""
    row = _row(
        guardrail="irr",
        assumption="expense_growth",
        assumed_value=0.02,
        adverse_direction="up",
        searched_to=1.0,
        breakeven_value=0.245859,
        margin=0.225859,
        metric_at_breakeven=None,
        bar=0.12,
    )
    bullet = _render_breakeven_row(row, max_iter=24)
    assert "clears until operating-expense growth reaches 24.5% a year" in bullet
    assert "**22.5 percentage points of room**" in bullet  # floor-rounded, as everywhere else
    assert "could not compute an IRR at all" in bullet
    assert "not to a measured crossing of the bar" in bullet
    assert "0.00%" not in bullet  # the sentinel never renders as a measurement
    assert "below the bar." not in bullet  # no measured-crossing claim on a cliff


def test_irr_cliff_renders_from_the_re_reviews_own_golden_case() -> None:
    """End-to-end on `units_12_horizon_10`, unmodified from the golden matrix: the deal whose
    rent-growth and expense-growth IRR rows converge on the undefined-IRR boundary. The section
    must carry the cliff sentence and must never claim a 0.00% measurement anywhere."""
    analysis = compute_breakevens(_golden_deal("units_12_horizon_10"))
    cliffs = [r for r in analysis.rows if r.guardrail == "irr" and r.outcome == "breakeven_found" and r.metric_at_breakeven is None]
    assert cliffs, "fixture regressed: expected at least one IRR-cliff row on this deal"
    text = _text(analysis, recourse_rendered=False)
    assert "could not compute an IRR at all" in text
    assert "measured 0.00%" not in text


@pytest.mark.parametrize(
    ("guardrail", "bar", "metric", "bar_text"),
    [
        ("dscr", 1.20, 1.1999999, "1.20"),
        ("coc", 0.03, 0.0299999, "3.00%"),
        ("spread", 0.015, 0.0149999, "1.50%"),
    ],
)
def test_a_metric_that_rounds_to_the_bar_never_contradicts_itself(guardrail: str, bar: float, metric: float, bar_text: str) -> None:
    """N1. RED before the fix: 39 of the golden matrix's 132 `breakeven_found` rows read
    "... ≥ 1.20 ... measured 1.20, below the bar" -- a sentence asserting a number is below a
    number it prints as identical. When the confirming metric rounds to the bar at the
    guardrail's OWN display precision, the words carry the fact instead -- and the metric is
    deliberately not re-rendered one digit finer, so one guardrail never appears at two
    precisions in one report."""
    row = _row(guardrail=guardrail, bar=bar, metric_at_breakeven=metric)  # type: ignore[arg-type]
    bullet = _render_breakeven_row(row, max_iter=24)
    assert "measured just below the bar, within one display step of it." in bullet
    assert f"measured {bar_text}, below the bar" not in bullet


def test_a_metric_distinct_at_display_precision_still_quotes_the_number() -> None:
    """The N1 fix's scope pin: when the two do NOT round equal, the measured number still ships
    verbatim at the guardrail's own precision -- the honest, checkable form."""
    bullet = _render_breakeven_row(_row(metric_at_breakeven=1.19), max_iter=24)
    assert "measured 1.19, below the bar." in bullet
    assert "just below the bar" not in bullet
