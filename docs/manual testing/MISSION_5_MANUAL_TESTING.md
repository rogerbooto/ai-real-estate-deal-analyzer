# Mission 5 — Adjoint Differentiation & Optimized Recourse Search — Manual Testing Handoff

_Author: mission-planner (charter time, 2026-08-31), against `main @ 7cfd449` (Mission 4 merged,
validated by Roger 2026-08-31, 9/9). **This mission is CHARTERED, NOT YET BUILT.** The "before"
commands below were run on this tree and their output is quoted as the current state; the "after" /
acceptance targets describe what the built mission must produce and are marked **[ACCEPTANCE TARGET —
not yet runnable]** where they depend on unbuilt work. The executing orchestrator MUST rewrite each
such block into a real, run-once command with quoted actual output before requesting the mission gate._

> ## Read this first
>
> Every "Status" box and the document-level box are left **unchecked on purpose** — that is Roger's
> gate, not the author's. "Actual result observed" fields are blank for Roger to fill in as he runs each
> command himself. Where a case says **[ACCEPTANCE TARGET]**, the feature it checks does not exist yet;
> the orchestrator replaces the target with a real command + observed output as the work lands, and the
> case is not tickable until then.

> **Verify the tree before trusting anything below:**
> `git branch --show-current` → `mission/5-adjoint-differentiation` (or, once merged, `main` with the
> merge commit in `git log`). If neither, you may be on the wrong tree.

---

**Overall validation:** ☐ NOT VALIDATED ☐ VALIDATED (Roger, ______) ☐ VALIDATED WITH ISSUES
**Blocking issues found:** _______________________________________________

---

## What this mission is, precisely (read before testing)

Mission 4's recourse feature finds "what would close this near-miss" by trial-and-error: nudge one
lever, re-run the whole engine, repeat ~10–20 times until the failing guardrail flips. **Half A** of
Mission 5 makes that search fast by computing the **derivative** of the model and using **Newton's
method** to jump to the answer in ~3–4 tries — **then confirming every reported number with one real,
un-differentiated engine re-run.** Because the fast method reorders floating-point arithmetic, it cannot
be bit-identical to Mission 4's golden, so Mission 5 **first** ships a **tolerance rule**: numbers may
move by at most ~1e-9 relative, always measured against the *original* golden, and the harness still
catches the ~9.4e-8 calibration bug. **Half B** (added by Roger's 2026-08-31 expand decision, and built
only if an internal AD checkpoint proves the fast math sound) adds a **second report section — "top-3
actionable combinations"** — alongside the existing single-lever menu: up to three realistic *bundles*
of lever moves, each confirmed by a real engine re-run, each drawn only from combinations a **unified
all-four-lever plausibility gate** calls sensible, and the three chosen to be genuinely different routes.
The mission also raises the horizon cap to 100, gives money fields lower bounds, and replaces an
out-of-range-horizon traceback with a clean message.

> **Note on the Half B cases (11–16):** if the internal AD checkpoint recorded **NO-GO**, Half B was
> deferred and the mission shipped Half A alone. In that case mark cases 11–16 **N/A** with a note
> pointing at the checkpoint decision in the sprint tracker — they are not failures.

---

## Prerequisites (do this once)

1. `cd /home/rtokime/projects/Personal/ai-real-estate-deal-analyzer`
2. `source /home/rtokime/anaconda3/etc/profile.d/conda.sh && conda activate airedeal`
   **Do not use `~/miniconda3` — it does not exist on this machine and some shells silently fall back to
   a different, wrong Python. Use the `anaconda3` path above, exactly.**
3. `which python` → must print `/home/rtokime/anaconda3/envs/airedeal/bin/python`. If not, stop and fix
   your shell before running anything below.
4. `git branch --show-current` → `mission/5-adjoint-differentiation` (or `main`, once merged).
5. **Start from an EMPTY output directory:** `rm -rf /tmp/m5 && mkdir -p /tmp/m5 && export OUT=/tmp/m5`.
   Not housekeeping — several cases `grep` a report a previous command was supposed to have just written;
   an empty dir makes a failed run error loudly instead of a stale file passing silently.
6. Sample deals used below (confirm they exist):
   - `export NEARMISS_CFG=data/sample_listings/82_champlain_dieppe/inputs.json` — a **DECLINE that fails
     3 of the 7 live guardrails** (`dscr`, `spread`, `irr`), exactly the "genuinely close" boundary
     (`GENUINELY_CLOSE_MAX_FAILS = 3`), so it grows the full recourse section.
   - `export FAR_CFG=data/sample_listings/36_kelly_moncton/inputs.json` — a DECLINE that fails 4
     guardrails, one past the gate; used to show the section correctly staying absent.
   - `ls -l "$NEARMISS_CFG" "$FAR_CFG"` → both must resolve to real files before you run anything.
