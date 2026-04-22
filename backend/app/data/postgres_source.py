"""
PostgreSQL Data Source

Connects to external Neon PostgreSQL database and syncs metric data.
"""

import logging
from typing import Dict, List, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

log = logging.getLogger(__name__)


class NeonDataSource:
    """
    Connection to external Neon PostgreSQL database.
    
    Usage:
        source = NeonDataSource(
            connection_string="postgresql://user:password@host/dbname"
        )
        data = source.fetch_metrics()
    """
    
    def __init__(self, connection_string: str):
        """
        Args:
            connection_string: PostgreSQL connection URL
                Format: postgresql://user:password@host:port/dbname
                Example: postgresql://user:pass@ep-xyz.us-east-1.neon.tech/metrics_db
        """
        self.connection_string = connection_string
        try:
            self.engine = create_engine(connection_string, echo=False)
            self.SessionLocal = sessionmaker(bind=self.engine)
            log.info("Connected to Neon database")
        except Exception as e:
            log.error(f"Failed to connect to Neon: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test if connection is working"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                log.info("Neon database connection test successful")
                return True
        except Exception as e:
            log.error(f"Neon connection test failed: {e}")
            return False
    
    def fetch_metrics(self) -> List[Dict]:
        """
        Fetch all metric data from Neon database.
        
        Expects a table with columns:
            - metric_name (VARCHAR)
            - period (VARCHAR)
            - segment (VARCHAR)
            - value (NUMERIC/FLOAT)
        
        Returns:
            List of dicts: [{"metric_name": ..., "period": ..., "segment": ..., "value": ...}]
        """
        try:
            session = self.SessionLocal()
            query = text("""
                SELECT 
                    metric_name,
                    period,
                    segment,
                    value
                FROM time_series_data
                ORDER BY period, segment, metric_name
            """)
            result = session.execute(query)
            rows = result.fetchall()
            session.close()
            
            # Convert to list of dicts
            data = [
                {
                    "metric_name": row[0],
                    "period": row[1],
                    "segment": row[2],
                    "value": float(row[3]),
                }
                for row in rows
            ]
            
            log.info(f"Fetched {len(data)} metric rows from Neon")
            return data
        
        except Exception as e:
            log.error(f"Error fetching from Neon: {e}")
            raise
    
    def fetch_metrics_for_period(self, period: str) -> List[Dict]:
        """Fetch metrics for a specific period"""
        try:
            session = self.SessionLocal()
            query = text("""
                SELECT 
                    metric_name,
                    period,
                    segment,
                    value
                FROM time_series_data
                WHERE period = :period
            """)
            result = session.execute(query, {"period": period})
            rows = result.fetchall()
            session.close()
            
            data = [
                {
                    "metric_name": row[0],
                    "period": row[1],
                    "segment": row[2],
                    "value": float(row[3]),
                }
                for row in rows
            ]
            
            log.info(f"Fetched {len(data)} rows for period {period}")
            return data
        
        except Exception as e:
            log.error(f"Error fetching period data from Neon: {e}")
            raise
    
    def close(self):
        """Close database connection"""
        if hasattr(self, 'engine'):
            self.engine.dispose()
            log.info("Neon connection closed")
