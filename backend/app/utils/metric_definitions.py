"""
Metric Definitions - 100% Database-Driven

Discovers available metrics from database schema dynamically.
No hardcoded metric lists - queries actual table columns from Neon DB.
"""

from typing import List, Optional, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import inspect


class MetricDefinitions:
    """
    Dynamically discover and define metrics from database schema.
    Queries real table columns instead of hardcoding metric mappings.
    """
    
    # Cache for discovered metrics (session-level)
    _metrics_cache: Dict[str, Tuple[str, str]] = {}
    _cache_initialized: bool = False
    
    @classmethod
    def discover_all_metrics(cls, db: Session) -> Dict[str, Tuple[str, str]]:
        """
        Discover all available metrics from database tables.
        
        Returns:
            Dict mapping metric_name → (table_name, display_name)
        """
        if cls._cache_initialized and cls._metrics_cache:
            return cls._metrics_cache
        
        from ..models.db_models import FinancialsPnL, FinancialsBalanceSheet, FinancialsCashFlow
        
        metrics = {}
        
        # Discover P&L metrics
        pnl_columns = cls._get_numeric_columns(db, FinancialsPnL, 'financials_pnl')
        for col in pnl_columns:
            if col not in ['filing_id', 'pnl_id']:  # Skip ID columns
                metrics[col] = ('financials_pnl', cls._make_display_name(col))
        
        # Discover Balance Sheet metrics
        try:
            bs_columns = cls._get_numeric_columns(db, FinancialsBalanceSheet, 'financials_balance_sheet')
            for col in bs_columns:
                if col not in ['filing_id', 'balance_sheet_id']:
                    metrics[col] = ('financials_balance_sheet', cls._make_display_name(col))
        except:
            pass  # Table might not exist or be accessible
        
        # Discover Cash Flow metrics
        try:
            cf_columns = cls._get_numeric_columns(db, FinancialsCashFlow, 'financials_cashflow')
            for col in cf_columns:
                if col not in ['filing_id', 'cashflow_id', 'cf_id']:
                    metrics[col] = ('financials_cashflow', cls._make_display_name(col))
        except:
            pass  # Table might not exist or be accessible
        
        cls._metrics_cache = metrics
        cls._cache_initialized = True
        
        return metrics
    
    @classmethod
    def _get_numeric_columns(cls, db: Session, model_class, table_name: str) -> List[str]:
        """
        Get all numeric column names from a table.
        
        Args:
            db: SQLAlchemy session
            model_class: SQLAlchemy model class
            table_name: Table name for fallback
            
        Returns:
            List of column names that contain numeric data
        """
        try:
            # Use SQLAlchemy inspector to get column info
            inspector = inspect(model_class)
            
            numeric_cols = []
            for column in inspector.columns:
                # Check if column type is numeric (Float, Integer, Numeric)
                col_type = str(column.type).lower()
                if any(t in col_type for t in ['float', 'integer', 'numeric', 'double', 'decimal']):
                    numeric_cols.append(column.name)
            
            return numeric_cols
        
        except Exception as e:
            print(f"Warning: Could not inspect {table_name}: {e}")
            return []
    
    @classmethod
    def _make_display_name(cls, column_name: str) -> str:
        """
        Convert snake_case column name to Display Name.
        
        Examples:
            revenue_from_operations → Revenue From Operations
            total_assets → Total Assets
            basic_eps → Basic EPS
        """
        # Split by underscore
        words = column_name.split('_')
        
        # Capitalize each word
        display_words = []
        for word in words:
            # Handle special cases
            if word.upper() in ['EPS', 'ROE', 'ROA', 'EBIT', 'EBITDA', 'PNL', 'CF']:
                display_words.append(word.upper())
            else:
                display_words.append(word.capitalize())
        
        return ' '.join(display_words)
    
    @classmethod
    def get_all_metrics(cls, db: Session) -> List[str]:
        """Get list of all available metric names"""
        metrics = cls.discover_all_metrics(db)
        return list(metrics.keys())
    
    @classmethod
    def get_table(cls, db: Session, metric_name: str) -> Optional[str]:
        """
        Get table name for a metric.
        
        Returns:
            Table name like 'financials_pnl' or None if not found
        """
        metrics = cls.discover_all_metrics(db)
        if metric_name in metrics:
            return metrics[metric_name][0]
        
        # Fallback: check canonical_metrics table
        from ..models.db_models import CanonicalMetric
        metric = db.query(CanonicalMetric).filter(
            CanonicalMetric.canonical_name == metric_name
        ).first()
        
        if metric and metric.table_name:
            return metric.table_name
        
        return None
    
    @classmethod
    def get_display_name(cls, db: Session, metric_name: str) -> str:
        """
        Get human-readable display name for a metric.
        
        Returns:
            Display name like "Revenue From Operations"
        """
        metrics = cls.discover_all_metrics(db)
        if metric_name in metrics:
            return metrics[metric_name][1]
        
        # Fallback: generate from metric name
        return cls._make_display_name(metric_name)
    
    @classmethod
    def metric_exists(cls, db: Session, metric_name: str) -> bool:
        """Check if a metric exists in the database"""
        metrics = cls.discover_all_metrics(db)
        return metric_name in metrics
    
    @classmethod
    def clear_cache(cls):
        """Clear the cache (useful for testing or schema changes)"""
        cls._metrics_cache.clear()
        cls._cache_initialized = False
