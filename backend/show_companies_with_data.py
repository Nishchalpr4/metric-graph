import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
db_url = os.getenv('DATABASE_URL')
conn = psycopg2.connect(db_url)
cur = conn.cursor()

print('=== SCHEMA OF financials_company ===')
print()

cur.execute("""
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'financials_company'
ORDER BY ordinal_position
""")
cols = cur.fetchall()

if not cols:
    print('Table financials_company does NOT exist or has no columns.')
    print()
    print('Available tables:')
    cur.execute("""
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public' ORDER BY table_name
    """)
    for (t,) in cur.fetchall():
        print(f'  {t}')
else:
    print(f'{"Column":35} {"Type":25} {"Nullable"}')
    print('-' * 70)
    for col_name, data_type, nullable in cols:
        print(f'{col_name:35} {data_type:25} {nullable}')
    print()

    print('=== FIRST 10 ROWS OF financials_company ===')
    print()
    col_names = [c[0] for c in cols]
    cur.execute('SELECT * FROM financials_company LIMIT 10')
    rows = cur.fetchall()
    for idx, row in enumerate(rows, 1):
        print(f'Row {idx}:')
        for cn, val in zip(col_names, row):
            print(f'  {cn}: {val}')
        print()

print()
print('=== COMPANY ID OVERLAP: financials_company vs financials_filing ===')
print()

try:
    cur.execute("""
    SELECT fc.company_id
    FROM financials_company fc
    ORDER BY fc.company_id
    LIMIT 20
    """)
    fc_ids = [r[0] for r in cur.fetchall()]
    print(f'First 20 company_ids in financials_company: {fc_ids}')
    print()

    check_ids = [22, 23, 24, 243]
    for cid in check_ids:
        cur.execute('SELECT COUNT(*) FROM financials_filing WHERE company_id = %s', (cid,))
        filing_count = cur.fetchone()[0]
        in_fc = cid in fc_ids
        print(f'  company_id={cid}: in financials_company={in_fc}, filings={filing_count}')
except Exception as e:
    print(f'Error checking overlap: {e}')

cur.close()
conn.close()
print()
print('Done.')
