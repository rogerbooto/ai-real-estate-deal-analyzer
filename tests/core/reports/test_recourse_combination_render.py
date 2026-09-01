# tests/core/reports/test_recourse_combination_render.py
"""
Mission 5, Half B (task IB.2): rendering coverage for the multi-lever combination sub-part of
"What would have to change?" (`_render_combinations` and friends in
`src/core/reports/generator.py`).

The load-bearing test in this file is `test_undetermined_never_renders_as_a_proven_null` and its
two companions: an `undetermined` outcome means the probe budget ran out — *we stopped looking* —
and rendering it as a proven null would tell an investor "nothing can save this deal" when the
truth is "we ran out of budget". That is the mission's honesty core, and it is pinned three ways:
the two leads must not share language, the `undetermined` lead must state the exhaustion, and the
renderer must read `outcome` rather than infer it from `combinations` being empty (which is true
of BOTH outcomes, and is exactly the shortcut that would produce the lie).

Fixtures are the two committed sample deals plus one derived deal, matching
`tests/unit/test_recourse_combinations.py`'s own choices so the rendered copy is verified against
real engine numbers, never a hand-typed payload — plus small hand-built `CombinationAnalysis`
objects for the state combinations production does not currently exhibit (found-with-exhaustion,
not-attempted).
"""

from __future__ import annotations

import pytest

from src.core.finance.engine import run_financial_model
from src.core.reports.generator import (
    _COMBINATIONS_HEADING_TEXT,
    _RECOURSE_METHODOLOGY_LINES,
    ABOUT_COMBINATIONS_BLOCK,
    ABOUT_RECOURSE_BLOCK,
    ABOUT_RECOURSE_BLOCK_WITH_COMBINATIONS,
    _combination_lever_columns,
    _combination_move_cell,
    _combination_move_phrase,
    _fmt_delta_bps,
    _render_combinations,
    _render_combinations_lead,
    _render_recourse,
)
from src.inputs.inputs import load_inputs
from src.market.recourse import compute_combinations, compute_recourse
from src.schemas.models import (
    CombinationAnalysis,
    CombinationLeverMove,
    FinancialForecast,
    FinancialInputs,
    GuardrailMargin,
    MarketAssumptions,
    RecourseAnalysis,
    RecourseCombination,
)

_CHAMPLAIN = "data/sample_listings/82_champlain_dieppe/inputs.json"
_KELLY = "data/sample_listings/36_kelly_moncton/inputs.json"

#: Every model-assumption name GD3 forbids from ever appearing as something to change. The ABOUT
#: block names them on purpose, in a sentence that says they are NEVER moved, so the GD3 scan
#: below runs over the asks only.
_ASSUMPTION_WORDS = ("vacancy", "occupancy", "rent growth", "expense growth", "exit cap", "cap drift", "horizon", "hold period")


def _champlain() -> FinancialInputs:
    return load_inputs(_CHAMPLAIN).inputs


def _kelly() -> FinancialInputs:
    return load_inputs(_KELLY).inputs


def _kelly_98() -> FinancialInputs:
    """Kelly at a 2% lower price — the honest-null-with-exemplar path on real engine numbers
    (same derivation as `tests/unit/test_recourse_combinations.py::_kelly_98`)."""
    fi = _kelly()
    return fi.model_copy(update={"financing": fi.financing.model_copy(update={"purchase_price": fi.financing.purchase_price * 0.98})})


@pytest.fixture(scope="module")
def found() -> CombinationAnalysis:
    return compute_combinations(_champlain())


@pytest.fixture(scope="module")
def proven_null() -> CombinationAnalysis:
    return compute_combinations(_kelly())


@pytest.fixture(scope="module")
def null_with_exemplar() -> CombinationAnalysis:
    return compute_combinations(_kelly_98())


@pytest.fixture(scope="module")
def undetermined() -> CombinationAnalysis:
    return compute_combinations(_champlain(), max_iter=3)


