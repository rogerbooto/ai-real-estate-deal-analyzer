# Investment Analysis – 36 Kelly Ave, Moncton NB (SAMPLE — observations are hand-fed, not from a real tagger)

**Amenities:**
- in-unit laundry
- parking

**Notes:**
- Sample artifact: the observations on this report were supplied by hand to exercise the comparison section.

**Condition & Defects:**
- old roof
- water stain


## Purchase Metrics

- **[Cap Rate](#g-cap) (Y1):** 6.64%
- **[Cash-on-Cash](#g-coc) (Y1):** -3.89%
- **[DSCR](#g-dscr) (Y1):** 0.94
- **Annual [Debt Service](#g-ds) (Y1):** $28,321.67
- **[Acquisition Cash Outlay](#g-acq):** $45,991.00
- **Cap Rate – Interest Spread:** 1.14%


## Forecasting Methodology

We produce **three parallel valuation tracks** and mark the first year where the loan-to-value (LTV) reaches **≤ 80%** (standard refi-ready threshold). All math is deterministic.

**1) Baseline (Appreciation-Based)**

Property value grows at an assumed annual appreciation rate $g$:

$$Value_t = PurchasePrice \times (1 + g)^t$$
$$LTV_t = \frac{MortgageBalance_t}{Value_t}$$
$$Equity_t^{(80\%)} = 0.80 \times Value_t - MortgageBalance_t$$

**2) Stress-Test (Rate-Anchored, Conservative)**

Anchors value growth to a fraction of today's debt rate $r$ (stress stance). If the model uses an adjustment $Adj$ to reflect effective basis (e.g., subtracting certain upfronts), then:

$$StressValue_t = (PurchasePrice - Adj) \times (1 + \tfrac{r}{3})^t$$
$$LTV_t = \frac{MortgageBalance_t}{StressValue_t}$$
$$Equity_t^{(80\%)} = 0.80 \times StressValue_t - MortgageBalance_t$$

**3) NOI-Based (Market-Income Approach with Cap Rate Drift)**

Values are derived from income with a drifting market cap rate:

$$CapRate_t = CapRate_0 + (drift_{per\_year} \times t)$$
$$NOIValue_t = \frac{NOI_t}{CapRate_t}$$
$$LTV_t = \frac{MortgageBalance_t}{NOIValue_t}$$
$$Equity_t^{(80\%)} = 0.80 \times NOIValue_t - MortgageBalance_t$$

**Notes**
- *Seasoning*: refi checks typically begin at Year 1 or later (configurable).
- We use end-of-year balances and values for consistency.
- LTV comparisons use a small epsilon to avoid floating-point edge cases.
- This report shows the full horizon; refi years are marked when available.


## Investment Thesis

- **Verdict:** DECLINE
- **Rationale:**
  - DSCR (Y1) is weak at 0.94 (< 1.20).
  - Cap-rate spread is thin at 1.14% (< 1.50%).
  - Projected IRR (10y) is 14.00% (≥ 12.00%).
  - Year-1 cash flow is negative at $-1,788.
- **Suggested Levers:**
  - Negotiate lower price to improve cap-rate spread to ≥ 150 bps.
  - Pursue lower interest rate or longer amortization to widen spread.
  - Increase down payment to reduce debt service and lift DSCR.
  - Trim OPEX (e.g., utilities, PM fees) via vendor bids to lift NOI.
  - Phase rent increases (e.g., renewal program) to strengthen DSCR.
  - Target rent optimization (ancillary income, fee schedule) to reach breakeven.
  - Defer non-critical CapEx; build reserves gradually to improve Y1 cash flow.
  - Address: cap-rate spread below target
  - Address: negative cash flow in projection


## 10-Year Pro Forma (Summary)

| Year | [GSI](#g-gsi) | [GOI](#g-goi) | Total [OPEX](#g-opex) | [NOI](#g-noi) | [Debt Service](#g-ds) | Cash Flow | [DSCR](#g-dscr) | Ending Balance |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | $36,600.00 | $33,726.90 | $7,193.00 | $26,533.90 | $28,321.67 | -$1,787.77 | 0.94 | $372,478.10 |
| 2 | $37,698.00 | $34,738.71 | $7,336.86 | $27,401.85 | $28,321.67 | -$919.82 | 0.97 | $364,642.73 |
| 3 | $38,828.94 | $35,780.87 | $7,483.60 | $28,297.27 | $28,321.67 | -$24.40 | 1.00 | $356,376.40 |
| 4 | $39,993.81 | $36,854.29 | $7,633.27 | $29,221.03 | $28,321.67 | $899.35 | 1.03 | $347,655.44 |
| 5 | $41,193.62 | $37,959.92 | $7,785.93 | $30,173.99 | $28,321.67 | $1,852.32 | 1.07 | $338,454.81 |
| 6 | $42,429.43 | $39,098.72 | $7,941.65 | $31,157.07 | $28,321.67 | $2,835.40 | 1.10 | $328,748.15 |
| 7 | $43,702.31 | $40,271.68 | $8,100.49 | $32,171.20 | $28,321.67 | $3,849.52 | 1.14 | $318,507.63 |
| 8 | $45,013.38 | $41,479.83 | $8,262.50 | $33,217.34 | $28,321.67 | $4,895.66 | 1.17 | $307,703.88 |
| 9 | $46,363.78 | $42,724.23 | $8,427.75 | $34,296.48 | $28,321.67 | $5,974.81 | 1.21 | $296,305.92 |
| 10 | $47,754.70 | $44,005.95 | $8,596.30 | $35,409.65 | $28,321.67 | $7,087.98 | 1.25 | $284,281.07 |


## Valuation – Baseline Appreciation (g = 3.00%)

| Year | Estimated Value | [LTV](#g-ltv) % | Available [Equity](#g-te) @80% |
| ---: | ---: | ---: | ---: |
| 1 | $411,897.00 | 90.43% | -$42,960.50 |
| 2 | $424,253.91 | 85.95% | -$25,239.60 |
| 3 | $436,981.53 | 81.55% | -$6,791.18 |
| 4 | $450,090.97 | 77.24% | $12,417.34 |
| 5 | $463,593.70 | 73.01% | $32,420.15 |
| 6 | $477,501.51 | 68.85% | $53,253.06 |
| 7 | $491,826.56 | 64.76% | $74,953.62 |
| 8 | $506,581.36 | 60.74% | $97,561.21 |
| 9 | $521,778.80 | 56.79% | $121,117.12 |
| 10 | $537,432.16 | 52.90% | $145,664.65 |


## Valuation – Stress-Test (rate-anchored: r/3 = 1.83%, adj = $0.00)

| Year | Estimated Value | [LTV](#g-ltv) % | Available [Equity](#g-te) @80% |
| ---: | ---: | ---: | ---: |
| 1 | $407,231.50 | 91.47% | -$46,692.90 |
| 2 | $414,697.41 | 87.93% | -$32,884.80 |
| 3 | $422,300.20 | 84.39% | -$18,536.25 |
| 4 | $430,042.37 | 80.84% | -$3,621.54 |
| 5 | $437,926.48 | 77.29% | $11,886.37 |
| 6 | $445,955.13 | 73.72% | $28,015.95 |
| 7 | $454,130.97 | 70.14% | $44,797.15 |
| 8 | $462,456.71 | 66.54% | $62,261.49 |
| 9 | $470,935.08 | 62.92% | $80,442.14 |
| 10 | $479,568.89 | 59.28% | $99,374.04 |


## Valuation – NOI-Based (with Cap Drift)

| Year | [Cap Rate](#g-cap) (applied) | Estimated Value | [LTV](#g-ltv) % | Available [Equity](#g-te) @80% |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 6.64% | $399,900.00 | 93.14% | -$52,558.10 |
| 2 | 6.64% | $412,981.08 | 88.30% | -$34,257.86 |
| 3 | 6.64% | $426,476.27 | 83.56% | -$15,195.39 |
| 4 | 6.64% | $440,398.43 | 78.94% | $4,663.31 |
| 5 | 6.64% | $454,760.82 | 74.42% | $25,353.84 |
| 6 | 6.64% | $469,577.08 | 70.01% | $46,913.51 |
| 7 | 6.64% | $484,861.30 | 65.69% | $69,381.41 |
| 8 | 6.64% | $500,627.99 | 61.46% | $92,798.51 |
| 9 | 6.64% | $516,892.09 | 57.32% | $117,207.75 |
| 10 | 6.64% | $533,669.03 | 53.27% | $142,654.15 |


## Operating Expenses - Year 1 Detail

- Insurance: $1,026.00
- Taxes: $4,747.00
- Utilities: $0.00
- Water & Sewer: $920.00
- Property Management: $0.00
- Repairs & Maintenance: $200.00
- Trash: $0.00
- Landscaping: $0.00
- Snow Removal: $0.00
- HOA Fees: $0.00
- Reserves: $300.00
- Other: $0.00
- **Total OPEX (Y1):** $7,193.00


## Adjustments Applied

Observations from the listing copy and photos moved some of the figures above. This section shows both pictures — the same deal with those observations and without them — and names the observation behind every change.

> **About these observations.** Condition tags, defects and amenities are *observations* — what
> the pipeline read in the listing copy and the photo set. Nothing was inspected or measured, and
> an observation can be wrong: a feature can be missed, or a label attached to something it does
> not describe. Each adjustment below is a fixed engine rule applied to an observation — a
> modeling allowance, not a quote or a measured cost. The baseline column is the same deal with
> none of them applied, so the observation-dependent part of this analysis can be read apart from
> the part that does not depend on any observation.

_AI photo tagging was on for this run (`AIREAL_USE_VISION`): the photo-derived observations are model output, so they carry a model's error rate on top of everything noted above._

**Year 1 impact** _(Change = with observations − baseline.)_

| Metric | Baseline | With observations (AI-assisted) | Change |
| :--- | ---: | ---: | ---: |
| Verdict | DECLINE | DECLINE | unchanged |
| GOI | $32,068.20 | $33,726.90 | +$1,658.70 |
| Total OPEX | $6,693.00 | $7,193.00 | +$500.00 |
| NOI | $25,375.20 | $26,533.90 | +$1,158.70 |
| Cash flow | -$2,946.47 | -$1,787.77 | +$1,158.70 |
| Cap rate | 6.35% | 6.64% | +0.29% |
| DSCR | 0.90 | 0.94 | +0.04 |
| Cash-on-cash | -6.41% | -3.89% | +2.52% |

**What moved each figure**

- Year 1: condition: old roof → reserves +$300/yr
- Year 1: defect: water stain → R&M +$200/yr
- Year 1: amenity uplift: in-unit laundry (+$25/mo/unit other income)
- Year 1: amenity uplift: parking (+$50/mo/unit other income)


## Returns Summary (10-Year)

- **[IRR](#g-irr):** 14.00%
- **[Equity Multiple](#g-em):** 3.64x


## Warnings

- cap-rate spread below target
- negative cash flow in projection


## Appendix — Run Provenance

The settings this report was generated under. Environment variables silently change the figures above, so reproducing a report means matching this table — see `.env.example` for the defaults.

| Setting | Value | Source |
| :--- | :--- | :--- |
| Cap-rate drift | 0 bps/yr | `AIREAL_CAP_DRIFT_BPS` |
| Baseline appreciation | 3.00% | `AIREAL_APPRECIATION_PCT` |
| Stress basis adjustment | $0.00 | `AIREAL_STRESS_ADJ` |
| Orchestration engine | deterministic | `AIREAL_ENGINE / --engine` |
| Market Scenarios | off | `AIREAL_SCENARIOS / --scenarios` |
| AI photo tagging | on | `AIREAL_USE_VISION` |
| Inputs file | data/sample_listings/36_kelly_moncton/inputs.json | `--config` |


## Appendix — Definitions

Every term below is defined **as this engine computes it**. Where a convention differs from the textbook form, the difference is stated rather than glossed over.

| Term | Stands for | Definition |
| :--- | :--- | :--- |
| <a id="g-gsi"></a>**GSI** | Gross Scheduled Income | Annualized rent plus other income for every unit at full occupancy, before any vacancy or collection loss. |
| <a id="g-goi"></a>**GOI** | Gross Operating Income | GSI after economic vacancy and bad debt: `GOI = GSI × occupancy × bad_debt_factor`. |
| <a id="g-opex"></a>**OPEX** | Operating Expenses | The sum of all itemized annual operating costs. Excludes debt service, income tax, and capital expenditure. |
| <a id="g-noi"></a>**NOI** | Net Operating Income | `NOI = GOI − OPEX`. The property's income before financing — the basis for cap rate and DSCR. |
| <a id="g-ds"></a>**Debt Service** | Annual principal + interest | Annual mortgage payment. Computed on **annual** periods (`payment = r × P ÷ (1 − (1+r)^−n)`, r annual, n in years), which runs slightly above a real monthly-pay loan of the same rate and term. |
| <a id="g-dscr"></a>**DSCR** | Debt Service Coverage Ratio | `DSCR = NOI ÷ Debt Service`. Below 1.00 the property does not cover its own mortgage from operations. |
| <a id="g-cap"></a>**Cap Rate** | Capitalization Rate | `Cap Rate = NOI (Year 1) ÷ purchase price`, unless a cap rate is supplied explicitly in the inputs. |
| <a id="g-coc"></a>**CoC** | Cash-on-Cash Return | `CoC = Year 1 cash flow ÷ acquisition cash outlay`. Unlike cap rate, it is net of financing. |
| <a id="g-acq"></a>**Acquisition Cash Outlay** | Total cash to close | `down payment + closing costs + upfront CapEx reserve + mortgage insurance premium` (the premium applies only when the down payment is below 20%). |
| <a id="g-ltv"></a>**LTV** | Loan-to-Value | `LTV = mortgage balance ÷ estimated value`. The 80% threshold is the conventional refinance-ready mark. |
| <a id="g-irr"></a>**IRR** | Internal Rate of Return | The discount rate at which the projected cash flows net to zero. The series is the acquisition cash outlay (negative), each year's cash flow, any refinance cash-out, and terminal equity in the final year. |
| <a id="g-em"></a>**Equity Multiple** | Total return multiple | `sum of all cash returned ÷ acquisition cash outlay`, including terminal equity. Undiscounted — unlike IRR it ignores timing. |
| <a id="g-te"></a>**Terminal Equity** | Modeled exit proceeds | `max(0, 0.80 × final-year value − mortgage balance)`. A proxy for sale proceeds to the owner; no sale costs are modeled. |
| <a id="g-io"></a>**IO** | Interest-Only | A front period during which payments cover interest only and the balance does not amortize. |
| <a id="g-ppsf"></a>**$/sq ft** | Price per square foot | List price ÷ stated finished area. Taken from the listing copy, not computed by the engine. |
