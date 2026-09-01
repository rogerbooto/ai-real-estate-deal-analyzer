# src/core/finance/jacobian.py
"""
The metrics Jacobian seam (Mission 5, IA.1a): value + all partial derivatives in ONE engine pass.

WHAT THIS IS. `forecast_metrics_with_jacobian(fi, directions, ...)` runs the SAME
`engine._forecast_core` that prices every shipped number -- not a slice, not a simplified model
-- with `Dual4` scalars seeded on up to four caller-named directions, and returns a
`MetricsJacobian`: the bit-identical primal `ForecastMetrics` plus
d(metric)/d(direction) for every one of `ForecastMetrics`' 8 float fields. Measured cost: ~4.1x
one plain `forecast_metrics` pass for the whole 8xN Jacobian (D.1 §1) vs 2N+ engine passes for
central finite differences.

SHAPE RULING (D.1 §3). Rows are `ForecastMetrics`' 8 float fields -- NOT guardrail names, and
NOT the charter's "7x4". "Live"/"failing" guardrails are market-layer facts that change per deal
and per config; baking them in here would make the seam's shape config-dependent. Columns are
the caller's own direction names, echoed back. There is NO bare matrix and NO positional
guessing anywhere: rows are addressed by `MetricName` literals (drift-guarded against the
dataclass at import time), columns by direction name, via `.partial(metric, direction)`.

HONEST DEGRADATION. `partials[m] is None` means "no trustworthy derivative exists at this
point" -- IRR undefined (`irr()` returned None: the coalesced 0.0 metric is a jump
discontinuity), an ill-conditioned IRR root (|dNPV/dr| under the conditioning floor), or a
non-finite tangent. Every None row appends a reason to `degraded`. `None` is NEVER `0.0`: a
true zero sensitivity (e.g. cap_rate w.r.t. interest_rate) is a real `0.0`. Callers seeing
`None` fall back to derivative-free search for that row.

THE IRR ROW (D.1 §2 ruling). The Brent root-finder is NEVER differentiated through: bracket
endpoints are theta-constants with zero tangents, so a bisection-terminated run would return
zero-built garbage, non-deterministically by deal. Instead the primal cash flows go through the
UNMODIFIED production `irr()` (inside `_forecast_core`), and the derivative is recovered here by
the implicit function theorem on f(r, theta) = sum_t CF_t(theta) * (1+r)^-t = 0:

    dr*/d(theta) = - (df/d(theta)) / (df/dr),  evaluated at the returned root r_hat
    df/d(theta)  = sum_t  dCF_t/d(theta) * (1 + r_hat)^-t
    df/dr        = sum_t  -t * CF_t * (1 + r_hat)^-(t+1)

The derivative inherits the root tolerance ONCE -- error O(tol) = O(1e-6), measured ~3.2e-7 on
the demo deal -- so tests compare the IRR row against FD in BANDS, never exactly; do not "fix" a
band failure by loosening the root tolerance.

WHAT THIS SEAM DOES NOT ACCEPT: `insights` (income uplifts rebuild the IncomeModel mid-engine --
exactly the case `PrecomputedIncome` already refuses; differentiation through insight modifiers
is out of scope and `_forecast_core` raises loudly if attempted), and per-unit rent seeds (the
rent direction seeds the `income.gsi_annual` AGGREGATE -- D.1 §1a: d(gsi)/d(rent/unit/month) is
the constant 12 * num_units, so no perturbed rent roll ever exists on a derivative pass, O(1) in
roll size).

FUTURE SEAM (designed for, deliberately NOT implemented here): evaluating the Jacobian at a
SHIFTED rent aggregate (t != 0) without materialising a roll. That lands as a separate,
guardian-reviewed parameter (an income-shift validated against the base `IncomeModel`, in
`PrecomputedIncome`'s loud-failure posture) that changes only the PRIMAL handed to
`_CoreOverrides.gsi_annual` (to `gsi + 12*N*t`); the direction/tangent machinery here is
unchanged by it. Nothing in this module bypasses `PrecomputedIncome`'s identity check -- a
supplied precompute is identity-validated below exactly as the engine validates it.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields as _dataclass_fields
from types import MappingProxyType
from typing import Literal, cast, get_args

from src.schemas.models import FinancialInputs, OperatingExpenses

from .dual import Dual4, primal, tangents
from .engine import (
    _OVERRIDE_OPEX_ORDER,
    DEFAULT_HORIZON_YEARS,
    ForecastMetrics,
    PrecomputedIncome,
    _annual_income,
    _CoreOverrides,
    _forecast_core,
)
from .partition import LEVER_IMAGE, assert_disjoint_from_assumptions

#: Exactly `ForecastMetrics`' float fields, in declaration order -- drift-guarded below.
MetricName = Literal[
    "cap_rate",
    "coc",
    "purchase_dscr",
    "year1_dscr",
    "spread_vs_rate",
    "irr_10yr",
    "cash_flow_y1",
    "min_cash_flow",
]

_METRIC_NAMES: tuple[MetricName, ...] = get_args(MetricName)

# Import-time drift guard (house style of `engine._YB_FIELDS`): if `ForecastMetrics` gains,
# loses or renames a float field, this module fails on import instead of silently shipping a
# Jacobian with a missing/phantom row.
_FORECAST_METRICS_FLOAT_FIELDS: tuple[str, ...] = tuple(f.name for f in _dataclass_fields(ForecastMetrics) if f.type in ("float", float))
if _FORECAST_METRICS_FLOAT_FIELDS != tuple(_METRIC_NAMES):
    raise RuntimeError(
        "jacobian.MetricName is out of sync with engine.ForecastMetrics' float fields: "
        f"expected {_FORECAST_METRICS_FLOAT_FIELDS} got {tuple(_METRIC_NAMES)}"
    )

#: The 12 seedable OPEX line items -- exactly `engine._OVERRIDE_OPEX_ORDER`, drift-guarded below.
OpexFieldName = Literal[
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
]

_OPEX_FIELD_NAMES: tuple[OpexFieldName, ...] = get_args(OpexFieldName)

if tuple(_OPEX_FIELD_NAMES) != _OVERRIDE_OPEX_ORDER:
    raise RuntimeError(
        "jacobian.OpexFieldName is out of sync with engine._OVERRIDE_OPEX_ORDER: "
        f"expected {_OVERRIDE_OPEX_ORDER} got {tuple(_OPEX_FIELD_NAMES)}"
    )
_opex_names_plain: set[str] = {str(name) for name in _OPEX_FIELD_NAMES}
if not _opex_names_plain <= set(OperatingExpenses.model_fields):
    raise RuntimeError(
        "jacobian.OpexFieldName names fields that no longer exist on schemas.OperatingExpenses: "
        f"{sorted(_opex_names_plain - set(OperatingExpenses.model_fields))}"
    )

#: Seed targets are EXACTLY the image of `partition.INVESTOR_LEVERS` under
#: `partition.LEVER_SEED_TARGETS` -- THE LEVER/ASSUMPTION PARTITION (GD3,
#: `docs/plans/mission-5-discovery/GD3_lever_assumption_invariant.md`), not a scope-economy
#: choice. Widening `SeedTarget` to reach a `MODEL_ASSUMPTIONS` path (vacancy/occupancy,
#: rent/expense growth, exit cap, cap drift, horizon) is a Founder Proxy escalation citing GD3 --
#: never a self-approved edit, whatever the rationale (Ruling 4). Per-unit rent targets are
#: separately NOT offered even within the lever's own image -- the rent lever seeds the
#: `income.gsi_annual` aggregate (D.1 §1a), and offering per-unit seeds would invite the
#: O(units)-per-probe pattern D.2 measured as 74.5% of a portfolio-scale recourse row.
SeedTarget = (
    Literal[
        "financing.purchase_price",
        "financing.interest_rate",
        "income.gsi_annual",
    ]
    | tuple[Literal["opex"], OpexFieldName]
)

_SCALAR_TARGETS: frozenset[str] = frozenset({"financing.purchase_price", "financing.interest_rate", "income.gsi_annual"})

# Import-time GD3 drift guard: `SeedTarget`'s full universe (scalar targets + every addressable
# `("opex", <line>)` pair, rendered `opex.<line>`) must be EXACTLY `partition.LEVER_IMAGE` -- the
# image of the four investor levers, nothing more. A future edit that widens `SeedTarget` beyond
# that image (e.g. adding an `income.occupancy` seed) fails here on import instead of silently
# shipping a differentiable assumption.
_SEED_TARGET_UNIVERSE: frozenset[str] = _SCALAR_TARGETS | {f"opex.{line}" for line in _OPEX_FIELD_NAMES}
if _SEED_TARGET_UNIVERSE != LEVER_IMAGE:
    raise RuntimeError(
        "jacobian.SeedTarget has drifted from partition.LEVER_IMAGE (GD3): "
        f"missing={sorted(LEVER_IMAGE - _SEED_TARGET_UNIVERSE)} "
        f"extra={sorted(_SEED_TARGET_UNIVERSE - LEVER_IMAGE)}. Extending SeedTarget beyond the "
        "image of INVESTOR_LEVERS is a Founder Proxy escalation citing GD3 -- see "
        "src/core/finance/partition.py and "
        "docs/plans/mission-5-discovery/GD3_lever_assumption_invariant.md."
    )

# Import-time GD3 disjointness guard (Ruling 2.3): the seed-target universe AND
# `_CoreOverrides`' own field set (the ONLY sanctioned way dual numbers enter the engine, per
# `_CoreOverrides`' own docstring) must both be disjoint from `partition.MODEL_ASSUMPTIONS`.
assert_disjoint_from_assumptions(
    {
        "jacobian._SEED_TARGET_UNIVERSE": _SEED_TARGET_UNIVERSE,
        "engine._CoreOverrides fields": frozenset(f.name for f in _dataclass_fields(_CoreOverrides)),
    }
)

#: |df/dr| below this fraction of the sum of its terms' magnitudes is catastrophic cancellation:
#: the implicit-function division would amplify rounding noise into a confident-looking garbage
#: slope, so the row degrades to None instead (D.1 §2's floor-check). 1e-12 loses ~4 of ~16
#: digits to cancellation before tripping -- a derivative that inaccurate is already junk.
_IFT_CONDITIONING_FLOOR = 1e-12

#: One dual pass carries at most this many directions (the fixed tangent width of `Dual4`,
#: chosen and measured in D.1 §1: width is nearly free UP TO the unrolled slot count).
MAX_DIRECTIONS = 4


@dataclass(frozen=True)
class TangentDirection:
    """One named Jacobian column: a direction in input space, as d(target)/d(direction) seeds.

    `name` is the caller's own label, echoed back verbatim in `MetricsJacobian.directions` and
    used to address the column in `.partial(metric, name)`. `seeds` maps engine seed targets to
    the direction's components -- e.g. the recourse rent lever is
    ``(("income.gsi_annual", 12.0 * num_units),)`` and its price lever is
    ``(("financing.purchase_price", -1.0),)``. Lever semantics (which seeds mean which product
    lever) belong to the market layer, not here.
    """

    name: str
    seeds: tuple[tuple[SeedTarget, float], ...]


@dataclass(frozen=True)
class MetricsJacobian:
    """The result of one dual pass: primal metrics + named partials + honest degradation.

    `metrics` is the PRIMAL of the same evaluation -- bit-identical to
    `engine.forecast_metrics(fi, ...)` (pinned across the golden matrix by
    `tests/core/finance/test_jacobian.py`). `partials[m]` is a tuple aligned with `directions`
    (never a bare matrix), or None when no trustworthy derivative exists -- in which case a
    human-readable reason is appended to `degraded`. None is never 0.0 and 0.0 is never None.
    """

    metrics: ForecastMetrics
    directions: tuple[str, ...]
    partials: Mapping[MetricName, tuple[float, ...] | None]
    degraded: tuple[str, ...]

    def partial(self, metric: MetricName, direction: str) -> float | None:
        """d(metric)/d(direction), or None if that metric's row is degraded. Loud on unknowns."""
        row = self.partials[metric]  # KeyError on an unknown metric -- never a silent default
        if row is None:
            return None
        try:
            j = self.directions.index(direction)
        except ValueError:
            raise ValueError(f"unknown direction {direction!r}; this Jacobian's directions are {self.directions}") from None
        return row[j]

    def value(self, metric: MetricName) -> float:
        """The primal value of `metric` -- the same float `forecast_metrics` returns."""
        if metric not in self.partials:
            raise KeyError(f"unknown metric {metric!r}; rows are {tuple(self.partials)}")
        return cast(float, getattr(self.metrics, metric))