@pytest.fixture(scope="module")
def champlain_recourse() -> tuple[RecourseAnalysis, FinancialForecast, MarketAssumptions]:
    """One shared recourse analysis + baseline forecast for the three seam tests below.

    Module-scoped on purpose: each of these is a real engine analysis, and `tests/perf/` times the
    same engine under a randomised test order — a test file that re-runs it once per test makes a
    neighbour's timing gate flaky for no coverage gain.
    """
    fi = _champlain()
    return compute_recourse(fi), run_financial_model(fi), fi.market


def _text(analysis: CombinationAnalysis) -> str:
    return "\n".join(_render_combinations(analysis))


def _move(lever: str, delta: float, *, baseline: float, fraction: float) -> CombinationLeverMove:
    return CombinationLeverMove(
        lever=lever,  # type: ignore[arg-type]
        baseline_value=baseline,
        target_value=baseline + delta,
        delta=delta,
        relative_change=abs(delta) / abs(baseline),
        fraction_of_cap=fraction,
    )


def _combo(*moves: CombinationLeverMove) -> RecourseCombination:
    return RecourseCombination(
        moves=moves,
        closes_all_live_guardrails=True,
        confirmed_margins=(GuardrailMargin(guardrail="dscr", bar=1.20, value=1.31),),
        rounded=True,
        total_fraction_of_caps=sum(m.fraction_of_cap for m in moves),
    )


