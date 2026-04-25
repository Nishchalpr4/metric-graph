"""
Verify: Graph edges - are they from DB or hardcoded defaults?
"""
import sys
sys.path.insert(0, '/path/to/backend')

from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.DEBUG)

# Import the graph builder
from app.database import SessionLocal
from app.graph.builder import build_graph

db = SessionLocal()

print("=" * 100)
print("GRAPH CONSTRUCTION AUDIT")
print("=" * 100)

# Build the graph
G = build_graph(db)

print(f"\n1. GRAPH SIZE")
print(f"   Nodes: {len(G.nodes())}")
print(f"   Edges: {len(G.edges())}")

# Show edge types
print(f"\n2. EDGE TYPES")
formula_edges = [e for e in G.edges(data=True) if e[2].get('relationship_type') == 'formula_dependency']
causal_edges = [e for e in G.edges(data=True) if e[2].get('relationship_type') == 'causal_driver']
print(f"   Formula dependency edges: {len(formula_edges)}")
print(f"   Causal driver edges: {len(causal_edges)}")

# Check for critical formula edges
print(f"\n3. CRITICAL FORMULA EDGES (for decomposition)")
critical_edges = [
    ('revenue_from_operations', 'gross_profit'),
    ('cost_of_material', 'gross_profit'),
    ('gross_profit', 'operating_profit'),
    ('operating_profit', 'profit_before_tax'),
]
for source, target in critical_edges:
    has_edge = G.has_edge(source, target)
    if has_edge:
        edge_data = G.get_edge_data(source, target)
        print(f"   ✓ {source} → {target} ({edge_data.get('relationship_type', 'unknown')})")
    else:
        print(f"   ✗ {source} → {target} **MISSING**")

# Show sample edges
print(f"\n4. SAMPLE FORMULA EDGES FROM DB")
for s, t, data in formula_edges[:10]:
    print(f"   {s} → {t} ({data['direction']})")

# Check if edges came from metrics.formula_inputs
print(f"\n5. EDGE SOURCES")
print(f"   From metric_relationships table: {len([e for e in G.edges(data=True) if e[2].get('_source') == 'db'])}")
print(f"   From inferred P&L structure: {len([e for e in G.edges(data=True) if e[2].get('_source') == 'inferred'])}")

# Verify operating_profit formula
if G.has_node('operating_profit'):
    import_nodes = list(G.predecessors('operating_profit'))
    print(f"\n6. OPERATING_PROFIT FORMULA INPUTS")
    print(f"   Incoming edges to operating_profit: {import_nodes}")

db.close()

print("\n" + "=" * 100)
print("VERDICT:")
print("=" * 100)
if len(formula_edges) > 20 and all(G.has_edge(s, t) for s, t in critical_edges):
    print("✓ GRAPH IS PROPERLY CONSTRUCTED FROM DATABASE")
    print(f"  - Has {len(critical_edges)} critical formula edges for decomposition")
    print(f"  - Has {len(formula_edges)} total formula dependency edges")
else:
    print("✗ GRAPH MAY BE INCOMPLETE OR NOT USING DB")
