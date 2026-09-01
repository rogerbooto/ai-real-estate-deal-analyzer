# src/core/finance/partition.py
"""
THE LEVER/ASSUMPTION PARTITION (GD3) -- single source of truth (Mission 5, principles-guardian
ruling `docs/plans/mission-5-discovery/GD3_lever_assumption_invariant.md`, VERDICT:
ADOPTED-WITH-CONDITIONS, VETO authority).

THE INVARIANT, EXACT WORDING (Ruling 1, quoted verbatim -- do not paraphrase this block; if the
wording changes, it changes here first and the ruling document is amended to match, never the
reverse):

    THE LEVER/ASSUMPTION PARTITION (GD3). Every scalar input the pipeline can perturb, search,
    or differentiate is classified exactly once as an INVESTOR LEVER (a quantity the investor
    can act on in the world: rent per unit/month, purchase price, interest rate, annual opex) or
    a MODEL ASSUMPTION (a quantity the investor guesses: vacancy/occupancy/bad-debt, rent
    growth, expense growth, exit cap and cap drift, hold horizon). A solve toward a guardrail
    boundary along a LEVER axis may be presented as recourse -- "what would have to change."
    The same solve along an ASSUMPTION axis may only ever be presented as breakeven / margin of
    safety -- "how wrong can this guess be before the deal fails" -- and must ship in a schema
    type of its own in which the recourse reading is inexpressible (no target_value/delta/ask
    field; fields named for the breakeven reading: assumed value, breakeven value, margin,
    direction of failure). No assumption may ever appear in LeverName, RecourseLever,
    RecourseAnalysis, the recourse search space (single-lever or combination), or any surface
    rendered under a "what would have to change" framing. Computing an assumption's sensitivity
    or breakeven is permitted and encouraged; presenting an assumption change as an action that
    closes a gap is forbidden -- it instructs the user to fudge an input until the model passes.

WHY THIS MODULE, NOT A COMMENT (Ruling 2). A closed `Literal` plus a docstring is not sufficient:
a `Literal` is one line from extension, and a scope-economy rationale ("ONLY what the four levers
need (YAGNI)") expires at the exact moment someone has the scope -- which is when the harm
arrives. This module converts a one-line-plus-one-rationale edit into a multi-file,
self-incriminating diff that has to modify THIS declaration. `jacobian.py` and this module's own
import both fail loudly (`RuntimeError`) if `SeedTarget`'s members stop being exactly the image
of `INVESTOR_LEVERS`, or if `MODEL_ASSUMPTIONS` collides with any investor-facing surface. Every
attempted crossing is therefore a founder-visible event by construction (this repo is
direct-to-main, founder-holds-all-gates).

THE TWO SETS.
  * `INVESTOR_LEVERS` -- CLOSED. The four quantities an investor acts on in the world. Mirrors
    `src.market.recourse.LeverName` exactly (pinned by `tests/core/finance/test_partition.py`).
  * `MODEL_ASSUMPTIONS` -- OPEN (may only ever grow). Field paths for quantities an investor
    guesses. Growing this set is the SAFE direction (it only restricts what may ever become a
    lever) and may be done by an engineer with a guardian note (Ruling 4). `INVESTOR_LEVERS` is
    the opposite: closed, and extending it is never a self-approved edit (below).
  * `LEVER_SEED_TARGETS` -- the lever -> seed-target correspondence (D.1 SS1a): the rent lever's
    image is `income.gsi_annual`; price and rate map to their own `financing.*` field; annual
    opex's image is all 12 dollar line items of `OperatingExpenses`, each addressed
    `opex.<line>`. `jacobian.SeedTarget` is drift-guarded against the union of these images at
    import time (`jacobian.py`, immediately after `SeedTarget` is declared).

BARRED AXES (Ruling 3) -- a strict subset of `MODEL_ASSUMPTIONS` that may not carry ANY
differentiation or breakeven surface at all, lever or assumption, until the terminal-model
prerequisite chain below is complete: `market.cap_rate_drift`, `refi.exit_cap_rate`,
`horizon_years`. Their signal lives wholly or dominantly inside `engine.py`'s terminal-equity
PROXY (`EQUITY_LTV * term_est_value - term_ending_balance` -- not a real sale identity: no sale
costs, no transaction costs anywhere), so a derivative or breakeven along these axes would put
margin-of-safety confidence on a functional form chosen for simplicity, not fidelity -- the
1e-9-tolerance-on-an-unchecked-formula trap from GD1, transposed. Lever axes (price, rate, rent,
opex) differentiating THROUGH the proxy remain permitted and already ship (the IRR row includes
terminal-equity terms); it is only axes that live INSIDE the proxy that are barred.

Prerequisite chain to lift the bar (all four, in order, founder-approved -- no rationale string
waives any of them): (i) an explicit terminal sale model, with a named sale-cost assumption as a
surfaced schema field and `EQUITY_LTV` either replaced by the real sale identity or documented as
deliberate conservatism in both the schema and the rendered report; (ii) golden cases pinned over
the new terminal math under the GD1 anchor discipline; (iii) guardian review of the resulting
seed target; (iv) even then, exit cap / cap drift / horizon remain ASSUMPTIONS under Ruling 1 --
breakeven surface only, NEVER recourse.

THE SHAPE RULE FOR ANY FUTURE BREAKEVEN TYPE (Ruling 2.4). If and when assumption breakevens
ship, they ship in a new schema type whose fields cannot express a recourse "ask" -- the harmful
sentence ("raise your vacancy assumption to 8% and the deal passes") has no field to live in.
`assert_breakeven_shape(model_cls)` below is the real, enforced check (not a comment): it raises
`RuntimeError` if the candidate type carries a field whose name contains "target", "delta", or
"ask". Field names should instead read for the breakeven reading: assumed value, breakeven
value, margin, direction of failure.

SIGN-OFF RULES (Ruling 4, quoted near-verbatim -- the load-bearing sentence is verbatim):
Growing `INVESTOR_LEVERS`, adding any seed target or `_CoreOverrides` field, or moving a name
between the two sets is a Founder Proxy escalation citing this ruling -- never a self-approved
edit, whatever the rationale. In short: **extension of `INVESTOR_LEVERS` is a Founder Proxy
escalation citing GD3; a rationale string is not a clearance.** Growing `MODEL_ASSUMPTIONS` is
the safe direction (it only restricts) and may be done by an engineer with a guardian note.
Lifting the Ruling-3 bar requires the full prerequisite chain above, founder-approved.

SCOPE (Ruling 4 table) -- all four layers are bound, not just this seam:
  | Layer      | Bound surface                                                              |
  | ---------- | --------------------------------------------------------------------------|
  | Core seam  | `jacobian.SeedTarget`, `engine._CoreOverrides`, any future dual entry point |
  | Market     | `recourse.LeverName`, the single-lever search, and the Half-B combination  |
  |            | optimizer -- its search space is drawn from `INVESTOR_LEVERS` via          |
  |            | `LEVER_SEED_TARGETS`, nothing else                                        |
  | Schema     | `RecourseLever`/`RecourseAnalysis` stay closed to levers; any breakeven    |
  |            | type obeys `assert_breakeven_shape`                                       |
  | Report     | the "What would have to change?" section renders `RecourseLever` rows     |
  |            | only; assumption breakevens, if ever built, render from their own type    |
  |            | under margin-of-safety copy                                               |

This module intentionally imports ONLY from `src.schemas.models` (schema-first, no upward
dependency on `engine.py` or `jacobian.py`): both of those import THIS module, not the reverse.
"""

