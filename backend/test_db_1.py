import sys
from app.config import DATABASE_URL
from sqlalchemy import create_engine, text

print(f'Database URL: {DATABASE_URL[:80]}...')
try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1 as connection_test'))
        print('✓ Database connection successful')
        
        # Check what tables exist
        tables = conn.execute(text('''
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
        '''))
        table_list = [row[0] for row in tables]
        print(f'✓ Tables in database: {table_list}')
        
        # Count rows in each table
        for table in table_list:
            try:
                count = conn.execute(text(f'SELECT COUNT(*) as cnt FROM {table}')).scalar()
                print(f'  - {table}: {count} rows')
            except:
                pass
except Exception as e:
    print(f'✗ Database connection failed: {type(e).__name__}: {e}')
    sys.exit(1)
