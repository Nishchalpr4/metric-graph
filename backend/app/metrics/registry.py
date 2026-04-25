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
    # ── Base / Input Metrics (Mappings to SEC line items) ─────────────────────
    "revenue_from_operations": {
        "display_name": "Revenue from Operations",
        "description": "Total top-line income from core business activities",
        "formula": None,
        "formula_inputs": [],
        "unit": "₹B",
        "category": "Financial",
        "is_base": True,
    },
    "cost_of_material": {
        "display_name": "Cost of Materials",
        "description": "Direct costs attributable to the production of goods sold",
        "formula": None,
        "formula_inputs": [],
        "unit": "₹B",
        "category": "Financial",
        "is_base": True,
    },
    "employee_benefit_expense": {
        "display_name": "Employee Benefit Expense",
        "description": "Total personnel costs, including salaries, bonuses, and benefits",
        "formula": None,
        "formula_inputs": [],
        "unit": "₹B",
        "category": "Financial",
        "is_base": True,
    },
    "depreciation": {
        "display_name": "Depreciation & Amortization",
        "description": "Non-cash expense representing the gradual loss of value of tangible/intangible assets",
        "formula": None,
        "formula_inputs": [],
        "unit": "₹B",
        "category": "Financial",
        "is_base": True,
    },
    "interest_expense": {
        "display_name": "Interest Expense",
        "description": "Cost of borrowing funds during the period",
        "formula": None,
        "formula_inputs": [],
        "unit": "₹B",
        "category": "Financial",
        "is_base": True,
    },
    
    # ── Derived / Computed Financial Metrics ──────────────────────────────────
    "gross_profit": {
        "display_name": "Gross Profit",
        "description": "Revenue minus direct costs (Cost of Materials) = Revenue - COGS",
        "formula": "revenue_from_operations - cost_of_material",
        "formula_inputs": ["revenue_from_operations", "cost_of_material"],
        "unit": "₹B",
        "category": "Financial",
        "is_base": False,
    },
    "ebitda": {
        "display_name": "EBITDA",
        "description": "Earnings Before Interest, Taxes, Depreciation, and Amortization = Gross Profit - Personnel Costs",
        "formula": "gross_profit - employee_benefit_expense",
        "formula_inputs": ["gross_profit", "employee_benefit_expense"],
        "unit": "₹B",
        "category": "Financial",
        "is_base": False,
    },
    "net_income": {
        "display_name": "Net Income / Profit",
        "description": "Bottom-line profit after all expenses = EBITDA - Depreciation - Interest",
        "formula": "ebitda - depreciation - interest_expense",
        "formula_inputs": ["ebitda", "depreciation", "interest_expense"],
        "unit": "₹B",
        "category": "Financial",
        "is_base": False,
    },
    "gross_margin_pct": {
        "display_name": "Gross Margin %",
        "description": "Efficiency of production: Gross Profit / Revenue",
        "formula": "gross_profit / revenue_from_operations * 100",
        "formula_inputs": ["gross_profit", "revenue_from_operations"],
        "unit": "%",
        "category": "Efficiency",
        "is_base": False,
    },
    "ebitda_margin_pct": {
        "display_name": "EBITDA Margin %",
        "description": "Operational efficiency: EBITDA / Revenue",
        "formula": "ebitda / revenue_from_operations * 100",
        "formula_inputs": ["ebitda", "revenue_from_operations"],
        "unit": "%",
        "category": "Efficiency",
        "is_base": False,
    },
}

DEFAULT_RELATIONSHIPS: List[Dict[str, Any]] = [
    # Formula dependencies (Mathematical link)
    {"source": "revenue_from_operations", "target": "gross_profit", "type": "formula_dependency", "direction": "positive", "strength": 1.0, "explanation": "Gross Profit = Revenue - COGS"},
    {"source": "cost_of_material", "target": "gross_profit", "type": "formula_dependency", "direction": "negative", "strength": 1.0, "explanation": "Higher production costs reduce gross profit"},
    
    {"source": "gross_profit", "target": "ebitda", "type": "formula_dependency", "direction": "positive", "strength": 1.0, "explanation": "EBITDA = Gross Profit - Operating Expenses"},
    {"source": "employee_benefit_expense", "target": "ebitda", "type": "formula_dependency", "direction": "negative", "strength": 1.0, "explanation": "Personnel costs directly reduce operational profit"},
    
    {"source": "ebitda", "target": "net_income", "type": "formula_dependency", "direction": "positive", "strength": 1.0, "explanation": "Net Income = EBITDA - D&A - Interest"},
    {"source": "depreciation", "target": "net_income", "type": "formula_dependency", "direction": "negative", "strength": 1.0, "explanation": "Non-cash expenses reduce taxable income"},
    {"source": "interest_expense", "target": "net_income", "type": "formula_dependency", "direction": "negative", "strength": 1.0, "explanation": "Cost of debt service reduces net profit"},

    # Efficiency Metrics
    {"source": "gross_profit", "target": "gross_margin_pct", "type": "formula_dependency", "direction": "positive", "strength": 1.0},
    {"source": "revenue_from_operations", "target": "gross_margin_pct", "type": "formula_dependency", "direction": "negative", "strength": 1.0},
    
    {"source": "ebitda", "target": "ebitda_margin_pct", "type": "formula_dependency", "direction": "positive", "strength": 1.0},
    {"source": "revenue_from_operations", "target": "ebitda_margin_pct", "type": "formula_dependency", "direction": "negative", "strength": 1.0},

    # Causal drivers (Business link)
    {"source": "revenue_from_operations", "target": "employee_benefit_expense", "type": "causal_driver", "direction": "positive", "strength": 0.35, "explanation": "As revenue grows, hiring often increases to support scale"},
    {"source": "cost_of_material", "target": "revenue_from_operations", "type": "causal_driver", "direction": "positive", "strength": 0.45, "explanation": "Increased materials cost can sometimes reflect higher sales volume"},
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
