# Mission 5 — Forward-Mode Differentiation & Optimized Recourse Search — Manual Testing Handoff

_Author: mission-planner (charter time, 2026-08-31), against `main @ 7cfd449` (Mission 4 merged,
validated by Roger 2026-08-31, 9/9). **REWRITTEN BY THE ORCHESTRATOR 2026-08-31: the mission is
BUILT and every case below is runnable now.** Each case carries a real command and the real output
the orchestrator observed running it on this tree. Nothing below says "should produce"; where a
charter-time acceptance target could not be demonstrated as written, it was replaced with the
demonstration that proves the same property, and the substitution is stated in the case._

> ## Read this first
>
> Every "Status" box and the document-level box are left **unchecked on purpose** — that is Roger's
> gate, not the author's, and not the orchestrator's. "Actual result observed" fields are blank for
> Roger to fill in as he runs each command himself. The **Observed (orchestrator, 2026-08-31)**
> transcripts are there so you know what a PASS looks like before you run it — they are not a
> substitute for running it.

> **Verify the tree before trusting anything below:**
> `git branch --show-current` → `mission/5-forward-mode-differentiation` (or, once merged, `main` with the
> merge commit in `git log`). If neither, you may be on the wrong tree.

---

**Overall validation:** ☐ NOT VALIDATED ☑ VALIDATED (Roger, 2026-09-01) ☐ VALIDATED WITH ISSUES
**Blocking issues found:** None — 17 of 17 cases PASS. One procedural deviation, checked and cleared by Roger: `$OUT` was `/tmp/m4` rather than a fresh `/tmp/m5`, so the empty-output-directory prerequisite did not hold; Roger verified that every report read during validation was written fresh in the same session and that no stale file was picked up.

---

## What this mission is, precisely (read before testing)

Mission 4's recourse feature finds "what would close this near-miss" by trial-and-error: nudge one
lever, re-run the whole engine, repeat until the failing guardrail flips. Mission 5 was chartered to
make that search fast with **Newton's method on an AD derivative**. **It did not ship that, and the
reason is measured, not rhetorical:** a dual-number pass costs ~4× a plain engine pass, so Newton
converges in **11–41 probes against bisection's fixed ~11** — a wash or a loss. What shipped instead:

- **Half A — the tolerance rule and the anchor.** Because forward-mode differentiation reorders
  floating-point arithmetic, the golden harness can no longer be bit-exact. Numbers may move by at
  most **1e-9 relative**, always measured against a **digest-pinned original golden** that no
  regeneration can quietly replace, and the harness still catches an ordinary `round(a money field)`
  bug that a naive 1e-6 rule would miss entirely (Cases 1 and 2).
- **Half A — the speed, from where it actually was.** The 5,000-unit / 100-year institutional
  ceiling went **438 ms → 65 ms** on this box, from an **aggregate-income seam** (the rent probe
  became O(1) instead of rebuilding a 5,000-unit rent roll) and a **scoped GC threshold** — neither
  of which is AD. Roger's **30 ms target was not met**, that is stated as a measured result, and the
  perf gate is set at 250 ms because a 30 ms gate would flake on a ±12% spread (Cases 4 and 5).
- **Half B — the combinations section.** A second report section listing **up to 11 propositions**
  (one minimal ask per surviving multi-lever subset), each confirmed by a real engine re-run, each
  passed by a **unified all-four-lever joint plausibility gate**, distinct **by construction** (one
  per subset), with the smallest total ask **labelled**. **There is no top-3 cut and no ranking** —
  Roger: *"with a 'cheapest total negotiation' alongside the others, we have no more need for a
  ranking"* (Cases 11–15). AD's real job here is **direction**: one dual pass per analysis picks
  which way to walk; bisection still decides how far.
- **Half B — the margin-of-safety section** ("How wrong can these guesses be?"), which was **not in
  the charter** and is new scope: how far a *guess* (vacancy, rent growth, expense growth) can drift
  before a currently-passing guardrail stops passing (Case 10).
- Plus the horizon cap raised to 100, lower bounds on money fields, and a clean message instead of a
  traceback for an out-of-range horizon (Cases 7–9).

---

## Prerequisites (do this once)

1. `cd /home/rtokime/projects/Personal/ai-real-estate-deal-analyzer`
2. `source /home/rtokime/anaconda3/etc/profile.d/conda.sh && conda activate airedeal`
   **Do not use `~/miniconda3` — it does not exist on this machine and some shells silently fall back to
   a different, wrong Python. Use the `anaconda3` path above, exactly.**
3. `which python` → must print `/home/rtokime/anaconda3/envs/airedeal/bin/python`. If not, stop and fix
   your shell before running anything below.
4. `git branch --show-current` → `mission/5-forward-mode-differentiation` (or `main`, once merged).
5. **Start from an EMPTY output directory:** `rm -rf /tmp/m5 && mkdir -p /tmp/m5 && export OUT=/tmp/m5`.
   Not housekeeping — several cases `grep` a report a previous command was supposed to have just written;
   an empty dir makes a failed run error loudly instead of a stale file passing silently.
6. Sample deals used below (confirm they exist):
   - `export NEARMISS_CFG=data/sample_listings/82_champlain_dieppe/inputs.json` — a **DECLINE that fails
     3 of the 6 live guardrails** (`dscr`, `spread`, `coc`), exactly the "genuinely close" boundary
     (`GENUINELY_CLOSE_MAX_FAILS = 3`), so it grows the full recourse section.
   - `export FAR_CFG=data/sample_listings/36_kelly_moncton/inputs.json` — a DECLINE that fails 4
     guardrails, one past the gate; used to show the section correctly staying absent.
   - `ls -l "$NEARMISS_CFG" "$FAR_CFG"` → both must resolve to real files before you run anything.
7. The report CLI is `python main.py --config <inputs.json> --out <file> [--horizon N]`. Only
   `python main.py`'s deterministic/CrewAI paths compute recourse (`deal-report`/`deal-advisor` do not).
8. **Every `python - <<'PY' … PY` block below must be run from the repository root**, so `src/` and
   `tests/` are importable. That is the only requirement; nothing here needs `PYTHONPATH` set by hand
   except Case 1, which says so explicitly.

---

## Case 1 — The tolerance harness still CATCHES the calibration bug (nine-nines, anchored to origin)

**Goal:** Prove the relaxed golden rule is tight enough: an ordinary money-rounding bug still FAILS the
build, while legitimate floating-point-reordering drift PASSES silently — and the near-breach band in
between fails LOUDLY instead of going quietly green.

> **✅ SHIPPED — run this now.**

> **⚠️ PROCEDURE CORRECTED 2026-08-31 (orchestrator), discharging guardian condition C4(a).** The
> charter's original steps 1 and 2 both said *"perturb one golden number."* **That procedure cannot
> produce the result it asks for, and it teaches the wrong habit.** Two reasons, both verified: (i)
> under the shipped anchor design the golden's `cases` subtree is digest-pinned, so editing a golden
> number trips the *anchor* test first, with a different error — Roger would never see the "exceeds
> tolerance" message the criterion asks him to observe (this is demonstrated on purpose in **Case 2**);
> (ii) more importantly, **perturbing the golden to test the tolerance teaches editing the anchor**,
> which is step one of the ratchet the anchor exists to prevent. Every step below perturbs the
> **computed side** and **never touches the golden file**.

**Step 0 — the injector.** One throwaway pytest plugin, written into `$OUT`, that monkeypatches
`src.core.finance.amortization.amortization_payment` (the most-amplified intermediate in the engine).
It patches the *computed* path only; the golden file is never opened, let alone written.

```bash
cat > "$OUT/inject_defect.py" <<'PY'
"""pytest plugin: inject a defect into the COMPUTED side (never the golden)."""
import os
from unittest import mock
import src.core.finance.amortization as amortization

_orig = amortization.amortization_payment
_MODE = os.environ.get("DEFECT", "none")

def _patched(principal, rate, years):
    v = _orig(principal, rate, years)
    if _MODE == "round4":
        return round(v, 4)
    if _MODE == "round6":
        return round(v, 6)
    if _MODE == "ulp":
        import math
        return math.nextafter(v, math.inf)
    return v

def pytest_configure(config):
    if _MODE == "none":
        return
    p = mock.patch.object(amortization, "amortization_payment", side_effect=_patched)
    p.start()
    config.add_cleanup(p.stop)
PY
```

**Steps 1–3 — run the harness under each injected defect.**

```bash
for M in round4 ulp round6; do
  echo "===== DEFECT=$M ====="
  DEFECT=$M PYTHONPATH=$OUT python -m pytest tests/core/finance/test_golden_forecasts.py \
      --no-cov -p inject_defect > "$OUT/$M.log" 2>&1; echo "exit=$?"
  echo "EXCEEDS-cases:     $(grep -c 'EXCEEDS TOLERANCE' "$OUT/$M.log")"
  echo "APPROACHING-cases: $(grep -c 'APPROACHING TOLERANCE, unjustified' "$OUT/$M.log")"
  grep -E "^[0-9]+ (failed|passed)" "$OUT/$M.log" | tail -1
done
```

**Observed (orchestrator, 2026-08-31):**
```
===== DEFECT=round4 =====
exit=1
EXCEEDS-cases:     31
APPROACHING-cases: 30
32 failed, 6 passed in 0.17s
===== DEFECT=ulp =====
exit=0
EXCEEDS-cases:     0
APPROACHING-cases: 0
38 passed in 0.08s
===== DEFECT=round6 =====
exit=1
EXCEEDS-cases:     0
APPROACHING-cases: 5
5 failed, 33 passed in 0.11s
```

Read it as three sentences. **`round4`** — someone rounded a money figure to four decimals — is
**caught**, 31 cases naming "EXCEEDS TOLERANCE". **`ulp`** — a single unit-in-the-last-place, which is
exactly the class AD's dual-number threading produces — **passes silently, all 38 green**. **`round6`**
— a drift at 98% of the budget, still technically inside it — **fails the build anyway** with the
approaching-tolerance state demanding written justification, rather than sliding through green.

**Step 4 — the four walls, measured end-to-end.** This is where the numbers behind the rule come from.

```bash
python - <<'PY'
"""The four tolerance walls, measured end-to-end through run_financial_model on the 34-case matrix."""
import json, math
from unittest import mock
import src.core.finance.amortization as amortization
from src.core.finance import run_financial_model
from src.schemas.models import FinancialInputs, ListingInsights
from tests.core.finance.golden_cases import CASES
from tests.core.finance.golden_tolerance import GOLDEN_PATH, REL_TOL, compare_golden

golden = json.loads(GOLDEN_PATH.read_text())["cases"]
orig = amortization.amortization_payment

def measure(patch):
    mx, over9, over6 = 0.0, 0, 0
    with mock.patch.object(amortization, "amortization_payment", side_effect=patch):
        for c in CASES:
            fi = FinancialInputs.model_validate(c["financial_inputs"])
            ins = ListingInsights.model_validate(c["insights"]) if c.get("insights") else None
            actual = run_financial_model(fi, horizon_years=c["horizon_years"], insights=ins).model_dump(mode="json")
            rep = compare_golden(c["id"], actual, golden[c["id"]]["forecast"])
            for rel in rep.float_rel_drift.values():
                mx = max(mx, rel)
                over9 += rel >= REL_TOL
                over6 += rel >= 1e-6
    return mx, over9, over6

print(f"{'injected into the COMPUTED side':<34} {'max rel drift':>14}  {'fields past 1e-9':>16}  {'past a naive 1e-6':>18}")
for label, fn in (
    ("1 ULP (the reordering floor)",      lambda p, r, y: math.nextafter(orig(p, r, y), math.inf)),
    ("round(payment, 6)",                 lambda p, r, y: round(orig(p, r, y), 6)),
    ("round(payment, 4)  <- the defect",  lambda p, r, y: round(orig(p, r, y), 4)),
    ("x (1 + 9.4e-8)  <- the contract",   lambda p, r, y: orig(p, r, y) * (1 + 9.4e-8)),
):
    mx, o9, o6 = measure(fn)
    print(f"{label:<34} {mx:14.4e}  {o9:16d}  {o6:18d}")
print(f"\nREL_TOL = {REL_TOL:.0e}")
PY
```

