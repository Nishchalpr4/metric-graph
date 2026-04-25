# 🌐 FRONTEND TESTING GUIDE

## ✅ Setup Complete

**Server:** Running on http://localhost:8002  
**Frontend:** Opened in browser (file:///C:/Users/nishc/Downloads/metric-graph-main(1)/metric-graph-main/frontend/index.html)  
**Database:** Fixed and fully operational (100% of filings linked)

---

## 📝 Test Queries for Different Companies

Based on our test results, here are real companies with data you can query:

### **Test Company 1: Company_269** (117 filings - Most data!)

**Revenue Analysis:**
```
Why did revenue change for Company_269 in Q4 2025?
```

**Expected Result:**
- Current Revenue: 1,362.75
- Previous Revenue (Q2 2025): 1,496.83
- Change: -8.96% ↓
- Shows operating profit, depreciation, employee benefits

**Metric Queries:**
```
What is the operating profit for Company_269?
Show me depreciation for Company_269 in Q4 2025
```

---

### **Test Company 2: Company_380** (114 filings)

**Revenue Analysis:**
```
Why did revenue decrease for Company_380?
```

**Expected Result:**
- Current Revenue: 66.46
- Previous Revenue: 71.44
- Change: -6.97% ↓

**Profitability:**
```
What is the profit before tax for Company_380?
Show cost of materials for Company_380
```

---

### **Test Company 3: Company_244** (114 filings)

**Revenue Analysis:**
```
Explain revenue change for Company_244
```

**Expected Result:**
- Current Revenue: 200.22
- Previous Revenue: 206.38
- Change: -2.98% ↓

**Cost Analysis:**
```
What are the employee benefits for Company_244?
Show total costs for Company_244
```

---

### **Test Company 4: Company_403** (114 filings) - REVENUE GREW! ✅

**Revenue Growth:**
```
Why did revenue increase for Company_403?
```

**Expected Result:**
- Current Revenue: 84.19
- Previous Revenue: 78.03
- Change: +7.89% ↑ (Positive growth!)

**Profit Analysis:**
```
What is the profit before tax for Company_403?
Show operating profit trend for Company_403
```

---

### **Test Company 5: Company_359** (114 filings) - ALSO GREW! ✅

**Revenue Growth:**
```
Explain revenue increase for Company_359
```

**Expected Result:**
- Current Revenue: 37.87
- Previous Revenue: 34.55
- Change: +9.61% ↑ (Strong growth!)

**Metrics:**
```
What is depreciation for Company_359?
Show all metrics for Company_359 in Q4 2025
```

---

## 🎯 Available Metrics to Query

Based on real data (verified from database):

1. **revenue_from_operations** - Total revenue
2. **cost_of_material** - Material costs
3. **operating_profit** - Operating profit/loss
4. **profit_before_tax** - Profit before tax
5. **depreciation** - Depreciation expense
6. **employee_benefit_expense** - Employee costs

---

## 📊 Test Scenarios

### Scenario 1: Simple Metric Query
```
What is the revenue for Company_269?
```
**Expected:** Returns latest revenue value (1,362.75)

### Scenario 2: Period Comparison
```
Compare revenue for Company_269 between Q4 2025 and Q2 2025
```
**Expected:** Shows -8.96% decrease

### Scenario 3: Multiple Metrics
```
Show all financial metrics for Company_380 in Q4 2025
```
**Expected:** Lists all 6 available metrics with values

### Scenario 4: Trend Analysis
```
What is the revenue trend for Company_403?
```
**Expected:** Shows increasing trend (+7.89%)

### Scenario 5: Cost Analysis
```
Why did costs change for Company_244?
```
**Expected:** Shows cost breakdown and changes

---

## ✅ What Should Work

Based on the core database fix:

✅ **All company queries return REAL values** (no more N/A!)  
✅ **Period comparisons work correctly**  
✅ **6 metrics queryable per company**  
✅ **Time series data available** (Q1 2025 → Q4 2025)  
✅ **Causal analysis** (if implemented in query handler)  
✅ **200 companies with data**

---

## 🧪 Quick Test Checklist

1. **Open Frontend:** ✅ Already opened in browser
2. **Test Simple Query:** Ask "What is revenue for Company_269?"
3. **Test Comparison:** Ask "Why did revenue change for Company_269?"
4. **Test Different Company:** Ask "Show metrics for Company_403"
5. **Test Growth Company:** Ask "Explain revenue increase for Company_359"
6. **Check No N/A:** Verify all responses show real numbers, not N/A

---

## 🐛 If You See Errors

### Error: "Cannot connect to server"
- **Fix:** Make sure server is running on port 8002
- **Command:** `cd backend; $env:PORT=8002; py wsgi.py`

### Error: "N/A" in results
- **Should NOT happen** - database is fixed!
- If you see this, let me know - there might be a frontend parsing issue

### Error: "Company not found"
- **Use:** Company_269, Company_380, Company_244, Company_403, or Company_359
- **NOT:** Company_1 through Company_21 (these have no data)

### Error: "Metric not found"
- **Use:** revenue_from_operations, cost_of_material, operating_profit, etc.
- **Check:** See "Available Metrics to Query" section above

---

## 📈 Expected UI Behavior

When you ask a query, you should see:

1. **Loading indicator** while processing
2. **Result card** with:
   - Company name
   - Metric values (REAL numbers, not N/A)
   - Period information (Q4 2025, Q2 2025, etc.)
   - Change percentage
   - Direction indicator (↑ or ↓)
3. **Optional:** Causal drivers (if implemented)
4. **Optional:** Graph visualization

---

## 🎉 Success Criteria

Your test is successful if:

✅ You can query at least 3 different companies  
✅ All values are real numbers (no N/A)  
✅ Period comparisons show correct percentages  
✅ Growth companies show positive changes  
✅ Declining companies show negative changes  
✅ System responds within 2-3 seconds

---

## 💡 Pro Tips

1. **Use specific companies:** Company_269, Company_380, Company_244, Company_403, Company_359
2. **Use exact metric names:** revenue_from_operations (not just "revenue")
3. **Specify periods:** Q4 2025, Q2 2025, Q1 2025
4. **Test both growth and decline:** Company_403 (↑), Company_269 (↓)
5. **Check console:** Open browser DevTools (F12) to see API calls

---

## 🌟 Database Status

**Fixed on:** April 21, 2026  
**Fix Type:** Core database repair (not bypass)  
**Periods:** 4 → 44 (complete)  
**Filings Linked:** 15,010/15,010 (100%)  
**Companies:** 200 queryable  
**Metrics:** 6+ available  
**Status:** ✅ Fully Operational

---

**Your frontend is now connected to the fixed database!** Try the test queries above and you should see real data from all 200 companies! 🎉
