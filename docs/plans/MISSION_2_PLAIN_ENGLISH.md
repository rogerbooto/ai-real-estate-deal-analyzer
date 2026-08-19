# Mission 2 — Close the Wiring Gaps — In Plain English

_For Roger. No jargon, no code references. One screen._

> **Status note — please read.** This brief was requested on the assumption that Mission 2 was
> planned but not yet built. That is out of date: **Mission 2 is DONE and shipped** — it was merged,
> released as version 0.3.0, and pushed, and it is live on the main line today. (The old roadmap page
> still says "ready to build"; that page simply wasn't updated when the work landed — a small
> irony for a mission about keeping documents honest.) You can verify every fix by hand with
> `docs/manual testing/MISSION_2_MANUAL_TESTING.md`.

## What is this mission?

A cleanup mission focused on one theme: **making the program tell the truth about itself.** An audit
found places where the report claimed things that weren't checked, where real calculated results
were quietly thrown away before they reached the page, and where command-line switches did nothing
or crashed. This mission fixed those and, importantly, added an automatic tripwire so the same kind
of "quiet drop" can't creep back in unnoticed.

## Why did we do it / what problem does it solve?

The product's whole promise is that its numbers are trustworthy. That promise was being quietly
broken. Concrete symptoms the audit found:

- The report always said a deal "respects the cap-rate floor policy" — even for deals with no floor
  set and even for deals that broke it. It was a sentence that printed no matter what.
- Analyze a listing without giving its financials, and the program silently underwrote *your*
  property against the *demo* property's price and rent — with nothing on the page admitting it.
- Several switches were dead or misleading; a couple of bad inputs threw raw error dumps at the user
  instead of a clear message; one switch silently overwrote your saved file.

## What are the goals?

- Stop the report from stating things the program didn't actually check.
- Stop silently discarding computed results before they reach the report.
- Make every command-line switch either do what it says or clearly explain why it can't.
- Add a safety net that fails loudly if any future change starts dropping information again.
- Fix the documentation so it matches what the code really does.

## What will we have when it's done that we don't now?

- **Before:** the report boasted about a floor policy unconditionally. **After:** it names the actual
  cap rate and the actual floor ("Purchase cap rate is 6.35% (≥ the 5.00% floor you set)"), and a
  real breach actually counts against the deal.
- **Before:** a listing with no financials silently borrowed the demo deal's numbers. **After:** the
  program refuses and tells you exactly how to fix it.
- **Before:** bad inputs produced ugly crash dumps; one export switch overwrote your JSON. **After:**
  clean, plain error messages; the export writes to a separate file and keeps your data.
- **Before:** facts and provenance the program computed never reached the page. **After:** the report
  shows the run's settings and the "why" behind the numbers.
- A retired duplicate "second opinion" calculator that disagreed with the real engine is gone, and a
  toy calculator that was inventing numbers was removed rather than shipped.

## What it deliberately will NOT do (left open on purpose)

- It does **not** close one back-door version of the "borrowed financials" problem that comes through
  environment settings — that touches a documented contract and was left for later.
- It does **not** change the pass/fail thresholds themselves; those were measured and handed to you
  as a separate decision.
- It does **not** add any new AI, user interface, or live market data.

## How you'll know it worked

Follow `docs/manual testing/MISSION_2_MANUAL_TESTING.md`. It walks each fix, shows the old broken
behaviour beside the new correct one, and marks the handful of items deliberately left for later so
nothing pretends to be finished when it isn't.