def _analysis(**overrides) -> CombinationAnalysis:
    """A minimal, valid `CombinationAnalysis` for the states production does not currently show."""
    base = dict(
        attempted=True,
        outcome="proven_null",
        combinations=(),
        cheapest_total_index=None,
        honest_null=True,
        subsets_searched=11,
        subsets_infeasible=11,
        subsets_edge_infeasible=0,
        subsets_gate_rejected=0,
        subsets_collapsed=0,
        subsets_exhausted=0,
        gate_reasons=(),
        confirm_failed=0,
        rejected_exemplar=None,
        max_iter=40,
    )
    base.update(overrides)
    return CombinationAnalysis(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# THE HONESTY CORE: undetermined is never a proven null.
# ---------------------------------------------------------------------------


def test_undetermined_never_renders_as_a_proven_null(undetermined: CombinationAnalysis) -> None:
    """An exhausted probe budget must read as "we stopped looking", never as "nothing exists".

    Pinned on the real `max_iter=3` champlain run, which produces `outcome="undetermined"` with an
    EMPTY `combinations` tuple — the exact payload a renderer that inferred its outcome from
    emptiness would mis-report as a proven null.
    """
    assert undetermined.outcome == "undetermined"
    assert undetermined.combinations == ()
    assert undetermined.honest_null is False
    text = _text(undetermined)

    # It says we stopped, and it says what stopped us, with the numbers.
    assert "did not finish" in text
    assert "stopped looking" in text
    assert "that is not a finding that nothing exists" in text
    assert f"budget of {undetermined.max_iter} model re-runs" in text
    assert f"{undetermined.subsets_exhausted} of the {undetermined.subsets_searched} combinations tried" in text

    # And it never makes, or implies, the proven-null claim.
    assert "No combination of two or more of these inputs clears every guardrail" not in text
    assert "completed search that came up empty" not in text
    assert "ran every one of them to a conclusion" not in text


def test_undetermined_and_proven_null_leads_share_no_language(undetermined: CombinationAnalysis, proven_null: CombinationAnalysis) -> None:
    """The two empty-list outcomes must be distinguishable to a reader who reads only the first
    sentence — so their leads are checked to be disjoint on their own load-bearing phrases, in
    both directions."""
    assert proven_null.outcome == "proven_null" and proven_null.combinations == ()
    assert undetermined.outcome == "undetermined" and undetermined.combinations == ()

    null_lead = "\n".join(_render_combinations_lead(proven_null))
    undet_lead = "\n".join(_render_combinations_lead(undetermined))
    assert null_lead != undet_lead

    for phrase in ("No combination", "completed search that came up empty", "ran every one of them to a conclusion"):
        assert phrase in null_lead
        assert phrase not in undet_lead
    for phrase in ("did not finish", "stopped looking", "may well exist", "did not establish it either way"):
        assert phrase in undet_lead
        assert phrase not in null_lead


def test_lead_reads_the_outcome_field_and_never_infers_it_from_emptiness() -> None:
    """The structural half of the guarantee: with `combinations` empty and every counter
    identical, flipping ONLY `outcome`/`honest_null` must flip the copy. A renderer keying off
    `if analysis.combinations:` would emit the same text for both — the bug this pins."""
    shared = dict(combinations=(), cheapest_total_index=None, subsets_searched=11, subsets_infeasible=0, subsets_edge_infeasible=0)
    as_null = _analysis(
        outcome="proven_null", honest_null=True, subsets_infeasible=11, **{k: v for k, v in shared.items() if k != "subsets_infeasible"}
    )
    as_undet = _analysis(outcome="undetermined", honest_null=False, subsets_exhausted=11, **shared)

    assert "stopped looking" in _text(as_undet)
    assert "stopped looking" not in _text(as_null)
    assert "No combination of two or more of these inputs clears every guardrail" in _text(as_null)
    assert "No combination of two or more of these inputs clears every guardrail" not in _text(as_undet)


# ---------------------------------------------------------------------------
# found: all of them, in model order, unranked.
# ---------------------------------------------------------------------------


def test_found_renders_every_combination_in_model_order_and_truncates_nothing(found: CombinationAnalysis) -> None:
    """No ranking, no top-N: the rows are the model's own tuple, in its own order. Verified by
    reading the rendered table's own numbers back and comparing them to the payload."""
    assert found.outcome == "found"
    assert len(found.combinations) == 11  # the verified live figure for 82_champlain_dieppe
    text = _text(found)

    rows = [line for line in text.splitlines() if line.startswith("| ") and line.split("|")[1].strip().isdigit()]
    asks_rows = rows[: len(found.combinations)]
    assert len(asks_rows) == len(found.combinations)
    for i, (row, combo) in enumerate(zip(asks_rows, found.combinations, strict=True), start=1):
        assert row.split("|")[1].strip() == str(i)
        assert row.rstrip("| ").split("|")[-1].strip() == f"{combo.total_fraction_of_caps:.2f}"
        for move in combo.moves:
            assert _combination_move_cell(move) in row


def test_cheapest_total_is_a_label_not_a_ranking(found: CombinationAnalysis) -> None:
    """`cheapest_total_index` is an argmin over a column the reader can re-add, and the copy beside
    it says in so many words that it is neither an ordering nor advice."""
    idx = found.cheapest_total_index
    assert idx is not None
    text = _text(found)
    total = found.combinations[idx].total_fraction_of_caps
    assert f"**Combination {idx + 1} has the smallest total ask, at {total:.2f}.**" in text
    assert "not a ranking of the others" in text
    assert "not a recommendation" in text
    # The label really is the argmin of the column as rendered.
    assert total == min(c.total_fraction_of_caps for c in found.combinations)
    # ... and the lead says the list itself carries no order.
    assert "**not a ranking**" in text


def test_every_lever_ask_shows_its_own_fraction_of_cap(found: CombinationAnalysis) -> None:
    """PD.2 call 5's surviving binding condition: the per-lever share ships on every ask, so the
    reader can override the implied ordering with their own judgement."""
    text = _text(found)
    for combo in found.combinations:
        for move in combo.moves:
            assert f"({move.fraction_of_cap * 100:.0f}%)" in _combination_move_cell(move)
            assert _combination_move_cell(move) in text


def test_confirmed_margins_render_with_their_bars_and_nothing_is_recomputed(found: CombinationAnalysis) -> None:
    """Every margin cell and every column bar is a value carried on the payload, formatted by the
    same helper the single-lever gap headers use — no arithmetic happens in the report layer."""
    from src.core.reports.generator import _recourse_fmt_metric

    text = _text(found)
    for margin in found.combinations[0].confirmed_margins:
        assert f"≥ {_recourse_fmt_metric(margin.guardrail, margin.bar)}" in text
    for combo in found.combinations:
        for margin in combo.confirmed_margins:
            assert _recourse_fmt_metric(margin.guardrail, margin.value) in text


def test_found_with_exhausted_subsets_says_the_list_is_incomplete() -> None:
    """`found` and `subsets_exhausted > 0` co-exist in the contract: some answers were found and
    the search still stopped short. The reader is told the list is partial rather than left to
    infer completeness from a table that looks complete."""
    combo = _combo(
        _move("rent_per_unit_month", 90.0, baseline=1412.5, fraction=0.64),
        _move("purchase_price", -54900.0, baseline=605000.0, fraction=0.60),
    )
    analysis = _analysis(
        outcome="found",
        honest_null=False,
        combinations=(combo,),
        cheapest_total_index=0,
        subsets_infeasible=0,
        subsets_exhausted=4,
    )
    text = _text(analysis)
    assert "**This list is not complete.**" in text
    assert "4 of the 11 combinations tried used up their budget" in text
    assert "may exist" in text


def test_a_lever_no_combination_moves_gets_no_column(found: CombinationAnalysis) -> None:
    """The asks table is as narrow as the answers allow — a set that never touches the rate has no
    rate column, so an empty column is never mistaken for "checked and unchanged"."""
    assert _combination_lever_columns(found.combinations) == [
        "rent_per_unit_month",
        "purchase_price",
        "interest_rate",
        "annual_opex",
    ]
    two = (
        _combo(
            _move("rent_per_unit_month", 90.0, baseline=1412.5, fraction=0.64),
            _move("purchase_price", -54900.0, baseline=605000.0, fraction=0.60),
        ),
    )
    assert _combination_lever_columns(two) == ["rent_per_unit_month", "purchase_price"]
    text = _text(_analysis(outcome="found", honest_null=False, combinations=two, cheapest_total_index=0, subsets_infeasible=0))
    assert "| Interest rate |" not in text
    assert "| Annual opex |" not in text


# ---------------------------------------------------------------------------
# proven_null: explained, with counters and reasons.
# ---------------------------------------------------------------------------


def test_proven_null_shows_every_counter_including_the_zeros(proven_null: CombinationAnalysis) -> None:
    """A printed zero is a reported zero; a suppressed zero is indistinguishable from a count
    nobody looked at. Every bucket renders, on every outcome, and they add to the total."""
    assert proven_null.outcome == "proven_null"
    text = _text(proven_null)
    assert (
        f"| Proven empty: every input in it at its realism limit at once, and a guardrail still fails | {proven_null.subsets_infeasible} |"
        in text
    )
    assert (
        f"| Reached the edge of the search range along its own direction without clearing them | {proven_null.subsets_edge_infeasible} |"
        in text
    )
    assert f"| Cleared the guardrails, but the joint realism check rejected the asks | {proven_null.subsets_gate_rejected} |" in text
    assert f"| Rounded down to a single input — the menu above already covers it | {proven_null.subsets_collapsed} |" in text
    assert (
        f"| Stopped early: the budget of {proven_null.max_iter} model re-runs for that combination ran out | {proven_null.subsets_exhausted} |"
        in text
    )
    assert f"| The confirming re-run failed | {proven_null.confirm_failed} |" in text
    assert f"| **Total combinations tried** | **{proven_null.subsets_searched}** |" in text
    accounted = (
        len(proven_null.combinations)
        + proven_null.subsets_infeasible
        + proven_null.subsets_edge_infeasible
        + proven_null.subsets_gate_rejected
        + proven_null.subsets_collapsed
        + proven_null.subsets_exhausted
        + proven_null.confirm_failed
    )
    assert accounted == proven_null.subsets_searched


def test_honest_null_exemplar_reason_is_inseparable_from_the_row(null_with_exemplar: CombinationAnalysis) -> None:
    """PD.2 call 4: the rejected exemplar ships on a null WITH its reason adjacent and inseparable
    — the row itself opens with "Rejected" and the reason is the line directly under it, so a row
    can never be quoted, screenshotted or skimmed as an answer."""
    ex = null_with_exemplar.rejected_exemplar
    assert ex is not None
    lines = _render_combinations(null_with_exemplar)
    row_idx = next(i for i, line in enumerate(lines) if line.startswith("- Rejected — "))
    assert lines[row_idx + 1] == f"  _Rejected because {ex.reason}_"
    # Its own confirming re-run's margins are on the very next line — the "it does close them"
    # claim never travels without its receipts.
    assert lines[row_idx + 2].startswith("  _Its confirming re-run measured:")
    for move in ex.combination.moves:
        assert _combination_move_phrase(move) in lines[row_idx]
    assert f"total ask {ex.combination.total_fraction_of_caps:.2f}" in lines[row_idx]


def test_exemplar_ships_only_on_a_null(found: CombinationAnalysis, proven_null: CombinationAnalysis) -> None:
    """Above zero it would read as one more answer, so the contract never populates it there and
    the renderer never invents one."""
    assert found.rejected_exemplar is None
    assert "Rejected — " not in _text(found)
    assert proven_null.rejected_exemplar is None
    assert "closest thing to an answer" not in _text(proven_null)


def test_gate_reasons_render_whenever_any_fired(null_with_exemplar: CombinationAnalysis) -> None:
    """A count with no "why" beside it is silence with a receipt. The deduped reasons ship; the
    exemplar's own reason is not repeated a second time under a generic heading."""
    text = _text(null_with_exemplar)
    assert null_with_exemplar.gate_reasons
    for reason in null_with_exemplar.gate_reasons:
        assert reason in text
    assert text.count(null_with_exemplar.gate_reasons[0]) == 1  # exemplar row only, never duplicated

    # With reasons but no exemplar, they render under their own lead.
    text2 = _text(_analysis(gate_reasons=("a stated reason.",), subsets_infeasible=10, subsets_gate_rejected=1))
    assert "Why the joint realism check rejected combinations that did clear every guardrail:" in text2
    assert "- _a stated reason._" in text2


# ---------------------------------------------------------------------------
# GD3, formatting, and the states that render nothing.
# ---------------------------------------------------------------------------


def test_gd3_no_model_assumption_ever_appears_as_an_ask(found: CombinationAnalysis, null_with_exemplar: CombinationAnalysis) -> None:
    """GD3 is structural (`CombinationLeverMove.lever` is closed to the four investor levers), and
    this pins the rendering half: the ask surfaces — table rows and the exemplar row — name only
    those four. The ABOUT block names the assumptions on purpose, in the sentence that says they
    are never moved, so it is excluded from the scan."""
    for analysis in (found, null_with_exemplar):
        asks = [line for line in _render_combinations(analysis) if line.startswith("| ") or line.startswith("- Rejected — ")]
        assert asks
        blob = "\n".join(asks).lower()
        for word in _ASSUMPTION_WORDS:
            assert word not in blob, f"GD3: {word!r} surfaced as an ask"
    assert "is ever presented here" in ABOUT_COMBINATIONS_BLOCK  # the denial is stated to the reader


@pytest.mark.parametrize(
    ("delta", "expected"),
    [(-0.0055, "-55 bps"), (0.003, "+30 bps"), (0.0, "0 bps"), (-0.00001, "0 bps")],
)
def test_rate_deltas_render_as_signed_basis_points(delta: float, expected: str) -> None:
    """Rate asks are in bps (the lever's native unit and the unit the single-lever menu already
    uses); a delta that rounds to zero never renders as a misleading "-0 bps"."""
    assert _fmt_delta_bps(delta) == expected


def test_currency_and_rate_asks_use_their_own_native_units(found: CombinationAnalysis) -> None:
    text = _text(found)
    assert "| Rent ($/unit/month) |" in text
    assert "+$90.00 (64%)" in text  # rent, native $/unit/month, verified live figure
    assert "-$54,900.00 (60%)" in text  # price, native dollars off
    assert "-55 bps (55%)" in text  # rate, native basis points


def test_every_markdown_table_row_matches_its_header_width(found: CombinationAnalysis, proven_null: CombinationAnalysis) -> None:
    """Markdown renders everywhere (GitHub, VS Code preview, PDF export) only if the tables are
    well formed: every row in a block has the same cell count as that block's header."""
    for analysis in (found, proven_null):
        width: int | None = None
        for line in _render_combinations(analysis):
            if not line.startswith("|"):
                width = None
                continue
            cells = len(line.split("|"))
            if width is None:
                width = cells
            assert cells == width, f"ragged table row: {line}"


def test_not_attempted_and_absent_analyses_render_nothing() -> None:
    """`attempted` is False exactly when no live guardrail fails — the enclosing section has no gap
    blocks either, so a paragraph explaining that nothing was searched because nothing is broken
    would be noise under a heading that already asks "what would have to change?"."""
    assert _render_combinations(None) == []
    assert _render_combinations(_analysis(attempted=False, outcome=None, honest_null=False, subsets_searched=0, subsets_infeasible=0)) == []


def test_render_is_byte_identical_across_two_calls(found: CombinationAnalysis, null_with_exemplar: CombinationAnalysis) -> None:
    for analysis in (found, null_with_exemplar):
        assert _render_combinations(analysis) == _render_combinations(analysis)


# ---------------------------------------------------------------------------
# The seam into the enclosing section: the amended copy, and byte-identity without it.
# ---------------------------------------------------------------------------


def test_menu_methodology_bullet_being_swapped_is_the_combinations_bullet() -> None:
    """`_render_recourse` swaps `_RECOURSE_METHODOLOGY_LINES[-1]` — the bullet asserting that
    combinations "were never searched", which is false once the sub-part renders. This pins that
    the last element really is that bullet, so a future append cannot silently drop a real one."""
    assert _RECOURSE_METHODOLOGY_LINES[-1].startswith("- **Combinations of levers were never searched.**")


def test_section_copy_stops_claiming_combinations_were_never_searched(champlain_recourse) -> None:
    """The two sentences that become false the moment the sub-part renders — the honesty block's
    and the methodology bullet's — are replaced, and both replacements point at the sub-part by its
    own heading string."""
    analysis, forecast, market = champlain_recourse
    text = _render_recourse(analysis, forecast, market)
    assert "were never searched" not in text
    assert ABOUT_RECOURSE_BLOCK_WITH_COMBINATIONS in text
    assert ABOUT_RECOURSE_BLOCK not in text
    assert text.count(f'"{_COMBINATIONS_HEADING_TEXT}"') == 2  # the honesty block and the menu bullet
    assert f"**{_COMBINATIONS_HEADING_TEXT}**" in text


def test_without_a_combination_analysis_the_section_is_unchanged(champlain_recourse) -> None:
    """An older payload (`combinations=None`) gets the pre-Mission-5 wording verbatim: the sub-part
    is absent, the honesty block is the original, and the menu's closing bullet still says
    combinations were never searched — which, for that payload, is true."""
    analysis, forecast, market = champlain_recourse
    without = _render_recourse(analysis.model_copy(update={"combinations": None}), forecast, market)
    assert ABOUT_RECOURSE_BLOCK in without
    assert ABOUT_RECOURSE_BLOCK_WITH_COMBINATIONS not in without
    assert _RECOURSE_METHODOLOGY_LINES[-1] in without
    assert _COMBINATIONS_HEADING_TEXT not in without
    assert without.endswith(_RECOURSE_METHODOLOGY_LINES[-1] + "\n")


def test_subpart_sits_between_the_menu_and_the_methodology(champlain_recourse) -> None:
    """Information hierarchy: one change first, several changes second, method last."""
    analysis, forecast, market = champlain_recourse
    text = _render_recourse(analysis, forecast, market)
    menu = text.index("**Cheapest single fix:**")
    subpart = text.index(f"**{_COMBINATIONS_HEADING_TEXT}**")
    methodology = text.index("**How these numbers were produced**")
    assert menu < subpart < methodology
