# src/market/breakeven.py
"""Assumption breakeven / margin of safety -- "how wrong can this guess be?" (Mission 5).

The mirror image of ``recourse.py`` under THE LEVER/ASSUMPTION PARTITION (GD3,
``src/core/finance/partition.py``). Recourse solves to a guardrail boundary along an INVESTOR
LEVER axis and reads the answer as an action: "what would have to change." This module performs
the same *kind* of solve along a MODEL ASSUMPTION axis -- occupancy, rent growth, expense
growth -- and reads it the ONLY way GD3 permits: as breakeven / margin of safety. "This deal
clears DSCR until vacancy hits 9.4%; you assumed 5%" is a fact about fragility. "Raise your
vacancy assumption to 8% and the deal passes" is an instruction to fudge an input until the
model manufactures a PASS, and it is inexpressible here by construction: ``AssumptionBreakeven``
carries no target/delta/ask field, and ``partition.assert_breakeven_shape`` enforces that at
import time, below.

SCOPE (GD3 Ruling 3): exactly three axes -- ``income.occupancy``, ``income.rent_growth``,
``opex.expense_growth``. Exit cap, cap-rate drift and hold horizon are BARRED
(``partition.BARRED_ASSUMPTION_AXES``): their signal lives inside the engine's terminal-equity
PROXY (``EQUITY_LTV * value - balance`` -- no sale costs, not even a simplified sale), and a
precise breakeven of a deliberately simplified placeholder would be a confident number about
nothing. Unbarring requires the full founder-approved prerequisite chain in ``partition.py``.
The import-time guards below pin all of this: every axis here is a ``MODEL_ASSUMPTIONS`` path,
none is barred, and none collides with the lever image.

ONLY CURRENTLY-PASSING GUARDRAILS GET A ROW, on purpose. A failing guardrail has no margin of
safety -- it is already failing at the assumed values (recorded as a fact in
``BreakevenAnalysis.failing_guardrails``) -- and solving it to the boundary in the FAVORABLE
direction ("it would pass if occupancy were 0.99") is the forbidden recourse reading in
disguise. Recourse (``compute_recourse`` / ``compute_combinations``) owns failing guardrails.

METHOD -- reuse what is measured, do not invent:

* **Direction is a data-flow fact, not a fit.** Each axis has one adverse direction, fixed by
  the engine's own arithmetic (``engine._forecast_core``): GOI = GSI x occupancy x bad_debt
  (income is nondecreasing in occupancy), year-y income scales by ``(1 + rent_growth)**(y-1)``
  (nondecreasing in rent_growth), year-y OPEX scales by ``(1 + expense_growth)**(y-1)`` (costs
  nondecreasing in expense_growth) -- and every guardrail metric is nondecreasing in income and
  nonincreasing in costs. Adverse is therefore: occupancy DOWN, rent_growth DOWN,
  expense_growth UP. (Mission 5 discovery additionally measured every margin monotone along
  every axis -- 2,196 segments, zero multi-crossings -- so the first crossing is the only one.)
* **Perturb-and-rerun, never differentiate an assumption.** ``jacobian.SeedTarget`` is closed
  to the image of the four investor levers by an import-time GD3 drift guard; widening it (e.g.
  an ``income.occupancy`` seed) is a Founder Proxy escalation citing GD3, never a self-approved
  edit (Ruling 4). This module does not need it: bisection is derivative-free, the adverse
  direction is fixed a priori (above), and Newton was already measured worse than bisection's
  fixed probe count. Every probe here is a real (light-path) engine re-run via
  ``forecast_metrics`` -- the honest path that already works.
* **Bisection on the assumption's own value axis** between the assumed value (passing) and the
  adverse domain edge (observed failing by a real probe), to ``_BREAKEVEN_TOL``.
* **Confirm-by-rerun (THE ONE DISCIPLINE, verbatim from recourse).** The value that ships is
  re-run through the FULL ``run_financial_model`` and the guardrail observed FAILING there;
  ``metric_at_breakeven`` is read off that confirming run and no other. Nothing unconfirmed
  ever reaches the schema.
* **Three outcomes, never two** (the same honesty contract as ``compute_combinations``):
  ``breakeven_found`` / ``never_breaks_in_range`` (a real engine run at the stated adverse edge
  still passes -- a PROVEN, strong result within that range) / ``undetermined`` (``max_iter``,
  the per-row engine-probe budget, ran out -- "we stopped looking", which must never render as
  proven safety).
* **Deterministic**: fixed enumeration order, fixed probe sequence, fixed exhaustion point --
  same inputs => byte-identical ``BreakevenAnalysis``.

DOMAIN EDGES (the honest-bounding rule): occupancy's natural domain is (0, 1], but the engine
treats occupancy == 0.0 as "unset" (``income.occupancy or 1.0`` in ``engine._annual_income``
-- exactly 0.0 silently means FULL occupancy), so the adverse probe edge is
``_OCCUPANCY_ADVERSE_EDGE`` (1e-6, vacancy ~100%). rent_growth's mathematical floor is -1.0
(the annual growth factor ``1 + g`` reaches zero; below it, income alternates sign --
meaningless). expense_growth has no natural ceiling; ``_EXPENSE_GROWTH_ADVERSE_EDGE`` (+1.0,
costs doubling every year) is a stated SEARCH ceiling, and every "never breaks" claim is scoped
by the row's own ``searched_to`` field -- never an unqualified "never".

THE MODELABLE EDGE (a fourth honest bound, and the reason ``searched_to`` is per-row rather than
a constant the report could look up). Those three nominal edges are the *domain*'s edges; they
are not always reachable. On a deal that REFINANCES, deep enough adversity drives year-`n` NOI
negative, so ``engine._forecast_core``'s NOI-based refi valuation goes negative, so
``refi_ltv * value`` is a negative loan and ``amortization.schedule_columns`` raises
``ValueError("principal must be >= 0")`` -- the engine correctly declining to score a deal it
cannot model, not a bug to swallow. Probing there would crash the report, and pretending the
probe passed would invent safety. So ``_modelable_edge`` bisects in from the nominal edge to the
adverse-most value the engine will actually model, and THAT value ships as the row's
``searched_to``. Every "never breaks" claim therefore remains scoped to a range that was really
searched with real engine runs. A probe that still refuses inside that bracket (the region is
monotone in practice, so this should not occur) is treated as ADVERSE, which can only move the
crossing toward the assumed value -- it understates the margin, never overstates it. And a
confirming re-run the engine refuses degrades to ``undetermined``, never to a number: the
confirm-by-rerun discipline has no exceptions. A refusal is recognised by the engine's ONE
documented refusal message (``_ENGINE_REFUSAL_TEXT``) and nothing broader: every other error --
above all the engine's deliberately loud precompute/shift identity checks -- propagates, so a
future bug can never masquerade as "the engine declines to model here" and silently narrow
``searched_to`` (Gate V re-review, N2).

THE IRR CLIFF (Gate V re-review, N-B1 -- a fifth honest bound, on the metric rather than the
axis). Far enough along an adverse axis a deal's projected cash flows can stop admitting ANY
internal rate of return: ``irr()`` returns None and the engine coalesces the metric to 0.0 for
guardrail purposes, attaching its "IRR undefined" warning (``engine._forecast_core``). The
bisection still converges on a real, confirmed boundary -- the IRR guardrail genuinely stops
clearing there, conservatively, on the engine's own ruling -- so the row stays
``breakeven_found`` and the margin stays: it is the measured distance to the point past which
the model can no longer demonstrate a passing IRR. What must NOT ship is the sentinel itself.
``metric_at_breakeven`` degrades to None when the confirming run carries that warning --
``jacobian.py``'s exact posture for the same value (its IRR partials row degrades to None
rather than claim 0.0 measurements nobody made) -- and the report renders the row as a cliff
("the confirming re-run there could not compute an IRR at all"), never as a return that decayed
gently to the bar.

Public API
----------
``compute_breakevens(inputs, *, horizon_years=DEFAULT_HORIZON_YEARS,
max_iter=DEFAULT_BREAKEVEN_MAX_ITER) -> BreakevenAnalysis``
    Self-contained (own fresh baseline, mirroring ``compute_combinations``'s precedent). Always
    returns a complete ``BreakevenAnalysis``; ``attempted`` is False (and ``rows`` empty) only
    when no live guardrail currently passes. The *whether to render* decision belongs to the
    report layer, not to this module.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Literal, get_args

from src.agents.chief_strategist import guardrail_checks_from_metrics
from src.core.finance.engine import (
    DEFAULT_HORIZON_YEARS,
    ForecastMetrics,
    PrecomputedIncome,
    forecast_metrics,
    metrics_of,
    precompute_income,
    run_financial_model,
)
from src.core.finance.partition import BARRED_ASSUMPTION_AXES, LEVER_IMAGE, MODEL_ASSUMPTIONS, assert_breakeven_shape

# Deliberate same-package reuse of recourse's guardrail vocabulary (reuse-first): these are the
# exact live-set / bar / metric readings `synthesize_thesis` tests, already derived once there.
from src.market.recourse import (
    _GUARDRAIL_ORDER,
    GuardrailName,
    _bar,
    _failing_guardrails,
    _live_guardrails,
    _metric,
    _ok,
)
from src.schemas.models import AssumptionBreakeven, BreakevenAnalysis, FinancialInputs

AssumptionName = Literal["occupancy", "rent_growth", "expense_growth"]

#: Fixed enumeration order for rows (assumption-major; the schema `Literal`'s own order).
_ASSUMPTION_ORDER: tuple[AssumptionName, ...] = get_args(AssumptionName)

#: Each in-scope axis's dotted field path in the partition's own vocabulary.
_ASSUMPTION_PATHS: Mapping[AssumptionName, str] = MappingProxyType(
    {
        "occupancy": "income.occupancy",
        "rent_growth": "income.rent_growth",
        "expense_growth": "opex.expense_growth",
    }
)

# ------------------------------------------------------------------------------------------
# Import-time GD3 guards (house pattern of `recourse.py`'s LeverName guard): every axis this
# module erodes must be a classified MODEL ASSUMPTION, none may be barred (Ruling 3), and none
# may collide with the lever image (a lever axis belongs to recourse, not here).
# ------------------------------------------------------------------------------------------
_AXIS_PATHS: frozenset[str] = frozenset(_ASSUMPTION_PATHS.values())
if not _AXIS_PATHS <= MODEL_ASSUMPTIONS:
    raise RuntimeError(
        "breakeven axes must all be partition.MODEL_ASSUMPTIONS paths (GD3): "
        f"unclassified={sorted(_AXIS_PATHS - MODEL_ASSUMPTIONS)}. See src/core/finance/partition.py."
    )
if _AXIS_PATHS & BARRED_ASSUMPTION_AXES:
    raise RuntimeError(
        "breakeven axes include a BARRED axis (GD3 Ruling 3 -- terminal-equity-proxy-dominated): "
        f"{sorted(_AXIS_PATHS & BARRED_ASSUMPTION_AXES)}. Lifting the bar requires the full "
        "founder-approved prerequisite chain in src/core/finance/partition.py."
    )
if _AXIS_PATHS & LEVER_IMAGE:
    raise RuntimeError(
        "breakeven axes collide with partition.LEVER_IMAGE (GD3): "
        f"{sorted(_AXIS_PATHS & LEVER_IMAGE)}. A lever axis is recourse territory, never breakeven."
    )

# The shape rule (GD3 Ruling 2.4) is a real, enforced check at import time -- the schema types
# this module ships can never grow a field able to express a recourse ask without failing here.
assert_breakeven_shape(AssumptionBreakeven)
assert_breakeven_shape(BreakevenAnalysis)

#: Adverse direction per axis -- engine data-flow facts (module docstring), not per-deal fits.
_ADVERSE_DIRECTION: Mapping[AssumptionName, Literal["down", "up"]] = MappingProxyType(
    {
        "occupancy": "down",
        "rent_growth": "down",
        "expense_growth": "up",
    }
)

#: Occupancy's adverse probe edge. NOT 0.0: `engine._annual_income` reads
#: `income.occupancy or 1.0`, so exactly 0.0 silently means FULL occupancy -- probing there
#: would report the healthiest possible deal at the sickest possible assumption. 1e-6 is
#: vacancy ~100% for every real purpose and stays on the truthy side of the quirk.
_OCCUPANCY_ADVERSE_EDGE: float = 1e-6

#: rent_growth's mathematical floor: the annual growth factor `1 + g` reaches zero (income is
#: zero from year 2 onward); below -1.0 the factor goes negative and income alternates sign.
_RENT_GROWTH_ADVERSE_EDGE: float = -1.0

#: expense_growth's SEARCH ceiling (no natural ceiling exists): +100%/yr, costs doubling every
#: year. A "never breaks" at this edge is honest only because the row's `searched_to` states it.
_EXPENSE_GROWTH_ADVERSE_EDGE: float = 1.0

#: Bisection tolerance, in the assumption's own units. All three axes are fractions; 5e-4
#: (5 bps) is finer than the 0.1-percentage-point display step the report layer rounds to, so
#: the rendered number is never coarser than what the bisection resolved (recourse's own rule).
_BREAKEVEN_TOL: float = 5e-4

#: Per-row engine-probe budget (edge probe + bisection probes + the full confirm). The
#: architecture's worst case is 1 + ceil(log2(width / _BREAKEVEN_TOL)) + 1 ~= 14 probes at the
#: widest possible bracket (rent_growth from ~+1 down to -1), or ~22 when the nominal edge is
#: refused and `_modelable_edge` spends its `_MODELABLE_EDGE_STEPS` clipping in; 24 is that
#: ceiling with headroom, and hitting it is reported as UNDETERMINED -- deterministically: same
#: inputs, same probe sequence, same exhaustion point (`compute_combinations`'s own contract).
DEFAULT_BREAKEVEN_MAX_ITER: int = 24

#: Same "does this metric move at all" threshold recourse's reachability probe uses.
_METRIC_MOVES_EPS: float = 1e-9

#: The engine's ONE documented refusal-to-model message (module docstring, THE MODELABLE EDGE):
#: `amortization.schedule_columns` raises exactly this when a negative NOI-based refi valuation
#: implies a negative loan. This -- and ONLY this -- ValueError means "the engine declines to
#: model the deal here". Every other error, in particular the engine's deliberately loud
#: precompute/shift identity checks (`engine._forecast_core`), must propagate: swallowing them
#: would let a stale precompute silently narrow `searched_to` with no trace (Gate V re-review,
#: N2). Pinned against amortization's actual message by `tests/unit/test_breakeven.py`.
_ENGINE_REFUSAL_TEXT: str = "principal must be >= 0"

#: The stable prefix of the engine's coalesced-IRR warning (`engine._forecast_core`: "IRR
#: undefined: no single discount rate solves NPV=0 ... treated as 0.00% for guardrail
#: purposes."). Its presence on a run's `ForecastMetrics.warnings` is the ONLY way to tell the
#: sentinel 0.0 from a genuinely computed 0% return; the full text is pinned by
#: `tests/core/finance/test_irr_undefined_warning.py`, and the prefix's drift trip-wire lives in
#: `tests/unit/test_breakeven.py`.
_IRR_UNDEFINED_WARNING_PREFIX: str = "IRR undefined"


def _is_engine_refusal(exc: ValueError) -> bool:
    """True iff `exc` is the engine's documented refusal to model (negative refi principal)."""
    return _ENGINE_REFUSAL_TEXT in str(exc)