**Observed (orchestrator, 2026-08-31):**
```
injected into the COMPUTED side     max rel drift  fields past 1e-9   past a naive 1e-6
1 ULP (the reordering floor)           1.1510e-13                 0                   0
round(payment, 6)                      9.7904e-10                 0                   0
round(payment, 4)  <- the defect       1.1325e-07              1613                   0
x (1 + 9.4e-8)  <- the contract        1.3477e-05              2958                 122

REL_TOL = 1e-09
```

**The whole calibration argument is in the last two columns.** `round(payment, 4)` moves **1,613
fields past 1e-9 and exactly ZERO past 1e-6.** A harness with a 1e-6 tolerance would have shipped that
bug and reported all green. That is why the rule is 1e-9 and not 1e-6, and it is a measurement, not a
preference. The floor (1.1510e-13) sits ~8,700× below the tolerance; the defect sits ~113× above it.

**On the "~9.4e-8" figure named in the charter:** it is a **contract figure, not a prior measurement.**
`git log --all -S"9.4e-8"` returns exactly one commit — the Mission 5 charter itself — so no earlier
measurement of it exists in this repo. It stands as a contract constant bound to the reproducible
`round(payment, 4)` recipe above, whose real measured signature is **1.1325e-7**. (Row 4 of the table
shows the literal `×(1 + 9.4e-8)` injection for completeness: 1.3477e-5 end-to-end.) The calibration
*logic* — 1e-9 catches this class, 1e-6 does not — is measured, reproduced, and sound; only the
specific number lacked provenance, and this is said out loud rather than quietly kept.

**Pass/fail criterion (checkable by eye in under a minute):** in the first transcript, `round4` says
**exit=1 with EXCEEDS-cases ≥ 1**; `ulp` says **exit=0, all passed, zero of both counters**; `round6`
says **exit=1 with EXCEEDS 0 but APPROACHING ≥ 1**. In the second, the **"past a naive 1e-6" column
reads 0 on the `round(payment, 4)` row.** All four = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-09-01
**Actual result observed:** round4 exit=1 (EXCEEDS 31, APPROACHING 30; 32 failed, 6 passed); ulp exit=0 (38 passed, 0 of both counters); round6 exit=1 (EXCEEDS 0, APPROACHING 5). Walls table reproduced exactly: 1 ULP 1.1510e-13; round(.,6) 9.7904e-10; round(.,4) 1.1325e-07 with 1613 fields past 1e-9 and **0 past a naive 1e-6**; x(1+9.4e-8) 1.3477e-05. REL_TOL = 1e-09.

---

## Case 2 — Drift cannot ratchet: the golden is digest-pinned, and regeneration REFUSES numeric drift

**Goal:** Prove a *sequence* of small, individually-passing edits cannot creep the shipped numbers away
from the truth — because the golden file cannot move at all without a named human approving it.

> **✅ SHIPPED — run this now.** _This case deliberately hand-edits a committed file and then
> restores it. The restore is part of the case and is verified, not assumed._

> **⚠️ SCOPE CORRECTED 2026-08-31 (orchestrator).** The charter asked for "two successive ~6e-10 drifts
> that must surface as a cumulative ~1.2e-9." **That demonstration cannot exist on this tree, and its
> absence is the stronger result:** there is no way to apply a first drift and keep it, because the
> golden cannot be regenerated to absorb it. The anti-ratchet is enforced one step earlier than the
> charter imagined — at the *write*, not at the *comparison*. What is demonstrated below is that
> earlier, harder guarantee, plus the cumulative-drift budget that governs the only sanctioned way the
> golden ever moves.

```bash
echo "=== 0. baseline: anchor test green ==="
python -m pytest tests/core/finance/test_golden_anchor.py --no-cov 2>&1 | tail -2

echo "=== 1. hand-edit ONE golden number (a 6e-10 relative nudge: individually UNDER 1e-9) ==="
python - <<'PY'
import json, pathlib
p = pathlib.Path("tests/data/golden/finance_engine_forecasts.json")
g = json.loads(p.read_text())
v = g["cases"]["sample_deal_36_kelly_moncton"]["forecast"]["purchase"]["dscr"]
g["cases"]["sample_deal_36_kelly_moncton"]["forecast"]["purchase"]["dscr"] = v * (1 + 6e-10)
p.write_text(json.dumps(g, indent=2, sort_keys=True) + "\n")
print(f"dscr {v!r} -> {v*(1+6e-10)!r}  (relative nudge 6.0e-10, i.e. 60% of REL_TOL)")
PY

echo "=== 2. the ANCHOR test fires, with its OWN distinct message ==="
python -m pytest tests/core/finance/test_golden_anchor.py --no-cov 2>&1 \
  | grep -E "^E .*(ANCHOR DIGEST MISMATCH|anchor says|golden is now|ratchet)" | head -4
python -m pytest tests/core/finance/test_golden_anchor.py --no-cov 2>&1 | grep -E "failed" | tail -1

echo "=== 3. a BARE regeneration REFUSES to absorb the drift ==="
python -m tests.core.finance.generate_golden_forecasts; echo "exit=$?"

echo "=== 4. --supersede-anchor without a written rationale / a named approver is refused ==="
python -m tests.core.finance.generate_golden_forecasts --supersede-anchor; echo "exit=$?"
python -m tests.core.finance.generate_golden_forecasts --supersede-anchor --rationale "speed"; echo "exit=$?"

echo "=== 5. RESTORE the golden, and PROVE it was restored ==="
git checkout -- tests/data/golden/finance_engine_forecasts.json
git status --porcelain tests/data/golden/
sha256sum tests/data/golden/finance_engine_forecasts.json
python -m pytest tests/core/finance/test_golden_anchor.py tests/core/finance/test_golden_forecasts.py --no-cov 2>&1 | tail -2
```

**Observed (orchestrator, 2026-08-31):**
```
=== 0. baseline: anchor test green ===
......                                                                   [100%]
6 passed in 0.04s
=== 1. hand-edit ONE golden number (a 6e-10 relative nudge: individually UNDER 1e-9) ===
dscr 0.8959640540190189 -> 0.8959640545565973  (relative nudge 6.0e-10, i.e. 60% of REL_TOL)
=== 2. the ANCHOR test fires, with its OWN distinct message ===
E       AssertionError: ANCHOR DIGEST MISMATCH -- tests/data/golden/finance_engine_forecasts.json's `cases` subtree does not match the digest recorded in tests/data/golden/ANCHOR.json.
E           anchor says:   540b3099fd0a7b6764170996008330c025b8102853c5a77ebce2d20b7eec9297
E           golden is now: 5b867bd95a4cfb4fc7337ff70820499f5fc4c99c37c216c6e8c0f6a1eac3c548
E         This means the golden file moved without a reviewed, rationale-carrying `--supersede-anchor` run. Do not edit ANCHOR.json to make this pass -- that is the ratchet this mechanism exists to prevent. Re-run `python -m tests.core.finance.generate_golden_forecasts --supersede-anchor --rationale "..." --approved-by "..."` if this drift is a reviewed, founder-approved decision.
1 failed, 5 passed in 0.06s
=== 3. a BARE regeneration REFUSES to absorb the drift ===
REFUSING TO REGENERATE.

1 pre-existing field(s) changed value:
    sample_deal_36_kelly_moncton::purchase.dscr: approaching, rel_drift=6.0000e-10 -- anchored=0.8959640545565973 new=0.8959640540190189

In-tolerance drift is NEVER a reason to re-anchor -- that is the ratchet this harness exists to prevent. If a number genuinely changed for a reason, that reason is a correctness decision: re-run with --supersede-anchor --rationale "<why>" --approved-by "<name>" and expect it to be reviewed as one.
exit=1
=== 4. --supersede-anchor without a written rationale / a named approver is refused ===
ERROR: --supersede-anchor requires --rationale "<why>".
exit=2
ERROR: --supersede-anchor requires --approved-by "<name>" (GD.1 condition C3).
exit=2
=== 5. RESTORE the golden, and PROVE it was restored ===
?? tests/data/golden/ANCHOR.json
?? tests/data/golden/DRIFT_LEDGER.json
936734c627f16d888b5033e7f9564c198d36bcbbb5367b296f35c13a4d4fa5cc  tests/data/golden/finance_engine_forecasts.json
............................................                             [100%]
44 passed in 0.09s
```

The restore is proven three ways: `git status --porcelain` lists **only the two untracked Mission 5
files and no modification to the golden**; the SHA-256 is back to `936734c6…`; and the 44 anchor +
golden tests are green again.

**And the budget on the only sanctioned path.** Even a founder-approved supersede is not free — every
hop records its drift against its predecessor, and the chain is capped:

```bash
python - <<'PY'
from tests.core.finance.golden_tolerance import CUMULATIVE_DRIFT_BUDGET, cumulative_drift, load_anchor
a = load_anchor(); n = 0; node = a
while node is not None:
    n += 1; node = node.get("supersedes")
print(f"anchor chain length: {n}")
print(f"cumulative drift across the chain: {cumulative_drift(a):.4e}")
print(f"budget: {CUMULATIVE_DRIFT_BUDGET:.4e}  (10 hops at full REL_TOL)")
PY
```

**Observed (orchestrator, 2026-08-31):**
```
anchor chain length: 1
cumulative drift across the chain: 0.0000e+00
budget: 1.0000e-08  (10 hops at full REL_TOL)
```

**Pass/fail criterion (checkable by eye in under a minute):** step 2 fails with the words **"ANCHOR
DIGEST MISMATCH"** (not a tolerance message); step 3 prints **"REFUSING TO REGENERATE"** and exits 1;
step 4 exits 2 twice; step 5's `git status` shows **no modification to the golden** and the tests are
green again. Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-09-01
**Actual result observed:** Baseline anchor green (6 passed). The 6e-10 nudge trips ANCHOR DIGEST MISMATCH, not a tolerance message (1 failed, 5 passed). Bare regeneration prints REFUSING TO REGENERATE, exit=1. --supersede-anchor exits 2 for the missing rationale and again for the missing approver. Restore proven: only the two untracked Mission 5 files in git status, sha256 back to 936734c6…, 44 passed. Anchor chain length 1, cumulative drift 0.0000e+00 against the 1.0000e-08 budget.

---

## Case 3 — THE ANTI-INVERSION CHECK: every shipped number re-derives from a real engine re-run

**Goal:** Prove every recourse number this report prints came from a real, un-differentiated
`run_financial_model` re-run — never a guardrail formula solved backward, never a gradient's guess.
**This is the mission's core honesty claim.** The test is simple: take the numbers off the page, apply
them to the deal file yourself, run the engine, and see if the engine agrees.

> **✅ SHIPPED — run this now.**

**Step 1 — read the report's own claims.**

```bash
python main.py --config "$NEARMISS_CFG" --out "$OUT/nearmiss.md"
grep -n "rent increase.*clears the DSCR" "$OUT/nearmiss.md" | head -1
sed -n '/^| # | Rent /,/^| 2 /p' "$OUT/nearmiss.md"
```

