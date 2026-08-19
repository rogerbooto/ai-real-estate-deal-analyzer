# Mission 1 — Scenario Intelligence — In Plain English

_For Roger. No jargon, no code references. One screen._

**Status: DONE and shipped.** It is in the program today, and you can check it yourself with the
hands-on guide at `docs/manual testing/MISSION_1_MANUAL_TESTING.md`.

## What is this mission?

The program already took one property, ran the numbers, and told you whether it looked like a buy.
This mission added a second, optional view: a "what if the market moves?" panel. When you ask for
it, the program re-runs the exact same math over a spread of market conditions — rents a little
higher or lower, interest rates up or down, vacancy worse — and shows you the range of outcomes
instead of a single number.

## Why did we do it / what problem does it solve?

A single verdict hides how fragile or sturdy a deal is. Two deals can both say "decline," but one
misses by a hair and the other by a mile — and the old report gave you no way to see which. The
building blocks to answer that already existed in the codebase but were never connected to the
report, so all that work sat unused. This mission connected them.

## What are the goals?

- Let you optionally see a range of outcomes (cash flow, returns, debt coverage) across many market
  what-ifs, not just one.
- Be honest about what the range is: deterministic what-ifs over *your own* assumptions, not a
  prediction and not live market data.
- Keep it strictly opt-in, so a normal run is completely unchanged.
- Make the program installable as a proper tool with working command shortcuts.

## What will we have when it's done that we don't now?

- **Before:** one report, one verdict, no sense of the spread. **After:** add one switch and the
  report grows a "Market Scenarios" panel showing best/middle/worst-case bands, each labelled
  plainly as a what-if, not a forecast.
- **Before:** installing the tool didn't fully work and the short commands (`deal-report`,
  `deal-advisor`, `ingest-listing`) didn't exist. **After:** it installs cleanly and those commands
  work.
- **Before:** an internal returns calculation could occasionally spit out a nonsensical number for
  deeply losing deals. **After:** it always returns a sensible one.

## What it deliberately will NOT do

- It does not change any normal report. With the switch off, output is identical to before —
  guaranteed.
- It does not predict the market or pull in live data. Every number comes from your own inputs.
- It does not touch the core financial math (beyond the one small returns-calculator fix above).

## How you'll know it worked

Follow `docs/manual testing/MISSION_1_MANUAL_TESTING.md`: run the program with and without the
switch, confirm the panel appears only when asked, confirm a normal run is byte-for-byte unchanged,
and confirm the short commands work. Every command there was run and passes today.