def _irr_is_coalesced(metrics: ForecastMetrics) -> bool:
    """True iff this run's `irr_10yr` is the engine's coalesced-0.0 sentinel, not a computed
    return -- read off the same run's own warnings, the channel the engine surfaces it on."""
    return any(w.startswith(_IRR_UNDEFINED_WARNING_PREFIX) for w in metrics.warnings)


def _assumed_value(inputs: FinancialInputs, assumption: AssumptionName) -> float:
    if assumption == "occupancy":
        return inputs.income.occupancy
    if assumption == "rent_growth":
        return inputs.income.rent_growth
    return inputs.opex.expense_growth


def _adverse_edge(assumption: AssumptionName) -> float:
    if assumption == "occupancy":
        return _OCCUPANCY_ADVERSE_EDGE
    if assumption == "rent_growth":
        return _RENT_GROWTH_ADVERSE_EDGE
    return _EXPENSE_GROWTH_ADVERSE_EDGE


def _perturb_assumption(inputs: FinancialInputs, assumption: AssumptionName, value: float) -> FinancialInputs:
    """A perturbed copy of `inputs` with the assumption set to the absolute `value`.

    SURGICAL copy, exactly recourse.`_perturb`'s discipline: only the one submodel this axis
    lives on is rebuilt via `model_copy(update=...)`; everything else is shared by reference,
    which is safe because nothing downstream mutates a submodel in place.
    """
    if assumption == "occupancy":
        return inputs.model_copy(update={"income": inputs.income.model_copy(update={"occupancy": value})})
    if assumption == "rent_growth":
        return inputs.model_copy(update={"income": inputs.income.model_copy(update={"rent_growth": value})})
    return inputs.model_copy(update={"opex": inputs.opex.model_copy(update={"expense_growth": value})})


