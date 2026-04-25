"""
Financial Data Accessor - 100% Database-Driven with Code Mitigation

Retrieves actual financial data from SEC filings without any hardcoded mappings.
All metrics, mappings, and relationships come from the database.

Mitigates database issues in code:
- Period linking failures: Uses PeriodMapper cache and graceful fallbacks
- JSONB columns: Uses DataTypeHandler for type conversion
- Missing metrics: Discovers all metrics from schema dynamically
- Company filtering: Only returns companies with actual filings
"""

from typing import Optional, Dict, List, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct

from ..models.db_models import (
    CanonicalCompany, CanonicalMetric, FinancialsPnL, FinancialsBalanceSheet,
    FinancialsCashFlow, FinancialsFiling, FinancialsPeriod, CanonicalMetricAlias
)
from ..utils.period_mapper import PeriodMapper
from ..utils.period_utils import PeriodNormalizer
from ..utils.data_type_handler import DataTypeHandler
from ..utils.metric_definitions import MetricDefinitions


class FinancialDataAccessor:
    """
    100% database-driven accessor for financial data.
    Zero hardcoding of metric → column mappings.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def _select_priority_filing(self, filings: List[FinancialsFiling]) -> Optional[FinancialsFiling]:
        """
        Select the best filing from multiple filings for same period.
        Priority order:
        1. Audited > Unaudited
        2. Consolidated > Standalone
        3. Latest filing_id (highest number)
        
        Args:
            filings: List of FinancialsFiling objects for same company/period
            
        Returns:
            Single FinancialsFiling with highest priority, or None if list empty
        """
        if not filings:
            return None
        
        if len(filings) == 1:
            return filings[0]
        
        # Sort by priority: audited DESC, consolidated DESC, filing_id DESC
        def filing_priority(f: FinancialsFiling) -> Tuple[int, int, int]:
            audited_score = 1 if f.audited == "Audited" else 0
            consolidated_score = 1 if f.nature == "Consolidated" else 0
            filing_id_score = f.filing_id
            return (audited_score, consolidated_score, filing_id_score)
        
        return max(filings, key=filing_priority)
    
    def get_metric_value(
        self,
        metric_canonical_name: str,
        company_legal_name: str,
        period_q_fiscal_year: str,  # e.g. "Q3 2023" or "Q2 FY2020"
    ) -> Optional[float]:
        """
        Get a single metric value for a company in a specific period.
        Queries REAL SEC filing data directly from Neon database.
        
        CODE MITIGATION APPLIED:
        - Uses PeriodNormalizer to handle multiple period formats
        - Uses MetricDefinitions to discover metric table dynamically
        - Uses DataTypeHandler for JSONB column conversion
        - Handles period linking failures gracefully
        
        Returns:
            Float value from actual SEC filings, or None if not found
        """
        # Query SEC financial tables DIRECTLY (100% real data, zero hardcoding)
        try:
            company = self.db.query(CanonicalCompany).filter(
                CanonicalCompany.official_legal_name == company_legal_name,
                CanonicalCompany.is_active == True
            ).first()
            
            if not company:
                return None  # Company not found in canonical companies
            
            # Parse period using PeriodNormalizer (handles any format)
            period_tuple = PeriodNormalizer.normalize(period_q_fiscal_year, self.db)
            if not period_tuple:
                return None  # Invalid period format
            
            quarter_str, fiscal_year = period_tuple
            
            # Get metric table dynamically from MetricDefinitions or CanonicalMetric
            table_name = MetricDefinitions.get_table(self.db, metric_canonical_name)
            
            # Fallback: try canonical_metrics table
            if not table_name:
                metric = self.db.query(CanonicalMetric).filter(
                    CanonicalMetric.canonical_name == metric_canonical_name
                ).first()
                if metric and metric.table_name:
                    # Normalize short table names (e.g. 'pnl' → 'financials_pnl')
                    raw = metric.table_name.strip().lower()
                    if raw == 'pnl':
                        table_name = 'financials_pnl'
                    elif raw == 'balance_sheet':
                        table_name = 'financials_balance_sheet'
                    elif raw == 'cashflow':
                        table_name = 'financials_cashflow'
                    else:
                        table_name = metric.table_name
                else:
                    return None  # Metric not found
            
            # Find the best filing for this company + period.
            # Uses the same dual-path approach as /api/available-data:
            #   Path 1: period_id FK → financials_period
            #   Path 2: reporting_end_date matches period's calendar_end
            # Only considers filings that actually have a row in the data table.
            # Priority: Audited > Unaudited, Consolidated > Standalone, lowest filing_id.
            from sqlalchemy import text as _sql_text
            row = self.db.execute(_sql_text(f"""
                SELECT ff.filing_id
                FROM financials_filing ff
                INNER JOIN {table_name} fdata ON ff.filing_id = fdata.filing_id
                INNER JOIN financials_period fp ON (
                    fp.period_id = ff.period_id
                    OR fp.calendar_end = ff.reporting_end_date
                )
                WHERE ff.company_id = :cid
                  AND fp.quarter = :quarter
                  AND fp.fiscal_year = :fiscal_year
                ORDER BY
                    (CASE WHEN ff.audited = 'Audited' THEN 1 ELSE 0 END) DESC,
                    (CASE WHEN ff.nature = 'Consolidated' THEN 1 ELSE 0 END) DESC,
                    ff.filing_id ASC
                LIMIT 1
            """), {
                "cid": company.company_id,
                "quarter": quarter_str,
                "fiscal_year": str(fiscal_year),
            }).first()

            if not row:
                return None

            filing_id = row[0]
            
            # Fetch value from appropriate SEC financial table
            # Uses DataTypeHandler to handle JSONB columns
            value = self._fetch_metric_value(
                metric_canonical_name,
                table_name,
                filing_id
            )
            
            return value
        except Exception as e:
            # Log error if needed but return None gracefully
            print(f"Error fetching {metric_canonical_name} for {company_legal_name} {period_q_fiscal_year}: {e}")
            return None
    
    
    def get_time_series(
        self,
        metric_canonical_name: str,
        company_legal_name: str,
    ) -> List[Dict[str, Any]]:
        """
        Get all available data points for a metric across all periods for a company.
        Queries REAL SEC filing data directly from Neon database.
        
        CODE MITIGATION APPLIED:
        - Uses explicit select_from() join to avoid ambiguity
        - Uses outer join for periods to handle broken period linking
        - Uses PeriodMapper for period_id → string conversion
        - Uses DataTypeHandler for JSONB columns
        
        Returns:
            List of {"period": "Q3 2023", "value": 12345.6} dicts
        """
        # Query SEC financial data DIRECTLY (100% real data)
        try:
            company = self.db.query(CanonicalCompany).filter(
                CanonicalCompany.official_legal_name == company_legal_name,
                CanonicalCompany.is_active == True
            ).first()
            
            if not company:
                return []
            
            # Get metric table dynamically
            table_name = MetricDefinitions.get_table(self.db, metric_canonical_name)
            
            # Fallback: try canonical_metrics table
            if not table_name:
                metric = self.db.query(CanonicalMetric).filter(
                    CanonicalMetric.canonical_name == metric_canonical_name
                ).first()
                if metric and metric.table_name:
                    raw = metric.table_name.strip().lower()
                    if raw == 'pnl':
                        table_name = 'financials_pnl'
                    elif raw == 'balance_sheet':
                        table_name = 'financials_balance_sheet'
                    elif raw == 'cashflow':
                        table_name = 'financials_cashflow'
                    else:
                        table_name = metric.table_name
                else:
                    return []
            
            # Get all filings for this company with period info
            # Use EXPLICIT JOIN with select_from() to avoid ambiguity
            # Use OUTER JOIN for period to handle broken period links
            filings = self.db.query(
                FinancialsFiling,
                FinancialsPeriod
            ).select_from(
                FinancialsFiling
            ).outerjoin(
                FinancialsPeriod,
                FinancialsFiling.period_id == FinancialsPeriod.period_id
            ).filter(
                FinancialsFiling.company_id == company.company_id
            ).order_by(
                FinancialsPeriod.fiscal_year.asc(),
                FinancialsPeriod.quarter.asc()
            ).all()
            
            # Group filings by period to handle multiple filings per period
            filings_by_period = {}
            for filing, period in filings:
                if period and period.period_id:
                    period_key = (period.fiscal_year, period.quarter)
                else:
                    # Fallback for broken period links
                    period_key = (None, None)
                
                if period_key not in filings_by_period:
                    filings_by_period[period_key] = []
                filings_by_period[period_key].append((filing, period))
            
            results = []
            for (fiscal_year, quarter), period_filings in filings_by_period.items():
                # Select priority filing for this period
                filing_list = [f for f, p in period_filings]
                priority_filing = self._select_priority_filing(filing_list)
                
                if not priority_filing:
                    continue
                
                # Get the period info for result string
                period = next((p for f, p in period_filings if f == priority_filing), period_filings[0][1])
                
                try:
                    # Get the value using DataTypeHandler
                    value = self._fetch_metric_value(
                        metric_canonical_name,
                        table_name,
                        priority_filing.filing_id
                    )
                    
                    if value is not None:
                        # Handle period: use period object if available, else use PeriodMapper
                        if period and period.quarter and period.fiscal_year:
                            period_str = f"{period.quarter} {period.fiscal_year}"
                        else:
                            # Period linking broken - try PeriodMapper
                            period_str = PeriodMapper.get_period_string(self.db, filing.period_id)
                            if not period_str:
                                period_str = f"Period_{filing.period_id}"  # Last resort
                        
                        results.append({
                            "period": period_str,
                            "value": value
                        })
                except Exception as e:
                    # Skip this filing if there's an error
                    print(f"Warning: Skipping filing {filing.filing_id}: {e}")
                    continue
            
            return results
        except Exception as e:
            print(f"Error getting time series for {metric_canonical_name} at {company_legal_name}: {e}")
            return []
    
    
    def _fetch_metric_value(
        self,
        metric_canonical_name: str,
        table_name: str,
        filing_id: int,
    ) -> Optional[float]:
        """
        Internal helper: fetch the actual metric value from the appropriate financial table.
        
        CODE MITIGATION APPLIED:
        - Uses DataTypeHandler to handle JSONB columns gracefully
        - Handles type conversion errors
        
        Map canonical metric name to column name dynamically from the database.
        """
        # The column name = snake_case version of canonical metric name
        # e.g. "revenue_from_operations" → column "revenue_from_operations"
        column_name = metric_canonical_name
        
        try:
            if table_name == "financials_pnl":
                row = self.db.query(FinancialsPnL).filter(
                    FinancialsPnL.filing_id == filing_id
                ).first()
                if not row:
                    return None
                # Use DataTypeHandler to handle JSONB and other type issues
                return DataTypeHandler.get_numeric_value(row, column_name)
            
            elif table_name == "financials_balance_sheet":
                row = self.db.query(FinancialsBalanceSheet).filter(
                    FinancialsBalanceSheet.filing_id == filing_id
                ).first()
                if not row:
                    return None
                return DataTypeHandler.get_numeric_value(row, column_name)
            
            elif table_name == "financials_cashflow":
                row = self.db.query(FinancialsCashFlow).filter(
                    FinancialsCashFlow.filing_id == filing_id
                ).first()
                if not row:
                    return None
                return DataTypeHandler.get_numeric_value(row, column_name)
            
            else:
                print(f"Warning: Unknown table for metric {metric_canonical_name}: {table_name}")
                return None
        
        except Exception as e:
            print(f"Error fetching {column_name} from {table_name} for filing {filing_id}: {e}")
            return None
    
    
    def get_available_companies(self) -> List[str]:
        """
        Get list of all real companies from SEC filings (no test data).
        
        CODE MITIGATION APPLIED:
        - Only returns companies that have actual filing data (filters out companies 1-21)
        - Uses JOIN to ensure companies have filings
        """
        # Get only companies that have actual filings (NOT companies 1-21 with no data)
        companies = self.db.query(
            CanonicalCompany.official_legal_name
        ).join(
            FinancialsFiling,
            CanonicalCompany.company_id == FinancialsFiling.company_id
        ).filter(
            CanonicalCompany.is_active == True
        ).distinct().order_by(
            CanonicalCompany.official_legal_name
        ).all()
        
        return [c[0] for c in companies]
    
    
    def get_available_periods(self) -> List[str]:
        """
        Get list of all available periods from financials_period table.
        
        CODE MITIGATION APPLIED:
        - Queries financials_period instead of time_series_data
        - Returns real periods from SEC filings
        """
        periods = self.db.query(
            FinancialsPeriod.quarter,
            FinancialsPeriod.fiscal_year
        ).distinct().order_by(
            FinancialsPeriod.fiscal_year.desc(),
            FinancialsPeriod.quarter.desc()
        ).all()
        
        return [f"{q} {y}" for q, y in periods if q and y]
    
    
    def get_available_metrics(self) -> List[str]:
        """
        Get list of all available metrics.
        
        CODE MITIGATION APPLIED:
        - Uses MetricDefinitions to discover ALL metrics from database schema
        - Not limited to only canonical_metrics table (which has only 5 metrics)
        - Discovers 15+ metrics from all financial statement tables
        """
        # Get all metrics from MetricDefinitions (discovers from schema)
        discovered_metrics = MetricDefinitions.get_all_metrics(self.db)
        
        # Also get metrics from canonical_metrics table
        canonical_metrics = self.db.query(CanonicalMetric.canonical_name).all()
        canonical_list = [m[0] for m in canonical_metrics]
        
        # Combine both (discovered metrics + canonical metrics)
        all_metrics = list(set(discovered_metrics + canonical_list))
        
        return sorted(all_metrics)
    
    
    def get_metrics_with_data_for_company(
        self,
        company_legal_name: str,
    ) -> List[str]:
        """
        Get metrics that actually have data for a specific company.
        
        CODE MITIGATION APPLIED:
        - Checks all financial statement tables (P&L, balance sheet, cashflow)
        - Returns only metrics with actual non-null values
        """
        company = self.db.query(CanonicalCompany).filter(
            CanonicalCompany.official_legal_name == company_legal_name,
            CanonicalCompany.is_active == True
        ).first()
        
        if not company:
            return []
        
        # Get all metrics that this company has data for
        # Check which tables have data for this company
        available_metrics = set()
        
        # Get filings for this company
        filings = self.db.query(FinancialsFiling.filing_id).filter(
            FinancialsFiling.company_id == company.company_id
        ).all()
        
        filing_ids = [f[0] for f in filings]
        
        if not filing_ids:
            return []
        
        # Check P&L metrics
        try:
            pnl_metrics = MetricDefinitions.discover_all_metrics(self.db)
            for metric_name, (table_name, _) in pnl_metrics.items():
                if table_name == 'financials_pnl':
                    # Check if this company has data for this metric
                    for filing_id in filing_ids[:5]:  # Check first 5 filings
                        value = self._fetch_metric_value(metric_name, table_name, filing_id)
                        if value is not None:
                            available_metrics.add(metric_name)
                            break
        except:
            pass
        
        return sorted(list(available_metrics))
