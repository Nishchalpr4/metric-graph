# NEON DATABASE MIGRATION PLAN

## Overview
This plan fixes all 10 identified issues in phases, starting with critical issues first.

**Timeline:** 4-6 hours total  
**Database:** Neon PostgreSQL (ap-southeast-1.aws.neon.tech)  
**Downtime:** ~15 minutes (for schema changes)

---

## PHASE 1: Critical Fixes (30 mins) 🔴

### 1.1 Fix Time Series Data Schema (Most Critical)

**Problem:** Can't store multi-company data (unique constraint missing company_id)

**Steps:**

```sql
-- Step 1: Add company_id column
ALTER TABLE time_series_data 
ADD COLUMN company_id INTEGER;

-- Step 2: Drop old constraint
ALTER TABLE time_series_data 
DROP CONSTRAINT IF EXISTS uq_metric_period_segment;

-- Step 3: Create new constraint with company_id
ALTER TABLE time_series_data 
ADD CONSTRAINT uq_metric_period_segment_company 
UNIQUE (metric_name, period, segment, company_id);

-- Step 4: Add foreign key (optional but recommended)
ALTER TABLE time_series_data
ADD CONSTRAINT fk_time_series_company
FOREIGN KEY (company_id) REFERENCES canonical_companies(company_id);

-- Step 5: Create index for performance
CREATE INDEX idx_time_series_company_period 
ON time_series_data(company_id, period, metric_name);
```

**After this fix:**
- ✅ Can store different values for same metric in same period for different companies
- ✅ Can extract real multi-company data

---

### 1.2 Investigate Period Linking Issue

**Problem:** Some period_ids in financials_filing don't exist in financials_period

**Diagnostic Script:**

```sql
-- Find missing period_ids
SELECT DISTINCT ff.period_id
FROM financials_filing ff
LEFT JOIN financials_period fp ON ff.period_id = fp.period_id
WHERE fp.period_id IS NULL
ORDER BY ff.period_id;

-- Count how many filings are affected
SELECT COUNT(*) as affected_filings
FROM financials_filing ff
LEFT JOIN financials_period fp ON ff.period_id = fp.period_id
WHERE fp.period_id IS NULL;

-- See the data in those filings
SELECT ff.filing_id, ff.company_id, ff.period_id, COUNT(*) as pnl_count
FROM financials_filing ff
LEFT JOIN financials_period fp ON ff.period_id = fp.period_id
LEFT JOIN financials_pnl pnl ON ff.filing_id = pnl.filing_id
WHERE fp.period_id IS NULL
GROUP BY ff.filing_id, ff.company_id, ff.period_id;
```

**Options to Fix:**

**Option A: Add Missing Periods** (If periods are known)
```sql
-- If you know what quarters/years the missing periods are:
INSERT INTO financials_period (period_id, quarter, fiscal_year)
VALUES 
  (missing_id_1, 'Q1', 2023),
  (missing_id_2, 'Q2', 2023),
  -- ... etc
ON CONFLICT DO NOTHING;
```

**Option B: Remove Bad Filings** (If data is corrupted)
```sql
-- Delete filings with invalid period_ids
DELETE FROM financials_filing ff
WHERE NOT EXISTS (
  SELECT 1 FROM financials_period fp 
  WHERE fp.period_id = ff.period_id
);
```

**Option C: Keep as-is** (Use NULL periods in queries)
```sql
-- Just accept NULL periods, query works fine with them
SELECT ff.*, pnl.revenue_from_operations
FROM financials_filing ff
JOIN financials_pnl pnl ON ff.filing_id = pnl.filing_id
WHERE ff.company_id = 269
-- periods will be NULL but data is still queryable
```

---

## PHASE 2: High Priority Fixes (1-2 hours) 🟠

### 2.1 Map All Metrics to canonical_metrics

**Current State:** Only 5 metrics mapped, 10+ missing

**SQL to Add Missing Metrics:**