from __future__ import annotations

from collections.abc import Mapping
from itertools import combinations
from types import MappingProxyType
from typing import Any, Literal, get_args

from src.schemas.models import (
    IncomeModel,
    MarketAssumptions,
    MarketSnapshot,
    OperatingExpenses,
    RefinancePlan,
)

# ------------------------------------------------------------------------------------------
# INVESTOR_LEVERS -- CLOSED. Mirrors `src.market.recourse.LeverName` exactly, guarded from BOTH
# sides: pinned by test here, and `recourse.py` carries its own import-time guard comparing
# `get_args(LeverName)` against this tuple and raising `RuntimeError` naming the Founder Proxy
# escalation citing GD3. (An earlier revision of this comment said that guard was deferred
# because `recourse.py` sat outside this module's edit boundary; it shipped in the same
# mission -- corrected at Gate V, GV2-M3.)
# ------------------------------------------------------------------------------------------
InvestorLever = Literal["rent_per_unit_month", "purchase_price", "interest_rate", "annual_opex"]
INVESTOR_LEVERS: tuple[InvestorLever, ...] = get_args(InvestorLever)

#: The 12 dollar-denominated OPEX line items, in `OperatingExpenses`' own declaration order --
#: derived LIVE from the schema (not a fifth hardcoded copy) so this can never drift from it.
#: `expense_growth` is a rate, not a lever-perturbable dollar line, and is excluded.
_OPEX_LEVER_LINES: tuple[str, ...] = tuple(name for name in OperatingExpenses.model_fields if name != "expense_growth")

