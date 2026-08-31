# src/market/recourse.py
"""Actionable recourse -- "What would have to change?" (Mission 4).

Attaches to a near-miss ``InvestmentThesis`` a structured answer to "how far is this deal from
the line, and what single investor-movable change would close the gap?" for each currently-failing
guardrail, expressed in four levers: rent per unit/month, purchase price, interest rate, and
annual operating costs.

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

import math
from dataclasses import dataclass
from typing import Literal

from src.agents.chief_strategist import (
    REQUIRE_POSITIVE_CF_ALL,
    REQUIRE_POSITIVE_CF_Y1,
    GuardrailChecks,
    guardrail_checks_from_metrics,
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
)
from src.market.hypotheses import DEFAULT_BANDS
from src.market.rejector import reject_unrealistic
from src.schemas.models import (
    FinancialForecast,
    FinancialInputs,
    HypothesisSet,
    IncomeModel,
    MarketAssumptions,
    MarketHypothesis,
    MarketSnapshot,
    RecourseAnalysis,
    RecourseLever,
    UnitIncome,
)

GuardrailName = Literal["dscr", "spread", "irr", "coc", "cf_y1", "cf_all", "cap_floor"]
LeverName = Literal["rent_per_unit_month", "purchase_price", "interest_rate", "annual_opex"]

#: Fixed lexicographic order used everywhere a guardrail set is iterated or tie-broken.
_GUARDRAIL_ORDER: tuple[GuardrailName, ...] = ("dscr", "spread", "irr", "coc", "cf_y1", "cf_all", "cap_floor")

#: Fixed lexicographic order used everywhere a lever set is iterated or tie-broken.
_LEVER_ORDER: tuple[LeverName, ...] = ("rent_per_unit_month", "purchase_price", "interest_rate", "annual_opex")

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
#: many of the (up to) seven LIVE guardrails are failing. This is a SCOPING predicate evaluated
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
    """
    return MarketSnapshot(
        region="recourse-derived",
        vacancy_rate=1.0 - inputs.income.occupancy,
        cap_rate=base_forecast.purchase.cap_rate,
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
    """
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
        perturbed = _perturb(inputs, lever, mid, total_opex_y1=total_opex_y1)
        forecast_mid = _rerun(perturbed, horizon_years=horizon_years, baseline_income=inputs.income, precomputed=precomputed)
        checks_mid = guardrail_checks_from_metrics(forecast_mid, market)
        if _ok(checks_mid, guardrail):
            hi, forecast_hi, checks_hi = mid, forecast_mid, checks_mid
        else:
            lo = mid
    if forecast_hi is None or checks_hi is None:
        perturbed = _perturb(inputs, lever, hi, total_opex_y1=total_opex_y1)
        forecast_hi = _rerun(perturbed, horizon_years=horizon_years, baseline_income=inputs.income, precomputed=precomputed)
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

    # Compose a specific reason from `reject_unrealistic`'s own already-public numeric constants
    # (discovery spec §3.3) -- messaging only; the accept/reject decision above is never re-derived.
    if lever == "interest_rate":
        return True, (
            f"a {abs(delta) * 10_000:.0f} bps rate cut is flagged by the plausibility guardrails "
            "this project uses to judge market-rate hypotheses."
        )
    new_cap = hyp.cap_rate_delta + snapshot.cap_rate
    return True, (
        f"a {_LEVER_NOUN[lever]} this large pushes the implied cap rate to {new_cap:.2%}, outside "
        "the [3.00%, 12.00%] range this project treats as a realistic market cap rate."
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
    perturbed_bound = _perturb(inputs, lever, bound.search_bound, total_opex_y1=total_opex_y1)
    forecast_bound = _rerun(perturbed_bound, horizon_years=horizon_years, baseline_income=inputs.income, precomputed=precomputed)
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
    """
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

    return RecourseAnalysis(
        verdict=thesis.verdict,
        failing_guardrails=failing,
        levers=levers,
        cheapest=cheapest,
        remaining_after_cheapest=remaining_after_cheapest,
        honest_null=honest_null,
    )
