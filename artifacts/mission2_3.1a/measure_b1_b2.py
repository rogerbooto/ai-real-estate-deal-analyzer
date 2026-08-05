"""
MEASUREMENT ONLY — Mission 2 / Wave 3 task 3.1a, Task B. This script IMPLEMENTS NOTHING.

It re-scores deals under two *hypothetical* guardrail changes and prints what would move, so the
decision can be made on numbers rather than on a description. Nothing in `src/` imports it, and it
changes no file.

    B1  Add a Year-1 cash-on-cash floor (MIN_COC_Y1 = 3%) as a live verdict input.
        The deleted `src/core/strategy/strategist.py` had `coc < 0.03`; the live strategist has no
        CoC guardrail at all, so `PurchaseMetrics.coc` is computed and never consulted.

    B2  Require the cap-floor DECLINE shortcut to need a *material* breach (>= 25bp / >= 50bp)
        AND `DSCR < 1.00`, instead of today's "any breach AND DSCR < 1.20".

Run from the repo root:

    source /home/rtokime/anaconda3/etc/profile.d/conda.sh; conda activate airedeal
    python artifacts/mission2_3.1a/measure_b1_b2.py
"""

from __future__ import annotations

import itertools
import pathlib
import sys
from collections import Counter
from typing import Any

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.agents.chief_strategist import (  # noqa: E402
    MIN_DSCR_Y1,
    MIN_IRR_10YR,
    REQUIRE_POSITIVE_CF_ALL,
    REQUIRE_POSITIVE_CF_Y1,
    spread_target_for,
)
from src.agents.financial_forecaster import forecast_financials  # noqa: E402
from src.inputs.inputs import InputsLoader  # noqa: E402
from src.schemas.models import (  # noqa: E402
    FinancialForecast,
    FinancialInputs,
    FinancingTerms,
    IncomeModel,
    MarketAssumptions,
    OperatingExpenses,
    RefinancePlan,
    UnitIncome,
)

MIN_COC_Y1 = 0.03  # B1 candidate, ported from the dead strategist.py


# ---------------------------------------------------------------------------------------------
# Scoring — a faithful re-implementation of chief_strategist's verdict rule, so the hypotheticals
# can be evaluated without editing it. Kept in one place and diffed against the real module by eye
# at review time; if the real rule changes, this must be re-derived before its numbers are quoted.
# ---------------------------------------------------------------------------------------------
def _guardrails(forecast: FinancialForecast, market: MarketAssumptions | None) -> dict[str, bool]:
    y1 = forecast.years[0]
    return {
        "dscr_ok": y1.dscr >= MIN_DSCR_Y1,
        "spread_ok": forecast.purchase.spread_vs_rate >= spread_target_for(market),
        "irr_ok": forecast.irr_10yr >= MIN_IRR_10YR,
        "cf_y1_ok": (y1.cash_flow >= 0.0) if REQUIRE_POSITIVE_CF_Y1 else True,
        "cf_all_ok": all(y.cash_flow >= 0.0 for y in forecast.years) if REQUIRE_POSITIVE_CF_ALL else True,
        "no_cap_floor_breach": not any("cap rate" in w.lower() and "below floor" in w.lower() for w in forecast.warnings),
    }


def _verdict(fails: list[bool], shortcut: bool) -> str:
    if not any(fails):
        return "BUY"
    return "DECLINE" if (sum(1 for f in fails if f) >= 3 or shortcut) else "CONDITIONAL"


