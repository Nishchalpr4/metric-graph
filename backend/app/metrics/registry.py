"""
Metric Registry — DYNAMIC LOADING from database at runtime

Architecture:
  1. SEED DATA: Hardcoded metrics below are used ONLY to seed the database (/api/seed endpoint)
  2. RUNTIME: All code loads metrics from the database via loader.py (zero hardcoding)
  3. For any company: Just change the database, no code changes needed

Import like this:
  from .registry import METRIC_REGISTRY, FORMULA_FUNCTIONS, COMPUTATION_ORDER, ALL_PERIODS
  
  These are now dynamic - they pull from loader.py which cached DB data
"""

from typing import Dict, Any, Callable, List, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# ─────────────────────────────────────────────────────────────────────────────
# SEED DATA: Used only for database initialization
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_METRICS: Dict[str, Dict[str, Any]] = {
    # ── Base / Input Metrics ──────────────────────────────────────────────────
    "orders": {
        "display_name": "Orders",
        "description": "Total orders placed on the platform in the period",
        "formula": None,
        "formula_inputs": [],
        "unit": "M",
        "category": "Operational",
        "is_base": True,
    },
    "aov": {
        "display_name": "Average Order Value (AOV)",
        "description": "Avg pre-discount order value; primary input to GMV",
        "formula": None,
        "formula_inputs": [],
        "unit": "₹",
        "category": "Financial",
        "is_base": True,
    },
    "commission_rate": {
        "display_name": "Commission Rate",
        "description": "% commission charged on GMV from restaurant/store partners",
        "formula": None,
        "formula_inputs": [],
        "unit": "%",
        "category": "Financial",
        "is_base": True,
    },
    "delivery_charges": {
        "display_name": "Delivery Revenue",
        "description": "Platform revenue from customer-paid delivery fees",
        "formula": None,
        "formula_inputs": [],
        "unit": "₹B",
        "category": "Financial",
        "is_base": True,
    },
    "discounts": {
        "display_name": "Platform Discounts",
        "description": "Total discounts funded by the platform (reduces net revenue)",
        "formula": None,
        "formula_inputs": [],
        "unit": "₹B",
        "category": "Financial",
        "is_base": True,
    },
    "marketing_spend": {
        "display_name": "Marketing Spend",
        "description": "Total marketing and user-acquisition expenditure",
        "formula": None,
        "formula_inputs": [],
        "unit": "₹B",
        "category": "Financial",
        "is_base": True,
    },
    "new_users": {
        "display_name": "New Users",
        "description": "First-time users acquired during the period",
        "formula": None,
        "formula_inputs": [],
        "unit": "M",
        "category": "User",
        "is_base": True,
    },
    "active_users": {
        "display_name": "Monthly Active Users (MAU)",
        "description": "Unique users who placed ≥1 order in the period",
        "formula": None,
        "formula_inputs": [],
        "unit": "M",
        "category": "User",
        "is_base": True,
    },
    "basket_size": {
        "display_name": "Basket Size",
        "description": "Average number of items per order",
        "formula": None,
        "formula_inputs": [],
        "unit": "items",
        "category": "Operational",
        "is_base": True,
    },
    "restaurant_partners": {
        "display_name": "Restaurant / Store Partners",
        "description": "Active merchant partners listed on the platform",
        "formula": None,
        "formula_inputs": [],
        "unit": "K",
        "category": "Operational",
        "is_base": True,
    },
    "pricing_index": {
        "display_name": "Pricing Index",
        "description": "Weighted avg price index of menu items (base = 100)",
        "formula": None,
        "formula_inputs": [],
        "unit": "index",
        "category": "Operational",
        "is_base": True,
    },
    # ── Derived / Computed Metrics ────────────────────────────────────────────
    "gmv": {
        "display_name": "Gross Merchandise Value (GMV)",
        "description": "Total order value placed on platform = Orders × AOV",
        "formula": "orders * aov / 1000",
        "formula_inputs": ["orders", "aov"],
        "unit": "₹B",
        "category": "Financial",
        "is_base": False,
    },
    "revenue": {
        "display_name": "Revenue",
        "description": "Net platform revenue = GMV×Commission + Delivery Revenue − Platform Discounts",
        "formula": "gmv * commission_rate / 100 + delivery_charges - discounts",
        "formula_inputs": ["gmv", "commission_rate", "delivery_charges", "discounts"],
        "unit": "₹B",
        "category": "Financial",
        "is_base": False,
    },
    "take_rate": {
        "display_name": "Take Rate",
        "description": "Revenue as a % of GMV — measures platform monetisation efficiency",
        "formula": "revenue / gmv * 100",
        "formula_inputs": ["revenue", "gmv"],
        "unit": "%",
        "category": "Financial",
        "is_base": False,
    },
    "arpu": {
        "display_name": "Average Revenue Per User (ARPU)",
        "description": "Revenue generated per active user = Revenue / MAU",
        "formula": "revenue / active_users * 1000",
        "formula_inputs": ["revenue", "active_users"],
        "unit": "₹",
        "category": "Financial",
        "is_base": False,
    },
    "order_frequency": {
        "display_name": "Order Frequency",
        "description": "Avg orders per active user per quarter = Orders / MAU",
        "formula": "orders / active_users",
        "formula_inputs": ["orders", "active_users"],
        "unit": "orders/user",
        "category": "Operational",
        "is_base": False,
    },
    "cac": {
        "display_name": "Customer Acquisition Cost (CAC)",
        "description": "Cost to acquire one new user = Marketing Spend / New Users",
        "formula": "marketing_spend / new_users * 1000",
        "formula_inputs": ["marketing_spend", "new_users"],
        "unit": "₹",
        "category": "Financial",
        "is_base": False,
    },
    "ebitda": {
        "display_name": "EBITDA",
        "description": "Earnings Before Interest, Taxes, Depreciation, Amortization = Revenue - Operating Expenses",
        "formula": "revenue - (delivery_charges + discounts) * 0.15",
        "formula_inputs": ["revenue", "delivery_charges", "discounts"],
        "unit": "₹B",
        "category": "Financial",
        "is_base": False,
    },
}

