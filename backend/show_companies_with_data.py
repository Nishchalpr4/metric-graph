import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
db_url = os.getenv("DATABASE_URL")

conn = psycopg2.connect(db_url)
cur = conn.cursor()

query = """
SELECT 
    mcc.company_id,
    mcc.official_legal_name,
    COUNT(fp.pnl_id) as pnl_records
FROM mappings_canonical_companies mcc
INNER JOIN financials_filing ff ON mcc.company_id = ff.company_id
INNER JOIN financials_pnl fp ON ff.filing_id = fp.filing_id
GROUP BY mcc.company_id, mcc.official_legal_name
ORDER BY pnl_records DESC
LIMIT 20;
"""

cur.execute(query)
print("\n" + "="*100)
print("COMPANIES WITH P&L DATA (Top 20)")
print("="*100)
print(f"{'ID':<5} {'Company Name':<50} {'Records':<10}")
print("-"*100)

for row in cur.fetchall():
    company_id, name, records = row
    print(f"{company_id:<5} {name:<50} {records:<10}")

cur.close()
conn.close()