def _validated_directions(directions: Sequence[TangentDirection]) -> tuple[TangentDirection, ...]:
    """Loud, complete validation of the caller's directions -- misuse fails here, not mid-pass."""
    dirs = tuple(directions)
    if not 1 <= len(dirs) <= MAX_DIRECTIONS:
        raise ValueError(
            f"got {len(dirs)} directions; forecast_metrics_with_jacobian takes 1..{MAX_DIRECTIONS} "
            f"(the fixed Dual4 tangent width). If a real >{MAX_DIRECTIONS}-direction need appears, "
            "chunk the directions across calls or widen the dual type deliberately -- do not drop columns."
        )
    names = [d.name for d in dirs]
    if len(set(names)) != len(names):
        raise ValueError(f"direction names must be unique, got {names}")
    for d in dirs:
        if not d.seeds:
            raise ValueError(f"direction {d.name!r} has no seeds; an all-zero column would be a silent lie -- say what it moves")
        seen: set[object] = set()
        for target, seed in d.seeds:
            if target in seen:
                raise ValueError(f"direction {d.name!r} seeds target {target!r} twice; combine the seeds into one entry")
            seen.add(target)
            if isinstance(target, tuple):
                if len(target) != 2 or target[0] != "opex" or target[1] not in _OPEX_FIELD_NAMES:
                    raise ValueError(
                        f"direction {d.name!r} has unknown seed target {target!r}; "
                        f"opex targets are ('opex', <line>) with line in {_OPEX_FIELD_NAMES}"
                    )
            elif target not in _SCALAR_TARGETS:
                raise ValueError(f"direction {d.name!r} has unknown seed target {target!r}; scalar targets are {sorted(_SCALAR_TARGETS)}")
            if not isinstance(seed, int | float) or isinstance(seed, bool) or not math.isfinite(seed):
                raise ValueError(f"direction {d.name!r} has non-finite or non-numeric seed {seed!r} for target {target!r}")
    return dirs