**Observed (orchestrator, 2026-08-31):**
```
115:- **$95.00/unit/month rent increase** → $1,507.50/unit/month (6.73% above current) — clears the DSCR (Y1) bar of 1.20. Also closes: Cash-on-cash (Y1).
| # | Rent ($/unit/month) | Purchase price | Interest rate | Annual opex | Total ask |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | +$90.00 (64%) | -$54,900.00 (60%) | — | — | 1.24 |
| 2 | +$120.00 (85%) | — | -55 bps (55%) | — | 1.40 |
```

**Step 2 — re-derive those numbers independently.** This script never imports
`src.market.recourse`. It edits a plain `dict` loaded from the deal file and calls the public
`run_financial_model` — the same path a completely separate tool would take.

```bash
python - <<'PY'
import json
from src.core.finance import run_financial_model
from src.schemas.models import FinancialInputs

raw = json.loads(open("data/sample_listings/82_champlain_dieppe/inputs.json").read())

def rerun(*, rent=0.0, price_cut=0.0, rate_cut_bps=0.0, opex_cut=0.0):
    d = json.loads(json.dumps(raw["inputs"]))          # plain dict, untouched by recourse code
    for u in d["income"]["units"]:
        u["rent_month"] += rent
    d["financing"]["purchase_price"] -= price_cut
    d["financing"]["interest_rate"] -= rate_cut_bps / 10_000.0
    opex_y1 = sum(d["opex"][k] for k in d["opex"] if k != "expense_growth")
    if opex_cut:
        f = 1.0 - opex_cut / opex_y1
        for k in list(d["opex"]):
            if k != "expense_growth":
                d["opex"][k] *= f
    fc = run_financial_model(FinancialInputs.model_validate(d), horizon_years=raw["run"]["horizon"])
    p = fc.purchase
    return (p.dscr, p.spread_vs_rate*100, (fc.irr_10yr or 0)*100, p.coc*100, fc.years[0].cash_flow, p.cap_rate*100)

hdr = ("DSCR", "spread%", "IRR%", "CoC%", "Y1 CF $", "cap%")
def show(label, v):
    print(f"{label:<44} " + "  ".join(f"{h}={x:,.2f}" for h, x in zip(hdr, v)))

print("BASELINE (no change):")
show("  as listed", rerun())
print()
print('SINGLE LEVER, report says "$95.00/unit/month rent increase clears DSCR (Y1) bar of 1.20":')
for r in (85, 90, 95):
    d = json.loads(json.dumps(raw["inputs"]))
    for u in d["income"]["units"]:
        u["rent_month"] += r
    fc = run_financial_model(FinancialInputs.model_validate(d), horizon_years=10)
    print(f"  rent +${r}: dscr={fc.purchase.dscr:.6f}   clears the 1.20 bar? {fc.purchase.dscr >= 1.20}")
print()
print("COMBINATION 1, report says rent +$90.00 and price -$54,900.00:")
show("  independent re-run", rerun(rent=90, price_cut=54900))
print("COMBINATION 6, report says rate -85 bps and opex -$3,450.00:")
show("  independent re-run", rerun(rate_cut_bps=85, opex_cut=3450))
print("COMBINATION 11, report says rent +$60, price -$37,600, rate -30bps, opex -$1,150:")
show("  independent re-run", rerun(rent=60, price_cut=37600, rate_cut_bps=30, opex_cut=1150))
PY
```

**Observed (orchestrator, 2026-08-31):**
```
BASELINE (no change):
  as listed                                  DSCR=1.10  spread%=0.12  IRR%=12.00  CoC%=2.77  Y1 CF $=3,654.55  cap%=6.92

SINGLE LEVER, report says "$95.00/unit/month rent increase clears DSCR (Y1) bar of 1.20":
  rent +$85: dscr=1.193973   clears the 1.20 bar? False
  rent +$90: dscr=1.199759   clears the 1.20 bar? False
  rent +$95: dscr=1.205545   clears the 1.20 bar? True

COMBINATION 1, report says rent +$90.00 and price -$54,900.00:
  independent re-run                         DSCR=1.32  spread%=1.54  IRR%=17.38  CoC%=9.18  Y1 CF $=11,103.94  cap%=8.34
COMBINATION 6, report says rate -85 bps and opex -$3,450.00:
  independent re-run                         DSCR=1.30  spread%=1.54  IRR%=16.11  CoC%=7.84  Y1 CF $=10,353.54  cap%=7.49
COMBINATION 11, report says rent +$60, price -$37,600, rate -30bps, opex -$1,150:
  independent re-run                         DSCR=1.31  spread%=1.55  IRR%=16.99  CoC%=8.77  Y1 CF $=10,921.59  cap%=8.05
```

**Compare those three rows against the report's own "What the confirming re-runs measured" table
(rows 1, 6, 11): 1.32 / 1.54% / 17.38% / 9.18% / $11,104 / 8.34% — identical, to the digit.**

**And the single-lever line is the sharpest evidence in this document.** At rent +$90 the DSCR is
**1.199759**, which *displays* as 1.20 — and the report does **not** offer it. It offers **+$95**, the
next $5 grid step, where DSCR is genuinely 1.205545. A tool that inverted a formula, or that trusted a
rounded display, would have printed +$90. This one re-ran the engine and believed the engine.

**Pass/fail criterion (checkable by eye in under a minute):** the three combination rows above match
the report's confirming-margins table digit for digit, and the rent ladder shows **+$90 → False,
+$95 → True**, matching the +$95 the report prints. Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-09-01
**Actual result observed:** All three combination re-runs reproduce the recorded values digit for digit (comb 1: DSCR 1.32 / spread 1.54% / IRR 17.38% / CoC 9.18% / Y1 CF $11,103.94 / cap 8.34%; comb 6 and comb 11 likewise). Rent ladder: +$85 → 1.193973 False, +$90 → 1.199759 False, +$95 → 1.205545 True — matching the +$95 the report prints.

---

## Case 4 — What actually decides HOW FAR and WHICH WAY (the AD-Newton framing is superseded)

**Goal:** See where the probes actually go, and see that AD's contribution is one pass per analysis —
not a Newton iteration replacing bisection.

> **✅ SHIPPED — run this now.**

> **⚠️ SUPERSEDED 2026-08-31 (measured, not argued).** The charter's target was "~10–20 probes per
> lever/guardrail → ~3–4, via Newton." **Newton was built, measured, and rejected.** A dual-number pass
> costs ~4× a plain engine pass, so Newton reached each flip in **11–41 probes against bisection's
> fixed ~11** — a wash at best. What shipped: **bisection owns the DISTANCE; the AD gradient owns only
> the DIRECTION**, at a cost of **one** dual pass for an entire analysis. Also note the charter's
> "before" figure of 150 probes on the ceiling row is no longer the comparable number: **Half B's
> combination search is new work that did not exist then**, and it is the reason the probe totals went
> up while the wall-clock went down 6.7× (Case 5). See `docs/plans/MISSION_5_SPRINT_TRACKER.md`
> (D.1, D.2, and "ROGER'S GATE-D DECISION").

```bash
python - <<'PY'
"""What actually decides HOW FAR (bisection) and WHICH WAY (one AD pass) -- counted, not asserted."""
import json
from collections import Counter
import src.market.recourse as R
from src.schemas.models import FinancialInputs

raw = json.loads(open("data/sample_listings/82_champlain_dieppe/inputs.json").read())
fi = FinancialInputs.model_validate(raw["inputs"])

n, halvings = Counter(), {}
orig = {k: getattr(R, k) for k in ("_bisect", "_rerun", "run_financial_model", "forecast_metrics_with_jacobian")}

def counted(key, fn):
    def wrapper(*a, **k):
        n[key] += 1
        return fn(*a, **k)
    return wrapper

def bisect(inputs, lever, guardrail, market, **kw):
    before = n["light"]
    out = orig["_bisect"](inputs, lever, guardrail, market, **kw)
    halvings[(lever, guardrail)] = n["light"] - before
    return out

R._bisect = bisect
R._rerun = counted("light", orig["_rerun"])
R.run_financial_model = counted("full", orig["run_financial_model"])
R.forecast_metrics_with_jacobian = counted("dual", orig["forecast_metrics_with_jacobian"])

R.compute_recourse(fi, horizon_years=10)
print("82_champlain_dieppe, one full compute_recourse (single-lever menu + combinations):")
print(f"  AD dual (Jacobian) passes for the WHOLE analysis : {n['dual']}")
print(f"  light search probes                              : {n['light']}")
print(f"  full confirming run_financial_model re-runs       : {n['full']}")
print()
print("  BISECTION owns the DISTANCE. Halvings spent per single-lever (lever, guardrail) crossing:")
for (lever, guardrail), c in sorted(halvings.items()):
    print(f"    {lever:<20} x {guardrail:<9} : {c} probes")
print(f"  -> {len(halvings)} crossings, {sorted(set(halvings.values()))} probes each -- set by the lever's")
print(f"     own _BISECT_TOL, never by the answer: {dict(R._BISECT_TOL)}")

for k, v in orig.items():
    setattr(R, k, v)
PY
```

**Observed (orchestrator, 2026-08-31):**
```
82_champlain_dieppe, one full compute_recourse (single-lever menu + combinations):
  AD dual (Jacobian) passes for the WHOLE analysis : 1
  light search probes                              : 256
  full confirming run_financial_model re-runs       : 23

  BISECTION owns the DISTANCE. Halvings spent per single-lever (lever, guardrail) crossing:
    annual_opex          x coc       : 8 probes
    annual_opex          x dscr      : 8 probes
    interest_rate        x coc       : 9 probes
    interest_rate        x dscr      : 9 probes
    interest_rate        x spread    : 9 probes
    purchase_price       x coc       : 12 probes
    purchase_price       x dscr      : 12 probes
    purchase_price       x spread    : 12 probes
    rent_per_unit_month  x coc       : 11 probes
    rent_per_unit_month  x dscr      : 11 probes
    rent_per_unit_month  x spread    : 11 probes
  -> 11 crossings, [8, 9, 11, 12] probes each -- set by the lever's
     own _BISECT_TOL, never by the answer: {'rent_per_unit_month': 1.0, 'purchase_price': 100.0, 'interest_rate': 0.0001, 'annual_opex': 50.0}
```

Three things to notice. **One dual pass.** Not one per lever, not one per bisection step — one, for
the whole analysis, feeding all 11 subsets their direction. **The bisection cost is fixed by the
tolerance, not by the answer**: every rent crossing costs exactly 11 probes because
`_BISECT_TOL["rent_per_unit_month"] = $1.00`, and the price lever costs 12 because its tolerance is
$100 over a wider bracket. That is what makes the search deterministic (Case 6). **And 23 full
confirming re-runs** — one per shipped number, which is Case 3's guarantee, priced.

The published benchmark says the same thing at the whole-analysis level:

```bash
python tests/perf/bench_finance_engine.py --repeats 5 | head -8
```

**Observed (orchestrator, 2026-08-31):**
```
PRIMARY -- real compute_recourse(), the production loop. THIS is the cost of an analysis.
                    deal          best/median   probes  by lever                                      verdict
----------------------------------------------------------------------------------------------------------------------
 5,000u / 100y (ceiling)      65.3/    65.5ms      382  annual:38, interest:102, purchase:144, rent:98  <= 250 ms: PASS
                          fails 3 guardrails ('dscr', 'spread', 'irr') -- the gate's limit (GENUINELY_CLOSE_MAX_FAILS=3)
  36_kelly_moncton (10y)       9.9/    10.0ms      213  annual:24, interest:57, purchase:67, rent:65  (real deal, not budgeted)
82_champlain_dieppe (10y)      17.0/    17.1ms      499  annual:112, interest:124, purchase:133, rent:130  (real deal, not budgeted)
```

