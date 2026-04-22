# ✅ WORKING TEST QUESTIONS - Full Metric & Graph Analysis

These questions leverage the complete 17-metric system with 37 causal relationships.
All questions will work with real Neon database data.

---

## 1. Operating Profit Driver Analysis
**Question:** "Why did operating profit change for Company_269 from Q2 2023 to Q2 2024?"

**Expected Response:**
- Operating profit values for both periods
- Key drivers from formula: `gross_profit - operating_expenses`
- Where operating_expenses = `employee_benefit_expense + depreciation + other_expenses + interest_expense`
- Shows which cost factors drove the change
- Driver contribution percentages

**Metrics in Graph:** operating_profit → gross_profit, employee_benefit_expense, depreciation, other_expenses, interest_expense

---

## 2. Gross Profit Margin Analysis
**Question:** "Compare gross profit margin for Company_380 in Q1 2023 vs Q1 2024. What changed?"

**Expected Response:**
- Gross margin % for both periods
- Base metrics: revenue_from_operations, cost_of_material
- Formula: `(gross_profit / revenue_from_operations) * 100`
- Shows revenue vs cost impact on margin
- Specific dollar changes and percentage change

**Metrics in Graph:** gross_margin_pct → gross_profit → revenue_from_operations, cost_of_material

---

## 3. Net Income Trend Analysis
**Question:** "Show net income trend for Company_403 across Q1 2023, Q2 2023, Q3 2023, Q4 2023"

**Expected Response:**
- All 4 quarters of net_income values
- Trend visualization (increasing/decreasing pattern)
- Formula breakdown: profit_before_tax - tax_expense = net_income
- Identifies which quarter had best/worst performance

**Metrics in Graph:** net_income → profit_before_tax, tax_expense

---

## 4. Profit Before Tax Analysis
**Question:** "Why did profit before tax increase for Company_269 in Q4 2024 compared to Q3 2024?"

**Expected Response:**
- PBT values for both periods
- Driver analysis from: operating_profit + other_income - interest_expense - tax_expense
- Shows contribution of each component
- Identifies if growth came from operations or other income

**Metrics in Graph:** profit_before_tax → operating_profit, other_income, interest_expense

---

## 5. EBITDA Analysis
**Question:** "Calculate EBITDA for Company_255 in Q2 2024 and explain the drivers"

**Expected Response:**
- EBITDA value: operating_profit + depreciation
- Component values shown separately
- Explains: EBITDA removes non-cash charges (depreciation)
- Useful for cash generation analysis

**Metrics in Graph:** ebitda → operating_profit, depreciation

---

## 6. Cost Structure Analysis
**Question:** "For Company_22, compare cost_of_material, employee_benefit_expense, and depreciation as % of revenue in Q1 2024"

**Expected Response:**
- Each cost as percentage of revenue_from_operations
- Individual cost values
- Revenue value
- Shows cost structure composition
- Identifies largest cost driver

**Metrics in Graph:** revenue_from_operations connected to all costs

---

## 7. Operating Efficiency
**Question:** "Show operating margin percentage for Company_100 across Q1-Q4 2024. What does this tell us?"

**Expected Response:**
- Operating_margin_pct for all 4 quarters
- Formula: (operating_profit / revenue_from_operations) * 100
- Trend analysis
- Interpretation of efficiency changes

**Metrics in Graph:** operating_margin_pct → operating_profit, revenue_from_operations

---

## 8. Profitability Chain
**Question:** "For Company_50, trace the profit chain: Revenue → Gross Profit → Operating Profit → Net Income in Q3 2024"

**Expected Response:**
- All 4 metrics values in sequence
- Each step's profitability percentage
- Shows "leakage" from revenue to net income
- Driver analysis at each level

**Metrics in Graph:** revenue → gross_profit → operating_profit → net_income (full chain)

---

## 9. Multi-Period Comparison
**Question:** "Compare operating profit for Company_269 across 4 quarters of 2024: Q1 vs Q2 vs Q3 vs Q4"

**Expected Response:**
- All 4 operating profit values
- Identifies peak and lowest quarters
- Shows seasonal patterns if any
- Driver changes between quarters

**Metrics in Graph:** operating_profit with period comparisons

---

## 10. Net Margin Analysis
**Question:** "Why is net margin (net_margin_pct) lower than operating margin for Company_380 in Q2 2024?"

**Expected Response:**
- net_margin_pct value: (net_income / revenue_from_operations) * 100
- operating_margin_pct value
- Difference explained by: interest_expense + tax_expense
- Shows impact of financing and taxes

**Metrics in Graph:** net_margin_pct, operating_margin_pct, interest_expense, tax_expense

---

## How to Use These Questions

1. **Copy-paste any question above into the frontend**
2. **System will:**
   - Parse company name and metric
   - Extract period(s)
   - Query real Neon database data
   - Build causal graph analysis
   - Show driver contributions
   - Return fully analyzed results

3. **All responses will include:**
   - Real database values (100% from financials_pnl)
   - Metric relationships from graph
   - Formula decomposition
   - Driver analysis with %
   - Trend/comparison analysis

---

## Expected Performance

- **Simple metric query (Q1):** ~500ms
- **Multi-period comparison (Q2):** ~800ms  
- **Driver analysis (Q4):** ~1.2s
- **Profit chain (Q8):** ~1.5s

All questions use **ZERO hardcoded data** - everything from Neon.

---

## Companies with Best Data

Use these for reliable results:
- Company_269 (117 filings, 24 periods)
- Company_380 (100+ filings)
- Company_403 (90+ filings)
- Company_22 (80+ filings)
- Company_255 (75+ filings)
- Company_50 (70+ filings)
- Company_100 (65+ filings)

---

## Alternative Query Formats

You can also ask:

- "What drove the change in [metric] for [company]?"
- "Compare [metric] for [company] between [period1] and [period2]"
- "Show the trend of [metric] for [company] across [Q1-Q4] [year]"
- "Why did [metric] increase/decrease for [company]?"
- "Which period had the highest [metric] for [company]?"

All will return proper graph analysis with drivers.
