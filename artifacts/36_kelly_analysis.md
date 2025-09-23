# Investment Analysis – 36 Kelly, Moncton, New Brunswick U1C 2R7

**Amenities:**
- duplex up-and-down
- legal basement apartment
- two self-contained units
- separate electrical meters
- in-unit laundry in both units
- electric baseboard heating
- municipal water
- vinyl siding exterior
- paved driveway
- large lot
- finished basement
- bright upper kitchen
- dining room (upper unit)
- living room (upper unit)
- close to schools and amenities
- year-round road access

**Notes:**
- Price: $399,900
- Square feet: 1,936
- Approx. price per sq ft: $207
- Lot size: 1,274.8 m² (~0.315 acres)
- Property taxes: $5,396.81 (2024)
- Assessment: $262,900
- Property type: Residential bungalow; duplex (up-and-down)
- Units: 2 total
- Upper unit: 3 bedrooms, 1 bathroom; bright kitchen with white cabinetry; dining room; living room; laundry
- Lower unit: 2 bedrooms, 1 bathroom; kitchen; combined living/dining; laundry
- Basement: fully finished legal apartment
- Occupancy: upper unit vacant; lower unit tenant-occupied
- Utilities: separate electrical meters
- Heating: electric baseboard
- Water: municipal
- Exterior: vinyl siding
- Driveway: paved
- Garage: none
- Dual-purpose: live in one unit, rent the other
- Location: close to schools and amenities; year-round road access
- Listing brokerage: EXIT Realty Associates
- Listing status: cancelled (useful for comps/analysis)

**Condition & Defects:**
- recently renovated
- move-in ready
- fully finished basement
- legal secondary suite


## Purchase Metrics

- **Cap Rate (Y1):** 6.35%
- **Cash-on-Cash (Y1):** -12.67%
- **DSCR (Y1):** 0.87
- **Annual Debt Service (Y1):** $29,174.14
- **Acquisition Cash Outlay:** $29,995.00
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


## Investment Thesis

- **Verdict:** CONDITIONAL
- **Rationale:**
  - Underwritten DSCR is 0.87 at purchase with negative cash flow for the first five years, indicating insufficient coverage of debt service under current assumptions.
  - Operating expenses omit property management and repairs/reserves, which would further depress DSCR and cash flow if applied realistically.
  - Cap-rate spread is 0.845% versus a 1.50% target, implying inadequate risk premium; targeting a ~7.0% cap on current NOI suggests a price near $362,500 or a rate buydown/higher equity to bridge the gap.
  - Subscale exposure (2 units) concentrates income risk; one vacancy or turn can materially impact performance.
  - Forecast taxes ($4,747) are below the listing’s 2024 property taxes (~$5,397), implying NOI may be overstated.
  - Strengths include a legal, separately metered duplex with recent renovations and one vacant unit enabling an immediate rent reset; amortization drives improving DSCR and positive cash flow from Year 6; modeled 10-year IRR of 15.34%.
  - Proceed only if price is reduced to approximately $362,500 (or equivalent seller concessions), or if financing terms are improved to achieve Year-1 DSCR of at least 1.20 and breakeven cash flow when underwriting with property management (~8% of GOI) and repairs/reserves (8–10% of GOI). If these conditions cannot be met, pass.


## 30-Year Pro Forma (Summary)