**The millisecond columns move ±10% run to run; the `probes` column does not.** Probe counts are the
part of this table that is a fact about the code rather than about the machine — if yours differ from
382 / 213 / 499, that is a real change and worth asking about. (Note the ceiling row's failing set is
`dscr`/`spread`/`irr`: that is the synthetic 5,000-unit stress deal, not `82_champlain_dieppe`, whose
failing set is `dscr`/`spread`/`coc`.)

**Pass/fail criterion (checkable by eye in under a minute):** the script reports **exactly 1 AD dual
pass** for a whole analysis, and the per-crossing probe counts are a **small fixed set** (8/9/11/12),
not a per-answer number. The claim being validated is *"AD picks the direction, bisection walks the
distance"* — not the charter's retracted "3–4 Newton steps." Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-09-01
**Actual result observed:** Exactly 1 AD dual (Jacobian) pass for the whole analysis; 256 light search probes; 23 full confirming re-runs. 11 crossings at 8/9/11/12 probes each — a fixed set from each lever's own _BISECT_TOL, not a per-answer number. Bench PRIMARY row: 67.8/67.9 ms on the 5,000u/100y ceiling, ≤ 250 ms PASS.

---

## Case 5 — Speed measured HONESTLY against the 30 ms target (5,000u / 100y)

**Goal:** The real before→after for the institutional ceiling, reported against Roger's 30 ms target.
**A measured near-miss is a result, not a failure — and it is not going to be hidden or re-labelled.**

> **✅ SHIPPED — run this now.**

> **⚠️ THE "AD MAKES IT FAST" PREMISE IS RETRACTED, and so is the charter's "73 ms" baseline.** The
> dominant cost of the ceiling row was never engine arithmetic: it was the rent lever rebuilding a
> 5,000-unit rent roll on every probe, plus garbage collection. **Neither is something AD touches.**
> The measured path to speed was an **aggregate-income seam** (`engine.ShiftedIncome`: the rent probe's
> whole effect on the one aggregate the engine reads is `gsi + 12·N·t`, so it is O(1)) and a **scoped
> GC threshold**. The "73 ms" figure was retracted by Roger himself at
> `docs/manual testing/MISSION_4_MANUAL_TESTING.md:513` — it came from a superseded harness that never
> ran the rent lever. **"30 ms" appears nowhere in the code; it is Roger's stated target, never a
> measurement.**

The A/B below removes both accelerations *in the same process, on the same deal*, so the before and
after are not two different days on two different machines.

```bash
python - <<'PY'
"""A/B the two Mission 5 accelerations on the 5,000u/100y ceiling row, same process, same deal."""
import contextlib, gc
import src.market.recourse as R
from tests.perf.bench_finance_engine import BUDGET_MS, build_gate_limit_inputs, time_analysis

fi, failing = build_gate_limit_inputs(5_000, 100)
print(f"workload: 5,000 units / 100 years, fails {len(failing)} guardrails {sorted(failing)}")

_orig_rerun, _orig_gc = R._rerun, R._search_gc_tuned

def rerun_without_the_seam(perturbed, *, horizon_years, baseline_income, precomputed, rent_shift=0.0):
    """Pre-Mission-5 shape: a rent probe MATERIALISES the whole roll (O(units)) instead of O(1)."""
    if rent_shift != 0.0:
        perturbed = R._perturb(perturbed, "rent_per_unit_month", rent_shift, total_opex_y1=1.0)
        rent_shift = 0.0
    return _orig_rerun(perturbed, horizon_years=horizon_years, baseline_income=baseline_income, precomputed=precomputed)

print(f"\nAFTER  (as shipped: aggregate seam + scoped GC)          ", end="", flush=True)
after_best, after_med = time_analysis(fi, 100, repeats=5)
print(f"best {after_best:6.1f} / median {after_med:6.1f} ms")
shipped = R.compute_recourse(fi, horizon_years=100)

R._rerun = rerun_without_the_seam
R._search_gc_tuned = contextlib.nullcontext
print(f"BEFORE (seam removed, GC left at {gc.get_threshold()})           ", end="", flush=True)
before_best, before_med = time_analysis(fi, 100, repeats=5)
print(f"best {before_best:6.1f} / median {before_med:6.1f} ms")
unaccelerated = R.compute_recourse(fi, horizon_years=100)
R._rerun, R._search_gc_tuned = _orig_rerun, _orig_gc

print(f"\nspeedup: {before_best / after_best:.1f}x   ({before_best:.1f} ms -> {after_best:.1f} ms)")
print(f"budget:  {after_best:.1f} ms <= BUDGET_MS {BUDGET_MS:.0f} -> {'PASS' if after_best <= BUDGET_MS else 'FAIL'}")
print(f"Roger's 30 ms target: {after_best:.1f} ms -> {'MET' if after_best <= 30 else 'NOT MET (short by %.1f ms)' % (after_best - 30)}")
print(f"\nsame ANSWERS either way (the seam changed the cost, not the numbers): {shipped == unaccelerated}")
PY
```

**Observed (orchestrator, 2026-08-31):**
```
workload: 5,000 units / 100 years, fails 3 guardrails ['dscr', 'irr', 'spread']

AFTER  (as shipped: aggregate seam + scoped GC)          best   65.5 / median   66.9 ms
BEFORE (seam removed, GC left at (700, 10, 10))           best  438.3 / median  448.4 ms

speedup: 6.7x   (438.3 ms -> 65.5 ms)
budget:  65.5 ms <= BUDGET_MS 250 -> PASS
Roger's 30 ms target: 65.5 ms -> NOT MET (short by 35.5 ms)

same ANSWERS either way (the seam changed the cost, not the numbers): True
```

**Say it plainly: 30 ms was not reached. 65.5 ms was, from 438 ms.** The last line is the one that
makes the speedup trustworthy — the accelerated and unaccelerated runs produce an **equal**
`RecourseAnalysis`, so nothing was bought by computing less.

_Reproducibility, so you know what "the same result" looks like: the orchestrator ran this A/B twice.
Second run — AFTER best **71.0** ms, BEFORE best **427.4** ms, speedup **6.0×**. The absolute
milliseconds move ~±10% between runs; **the order of magnitude and the ~6× do not**, and neither does
the `same ANSWERS either way: True` line. If your numbers land anywhere in AFTER 60–80 ms / BEFORE
400–460 ms, that is this result._

**And the budget now actually gates.** Before this mission `BUDGET_MS` had no reader outside the
benchmark file: the project measured beautifully and gated nothing. It is now asserted in the default
`pytest` run:

```bash
python -m pytest tests/perf/ --no-cov 2>&1 | tail -2
```

**Observed (orchestrator, 2026-08-31):**
```
.......                                                                  [100%]
7 passed in 1.35s
```

**Why the gate is 250 ms and not 30 ms, stated rather than buried:** dev-box spread is ~±12% and CI
hardware is slower, so a gate set at the measurement would fail on noise instead of on regressions.
What the 250 ms gate actually catches is the loss of the acceleration itself — the A/B above shows
that removing the seam puts the row at 438 ms, **1.75× over the budget**, loudly. The real-deal rows
are gated separately at 40 ms (measured best: kelly 9.8 ms, champlain 16.8 ms).

**Pass/fail criterion (checkable by eye in under a minute):** the A/B prints a **before/after pair
with the after under 250 ms**, the words **"NOT MET"** against the 30 ms target (an honest miss, not a
silent pass), and **`same ANSWERS either way: True`**. `tests/perf/` is green. If the benchmark prints
its "machine was busy" warning, re-run before quoting any number. Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-09-01
**Actual result observed:** AFTER 71.4 / 73.7 ms; BEFORE (seam removed, GC untuned) 459.5 / 492.3 ms → 6.4x. 71.4 ms ≤ BUDGET_MS 250 → PASS. Roger's 30 ms target: NOT MET, short by 41.4 ms. same ANSWERS either way: True. tests/perf/ 7 passed. This box measured slower than the orchestrator's (71.4 vs 65.5 ms after, 459.5 vs 438 ms before); the ratio and every conclusion are unchanged.

---

## Case 6 — Determinism: the same deal, run three times, is byte-identical

**Goal:** Same inputs ⇒ same report, exactly. AD, the combination search and the breakeven search must
not introduce run-to-run wobble — not even at the last decimal place.

> **✅ SHIPPED — run this now.** _(Widened from the charter's two runs of one artifact: it now covers
> the whole report over three runs, AND each of the three Mission 5 analyses at the object level.)_

```bash
for i in 1 2 3; do python main.py --config "$NEARMISS_CFG" --out "$OUT/det_$i.md" >/dev/null; done
sha256sum "$OUT/det_1.md" "$OUT/det_2.md" "$OUT/det_3.md"
diff -q "$OUT/det_1.md" "$OUT/det_2.md" && diff -q "$OUT/det_1.md" "$OUT/det_3.md" && echo "IDENTICAL (3 runs, byte for byte)"
```

**Observed (orchestrator, 2026-08-31):**
```
54c9cc4ff2cec18c0769e88bbb1a502a4ed02d4fc91efe50368b31c29dbf6fe6  /tmp/m5/det_1.md
54c9cc4ff2cec18c0769e88bbb1a502a4ed02d4fc91efe50368b31c29dbf6fe6  /tmp/m5/det_2.md
54c9cc4ff2cec18c0769e88bbb1a502a4ed02d4fc91efe50368b31c29dbf6fe6  /tmp/m5/det_3.md
IDENTICAL (3 runs, byte for byte)
```

**No "modulo timestamps" caveat is needed** — the whole file, provenance appendix included, hashes the
same. Now the same claim one level down, on the analysis objects themselves:

```bash
python - <<'PY'
"""Determinism at the analysis-object level: all three Mission 5 searches, twice, in one process."""
import json
from src.market.breakeven import compute_breakevens
from src.market.recourse import compute_combinations, compute_recourse
from src.schemas.models import FinancialInputs

raw = json.loads(open("data/sample_listings/82_champlain_dieppe/inputs.json").read())
fi = FinancialInputs.model_validate(raw["inputs"])

for name, fn in (("RecourseAnalysis   (single-lever menu)", compute_recourse),
                 ("CombinationAnalysis (Half B propositions)", compute_combinations),
                 ("BreakevenAnalysis  (margin of safety)", compute_breakevens)):
    a, b = fn(fi, horizon_years=10), fn(fi, horizon_years=10)
    print(f"{name:<42} equal: {a == b}   byte-identical JSON: {a.model_dump_json() == b.model_dump_json()}")
PY
```

**Observed (orchestrator, 2026-08-31):**
```
RecourseAnalysis   (single-lever menu)     equal: True   byte-identical JSON: True
CombinationAnalysis (Half B propositions)  equal: True   byte-identical JSON: True
BreakevenAnalysis  (margin of safety)      equal: True   byte-identical JSON: True
```

This is not luck: Case 4 showed the probe schedule is fixed by tolerances rather than by the answer,
so the same deal exhausts at the same probe every time.

**Pass/fail criterion (checkable by eye in under a minute):** **three identical SHA-256s**, `IDENTICAL`
prints, and all three analyses report `equal: True` **and** `byte-identical JSON: True`. Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-09-01
**Actual result observed:** Three identical SHA-256s (54c9cc4ff2cec18c0769e88bbb1a502a4ed02d4fc91efe50368b31c29dbf6fe6 — byte-for-byte the same report the orchestrator produced), IDENTICAL printed, and RecourseAnalysis / CombinationAnalysis / BreakevenAnalysis all equal: True with byte-identical JSON: True.

---

## Case 7 — Open item: a negative purchase price is now REFUSED with a clean message

**Goal:** Money fields reject nonsense instead of accepting it.

> **✅ SHIPPED — run this now.** _(The pre-fix "Before" block is gone: `purchase_price` now
> carries `gt=0`, so it can no longer be demonstrated on this tree.)_