def _seed_vectors(
    dirs: tuple[TangentDirection, ...],
) -> tuple[list[float], list[float], list[float], dict[OpexFieldName, list[float]]]:
    """Per-target tangent 4-vectors (direction j in slot j; unused slots stay exactly 0.0)."""
    price = [0.0, 0.0, 0.0, 0.0]
    rate = [0.0, 0.0, 0.0, 0.0]
    gsi = [0.0, 0.0, 0.0, 0.0]
    opex: dict[OpexFieldName, list[float]] = {}
    for j, d in enumerate(dirs):
        for target, seed in d.seeds:
            if target == "financing.purchase_price":
                price[j] = float(seed)
            elif target == "financing.interest_rate":
                rate[j] = float(seed)
            elif target == "income.gsi_annual":
                gsi[j] = float(seed)
            else:  # ("opex", <line>) -- the only remaining valid shape after validation
                line = cast(OpexFieldName, cast(tuple[str, str], target)[1])
                opex.setdefault(line, [0.0, 0.0, 0.0, 0.0])[j] = float(seed)
    return price, rate, gsi, opex


def _irr_partials_ift(
    equity_cash_flows: Sequence[float],
    r_hat: float,
    n_directions: int,
) -> tuple[tuple[float, ...] | None, str | None]:
    """The IRR row via the implicit function theorem at the production root (module docstring).

    `equity_cash_flows` is the exact vector `irr()` was solved over (generic scalars: floats
    and/or Dual4s), `r_hat` the root it returned. Returns (row, None) or (None, reason).
    """
    base = 1.0 + r_hat  # > 0: irr()'s bracket search never returns a rate at or below -100%
    dfdr = 0.0
    scale = 0.0
    dfdth = [0.0] * n_directions
    try:
        for t, cf in enumerate(equity_cash_flows):
            w = base ** (-t)  # discount factor (1+r)^-t
            p = primal(cf)
            term = t * p * (w / base)  # t * CF_t * (1+r)^-(t+1)
            dfdr -= term
            scale += abs(term)
            if isinstance(cf, Dual4):
                dfdth[0] += cf.d0 * w
                if n_directions > 1:
                    dfdth[1] += cf.d1 * w
                if n_directions > 2:
                    dfdth[2] += cf.d2 * w
                if n_directions > 3:
                    dfdth[3] += cf.d3 * w
    except OverflowError:
        return None, "irr_10yr: discount-base overflow in the IFT sums (root near the domain floor)"
    if not math.isfinite(dfdr) or not all(math.isfinite(x) for x in dfdth):
        return None, "irr_10yr: non-finite terms in the IFT sums"
    if scale == 0.0 or abs(dfdr) <= _IFT_CONDITIONING_FLOOR * scale:
        return None, (
            "irr_10yr: ill-conditioned root (|dNPV/dr| = "
            f"{abs(dfdr):.3e} <= {_IFT_CONDITIONING_FLOOR:.0e} * {scale:.3e}); a derivative here would be rounding noise"
        )
    row = tuple(-x / dfdr for x in dfdth)
    if not all(math.isfinite(x) for x in row):
        return None, "irr_10yr: non-finite partial after the IFT division"
    return row, None


