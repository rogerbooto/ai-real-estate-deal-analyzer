# Mission 1 — Scenario Intelligence — Manual Testing Handoff

_Author: mission-planner · Written & run 2026-08-19 against `main @ 8ed9397` (Mission 1 shipped and
merged to `main`, synced with `origin/main`). Every command below was executed in the `airedeal`
env on this commit; the "Expected result" text is the literal output observed today._

> **Mission status: SHIPPED.** This is a *verification* checklist — the features exist and these
> commands pass right now. Your job is to reproduce them with your own hands and tick the boxes.
> The VALIDATED marks are yours to make, not mine.

---

**Overall validation:** ☐ NOT VALIDATED ☐ VALIDATED (Roger, ______) ☐ VALIDATED WITH ISSUES
**Blocking issues found:** ______________________________________________

---

## Prerequisites (do this once)

1. Open a terminal at the repo root:
   `cd /home/rtokime/projects/Personal/ai-real-estate-deal-analyzer`
2. Activate the project env (the miniconda path in old notes is wrong — use this one):
   `source /home/rtokime/anaconda3/etc/profile.d/conda.sh && conda activate airedeal`
3. Confirm the interpreter is the env's Python (must print a path under `.../envs/airedeal/`):
   `which python`  → expect `/home/rtokime/anaconda3/envs/airedeal/bin/python`
4. Confirm you are on the shipped code:
   `git rev-parse --abbrev-ref HEAD` → `main` · `git log --oneline -1` → starts `8ed9397` or later.
5. Make a scratch folder for outputs so you never touch tracked files:
   `mkdir -p /tmp/m1 && OUT=/tmp/m1`

All commands are read/compute only (no network in the core pipeline) and deterministic — re-running
gives identical numbers.

---

## Test Case 1 — The opt-in scenario path adds a "Market Scenarios" section (`--scenarios`)

**Goal:** Prove the `--scenarios` flag turns on the prior-weighted market what-if overlay that
Mission 1 wired in, and that a normal run does *not* show it.

**Steps to reproduce**
1. Run the analyzer once WITHOUT the flag, once WITH it, writing to two files.
2. Look for a top-level `## Market Scenarios` heading in each.

**Command(s)**
```
python main.py --out $OUT/plain.md
python main.py --scenarios --out $OUT/scen.md
grep -c '^## Market Scenarios' $OUT/plain.md $OUT/scen.md
```

**Expected result**
- Both runs print `Thesis verdict: DECLINE` and `Report written to …`.
- The `grep` prints:
  ```
  /tmp/m1/plain.md:0
  /tmp/m1/scen.md:1
  ```
  i.e. the plain report has **no** `## Market Scenarios` section; the `--scenarios` report has
  exactly one. (The plain report still *mentions* scenarios once, in its Run Provenance table as
  `| Market Scenarios | off | …` — that is a settings row, not the section, which is why we match on
  the `##` heading.)

**Before this shipped:** there was no scenario overlay at all — the only "what-ifs" were ad-hoc
environment-knob stress overrides, with no prior-weighted bands.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## Test Case 2 — The env var is equivalent to the flag (`AIREAL_SCENARIOS=1`)

**Goal:** Prove the documented opt-in also works via the environment variable, so a `.env` or CI
setting behaves like `--scenarios`.

**Steps to reproduce**
1. Run with the env var set instead of the flag.
2. Confirm the section appears.

**Command(s)**
```
AIREAL_SCENARIOS=1 python main.py --out $OUT/env.md
grep -c '^## Market Scenarios' $OUT/env.md
```

**Expected result**
- Prints `Thesis verdict: DECLINE`.
- `grep` prints `1` — the section is present, exactly as with `--scenarios`.

**Before this shipped:** no such overlay existed under any switch.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## Test Case 3 — The scenario section is honest and prior-weighted (content check)

**Goal:** Prove the section shows prior-weighted DSCR/CoC/cash-flow/IRR bands **and** a plain-English
honesty block stating these are deterministic what-ifs, not predictions or live market data.

**Steps to reproduce**
1. Open the `--scenarios` report from Test Case 1.
2. Read the section between `## Market Scenarios` and the next `##`.

**Command(s)**
```
sed -n '/^## Market Scenarios/,/^## Appendix/p' $OUT/scen.md
```

**Expected result** — the section contains, in order:
- An "About these scenarios" block stating they are **"deterministic what-if calculations … not
  predictions, forecasts, or live market data"** and that the priors are **"heuristic penalty
  weights, not calibrated probabilities."**
- A **Market snapshot** table (Vacancy 5.00% · Cap rate 6.35% · Rent growth 3.00% · Opex growth
  2.00% · Interest rate 5.50%) with a note that it is derived from the file and the engine's own Y1
  output, *not* external market data.
- A **Scenario grid — top 5 by prior** table and a **Prior-weighted bands** table with rows
  `DSCR (Y1)`, `CoC (Y1)`, `Cash flow (Y1)`, `IRR (10yr)`, `Equity multiple (10yr)` and columns
  `downside (p25) · median (p50) · mean (expected) · min · max`.
- A `168 of 189 scenarios admitted under guardrails · admitted priors sum to 1.00` line.
- A **Caveats** block and a **Narrative flags (not modeled)** block.

**Pass/fail criterion:** Can you find the "not predictions / heuristic penalty weights" honesty
wording AND the five-row Prior-weighted bands table? Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## Test Case 4 — Default-off is byte-identical (the safety guarantee)

