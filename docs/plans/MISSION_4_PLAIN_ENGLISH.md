# Mission 4 — "What Would Have To Change?" — In Plain English

_For Roger. No jargon, no code references. One screen._

> **Status: CHARTERED, NOT YET BUILT — and sequenced after Mission 3.** This is the plan for the mission
> after the one you're finishing. Nothing has been built yet, and by the one-mission-at-a-time rule it
> does not start until Mission 3 (the bring-your-own AI model work) has cleared your gate and merged.
> When it is built, you will verify it by hand with `docs/manual testing/MISSION_4_MANUAL_TESTING.md`.
> Until then, every test case in that document is expected to **fail** — it describes the gap this
> mission closes, and doubles as the acceptance checklist you tick off at the end.

## What is this mission?

Right now the program gives every deal a clear verdict: buy, proceed-with-conditions, or walk away. But
when a deal *just barely* misses, it says so only in its own technical language — something like "debt
coverage is weak at 1.19, below the 1.20 line." That sentence is true, but it doesn't tell an investor
anything they can act on. Nobody negotiates a purchase in "debt coverage points."

This mission keeps the verdict exactly as it is and adds one honest, practical thing next to a
near-miss: **how far the deal is from passing, and what single change would close the gap — described in
things an investor can actually move.** Not one answer, but several, so you can pick the lever you have
control over.

## Why are we doing it / what problem does it solve?

A deal that misses by a hair and a deal that misses by a mile currently get the same stamp. That flattens
away the most useful information there is: *how close was it, and what would it take?* An investor
staring at "conditional" wants to know whether they're one small rent bump away or hopelessly short — and
the program has all the numbers to answer that, it just never does. This turns a discouraging-looking
label into a negotiating checklist.

## What are the goals?

- For a near-miss deal, show **how far it sits from the line** on each thing it failed.
- Translate that distance into **investor-movable levers**: a bit more rent per unit, a lower purchase
  price, a slightly better interest rate, or lower yearly operating costs.
- Give **several routes for the same gap** — so the person who can push rents and the person who can only
  push price each get an answer that fits them.
- Be **honest about the levers**: if a suggested change is unrealistic (say, a rent already at the top of
  the market), still show it, but flag *why* it's a stretch — never quietly hide it.
- When several things are wrong at once, **lead with the cheapest single fix** but say clearly that other
  gaps remain, so a partial fix is never mistaken for a complete one.
- When **nothing realistic** would close the gap, say so plainly — no false hope.

## What will we have when it's done that we don't now?

- **Before:** a near-miss says "debt coverage is weak at 1.19 (< 1.20)" and stops there.
  **After:** it also says, in plain money terms, what would close it — several ways, like this:

  > **CONDITIONAL — debt coverage falls just short.**
  > Any ONE of these *would* close it (holding the other levers fixed):
  > - about **$38 more rent per unit per month** (a 3.1% increase) — flagged: already near top-of-market
  > - about **$9,800 off the purchase price** (2.4% below asking)
  > - about **0.18% off your interest rate**
  > - about **$460 less in annual operating costs**

- **Before:** the distance to passing is invisible — miss-by-a-hair and miss-by-a-mile look identical.
  **After:** you can see at a glance whether a deal is one nudge away or genuinely out of reach.
- **Before:** nothing tells you which fix is smallest when several things are wrong.
  **After:** the cheapest single fix is called out first, with an honest note that other gaps remain.
- **Before:** a hopeless deal still just says "decline."
  **After:** a hopeless deal says, plainly, that no realistic change would close it — so you don't waste
  time chasing it.

**One thing worth stressing, because it's the whole point of doing this carefully:** the levers are not
independent of each other. Dropping the purchase price doesn't just lower the price — it also shrinks the
loan, changes the cap rate, and changes how much cash you put in, all at once. So the program will not do
quick back-of-envelope math on one number in isolation (that would over-promise — it would claim a price
cut fixes a gap it doesn't actually fix). Instead it re-runs the **same trusted deal calculator** it
already uses, changing one lever at a time, and reads off the real result. Slower, but it can never drift
from what the program actually does. This is deliberate, and it's a test the work has to pass before it
ships.

## What it deliberately will NOT do (left open on purpose)

- It will **not** change any verdict, any pass/fail line, or any of the program's thresholds. The buy /
  conditional / decline decision stays exactly as it is today. (It does make it sensible to *revisit*
  some of those thresholds later, because a near-miss stops looking fatal — but that's a separate,
  future decision, not this mission.)
- It will **not** touch the financial engine's internal math. It only *calls* that engine, as a sealed
  box, once per "what if I changed this one thing" question.
- It will **not** pull in live market data, comps, or anything from the internet. Realism checks use the
  program's existing plausibility logic only.
- It will **not** add any screen, app, or interactive interface — the output is the written report.
- It will **not** involve any AI, model, or the photo/vision work. This is pure, deterministic deal math,
  which is exactly why it's independent of Mission 3.

## How you'll know it worked

Follow `docs/manual testing/MISSION_4_MANUAL_TESTING.md`. It walks you through running a near-miss deal
and seeing the new "what would have to change?" block appear with several honest levers; checking that
each stated change, when you actually feed it back through the program, really does flip the verdict (the
proof it re-ran the engine instead of guessing); seeing a stretch lever flagged rather than hidden;
seeing the cheapest fix lead when several things fail; and seeing a genuinely hopeless deal say so
plainly. Every step has a clear yes/no so nothing can pretend to be finished when it isn't.