7. The report CLI is `python main.py --config <inputs.json> --out <file> [--horizon N]`. Only
   `python main.py`'s deterministic/CrewAI paths compute recourse (`deal-report`/`deal-advisor` do not).

---

## Case 1 — The tolerance harness still CATCHES the calibration bug (nine-nines, anchored to origin)

**Goal:** Prove the relaxed golden rule is tight enough: a ~9.4e-8 relative rounding drift still FAILS
(that is the injected-bug calibration point), while a legitimate ~1e-9-scale drift PASSES — and the
comparison is against the ORIGINAL golden, not the previous version.

**Before (runnable now — bit-exact, no tolerance yet):**
```bash
pytest tests/core/finance/test_golden_forecasts.py -q
```
Today this passes because the harness compares **bit-exactly** (`assert actual == expected`). Any drift,
however tiny, fails — there is no tolerance to calibrate yet. That is the state Mission 5 changes.

**After [ACCEPTANCE TARGET — not yet runnable]:** with the tolerance rule shipped, the orchestrator will
supply two real commands here:
1. Perturb one golden number by **~9.4e-8 relative**, re-run the harness → it must **FAIL** with an
   "exceeds tolerance" message naming the case/field (this is the bug the harness must always catch).
2. Perturb one golden number by **~1e-9 relative**, re-run the harness → it must **PASS** (a legitimate
   AD-scale drift), and if it *approaches* the limit it must print an **"approaching tolerance — written
   justification required"** state, not a silent green.

**Pass/fail criterion:** ~9.4e-8 drift fails; ~1e-9 drift passes (with the approaching-tolerance state
where relevant); both judged against the original golden. Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ____________________________________________

---

## Case 2 — Drift cannot ratchet: anchoring to the ORIGINAL golden, never the previous version

**Goal:** Prove a *sequence* of small, individually-passing changes cannot creep the numbers far from
the truth, because every change is measured against the first-correct golden, not the last one.

**After [ACCEPTANCE TARGET — not yet runnable]:** the orchestrator supplies a real demonstration:
apply two successive ~6e-10 drifts in the same direction (each individually under 1e-9 vs the previous
version). Because the harness anchors to the **original**, the *cumulative* ~1.2e-9 drift is what gets
measured, and it must surface as at-or-approaching tolerance — it must NOT show two silent greens. Show
the harness reads the pinned original golden, never a regenerated intermediate.

**Pass/fail criterion:** The cumulative drift is caught / flagged against the original; it does not slip
through as two independent green steps. Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ____________________________________________

---

## Case 3 — THE ANTI-INVERSION CHECK: the AD-accelerated answer MATCHES a real engine re-run

**Goal:** Prove every recourse number Mission 5 prints is confirmed by one real, un-differentiated engine
re-run — the fast Newton jump never ships an answer the real model disagrees with.

**Before (runnable now — Mission 4 recourse via bisection):**
```bash
python main.py --config "$NEARMISS_CFG" --out "$OUT/nearmiss.md"
grep -iA 25 "What would have to change" "$OUT/nearmiss.md"
```
Today the section is produced by bisection (~10–20 probes/lever). Note the exact lever numbers printed.

**After [ACCEPTANCE TARGET]:** with AD shipped, take the exact rent (or price/rate/opex) figure the
report states "WOULD close it", feed it back independently through the engine (the orchestrator supplies
the one-line re-run command), and confirm the guardrail actually clears at that value — and that the AD
answer equals the bisection answer to within tolerance. If the AD jump and the real re-run ever
disagree, the report must show the re-run's confirmed value, not the jump.

**Pass/fail criterion:** The stated lever value clears the guardrail on an independent re-run, and the
printed number is the re-run-confirmed one. Yes = PASS. (If Gate D stopped the AD portion, this case is
marked N/A with a note, and the mission ships the tolerance rule alone.)

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ____________________________________________

---

## Case 4 — The probe count dropped (~10–20 per lever/guardrail → ~3–4)

**Goal:** See the search get cheaper, in tries, not just wall-clock.

**Before (runnable now):**
```bash
python tests/perf/bench_finance_engine.py --repeats 5 | grep -A2 "PRIMARY"
```
Current output on this tree (2026-08-31): the 5,000u/100y row reports **150 probes**
(`annual:3, interest:33, purchase:75, rent:39`). That is the bisection cost to beat.

**After [ACCEPTANCE TARGET]:** the same row must show a **materially lower probe total** (Newton reaching
each flip in ~3–4 steps per lever/guardrail instead of ~10–20), with a RED-on-regression test pinning
the reduction.

**Pass/fail criterion:** Probe total on the 5,000u/100y row drops materially versus the 150 baseline,
and a test fails if it regresses. Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ____________________________________________