**Goal:** Prove that turning scenarios OFF changes nothing — two plain runs are byte-for-byte
identical, so the opt-in feature cannot silently alter a normal report.

**Steps to reproduce**
1. Run the plain pipeline twice into two files.
2. Diff them.

**Command(s)**
```
python main.py --out $OUT/a.md
python main.py --out $OUT/b.md
diff $OUT/a.md $OUT/b.md && echo "BYTE-IDENTICAL"
```

**Expected result**
- `diff` prints nothing and you see `BYTE-IDENTICAL` (exit 0).

**Pass/fail criterion:** Did `diff` report zero differences? Yes = PASS. Any diff = FAIL (the
determinism/default-off guarantee is broken).

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## Test Case 5 — Wave 0 packaging: `pip install -e .` works and the console scripts resolve

**Goal:** Prove the packaging fix landed — the project installs as a package and the three declared
command-line tools are on `PATH` (they used to be dead).

**Steps to reproduce**
1. Confirm the three console scripts resolve to the env's `bin/`.
2. Confirm each runs its `--help`.
3. (Optional, slower) re-install editable to prove `pip install -e .` still succeeds.

**Command(s)**
```
which ingest-listing deal-report deal-advisor
deal-report --help    | head -3
deal-advisor --help   | head -3
ingest-listing --help | head -3
# optional full re-install:
pip install -e . 2>&1 | tail -3
```

**Expected result**
- `which` prints three paths, all under `.../envs/airedeal/bin/`.
- Each `--help` prints a usage line (`usage: report-cli …`, `usage: advisor-cli …`,
  `usage: ingest-listing …`) with no `command not found` and no traceback.
- `pip install -e .` ends in `Successfully installed …` (or "already satisfied").

**Before this shipped:** `pyproject.toml` had no `[project]` table, so `pip install -e .` failed and
the console scripts did not exist — the CLIs could only be reached via `python -m`.

**Known cosmetic note (not a failure):** `pip show ai-real-estate-deal-analyzer` may report
`Version: 0.1.0` even though `pyproject.toml` now says `0.3.0` — this is stale editable-install
metadata from an earlier install, not a functional problem. Re-running `pip install -e .` refreshes
it. Flag it if you like, but the scripts working is the pass criterion here.

**Pass/fail criterion:** Do all three commands resolve and print a usage line? Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## Test Case 6 — IRR-solver core fix: no spurious sub-(−100%) roots

**Goal:** Prove Mission 1's one authorized finance-core fix — the IRR solver no longer returns
economically-meaningless roots below −100% for deeply-underwater cash flows.

**Steps to reproduce**
1. Run the IRR edge-case test that pins the fix.
2. (Optional) read the guard comment in the solver.

**Command(s)**
```
python -m pytest tests/core/finance/test_irr_edge_cases.py::test_irr_deep_underwater_returns_valid_domain_root_not_spurious tests/unit/test_irr_bisection.py --no-cov -q
git log --oneline -1 -- src/core/finance/irr.py
```

**Expected result**
- pytest prints a row of dots and `passed` (0 failures).
- The `git log` line is `b6304eb fix(finance): guard IRR solver against spurious sub-(-100%) roots`.

**Before this shipped:** the Newton–Raphson step could converge to a spurious real root where
`1 + r < 0` (a rate below −100%), which is not a meaningful discount rate; the solver now rejects it
and falls through to a domain-bounded bisection on `(−1, ∞)`.

**Pass/fail criterion:** Does the named test pass? Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## Test Case 7 — Failure/edge case: scenarios loud-fail when no market snapshot can be derived

**Goal:** Prove the opt-in fails **loudly and clearly** (not silently, not with a fabricated
snapshot) when it has nothing to build a market snapshot from.

**Note on the input file:** no committed config triggers this, because the shipped
`36_kelly_moncton` bundle carries a `market` block. To observe the guard you build a one-line
throwaway config (outside `data/`, so nothing tracked is touched). This is a deliberately
constructed *broken* input, clearly marked as throwaway — not a repo sample.

**Steps to reproduce**
1. Create a throwaway config from the demo inputs with the `market` block removed and
   `cap_rate_purchase` set to null.
2. Run `--scenarios` against it.

**Command(s)**
```
python -c "import json; d=json.load(open('data/sample_listings/36_kelly_moncton/inputs.json')); i=d['inputs']; i.setdefault('market',{})['cap_rate_purchase']=None; open('/tmp/m1/nomarket.json','w').write(json.dumps({'inputs':i}))"
python main.py --scenarios --config /tmp/m1/nomarket.json --out /tmp/m1/x.md
```

**Expected result** — the run stops with a clear message (not a silent empty section):
```
ValueError: Cannot derive a market snapshot cap rate for scenario analysis: no 'market' block was
provided and inputs.market.cap_rate_purchase is None. Fix by adding a 'market' block to the inputs
(region/vacancy_rate/cap_rate/rent_growth/expense_growth/interest_rate) or by setting
market.cap_rate_purchase.
```
Exit code is non-zero (1). (A short Python traceback precedes the message; the *message* is the
point — it names the cause and the fix.)

**Pass/fail criterion:** Did the run refuse with a message that names the missing `market` block and
tells you how to fix it, rather than producing a scenario section built on invented numbers?
Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

_End of Mission 1 manual testing handoff._
