import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
db_url = os.getenv('DATABASE_URL')

if not db_url:
    print('ERROR: DATABASE_URL not found in .env file')
    exit(1)

print('Connecting to database...')
try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    print('Connected successfully!\n')
except Exception as e:
    print(f'ERROR: Failed to connect - {e}')
    exit(1)

print('=' * 80)
print('DATABASE ROW COUNTS')
print('=' * 80)
print()

tables_to_check = [
    'mappings_canonical_companies',
    'financials_period',
    'financials_filing',
    'financials_pnl'
]

for table_name in tables_to_check:
    try:
        cur.execute(f'SELECT COUNT(*) FROM {table_name}')
        count = cur.fetchone()[0]
        print(f'{table_name:40} {count:10,} rows')
    except Exception as e:
        print(f'{table_name:40} ERROR: {str(e)}')

print()
print('=' * 80)
print('SCHEMA: ALL TABLES IN DATABASE')
print('=' * 80)
print()

cur.execute('''
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name
''')

tables = cur.fetchall()
print(f'Found {len(tables)} tables:\n')
for idx, (table_name,) in enumerate(tables, 1):
    print(f'  {idx:2d}. {table_name}')

print()
print('=' * 80)

cur.close()
conn.close()
print('\nQuery completed successfully!')
