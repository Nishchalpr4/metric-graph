# Data Import Guide

## Overview
The system now reads all metric data from the database instead of hardcoded values.

**Two options:**
1. **Neon PostgreSQL** (Recommended) — Direct sync from cloud Postgres
2. **CSV Upload** — Upload metrics from file

## Option 1: Sync from Neon PostgreSQL (Recommended)

### Prerequisites
- Neon database with table: `time_series_data`
- Connection string from Neon dashboard

### Table Schema (Neon)
```sql
CREATE TABLE time_series_data (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    period VARCHAR(20) NOT NULL,
    segment VARCHAR(100) NOT NULL,
    value NUMERIC NOT NULL,
    is_computed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Steps

**1. Initialize local database**
```bash
curl -X POST http://localhost:8000/api/seed
```

**2. Sync from Neon**
```bash
curl -X POST http://localhost:8000/api/sync-from-neon \
  -H "Content-Type: application/json" \
  -d '{
    "neon_connection_string": "postgresql://user:password@ep-xyz.us-east-1.neon.tech/dbname",
    "clear_existing": false
  }'
```

**Response:**
```json
{
  "status": "success",
  "rows_inserted": 150,
  "rows_updated": 0,
  "total_rows_synced": 150,
  "errors": [],
  "error_count": 0
}
```

### Get Neon Connection String
1. Go to [Neon Dashboard](https://console.neon.tech)
2. Select your project → database
3. Click "Connection string"
4. Choose "Pooled connection" or "Direct"
5. Copy the URL: `postgresql://user:password@ep-xyz.neon.tech/dbname`

---

## Option 2: CSV Upload

### CSV Format
```
metric_name,period,segment,value
orders,Q1 2022,Food Delivery,85.0
aov,Q1 2022,Food Delivery,295.0
commission_rate,Q1 2022,Food Delivery,17.5
```

**Columns:**
- `metric_name` — metric name
- `period` — quarter (e.g., "Q1 2022")
- `segment` — segment name
- `value` — numeric value

### Steps

**1. Initialize local database**
```bash
curl -X POST http://localhost:8000/api/seed
```

**2. Upload CSV**
```bash
curl -X POST -F "file=@metrics.csv" http://localhost:8000/api/import-csv
```

Or clear before importing:
```bash
curl -X POST -F "file=@metrics.csv" -F "clear=true" http://localhost:8000/api/import-csv
```

**Response:**
```json
{
  "status": "success",
  "rows_inserted": 50,
  "errors": [],
  "error_count": 0
}
```

---

## Query the Data

Both methods populate the same database, so all queries work identically:

```bash
# List metrics
curl "http://localhost:8000/api/metrics"

# Get metric time-series
curl "http://localhost:8000/api/metric/orders"

# Run analysis
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "Why did revenue increase?"}'
```

---

## Comparison

| Feature | Neon | CSV |
|---------|------|-----|
| **Setup** | Connection string | CSV file |
| **Real-time** | ✅ Sync on-demand | ❌ Manual upload |
| **Large data** | ✅ Efficient | ❌ File size limits |
| **Incremental** | ✅ Update existing | ⚠️ Row-level errors |
| **Automation** | ✅ Easy scripting | ❌ Manual |

---

## Troubleshooting

### Neon: "Failed to connect"
- Check connection string format
- Verify database exists and is accessible
- Test with: `psql "postgresql://..."`

### Neon: "No data found"
- Ensure table `time_series_data` exists
- Check columns: `metric_name, period, segment, value`
- Verify data is in the table

### CSV: Parsing errors
- Check for missing columns in header
- Ensure `value` is numeric
- Verify no extra spaces in CSV

