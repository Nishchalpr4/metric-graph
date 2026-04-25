import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
db_url = os.getenv('DATABASE_URL')
conn = psycopg2.connect(db_url)
cur = conn.cursor()

print('=' * 90)
print('INVESTIGATING FILING DISCREPANCIES')
print('=' * 90)
print()

# Check Bajaj Auto filings
print('1. BAJAJ AUTO - Q2 2024 & Q2 2023 FILINGS')
print('-' * 90)

cur.execute('''
SELECT company_id FROM mappings_canonical_companies 
WHERE official_legal_name ILIKE '%Bajaj Auto%'
''')
bajaj_id = cur.fetchone()[0]

cur.execute('''
SELECT ff.filing_id, ff.reporting_end_date, ff.filing_type, ff.nature, ff.audited,
       fp.revenue_from_operations, fp.operating_profit
FROM financials_filing ff
LEFT JOIN financials_pnl fp ON ff.filing_id = fp.filing_id
WHERE ff.company_id = %s
AND EXTRACT(QUARTER FROM ff.reporting_end_date) = 2
AND EXTRACT(YEAR FROM ff.reporting_end_date) IN (2024, 2023)
ORDER BY ff.reporting_end_date DESC, ff.filing_type, ff.nature
''', (bajaj_id,))

bajaj_filings = cur.fetchall()
print(f'Found {len(bajaj_filings)} filing records:')
for fid, date, ftype, nature, audited, rev, op_profit in bajaj_filings:
    print(f'  Filing {fid}: {date} | Type: {ftype} | Nature: {nature} | Audited: {audited}')
    print(f'    Revenue: {rev}, Operating Profit: {op_profit}')
print()

# Check Bosch filings
print('2. BOSCH LTD - Q1 2024 & Q2 2023 FILINGS')
print('-' * 90)

cur.execute('''
SELECT company_id FROM mappings_canonical_companies 
WHERE official_legal_name ILIKE '%Bosch%'
LIMIT 1
''')
bosch_id = cur.fetchone()[0]

cur.execute('''
SELECT ff.filing_id, ff.reporting_end_date, ff.filing_type, ff.nature, ff.audited,
       fp.employee_benefit_expense
FROM financials_filing ff
LEFT JOIN financials_pnl fp ON ff.filing_id = fp.filing_id
WHERE ff.company_id = %s
AND (
  (EXTRACT(QUARTER FROM ff.reporting_end_date) = 1 AND EXTRACT(YEAR FROM ff.reporting_end_date) = 2024)
  OR
  (EXTRACT(QUARTER FROM ff.reporting_end_date) = 2 AND EXTRACT(YEAR FROM ff.reporting_end_date) = 2023)
)
ORDER BY ff.reporting_end_date DESC, ff.filing_type, ff.nature
''', (bosch_id,))

bosch_filings = cur.fetchall()
print(f'Found {len(bosch_filings)} filing records:')
for fid, date, ftype, nature, audited, emp_benefit in bosch_filings:
    print(f'  Filing {fid}: {date} | Type: {ftype} | Nature: {nature} | Audited: {audited}')
    print(f'    Employee Benefit: {emp_benefit}')
print()

# Check filing type distribution
print('3. FILING TYPE DISTRIBUTION (All Companies)')
print('-' * 90)
cur.execute('''
SELECT filing_type, nature, COUNT(*) as count
FROM financials_filing
GROUP BY filing_type, nature
ORDER BY count DESC
''')

for ftype, nature, count in cur.fetchall():
    print(f'  Type: {ftype:20} | Nature: {nature:20} | Count: {count}')
print()

# Recommendation
print('4. ANALYSIS & RECOMMENDATION')
print('-' * 90)
print('✓ Issue: Multiple filings per period with different values')
print('✓ Solution: System should prioritize:')
print('  1. Audited filings (audited = Yes) over unaudited')
print('  2. Consolidated filings over Standalone')
print('  3. Latest filing_id if all else equal')
print()
print('This ensures consistent, official financial data is used.')
print()

cur.close()
conn.close()