def _probe(
    inputs: FinancialInputs,
    assumption: AssumptionName,
    value: float,
    *,
    horizon_years: int,
    precomputed: PrecomputedIncome,
) -> ForecastMetrics | None:
    """One light-path search probe at the absolute assumption `value`, or None when the engine
    DECLINES to model the deal there.

    The precompute is reused when -- and ONLY when -- the perturbed copy provably shares the
    baseline income object (object identity, recourse.`_rerun`'s own test): expense_growth
    leaves `inputs.income` untouched by reference; occupancy and rent_growth rebuild it, so
    their aggregates are genuinely recomputed (occupancy genuinely changes GOI; the engine
    independently enforces the same identity check, belt and braces).

    None is a REFUSAL, not a failure: far enough into the adverse range a refinancing deal's
    year-`n` NOI goes negative, the NOI-based refi valuation with it, and the engine raises
    rather than amortize a negative loan (module docstring, THE MODELABLE EDGE). That is the
    engine being right. Every caller here treats None as "this point is outside what can be
    modeled" and narrows what it claims accordingly -- none of them treats it as a pass, and
    none of them lets it reach the schema as a number.
    """
    perturbed = _perturb_assumption(inputs, assumption, value)
    reusable = precomputed if perturbed.income is inputs.income else None
    try:
        return forecast_metrics(perturbed, horizon_years=horizon_years, precomputed_income=reusable)
    except ValueError as exc:
        # ONLY the documented refusal (negative refi principal) means "unmodelable here". The
        # engine's loud identity errors -- and anything else -- stay loud: a broad catch here is
        # exactly what would let a stale precompute silently clip `searched_to` (N2).
        if not _is_engine_refusal(exc):
            raise
        return None


