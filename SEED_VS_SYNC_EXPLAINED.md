# SEED DB vs SYNC NOW - Complete Explanation

## 🎯 Quick Comparison

| Feature | **Seed DB** ↻ | **Sync Now** 🔗 |
|---------|-----|---------|
| **What it does** | Resets database & loads default metrics | Imports time-series data from external DB |
| **Creates** | Metric definitions (18 metrics) | Time-series values (data points) |
| **Data source** | Hardcoded defaults in code | External Neon database |
| **Destructive?** | YES - drops & recreates all tables | NO - appends or updates data |
| **When to use** | First time setup, reset database | Import real data, sync updates |
| **Button shows** | ↻ Seed DB | 🔗 Sync Now |
| **Endpoint** | POST `/api/seed` | POST `/api/sync-from-neon` |
| **Time to complete** | <1 second | Depends on data size |

---

## 🌱 SEED DB (↻ Button)

### What It Does:
1. **Drops existing tables** (clears everything)
2. **Recreates 5 tables** from scratch:
   - `metrics` (metric definitions)
   - `metric_relationships` (causal drivers)
   - `time_series_data` (data points)
   - `causal_events` (audit trail)
   - `query_log` (query history)
3. **Inserts default data**:
   - 18 metric definitions (11 base + 7 derived)
   - 24 relationships (causal + formula dependencies)
   - 0 data points (empty - no actual values yet)
4. **Invalidates cache** to reload from fresh DB

### Result:
```
Before:              After Seed:
┌────────┐          ┌─────────────────┐
│ Empty  │          │ metrics (18)    │
│        │    →     │ relationships.. │
└────────┘          │ time_series (0) │
                    └─────────────────┘
```

### Frontend Display:
```
✓ Database Seeded Successfully
{
  "status": "success",
  "inserted": {
    "metrics": 18,
    "relationships": 24
  }
}
```

### When to Use:
- ✅ **First time setup** (initialize fresh database)
- ✅ **Reset system** (start over with clean slate)
- ✅ **Testing** (ensure known state)
- ❌ **Don't use** if you have existing data you want to keep!

### Code Behind It (routes.py):
```python
@router.post("/api/seed")
def seed_database(db: Session = Depends(get_db)):
    """Drop and reseed the database."""
    try:
        counts = seed_all(db)  # ← Calls seeder.py
        _invalidate_graph()    # ← Clear caches
        return {"status": "success", "inserted": counts}
```

---

## 🔗 SYNC NOW (🔗 Button)

### What It Does:
1. **Reads data from external Neon database** (using DATABASE_URL in .env)
2. **Optionally clears existing data** (if requested)
3. **Fetches time-series values** from `time_series_data` table
4. **Imports into local database**:
   - INSERT new rows
   - UPDATE existing rows (upsert logic)
5. **Tracks sync statistics**:
   - How many rows synced
   - How many inserted vs updated
   - Any errors encountered
6. **Invalidates cache** to reload with new data

### Result:
```
Before:                After Sync:
Local DB: Empty   →    Local DB: Populated with
                       44+ data points from
Neon DB: Has data      external database
```

### Frontend Display:
```
✓ Neon Sync Successful

Rows Synced:   44
Inserted:      44
Updated:       0
Errors:        0

All rows synced without errors!
```

### When to Use:
- ✅ **Import real data** (company metrics from external Neon)
- ✅ **Update existing data** (sync new values)
- ✅ **Bulk data load** (44+ rows at once)
- ✅ **Periodic sync** (keep local DB in sync with remote)
- ❌ **Don't use** if external database doesn't exist!

### Code Behind It (routes.py):
```python
@router.post("/api/sync-from-neon")
def sync_from_neon(req: NeonSyncRequest, db: Session = Depends(get_db)):
    """Import metric data from Neon PostgreSQL."""
    # Connect to Neon using DATABASE_URL
    neon_source = NeonDataSource(DATABASE_URL)
    
    # Fetch data from Neon
    rows_data = neon_source.fetch_metrics()  # ← Reads external DB
    
    # Insert/update into local DB
    for row in rows_data:
        insert_or_update(row)  # ← Upsert logic
    
    # Return sync stats
    return {
        "status": "success",
        "total_rows_synced": 44,
        "rows_inserted": 44,
        "rows_updated": 0,
        "error_count": 0
    }
```

---

## 📊 TYPICAL WORKFLOW

### Step 1: Initial Setup
```
User clicks: ↻ Seed DB
        ↓
Creates empty metric structure:
- 18 metrics defined
- 24 relationships defined
- 0 data points
        ↓
Ready for data import
```

