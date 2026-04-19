# Database Structure Decision

## Summary

**Performance Impact:** ~5-10ms latency difference between proposed structure and current setup. Negligible for most use cases.

**Conclusion:** Keep current DB structure. The operational difference is minimal.

---

## Why Current Structure is Fine

| Aspect | Impact |
|---|---|
| Query latency | +5-10ms (adapter transformation + joins) — acceptable |
| System functionality | ✅ Works identically |
| User experience | ✅ No visible difference |
| Maintenance | ✅ No schema migration risk |

---

## Single Unified DB: Preferred (Not Critical)

Ideally, one Neon database consolidating:
- `metrics` + `metric_relationships` (from fuzzy_search_v1)
- `pnl` + `filing` + `company` (from llm_data_ana_test_v3)
- `time_series_data`, `causal_events`, `query_log` (system tables)

**But:** This requires data migration. Not worth the risk now.

**Timeline:** Migrate to unified DB in Q4 2026 (after system is battle-tested).

---

## Near-Term Fixes (Instead of DB Restructuring)

### 1. **Build Adapter Layer** (Recommended)
Create `backend/app/data/adapter.py` to:
- Read from DB-1: `pnl + filing + company` → transform to long format
- Read from DB-2: `canonical_metrics_combined_1.extras` → populate metrics
- Merge relationships from `extras` JSONB

**Benefit:** Code change, zero downtime, easy to test.

### 2. **Enhance `metrics.csv` Imports**
Add script to auto-load metrics from DB-2:
```python
# backend/app/data/sync_metrics_from_neon.py
def sync_metrics_from_source_db():
    """Pull canonical_metrics_combined_1 and populate local metrics table"""
    pass
```

**Benefit:** Keeps metric definitions in sync without manual CSV updates.

### 3. **Standardize Period Format**
Ensure `pnl` table uses `"Q3 2023"` format, not separate quarter/year columns.
```sql
SELECT 'Q' || quarter || ' ' || fiscal_year AS period FROM filing;
```

**Benefit:** System expects period strings; standardizing saves transformation logic.

### 4. **Add Segment Column to PnL**
If not already present:
```sql
ALTER TABLE pnl ADD COLUMN segment VARCHAR(100) DEFAULT 'Overall';
```

**Benefit:** Unpivoting from wide → long format requires segment.

---

## Implementation Priority

| Priority | Task | Effort | Impact |
|---|---|---|---|
| **1** | Build adapter.py | 1 day | Unblocks system integration |
| **2** | Standardize period format | 2 hours | Simplifies all queries |
| **3** | Add segment column | 1 hour | Enables segment analysis |
| **4** | Auto-sync metrics script | 4 hours | Keeps definitions fresh |

---

## What NOT to Do

❌ **Don't migrate DB structure now** — too risky, marginal benefit
❌ **Don't add `companies` table** — complexity not needed yet
❌ **Don't refactor metric_relationships to DB** — code version works fine
❌ **Don't consolidate DBs immediately** — wait until you're confident

---

## Next Steps

1. Implement adapter layer (reads from DB-1 + DB-2, transforms on the fly)
2. Test end-to-end with real data from your two Neon DBs
3. Run system for 2-3 months
4. **Then:** Decide if unified DB migration is worth the effort

**Timeline:** Adapter layer done by end of April 2026 → System live with zero risk.
