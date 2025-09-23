# Investment Analysis – 20 Gallagher, Shediac, New Brunswick E4P1S8

**Amenities:**
- Central air conditioning
- Air exchanger
- Forced air heating
- Propane heat
- Municipal water
- Municipal sewage system
- Shed
- Corner lot
- Level lot
- Landscaped yard
- Freehold title
- Year-round access
- Cedar shingles exterior
- Block foundation
- Laminate, tile and vinyl flooring
- Basement with flex space
- Walkable downtown location

**Notes:**
- List price: $199,900
- 4 bedrooms, 1 bathroom (4pc)
- Potential to convert basement flex space into a 5th bedroom
- Basement bedroom listed; verify egress/legal conformity
- Square footage: 1,440 sq ft above grade (total finished also 1,440 sq ft; basement largely unfinished)
- Heating: forced air (propane); Cooling: central A/C; Air exchanger present
- Rental equipment: furnace and propane tank (buyer to assume or negotiate buyout)
- Lot size: 512 m2
- Annual property taxes: $2,620.85
- Utilities: municipal water and sewer
- Foundation: block; Exterior: cedar shingles
- Title: Freehold
- Prime downtown Shediac location; walkable to restaurants, shops, marina and Parlee Beach
- Suitable for end-user or investment (short-term or long-term rental potential)
- Quick closing available

**Condition & Defects:**
- As-is sale
- Priced under assessment
- Quick closing
- Investment potential
- Unfinished basement
- Rental equipment attached


## Purchase Metrics

- **Cap Rate (Y1):** 1.41%
- **Cash-on-Cash (Y1):** -71.01%
- **DSCR (Y1):** 0.21
- **Annual Debt Service (Y1):** $13,471.01
- **Acquisition Cash Outlay:** $14,995.00
- **Cap Rate – Interest Spread:** -3.29%


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

- **Verdict:** PASS
- **Rationale:**
  - Year-1 DSCR of 0.21 is far below 1.00 and remains <1.00 for roughly 25 years, indicating inability to cover debt service from NOI
  - Purchase cap rate of 1.41% is materially below typical underwriting floors and implied debt costs, with a negative cap-rate spread of -3.29%
  - Cash-on-cash return at acquisition is -71.01%, driven by projected Year-1 cash flow of approximately -$10.65k
  - 10-year IRR of 3.38% is well below risk-adjusted return hurdles for small residential rentals
  - Persistent negative cash flow through the amortization period requires ongoing capital infusions and increases risk
  - Subscale asset risk (fewer than 4 units) amplifies vacancy and expense shocks
  - Operating costs and third-party management burden are high relative to GOI, constraining NOI growth
  - As-is sale and potential code/egress compliance for basement bedroom introduce unmodeled capex risk
  - Rental equipment obligations (furnace and propane tank) may add recurring costs not fully reflected in the model
  - Small-market exposure limits exit liquidity and rent growth certainty, undermining refinancing or disposition upside


## 30-Year Pro Forma (Summary)

