# Mission 5 — Forward-Mode Differentiation & Optimized Recourse Search — In Plain English

_For Roger. No jargon, no code references. One screen (a bit more, now that it's two halves)._

> **Status: CHARTERED, NOT YET BUILT.** This is the plan for the next mission. Mission 4 (the
> "what would have to change?" recourse feature) is already finished and merged. **You expanded this
> mission on 2026-08-31** to cover two things instead of one — the faster math AND a new "bundles of
> changes" feature — so it is bigger than the original plan. When it's built you'll verify it by hand
> with `docs/manual testing/MISSION_5_MANUAL_TESTING.md`. Until then, the cases in that document
> describe the target — they double as the acceptance checklist you tick off at the end.

## What is this mission? (it has two halves)

**Half A — make the existing feature faster.** Right now, when the program tells you what would close a
near-miss deal, it finds the answer by **trial and error**. It nudges one thing — say the rent — re-runs
the entire financial model, sees if the deal now passes, nudges again, and repeats, ten to twenty times,
until it homes in on the number. It works and it is honest, but it is slow, especially on a big
portfolio. This half teaches the program a faster way to arrive at the *same* answer: instead of guessing
and checking over and over, it works out the **slope** — how much the result moves when you move a lever
a little — and uses that slope to **jump almost straight to the answer** in three or four tries instead
of twenty. Then, and this is the important safeguard, it **confirms the jump with one real, full re-run
of the model** before it shows you anything. So we get the speed of the shortcut and the trust of the
real calculation.

**Half B — a new "bundles of changes" section (this is the part you added).** Today the program
only ever tells you the single cheapest thing to change: "raise rent by $38, OR cut price by $9,800,
OR…". But you might be able to move *more than one lever at once*. So besides the single-lever list, the
report will now also show **every realistic bundle of changes that survives a sanity check** — up to
eleven of them, one per meaningful combination of the four levers — e.g. "a smaller rent bump *and* a
small price cut *together* would close it." Each bundle is **checked by the real calculator** before
it's shown, and the program **only ever suggests combinations that make sense** — it won't tell you to
do two things that individually look fine but together are unrealistic.

> **⚠ CORRECTED 2026-08-31 — you settled the final shape yourself.** The earlier plan (below, under
> "goals" and "how you'll know it worked") described a **ranked "top-3"** list. You changed that: since
> a bundle is shown for every lever-combination that survives, the single cheapest one is simply
> **labelled** "cheapest total negotiation" instead of being picked by a separate ranking step — in
> your words, *"with a 'cheapest total negotiation' alongside the others, we have no more need for a
> ranking."* So you'll see all the survivors, unranked, with the cheapest one marked.

You get **both** views — the single cheapest lever AND the sensible bundles — because we don't know in
advance whether you can move one thing or several.

**Why the two halves are done in that order, with a checkpoint between them.** The bundles feature (B)
is built on top of the fast slope math (A). So we prove the fast math is correct *first*, at a hard
checkpoint, before building the bundles on it. If the fast math doesn't pan out, we still ship Half A's
speed-up (or at least the safety rule below) and set the bundles aside for later — and if a bundle ever
comes out wrong, we know the problem is in the bundle-picker, not hidden in the math underneath.

## Why are we doing it / what problem does it solve?

The recourse search is the slowest part of a large analysis. On the biggest deals we care about
(thousands of units, a hundred-year horizon), all that nudge-and-recheck adds up. You set a target of
making a 5,000-unit / 100-year analysis fast.

> **⚠ CORRECTED 2026-08-31 — the "this is the remaining credible way to get there" line above turned
> out to be wrong, and you asked us to say so plainly.** We measured it three separate ways and the
> slope-and-jump shortcut does **not** get us to your speed target — it costs about four times as much
> per try as the old nudge-and-recheck, so with fewer-but-costlier tries it's a wash at best. What
> *actually* eats the time on the big analysis is copying the 5,000-unit rent roll on every rent try
> (about three-quarters of the slow row) and Python's routine memory cleanup (about another third) —
> neither of which the slope math touches. **Your call: keep building all of it, just tell the story
> straight.** The real path to your speed target is tuning that memory cleanup and removing the
> unnecessary rent-roll copy — not the slope math. The slope math earns its place for a different
> reason: it's what makes the "bundles of changes" feature (Half B) possible and trustworthy, by telling
> the program *which direction* to try instead of *how far* — so Half B, not raw speed, is the real
> point of this mission now.

## What are the goals?

- Replace most of the trial-and-error with a **compute-the-slope-and-jump** method, so each lever needs
  far fewer re-runs (roughly twenty down to three or four).
- **Never** trust the shortcut blindly: every number we print — single levers AND bundles — is confirmed
  by one real, full re-run first. If the shortcut and the real run ever disagree, we keep the answer the
  honest slow way already gives.
- Measure the speed honestly against your target and **report the real number**, even if it lands just
  short — a measured near-miss is a result, not a fudge.
- Add a **"bundles of changes"** section next to the existing single-lever list, so you can see every
  realistic combination that survives, not just the one cheapest lever — with the overall cheapest one
  labelled, not picked by a separate ranking.
- Make sure a bundle is only ever suggested if it genuinely **makes sense** — including not suggesting
  two changes that are each fine on their own but silly together — and that the bundles shown are
  **genuinely different routes** by construction (one per lever combination), not variations on one idea.
- Fix a few small, unrelated rough edges along the way (see below).

## The one tradeoff, in plain terms — please read this part

The slow trial-and-error method could promise the report's numbers were **bit-for-bit identical** every
time. The fast slope-based method **cannot** — by its nature it rearranges the arithmetic slightly, so
answers can differ in the last few decimal places. So before we build anything fast, we change one rule:
instead of "no number may change at all, ever," the rule becomes **"no number may change by more than a
vanishingly small amount"** — nine-nines small, i.e. a difference in about the ninth decimal place.

Two guardrails make that safe, and both are non-negotiable:

1. **It is still tight enough to catch real mistakes.** We calibrated it against a synthetic test bug
   (not one we've actually shipped and caught before — a rounding-bug shape we deliberately injected to
   test the rule) that shows up as a difference around the *eighth* decimal place. The new rule is set
   one notch tighter than that, so it would still catch a bug that size. A looser rule (say, sixth
   decimal) would let it through — that is exactly why we picked nine-nines and not something more
   relaxed. (Corrected 2026-08-31: an earlier draft of this document implied this was a bug we'd
   previously actually caught in production; it's a designed test case, not a war story.)
2. **We always measure drift against the very first correct answer, never the last one.** This matters
   more than it sounds. If each change were measured only against the previous version, ten tiny changes
   could each look fine while the total quietly crept far from the truth. By always comparing back to the
   original, the budget can never be spent twice — drift cannot ratchet.

And if any future change gets anywhere *near* that tiny limit, it does not just quietly pass — it has to
come with a **written explanation** of why the drift is legitimate. This tolerance rule is built and
locked in **first**, before any of the fast math, precisely because it is what makes the fast math
reviewable.

## What will we have when it's done that we don't now?

- **Before:** finding what closes a near-miss takes ~10–20 full re-runs per lever.
  **After:** it takes ~3–4, then one confirming re-run — the answer is the same, the wait is shorter.
- **Before:** the report only ever offers single-lever fixes ("change *one* of these").
  **After:** it *also* offers every realistic **bundle** of changes that survives a sanity check (up to
  eleven), each one checked by the real calculator, with the cheapest overall one labelled — for when
  you can move more than one lever.
- **Before:** the big-portfolio benchmark runs slower than your target.
  **After:** a measured, honestly-reported time against that target (faster; we will tell you exactly
  how much, and whether it fully meets the goal).
- **Before:** the program will accept a **negative purchase price** without complaint.
  **After:** money fields refuse nonsense values with a clean message.
- **Before:** the forecast horizon is capped at 50 years; real 99-year leases don't fit.
  **After:** the cap is raised to 100.
- **Before:** asking for an out-of-range horizon dumps an ugly technical error with the useful part
  buried at the bottom.
  **After:** one clean, readable line telling you what went wrong.

## What it deliberately will NOT do (left open on purpose)

- It will **not** change any verdict, pass/fail line, or the meaning of any number. The report says the
  same things; it just computes the recourse answers faster.
- It will **not** replace the real model with a shortcut. The real, full re-run stays the source of
  truth and the final check on every number shown.
- It will **not** pull in a big external math library or anything from the internet, unless measuring
  proves it is worth it and you approve.
- It will **not** use any "machine-learning" or fancy dimension-reducing tricks to pick the bundles.
  We deliberately chose plain, well-understood optimization math on your own real model — because we
  own the exact calculator, those classical methods are the right and trustworthy tool, and they keep
  every suggestion in terms of the *real* levers you understand (rent, price, rate, costs), never some
  blended abstract quantity.
- The bundles feature is built **only after** the fast math is proven correct at a checkpoint. If the
  fast math doesn't pan out, the bundles are set aside for later rather than shipped on shaky ground.
- It will **not** start the bigger "represent money in exact whole cents" project. That is a real,
  separate follow-on mission — named and parked, not started here.

## How you'll know it worked

Follow `docs/manual testing/MISSION_5_MANUAL_TESTING.md`. It walks you through: confirming the new
tolerance rule still catches the calibration bug and can't let drift creep past the original answer;
checking that a fast recourse answer matches what a real full re-run says on a near-miss deal; seeing the
number of tries drop; timing the big 5,000-unit / 100-year run against your target (honestly — the real
speed-up is expected to come from the memory-cleanup tuning and the rent-roll fix, not the slope math,
so don't be surprised if the slope math alone doesn't move this number much); **checking the new
"bundles" section — that it appears, that every bundle shown really does flip the verdict when the real
calculator re-runs it, that a silly combination is refused, that the bundles shown are genuinely
different routes, that the cheapest one is labelled rather than picked by a hidden ranking, and that the
same deal always produces the same bundles**; and checking the small fixes (negative price refused,
100-year horizon accepted, a clean message instead of an ugly error). Every step has a clear yes/no so
nothing can pretend to be finished when it isn't.
