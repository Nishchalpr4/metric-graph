"""
Full end-to-end diagnostic for the metric analysis system.
Tests the full pipeline and reveals exactly where it breaks.
"""
import psycopg2
import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()
db_url = os.getenv("DATABASE_URL")
API = "http://127.0.0.1:8000"

conn = psycopg2.connect(db_url)
cur = conn.cursor()

print("=" * 80)
print("STEP 1: Check metrics table (used by METRIC_REGISTRY)")
print("=" * 80)
cur.execute("SELECT COUNT(*) FROM metrics")
count = cur.fetchone()[0]
print(f"  metrics table rows: {count}")
if count > 0:
    cur.execute("SELECT name, formula, is_base FROM metrics LIMIT 10")
    for row in cur.fetchall():
        print(f"  {row[0]:<35} formula={str(row[1]):<35} base={row[2]}")

print()
print("=" * 80)
print("STEP 2: Check mappings_canonical_metrics_combined_1 (used by parser)")
print("=" * 80)
cur.execute("SELECT COUNT(*) FROM mappings_canonical_metrics_combined_1")
count = cur.fetchone()[0]
print(f"  canonical metrics rows: {count}")
cur.execute("SELECT canonical_name, table_name FROM mappings_canonical_metrics_combined_1 LIMIT 15")
for row in cur.fetchall():
    print(f"  {row[0]:<35} table={row[1]}")

print()
print("=" * 80)
print("STEP 3: Check mappings_metric_aliases_combined_1 (used by parser)")
print("=" * 80)
cur.execute("SELECT COUNT(*) FROM mappings_metric_aliases_combined_1")
count = cur.fetchone()[0]
print(f"  metric aliases rows: {count}")
if count > 0:
    cur.execute("SELECT alias_name, metric_id FROM mappings_metric_aliases_combined_1 LIMIT 10")
    for row in cur.fetchall():
        print(f"  alias='{row[0]}' -> metric_id={row[1]}")

print()
print("=" * 80)
print("STEP 4: Check mappings_company_aliases (used by parser)")
print("=" * 80)
cur.execute("SELECT COUNT(*) FROM mappings_company_aliases")
count = cur.fetchone()[0]
print(f"  company aliases rows: {count}")
if count > 0:
    cur.execute("SELECT surface_form, company_id FROM mappings_company_aliases LIMIT 10")
    for row in cur.fetchall():
        print(f"  alias='{row[0]}' -> company_id={row[1]}")

print()
print("=" * 80)
print("STEP 5: Sample period data for Castrol India Ltd")
print("=" * 80)
cur.execute("""
    SELECT fp.quarter, fp.fiscal_year, fpnl.operating_profit, fpnl.revenue_from_operations
    FROM mappings_canonical_companies mcc
    JOIN financials_filing ff ON mcc.company_id = ff.company_id
    JOIN financials_period fp ON ff.period_id = fp.period_id
    JOIN financials_pnl fpnl ON ff.filing_id = fpnl.filing_id
    WHERE mcc.official_legal_name = 'Castrol India Ltd'
    ORDER BY fp.fiscal_year, fp.quarter
    LIMIT 10
""")
rows = cur.fetchall()
print(f"  found {len(rows)} rows for Castrol India Ltd")
for row in rows:
    print(f"  {row[0]} {row[1]} | operating_profit={row[2]} | revenue={row[3]}")

print()
print("=" * 80)
print("STEP 6: Live API test - /api/health")
print("=" * 80)
try:
    r = requests.get(f"{API}/api/health", timeout=5)
    print(f"  Status: {r.status_code} | Response: {r.json()}")
except Exception as e:
    print(f"  ERROR: {e}")

print()
print("=" * 80)
print("STEP 7: Live API test - /api/companies")
print("=" * 80)
try:
    r = requests.get(f"{API}/api/companies", timeout=5)
    data = r.json()
    print(f"  Status: {r.status_code} | Total companies: {data.get('total', 0)}")
    for c in (data.get('companies') or [])[:5]:
        print(f"  {c['id']}: {c['name']}")
except Exception as e:
    print(f"  ERROR: {e}")

print()
print("=" * 80)
print("STEP 8: Live API test - Full NL query for Castrol India Ltd")
print("=" * 80)
try:
    payload = {"query": "Why did operating profit change for Castrol India Ltd in Q2 2024 compared to Q2 2021?"}
    r = requests.post(f"{API}/api/query", json=payload, timeout=15)
    print(f"  Status: {r.status_code}")
    data = r.json()
    if r.status_code == 200:
        print(f"  Parsed: {json.dumps(data.get('parsed', {}), indent=2)}")
        result = data.get('result', {})
        print(f"  Result type: {result.get('type')}")
        if result.get('type') == 'error':
            print(f"  ERROR: {result.get('error') or result.get('message')}")
        elif 'change' in result:
            print(f"  Change: {json.dumps(result['change'], indent=2)}")
        if data.get('warnings'):
            print(f"  Warnings: {data['warnings']}")
    else:
        print(f"  Error: {data}")
except Exception as e:
    print(f"  ERROR: {e}")

cur.close()
conn.close()