#: The lever -> seed-target correspondence (D.1 SS1a). This IS "the image of INVESTOR_LEVERS":
#: `jacobian.py` drift-guards `SeedTarget` against the union of these tuples at import time.
LEVER_SEED_TARGETS: Mapping[InvestorLever, tuple[str, ...]] = MappingProxyType(
    {
        "rent_per_unit_month": ("income.gsi_annual",),
        "purchase_price": ("financing.purchase_price",),
        "interest_rate": ("financing.interest_rate",),
        "annual_opex": tuple(f"opex.{line}" for line in _OPEX_LEVER_LINES),
    }
)

if frozenset(LEVER_SEED_TARGETS) != frozenset(INVESTOR_LEVERS):
    raise RuntimeError(
        "partition.LEVER_SEED_TARGETS' keys have drifted from partition.INVESTOR_LEVERS: "
        f"missing={sorted(frozenset(INVESTOR_LEVERS) - frozenset(LEVER_SEED_TARGETS))} "
        f"extra={sorted(frozenset(LEVER_SEED_TARGETS) - frozenset(INVESTOR_LEVERS))}"
    )

#: The full image of INVESTOR_LEVERS in seed-target space -- every dotted field path a lever is
#: allowed to reach, and (by the disjointness check below) exactly what an assumption may not.
LEVER_IMAGE: frozenset[str] = frozenset(target for targets in LEVER_SEED_TARGETS.values() for target in targets)

# ------------------------------------------------------------------------------------------
# MODEL_ASSUMPTIONS -- OPEN (safe direction: growing this set only restricts what may ever
# become a lever; Ruling 4). Field paths, covering at minimum the set the guardian named (C1).
# ------------------------------------------------------------------------------------------
MODEL_ASSUMPTIONS: frozenset[str] = frozenset(
    {
        "income.occupancy",
        "income.bad_debt_factor",
        "income.rent_growth",
        "opex.expense_growth",
        "market.cap_rate_drift",
        "refi.exit_cap_rate",
        "horizon_years",  # a call parameter (`horizon_years: int`), not a pydantic field -- see below
        "MarketSnapshot.vacancy_rate",
        "MarketSnapshot.rent_growth",
        "MarketSnapshot.expense_growth",
    }
)

#: Ruling 3 -- barred axes: a strict subset of MODEL_ASSUMPTIONS additionally forbidden from
#: EVERY differentiation and breakeven surface (not just recourse) until the terminal-sale-model
#: prerequisite chain (module docstring) is complete, because their signal lives wholly or
#: dominantly inside `engine.py`'s terminal-equity proxy.
BARRED_ASSUMPTION_AXES: frozenset[str] = frozenset({"market.cap_rate_drift", "refi.exit_cap_rate", "horizon_years"})

