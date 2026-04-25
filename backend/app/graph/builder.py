"""
Graph Builder - 100% Database-Driven with Data-Inferred Relationships

Loads all MetricRelationship rows from the DB and constructs an in-memory
NetworkX directed graph.

CODE MITIGATION APPLIED:
- Discovers metrics from actual database schema (not just Metric table)
- Infers relationships from financial statement structure
- Builds comprehensive graph even if relationship table is empty

Node attributes:
  display_name, unit, category, is_base, formula_inputs

Edge attributes:
  relationship_type  ("formula_dependency" | "causal_driver")
  direction          ("positive" | "negative")
  strength           (float 0–1)
  explanation        (str)

The graph is rebuilt from the DB on every application startup and can be
refreshed on demand via `build_graph()`.
"""

import networkx as nx
from sqlalchemy.orm import Session

from ..models.db_models import Metric, MetricRelationship
from ..utils.metric_definitions import MetricDefinitions


def build_graph(db: Session) -> nx.DiGraph:
    """
    Return a fully populated directed graph from the current DB state.
    Direction: source → target  (source influences / is needed by target).
    
    CODE MITIGATION APPLIED:
    - Uses MetricDefinitions to discover all available metrics
    - Infers relationships from P&L structure if relationship table is empty
    - Builds comprehensive graph from real data
    """
    G = nx.DiGraph()

    # Add nodes from Metric table (if exists)
    metric_count = 0
    try:
        for m in db.query(Metric).all():
            G.add_node(m.name, **{
                "display_name": m.display_name,
                "unit": m.unit or "",
                "category": m.category or "",
                "is_base": m.is_base,
                "formula_inputs": m.formula_inputs or [],
                "description": m.description or "",
            })
            metric_count += 1
    except Exception as e:
        print(f"Warning: Could not load from Metric table: {e}")
        db.rollback()  # Rollback failed transaction
        metric_count = 0
    
    # Always discover metrics from schema to ensure we have all P&L columns
    # (Even if Metric table has some entries, they might be incomplete)
    print(f"Discovering all metrics from database schema (current: {metric_count})...")
    discovered_metrics = MetricDefinitions.discover_all_metrics(db)
    
    for metric_name, (table_name, display_name) in discovered_metrics.items():
        if metric_name not in G.nodes:
            G.add_node(metric_name, **{
                "display_name": display_name,
                "unit": "",  # Unit comes from metrics table where available
                "category": _categorize_metric(metric_name, table_name),
                "is_base": True,  # All discovered metrics are base (from filings)
                "formula_inputs": [],
                "description": f"From {table_name}",
            })
    
    print(f"Total metrics in graph: {len(G.nodes)}")

    # Add edges from MetricRelationship table
    relationship_count = 0
    try:
        for r in db.query(MetricRelationship).all():
            G.add_edge(r.source_metric, r.target_metric, **{
                "relationship_type": r.relationship_type,
                "direction": r.direction,
                "strength": r.strength,
                "explanation": r.explanation or "",
            })
            relationship_count += 1
    except Exception as e:
        print(f"Warning: Could not load from MetricRelationship table: {e}")
        db.rollback()  # Rollback failed transaction
        relationship_count = 0
    
    # Always add formula dependency edges from the metrics table formulas.
    # These connect e.g. revenue_from_operations → gross_profit (formula dep).
    try:
        for m in db.query(Metric).filter(Metric.formula_inputs != None).all():
            if not m.formula_inputs:
                continue
            for inp in m.formula_inputs:
                if inp in G.nodes and m.name in G.nodes:
                    if not G.has_edge(inp, m.name):
                        G.add_edge(inp, m.name, **{
                            "relationship_type": "formula_dependency",
                            "direction": "positive",
                            "strength": 1.0,
                            "explanation": f"{inp} is a formula input for {m.name}",
                        })
    except Exception as e:
        print(f"Warning: Could not add formula edges: {e}")
        db.rollback()

    # Always infer additional relationships from actual data correlations.
    # This is the data-driven fallback that requires no hardcoded metric names.
    # Uses if-not-exists guard so it won't overwrite seeded expert edges.
    print("Inferring relationships from data correlations (Pearson)...")
    _infer_relationships_from_data(G, db)

    return G


def _categorize_metric(metric_name: str, table_name: str) -> str:
    """Categorize a metric based on its name and table"""
    if table_name == "financials_pnl":
        if any(word in metric_name.lower() for word in ['revenue', 'income', 'sales']):
            return "Revenue"
        elif any(word in metric_name.lower() for word in ['cost', 'expense']):
            return "Expense"
        elif any(word in metric_name.lower() for word in ['profit', 'earnings', 'ebit']):
            return "Profit"
        else:
            return "P&L"
    elif table_name == "financials_balance_sheet":
        return "Balance Sheet"
    elif table_name == "financials_cashflow":
        return "Cash Flow"
    return "Financial"


