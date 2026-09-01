# src/market/recourse.py
"""Actionable recourse -- "What would have to change?" (Mission 4).

Attaches to a near-miss ``InvestmentThesis`` a structured answer to "how far is this deal from
the line, and what single investor-movable change would close the gap?" for each currently-failing
guardrail, expressed in four levers: rent per unit/month, purchase price, interest rate, and
annual operating costs. Those four are exactly ``partition.INVESTOR_LEVERS`` — the GD3
lever/assumption partition (``src/core/finance/partition.py``): a recourse ask may only ever be a
quantity the investor acts on in the world, NEVER a model assumption (vacancy/occupancy, rent
growth, expense growth, exit cap, cap drift, hold horizon) — presenting an assumption change as
an action would instruct the user to fudge an input until the model passes. The set is closed by
an import-time drift guard below; extending it is a Founder Proxy escalation citing GD3.

Mission 5 Half B adds the MULTI-lever section (``compute_combinations`` /
``judge_combination`` — see the "Multi-lever combinations" banner below): one minimal-ask solve
per lever subset, an AD-chosen direction, a bisected distance, a unified joint plausibility gate,
and a three-outcome (found / proven-null / undetermined) honesty contract. Same disciplines: the
same four levers, re-run-never-invert, confirm-by-rerun before anything ships.

THE ONE DISCIPLINE (binding, non-negotiable): **re-run the engine, never invert a guardrail
formula.** The levers are not independent -- a price cut shrinks the loan, lifts the cap rate, and
changes cash-in all at once. Every lever answer in this module comes from perturbing a copy of
``FinancialInputs`` (a surgical, submodel-scoped copy -- see ``_perturb`` -- not a full deep copy;
untouched submodels are shared by reference, which is safe because nothing here or in the engine
ever mutates one in place), changing exactly one input, calling ``run_financial_model`` on the
copy, and reading the result off ``guardrail_checks``. No guardrail formula is ever solved
algebraically for the unknown lever value, anywhere in this module.

**The trap, concretely** (verified against the committed sample deal,
``data/sample_listings/36_kelly_moncton/inputs.json``): for the ``coc`` guardrail via the
``purchase_price`` lever, ``coc = cash_flow_y1(price) / acquisition_cash(price)`` has BOTH the
numerator and the denominator depend on price (a price cut shrinks the loan payment AND the down
payment + MIP at once). The true re-run flip point is $341,057.63; naively inverting the CoC
formula while freezing ``acquisition_cash`` at its baseline value gives $338,814.34 -- whose real
CoC (re-run) is 3.4073%, not the 3.00% the naive formula believed it was landing on. Every other
lever/guardrail pair in this engine happens to be an exact, closed-form hyperbola with no hidden
coupling (see ``engine.py``'s amortization/cap-rate math), so this is the one pair where "just
solve for x" is a real, tempting, wrong shortcut -- which is exactly why the re-run discipline is
not optional for any of them.

Public API
----------
``is_genuinely_close(inputs, *, horizon_years=DEFAULT_HORIZON_YEARS) -> bool``
    Pre-computation scoping gate (Roger's Gate D ruling): decide, from the baseline forecast
    ALONE -- never by peeking at search results -- whether recourse is worth attempting at all.
``compute_recourse(inputs, *, horizon_years=DEFAULT_HORIZON_YEARS) -> RecourseAnalysis``
    Always returns a complete, fully-populated ``RecourseAnalysis`` -- never ``None``, never a
    blanked-out result, regardless of whether every row turns out to be an honest null. The
    *whether to attempt at all* decision is ``is_genuinely_close``'s job, made before this is ever
    called; the *whether to render* decision belongs to the report layer, not to this module.
"""

from __future__ import annotations

import gc
import math
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Literal, cast, get_args

# `typing.assert_never` is 3.11+; this project targets 3.10 (mypy.ini: python_version = 3.10),
# so it comes from `typing_extensions` instead -- already a hard transitive dependency via
# pydantic (pydantic>=2.7,<3.0 requires typing-extensions on every supported Python), declared
# explicitly here rather than accidentally, same rationale as `onnxruntime` in requirements.txt.
from typing_extensions import assert_never

from src.agents.chief_strategist import (
    MIN_COC_Y1,
    MIN_DSCR_Y1,
    MIN_IRR_10YR,
    REQUIRE_POSITIVE_CF_ALL,
    REQUIRE_POSITIVE_CF_Y1,
    GuardrailChecks,
    guardrail_checks_from_metrics,
    spread_target_for,
    synthesize_thesis,
)
from src.core.finance.engine import (
    DEFAULT_HORIZON_YEARS,
    ForecastMetrics,
    PrecomputedIncome,
    forecast_metrics,
    metrics_of,
    precompute_income,
    run_financial_model,
    shift_income,
)
from src.core.finance.jacobian import (
    MAX_DIRECTIONS,
    MetricName,
    MetricsJacobian,
    SeedTarget,
    TangentDirection,
    forecast_metrics_with_jacobian,
)
from src.core.finance.partition import INVESTOR_LEVERS, investor_lever_combinations
from src.market.hypotheses import DEFAULT_BANDS
from src.market.rejector import (
    CAP_RATE_MAX,
    CAP_RATE_MIN,
    RATES_VS_CAP_MAX_DIVERGENCE,
    VACANCY_MAX,
    VACANCY_MIN,
    HardRule,
    reject_unrealistic,
    violated_hard_rules,
)
from src.schemas.models import (
    CombinationAnalysis,
    CombinationLeverMove,
    FinancialForecast,
    FinancialInputs,
    GuardrailMargin,
    HypothesisSet,
    IncomeModel,
    MarketAssumptions,
    MarketHypothesis,
    MarketSnapshot,
    RecourseAnalysis,
    RecourseCombination,
    RecourseLever,
    RejectedCombination,
    UnitIncome,
)

GuardrailName = Literal["dscr", "spread", "irr", "coc", "cf_y1", "cf_all", "cap_floor"]
LeverName = Literal["rent_per_unit_month", "purchase_price", "interest_rate", "annual_opex"]

# Import-time GD3 drift guard (partition condition C1, house pattern of `_UI_KWARG_KEYS` below
# and `jacobian.py`'s seed-target guard): this module's lever vocabulary IS the partition's
# closed `INVESTOR_LEVERS` set — a quantity the investor acts on in the world, never a model
# assumption. If `LeverName` and `partition.INVESTOR_LEVERS` ever disagree, fail on import.
if get_args(LeverName) != INVESTOR_LEVERS:
    raise RuntimeError(
        "recourse.LeverName has drifted from partition.INVESTOR_LEVERS (GD3): "
        f"LeverName={get_args(LeverName)} INVESTOR_LEVERS={INVESTOR_LEVERS}. Extending the recourse "
        "lever set is a Founder Proxy escalation citing GD3 -- see src/core/finance/partition.py and "
        "docs/plans/mission-5-discovery/GD3_lever_assumption_invariant.md."
    )

#: Fixed lexicographic order used everywhere a guardrail set is iterated or tie-broken.
_GUARDRAIL_ORDER: tuple[GuardrailName, ...] = ("dscr", "spread", "irr", "coc", "cf_y1", "cf_all", "cap_floor")

#: Fixed lexicographic order used everywhere a lever set is iterated or tie-broken. Pinned to the
#: partition's own declaration order by the guard above (INVESTOR_LEVERS == get_args(LeverName)).
_LEVER_ORDER: tuple[LeverName, ...] = INVESTOR_LEVERS

#: The one pair that is hopeless for EVERY deal regardless of configuration: interest rate never
#: appears in the cap-rate formula (`cap_rate = noi_y1 / purchase_price`, or the market override),
#: so no amount of rate negotiation can ever cure a cap-rate-floor breach. Excluded before any
#: engine call is made -- a documented fact about the engine's data flow, not a formula inversion.
_STATICALLY_HOPELESS: frozenset[tuple[LeverName, GuardrailName]] = frozenset({("interest_rate", "cap_floor")})

#: Bisection convergence tolerance per lever, in the lever's own perturbation units (a dollar
#: amount for rent/price/opex, a fraction for the rate). Deliberately finer than the rounding
#: step below so the rounded-and-re-run ask (see ROUND_STEP) is never coarser than what the
#: bisection actually resolved.
_BISECT_TOL: dict[LeverName, float] = {
    "rent_per_unit_month": 1.0,
    "purchase_price": 100.0,
    "interest_rate": 0.0001,  # 1 bp
    "annual_opex": 50.0,
}

#: Round-the-ask-away-from-zero step per lever (Roger's Gate D product decision, 2026-08-29): the
#: reported ask is always a clean, human-facing number, rounded in the direction that keeps the
#: claim true (a required cut rounds to a LARGER cut, a required increase to a LARGER increase --
#: never the direction that would undershoot the bar), and re-confirmed by one more engine re-run
#: at that rounded value so the number on the page and the metric beside it come from the same run.
ROUND_STEP: dict[LeverName, float] = {
    "rent_per_unit_month": 5.0,
    "purchase_price": 100.0,
    "interest_rate": 0.0005,  # 5 bps
    "annual_opex": 50.0,
}

#: Relative-magnitude plausibility fallback per lever (Gate D, proposed defaults confirmed): flag
#: (never remove) a lever whose |relative_change| exceeds this fraction of the lever's own
#: baseline value. Independent of, and in addition to, the rejector-based check below.
_MAGNITUDE_RELATIVE_THRESHOLD: dict[Literal["rent_per_unit_month", "purchase_price", "annual_opex"], float] = {
    "rent_per_unit_month": 0.10,
    "purchase_price": 0.15,
    "annual_opex": 0.20,
}

#: Absolute-magnitude plausibility fallback for the interest_rate lever (Gate D, 2026-08-29):
#: sourced from the repo's OWN working definition of "a big rate move" -- reuse, not invention --
#: rather than a newly-invented number. `DEFAULT_BANDS["interest_rate_delta"]` is Mission 1's own
#: generator band `(-0.01, 0.00, 0.02)`; its most extreme CUT magnitude is 100 bps.
RATE_MAGNITUDE_THRESHOLD = abs(DEFAULT_BANDS["interest_rate_delta"][0])

#: A DECLINE is judged "genuinely close" -- worth attempting recourse at all -- when at most this
#: many of the (up to) six LIVE guardrails are failing (seven booleans are computed, but `cf_all`
#: is structurally dead under the shipped `REQUIRE_POSITIVE_CF_ALL = False`, `chief_strategist.py`,
#: and `cap_floor` is live only when the user sets `market.cap_rate_floor` -- so six live requires
#: a user-set floor; see `_live_guardrails`). This is a SCOPING predicate evaluated
#: BEFORE any search runs, on the baseline forecast alone; it never moves, and is independent of,
#: `chief_strategist.synthesize_thesis`'s own verdict fail-count rule (DECLINE at >=3 fails, or a
#: cap-floor breach + DSCR fail together) -- that rule still solely decides BUY/CONDITIONAL/DECLINE.
#: A CONDITIONAL always has 1 or 2 of the live guardrails failing (the verdict logic's own
#: arithmetic), so this bound naturally includes every CONDITIONAL; for a DECLINE it draws the
#: line at "a handful of guardrails are off," not "the whole deal failed" -- Roger's Gate D ruling
#: (2026-08-29) that the earlier draft's "compute recourse, then discard it post-hoc" design would
#: have hidden a real, computed answer (see this module's docstring and the guardian's Gate D
#: record in docs/plans/MISSION_4_SPRINT_TRACKER.md).
GENUINELY_CLOSE_MAX_FAILS = 3


