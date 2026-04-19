"""
Dynamic Metrics Loader

Loads all metric definitions and formulas from the database at runtime.
Zero hardcoded metrics - everything comes from the database.
"""

import logging
import math
import re
from typing import Dict, Any, Callable, Optional, List
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

# Global cache for loaded metrics (populated at startup)
_METRIC_CACHE: Dict[str, Dict[str, Any]] = {}
_FORMULA_FUNCTIONS: Dict[str, Callable] = {}
_COMPUTATION_ORDER: List[str] = []
_ALL_PERIODS: List[str] = []
_RELATIONSHIPS: List[Dict[str, Any]] = []


def load_metrics_from_database(db: Session) -> Dict[str, Dict[str, Any]]:
    """
    Load all metric definitions from the metrics table.
    
    Returns:
        Dictionary mapping metric name to its definition.
    """
    global _METRIC_CACHE, _FORMULA_FUNCTIONS, _COMPUTATION_ORDER
    
    from ..models.db_models import Metric, MetricRelationship, TimeSeriesData
    
    log.info("Loading metrics from database...")
    _METRIC_CACHE = {}
    _FORMULA_FUNCTIONS = {}
    
    # Load all metrics
    metrics = db.query(Metric).all()
    
    if not metrics:
        log.warning("No metrics found in database. Run /api/seed first.")
        return {}
    
    for m in metrics:
        metric_dict = {
            "name": m.name,
            "display_name": m.display_name,
            "description": m.description,
            "formula": m.formula,
            "formula_inputs": m.formula_inputs or [],
            "unit": m.unit,
            "category": m.category,
            "is_base": m.is_base,
            "granularity": m.granularity,
        }
        _METRIC_CACHE[m.name] = metric_dict
        
        # Compile formula if it's a derived metric
        if m.formula and not m.is_base:
            try:
                _FORMULA_FUNCTIONS[m.name] = _compile_formula(m.formula, m.formula_inputs or [])
                if m.name not in _FORMULA_FUNCTIONS:
                    log.warning(f"Failed to compile formula for metric {m.name}")
            except Exception as e:
                log.error(f"Error compiling formula for {m.name}: {e}")
    
    # Load relationships
    relationships = db.query(MetricRelationship).all()
    global _RELATIONSHIPS
    _RELATIONSHIPS = [
        {
            "source": r.source_metric,
            "target": r.target_metric,
            "type": r.relationship_type,
            "direction": r.direction,
            "strength": r.strength,
            "explanation": r.explanation,
        }
        for r in relationships
    ]
    
    # Calculate topological order for computation
    _compute_topological_order()
    
    # Load all available periods from time series data
    _load_all_periods(db)
    
    log.info(f"Loaded {len(_METRIC_CACHE)} metrics, {len(_FORMULA_FUNCTIONS)} formulas, "
             f"{len(_RELATIONSHIPS)} relationships, {len(_ALL_PERIODS)} periods")
    
    return _METRIC_CACHE