#: Bisection steps `_modelable_edge` may spend narrowing a refused nominal edge in to a modelable
#: one. 8 halvings land within 1/256th of the original bracket -- far finer than this needs to be
#: (it only has to find *a* workable adverse anchor, not a precise boundary), and small enough
#: that the row's own `max_iter` budget still leaves room for the bisection and the confirm.
_MODELABLE_EDGE_STEPS: int = 8


def _modelable_edge(
    inputs: FinancialInputs,
    assumption: AssumptionName,
    *,
    assumed: float,
    edge: float,
    horizon_years: int,
    precomputed: PrecomputedIncome,
) -> tuple[float, ForecastMetrics | None, int]:
    """The adverse-most value the engine will actually model, its metrics, and probes spent.

    Returns the nominal `edge` untouched (one probe) in the ordinary case where the engine models
    it. Otherwise it bisects [assumed, edge] on MODELABILITY -- not on the guardrail -- and
    returns the adverse-most modelable point found, which becomes the row's `searched_to` so that
    every claim the row makes is scoped to a range real engine runs actually covered.

    The metrics come back None only if no modelable point is found at all, which cannot happen
    for a well-formed deal (`assumed` itself was modeled to produce the baseline) but is reported
    honestly as `undetermined` by the caller rather than assumed away.
    """
    metrics = _probe(inputs, assumption, edge, horizon_years=horizon_years, precomputed=precomputed)
    probes = 1
    if metrics is not None:
        return edge, metrics, probes

    # `near` is modelable by construction (it is the assumed value, whose baseline run succeeded);
    # `far` is refused. Halve toward `near` until a modelable anchor is found, then keep pushing
    # the anchor outward with the remaining steps.
    near, far = assumed, edge
    best: tuple[float, ForecastMetrics] | None = None
    for _ in range(_MODELABLE_EDGE_STEPS):
        mid = (near + far) / 2.0
        mid_metrics = _probe(inputs, assumption, mid, horizon_years=horizon_years, precomputed=precomputed)
        probes += 1
        if mid_metrics is None:
            far = mid
        else:
            best = (mid, mid_metrics)
            near = mid
    if best is None:
        return assumed, None, probes
    return best[0], best[1], probes