def forecast_metrics_with_jacobian(
    fi: FinancialInputs,
    directions: Sequence[TangentDirection],
    *,
    horizon_years: int = DEFAULT_HORIZON_YEARS,
    precomputed_income: PrecomputedIncome | None = None,
) -> MetricsJacobian:
    """One dual `_forecast_core` pass: bit-identical primal metrics + all named partials.

    `precomputed_income` is the same purely-additive performance hint `forecast_metrics` takes,
    identity-validated against `fi.income` exactly as the engine validates it (it is resolved
    HERE -- the engine itself refuses a precompute alongside overrides, so there is exactly one
    place the aggregate can come from). No `insights` parameter exists on purpose: see the
    module docstring.

    NOTE the one deliberate typing boundary in this function: `_CoreOverrides`' fields are
    annotated `float` while a `Dual4` may flow through them at runtime (the D.1 §4 mypy ruling
    -- the engine keeps its float annotations; duals are duck-typed through it). The
    `cast(float, ...)` calls below are that boundary, in one screenful, documented.
    """
    dirs = _validated_directions(directions)
    n = len(dirs)
    names = tuple(d.name for d in dirs)
    price_t, rate_t, gsi_t, opex_t = _seed_vectors(dirs)

    # -- primal income aggregate: same source, same identity check as the engine ---------------
    if precomputed_income is not None:
        if precomputed_income.income is not fi.income:
            raise ValueError(
                "precomputed_income was derived from a different IncomeModel than the one being "
                "differentiated. Rebuild it with precompute_income(fi.income) for this exact "
                "input, or pass precomputed_income=None."
            )
        gsi_p, goi_p = precomputed_income.gsi_annual, precomputed_income.goi_annual
    else:
        gsi_p, goi_p = _annual_income(fi.income)

    # -- seed the dual scalars (only seeded targets become dual; theta-constants stay float) ----
    gsi_scalar: float
    goi_scalar: float
    if any(gsi_t):
        # D.1 §1a: the rent direction is a constant seed on the aggregate. GOI is re-derived
        # from the dual GSI with the engine's own expression (`_annual_income`'s multiply, same
        # operands, same order), so its primal is bit-identical to `goi_p`.
        gsi_dual = Dual4(gsi_p, gsi_t[0], gsi_t[1], gsi_t[2], gsi_t[3])
        goi_dual = gsi_dual * (fi.income.occupancy or 1.0) * (fi.income.bad_debt_factor or 1.0)
        gsi_scalar = cast(float, gsi_dual)
        goi_scalar = cast(float, goi_dual)
    else:
        gsi_scalar, goi_scalar = gsi_p, goi_p

    price_scalar: float | None = None
    if any(price_t):
        price_scalar = cast(float, Dual4(fi.financing.purchase_price, price_t[0], price_t[1], price_t[2], price_t[3]))
    rate_scalar: float | None = None
    if any(rate_t):
        rate_scalar = cast(float, Dual4(fi.financing.interest_rate, rate_t[0], rate_t[1], rate_t[2], rate_t[3]))

    opex_scalars: tuple[float, ...] | None = None
    if opex_t:
        line_values: list[float] = []
        for line in _OPEX_FIELD_NAMES:
            base_value = cast(float, getattr(fi.opex, line))
            seeds = opex_t.get(line)
            if seeds is None:
                line_values.append(base_value)  # the same float object the engine would read
            else:
                line_values.append(cast(float, Dual4(base_value, seeds[0], seeds[1], seeds[2], seeds[3])))
        opex_scalars = tuple(line_values)

    overrides = _CoreOverrides(
        gsi_annual=gsi_scalar,
        goi_annual=goi_scalar,
        purchase_price=price_scalar,
        interest_rate=rate_scalar,
        opex=cast("tuple[float, float, float, float, float, float, float, float, float, float, float, float] | None", opex_scalars),
    )

    core = _forecast_core(
        fi,
        horizon_years=horizon_years,
        insights=None,
        precomputed_income=None,  # resolved above; the engine refuses it alongside overrides
        want_rows=False,
        _overrides=overrides,
    )

    # -- primal metrics: the same reductions `forecast_metrics` performs, over the same scalars.
    # Comparisons on Dual4 read the primal, so min/all pick the identical elements/branches. ---
    cash_flows = core.year_cash_flows
    cf_y1 = cash_flows[0]
    min_cf = min(cash_flows)
    metrics = ForecastMetrics(
        cap_rate=primal(core.cap_rate),
        coc=primal(core.coc),
        purchase_dscr=primal(core.dscr_y1),
        year1_dscr=primal(core.dscr_y1),
        spread_vs_rate=primal(core.spread_vs_rate),
        irr_10yr=core.irr_10yr,  # already primal: irr() only ever sees primal floats
        cash_flow_y1=primal(cf_y1),
        min_cash_flow=primal(min_cf),
        all_cash_flows_nonneg=all(cf >= 0.0 for cf in cash_flows),
        warnings=tuple(core.warnings),
    )

    # -- pack rows: tuple of tangents, or None + reason on any non-finite entry ----------------
    degraded: list[str] = []
    partials: dict[MetricName, tuple[float, ...] | None] = {}

    def _pack(metric: MetricName, scalar: float) -> None:
        row = tangents(scalar, n)
        if all(math.isfinite(x) for x in row):
            partials[metric] = row
        else:
            partials[metric] = None
            degraded.append(f"{metric}: non-finite tangent {row}; no trustworthy derivative at this point")

    _pack("cap_rate", core.cap_rate)
    _pack("coc", core.coc)
    _pack("purchase_dscr", core.dscr_y1)
    _pack("year1_dscr", core.dscr_y1)
    _pack("spread_vs_rate", core.spread_vs_rate)

    if core.irr_raw is None:
        # The engine coalesced the metric to 0.0 (+ its warning); that constant has a jump
        # discontinuity here, so there is no derivative to report. 0.0 partials would silently
        # claim "no lever can ever move IRR" -- wrong and invisible.
        partials["irr_10yr"] = None
        degraded.append("irr_10yr: IRR undefined (irr() returned None; metric is the coalesced 0.0 constant)")
    else:
        irr_row, reason = _irr_partials_ift(core.equity_cash_flows, core.irr_raw, n)
        partials["irr_10yr"] = irr_row
        if reason is not None:
            degraded.append(reason)

    _pack("cash_flow_y1", cf_y1)
    _pack("min_cash_flow", min_cf)

    return MetricsJacobian(
        metrics=metrics,
        directions=names,
        partials=MappingProxyType(partials),
        degraded=tuple(degraded),
    )
