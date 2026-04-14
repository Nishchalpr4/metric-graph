"""
Formula Computation Engine

Responsibilities:
  1. Given a snapshot of base-metric values for one (period, segment), compute
     all derived metrics in topological order.
  2. Given values for the SAME metric in two periods, compute the numerically
     attributed contribution of each formula input to the observed change.

Attribution method — midpoint gradient:
  For Y = f(X1, X2, ..., Xn):
    ∂Y/∂Xi evaluated at the midpoint of (prev, curr) → gradient_i
    raw_i = gradient_i × ΔXi
    Then normalise so Σ contributions = actual ΔY (handles interaction terms).
"""

from typing import Dict, List, Optional, Tuple
from .registry import METRIC_REGISTRY, FORMULA_FUNCTIONS, COMPUTATION_ORDER

_EPSILON = 1e-8   # finite-difference step
_MIN_CHANGE = 1e-6  # threshold below which we consider a value unchanged


def compute_all_metrics(base_values: Dict[str, float]) -> Dict[str, float]:
    """
    Given a flat dict {metric_name: value} containing at least all base metrics,
    fill in every derived metric in topological order and return the full dict.
    """
    values = dict(base_values)
    for metric in COMPUTATION_ORDER:
        if metric in FORMULA_FUNCTIONS and metric not in values:
            fn = FORMULA_FUNCTIONS[metric]
            inputs = METRIC_REGISTRY[metric]["formula_inputs"]
            input_vals = {k: values.get(k, 0.0) for k in inputs}
            try:
                values[metric] = fn(input_vals)
            except (ZeroDivisionError, KeyError):
                values[metric] = 0.0
    return values


def _safe_call(fn, values: Dict[str, float]) -> float:
    try:
        return fn(values)
    except (ZeroDivisionError, KeyError):
        return 0.0


def attribute_contributions(
    metric_name: str,
    prev_values: Dict[str, float],
    curr_values: Dict[str, float],
) -> Tuple[Dict[str, float], float]:
    """
    Attribute the change in `metric_name` between two periods to its formula inputs.

    Returns:
        contributions: {input_name: attributed_amount}  (signed ₹/% etc.)
        total_change:  actual change in the metric
    """
    fn = FORMULA_FUNCTIONS.get(metric_name)
    if fn is None:
        return {}, 0.0

    inputs = METRIC_REGISTRY[metric_name]["formula_inputs"]

    y_prev = _safe_call(fn, prev_values)
    y_curr = _safe_call(fn, curr_values)
    total_change = y_curr - y_prev

    if abs(total_change) < _MIN_CHANGE:
        return {inp: 0.0 for inp in inputs}, 0.0

    # Midpoint values for gradient evaluation
    mid = {k: (prev_values.get(k, 0.0) + curr_values.get(k, 0.0)) / 2.0 for k in inputs}

    gradients: Dict[str, float] = {}
    for inp in inputs:
        h = max(abs(mid[inp]), 1.0) * _EPSILON
        up = {**mid, inp: mid[inp] + h}
        dn = {**mid, inp: mid[inp] - h}
        gradients[inp] = (_safe_call(fn, up) - _safe_call(fn, dn)) / (2 * h)

    # Raw attribution: gradient × Δinput
    raw: Dict[str, float] = {}
    for inp in inputs:
        delta = curr_values.get(inp, 0.0) - prev_values.get(inp, 0.0)
        raw[inp] = gradients[inp] * delta

    # Normalise to match actual Δ (handles nonlinearity / interaction terms)
    raw_sum = sum(raw.values())
    if abs(raw_sum) < _MIN_CHANGE:
        # fallback: split proportionally to absolute raw values
        abs_sum = sum(abs(v) for v in raw.values()) or 1.0
        contributions = {k: (abs(v) / abs_sum) * total_change for k, v in raw.items()}
    else:
        scale = total_change / raw_sum
        contributions = {k: v * scale for k, v in raw.items()}

    return contributions, total_change


def get_metric_values_for_period(
    db,
    period: str,
    segment: str,
    metric_names: Optional[List[str]] = None,
) -> Dict[str, float]:
    """
    Load metric values from DB for a given (period, segment).
    Returns a flat dict {metric_name: value}.
    """
    from ..models.db_models import TimeSeriesData
    query = db.query(TimeSeriesData).filter(
        TimeSeriesData.period == period,
        TimeSeriesData.segment == segment,
    )
    if metric_names:
        query = query.filter(TimeSeriesData.metric_name.in_(metric_names))
    rows = query.all()
    return {row.metric_name: row.value for row in rows}