---

## Case 5 — Speed measured HONESTLY against the 30 ms target (5,000u / 100y)

**Goal:** Get the real before→after time for the institutional-ceiling analysis, reported honestly
against Roger's 30 ms target — a measured near-miss is a result, not a failure.

**Before (runnable now):**
```bash
python tests/perf/bench_finance_engine.py --repeats 5 | grep "5,000u / 100y (ceiling)"
```
Current output on this tree (2026-08-31): **best 169.8 / median 178.0 ms** against `BUDGET_MS = 250.0`,
PASS. (Note: the brief's "73 ms" figure is NOT what this tree measures — the orchestrator reconciles
that claim in Discovery.)

**After [ACCEPTANCE TARGET]:** the same row, re-measured with AD, with the number reported plainly and
compared to the 30 ms target. If it lands short of 30 ms, that is stated as a measured result, not
hidden.

**Pass/fail criterion:** A measured after-time is recorded and compared to 30 ms; the before→after is
honest and reproducible (re-run if the "machine was busy" warning appears). Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ____________________________________________

---

## Case 6 — Determinism: the near-miss deal, run twice, is identical (within tolerance)

**Goal:** Same inputs ⇒ same report. AD must not introduce run-to-run wobble beyond the stated tolerance.

**Runnable now (and after):**
```bash
python main.py --config "$NEARMISS_CFG" --out "$OUT/det_a.md"
python main.py --config "$NEARMISS_CFG" --out "$OUT/det_b.md"
diff "$OUT/det_a.md" "$OUT/det_b.md" && echo IDENTICAL
```
Today (bisection) this prints `IDENTICAL`. After AD it must remain `IDENTICAL` (the search is
deterministic — fixed seeds/bounds), with any tolerance-scale differences documented if they appear.

**Pass/fail criterion:** `diff` is clean and `IDENTICAL` prints. Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ____________________________________________

---

## Case 7 — Open item: a negative purchase price is now REFUSED with a clean message

**Goal:** Money fields reject nonsense instead of accepting it.

**Before (runnable now — negative price is accepted):**
```bash
python - <<'PY'
from src.schemas.models import FinancialInputs
import json
d = json.load(open('data/sample_listings/82_champlain_dieppe/inputs.json'))
fin = d['inputs']['financing']; fin['purchase_price'] = -605000
# construct with the negative value — today this does NOT raise
print("built OK with purchase_price =", fin['purchase_price'])
PY
```
Today `purchase_price` has no lower bound (`src/schemas/models.py:24`), so a negative price is accepted.

**After [ACCEPTANCE TARGET]:** the same construction must raise a **clean validation error** naming the
field and the bound (not a raw traceback dump), and a RED test pins the rejection.

**Pass/fail criterion:** Negative price is rejected with a readable message; a valid price still builds.
Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ____________________________________________

---

## Case 8 — Open item: a 100-year horizon is now ACCEPTED (cap raised from 50)

**Goal:** 99-year leases are real; the horizon cap should allow 100.

**Before (runnable now — 100 is rejected at `le=50`):**
```bash
python main.py --config "$NEARMISS_CFG" --out "$OUT/h100.md" --horizon 100; echo "exit=$?"
```
Today this fails validation (horizon `le=50`, `src/inputs/inputs.py:74`).

**After [ACCEPTANCE TARGET]:** `--horizon 100` completes and writes the report; `--horizon 101` is
rejected. RED tests pin both (100 accepted, 101 rejected).

**Pass/fail criterion:** 100 accepted and produces a report; 101 rejected. Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ____________________________________________

---

## Case 9 — Open item (edge/failure path): an out-of-range horizon prints a CLEAN message, not a traceback

**Goal:** A bad `--horizon` value should read as one clean line, not a raw pydantic traceback with the
useful part buried at the bottom.

**Before (runnable now — raw traceback):**
```bash
python main.py --config "$NEARMISS_CFG" --out "$OUT/hbad.md" --horizon 101 2>&1 | tail -20; echo "exit=$?"
```
Today an out-of-range horizon surfaces as a raw pydantic `ValidationError` traceback.

**After [ACCEPTANCE TARGET]:** the same command exits non-zero with **one clean, readable line**
(e.g. "Forecast horizon must be between 1 and 100 years; got 101") and **no traceback**. RED test pins
the clean message + non-zero exit.

**Pass/fail criterion:** Clean single-line message, non-zero exit, no traceback. Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ____________________________________________

---

## Case 11 — Half B: a near-miss deal now shows a "top-3 combinations" section, AND each combination flips the verdict on a real re-run

**Goal:** Prove the new second section appears next to the single-lever menu, and that every combination
it lists really does flip the verdict when the *real* engine re-runs it (not just when the fast optimizer
says so).