@dataclass(frozen=True)
class _Bound:
    """Search bound (how far bisection may look) and baseline value for one lever, on one deal."""

    baseline_value: float
    search_bound: float


def _ok(checks: GuardrailChecks, guardrail: GuardrailName) -> bool:
    return {
        "dscr": checks.dscr_ok,
        "spread": checks.spread_ok,
        "irr": checks.irr_ok,
        "coc": checks.coc_ok,
        "cf_y1": checks.cf_y1_ok,
        "cf_all": checks.cf_all_ok,
        "cap_floor": checks.no_cap_floor_breach,
    }[guardrail]


def _metric(metrics: ForecastMetrics, guardrail: GuardrailName) -> float:
    """The single scalar each guardrail's own `>=` bar tests -- HIGHER is better for every one of
    the seven (dscr/spread/irr/coc/cf_y1/cf_all/cap_floor all clear their bar by being >= it), so
    no per-guardrail sign flip is needed anywhere in this module.

    `cap_floor` has no numeric bar of its own (the guardrail is a warning-string test -- see
    `guardrail_checks`), but its cap rate is exactly the number the warning is derived from, and
    is what the reachability probe (in `_search_one`) reads to detect "this lever does not move
    this guardrail at all" (discovery spec §1.3/§2.1).
    """
    if guardrail == "dscr":
        return metrics.purchase_dscr
    if guardrail == "spread":
        return metrics.spread_vs_rate
    if guardrail == "irr":
        return metrics.irr_10yr
    if guardrail == "coc":
        return metrics.coc
    if guardrail == "cf_y1":
        return metrics.cash_flow_y1
    if guardrail == "cf_all":
        return metrics.min_cash_flow
    return metrics.cap_rate  # cap_floor


def _live_guardrails(market: MarketAssumptions) -> frozenset[GuardrailName]:
    """Which of the seven guardrails are ever tested for this deal (mirrors the discovery spec's
    §1.2 table exactly, read straight off the same module constants `guardrail_checks`'s caller,
    `synthesize_thesis`, uses)."""
    live: set[GuardrailName] = {"dscr", "spread", "irr", "coc"}
    if REQUIRE_POSITIVE_CF_Y1:
        live.add("cf_y1")
    if REQUIRE_POSITIVE_CF_ALL:
        live.add("cf_all")
    if market.cap_rate_floor is not None:
        live.add("cap_floor")
    return frozenset(live)


def _failing_guardrails(checks: GuardrailChecks, live: frozenset[GuardrailName]) -> tuple[GuardrailName, ...]:
    return tuple(g for g in _GUARDRAIL_ORDER if g in live and not _ok(checks, g))


def _num_fails(checks: GuardrailChecks, live: frozenset[GuardrailName]) -> int:
    return len(_failing_guardrails(checks, live))


def is_genuinely_close(inputs: FinancialInputs, *, horizon_years: int = DEFAULT_HORIZON_YEARS) -> bool:
    """Pre-computation scoping gate: decide whether recourse is worth attempting at all.

    Evaluated from a fresh baseline forecast of ``inputs`` alone -- no search, no bisection, no
    lever perturbation happens here. (It takes the engine's light ``forecast_metrics`` path rather
    than ``run_financial_model``: the two are pinned bit-identical on every guardrail number
    (``tests/core/finance/test_metrics_parity.py``), and this gate publishes no figure -- it only
    decides whether to proceed.) A ``BUY`` (0 fails) is never close (nothing to
    fix); a DECLINE with more than ``GENUINELY_CLOSE_MAX_FAILS`` of the live guardrails failing is
    judged "not genuinely close" and recourse is never computed for it (the report stays
    byte-identical to a run with no recourse feature at all). This does NOT peek at whether any
    lever could actually close a gap -- that is `compute_recourse`'s job, run only after this gate
    opens.
    """
    # A GATE, not a report: nothing here is ever shown to the investor, so it takes the light
    # search path. `guardrail_checks_from_metrics` is the same one implementation the report path
    # reaches through `guardrail_checks`, so the gate cannot answer differently from the thesis.
    metrics = forecast_metrics(inputs, horizon_years=horizon_years)
    checks = guardrail_checks_from_metrics(metrics, inputs.market)
    live = _live_guardrails(inputs.market)
    num_fails = _num_fails(checks, live)
    return 0 < num_fails <= GENUINELY_CLOSE_MAX_FAILS


def _derive_snapshot(inputs: FinancialInputs, base_forecast: FinancialForecast) -> MarketSnapshot:
    """A recourse-own, always-available `MarketSnapshot` (discovery spec §3.2).

    `resolve_snapshot` (`src/market/scenario_runner.py`) raises exactly when no explicit `market`
    block was supplied AND `inputs.market.cap_rate_purchase is None` -- precisely the case where
    price/rent/opex levers move the cap rate, and thus the one case recourse's plausibility check
    needs a real snapshot cap the most. This mirrors `resolve_snapshot`'s fallback branch but reads
    the cap off the ALREADY-COMPUTED baseline forecast (`base_forecast.purchase.cap_rate`, always
    populated, override or not) instead of `inputs.market.cap_rate_purchase` (sometimes `None`).
    A new, small, additive helper next to (never calling into) `resolve_snapshot` -- the two solve
    genuinely different preconditions.

    PRECONDITION, loud (Mission 5 Gate V re-review, N5): `MarketSnapshot.cap_rate` is `ge=0`;
    `PurchaseMetrics.cap_rate` is not (a negative-NOI deal computes a negative purchase cap rate
    validly). `compute_recourse`/`compute_combinations` are self-contained -- they compute their
    OWN fresh baseline rather than accepting one from a caller who already ran `is_genuinely_close`
    (see their docstrings) -- so a negative-NOI deal reaches this constructor directly on those
    entry points, not just through a caller who forgot the gate. At pipeline level
    (`src/orchestrators`) `is_genuinely_close` runs first and a negative-NOI deal fails enough
    live guardrails to shut the gate before this is ever called, so the crash was never observed
    end-to-end -- but `compute_combinations` is now documented public API
    (`src/market/README.md`), and its docstring makes no such promise. Rather than let that
    reach the investor as a `pydantic.ValidationError` two layers down inside `MarketSnapshot`'s
    constructor, fail here, in recourse's own vocabulary, naming the actual precondition.
    """
    cap_rate = base_forecast.purchase.cap_rate
    if cap_rate < 0:
        raise ValueError(
            f"cannot derive a recourse market snapshot: this deal's Year 1 purchase cap rate is "
            f"negative ({cap_rate:.4%}), which means Year 1 NOI is negative. MarketSnapshot.cap_rate "
            "requires >= 0, and recourse/combination search needs a real cap to reason about "
            "plausibility against. This is a data problem with the deal's income/opex inputs, not "
            "something a lever search can work around -- fix the inputs before calling "
            "compute_recourse or compute_combinations."
        )
    return MarketSnapshot(
        region="recourse-derived",
        vacancy_rate=1.0 - inputs.income.occupancy,
        cap_rate=cap_rate,
        rent_growth=inputs.income.rent_growth,
        expense_growth=inputs.opex.expense_growth,
        interest_rate=inputs.financing.interest_rate,
        notes="Derived for recourse plausibility only; not the scenario-analysis snapshot.",
    )


# ---------------------------------------------------------------------------
# Lever perturbation
# ---------------------------------------------------------------------------

_OPEX_FIELDS: tuple[str, ...] = (
    "insurance",
    "taxes",
    "utilities",
    "water_sewer",
    "property_management",
    "repairs_maintenance",
    "trash",
    "landscaping",
    "snow_removal",
    "hoa_fees",
    "reserves",
    "other",
)


def _baseline_value(inputs: FinancialInputs, lever: LeverName, *, total_opex_y1: float) -> float:
    if lever == "rent_per_unit_month":
        units = inputs.income.units
        return (sum(u.rent_month for u in units) / len(units)) if units else 0.0
    if lever == "purchase_price":
        return inputs.financing.purchase_price
    if lever == "interest_rate":
        return inputs.financing.interest_rate
    return total_opex_y1  # annual_opex


def _search_bound(inputs: FinancialInputs, lever: LeverName, *, total_opex_y1: float) -> float:
    """ "Generous but finite" search bounds (discovery spec §2.2, Gate D confirmed)."""
    if lever == "rent_per_unit_month":
        units = inputs.income.units
        avg = (sum(u.rent_month for u in units) / len(units)) if units else 0.0
        return avg  # 0 -> +100% of the current average rent/unit/month
    if lever == "purchase_price":
        return 0.40 * inputs.financing.purchase_price
    if lever == "interest_rate":
        return min(0.03, inputs.financing.interest_rate)  # 0 -> -300 bps, floored at 0%
    return 0.40 * total_opex_y1  # annual_opex


# ----------------------------------------------------------------------------------------------
# PERF (Mission 4, PV.4): validation-free `UnitIncome` construction for the rent-per-unit lever.
#
# WHY: the rent-lever branch of `_perturb` rebuilds every `UnitIncome` in the rent roll (the
# other three levers touch `financing`/`opex` only and share `income` by reference -- see the
# module docstring). At the 5,000-unit institutional ceiling this cost ~5.42 ms/probe against
# ~0.45 ms of actual engine work per probe -- the copy was ~12x the calculation it wraps, and a
# real `compute_recourse` fires ~159 rent-lever probes, so this was roughly 80% of a
# portfolio-scale analysis's wall time. `UnitIncome.model_copy(update=...)` already skips
# validation on the updated field, but it still pays for pydantic's generic copy machinery
# (deep/shallow branch, private-attr handling, dict merge) on every one of the 5,000 calls. This
# builds the instance's state directly instead -- exactly the technique `engine._year_row` uses
# for `YearBreakdown`, applied here because the same preconditions hold (see below).
#
# WHY IT IS SAFE, specifically:
#   * `rent_month` is `u.rent_month + t`, computed a line above out of already-validated floats;
#     `other_income_month` is copied UNCHANGED from the source unit. There is no external/
#     untrusted input on this path.
#   * `UnitIncome` has no validators, no aliases, no computed fields and no private attributes
#     (confirmed against `src/schemas/models.py`), so a validated instance's state is exactly:
#     `__dict__` = the two field values, `__pydantic_fields_set__` = both names,
#     `__pydantic_extra__` = None, `__pydantic_private__` = None. That equivalence is asserted
#     field-by-field, and on `model_dump()` / `model_dump(mode="json")` / `model_dump_json()` /
#     `==` / `__pydantic_fields_set__`, in `tests/unit/test_recourse_perturb_bitexact.py`.
#   * `__pydantic_fields_set__` is a fresh `set` per unit (a `.copy()` of the template, not the
#     shared object): pydantic mutates that set on attribute assignment (`validate_assignment` is
#     on for this model), so sharing one instance across units would be a real aliasing bug.
#   * `_UI_FIELDS` is derived from the model itself and cross-checked against the literal field
#     list at import time, so a future `UnitIncome` field addition/rename fails loudly on import
#     instead of silently producing a half-built model.
#   * Bypassing validation at CONSTRUCTION time does not disturb `validate_assignment` on the
#     resulting object -- that behaviour lives on the class's `__setattr__`, not on how the
#     instance was built (`tests/unit/test_recourse_perturb_bitexact.py` pins this directly).
#
# The other three levers (`purchase_price`, `interest_rate`, `annual_opex`) are NOT touched here:
# each calls `model_copy` exactly once (on `financing` or `opex`), never once per unit, so the
# per-call overhead this optimises away never shows up on their path.
# ----------------------------------------------------------------------------------------------
_UI_FIELDS: tuple[str, ...] = tuple(UnitIncome.model_fields)
_UI_FIELDS_TEMPLATE: set[str] = set(_UI_FIELDS)
_UI_OBJ_SETATTR = object.__setattr__