| Year | GSI | GOI | Total OPEX | NOI | Debt Service | Cash Flow | DSCR | Ending Balance |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | $37,200.00 | $24,180.00 | $21,357.00 | $2,823.00 | $13,471.01 | -$10,648.01 | 0.21 | $193,640.33 |
| 2 | $38,688.00 | $25,147.20 | $22,104.49 | $3,042.71 | $13,471.01 | -$10,428.30 | 0.23 | $189,175.05 |
| 3 | $40,235.52 | $26,153.09 | $22,878.15 | $3,274.94 | $13,471.01 | -$10,196.07 | 0.24 | $184,495.31 |
| 4 | $41,844.94 | $27,199.21 | $23,678.89 | $3,520.32 | $13,471.01 | -$9,950.68 | 0.26 | $179,590.82 |
| 5 | $43,518.74 | $28,287.18 | $24,507.65 | $3,779.53 | $13,471.01 | -$9,691.48 | 0.28 | $174,450.80 |
| 6 | $45,259.49 | $29,418.67 | $25,365.42 | $4,053.25 | $13,471.01 | -$9,417.76 | 0.30 | $169,063.91 |
| 7 | $47,069.87 | $30,595.41 | $26,253.21 | $4,342.21 | $13,471.01 | -$9,128.80 | 0.32 | $163,418.32 |
| 8 | $48,952.66 | $31,819.23 | $27,172.07 | $4,647.16 | $13,471.01 | -$8,823.85 | 0.34 | $157,501.60 |
| 9 | $50,910.77 | $33,092.00 | $28,123.09 | $4,968.91 | $13,471.01 | -$8,502.10 | 0.37 | $151,300.72 |
| 10 | $52,947.20 | $34,415.68 | $29,107.40 | $5,308.28 | $13,471.01 | -$8,162.73 | 0.39 | $144,802.04 |
| 11 | $55,065.09 | $35,792.31 | $30,126.16 | $5,666.15 | $13,471.01 | -$7,804.86 | 0.42 | $137,991.25 |
| 12 | $57,267.69 | $37,224.00 | $31,180.57 | $6,043.43 | $13,471.01 | -$7,427.58 | 0.45 | $130,853.37 |
| 13 | $59,558.40 | $38,712.96 | $32,271.89 | $6,441.07 | $13,471.01 | -$7,029.94 | 0.48 | $123,372.69 |
| 14 | $61,940.73 | $40,261.48 | $33,401.41 | $6,860.07 | $13,471.01 | -$6,610.94 | 0.51 | $115,532.74 |
| 15 | $64,418.36 | $41,871.94 | $34,570.46 | $7,301.48 | $13,471.01 | -$6,169.53 | 0.54 | $107,316.28 |
| 16 | $66,995.10 | $43,546.81 | $35,780.42 | $7,766.39 | $13,471.01 | -$5,704.62 | 0.58 | $98,705.21 |
| 17 | $69,674.90 | $45,288.69 | $37,032.74 | $8,255.95 | $13,471.01 | -$5,215.06 | 0.61 | $89,680.58 |
| 18 | $72,461.90 | $47,100.23 | $38,328.89 | $8,771.35 | $13,471.01 | -$4,699.66 | 0.65 | $80,222.55 |
| 19 | $75,360.37 | $48,984.24 | $39,670.40 | $9,313.85 | $13,471.01 | -$4,157.16 | 0.69 | $70,310.28 |
| 20 | $78,374.79 | $50,943.61 | $41,058.86 | $9,884.75 | $13,471.01 | -$3,586.26 | 0.73 | $59,921.97 |
| 21 | $81,509.78 | $52,981.36 | $42,495.92 | $10,485.44 | $13,471.01 | -$2,985.57 | 0.78 | $49,034.75 |
| 22 | $84,770.17 | $55,100.61 | $43,983.28 | $11,117.33 | $13,471.01 | -$2,353.67 | 0.83 | $37,624.66 |
| 23 | $88,160.98 | $57,304.64 | $45,522.69 | $11,781.94 | $13,471.01 | -$1,689.07 | 0.87 | $25,666.60 |
| 24 | $91,687.42 | $59,596.82 | $47,115.99 | $12,480.83 | $13,471.01 | -$990.17 | 0.93 | $13,134.24 |
| 25 | $95,354.91 | $61,980.69 | $48,765.05 | $13,215.65 | $13,471.01 | -$255.36 | 0.98 | $0.00 |
| 26 | $99,169.11 | $64,459.92 | $50,471.82 | $13,988.10 | $0.00 | $13,988.10 | 0.00 | $0.00 |
| 27 | $103,135.88 | $67,038.32 | $52,238.34 | $14,799.98 | $0.00 | $14,799.98 | 0.00 | $0.00 |
| 28 | $107,261.31 | $69,719.85 | $54,066.68 | $15,653.17 | $0.00 | $15,653.17 | 0.00 | $0.00 |
| 29 | $111,551.76 | $72,508.65 | $55,959.01 | $16,549.63 | $0.00 | $16,549.63 | 0.00 | $0.00 |
| 30 | $116,013.83 | $75,408.99 | $57,917.58 | $17,491.41 | $0.00 | $17,491.41 | 0.00 | $0.00 |


