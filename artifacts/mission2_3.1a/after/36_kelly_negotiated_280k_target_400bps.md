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

- **[Cap Rate](#g-cap) (Y1):** 9.06%
- **[Cash-on-Cash](#g-coc) (Y1):** 15.75%
- **[DSCR](#g-dscr) (Y1):** 1.28
- **Annual [Debt Service](#g-ds) (Y1):** $19,830.13
- **[Acquisition Cash Outlay](#g-acq):** $35,200.00
- **Cap Rate – Interest Spread:** 3.56%


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

- **Verdict:** CONDITIONAL
- **Rationale:**
  - DSCR (Y1) is healthy at 1.28 (≥ 1.20).
  - Cap-rate spread is thin at 3.56% (< 4.00%).
  - Projected IRR (10y) is 27.37% (≥ 12.00%).
  - Year-1 cash flow is positive at $5,545.
- **Suggested Levers:**
  - Negotiate lower price to improve cap-rate spread to ≥ 400 bps.
  - Pursue lower interest rate or longer amortization to widen spread.
  - Address: cap-rate spread below target


## 10-Year Pro Forma (Summary)

| Year | [GSI](#g-gsi) | [GOI](#g-goi) | Total [OPEX](#g-opex) | [NOI](#g-noi) | [Debt Service](#g-ds) | Cash Flow | [DSCR](#g-dscr) | Ending Balance |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | $34,800.00 | $32,068.20 | $6,693.00 | $25,375.20 | $19,830.13 | $5,545.07 | 1.28 | $260,799.87 |
| 2 | $35,844.00 | $33,030.25 | $6,826.86 | $26,203.39 | $19,830.13 | $6,373.26 | 1.32 | $255,313.74 |
| 3 | $36,919.32 | $34,021.15 | $6,963.40 | $27,057.76 | $19,830.13 | $7,227.63 | 1.36 | $249,525.86 |
| 4 | $38,026.90 | $35,041.79 | $7,102.67 | $27,939.12 | $19,830.13 | $8,108.99 | 1.41 | $243,419.66 |
| 5 | $39,167.71 | $36,093.04 | $7,244.72 | $28,848.32 | $19,830.13 | $9,018.20 | 1.45 | $236,977.61 |
| 6 | $40,342.74 | $37,175.83 | $7,389.61 | $29,786.22 | $19,830.13 | $9,956.09 | 1.50 | $230,181.25 |
| 7 | $41,553.02 | $38,291.11 | $7,537.41 | $30,753.70 | $19,830.13 | $10,923.57 | 1.55 | $223,011.09 |
| 8 | $42,799.61 | $39,439.84 | $7,688.15 | $31,751.69 | $19,830.13 | $11,921.56 | 1.60 | $215,446.58 |
| 9 | $44,083.60 | $40,623.04 | $7,841.92 | $32,781.12 | $19,830.13 | $12,950.99 | 1.65 | $207,466.01 |
| 10 | $45,406.11 | $41,841.73 | $7,998.75 | $33,842.97 | $19,830.13 | $14,012.84 | 1.71 | $199,046.51 |


## Valuation – Baseline Appreciation (g = 3.00%)

| Year | Estimated Value | [LTV](#g-ltv) % | Available [Equity](#g-te) @80% |
| ---: | ---: | ---: | ---: |
| 1 | $288,400.00 | 90.43% | -$30,079.87 |
| 2 | $297,052.00 | 85.95% | -$17,672.14 |
| 3 | $305,963.56 | 81.55% | -$4,755.02 |
| 4 | $315,142.47 | 77.24% | $8,694.31 |
| 5 | $324,596.74 | 73.01% | $22,699.78 |
| 6 | $334,334.64 | 68.85% | $37,286.46 |
| 7 | $344,364.68 | 64.76% | $52,480.65 |
| 8 | $354,695.62 | 60.74% | $68,309.92 |
| 9 | $365,336.49 | 56.79% | $84,803.18 |
| 10 | $376,296.59 | 52.90% | $101,990.76 |


## Valuation – Stress-Test (rate-anchored: r/3 = 1.83%, adj = $0.00)

| Year | Estimated Value | [LTV](#g-ltv) % | Available [Equity](#g-te) @80% |
| ---: | ---: | ---: | ---: |
| 1 | $285,133.33 | 91.47% | -$32,693.21 |
| 2 | $290,360.78 | 87.93% | -$23,025.11 |
| 3 | $295,684.06 | 84.39% | -$12,978.62 |
| 4 | $301,104.93 | 80.84% | -$2,535.71 |
| 5 | $306,625.19 | 77.29% | $8,322.54 |
| 6 | $312,246.65 | 73.72% | $19,616.07 |
| 7 | $317,971.17 | 70.14% | $31,365.84 |
| 8 | $323,800.65 | 66.54% | $43,593.94 |
| 9 | $329,736.99 | 62.92% | $56,323.58 |
| 10 | $335,782.17 | 59.28% | $69,579.22 |


## Valuation – NOI-Based (with Cap Drift)

| Year | [Cap Rate](#g-cap) (applied) | Estimated Value | [LTV](#g-ltv) % | Available [Equity](#g-te) @80% |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 9.06% | $280,000.00 | 93.14% | -$36,799.87 |
| 2 | 9.06% | $289,138.53 | 88.30% | -$24,002.91 |
| 3 | 9.06% | $298,565.99 | 83.57% | -$10,673.07 |
| 4 | 9.06% | $308,291.34 | 78.96% | $3,213.41 |
| 5 | 9.06% | $318,323.82 | 74.45% | $17,681.44 |
| 6 | 9.06% | $328,672.94 | 70.03% | $32,757.10 |
| 7 | 9.06% | $339,348.53 | 65.72% | $48,467.73 |
| 8 | 9.06% | $350,360.69 | 61.49% | $64,841.98 |
| 9 | 9.06% | $361,719.85 | 57.36% | $81,909.87 |
| 10 | 9.06% | $373,436.76 | 53.30% | $99,702.89 |


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

- **[IRR](#g-irr):** 27.37%
- **[Equity Multiple](#g-em):** 5.56x


## Warnings

- cap-rate spread below target


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
| Inputs file | artifacts/mission2_3.1a/configs/36_kelly_negotiated_280k_target_400bps.json | `--config` |


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