def _fast_unit_income(*, rent_month: float, other_income_month: float) -> UnitIncome:
    """Build a `UnitIncome` with both fields explicitly supplied, bypassing pydantic validation.

    Equivalent, field-for-field and dump-for-dump, to `UnitIncome(**kwargs)` -- see the module
    note above for why, and `test_recourse_perturb_bitexact.py` for the proof.
    """
    unit: UnitIncome = object.__new__(UnitIncome)
    _UI_OBJ_SETATTR(unit, "__dict__", {"rent_month": rent_month, "other_income_month": other_income_month})
    _UI_OBJ_SETATTR(unit, "__pydantic_fields_set__", _UI_FIELDS_TEMPLATE.copy())
    _UI_OBJ_SETATTR(unit, "__pydantic_extra__", None)
    _UI_OBJ_SETATTR(unit, "__pydantic_private__", None)
    return unit


#: Import-time drift guard for `_fast_unit_income`'s literal kwarg list (see the note above).
_UI_KWARG_KEYS: frozenset[str] = frozenset(_fast_unit_income.__kwdefaults__ or {}) | frozenset(
    _fast_unit_income.__code__.co_varnames[: _fast_unit_income.__code__.co_kwonlyargcount]
)
if _UI_KWARG_KEYS != frozenset(_UI_FIELDS):
    raise RuntimeError(
        "recourse._fast_unit_income is out of sync with schemas.UnitIncome: "
        f"missing={sorted(frozenset(_UI_FIELDS) - _UI_KWARG_KEYS)} extra={sorted(_UI_KWARG_KEYS - frozenset(_UI_FIELDS))}"
    )


def _perturb(inputs: FinancialInputs, lever: LeverName, t: float, *, total_opex_y1: float) -> FinancialInputs:
    """Return a perturbed copy of `inputs` for lever `lever` at non-negative magnitude `t`.

    `t` is always >= 0 (see module docstring / discovery spec §1.1: every lever here is searched
    in one direction only -- rent/income only ever helps, price/rate/opex cuts only ever help).
    The ORIGINAL `inputs` (and every nested submodel) is left untouched.

    SURGICAL copy, not a full deep copy: only the ONE submodel this lever actually touches is
    rebuilt (via nested ``model_copy(update=...)``); every other field of ``inputs`` (and, for the
    price/rate levers, every field of ``opex``/``income`` too) is shared BY REFERENCE with the
    caller's object. This is safe -- and 2x+ faster at scale than ``model_copy(deep=True)`` /
    ``copy.deepcopy`` -- precisely because neither `run_financial_model` nor anything in this
    module ever mutates a submodel in place; every change here goes through `.model_copy(update=)`
    (the rent lever's per-unit rebuild is the one exception -- see `_fast_unit_income` above,
    which returns a NEW, validation-free instance rather than calling `model_copy`, for the same
    "never mutate in place" reason), so every returned object is always a NEW instance. Do not add
    in-place mutation anywhere in this module without re-auditing this assumption.
    """
    if lever == "rent_per_unit_month":
        new_units = [_fast_unit_income(rent_month=u.rent_month + t, other_income_month=u.other_income_month) for u in inputs.income.units]
        new_income = inputs.income.model_copy(update={"units": new_units})
        return inputs.model_copy(update={"income": new_income})

    if lever == "purchase_price":
        new_financing = inputs.financing.model_copy(update={"purchase_price": inputs.financing.purchase_price - t})
        return inputs.model_copy(update={"financing": new_financing})

    if lever == "interest_rate":
        new_rate = max(0.0, inputs.financing.interest_rate - t)
        new_financing = inputs.financing.model_copy(update={"interest_rate": new_rate})
        return inputs.model_copy(update={"financing": new_financing})

    # annual_opex: an aggregate dollar cut `t`, spread proportionally across every line item so no
    # single vendor negotiation is fabricated (discovery spec §1.1's rationale).
    factor = (1.0 - (t / total_opex_y1)) if total_opex_y1 > 0 else 1.0
    updates = {field: getattr(inputs.opex, field) * factor for field in _OPEX_FIELDS}
    new_opex = inputs.opex.model_copy(update=updates)
    return inputs.model_copy(update={"opex": new_opex})


def _rerun(
    perturbed: FinancialInputs,
    *,
    horizon_years: int,
    baseline_income: IncomeModel,
    precomputed: PrecomputedIncome,
    rent_shift: float = 0.0,
) -> ForecastMetrics:
    """A SEARCH probe: re-run the engine on a perturbed copy and return only the guardrail scalars.

    THE LIGHT PATH IS FOR SEARCHING, THE FULL PATH IS FOR REPORTING. This is called hundreds of
    times per analysis (one bound probe plus ~10 bisection steps per lever/guardrail pair) and the
    caller reads one scalar and seven booleans from each. `engine.forecast_metrics` runs the
    identical `_forecast_core` and skips only the materialisation of the ~100 `YearBreakdown`
    objects nobody looks at -- no arithmetic differs, and `tests/core/finance/test_metrics_parity.py`
    pins that bit-for-bit. The number finally SHOWN to the investor still comes from a full
    `run_financial_model` re-run at the rounded ask, in `_search_one` below.

    It also reuses the baseline rent-roll aggregate when -- and ONLY when -- this perturbation
    provably did not touch income.

    BUILD THE CURVE ONCE, REPRICE MANY TIMES. Three of the four levers (price, rate, opex) do not
    read the rent roll at all: `_perturb` shares `inputs.income` BY REFERENCE for those, so the
    engine's O(units) income pass would recompute an identical number on every one of the hundreds
    of re-runs a full analysis performs. The fourth lever (`rent_per_unit_month`) rebuilds every
    `UnitIncome`, so its aggregate genuinely changes and must genuinely be recomputed.

    The test below is that exact distinction, expressed as the strongest form available -- object
    identity, not a value comparison and not a guess about which lever we are on. If the income
    object is not the very same object the precompute was built from, no precompute is used. (The
    engine independently re-checks the same identity and raises on a mismatch; this is a belt and
    braces arrangement, deliberately, because a stale aggregate would be a silently wrong dollar
    figure rather than a visible failure.)

    `rent_shift` (Mission 5 acceleration) is the rent lever's O(1) aggregate-shift fast path:
    the lever adds the same `t` to every unit with no clamping, so its whole effect on the one
    aggregate the engine reads is `gsi + 12*N*t` (`engine.ShiftedIncome` -- built from, and
    identity-validated against, the SAME baseline precompute, in the same loud-failure posture).
    When it is non-zero, `perturbed` must carry the BASELINE income object -- the rent change is
    expressed by the shift, never by a materialised roll (the engine hard-errors on any attempt
    to apply a shift on top of a changed IncomeModel, so double-application is impossible). This
    replaced the O(units) per-probe roll rebuild measured at ~83% of a portfolio-scale analysis;
    the confirming re-runs in `_search_one`/`full_confirm` still materialise the roll and run the
    full engine, so no shifted number is ever the one shown to the investor.
    """
    if rent_shift != 0.0:
        return forecast_metrics(
            perturbed,
            horizon_years=horizon_years,
            income_shift=shift_income(precomputed, rent_shift_month=rent_shift),
        )
    reusable = precomputed if perturbed.income is baseline_income else None
    return forecast_metrics(perturbed, horizon_years=horizon_years, precomputed_income=reusable)


def _signed_delta(lever: LeverName, t: float) -> float:
    """`target_value - baseline_value` for a lever perturbed by non-negative magnitude `t`."""
    return t if lever == "rent_per_unit_month" else -t


def _round_away_from_zero(delta: float, step: float) -> float:
    """Round `|delta|` UP to the next multiple of `step`, preserving sign.

    "Away from zero" keeps the claim true: a required cut of $58,842.37 rounds to a LARGER cut
    ($58,900), never a smaller one that would undershoot the bar the bisection just confirmed.
    """
    if delta == 0.0 or step <= 0.0:
        return delta
    magnitude = math.ceil((abs(delta) / step) - 1e-9) * step
    return math.copysign(magnitude, delta)


# ---------------------------------------------------------------------------
# Reachability probe + bisection (discovery spec §2)
# ---------------------------------------------------------------------------


def _light_probe_one(
    inputs: FinancialInputs,
    lever: LeverName,
    t: float,
    *,
    horizon_years: int,
    total_opex_y1: float,
    precomputed: PrecomputedIncome,
) -> ForecastMetrics:
    """One single-lever SEARCH probe at magnitude `t` -- light path; nothing shipped comes from it.

    The rent lever takes `_rerun`'s O(1) aggregate-shift path: no perturbed copy exists at all
    (the baseline `inputs` goes down unchanged, the shift rides in `engine.ShiftedIncome`). The
    other three levers build their surgical one-submodel copy via `_perturb` exactly as before.
    """
    if lever == "rent_per_unit_month":
        return _rerun(inputs, horizon_years=horizon_years, baseline_income=inputs.income, precomputed=precomputed, rent_shift=t)
    perturbed = _perturb(inputs, lever, t, total_opex_y1=total_opex_y1)
    return _rerun(perturbed, horizon_years=horizon_years, baseline_income=inputs.income, precomputed=precomputed)


def _bisect(
    inputs: FinancialInputs,
    lever: LeverName,
    guardrail: GuardrailName,
    market: MarketAssumptions,
    *,
    bound: float,
    tol: float,
    total_opex_y1: float,
    horizon_years: int,
    precomputed: PrecomputedIncome,
) -> tuple[float, ForecastMetrics, GuardrailChecks]:
    """Standard bisection on `[0, bound]` for the SMALLEST `t` whose re-run clears the guardrail's
    own inclusive `>=` bar. Precondition (guaranteed by the caller's probe): the guardrail fails at
    `t=0` and passes at `t=bound`. Returns `(t*, forecast_at_t*, checks_at_t*)` where `t*` is
    re-run-confirmed to pass -- never an open-interval infimum (discovery spec §2.3).
    """
    lo, hi = 0.0, bound
    forecast_hi: ForecastMetrics | None = None
    checks_hi: GuardrailChecks | None = None
    while hi - lo > tol:
        mid = (lo + hi) / 2.0
        forecast_mid = _light_probe_one(
            inputs, lever, mid, horizon_years=horizon_years, total_opex_y1=total_opex_y1, precomputed=precomputed
        )
        checks_mid = guardrail_checks_from_metrics(forecast_mid, market)
        if _ok(checks_mid, guardrail):
            hi, forecast_hi, checks_hi = mid, forecast_mid, checks_mid
        else:
            lo = mid
    if forecast_hi is None or checks_hi is None:
        forecast_hi = _light_probe_one(inputs, lever, hi, horizon_years=horizon_years, total_opex_y1=total_opex_y1, precomputed=precomputed)
        checks_hi = guardrail_checks_from_metrics(forecast_hi, market)
    return hi, forecast_hi, checks_hi


# ---------------------------------------------------------------------------
# Plausibility (discovery spec §3)
# ---------------------------------------------------------------------------

_LEVER_NOUN: dict[LeverName, str] = {
    "rent_per_unit_month": "rent increase",
    "purchase_price": "price cut",
    "interest_rate": "rate cut",
    "annual_opex": "opex cut",
}