### Step 2: Import Data
```
User clicks: 🔗 Sync Now
        ↓
Reads from Neon database (external):
- Fetches all time-series values
- Validates each row
- Inserts into local DB
        ↓
Now have: 18 metrics + 44 data points
Ready for analysis!
```

### Step 3: Ask Questions
```
User: "Why did orders grow Q1→Q4?"
        ↓
System processes with both:
- Metrics (from SEED)
- Data (from SYNC)
        ↓
Returns: "Orders ↑ 15% driven by
         Marketing ↑ 8.3%,
         Active Users ↑ 4.5%"
```

---

## 🔄 DATA FLOW DIAGRAM

```
┌─────────────────────────────────────────────────────────────┐
│                   FRONTEND (Browser)                        │
│  ↻ Seed DB           |           🔗 Sync Now               │
└──────────────┬────────────────────────────┬──────────────────┘
               │                            │
               v                            v
        ┌─────────────┐              ┌──────────────┐
        │ POST        │              │ POST         │
        │ /api/seed   │              │ /api/sync    │
        └──────┬──────┘              └──────┬───────┘
               │                            │
               v                            v
        ┌─────────────────────────────────────────┐
        │    BACKEND (Python/FastAPI)             │
        │                                         │
        │  SEED:              SYNC:               │
        │  ├─ Drop tables     ├─ Read DATABASE_URL
        │  ├─ Create new      ├─ Connect to Neon  
        │  ├─ Insert defaults ├─ Fetch data       
        │  └─ Clear caches    └─ Insert locally   
        └──────────────┬──────────────────────────┘
                       │
                       v
        ┌─────────────────────────────────────────┐
        │   LOCAL DATABASE                        │
        │                                         │
        │  AFTER SEED:        AFTER SYNC:        │
        │  ├─ metrics (18)     ├─ metrics (18)   │
        │  ├─ relationships    ├─ relationships  │
        │  └─ time_series (0)  └─ time_series(44)
        └─────────────────────────────────────────┘
```

---

## 🎯 REAL-WORLD EXAMPLE

### Scenario: You have a company's data in Neon, want to analyze it

**Step 1: Fresh Start**
```bash
Click: ↻ Seed DB
Result: Database prepared with metric structure
Database now has: 18 metrics defined, no data
```

**Step 2: Load Company Data**
```bash
Click: 🔗 Sync Now
Backend connects to YOUR Neon database (via .env)
Fetches: orders, revenue, aov, discounts, etc.
Inserts: 44 rows of Q1-Q4 2023 data
Result: Database ready for analysis!
```

**Step 3: Analyze**
```bash
Ask: "Why did orders grow Q1→Q4?"
System uses:
  - Metrics from SEED (structure)
  - Data from SYNC (values)
Result: Shows root causes with visualization
```

---

## ⚙️ TECHNICAL DETAILS

### SEED DB - Detailed Process
```python
# app/metrics/seeder.py
def seed_all(db):
    # 1. Drop all existing tables
    TimeSeriesData.__table__.drop(engine)
    Metric.__table__.drop(engine)
    MetricRelationship.__table__.drop(engine)
    etc...
    
    # 2. Create tables from scratch
    Base.metadata.create_all(engine)
    
    # 3. Insert default metrics (18 rows)
    # From HARDCODED DEFAULT_METRICS:
    db.add(Metric(name="orders", display_name="Orders", ...))
    db.add(Metric(name="revenue", display_name="Revenue", ...))
    # ... 18 total
    
    # 4. Insert default relationships (24 rows)
    # From HARDCODED DEFAULT_RELATIONSHIPS:
    db.add(MetricRelationship(
        metric_id=orders_id,
        driver_id=active_users_id,
        type="causal",
        strength=0.85
    ))
    # ... 24 total
    
    # 5. Return counts
    return {"metrics": 18, "relationships": 24}
```

