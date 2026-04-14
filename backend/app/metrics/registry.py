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
# 4. TIME-SERIES BASE DATA  (8 quarters: Q1 2022 → Q4 2023)
#    Key: (period, segment, metric_name)  →  float value
#    Units match the metric registry.
# ─────────────────────────────────────────────────────────────────────────────

# All periods in display order
ALL_PERIODS = [
    "Q1 2022", "Q2 2022", "Q3 2022", "Q4 2022",
    "Q1 2023", "Q2 2023", "Q3 2023", "Q4 2023",
]

RAW_DATA: Dict[Tuple[str, str, str], float] = {

    # ── FOOD DELIVERY ─────────────────────────────────────────────────────────

    # Orders (M)
    ("Q1 2022", "Food Delivery", "orders"): 85.0,
    ("Q2 2022", "Food Delivery", "orders"): 95.0,
    ("Q3 2022", "Food Delivery", "orders"): 105.0,
    ("Q4 2022", "Food Delivery", "orders"): 100.0,
    ("Q1 2023", "Food Delivery", "orders"): 110.0,
    ("Q2 2023", "Food Delivery", "orders"): 120.0,
    ("Q3 2023", "Food Delivery", "orders"): 145.0,   # ← summer campaign spike
    ("Q4 2023", "Food Delivery", "orders"): 152.0,

    # AOV (₹)
    ("Q1 2022", "Food Delivery", "aov"): 295.0,
    ("Q2 2022", "Food Delivery", "aov"): 300.0,
    ("Q3 2022", "Food Delivery", "aov"): 305.0,
    ("Q4 2022", "Food Delivery", "aov"): 310.0,
    ("Q1 2023", "Food Delivery", "aov"): 312.0,
    ("Q2 2023", "Food Delivery", "aov"): 315.0,
    ("Q3 2023", "Food Delivery", "aov"): 332.0,     # ← basket size + premium restaurants
    ("Q4 2023", "Food Delivery", "aov"): 340.0,

    # Commission Rate (%)
    ("Q1 2022", "Food Delivery", "commission_rate"): 17.5,
    ("Q2 2022", "Food Delivery", "commission_rate"): 17.5,
    ("Q3 2022", "Food Delivery", "commission_rate"): 18.0,
    ("Q4 2022", "Food Delivery", "commission_rate"): 18.0,
    ("Q1 2023", "Food Delivery", "commission_rate"): 18.5,
    ("Q2 2023", "Food Delivery", "commission_rate"): 18.5,
    ("Q3 2023", "Food Delivery", "commission_rate"): 19.5,  # ← rate revision
    ("Q4 2023", "Food Delivery", "commission_rate"): 19.5,

    # Delivery Revenue (₹B)
    ("Q1 2022", "Food Delivery", "delivery_charges"): 0.85,
    ("Q2 2022", "Food Delivery", "delivery_charges"): 0.95,
    ("Q3 2022", "Food Delivery", "delivery_charges"): 1.05,
    ("Q4 2022", "Food Delivery", "delivery_charges"): 1.00,
    ("Q1 2023", "Food Delivery", "delivery_charges"): 1.10,
    ("Q2 2023", "Food Delivery", "delivery_charges"): 1.20,
    ("Q3 2023", "Food Delivery", "delivery_charges"): 1.45,
    ("Q4 2023", "Food Delivery", "delivery_charges"): 1.55,

    # Platform Discounts (₹B)
    ("Q1 2022", "Food Delivery", "discounts"): 2.50,
    ("Q2 2022", "Food Delivery", "discounts"): 2.80,
    ("Q3 2022", "Food Delivery", "discounts"): 3.00,
    ("Q4 2022", "Food Delivery", "discounts"): 2.90,
    ("Q1 2023", "Food Delivery", "discounts"): 3.10,
    ("Q2 2023", "Food Delivery", "discounts"): 3.30,
    ("Q3 2023", "Food Delivery", "discounts"): 3.80,   # ← summers promos cost
    ("Q4 2023", "Food Delivery", "discounts"): 4.00,

    # Marketing Spend (₹B)
    ("Q1 2022", "Food Delivery", "marketing_spend"): 2.00,
    ("Q2 2022", "Food Delivery", "marketing_spend"): 2.20,
    ("Q3 2022", "Food Delivery", "marketing_spend"): 2.30,
    ("Q4 2022", "Food Delivery", "marketing_spend"): 2.10,
    ("Q1 2023", "Food Delivery", "marketing_spend"): 2.40,
    ("Q2 2023", "Food Delivery", "marketing_spend"): 2.60,
    ("Q3 2023", "Food Delivery", "marketing_spend"): 3.20,   # ← big push
    ("Q4 2023", "Food Delivery", "marketing_spend"): 3.00,

    # New Users (M)
    ("Q1 2022", "Food Delivery", "new_users"): 6.0,
    ("Q2 2022", "Food Delivery", "new_users"): 7.0,
    ("Q3 2022", "Food Delivery", "new_users"): 7.5,
    ("Q4 2022", "Food Delivery", "new_users"): 6.5,
    ("Q1 2023", "Food Delivery", "new_users"): 7.0,
    ("Q2 2023", "Food Delivery", "new_users"): 8.0,
    ("Q3 2023", "Food Delivery", "new_users"): 10.5,  # ← acquisition drive
    ("Q4 2023", "Food Delivery", "new_users"): 9.0,

    # Active Users / MAU (M)
    ("Q1 2022", "Food Delivery", "active_users"): 30.0,
    ("Q2 2022", "Food Delivery", "active_users"): 32.0,
    ("Q3 2022", "Food Delivery", "active_users"): 35.0,
    ("Q4 2022", "Food Delivery", "active_users"): 34.0,
    ("Q1 2023", "Food Delivery", "active_users"): 36.0,
    ("Q2 2023", "Food Delivery", "active_users"): 39.0,
    ("Q3 2023", "Food Delivery", "active_users"): 46.0,  # ← new users + retention
    ("Q4 2023", "Food Delivery", "active_users"): 49.0,

    # Basket Size (items/order)
    ("Q1 2022", "Food Delivery", "basket_size"): 2.8,
    ("Q2 2022", "Food Delivery", "basket_size"): 2.9,
    ("Q3 2022", "Food Delivery", "basket_size"): 3.0,
    ("Q4 2022", "Food Delivery", "basket_size"): 3.0,
    ("Q1 2023", "Food Delivery", "basket_size"): 3.1,
    ("Q2 2023", "Food Delivery", "basket_size"): 3.2,
    ("Q3 2023", "Food Delivery", "basket_size"): 3.5,   # ← upsell initiative
    ("Q4 2023", "Food Delivery", "basket_size"): 3.6,

    # Restaurant Partners (K)
    ("Q1 2022", "Food Delivery", "restaurant_partners"): 180.0,
    ("Q2 2022", "Food Delivery", "restaurant_partners"): 190.0,
    ("Q3 2022", "Food Delivery", "restaurant_partners"): 200.0,
    ("Q4 2022", "Food Delivery", "restaurant_partners"): 205.0,
    ("Q1 2023", "Food Delivery", "restaurant_partners"): 215.0,
    ("Q2 2023", "Food Delivery", "restaurant_partners"): 230.0,
    ("Q3 2023", "Food Delivery", "restaurant_partners"): 255.0,  # ← expansion
    ("Q4 2023", "Food Delivery", "restaurant_partners"): 270.0,

    # Pricing Index (base = 100)
    ("Q1 2022", "Food Delivery", "pricing_index"): 100.0,
    ("Q2 2022", "Food Delivery", "pricing_index"): 101.0,
    ("Q3 2022", "Food Delivery", "pricing_index"): 102.0,
    ("Q4 2022", "Food Delivery", "pricing_index"): 103.0,
    ("Q1 2023", "Food Delivery", "pricing_index"): 104.0,
    ("Q2 2023", "Food Delivery", "pricing_index"): 105.0,
    ("Q3 2023", "Food Delivery", "pricing_index"): 108.0,  # ← premium shift
    ("Q4 2023", "Food Delivery", "pricing_index"): 110.0,

    # ── GROCERY DELIVERY ──────────────────────────────────────────────────────

    ("Q1 2022", "Grocery Delivery", "orders"): 15.0,
    ("Q2 2022", "Grocery Delivery", "orders"): 18.0,
    ("Q3 2022", "Grocery Delivery", "orders"): 20.0,
    ("Q4 2022", "Grocery Delivery", "orders"): 22.0,
    ("Q1 2023", "Grocery Delivery", "orders"): 25.0,
    ("Q2 2023", "Grocery Delivery", "orders"): 28.0,
    ("Q3 2023", "Grocery Delivery", "orders"): 36.0,   # ← blitz campaign
    ("Q4 2023", "Grocery Delivery", "orders"): 42.0,

    ("Q1 2022", "Grocery Delivery", "aov"): 380.0,
    ("Q2 2022", "Grocery Delivery", "aov"): 390.0,
    ("Q3 2022", "Grocery Delivery", "aov"): 395.0,
    ("Q4 2022", "Grocery Delivery", "aov"): 400.0,
    ("Q1 2023", "Grocery Delivery", "aov"): 405.0,
    ("Q2 2023", "Grocery Delivery", "aov"): 410.0,
    ("Q3 2023", "Grocery Delivery", "aov"): 425.0,
    ("Q4 2023", "Grocery Delivery", "aov"): 440.0,

    ("Q1 2022", "Grocery Delivery", "commission_rate"): 8.0,
    ("Q2 2022", "Grocery Delivery", "commission_rate"): 8.0,
    ("Q3 2022", "Grocery Delivery", "commission_rate"): 8.5,
    ("Q4 2022", "Grocery Delivery", "commission_rate"): 8.5,
    ("Q1 2023", "Grocery Delivery", "commission_rate"): 9.0,
    ("Q2 2023", "Grocery Delivery", "commission_rate"): 9.0,
    ("Q3 2023", "Grocery Delivery", "commission_rate"): 10.0,
    ("Q4 2023", "Grocery Delivery", "commission_rate"): 10.0,

    ("Q1 2022", "Grocery Delivery", "delivery_charges"): 0.15,
    ("Q2 2022", "Grocery Delivery", "delivery_charges"): 0.18,
    ("Q3 2022", "Grocery Delivery", "delivery_charges"): 0.20,
    ("Q4 2022", "Grocery Delivery", "delivery_charges"): 0.22,
    ("Q1 2023", "Grocery Delivery", "delivery_charges"): 0.25,
    ("Q2 2023", "Grocery Delivery", "delivery_charges"): 0.28,
    ("Q3 2023", "Grocery Delivery", "delivery_charges"): 0.36,
    ("Q4 2023", "Grocery Delivery", "delivery_charges"): 0.42,

    ("Q1 2022", "Grocery Delivery", "discounts"): 0.50,
    ("Q2 2022", "Grocery Delivery", "discounts"): 0.60,
    ("Q3 2022", "Grocery Delivery", "discounts"): 0.65,
    ("Q4 2022", "Grocery Delivery", "discounts"): 0.68,
    ("Q1 2023", "Grocery Delivery", "discounts"): 0.75,
    ("Q2 2023", "Grocery Delivery", "discounts"): 0.85,
    ("Q3 2023", "Grocery Delivery", "discounts"): 1.05,
    ("Q4 2023", "Grocery Delivery", "discounts"): 1.15,

    ("Q1 2022", "Grocery Delivery", "marketing_spend"): 0.40,
    ("Q2 2022", "Grocery Delivery", "marketing_spend"): 0.50,
    ("Q3 2022", "Grocery Delivery", "marketing_spend"): 0.50,
    ("Q4 2022", "Grocery Delivery", "marketing_spend"): 0.45,
    ("Q1 2023", "Grocery Delivery", "marketing_spend"): 0.55,
    ("Q2 2023", "Grocery Delivery", "marketing_spend"): 0.65,
    ("Q3 2023", "Grocery Delivery", "marketing_spend"): 0.90,
    ("Q4 2023", "Grocery Delivery", "marketing_spend"): 0.85,

    ("Q1 2022", "Grocery Delivery", "new_users"): 2.0,
    ("Q2 2022", "Grocery Delivery", "new_users"): 2.5,
    ("Q3 2022", "Grocery Delivery", "new_users"): 2.8,
    ("Q4 2022", "Grocery Delivery", "new_users"): 2.5,
    ("Q1 2023", "Grocery Delivery", "new_users"): 3.0,
    ("Q2 2023", "Grocery Delivery", "new_users"): 3.5,
    ("Q3 2023", "Grocery Delivery", "new_users"): 5.2,
    ("Q4 2023", "Grocery Delivery", "new_users"): 4.5,

    ("Q1 2022", "Grocery Delivery", "active_users"): 8.0,
    ("Q2 2022", "Grocery Delivery", "active_users"): 9.0,
    ("Q3 2022", "Grocery Delivery", "active_users"): 10.0,
    ("Q4 2022", "Grocery Delivery", "active_users"): 11.0,
    ("Q1 2023", "Grocery Delivery", "active_users"): 12.0,
    ("Q2 2023", "Grocery Delivery", "active_users"): 14.0,
    ("Q3 2023", "Grocery Delivery", "active_users"): 18.0,
    ("Q4 2023", "Grocery Delivery", "active_users"): 22.0,

    ("Q1 2022", "Grocery Delivery", "basket_size"): 5.0,
    ("Q2 2022", "Grocery Delivery", "basket_size"): 5.2,
    ("Q3 2022", "Grocery Delivery", "basket_size"): 5.3,
    ("Q4 2022", "Grocery Delivery", "basket_size"): 5.5,
    ("Q1 2023", "Grocery Delivery", "basket_size"): 5.5,
    ("Q2 2023", "Grocery Delivery", "basket_size"): 5.8,
    ("Q3 2023", "Grocery Delivery", "basket_size"): 6.2,
    ("Q4 2023", "Grocery Delivery", "basket_size"): 6.5,

    ("Q1 2022", "Grocery Delivery", "restaurant_partners"): 5.0,
    ("Q2 2022", "Grocery Delivery", "restaurant_partners"): 6.0,
    ("Q3 2022", "Grocery Delivery", "restaurant_partners"): 7.0,
    ("Q4 2022", "Grocery Delivery", "restaurant_partners"): 8.0,
    ("Q1 2023", "Grocery Delivery", "restaurant_partners"): 9.0,
    ("Q2 2023", "Grocery Delivery", "restaurant_partners"): 11.0,
    ("Q3 2023", "Grocery Delivery", "restaurant_partners"): 14.0,
    ("Q4 2023", "Grocery Delivery", "restaurant_partners"): 17.0,

    ("Q1 2022", "Grocery Delivery", "pricing_index"): 100.0,
    ("Q2 2022", "Grocery Delivery", "pricing_index"): 101.0,
    ("Q3 2022", "Grocery Delivery", "pricing_index"): 103.0,
    ("Q4 2022", "Grocery Delivery", "pricing_index"): 105.0,
    ("Q1 2023", "Grocery Delivery", "pricing_index"): 106.0,
    ("Q2 2023", "Grocery Delivery", "pricing_index"): 108.0,
    ("Q3 2023", "Grocery Delivery", "pricing_index"): 112.0,
    ("Q4 2023", "Grocery Delivery", "pricing_index"): 115.0,
}