def _baseline_vacancy_reason(snapshot: MarketSnapshot) -> str:
    """The honest reason when the rejector's vacancy-bounds rule fires on the BASELINE alone.

    Every recourse hypothesis (single-lever and joint) carries `vacancy_delta=0.0` -- none of the
    four investor levers moves vacancy -- so when `_derive_snapshot`'s
    `vacancy_rate = 1 - occupancy` already sits outside the rejector's band (any deal with
    occupancy < 0.80), the rule rejects EVERY hypothesis on an axis no ask can move. Saying so,
    in exactly those terms, is what keeps a rejection count from becoming "silence with a
    receipt" (B2's second harm); attributing it to the ask's size would be a false statement.
    """
    return (
        f"this deal's baseline vacancy of {snapshot.vacancy_rate:.1%} sits outside the "
        f"[{VACANCY_MIN:.0%}, {VACANCY_MAX:.0%}] band the plausibility guardrails accept for any market hypothesis — "
        "a fact about the deal itself, not about the asks judged against it."
    )


def _rejector_flagged(
    *,
    lever: LeverName,
    guardrail: GuardrailName,
    delta: float,
    base_forecast: ForecastMetrics,
    target_forecast: ForecastMetrics,
    snapshot: MarketSnapshot,
    market: MarketAssumptions,
) -> tuple[bool, str | None]:
    """Real reuse of `reject_unrealistic` (discovery spec §3.1) -- never a re-decided accept/reject,
    only a composed, more-specific reason string when the SAME rejector call finds a violation.

    Interest-rate lever: literal reuse via `interest_rate_delta` on every closing row.
    Rent/price/opex levers: reuse via a DERIVED `cap_rate_delta` (real engine-computed cap rates,
    never a re-derivation), but only applicable to the `spread`/`cap_floor` guardrails -- the only
    two guardrails that route through `purchase.cap_rate` at all (see `_metric`'s docstring and
    the discovery spec §1.3 reachability table). Every other (lever, guardrail) combination has no
    rejector axis and is judged by the magnitude fallback alone (`_magnitude_flagged`).
    """
    if lever == "interest_rate":
        hyp = MarketHypothesis(
            rent_delta=0.0,
            expense_growth_delta=0.0,
            interest_rate_delta=delta,  # already signed: a cut is negative
            cap_rate_delta=0.0,
            vacancy_delta=0.0,
            str_viability=False,
            prior=1.0,
            rationale="recourse:interest_rate",
        )
    elif guardrail in ("spread", "cap_floor"):
        cap_delta = target_forecast.cap_rate - base_forecast.cap_rate
        hyp = MarketHypothesis(
            rent_delta=0.0,
            expense_growth_delta=0.0,
            interest_rate_delta=0.0,
            cap_rate_delta=cap_delta,
            vacancy_delta=0.0,
            str_viability=False,
            prior=1.0,
            rationale=f"recourse:{lever}",
        )
    else:
        return False, None  # not applicable to this row (see docstring)

    hset = HypothesisSet(snapshot_region=snapshot.region, seed=0, items=(hyp,), notes=None)
    result = reject_unrealistic(hset, snapshot)
    if result.items:
        return False, None

    # Compose a specific reason for the rule the rejector ITSELF names (`violated_hard_rules` is
    # `reject_unrealistic`'s own hard-rejection pass -- one implementation, so the message can
    # never disagree with the decision above; B2 companion fix 2026-08-31: this tail used to
    # assume the cap-band rule and would mislabel a baseline-vacancy rejection as a cap-band
    # one). Messaging only; the accept/reject decision above is never re-derived.
    rules = violated_hard_rules(hyp, snapshot)
    if not rules:  # pragma: no cover -- unreachable: the same pass just emptied `result.items`
        raise RuntimeError("rejector rejected a hypothesis but names no violated rule -- rejector.py refactor bug")
    if "vacancy_bounds" in rules and len(rules) == 1:
        # Only the baseline-vacancy rule fired: nothing about THIS ask tripped the rejector, and
        # naming the ask would mislabel a fact about the deal (B2's silent second harm).
        return True, _baseline_vacancy_reason(snapshot)
    if lever == "interest_rate":
        return True, (
            f"a {abs(delta) * 10_000:.0f} bps rate cut is flagged by the plausibility guardrails "
            "this project uses to judge market-rate hypotheses."
        )
    if "cap_bounds" in rules:
        new_cap = hyp.cap_rate_delta + snapshot.cap_rate
        return True, (
            f"a {_LEVER_NOUN[lever]} this large pushes the implied cap rate to {new_cap:.2%}, outside "
            f"the [{CAP_RATE_MIN:.2%}, {CAP_RATE_MAX:.2%}] range this project treats as a realistic market cap rate."
        )
    # `rates_vs_cap` fired on the cap axis alone (this hypothesis carries no rate move); the old
    # tail mislabeled this case as a cap-band violation.
    return True, (
        f"a {_LEVER_NOUN[lever]} this large moves the implied cap rate by {hyp.cap_rate_delta * 10_000:+.0f} bps with no rate move "
        f"alongside it — more than the {RATES_VS_CAP_MAX_DIVERGENCE * 10_000:.0f} bps divergence this project treats as a "
        "realistic market hypothesis."
    )


def _magnitude_flagged(*, lever: LeverName, delta: float, relative_change: float | None) -> tuple[bool, str | None]:
    """Lever-native magnitude fallback (discovery spec §3.3, Gate D-confirmed thresholds).

    Always applied in addition to `_rejector_flagged` -- two of the four levers (rent, opex) have
    no rejector axis at all, and even the cap-rate proxy is inapplicable to three of the seven
    guardrails (dscr/irr/coc/cf_y1/cf_all), so this is the only check that ever runs for those.
    """
    if lever == "interest_rate":
        if abs(delta) > RATE_MAGNITUDE_THRESHOLD + 1e-12:
            return True, (
                f"a {abs(delta) * 10_000:.0f} bps rate cut is larger than the "
                f"{RATE_MAGNITUDE_THRESHOLD * 10_000:.0f} bps this project treats as a realistic "
                "single-negotiation rate move."
            )
        return False, None

    threshold = _MAGNITUDE_RELATIVE_THRESHOLD[lever]
    if relative_change is not None and relative_change > threshold + 1e-12:
        return True, (
            f"a {_LEVER_NOUN[lever]} of {relative_change:.1%} is larger than the {threshold:.0%} "
            "this project treats as a realistic single ask."
        )
    return False, None


def _judge_plausibility(
    *,
    lever: LeverName,
    guardrail: GuardrailName,
    delta: float,
    relative_change: float | None,
    base_forecast: ForecastMetrics,
    target_forecast: ForecastMetrics,
    snapshot: MarketSnapshot,
    market: MarketAssumptions,
) -> tuple[bool, str | None]:
    reasons: list[str] = []

    rej_flag, rej_reason = _rejector_flagged(
        lever=lever,
        guardrail=guardrail,
        delta=delta,
        base_forecast=base_forecast,
        target_forecast=target_forecast,
        snapshot=snapshot,
        market=market,
    )
    if rej_flag and rej_reason:
        reasons.append(rej_reason)

    mag_flag, mag_reason = _magnitude_flagged(lever=lever, delta=delta, relative_change=relative_change)
    if mag_flag and mag_reason:
        reasons.append(mag_reason)

    plausible = not (rej_flag or mag_flag)
    return plausible, (" ".join(reasons) if reasons else None)


# ---------------------------------------------------------------------------
# Per-(lever, guardrail) row
# ---------------------------------------------------------------------------


def _null_row(*, lever: LeverName, guardrail: GuardrailName, baseline_value: float, structurally_hopeless: bool) -> RecourseLever:
    return RecourseLever(
        guardrail=guardrail,
        lever=lever,
        baseline_value=baseline_value,
        target_value=None,
        delta=None,
        relative_change=None,
        closes_guardrail=False,
        structurally_hopeless=structurally_hopeless,
        plausible=True,
        plausibility_reason=None,
        also_closes=(),
    )


def _search_one(
    inputs: FinancialInputs,
    base_metrics: ForecastMetrics,
    lever: LeverName,
    guardrail: GuardrailName,
    *,
    market: MarketAssumptions,
    snapshot: MarketSnapshot,
    bound: _Bound,
    total_opex_y1: float,
    failing: tuple[GuardrailName, ...],
    horizon_years: int,
    precomputed: PrecomputedIncome,
) -> RecourseLever:
    baseline_value = bound.baseline_value
    tol = _BISECT_TOL[lever]

    # --- Reachability probe (discovery spec §2.1): re-run once at the search bound. ---
    forecast_bound = _light_probe_one(
        inputs, lever, bound.search_bound, horizon_years=horizon_years, total_opex_y1=total_opex_y1, precomputed=precomputed
    )
    checks_bound = guardrail_checks_from_metrics(forecast_bound, market)

    base_metric = _metric(base_metrics, guardrail)
    bound_metric = _metric(forecast_bound, guardrail)

    if abs(bound_metric - base_metric) < 1e-9:
        # The guardrail's own metric does not move at all with this lever, for this deal (e.g.
        # interest_rate never touches cap_rate; or ANY lever vs spread/cap_floor when
        # market.cap_rate_purchase is overridden, per discovery spec §1.3's runtime-detected case).
        return _null_row(lever=lever, guardrail=guardrail, baseline_value=baseline_value, structurally_hopeless=True)

    if not _ok(checks_bound, guardrail):
        # Moved (helpfully or not), but the bound itself never crosses the bar. Honest per-row
        # null: do not assume a fix exists further out, and do not extrapolate past the bound.
        return _null_row(lever=lever, guardrail=guardrail, baseline_value=baseline_value, structurally_hopeless=False)

    # --- Bisect for the smallest t whose re-run clears the bar. ---
    t_star, metrics_star, checks_star = _bisect(
        inputs,
        lever,
        guardrail,
        market,
        bound=bound.search_bound,
        tol=tol,
        total_opex_y1=total_opex_y1,
        horizon_years=horizon_years,
        precomputed=precomputed,
    )

    # --- Round the ask away from zero, then RE-RUN at the rounded value (Gate D). ---
    raw_delta = _signed_delta(lever, t_star)
    rounded_delta = _round_away_from_zero(raw_delta, ROUND_STEP[lever])
    rounded_t = min(abs(rounded_delta), bound.search_bound)
    rounded_delta = math.copysign(rounded_t, raw_delta) if raw_delta != 0.0 else 0.0

    # THE CONFIRMING RE-RUN IS THE FULL ENGINE, deliberately. Everything above this line is
    # search -- probes whose only job is to bracket the answer -- and takes the light path. The
    # value that ends up on the page comes from a real `run_financial_model` forecast, so what the
    # investor is shown and what was tested came off the same object. (The two paths are pinned
    # bit-identical, so this is about provenance and auditability, not about distrusting them.)
    perturbed_rounded = _perturb(inputs, lever, rounded_t, total_opex_y1=total_opex_y1)
    reusable = precomputed if perturbed_rounded.income is inputs.income else None
    forecast_rounded = metrics_of(run_financial_model(perturbed_rounded, horizon_years=horizon_years, precomputed_income=reusable))
    checks_rounded = guardrail_checks_from_metrics(forecast_rounded, market)

    if not _ok(checks_rounded, guardrail):
        # Defensive fallback -- should not trigger given the probe already confirmed monotonic
        # movement toward passing and rounding only ENLARGES the ask in that same direction, but
        # a claim is never shipped without a re-run confirming it: fall back to the bisection's
        # own already-confirmed-passing point rather than the rounded one.
        # Same rule as above: fall back to the bisection's confirmed point, but re-derive it from
        # a FULL engine run rather than shipping the search path's own probe.
        perturbed_star = _perturb(inputs, lever, t_star, total_opex_y1=total_opex_y1)
        reusable_star = precomputed if perturbed_star.income is inputs.income else None
        forecast_star = metrics_of(run_financial_model(perturbed_star, horizon_years=horizon_years, precomputed_income=reusable_star))
        rounded_delta, forecast_rounded, checks_rounded = raw_delta, forecast_star, checks_star

    target_value = baseline_value + rounded_delta
    relative_change = (abs(rounded_delta) / abs(baseline_value)) if baseline_value != 0 else None

    plausible, reason = _judge_plausibility(
        lever=lever,
        guardrail=guardrail,
        delta=rounded_delta,
        relative_change=relative_change,
        base_forecast=base_metrics,
        target_forecast=forecast_rounded,
        snapshot=snapshot,
        market=market,
    )

    also_closes = tuple(g for g in failing if g != guardrail and _ok(checks_rounded, g))

    return RecourseLever(
        guardrail=guardrail,
        lever=lever,
        baseline_value=baseline_value,
        target_value=target_value,
        delta=rounded_delta,
        relative_change=relative_change,
        closes_guardrail=True,
        structurally_hopeless=False,
        plausible=plausible,
        plausibility_reason=reason,
        also_closes=also_closes,
    )