## Valuation – Baseline Appreciation (g = 3.00%)

| Year | Estimated Value | LTV % | Available Equity @80% |
| ---: | ---: | ---: | ---: |
| 1 | $205,897.00 | 94.05% | -$28,922.73 |
| 2 | $212,073.91 | 89.20% | -$19,515.92 |
| 3 | $218,436.13 | 84.46% | -$9,746.41 |
| 4 | $224,989.21 | 79.82% | $400.55 |
| 5 | $231,738.89 | 75.28% | $10,940.31 |
| 6 | $238,691.05 | 70.83% | $21,888.93 |
| 7 | $245,851.79 | 66.47% | $33,263.10 |
| 8 | $253,227.34 | 62.20% | $45,080.27 |
| 9 | $260,824.16 | 58.01% | $57,358.61 |
| 10 | $268,648.88 | 53.90% | $70,117.07 |
| 11 | $276,708.35 | 49.87% | $83,375.43 |
| 12 | $285,009.60 | 45.91% | $97,154.31 |
| 13 | $293,559.89 | 42.03% | $111,475.22 |
| 14 | $302,366.69 | 38.21% | $126,360.60 |
| 15 | $311,437.69 | 34.46% | $141,833.87 |
| 16 | $320,780.82 | 30.77% | $157,919.45 |
| 17 | $330,404.24 | 27.14% | $174,642.81 |
| 18 | $340,316.37 | 23.57% | $192,030.55 |
| 19 | $350,525.86 | 20.06% | $210,110.41 |
| 20 | $361,041.64 | 16.60% | $228,911.34 |
| 21 | $371,872.88 | 13.19% | $248,463.56 |
| 22 | $383,029.07 | 9.82% | $268,798.60 |
| 23 | $394,519.94 | 6.51% | $289,949.36 |
| 24 | $406,355.54 | 3.23% | $311,950.20 |
| 25 | $418,546.21 | 0.00% | $334,836.97 |
| 26 | $431,102.59 | 0.00% | $344,882.08 |
| 27 | $444,035.67 | 0.00% | $355,228.54 |
| 28 | $457,356.74 | 0.00% | $365,885.39 |
| 29 | $471,077.44 | 0.00% | $376,861.96 |
| 30 | $485,209.77 | 0.00% | $388,167.81 |


## Valuation – Stress-Test (rate-anchored: r/3 = 1.57%, adj = $0.00)

| Year | Estimated Value | LTV % | Available Equity @80% |
| ---: | ---: | ---: | ---: |
| 1 | $203,031.77 | 95.37% | -$31,214.92 |
| 2 | $206,212.60 | 91.74% | -$24,204.97 |
| 3 | $209,443.26 | 88.09% | -$16,940.70 |
| 4 | $212,724.54 | 84.42% | -$9,411.19 |
| 5 | $216,057.22 | 80.74% | -$1,605.02 |
| 6 | $219,442.12 | 77.04% | $6,489.78 |
| 7 | $222,880.05 | 73.32% | $14,885.71 |
| 8 | $226,371.83 | 69.58% | $23,595.87 |
| 9 | $229,918.33 | 65.81% | $32,633.94 |
| 10 | $233,520.38 | 62.01% | $42,014.27 |
| 11 | $237,178.87 | 58.18% | $51,751.84 |
| 12 | $240,894.67 | 54.32% | $61,862.36 |
| 13 | $244,668.68 | 50.42% | $72,362.26 |
| 14 | $248,501.83 | 46.49% | $83,268.72 |
| 15 | $252,395.02 | 42.52% | $94,599.74 |
| 16 | $256,349.21 | 38.50% | $106,374.16 |
| 17 | $260,365.35 | 34.44% | $118,611.70 |
| 18 | $264,444.41 | 30.34% | $131,332.98 |
| 19 | $268,587.37 | 26.18% | $144,559.62 |
| 20 | $272,795.24 | 21.97% | $158,314.22 |
| 21 | $277,069.03 | 17.70% | $172,620.48 |
| 22 | $281,409.78 | 13.37% | $187,503.16 |
| 23 | $285,818.53 | 8.98% | $202,988.23 |
| 24 | $290,296.35 | 4.52% | $219,102.85 |
| 25 | $294,844.33 | 0.00% | $235,875.46 |
| 26 | $299,463.56 | 0.00% | $239,570.85 |
| 27 | $304,155.15 | 0.00% | $243,324.12 |
| 28 | $308,920.25 | 0.00% | $247,136.20 |
| 29 | $313,760.00 | 0.00% | $251,008.00 |
| 30 | $318,675.58 | 0.00% | $254,940.46 |