```bash
python - <<'PY'
from src.schemas.models import FinancialInputs
import json
d = json.load(open('data/sample_listings/82_champlain_dieppe/inputs.json'))
fin = dict(d['inputs']['financing']); fin['purchase_price'] = -605000
try:
    FinancialInputs(**{**d['inputs'], 'financing': fin}); print("BUILT OK -- BUG")
except Exception as e:
    print(type(e).__name__); print(str(e).split("For further")[0].strip())
PY
```

**Observed (orchestrator, 2026-08-31):**
```
ValidationError
1 validation error for FinancialInputs
financing.purchase_price
  Input should be greater than 0 [type=greater_than, input_value=-605000, input_type=int]
```
Clean, names the field and the bound, no traceback dump. `purchase_price` is **`gt=0`** (all-cash is
`down_payment_rate=1.0`, never a zero price); the other 16 money fields are **`ge=0`** because zero is
legitimate for each (self-managed unit, vacant unit, absent expense). Pinned by
`tests/unit/test_money_field_bounds.py`.

**Pass/fail criterion:** Negative price is rejected with a readable message; a valid price still builds.
Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-09-01
**Actual result observed:** ValidationError on financing.purchase_price: 'Input should be greater than 0' — names the field and the bound, no traceback. A valid price builds throughout every other case in this run.

---

## Case 8 — Open item: a 100-year horizon is now ACCEPTED (cap raised from 50)

**Goal:** 99-year leases are real; the horizon cap should allow 100.

> **✅ SHIPPED — run this now.** _(The `le=50` "Before" no longer exists on this tree.)_

```bash
python main.py --config "$NEARMISS_CFG" --out "$OUT/h100.md" --horizon 100; echo "exit=$?"
```

**Observed (orchestrator, 2026-08-31):**
```
Running AI Real Estate Deal Analyzer (V3)...
Report written to <OUT>/h100.md
Thesis verdict: DECLINE
exit=0
```
Ratified on provenance that checks out (unlike the 9.4e-8 figure):
`docs/manual testing/MISSION_4_MANUAL_TESTING.md:540-579` — *"a 99-year ground lease is a real
financial instrument."* The founder **explicitly rejected** "the benchmark runs at 100" as
justification: the 5,000u/100y bench row bypasses `RunOptions` entirely, and a stress ceiling is not a
product envelope. Honesty note: under shipped defaults **no guardrail reads past Year 10**, so years
11–100 add table rows without changing the verdict.

**Pass/fail criterion:** 100 accepted and produces a report; 101 rejected. Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-09-01
**Actual result observed:** --horizon 100 accepted: exit=0, report written, verdict DECLINE. --horizon 101 refused.

---

## Case 9 — Open item (edge/failure path): an out-of-range horizon prints a CLEAN message, not a traceback

**Goal:** A bad `--horizon` value should read as one clean line, not a raw pydantic traceback with the
useful part buried at the bottom.

> **✅ SHIPPED — run this now.**

```bash
python main.py --config "$NEARMISS_CFG" --out "$OUT/hbad.md" --horizon 101 2>&1 | tail -6
echo "exit=${PIPESTATUS[0]}"
```

**Observed (orchestrator, 2026-08-31):**
```
Running AI Real Estate Deal Analyzer (V3)...
Forecast horizon must be between 1 and 100 years; got 101.
exit=1
```
One line, **no traceback**, exit 1 — and the bounds are read from the field constraint, never typed as
literals, so the message cannot drift from the schema. **Two further holes were found and folded into
the same defect:** `main.py:256`'s `horizon = args.horizon or 10` **bypassed validation entirely** (and
swallowed a legitimate `0`), and `src/inputs/inputs.py:305-311` **silently ignored** an unparseable
`AIREAL_HORIZON` — which the founder called *worse than a traceback, because the user gets a report at
a horizon they did not choose.* Both now fail loudly. Pinned by
`tests/integration/test_horizon_range_and_cli_message.py`.

**Pass/fail criterion:** Clean single-line message, non-zero exit, no traceback. Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-09-01
**Actual result observed:** 'Forecast horizon must be between 1 and 100 years; got 101.' — one clean line, exit=1, no traceback.

---

## Case 10 — NEW SCOPE: "How wrong can these guesses be?" (margin of safety) never overstates safety

**Goal:** The report's newest section measures how far a *guess* — vacancy, rent growth, expense growth
— can drift before a currently-passing guardrail stops passing. **Its whole risk is telling an investor
they have room they do not have.** This case attacks that from five directions.

> **✅ SHIPPED — run this now.** _(No case existed for this: the breakeven / margin-of-safety section is
> scope added after the charter was written. This case is new, written by the orchestrator.)_

**Step 1 — the section renders, on a real report.**

```bash
grep -n "^## How wrong can these guesses be?" "$OUT/nearmiss.md"
sed -n '/^## How wrong can these guesses be?/,/^\*\*Rent growth/p' "$OUT/nearmiss.md" | tail -12
```

**Observed (orchestrator, 2026-08-31):**
```
210:## How wrong can these guesses be?

**3 of the 6 guardrails this deal is judged against clear their bars at the values you assumed: Projected IRR (10y), Year-1 cash flow, Purchase cap rate.** Each line below is how far ONE of your modeling assumptions can drift the wrong way before that guardrail stops clearing — with everything else held exactly as modeled, and one assumption moving at a time.

**DSCR (Y1), Cap-rate spread, Cash-on-cash (Y1) do not appear below, and their absence is not a pass.** They are already under their bars at these same assumed values, so there is no margin of safety to measure for them: a guardrail that is already failing has no room left to lose. What would have to change about them is a different question, answered under "What would have to change?" above.

**Vacancy — you assumed 5.0%.** More empty units never helps this deal, so each guardrail below was re-tested against it moving the wrong way, out to 100.0% — every unit empty. That is the whole range this assumption has, not a limit of the search.

- **Projected IRR (10y) ≥ 12.00%** — clears until vacancy reaches 5.0%; you assumed 5.0%. **Less than 0.1 percentage points of room** — the confirming re-run there measured 11.98%, below the bar.
- **Year-1 cash flow ≥ $0** — clears until vacancy reaches 10.5%; you assumed 5.0%. **5.5 percentage points of room** — the confirming re-run there measured $-6, below the bar.
- **Purchase cap rate ≥ 5.00%** — clears until vacancy reaches 22.7%; you assumed 5.0%. **17.7 percentage points of room** — the confirming re-run there measured just below the bar, within one display step of it.

**Rent growth — you assumed 3.0% a year.** Slower rent growth never helps this deal, so each guardrail below was re-tested against it moving the wrong way, out to -100.0% a year — rents falling to nothing after year 1. That is the arithmetic floor of this assumption, not a limit of the search.
```

**Step 2 — the four honesty properties, each demonstrated.**

```bash
python - <<'PY'
"""Margin of safety: the three outcomes, the floor rounding, the razor margin and the IRR cliff."""
from collections import Counter
import json
from src.core.reports.generator import _fmt_breakeven_margin, _render_breakeven_row
from src.market.breakeven import DEFAULT_BREAKEVEN_MAX_ITER, compute_breakevens
from src.schemas.models import FinancialInputs
from tests.core.finance.golden_cases import CASES

raw = json.loads(open("data/sample_listings/82_champlain_dieppe/inputs.json").read())
fi = FinancialInputs.model_validate(raw["inputs"])

print("=== 1. THE THREE OUTCOMES ARE DISTINGUISHABLE (full budget of 24) ===")
full = compute_breakevens(fi, horizon_years=10)
print("   ", dict(Counter(r.outcome for r in full.rows)), f"over {len(full.rows)} rows\n")

print("=== 2. A STARVED RUN READS AS 'NOT DETERMINED', NEVER AS SAFETY (max_iter=1) ===")
starved = compute_breakevens(fi, horizon_years=10, max_iter=1)
print("   ", dict(Counter(r.outcome for r in starved.rows)))
row = next(r for r in starved.rows if r.outcome == "undetermined")
line = _render_breakeven_row(row, max_iter=1)
print("    rendered:", line)
for forbidden in ("clears until", "still clears", "of room"):
    print(f'    contains "{forbidden}"? {forbidden in line}')
print()

print("=== 3. THE ROOM IS FLOORED TOWARD YOUR ASSUMPTION, NEVER AWAY FROM IT ===")
for m in (0.0065, 0.0064, 0.0099, 0.0004, 1e-9):
    print(f"    measured margin {m * 100:.4f} pp  ->  {_fmt_breakeven_margin(m)!r}")
print()

print("=== 4. A RAZOR MARGIN NEVER RENDERS AS 0.0 ===")
razor = [r for r in full.rows if r.outcome == "breakeven_found" and r.margin is not None and r.margin * 100 < 0.1]
print(f"    {len(razor)} razor-thin row(s) on this deal; each renders:")
for r in razor:
    print("     ", _render_breakeven_row(r, max_iter=DEFAULT_BREAKEVEN_MAX_ITER)[:150] + " ...")
print()

print("=== 5. THE IRR CLIFF: 'could not compute an IRR at all', never the engine's 0.00% sentinel ===")
cliff_rows, irr_rows, sentinels, skipped = [], 0, 0, 0
for c in CASES:
    try:
        a = compute_breakevens(FinancialInputs.model_validate(c["financial_inputs"]), horizon_years=c["horizon_years"])
    except ValueError:
        skipped += 1
        continue
    for r in a.rows:
        if r.guardrail != "irr" or r.outcome != "breakeven_found":
            continue
        irr_rows += 1
        if r.metric_at_breakeven is None:
            cliff_rows.append((c["id"], r))
        elif r.metric_at_breakeven == 0.0:
            sentinels += 1
print(f"    across the {len(CASES) - skipped} runnable golden cases: {irr_rows} confirmed IRR breakeven rows")
print(f"    {len(cliff_rows)} degrade to 'no computable IRR'; {sentinels} ship the coalesced 0.00% sentinel as a number")
cid, r = cliff_rows[0]
print(f"\n    example ({cid}, {r.assumption}) renders as:")
print("     ", _render_breakeven_row(r, max_iter=DEFAULT_BREAKEVEN_MAX_ITER))
print(f'\n    any cliff row quoting "0.00%"? {any("0.00%" in _render_breakeven_row(r, max_iter=24) for _, r in cliff_rows)}')
PY
```

**Observed (orchestrator, 2026-08-31):**
```
=== 1. THE THREE OUTCOMES ARE DISTINGUISHABLE (full budget of 24) ===
    {'breakeven_found': 5, 'never_breaks_in_range': 4} over 9 rows

=== 2. A STARVED RUN READS AS 'NOT DETERMINED', NEVER AS SAFETY (max_iter=1) ===
    {'undetermined': 5, 'never_breaks_in_range': 4}
    rendered: - **Projected IRR (10y) ≥ 12.00%** — **not determined within budget.** This line used up its budget of 1 model re-run before it could locate the point where vacancy breaks this guardrail, so this run does not know how much room there is. That is not a finding that there is room to spare.
    contains "clears until"? False
    contains "still clears"? False
    contains "of room"? False

=== 3. THE ROOM IS FLOORED TOWARD YOUR ASSUMPTION, NEVER AWAY FROM IT ===
    measured margin 0.6500 pp  ->  '0.6 percentage points of room'
    measured margin 0.6400 pp  ->  '0.6 percentage points of room'
    measured margin 0.9900 pp  ->  '0.9 percentage points of room'
    measured margin 0.0400 pp  ->  'Less than 0.1 percentage points of room'
    measured margin 0.0000 pp  ->  'Less than 0.1 percentage points of room'

=== 4. A RAZOR MARGIN NEVER RENDERS AS 0.0 ===
    3 razor-thin row(s) on this deal; each renders:
      - **Projected IRR (10y) ≥ 12.00%** — clears until vacancy reaches 5.0%; you assumed 5.0%. **Less than 0.1 percentage points of room** — the confirming ...
      - **Projected IRR (10y) ≥ 12.00%** — clears until rent growth falls to 3.0% a year; you assumed 3.0% a year. **Less than 0.1 percentage points of room ...
      - **Projected IRR (10y) ≥ 12.00%** — clears until operating-expense growth reaches 2.0% a year; you assumed 2.0% a year. **Less than 0.1 percentage po ...

=== 5. THE IRR CLIFF: 'could not compute an IRR at all', never the engine's 0.00% sentinel ===
    across the 34 runnable golden cases: 46 confirmed IRR breakeven rows
    15 degrade to 'no computable IRR'; 0 ship the coalesced 0.00% sentinel as a number

    example (units_2_horizon_10, occupancy) renders as:
      - **Projected IRR (10y) ≥ 12.00%** — clears until vacancy reaches 9.7%; you assumed 5.0%. **4.7 percentage points of room** — but this room does not end with the return easing down to the bar: the confirming re-run there could not compute an IRR at all. At that point the deal's projected cash flows no longer admit any rate of return, and the model counts that against this guardrail. The room shown is the distance to where the return stops being computable — not to a measured crossing of the bar.

    any cliff row quoting "0.00%"? False
```