def _row(
    *,
    assumption: AssumptionName,
    guardrail: GuardrailName,
    assumed_value: float,
    searched_to: float,
    bar: float,
    outcome: Literal["breakeven_found", "never_breaks_in_range", "undetermined"],
    metric_moves: bool,
    probes_used: int,
    breakeven_value: float | None = None,
    margin: float | None = None,
    metric_at_breakeven: float | None = None,
) -> AssumptionBreakeven:
    return AssumptionBreakeven(
        guardrail=guardrail,
        assumption=assumption,
        assumed_value=assumed_value,
        adverse_direction=_ADVERSE_DIRECTION[assumption],
        searched_to=searched_to,
        outcome=outcome,
        breakeven_value=breakeven_value,
        margin=margin,
        metric_at_breakeven=metric_at_breakeven,
        bar=bar,
        metric_moves=metric_moves,
        resolution=_BREAKEVEN_TOL,
        probes_used=probes_used,
    )


def _breakeven_one(
    inputs: FinancialInputs,
    assumption: AssumptionName,
    guardrail: GuardrailName,
    *,
    base_metrics: ForecastMetrics,
    horizon_years: int,
    precomputed: PrecomputedIncome,
    max_iter: int,
) -> AssumptionBreakeven:
    """One (assumption, currently-passing guardrail) row. Precondition: `guardrail` passes at
    the baseline (`compute_breakevens` only ever calls this for passing guardrails)."""
    market = inputs.market
    assumed = _assumed_value(inputs, assumption)
    edge = _adverse_edge(assumption)
    bar = _bar(guardrail, market)
    direction = _ADVERSE_DIRECTION[assumption]

    # Degenerate bracket: the assumed value already sits at (or beyond) the adverse edge --
    # there is no adverse room left to search, so there is trivially no crossing in range.
    if (direction == "down" and assumed <= edge) or (direction == "up" and assumed >= edge):
        return _row(
            assumption=assumption,
            guardrail=guardrail,
            assumed_value=assumed,
            searched_to=assumed,
            bar=bar,
            outcome="never_breaks_in_range",
            metric_moves=False,
            probes_used=0,
        )

    # --- Edge probe: one real run at the adverse domain edge, clipped in to the adverse-most
    # value the ENGINE WILL MODEL if it refuses the nominal one (module docstring, THE MODELABLE
    # EDGE). `edge` is rebound to whatever was actually reached, and it is that value -- never the
    # nominal one -- that ships as `searched_to` below, so no claim outruns the range searched.
    edge, edge_metrics, probes = _modelable_edge(
        inputs,
        assumption,
        assumed=assumed,
        edge=edge,
        horizon_years=horizon_years,
        precomputed=precomputed,
    )
    if edge_metrics is None:
        # No modelable adverse point was found at all. Nothing was measured, so nothing is
        # claimed: "we could not determine this", never "nothing breaks it".
        return _row(
            assumption=assumption,
            guardrail=guardrail,
            assumed_value=assumed,
            searched_to=assumed,
            bar=bar,
            outcome="undetermined",
            metric_moves=True,
            probes_used=probes,
        )
    if abs(_metric(edge_metrics, guardrail) - _metric(base_metrics, guardrail)) < _METRIC_MOVES_EPS:
        # Structurally independent for this deal (e.g. Year-1 DSCR never reads rent_growth):
        # the metric does not move at all across the ENTIRE adverse range. Proven safe in range.
        return _row(
            assumption=assumption,
            guardrail=guardrail,
            assumed_value=assumed,
            searched_to=edge,
            bar=bar,
            outcome="never_breaks_in_range",
            metric_moves=False,
            probes_used=probes,
        )
    if _ok(guardrail_checks_from_metrics(edge_metrics, market), guardrail):
        # Moves, but still clears the bar at the stated adverse edge: never breaks WITHIN the
        # searched range (a strong, proven result -- the range is on the row, in `searched_to`).
        return _row(
            assumption=assumption,
            guardrail=guardrail,
            assumed_value=assumed,
            searched_to=edge,
            bar=bar,
            outcome="never_breaks_in_range",
            metric_moves=True,
            probes_used=probes,
        )

    # --- Bisect on the value axis: `passing_value` clears, `failing_value` breaks. ---------
    # Monotone along the axis (measured; module docstring), so first crossing = only crossing.
    passing_value, failing_value = assumed, edge
    while abs(failing_value - passing_value) > _BREAKEVEN_TOL:
        if probes >= max_iter:
            return _row(
                assumption=assumption,
                guardrail=guardrail,
                assumed_value=assumed,
                searched_to=edge,
                bar=bar,
                outcome="undetermined",
                metric_moves=True,
                probes_used=probes,
            )
        mid = (passing_value + failing_value) / 2.0
        mid_metrics = _probe(inputs, assumption, mid, horizon_years=horizon_years, precomputed=precomputed)
        probes += 1
        # A refusal inside the bracket (both ends are modelable, and the region is monotone in
        # practice, so this should not occur) counts as ADVERSE. That can only pull the crossing
        # toward the assumed value, i.e. shrink the reported margin -- it understates the room,
        # never overstates it -- and the confirming re-run below still has to observe a real
        # failure at whatever value that lands on, or the row degrades to `undetermined`.
        if mid_metrics is not None and _ok(guardrail_checks_from_metrics(mid_metrics, market), guardrail):
            passing_value = mid
        else:
            failing_value = mid

    # --- THE CONFIRMING RE-RUN IS THE FULL ENGINE, deliberately (recourse's own rule). ------
    # Everything above was search; the number that ships comes from a real
    # `run_financial_model` forecast at exactly `failing_value`, observed FAILING there.
    if probes >= max_iter:
        return _row(
            assumption=assumption,
            guardrail=guardrail,
            assumed_value=assumed,
            searched_to=edge,
            bar=bar,
            outcome="undetermined",
            metric_moves=True,
            probes_used=probes,
        )
    perturbed = _perturb_assumption(inputs, assumption, failing_value)
    reusable = precomputed if perturbed.income is inputs.income else None
    try:
        confirm: ForecastMetrics | None = metrics_of(
            run_financial_model(perturbed, horizon_years=horizon_years, precomputed_income=reusable)
        )
    except ValueError as exc:
        # Same narrowing as `_probe` (N2): only the engine's documented refusal is handled.
        if not _is_engine_refusal(exc):
            raise
        # The engine declines to model the deal at the value the bisection landed on. There is
        # therefore no confirmed crossing, and the confirm-by-rerun discipline has no exceptions:
        # this is reported as not determined, never as a number and never as safety.
        confirm = None
    probes += 1
    if confirm is None or _ok(guardrail_checks_from_metrics(confirm, market), guardrail):
        # Defensive -- the light/full paths are pinned bit-identical, so this should never
        # trigger; but a claim is NEVER shipped without a re-run confirming it, so an
        # unconfirmed crossing degrades to the honest "we could not confirm", never to a number.
        return _row(
            assumption=assumption,
            guardrail=guardrail,
            assumed_value=assumed,
            searched_to=edge,
            bar=bar,
            outcome="undetermined",
            metric_moves=True,
            probes_used=probes,
        )
    # THE IRR CLIFF (module docstring; Gate V re-review, N-B1). When the confirming run's IRR is
    # the engine's coalesced-0.0 sentinel (its "IRR undefined" warning says so on this very run),
    # the crossing is real -- the guardrail was genuinely observed failing, conservatively, on
    # the engine's own ruling -- but there is no measured metric to ship: 0.0 is a substitution,
    # not a measurement, and shipping it here is what let the report claim "measured 0.00%,
    # below the bar" about a return that never decayed at all. `metric_at_breakeven` degrades to
    # None (jacobian.py's posture for the same value); the margin stays, as the measured distance
    # to where the return stops being computable, and the report words it as exactly that.
    confirmed_metric: float | None = _metric(confirm, guardrail)
    if guardrail == "irr" and _irr_is_coalesced(confirm):
        confirmed_metric = None
    return _row(
        assumption=assumption,
        guardrail=guardrail,
        assumed_value=assumed,
        searched_to=edge,
        bar=bar,
        outcome="breakeven_found",
        metric_moves=True,
        probes_used=probes,
        breakeven_value=failing_value,
        margin=abs(failing_value - assumed),
        metric_at_breakeven=confirmed_metric,
    )


