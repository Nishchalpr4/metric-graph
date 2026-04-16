"""
Metric Registry — single source of truth for ALL metric definitions,
formula functions, relationship definitions, and raw time-series data.

Design principles:
  - No hardcoded business values inside the engine; every rule lives here.
  - Formulas are stored as both human-readable strings (for the DB) and
    executable Python lambdas (for the computation engine).
  - Relationships carry full metadata: type, direction, strength, explanation.
  - Raw time-series data is keyed by (period, segment, metric_name).
"""

from typing import Dict, Any, Callable, List, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# 1. METRIC DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

METRIC_REGISTRY: Dict[str, Dict[str, Any]] = {

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
}


# ─────────────────────────────────────────────────────────────────────────────
# 2. FORMULA FUNCTIONS (executable, no eval)
#    Each lambda receives a dict {metric_name: float_value}.
# ─────────────────────────────────────────────────────────────────────────────

FORMULA_FUNCTIONS: Dict[str, Callable[[Dict[str, float]], float]] = {
    "gmv": lambda v: v["orders"] * v["aov"] / 1000,
    "revenue": lambda v: (
        v["gmv"] * v["commission_rate"] / 100
        + v["delivery_charges"]
        - v["discounts"]
    ),
    "take_rate": lambda v: (v["revenue"] / v["gmv"] * 100) if v["gmv"] else 0.0,
    "arpu": lambda v: (v["revenue"] / v["active_users"] * 1000) if v["active_users"] else 0.0,
    "order_frequency": lambda v: (v["orders"] / v["active_users"]) if v["active_users"] else 0.0,
    "cac": lambda v: (v["marketing_spend"] / v["new_users"] * 1000) if v["new_users"] else 0.0,
}

# Topological order — base metrics first, then dependents in dependency order
COMPUTATION_ORDER: List[str] = [
    # base
    "orders", "aov", "commission_rate", "delivery_charges", "discounts",
    "marketing_spend", "new_users", "active_users",
    "basket_size", "restaurant_partners", "pricing_index",
    # level-1 derived
    "gmv",
    # level-2 derived
    "revenue",
    # level-3 derived
    "take_rate", "arpu", "order_frequency", "cac",
]


# ─────────────────────────────────────────────────────────────────────────────
# 3. RELATIONSHIP DEFINITIONS
#    Each entry becomes one row in metric_relationships.
# ─────────────────────────────────────────────────────────────────────────────

