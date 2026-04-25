"""
Verify: Are metrics really from DB or just hardcoded defaults?
And are graph edges actually constructed from DB or hardcoded?
"""
import psycopg2
from dotenv import load_dotenv
import os
import json

load_dotenv()
db_url = os.getenv("DATABASE_URL")
conn = psycopg2.connect(db_url)
cur = conn.cursor()

print("=" * 100)
print("DATABASE AUDIT - Is the system truly DB-driven or using hardcoded defaults?")
print("=" * 100)

# 1. Check METRICS table
print("\n1. METRICS TABLE (17 metrics expected from registry.py defaults)")
cur.execute("SELECT COUNT(*), STRING_AGG(name, ', ') FROM metrics")
count, names = cur.fetchone()
print(f"   Records: {count}")
print(f"   Names: {names[:200]}...")
print(f"   Conclusion: {'✓ DB Populated' if count > 0 else '✗ EMPTY - Using hardcoded defaults'}")

# 2. Check METRIC_RELATIONSHIPS table
print("\n2. METRIC_RELATIONSHIPS TABLE (formula/causal edges)")
cur.execute("SELECT COUNT(*) FROM metric_relationships")
count = cur.fetchone()[0]
print(f"   Records: {count}")
if count > 0:
    cur.execute("SELECT source_metric, target_metric, relationship_type, direction FROM metric_relationships LIMIT 5")
    for row in cur.fetchall():
        print(f"   {row[0]} → {row[1]} ({row[2]}, {row[3]})")
print(f"   Conclusion: {'✓ DB Populated' if count > 0 else '✗ EMPTY - Will use hardcoded DEFAULT_RELATIONSHIPS'}")

# 3. Check MAPPINGS_CANONICAL_METRICS_COMBINED_1
print("\n3. MAPPINGS_CANONICAL_METRICS_COMBINED_1 (metric definitions)")
cur.execute("SELECT COUNT(*) FROM mappings_canonical_metrics_combined_1")
count = cur.fetchone()[0]
print(f"   Records: {count}")
if count > 0:
    cur.execute("SELECT canonical_name, table_name FROM mappings_canonical_metrics_combined_1 LIMIT 5")
    for row in cur.fetchall():
        print(f"   {row[0]} from {row[1]}")
print(f"   Conclusion: {'✓ DB Populated' if count > 0 else '✗ EMPTY'}")

# 4. Check MAPPINGS_CANONICAL_COMPANIES
print("\n4. MAPPINGS_CANONICAL_COMPANIES (company list)")
cur.execute("SELECT COUNT(*), STRING_AGG(official_legal_name, ', ') FROM mappings_canonical_companies LIMIT 10")
count, names = cur.fetchone()
print(f"   Total: {count}")
print(f"   Sample: {names}")
print(f"   Conclusion: {'✓ Real companies from SEC' if count > 0 else '✗ EMPTY'}")

# 5. Check FINANCIALS_PERIOD
print("\n5. FINANCIALS_PERIOD (available periods)")
cur.execute("SELECT COUNT(*), STRING_AGG(DISTINCT quarter || ' ' || fiscal_year, ', ' ORDER BY quarter || ' ' || fiscal_year) FROM financials_period")
count, periods = cur.fetchone()
print(f"   Total periods: {count}")
print(f"   Sample: {periods[:150] if periods else 'NONE'}...")
print(f"   Conclusion: {'✓ Real periods from filings' if count > 0 else '✗ EMPTY'}")

# 6. Check what metrics table says about formulas
print("\n6. FORMULA DEFINITIONS IN METRICS TABLE")
cur.execute("SELECT name, formula, formula_inputs FROM metrics WHERE formula IS NOT NULL LIMIT 5")
for row in cur.fetchall():
    print(f"   {row[0]}: {row[1]}")
    print(f"      inputs: {row[2]}")

print("\n" + "=" * 100)
print("VERDICT:")
print("=" * 100)

cur.execute("""
SELECT 
  (SELECT COUNT(*) FROM metrics) as m_count,
  (SELECT COUNT(*) FROM metric_relationships) as r_count,
  (SELECT COUNT(*) FROM mappings_canonical_metrics_combined_1) as cm_count,
  (SELECT COUNT(*) FROM mappings_canonical_companies) as co_count,
  (SELECT COUNT(*) FROM financials_period) as p_count
""")
m, r, cm, co, p = cur.fetchone()

print(f"Metrics table populated: {m > 0}")
print(f"Metric relationships table populated: {r > 0}")
print(f"Canonical metrics populated: {cm > 0}")
print(f"Companies with data: {co > 0}")
print(f"Periods available: {p > 0}")

if m > 0 and r > 0 and co > 0 and p > 0:
    print("\n✓ SYSTEM IS DATABASE-DRIVEN")
else:
    print("\n✗ SYSTEM IS USING HARDCODED DEFAULTS")

cur.close()
conn.close()