def compute_breakevens(
    inputs: FinancialInputs,
    *,
    horizon_years: int = DEFAULT_HORIZON_YEARS,
    max_iter: int = DEFAULT_BREAKEVEN_MAX_ITER,
) -> BreakevenAnalysis:
    """Compute the assumption breakeven / margin-of-safety analysis for `inputs`,
    self-contained (own fresh baseline, mirroring `compute_combinations`'s precedent).

    Always returns a complete `BreakevenAnalysis`. `attempted` is False (and `rows` empty) only
    when no live guardrail currently passes -- there is no margin of safety to measure. Every
    row's outcome is exactly one of three: `breakeven_found` (confirmed by a full
    `run_financial_model` re-run at the shipped value), `never_breaks_in_range` (a real engine
    run at the row's stated `searched_to` edge still passes -- proven within that range), or
    `undetermined` (`max_iter` exhausted: we stopped looking). Same inputs => byte-identical
    result, including the exhaustion point.
    """
    if max_iter <= 0:
        raise ValueError(f"max_iter must be a positive per-row probe budget, got {max_iter}")

    precomputed = precompute_income(inputs.income)
    base_forecast = run_financial_model(inputs, horizon_years=horizon_years, precomputed_income=precomputed)
    base_metrics = metrics_of(base_forecast)
    base_checks = guardrail_checks_from_metrics(base_metrics, inputs.market)
    live = _live_guardrails(inputs.market)
    failing = _failing_guardrails(base_checks, live)
    passing = tuple(g for g in _GUARDRAIL_ORDER if g in live and g not in failing)

    rows = tuple(
        _breakeven_one(
            inputs,
            assumption,
            guardrail,
            base_metrics=base_metrics,
            horizon_years=horizon_years,
            precomputed=precomputed,
            max_iter=max_iter,
        )
        for assumption in _ASSUMPTION_ORDER
        for guardrail in passing
    )

    return BreakevenAnalysis(
        attempted=bool(passing),
        passing_guardrails=passing,
        failing_guardrails=failing,
        rows=rows,
        max_iter=max_iter,
    )
