from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text,
    TIMESTAMP, UniqueConstraint, ForeignKey, JSON, CHAR, Date
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql import func
from ..database import Base


class Metric(Base):
    """
    Every financial or operational metric tracked in the system.
    is_base=True  → raw input fed from external data
    is_base=False → computed from a formula over other metrics
    """
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=False)
    description = Column(Text)
    formula = Column(String(500))          # Human-readable formula string
    formula_inputs = Column(ARRAY(String)) # Names of metrics this formula depends on
    unit = Column(String(50))              # ₹B, %, M, ₹, items, K, index
    granularity = Column(String(50), default="quarterly")
    category = Column(String(100))         # Financial | Operational | User
    is_base = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


class MetricRelationship(Base):
    """
    Directed edge in the causal knowledge graph.

    relationship_type options:
      "formula_dependency" – source is mathematically required to compute target
      "causal_driver"      – source causes target to move (business logic)

    direction: "positive" | "negative"
    strength : 0.0–1.0  (how strongly source drives target)
    """
    __tablename__ = "metric_relationships"

    id = Column(Integer, primary_key=True, index=True)
    source_metric = Column(String(100), ForeignKey("metrics.name"), nullable=False)
    target_metric = Column(String(100), ForeignKey("metrics.name"), nullable=False)
    relationship_type = Column(String(50), nullable=False)
    direction = Column(String(20), default="positive")
    strength = Column(Float, default=1.0)
    explanation = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())


class TimeSeriesData(Base):
    """
    One row = one metric, one quarter, one segment.
    is_computed=True means the value was derived by the formula engine.
    """
    __tablename__ = "time_series_data"

    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(100), ForeignKey("metrics.name"), nullable=False)
    period = Column(String(20), nullable=False)      # e.g. "Q3 2023"
    segment = Column(String(100), default="Overall")  # Default segment name
    value = Column(Float, nullable=False)
    is_computed = Column(Boolean, default=False)
    notes = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "metric_name", "period", "segment",
            name="uq_metric_period_segment"
        ),
    )


class CausalEvent(Base):
    """
    Named business events that explain causal spikes in a given period.
    Enriches the inference output with narrative context.
    """
    __tablename__ = "causal_events"

    id = Column(Integer, primary_key=True, index=True)
    period = Column(String(20), nullable=False)
    event_name = Column(String(200), nullable=False)
    segment = Column(String(100), default="Overall")
    affected_metrics = Column(ARRAY(String))
    direction = Column(String(20))      # positive | negative
    magnitude = Column(String(20))      # high | medium | low
    explanation = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())


class QueryLog(Base):
    """Stores every NL query and its result for auditability."""
    __tablename__ = "query_log"

    id = Column(Integer, primary_key=True, index=True)
    query_text = Column(Text, nullable=False)
    parsed_metric = Column(String(100))
    parsed_period = Column(String(20))
    parsed_compare_period = Column(String(20))
    parsed_segment = Column(String(100))
    result = Column(JSON)
    created_at = Column(TIMESTAMP, server_default=func.now())


class CanonicalCompany(Base):
    """
    Real company master data from SEC/regulatory filings.
    Maps to actual financial statements and metrics.
    """
    __tablename__ = "mappings_canonical_companies"

    company_id = Column(Integer, primary_key=True, index=True)
    official_legal_name = Column(Text, nullable=False, index=True)
    domicile_country = Column(CHAR(2), nullable=True)
    lei_code = Column(String(20), nullable=True)
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    popularity_score = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())


class CanonicalMetric(Base):
    """
    Unified metric definitions from SEC/XBRL data.
    Single source of truth for all metrics in the system.
    """
    __tablename__ = "mappings_canonical_metrics_combined_1"

    metric_id = Column(Integer, primary_key=True, index=True)
    canonical_name = Column(Text, nullable=False, index=True, unique=True)
    xbrl_tag = Column(String(100), nullable=True)
    semantic_definition = Column(Text)
    standard_unit = Column(String(50))
    category = Column(String(100))
    intent_type = Column(String(50))
    table_name = Column(String(50))  # Which financial table it comes from
    extras = Column(JSON)


class CanonicalMetricAlias(Base):
    """
    All aliases for metrics (e.g. 'net income', 'profit', 'earnings' → 'net_income')
    100% dynamic - zero hardcoded aliases.
    """
    __tablename__ = "mappings_metric_aliases_combined_1"

    alias_id = Column(Integer, primary_key=True, index=True)
    metric_id = Column(Integer, ForeignKey("mappings_canonical_metrics_combined_1.metric_id"))
    alias_name = Column(Text, nullable=False, index=True)
    alias_type = Column(String(50))
    score = Column(Float, default=1.0)


