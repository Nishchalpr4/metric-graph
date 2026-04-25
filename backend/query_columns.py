import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()
conn_str = os.getenv('DATABASE_URL')
conn = psycopg2.connect(conn_str)
cur = conn.cursor(cursor_factory=RealDictCursor)

tables = ['financials_filing', 'financials_pnl', 'mappings_canonical_companies']

for table in tables:
    print()
    print('=== ' + table.upper() + ' ===')
    query = 'SELECT column_name, data_type FROM information_schema.columns WHERE table_name = ' + "'" + table + "'" + ' ORDER BY ordinal_position'
    cur.execute(query)
    results = cur.fetchall()
    for row in results:
        col_name = row['column_name']
        data_type = row['data_type']
        print(col_name.ljust(30) + data_type.ljust(20))

cur.close()
conn.close()
