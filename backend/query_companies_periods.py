import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
db_url = os.getenv('DATABASE_URL')
conn = psycopg2.connect(db_url)
cur = conn.cursor()

print('=' * 80)
print('DATABASE QUERY: COMPANIES AND PERIODS')
print('=' * 80)
print()

# 1. Count total companies
print('1. TOTAL COMPANY COUNT')
print('-' * 80)
cur.execute('SELECT COUNT(*) FROM mappings_canonical_companies')
total_companies = cur.fetchone()[0]
print(f'Total companies in database: {total_companies}')
print()

# 2. List first 30 companies alphabetically
print('2. FIRST 30 COMPANIES (ALPHABETICALLY)')
print('-' * 80)
cur.execute('''
SELECT company_id, official_legal_name
FROM mappings_canonical_companies
ORDER BY official_legal_name ASC
LIMIT 30
''')

companies = cur.fetchall()
for idx, (cid, cname) in enumerate(companies, 1):
    print(f'  {idx:2d}. [{cid:4d}] {cname}')
print()

# 3. Count total periods
print('3. TOTAL PERIOD COUNT')
print('-' * 80)
cur.execute('SELECT COUNT(*) FROM financials_period')
total_periods = cur.fetchone()[0]
print(f'Total periods in database: {total_periods}')
print()

# 4. List sample periods
print('4. SAMPLE PERIODS FROM DATABASE')
print('-' * 80)
cur.execute('''
SELECT period_id, period_name, period_type, start_date, end_date
FROM financials_period
ORDER BY end_date DESC
LIMIT 10
''')

periods = cur.fetchall()
for period_id, period_name, period_type, start_date, end_date in periods:
    print(f'  Period ID: {period_id}')
    print(f'    Name: {period_name}')
    print(f'    Type: {period_type}')
    print(f'    Date Range: {start_date} to {end_date}')
    print()

print('=' * 80)

cur.close()
conn.close()
