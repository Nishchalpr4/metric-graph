# Data Import Guide: Making System 100% Database-Driven

## ⚡ How It Works

The system is **fully database-driven** with **NO hardcoded defaults**:
- Company names are dynamically loaded from Neon
- All metrics come from the database
- Parser automatically detects any company in your Neon data
- No manual configuration needed

## 📥 Importing Your Data

### Option 1: Import from CSV File

**Step 1: Prepare CSV with your data**

Format:
```csv
metric_name,period,segment,value
orders,Q1 2023,Swiggy,85000
aov,Q1 2023,Swiggy,295.5
gmv,Q1 2023,Swiggy,25000000
revenue,Q1 2023,Swiggy,1500000
orders,Q1 2023,Zomato,75000
aov,Q1 2023,Zomato,285.0
gmv,Q1 2023,Zomato,21500000
revenue,Q1 2023,Zomato,1350000
```

**Columns required:**
- `metric_name`: One of the 18 available metrics (orders, revenue, gmv, active_users, aov, take_rate, cac, arpu, etc.)
- `period`: Format as "Q1 2023", "Q2 2023", etc.
- `segment`: Company/segment name (ANY text - "Swiggy", "Zomato", "FatsoFood", etc.)
- `value`: Numeric value

**Step 2: Upload via API**

```bash
# Using curl
curl -X POST "http://127.0.0.1:8000/api/import-csv" \
  -F "file=@your_data.csv"

# Using PowerShell
$file = Get-Item "your_data.csv"
$url = "http://127.0.0.1:8000/api/import-csv"
$form = @{file = $file}
Invoke-RestMethod -Uri $url -Method Post -Form $form
```

**Response:**
```json
{
  "status": "success",
  "rows_inserted": 10800,
  "errors": 0,
  "error_count": 0
}
```

### Option 2: Sync Directly from Neon

If your data already exists in Neon:

```bash
curl -X POST "http://127.0.0.1:8000/api/sync-from-neon" \
  -H "Content-Type: application/json" \
  -d '{"clear_existing": false}'
```

## 🔍 Verify Your Data

**Check all companies imported:**
```bash
curl "http://127.0.0.1:8000/api/segments"
```

Returns:
```json
{
  "segments": ["Swiggy", "Zomato", "FatsoFood", "TroyFood", ...]
}
```

**Check all metrics available:**
```bash
curl "http://127.0.0.1:8000/api/metrics"
```

**Check data for specific company:**
```bash
curl "http://127.0.0.1:8000/api/metric/revenue?segment=Swiggy"
```

## 🎯 Query Your Companies

Once data is imported, query ANY company name automatically:

```json
POST /api/query
{
  "query": "Why did revenue increase for Swiggy in Q3 2023?"
}
```

The parser will:
1. ✅ Detect "Swiggy" from your actual Neon segments
2. ✅ Extract metric "revenue" and period "Q3 2023"
3. ✅ Run causal analysis for that specific company
4. ✅ Return detailed drivers and decomposition

## 📊 What Metrics Are Available?

All 18 metrics are database-driven:

**Base Metrics** (raw inputs, no formula):
- orders
- active_users
- new_users
- restaurant_partners
- marketing_spend
- pricing_index

**Computed Metrics** (derived from formulas):
- revenue
- gmv
- aov
- order_frequency
- basket_size
- delivery_charges
- discounts
- commission_rate
- cac
- take_rate
- arpu
- ebitda

## ⚠️ Error Handling

If user queries a company NOT in Neon:

```json
{
  "detail": "Company not found in query. Available companies in Neon: Swiggy, Zomato, FatsoFood, ... and 47 more\nTotal companies: 50"
}
```

**Status: 400 Bad Request** (not 500)

## 🔄 Workflow Example

```bash
# 1. Prepare CSV with 100 companies' data
# (5 metrics × 4 quarters = 20 rows per company)
# Total: 100 companies × 20 rows = 2000 rows

# 2. Import
curl -X POST "http://127.0.0.1:8000/api/import-csv" -F "file=@data_100_companies.csv"

# 3. Verify
curl "http://127.0.0.1:8000/api/segments" | jq '.segments | length'
# Output: 100

# 4. Query any company
curl -X POST "http://127.0.0.1:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "Why did revenue increase for CompanyXYZ in Q4 2023?"}'

# 5. Get results with full causal decomposition
```

## 🛠️ No Hardcoding - Everything from DB

**Parser is 100% dynamic:**
- ✅ No hardcoded segment names
- ✅ No hardcoded company aliases
- ✅ Reads actual segment list from time_series_data table on every query
- ✅ Fuzzy matching on actual DB segments
- ✅ Clear error messages showing available companies

**System architecture:**
```
User Query → Parser (loads segments from DB) → Match company in DB → Analysis
```

## 📝 CSV Import Tips

1. **Data validation**: Ensure all metric_name values match available metrics
2. **Period format**: Use "Q1 2023", "Q2 2023", etc. (not "2023-Q1" or "q1")
3. **Unique entries**: Each (metric_name, period, segment) combo should be unique
4. **Numeric values**: All values must be valid numbers (integers or decimals)
5. **Scale**: Values should match your business scale (e.g., don't use billions if data is in thousands)

## 🚀 Start Fresh

To clear and reimport:

```bash
# Via database directly (SQL)
DELETE FROM time_series_data;

# Then import new CSV
curl -X POST "http://127.0.0.1:8000/api/import-csv" -F "file=@new_data.csv"
```

---

**That's it!** 🎉 Your system now reads everything from Neon with zero hardcoding.