### SYNC NOW - Detailed Process
```python
# app/data/postgres_source.py (Neon connector)
def fetch_metrics():
    # 1. Connect to Neon via DATABASE_URL
    connection = create_engine(DATABASE_URL)
    
    # 2. Query Neon's time_series_data table
    query = "SELECT metric_name, period, segment, value FROM time_series_data"
    rows = connection.execute(query)
    
    # 3. Return list of dictionaries
    return [{
        "metric_name": "orders",
        "period": "Q1 2023",
        "segment": "Overall",
        "value": 100000.0
    }, ...]

# app/api/routes.py (Sync endpoint)
def sync_from_neon(req):
    # 1. Optional: Clear existing data
    if req.clear_existing:
        db.query(TimeSeriesData).delete()
    
    # 2. Fetch from Neon
    rows = neon_source.fetch_metrics()
    
    # 3. Upsert into local DB (insert or update)
    for row in rows:
        existing = db.query(TimeSeriesData).filter(
            TimeSeriesData.metric_id == metric.id,
            TimeSeriesData.period == row["period"],
            TimeSeriesData.segment == row["segment"]
        ).first()
        
        if existing:
            existing.value = row["value"]  # Update
            updated += 1
        else:
            db.add(TimeSeriesData(...))  # Insert
            inserted += 1
    
    db.commit()
    
    # 4. Return stats
    return {
        "total_rows_synced": len(rows),
        "rows_inserted": inserted,
        "rows_updated": updated,
        "error_count": errors
    }
```

---

## 📱 Frontend Button Handlers

### Seed DB Button (app.js line 23)
```javascript
async function seedDatabase() {
  showLoading('Seeding database (drops + recreates tables)…');
  try {
    const result = await apiFetch('/api/seed', { method: 'POST' });
    showContent(`
      <div class="card">
        <div class="card-title">Database Seeded Successfully</div>
        <pre>${JSON.stringify(result, null, 2)}</pre>
        <p>You can now ask questions about your metrics.</p>
      </div>
    `);
  } catch (e) {
    showError(e.message);
  }
}

// Triggered by: <button onclick="seedDatabase()">↻ Seed DB</button>
```

### Sync Now Button (app.js line 41)
```javascript
async function syncFromNeon() {
  showLoading('Syncing data from Neon…');
  try {
    const result = await apiFetch('/api/sync-from-neon', {
      method: 'POST',
      body: JSON.stringify({
        clear_existing: false  // Don't delete, just append/update
      }),
    });
    showContent(`
      <div class="card">
        <div class="card-title" style="color:green;">✓ Neon Sync Successful</div>
        <div>
          <div>Rows Synced: <strong>${result.total_rows_synced || 0}</strong></div>
          <div>Inserted: <strong>${result.rows_inserted || 0}</strong></div>
          <div>Updated: <strong>${result.rows_updated || 0}</strong></div>
          <div>Errors: <strong>${result.error_count || 0}</strong></div>
        </div>
      </div>
    `);
  } catch (e) {
    showError(e.message);
  }
}

// Triggered by: <button onclick="syncFromNeon()">🔗 Sync Now</button>
```

---

## ❓ FAQ

### Q: Can I use Sync Now without Seed DB first?
**A:** No. Sync Now needs the metrics table to exist (created by Seed DB). Do Seed first, then Sync.

### Q: Does Sync Now delete existing data?
**A:** By default, No (clear_existing=false). New rows added, existing updated. Set clear_existing=true to delete first.

### Q: What database does Sync Now read from?
**A:** The external Neon database specified in DATABASE_URL (.env file). Must have a time_series_data table.

### Q: Can I use Seed DB repeatedly?
**A:** Yes, but it DELETES everything. Use with caution! Only when you want to start fresh.

### Q: What's the difference between Seed and importing CSV?
**A:** 
- Seed: Loads metric definitions + relationships (structure only, no data)
- CSV Import: Loads time-series values (data points)
- Sync Now: Same as CSV but from external database instead of file

### Q: How long does Sync take?
**A:** <1 second for 44 rows. Scales with data size. Can sync 10K+ rows in seconds.

### Q: Can I schedule automatic syncs?
**A:** Not yet, but the endpoint supports it! Could add a cron job:
```bash
curl -X POST http://localhost:8000/api/sync-from-neon \
  -H "Content-Type: application/json" \
  -d '{"clear_existing": false}'
```

---

## 🎓 Summary

| Aspect | Seed DB | Sync Now |
|--------|---------|----------|
| **Purpose** | Initialize structure | Load data |
| **Creates** | Metric definitions | Time-series values |
| **Destructive** | YES (drops tables) | NO (appends/updates) |
| **Source** | Hardcoded in code | External Neon DB |
| **Frequency** | Once per reset | As needed |
| **Data loss** | Yes | No (unless you choose clear) |
| **Dependencies** | None | Neon DB must exist |

---

**In 30 Seconds:**
- **Seed DB** = Set up the structure (metrics, relationships, empty tables)
- **Sync Now** = Fill it with data from an external database
- **Do both** = Get: metrics + relationships (Seed) + data (Sync)

✅ That's it! You now understand both buttons completely.