def score(forecast: FinancialForecast, market: MarketAssumptions | None, *, materiality_bp: float) -> dict[str, Any]:
    g = _guardrails(forecast, market)
    y1 = forecast.years[0]
    coc = forecast.purchase.coc

    fails = [
        not g["dscr_ok"],
        not g["spread_ok"],
        not g["irr_ok"],
        not g["cf_y1_ok"],
        not g["cf_all_ok"],
        not g["no_cap_floor_breach"],
    ]
    shortcut_today = (not g["no_cap_floor_breach"]) and (not g["dscr_ok"])

    floor = market.cap_rate_floor if market is not None else None
    breach_bp = (floor - forecast.purchase.cap_rate) * 10_000 if (floor is not None and forecast.purchase.cap_rate < floor) else None
    material = breach_bp is not None and breach_bp >= materiality_bp

    return {
        "cap": forecast.purchase.cap_rate,
        "spread": forecast.purchase.spread_vs_rate,
        "dscr": y1.dscr,
        "coc": coc,
        "coc_ok": coc >= MIN_COC_Y1,
        "irr": forecast.irr_10yr,
        "cf1": y1.cash_flow,
        "warnings": list(forecast.warnings),
        "n_fails": sum(1 for f in fails if f),
        "shortcut_today": shortcut_today,
        "breach_bp": breach_bp,
        "today": _verdict(fails, shortcut_today),
        "b1": _verdict(fails + [coc < MIN_COC_Y1], shortcut_today),
        "b2": _verdict(fails, material and y1.dscr < 1.00),
    }


# ---------------------------------------------------------------------------------------------
# Corpus 1 — every deal that ships in this repo and can actually be underwritten end to end.
# ---------------------------------------------------------------------------------------------
def repo_corpus() -> list[tuple[str, str, FinancialInputs]]:
    from main import build_sample_inputs
    from tests.integration.test_chief_strategist import _inputs_good, _inputs_mixed, _inputs_poor

    def load(p: pathlib.Path) -> FinancialInputs:
        return InputsLoader().load(str(p)).inputs

    shipped = "data/sample_listings/36_kelly_moncton/inputs.json"
    out = [("36 Kelly (shipped sample)", shipped, load(REPO / shipped))]
    for cfg in sorted((REPO / "artifacts/mission2_3.1a/configs").glob("*.json")):
        out.append((f"36 Kelly variant: {cfg.stem}", f"artifacts/mission2_3.1a/configs/{cfg.name}", load(cfg)))
    out += [
        ("main.py built-in demo deal", "main.build_sample_inputs()", build_sample_inputs()),
        ("suite fixture: strong deal", "tests/integration/test_chief_strategist.py::_inputs_good", _inputs_good()),
        ("suite fixture: marginal deal", "tests/integration/test_chief_strategist.py::_inputs_mixed", _inputs_mixed()),
        ("suite fixture: weak deal", "tests/integration/test_chief_strategist.py::_inputs_poor", _inputs_poor()),
    ]
    return out


# ---------------------------------------------------------------------------------------------
# Corpus 2 — a systematic sweep, because the repo ships too few deals to answer "how often".
# ---------------------------------------------------------------------------------------------
PRICES = [250_000.0, 350_000.0, 500_000.0, 750_000.0]
DPS = [0.05, 0.10, 0.20, 0.25, 0.35, 0.50]
RATES = [0.040, 0.050, 0.055, 0.065, 0.075]
RENTS = [900.0, 1100.0, 1300.0, 1600.0, 2000.0]
UNITS = [2, 4, 6]
FLOORS: list[float | None] = [None, 0.05, 0.06, 0.07]
TARGETS = [0.005, 0.015, 0.025]


def build(price: float, dp: float, rate: float, rent: float, units: int, floor: float | None, target: float) -> FinancialInputs:
    return FinancialInputs(
        financing=FinancingTerms(
            purchase_price=price, closing_costs=8_000.0, down_payment_rate=dp, interest_rate=rate, amort_years=30, io_years=0
        ),
        opex=OperatingExpenses(
            insurance=2400.0,
            taxes=price * 0.012,
            utilities=3600.0,
            water_sewer=1800.0,
            property_management=rent * units * 12 * 0.08,
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
            units=[UnitIncome(rent_month=rent, other_income_month=50.0) for _ in range(units)],
            occupancy=0.95,
            bad_debt_factor=0.97,
            rent_growth=0.03,
        ),
        refi=RefinancePlan(do_refi=False),
        market=MarketAssumptions(cap_rate_purchase=None, cap_rate_floor=floor, cap_rate_spread_target=target),
        capex_reserve_upfront=0.0,
    )


def sweep(materiality_bp: float) -> list[dict[str, Any]]:
    rows = []
    for price, dp, rate, rent, units, floor, target in itertools.product(PRICES, DPS, RATES, RENTS, UNITS, FLOORS, TARGETS):
        inputs = build(price, dp, rate, rent, units, floor, target)
        f = forecast_financials(inputs=inputs, insights=None, horizon_years=10)
        shape = {"inputs": inputs, "dp": dp, "price": price, "rate": rate, "rent": rent, "units": units, "floor": floor, "target": target}
        rows.append({**score(f, inputs.market, materiality_bp=materiality_bp), **shape})
    return rows


