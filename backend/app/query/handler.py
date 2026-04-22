"""
Query Handler - 100% Database-Driven

Orchestrates the full pipeline:
  parse NL query → validate → fetch from real financials → log → return result
"""

import logging
from typing import Any, Dict

import networkx as nx
from sqlalchemy.orm import Session

from .parser import parse_query, ParsedQuery
from ..graph.inference import analyse
from ..data.financial_accessor import FinancialDataAccessor
from ..models.db_models import QueryLog

log = logging.getLogger(__name__)


def handle_query(
    raw_query: str,
    db: Session,
    graph: nx.DiGraph,
) -> Dict[str, Any]:
    """
    Main entry-point called from the API layer.
    Returns the complete analysis result dict.
    100% driven by real financial data from Neon.
    """
    parsed = parse_query(raw_query, db=db)
    log.info("Parsed query: metric=%s period=%s vs %s company=%s",
             parsed.metric, parsed.period, parsed.compare_period, parsed.company)

    result = _dispatch(parsed, db, graph)

    # Persist query log (best-effort; don't fail on log error)
    try:
        db.add(QueryLog(
            query_text=raw_query,
            parsed_metric=parsed.metric,
            parsed_period=parsed.period,
            parsed_compare_period=parsed.compare_period,
            parsed_segment=parsed.company,  # Store company as segment for compatibility
            result=result,
        ))
        db.commit()
    except Exception as exc:
        log.warning("Could not write query log: %s", exc)
        db.rollback()

    return {
        "parsed": {
            "metric": parsed.metric,
            "period": parsed.period,
            "compare_period": parsed.compare_period,
            "company": parsed.company,
            "intent": parsed.intent,
        },
        "warnings": parsed.warnings,
        "result": result,
    }


# ─────────────────────────────────────────────────────────────────────────────

def _dispatch(parsed: ParsedQuery, db: Session, graph: nx.DiGraph) -> Dict[str, Any]:
    """Route to appropriate analysis based on intent."""
    accessor = FinancialDataAccessor(db)
    
    if parsed.intent == "trend":
        return _trend_analysis(parsed, accessor)
    if parsed.intent == "segment_breakdown":
        return _segment_breakdown(parsed, accessor)
    # Default: explain_change (causal analysis)
    return _explain_change(parsed, accessor, graph)


def _explain_change(
    parsed: ParsedQuery,
    accessor: FinancialDataAccessor,
    graph: nx.DiGraph,
) -> Dict[str, Any]:
    """
    Explain what drove a metric change between two periods.
    Uses the full inference engine for deep driver analysis with:
    - Formula decomposition (mathematical layer)
    - Causal driver analysis (business layer)  
    - Recursive sub-driver breakdown
    - Contribution attribution
    - Period events
    """
    # Use the full inference engine for deep analysis
    result = analyse(
        metric_name=parsed.metric,
        period=parsed.period,
        compare_period=parsed.compare_period,
        segment=parsed.company,  # company is used as segment
        db=accessor.db,
        graph=graph,
    )
    
    # Add type field for frontend compatibility
    result["type"] = "explain_change"
    result["company"] = parsed.company
    
    # Keep backward compatibility fields
    if "change" in result:
        result["value_period"] = result["change"].get("current_value")
        result["value_compare"] = result["change"].get("prev_value")
        result["change_value"] = result["change"].get("absolute")
        result["change_pct"] = result["change"].get("pct")
        result["direction"] = result["change"].get("direction", "no change")
    
    return result


def _trend_analysis(
    parsed: ParsedQuery,
    accessor: FinancialDataAccessor,
) -> Dict[str, Any]:
    """Return time-series values for the metric across all available periods."""
    try:
        data = accessor.get_time_series(
            metric_canonical_name=parsed.metric,
            company_legal_name=parsed.company,
        )
    except ValueError as e:
        return {
            "type": "error",
            "message": str(e),
        }
    
    return {
        "type": "trend",
        "metric": parsed.metric,
        "company": parsed.company,
        "data": data,
    }


def _segment_breakdown(
    parsed: ParsedQuery,
    accessor: FinancialDataAccessor,
) -> Dict[str, Any]:
    """
    For real financial data, this returns data for all companies in a period.
    (Note: Real financial data doesn't have "segments" like test data did)
    """
    try:
        companies = accessor.get_available_companies()
    except Exception as e:
        return {
            "type": "error",
            "message": f"Cannot fetch companies: {str(e)}",
        }
    
    data = []
    for company in companies:
        try:
            value = accessor.get_metric_value(
                metric_canonical_name=parsed.metric,
                company_legal_name=company,
                period_q_fiscal_year=parsed.period,
            )
            if value is not None:
                data.append({"company": company, "value": round(value, 2)})
        except ValueError:
            # Skip companies that don't have this metric
            pass
    
    total = sum(d["value"] for d in data) or 1
    for d in data:
        d["share_pct"] = round(d["value"] / total * 100, 1)
    
    return {
        "type": "segment_breakdown",
        "metric": parsed.metric,
        "period": parsed.period,
        "data": data,
    }