def _pick_cheapest(levers: tuple[RecourseLever, ...]) -> RecourseLever | None:
    """Cheapest-single-fix ordering (discovery spec §4.2): prefer plausible rows over flagged
    ones; within a tier, smallest `relative_change`; ties break on `(lever, guardrail)` machine
    names -- deterministic, never insertion order."""
    closing = [row for row in levers if row.closes_guardrail]
    if not closing:
        return None

    def _key(row: RecourseLever) -> tuple[int, float, str, str]:
        tier = 0 if row.plausible else 1
        rc = row.relative_change if row.relative_change is not None else float("inf")
        return (tier, rc, row.lever, row.guardrail)

    return min(closing, key=_key)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def compute_recourse(inputs: FinancialInputs, *, horizon_years: int = DEFAULT_HORIZON_YEARS) -> RecourseAnalysis:
    """Compute the full recourse analysis for `inputs`.

    Always returns a complete, fully-populated `RecourseAnalysis` -- never `None`, never a
    blanked-out result, regardless of `honest_null`. Callers decide WHETHER to call this at all
    via `is_genuinely_close`; once called, nothing computed here is ever discarded (Roger's Gate D
    ruling -- a computed "nothing realistic closes this" is a real, informative answer, not silence).

    Self-contained by design (mirrors `run_scenarios`' own precedent, `src/market/scenario_runner.py`):
    computes its own fresh baseline via `run_financial_model(inputs)`, ignoring listing insights,
    so every lever's baseline and every perturbed re-run are judged on the exact same footing.

    Runs inside `_search_gc_tuned` (a scoped, always-restored GC-threshold raise): the probe
    loop's short-lived allocations are the measured GC hotspot, and the tuning must never leak
    into the host process.

    Raises `ValueError` if `inputs`' Year 1 NOI is negative (a negative purchase cap rate) --
    see `_derive_snapshot`. `is_genuinely_close` is the normal gate that keeps this from being
    reached in the pipeline; called directly, this precondition is yours to satisfy.
    """
    with _search_gc_tuned():
        return _compute_recourse_impl(inputs, horizon_years=horizon_years)


def _compute_recourse_impl(inputs: FinancialInputs, *, horizon_years: int) -> RecourseAnalysis:
    """`compute_recourse`'s body, inside the GC scope -- see the public wrapper's contract."""
    # Built ONCE for the whole analysis and reused across every re-run whose lever leaves income
    # untouched -- see `_rerun` for the identity rule that decides that, per re-run.
    precomputed = precompute_income(inputs.income)
    base_forecast = run_financial_model(inputs, horizon_years=horizon_years, precomputed_income=precomputed)
    thesis = synthesize_thesis(base_forecast, market=inputs.market)
    base_metrics = metrics_of(base_forecast)
    base_checks = guardrail_checks_from_metrics(base_metrics, inputs.market)

    live = _live_guardrails(inputs.market)
    failing = _failing_guardrails(base_checks, live)

    snapshot = _derive_snapshot(inputs, base_forecast)
    total_opex_y1 = base_forecast.years[0].total_opex

    rows: list[RecourseLever] = []
    for lever in _LEVER_ORDER:
        baseline_value = _baseline_value(inputs, lever, total_opex_y1=total_opex_y1)
        search_bound = _search_bound(inputs, lever, total_opex_y1=total_opex_y1)
        bound = _Bound(baseline_value=baseline_value, search_bound=search_bound)
        for guardrail in failing:
            if (lever, guardrail) in _STATICALLY_HOPELESS:
                rows.append(_null_row(lever=lever, guardrail=guardrail, baseline_value=baseline_value, structurally_hopeless=True))
                continue
            rows.append(
                _search_one(
                    inputs,
                    base_metrics,
                    lever,
                    guardrail,
                    market=inputs.market,
                    snapshot=snapshot,
                    bound=bound,
                    total_opex_y1=total_opex_y1,
                    failing=failing,
                    horizon_years=horizon_years,
                    precomputed=precomputed,
                )
            )

    levers = tuple(rows)
    cheapest = _pick_cheapest(levers)
    honest_null = cheapest is None
    remaining_after_cheapest: tuple[GuardrailName, ...] = ()
    if cheapest is not None:
        remaining_after_cheapest = tuple(g for g in failing if g != cheapest.guardrail and g not in cheapest.also_closes)

    # Mission 5 Half B: the multi-lever combination section, additive beside the single-lever
    # menu (flag-don't-remove — the founder: "we do not know if the investor can act on one or
    # multiple levers"). Shares this analysis's baseline artifacts; no second baseline run.
    combinations = _compute_combinations_core(
        inputs,
        base_metrics=base_metrics,
        failing=failing,
        live=live,
        snapshot=snapshot,
        total_opex_y1=total_opex_y1,
        horizon_years=horizon_years,
        precomputed=precomputed,
        max_iter=DEFAULT_COMBINATION_MAX_ITER,
    )

    return RecourseAnalysis(
        verdict=thesis.verdict,
        failing_guardrails=failing,
        levers=levers,
        cheapest=cheapest,
        remaining_after_cheapest=remaining_after_cheapest,
        honest_null=honest_null,
        combinations=combinations,
    )


# ---------------------------------------------------------------------------
# Multi-lever combinations (Mission 5, Half B / IB.1)
# ---------------------------------------------------------------------------
#
# THE ARCHITECTURE (founder-settled, superseding D.4's fixed ray grid): one minimal-ask solve
# per lever SUBSET (|S| >= 2; singletons are Mission 4's menu above). Within each subset the AD
# gradient (one `forecast_metrics_with_jacobian` pass at t=0) chooses the DIRECTION — steepest
# deficit-normalized margin gain per unit of own-cap ask — and bisection decides the DISTANCE
# along it (measured: margins are monotone non-decreasing along every axis and diagonal inside
# the plausibility box, so the first crossing is the only crossing; a Newton step was measured
# strictly worse, D.4 par.1). The SUBSET RESTRICTION is what keeps the answers distinct: D.5
# measured that unrestricted seeds all collapse to the single min-sum optimum. AD PROPOSES; THE
# ENGINE CONFIRMS: the gradient only ever picks a direction — every shipped number comes from a
# real, un-differentiated `run_financial_model` re-run, and a wrong direction can cost probes,
# never correctness.
#
# THREE OUTCOMES, NEVER TWO: `found` / `proven_null` / `undetermined` (max_iter exhausted — we
# stopped looking). Structurally distinct in `CombinationAnalysis.outcome`; an exhausted budget
# is never reported as a null.

#: Combination arity floor: singletons belong to Mission 4's single-lever menu, so the smallest
#: combination this section will ever show is two levers. This constant is ALSO the R3 budget's
#: derivation base (below) — change it and the budget moves with it, visibly (PD.2 call 2).
_MIN_COMBINATION_LEVERS: int = 2

#: R3, the total-ask budget: `sum_i |delta_i| / cap_i <= B`. Each term is the lever's move as a
#: fraction of ITS OWN single-ask plausibility cap, so the sum's unit is literally "maxed-out
#: single asks" — no cross-lever dollar/bps commensuration anywhere. B is NOT a new magic float:
#: it is the arity floor expressed in that unit — "a combination may not ask for more, in total,
#: than the smallest combination this section will ever show: two levers, each at its individual
#: limit" (PD.2 call 2, with its own band calibration: gate-open crossings measured 1.210-1.640,
#: gate-closed 2.309-2.799; the band assertion lives in the test suite, not here).
_COMBINATION_ASK_BUDGET: float = float(_MIN_COMBINATION_LEVERS)

#: Bisection tolerance on the ray scalar in [0, 1] — finer, in every lever's own native units at
#: its cap, than that lever's ROUND_STEP (e.g. price: 1e-3 x 15% x $605k = $91 < $100).
_COMBINATION_RAY_TOL: float = 1e-3

#: Founder-required per-subset engine-probe budget (light probes + full confirms; the one shared
#: AD pass is outside it). Bounds the outer per-subset solve against the measured pathology of
#: unbounded search on infeasible subsets (D.5: 1,686-2,356 probes vs ~77-246 healthy). The
#: bisection architecture's worst case is ~15 probes/subset (1 corner + <=2 edges + <=10
#: bisections + 2 full confirms); 40 is that ceiling with headroom, and hitting it is reported
#: as UNDETERMINED — deterministically: same inputs, same probe sequence, same exhaustion point.
DEFAULT_COMBINATION_MAX_ITER: int = 40

#: Guardrail -> the `ForecastMetrics` field its bar tests, in Jacobian row names. `dscr` maps to
#: `year1_dscr` because `guardrail_checks_from_metrics` tests exactly that field.
_GUARDRAIL_METRIC: dict[GuardrailName, MetricName] = {
    "dscr": "year1_dscr",
    "spread": "spread_vs_rate",
    "irr": "irr_10yr",
    "coc": "coc",
    "cf_y1": "cash_flow_y1",
    "cf_all": "min_cash_flow",
    "cap_floor": "cap_rate",
}


def _bar(guardrail: GuardrailName, market: MarketAssumptions) -> float:
    """The guardrail's own inclusive `>=` bar — the same constants `guardrail_checks_from_metrics`
    tests, never a re-derivation."""
    if guardrail == "dscr":
        return MIN_DSCR_Y1
    if guardrail == "spread":
        return spread_target_for(market)
    if guardrail == "irr":
        return MIN_IRR_10YR
    if guardrail == "coc":
        return MIN_COC_Y1
    if guardrail in ("cf_y1", "cf_all"):
        return 0.0
    if market.cap_rate_floor is None:  # cap_floor is only ever live when the user set a floor
        raise ValueError("cap_floor bar requested but market.cap_rate_floor is not configured")
    return market.cap_rate_floor


def _lever_cap(lever: LeverName, *, baseline_value: float) -> float:
    """The lever's single-ask plausibility cap in its own native units — reuse of Mission 4's own
    constants (`_MAGNITUDE_RELATIVE_THRESHOLD` / `RATE_MAGNITUDE_THRESHOLD`), with the rate cap
    floored at a 0% rate (a cut below zero is not a negotiation)."""
    if lever == "interest_rate":
        return min(RATE_MAGNITUDE_THRESHOLD, max(0.0, baseline_value))
    return _MAGNITUDE_RELATIVE_THRESHOLD[lever] * abs(baseline_value)