| Year | GSI | GOI | Total OPEX | NOI | Debt Service | Cash Flow | DSCR | Ending Balance |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | $34,800.00 | $32,068.20 | $6,693.00 | $25,375.20 | $29,174.14 | -$3,798.94 | 0.87 | $388,312.00 |
| 2 | $35,844.00 | $33,030.25 | $6,826.86 | $26,203.39 | $29,174.14 | -$2,970.76 | 0.90 | $380,294.93 |
| 3 | $36,919.32 | $34,021.15 | $6,963.40 | $27,057.76 | $29,174.14 | -$2,116.39 | 0.93 | $371,825.62 |
| 4 | $38,026.90 | $35,041.79 | $7,102.67 | $27,939.12 | $29,174.14 | -$1,235.02 | 0.96 | $362,878.58 |
| 5 | $39,167.71 | $36,093.04 | $7,244.72 | $28,848.32 | $29,174.14 | -$325.82 | 0.99 | $353,426.86 |
| 6 | $40,342.74 | $37,175.83 | $7,389.61 | $29,786.22 | $29,174.14 | $612.08 | 1.02 | $343,441.99 |
| 7 | $41,553.02 | $38,291.11 | $7,537.41 | $30,753.70 | $29,174.14 | $1,579.56 | 1.05 | $332,893.89 |
| 8 | $42,799.61 | $39,439.84 | $7,688.15 | $31,751.69 | $29,174.14 | $2,577.55 | 1.09 | $321,750.80 |
| 9 | $44,083.60 | $40,623.04 | $7,841.92 | $32,781.12 | $29,174.14 | $3,606.98 | 1.12 | $309,979.14 |
| 10 | $45,406.11 | $41,841.73 | $7,998.75 | $33,842.97 | $29,174.14 | $4,668.83 | 1.16 | $297,543.48 |
| 11 | $46,768.29 | $43,096.98 | $8,158.73 | $34,938.25 | $29,174.14 | $5,764.11 | 1.20 | $284,406.34 |
| 12 | $48,171.34 | $44,389.89 | $8,321.90 | $36,067.98 | $29,174.14 | $6,893.84 | 1.24 | $270,528.17 |
| 13 | $49,616.48 | $45,721.59 | $8,488.34 | $37,233.24 | $29,174.14 | $8,059.10 | 1.28 | $255,867.16 |
| 14 | $51,104.97 | $47,093.23 | $8,658.11 | $38,435.12 | $29,174.14 | $9,260.98 | 1.32 | $240,379.15 |
| 15 | $52,638.12 | $48,506.03 | $8,831.27 | $39,674.76 | $29,174.14 | $10,500.62 | 1.36 | $224,017.50 |
| 16 | $54,217.27 | $49,961.21 | $9,007.90 | $40,953.31 | $29,174.14 | $11,779.17 | 1.40 | $206,732.92 |
| 17 | $55,843.78 | $51,460.05 | $9,188.05 | $42,271.99 | $29,174.14 | $13,097.85 | 1.45 | $188,473.35 |
| 18 | $57,519.10 | $53,003.85 | $9,371.82 | $43,632.03 | $29,174.14 | $14,457.89 | 1.50 | $169,183.81 |
| 19 | $59,244.67 | $54,593.96 | $9,559.25 | $45,034.71 | $29,174.14 | $15,860.57 | 1.54 | $148,806.18 |
| 20 | $61,022.01 | $56,231.78 | $9,750.44 | $46,481.35 | $29,174.14 | $17,307.20 | 1.59 | $127,279.09 |
| 21 | $62,852.67 | $57,918.74 | $9,945.45 | $47,973.29 | $29,174.14 | $18,799.15 | 1.64 | $104,537.70 |
| 22 | $64,738.25 | $59,656.30 | $10,144.35 | $49,511.94 | $29,174.14 | $20,337.80 | 1.70 | $80,513.53 |
| 23 | $66,680.40 | $61,445.99 | $10,347.24 | $51,098.75 | $29,174.14 | $21,924.60 | 1.75 | $55,134.20 |
| 24 | $68,680.81 | $63,289.37 | $10,554.19 | $52,735.18 | $29,174.14 | $23,561.04 | 1.81 | $28,323.27 |
| 25 | $70,741.23 | $65,188.05 | $10,765.27 | $54,422.78 | $29,174.14 | $25,248.64 | 1.87 | $0.00 |
| 26 | $72,863.47 | $67,143.69 | $10,980.58 | $56,163.11 | $0.00 | $56,163.11 | 0.00 | $0.00 |
| 27 | $75,049.38 | $69,158.00 | $11,200.19 | $57,957.81 | $0.00 | $57,957.81 | 0.00 | $0.00 |
| 28 | $77,300.86 | $71,232.74 | $11,424.19 | $59,808.55 | $0.00 | $59,808.55 | 0.00 | $0.00 |
| 29 | $79,619.88 | $73,369.72 | $11,652.68 | $61,717.05 | $0.00 | $61,717.05 | 0.00 | $0.00 |
| 30 | $82,008.48 | $75,570.81 | $11,885.73 | $63,685.09 | $0.00 | $63,685.09 | 0.00 | $0.00 |


