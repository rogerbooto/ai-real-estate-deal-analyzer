# Investment Analysis – 36 Kelly

**As listed:** List price $399,900.00 · 3 bd / 1 ba · 1,936 sq ft · [$206.56/sq ft](#g-ppsf)

**Amenities:**
- in_unit_laundry
- laundry
- parking
- stainless_appliances

**Notes:**
- Duplex

**Condition & Defects:**
- move-in ready
- renovated


## Purchase Metrics

- **[Cap Rate](#g-cap) (Y1):** 6.35%
- **[Cash-on-Cash](#g-coc) (Y1):** -6.41%
- **[DSCR](#g-dscr) (Y1):** 0.90
- **Annual [Debt Service](#g-ds) (Y1):** $28,321.67
- **[Acquisition Cash Outlay](#g-acq):** $45,991.00
- **Cap Rate – Interest Spread:** 0.85%


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


## Media Overview

- **Total Assets:** 12 &nbsp;&nbsp;(images: 12, videos: 0, docs: 0, other: 0)
- **Total Size:** 1,130,380 B (1130380 bytes)
- **Image Dimensions:** width 482–1024, height 677–768, avg ≈ 979×710
- **Orientation:** landscape 11, portrait 1, square 0
- **Hero Image:** `0af4371421b597487891c15be730d37850726dcca6c254193de898ba5934bf73`


## Photo Coverage

- **Images:** 12 readable of 12 · 5 detections · provider `cv_v2`
- **Rooms Documented:** bath 1, bedroom 1, kitchen 1, living 1
- **Amenities Seen in Photos:** stainless_kitchen


## Investment Thesis

- **Verdict:** DECLINE
- **Rationale:**
  - DSCR (Y1) is weak at 0.90 (< 1.20).
  - Cap-rate spread is thin at 0.85% (< 1.50%).
  - Projected IRR (10y) is 12.29% (≥ 12.00%).
  - Year-1 cash flow is negative at $-2,946.
- **Suggested Levers:**
  - Negotiate lower price to improve cap-rate spread to ≥ 150 bps.
  - Pursue lower interest rate or longer amortization to widen spread.
  - Increase down payment to reduce debt service and lift DSCR.
  - Trim OPEX (e.g., utilities, PM fees) via vendor bids to lift NOI.
  - Phase rent increases (e.g., renewal program) to strengthen DSCR.
  - Target rent optimization (ancillary income, fee schedule) to reach breakeven.
  - Defer non-critical CapEx; build reserves gradually to improve Y1 cash flow.
  - Address: negative cash flow in projection


## 10-Year Pro Forma (Summary)

| Year | [GSI](#g-gsi) | [GOI](#g-goi) | Total [OPEX](#g-opex) | [NOI](#g-noi) | [Debt Service](#g-ds) | Cash Flow | [DSCR](#g-dscr) | Ending Balance |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | $34,800.00 | $32,068.20 | $6,693.00 | $25,375.20 | $28,321.67 | -$2,946.47 | 0.90 | $372,478.10 |
| 2 | $35,844.00 | $33,030.25 | $6,826.86 | $26,203.39 | $28,321.67 | -$2,118.29 | 0.93 | $364,642.73 |
| 3 | $36,919.32 | $34,021.15 | $6,963.40 | $27,057.76 | $28,321.67 | -$1,263.92 | 0.96 | $356,376.40 |
| 4 | $38,026.90 | $35,041.79 | $7,102.67 | $27,939.12 | $28,321.67 | -$382.55 | 0.99 | $347,655.44 |
| 5 | $39,167.71 | $36,093.04 | $7,244.72 | $28,848.32 | $28,321.67 | $526.65 | 1.02 | $338,454.81 |
| 6 | $40,342.74 | $37,175.83 | $7,389.61 | $29,786.22 | $28,321.67 | $1,464.55 | 1.05 | $328,748.15 |
| 7 | $41,553.02 | $38,291.11 | $7,537.41 | $30,753.70 | $28,321.67 | $2,432.03 | 1.09 | $318,507.63 |
| 8 | $42,799.61 | $39,439.84 | $7,688.15 | $31,751.69 | $28,321.67 | $3,430.02 | 1.12 | $307,703.88 |
| 9 | $44,083.60 | $40,623.04 | $7,841.92 | $32,781.12 | $28,321.67 | $4,459.45 | 1.16 | $296,305.92 |
| 10 | $45,406.11 | $41,841.73 | $7,998.75 | $33,842.97 | $28,321.67 | $5,521.30 | 1.19 | $284,281.07 |


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
| 1 | 6.35% | $399,900.00 | 93.14% | -$52,558.10 |
| 2 | 6.35% | $412,951.78 | 88.30% | -$34,281.30 |
| 3 | 6.35% | $426,416.21 | 83.57% | -$15,243.43 |
| 4 | 6.35% | $440,306.10 | 78.96% | $4,589.44 |
| 5 | 6.35% | $454,634.62 | 74.45% | $25,252.88 |
| 6 | 6.35% | $469,415.39 | 70.03% | $46,784.16 |
| 7 | 6.35% | $484,662.42 | 65.72% | $69,222.30 |
| 8 | 6.35% | $500,390.14 | 61.49% | $92,608.24 |
| 9 | 6.35% | $516,613.46 | 57.36% | $116,984.85 |
| 10 | 6.35% | $533,347.71 | 53.30% | $142,397.09 |


## Operating Expenses - Year 1 Detail

- Insurance: $1,026.00
- Taxes: $4,747.00
- Utilities: $0.00
- Water & Sewer: $920.00
- Property Management: $0.00
- Repairs & Maintenance: $0.00
- Trash: $0.00
- Landscaping: $0.00
- Snow Removal: $0.00
- HOA Fees: $0.00
- Reserves: $0.00
- Other: $0.00
- **Total OPEX (Y1):** $6,693.00


## Returns Summary (10-Year)

- **[IRR](#g-irr):** 12.29%
- **[Equity Multiple](#g-em):** 3.34x


## Warnings

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
| AI photo tagging | off | `AIREAL_USE_VISION` |
| LLM-authored observations | off | `AIREAL_LLM_MODE` |
| Inputs file | artifacts/mission2_3.1a/configs/36_kelly_target_050bps.json | `--config` |


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
