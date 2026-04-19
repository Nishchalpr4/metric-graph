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
from ..metrics.engine import attribute_contributions, get_metric_values_for_period
from ..models.db_models import CausalEvent

log = logging.getLogger(__name__)

# Minimum % change (absolute) to consider a contributor "significant"
_SIG_PCT = 1.0
_MAX_DEPTH = 3


# ─────────────────────────────────────────────────────────────────────────────
# Public entry-point
# ─────────────────────────────────────────────────────────────────────────────

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
    # Load ALL metric values for both periods in one pass
    all_curr = _load_all(db, period, segment)
    all_prev = _load_all(db, compare_period, segment)

    if not all_curr or not all_prev:
        return _error(f"No data found for {segment} in {period} or {compare_period}.")

    curr_val = all_curr.get(metric_name)
    prev_val = all_prev.get(metric_name)

    if curr_val is None or prev_val is None:
        return _error(
            f"Metric '{metric_name}' has no data for {segment} "
            f"in {period} or {compare_period}."
        )

    total_change = curr_val - prev_val
    pct_change = (total_change / abs(prev_val) * 100) if prev_val else 0.0
    direction = "increased" if total_change >= 0 else "decreased"

    metrics_registry = METRIC_REGISTRY()
    meta = metrics_registry.get(metric_name, {})

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
    }


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_all(db: Session, period: str, segment: str) -> Dict[str, float]:
    """Load all metric values for a (period, segment) from DB."""
    return get_metric_values_for_period(db, period, segment)


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