```sql
-- Check what metrics are already mapped
SELECT canonical_name, table_name FROM canonical_metrics;

-- Add missing P&L metrics
INSERT INTO canonical_metrics (canonical_name, table_name, semantic_definition)
VALUES
  ('other_income', 'pnl', 'Other income sources not from core operations'),
  ('total_income', 'pnl', 'Total operating and other income'),
  ('operating_profit', 'pnl', 'Profit from core business operations'),
  ('profit_before_tax', 'pnl', 'Profit before income tax expense'),
  ('pnl_for_period', 'pnl', 'Net profit for the period'),
  ('tax_expense', 'pnl', 'Income tax expense'),
  ('comprehensive_income_for_the_period', 'pnl', 'Total comprehensive income'),
  ('basic_eps', 'pnl', 'Basic earnings per share'),
  -- Balance Sheet metrics
  ('total_assets', 'balance_sheet', 'Total company assets'),
  ('total_liabilities', 'balance_sheet', 'Total company liabilities'),
  ('stockholders_equity', 'balance_sheet', 'Total shareholders equity'),
  ('current_assets', 'balance_sheet', 'Assets expected to be converted to cash in 1 year'),
  ('current_liabilities', 'balance_sheet', 'Liabilities due within 1 year'),
  -- Cash Flow metrics
  ('operating_cash_flow', 'cashflow', 'Cash generated from operations'),
  ('investing_cash_flow', 'cashflow', 'Cash from/used in investments'),
  ('financing_cash_flow', 'cashflow', 'Cash from/used in financing'),
  ('free_cash_flow', 'cashflow', 'Operating cash flow minus capital expenditures')
ON CONFLICT DO NOTHING;
```

**Update ORM Model (Python):**

In [backend/app/models/db_models.py](backend/app/models/db_models.py):

```python
# Add these constants for new metrics
CANONICAL_METRICS = {
    'revenue_from_operations': 'pnl',
    'cost_of_material': 'pnl',
    'depreciation': 'pnl',
    'employee_benefit_expense': 'pnl',
    'interest_expense': 'pnl',
    # NEW:
    'other_income': 'pnl',
    'total_income': 'pnl',
    'operating_profit': 'pnl',
    'profit_before_tax': 'pnl',
    'pnl_for_period': 'pnl',
    'tax_expense': 'pnl',
    'comprehensive_income_for_the_period': 'pnl',
    'basic_eps': 'pnl',
    'total_assets': 'balance_sheet',
    'total_liabilities': 'balance_sheet',
    'stockholders_equity': 'balance_sheet',
    'current_assets': 'balance_sheet',
    'current_liabilities': 'balance_sheet',
    'operating_cash_flow': 'cashflow',
    'investing_cash_flow': 'cashflow',
    'financing_cash_flow': 'cashflow',
    'free_cash_flow': 'cashflow',
}
```

---

### 2.2 Fix Column Type Issues

**Problem:** Some columns are JSONB instead of FLOAT

**SQL Fix:**

```sql
-- Check column types
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'financials_pnl'
AND data_type = 'jsonb';

-- Fix: Convert JSONB columns to FLOAT
ALTER TABLE financials_pnl
ALTER COLUMN "other" TYPE FLOAT8 USING ("other"::text::float8);

-- Check and fix other problematic columns
-- Run for each JSONB column in financials_pnl
```

---

### 2.3 Fix Company Names (Optional UI Fix)

**Problem:** Shows "Company_269" instead of real names

**Option 1: Bulk Update with Real Names** (If you have them)

```sql
-- If you have a mapping of company IDs to real names:
UPDATE canonical_companies
SET official_legal_name = 'Real Company Name'
WHERE company_id = 269;
```

**Option 2: Query with Better Names in Backend** (Temporary)

Update [backend/app/data/financial_accessor.py](backend/app/data/financial_accessor.py):

```python
def get_available_companies(self) -> List[str]:
    """Get list of all real companies from SEC filings."""
    companies = self.db.query(CanonicalCompany.official_legal_name).filter(
        CanonicalCompany.is_active == True
    ).order_by(CanonicalCompany.official_legal_name).all()
    
    # Format names for display (optional)
    names = []
    for c in companies:
        # Keep as-is if real name, or generate better name
        display_name = c[0] if not c[0].startswith('Company_') else f"Company {c[0].split('_')[1]}"
        names.append(display_name)
    
    return names
```

---

## PHASE 3: Data Migration (1-2 hours) 🟡

### 3.1 Extract Real Multi-Company Data to time_series_data

**After schema is fixed, extract real data:**

