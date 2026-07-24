# Mission 1 · Wave 2 (Task 2.4, design half) — "Market Scenarios" Report Section Spec

_Design/spec only. No production code lands with this note._
_Author: Report & CLI Experience Designer · Date: 2026-07-24 · Base: `main` @ `e4716df`_
_Implements the rendering half of Wave 2. Binding source: `MISSION_1_wave1_design_note.md`
§0, §4, §7, §7a, §10 (G1–G7). Target file: `src/core/reports/generator.py`._

This spec tells the Python engineer exactly what to render, in what order, with what formatting,
and under which conditions — so the section looks native to the existing report and no honesty
guardrail (G1–G7) is left to interpretation.

---

## 0. Formatting contract — reuse the existing helpers verbatim

Every number in this section is emitted through the report's **existing** helpers so the section is
byte-for-byte consistent with the rest of the report and deterministic across runs (G-determinism):

| Quantity | Helper (existing) | Renders as | dp |
|---|---|---|---|
| Money (cash flow) | `_fmt_currency(x)` | `$3,798.94`, negative `-$3,798.94` | 2 |
| Percent / rate / return (CoC, IRR, rents, occupancy, cap) | `_fmt_pct(x)` (fraction → %) | `6.35%` | 2 |
| DSCR (ratio) | inline `f"{x:.2f}"` | `0.87` | 2 |
| Equity multiple | inline `f"{x:.2f}x"` | `2.10x` | 2 |

**One new formatter is permitted (recommended), reusing the 2dp percent convention:**

```python
def _fmt_delta_pct(x: float) -> str:
    # Explicit sign so a delta (Δ) is never confused with an applied level.
    # Reuses the existing 2dp percent convention; 0.0 renders as "0.00%".
    return f"{'+' if x > 0 else ''}{x * 100:.2f}%"
```

`_fmt_delta_pct(0.02) -> "+2.00%"`, `_fmt_delta_pct(-0.02) -> "-2.00%"`, `_fmt_delta_pct(0.0) -> "0.00%"`.
Used **only** in the delta columns of the scenario-grid table. Applied levels and outcomes use the
unsigned `_fmt_pct`. This keeps "what was perturbed" visually distinct from "what the engine consumed."

**Determinism (G-determinism / §8):** all floats route through `.2f`-based helpers → no unstable
trailing digits. There is no locale, wall-clock, or dict-ordering dependence. With scenarios OFF the
section is not emitted at all (§8 below).

---

## 1. Placement & heading