def main() -> None:
    print("#" * 118)
    print("# PART 1 — the deals that actually ship in this repo")
    print("#" * 118)
    head = f"{'deal':<44} {'cap':>7} {'spread':>7} {'DSCR':>6} {'CoC Y1':>8} {'IRR':>7}"
    print(head + f" {'CF Y1':>9} {'today':>12} {'with B1':>12} {'with B2':>12}")
    print("-" * 118)
    for label, _prov, inputs in repo_corpus():
        f = forecast_financials(inputs=inputs, insights=None, horizon_years=10)
        s = score(f, inputs.market, materiality_bp=25.0)
        mark1 = " <-- MOVES" if s["b1"] != s["today"] else ""
        mark2 = " <-- MOVES" if s["b2"] != s["today"] else ""
        print(
            f"{label:<44} {s['cap']:>7.2%} {s['spread']:>7.2%} {s['dscr']:>6.2f} {s['coc']:>8.2%} {s['irr']:>7.2%} "
            f"{s['cf1']:>9,.0f} {s['today']:>12} {s['b1']:>12}{mark1} {s['b2']:>12}{mark2}"
        )

    rows = sweep(25.0)
    rows50 = sweep(50.0)
    n = len(rows)
    print()
    print("#" * 118)
    print(f"# PART 2 — systematic sweep, {n:,} deals (price x down-payment x rate x rent x units x cap-floor x spread-target)")
    print("#" * 118)
    print(f"Verdict mix today: {dict(Counter(r['today'] for r in rows))}")

    print()
    print(f"--- B1: a {MIN_COC_Y1:.0%} Year-1 cash-on-cash floor " + "-" * 60)
    movers = [r for r in rows if r["b1"] != r["today"]]
    moves = dict(Counter((r["today"], r["b1"]) for r in movers))
    print(f"verdicts that move: {len(movers):,} / {n:,} = {len(movers) / n:.2%}   transitions: {moves}")
    missers = [r for r in rows if not r["coc_ok"]]
    print(f"deals that miss the {MIN_COC_Y1:.0%} floor at all: {len(missers):,} ({len(missers) / n:.1%})")
    flagged = sum(1 for r in missers if r["n_fails"] >= 1)
    clean = sum(1 for r in missers if r["n_fails"] == 0)
    print(f"    ... of which ALREADY fail >=1 existing guardrail: {flagged:,} ({flagged / len(missers):.1%})")
    print(f"    ... of which are a clean BUY today (i.e. the floor would catch something nothing else does): {clean:,}")
    if movers:
        cocs = sorted(r["coc"] for r in movers)
        med = cocs[len(cocs) // 2]
        print(
            f"movers' Year-1 CoC: min {cocs[0]:.2%}, median {med:.2%}, max {cocs[-1]:.2%}; "
            f"median shortfall {(MIN_COC_Y1 - med) * 100:.2f}pp"
        )
        pos = sum(1 for r in movers if r["cf1"] > 0)
        irr_ok = sum(1 for r in movers if r["irr"] >= 0.12)
        dscr_ok = sum(1 for r in movers if r["dscr"] >= 1.20)
        allthree = sum(1 for r in movers if r["cf1"] > 0 and r["irr"] >= 0.12 and r["dscr"] >= 1.20)
        print(f"movers that are cash-flow positive: {pos:,} · with IRR >= 12%: {irr_ok:,} · with DSCR >= 1.20: {dscr_ok:,}")
        print(f"movers passing all three of those at once: {allthree:,}")
        c = max(movers, key=lambda r: r["coc"])
        short_bp = (MIN_COC_Y1 - c["coc"]) * 10_000
        print(
            f"closest call: CoC {c['coc']:.4%} (short by {short_bp:.1f} bp) — "
            f"DSCR {c['dscr']:.2f}, IRR {c['irr']:.2%}, Y1 CF ${c['cf1']:,.0f}"
        )

    print()
    print("--- B2: material breach (>=25bp / >=50bp) AND DSCR < 1.00 " + "-" * 45)
    breachers = [r for r in rows if r["breach_bp"] is not None]
    fired = [r for r in breachers if r["shortcut_today"]]
    decisive = [r for r in fired if r["n_fails"] < 3]
    print(f"deals that breach their floor at all: {len(breachers):,} ({len(breachers) / n:.1%})")
    redundant = len(fired) - len(decisive)
    print(
        f"shortcut fires today: {len(fired):,} — but {redundant:,} "
        f"({redundant / max(1, len(fired)):.1%}) already DECLINE via the >=3-fails rule"
    )
    print(
        f"DECLINEs that exist ONLY because of the shortcut: {len(decisive):,} "
        f"({len(decisive) / n:.2%} of all deals) <- its entire real effect"
    )
    if decisive:
        bps = sorted(r["breach_bp"] for r in decisive)
        dscrs = sorted(r["dscr"] for r in decisive)
        print(f"    their breach sizes: min {bps[0]:.2f}bp, median {bps[len(bps) // 2]:.2f}bp, max {bps[-1]:.2f}bp")
        print(f"    their DSCRs:        min {dscrs[0]:.2f}, median {dscrs[len(dscrs) // 2]:.2f}, max {dscrs[-1]:.2f}")
        print(f"    spared by the DSCR<1.00 half alone: {sum(1 for r in decisive if r['dscr'] >= 1.00):,} of {len(decisive):,}")
        under25 = sum(1 for r in decisive if r["breach_bp"] < 25)
        under50 = sum(1 for r in decisive if r["breach_bp"] < 50)
        print(f"    spared by the materiality half alone (>=25bp): {under25:,};  (>=50bp): {under50:,}")
    for tag, rs in (("@25bp", rows), ("@50bp", rows50)):
        mv = [r for r in rs if r["b2"] != r["today"]]
        tr = dict(Counter((r["today"], r["b2"]) for r in mv))
        print(f"B2 {tag}: verdicts that move: {len(mv):,} / {n:,} = {len(mv) / n:.2%}   transitions: {tr}")

    print()
    print("--- B2 supporting: is the shortcut near-tautological? " + "-" * 50)
    print("Among deals that breach their cap-rate floor, how often is DSCR already below the bar?")
    for label, sub in (
        ("all leverage", breachers),
        ("LTV >= 70% (<=30% down)", [r for r in breachers if r["dp"] <= 0.30]),
        ("LTV < 70%", [r for r in breachers if r["dp"] > 0.30]),
        ("5% floor, LTV >= 70%", [r for r in breachers if r["floor"] == 0.05 and r["dp"] <= 0.30]),
    ):
        if sub:
            u120 = sum(1 for r in sub if r["dscr"] < 1.20) / len(sub)
            u100 = sum(1 for r in sub if r["dscr"] < 1.00) / len(sub)
            print(f"  {label:<26} n={len(sub):>5}   DSCR < 1.20 in {u120:>6.1%}   DSCR < 1.00 in {u100:>6.1%}")

    print()
    print("--- B2: the hairline-breach case, constructed " + "-" * 58)
    print("Take the healthiest deal the shortcut currently DECLINEs and shrink its breach toward zero.")
    if decisive:
        seed = max(decisive, key=lambda r: r["dscr"])
        si: FinancialInputs = seed["inputs"]
        for delta in (2e-8, 2.5e-5, 5e-5, 1e-3):
            tweaked = si.model_copy(update={"market": si.market.model_copy(update={"cap_rate_floor": seed["cap"] + delta})})
            f = forecast_financials(inputs=tweaked, insights=None, horizon_years=10)
            s = score(f, tweaked.market, materiality_bp=25.0)
            s50 = score(f, tweaked.market, materiality_bp=50.0)
            print(
                f"  breach {s['breach_bp']:>9.4f}bp | DSCR {s['dscr']:.2f} · IRR {s['irr']:.2%} · "
                f"Y1 cash flow ${s['cf1']:,.0f} · other fails {s['n_fails'] - 1} "
                f"|| today = {s['today']:<11} B2@25bp = {s['b2']:<11} B2@50bp = {s50['b2']}"
            )


if __name__ == "__main__":
    main()