DEFAULT_RELATIONSHIPS: List[Dict[str, Any]] = [
    # Formula dependencies
    {"source": "orders", "target": "gmv", "type": "formula_dependency", "direction": "positive", "strength": 0.9, "explanation": "GMV = Orders × AOV"},
    {"source": "aov", "target": "gmv", "type": "formula_dependency", "direction": "positive", "strength": 0.9, "explanation": "GMV = Orders × AOV"},
    {"source": "gmv", "target": "revenue", "type": "formula_dependency", "direction": "positive", "strength": 0.85, "explanation": "Revenue includes commission on GMV"},
    {"source": "commission_rate", "target": "revenue", "type": "formula_dependency", "direction": "positive", "strength": 0.65, "explanation": "Higher commission rate lifts revenue"},
    {"source": "delivery_charges", "target": "revenue", "type": "formula_dependency", "direction": "positive", "strength": 0.45, "explanation": "Delivery revenue is additive"},
    {"source": "discounts", "target": "revenue", "type": "formula_dependency", "direction": "negative", "strength": 0.50, "explanation": "Discounts reduce revenue"},
    {"source": "revenue", "target": "take_rate", "type": "formula_dependency", "direction": "positive", "strength": 0.9, "explanation": "Take Rate = Revenue / GMV"},
    {"source": "gmv", "target": "take_rate", "type": "formula_dependency", "direction": "negative", "strength": 0.9, "explanation": "Take Rate = Revenue / GMV"},
    {"source": "revenue", "target": "arpu", "type": "formula_dependency", "direction": "positive", "strength": 0.9, "explanation": "ARPU = Revenue / MAU"},
    {"source": "active_users", "target": "arpu", "type": "formula_dependency", "direction": "negative", "strength": 0.7, "explanation": "More users dilutes ARPU"},
    {"source": "orders", "target": "order_frequency", "type": "formula_dependency", "direction": "positive", "strength": 0.9, "explanation": "Order Frequency = Orders / MAU"},
    {"source": "active_users", "target": "order_frequency", "type": "formula_dependency", "direction": "negative", "strength": 0.7, "explanation": "More users dilutes frequency"},
    {"source": "marketing_spend", "target": "cac", "type": "formula_dependency", "direction": "positive", "strength": 0.9, "explanation": "CAC = Marketing Spend / New Users"},
    {"source": "new_users", "target": "cac", "type": "formula_dependency", "direction": "negative", "strength": 0.9, "explanation": "More acquisitions lower CAC"},
    # Causal drivers
    {"source": "basket_size", "target": "aov", "type": "causal_driver", "direction": "positive", "strength": 0.75, "explanation": "More items per order raises AOV"},
    {"source": "pricing_index", "target": "aov", "type": "causal_driver", "direction": "positive", "strength": 0.60, "explanation": "Higher prices increase AOV"},
    {"source": "restaurant_partners", "target": "aov", "type": "causal_driver", "direction": "positive", "strength": 0.35, "explanation": "Premium restaurants increase AOV"},
    {"source": "discounts", "target": "aov", "type": "causal_driver", "direction": "negative", "strength": 0.40, "explanation": "Heavy discounts attract low-value orders"},
    {"source": "active_users", "target": "orders", "type": "causal_driver", "direction": "positive", "strength": 0.85, "explanation": "More users generate orders"},
    {"source": "order_frequency", "target": "orders", "type": "causal_driver", "direction": "positive", "strength": 0.80, "explanation": "Higher frequency expands order volume"},
    {"source": "discounts", "target": "orders", "type": "causal_driver", "direction": "positive", "strength": 0.60, "explanation": "Discounts generate extra orders"},
    {"source": "restaurant_partners", "target": "orders", "type": "causal_driver", "direction": "positive", "strength": 0.50, "explanation": "More restaurants improve conversion"},
    {"source": "marketing_spend", "target": "orders", "type": "causal_driver", "direction": "positive", "strength": 0.50, "explanation": "Marketing drives orders"},
    {"source": "new_users", "target": "active_users", "type": "causal_driver", "direction": "positive", "strength": 0.70, "explanation": "New users increase MAU"},
]