class CompanyAlias(Base):
    """
    All aliases for companies (e.g. 'AAPL', 'Apple Computer Inc' → 'Apple Inc.')
    100% dynamic - zero hardcoded aliases.
    """
    __tablename__ = "mappings_company_aliases"

    alias_id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("mappings_canonical_companies.company_id"))
    surface_form = Column(Text, nullable=False, index=True)
    alias_type = Column(String(50))


class CompanyTicker(Base):
    """Stock ticker symbols for companies."""
    __tablename__ = "mappings_company_tickers"

    ticker_id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("mappings_canonical_companies.company_id"))
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(10))
    is_primary = Column(Boolean, default=False)


class FinancialsPeriod(Base):
    """
    All fiscal periods in the system.
    100% dynamic - system reads what's actually in the database.
    """
    __tablename__ = "financials_period"

    period_id = Column(Integer, primary_key=True, index=True)
    quarter = Column(String(10), nullable=False)  # e.g. "Q1", "Q2"
    fiscal_year = Column(String(10), nullable=False)  # e.g. "2023"
    calendar_start = Column(Date, nullable=False)
    calendar_end = Column(Date, nullable=False)
    created_at = Column(TIMESTAMP, default=func.now(), server_default=func.now())


class FinancialsFiling(Base):
    """
    SEC filing metadata.
    Connects company → period → financial statements.
    """
    __tablename__ = "financials_filing"

    filing_id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("mappings_canonical_companies.company_id"), nullable=False)
    period_id = Column(Integer, ForeignKey("financials_period.period_id"), nullable=False)
    type = Column(String(50))  # 10-K, 10-Q, etc.
    nature = Column(String(50))
    audited = Column(String(20))
    filing_type = Column(String(50))
    cash_flow_type = Column(String(50))
    reporting_start_date = Column(String(20))
    reporting_end_date = Column(String(20))


class FinancialsPnL(Base):
    """
    Income Statement (P&L) data.
    Raw data from SEC filings - every line item.
    """
    __tablename__ = "financials_pnl"

    pnl_id = Column(Integer, primary_key=True, index=True)
    filing_id = Column(Integer, ForeignKey("financials_filing.filing_id"), nullable=False)
    revenue_from_operations = Column(Float)
    other_income = Column(Float)
    total_income = Column(Float)
    cost_of_material = Column(Float)
    employee_benefit_expense = Column(Float)
    depreciation = Column(Float)
    other_expenses = Column(Float)
    interest_expense = Column(Float)
    total_expense = Column(Float)
    operating_profit = Column(Float)
    profit_before_tax = Column(Float)
    pnl_for_period = Column(Float)
    tax_expense = Column(Float)
    other_comprehensive_income = Column(Float)
    comprehensive_income_for_the_period = Column(Float)
    basic_eps = Column(Float)
    diluted_eps = Column(Float)
    other = Column(JSON)  # Additional fields


class FinancialsBalanceSheet(Base):
    """
    Balance Sheet data.
    Assets, Liabilities, Equity from SEC filings.
    """
    __tablename__ = "financials_balance_sheet"

    bs_id = Column(Integer, primary_key=True, index=True)
    filing_id = Column(Integer, ForeignKey("financials_filing.filing_id"), nullable=False)
    total_assets = Column(Float)
    total_non_curr_assets = Column(Float)
    total_current_assets = Column(Float)
    total_equity = Column(Float)
    tot_non_curr_liab = Column(Float)  # Note: "tot" not "total"
    total_curr_liab = Column(Float)
    equity_share_capital = Column(Float)
    other_equity = Column(Float)
    other = Column(JSON)  # Additional fields


class FinancialsCashFlow(Base):
    """
    Cash Flow Statement data.
    Operating, Investing, Financing cash flows.
    """
    __tablename__ = "financials_cashflow"

    cashflow_id = Column(Integer, primary_key=True, index=True)
    filing_id = Column(Integer, ForeignKey("financials_filing.filing_id"), nullable=False)
    operating_cash_flow = Column(Float)
    investing_cash_inflow_outflow = Column(Float)
    financing_inflow_outflow_of_cash = Column(Float)
    net_cash_and_cash_equivalent_at_beginning = Column(Float)
    net_cash_and_cash_equivalent_at_end = Column(Float)
    other = Column(JSON)  # Additional fields