RELATIONSHIP_DEFINITIONS: List[Dict[str, Any]] = [

    # ── Formula Dependencies ──────────────────────────────────────────────────
    {
        "source": "orders", "target": "gmv",
        "type": "formula_dependency", "direction": "positive", "strength": 0.9,
        "explanation": "GMV = Orders × AOV. Orders is a direct multiplicative input.",
    },
    {
        "source": "aov", "target": "gmv",
        "type": "formula_dependency", "direction": "positive", "strength": 0.9,
        "explanation": "GMV = Orders × AOV. AOV is a direct multiplicative input.",
    },
    {
        "source": "gmv", "target": "revenue",
        "type": "formula_dependency", "direction": "positive", "strength": 0.85,
        "explanation": "Revenue = GMV × Commission Rate + Delivery − Discounts. GMV is the primary revenue lever.",
    },
    {
        "source": "commission_rate", "target": "revenue",
        "type": "formula_dependency", "direction": "positive", "strength": 0.65,
        "explanation": "A higher commission rate multiplied against GMV directly lifts revenue.",
    },
    {
        "source": "delivery_charges", "target": "revenue",
        "type": "formula_dependency", "direction": "positive", "strength": 0.45,
        "explanation": "Delivery revenue is an additive component of total platform revenue.",
    },
    {
        "source": "discounts", "target": "revenue",
        "type": "formula_dependency", "direction": "negative", "strength": 0.50,
        "explanation": "Platform-funded discounts are subtracted from revenue; more discounts = lower revenue.",
    },
    {
        "source": "revenue", "target": "take_rate",
        "type": "formula_dependency", "direction": "positive", "strength": 0.9,
        "explanation": "Take Rate = Revenue / GMV. Higher revenue raises take rate.",
    },
    {
        "source": "gmv", "target": "take_rate",
        "type": "formula_dependency", "direction": "negative", "strength": 0.9,
        "explanation": "Take Rate = Revenue / GMV. Higher GMV with same revenue dilutes take rate.",
    },
    {
        "source": "revenue", "target": "arpu",
        "type": "formula_dependency", "direction": "positive", "strength": 0.9,
        "explanation": "ARPU = Revenue / MAU. Revenue growth directly lifts ARPU.",
    },
    {
        "source": "active_users", "target": "arpu",
        "type": "formula_dependency", "direction": "negative", "strength": 0.7,
        "explanation": "ARPU = Revenue / MAU. More users (same revenue) dilutes per-user revenue.",
    },
    {
        "source": "orders", "target": "order_frequency",
        "type": "formula_dependency", "direction": "positive", "strength": 0.9,
        "explanation": "Order Frequency = Orders / MAU.",
    },
    {
        "source": "active_users", "target": "order_frequency",
        "type": "formula_dependency", "direction": "negative", "strength": 0.7,
        "explanation": "More users ordering the same total dilutes per-user frequency.",
    },
    {
        "source": "marketing_spend", "target": "cac",
        "type": "formula_dependency", "direction": "positive", "strength": 0.9,
        "explanation": "CAC = Marketing Spend / New Users. More spend raises CAC.",
    },
    {
        "source": "new_users", "target": "cac",
        "type": "formula_dependency", "direction": "negative", "strength": 0.9,
        "explanation": "CAC = Marketing Spend / New Users. More acquisitions lower CAC.",
    },

    # ── Causal Drivers ────────────────────────────────────────────────────────
    {
        "source": "basket_size", "target": "aov",
        "type": "causal_driver", "direction": "positive", "strength": 0.75,
        "explanation": "More items per order raises the total bill — the single biggest AOV driver.",
    },
    {
        "source": "pricing_index", "target": "aov",
        "type": "causal_driver", "direction": "positive", "strength": 0.60,
        "explanation": "Higher average menu prices (e.g. premiumisation) increase AOV.",
    },
    {
        "source": "restaurant_partners", "target": "aov",
        "type": "causal_driver", "direction": "positive", "strength": 0.35,
        "explanation": "Expansion into premium restaurants introduces higher-priced items, lifting AOV.",
    },
    {
        "source": "discounts", "target": "aov",
        "type": "causal_driver", "direction": "negative", "strength": 0.40,
        "explanation": "Large blanket discounts attract price-sensitive, smaller orders, pulling AOV down.",
    },
    {
        "source": "active_users", "target": "orders",
        "type": "causal_driver", "direction": "positive", "strength": 0.85,
        "explanation": "Every incremental active user generates orders — the strongest volume driver.",
    },
    {
        "source": "order_frequency", "target": "orders",
        "type": "causal_driver", "direction": "positive", "strength": 0.80,
        "explanation": "Users ordering more frequently expand total order volume.",
    },
    {
        "source": "discounts", "target": "orders",
        "type": "causal_driver", "direction": "positive", "strength": 0.60,
        "explanation": "Promotional discounts reduce friction and pull in extra orders.",
    },
    {
        "source": "restaurant_partners", "target": "orders",
        "type": "causal_driver", "direction": "positive", "strength": 0.50,
        "explanation": "Wider restaurant selection improves conversion; more choices → more orders.",
    },
    {
        "source": "marketing_spend", "target": "orders",
        "type": "causal_driver", "direction": "positive", "strength": 0.50,
        "explanation": "Demand-generation campaigns (performance ads, notifications) drive incremental orders.",
    },
    {
        "source": "new_users", "target": "active_users",
        "type": "causal_driver", "direction": "positive", "strength": 0.70,
        "explanation": "Newly acquired users enter and grow the active-user base.",
    },
    {
        "source": "marketing_spend", "target": "new_users",
        "type": "causal_driver", "direction": "positive", "strength": 0.75,
        "explanation": "User-acquisition campaigns (referral, app-store ads) directly bring in new users.",
    },
    {
        "source": "basket_size", "target": "gmv",
        "type": "causal_driver", "direction": "positive", "strength": 0.55,
        "explanation": "Larger baskets raise AOV which flows into higher GMV.",
    },
    {
        "source": "restaurant_partners", "target": "gmv",
        "type": "causal_driver", "direction": "positive", "strength": 0.45,
        "explanation": "More supply-side partners drive both order volume and AOV, growing GMV.",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# 4. AVAILABLE PERIODS (for reference)
# ─────────────────────────────────────────────────────────────────────────────

ALL_PERIODS = [
    "Q1 2022", "Q2 2022", "Q3 2022", "Q4 2022",
    "Q1 2023", "Q2 2023", "Q3 2023", "Q4 2023",
]