## Valuation – Baseline Appreciation (g = 3.00%)

| Year | Estimated Value | LTV % | Available Equity @80% |
| ---: | ---: | ---: | ---: |
| 1 | $411,897.00 | 94.27% | -$58,794.40 |
| 2 | $424,253.91 | 89.64% | -$40,891.80 |
| 3 | $436,981.53 | 85.09% | -$22,240.40 |
| 4 | $450,090.97 | 80.62% | -$2,805.80 |
| 5 | $463,593.70 | 76.24% | $17,448.10 |
| 6 | $477,501.51 | 71.92% | $38,559.22 |
| 7 | $491,826.56 | 67.69% | $60,567.36 |
| 8 | $506,581.36 | 63.51% | $83,514.29 |
| 9 | $521,778.80 | 59.41% | $107,443.89 |
| 10 | $537,432.16 | 55.36% | $132,402.25 |
| 11 | $553,555.12 | 51.38% | $158,437.76 |
| 12 | $570,161.78 | 47.45% | $185,601.25 |
| 13 | $587,266.63 | 43.57% | $213,946.15 |
| 14 | $604,884.63 | 39.74% | $243,528.55 |
| 15 | $623,031.17 | 35.96% | $274,407.44 |
| 16 | $641,722.10 | 32.22% | $306,644.76 |
| 17 | $660,973.77 | 28.51% | $340,305.66 |
| 18 | $680,802.98 | 24.85% | $375,458.58 |
| 19 | $701,227.07 | 21.22% | $412,175.48 |
| 20 | $722,263.88 | 17.62% | $450,532.02 |
| 21 | $743,931.80 | 14.05% | $490,607.74 |
| 22 | $766,249.75 | 10.51% | $532,486.28 |
| 23 | $789,237.25 | 6.99% | $576,255.60 |
| 24 | $812,914.36 | 3.48% | $622,008.22 |
| 25 | $837,301.79 | 0.00% | $669,841.44 |
| 26 | $862,420.85 | 0.00% | $689,936.68 |
| 27 | $888,293.47 | 0.00% | $710,634.78 |
| 28 | $914,942.28 | 0.00% | $731,953.82 |
| 29 | $942,390.55 | 0.00% | $753,912.44 |
| 30 | $970,662.26 | 0.00% | $776,529.81 |


## Valuation – Stress-Test (rate-anchored: r/3 = 1.83%, adj = $0.00)

| Year | Estimated Value | LTV % | Available Equity @80% |
| ---: | ---: | ---: | ---: |
| 1 | $407,231.50 | 95.35% | -$62,526.80 |
| 2 | $414,697.41 | 91.70% | -$48,537.00 |
| 3 | $422,300.20 | 88.05% | -$33,985.46 |
| 4 | $430,042.37 | 84.38% | -$18,844.69 |
| 5 | $437,926.48 | 80.70% | -$3,085.68 |
| 6 | $445,955.13 | 77.01% | $13,322.11 |
| 7 | $454,130.97 | 73.30% | $30,410.89 |
| 8 | $462,456.71 | 69.57% | $48,214.57 |
| 9 | $470,935.08 | 65.82% | $66,768.92 |
| 10 | $479,568.89 | 62.04% | $86,111.64 |
| 11 | $488,360.99 | 58.24% | $106,282.45 |
| 12 | $497,314.27 | 54.40% | $127,323.25 |
| 13 | $506,431.70 | 50.52% | $149,278.20 |
| 14 | $515,716.28 | 46.61% | $172,193.87 |
| 15 | $525,171.08 | 42.66% | $196,119.37 |
| 16 | $534,799.22 | 38.66% | $221,106.45 |
| 17 | $544,603.87 | 34.61% | $247,209.74 |
| 18 | $554,588.27 | 30.51% | $274,486.81 |
| 19 | $564,755.72 | 26.35% | $302,998.40 |
| 20 | $575,109.58 | 22.13% | $332,808.57 |
| 21 | $585,653.25 | 17.85% | $363,984.90 |
| 22 | $596,390.23 | 13.50% | $396,598.66 |
| 23 | $607,324.05 | 9.08% | $430,725.05 |
| 24 | $618,458.33 | 4.58% | $466,443.39 |
| 25 | $629,796.73 | 0.00% | $503,837.38 |
| 26 | $641,343.00 | 0.00% | $513,074.40 |
| 27 | $653,100.96 | 0.00% | $522,480.77 |
| 28 | $665,074.47 | 0.00% | $532,059.58 |
| 29 | $677,267.51 | 0.00% | $541,814.01 |
| 30 | $689,684.08 | 0.00% | $551,747.26 |