def _combination_subsets(available: tuple[LeverName, ...]) -> tuple[tuple[LeverName, ...], ...]:
    """All lever subsets with |S| >= _MIN_COMBINATION_LEVERS whose members are all `available`,
    in (|S|, lexicographic-in-`_LEVER_ORDER`) order — deterministic, never a dict/set iteration.

    GD3 (partition Ruling 4): the candidate space is drawn from the SANCTIONED builder
    `partition.investor_lever_combinations`, never a hand-rolled enumeration, so an assumption
    axis has no path into the search space short of editing `INVESTOR_LEVERS` itself (a Founder
    Proxy escalation citing GD3). Filtering to `available` (levers with a non-zero plausibility
    box) preserves the builder's fixed order.
    """
    allowed = frozenset(available)
    return tuple(s for s in investor_lever_combinations(min_size=_MIN_COMBINATION_LEVERS) if allowed.issuperset(s))


def _lever_directions(inputs: FinancialInputs, available: tuple[LeverName, ...], *, total_opex_y1: float) -> tuple[TangentDirection, ...]:
    """One named Jacobian column per available lever: d(engine input)/d(ask magnitude t), exactly
    mirroring `_perturb`'s own action (rent: +t on every unit -> d(gsi)/dt = 12*N; price/rate:
    -t; opex: each line scaled by (1 - t/total) -> d(line)/dt = -line/total). At most 4 levers =
    `MAX_DIRECTIONS` (Dual4's fixed tangent width), so this always fits in ONE dual pass."""
    if len(available) > MAX_DIRECTIONS:  # structurally impossible with 4 levers; loud if it ever changes
        raise ValueError(f"{len(available)} lever directions exceed the Dual4 width {MAX_DIRECTIONS}")
    directions: list[TangentDirection] = []
    for lever in available:
        seeds: tuple[tuple[SeedTarget, float], ...]
        if lever == "rent_per_unit_month":
            seeds = (("income.gsi_annual", 12.0 * len(inputs.income.units)),)
        elif lever == "purchase_price":
            seeds = (("financing.purchase_price", -1.0),)
        elif lever == "interest_rate":
            seeds = (("financing.interest_rate", -1.0),)
        else:  # annual_opex: the proportional spread `_perturb` applies, differentiated
            seeds = tuple((cast(SeedTarget, ("opex", field)), -getattr(inputs.opex, field) / total_opex_y1) for field in _OPEX_FIELDS)
        directions.append(TangentDirection(name=lever, seeds=seeds))
    return tuple(directions)


def _direction_weights(
    subset: tuple[LeverName, ...],
    jac: MetricsJacobian,
    *,
    failing: tuple[GuardrailName, ...],
    market: MarketAssumptions,
    caps: Mapping[LeverName, float],
) -> tuple[float, ...]:
    """The AD gradient's direction WITHIN a subset, as own-cap-fraction weights (max weight 1.0).

    Score per lever = sum over failing guardrails of (full-cap margin gain / deficit): the
    steepest deficit-normalized margin gain per unit of own-cap ask. Guardrails are made
    commensurate by their own deficits (bar - value, > 0 for a failing guardrail), never by a
    cross-lever unit mix. Honest degradation: any `None` partial (no trustworthy derivative —
    jacobian's None-is-never-0.0 contract) or an all-zero gradient falls back to the balanced
    direction. The weights only steer probes; the engine's re-runs decide everything shipped.
    """
    balanced = tuple(1.0 for _ in subset)
    scores: list[float] = []
    for lever in subset:
        score = 0.0
        for guardrail in failing:
            metric = _GUARDRAIL_METRIC[guardrail]
            partial = jac.partial(metric, lever)
            if partial is None:
                return balanced
            deficit = _bar(guardrail, market) - jac.value(metric)
            score += max(0.0, partial) * caps[lever] / max(deficit, 1e-12)
        scores.append(score)
    top = max(scores)
    if top <= 0.0:
        return balanced
    return tuple(score / top for score in scores)


_Asks = tuple[tuple[LeverName, float], ...]


def _ray_asks(subset: tuple[LeverName, ...], weights: tuple[float, ...], caps: Mapping[LeverName, float], s: float) -> _Asks:
    return tuple((lever, s * weight * caps[lever]) for lever, weight in zip(subset, weights, strict=True))


def _perturb_combo(inputs: FinancialInputs, asks: _Asks, *, total_opex_y1: float) -> FinancialInputs:
    """Perturb several levers at once by chaining `_perturb` in `_LEVER_ORDER` (asks arrive in
    that order by construction). Submodels are disjoint per lever except financing (price, rate),
    where chained `model_copy` composes exactly; the opex cut stays relative to the BASELINE
    `total_opex_y1`. Levers with t=0 are skipped so `inputs.income` keeps its identity (and the
    income precompute stays reusable) whenever rent is untouched."""
    perturbed = inputs
    for lever, t in asks:
        if t > 0.0:
            perturbed = _perturb(perturbed, lever, t, total_opex_y1=total_opex_y1)
    return perturbed


def _perturb_combo_light(inputs: FinancialInputs, asks: _Asks, *, total_opex_y1: float) -> tuple[FinancialInputs, float]:
    """`_perturb_combo` for SEARCH probes: the rent ask is split out as an aggregate shift.

    Returns `(perturbed, rent_t)` where `perturbed` carries every non-rent ask (surgical copies,
    exactly `_perturb_combo`'s composition) and still shares the BASELINE `IncomeModel` by
    reference, and `rent_t` is the rent ask (0.0 when rent is untouched) to hand to `_rerun`'s
    `rent_shift` -- the O(1) equivalent of materialising the roll (see `_rerun`). Confirming
    re-runs must keep using `_perturb_combo`: shipped numbers come off a materialised roll.
    """
    perturbed = inputs
    rent_t = 0.0
    for lever, t in asks:
        if t <= 0.0:
            continue
        if lever == "rent_per_unit_month":
            rent_t = t
        else:
            perturbed = _perturb(perturbed, lever, t, total_opex_y1=total_opex_y1)
    return perturbed, rent_t


#: Gen-0/1/2 GC thresholds inside the search scope (Mission 5 acceleration). The search loop is
#: an allocation storm of provably-unreachable-on-return short-lived objects (perturbed pydantic
#: submodels, per-probe `ForecastMetrics`), and CPython's default gen-0 threshold of 700 makes
#: the collector run thousands of times inside one analysis for nothing -- measured 71.8 ms ->
#: 63.3 ms best (~12%) on the 5,000u/100y ceiling row with these values, indistinguishable from
#: `gc.disable()` (63.2 ms) but bounded: collection still happens, so a pathological host cannot
#: grow without limit inside the scope.
_SEARCH_GC_THRESHOLD: tuple[int, int, int] = (50_000, 10, 10)


@contextmanager
def _search_gc_tuned() -> Iterator[None]:
    """Raise the GC thresholds for the duration of one recourse search, then restore, always.

    SCOPED, NOT PROCESS-WIDE, DELIBERATELY: a library that retunes the process collector at
    import (or leaves it retuned after a call) imposes a silent side effect on its host -- every
    other allocation pattern in the embedding app would inherit our trade-off without consenting
    to it. This scope is exactly the measured allocation storm (the probe loops of
    `compute_recourse` / `compute_combinations`) and nothing else; the previous thresholds are
    restored on every exit path, exceptions included (pinned by
    `tests/perf/test_perf_gates.py::TestSearchGcScope`). Only thresholds are touched -- never
    `gc.enable`/`gc.disable` -- so a host that runs with GC disabled stays disabled.
    """
    previous = gc.get_threshold()
    gc.set_threshold(*_SEARCH_GC_THRESHOLD)
    try:
        yield
    finally:
        gc.set_threshold(*previous)


class _ProbeBudget:
    """The founder-required `max_iter` bound, counted in engine evaluations (light probes and
    full confirming runs alike) per subset solve. Deterministic: the probe sequence is fixed by
    the enumeration, so the same inputs exhaust at the same probe, every run."""

    __slots__ = ("limit", "used")

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.used = 0

    def spend(self) -> bool:
        """Reserve one probe; False when the budget is exhausted (caller reports UNDETERMINED)."""
        if self.used >= self.limit:
            return False
        self.used += 1
        return True


def _r2_reason(rule: HardRule, *, rate_delta: float, cap_delta: float, snapshot: MarketSnapshot) -> str:
    """The joint gate's reason for ONE rejector rule, named by the rejector itself.

    TOTAL over `HardRule` -- every rule maps to a non-empty string, and the trailing
    `assert_never(rule)` is what makes mypy prove the chain exhaustive at type-check time: a bare
    `raise AssertionError(...)` type-checks as returning `str` on every path (it satisfies any
    return type -- verified with a minimal `mypy --strict` repro), so it would NOT have caught a
    new `HardRule` member; `assert_never`'s parameter type is `Never`, so passing it anything
    still-possibly-a-`HardRule` is a mypy error, and a new member added to `HardRule` without a
    matching `if` above turns into exactly that error here. The call is an unreachable runtime
    backstop only once mypy has confirmed there is nothing left for it to reach. Totality is B2's
    structural guarantee: R2 trips exactly when `violated_hard_rules` is non-empty, and each named
    rule yields one reason, so a rejection can never again ship with `reasons=()` (the empty
    string that crashed `RejectedCombination`'s `min_length=1` on any deal with occupancy < 0.80).

    Thresholds in the copy are the rejector's own named constants (`rejector.py`) -- the same
    objects the decision used -- never re-stated literals, so decision and message cannot drift.
    """
    if rule == "rates_vs_cap":
        divergence = abs(rate_delta - cap_delta)
        if rate_delta != 0.0:
            return (
                f"a {abs(rate_delta) * 10_000:.0f} bps rate cut alongside a combination that moves the implied cap rate by "
                f"{cap_delta * 10_000:+.0f} bps moves rates and cap apart by {divergence * 10_000:.0f} bps — more than the "
                f"{RATES_VS_CAP_MAX_DIVERGENCE * 10_000:.0f} bps divergence this project treats as a realistic market hypothesis."
            )
        return (
            f"this combination moves the implied cap rate by {cap_delta * 10_000:+.0f} bps with no rate move alongside it — "
            f"rates and cap moving apart by more than the {RATES_VS_CAP_MAX_DIVERGENCE * 10_000:.0f} bps divergence this project "
            "treats as a realistic market hypothesis."
        )
    if rule == "cap_bounds":
        new_cap = snapshot.cap_rate + cap_delta
        return (
            f"this combination pushes the implied cap rate to {new_cap:.2%}, outside the "
            f"[{CAP_RATE_MIN:.2%}, {CAP_RATE_MAX:.2%}] range this project "
            "treats as a realistic market cap rate."
        )
    if rule == "vacancy_bounds":
        return _baseline_vacancy_reason(snapshot)
    if rule == "rent_vs_vacancy":
        # Unreachable for the R2 hypothesis as constructed (its rent_delta and vacancy_delta are
        # both 0.0), but totality is the point: a future edit that populates those axes still
        # gets words, never an empty tuple.
        return (
            "the rejector's rent-vs-vacancy coherence rule fired: a rent-growth move this strong is not plausible "
            "alongside the assumed vacancy move."
        )
    assert_never(rule)  # pragma: no cover -- mypy proves the chain exhaustive (see docstring)