## Valuation – NOI-Based (with Cap Drift)

| Year | Cap Rate (applied) | Estimated Value | LTV % | Available Equity @80% |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 1.41% | $199,900.00 | 96.87% | -$33,720.33 |
| 2 | 1.46% | $208,090.02 | 90.91% | -$22,703.03 |
| 3 | 1.51% | $216,566.75 | 85.19% | -$11,241.90 |
| 4 | 1.56% | $225,343.11 | 79.70% | $683.67 |
| 5 | 1.61% | $234,432.26 | 74.41% | $13,095.01 |
| 6 | 1.66% | $243,847.66 | 69.33% | $26,014.22 |
| 7 | 1.71% | $253,603.11 | 64.44% | $39,464.16 |
| 8 | 1.76% | $263,712.75 | 59.72% | $53,468.60 |
| 9 | 1.81% | $274,191.17 | 55.18% | $68,052.21 |
| 10 | 1.86% | $285,053.35 | 50.80% | $83,240.64 |
| 11 | 1.91% | $296,314.77 | 46.57% | $99,060.56 |
| 12 | 1.96% | $307,991.39 | 42.49% | $115,539.74 |
| 13 | 2.01% | $320,099.70 | 38.54% | $132,707.07 |
| 14 | 2.06% | $332,656.75 | 34.73% | $150,592.66 |
| 15 | 2.11% | $345,680.17 | 31.04% | $169,227.86 |
| 16 | 2.16% | $359,188.19 | 27.48% | $188,645.35 |
| 17 | 2.21% | $373,199.71 | 24.03% | $208,879.18 |
| 18 | 2.26% | $387,734.27 | 20.69% | $229,964.87 |
| 19 | 2.31% | $402,812.13 | 17.45% | $251,939.42 |
| 20 | 2.36% | $418,454.28 | 14.32% | $274,841.45 |
| 21 | 2.41% | $434,682.46 | 11.28% | $298,711.22 |
| 22 | 2.46% | $451,519.23 | 8.33% | $323,590.72 |
| 23 | 2.51% | $468,987.94 | 5.47% | $349,523.76 |
| 24 | 2.56% | $487,112.84 | 2.70% | $376,556.03 |
| 25 | 2.61% | $505,919.05 | 0.00% | $404,735.24 |
| 26 | 2.66% | $525,432.62 | 0.00% | $420,346.10 |
| 27 | 2.71% | $545,680.60 | 0.00% | $436,544.48 |
| 28 | 2.76% | $566,691.00 | 0.00% | $453,352.80 |
| 29 | 2.81% | $588,492.92 | 0.00% | $470,794.33 |
| 30 | 2.86% | $611,116.51 | 0.00% | $488,893.21 |


## Operating Expenses - Year 1 Detail

- Insurance: $1,200.00
- Taxes: $2,621.00
- Utilities: $3,600.00
- Water & Sewer: $1,200.00
- Property Management: $8,360.00
- Repairs & Maintenance: $3,500.00
- Trash: $0.00
- Landscaping: $276.00
- Snow Removal: $600.00
- HOA Fees: $0.00
- Reserves: $0.00
- Other: $0.00
- **Total OPEX (Y1):** $21,357.00


## Returns Summary (10-Year)

- **IRR:** 3.38%
- **Equity Multiple:** 13.27x


## Warnings

- Purchase cap rate 1.412% below floor 5.000%.
- Cap-rate spread -3.288% below target 1.500%.
- Subscale risk: fewer than 4 units.
- Negative cash flow in one or more years.
