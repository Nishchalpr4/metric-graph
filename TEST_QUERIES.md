# Test Questions for Causal Financial Knowledge Graph

## Multi-Company Questions

### Castrol India Ltd
- Why did operating profit increase for Castrol India Ltd in Q2 2024 compared to Q2 2021?
- What was the revenue from operations for Castrol India Ltd in Q3 2023?
- How did cost of material change for Castrol India Ltd between Q1 2023 and Q1 2024?
- Why did net profit decline for Castrol India Ltd in Q4 2021 vs Q4 2020?
- What drove the changes in employee benefit expense for Castrol India Ltd in H1 2024?
- Compare depreciation trends for Castrol India Ltd across Q2 2020, Q2 2022, and Q2 2024

### ASK Automotive Ltd
- Why did revenue from operations change for ASK Automotive Ltd in Q2 2024 vs Q2 2021?
- What was the operating profit for ASK Automotive Ltd in Q1 2023?
- How did other expenses affect operating profit for ASK Automotive Ltd in Q3 2024?
- What was the cost of material for ASK Automotive Ltd in Q4 2022?
- Why did net profit increase/decrease for ASK Automotive Ltd in recent quarters?

### Alicon Castalloy Ltd
- What drove the change in operating profit for Alicon Castalloy Ltd in Q2 2024?
- How much revenue did Alicon Castalloy Ltd make in Q1 2024?
- What were the key cost drivers (material, labour, depreciation) for Alicon Castalloy in Q3 2023?

### Motherson Sumi Systems Ltd
- Why did operating profit change for Motherson Sumi Systems Ltd in Q2 2024 vs Q2 2023?
- What was the gross profit contribution by revenue for Motherson in H2 2024?

### GTO Bearing Ltd
- How did other expenses impact operating profit for GTO Bearing Ltd in Q4 2023?
- What was the operating cash efficiency (revenue/employee benefit) for GTO Bearing in Q2 2024?

---

## Revenue-Focused Questions

- Why did revenue from operations increase for [Company] in Q2 2024?
- What was the segmental revenue for [Company] in Q1 2024?
- How did revenue growth rate differ between Q1 and Q2 2024 for [Company]?
- What percentage of total income came from revenue from operations for [Company] in Q3 2023?

---

## Operating Profit / Margin Analysis

- Why did operating profit margin improve for [Company] in Q2 2024 vs Q2 2023?
- What was the operating profit for [Company] in each quarter of 2023?
- How did depreciation as % of revenue impact operating profit for [Company]?
- Did operating profit grow faster than revenue for [Company] in Q3 2024?

---

## Cost Structure Questions

- How much did cost of material increase for [Company] between Q1 2023 and Q1 2024?
- What was the ratio of cost of material to revenue for [Company] in Q2 2024?
- Why did employee benefit expense change for [Company] in H1 2024?
- How did depreciation expense trend for [Company] over the past 8 quarters?
- What was the impact of other expenses on operating profit for [Company] in Q4 2023?

---

## Profitability Questions

- Why did net profit (PNL for period) change for [Company] in Q2 2024 vs Q2 2021?
- What was the net margin for [Company] in Q1 2023?
- How did profit before tax compare to net profit for [Company] in Q3 2024?
- What was the tax burden (tax as % of PBT) for [Company] in Q2 2023?

---

## Period-over-Period Questions

- How did [Company]'s financial metrics change from Q2 2023 to Q2 2024?
- Compare [Company]'s profitability in Q1 across 2021, 2022, 2023, 2024
- Was [Company]'s operating efficiency better in H1 or H2 2024?
- What changed in [Company]'s cost structure from 2021 to 2024?

---

## Comparative Questions (Multiple Companies)

- Compare operating profit margins: Castrol vs ASK Automotive vs Motherson in Q2 2024
- Which company had higher revenue in Q1 2024: Castrol or ASK Automotive?
- How did cost of material as % of revenue differ in Q2 2024 across all companies?
- Which company improved profitability the most between 2021 and 2024?

---

## Drill-Down Navigation Questions

After initial analysis, click on nodes to explore:
- *Click "Operating Profit" node* → breaks into Gross Profit + Other Expenses
- *Click "Gross Profit" node* → breaks into Revenue + Cost of Material relationships
- *Click "Revenue from Operations"* → see segmental breakdown
- *Click "Other Expenses"* → see component drivers

---

## Advanced Causal Analysis

- What was the multiplier effect of a 10% revenue increase on operating profit for [Company]?
- Did [Company]'s variable costs scale proportionally with revenue in Q2 2024?
- How did fixed costs (depreciation) impact profitability for [Company] in different quarters?
- What was the contribution margin for [Company] in Q1 2024?

---

## Expected System Capabilities

The system should handle:
✓ Any company from 209 in database  
✓ Any metric from 17 in metrics table  
✓ Any period from 44 available  
✓ Period-over-period comparisons  
✓ Hierarchical drill-down via graph navigation  
✓ Causal decomposition (what drives what)  
✓ Calculated derived metrics (margins, ratios, changes)  

---

## Example Verified Companies (209 total available)

- Castrol India Ltd
- ASK Automotive Ltd  
- Alicon Castalloy Ltd
- Motherson Sumi Systems Ltd
- GTO Bearing Ltd
- Almondz Global Securities Ltd
- Axle India Ltd
- Bharat Petroleum Corporation Ltd
- Bombay Dyeing & Mfg Co Ltd
- Cummins India Ltd
- Deepak Fertilisers & Petrochemicals Corporation Ltd
- Eicher Motors Ltd
- Ester Industries Ltd
- Fiem Industries Ltd
- Force Motors Ltd
- Grindwell Norton Ltd
- Haryana Petrochemicals Ltd
- Hindustan Motors Ltd
- Hindustan Petroleum Corporation Ltd
- [... and 189 more Indian auto-sector companies]

---

## Query Testing Strategy

**Phase 1 - Basic Verification:**
1. Try same question across 3 different companies
2. Try 3 different questions on same company
3. Verify graph shows correct causal structure each time

**Phase 2 - Metric Coverage:**
1. Test Revenue questions → verify revenue_from_operations is correct
2. Test Profit questions → verify operating_profit, pbt, pnl_for_period
3. Test Cost questions → verify cost_of_material, employee_benefit, depreciation, other_expenses
4. Test Margin questions → verify calculated percentages

**Phase 3 - Navigation:**
1. Ask question about Operating Profit
2. Graph appears with causal drivers
3. Click on "Gross Profit" node → drills into sub-components
4. Click on "Revenue" node → sees what drives it
5. Breadcrumb trail updates correctly

**Phase 4 - Time Series:**
1. Compare Q2 across multiple years
2. Compare Q1 vs Q2 vs Q3 vs Q4 in same year
3. 8-quarter trends
4. Year-over-year changes