if not BARRED_ASSUMPTION_AXES <= MODEL_ASSUMPTIONS:
    raise RuntimeError(
        "partition.BARRED_ASSUMPTION_AXES names a path not present in partition.MODEL_ASSUMPTIONS: "
        f"{sorted(BARRED_ASSUMPTION_AXES - MODEL_ASSUMPTIONS)}"
    )

#: Which pydantic model each dotted MODEL_ASSUMPTIONS prefix resolves to, for the schema-drift
#: check below. `horizon_years` has no entry: it is a call parameter, not a schema field.
_ASSUMPTION_MODEL_MAP: Mapping[str, type[Any]] = MappingProxyType(
    {
        "income": IncomeModel,
        "opex": OperatingExpenses,
        "market": MarketAssumptions,
        "refi": RefinancePlan,
        "MarketSnapshot": MarketSnapshot,
    }
)


def _validate_model_assumption_paths() -> None:
    """Import-time drift guard: every dotted `MODEL_ASSUMPTIONS` path must name a real field on
    a real schema model, so a future rename/removal in `models.py` fails here instead of quietly
    leaving a dangling assumption path that no longer means anything."""
    for path in MODEL_ASSUMPTIONS:
        if path == "horizon_years":
            continue
        prefix, sep, field = path.partition(".")
        if not sep:
            raise RuntimeError(f"partition.MODEL_ASSUMPTIONS path {path!r} is not dotted and is not the 'horizon_years' special case")
        model_cls = _ASSUMPTION_MODEL_MAP.get(prefix)
        if model_cls is None or field not in model_cls.model_fields:
            raise RuntimeError(
                f"partition.MODEL_ASSUMPTIONS names {path!r}, which does not resolve to a real field "
                f"of a known schema model (prefix {prefix!r}). Fix the drift in src/core/finance/partition.py."
            )


_validate_model_assumption_paths()


# ------------------------------------------------------------------------------------------
# Ruling 2.3 -- disjointness with teeth. The message names the Founder Proxy escalation path
# explicitly, per C1/C3(b).
# ------------------------------------------------------------------------------------------


def _gd3_violation_message(surface_name: str, overlap: frozenset[str]) -> str:
    return (
        f"GD3 VIOLATION: {surface_name} contains {sorted(overlap)}, which THE LEVER/ASSUMPTION "
        "PARTITION (GD3, src/core/finance/partition.py) classifies as a MODEL ASSUMPTION (a "
        "quantity the investor guesses), not an INVESTOR LEVER (a quantity the investor can act "
        "on in the world). Presenting a solve along an assumption axis as recourse instructs the "
        "user to fudge an input until the model returns PASS -- a manufactured verdict. "
        "Extension of INVESTOR_LEVERS, any seed target, or any _CoreOverrides/RecourseLever "
        "field to reach a MODEL_ASSUMPTIONS path is a FOUNDER PROXY ESCALATION CITING GD3 -- a "
        "rationale string is not a clearance. See "
        "docs/plans/mission-5-discovery/GD3_lever_assumption_invariant.md (Ruling 2.3, Ruling 4)."
    )


def assert_disjoint_from_assumptions(
    external_surfaces: Mapping[str, Any] = MappingProxyType({}),
) -> None:
    """Import-time GD3 enforcement (Ruling 2.3): `INVESTOR_LEVERS`, `LEVER_IMAGE`, and any
    caller-supplied surface (e.g. `engine._CoreOverrides`' field names, `RecourseLever.lever`'s
    `Literal` args) must be disjoint from `MODEL_ASSUMPTIONS`. Raises `RuntimeError` naming the
    Founder Proxy escalation path on the first collision found. Called with no arguments at this
    module's own import time (self-check of `INVESTOR_LEVERS`/`LEVER_IMAGE`); callers such as
    `jacobian.py` pass their own additional surfaces.
    """
    surfaces: dict[str, frozenset[str]] = {
        "INVESTOR_LEVERS": frozenset(INVESTOR_LEVERS),
        "LEVER_IMAGE": LEVER_IMAGE,
    }
    for name, values in external_surfaces.items():
        surfaces[name] = frozenset(values)
    for surface_name, values in surfaces.items():
        overlap = values & MODEL_ASSUMPTIONS
        if overlap:
            raise RuntimeError(_gd3_violation_message(surface_name, overlap))