```python
# backend/extract_real_data_fixed.py
from app.database import SessionLocal
from app.models.db_models import (
    CanonicalCompany, FinancialsFiling, FinancialsPnL,
    FinancialsPeriod, CanonicalMetric, TimeSeriesData
)
from sqlalchemy import func

def extract_all_real_data():
    """Extract all real P&L data to time_series_data with company_id."""
    db = SessionLocal()
    
    # Get all metrics
    metrics = db.query(CanonicalMetric).filter(
        CanonicalMetric.table_name == 'pnl'
    ).all()
    
    metric_columns = {m.canonical_name: m for m in metrics}
    
    # Get all filings with companies
    filings = db.query(
        CanonicalCompany.company_id,
        CanonicalCompany.official_legal_name,
        FinancialsFiling.filing_id,
        FinancialsPeriod.quarter,
        FinancialsPeriod.fiscal_year,
        FinancialsPnL
    ).join(
        FinancialsFiling,
        CanonicalCompany.company_id == FinancialsFiling.company_id
    ).join(
        FinancialsPnL,
        FinancialsFiling.filing_id == FinancialsPnL.filing_id
    ).outerjoin(
        FinancialsPeriod,
        FinancialsFiling.period_id == FinancialsPeriod.period_id
    ).all()
    
    records_added = 0
    
    for company_id, company_name, filing_id, quarter, year, pnl in filings:
        # Format period string
        if quarter and year:
            period_str = f"{quarter} {year}"
        else:
            period_str = f"Period_{filings[0].period_id if hasattr(filings[0], 'period_id') else 'Unknown'}"
        
        # Extract each metric
        for metric_name, metric_obj in metric_columns.items():
            value = getattr(pnl, metric_name, None)
            
            if value is not None and value != 0:
                # Check if already exists
                existing = db.query(TimeSeriesData).filter(
                    TimeSeriesData.metric_name == metric_name,
                    TimeSeriesData.period == period_str,
                    TimeSeriesData.company_id == company_id,
                    TimeSeriesData.segment == 'Overall'
                ).first()
                
                if not existing:
                    ts_record = TimeSeriesData(
                        metric_name=metric_name,
                        period=period_str,
                        segment='Overall',
                        value=float(value),
                        is_computed=False,
                        company_id=company_id,  # NEW!
                        notes=company_name
                    )
                    db.add(ts_record)
                    records_added += 1
                    
                    if records_added % 100 == 0:
                        db.commit()
                        print(f"✓ {records_added} records added...")
    
    db.commit()
    print(f"✅ Total records extracted: {records_added}")

if __name__ == "__main__":
    extract_all_real_data()
```

**Run it:**
```bash
cd backend
py extract_real_data_fixed.py
```

---

### 3.2 Clean Up Old Test Data

```sql
-- Delete old Period_XXX format test data
DELETE FROM time_series_data
WHERE period LIKE 'Period_%';

-- Keep only Q1, Q2, Q3, Q4 format and any company-specific data
SELECT COUNT(*) FROM time_series_data
WHERE period NOT LIKE 'Q% %';
```

---

## PHASE 4: Validation & Testing (30 mins) ✅

### 4.1 Validation Queries

Run these to verify everything works:

```sql
-- 1. Check time_series_data has company_id
SELECT COUNT(*) as total, 
       COUNT(company_id) as with_company_id,
       COUNT(DISTINCT company_id) as unique_companies
FROM time_series_data;

-- 2. Check all metrics are mapped
SELECT COUNT(*) as metric_count FROM canonical_metrics;

-- 3. Verify multi-company data in same period
SELECT period, metric_name, COUNT(DISTINCT company_id) as company_count
FROM time_series_data
WHERE period LIKE 'Q% %'
GROUP BY period, metric_name
LIMIT 10;

-- 4. Check for NULL periods in filings
SELECT COUNT(*) as filings_without_period
FROM financials_filing ff
LEFT JOIN financials_period fp ON ff.period_id = fp.period_id
WHERE fp.period_id IS NULL;
```

### 4.2 Test Queries via Python

```python
from app.database import SessionLocal
from app.data.financial_accessor import FinancialDataAccessor

db = SessionLocal()
accessor = FinancialDataAccessor(db)

# Test 1: Get available companies
companies = accessor.get_available_companies()
print(f"✓ Found {len(companies)} companies")

# Test 2: Query real data for multiple companies, same period
print("\nTesting multi-company query for same period:")
for company_name in companies[:3]:
    value = accessor.get_metric_value(
        'revenue_from_operations',
        company_name,
        'Q1 2024'  # Same period
    )
    if value:
        print(f"  {company_name}: {value}")

# Test 3: Time series data
print("\nTesting time series query:")
series = accessor.get_time_series(
    'revenue_from_operations',
    companies[0]
)
print(f"  {companies[0]}: {len(series)} data points")
if series:
    print(f"    Periods: {[s['period'] for s in series[:5]]}")
```

