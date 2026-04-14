"""
Query Handler

Orchestrates the full pipeline:
  parse NL query → validate → run inference → log → return result
"""

import logging
from typing import Any, Dict, List

import networkx as nx
from sqlalchemy.orm import Session

from .parser import parse_query, ParsedQuery
from ..graph.inference import analyse
from ..metrics.registry import METRIC_REGISTRY, ALL_PERIODS
from ..models.db_models import QueryLog, TimeSeriesData

log = logging.getLogger(__name__)


def handle_query(
    raw_query: str,
    db: Session,
    graph: nx.DiGraph,
) -> Dict[str, Any]:
    """
    Main entry-point called from the API layer.
    Returns the complete analysis result dict.
    """
    parsed = parse_query(raw_query)
    log.info("Parsed query: metric=%s period=%s vs %s segment=%s",
             parsed.metric, parsed.period, parsed.compare_period, parsed.segment)

    result = _dispatch(parsed, db, graph)

    # Persist query log (best-effort; don't fail on log error)
    try:
        db.add(QueryLog(
            query_text=raw_query,
            parsed_metric=parsed.metric,
            parsed_period=parsed.period,
            parsed_compare_period=parsed.compare_period,
            parsed_segment=parsed.segment,
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
            "segment": parsed.segment,
            "intent": parsed.intent,
        },
        "warnings": parsed.warnings,
        "result": result,
    }


# ─────────────────────────────────────────────────────────────────────────────

def _dispatch(parsed: ParsedQuery, db: Session, graph: nx.DiGraph) -> Dict[str, Any]:
    if parsed.intent == "trend":
        return _trend_analysis(parsed, db)
    if parsed.intent == "segment_breakdown":
        return _segment_breakdown(parsed, db)
    # Default: explain_change
    return analyse(
        metric_name=parsed.metric,
        period=parsed.period,
        compare_period=parsed.compare_period,
        segment=parsed.segment,
        db=db,
        graph=graph,
    )


def _trend_analysis(parsed: ParsedQuery, db: Session) -> Dict[str, Any]:
    """Return time-series values for the metric across all available periods."""
    rows = (
        db.query(TimeSeriesData)
        .filter(
            TimeSeriesData.metric_name == parsed.metric,
            TimeSeriesData.segment == parsed.segment,
        )
        .order_by(TimeSeriesData.period)
        .all()
    )
    # Sort by ALL_PERIODS order
    period_order = {p: i for i, p in enumerate(ALL_PERIODS)}
    sorted_rows = sorted(rows, key=lambda r: period_order.get(r.period, 999))
    meta = METRIC_REGISTRY.get(parsed.metric, {})
    return {
        "type": "trend",
        "metric": parsed.metric,
        "display_name": meta.get("display_name", parsed.metric),
        "unit": meta.get("unit", ""),
        "segment": parsed.segment,
        "data": [
            {"period": r.period, "value": round(r.value, 4)}
            for r in sorted_rows
        ],
    }


def _segment_breakdown(parsed: ParsedQuery, db: Session) -> Dict[str, Any]:
    """Compare a metric across segments for the target period."""
    segments = ["Food Delivery", "Grocery Delivery"]
    meta = METRIC_REGISTRY.get(parsed.metric, {})
    data = []
    for seg in segments:
        row = (
            db.query(TimeSeriesData)
            .filter(
                TimeSeriesData.metric_name == parsed.metric,
                TimeSeriesData.period == parsed.period,
                TimeSeriesData.segment == seg,
            )
            .first()
        )
        if row:
            data.append({"segment": seg, "value": round(row.value, 4)})
    total = sum(d["value"] for d in data) or 1
    for d in data:
        d["share_pct"] = round(d["value"] / total * 100, 1)
    return {
        "type": "segment_breakdown",
        "metric": parsed.metric,
        "display_name": meta.get("display_name", parsed.metric),
        "unit": meta.get("unit", ""),
        "period": parsed.period,
        "data": data,
    }