**Placement:** a single, structurally separate `## Market Scenarios` section rendered **last**, after
every headline-forecast section (Purchase Metrics → Methodology → Media → Thesis → Pro Forma →
Valuation tables → OPEX → Refi → Returns Summary → **Warnings**). It is never interleaved with the
headline numbers (§7a #1). Concretely, in `generate_report(...)` it is the **final entry** of the
`parts` list, appended only when a `ScenarioAnalysis` is supplied:

```
parts = [ ... , _render_returns(forecast), _render_warnings(forecast.warnings) ]
if scenarios is not None:
    parts.append(_render_market_scenarios(scenarios))
```

Placing it after `Warnings` puts the entire base underwriting above it, so the reader reaches the
what-if overlay only after the headline verdict — reinforcing "this is an overlay, not the base."

**Wiring (from §7 / §10 C1):** `generate_report` and `write_report` gain a **keyword-only**
`scenarios: ScenarioAnalysis | None = None` parameter (after `*`). Default `None` → today's output is
byte-identical (G2). `generate_report` already has a positional `title_override` before `*`, so
keyword-only is mandatory to keep existing call sites intact.

**Heading (exact):**

```
## Market Scenarios
```

**Lead-in (exact, single line, rendered immediately under the heading, before the verbatim block):**

```
A what-if overlay on the base underwriting above — the same math re-run on perturbed copies of your inputs. This is not part of the headline forecast.
```

The lead-in is designed framing (not a guardrail-verbatim string); it may be edited by the narrative
writer, but it must always say the section is an overlay, not the base underwriting (§7a #1).

---

## 2. Verbatim honesty block (G1)

Immediately after the lead-in, render the FIXED VERBATIM "About these scenarios" block from §0 of the
Wave 1 note, **byte-for-byte**, from a module-level constant. No per-run interpolation, no
paraphrase (G1). It is a five-line Markdown blockquote:

```
> **About these scenarios.** These are deterministic what-if calculations over your own market and
> financing assumptions — the same underwriting math re-run on perturbed copies of your inputs. They
> are **not** predictions, forecasts, or live market data. The scenario weights ("priors") are
> **heuristic penalty weights**, not calibrated probabilities, so the weighted figures are what-if
> quantiles over a rule-based grid — not statistical percentiles of real-world outcomes. Every number
> here is exactly reproducible from your inputs and the fixed seed.
```

Because this block sits at the top of the section, **every weighted figure below it is on the same
section as the priors-are-heuristic disclosure** — satisfying G3's "no weighted number without that
context visible" for the entire section.

**Provenance line (G6):** directly under the block, render one non-interpolated-into-variation line:

```
_Region: {snapshot.region} · seed {seed} (provenance only — the grid is a fixed deterministic set, not randomized by the seed) · {n_accepted} of {n_generated} scenarios admitted under guardrails._
```

Wording must never imply the seed drives scenario **variation** (G6): the parenthetical states the
grid is fixed. `region`, `seed`, `n_accepted`, `n_generated` come straight off `ScenarioAnalysis`.

---

## 3. Scenario grid — top-N-by-prior (two linked tables)

**N = 5.** Show the **5 accepted scenarios with the highest prior** (`outcomes` sorted by prior
descending; ties broken by the existing lexicographic hypothesis key from §4 of the Wave 1 note, which
is already the deterministic order). If `n_accepted < 5`, show all of them.

The full column set required by the brief — 5 deltas + 5 applied inputs + 5 outcome metrics + prior —
is 16 numeric columns and would overflow GitHub / PDF (report principle 6). **Design decision: split
into two tables sharing a `#` join key** (row 1 = highest prior, etc.). This keeps each table scannable
and non-overflowing while preserving full traceability (skeptic test: every applied input and every
outcome is present and tied to its perturbation).

A one-line honesty note precedes the tables (the table is a sample; the **bands** in §4 summarize
**all** `n_accepted`):

```
**Scenario grid — top 5 by prior weight** _(of {n_accepted} admitted; the bands below summarize all of them)._
_Priors are heuristic penalty weights, not probabilities (see the note above)._
```

### 3a. Table A — perturbations (what changed)

Columns and formatting (all deltas via `_fmt_delta_pct`, prior via `_fmt_pct`):

```
| # | Prior | Δ Rent growth | Δ Opex growth | Δ Interest rate | Δ Cap rate | Δ Vacancy |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
```

- `#` — integer rank, 1..N by prior desc (the join key).
- `Prior` — `_fmt_pct(outcome.hypothesis.prior)`.
- `Δ Rent growth` — `_fmt_delta_pct(hypothesis.rent_delta)`.
- `Δ Opex growth` — `_fmt_delta_pct(hypothesis.expense_growth_delta)`.
- `Δ Interest rate` — `_fmt_delta_pct(hypothesis.interest_rate_delta)`.
- `Δ Cap rate` — `_fmt_delta_pct(hypothesis.cap_rate_delta)`.
- `Δ Vacancy` — `_fmt_delta_pct(hypothesis.vacancy_delta)`. (This is the raw hypothesis vacancy delta;
  the sign flip into occupancy is shown in Table B's `Occupancy` applied column.)

`str_viability` is **not** a column here (§6 below, G4).

### 3b. Table B — applied engine inputs & outcomes (what the engine consumed and produced)

Columns and formatting:

```
| # | Rent growth | Opex growth | Interest rate | Occupancy | Cap rate (applied) | DSCR (Y1) | CoC (Y1) | Cash flow (Y1) | IRR (10yr) | Equity × |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
```

- `#` — same rank/join key as Table A.
- `Rent growth` — `_fmt_pct(outcome.rent_growth_applied)`.
- `Opex growth` — `_fmt_pct(outcome.expense_growth_applied)`.
- `Interest rate` — `_fmt_pct(outcome.interest_rate_applied)`.
- `Occupancy` — `_fmt_pct(outcome.occupancy_applied)`.
- `Cap rate (applied)` — `_fmt_pct(outcome.cap_rate_purchase_applied)` — **must be shown so the
  clamp is visible (G5).** If it is ever `None` (should not happen when scenarios run; the resolver
  loud-fails per §5 of the Wave 1 note), render `N/A` rather than crashing.
- `DSCR (Y1)` — `f"{outcome.dscr_y1:.2f}"`.
- `CoC (Y1)` — `_fmt_pct(outcome.coc_y1)`.
- `Cash flow (Y1)` — `_fmt_currency(outcome.cash_flow_y1)` — negatives render `-$…`, visually
  unmistakable (formatting principle 3).
- `IRR (10yr)` — `_fmt_pct(outcome.irr_10yr)`.
- `Equity ×` — `f"{outcome.equity_multiple_10yr:.2f}x"`.

Row `#1` in this table (the highest-prior, near-center scenario) reproduces the headline forecast's
Year-1 cap and metrics when its deltas are all zero — the honest tie-out from §1b of the Wave 1 note.

---

## 4. Bands block — prior-weighted distribution per metric (G-label discipline)

After the grid, render the per-metric bands that summarize **all** `n_accepted` scenarios. Lead-in:

```
**Prior-weighted bands** _(across all {n_accepted} admitted scenarios; weighted by heuristic prior)._
```

One table, one row per metric, columns in this exact order and with these exact labels (G-labels):

```
| Metric | downside (p25) | median (p50) | mean (expected) | min | max |
| :--- | ---: | ---: | ---: | ---: | ---: |
```

Rows and per-cell formatting (source: the `ScenarioMetricBand` for each metric on `ScenarioAnalysis`):

| Metric row label | Band source | Cell formatter |
|---|---|---|
| `DSCR (Y1)` | `analysis.dscr` | `f"{v:.2f}"` |
| `CoC (Y1)` | `analysis.coc` | `_fmt_pct(v)` |
| `Cash flow (Y1)` | `analysis.cash_flow_y1` | `_fmt_currency(v)` |
| `IRR (10yr)` | `analysis.irr_10yr` | `_fmt_pct(v)` |
| `Equity multiple (10yr)` | `analysis.equity_multiple_10yr` | `f"{v:.2f}x"` |

For each row, the five cells are `band.p25, band.p50, band.mean, band.min, band.max` in that column
order.

**Label discipline is mandatory (G4 / §7a #4):**
- The p25 column header is literally `downside (p25)` — never "worst case" (G5).
- The p50 column header is literally `median (p50)` — **never** "expected."
- The mean column header is literally `mean (expected)` — "expected" maps to the **mean**, never p50.

All five metrics are higher-is-better, so `downside (p25)` is the reasonable-bad-case lower tail; `min`
is the absolute worst admitted corner (retained for transparency, §4 of the Wave 1 note).

---

## 5. Caveats (each rendered under its trigger — G3)

Render a `**Caveats**` bold sub-label followed by a bullet list, immediately after the bands table so
the cap/rate/IO caveats sit adjacent to the metrics they qualify (G3 "on the same section/screen"):

```
**Caveats**
```

Bullets, in this order:

1. **Priors are heuristic (always shown).** Restate adjacent to the weighted figures:
   `- The bands are weighted by heuristic penalty weights, not probabilities — read them as what-if quantiles over a rule-based grid, not statistical percentiles.`
   (Reinforces the verbatim block right next to the numbers; satisfies G3's adjacency requirement even
   for a reader who scrolled past the top-of-section block.)

2. **Cap-sensitivity, next to IRR / equity multiple (always shown, G3 / §7a #5):**
   `- IRR (10yr) and the equity multiple are terminal-value / cap-rate dominated. The scenario base reproduces the headline purchase cap exactly, so these two move only with the modeled cap-rate delta — treat their spread as cap sensitivity, not a forecast.`

3. **Rate-shock-both-loans, next to rate-sensitive metrics (always shown, G3 / §7a #7):**
   `- An interest-rate delta is applied to both the acquisition loan and the year-5 refinance loan and holds for the full hold period — a rate shock here is a permanent, whole-deal shock, not a temporary one.`

4. **IO-period caveat (conditional — render ONLY if any admitted scenario has `io_years > 0`, G3 /
   §7a #6):**
   `- One or more scenarios use an interest-only period, so their Year-1 DSCR, CoC, and cash flow are interest-only-flattered and understate the debt load once amortization begins. Read the Year-1 downside as optimistic for those scenarios.`
   Trigger check: `any(o.hypothesis... io_years > 0)` via the applied financing on each outcome
   (engineer resolves the exact accessor; for the sample all scenarios have `io_years == 0`, so this
   bullet is **omitted** — the caveat list must not show it when it does not apply).

The caveats subsection must always render bullets 1–3 (their triggers — weighted figures, cap-driven
metrics, and a perturbed rate — are always present). Bullet 4 appears only under its trigger. A weighted
or rate/cap-driven number without its caveat visible in the same section is a G3 veto.

---

## 6. `str_viability` — narrative flag only (G4 / §7a #8)

**Default: omit `str_viability` from every numeric table** (Tables A and B above). It is never a column
beside DSCR/CoC/CF/IRR — the engine never consumes it (§1 of the Wave 1 note), so a column there would
imply it moved a metric.

**If surfaced at all**, it goes in a clearly separated note after the caveats, with the literal label
`not modeled — narrative flag only`:

```
**Narrative flags (not modeled)**
- STR viability flagged in {k} of {n_accepted} admitted scenarios — not modeled — narrative flag only. It did not move any number above.
```

Render this note only when at least one admitted scenario has `str_viability == True`; otherwise omit
the whole `Narrative flags` block. The literal string `not modeled — narrative flag only` must appear
verbatim (G4).

---

## 7. Empty-set state (`n_accepted == 0`)

When the rejector admits nothing, `ScenarioAnalysis` carries `n_accepted == 0`, empty `outcomes`, and
`None` bands (§4 / §7 of the Wave 1 note). Render the heading, lead-in, verbatim block, and provenance
line **as normal**, then — instead of any table or band — render:

```
**No admissible scenarios under the current guardrails.**

None of the {n_generated} generated hypotheses passed the rejector, so there are no prior-weighted
outcomes to report. No numbers are fabricated.

{notes}
```

`{notes}` is `analysis.notes` (the rejector's explanation) rendered verbatim if present; if `notes`
is `None`, omit that line. No grid, no bands, no caveats subsection (there are no numbers to qualify).
This is a designed, honest state — never a silent gap or crash (report principle: states are designed).

---

## 8. Determinism & OFF guarantee

- **Fixed precision:** every emitted float goes through `_fmt_currency` / `_fmt_pct` / `_fmt_delta_pct`
  / `.2f`, all 2dp — no unstable trailing digits, no locale dependence. Same `ScenarioAnalysis` →
  identical bytes (§8, G-determinism).
- **Deterministic ordering:** rows follow `outcomes` order (prior desc, lexicographic tie-break) already
  guaranteed upstream; the renderer must not re-sort by any float or dict iteration.
- **OFF ⇒ section absent (byte-identical, G2):** the section is emitted **only** when
  `scenarios is not None`. With `--scenarios` off, `write_report`/`generate_report` are called with
  `scenarios=None`, the `_render_market_scenarios` branch never runs, and the produced Markdown is
  byte-identical to today's. The dedicated scenarios-OFF byte-identical test (G2) pins this.

---

## 9. Rendered mockup (fake but plausible data — Moncton duplex)

> Sample numbers only, for look-and-feel review. Not a real analysis.

---

## Market Scenarios

A what-if overlay on the base underwriting above — the same math re-run on perturbed copies of your inputs. This is not part of the headline forecast.

> **About these scenarios.** These are deterministic what-if calculations over your own market and
> financing assumptions — the same underwriting math re-run on perturbed copies of your inputs. They
> are **not** predictions, forecasts, or live market data. The scenario weights ("priors") are
> **heuristic penalty weights**, not calibrated probabilities, so the weighted figures are what-if
> quantiles over a rule-based grid — not statistical percentiles of real-world outcomes. Every number
> here is exactly reproducible from your inputs and the fixed seed.

_Region: Moncton, NB · seed 42 (provenance only — the grid is a fixed deterministic set, not randomized by the seed) · 18 of 243 scenarios admitted under guardrails._

**Scenario grid — top 5 by prior weight** _(of 18 admitted; the bands below summarize all of them)._
_Priors are heuristic penalty weights, not probabilities (see the note above)._

| # | Prior | Δ Rent growth | Δ Opex growth | Δ Interest rate | Δ Cap rate | Δ Vacancy |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 12.40% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| 2 | 9.80% | +1.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| 3 | 9.10% | 0.00% | +1.00% | 0.00% | 0.00% | +2.00% |
| 4 | 7.60% | -1.00% | 0.00% | +1.00% | +0.50% | 0.00% |
| 5 | 6.30% | +2.00% | 0.00% | +1.00% | 0.00% | +2.00% |

| # | Rent growth | Opex growth | Interest rate | Occupancy | Cap rate (applied) | DSCR (Y1) | CoC (Y1) | Cash flow (Y1) | IRR (10yr) | Equity × |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 3.00% | 2.00% | 5.50% | 95.00% | 6.35% | 0.87 | -12.67% | -$3,798.94 | 15.34% | 2.10x |
| 2 | 4.00% | 2.00% | 5.50% | 95.00% | 6.35% | 0.89 | -10.42% | -$3,124.55 | 16.88% | 2.24x |
| 3 | 3.00% | 3.00% | 5.50% | 93.00% | 6.35% | 0.81 | -18.03% | -$5,406.12 | 13.02% | 1.88x |
| 4 | 2.00% | 2.00% | 6.50% | 95.00% | 6.85% | 0.79 | -21.55% | -$6,460.77 | 11.47% | 1.71x |
| 5 | 5.00% | 2.00% | 6.50% | 93.00% | 6.35% | 0.83 | -16.90% | -$5,068.21 | 14.10% | 1.96x |

**Prior-weighted bands** _(across all 18 admitted scenarios; weighted by heuristic prior)._

| Metric | downside (p25) | median (p50) | mean (expected) | min | max |
| :--- | ---: | ---: | ---: | ---: | ---: |
| DSCR (Y1) | 0.81 | 0.86 | 0.85 | 0.76 | 0.93 |
| CoC (Y1) | -18.03% | -13.44% | -14.02% | -24.90% | -6.11% |
| Cash flow (Y1) | -$5,406.12 | -$4,030.18 | -$4,205.66 | -$7,468.03 | -$1,832.40 |
| IRR (10yr) | 13.02% | 15.10% | 14.88% | 9.95% | 18.42% |
| Equity multiple (10yr) | 1.88x | 2.07x | 2.05x | 1.62x | 2.38x |

**Caveats**
- The bands are weighted by heuristic penalty weights, not probabilities — read them as what-if quantiles over a rule-based grid, not statistical percentiles.
- IRR (10yr) and the equity multiple are terminal-value / cap-rate dominated. The scenario base reproduces the headline purchase cap exactly, so these two move only with the modeled cap-rate delta — treat their spread as cap sensitivity, not a forecast.
- An interest-rate delta is applied to both the acquisition loan and the year-5 refinance loan and holds for the full hold period — a rate shock here is a permanent, whole-deal shock, not a temporary one.

_(The interest-only caveat bullet is omitted here because every admitted scenario in this sample has `io_years == 0`.)_

---

### Empty-set variant (for reference — same header, no numbers)

## Market Scenarios

A what-if overlay on the base underwriting above — the same math re-run on perturbed copies of your inputs. This is not part of the headline forecast.

> **About these scenarios.** These are deterministic what-if calculations over your own market and
> financing assumptions — the same underwriting math re-run on perturbed copies of your inputs. They
> are **not** predictions, forecasts, or live market data. The scenario weights ("priors") are
> **heuristic penalty weights**, not calibrated probabilities, so the weighted figures are what-if
> quantiles over a rule-based grid — not statistical percentiles of real-world outcomes. Every number
> here is exactly reproducible from your inputs and the fixed seed.

_Region: Moncton, NB · seed 42 (provenance only — the grid is a fixed deterministic set, not randomized by the seed) · 0 of 243 scenarios admitted under guardrails._

**No admissible scenarios under the current guardrails.**

None of the 243 generated hypotheses passed the rejector, so there are no prior-weighted outcomes to report. No numbers are fabricated.

All generated hypotheses violated the cap-rate guardrail (0.03 ≤ cap ≤ 0.12) after applying deltas.

---

## 10. Engineer checklist (maps to guardians' G1–G7)

- [ ] Section is last, keyword-only `scenarios` param, absent when `None` (G2, §1/§8).
- [ ] §0 verbatim block from a module-level constant, byte-for-byte (G1, §2).
- [ ] Provenance line says seed is provenance-only, not variation (G6, §2).
- [ ] Top-5-by-prior grid; `cap_rate_purchase_applied` column present (G5, §3b).
- [ ] Band column headers exactly `downside (p25)` / `median (p50)` / `mean (expected)` / `min` / `max`;
      p50 never called "expected" (G4/G5, §4).
- [ ] Priors-heuristic, cap-sensitivity, rate-shock caveats always render; IO caveat only when any
      `io_years > 0` (G3, §5).
- [ ] `str_viability` omitted from numeric tables; if shown, literal `not modeled — narrative flag only`
      (G4, §6).
- [ ] `n_accepted == 0` renders the empty-set state, no fabricated bands (§7).
- [ ] All floats via `_fmt_currency` / `_fmt_pct` / `_fmt_delta_pct` / `.2f`; deterministic row order
      (G-determinism, §0/§8).
- [ ] No new runtime dependency introduced by the renderer (G7).
