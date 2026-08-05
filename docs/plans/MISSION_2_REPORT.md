# Mission 2 — what I did, what I found, and what I'm unsure about

**Branch:** `mission/2-wiring-gaps` · **merged locally into `main` as `8b2acf8`** · **not pushed**
**Written for Roger, 2026-08-05.** Plain English. Jargon gets defined the first time it appears.

---

## The one-paragraph version

The tool had features that were documented but that nothing actually ran, and it had numbers on the
page that came from somewhere other than the calculator. I fixed both. Along the way the mission's
own idea turned on me twice — I wired up dead code without checking whether what it printed was
*true*, and I wrote a sentence claiming the tool had checked for something it cannot check. Three
independent reviewers caught both. The suite went from 310 tests to 630, and the part of the code
that does money math changed by exactly five lines, which is what you approved and nothing more.

---

## First, the words I'm going to use

You asked me to define jargon rather than bury it. Here are the terms that carry weight in this
report.

| Term | What it means here |
| --- | --- |
| **Deterministic** | Same inputs always produce the same output. No randomness, no model guessing. Your money math is deterministic, and this mission kept it that way. |
| **The engine** | `src/core/finance/` — the only place allowed to calculate money. Everything else may *describe* numbers, never *invent* them. |
| **Reachable** | Some code path actually calls it when you run the tool. Unreachable code can be perfect and still do nothing. |
| **RED on revert** | A test that I proved fails when I undo the fix. If a test passes both with and without the fix, it proves nothing — it's decoration. |
| **Regression** | Something that used to work and now doesn't. |
| **Cap rate** | Yearly net income ÷ purchase price. A rough "what does this property yield" number. |
| **DSCR** | Debt Service Coverage Ratio: net income ÷ mortgage payments. Below 1.0 means the property doesn't cover its own loan. |
| **Cash-on-cash (CoC)** | First-year cash flow ÷ cash you actually put in. What your money earned, ignoring appreciation. |
| **bps** | "Basis points." 100 bps = 1%. So "150 bps" and "1.50%" are the same thing — and the report currently uses both, which is one of the things still on the list. |
| **Predicate** | A small function that answers yes/no. One appears repeatedly below because it decides whether a photo-derived label is allowed to affect your numbers. |
| **Schema** | The definition of what fields exist and what type they are. Changing one can break saved files, so we only *add*, never rename or remove. |
| **Gate** | A checkpoint where reviewers can block the work. |
| **VETO** | A reviewer with authority to stop the mission until something is fixed. |

---

## Part 1 — What I set out to do

Close the gap between what the documentation promised and what the code actually did. Specifically:
features described in the README that no code path reached, numbers the engine computed that never
made it onto the page, and modules sitting in the repo that nothing called.

---

## Part 2 — The issues I found, and what I did about each

### 2.1 Your cap-rate drift setting did nothing to the report

**The problem.** You can set a cap rate that drifts over time — say 0.03, meaning the cap rate
worsens each year. The engine honoured it correctly, moving from 7.44% up to 34.44% across ten
years. The report printed **7.44% on every single row**. So the report showed a flat line where your
own setting said the picture changes dramatically.

**Why nobody noticed.** There was a test meant to catch exactly this. It asserted
`"6.35%" not in table or "6.40%" in table` against a fixture whose actual value was 7.44%. Both
halves were true no matter what the code did. It could never fail.

**The fix.** The report now reads the engine's per-year values. 41 distinct numbers where there used
to be one, repeated.

**What I assumed:** that you want the report to show what the engine computed, not a simplification
of it. I think that's obvious, but I'm naming it because it's an assumption.

### 2.2 The report showed negative "available equity"

It printed things like *-$52,558.10* of available equity. Equity below zero isn't a number you can
draw against — it's just "none." The report was recomputing this itself instead of reading the
engine's already-floored value. Now it reads the engine, and shows `$0.00` with the loan-to-value
percentage beside it so you can see how far above the line the loan still sits.

