# 82 Champlain Street, Dieppe, NB — Mission 4 recourse fixture

This deal is a **synthetic** fixture (fictional address, fictional listing agent — see the notice
at the bottom of `listing.txt`), built for one purpose: to be a realistic property whose
underwriting output actually opens the "What would have to change?" gate
(`src/market/recourse.py`'s `is_genuinely_close`), so that report section has real data to render
against. **`36_kelly_moncton`, the pinned demo deal, deliberately does not** — it fails 4 of 6 live
guardrails, which is past `GENUINELY_CLOSE_MAX_FAILS = 3`, and it must keep producing an
unchanged, byte-identical report (it is pinned by golden fixtures and the `python main.py`
determinism hash). This fixture is additive; it does not touch `36_kelly_moncton` in any way.

## Why these specific numbers

A 4-unit purpose-built fourplex, $605,000, financed with 20% down (no mortgage insurance —
`down_payment_rate` is exactly at the 20% cutoff) at a 6.80% rate over 30 years. Rents are
$1,450 / $1,450 / $1,400 / $1,350 per month (a plausible, slightly-below-market rent roll for a
fourplex in a smaller Atlantic Canada market), and operating expenses ($20,600/yr total — taxes,
insurance, individually-metered utilities, water/sewer, a modest property-management line,
repairs, and reserves) are ordinary, itemized numbers for a building this size — not reverse-
engineered from a target ratio.

These numbers were **found by search, not invented backward from the recourse output**: starting
from a plausible 4-unit deal shape, purchase price and interest rate were walked in $/bps
increments (re-running the real underwriting engine each time, the same discipline
`src/market/recourse.py` itself uses) until the deal landed in the "genuinely close" band — at
most 3 of the 6 live guardrails failing, at least 1. The specific point chosen (three narrow
misses, one of them landing within a fraction of a percentage point of its own bar) was picked
over several other points in that same band because it is the most *demonstrative* one, not
because it is the only realistic one. If you need a deal that is realistic AND uninteresting for
recourse (e.g. exactly one guardrail failing by a wide margin), most of the price/rate grid this
fixture was searched from would also qualify — this one was kept because it exercises three
different render paths at once (see below).

## What it actually produces (verified against the real `compute_recourse` + `generate_report` output)

Verdict: **DECLINE**. Three guardrails fail: **DSCR (Y1)** 1.10 (bar 1.20), **Cap-rate spread**
0.12% (bar 1.50%), **Cash-on-cash (Y1)** 2.77% (bar 3.00%). Projected IRR (10y) clears its bar
narrowly (12.00%, bar 12.00%) and Year-1 cash flow is positive ($3,655) — this is a real
multi-metric near-miss, not a single-number miss dressed up as one.

This exercises, in one fixture, the three things the recourse section needed a real example of:

1. **A plausible, cheap closing lever.** The cash-on-cash gap is nearly closed already — a
   **$10/unit/month** rent increase (0.71% above current), or equivalently a $4,500 price cut, a
   10 bps rate cut, or a $350 opex cut, all close it on their own. The cheapest of these
   (the rent increase) is the section's lead recommendation.
2. **A flagged (implausible) closing lever sitting beside a genuinely plausible one, in the same
   block.** Every lever that *would* close the cap-rate-spread gap on its own is a real fix, but
   every one of them is also a *big* ask on this deal (a 13.5% rent increase, a 16.6% price cut,
   or a 140 bps rate cut) — all three get flagged by this project's own realism thresholds, and
   the opex lever, uniquely for this gap, is a genuine per-row "searched, found nothing within the
   bound" null (not structurally hopeless — it moves the metric, just not far enough). The spread
   gap block is the one place in this fixture with **zero unflagged closing rows** — the honest
   "every fix here is a stretch" case.
3. **"Cheapest fix, other gaps remain."** The single cheapest fix (the $10 rent increase) closes
   *only* the cash-on-cash gap — DSCR and cap-rate spread are untouched by it and need their own,
   larger moves. `remaining_after_cheapest` is non-empty, which is exactly the case Gate V's
   review flagged as never allowed to be omitted or buried.

## What it deliberately does NOT exercise

This fixture does not produce a `structurally_hopeless` row (that needs either an interest-rate
lever against a cap-floor breach, or an overridden `market.cap_rate_purchase` — this deal lets the
cap rate float, and cap_floor is not one of its failing guardrails) or a whole-analysis
`honest_null`. Both of those render paths are covered by dedicated unit fixtures instead — see
`tests/core/reports/test_recourse_render.py` — rather than distorted into this deal, per this
task's own instruction to prefer "realistic and less interesting" over reverse-engineered
numbers when the two are in tension.

## Files

- `inputs.json` — the full `FinancialInputs` payload (nested under `"inputs"`, matching
  `36_kelly_moncton`'s convention), plus `"run"` and a top-level `"market"` snapshot block for the
  opt-in scenario engine.
- `listing.txt` — a plain-text listing in the same style as the other sample bundles.
- `finance.json` — the `deal-advisor` CLI's discovery summary (irr / cashflow_monthly /
  price-per-sqft), computed from the same inputs.
- No `photos/` directory ships with this fixture — it exists purely to exercise the financial
  guardrail/recourse pipeline, not the CV/media pipeline, and `main.py`/`ensure_sample_assets`
  tolerate a missing photos folder without fabricating anything (verified: running
  `python main.py --config data/sample_listings/82_champlain_dieppe/inputs.json` produces a report
  with no Media Overview section and no crash).