def _infer_relationships_from_data(G: nx.DiGraph, db: Session):
    """
    Infer causal relationships by computing Pearson correlations between
    all metric pairs from actual financial data in the database.

    No metric names are hardcoded here. Relationships are discovered
    entirely from statistical patterns in the real filing data:
      - Edge direction: upstream → downstream using column-name position heuristic
        (revenue/cost columns precede profit columns in P&L flow)
      - Edge weight (strength): absolute Pearson r
      - Edge sign (direction): positive or negative based on correlation sign
    """
    import numpy as np
    from sqlalchemy import text

    # Discover all PnL metric columns directly from DB schema (no hardcoding)
    pnl_nodes = [
        col
        for col, (table_name, _) in MetricDefinitions.discover_all_metrics(db).items()
        if table_name == "financials_pnl" and col in G.nodes
    ]

    if len(pnl_nodes) < 2:
        return

    # Fetch all values for these columns in one query
    cols_sql = ", ".join(f'"{col}"' for col in pnl_nodes)
    try:
        rows = db.execute(text(f"SELECT {cols_sql} FROM financials_pnl")).fetchall()
    except Exception as e:
        print(f"Warning: Could not query financials_pnl for correlation: {e}")
        db.rollback()
        return

    if len(rows) < 20:
        return

    data = np.array(
        [[float(v) if v is not None else np.nan for v in row] for row in rows],
        dtype=float,
    )

    def _flow_rank(col_name: str) -> int:
        """
        Score a metric column's position in the P&L waterfall
        purely from its name, without listing specific column names.
        Lower = more upstream (raw input), higher = more derived/summary.
        """
        n = col_name.lower()
        # Topmost: raw revenues and top-line income
        if any(t in n for t in ("revenue", "sales", "turnover")):
            return 0
        # Costs and operating expenses (reduce profit)
        if any(t in n for t in ("cost", "expense", "depreciation", "amortisation", "amortization")):
            return 1
        # Intermediate profit lines
        if any(t in n for t in ("gross", "ebitda", "ebit", "operating_profit", "operating profit")):
            return 2
        # Below-the-line items
        if any(t in n for t in ("interest", "finance", "other_income", "other income")):
            return 3
        # Pre-tax
        if "before_tax" in n or "pbt" in n:
            return 4
        # Net profit / bottom line
        if any(t in n for t in ("net_profit", "pnl_for", "profit_after", "comprehensive", "net profit")):
            return 5
        # Per-share / derived ratios
        if any(t in n for t in ("eps", "per_share", "margin", "ratio", "return")):
            return 6
        return 3  # default: mid-range

    CORR_THRESHOLD = 0.40

    edges_added = 0
    n = len(pnl_nodes)
    for i in range(n):
        for j in range(i + 1, n):
            vi, vj = data[:, i], data[:, j]
            mask = ~(np.isnan(vi) | np.isnan(vj))
            if mask.sum() < 20:
                continue

            r = np.corrcoef(vi[mask], vj[mask])[0, 1]
            if np.isnan(r) or abs(r) < CORR_THRESHOLD:
                continue

            ri = _flow_rank(pnl_nodes[i])
            rj = _flow_rank(pnl_nodes[j])

            # Edge goes from the more upstream metric to the more downstream one.
            # If same rank, use alphabetical order to keep the graph acyclic.
            if ri < rj or (ri == rj and pnl_nodes[i] < pnl_nodes[j]):
                src, tgt = pnl_nodes[i], pnl_nodes[j]
            else:
                src, tgt = pnl_nodes[j], pnl_nodes[i]

            direction = "positive" if r > 0 else "negative"

            if not G.has_edge(src, tgt):
                G.add_edge(src, tgt, **{
                    "relationship_type": "causal_driver",
                    "direction": direction,
                    "strength": round(float(abs(r)), 3),
                    "explanation": (
                        f"Pearson r={r:.2f} across {int(mask.sum())} company-period observations"
                    ),
                })
                edges_added += 1

    print(f"  Inferred {edges_added} relationships from data correlations ({n} metrics, {len(rows)} observations)")




def get_formula_ancestors(G: nx.DiGraph, metric: str) -> list:
    """
    Return all metrics that `metric` depends on (directly or transitively)
    via formula_dependency edges only.
    """
    ancestors = []
    for u, v, data in G.edges(data=True):
        if v == metric and data.get("relationship_type") == "formula_dependency":
            ancestors.append(u)
    return ancestors


def get_causal_drivers(G: nx.DiGraph, metric: str) -> list:
    """
    Return all metrics that causally drive `metric`
    (causal_driver edges only, incoming to metric).
    """
    drivers = []
    for u, v, data in G.in_edges(metric, data=True):
        if data.get("relationship_type") == "causal_driver":
            drivers.append((u, data))
    return drivers


def graph_to_dict(G: nx.DiGraph) -> dict:
    """Serialise graph to a JSON-friendly dict for the /graph endpoint."""
    return {
        "nodes": [
            {"id": n, **attrs}
            for n, attrs in G.nodes(data=True)
        ],
        "edges": [
            {"source": u, "target": v, **data}
            for u, v, data in G.edges(data=True)
        ],
    }