# ─────────────────────────────────────────────────────────────────────────────
# 5. CAUSAL EVENTS  (narrative context per period)
# ─────────────────────────────────────────────────────────────────────────────

CAUSAL_EVENTS: List[Dict[str, Any]] = [
    {
        "period": "Q3 2023",
        "event_name": "Summer Promotions Campaign",
        "segment": "Food Delivery",
        "affected_metrics": ["orders", "discounts", "active_users"],
        "direction": "positive",
        "magnitude": "high",
        "explanation": (
            "A large-scale summer campaign offered 40% discounts on first 5 orders "
            "for returning users and free delivery on weekends. This drove a surge of "
            "+25M orders and +7M active users, but raised platform discount spend by ₹0.5B."
        ),
    },
    {
        "period": "Q3 2023",
        "event_name": "Premium Restaurant Expansion",
        "segment": "Food Delivery",
        "affected_metrics": ["restaurant_partners", "aov", "pricing_index"],
        "direction": "positive",
        "magnitude": "medium",
        "explanation": (
            "Onboarded 25K new premium and cloud-kitchen restaurant partners in Tier-1 cities. "
            "Premium menus raised the pricing index by 3 points and basket size by 0.3 items, "
            "pushing AOV from ₹315 to ₹332."
        ),
    },
    {
        "period": "Q3 2023",
        "event_name": "Commission Rate Revision",
        "segment": "Food Delivery",
        "affected_metrics": ["commission_rate", "revenue"],
        "direction": "positive",
        "magnitude": "medium",
        "explanation": (
            "Renegotiated restaurant commission agreements increased the blended rate from "
            "18.5% to 19.5% — adding ~₹0.48B to revenue directly."
        ),
    },
    {
        "period": "Q3 2023",
        "event_name": "User Acquisition Drive & Referral Program",
        "segment": "Food Delivery",
        "affected_metrics": ["marketing_spend", "new_users", "active_users"],
        "direction": "positive",
        "magnitude": "high",
        "explanation": (
            "Marketing spend increased by ₹0.6B to fund a referral programme (₹150 credit "
            "per referral). This brought in 10.5M new users — 31% more than Q2 2023 — and "
            "expanded MAU from 39M to 46M."
        ),
    },
    {
        "period": "Q3 2023",
        "event_name": "Upsell & Cross-sell Initiative",
        "segment": "Food Delivery",
        "affected_metrics": ["basket_size", "aov"],
        "direction": "positive",
        "magnitude": "medium",
        "explanation": (
            "In-app recommendations and combo-deal nudges increased basket size from "
            "3.2 to 3.5 items per order, contributing ~₹10 to AOV improvement."
        ),
    },
    {
        "period": "Q3 2023",
        "event_name": "Grocery Blitz Week",
        "segment": "Grocery Delivery",
        "affected_metrics": ["orders", "new_users", "discounts"],
        "direction": "positive",
        "magnitude": "high",
        "explanation": (
            "A 10-day grocery blitz (flat ₹100 off on orders >₹300) boosted grocery orders "
            "by 29% QoQ and brought 5.2M new grocery users onto the platform."
        ),
    },
    {
        "period": "Q1 2023",
        "event_name": "Post-Festival Demand Slowdown",
        "segment": "Food Delivery",
        "affected_metrics": ["orders", "active_users"],
        "direction": "negative",
        "magnitude": "low",
        "explanation": (
            "Seasonal slowdown post-Diwali (Q4 2022) led to a 10% dip in orders in Q1 2023 "
            "vs the peak Q3 2022 festival period."
        ),
    },
]
