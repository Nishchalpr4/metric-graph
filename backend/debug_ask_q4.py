"""Diagnostic: trace exactly why financial_accessor fails for ASK Automotive Q4 2025."""
import os
from dotenv import load_dotenv
load_dotenv()
import psycopg2

db_url = os.getenv('DATABASE_URL')
conn = psycopg2.connect(db_url)
cur = conn.cursor()

# 1. Find company_id for ASK Automotive Ltd
cur.execute("""
SELECT company_id, official_legal_name, is_active
FROM mappings_canonical_companies
WHERE official_legal_name = 'ASK Automotive Ltd'
""")
rows = cur.fetchall()
print(f"1. Company lookup (exact name):")
for r in rows:
    print(f"   company_id={r[0]}, name={r[1]}, is_active={r[2]}")
if not rows:
    print("   !! NOT FOUND with exact name — checking ilike match...")
    cur.execute("SELECT company_id, official_legal_name, is_active FROM mappings_canonical_companies WHERE official_legal_name ILIKE '%ASK%'")
    for r in cur.fetchall():
        print(f"   {r}")

cid = rows[0][0] if rows else None
print()

# 2. What periods exist via FK path?
print("2. Periods via period_id FK (as financial_accessor uses):")
cur.execute("""
SELECT DISTINCT fp.quarter, fp.fiscal_year, ff.filing_id, ff.audited, ff.nature, ff.period_id
FROM financials_filing ff
JOIN financials_period fp ON ff.period_id = fp.period_id
WHERE ff.company_id = %s
ORDER BY fp.fiscal_year DESC, fp.quarter DESC
LIMIT 20
""", (cid,))
fk_rows = cur.fetchall()
for r in fk_rows:
    print(f"   {r[0]} {r[1]} | filing={r[2]} | {r[3]} | {r[4]} | period_id={r[5]}")
print(f"   Total via FK: {len(fk_rows)}")
print()

# 3. Which of the FK-path filings have PnL rows?
print("3. FK-path Q4 2025 filings with PnL rows:")
cur.execute("""
SELECT ff.filing_id, fp.quarter, fp.fiscal_year, fpnl.operating_profit, fpnl.revenue_from_operations
FROM financials_filing ff
JOIN financials_period fp ON ff.period_id = fp.period_id
JOIN financials_pnl fpnl ON ff.filing_id = fpnl.filing_id
WHERE ff.company_id = %s AND fp.quarter = 'Q4' AND fp.fiscal_year = '2025'
""", (cid,))
pnl_rows = cur.fetchall()
print(f"   Results ({len(pnl_rows)}):")
for r in pnl_rows:
    print(f"   filing={r[0]}, {r[1]} {r[2]}, op_profit={r[3]}, revenue={r[4]}")
print()

# 4. Periods via reporting_end_date = calendar_end path
print("4. Periods via reporting_end_date = calendar_end (fallback path):")
cur.execute("""
SELECT DISTINCT fp.quarter, fp.fiscal_year, ff.filing_id, ff.reporting_end_date, fp.calendar_end
FROM financials_filing ff
JOIN financials_period fp ON fp.calendar_end = ff.reporting_end_date
JOIN financials_pnl fpnl ON ff.filing_id = fpnl.filing_id
WHERE ff.company_id = %s
ORDER BY fp.fiscal_year DESC, fp.quarter DESC
LIMIT 20
""", (cid,))
rd_rows = cur.fetchall()
for r in rd_rows:
    print(f"   {r[0]} {r[1]} | filing={r[2]} | reporting={r[3]} | calendar_end={r[4]}")
print(f"   Total via date match: {len(rd_rows)}")
print()

# 5. All raw filings for this company
print("5. ALL filings for ASK Automotive (with and without period link):")
cur.execute("""
SELECT ff.filing_id, ff.period_id, ff.reporting_end_date, ff.audited, ff.nature,
       (SELECT COUNT(*) FROM financials_pnl WHERE filing_id=ff.filing_id) AS pnl_count
FROM financials_filing ff
WHERE ff.company_id = %s
ORDER BY ff.reporting_end_date DESC
LIMIT 30
""", (cid,))
all_filings = cur.fetchall()
for r in all_filings:
    print(f"   filing={r[0]}, period_id={r[1]}, date={r[2]}, {r[3]}, {r[4]}, pnl_rows={r[5]}")
print(f"   Total: {len(all_filings)}")
print()

# 6. Q4 FY2025 in financials_period
print("6. financials_period rows for Q4 2025:")
cur.execute("""
SELECT period_id, quarter, fiscal_year, calendar_start, calendar_end
FROM financials_period
WHERE quarter = 'Q4' AND fiscal_year = '2025'
""")
for r in cur.fetchall():
    print(f"   period_id={r[0]}, {r[1]} {r[2]}, {r[3]} to {r[4]}")

cur.close()
conn.close()
