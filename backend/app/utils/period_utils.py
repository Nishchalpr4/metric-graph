"""
Period Utilities - 100% Database-Driven

Normalizes different period formats to a standard format.
All lookups query the database - NO hardcoded periods.
"""

import re
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from .period_mapper import PeriodMapper


class PeriodNormalizer:
    """
    Normalize various period input formats to standard (quarter, year) tuple.
    Handles formats like:
    - "Q1 2024"
    - "Q1FY2024" 
    - "2024-Q1"
    - "Period_231" (looks up in database)
    """
    
    @staticmethod
    def normalize(period_input: str, db: Session) -> Optional[Tuple[str, int]]:
        """
        Convert any period format to (quarter, year) tuple.
        
        Args:
            period_input: Period string in any recognized format
            db: SQLAlchemy session for database lookups
            
        Returns:
            Tuple like ("Q1", 2024) or None if cannot parse
        """
        if not period_input:
            return None
        
        period_str = period_input.strip()
        
        # Format: "Q1 2024" or "Q1  2024" (standard format)
        match = re.match(r'Q(\d)\s+(\d{4})', period_str)
        if match:
            quarter = f"Q{match.group(1)}"
            year = int(match.group(2))
            return (quarter, year)
        
        # Format: "Period_231" - lookup in database
        match = re.match(r'Period_(\d+)', period_str)
        if match:
            period_id = int(match.group(1))
            result = PeriodMapper.get_period_tuple(db, period_id)
            return result
        
        # Format: "Q1 FY2024" or "Q1FY2024"
        match = re.match(r'Q(\d)\s*FY(\d{4})', period_str, re.IGNORECASE)
        if match:
            quarter = f"Q{match.group(1)}"
            year = int(match.group(2))
            return (quarter, year)
        
        # Format: "2024-Q1"
        match = re.match(r'(\d{4})-Q(\d)', period_str)
        if match:
            quarter = f"Q{match.group(2)}"
            year = int(match.group(1))
            return (quarter, year)
        
        # Format: "FY2024 Q1"
        match = re.match(r'FY(\d{4})\s+Q(\d)', period_str, re.IGNORECASE)
        if match:
            quarter = f"Q{match.group(2)}"
            year = int(match.group(1))
            return (quarter, year)
        
        return None
    
    @staticmethod
    def to_string(quarter: str, year: int) -> str:
        """Convert (quarter, year) tuple back to standard string format"""
        return f"{quarter} {year}"
    
    @staticmethod
    def parse_period(period_input: str, db: Session) -> Optional[str]:
        """
        Parse any period format and return standard "Q1 2024" format.
        
        Args:
            period_input: Period in any format
            db: SQLAlchemy session
            
        Returns:
            Standard format like "Q1 2024" or None if cannot parse
        """
        result = PeriodNormalizer.normalize(period_input, db)
        if result:
            quarter, year = result
            return PeriodNormalizer.to_string(quarter, year)
        return None