## Valuation – NOI-Based (with Cap Drift)

| Year | Cap Rate (applied) | Estimated Value | LTV % | Available Equity @80% |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 6.35% | $399,900.00 | 97.10% | -$68,392.00 |
| 2 | 6.40% | $409,723.27 | 92.82% | -$52,516.31 |
| 3 | 6.45% | $419,800.38 | 88.57% | -$35,985.32 |
| 4 | 6.50% | $430,137.97 | 84.36% | -$18,768.21 |
| 5 | 6.55% | $440,742.86 | 80.19% | -$832.57 |
| 6 | 6.60% | $451,622.07 | 76.05% | $17,855.66 |
| 7 | 6.65% | $462,782.77 | 71.93% | $37,332.32 |
| 8 | 6.70% | $474,232.35 | 67.85% | $57,635.08 |
| 9 | 6.75% | $485,978.39 | 63.78% | $78,803.57 |
| 10 | 6.80% | $498,028.68 | 59.74% | $100,879.47 |
| 11 | 6.85% | $510,391.20 | 55.72% | $123,906.62 |
| 12 | 6.90% | $523,074.16 | 51.72% | $147,931.16 |
| 13 | 6.95% | $536,085.99 | 47.73% | $173,001.63 |
| 14 | 7.00% | $549,435.32 | 43.75% | $199,169.11 |
| 15 | 7.05% | $563,131.05 | 39.78% | $226,487.35 |
| 16 | 7.10% | $577,182.30 | 35.82% | $255,012.92 |
| 17 | 7.15% | $591,598.41 | 31.86% | $284,805.38 |
| 18 | 7.20% | $606,389.02 | 27.90% | $315,927.41 |
| 19 | 7.25% | $621,563.98 | 23.94% | $348,445.01 |
| 20 | 7.30% | $637,133.44 | 19.98% | $382,427.66 |
| 21 | 7.35% | $653,107.79 | 16.01% | $417,948.53 |
| 22 | 7.40% | $669,497.73 | 12.03% | $455,084.66 |
| 23 | 7.45% | $686,314.22 | 8.03% | $493,917.18 |
| 24 | 7.50% | $703,568.54 | 4.03% | $534,531.56 |
| 25 | 7.55% | $721,272.24 | 0.00% | $577,017.80 |
| 26 | 7.60% | $739,437.22 | 0.00% | $591,549.77 |
| 27 | 7.65% | $758,075.66 | 0.00% | $606,460.52 |
| 28 | 7.70% | $777,200.08 | 0.00% | $621,760.06 |
| 29 | 7.75% | $796,823.35 | 0.00% | $637,458.68 |
| 30 | 7.80% | $816,958.68 | 0.00% | $653,566.94 |


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

- **IRR:** 15.34%
- **Equity Multiple:** 47.83x


## Warnings

- Cap-rate spread 0.845% below target 1.500%.
- Subscale risk: fewer than 4 units.
- Negative cash flow in one or more years.