@dataclass(frozen=True)
class CombinationJudgment:
    """The joint plausibility gate's verdict on ONE combination — a pure judgment, engine-free
    (the caller hands in the confirming run's metrics; the gate never runs the engine)."""

    plausible: bool
    reasons: tuple[str, ...]
    tripped_rules: tuple[str, ...]


def judge_combination(
    deltas: Mapping[LeverName, float],
    *,
    base_metrics: ForecastMetrics,
    target_metrics: ForecastMetrics,
    baselines: Mapping[LeverName, float],
    snapshot: MarketSnapshot,
    market: MarketAssumptions,
) -> CombinationJudgment:
    """The unified all-lever joint plausibility gate (D.4 par.3, PD.2-ratified: R1 + R2 + R3; R4
    rejected for v1). Deterministic and boolean; an a-posteriori FILTER on engine-computed
    quantities, never an objective term and never a pretend-inverse of the engine.

    `deltas` are SIGNED, exactly as shipped (rent +, cuts -), keyed by lever; levers absent or
    zero are untouched. All rules are always evaluated and their reasons compose, in fixed rule
    order (same posture as `_judge_plausibility` above).

    - R1 — per-lever caps: literal reuse of `_magnitude_flagged` (same constants, same
      strict-`>`-plus-1e-12 comparison). The search already stays inside this box, but the gate
      judges ANY combination handed to it, so the rule stays here (self-containment).
    - R2 — joint rejector reuse: ONE `MarketHypothesis` carrying BOTH the combination's signed
      rate delta AND its engine-computed implied-cap delta (`target.cap_rate - base.cap_rate`,
      real re-run cap rates) through the UNMODIFIED `reject_unrealistic` — so the rejector's own
      cross-axis rule `|interest_rate_delta - cap_rate_delta| <= 0.02` (`rejector.py`) finally
      fires JOINTLY, with zero new constants, and the [3%, 12%] cap band comes along for free.
      ALL FOUR rejector rules apply, including vacancy bounds: the hypothesis carries
      `vacancy_delta=0`, so that rule can only fire on the deal's BASELINE vacancy
      (occupancy < 0.80 => vacancy > 20%), rejecting every combination on an axis no lever moves
      — the reason says exactly that (see `_baseline_vacancy_reason`; B2). Reasons come from
      `violated_hard_rules` + the total `_r2_reason`, never re-derived literals.
      SEMANTIC STRETCH, DOCUMENTED (PD.2 R2 condition 2): `cap_rate_delta` in the rejector means
      "the market's cap rate moves"; here it carries "this deal's IMPLIED cap moves because the
      combination changed price/rent/opex" — the same stretch Mission 4's single-lever
      `_rejector_flagged` already ships, extended jointly. DEGENERATE CASE, PINNED BY TEST: when
      `market.cap_rate_purchase` is overridden the implied cap never moves, so `cap_rate_delta`
      is 0 and R2 collapses to `|rate_delta| <= 0.02` — weaker than R1's own 100 bps cap, i.e.
      inert. That silent-does-nothing fact is stated here so it cannot rot.
    - R3 — total own-fraction ask budget: `sum |delta_i| / cap_i <= _COMBINATION_ASK_BUDGET`
      (the arity-floor-derived B; see the constant). Each term is own-axis; the sum's unit is
      "maxed-out single asks", and the reason states it in exactly that unit where it bites.
    """
    reasons: list[str] = []
    tripped: list[str] = []

    # --- R1: per-lever caps, reused verbatim from the single-lever gate ----------------------
    for lever in _LEVER_ORDER:
        delta = deltas.get(lever, 0.0)
        if delta == 0.0:
            continue
        baseline = baselines[lever]
        relative = (abs(delta) / abs(baseline)) if baseline != 0 else None
        flagged, reason = _magnitude_flagged(lever=lever, delta=delta, relative_change=relative)
        if flagged and reason:
            if "R1" not in tripped:
                tripped.append("R1")
            reasons.append(reason)

    # --- R2: the joint rejector — both axes populated at once --------------------------------
    rate_delta = deltas.get("interest_rate", 0.0)
    cap_delta = target_metrics.cap_rate - base_metrics.cap_rate
    hyp = MarketHypothesis(
        rent_delta=0.0,
        expense_growth_delta=0.0,
        interest_rate_delta=rate_delta,
        cap_rate_delta=cap_delta,
        vacancy_delta=0.0,
        str_viability=False,
        prior=1.0,
        rationale="recourse:combination",
    )
    hset = HypothesisSet(snapshot_region=snapshot.region, seed=0, items=(hyp,), notes=None)
    r2_rejected = not reject_unrealistic(hset, snapshot).items
    # Messaging: ask the rejector WHICH rule fired (`violated_hard_rules` IS `reject_unrealistic`'s
    # hard-rejection pass — one implementation, so decision and diagnosis cannot drift). B2 fix
    # (Gate V, 2026-08-31): this block used to re-derive the rule from duplicated literals,
    # reproduced only 2 of the rejector's 4 rules, and shipped `reasons=()` — a pipeline-reachable
    # `ValidationError` against `RejectedCombination.reason`'s `min_length=1` — whenever the
    # un-reproduced vacancy-bounds rule fired alone, which ANY deal with occupancy < 0.80 triggers
    # via `_derive_snapshot`. `_r2_reason` is total over `HardRule`, so R2 tripping now implies at
    # least one reason, structurally (PD.2 R2 condition 1 restored by construction).
    r2_rules = violated_hard_rules(hyp, snapshot)
    if r2_rejected != bool(r2_rules):  # pragma: no cover -- unreachable: one implementation serves both callers
        raise RuntimeError(
            f"R2 decision/diagnosis split: reject_unrealistic rejected={r2_rejected} but "
            f"violated_hard_rules names {r2_rules!r} — rejector.py refactor bug."
        )
    if r2_rules:
        tripped.append("R2")
        reasons.extend(_r2_reason(rule, rate_delta=rate_delta, cap_delta=cap_delta, snapshot=snapshot) for rule in r2_rules)

    # --- R3: the total own-fraction ask budget ------------------------------------------------
    total_fraction = 0.0
    for lever in _LEVER_ORDER:
        delta = deltas.get(lever, 0.0)
        if delta == 0.0:
            continue
        cap = _lever_cap(lever, baseline_value=baselines[lever])
        total_fraction += (abs(delta) / cap) if cap > 0.0 else math.inf
    if total_fraction > _COMBINATION_ASK_BUDGET + 1e-12:
        tripped.append("R3")
        reasons.append(
            f"this combination totals {total_fraction:.1f} maxed-out single asks; this project shows at most "
            f"{_COMBINATION_ASK_BUDGET:.0f}."
        )

    return CombinationJudgment(plausible=not tripped, reasons=tuple(reasons), tripped_rules=tuple(tripped))


_SubsetStatus = Literal["found", "infeasible", "edge_infeasible", "gate_rejected", "collapsed", "confirm_failed", "exhausted"]


@dataclass(frozen=True)
class _SubsetOutcome:
    status: _SubsetStatus
    combination: RecourseCombination | None = None
    rejected: RejectedCombination | None = None
    gate_reasons: tuple[str, ...] = ()


def _build_combination(
    asks: _Asks,
    *,
    baselines: Mapping[LeverName, float],
    caps: Mapping[LeverName, float],
    confirmed: ForecastMetrics,
    live: frozenset[GuardrailName],
    market: MarketAssumptions,
    rounded: bool,
) -> RecourseCombination:
    """Assemble the shipped shape from the CONFIRMING run's metrics and nothing else."""
    moves = []
    total_fraction = 0.0
    for lever, t in asks:
        if t <= 0.0:
            continue
        delta = _signed_delta(lever, t)
        fraction = t / caps[lever]
        total_fraction += fraction
        moves.append(
            CombinationLeverMove(
                lever=lever,
                baseline_value=baselines[lever],
                target_value=baselines[lever] + delta,
                delta=delta,
                relative_change=abs(delta) / abs(baselines[lever]),
                fraction_of_cap=fraction,
            )
        )
    margins = tuple(GuardrailMargin(guardrail=g, bar=_bar(g, market), value=_metric(confirmed, g)) for g in _GUARDRAIL_ORDER if g in live)
    return RecourseCombination(
        moves=tuple(moves),
        closes_all_live_guardrails=True,
        confirmed_margins=margins,
        rounded=rounded,
        total_fraction_of_caps=total_fraction,
    )