# ─────────────────────────────────────────────────────────────────────────────
# DYNAMIC REGISTRY: Populated at runtime from database
# ─────────────────────────────────────────────────────────────────────────────

# These are functions that call the loader - populated at startup
def METRIC_REGISTRY() -> Dict[str, Dict[str, Any]]:
    """Get metrics from database (loaded at startup). Falls back to seed data if DB empty."""
    from .loader import get_metric_registry
    registry = get_metric_registry()
    return registry if registry else DEFAULT_METRICS

def FORMULA_FUNCTIONS() -> Dict[str, Callable]:
    """Get compiled formulas from database (loaded at startup)."""
    from .loader import get_formula_functions
    return get_formula_functions()

def COMPUTATION_ORDER() -> List[str]:
    """Get computation order from database (loaded at startup)."""
    from .loader import get_computation_order
    order = get_computation_order()
    return order if order else list(DEFAULT_METRICS.keys())

def ALL_PERIODS() -> List[str]:
    """Get all available periods from database (loaded at startup)."""
    from .loader import get_all_periods
    periods = get_all_periods()
    # Return at least a placeholder
    return periods if periods else ["Q1 2023", "Q2 2023", "Q3 2023", "Q4 2023"]

def RELATIONSHIP_DEFINITIONS() -> List[Dict[str, Any]]:
    """Get relationships from database (loaded at startup)."""
    from .loader import get_relationships
    rels = get_relationships()
    return rels if rels else DEFAULT_RELATIONSHIPS