Five separate ways of not overstating safety, in order.

1. **Three outcomes, not two.** The full-budget run finds 5 crossings and proves 4 guardrails never
   break inside the range searched. Those are different claims and they render differently.
2. **A starved search says so.** With a budget of one probe, the five found crossings become
   **`undetermined`** — and the rendered line says *"not determined within budget… That is not a
   finding that there is room to spare."* The words **"clears until," "still clears" and "of room"
   are all absent**, verified mechanically, so an exhausted budget can never be misread as safety.
3. **The room is floored, never rounded.** A measured 0.65 pp renders as **0.6**, not 0.7. `round()`
   would have handed the investor 0.05 pp of room nobody measured; `math.floor` cannot.
4. **A razor margin says "less than 0.1", never "0.0".** All three of this deal's razor rows do —
   "0.0 percentage points of room" reads like a rounding artifact, when the truth is that the deal is
   sitting on the line.
5. **The IRR cliff tells the truth about what happened.** In **15** of the 46 confirmed IRR rows
   across the golden matrix, the confirming re-run at the crossing has **no computable IRR at all** —
   the cash flows admit no rate of return. The engine's internal `0.00%` sentinel is **never** quoted
   as a measurement (0 occurrences), because "measured 0.00%" would tell a reader the return decayed
   gently to the bar when it actually stopped existing.

**Pass/fail criterion (checkable by eye in under a minute):** block 2 shows **`contains "of room"?
False`**; block 3 shows **0.65 pp → "0.6"**; block 4 shows **"Less than 0.1 percentage points"** and
no `0.0`; block 5 shows **0 coalesced sentinels** and a cliff line that says *"could not compute an
IRR at all."* All five = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-09-01
**Actual result observed:** Full budget: 5 breakeven_found / 4 never_breaks_in_range over 9 rows. Starved (max_iter=1): 5 undetermined, rendered as 'not determined within budget' with 'clears until', 'still clears' and 'of room' all absent (False, False, False). Flooring toward the assumption: 0.65pp → '0.6', 0.64pp → '0.6', 0.99pp → '0.9', 0.04pp → 'Less than 0.1', 1e-9 → 'Less than 0.1' — never 0.0. 3 razor-thin rows on this deal. Across the 34 runnable golden cases: 46 confirmed IRR breakeven rows, 15 degrade to 'could not compute an IRR at all', **0** coalesced 0.00% sentinels, no cliff row quoting '0.00%'.

---

> **⚠️ CORRECTED 2026-08-31 — Cases 11–15 no longer describe the charter's "top-3" design.** Roger's
> settled architecture (`docs/plans/MISSION_5_SPRINT_TRACKER.md`, "FINAL HALF B ARCHITECTURE") replaced
> the fixed top-3 with **one minimal-ask proposition per feasible lever subset** — up to **11** (the 15
> non-empty subsets of the 4 levers, minus the 4 singletons Mission 4 already ships as the single-lever
> menu). The **smallest total ask is a LABEL** on one of the already-computed propositions — a provable
> `argmin` over a set that exists regardless, not a separate ranked search — so **no ranking is needed
> at all**. The charter's Lagrangian/KKT method was also superseded (measured as a wash against
> subset-restricted bisection seeded by the AD gradient's direction). The cases below have been
> rewritten by the orchestrator against what shipped.

## Case 11 — Half B: the combinations section renders, and EVERY proposition survives an independent re-run

**Goal:** Prove the second section appears next to the single-lever menu, and that every combination it
lists really does clear every guardrail when the *real* engine re-runs it — not just when the search
said so.

> **✅ SHIPPED — run this now.**

**Step 1 — both sections are on the report, and the far deal correctly has neither.**

```bash
grep -n "^## What would have to change?\|^\*\*If more than one input can move at once\*\*" "$OUT/nearmiss.md"
python main.py --config "$FAR_CFG" --out "$OUT/far.md" >/dev/null
grep -c "^## What would have to change?" "$OUT/far.md"
```

**Observed (orchestrator, 2026-08-31):**
```
97:## What would have to change?
137:**If more than one input can move at once**
0
```

_(The last `grep` anchors on `^## ` deliberately: a plain `grep -c "What would have to change"` returns
**1** on `far.md`, because the margin-of-safety section's lead sentence mentions the other section by
name. Counting headings, not phrases, is what makes the `0` mean what it looks like.)_

The near-miss deal has the single-lever menu **and** the combinations block. `36_kelly_moncton` fails 4
guardrails — one past `GENUINELY_CLOSE_MAX_FAILS = 3` — so it gets **neither**, which is the designed
behaviour, not a bug (Case 12 shows what its combination search would have concluded).

**Step 2 — re-derive all 11 propositions independently.** Same discipline as Case 3: a plain `dict`,
the public `run_financial_model`, and no help from `src.market.recourse` except reading its output.

```bash
python - <<'PY'
"""Re-derive EVERY shipped proposition from a clean dict, through run_financial_model alone."""
import json
from src.core.finance import run_financial_model
from src.market.recourse import compute_combinations
from src.schemas.models import FinancialInputs

raw = json.loads(open("data/sample_listings/82_champlain_dieppe/inputs.json").read())
analysis = compute_combinations(FinancialInputs.model_validate(raw["inputs"]), horizon_years=10)

def independent_rerun(moves):
    """Apply the asks to a PLAIN dict and re-run the engine. No recourse helper is used."""
    d = json.loads(json.dumps(raw["inputs"]))
    opex_y1 = sum(v for k, v in d["opex"].items() if k != "expense_growth")
    for m in moves:
        if m.lever == "rent_per_unit_month":
            for u in d["income"]["units"]:
                u["rent_month"] += m.delta
        elif m.lever == "purchase_price":
            d["financing"]["purchase_price"] += m.delta
        elif m.lever == "interest_rate":
            d["financing"]["interest_rate"] += m.delta
        else:
            f = 1.0 + m.delta / opex_y1
            for k in d["opex"]:
                if k != "expense_growth":
                    d["opex"][k] *= f
    fc = run_financial_model(FinancialInputs.model_validate(d), horizon_years=10)
    p = fc.purchase
    return {"dscr": p.dscr, "spread": p.spread_vs_rate, "irr": fc.irr_10yr or 0.0,
            "coc": p.coc, "cf_y1": fc.years[0].cash_flow, "cap_floor": p.cap_rate}

def fmt(m):
    if m.lever == "rent_per_unit_month":
        return f"rent {m.delta:+,.0f}/mo"
    if m.lever == "purchase_price":
        return f"price {m.delta:+,.0f}"
    if m.lever == "interest_rate":
        return f"rate {m.delta * 10_000:+,.0f}bps"
    return f"opex {m.delta:+,.0f}"

print(f"{'#':>2}  {'lever subset':<19}  {'asks as shipped':<52}  {'clears':>6}  {'margins match':>13}  {'total':>5}")
allok = True
for i, c in enumerate(analysis.combinations, 1):
    subset = "+".join(m.lever.split("_")[0] for m in c.moves)
    asks = ", ".join(fmt(m) for m in c.moves)
    mine = independent_rerun(c.moves)
    clears = all(mine[g.guardrail] >= g.bar for g in c.confirmed_margins)
    same = all(abs(mine[g.guardrail] - g.value) < 1e-9 for g in c.confirmed_margins)
    allok &= clears and same
    star = "  <-- cheapest total" if i - 1 == analysis.cheapest_total_index else ""
    print(f"{i:>2}  {subset:<19}  {asks:<52}  {str(clears):>6}  {str(same):>13}  {c.total_fraction_of_caps:5.3f}{star}")

print(f"\nevery proposition clears every live guardrail on an INDEPENDENT re-run,")
print(f"and every shipped margin reproduces to <1e-9: {allok}")
totals = [c.total_fraction_of_caps for c in analysis.combinations]
print(f"\ndistinct lever subsets: {len({tuple(m.lever for m in c.moves) for c in analysis.combinations})} of {len(analysis.combinations)} propositions -- one each, no duplicates")
print(f"cheapest_total_index = {analysis.cheapest_total_index}; argmin of the totals column = {totals.index(min(totals))}; equal: {analysis.cheapest_total_index == totals.index(min(totals))}")
print(f"totals span {min(totals):.3f} .. {max(totals):.3f}; the listed order is the enumeration order, NOT sorted: {totals != sorted(totals)}")
PY
```

**Observed (orchestrator, 2026-08-31):**
```
 #  lever subset         asks as shipped                                       clears  margins match  total
 1  rent+purchase        rent +90/mo, price -54,900                              True           True  1.242  <-- cheapest total
 2  rent+interest        rent +120/mo, rate -55bps                               True           True  1.400
 3  rent+annual          rent +135/mo, opex -2,550                               True           True  1.575
 4  purchase+interest    price -69,200, rate -50bps                              True           True  1.263
 5  purchase+annual      price -73,900, opex -2,250                              True           True  1.360
 6  interest+annual      rate -85bps, opex -3,450                                True           True  1.687
 7  rent+purchase+interest  rent +70/mo, price -43,600, rate -35bps                 True           True  1.326
 8  rent+purchase+annual  rent +75/mo, price -45,900, opex -1,400                 True           True  1.377
 9  rent+interest+annual  rent +95/mo, rate -45bps, opex -1,800                   True           True  1.559
10  purchase+interest+annual  price -55,000, rate -40bps, opex -1,650                 True           True  1.407
11  rent+purchase+interest+annual  rent +60/mo, price -37,600, rate -30bps, opex -1,150    True           True  1.418

every proposition clears every live guardrail on an INDEPENDENT re-run,
and every shipped margin reproduces to <1e-9: True

distinct lever subsets: 11 of 11 propositions -- one each, no duplicates
cheapest_total_index = 0; argmin of the totals column = 0; equal: True
totals span 1.242 .. 1.687; the listed order is the enumeration order, NOT sorted: True
```

**This one script is the evidence for Cases 11, 13 and 15 at once** — it is re-quoted, with the
relevant column called out, in each. Here the load-bearing column is `clears`: **11 of 11 True**, and
`margins match` **11 of 11 True**, meaning the exact numbers the report prints in its "What the
confirming re-runs measured" table reproduce to within 1e-9 from a completely independent re-run.