def _solve_subset(
    inputs: FinancialInputs,
    subset: tuple[LeverName, ...],
    *,
    jac: MetricsJacobian,
    base_metrics: ForecastMetrics,
    baselines: Mapping[LeverName, float],
    caps: Mapping[LeverName, float],
    live: frozenset[GuardrailName],
    failing: tuple[GuardrailName, ...],
    market: MarketAssumptions,
    snapshot: MarketSnapshot,
    total_opex_y1: float,
    horizon_years: int,
    precomputed: PrecomputedIncome,
    max_iter: int,
) -> _SubsetOutcome:
    """One minimal-ask solve for one lever subset: corner proof, gradient direction, bisected
    distance, round, confirm-by-rerun, joint gate. Every exit is a named, counted outcome."""
    budget = _ProbeBudget(max_iter)

    def light_probe(asks: _Asks) -> tuple[ForecastMetrics, bool] | None:
        """Light-path probe (search only; nothing shown to the investor comes from it). None on
        budget exhaustion."""
        if not budget.spend():
            return None
        perturbed, rent_t = _perturb_combo_light(inputs, asks, total_opex_y1=total_opex_y1)
        m = _rerun(perturbed, horizon_years=horizon_years, baseline_income=inputs.income, precomputed=precomputed, rent_shift=rent_t)
        feasible = _num_fails(guardrail_checks_from_metrics(m, market), live) == 0
        return m, feasible

    def full_confirm(asks: _Asks) -> tuple[ForecastMetrics, bool] | None:
        """THE CONFIRMING RE-RUN IS THE FULL ENGINE — same provenance rule as `_search_one`."""
        if not budget.spend():
            return None
        perturbed = _perturb_combo(inputs, asks, total_opex_y1=total_opex_y1)
        reusable = precomputed if perturbed.income is inputs.income else None
        m = metrics_of(run_financial_model(perturbed, horizon_years=horizon_years, precomputed_income=reusable))
        feasible = _num_fails(guardrail_checks_from_metrics(m, market), live) == 0
        return m, feasible

    # --- Corner proof: the full-cap corner dominates every point of the subset's box, and the
    # measured monotone-margin property makes that a real proof — corner fails => the whole
    # plausibility box fails, for this subset (an honest, engine-probed PROVEN-empty exit). ---
    corner = tuple((lever, caps[lever]) for lever in subset)
    corner_result = light_probe(corner)
    if corner_result is None:
        return _SubsetOutcome("exhausted")
    if not corner_result[1]:
        return _SubsetOutcome("infeasible")

    # --- Direction (AD gradient), then the R3 budget as an A PRIORI clip on the ray scalar
    # (PD.2 R3 condition 4): no probe is ever spent past sum-of-fractions = B. Fallback to the
    # balanced ray when the gradient ray's clipped edge does not cross (D.5's honest fallback).
    balanced = tuple(1.0 for _ in subset)
    gradient = _direction_weights(subset, jac, failing=failing, market=market, caps=caps)
    chosen: tuple[tuple[float, ...], float] | None = None
    for weights in (gradient, balanced) if gradient != balanced else (balanced,):
        s_edge = min(1.0, _COMBINATION_ASK_BUDGET / sum(weights))
        edge_asks = _ray_asks(subset, weights, caps, s_edge)
        if edge_asks == corner:  # the balanced edge of a pair IS the corner, already probed feasible
            chosen = (weights, s_edge)
            break
        edge_result = light_probe(edge_asks)
        if edge_result is None:
            return _SubsetOutcome("exhausted")
        if edge_result[1]:
            chosen = (weights, s_edge)
            break
    if chosen is None:
        return _SubsetOutcome("edge_infeasible")

    # --- Distance: safeguarded bisection on the ray scalar (first crossing = only crossing
    # under the measured monotonicity; the confirm below still re-verifies for real). ---------
    weights, s_edge = chosen
    lo, hi = 0.0, s_edge
    while hi - lo > _COMBINATION_RAY_TOL:
        mid = (lo + hi) / 2.0
        mid_result = light_probe(_ray_asks(subset, weights, caps, mid))
        if mid_result is None:
            return _SubsetOutcome("exhausted")
        if mid_result[1]:
            hi = mid
        else:
            lo = mid
    crossing = _ray_asks(subset, weights, caps, hi)

    # --- Round each ask away from zero (the claim stays true), clipped back to its cap; a
    # combination that rounds below two live levers is single-lever territory (Mission 4's). ---
    rounded_asks = tuple(
        (lever, min(caps[lever], abs(_round_away_from_zero(_signed_delta(lever, t), ROUND_STEP[lever])))) for lever, t in crossing
    )
    active_rounded = tuple((lever, t) for lever, t in rounded_asks if t > 0.0)
    if len(active_rounded) < _MIN_COMBINATION_LEVERS:
        return _SubsetOutcome("collapsed")

    def judge(asks: _Asks, confirmed: ForecastMetrics) -> CombinationJudgment:
        deltas = {lever: _signed_delta(lever, t) for lever, t in asks}
        return judge_combination(
            deltas, base_metrics=base_metrics, target_metrics=confirmed, baselines=baselines, snapshot=snapshot, market=market
        )

    # --- Confirm-by-rerun at the rounded asks, then the joint gate on the CONFIRMED metrics. --
    rejected: RejectedCombination | None = None
    gate_reasons: tuple[str, ...] = ()
    rounded_confirm = full_confirm(active_rounded)
    if rounded_confirm is None:
        return _SubsetOutcome("exhausted")
    if rounded_confirm[1]:
        judgment = judge(active_rounded, rounded_confirm[0])
        combo = _build_combination(
            active_rounded, baselines=baselines, caps=caps, confirmed=rounded_confirm[0], live=live, market=market, rounded=True
        )
        if judgment.plausible:
            return _SubsetOutcome("found", combination=combo)
        rejected = RejectedCombination(combination=combo, reason=" ".join(judgment.reasons))
        gate_reasons = judgment.reasons

    # --- Fallback: the exact (unrounded) crossing, exactly Mission 4's fallback posture — used
    # when the rounded confirm failed a guardrail (defensive) OR when rounding alone pushed the
    # asks across a gate boundary the crossing itself respects. ---------------------------------
    active_unrounded = tuple((lever, t) for lever, t in crossing if t > 0.0)
    unrounded_confirm = full_confirm(active_unrounded)
    if unrounded_confirm is None:
        return _SubsetOutcome("exhausted")
    if unrounded_confirm[1]:
        judgment = judge(active_unrounded, unrounded_confirm[0])
        if judgment.plausible:
            combo = _build_combination(
                active_unrounded, baselines=baselines, caps=caps, confirmed=unrounded_confirm[0], live=live, market=market, rounded=False
            )
            return _SubsetOutcome("found", combination=combo)
        if rejected is None:
            combo = _build_combination(
                active_unrounded, baselines=baselines, caps=caps, confirmed=unrounded_confirm[0], live=live, market=market, rounded=False
            )
            rejected = RejectedCombination(combination=combo, reason=" ".join(judgment.reasons))
            gate_reasons = judgment.reasons
    if rejected is not None:
        return _SubsetOutcome("gate_rejected", rejected=rejected, gate_reasons=gate_reasons)
    return _SubsetOutcome("confirm_failed")


def _compute_combinations_core(
    inputs: FinancialInputs,
    *,
    base_metrics: ForecastMetrics,
    failing: tuple[GuardrailName, ...],
    live: frozenset[GuardrailName],
    snapshot: MarketSnapshot,
    total_opex_y1: float,
    horizon_years: int,
    precomputed: PrecomputedIncome,
    max_iter: int,
) -> CombinationAnalysis:
    """The subset-restricted multi-lever search over shared baseline artifacts (see
    `compute_combinations` for the self-contained entry point and the full contract)."""
    if max_iter <= 0:
        raise ValueError(f"max_iter must be a positive per-subset probe budget, got {max_iter}")
    if not failing:
        return CombinationAnalysis(
            attempted=False,
            outcome=None,
            combinations=(),
            cheapest_total_index=None,
            honest_null=False,
            subsets_searched=0,
            subsets_infeasible=0,
            subsets_edge_infeasible=0,
            subsets_gate_rejected=0,
            subsets_collapsed=0,
            subsets_exhausted=0,
            gate_reasons=(),
            confirm_failed=0,
            rejected_exemplar=None,
            max_iter=max_iter,
        )

    baselines: dict[LeverName, float] = {}
    caps: dict[LeverName, float] = {}
    for lever in _LEVER_ORDER:
        baselines[lever] = _baseline_value(inputs, lever, total_opex_y1=total_opex_y1)
        caps[lever] = _lever_cap(lever, baseline_value=baselines[lever])
    # A lever with a zero-width plausible box (e.g. a 0% baseline rate) is excluded statically —
    # deterministic by rule, not by float accident.
    available = tuple(lever for lever in _LEVER_ORDER if caps[lever] > 0.0)
    subsets = _combination_subsets(available)

    outcomes: list[_SubsetOutcome] = []
    if subsets:
        # ONE dual pass for the whole analysis: every subset's direction reads off this Jacobian.
        jac = forecast_metrics_with_jacobian(
            inputs,
            _lever_directions(inputs, available, total_opex_y1=total_opex_y1),
            horizon_years=horizon_years,
            precomputed_income=precomputed,
        )
        for subset in subsets:
            outcomes.append(
                _solve_subset(
                    inputs,
                    subset,
                    jac=jac,
                    base_metrics=base_metrics,
                    baselines=baselines,
                    caps=caps,
                    live=live,
                    failing=failing,
                    market=inputs.market,
                    snapshot=snapshot,
                    total_opex_y1=total_opex_y1,
                    horizon_years=horizon_years,
                    precomputed=precomputed,
                    max_iter=max_iter,
                )
            )

    # --- Aggregate, in subset enumeration order (deterministic end to end). -------------------
    combinations: list[RecourseCombination] = []
    counters = {"infeasible": 0, "edge_infeasible": 0, "gate_rejected": 0, "collapsed": 0, "exhausted": 0, "confirm_failed": 0}
    gate_reasons: list[str] = []
    rejected_candidates: list[tuple[float, int, RejectedCombination]] = []
    for ordinal, outcome in enumerate(outcomes):
        if outcome.status == "found" and outcome.combination is not None:
            if any(existing.moves == outcome.combination.moves for existing in combinations):
                counters["collapsed"] += 1  # a wider subset degenerated onto an already-found answer
            else:
                combinations.append(outcome.combination)
        elif outcome.status == "gate_rejected":
            counters["gate_rejected"] += 1
            for reason in outcome.gate_reasons:
                if reason not in gate_reasons:
                    gate_reasons.append(reason)
            if outcome.rejected is not None:
                rejected_candidates.append((outcome.rejected.combination.total_fraction_of_caps, ordinal, outcome.rejected))
        else:
            counters[outcome.status] += 1

    # THE THREE OUTCOMES: found / proven_null / undetermined. An exhausted subset with zero
    # findings means we STOPPED LOOKING — never a proof that nothing exists.
    outcome_label: Literal["found", "proven_null", "undetermined"]
    if combinations:
        outcome_label = "found"
    elif counters["exhausted"] > 0:
        outcome_label = "undetermined"
    else:
        outcome_label = "proven_null"
    honest_null = outcome_label == "proven_null"

    cheapest_index: int | None = None
    if combinations:
        cheapest_index = min(range(len(combinations)), key=lambda i: (combinations[i].total_fraction_of_caps, i))

    exemplar: RejectedCombination | None = None
    if honest_null and rejected_candidates:
        exemplar = min(rejected_candidates, key=lambda item: (item[0], item[1]))[2]

    return CombinationAnalysis(
        attempted=True,
        outcome=outcome_label,
        combinations=tuple(combinations),
        cheapest_total_index=cheapest_index,
        honest_null=honest_null,
        subsets_searched=len(subsets),
        subsets_infeasible=counters["infeasible"],
        subsets_edge_infeasible=counters["edge_infeasible"],
        subsets_gate_rejected=counters["gate_rejected"],
        subsets_collapsed=counters["collapsed"],
        subsets_exhausted=counters["exhausted"],
        gate_reasons=tuple(gate_reasons),
        confirm_failed=counters["confirm_failed"],
        rejected_exemplar=exemplar,
        max_iter=max_iter,
    )


def compute_combinations(
    inputs: FinancialInputs,
    *,
    horizon_years: int = DEFAULT_HORIZON_YEARS,
    max_iter: int = DEFAULT_COMBINATION_MAX_ITER,
) -> CombinationAnalysis:
    """Compute the multi-lever combination analysis for `inputs`, self-contained (own fresh
    baseline, mirroring `compute_recourse`'s precedent).

    Always returns a complete `CombinationAnalysis`. `attempted` is False (and `outcome` None)
    only when no live guardrail is failing — there is nothing to search. Otherwise `outcome` is
    exactly one of the three: `found`, `proven_null`, or `undetermined` (`max_iter` exhausted —
    see `DEFAULT_COMBINATION_MAX_ITER`). Same inputs => byte-identical result, including the
    exhaustion point.

    Runs inside `_search_gc_tuned`, same contract as `compute_recourse`.

    Raises `ValueError` if `inputs`' Year 1 NOI is negative (a negative purchase cap rate) --
    see `_derive_snapshot`. `is_genuinely_close` is the normal gate that keeps this from being
    reached in the pipeline; called directly (this is documented public API,
    `src/market/README.md`), this precondition is yours to satisfy.
    """
    with _search_gc_tuned():
        return _compute_combinations_impl(inputs, horizon_years=horizon_years, max_iter=max_iter)


def _compute_combinations_impl(inputs: FinancialInputs, *, horizon_years: int, max_iter: int) -> CombinationAnalysis:
    """`compute_combinations`' body, inside the GC scope -- see the public wrapper's contract."""
    precomputed = precompute_income(inputs.income)
    base_forecast = run_financial_model(inputs, horizon_years=horizon_years, precomputed_income=precomputed)
    base_metrics = metrics_of(base_forecast)
    base_checks = guardrail_checks_from_metrics(base_metrics, inputs.market)
    live = _live_guardrails(inputs.market)
    failing = _failing_guardrails(base_checks, live)
    return _compute_combinations_core(
        inputs,
        base_metrics=base_metrics,
        failing=failing,
        live=live,
        snapshot=_derive_snapshot(inputs, base_forecast),
        total_opex_y1=base_forecast.years[0].total_opex,
        horizon_years=horizon_years,
        precomputed=precomputed,
        max_iter=max_iter,
    )