**Before (runnable now — only the single-lever menu exists):**
```bash
python main.py --config "$NEARMISS_CFG" --out "$OUT/combos_before.md"
grep -iA 40 "What would have to change" "$OUT/combos_before.md"
```
Today the report shows only single-lever fixes ("any ONE of these closes it"). There is **no**
combinations section.

**After [ACCEPTANCE TARGET — not yet runnable]:** with Half B shipped, the same report gains a **second
section listing up to three combinations** (e.g. "raise rent by $X *and* cut price by $Y"). For each
listed combination, the orchestrator supplies a one-line command that feeds that exact bundle back
through the engine independently; the verdict must flip (the failing guardrails must clear) on that real
re-run. If the optimizer's jump and the real re-run ever disagree, the report must show the
re-run-confirmed bundle.

**Pass/fail criterion:** Both sections are present (single-lever menu AND top-3 combinations); each
listed combination clears the guardrails on an independent real re-run. Yes = PASS. (If the AD
checkpoint = NO-GO, mark N/A — see the note at the top.)

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ____________________________________________

---

## Case 12 — Half B: the unified gate REFUSES an implausible combination (including a jointly-implausible one that is individually fine)

**Goal:** Prove the combination-plausibility gate judges the *whole bundle*, not just each lever alone —
so two moves that each look fine but are unrealistic *together* are not offered.

**After [ACCEPTANCE TARGET — not yet runnable]:** the orchestrator supplies a real demonstration on a
deal where a bundle that is **individually fine per lever but jointly implausible** (e.g. simultaneously
cutting price AND raising rent past what the market supports together) is **excluded** from the top-3,
with the gate's reason visible — while a genuinely plausible bundle on the same deal is included. Contrast
this with today's behaviour, where plausibility is judged one lever at a time and no joint check exists.

**Pass/fail criterion:** A jointly-implausible bundle is refused (not surfaced), a plausible one is
surfaced, and the difference is the *joint* judgement, not a single-lever magnitude. Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ____________________________________________

---

## Case 13 — Half B: the three combinations are genuinely DIFFERENT routes (diversity)

**Goal:** The top-3 must be three distinct strategies, not three near-copies of the same bundle.

**After [ACCEPTANCE TARGET — not yet runnable]:** on a near-miss deal that admits several routes, the
three listed combinations must move **different sets of levers** (e.g. one rent-led, one price-led, one
blended) rather than three variants of a single lever mix. The orchestrator quotes the three bundles so
the distinctness is visible.

**Pass/fail criterion:** The three combinations are visibly different routes, not minor variants of one.
Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ____________________________________________

---

## Case 14 — Half B: multi-start is DETERMINISTIC — the same deal always yields the same three combinations

**Goal:** Same inputs ⇒ same three bundles, every run. The globality search uses fixed seeds, not
randomness.

**Runnable now (structure) and after (must hold):**
```bash
python main.py --config "$NEARMISS_CFG" --out "$OUT/combos_a.md"
python main.py --config "$NEARMISS_CFG" --out "$OUT/combos_b.md"
diff "$OUT/combos_a.md" "$OUT/combos_b.md" && echo IDENTICAL
```
**After [ACCEPTANCE TARGET]:** with Half B shipped, the two reports (including the combinations section)
must be `IDENTICAL` — the same three combinations in the same order. A RED test pins the determinism.

**Pass/fail criterion:** `diff` is clean and `IDENTICAL` prints, combinations section included.
Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ____________________________________________

---

## Case 15 — Half B: parsimony ordering — simpler bundles are preferred

**Goal:** All else equal, a bundle that moves **fewer** levers is ranked ahead of one that moves more —
the report leads with the simplest realistic route.

**After [ACCEPTANCE TARGET — not yet runnable]:** on a deal where both a one-or-two-lever bundle and a
three-lever bundle close the gap plausibly, the simpler bundle must appear first / be preferred in the
top-3. The orchestrator quotes the ordering.

**Pass/fail criterion:** Fewer-lever bundles are preferred over more-lever bundles at equal plausibility.
Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ____________________________________________

---

## Case 16 — Whole-suite sanity: tests, formatting, linting, typing, coverage

**Goal:** The quality gate is green with BOTH ruff commands (Mission 4 lesson: `ruff check` alone is not
"ruff clean").

**Runnable now (baseline) and after (must stay green):**
```bash
pytest -q
ruff format --check .
ruff check .
mypy .
```

**Pass/fail criterion:** `pytest` green with coverage ≥80%; **both** `ruff format --check` and
`ruff check` clean; `mypy .` clean. Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ____________________________________________

---

_When every case above reads PASS and every box is ticked, flip the document-level box at the top to
VALIDATED. The mission gate cannot be requested until it does._