def _compile_formula(formula_str: str, inputs: List[str]) -> Callable:
    """
    Safely compile a formula string into an executable Python function.
    
    Formula can contain:
      - Metric names (replaced with v['metric_name'])
      - Basic math operators: +, -, *, /, **
      - math functions: sqrt, log, exp, abs, min, max
      - Parentheses for grouping
    """
    # Sanitize formula: replace metric names with dict access
    sanitized = formula_str
    
    # Sort inputs by length (longest first) to avoid partial replacements
    for inp in sorted(inputs, key=len, reverse=True):
        # Replace metric names with v['metric_name'], but avoid double-replacement
        pattern = r'\b' + re.escape(inp) + r'\b'
        sanitized = re.sub(pattern, f"v['{inp}']", sanitized)
    
    # Remove any dangerous characters
    allowed_chars = set("v[]'.-+*/%() 0123456789.,abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_")
    if not all(c in allowed_chars for c in sanitized):
        log.warning(f"Formula contains disallowed characters: {formula_str}")
        return lambda v: 0.0
    
    # Create safe namespace with allowed functions
    safe_namespace = {
        "sqrt": math.sqrt,
        "log": math.log,
        "exp": math.exp,
        "abs": abs,
        "min": min,
        "max": max,
        "pow": pow,
    }
    
    try:
        # Compile the formula
        code = f"lambda v: ({sanitized})"
        formula_fn = eval(code, {"__builtins__": {}}, safe_namespace)
        
        # Test with zero values to catch errors early
        test_vals = {inp: 0.0 for inp in inputs}
        try:
            formula_fn(test_vals)
        except (ZeroDivisionError, KeyError, ValueError):
            # These are expected for some formulas, wrap to handle gracefully
            pass
        
        # Return a safe wrapper
        def safe_formula(v: Dict[str, float]) -> float:
            try:
                result = formula_fn(v)
                # Handle NaN, inf
                if result != result:  # NaN check
                    return 0.0
                if result == float('inf'):
                    return float('inf')
                if result == float('-inf'):
                    return float('-inf')
                return float(result)
            except (ZeroDivisionError, KeyError, ValueError, TypeError):
                return 0.0
        
        return safe_formula
    
    except Exception as e:
        log.error(f"Failed to compile formula '{formula_str}': {e}")
        return lambda v: 0.0


def _compute_topological_order() -> None:
    """
    Compute topological order for metric calculation (base metrics first, then derived).
    Uses simple topological sort based on formula dependencies.
    """
    global _COMPUTATION_ORDER
    
    from ..models.db_models import Metric
    
    # Start with base metrics
    _COMPUTATION_ORDER = []
    remaining = set(_METRIC_CACHE.keys())
    
    max_iterations = len(_METRIC_CACHE) + 1
    iterations = 0
    
    while remaining and iterations < max_iterations:
        iterations += 1
        added_this_round = False
        
        for metric_name in list(remaining):
            metric = _METRIC_CACHE[metric_name]
            
            # Add if it's a base metric
            if metric["is_base"]:
                _COMPUTATION_ORDER.append(metric_name)
                remaining.remove(metric_name)
                added_this_round = True
            else:
                # Add if all its inputs are already in the order
                inputs = metric["formula_inputs"]
                if all(inp in _COMPUTATION_ORDER for inp in inputs):
                    _COMPUTATION_ORDER.append(metric_name)
                    remaining.remove(metric_name)
                    added_this_round = True
        
        if not added_this_round:
            # Circular dependency or missing input metric
            log.warning(f"Could not order these metrics (possible circular dependency): {remaining}")
            _COMPUTATION_ORDER.extend(sorted(remaining))
            break
    
    log.debug(f"Computation order: {_COMPUTATION_ORDER}")


def _load_all_periods(db: Session) -> None:
    """Load all available periods from the database."""
    global _ALL_PERIODS
    
    from ..models.db_models import TimeSeriesData
    
    periods = db.query(TimeSeriesData.period).distinct().order_by(TimeSeriesData.period).all()
    _ALL_PERIODS = [p[0] for p in periods if p[0]]
    log.debug(f"Available periods: {_ALL_PERIODS}")


# Public API - access cached data
def get_metric_registry() -> Dict[str, Dict[str, Any]]:
    """Get the cached metric registry."""
    return _METRIC_CACHE


def get_formula_functions() -> Dict[str, Callable]:
    """Get the cached formula functions."""
    return _FORMULA_FUNCTIONS


def get_computation_order() -> List[str]:
    """Get the cached computation order."""
    return _COMPUTATION_ORDER


def get_all_periods() -> List[str]:
    """Get the cached list of all periods."""
    return _ALL_PERIODS


def get_relationships() -> List[Dict[str, Any]]:
    """Get the cached relationships."""
    return _RELATIONSHIPS


def is_loaded() -> bool:
    """Check if metrics have been loaded."""
    return len(_METRIC_CACHE) > 0
