import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
db_url = os.getenv('DATABASE_URL')
conn = psycopg2.connect(db_url)
cur = conn.cursor()

print('=== SCHEMA OF financials_filing TABLE ===')
cur.execute('''
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name='financials_filing'
ORDER BY ordinal_position
''')

columns = cur.fetchall()
for col_name, data_type in columns:
    print(f'  {col_name:30} ({data_type})')

cur.close()
conn.close()