### 2.3 A blank grey image named `mold_basement.jpg` became a mould finding

**This is the one I'd flag hardest if I were you.**

The tool read file *names* and turned them into findings. A completely blank grey image called
`mold_basement.jpg` produced `mold_suspected` at **0.90 confidence**, with no evidence attached, and
stamped as though a computer-vision detector had seen it in the pixels. It hadn't. Nothing had
looked at that image at all.

**Your call (Option D) is what fixed it.** You said: keep filename signals, but confirm them with
real CV — 70% detector confidence, 30% filename corroboration. That became a three-way rule:

| Can a detector look for this label? | Did it report it? | Result |
| --- | --- | --- |
| Yes | Yes | **Confirmed** — scored `0.7 × detector + 0.3` |
| Yes | No | **Contested** — something looked and disagreed. Scored 0.30, but kept out of your numbers |
| No | n/a | **Unconfirmed** — nothing could check. **No confidence score at all** |

**Why the third row gets no number.** A 0.30 would be a measurement of nothing. When a detector
covers a label and stays quiet, 0.30 means "something looked and disagreed" — weak but earned. When
nothing can look, the same number asserts a degree of belief about a question nobody asked. The
first is honestly weak; the second is fabricated precision.

**Two real money leaks closed.** Contested filename claims were moving **$1,105.80** of first-year
cash flow. Now $0.00.

**The subtle part that took three rounds.** The engine picks its rules by *membership* in a list —
"is `parking` in the amenities list?" — and never looks at the confidence score. So a 0.30 claim in
that list moves exactly as much money as a 1.00 claim. The score was never protecting anything.

### 2.4 The same defect survived on a second code path

There were two producers building the same kind of data. I fixed one. The other still shipped
contested claims into the money-reading lists, and moved no money **only because of a naming
mismatch** — the engine matches the literal word `"parking"` while that path emits `"parking_garage"`.
Safe by accident, not by design. Close that unrelated naming gap and it would have started moving
dollars immediately. Both paths now use the same single yes/no function rather than each keeping
their own copy of the rule.

### 2.5 Dead code — but I looked into *why* it existed first

You asked me to find out why these modules were created before deleting anything. That was the right
instruction and it changed the answer.

- `strategist.py` looked like old legacy code. It wasn't. It was the **newer, unfinished half** of a
  migration — and on one guardrail it was *more* correct than the live code. Deleting it blindly
  would have thrown away the better logic.
- `photo_tagger.py` and `agents/listing_ingest.py` were the opposite migration, abandoned when
  another file reached past them directly.

**Your architecture direction settled it:** *an agent exists only where a model might one day enter;
everything deterministic is called directly.* The genuinely dead ones were deleted; the useful logic
was moved, not lost.

### 2.6 The cash-on-cash floor — you overrode my recommendation, and I want to be straight about that

I recommended skipping it. Measured across 21,600 simulated deals, it never catches a deal the
existing rules miss — zero times. Its entire effect is escalating already-flagged deals from
"conditional" to "decline."

You said add it. It's added, at 3%. **I still think the measurement stands**, and it's on the record
so a future decision has the data. It's your tool and your risk appetite; the number is now visible
and explained in the report rather than hidden in code.

### 2.7 A stale cache was serving results from before the fix

Fixing behaviour doesn't help if a cached answer from yesterday gets served instead. The cache now
carries a version marker plus a fingerprint of what the detectors can do, so a behaviour change
invalidates it automatically.

---

## Part 3 — Where the mission's own idea turned on me

Two things I got wrong. Both were caught by reviewers, not by me.

### 3.1 I wired dead code without checking whether it told the truth

I connected five unused modules to the tool. I verified they were *called*, that documentation paths
resolved, and that no existing output was lost. I never checked **what they printed**.

Three of them printed numbers the engine never computed:

- The "what-if" scenario model was, in its own code comments, a **"toy."** Two invented coefficients
  (`0.4` and `1.2` per $1,000 of price), no mortgage amortization anywhere. A reviewer ran your real
  engine on the same inputs: **the page understated the engine by 25×**, and showed the downside and
  upside as mirror images when amortization says they aren't.
- Its baseline read a field that **does not exist on that object** — the type has six fields and
  that isn't one of them. So it silently fell back to a 25% down payment against your real 5%,
  printing **$99,975 of cash at close against an actual $19,995**, and labelling that fiction "base."
- Its own code returned a note saying *"Approximate scenario; does not re-run engine."* The renderer
  dropped that note before it reached the page.
- A short-term-rental multiplier of 1.5× printed for **every region on earth**, gated by a function
  whose entire body was `return True`, under a comment saying "replace with real policy lookups
  later." Many New Brunswick municipalities regulate short-term rentals.

**Resolution: deleted, not caveated.** Wire-first was never "find a home for every orphan." A module
that can only be connected by printing a number the engine didn't compute is un-connectable, and the
plan's own fallback clause covers exactly that. The CHANGELOG claim was **retracted rather than made
true** — correcting a false claim is cheaper and more honest than building a toy to justify it.

**On your "flag, don't remove" instruction** — I checked this against the guardian, because deleting
felt like it might conflict with what you told me. Its ruling:

> That instruction is about not withholding a **finding about the property** from the investor. It
> is not a licence to keep a calculator that emits wrong numbers. Deleting a broken sensitivity
> model removes no finding.

I agree, and I'm recording it here so nobody later cites your words to justify keeping something broken.

### 3.2 I wrote the exact defect this mission exists to prevent — backwards

The report printed:

> **Parking (from photos):** none · no EV charging observed

No detector in the entire codebase can look for EV chargers. That sentence was a *default value*
printed as a *negative sighting*. I spent this mission stopping a file name from claiming a thing
**exists**; I left the report claiming a thing **doesn't**, on identical non-evidence.

It now reads:

> **Parking (from photos):** not checked — no photo check in this run looks for parking · EV
> charging not checked — no photo check in this run looks for chargers

Same for quality scores, which used to print `0.00` where "not measured" was the truth.

### 3.3 Three times I stated something stronger than the code did

Worth listing, because the pattern matters more than the individual slips:

1. **A safety check I described as "fails safe" did the opposite.** I wrote that an unrecognised
   input would default to the cautious branch. It defaulted to *trusting* it. The check was a list
   of known-bad values, so anything not on the list was treated as a genuine detector finding. **I
   had repeated this claim in three places** — a code comment, the tracker, and a commit message —
   and never once tested it. It's now an allow-list (only two values mean "a detector saw this";
   everything else is withheld), pinned by a test that feeds it a value that doesn't exist.
2. **A commit message of mine said a rule now covered both code paths.** It covered one.
3. **I claimed the graph tool "lied"** after checking against today's code rather than against the
   commit the graph was built from. You caught that one directly.

**The lesson, stated plainly:** a claim repeated across three documents is not more true than a claim
written once. Only a test makes it true. Every one of these is now tested.

---

## Part 4 — What the reviewers said

Three independent reviewers, run separately so they couldn't anchor on each other.

| Reviewer | Verdict | Caught |
| --- | --- | --- |
| **Founder-proxy** (speaks for your priorities) | Ship with conditions | The fabricated what-if numbers |
| **Principles guardian** (holds VETO) | **VETO**, later lifted | The EV-charging inversion; a README example that crashed |
| **Staff code reviewer** | Request changes, later **approved** | The fail-safe check that wasn't; two code paths disagreeing |

Then the fix introduced a *new* blocker, which the re-review caught: the capability check crashed on
`onnx` — the exact provider it was written for. `onnx` is a valid provider name, so it passed the
first guard, but it has no default registration, so generating a report from an `onnx` run exited
with a raw error trace. Twelve tests covered `onnx` and all twelve missed it, because every one of
them registered a provider first. The untested shape was the only shape that happens in production.

**Final state: VETO lifted, code review approved.**