assert_disjoint_from_assumptions()


# ------------------------------------------------------------------------------------------
# Ruling 2.4 -- the breakeven shape rule: a real, enforced check, not a comment.
# ------------------------------------------------------------------------------------------

#: Field-name substrings (case-insensitive) that could express a recourse "ask". No future
#: assumption-breakeven type may carry a field whose name contains any of these.
_FORBIDDEN_BREAKEVEN_FIELD_TOKENS: tuple[str, ...] = ("target", "delta", "ask")


def assert_breakeven_shape(model_cls: type[Any]) -> None:
    """Ruling 2.4: an assumption-axis breakeven type may not carry a field that could express a
    recourse "ask" -- no `target_value`/`delta`/`ask`/`target`-shaped field, so the harmful
    sentence ("raise your vacancy assumption to 8% and the deal passes") has no field to live in.
    Fields should instead be named for the breakeven reading: assumed value, breakeven value,
    margin, direction of failure. Raises `RuntimeError` naming the Founder Proxy escalation path
    if `model_cls` (a pydantic `BaseModel` subclass) violates the shape rule.
    """
    fields = getattr(model_cls, "model_fields", None)
    if fields is None:
        raise TypeError(f"{model_cls!r} has no model_fields; assert_breakeven_shape expects a pydantic BaseModel subclass")
    bad = sorted(name for name in fields if any(token in name.lower() for token in _FORBIDDEN_BREAKEVEN_FIELD_TOKENS))
    if bad:
        raise RuntimeError(
            f"GD3 VIOLATION: {getattr(model_cls, '__name__', model_cls)} carries field(s) {bad} that could "
            "express a recourse 'ask' on a MODEL_ASSUMPTIONS axis (THE LEVER/ASSUMPTION PARTITION, Ruling "
            "2.4). An assumption-breakeven type's fields must be named for the breakeven reading only "
            "(assumed value, breakeven value, margin, direction of failure) -- shipping a target_value/"
            "delta/ask field here is a FOUNDER PROXY ESCALATION CITING GD3; a rationale string is not a "
            "clearance. See docs/plans/mission-5-discovery/GD3_lever_assumption_invariant.md (Ruling 2.4)."
        )


def investor_lever_combinations(*, min_size: int = 1, max_size: int | None = None) -> tuple[tuple[InvestorLever, ...], ...]:
    """Every subset of `INVESTOR_LEVERS`, size `min_size..max_size` (default: every non-empty
    subset), in a fixed, deterministic order. This is the ONLY sanctioned way to build a
    multi-lever candidate space (Ruling 4's Market row: "its search space is drawn from
    INVESTOR_LEVERS via the correspondence table, nothing else") -- a future Half-B combination
    optimizer draws its candidate space from THIS function, never from a hand-rolled list, so an
    assumption axis has no path into the search space short of editing `INVESTOR_LEVERS` itself
    (a Founder Proxy escalation citing GD3).
    """
    n = len(INVESTOR_LEVERS)
    hi = n if max_size is None else max_size
    if not (0 <= min_size <= hi <= n):
        raise ValueError(f"invalid size range [{min_size}, {hi}] for {n} levers")
    out: list[tuple[InvestorLever, ...]] = []
    for size in range(min_size, hi + 1):
        out.extend(combinations(INVESTOR_LEVERS, size))
    return tuple(out)
