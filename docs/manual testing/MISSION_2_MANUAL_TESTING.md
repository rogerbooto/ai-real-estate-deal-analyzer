# Mission 2 — Close the End-to-End Wiring Gaps — Manual Testing Handoff

_Author: mission-planner · Written & spot-run 2026-08-19 against `main @ 8ed9397`._

> ## ⚠ Read this first — the mission's status changed since this doc was requested
>
> This doc was commissioned as an **acceptance test plan for work not yet built** ("these tests
> currently FAIL / demonstrate the defect"). **That premise is out of date.** Ground truth on
> `main` today: **Mission 2 is SHIPPED** — merged as `8b2acf8` ("Merge Mission 2: close the
> end-to-end wiring gaps"), released as **v0.3.0** (`652acd7`), and **`origin/main` is in sync with
> local `main`** (`git rev-list --left-right --count origin/main...main` → `0 0`). The stale
> `ROADMAP_TRACKER.md` §5 still reads "chartered, ready to execute" — its changelog stops at
> 2026-08-03 while the work landed through 2026-08-05 and released later; that stale section is what
> the request was built from. **This is a documentation-drift finding in its own right.**
>
> So this is written as a **verification checklist**, not a red-until-fixed plan. Each case still
> records the **Current behaviour (before)** — the literal defect, so you can see what changed — but
> the **Expected result** is the *shipped* behaviour, which passes today. A handful of items were
> **deliberately deferred** (not shipped) and are marked **DEFERRED** in bold; those are the only
> cases you should expect *not* to be "green," and they double as the real remaining acceptance
> list.

> **Verify the tree before trusting anything below:** `git log --oneline | grep -i "Merge Mission 2"`
> should return `8b2acf8`. If it does not, you are not on the shipped code and this doc does not
> apply.

---

**Overall validation:** ☐ NOT VALIDATED ☐ VALIDATED (Roger, ______) ☐ VALIDATED WITH ISSUES
**Blocking issues found:** ______________________________________________

---

## Prerequisites (do this once)

1. `cd /home/rtokime/projects/Personal/ai-real-estate-deal-analyzer`
2. `source /home/rtokime/anaconda3/etc/profile.d/conda.sh && conda activate airedeal`
3. `which python` → must be `/home/rtokime/anaconda3/envs/airedeal/bin/python`
4. `git log --oneline -1` → `8ed9397` or later; `git status --porcelain` → clean.
5. `mkdir -p /tmp/m2 && OUT=/tmp/m2`

The CLIs are: `ingest-listing` (ingest a listing), `deal-report` (render a report from JSON),
`deal-advisor` (rank deals). All resolve on `PATH` after `conda activate airedeal`.

---
---

# WAVE 0 — Truth (false report claims + dependency hygiene)

## W0.1 — Finding F1: the cap-rate floor is real, and the report says so honestly

**Goal:** The engine now emits a real "cap rate below floor" signal, the strategist consumes it, and
the report names the actual cap and floor instead of an unconditional boast.

**Current behaviour (before):** `cap_rate_floor` was read by zero lines, so the thesis rationale
printed **"Purchase cap rate respects the floor policy."** for *every* deal — including configs with
no floor set at all — and one of the DECLINE inputs was permanently dead.

**Command(s)**
```
python main.py --out $OUT/rep.md
grep -n -i "floor" $OUT/rep.md
```

**Expected result** — instead of the old boast, the report reads (line ~94):
```
- Purchase cap rate is 6.35% (≥ the 5.00% floor you set).
```
naming both numbers, and the Run Provenance appendix shows `| Cap-rate floor | 5.00% |
`market.cap_rate_floor` |`. A deal whose purchase cap fell **below** the floor would instead get a
real breach warning that feeds the DECLINE path.

**Pass/fail criterion:** Does the floor line name both the actual cap **and** the floor value,
rather than the old unconditional "respects the floor policy"? Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W0.2 — Finding F2: a listing without financials refuses to borrow the demo deal's numbers

**Goal:** Passing `--listing`/`--photos` without `--config` now loud-fails instead of silently
underwriting your property against the built-in demo deal's price and rent roll.

**Current behaviour (before):** `--listing other.txt` with no `--config` fell through to
`36_kelly_moncton/inputs.json`, so the report described *your* address against *36 Kelly's* purchase
price, financing and rent roll — silently, with no line admitting the mismatch.

**Command(s)**
```
python main.py --listing data/sample_listings/47_perrot_shediac/listing.txt --out $OUT/x.md ; echo "exit=$?"
```

**Expected result** — exits non-zero (1) with:
```
--listing supplied without --config. The financials would then come from the built-in demo deal
(data/sample_listings/36_kelly_moncton/inputs.json) rather than from your property … Pass --config
pointing at a JSON that describes the same property …, or run `python main.py` with no arguments …
```
Happy path still works: `python main.py --config data/sample_listings/36_kelly_moncton/inputs.json
--listing data/sample_listings/36_kelly_moncton/listing.txt --out $OUT/ok.md` succeeds (a
user-chosen, matching pairing is legitimate).

**Pass/fail criterion:** Does the asset-without-config run refuse loudly, and the matching pairing
succeed? Yes = PASS.

> **⚠ Partial by design — the env vector is DEFERRED (a real remaining gap).**
> Setting `AIREAL_LISTING=<other>` / `AIREAL_PHOTOS=<other>` with **no `--config`** still reaches
> the same defect, because those env vars are applied *after* the guard runs. This was consciously
> left open (constraining a documented env contract is a separate follow-on). Do not expect the env
> form to refuse. Reproduce the still-open behaviour with:
> `AIREAL_LISTING=data/sample_listings/47_perrot_shediac/listing.txt python main.py --out $OUT/env.md`
> — it produces a report (the Run Provenance appendix does at least name the inputs file used).

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W0.3 — Finding F7: `lxml` is a declared dependency, at a secure floor

**Goal:** `lxml` (named explicitly by BeautifulSoup in the fetch/normalize code) is now declared,
not merely pulled in transitively, and pinned above the CVE-2026-41066 range.

**Current behaviour (before):** `lxml` was undeclared; 8 `BeautifulSoup(..., "lxml")` sites relied
on it arriving transitively.

**Command(s)**
```
grep -n "lxml" requirements.txt
```

**Expected result:** a comment explaining it was transitive-only, then `lxml>=6.1.0` (the floor
Roger directed be raised so the known-vulnerable `< 6.1.0` range is excluded).

**Pass/fail criterion:** Is `lxml>=6.1.0` present in `requirements.txt`? Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W0.4 — Finding F8: a failed page render warns instead of silently continuing

**Goal:** When `--render` fails, the fetcher now emits a warning/signal instead of swallowing the
exception and continuing as if nothing happened; `playwright` is declared as an optional `render`
extra.

**Current behaviour (before):** `except Exception: rendered_bytes = None` silently discarded a
render failure at two sites, so a `--render` run could proceed with no rendered content and no word
to the user.

**Command(s)** (the render path needs `playwright` + a live URL, which this offline checkout does
not exercise; the fix is pinned by tests — run those):
```
python -m pytest tests/ -k "render and (warn or swallow or fetch)" --no-cov -q
grep -n "playwright" requirements*.txt pyproject.toml 2>/dev/null
```

**Expected result:** the render-warning tests pass (they assert a warning is now raised on a failed
render; reverting the fix makes them fail — proven RED-on-revert in the mission record). `playwright`
appears only as an optional extra, not a hard runtime requirement.

**Pass/fail criterion:** Do the render-path tests pass and `playwright` show up only as optional?
Yes = PASS. (If you have `playwright` + network, a real failed `--render` should print a warning.)

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W0.5 — Finding F9: `onnxruntime` is documented as an optional opt-in provider (docs only)

**Goal:** The ONNX bring-your-own-model provider is documented as Python-API-only and optional — no
code change, just honest docs.

**Current behaviour (before):** `onnxruntime` was undeclared and the ONNX provider was undocumented
as opt-in; a reader could think it was wired into a CLI (it is not — zero callers).

**Command(s)**
```
grep -n -i "onnx" README.md src/core/README.md
```

**Expected result:** prose stating the ONNX provider is registered via the Python API
(`register_onnx_provider`), is not reachable from any CLI, and raises a clear error if `onnxruntime`
is absent.

**Pass/fail criterion:** Do the docs describe ONNX as an optional, Python-API-only provider?
Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---
---

# WAVE 1 — Wiring + anti-regression guard

## W1.1 — Finding F3: OPEX-adjustment explanations can now reach the report

**Goal:** The report renders `YearBreakdown.notes` (an "Adjustments Applied" section) so a reader
sees *why* an expense changed, instead of the note being computed and dropped.

**Current behaviour (before):** the generator rendered `insights.notes` and `analysis.notes` but
never `forecast.years[*].notes`, so OPEX-mutation explanations never shipped.

> **⚠ Honesty caveat you must know before testing (documented defect #4).** On real pipeline data
> the section is **currently empty**, because the engine's OPEX-adjustment triggers test
> pre-normalization strings (`"old roof"`, `"water stain"`) that the CV layer normalizes away before
> the engine sees them. F3 renders whatever the engine puts in `notes`; today, on real data, that is
> nothing. So the demo report is byte-identical before/after F3. The rendering is correct; the
> upstream trigger/label mismatch is a logged follow-on, not a Mission 2 fix.

**Command(s)** (prove the renderer works using a hand-built forecast that trips the triggers — the
mission verified this programmatically):
```
python -m pytest tests/core/reports/test_generator_field_guard.py --no-cov -q
```

**Expected result:** the generator field-guard tests pass, including the one that constructs a
forecast with year notes and asserts they render under "Adjustments Applied."

**Pass/fail criterion:** Do the generator guard tests pass? Yes = PASS. (Do **not** expect the
section to appear in `python main.py` output — see the caveat.)

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W1.2 — Finding F4: synthesized listing insights carry every stated fact

**Goal:** `synthesize_listing_insights` now carries `title/price/sqft/bedrooms/bathrooms/year_built`
through, not just address/amenities/tags/defects.

**Current behaviour (before):** those six fields were dropped in synthesis — the canonical instance
of "transforms rebuild models field-by-field and silently lose new fields."

**Command(s)**
```
ingest-listing --file data/sample_listings/47_perrot_shediac/listing.txt 2>&1 | grep -A1 "listing insights:"
```

**Expected result:**
```
listing insights:
address='47 Perrot Street, E4P 0H3, NB, CA', title='47 Perrot Street, Shediac', price=219900.0,
sqft=1016, bedrooms=3.0, bathrooms=1.0, year_built=2015, amenities=2, condition_tags=0, defects=0,
notes=3
```
— all six stated facts are present and populated.

**Pass/fail criterion:** Are `title/price/sqft/bedrooms/bathrooms/year_built` all shown with real
values? Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W1.3 — Findings F5 & F6: the crewai engine and the report CLI stop dropping media sections

**Goal:** F5 — the crewai runner now sets `media_insights`/`media_report` on its result (so
`--engine crewai` no longer drops two report sections). F6 — `report_cli` now passes `media_report`
and `provenance` to `write_report`, so its output is comparable to `main.py`.

**Current behaviour (before):** the crewai path returned a result missing both media fields; the
report CLI omitted `media_report` and `provenance` even though the signature accepts them.

**Command(s)** (both are pinned by RED-on-revert tests; run them):
```
python -m pytest tests/orchestrators/test_orchestration_result_field_guard.py --no-cov -q
deal-report --help | grep -E "media-report|provenance"
```

**Expected result:** the orchestration-result field-guard tests pass; `deal-report --help` lists
both `--media-report` and `--provenance` options.

**Pass/fail criterion:** Do the guard tests pass and both flags appear in `deal-report --help`?
Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W1.4 — Root cause 2: the anti-regression field-drop guard exists and works

**Goal:** A guard test constructs each source model with every field non-default, pushes it through
each transform, and fails if any field reverts to default — so this whole class of silent drop
cannot recur unnoticed.

**Current behaviour (before):** nothing tested end-to-end reachability; a newly-added schema field
could be silently dropped by any transform with no test going red.

**Command(s)**
```
python -m pytest tests/orchestrators/test_orchestration_result_field_guard.py tests/integration/test_listing_analyst_field_guard.py tests/core/reports/test_generator_field_guard.py tests/core/insights/test_synthesis_field_guard.py --no-cov -q
```

**Expected result:** all guard tests pass (24 collected in the set the planner ran). The guard
enumerates model fields dynamically, so it cannot itself carry the defect it guards against.

**Pass/fail criterion:** Do all four guard suites pass? Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---
---

# WAVE 2 — CLI honesty + docs

## W2.1 — Finding F10: `ingest-listing` prints the insights it computes

**Goal:** The ingest CLI now surfaces `result.insights` and `result.photos` instead of computing
them and printing nothing.

**Current behaviour (before):** `--photos` computed photo insights and a synthesized
`ListingInsights`, but the CLI never printed either — the work vanished.

**Command(s)**
```
ingest-listing --file data/sample_listings/47_perrot_shediac/listing.txt 2>&1 | grep -E "listing insights:|photo insights:"
```

**Expected result:** both `listing insights:` and `photo insights:` summary lines appear (full JSON
is available under `--pretty 1`).

**Pass/fail criterion:** Are both summary lines printed? Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W2.2 — Finding F11: media flags in `--file` mode explain their limitation instead of no-op'ing

**Goal:** `--download-media/--max-media/--media-kinds/--media-intel` with `--file` now print a clear
note that they need an HTML source, instead of silently producing an empty media bundle.

**Current behaviour (before):** those flags were inert in `--file` mode with no explanation — the
user thought media intelligence ran when it did not.

**Command(s)**
```
ingest-listing --file data/sample_listings/47_perrot_shediac/listing.txt --download-media 1 2>&1 | head -2
```

**Expected result:** the first line is a note:
```
note: --download-media/--max-media/--media-kinds/--media-intel require an HTML source (--url) to
scan for media links; --file input alone yields an empty media bundle. Use --photos for a local
photo directory instead.
```

**Pass/fail criterion:** Is the limitation stated explicitly? Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W2.3 — Finding F12: `deal-advisor --debug` actually does something

**Goal:** `--debug` now prints the full ranked/portfolio JSON payload (the help text already
promised it; the promise was never honoured).

**Current behaviour (before):** `--debug` was declared but `args.debug` was never read — a dead flag.

**Command(s)**
```
deal-advisor --help | grep -A1 "debug"
deal-advisor --files data/examples/advisor_deal_config.json --out $OUT/adv.json --debug 2>&1 | tail -5
```

**Expected result:** help says "Print the full ranked/portfolio JSON payload to stdout, in addition
to the compact table"; the run prints that JSON payload to stdout.

**Pass/fail criterion:** Does `--debug` emit the JSON payload? Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W2.4 — Finding F13: `deal-advisor --markdown` no longer clobbers the JSON

**Goal:** When `--out` ends in `.md`, the markdown is written to a `_report.md` sibling and the JSON
at `--out` is preserved, with a loud note naming both paths.

**Current behaviour (before):** `--out x.md --markdown` computed `x.md.with_suffix(".md") == x.md`
and overwrote the JSON with markdown — silent data loss.

**Command(s)**
```
deal-advisor --files data/examples/advisor_deal_config.json --out $OUT/clob.md --markdown 2>&1 | tail -4
python -c "import json; json.load(open('$OUT/clob.md')); print('clob.md is still valid JSON')"
ls $OUT/clob*.md
```

**Expected result:** a note — "Note: --out ends in .md, so writing Markdown to …/clob_report.md
instead, to avoid overwriting the JSON at …/clob.md." — `clob.md` still parses as JSON, and
`clob_report.md` holds the markdown.

**Pass/fail criterion:** Does the JSON survive and the markdown land in a separate file? Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W2.5 — Finding F14: `deal-report --insights` rejects unrelated JSON

**Goal:** Passing a JSON with no recognized `ListingInsights` field is refused with a clear message,
instead of producing an empty-insights report section.

**Current behaviour (before):** `ListingInsights` is all-optional, so any JSON was accepted and a
hollow section was rendered from `{"totally":"unrelated"}`.

**Command(s)**
```
echo '{"totally":"unrelated"}' > $OUT/junk.json
deal-report --forecast data/examples/forecast.json --insights $OUT/junk.json --out $OUT/r.md ; echo "exit=$?"
echo '{"address":"12 Real St"}' > $OUT/ok.json
deal-report --forecast data/examples/forecast.json --insights $OUT/ok.json --out $OUT/r2.md ; echo "exit=$?"
```

**Expected result:** the first run exits 1 with "no recognized ListingInsights field found among
['totally']. Expected at least one of [...]. Refusing to build a report section from unrelated
JSON." The second run (a real but sparse insight) succeeds — absent facts are legitimate, the
project just never fabricates them.

**Pass/fail criterion:** Unrelated JSON refused, sparse-but-real JSON accepted? Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W2.6 — Finding F15: `ingest-listing --ai` help text tells the truth

**Goal:** `--ai` now has help text that states it *does* change the output (switching the provider
from `local` to `vision`), not the earlier false claim that output was unchanged.

**Current behaviour (before):** first `--ai` had no help text; a Wave 2 draft then wrongly said
"output does not change from the default path yet" — but `--ai 1` changes 7 fields. Corrected.

**Command(s)**
```
ingest-listing --help 2>&1 | grep -A3 "\-\-ai "
```

**Expected result:** help says it switches the detection provider to `vision` and that "This DOES"
change the output (the description continues to enumerate the effect).

**Pass/fail criterion:** Does the `--ai` help state it changes output? Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W2.7 — Finding F16: `--pretty` split from screenshot persistence

**Goal:** The dual-purpose `--pretty` (console dump *and* silently gating screenshot saving) is
split — `--save-screenshot` is now its own flag (default 1), so turning down console noise no longer
silently stops persisting an artifact.

**Current behaviour (before):** `--pretty 0` both quieted the console *and* silently stopped saving
the screenshot — one flag, two hidden jobs.

**Command(s)**
```
ingest-listing --help 2>&1 | grep -B0 -A2 -E "save-screenshot"
```

**Expected result:** `--save-screenshot {0,1}` is listed as its own flag, described as previously
"silently tied to --pretty; it is now its own flag," default 1.

**Pass/fail criterion:** Is `--save-screenshot` a distinct, documented flag? Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W2.8 — Finding F17: `deal-advisor --files` error cites an example that actually works

**Goal:** A committed `data/examples/advisor_deal_config.json` exists with the real keys the advisor
expects (`listing_path`/`photos_dir`/`finance_inputs_path`), and the CLI runs against it.

**Current behaviour (before):** the error message pointed at `inputs.json`, whose keys are
`inputs/run/market` — not the keys the advisor needs; there was no valid example to copy.

**Command(s)**
```
cat data/examples/advisor_deal_config.json
deal-advisor --files data/examples/advisor_deal_config.json --out $OUT/adv2.json ; echo "exit=$?"
```

**Expected result:** the file has `listing_path`, `photos_dir`, `finance_inputs_path`, `title`
pointing at real `36_kelly_moncton` assets; the advisor run exits 0 and writes a ranked JSON.

**Pass/fail criterion:** Does the cited example exist and run cleanly? Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W2.9 — Finding F18: an invalid `--media-kinds` value is a clean usage error, not a traceback

**Goal:** `--media-kinds bogus` now produces an argparse usage error, not a raw
`ArgumentTypeError` traceback.

**Current behaviour (before):** the validation helper ran *after* `parse_args`, so a bad value threw
a raw traceback at the user.

**Command(s)**
```
ingest-listing --file data/sample_listings/47_perrot_shediac/listing.txt --media-kinds bogus ; echo "exit=$?"
```

**Expected result:** exit 2, ending with:
```
ingest-listing: error: argument --media-kinds: invalid media kind: 'bogus' (choose from:
['document', 'floorplan', 'image', 'other', 'video'])
```
No Python traceback.

**Pass/fail criterion:** Clean usage error, no traceback? Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W2.10 — Finding F19: `deal-report` with a missing forecast file fails cleanly

**Goal:** A non-existent `--forecast` path yields a clean, actionable message, not a raw
`FileNotFoundError` traceback.

**Current behaviour (before):** a missing forecast file raised a raw `FileNotFoundError`; the
intended `ap.error(...)` was unreachable because the arg was `required=True`.

**Command(s)**
```
deal-report --forecast /tmp/does_not_exist.json --out $OUT/z.md ; echo "exit=$?"
```

**Expected result:**
```
/tmp/does_not_exist.json: file not found. Check the path passed to this flag.
```
No Python traceback.

**Pass/fail criterion:** Clean message, no traceback? Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W2.11 — Finding F20: structured address prints (`address_struct` → `address_structure`)

**Goal:** The CLI reads the correct field name, so the structured-address block prints; and the
parser fallback dicts no longer silently drop it.

**Current behaviour (before):** the CLI read `address_struct` while the model field is
`address_structure`, so the structured-address print never fired; the fallback dicts had the same
typo and `extra="ignore"` discarded it.

**Command(s)**
```
ingest-listing --file data/sample_listings/47_perrot_shediac/listing.txt 2>&1 | grep -A1 "address_structure:"
```

**Expected result:**
```
address_structure: {'address_line': '47 Perrot Street', 'civic_number': '47', 'unit_suite': None,
'city': 'Shediac', 'state_province': 'NB', 'postal_code': 'E4P 0H3', 'country_hint': 'CA'}
```

**Pass/fail criterion:** Does a populated `address_structure` block print? Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W2.12 — Tier 6: living docs reconciled + a reachability net

**Goal:** Docs that asserted unwired features were corrected (living docs edited in place; CHANGELOG
released history got a dated note, not a rewrite), and a test now ties each documented CLI
flag/feature to a reachable code path so a doc claim cannot silently go stale.

**Current behaviour (before):** the README's ingest example implied media intelligence worked in
`--file` mode; `market/README` documented a dead `regional_income` entry point; `reports/README`
signatures omitted `media_report`/`provenance`; several documented `pytest` subset commands exited
non-zero due to the global coverage gate.

**Command(s)**
```
python -m pytest tests/integration/test_cli_reachable_paths.py --no-cov -q
grep -n "Last reconciled" src/core/reports/README.md src/market/README.md 2>/dev/null | head
```

**Expected result:** the reachable-paths test passes (it fails if a documented flag becomes
unreachable); reconciled living docs carry `_Last reconciled_` stamps.

**Pass/fail criterion:** Does the reachability test pass? Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---
---

# WAVE 3 — Disposition (wire-first) + Gate-3 dispositions

## W3.1 — Disposition 3.1a (OPD-1): the dead second verdict engine is gone, thresholds reconciled

**Goal:** `strategist.py` (a dead second verdict engine with diverged thresholds) was audited, its
one genuinely-better behaviour (honouring the input `cap_rate_spread_target` instead of a hardcoded
`0.015`) reconciled into the live strategist, reviewed, and only then deleted.

**Current behaviour (before):** a report could print "cap-rate spread below target" in Warnings while
its own thesis said "meets target," because the engine used the input target and the live strategist
hardcoded `0.015`.

**Command(s)**
```
ls src/core/strategy/strategist.py ; echo "exit=$?"
python -m pytest tests/ -k "strateg or spread" --no-cov -q
```

**Expected result:** `strategist.py` does **not** exist (`No such file or directory`, exit non-zero
for the `ls`); the strategist/spread tests pass with the reconciled threshold.

**Pass/fail criterion:** Is `strategist.py` deleted and the spread-threshold contradiction closed?
Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W3.2 — Disposition 3.1b (OPD-3): wire-first, and the un-wireable deleted

**Goal:** Dead modules were wired into live paths where honest, and deleted where they could only be
"wired" by printing numbers the engine never computed. Kept: `--regional-income` and two internal
swaps (`utils/markdown`, `utils/serialize`). Deleted: `orchestrator.py` (0-byte),
`agents/listing_ingest.py` (true duplicate), and — at the Gate-3 founder ruling — the toy
`scenarios.py`, `narrative_builder.py`, `report_builder.py` (they fabricated money on the page).

**Current behaviour (before):** ~350 LOC across ~11 modules was reachable only from tests; a
CHANGELOG line claimed scenario what-ifs shipped.

**Command(s)**
```
for f in src/orchestrators/orchestrator.py src/agents/listing_ingest.py src/core/advisor/scenarios.py; do ls $f 2>&1; done
deal-advisor --help | grep -E "regional-income|what-if|narrative"
```

**Expected result:** all three files report "No such file or directory" (deleted);
`deal-advisor --help` shows **`--regional-income`** but **not** `--what-if` or `--narrative` (those
were pulled with the toy engine).

**Pass/fail criterion:** Are the un-wireable/toy modules gone, `--regional-income` kept,
`--what-if`/`--narrative` removed? Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W3.3 — Disposition 3.2 (OPD-4): computed-then-discarded fields now reach the report

**Goal:** Fields the engine computed but never showed are now rendered — the cap-rate **floor
value** (M3), `YearBreakdown` LTV/available-equity/estimated-value, `MarketSnapshot.notes`, and the
`MediaReport` schema/ontology/provenance fields — additively (no schema change).

**Current behaviour (before):** a breach line named neither cap nor floor; LTV/equity/value were
recomputed in the generator instead of using stored values; media provenance never surfaced.

**Command(s)**
```
python main.py --out $OUT/rep.md
grep -n -E "floor you set|Cap-rate floor|Media report schema|CV ontology|Photo pipeline — provider_kind" $OUT/rep.md
```

**Expected result:** the report shows "Purchase cap rate is 6.35% (≥ the 5.00% floor you set)." and a
Run Provenance appendix with `Cap-rate floor | 5.00%`, `Media report schema | media_report_v1`,
`CV ontology | amenities_defects_v1`, and `Photo pipeline — provider_kind | heuristic_stub` rows.

**Pass/fail criterion:** Do the floor value and the media provenance rows appear in the report?
Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W3.4 — Disposition 3.3 (M14): the last filename/geometry fabrication removed

**Goal:** `_provider_llm_stub` no longer invents `"on-street parking"` from an image being wide and
bright — the same fabrication already removed from its sibling `_provider_vision_stub`.

**Current behaviour (before):** the LLM stub emitted `"on-street parking"` at confidence 0.61 from
`aspect == "landscape" and lum >= 0.55`; registering that stub would have let a blank bright photo
move money.

**Command(s)**
```
grep -n "on-street parking" src/core/cv/amenities_defects.py
python -m pytest tests/core/cv/ -k "corrobor or contested or filename or stub" --no-cov -q
```

**Expected result:** the only remaining mentions of `"on-street parking"` are in an **explanatory
comment** ("It used to emit `"on-street parking"` … whenever [the image was] wide and not dark") —
i.e. the live emission was removed and only the note recording its removal remains. There is no
active code line that returns that label. The corroboration/contested CV tests pass.

**Pass/fail criterion:** Is the geometry-derived parking emission removed and the CV tests green?
Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W3.5 — Disposition 3.4 (G2-N1/G2-N2): a filename a detector contradicted cannot move money

**Goal:** A filename-derived amenity/defect claim that a covering detector *contradicted* is kept as
a flagged "contested hint" and is **not** allowed to select an income/OPEX rule; the
`DetectedLabelModel.source` marker now survives the schema boundary (it was silently dropped by
`extra="ignore"`).

**Current behaviour (before):** a blank grey `garage.jpg` with a detector that covered
`parking_garage` and reported nothing still yielded `amenities: ['parking']` and moved Y1 cash flow
by **$1,105.80**; the record was stamped `origin=cv_provider` — asserting a detector found what it
explicitly did not.

**Command(s)** (pinned by RED-on-revert tests):
```
python -m pytest tests/core/cv/test_filename_corroboration.py tests/core/insights/test_synthesis_field_guard.py --no-cov -q
grep -n "source" src/schemas/models.py | grep -i "detect" | head
```

**Expected result:** the corroboration/synthesis tests pass; `DetectedLabelModel` carries an
additive `source` field. The contested claim now records as a flagged hint with a $0.00 money delta.

**Pass/fail criterion:** Do the contested-label tests pass (claim flagged, not monetized)?
Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W3.6 — Disposition 3.5: `tag_images` material promotion flagged

**Goal:** A filename like `kitchen_island.jpg` promoted to the `kitchen_island` amenity surface is
the same filename-fabrication class on a different mechanism; it hits no engine rule (no dollars
move) and is flagged rather than silently trusted.

**Current behaviour (before):** the promotion happened with no flag; it was latent because the
engine matches a different literal string.

**Command(s)**
```
python -m pytest tests/ -k "tag_images or promotion or kitchen_island" --no-cov -q
```

**Expected result:** the relevant tests pass (the promotion is flagged; no money moves).

**Pass/fail criterion:** Do the tests pass with the promotion flagged? Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---

## W3.7 — Gate-3 report-honesty fix (B3): "not measured" instead of a false negative sighting

**Goal:** When no built-in provider can even look for a thing (parking, EV charging, quality
proxies), the report says "not checked — no photo check in this run looks for parking" rather than
rendering a default as a positive claim that the thing is *absent*.

**Current behaviour (before):** the report printed "Parking (from photos): none · no EV charging
observed" and "Quality Proxies … 0.00" — indistinguishable from "we looked and saw none," on
non-evidence.

**Command(s)**
```
python main.py --out $OUT/rep.md
grep -n -E "not checked|not measured" $OUT/rep.md
```

**Expected result:** the report contains "not checked — no photo check in this run looks for
parking" / "not measured" wording for uncovered capabilities, gated on whether a provider could look.

**Pass/fail criterion:** Does the report say "not checked/not measured" rather than asserting a
negative sighting? Yes = PASS.

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______
**Actual result observed:** ______________________________________________

---
---

# DEFERRED — shipped as conscious deferrals (expect these to remain open)

These were **not** fixed in Mission 2, by decision. They are the real remaining acceptance list; do
**not** expect them "green." Recorded so nothing masquerades as done.

| Item | State | Note |
| --- | --- | --- |
| **F2 env vector** (`AIREAL_LISTING`/`AIREAL_PHOTOS` with no `--config`) | **OPEN** | Still reaches the F2 defect (see W0.2). Closing it constrains a documented env contract — a follow-on. |
| **3.1c threshold decisions** (Year-1 CoC floor; DECLINE-shortcut materiality) | **NOT APPLIED** | Measured across 21,600 deals; planner recommends SKIP the CoC floor and change the DSCR half 1.20→1.00. Roger's call, deferred behind backlog #6 ("what would have to change?"). |
| **`RegionalIncomeTable.turnover_cost`** field | **OPEN** | Still a required field carrying `median_rent*0.5` internally; never rendered now. Removing a required field is breaking — Roger's call. |
| **`strict_dom` bypass** on rendered-HTML DOM-parse failure | **BACKLOG** | Pre-existing; a `strict_dom=True` caller gets a fallback instead of the raise they asked for. Follow-on. |
| **Report plain-language pass** | **BACKLOG** | Raw ontology ids (`mold_suspected`), undefined `bps`, unglossed "cap-rate spread"/"seasoning", 64-char SHA in an investor doc. |

**Status:** ☐ Reviewed and understood (Roger) · Date: ______

---

## Whole-suite sanity (optional, ~minutes)

```
python -m pytest -q
```
**Expected:** ~630 tests pass, coverage ≥ 80% (the mission closed at 630 tests / 86.09% @ `fbc3179`).

**Status:** ☐ PASS ☐ FAIL ☐ BLOCKED · Validated by Roger: ☐ Date: ______

---

_End of Mission 2 manual testing handoff._
