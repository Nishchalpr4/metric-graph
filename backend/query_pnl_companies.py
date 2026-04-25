import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2 import sql
from datetime import datetime

# Load environment variables from .env
load_dotenv()
database_url = os.getenv('DATABASE_URL')

if not database_url:
    print("ERROR: DATABASE_URL not found in .env file")
    sys.exit(1)

print("=" * 100)
print("COMPANIES WITH P&L FINANCIAL DATA ANALYSIS")
print("=" * 100)

try:
    # Connect to the database
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    print("\n[OK] Successfully connected to Neon database\n")
    
    # Query to find companies with P&L data
    query = """
    SELECT 
        mcc.company_id,
        mcc.official_legal_name,
        COUNT(fp.id) as pnl_record_count,
        MAX(ff.period_end_date) as last_period_with_data
    FROM 
        mappings_canonical_companies mcc
        INNER JOIN financials_filing ff ON mcc.company_id = ff.company_id
        INNER JOIN financials_pnl fp ON ff.id = fp.filing_id
    GROUP BY 
        mcc.company_id,
        mcc.official_legal_name
    ORDER BY 
        pnl_record_count DESC
    LIMIT 15
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    
    if results:
        print(f"Found {len(results)} companies with P&L financial data (Top 15):\n")
        print("-" * 100)
        print(f"{'Rank':<6} {'Company ID':<12} {'Company Name':<50} {'PnL Records':<15} {'Last Period':<20}")
        print("-" * 100)
        
        for idx, row in enumerate(results, 1):
            company_id, company_name, pnl_count, last_period = row
            last_period_str = last_period.strftime("%Y-%m-%d") if last_period else "N/A"
            
            # Truncate company name if too long
            display_name = company_name[:47] + "..." if len(company_name) > 50 else company_name
            
            print(f"{idx:<6} {company_id:<12} {display_name:<50} {pnl_count:<15} {last_period_str:<20}")
        
        print("-" * 100)
        print(f"\nTotal Companies with P&L Data: {len(results)}")
    else:
        print("No companies found with P&L financial data.")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"ERROR: {str(e)}")
    sys.exit(1)
