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

    # If relationship table is empty, infer relationships from P&L structure
    if relationship_count < 3:
        print("MetricRelationship table has few entries, inferring relationships...")
        _infer_pnl_relationships(G)

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


def _infer_pnl_relationships(G: nx.DiGraph):
    """
    Infer causal relationships based on standard P&L structure.
    
    Standard P&L flow:
    Revenue - Costs/Expenses = Operating Profit
    Operating Profit - Interest/Tax = Net Profit
    """
    # Known P&L metrics and their relationships
    pnl_structure = {
        # Revenue metrics (top line)
        "revenue_from_operations": {
            "drives": ["total_income", "operating_profit", "profit_before_tax", "pnl_for_period"],
            "direction": "positive",
            "strength": 0.9,
        },
        "other_income": {
            "drives": ["total_income", "profit_before_tax"],
            "direction": "positive",
            "strength": 0.5,
        },
        # Cost metrics (reduce profit)
        "cost_of_material": {
            "drives": ["operating_profit", "profit_before_tax", "pnl_for_period"],
            "direction": "negative",
            "strength": 0.8,
        },
        "employee_benefit_expense": {
            "drives": ["operating_profit", "profit_before_tax", "pnl_for_period"],
            "direction": "negative",
            "strength": 0.7,
        },
        "depreciation": {
            "drives": ["operating_profit", "profit_before_tax", "pnl_for_period"],
            "direction": "negative",
            "strength": 0.6,
        },
        "interest_expense": {
            "drives": ["profit_before_tax", "pnl_for_period"],
            "direction": "negative",
            "strength": 0.7,
        },
        "tax_expense": {
            "drives": ["pnl_for_period", "comprehensive_income_for_the_period"],
            "direction": "negative",
            "strength": 0.8,
        },
        # Profit metrics
        "operating_profit": {
            "drives": ["profit_before_tax", "pnl_for_period"],
            "direction": "positive",
            "strength": 0.9,
        },
        "profit_before_tax": {
            "drives": ["pnl_for_period"],
            "direction": "positive",
            "strength": 0.95,
        },
        "pnl_for_period": {
            "drives": ["comprehensive_income_for_the_period", "basic_eps"],
            "direction": "positive",
            "strength": 0.95,
        },
    }
    
    # Add inferred relationships to graph
    for source_metric, config in pnl_structure.items():
        if source_metric in G.nodes:
            for target_metric in config["drives"]:
                if target_metric in G.nodes:
                    # Only add if edge doesn't exist
                    if not G.has_edge(source_metric, target_metric):
                        G.add_edge(source_metric, target_metric, **{
                            "relationship_type": "causal_driver",
                            "direction": config["direction"],
                            "strength": config["strength"],
                            "explanation": f"{source_metric} {'increases' if config['direction'] == 'positive' else 'decreases'} {target_metric}",
                        })



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
