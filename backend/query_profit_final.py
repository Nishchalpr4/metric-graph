import psycopg2
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()
db_url = os.getenv('DATABASE_URL')
conn = psycopg2.connect(db_url)
cur = conn.cursor()

print('=== QUERYING OPERATING PROFIT FOR CASTROL INDIA LTD ===')
print()

# First, find Castrol India Ltd company_id
cur.execute('''
SELECT company_id, official_legal_name
FROM mappings_canonical_companies
WHERE official_legal_name ILIKE '%Castrol%'
''')

companies = cur.fetchall()
print(f'Found {len(companies)} company(ies) matching Castrol:')
for cid, cname in companies:
    print(f'  ID: {cid}, Name: {cname}')
print()

if not companies:
    print('ERROR: Castrol India Ltd not found!')
    cur.close()
    conn.close()
    exit(1)

castrol_id = companies[0][0]

# Query filings for Q2 2024 and Q2 2021
print('=== FETCHING Q2 2024 AND Q2 2021 FILINGS ===')
print()

cur.execute('''
SELECT filing_id, reporting_end_date, period_id, company_id
FROM financials_filing
WHERE company_id = %s
AND (
    (EXTRACT(QUARTER FROM reporting_end_date) = 2 AND EXTRACT(YEAR FROM reporting_end_date) = 2024)
    OR
    (EXTRACT(QUARTER FROM reporting_end_date) = 2 AND EXTRACT(YEAR FROM reporting_end_date) = 2021)
)
ORDER BY reporting_end_date DESC
''', (castrol_id,))

filings = cur.fetchall()
print(f'Found {len(filings)} filings:')
for fid, fdate, period_id, cid in filings:
    print(f'  Filing ID: {fid}, Date: {fdate}, Period ID: {period_id}')
print()

# Now fetch operating profit for each filing
print('=== OPERATING PROFIT VALUES ===')
print()

q2_2024_op = None
q2_2021_op = None

for filing_id, reporting_end_date, period_id, cid in filings:
    cur.execute('''
    SELECT operating_profit
    FROM financials_pnl
    WHERE filing_id = %s
    ''', (filing_id,))
    
    result = cur.fetchone()
    op_profit = result[0] if result else None
    
    year = reporting_end_date.year
    print(f'Filing ID {filing_id} ({reporting_end_date}, Q2 {year}):')
    print(f'  Operating Profit: {op_profit}')
    
    if year == 2024:
        q2_2024_op = op_profit
    elif year == 2021:
        q2_2021_op = op_profit
    print()

print('=== CALCULATIONS ===')
print()

if q2_2024_op is not None and q2_2021_op is not None:
    difference = q2_2024_op - q2_2021_op
    pct_change = (difference / q2_2021_op * 100) if q2_2021_op != 0 else 0
    
    print(f'Q2 2024 Operating Profit: {q2_2024_op}')
    print(f'Q2 2021 Operating Profit: {q2_2021_op}')
    print(f'Difference: {difference}')
    print(f'Percentage Change: {pct_change:.1f}%')
    print()
    print('=== VERIFICATION AGAINST EXPECTED VALUES ===')
    print()
    print(f'Expected Q2 2024: 322.44')
    print(f'Actual Q2 2024:   {q2_2024_op}')
    print(f'Match: {abs(float(q2_2024_op) - 322.44) < 0.01}')
    print()
    print(f'Expected Q2 2021: 197.5')
    print(f'Actual Q2 2021:   {q2_2021_op}')
    print(f'Match: {abs(float(q2_2021_op) - 197.5) < 0.01}')
    print()
    print(f'Expected Change: +124.94')
    print(f'Actual Change:   {difference}')
    print(f'Match: {abs(float(difference) - 124.94) < 0.01}')
    print()
    print(f'Expected % Change: +63.3%')
    print(f'Actual % Change:   {pct_change:.1f}%')
    print(f'Match: {abs(pct_change - 63.3) < 0.1}')
else:
    print('ERROR: Could not find both Q2 2024 and Q2 2021 data!')
    if q2_2024_op is None:
        print('  Missing Q2 2024 data')
    if q2_2021_op is None:
        print('  Missing Q2 2021 data')

cur.close()
conn.close()
