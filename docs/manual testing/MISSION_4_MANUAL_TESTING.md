# Mission 4 — Actionable Recourse ("What would have to change?") — Manual Testing Handoff

_Author: `staff-report-experience-designer` · Rewritten & spot-run 2026-08-29 against branch
`mission/4-actionable-recourse`, working tree on top of `main @ bfdf565` (Mission 3's validated base).
Every command below was executed by hand, once, on this tree, before this doc was handed to you._

> ## Read this first — this doc replaces an out-of-date acceptance plan
>
> The previous version of this file was written as a **pre-build acceptance plan** ("every case
> below is expected to FAIL right now"). That premise is gone: the feature is built, the sample
> deal exists, the engine changes are in, and the whole suite is green. This rewrite verifies the
> **actual, shipped behaviour** — every command below was run on this machine, and the "Expected
> result" blocks quote what that run actually printed, not a prediction.
>
> **This doc has NOT yet been through Roger's own hand-validation pass.** Every "Status" box and
> the document-level box at the top are left unchecked on purpose — that is your gate, not mine.
> "Actual result observed" fields are left blank for you to fill in as you run each command
> yourself; the "Expected result" blocks are what I observed and are what yours should match.

> **Verify the tree before trusting anything below:**
> `git branch --show-current` → `mission/4-actionable-recourse` (or, once merged, `main` with the
> merge commit in `git log`). If neither, you may be on the wrong tree.

---

**Overall validation:** ☐ NOT VALIDATED ☑ VALIDATED (Roger, 2026-08-31) ☐ VALIDATED WITH ISSUES

> **How this was signed off, for the record.** Roger ran every case himself — Cases 4, 5 and 8 on
> 2026-08-30, and Cases 1, 2, 3, 6, 7 and 9 re-run on 2026-08-31 after the Case 7 fix, from a clean
> `/tmp/m4` with both config variables verified present. On 2026-08-31 he reviewed the results and
> authorized Claude to mark the boxes; the ticks above and below were entered by Claude on that
> explicit instruction, not on Claude's own judgement. **Marked VALIDATED rather than VALIDATED
> WITH ISSUES** because all nine cases pass on Roger's own runs — the one defect found during the
> pass (Case 7) was fixed and re-validated within it. Flip this to VALIDATED WITH ISSUES if you'd
> rather the found-and-fixed defect show in the header as well as the log.
>
> **One decision rides on this sign-off:** Case 7's pass criterion includes accepting the
> `BUDGET_MS` re-baseline from **120 ms → 250 ms**. Marking Case 7 PASS records that acceptance.
> That is a threshold change, not a measurement — if you did not intend to ratify it, Case 7 goes
> back to ☐ and the loop needs optimising instead (see that case for where).
**Blocking issues found:** One, now fixed — **Case 7's benchmark did not measure the production
loop and reported PASS against a budget the real loop misses.** See the validation log below and
Case 7's own observation field. The recourse feature itself (Cases 1–6, 8) is sound.

### Validation log — 2026-08-30 pass

Roger ran all nine cases; Claude then verified the transcript against the code and re-ran the
parts that turned out to be void. Two distinct outcomes, kept separate on purpose:

1. **Cases 1, 2, 3, 6 were void as first run** — not failures, non-runs. Prerequisite step 6 was
   skipped, so `$NEARMISS_CFG`/`$DECLINE_CFG` were empty, every `--config $VAR` invocation died at
   `argparse`, and the greps read artifacts left behind by the 2026-08-29 authoring run
   (`/tmp/m4/nearmiss.md`, `far_decline.md`, `det_a.md`, `det_b.md`, all timestamped `Aug 29
   22:19–22:20`). Case 6's `IDENTICAL` was therefore vacuous: it compared two files that neither
   run had touched. All four were **re-run correctly and all four pass** — and the regenerated
   `nearmiss.md` is byte-identical to the 2026-08-29 artifact, which is a stronger determinism
   result than Case 6 was designed to produce. Prerequisites 5 and 7 above were rewritten so this
   trap cannot recur.
2. **Case 7 was a real defect**, described in full in its own section below, and has been fixed by
   rewriting `tests/perf/bench_finance_engine.py`. **The budget re-baseline in that fix (120 ms →
   250 ms) is a threshold change and needs Roger's explicit ratification** — it is the one item in
   this document that is not merely a measurement.

Cases 4, 5, 8 and 9 were valid exactly as Roger ran them.

---

## What this mission is, precisely (read before testing)

The program keeps its BUY / CONDITIONAL / DECLINE verdict, unchanged. For a deal that is
**genuinely close** — a CONDITIONAL, or a DECLINE failing at most 3 of the (up to) seven live
guardrails — the report gains a **"What would have to change?"** section, placed immediately
adjacent to the Investment Thesis: for each currently-failing guardrail, one or more single-lever
changes (rent/unit/month, purchase price, interest rate, annual opex) that **would** close it,
holding every other input fixed. **Every number comes from a real re-run of the engine on a
perturbed copy of your inputs — never from inverting a guardrail formula.** When several
guardrails fail, the cheapest single fix leads with a bold, adjacent note about what still doesn't
clear. Implausible levers are flagged with a reason, never hidden. When nothing realistic closes a
gap, the report says so plainly.

**Scope note, honestly stated:** the mission's original zero-`finance-core`-diff constraint was
**waived by Roger mid-mission** (charter amendment, `docs/plans/MISSION_4_SPRINT_TRACKER.md` §"CHARTER
AMENDMENT") after a portfolio-scale perf review found the recourse re-run loop would crash at
5,000 units / 100 years. `src/core/finance/engine.py`, `irr.py`, and `amortization.py` were
rewritten for performance (surgical-copy + loop-invariant hoist) and correctness (a solver fix for
a real crash). This doc covers both strands — the report feature and the engine work it forced —
because both shipped together and both need your eyes.

---

## Prerequisites (do this once)

1. `cd /home/rtokime/projects/Personal/ai-real-estate-deal-analyzer`
2. `source /home/rtokime/anaconda3/etc/profile.d/conda.sh && conda activate airedeal`
   **Do not use `~/miniconda3` — it does not exist on this machine and some shells silently fall
   back to a different, wrong Python. Use the `anaconda3` path above, exactly.**
3. `which python` → must print `/home/rtokime/anaconda3/envs/airedeal/bin/python`. If it prints
   anything else, stop and fix your shell before running anything below.
4. `git branch --show-current` → `mission/4-actionable-recourse` (or `main`, once merged).
5. **Start from an EMPTY output directory** — `rm -rf /tmp/m4 && mkdir -p /tmp/m4 && export OUT=/tmp/m4`.
   Not optional, and not housekeeping. Several cases below `grep` a report file that a previous
   command was supposed to have just written. If that command fails, a **stale file from an earlier
   session is still sitting there**, and the `grep` happily reads it — the case then appears to pass
   while testing nothing. With an empty directory a failed run makes the next `grep` error loudly
   (`No such file or directory`) instead. This exact trap voided four cases in the 2026-08-30
   validation pass; see the validation log at the top of this document.
6. Confirm the mission's new sample deal exists:
   `ls data/sample_listings/82_champlain_dieppe/` → `finance.json  inputs.json  listing.txt  README.md`.
   `export NEARMISS_CFG=data/sample_listings/82_champlain_dieppe/inputs.json` — this is the deal
   every case below uses to show the feature. **It is a DECLINE, not a CONDITIONAL** — it fails 3 of
   the 7 live guardrails, which is exactly the boundary the "genuinely close" gate accepts
   (`GENUINELY_CLOSE_MAX_FAILS = 3`, `src/market/recourse.py:143`), so it grows the full section.
   `export DECLINE_CFG=data/sample_listings/36_kelly_moncton/inputs.json` — a DECLINE that fails 4
   guardrails, one past the gate, used below to show the section correctly staying **absent** for a
   deal that is not close.

7. **Prove both variables actually resolved before running anything.** An unset variable does not
   fail loudly here — `--config $NEARMISS_CFG` with an empty value makes `argparse` exit with
   `error: argument --config: expected one argument`, and because every case pipes through
   `grep -iE "verdict"`, **that error is swallowed and you see nothing at all**. A case that prints
   no `Thesis verdict:` line has not run. Check first:
   ```bash
   ls -l "$NEARMISS_CFG" "$DECLINE_CFG"   # both must resolve to real files
   ```

The CLIs are: `python main.py` (the deterministic default pipeline that writes the report),
`deal-report`, `deal-advisor`, and `ingest-listing`. All resolve on `PATH` after
`conda activate airedeal`. **Only `python main.py`'s deterministic and CrewAI orchestration paths
compute recourse** (`src/orchestrators/crew.py:build_recourse`, called from `main.py` and
`src/orchestrators/crewai_runner.py`). `deal-report` and `deal-advisor` (`src/cli/report_cli.py`,
`src/cli/advisor_cli.py`) do not import or call the recourse module at all — this is a structural
fact, the same shape as Mission 3's ONNX-flags/`main.py` boundary, not an oversight.

---
---

## Case 1 — The near-miss deal grows a "What would have to change?" section, adjacent to the verdict

**Command**
```bash
rm -rf .cache/cv
python main.py --config $NEARMISS_CFG --horizon 10 --out $OUT/nearmiss.md 2>&1 | grep -iE "verdict"
grep -n "^## " $OUT/nearmiss.md
```

**Expected result:**
```
Thesis verdict: DECLINE
```
and the section-heading list shows `## Investment Thesis` immediately followed by
`## What would have to change?`, with `## 10-Year Pro Forma (Summary)` only after that — i.e. the
recourse section sits directly between the verdict and the tables, not appended ~115 lines later
after Warnings.

**What to look at in the section itself** (`sed -n '85,150p' $OUT/nearmiss.md`):
- The honesty preamble: `> **About this section.** Each gap below is the smallest single change
  to ONE input that WOULD close it — a real re-run of the underwriting model...`
- **Cheapest single fix leads, bold, and the "other gaps remain" line is bold and on the very next
  line** — not below the fold, not omitted:
  ```
  **Cheapest single fix:** **$10.00/unit/month rent increase** → $1,422.50/unit/month (0.71% above current) — clears the Cash-on-cash (Y1) bar of 3.00%.

  **Other gaps remain: DSCR (Y1), Cap-rate spread would still not clear their own bars.**
  ```
- A **flagged implausible lever that keeps its numbers and carries a reason**, under the
  Cap-rate spread gap:
  ```
  - Flagged — **$190.00/unit/month rent increase** → $1,602.50/unit/month (13.45% above current) — clears the Cap-rate spread bar of 1.50%. Also closes: DSCR (Y1), Cash-on-cash (Y1).
    _a rent increase of 13.5% is larger than the 10% this project treats as a realistic single ask._
  ```
  The number ($190.00, 13.45%) is not removed or hedged away — only annotated.
- The footer, `**How these numbers were produced**`, with its thresholds spelled out in numbers:
  search ranges per lever (rent 0–100%, price 0 to −40%, rate 0 to −300 bps floored at 0%, opex 0
  to −40%), rounding-away-from-zero + re-confirm discipline, and the realism thresholds (rent
  >10%, price >15%, opex >20%, rate >100 bps, or a resulting cap rate outside 3.00%–12.00%).

**Pass/fail criterion:** Does the section exist, sit immediately after Investment Thesis, and
contain all four things above (preamble, bold cheapest-fix + adjacent "other gaps remain", a
flagged-but-numbered lever, and a footer with numeric thresholds)? Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-08-31
**Actual result observed:** _Roger, 2026-08-30; void first run, re-run by Claude the same day._
**First attempt VOID, not failed** — `$NEARMISS_CFG` was unset (prereq 6 skipped), so `main.py`
exited at `argparse` and the greps read the stale 2026-08-29 `/tmp/m4/nearmiss.md`. The tell was in
the transcript: **no `Thesis verdict:` line printed at all**. Re-run with the variable set:
`Thesis verdict: DECLINE`; headings `## Investment Thesis` (76) → `## What would have to change?`
(97) → `## 10-Year Pro Forma (Summary)` (145), i.e. adjacent to the verdict, not after Warnings.
All four required elements present: the honesty preamble; `**Cheapest single fix:** **$10.00/unit/month
rent increase**` with the bold "Other gaps remain: DSCR (Y1), Cap-rate spread" line immediately
after it; the flagged `$190.00/unit/month` / 13.45% row keeping its exact numbers with its reason;
and the numeric-threshold footer. The regenerated file is **byte-identical** to the 2026-08-29
artifact. **Roger re-ran this himself on 2026-08-31**, from a clean `/tmp/m4` with both config
variables verified present: identical output, same heading line numbers (76 → 97 → 145), same lever
numbers throughout. **PASS, on Roger's own run.**

---

## Case 2 — Roger's three Gate D decisions, each as something to look AT, not an abstraction

**Decision 1 — a DECLINE only gets a section if it's genuinely close; if close, even a "nothing
closes this" answer is shown, never silently discarded.**

```bash
# far DECLINE (4 of 7 guardrails fail) -- gate never opens, section absent
python main.py --config $DECLINE_CFG --horizon 10 --out $OUT/far_decline.md 2>&1 | grep -iE "verdict"
grep -c "What would have to change" $OUT/far_decline.md
```
**Expected:** `Thesis verdict: DECLINE`, then `0` (no section at all — this deal fails DSCR, spread,
CoC, and Year-1 cash flow simultaneously, one past the `GENUINELY_CLOSE_MAX_FAILS = 3` gate).

For the "found but discarded" half of this decision — Roger's Gate D ruling was that a computed
honest-null answer must never evaporate before reaching the report — the automated suite is the
place to see it proven, since none of the committed sample deals produces a full-analysis
honest-null naturally:
```bash
python -m pytest tests/unit/test_recourse.py::test_honest_null_analysis_is_still_fully_populated_not_blanked -v --no-cov
```
**Expected:** 1 passed. Open the test — it builds an all-null `RecourseAnalysis` and asserts every
field is still populated (never `None`), which is the exact guarantee the guardian's Gate D ruling
required.

You can see the **per-lever** (not whole-deal) honest-null treatment for real, in `$NEARMISS_CFG`'s
own report — one lever, searched, found nothing, said so plainly, right next to the ones that did:
```bash
grep -A1 "does not close this gap" $OUT/nearmiss.md
```
**Expected:**
```
- _An opex cut alone, up to the largest change checked, does not close this gap — another lever, or a combination, might._
```

**Decision 2 — placement is adjacent to the Investment Thesis, not appended after Warnings.**
Already checked in Case 1's heading list. Confirm the reasoning is in the code, not just the
output:
```bash
grep -n "immediately adjacent to the Investment Thesis" src/core/reports/generator.py
```
**Expected:** a hit around line 1839, in the comment directly above the `if recourse is not None:`
branch in `generate_report`, naming this exact placement decision and why (never ~115 lines below
the verdict, separated by five tables).

**Decision 3 — the old heuristic lever block is now visibly marked qualitative.**
```bash
grep -n "Suggested Levers" $OUT/nearmiss.md
```
**Expected:**
```
- **Suggested Levers** _(qualitative — pattern-matched from the numbers above, not verified by re-running the model)._
```
This heading is unconditional — it appears on **every** report that has any `thesis.levers`,
including the default demo deal (Case 5), whether or not a computed recourse section also renders.

**Pass/fail criterion:** Do all three decisions check out as described? Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-08-31
**Actual result observed:** _Roger, 2026-08-30; void first run, re-run by Claude the same day._
Same staleness as Case 1 (`$DECLINE_CFG` unset, no verdict line printed). On re-run all three
decisions hold: `Thesis verdict: DECLINE` then `0` recourse sections for the far-decline deal;
`test_honest_null_analysis_is_still_fully_populated_not_blanked` **1 passed** (this half was always
valid — it takes no config); the per-lever honest-null line present in `nearmiss.md`; the placement
comment found at `generator.py:1788` and `:1839`; and the `Suggested Levers` qualitative marker
present. **Independently corroborated:** the default bundle *is* `36_kelly_moncton`, so
`far_decline.md` and Case 5's `def1.md` are the same content — Case 5's valid run confirms the
absent section without depending on the variable at all. **Roger re-ran this himself on
2026-08-31**: `Thesis verdict: DECLINE`, `0`, and the per-lever honest-null line present. **PASS,
on Roger's own run.** (The `test_honest_null_analysis_is_still_fully_populated_not_blanked` and
`generator.py` grep halves were already valid in the 2026-08-30 pass — neither takes a config —
and were not repeated.)

---

## Case 3 — Honest wording: "WOULD close it" — never "WILL", and the holding assumption is named

```bash
grep -iE "would|will|holding|holds every other" $OUT/nearmiss.md
```

**Expected result:** every occurrence of a certainty word is "**would** close it" (not "will"), and
the preamble states the holding assumption explicitly: *"every line holds every OTHER assumption
exactly as modeled, and the levers are not independent."* No line anywhere claims a change **will**
pass the deal.

**Pass/fail criterion:** No lever line says "will"; the holding-fixed caveat is present. Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-08-31
**Actual result observed:** _Roger, 2026-08-30; read a stale file, re-checked by Claude the same day._
Roger's grep hit the 2026-08-29 `nearmiss.md` (see Case 1). Re-checked against the freshly
regenerated, byte-identical file: **holds**. Every certainty word is "**would** close it"; the
preamble carries the holding assumption verbatim ("every line holds every OTHER assumption exactly
as modeled, and the levers are not independent"); the only `will` on the page is inside
"...never a number that would undershoot the bar", which is not a claim about the deal. No lever
line anywhere says a change **will** pass the deal. **Roger re-ran this himself on 2026-08-31**
against the freshly generated file: same 10 matches, every one of them "would". **PASS, on Roger's
own run.**

---

## Case 4 — THE ANTI-INVERSION CHECK: an independently-applied lever really does clear the guardrail

**Goal — the most convincing check in this document.** Take one printed lever ask from Case 1,
apply *exactly that number* to a copy of the inputs (not through the recourse module — by hand,
with `python`/`jq`), re-run the whole program, and confirm the guardrail clears. Then apply a
**smaller** change and confirm it does **not** clear — proving the printed number is a real
minimum, not an approximation.

**Step 1 — build two configs, one with the exact stated rent ask, one $5 short of it**
```bash
python - <<'PY'
import json
base = json.load(open("data/sample_listings/82_champlain_dieppe/inputs.json"))

def bump_rent(delta, path):
    cfg = json.loads(json.dumps(base))
    for u in cfg["inputs"]["income"]["units"]:
        u["rent_month"] += delta
    json.dump(cfg, open(path, "w"), indent=2)

bump_rent(10.0, "/tmp/m4/rent_exact.json")   # Case 1's stated cheapest-fix ask: +$10/unit/month
bump_rent(5.0, "/tmp/m4/rent_short.json")    # deliberately short of the stated ask
PY
```

**Step 2 — run both through the real program and read the guardrail line, independently**
```bash
python main.py --config /tmp/m4/rent_exact.json --horizon 10 --out /tmp/m4/rent_exact.md 2>&1 | grep -iE "verdict"
grep -E "^  - Cash-on-cash \(Y1\) is" /tmp/m4/rent_exact.md

python main.py --config /tmp/m4/rent_short.json --horizon 10 --out /tmp/m4/rent_short.md 2>&1 | grep -iE "verdict"
grep -E "^  - Cash-on-cash \(Y1\) is" /tmp/m4/rent_short.md
```
(the `^  - ` anchor picks out only the Investment Thesis rationale bullet — both reports still
grow their own recourse section, which repeats "Cash-on-cash (Y1)" many more times in the gap
breakdown; an unanchored grep will show all of them, which is fine to look at but is not what the
snippet below quotes.)

**Expected result:**
```
Thesis verdict: CONDITIONAL
  - Cash-on-cash (Y1) is healthy at 3.10% (≥ 3.00%).
Thesis verdict: DECLINE
  - Cash-on-cash (Y1) is weak at 2.94% (< 3.00%).
```
The exact stated ask (+$10/unit/month) clears the bar and the deal improves to CONDITIONAL; $5
less does not, and the deal stays a DECLINE. This was produced by re-running the whole program on
a hand-edited config — nothing here touched `src/market/recourse.py`. That the module's own printed
number is the true minimum, re-derived independently, is the whole point of the "re-run, never
invert" discipline.

**For the module's own, automated proof of the harder case (price-lever coupling via `coc`, where
naive algebra is provably wrong):**
```bash
python -m pytest tests/unit/test_recourse_nonindependence_trap.py -v --no-cov
```
**Expected:** all pass (6 tests, 0 failed — see Case 9 for the full battery). Read
`test_naive_formula_believes_the_wrong_coc_at_its_own_answer` and
`test_naive_vs_true_divergence_dwarfs_the_search_tolerance` — they assert that the naive
formula-inversion answer ($338,814.34) is **not** what the module reports, and that the true re-run
answer ($341,057.63) differs from the naive one by **$2,243.29**, over 20× the module's own $100
search tolerance — a trap that cannot be passed by accident.

**Pass/fail criterion:** Does the exact stated rent ask clear the guardrail on independent re-run,
while $5 less does not? Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-08-30
**Actual result observed:** _Roger, 2026-08-30 — **valid exactly as run**_ (this case uses
explicit paths, so the unset-variable trap never touched it). `+$10.00/unit/month` →
`Thesis verdict: CONDITIONAL`, `Cash-on-cash (Y1) is healthy at 3.10% (≥ 3.00%)`; `+$5.00` →
`Thesis verdict: DECLINE`, `Cash-on-cash (Y1) is weak at 2.94% (< 3.00%)`.
`tests/unit/test_recourse_nonindependence_trap.py` **6 passed**. This is the strongest evidence in
the document — it re-derives the module's printed minimum by hand, through the whole program,
without touching `src/market/recourse.py`, and it also retroactively corroborates the numbers in
Cases 1–3 that were read from the stale file.

---

## Case 5 — The default demo deal is unchanged, with one stated, deliberate exception

```bash
rm -rf .cache/cv
python main.py --out $OUT/def1.md
python main.py --out $OUT/def2.md
sha256sum $OUT/def1.md $OUT/def2.md
```

**Expected result:**
```
e6451c9af19e491a14495e9055501fff44034040552317325e539ab42b9f9ee9  /tmp/m4/def1.md
e6451c9af19e491a14495e9055501fff44034040552317325e539ab42b9f9ee9  /tmp/m4/def2.md
```
Both runs match each other and match this pinned sha.

**The one deliberate exception, stated plainly:** this sha is **not** the pre-Mission-4 sha
(`545e22b20b967b37c5b7ba20477f9df7c85f5b5a7c151f2e0d79b543d69d31f0`, Mission 3's pinned baseline).
The only difference is the "Suggested Levers" heading now carries the qualitative marker (Case 2,
decision 3) — this fires on **every** report with any `thesis.levers`, including the default demo
deal, which is a DECLINE not close enough to grow a recourse section of its own:
```bash
grep -n "What would have to change\|Suggested Levers" $OUT/def1.md
```
**Expected:** only the `Suggested Levers` line (with the qualitative marker), no `What would have
to change?` heading — confirming the default deal's byte-difference from pre-mission is that one
heading annotation, and nothing else.

**Pass/fail criterion:** Do both default runs match each other and the pinned post-mission sha
above, and is the only content difference from the pre-mission baseline the qualitative marker
line? Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-08-30
**Actual result observed:** _Roger, 2026-08-30 — **valid exactly as run**._ Both runs
`Thesis verdict: DECLINE`; `sha256sum` identical across the two and matching the pinned
post-mission sha `e6451c9af19e491a14495e9055501fff44034040552317325e539ab42b9f9ee9`.
`grep -n "What would have to change\|Suggested Levers"` returned only the `Suggested Levers` line
(with the qualitative marker) at line 95 — no recourse heading, as specified for a deal past the
gate.

---

## Case 6 — Determinism: the near-miss deal, run twice, is byte-identical

```bash
rm -rf .cache/cv
python main.py --config $NEARMISS_CFG --horizon 10 --out $OUT/det_a.md
rm -rf .cache/cv
python main.py --config $NEARMISS_CFG --horizon 10 --out $OUT/det_b.md
diff $OUT/det_a.md $OUT/det_b.md && echo "IDENTICAL"
```

**Expected result:** `IDENTICAL` — the recourse section (every lever number, every flag, every
null line) is byte-for-byte the same across runs.

**Pass/fail criterion:** Is the diff clean and `IDENTICAL` printed? Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-08-31
**Actual result observed:** _Roger, 2026-08-30; void first run, re-run by Claude the same day._
**First attempt VOID, and this one printed a false positive.** Both runs died at
`main.py: error: argument --config: expected one argument` (empty `$NEARMISS_CFG`), so neither
`det_a.md` nor `det_b.md` was written — yet `diff … && echo "IDENTICAL"` printed `IDENTICAL`,
because it compared two **untouched 2026-08-29 files**. A determinism check that passes while the
program never runs is the exact failure mode prerequisite 5 now guards against. Re-run correctly
with the CV cache cleared between runs: both `Thesis verdict: DECLINE`, `diff` clean, `IDENTICAL`,
sha `f526fceaa140430116b203292c8cb17e2de22cf979b047a2a4c5f73d805c6e33` on both. Stronger still, the
freshly generated report is byte-identical to the 2026-08-29 artifact — determinism holds across
sessions and across days, not just back-to-back. **Roger re-ran this himself on 2026-08-31**, from
a clean `/tmp/m4` so both files were provably written this run (both printed
`Thesis verdict: DECLINE` before the diff): `diff` clean, `IDENTICAL`. **PASS, on Roger's own run —
and this time the check actually ran.**

---

## Case 7 — Speed: the recourse re-run loop stays inside its own budget at institutional scale

```bash
python -m tests.perf.bench_finance_engine
```

> **This case was rewritten on 2026-08-30.** The version above it in git asked you to confirm
> `<= 120 ms: PASS` on a `search` column. That column measured 432 probes of the **cheapest** lever
> shape (`purchase_price`, which shares the rent roll by reference); the `rent_per_unit_month`
> shape — ~24× costlier at 5,000 units and ~26% of the real probe mix — was excluded from the table
> and reported below it **in different units** (per-probe, beside a per-432-probe table). The real
> loop misses that 120 ms budget by ~60%. `tests/perf/bench_finance_engine.py` no longer models the
> loop; it **calls** `compute_recourse` and **counts** its probes.

**Expected result:** two blocks. `PRIMARY` is the honest end-to-end figure and the only one the
budget judges:

```
PRIMARY -- real compute_recourse(), the production loop. THIS is the cost of an analysis.
                    deal          best/median   probes  by lever                                      verdict
 5,000u / 100y (ceiling)     192.7/   196.9ms      150  annual:3, interest:33, purchase:75, rent:39   <= 250 ms: PASS
                          fails 3 guardrails ('dscr', 'spread', 'irr') -- the gate's limit (GENUINELY_CLOSE_MAX_FAILS=3)
  36_kelly_moncton (10y)       9.2/     9.5ms      159  annual:11, interest:44, purchase:52, rent:52  (real deal, not budgeted)
82_champlain_dieppe (10y)       8.2/     8.3ms      135  annual:21, interest:33, purchase:42, rent:39  (real deal, not budgeted)
```

Then `ATTRIBUTION`, in microseconds **per probe**, with both lever shapes in the same table and the
same units — `rent search` at ~4,200 µs against `price search` at ~178 µs on the 5,000u/100y row is
the cost the old harness hid. Your millisecond figures will differ with machine load; the shapes,
the counted probe totals, and the PASS/FAIL verdict should not.

**Three things worth understanding about these numbers:**

- **5,000u/100y is priced to fail exactly 3 guardrails** — `GENUINELY_CLOSE_MAX_FAILS`, the worst
  case the production gate admits. At 4+ fails `is_genuinely_close` returns False and
  `compute_recourse` is never called at all. The price is *searched* at run time, not hard-coded,
  so an engine change that moves where guardrails break moves the workload with it rather than
  silently benchmarking a deal that fires zero probes.
- **432 is a ceiling, not a measurement.** It is the discovery spec's §2.4 analytic bound
  (`27 non-excluded pairs × (1 + 15)`). Real analyses fire the counted totals above — 159, 135, 150.
  Never quote 432 as a per-deal cost.
- **A real deal costs ~8–9 ms.** The 193 ms row is a synthetic 5,000-unit institutional portfolio.

**The budget itself needs Roger's ratification.** `BUDGET_MS` was re-baselined **120 → 250 ms**
because the 120 ms figure was set against the harness that never ran the rent lever — it was never
a judgement about the shipped loop. Measured worst case is ~193 ms, of which ~164 ms (85%) is the
39 rent-lever probes. If 120 ms is to stand as the requirement, the **loop** needs optimising, not
the harness re-tuning: the obvious target is `_perturb`'s rent path, which rebuilds all 5,000
`UnitIncome` models to change one scalar.

**Why a budget matters here at all, briefly:** before this mission's surgical-copy +
loop-invariant-hoist fix, a full recourse analysis at 5,000 units/50 years took **11.37 s wall
time**, and 5,000u/100y **crashed outright** (see Case 8). The fix is the difference between
"usable" and "broken" at the scale Roger set as the target — that conclusion survives the
re-measurement unchanged.

**Pass/fail criterion:** Does `PRIMARY`'s 5,000u/100y row print `PASS`, do the sample deals report
counted probe totals in single-digit milliseconds, and **do you accept the 250 ms budget**? Yes to
all three = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-08-31
**Actual result observed:** _Roger, 2026-08-30 — **FAIL as recorded; benchmark rewritten the same
day; the 250 ms budget still needs Roger's ratification.**_ The run printed
`5,000u / 100y … 73.8/ 74.0ms … <= 120 ms: PASS`, but that PASS did not measure the production
loop. Verified by calling the real `compute_recourse` directly at 5,000u/100y: at the gate's limit
of 3 failing guardrails it fires **150 probes in 192.7 ms** — **61% over the 120 ms budget the
benchmark reported as PASS**. Cause: all 432 timed probes used the cheap `purchase_price` shape,
while **39 of the 150 real probes are `rent_per_unit_month`**, measured at ~4,200 µs each against
~178 µs for the price shape (~24×) — **~164 ms, or 85% of the total, in the one lever the harness
excluded**, reported below the table in per-probe units next to a per-432-probe table. Two further
errors, in opposite directions: `PROBES = 432` was documented as "what one full recourse analysis
costs … measured against the committed sample deal" when it is neither measured nor that deal's
figure (real: **159** on `36_kelly_moncton`, **135** on `82_champlain_dieppe`), and its stated
derivation counts 7 guardrails when only 4 are live and failing there. **Fixed** by rewriting
`tests/perf/bench_finance_engine.py` to call `compute_recourse` and count its probes rather than
model the loop; both lever shapes now sit in one table in one unit; 432 is labelled a ceiling
everywhere. `ruff`/`mypy` clean, exits non-zero when over budget.
**Scale honestly stated:** in wall-clock this was never a user-facing problem — real deals finish
in **8–9 ms**. It was a false-assurance defect, and it mattered because this budget is what
justified waiving the zero-`finance-core`-diff constraint.
**Roger ran the rewritten benchmark himself on 2026-08-31:** `197.3/213.0ms`, 150 counted probes
(`rent:39`), `<= 250 ms: PASS`; sample deals 8.4 ms and 7.4 ms; `rent search` 3,451 µs vs
`price search` 164.5 µs (21×). **The harness now reports the real loop — but the 250 ms budget is
still unratified**, and Roger's figures are the highest observed so far: 181–197 ms best and up to
213 ms median across runs leaves only **~15–21% headroom**, not the ~28% first written into the
constant (since corrected). Thin enough that a loaded machine could trip this row; the
`median > 1.15 × best` warning is there to distinguish that from a real regression.

---

## Case 8 — The crash is gone: a 99-year horizon on a 5,000-unit portfolio now completes

**Goal:** `run_financial_model` used to raise `OverflowError` in `irr.py`'s Newton-Raphson solver
for large-unit-count, long-horizon deals — reachable in shipped code via `main.py --horizon`. Prove
it no longer does, on the exact realistic-rate shape that used to crash.

```bash
python - <<'PY'
import time
from src.core.finance import run_financial_model
from src.schemas.models import (
    FinancialInputs, FinancingTerms, IncomeModel, MarketAssumptions,
    OperatingExpenses, RefinancePlan, UnitIncome,
)

units_list = [UnitIncome(rent_month=1600.0, other_income_month=0.0) for _ in range(5000)]
inputs = FinancialInputs(
    financing=FinancingTerms(purchase_price=399_900.0, closing_costs=10_000.0, down_payment_rate=0.05,
                              interest_rate=0.055, amort_years=25, io_years=0, mortgage_insurance_rate=0.04),
    opex=OperatingExpenses(insurance=1026.0, taxes=4747.0, utilities=0.0, water_sewer=920.0,
                            property_management=0.0, repairs_maintenance=0.0, trash=0.0, landscaping=0.0,
                            snow_removal=0.0, hoa_fees=0.0, reserves=0.0, other=0.0, expense_growth=0.02),
    income=IncomeModel(units=units_list, occupancy=0.95, bad_debt_factor=0.97, rent_growth=0.03),
    refi=RefinancePlan(do_refi=True, year_to_refi=10, refi_ltv=0.8),
    market=MarketAssumptions(cap_rate_purchase=None, cap_rate_floor=0.05, cap_rate_spread_target=0.015),
    capex_reserve_upfront=0.0,
)

t0 = time.perf_counter()
result = run_financial_model(inputs, horizon_years=99)
t1 = time.perf_counter()
print(f"5000 units, horizon=99: completed in {(t1-t0)*1000:.1f} ms, irr_10yr={result.irr_10yr}")
PY
```

**Expected result:** completes without a traceback, in low single-digit milliseconds (observed
between 0.9 ms and 4.8 ms across repeated runs on this machine — the exact figure isn't the point,
"does not crash" is), printing an `irr_10yr` value. Pre-fix, this exact shape (5,000 units, this
rate/refi profile) raised `OverflowError` from horizon 95 onward. This shape is deliberately not a
synthetic edge case — a 99-year ground lease is a real financial instrument.

**A known open finding, visible in this exact command — read before you file it as a new bug:**
the printed `irr_10yr` is **`0.0`**, i.e. `0.00%`, not an "undefined" marker. This deal shape has no
single well-defined IRR at this horizon, and `engine.py:589` reads
`irr_10yr_val = irr(cashflows) or 0.0` — a `None` (no defined root) is coalesced to exactly `0.00%`,
which is indistinguishable in the report from "we computed an IRR and it happens to be zero."
This is a real, logged, **not-fixed** gap (tracked in
`docs/plans/MISSION_4_SPRINT_TRACKER.md`'s finance-core work), scoped as low-exposure because
realistic property shapes with mid-hold capex/refi still resolve to a real root — this benchmark
fixture is one of the shapes that doesn't. Don't be surprised by it; do flag it if you see it on a
report you didn't expect it on.

For the automated, permanent pins of this fix (both trigger shapes, both directions):
```bash
python -m pytest tests/core/finance/test_irr_overflow_known_bug.py -v --no-cov
```
**Expected:** all pass (10 tests this run) — including `test_formerly_crashed_realistic_rate_5000_units_horizon_99`,
the exact case reproduced above.

**Pass/fail criterion:** Does the 5,000u/99y run complete without a traceback and return a defined
(if occasionally `0.0`) `irr_10yr`? Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-08-30
**Actual result observed:** _Roger, 2026-08-30 — **valid exactly as run**._
`5000 units, horizon=99: completed in 1.1 ms, irr_10yr=0.0` — no traceback, which is the point of
the case. `tests/core/finance/test_irr_overflow_known_bug.py` **10 passed**. The `irr_10yr=0.0` is
the **already-documented** known finding (`engine.py:590`, `irr_raw or 0.0` coalescing an undefined
root to `0.00%`) — flagged in this case's own text above and in "Things stated honestly"; it is not
a new defect and it is not a computed zero return. The 1.1 ms is consistent with Case 7's rewritten
attribution table once the units are read per-probe.

---

## Case 9 — Whole-suite sanity: tests, formatting, linting, typing

```bash
python -m pytest -q
ruff format --check .
ruff check .
mypy .
```

**Expected result — the real numbers observed on this tree, 2026-08-29:**
- `pytest`: **3,191 passed, 0 failed, 0 errors, 1 skipped**, coverage **88.36%** against the 80%
  gate ("Required test coverage of 80% reached. Total coverage: 88.36%").
- `ruff format --check .`: **237 files already formatted**, exit 0.
- `ruff check .`: **All checks passed!**, exit 0.
- `mypy .`: **Success: no issues found in 235 source files**, exit 0.

> **A note on how the pass count was confirmed, for transparency (same quirk as Mission 3's doc):**
> in this sandboxed shell, `pytest -q`'s final one-line summary did not print to the terminal even
> though the run completed cleanly. The **3,191 / 0 failed / 1 skipped** figures above were
> confirmed via `--junitxml` (machine-readable): `tests="3192" errors="0" failures="0"
> skipped="1"` (3,192 total minus 1 skipped = 3,191 passed). If your terminal shows the normal
> summary line, trust it — it should read `3191 passed, 1 skipped in ~23s`.

**Diff-scope sanity, git-verified (not merely asserted):**
```bash
git diff --stat main -- src/core/finance/
git diff --numstat main -- src/schemas/models.py
```

**Expected result:** the first command shows real, nonzero changes to `engine.py`, `irr.py`, and
`amortization.py` — expected, per the charter amendment, not a regression to flag. The exact
line-change totals moved slightly between repeated runs of this benchmark in this sandboxed
environment (something in this shell re-touches file mtimes between commands — the underlying
diff content is stable when checked with `md5sum`; the totals are not a number worth pinning
precisely). The second command is the one that must be exact: `97	0	src/schemas/models.py` —
**97 lines added, 0 lines removed.** Additive only.

**Pass/fail criterion:** Does `src/core/finance/` show real changes, and is
`src/schemas/models.py`'s diff exactly `97 0` (purely additive, zero deletions)? Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-08-31
**Actual result observed:** _Roger, 2026-08-30 — **valid exactly as run**._ `pytest -q` green
with coverage **88.37%** against the 80% gate (the terminal summary-line quirk noted above recurred;
no failures or errors reported). `ruff format --check .` → **238 files already formatted**;
`ruff check .` → **All checks passed!**; `mypy .` → **Success: no issues found in 236 source
files**. Diff scope: `src/core/finance/` shows real changes to `amortization.py`, `engine.py` and
`irr.py` (828 insertions / 182 deletions), and `src/schemas/models.py` is exactly `97 0` — additive
only, as required. `tests/core/finance/test_golden_forecasts.py` **38 passed**.
**Re-verified after the Case 7 benchmark rewrite** (Claude, 2026-08-30): `ruff format --check .`
**238 files already formatted**, `ruff check .` **All checks passed!**, `mypy .` **Success: no
issues found in 236 source files**, `pytest -q` **3,197 passed / 0 failed / 0 errors / 1 skipped**
(counted via `--junitxml`, since the terminal summary-line quirk recurs). The rewrite edits
`tests/perf/bench_finance_engine.py` in place and adds no files, so the counts are unchanged by it.
**Benign drift from the pinned 2026-08-29 figures** (237 files / 235 source files / 88.36% /
3,191 passed): the tree gained a file and tests between the two dates.
**Roger re-ran the full sweep himself on 2026-08-31, after the benchmark rewrite:** `pytest -q`
green at **88.37%** coverage against the 80% gate, `ruff format --check .` **238 files already
formatted**, `ruff check .` **All checks passed!**, `mypy .` **Success: no issues found in 236
source files**. **PASS, on Roger's own run.**

---
---

## Things stated honestly, not omitted — read before validating

### The solver change moved numbers — deliberately, founder-approved

`irr.py` replaced its Newton-Raphson-first solver with a domain-bounded bracket search + Brent's
method, because the old solver could return an economically meaningless root (an IRR outside
`[-100%, ∞)`, silently floor-corrected to exactly −100%, masking the real error). This **moved 33
of 34 golden-case `irr_10yr` values** (the 34th, `units_1_horizon_10`, was unchanged). The largest
movement was **2.04e-7** (`interest_rate_high`) — about 5× smaller than the harness's own tolerance
philosophy and three orders of magnitude below the solver's own `1e-6` convergence tolerance. See
it for yourself:
```bash
python -m pytest tests/core/finance/test_golden_forecasts.py -q --no-cov
```
then open the module docstring at the top of `tests/core/finance/test_golden_forecasts.py` — it
carries the full before/after table, all 34 cases, case-by-case.

### A known open finding: `0.00%` IRR instead of "undefined"

Covered in Case 8 above, with a command that reproduces it directly: `engine.py:589`'s
`irr(cashflows) or 0.0` coalesces "no single well-defined root" to exactly `0.00%`. Low exposure —
realistic property shapes with mid-hold capex/refi still resolve to a real root — but logged, not
fixed. If you see a report with `IRR: 0.00%` and it looks wrong, check whether the cash-flow shape
plausibly has no single root before assuming a bug.

### Other open items the sprint tracker records

- **The negative-purchase-price bound is still open.** `validate_assignment=True` was added to
  every input model (`src/schemas/models.py`) and `--horizon` overrides now re-validate (see below)
  — but `FinancingTerms.purchase_price` itself never declared a `ge=0` (or `gt=0`) constraint, so
  `validate_assignment` has nothing to enforce on that specific field. Confirmed directly:
  ```bash
  python -c "
  from src.schemas.models import FinancingTerms
  ft = FinancingTerms(purchase_price=500_000.0, down_payment_rate=0.2, interest_rate=0.05)
  ft.purchase_price = -999.0
  print('no error, purchase_price =', ft.purchase_price)
  "
  ```
  **Expected:** `no error, purchase_price = -999.0` — this still succeeds. The systemic-defects
  table in `docs/plans/MISSION_4_SPRINT_TRACKER.md` (§"pydantic constraints enforced at
  construction only") named this exact case; only the *mechanism* (`validate_assignment`) was
  fixed, not this specific field's missing bound. Worth knowing before you assume every
  configuration error is now loud.
- **The `--horizon` ceiling IS now loudly enforced (good news, confirm it yourself):**
  ```bash
  python main.py --config $NEARMISS_CFG --horizon 100
  ```
  **Expected:** a non-zero exit and `ValueError: Rejected CLI override(s) to run options:
  - horizon: Input should be less than or equal to 50 (got 100)` — this used to silently accept
  100 (the schema declared `le=50` but `with_overrides` never re-ran the validator). It now
  re-validates and loud-fails, which is the fix. **CLI-experience note, out of this mission's
  scope but worth a future look:** the loud failure is correct and the actionable message is
  present, but it is buried at the bottom of a raw Python traceback (a `pydantic.ValidationError`
  printed in full, then the wrapping `ValueError`) rather than a single clean line — this doesn't
  meet this project's own "errors teach, no raw traceback" bar as cleanly as, say, Mission 3's
  `--onnx-model` error paths do. Not a Mission 4 regression (the pre-fix behaviour was silent
  data corruption, which is worse), just not yet polished.
- **The "genuinely close" cutoff (`GENUINELY_CLOSE_MAX_FAILS = 3`) is a bounded product decision,
  not a bug** — Roger's Gate D ruling, documented in `src/market/recourse.py:130-143`. It is worth
  knowing it exists as a tunable constant, not treating it as an arbitrary or hidden cutoff: a
  CONDITIONAL always has 1–2 fails and is always covered; a DECLINE gets a section only up to 3
  fails, and `$DECLINE_CFG` (4 fails) in Case 2 is the deliberate demonstration of where that line
  sits.

---

## Deferred / out of scope — read before filing anything below as a defect

- **`deal-report` and `deal-advisor` do not surface recourse at all.** Confirmed by import
  inspection: neither `src/cli/report_cli.py` nor `src/cli/advisor_cli.py` references
  `src/market/recourse.py` or `src/orchestrators/crew.py`. Only `python main.py`'s deterministic
  path and the CrewAI orchestration path (`src/orchestrators/crewai_runner.py`) compute and can
  render it. This is the same "one surface, not every surface" shape Mission 3 shipped for the
  ONNX flags — not an oversight.
- **No verdict or threshold changes.** BUY/CONDITIONAL/DECLINE and every guardrail line are exactly
  as before. This feature only *describes* the distance and the fix; it never moves the line.
- **No live market data.** Plausibility uses the program's existing in-repo rejector/snapshot logic
  only (now two-sided for rate cuts — see the CHANGELOG's "Fixed" section).
- **No AI, no vision, no ONNX, no network, no user-supplied files.** Pure deterministic deal math.
- **No UI.** The output is the Markdown report section, nothing else.
- **Combinations of levers were never searched.** Every recourse row changes exactly one input; a
  smaller combined move across two levers may exist and is not checked or claimed.

---

_End of Mission 4 manual testing handoff._
