"""
Graph Builder

Loads all MetricRelationship rows from the DB and constructs an in-memory
NetworkX directed graph.

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


def build_graph(db: Session) -> nx.DiGraph:
    """
    Return a fully populated directed graph from the current DB state.
    Direction: source → target  (source influences / is needed by target).
    """
    G = nx.DiGraph()

    # Add nodes
    for m in db.query(Metric).all():
        G.add_node(m.name, **{
            "display_name": m.display_name,
            "unit": m.unit or "",
            "category": m.category or "",
            "is_base": m.is_base,
            "formula_inputs": m.formula_inputs or [],
            "description": m.description or "",
        })

    # Add edges
    for r in db.query(MetricRelationship).all():
        G.add_edge(r.source_metric, r.target_metric, **{
            "relationship_type": r.relationship_type,
            "direction": r.direction,
            "strength": r.strength,
            "explanation": r.explanation or "",
        })

    return G


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
