import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2 import sql

# Load environment variables from .env
load_dotenv()
database_url = os.getenv('DATABASE_URL')

if not database_url:
    print("ERROR: DATABASE_URL not found in .env file")
    sys.exit(1)

print("=" * 80)
print("NEON DATABASE SCHEMA INSPECTOR")
print("=" * 80)

try:
    # Connect to the database
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    print("\n[OK] Successfully connected to Neon database\n")
    
    # Query all tables from information_schema
    cursor.execute("""
        SELECT table_schema, table_name 
        FROM information_schema.tables 
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY table_schema, table_name
    """)
    
    tables = cursor.fetchall()
    
    if not tables:
        print("No tables found in the database")
        cursor.close()
        conn.close()
        sys.exit(0)
    
    print(f"Found {len(tables)} table(s):\n")
    
    # For each table, get details
    for schema, table_name in tables:
        print("-" * 80)
        print(f"TABLE: {schema}.{table_name}")
        print("-" * 80)
        
        # Get row count
        cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
            sql.Identifier(schema),
            sql.Identifier(table_name)
        ))
        row_count = cursor.fetchone()[0]
        print(f"Row Count: {row_count:,}")
        
        # Get column information
        cursor.execute("""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """, (schema, table_name))
        
        columns = cursor.fetchall()
        
        if columns:
            print(f"\nColumns ({len(columns)}):")
            print(f"  {'Name':<30} {'Type':<20} {'Nullable':<10} {'Default':<25}")
            print(f"  {'-'*30} {'-'*20} {'-'*10} {'-'*25}")
            
            for col_name, data_type, is_nullable, col_default in columns:
                nullable_str = "YES" if is_nullable == 'YES' else "NO"
                default_str = str(col_default)[:23] if col_default else "NULL"
                print(f"  {col_name:<30} {data_type:<20} {nullable_str:<10} {default_str:<25}")
        
        # Get primary key info using constraint names
        cursor.execute("""
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            JOIN pg_class t ON t.oid = i.indrelid
            WHERE t.relname = %s AND t.relnamespace = (
                SELECT oid FROM pg_namespace WHERE nspname = %s
            ) AND i.indisprimary
            ORDER BY a.attnum
        """, (table_name, schema))
        
        pk_columns = cursor.fetchall()
        if pk_columns:
            pk_list = ", ".join([pk[0] for pk in pk_columns])
            print(f"\nPrimary Key: {pk_list}")
        
        print()
    
    # Get database statistics
    print("-" * 80)
    print("DATABASE STATISTICS")
    print("-" * 80)
    
    cursor.execute("""
        SELECT 
            schemaname,
            COUNT(*) as table_count,
            SUM(n_live_tup) as total_rows
        FROM pg_stat_user_tables
        GROUP BY schemaname
        ORDER BY schemaname
    """)
    
    stats = cursor.fetchall()
    for schema_name, table_count, total_rows in stats:
        total_rows = total_rows if total_rows else 0
        print(f"Schema: {schema_name}")
        print(f"  Tables: {table_count}")
        print(f"  Total Rows: {total_rows:,}")
        print()
    
    cursor.close()
    conn.close()
    print("=" * 80)
    print("[OK] Schema inspection completed successfully")
    print("=" * 80)

except psycopg2.OperationalError as e:
    print(f"ERROR: Failed to connect to database: {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