### 4.3 Test API Queries

```bash
# Start server
cd backend
py wsgi.py

# In another terminal, test queries
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Company_269 revenue from operations"}'

curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Company_255 cost of material"}'
```

---

## PHASE 5: Code Updates (Optional, 30 mins) 💻

### 5.1 Update financial_accessor.py

The accessor already queries SEC tables directly, but enhance it for balance sheet/cashflow:

```python
def _fetch_metric_value(
    self,
    metric_canonical_name: str,
    table_name: str,
    filing_id: int,
) -> Optional[float]:
    """Fetch metric from appropriate financial table."""
    column_name = metric_canonical_name
    
    if table_name == "pnl":  # Changed from "financials_pnl"
        row = self.db.query(FinancialsPnL).filter(
            FinancialsPnL.filing_id == filing_id
        ).first()
        if not row:
            return None
        return getattr(row, column_name, None)
    
    elif table_name == "balance_sheet":  # NEW
        row = self.db.query(FinancialsBalanceSheet).filter(
            FinancialsBalanceSheet.filing_id == filing_id
        ).first()
        if not row:
            return None
        return getattr(row, column_name, None)
    
    elif table_name == "cashflow":  # NEW
        row = self.db.query(FinancialsCashFlow).filter(
            FinancialsCashFlow.filing_id == filing_id
        ).first()
        if not row:
            return None
        return getattr(row, column_name, None)
    
    else:
        raise ValueError(f"Unknown table for metric {metric_canonical_name}: {table_name}")
```

---

## COMPLETE MIGRATION CHECKLIST

- [ ] **Phase 1: Critical Fixes**
  - [ ] Run time_series_data schema migration (add company_id column & new constraint)
  - [ ] Diagnose period linking issue (run diagnostic SQL)
  - [ ] Decide on period issue fix (add missing periods, remove bad filings, or keep as-is)

- [ ] **Phase 2: High Priority**
  - [ ] Insert missing metrics into canonical_metrics table (SQL INSERT)
  - [ ] Fix JSONB column types in financials_pnl (ALTER TABLE)
  - [ ] Update company name display (optional UI fix)

- [ ] **Phase 3: Data Migration**
  - [ ] Run extract_real_data_fixed.py to populate time_series_data with real multi-company data
  - [ ] Delete old Period_XXX format test data
  - [ ] Verify data extraction with sample queries

- [ ] **Phase 4: Validation**
  - [ ] Run validation SQL queries to confirm schema changes
  - [ ] Test accessor via Python script
  - [ ] Test API endpoints with curl/Postman

- [ ] **Phase 5: Code Updates (Optional)**
  - [ ] Update financial_accessor.py to handle balance_sheet and cashflow tables
  - [ ] Update ORM models with table_name references

- [ ] **Final: Documentation**
  - [ ] Update API documentation with new metrics
  - [ ] Update user guide with available companies/metrics
  - [ ] Mark issues as RESOLVED in NEON_DB_ISSUES.md

---

## Estimated Time & Risk

| Phase | Time | Risk | Impact |
|-------|------|------|--------|
| 1 | 30 min | LOW | High (fixes critical blocker) |
| 2 | 1-2 hrs | LOW | Medium (expands functionality) |
| 3 | 1-2 hrs | MEDIUM | High (enables real queries) |
| 4 | 30 min | LOW | Confirms everything works |
| 5 | 30 min | LOW | Polish & optimization |
| **TOTAL** | **4-6 hrs** | **MEDIUM** | **Complete Fix** |

---

## Rollback Plan

If anything breaks:

```sql
-- Restore old schema (if Phase 1 goes wrong)
ALTER TABLE time_series_data DROP COLUMN company_id CASCADE;
ALTER TABLE time_series_data ADD CONSTRAINT uq_metric_period_segment 
  UNIQUE (metric_name, period, segment);

-- Drop added metrics (if Phase 2 goes wrong)
DELETE FROM canonical_metrics 
WHERE canonical_name IN ('other_income', 'total_income', ...);

-- Clear extracted data (if Phase 3 goes wrong)
DELETE FROM time_series_data WHERE company_id IS NOT NULL;
```

---

**Ready to start? Run Phase 1 first - it's the quickest win!**
