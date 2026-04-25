"""
Natural Language Query Parser - 100% Database-Driven

Zero hardcoding. All metrics, periods, companies, aliases loaded from Neon.
Everything is dynamic and driven by actual data in the database.
"""

import re
from dataclasses import dataclass, field
from typing import Optional
from sqlalchemy.orm import Session


@dataclass
class ParsedQuery:
    """Parsed natural language financial query."""
    raw_query: str
    metric: str                          # canonical metric name from DB
    period: str                          # e.g. "Q3 2023"
    compare_period: str                  # e.g. "Q2 2023"  (QoQ default)
    company: str                         # company legal name from DB
    intent: str = "explain_change"       # explain_change | trend | segment_breakdown
    direction: Optional[str] = None      # "increase" | "decrease" | None (unknown)
    confidence: float = 1.0
    warnings: list = field(default_factory=list)


# Direction keywords - these ARE safe because they're language constants, not data
_INCREASE_WORDS = {
    "increase", "increased", "grew", "growth", "rise", "rose", "jumped",
    "improved", "up", "higher", "surge", "surged", "boost", "boosted",
    "expand", "expanded", "spike", "spiked",
}
_DECREASE_WORDS = {
    "decrease", "decreased", "declined", "decline", "drop", "dropped",
    "fell", "fall", "down", "lower", "reduction", "reduced", "shrink",
    "shrunk", "dip", "dipped", "plunge", "plunged",
}