**Pass/fail criterion (checkable by eye in under a minute):** both section headings are found on the
near-miss report and neither is on the far one; the `clears` and `margins match` columns are **True on
every row**; the summary line reads **`… reproduces to <1e-9: True`**. Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-09-01
**Actual result observed:** Both headings on the near-miss report (lines 97 and 137); grep -c on the far report returns 0. All 11 propositions: clears True and margins match True on an independent re-run from a plain dict. 'every proposition clears every live guardrail … and every shipped margin reproduces to <1e-9: True'.

---

## Case 12 — Half B: the unified gate REFUSES a bundle that is fine lever-by-lever and implausible together

**Goal:** Prove the plausibility gate judges the **whole bundle**, not each lever alone — so two moves
that each look reasonable but do not hang together as one market story are not offered.

> **✅ SHIPPED — run this now.** The fixture is chosen so the *only* thing that changes between
> "accepted" and "refused" is whether the two asks are judged together.

```bash
python - <<'PY'
"""The unified joint gate: two asks that are each fine ALONE and implausible TOGETHER."""
import json
from src.core.finance import run_financial_model
from src.market.recourse import _baseline_value, _derive_snapshot, _perturb_combo, judge_combination, metrics_of
from src.schemas.models import FinancialInputs

raw = json.loads(open("data/sample_listings/82_champlain_dieppe/inputs.json").read())
fi = FinancialInputs.model_validate(raw["inputs"])
base = run_financial_model(fi, horizon_years=10)
base_m, snap = metrics_of(base), _derive_snapshot(fi, base)
opex_y1 = base.years[0].total_opex
baselines = {lv: _baseline_value(fi, lv, total_opex_y1=opex_y1)
             for lv in ("rent_per_unit_month", "purchase_price", "interest_rate", "annual_opex")}

def judge(**asks):
    signed = {"rent_per_unit_month": asks.get("rent", 0.0), "purchase_price": -asks.get("price_cut", 0.0),
              "interest_rate": -asks.get("rate_cut", 0.0), "annual_opex": -asks.get("opex_cut", 0.0)}
    t = [(lv, abs(v)) for lv, v in signed.items() if v != 0.0]
    target = run_financial_model(_perturb_combo(fi, tuple(t), total_opex_y1=opex_y1), horizon_years=10)
    j = judge_combination(signed, base_metrics=base_m, target_metrics=metrics_of(target),
                          baselines=baselines, snapshot=snap, market=fi.market)
    return j, signed["interest_rate"], metrics_of(target).cap_rate - base_m.cap_rate

for label, kw in [("rate cut of 90 bps, ALONE", dict(rate_cut=0.0090)),
                  ("price cut of $90,000, ALONE", dict(price_cut=90_000)),
                  ("rate cut 90 bps AND price cut $90,000, TOGETHER", dict(rate_cut=0.0090, price_cut=90_000))]:
    j, rate_delta, cap_delta = judge(**kw)
    print(f"{label}")
    print(f"   rate delta {rate_delta:+.4f}   implied-cap delta {cap_delta:+.4f}   |difference| = {abs(rate_delta - cap_delta):.4f}  (rejector bar: 0.0200)")
    print(f"   plausible = {j.plausible}   rules tripped = {list(j.tripped_rules)}")
    for r in j.reasons:
        print(f"   reason: {r}")
    print()
PY
```

**Observed (orchestrator, 2026-08-31):**
```
rate cut of 90 bps, ALONE
   rate delta -0.0090   implied-cap delta +0.0000   |difference| = 0.0090  (rejector bar: 0.0200)
   plausible = True   rules tripped = []

price cut of $90,000, ALONE
   rate delta -0.0000   implied-cap delta +0.0121   |difference| = 0.0121  (rejector bar: 0.0200)
   plausible = True   rules tripped = []

rate cut 90 bps AND price cut $90,000, TOGETHER
   rate delta -0.0090   implied-cap delta +0.0121   |difference| = 0.0211  (rejector bar: 0.0200)
   plausible = False   rules tripped = ['R2']
   reason: a 90 bps rate cut alongside a combination that moves the implied cap rate by +121 bps moves rates and cap apart by 211 bps — more than the 200 bps divergence this project treats as a realistic market hypothesis.
```

**Read the third column.** A 90 bps rate cut alone pushes rates and the implied cap **0.0090** apart —
fine. A $90,000 price cut alone pushes them **0.0121** apart — fine. Together the divergence is
**0.0211**, over the 0.0200 bar, and the bundle is refused. **Neither lever is individually near its
own limit; the refusal comes purely from the joint judgement**, which is the thing Mission 4 could not
do (it judged one lever at a time and had no joint check at all). And the reason is in the investor's
own units — "moves rates and cap apart by 211 bps" — not a rule number.

**And the gate is not decorative — it produces a whole outcome.** On `36_kelly_moncton` the search
completes and proves there is nothing to offer:

```bash
python - <<'PY'
import json
from src.market.recourse import compute_combinations
from src.schemas.models import FinancialInputs

def show(label, a):
    print(label)
    for f in ("outcome", "honest_null", "cheapest_total_index", "subsets_searched", "subsets_infeasible",
              "subsets_edge_infeasible", "subsets_gate_rejected", "subsets_collapsed", "subsets_exhausted", "confirm_failed"):
        print(f"  {f:<24}: {getattr(a, f)}")
    print(f"  {'propositions found':<24}: {len(a.combinations)}\n")

def load(p):
    raw = json.loads(open(p).read())
    return FinancialInputs.model_validate(raw["inputs"]), raw["run"]["horizon"]

champ, ch = load("data/sample_listings/82_champlain_dieppe/inputs.json")
kelly, kh = load("data/sample_listings/36_kelly_moncton/inputs.json")
show("OUTCOME 1 -- 'found'        82_champlain_dieppe, default budget", compute_combinations(champ, horizon_years=ch))
show("OUTCOME 2 -- 'proven_null'  36_kelly_moncton, default budget", compute_combinations(kelly, horizon_years=kh))
show("OUTCOME 3 -- 'undetermined' 82_champlain_dieppe, max_iter=3 (starved)", compute_combinations(champ, horizon_years=ch, max_iter=3))
PY
```

**Observed (orchestrator, 2026-08-31):**
```
OUTCOME 1 -- 'found'        82_champlain_dieppe, default budget
  outcome                 : found
  honest_null             : False
  cheapest_total_index    : 0
  subsets_searched        : 11
  subsets_infeasible      : 0
  subsets_edge_infeasible : 0
  subsets_gate_rejected   : 0
  subsets_collapsed       : 0
  subsets_exhausted       : 0
  confirm_failed          : 0
  propositions found      : 11

OUTCOME 2 -- 'proven_null'  36_kelly_moncton, default budget
  outcome                 : proven_null
  honest_null             : True
  cheapest_total_index    : None
  subsets_searched        : 11
  subsets_infeasible      : 7
  subsets_edge_infeasible : 4
  subsets_gate_rejected   : 0
  subsets_collapsed       : 0
  subsets_exhausted       : 0
  confirm_failed          : 0
  propositions found      : 0

OUTCOME 3 -- 'undetermined' 82_champlain_dieppe, max_iter=3 (starved)
  outcome                 : undetermined
  honest_null             : False
  cheapest_total_index    : None
  subsets_searched        : 11
  subsets_infeasible      : 0
  subsets_edge_infeasible : 0
  subsets_gate_rejected   : 0
  subsets_collapsed       : 0
  subsets_exhausted       : 11
  confirm_failed          : 0
```

**The three outcomes are structurally different and every subset is accounted for in exactly one
bucket.** Kelly's 11 subsets split 7 corner-infeasible (every lever at its cap at once and a guardrail
*still* fails — a real proof within the plausibility box) + 4 edge-infeasible, **0 exhausted**, so
`honest_null` is `True`: *nothing works*. Starve champlain to 3 probes per subset and all 11 land in
`subsets_exhausted` with `outcome='undetermined'` and — critically — **`honest_null=False`**. "We ran
out of budget" is never reported as "nothing can save this deal."

**Pass/fail criterion (checkable by eye in under a minute):** the two singleton asks read
**`plausible = True`** and the bundle of the same two reads **`plausible = False`** with the reason
naming 211 bps against 200; and in the second block, `proven_null` carries **`honest_null: True`**
while `undetermined` carries **`honest_null: False`**. Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-09-01
**Actual result observed:** 90 bps rate cut alone: plausible True (0.0090 divergence). $90,000 price cut alone: plausible True (0.0121). The same two together: plausible False, rules tripped ['R2'], reason naming 211 bps against the 200 bps bar. Outcome block: proven_null carries honest_null True (36_kelly_moncton, 7 infeasible + 4 edge-infeasible); undetermined carries honest_null False (starved, 11 exhausted).

---

## Case 13 — Half B: the propositions are genuinely DIFFERENT routes (distinct by construction)

**Goal:** The listed propositions must be distinct strategies, not near-copies of one bundle.

> **✅ SHIPPED — run Case 11's second script and read the `lever subset` column.** Nothing new to run.

> **⚠️ CORRECTED 2026-08-31.** The charter framed diversity as something a *selection rule* achieves
> after the fact. It is now **structural**: the search solves **one minimal ask per lever subset**, so
> two propositions cannot be near-copies — they are moving different inputs. Distinctness is not
> filtered for; it is the shape of the enumeration. (Discovery D.5 measured the alternative: with
> unrestricted seeds, every start collapses onto the single min-sum optimum. That is exactly the
> failure mode this design removes.)

The `lever subset` column of Case 11's table is the whole argument:

```
 1  rent+purchase                    rent +90/mo, price -54,900
 2  rent+interest                    rent +120/mo, rate -55bps
 3  rent+annual                      rent +135/mo, opex -2,550
 4  purchase+interest                price -69,200, rate -50bps
 5  purchase+annual                  price -73,900, opex -2,250
 6  interest+annual                  rate -85bps, opex -3,450
 7  rent+purchase+interest           rent +70/mo, price -43,600, rate -35bps
 8  rent+purchase+annual             rent +75/mo, price -45,900, opex -1,400
 9  rent+interest+annual             rent +95/mo, rate -45bps, opex -1,800
10  purchase+interest+annual         price -55,000, rate -40bps, opex -1,650
11  rent+purchase+interest+annual    rent +60/mo, price -37,600, rate -30bps, opex -1,150

distinct lever subsets: 11 of 11 propositions -- one each, no duplicates
```

**Every one of the 11 is a different conversation with a different party.** Row 1 is a landlord
conversation plus a seller conversation. Row 6 is a lender conversation plus a vendor conversation —
it does not touch the seller at all. An investor who can only reach the seller reads row 1 or 4; one
who can only reach the lender reads row 2, 4, 6 or 10. That is the point of not ranking them: the tool
cannot know which door is open to you.

**Pass/fail criterion (checkable by eye in under a minute):** the `lever subset` column shows **11
different subsets, no repeats** — confirmed mechanically by the `distinct lever subsets: 11 of 11`
line. Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-09-01
**Actual result observed:** 'distinct lever subsets: 11 of 11 propositions -- one each, no duplicates'; the lever-subset column lists 11 different subsets with no repeats.

---

## Case 14 — Half B: the combination search is DETERMINISTIC

**Goal:** Same deal ⇒ the same propositions, in the same order, every run. The search uses a fixed
enumeration and fixed bisection tolerances, never randomness or a multi-start seed.

> **✅ SHIPPED — covered by Case 6, which was widened to include this.** The commands are there; this
> case exists so Roger can tick the Half B claim separately.

Case 6's evidence, restated for the combinations section specifically:

```
54c9cc4ff2cec18c0769e88bbb1a502a4ed02d4fc91efe50368b31c29dbf6fe6  /tmp/m5/det_1.md
54c9cc4ff2cec18c0769e88bbb1a502a4ed02d4fc91efe50368b31c29dbf6fe6  /tmp/m5/det_2.md
54c9cc4ff2cec18c0769e88bbb1a502a4ed02d4fc91efe50368b31c29dbf6fe6  /tmp/m5/det_3.md
IDENTICAL (3 runs, byte for byte)

CombinationAnalysis (Half B propositions)  equal: True   byte-identical JSON: True
```

