"""
Inference Engine — the analytical brain of the system.

Given a target metric, a current period, and a comparison period, it:

  1. Detects the change (absolute + %).
  2. Decomposes the change into formula-input contributions (mathematical layer).
  3. For each significant contributing input, recurses one level deeper.
  4. For each changed metric it also gathers causal drivers (business layer).
  5. Enriches each period with known causal events.
  6. Returns a fully structured result dict ready for the API / frontend.

Multi-step inference example
─────────────────────────────
Query : "Why did Revenue increase in Q3 2023?"
Step 1 : Revenue ↑ ₹2.14B (+43.8%)
Step 2 : Decompose  → GMV contrib (+₹1.91B), Commission Rate (+₹0.48B),
                       Delivery Charges (+₹0.25B), Discounts (-₹0.50B)
Step 3 : Drill GMV  → Orders contrib (+₹5.65B equivalent), AOV contrib (+₹2.17B)
Step 4 : Drill Orders → causal: Active Users ↑, Marketing Spend ↑, Discounts ↑
Step 5 : Drill AOV    → causal: Basket Size ↑, Pricing Index ↑, Restaurant Partners ↑
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
from sqlalchemy.orm import Session

from ..metrics.registry import METRIC_REGISTRY
from ..metrics.engine import attribute_contributions
from ..models.db_models import CausalEvent
from ..data.financial_accessor import FinancialDataAccessor

log = logging.getLogger(__name__)

# Minimum % change (absolute) to consider a contributor "significant"
_SIG_PCT = 1.0
_MAX_DEPTH = 3


# ─────────────────────────────────────────────────────────────────────────────
# Public entry-point
# ─────────────────────────────────────────────────────────────────────────────

def _display_to_column(metric_name: str, db: Session) -> str:
    """
    Convert display name like 'Operating Profit' to column name 'operating_profit'.
    Tries: exact match, snake_case conversion, MetricDefinitions lookup.
    """
    from ..utils.metric_definitions import MetricDefinitions
    # Try exact match first
    all_metrics = MetricDefinitions.discover_all_metrics(db)
    if metric_name in all_metrics:
        return metric_name
    # Try snake_case conversion: 'Operating Profit' -> 'operating_profit'
    snake = metric_name.lower().replace(' ', '_').replace('/', '_').replace('-', '_')
    if snake in all_metrics:
        return snake
    # Known display name overrides (cases where snake_case doesn't match column name)
    _DISPLAY_MAP = {
        "net profit": "pnl_for_period",
        "profit": "pnl_for_period",
        "revenue": "revenue_from_operations",
        "ebitda": "operating_profit",
    }
    lower = metric_name.lower()
    if lower in _DISPLAY_MAP and _DISPLAY_MAP[lower] in all_metrics:
        return _DISPLAY_MAP[lower]
    # Return original as fallback
    return metric_name


def analyse(
    *,
    metric_name: str,
    period: str,
    compare_period: str,
    segment: str,
    db: Session,
    graph: nx.DiGraph,
) -> Dict[str, Any]:
    """
    Top-level inference call.  Returns a structured explanation dict.
    """
    # Normalize metric name from display name to column name
    metric_key = _display_to_column(metric_name, db)
    # Load ALL metric values for both periods in one pass
    all_curr = _load_all(db, period, segment)
    all_prev = _load_all(db, compare_period, segment)

    if not all_curr or not all_prev:
        # Provide helpful error message with available data
        from ..models.db_models import FinancialsFiling, FinancialsPeriod, CanonicalCompany
        from sqlalchemy import func, distinct
        
        # Check if company exists
        company = db.query(CanonicalCompany).filter(
            CanonicalCompany.official_legal_name == segment
        ).first()
        
        if not company:
            return _error(f"Company '{segment}' not found in database.")
        
        # Check what periods exist for this company
        company_periods = db.query(distinct(FinancialsPeriod.period_id)).join(
            FinancialsFiling, FinancialsFiling.period_id == FinancialsPeriod.period_id
        ).filter(
            FinancialsFiling.company_id == company.company_id
        ).all()
        
        available = []
        for (pid,) in company_periods:
            p = db.query(FinancialsPeriod).filter(FinancialsPeriod.period_id == pid).first()
            if p:
                available.append(f"{p.quarter} {p.fiscal_year}")
        
        available_str = ", ".join(sorted(set(available))[:10])
        if len(set(available)) > 10:
            available_str += f", ... and {len(set(available)) - 10} more"
        
        error_msg = (
            f"No data for '{metric_name}' in {segment} for periods: {period} or {compare_period}. "
            f"Available periods: {available_str}"
        )
        return _error(error_msg)

    curr_val = all_curr.get(metric_key)
    prev_val = all_prev.get(metric_key)

    if curr_val is None or prev_val is None:
        return _error(
            f"Metric '{metric_name}' has no data for {segment} "
            f"in {period} or {compare_period}."
        )

    total_change = curr_val - prev_val
    pct_change = (total_change / abs(prev_val) * 100) if prev_val else 0.0
    direction = "increased" if total_change >= 0 else "decreased"

    metrics_registry = METRIC_REGISTRY()
    meta = metrics_registry.get(metric_key, metrics_registry.get(metric_name, {}))

    # Recursive decomposition
    drivers = _decompose(
        metric_name=metric_name,
        period=period,
        compare_period=compare_period,
        segment=segment,
        all_curr=all_curr,
        all_prev=all_prev,
        graph=graph,
        db=db,
        depth=0,
        parent_total_change=total_change,
    )

    # Events for this period
    events = _get_events(db, period, segment)

    # Human-readable summary
    summary = _make_summary(
        metric_name, meta.get("display_name", metric_name),
        meta.get("unit", ""),
        period, compare_period,
        curr_val, prev_val, total_change, pct_change, direction,
        drivers, events,
    )

    # Collect all metrics used in this analysis (for graph highlighting)
    metrics_used = _collect_metrics_from_drivers(metric_name, drivers)

    return {
        "query_meta": {
            "metric": metric_name,
            "display_name": meta.get("display_name", metric_name),
            "unit": meta.get("unit", ""),
            "period": period,
            "compare_period": compare_period,
            "segment": segment,
        },
        "change": {
            "current_value": round(curr_val, 4),
            "prev_value": round(prev_val, 4),
            "absolute": round(total_change, 4),
            "pct": round(pct_change, 2),
            "direction": direction,
        },
        "drivers": drivers,
        "period_events": events,
        "summary": summary,
        "metrics_used": metrics_used,  # For graph highlighting
    }


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_all(db: Session, period: str, segment: str) -> Dict[str, float]:
    """
    Load all metric values for a (period, segment) from REAL financial data.
    
    Uses FinancialDataAccessor to query from financials_pnl/balance_sheet/cashflow
    instead of the broken time_series_data table.
    
    Args:
        db: Database session
        period: Period in format "Q1 2024", "Q2 FY2023", etc.
        segment: Company legal name (used as segment identifier)
    
    Returns:
        Dict mapping metric_canonical_name -> value
    """
    accessor = FinancialDataAccessor(db)
    result = {}
    
    # Get ALL available metrics from database schema (not just registry subset)
    from ..utils.metric_definitions import MetricDefinitions
    all_discovered = MetricDefinitions.discover_all_metrics(db)
    
    # Also include METRIC_REGISTRY metrics (computed/derived ones)
    metrics_registry = METRIC_REGISTRY()
    
    # Merge: discovered DB columns + registry derived metrics
    combined_metrics = {**{k: {} for k in all_discovered.keys()}, **metrics_registry}
    
    if not combined_metrics:
        log.error(f"No metrics available - cannot load data")
        return result
    
    log.debug(f"Loading {len(combined_metrics)} metrics for {segment} in {period}")
    
    # Try to load each metric
    failed_metrics = []
    for metric_name, meta in combined_metrics.items():
        try:
            value = accessor.get_metric_value(
                metric_canonical_name=metric_name,
                company_legal_name=segment,
                period_q_fiscal_year=period,
            )
            if value is not None:
                result[metric_name] = value
                log.debug(f"  ✓ {metric_name} = {value}")
            else:
                log.debug(f"  ✗ {metric_name} = None (no value for this period/company)")
                failed_metrics.append(metric_name)
        except Exception as e:
            log.debug(f"  ✗ {metric_name} failed: {type(e).__name__}: {e}")
            failed_metrics.append(metric_name)
    
    if not result:
        log.warning(f"No metrics loaded for {segment} in {period}. Checked {len(failed_metrics)} metrics, all failed.")
        log.warning(f"First 5 failed metrics: {failed_metrics[:5]}")
        return result

    # Compute derived metrics (e.g. gross_profit = revenue - COGS) that are not
    # stored as direct columns in the DB but are needed for driver decomposition.
    # compute_all_metrics only fills in values that are NOT already loaded from DB.
    from ..metrics.engine import compute_all_metrics
    result = compute_all_metrics(result)
    log.debug(f"After compute_all_metrics: {len(result)} metrics total for {segment} in {period}")

    return result


def _decompose(
    *,
    metric_name: str,
    period: str,
    compare_period: str,
    segment: str,
    all_curr: Dict[str, float],
    all_prev: Dict[str, float],
    graph: nx.DiGraph,
    db: Session,
    depth: int,
    parent_total_change: float,
) -> List[Dict[str, Any]]:
    """
    Recursively decompose the change in `metric_name` into ranked drivers.
    Returns a list of driver dicts sorted by |contribution| descending.
    """
    if depth >= _MAX_DEPTH:
        return []

    metrics_registry = METRIC_REGISTRY()
    meta = metrics_registry.get(metric_name, {})
    formula_inputs: List[str] = meta.get("formula_inputs") or []
    drivers: List[Dict[str, Any]] = []

    # ── Layer 1: Mathematical formula decomposition ───────────────────────────
    if formula_inputs:
        contributions, total = attribute_contributions(
            metric_name,
            {k: all_prev.get(k, 0.0) for k in formula_inputs},
            {k: all_curr.get(k, 0.0) for k in formula_inputs},
        )

        for inp, contrib in contributions.items():
            inp_curr = all_curr.get(inp)
            inp_prev = all_prev.get(inp)
            if inp_curr is None or inp_prev is None:
                continue

            inp_change = inp_curr - inp_prev
            inp_pct = (inp_change / abs(inp_prev) * 100) if inp_prev else 0.0
            contrib_pct = (contrib / abs(parent_total_change) * 100) if parent_total_change else 0.0

            metrics_registry = METRIC_REGISTRY()
            inp_meta = metrics_registry.get(inp, {})
            edge_data = graph.get_edge_data(inp, metric_name) or {}

            driver = {
                "metric": inp,
                "display_name": inp_meta.get("display_name", inp),
                "unit": inp_meta.get("unit", ""),
                "relationship_type": "formula_dependency",
                "direction": edge_data.get("direction", "positive"),
                "contribution": round(contrib, 6),
                "contribution_pct": round(contrib_pct, 2),
                "current_value": round(inp_curr, 4),
                "prev_value": round(inp_prev, 4),
                "change": round(inp_change, 4),
                "change_pct": round(inp_pct, 2),
                "explanation": edge_data.get("explanation", ""),
                "sub_drivers": [],
            }

            # Recurse if the input itself changed meaningfully
            if abs(inp_pct) >= _SIG_PCT and depth + 1 < _MAX_DEPTH:
                driver["sub_drivers"] = _decompose(
                    metric_name=inp,
                    period=period,
                    compare_period=compare_period,
                    segment=segment,
                    all_curr=all_curr,
                    all_prev=all_prev,
                    graph=graph,
                    db=db,
                    depth=depth + 1,
                    parent_total_change=inp_change,
                )

            drivers.append(driver)

    # ── Layer 2: causal drivers from the graph (business layer) ──────────────
    # Only attach causal context at the top 2 levels to avoid noise
    if depth <= 1 and graph.has_node(metric_name):
        for u, _v, edge_data in graph.in_edges(metric_name, data=True):
            if edge_data.get("relationship_type") != "causal_driver":
                continue
            # Skip if already covered by formula decomposition
            if u in {d["metric"] for d in drivers}:
                continue

            u_curr = all_curr.get(u)
            u_prev = all_prev.get(u)
            if u_curr is None or u_prev is None:
                continue

            u_change = u_curr - u_prev
            u_pct = (u_change / abs(u_prev) * 100) if u_prev else 0.0

            if abs(u_pct) < _SIG_PCT:
                continue   # didn't change enough to matter

            metrics_registry = METRIC_REGISTRY()
            u_meta = metrics_registry.get(u, {})
            drivers.append({
                "metric": u,
                "display_name": u_meta.get("display_name", u),
                "unit": u_meta.get("unit", ""),
                "relationship_type": "causal_driver",
                "direction": edge_data.get("direction", "positive"),
                "strength": edge_data.get("strength", 0.5),
                "contribution": None,      # qualitative; no formula attribution
                "contribution_pct": None,
                "current_value": round(u_curr, 4),
                "prev_value": round(u_prev, 4),
                "change": round(u_change, 4),
                "change_pct": round(u_pct, 2),
                "explanation": edge_data.get("explanation", ""),
                "sub_drivers": [],
            })

    # Sort: formula deps by |contribution| desc, causal drivers by |change_pct| desc
    formula_drivers = sorted(
        [d for d in drivers if d["relationship_type"] == "formula_dependency"],
        key=lambda d: abs(d["contribution"] or 0),
        reverse=True,
    )
    causal_drivers = sorted(
        [d for d in drivers if d["relationship_type"] == "causal_driver"],
        key=lambda d: abs(d["change_pct"] or 0),
        reverse=True,
    )
    return formula_drivers + causal_drivers


def _collect_metrics_from_drivers(root_metric: str, drivers: List[Dict[str, Any]]) -> List[str]:
    """
    Recursively collect all metric names appearing in the driver breakdown.
    Used to highlight relevant nodes in the graph visualization.
    """
    metrics = {root_metric}
    
    def _collect_recursive(driver_list):
        for driver in driver_list:
            metrics.add(driver["metric"])
            if driver.get("sub_drivers"):
                _collect_recursive(driver["sub_drivers"])
    
    _collect_recursive(drivers)
    return sorted(list(metrics))


def _get_events(db: Session, period: str, segment: str) -> List[Dict[str, Any]]:
    """Fetch causal events for this period (matching segment or 'Overall')."""
    rows = (
        db.query(CausalEvent)
        .filter(
            CausalEvent.period == period,
            CausalEvent.segment.in_([segment, "Overall"]),
        )
        .all()
    )
    return [
        {
            "event_name": r.event_name,
            "affected_metrics": r.affected_metrics or [],
            "direction": r.direction,
            "magnitude": r.magnitude,
            "explanation": r.explanation,
        }
        for r in rows
    ]


def _make_summary(
    metric_name: str,
    display_name: str,
    unit: str,
    period: str,
    compare_period: str,
    curr_val: float,
    prev_val: float,
    total_change: float,
    pct_change: float,
    direction: str,
    drivers: List[Dict],
    events: List[Dict],
) -> str:
    """Generate a concise analyst-style narrative summary."""
    unit_str = f" {unit}" if unit else ""
    lines = [
        f"{display_name} {direction} by {abs(pct_change):.1f}% "
        f"({_fmt(prev_val, unit)} → {_fmt(curr_val, unit)}) "
        f"in {period} vs {compare_period}.",
    ]

    top_formula = [d for d in drivers if d["relationship_type"] == "formula_dependency"][:3]
    if top_formula:
        parts = []
        for d in top_formula:
            sign = "+" if d["contribution"] >= 0 else ""
            parts.append(
                f"{d['display_name']} ({sign}{_fmt(d['contribution'], d['unit'])} / "
                f"{sign}{d['contribution_pct']:.1f}%)"
            )
        lines.append("Key formula drivers: " + ", ".join(parts) + ".")

    top_causal = [d for d in drivers if d["relationship_type"] == "causal_driver"][:3]
    if top_causal:
        parts = [
            f"{d['display_name']} {'↑' if d['change'] >= 0 else '↓'} "
            f"{abs(d['change_pct']):.1f}%"
            for d in top_causal
        ]
        lines.append("Causal business drivers: " + ", ".join(parts) + ".")

    if events:
        ev_names = ", ".join(f'"{e["event_name"]}"' for e in events[:3])
        lines.append(f"Business context: {ev_names}.")

    return "  ".join(lines)


def _fmt(value: Optional[float], unit: str) -> str:
    if value is None:
        return "N/A"
    if unit in ("₹B",):
        return f"₹{value:.2f}B"
    if unit in ("₹",):
        return f"₹{value:.0f}"
    if unit == "%":
        return f"{value:.2f}%"
    if unit == "M":
        return f"{value:.1f}M"
    if unit == "K":
        return f"{value:.0f}K"
    return f"{value:.2f}"


def _error(msg: str) -> Dict[str, Any]:
    return {"error": msg, "drivers": [], "period_events": [], "summary": msg}