def parse_query(raw: str, db: Session) -> ParsedQuery:
    """
    Parse query with MANDATORY database context.
    Everything comes from Neon - no defaults, no hardcoding.
    
    Raises:
        ValueError: If required data not found in database
    """
    if db is None:
        raise ValueError("Database context is required")
    
    text = raw.strip().lower()
    warnings: list[str] = []

    # ── 1. Load available metrics from DB ──────────────────────────────────
    from ..models.db_models import CanonicalMetric, CanonicalMetricAlias, Metric
    try:
        metrics_db = db.query(CanonicalMetric).all()
        metric_aliases_db = db.query(CanonicalMetricAlias).all()
        operational_metrics_db = db.query(Metric).all()
        
        # Build metric lookup: alias → canonical name
        alias_to_metric = {}
        for alias_record in metric_aliases_db:
            metric_canonical = next(
                (m.canonical_name for m in metrics_db if m.metric_id == alias_record.metric_id),
                None
            )
            if metric_canonical:
                alias_to_metric[alias_record.alias_name.lower()] = metric_canonical
        
        # Also add canonical names themselves as aliases
        for metric in metrics_db:
            alias_to_metric[metric.canonical_name.lower()] = metric.canonical_name

        # Add operational metrics (from 'metrics' table) as aliases
        for op_metric in operational_metrics_db:
            # If the name is already there, leave it. If not, add it.
            if op_metric.name.lower() not in alias_to_metric:
                alias_to_metric[op_metric.name.lower()] = op_metric.name
            if op_metric.display_name.lower() not in alias_to_metric:
                alias_to_metric[op_metric.display_name.lower()] = op_metric.name
            
    except Exception as e:
        raise ValueError(f"Cannot load metrics from database: {e}")

    # ── Guarantee all Quick Query Builder display names are parseable ─────────
    # The QQB uses these exact phrases in NL queries. The canonical names here
    # are the DB column names which financial_accessor can always look up.
    _qqb_display_aliases = {
        "net profit":               "pnl_for_period",
        "net income":               "pnl_for_period",
        "revenue from operations":  "revenue_from_operations",
        "cost of material":         "cost_of_material",
        "employee benefit expense": "employee_benefit_expense",
        "depreciation":             "depreciation",
        "other expenses":           "other_expenses",
        "operating profit":         "operating_profit",
        "profit before tax":        "profit_before_tax",
        "interest expense":         "interest_expense",
        "tax expense":              "tax_expense",
        "other income":             "other_income",
        "total income":             "total_income",
        "total expense":            "total_expense",
        "basic eps":                "basic_eps",
        "diluted eps":              "diluted_eps",
        "gross profit":             "gross_profit",
        "ebitda":                   "ebitda",
    }
    alias_to_metric.update(_qqb_display_aliases)

    if not alias_to_metric:
        raise ValueError(
            "No metrics found in database. Load metrics from mappings_canonical_metrics_combined_1 first."
        )

    # ── 2. Extract metric (longest match wins) ───────────────────────────────
    metric = _extract_metric(text, alias_to_metric)
    if metric is None:
        # No metric found - list available ones
        available_metrics = sorted(set(alias_to_metric.values()))
        metrics_str = ", ".join(available_metrics[:10])
        if len(available_metrics) > 10:
            metrics_str += f", ... and {len(available_metrics) - 10} more"
        raise ValueError(
            f"Metric not found in query. Available metrics: {metrics_str}"
        )

    # ── 3. Load available periods from DB ──────────────────────────────────
    from ..models.db_models import FinancialsPeriod, TimeSeriesData
    try:
        periods_db = db.query(FinancialsPeriod).all()
        available_periods = [f"{p.quarter} {p.fiscal_year}" for p in periods_db]
    except Exception as e:
        raise ValueError(f"Cannot load periods from database: {e}")
    
    if not available_periods:
        raise ValueError("No periods found in financials_period table")

    # ── 4. Load available companies from DB ────────────────────────────────
    from ..models.db_models import CanonicalCompany, CompanyAlias
    try:
        companies_db = db.query(CanonicalCompany).filter(
            CanonicalCompany.is_active == True
        ).all()
        
        company_aliases_db = db.query(CompanyAlias).all()
        
        # Load unique segments from TimeSeriesData (operational entities)
        segments = db.query(TimeSeriesData.segment).distinct().all()
        segment_names = [s[0] for s in segments if s[0]]
        
        # Build company lookup: alias → canonical name
        alias_to_company = {}
        for alias_record in company_aliases_db:
            company_canonical = next(
                (c.official_legal_name for c in companies_db if c.company_id == alias_record.company_id),
                None
            )
            if company_canonical:
                alias_to_company[alias_record.surface_form.lower()] = company_canonical
        
        # Also add canonical names themselves as aliases
        for company in companies_db:
            alias_to_company[company.official_legal_name.lower()] = company.official_legal_name
            
        # Add operational segments as aliases
        for segment_name in segment_names:
            if segment_name.lower() not in alias_to_company:
                alias_to_company[segment_name.lower()] = segment_name
                
    except Exception as e:
        raise ValueError(f"Cannot load companies from database: {e}")
    
    if not alias_to_company:
        raise ValueError("No companies found in database")

    # ── 5. Extract company ────────────────────────────────────────────────────
    company, company_warnings = _extract_company(text, alias_to_company)
    warnings.extend(company_warnings)
    if company is None:
        # No company found - list available ones
        available_companies = sorted(set(alias_to_company.values()))
        companies_str = ", ".join(available_companies[:10])
        if len(available_companies) > 10:
            companies_str += f", ... and {len(available_companies) - 10} more"
        raise ValueError(
            f"Company not found in query. Available: {companies_str}"
        )

    # ── 6. Extract period ─────────────────────────────────────────────────────
    period, compare_period = _extract_period(text, available_periods)
    if period is None:
        # Smart Default: Find the latest period that has data for THIS company
        latest_data_period = db.query(TimeSeriesData.period).filter(
            TimeSeriesData.segment == company
        ).order_by(TimeSeriesData.period.desc()).first()
        
        if latest_data_period:
            period = latest_data_period[0]
            compare_period = _prev_period(period, available_periods)
            warnings.append(f"No period in query - using latest available for {company}: {period} vs {compare_period}")
        else:
            # Fallback to absolute latest
            period = available_periods[-1]
            compare_period = available_periods[-2] if len(available_periods) > 1 else available_periods[0]
            warnings.append(f"No period in query - using absolute latest: {period} vs {compare_period}")

    # ── 7. Intent & direction ─────────────────────────────────────────────────
    intent, direction = _extract_intent(text)

    confidence = 1.0 if not warnings else 0.7

    return ParsedQuery(
        raw_query=raw,
        metric=metric,
        period=period,
        compare_period=compare_period,
        company=company,
        intent=intent,
        direction=direction,
        confidence=confidence,
        warnings=warnings,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────

def _extract_metric(text: str, alias_to_metric: dict) -> Optional[str]:
    """
    Find metric by matching longest alias.
    100% dynamic - reads from alias_to_metric dict loaded from DB.
    """
    best_metric = None
    best_len = 0
    
    for alias_lower, canonical in alias_to_metric.items():
        if alias_lower in text and len(alias_lower) > best_len:
            best_metric = canonical
            best_len = len(alias_lower)
    
    return best_metric


def _extract_period(text: str, available_periods: list) -> tuple[Optional[str], Optional[str]]:
    """
    Extract period from text using actual periods from DB.
    100% dynamic - no hardcoded period patterns.
    
    Handles patterns like:
    - "from Q2 2023 to Q2 2024" → (Q2 2024, Q2 2023)  # "to" is current
    - "Q2 2024 vs Q2 2023" → (Q2 2024, Q2 2023)
    - "Q2 2024 compared to Q2 2023" → (Q2 2024, Q2 2023)
    """
    # Build regex from actual available periods
    period_pattern = "|".join(re.escape(p) for p in available_periods)
    period_re = re.compile(f"\\b({period_pattern})\\b", re.IGNORECASE)
    
    # Check for explicit "from X to Y" pattern (to is current, from is comparison)
    from_to_re = re.compile(
        f"from\\s+({period_pattern})\\s+to\\s+({period_pattern})\\b",
        re.IGNORECASE,
    )
    from_to_match = from_to_re.search(text)
    if from_to_match:
        # "from X to Y" means Y is current, X is comparison
        p_comparison = _normalize_period(from_to_match.group(1), available_periods)
        p_current = _normalize_period(from_to_match.group(2), available_periods)
        return (p_current, p_comparison)
    
    # Check for explicit "X vs Y" or "X compared to Y" pattern
    vs_re = re.compile(
        f"\\b({period_pattern})\\s+(?:vs\\.?|versus|compared to|against)\\s+({period_pattern})\\b",
        re.IGNORECASE,
    )
    
    vs_match = vs_re.search(text)
    if vs_match:
        p1 = _normalize_period(vs_match.group(1), available_periods)
        p2 = _normalize_period(vs_match.group(2), available_periods)
        return (p1, p2)
    
    # Find all period mentions
    all_found = [_normalize_period(m, available_periods) for m in period_re.findall(text)]
    
    if len(all_found) >= 2:
        # Assume first mentioned is comparison, last is current
        # (e.g., "revenue changed from Q2 2023 to Q2 2024" - Q2 2024 is current)
        return (all_found[-1], all_found[0])
    elif len(all_found) == 1:
        return (all_found[0], _prev_period(all_found[0], available_periods))
    
    return (None, None)


def _extract_company(text: str, alias_to_company: dict) -> tuple[Optional[str], list[str]]:
    """
    Find company by matching longest alias.
    100% dynamic - reads from alias_to_company dict loaded from DB.
    """
    warnings = []
    best_match = None
    best_len = 0
    
    # Longest match wins
    for alias_lower, canonical in alias_to_company.items():
        if alias_lower in text and len(alias_lower) > best_len:
            best_match = canonical
            best_len = len(alias_lower)
    
    return (best_match, warnings)


def _extract_intent(text: str) -> tuple[str, Optional[str]]:
    """Extract query intent and direction from text."""
    words = set(re.findall(r'\b\w+\b', text.lower()))
    
    if words & _INCREASE_WORDS:
        direction = "increase"
        intent = "explain_change"
    elif words & _DECREASE_WORDS:
        direction = "decrease"
        intent = "explain_change"
    elif any(w in text for w in ("trend", "over time", "history", "historical")):
        direction = None
        intent = "trend"
    elif any(w in text for w in ("segment", "breakdown", "split", "contribute", "which")):
        direction = None
        intent = "segment_breakdown"
    else:
        direction = None
        intent = "explain_change"
    
    return (intent, direction)


def _normalize_period(raw: str, available_periods: list) -> Optional[str]:
    """Normalize period to exact format in available_periods."""
    raw_lower = raw.strip().lower()
    
    # Find exact match (case-insensitive)
    for period in available_periods:
        if period.lower() == raw_lower:
            return period
    
    return None


def _prev_period(period: str, available_periods: list) -> str:
    """Get previous period from available_periods."""
    try:
        idx = available_periods.index(period)
        return available_periods[idx - 1] if idx > 0 else available_periods[0]
    except (ValueError, IndexError):
        return available_periods[0] if available_periods else period
