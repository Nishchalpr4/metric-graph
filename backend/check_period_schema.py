import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
db_url = os.getenv('DATABASE_URL')
conn = psycopg2.connect(db_url)
cur = conn.cursor()

# Check schema of financials_period table
print('Columns in financials_period table:')
print('-' * 80)
cur.execute('''
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name='financials_period'
ORDER BY ordinal_position
''')

for col_name, data_type in cur.fetchall():
    print(f'  {col_name:30} ({data_type})')

cur.close()
conn.close()
