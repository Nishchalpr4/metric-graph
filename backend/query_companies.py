import sys
from app.config import DATABASE_URL
from sqlalchemy import create_engine, text

print("Querying for companies with financial data...\n")
try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        # Query companies with PnL records
        query = """
        SELECT 
            c.company_id,
            c.official_legal_name,
            COUNT(pnl.id) as pnl_record_count
        FROM company c
        LEFT JOIN financial_pnl pnl ON c.company_id = pnl.company_id
        WHERE pnl.id IS NOT NULL
        GROUP BY c.company_id, c.official_legal_name
        ORDER BY pnl_record_count DESC
        LIMIT 20;
        """
        
        result = conn.execute(text(query))
        rows = result.fetchall()
        
        print(f"{'Company ID':<15} {'Official Legal Name':<50} {'PnL Records':<15}")
        print("-" * 80)
        for row in rows:
            company_id, legal_name, count = row
            print(f"{str(company_id):<15} {str(legal_name):<50} {str(count):<15}")
        
        print(f"\nTotal companies with financial data: {len(rows)}")
        
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    sys.exit(1)