---

## Part 5 — Sources and where the reasoning came from

- **Your own decisions**, quoted in the tracker as you made them: the deterministic-decision rule,
  two report sections rather than two documents, Option D's 70/30 weighting, the cash-on-cash floor,
  the agent-only-where-a-model-might-go architecture, and "flag, don't remove."
- **The project's own engine**, used as ground truth to prove the what-if model wrong. Not an
  opinion — I ran your calculator on the same inputs and compared.
- **Measurement over intuition** on the threshold questions: 21,600 simulated deals, not a guess.
- **The repo's own history**, to find out why dead modules existed before deleting them.
- **"Actionable recourse" / counterfactual explanations** — the established research field matching
  your "what would have to change?" idea. Recorded as backlog #6, not built.
- **Named reviewers over self-assessment.** I did not approve my own work at any gate.

---

## Part 6 — Assumptions I made, stated so you can overrule them

1. **The report should show what the engine computed**, not a simplified version. (Drove 2.1, 2.2.)
2. **A number printed without a caveat will be read as a measurement.** This drove the deletions
   rather than adding disclaimers — a caveat manages a wrong number, it doesn't fix it.
3. **"Nothing looked" and "something looked and found none" are different facts** and the reader
   deserves to know which. This is the whole spine of the CV work.
4. **Deleting a broken calculator doesn't violate "flag, don't remove."** Checked with the guardian
   rather than assumed. If you disagree, the modules are recoverable from git history.
5. **Silence about an unchecked thing beats a confident negative.** Applied to parking/EV charging.
6. **A follow-on mission is the right home for report *readability*** — plain wording, glossary gaps
   — as opposed to report *honesty*, which is a Mission 2 blocker. This is a judgement call and the
   reviewers agreed, but it's a call.

---

## Part 7 — What I deliberately did not do

| Item | Why |
| --- | --- |
| **Remove `RegionalIncomeTable.turnover_cost`** | It holds a made-up value (`median rent × 0.5`). It now reaches no reader — verified in both the JSON and the Markdown — and its description says plainly that it is not a measurement. But **removing a required field is a breaking change**, and that's your call, not an agent's. |
| **The 3% cash-on-cash and decline-shortcut threshold values** | Measured, recommendations written, **not applied**. Verdict-moving decisions are yours. |
| **A fourth decorative test assertion** | Found two lines below one I'd just fixed, late in a long session. Slipping in an unverified tightening at a gate is exactly how a test starts passing for the wrong reason — the failure mode this mission spent five rewrites on. Recorded, not patched. |
| **Report plain-language pass** | Raw identifiers like `mold_suspected` still shown to readers; `bps` never defined; "cap-rate spread" and "seasoning" unglossed. **Prioritise `bps`** — it appears in a lever the report tells you to act on. |
| **Push to remote** | Your explicit instruction. |

---

## Part 8 — Where things stand

```
630 tests (mission start: 310) · coverage 86.09% · three consecutive clean runs
ruff clean · mypy --strict clean · python main.py byte-identical run to run
src/core/finance/ diff = exactly the 5-line cap-rate-floor hunk you approved, nothing else
src/schemas/models.py = additive only; no field renamed, retyped, or removed
Merged locally to main as 8b2acf8 (--no-ff). NOT PUSHED.
```

**One honest caveat about this document:** the suite count line in the tracker has gone stale every
single time it has been touched — four times, including once inside the very message reporting the
fix for the previous staleness. It now carries a commit SHA so a stale number is visibly attached to
a stale tree. The real fix is to derive it from a build artifact instead of typing it, and that's
backlog. A figure that has to be re-typed is a claim with no test behind it.

## What I'd like from you

1. **The `turnover_cost` field** — remove it (breaking change) or leave it dormant?
2. **The threshold values** in 3.1c — measured and waiting on you.
3. **The push to remote** — 61 commits sit on local `main`, unpushed.
4. Whether the report-readability work becomes Mission 3, or waits.