Those reports **contain the 11-row propositions table**, so a byte-identical report is a byte-identical
propositions section — including the enumeration order and the cheapest-total label's position. The
mechanism is visible in Case 4: the probe schedule is fixed by `_COMBINATION_RAY_TOL`, not by the
answer, so the same deal spends the same probes in the same order every time. Note the charter's
"multi-start" framing does not apply — **there is no multi-start**: one deterministic solve per subset.

**Pass/fail criterion (checkable by eye in under a minute):** three identical SHA-256s on reports that
contain the propositions table, and `CombinationAnalysis … equal: True`. Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-09-01
**Actual result observed:** Covered by Case 6: three identical SHA-256s (54c9cc4f…) on reports that carry the 11-row propositions table, and CombinationAnalysis equal: True with byte-identical JSON: True.

---

## Case 15 — Half B: "cheapest total negotiation" is a LABEL (an argmin), not a ranking

**Goal:** All surviving propositions are shown, unranked; exactly one — the smallest total ask —
carries the label, and it is verifiably the `argmin` of the set already computed.

> **✅ SHIPPED — run Case 11's second script and read the `total` column and the last three lines.**

> **⚠️ SUPERSEDED 2026-08-31.** The originally-charted parsimony/leximin ranking is **eliminated, not
> re-ordered** — Roger: *"with a 'cheapest total negotiation' alongside the others, we have no more
> need for a ranking."* Every subset's proposition ships; nothing is preferred or suppressed by lever
> count. The designed parsimony order is kept on the shelf (not deleted) as a possible future v2
> opt-in, per the sprint tracker's "Net effect on the mission" table.

Two checks, both in Case 11's output:

```
cheapest_total_index = 0; argmin of the totals column = 0; equal: True
totals span 1.242 .. 1.687; the listed order is the enumeration order, NOT sorted: True
```

`cheapest_total_index` is **recomputed independently** as the `argmin` of the printed `total` column
and the two agree. And the second line is the anti-ranking check: **the totals are NOT in sorted
order** (1.242, 1.400, 1.575, 1.263, …), so the list is genuinely the subset enumeration, not a league
table with the winner at the top.

**And the label reads as a label in the report, with its unit explained:**

```bash
grep -n "smallest total ask" "$OUT/nearmiss.md"
```

**Observed (orchestrator, 2026-08-31):**
```
167:**Combination 1 has the smallest total ask, at 1.24.** That is the arithmetic minimum of the "Total ask" column above — not a ranking of the others, and not a recommendation. "Total ask" adds up the bracketed shares: 1.00 is one input moved all the way to its own realism limit, so a total of 1.24 spread across 2 inputs is a smaller ask on each of them than any one input taken to its limit alone.
```

**HONEST NOTE (orchestrator):** the shipped sentence says **"has the smallest total ask"** — it does
not use the charter's literal phrase "cheapest total negotiation." The behaviour is exactly what was
specified (one labelled `argmin`, no ranking, with the disclaimer "not a ranking of the others, and not
a recommendation" attached), but the wording differs from the charter, and that is stated here rather
than glossed over. If Roger wants the charter's phrase in the rendered report, that is a one-line copy
change, not a design change.

**Pass/fail criterion (checkable by eye in under a minute):** `equal: True` on the argmin check;
**`NOT sorted: True`** (proving there is no ranking); and exactly **one** line in the report carrying
the smallest-total-ask label. Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-09-01
**Actual result observed:** cheapest_total_index = 0, argmin of the totals column = 0, equal: True. Totals span 1.242 .. 1.687 and 'the listed order is the enumeration order, NOT sorted: True'. Exactly one line in the report carries the smallest-total-ask label (line 167).

---

## Case 17 — The guards Gate V added: four things the code now REFUSES to do

**Goal:** Four defects were found *after* the feature work was finished — three by an adversarial code
review, one by a guardian ruling. Each was closed with a guard rather than a patch. This case checks all
four still fire, because a guard nobody exercises is a guard nobody knows is broken.

> **✅ SHIPPED — run each block. Every one must RAISE.**

**17a — A rent figure can no longer be changed behind the model's back.** The review found that mutating
one unit's rent in place moved DSCR by **0.140** with nothing raising: the aggregate the engine had
already cached went stale and no layer could see it. `IncomeModel`/`UnitIncome` are now frozen.

```bash
python - <<'PY'
import json
from src.schemas.models import FinancialInputs
d = json.load(open('data/sample_listings/82_champlain_dieppe/inputs.json'))['inputs']
fi = FinancialInputs(**d)
before = fi.income.units[0].rent_month
try:
    fi.income.units[0].rent_month += 1000.0
    print("MUTATED SILENTLY -- THE GUARD IS GONE")
except Exception as e:
    print(type(e).__name__); print(str(e).split("For further")[0].strip())
print("rent_month unchanged:", fi.income.units[0].rent_month == before)
PY
```

**Observed (orchestrator, 2026-09-01):**
```
ValidationError
1 validation error for UnitIncome
rent_month
  Instance is frozen [type=frozen_instance, input_value=2450.0, input_type=float]
rent_month unchanged: True
```

**17b — An assumption can no longer be smuggled in as a lever.** This is the GD3 invariant, and it is the
one with a founder decision behind it: levers are things an investor *acts on*, assumptions are things
they *guess*. Presenting a solve along an assumption axis as recourse would tell the user to edit an
input until the model reports PASS.

```bash
python -c "
from src.core.finance.partition import assert_disjoint_from_assumptions, LEVER_IMAGE
try:
    assert_disjoint_from_assumptions({'demo': frozenset(LEVER_IMAGE) | {'income.occupancy'}})
    print('NO GUARD FIRED -- the partition is open')
except RuntimeError as e:
    print('RuntimeError:'); print(' '.join(str(e).split())[:300])
"
```

**Observed — a `RuntimeError` naming the escalation path, not a quiet acceptance** (caught and printed, so a clean run shows the message rather than a traceback)**:**
```
GD3 VIOLATION: demo contains ['income.occupancy'], which THE LEVER/ASSUMPTION PARTITION
(GD3, src/core/finance/partition.py) classifies as a MODEL ASSUMPTION (a quantity the
investor guesses), not an INVESTOR LEVER ... Extension of INVESTOR_LEVERS, any seed target,
or any _CoreOverrides/RecourseLever field to reach a MODEL_ASSUMPTIONS path is a FOUNDER
PROXY ESCALATION CITING GD3 -- a rationale string is not a clearance.
```

_This guard has already caught something real: the margin-of-safety feature was built under it, and a
field named `vacancy_ask` was killed at import before it could ship._

**17c — A deal the model cannot describe fails by name, not by accident.** A negative-NOI deal used to
surface as a raw `pydantic.ValidationError` from two layers down. `compute_combinations` is public API
now, so it fails in the module's own words.

```bash
python - <<'PY'
import json
from src.schemas.models import FinancialInputs
from src.market.recourse import compute_recourse
d = json.load(open('data/sample_listings/82_champlain_dieppe/inputs.json'))['inputs']
op = dict(d['opex']); op['taxes'] = op.get('taxes', 0) + 900_000.0
try:
    compute_recourse(FinancialInputs(**{**d, 'opex': op}))
    print("no guard fired")
except ValueError as e:
    print("ValueError:", str(e)[:170])
PY
```

**Observed:**
```
ValueError: cannot derive a recourse market snapshot: this deal's Year 1 purchase cap rate is
negative (-141.8384%), which means Year 1 NOI is negative.
```

**17d — The exhaustiveness claim is now true.** The gate's reason-writer said mypy proved it total; it did
not — a trailing `raise AssertionError` satisfies any return type. It now uses `assert_never`, so adding a
rule without words is a **type error**, not a runtime surprise.

```bash
grep -n "assert_never" src/market/recourse.py
grep -n "typing_extensions" requirements.txt
```
Both must return a line. The second is the one **new declared dependency** of this mission — pydantic
already required it, so nothing extra installs; it is declared because a direct import should not ride an
accidental transitive path.

**Pass/fail criterion:** 17a, 17b and 17c each raise with the message shown, the rent figure is unchanged
after 17a, and both greps in 17d return a line. Yes to all = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-09-01
**Actual result observed:** 17a: ValidationError 'Instance is frozen' on UnitIncome.rent_month, rent_month unchanged: True. 17b: RuntimeError 'GD3 VIOLATION' naming income.occupancy as a model assumption, not an investor lever. 17c: ValueError refusing a recourse snapshot on a negative Year-1 cap rate (-141.8384%). 17d: assert_never present at src/market/recourse.py:1348 and typing_extensions>=4.7.0 pinned at requirements.txt:45.

---

## Case 16 — Whole-suite sanity: tests, formatting, linting, typing, coverage

**Goal:** The quality gate is green with BOTH ruff commands (Mission 4 lesson: `ruff check` alone is not
"ruff clean").

> **✅ SHIPPED — run this now.** Takes about 40 seconds end to end.

```bash
pytest 2>&1 | tail -3
ruff format --check .
ruff check .
mypy .
```

**Observed (orchestrator, 2026-08-31):**
```
Coverage XML written to file coverage.xml
Required test coverage of 80% reached. Total coverage: 89.60%
3560 passed, 1 skipped in 32.89s

263 files already formatted

All checks passed!

Success: no issues found in 261 source files
```

The one skip is a deliberate structural skip, not a disabled test — run `pytest --no-cov -rs` and it
names itself: `tests/core/finance/test_metrics_parity.py:96: insights rebuild income internally; a
precompute is correctly refused here`. Coverage is **89.60%** against a
`--cov-fail-under=80` floor. `pytest --no-cov` is also green (the perf gates in `tests/perf/` are
written to work with coverage tracing on *or* off — see `tests/perf/conftest.py` for why a static
`@pytest.mark.no_cover` would crash under `--no-cov`).

**Pass/fail criterion (checkable by eye in under a minute):** `pytest` green with coverage ≥ 80%;
**both** `ruff format --check` and `ruff check` clean; `mypy .` clean. Yes = PASS.

**Status:** ☑ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☑ Date: 2026-09-01
**Actual result observed:** 3560 passed, 1 skipped; 'Required test coverage of 80% reached. Total coverage: 89.60%'. ruff format --check: 263 files already formatted. ruff check: All checks passed. mypy: Success, no issues found in 261 source files. (Wall time 50.85s on this box vs the recorded 32.89s — timing only.)

---

## What this document does NOT claim

Stated here so nothing above has to be read charitably:

- **The 30 ms target was not met.** 65.5 ms, from 438 ms. Case 5.
- **AD did not make the search faster.** Newton was measured and rejected; the speed came from the
  aggregate-income seam and a scoped GC threshold. AD's shipped job is choosing a direction. Cases 4–5.
- **The "~9.4e-8" calibration figure has no prior measurement in this repo.** It is a contract constant
  bound to the `round(payment, 4)` recipe, whose real signature is 1.1325e-7. Case 1.
- **The charter's "two successive 6e-10 drifts" demonstration does not exist**, because the golden
  cannot be regenerated to absorb the first one. The stronger guarantee is demonstrated instead. Case 2.
- **The rendered label says "has the smallest total ask", not "cheapest total negotiation."** Case 15.
- **Years 11–100 change no verdict** under shipped defaults, because no guardrail reads past Year 10.
  Case 8.

---

_When every case above reads PASS and every box is ticked, flip the document-level box at the top to
VALIDATED. The mission gate cannot be requested until it does._
