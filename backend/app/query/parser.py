"""
Natural Language Query Parser

Converts a free-text query into a structured ParsedQuery object without
any heavy ML dependencies.  Uses regex and keyword tables.

Supported query patterns (examples):
  "Why did revenue increase in Q3 2023?"
  "What drove GMV growth in Q3 2023 vs Q2 2023?"
  "What caused AOV to fall in Q4 2022?"
  "Show revenue trends"
  "Which segment contributed most to orders in Q3 2023?"
  "Top drivers of take rate in Q1 2023"
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from ..metrics.registry import METRIC_REGISTRY, ALL_PERIODS

# ─────────────────────────────────────────────────────────────────────────────
# Keyword mappings
# ─────────────────────────────────────────────────────────────────────────────

_METRIC_ALIASES: dict[str, list[str]] = {
    "revenue":          ["revenue", "net revenue", "platform revenue"],
    "ebitda":           ["ebitda", "ebita", "earnings before interest taxes depreciation amortization"],
    "gmv":              ["gmv", "gross merchandise value", "gross merchandise", "gross merch"],
    "aov":              ["aov", "average order value", "order value", "avg order value"],
    "orders":           ["orders", "order count", "total orders", "number of orders", "order volume"],
    "take_rate":        ["take rate", "take_rate", "monetisation rate", "monetization rate"],
    "active_users":     ["active users", "mau", "monthly active users", "active user"],
    "new_users":        ["new users", "user acquisition", "acquired users", "user growth"],
    "arpu":             ["arpu", "average revenue per user", "revenue per user"],
    "order_frequency":  ["order frequency", "ordering frequency", "frequency"],
    "cac":              ["cac", "customer acquisition cost", "acquisition cost"],
    "basket_size":      ["basket size", "items per order", "basket", "cart size"],
    "discounts":        ["discounts", "promotions", "promotional spend", "discount spend"],
    "commission_rate":  ["commission rate", "commission"],
    "delivery_charges": ["delivery charges", "delivery revenue", "delivery fees"],
    "marketing_spend":  ["marketing spend", "marketing", "ad spend"],
    "pricing_index":    ["pricing index", "price index", "pricing"],
    "restaurant_partners": ["restaurant partners", "partners", "restaurant count"],
}

_SEGMENT_ALIASES: dict[str, list[str]] = {
    "Food Delivery":    ["food delivery", "food", "restaurant delivery"],
    "Grocery Delivery": ["grocery delivery", "grocery", "groceries", "quick commerce"],
    "Overall":          ["overall", "total", "all segments", "combined"],
}

_INCREASE_WORDS = {
    "increase", "increased", "grew", "growth", "rise", "rose", "jumped",
    "improved", "up", "higher", "surge", "surged", "boost", "boosted",
    "expand", "expanded",
}
_DECREASE_WORDS = {
    "decrease", "decreased", "declined", "decline", "drop", "dropped",
    "fell", "fall", "down", "lower", "reduction", "reduced", "shrink",
    "shrunk", "dip", "dipped",
}

# Regex for period strings like "Q3 2023" or "Q3 '23"
_PERIOD_RE = re.compile(r'\b(Q[1-4]\s+20\d{2})\b', re.IGNORECASE)
# Also match "Q3 2023 vs Q2 2023" for explicit comparison
_VS_RE = re.compile(
    r'\b(Q[1-4]\s+20\d{2})\s+(?:vs\.?|versus|compared to|against)\s+(Q[1-4]\s+20\d{2})\b',
    re.IGNORECASE,
)


# ─────────────────────────────────────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ParsedQuery:
    raw_query: str
    metric: str                          # canonical metric name
    period: str                          # e.g. "Q3 2023"
    compare_period: str                  # e.g. "Q2 2023"  (QoQ default)
    segment: str = "Food Delivery"
    intent: str = "explain_change"       # explain_change | trend | segment_breakdown
    direction: Optional[str] = None      # "increase" | "decrease" | None (unknown)
    confidence: float = 1.0
    warnings: list = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Parser
# ─────────────────────────────────────────────────────────────────────────────

def parse_query(raw: str) -> ParsedQuery:
    text = raw.strip().lower()
    warnings: list[str] = []

    # ── 1. Metric detection ───────────────────────────────────────────────────
    metric = _extract_metric(text)
    if metric is None:
        metric = "revenue"   # sensible default
        warnings.append("Could not identify a specific metric — defaulting to 'revenue'.")

    # ── 2. Period detection ───────────────────────────────────────────────────
    # Check for explicit "X vs Y" first
    vs_match = _VS_RE.search(raw)
    if vs_match:
        period = _normalise_period(vs_match.group(1))
        compare_period = _normalise_period(vs_match.group(2))
    else:
        all_periods_found = [_normalise_period(m) for m in _PERIOD_RE.findall(raw)]
        if len(all_periods_found) >= 2:
            period = all_periods_found[0]
            compare_period = all_periods_found[1]
        elif len(all_periods_found) == 1:
            period = all_periods_found[0]
            compare_period = _prev_period(period)
        else:
            # Default: latest period vs previous
            period = ALL_PERIODS[-1]
            compare_period = ALL_PERIODS[-2]
            warnings.append(
                f"No period found in query — defaulting to {period} vs {compare_period}."
            )

    # ── 3. Segment detection ──────────────────────────────────────────────────
    segment = _extract_segment(text)

    # ── 4. Intent & direction ─────────────────────────────────────────────────
    intent, direction = _extract_intent(text)

    confidence = 1.0 if not warnings else 0.7

    return ParsedQuery(
        raw_query=raw,
        metric=metric,
        period=period,
        compare_period=compare_period,
        segment=segment,
        intent=intent,
        direction=direction,
        confidence=confidence,
        warnings=warnings,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────

def _extract_metric(text: str) -> Optional[str]:
    # Longest alias wins to handle multi-word names (e.g. "average order value" before "order")
    best_metric = None
    best_len = 0
    for canonical, aliases in _METRIC_ALIASES.items():
        for alias in aliases:
            if alias in text and len(alias) > best_len:
                best_metric = canonical
                best_len = len(alias)
    return best_metric


def _extract_segment(text: str) -> str:
    for canonical, aliases in _SEGMENT_ALIASES.items():
        for alias in aliases:
            if alias in text:
                return canonical
    return "Food Delivery"   # platform default


def _extract_intent(text: str) -> tuple[str, Optional[str]]:
    words = set(re.findall(r'\b\w+\b', text))
    if words & _INCREASE_WORDS:
        direction = "increase"
        intent = "explain_change"
    elif words & _DECREASE_WORDS:
        direction = "decrease"
        intent = "explain_change"
    elif any(w in text for w in ("trend", "over time", "history", "historical")):
        direction = None
        intent = "trend"
    elif any(w in text for w in ("segment", "breakdown", "split", "contribute", "which")):
        direction = None
        intent = "segment_breakdown"
    else:
        direction = None
        intent = "explain_change"
    return intent, direction


def _normalise_period(raw: str) -> str:
    """Normalise 'q3 2023' → 'Q3 2023'."""
    raw = raw.strip()
    parts = raw.upper().split()
    if len(parts) == 2:
        return f"{parts[0]} {parts[1]}"
    return raw.upper()


def _prev_period(period: str) -> str:
    """Return the immediately preceding quarter."""
    if period not in ALL_PERIODS:
        return period
    idx = ALL_PERIODS.index(period)
    return ALL_PERIODS[idx - 1] if idx > 0 else ALL_PERIODS[0]
