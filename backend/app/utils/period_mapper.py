"""
Period Mapper - 100% Database-Driven

Handles period lookups and mappings by querying the financials_period table.
Caches results to avoid repeated database queries.
NO hardcoded period mappings.
"""

from typing import Optional, Dict, Tuple
from sqlalchemy.orm import Session


class PeriodMapper:
    """
    Maps period_id to human-readable period format (Q1 2024).
    Queries financials_period table from Neon DB.
    """
    
    # Cache to avoid repeated DB queries (session-level cache)
    _period_cache: Dict[int, Tuple[str, int]] = {}
    
    @classmethod
    def get_period_string(cls, db: Session, period_id: Optional[int]) -> Optional[str]:
        """
        Convert period_id to 'Q1 2024' format.
        
        Args:
            db: SQLAlchemy session
            period_id: Period ID from financials_filing table
            
        Returns:
            Period string like "Q1 2024" or None if period not found
        """
        if period_id is None:
            return None
        
        # Check cache first
        if period_id in cls._period_cache:
            quarter, year = cls._period_cache[period_id]
            return f"{quarter} {year}"
        
        # Query database
        from ..models.db_models import FinancialsPeriod
        
        period = db.query(FinancialsPeriod).filter(
            FinancialsPeriod.period_id == period_id
        ).first()
        
        if period and period.quarter and period.fiscal_year:
            # Cache the result
            cls._period_cache[period_id] = (period.quarter, period.fiscal_year)
            return f"{period.quarter} {period.fiscal_year}"
        
        return None  # Period not found in database
    
    @classmethod
    def get_period_tuple(cls, db: Session, period_id: int) -> Optional[Tuple[str, int]]:
        """
        Get (quarter, fiscal_year) tuple for a period_id.
        
        Returns:
            Tuple like ("Q1", 2024) or None if not found
        """
        if period_id in cls._period_cache:
            return cls._period_cache[period_id]
        
        from ..models.db_models import FinancialsPeriod
        
        period = db.query(FinancialsPeriod).filter(
            FinancialsPeriod.period_id == period_id
        ).first()
        
        if period and period.quarter and period.fiscal_year:
            result = (period.quarter, period.fiscal_year)
            cls._period_cache[period_id] = result
            return result
        
        return None
    
    @classmethod
    def find_period_id(cls, db: Session, quarter: str, fiscal_year: int) -> Optional[int]:
        """
        Reverse lookup: find period_id for a quarter/year.
        
        Args:
            db: SQLAlchemy session
            quarter: Quarter string like "Q1", "Q2", etc.
            fiscal_year: Fiscal year like 2024
            
        Returns:
            period_id or None if not found
        """
        from ..models.db_models import FinancialsPeriod
        
        period = db.query(FinancialsPeriod).filter(
            FinancialsPeriod.quarter == quarter,
            FinancialsPeriod.fiscal_year == str(fiscal_year)  # Convert to string - DB column is TEXT
        ).first()
        
        if period:
            # Cache it
            cls._period_cache[period.period_id] = (period.quarter, period.fiscal_year)
            return period.period_id
        
        return None
    
    @classmethod
    def clear_cache(cls):
        """Clear the cache (useful for testing or if database changes)"""
        cls._period_cache.clear()
