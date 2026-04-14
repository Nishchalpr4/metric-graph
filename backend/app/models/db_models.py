from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text,
    TIMESTAMP, UniqueConstraint, ForeignKey, JSON
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql import func
from ..database import Base


class Metric(Base):
    """
    Every financial or operational metric tracked in the system.
    is_base=True  → raw input fed from external data
    is_base=False → computed from a formula over other metrics
    """
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=False)
    description = Column(Text)
    formula = Column(String(500))          # Human-readable formula string
    formula_inputs = Column(ARRAY(String)) # Names of metrics this formula depends on
    unit = Column(String(50))              # ₹B, %, M, ₹, items, K, index
    granularity = Column(String(50), default="quarterly")
    category = Column(String(100))         # Financial | Operational | User
    is_base = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


class MetricRelationship(Base):
    """
    Directed edge in the causal knowledge graph.

    relationship_type options:
      "formula_dependency" – source is mathematically required to compute target
      "causal_driver"      – source causes target to move (business logic)

    direction: "positive" | "negative"
    strength : 0.0–1.0  (how strongly source drives target)
    """
    __tablename__ = "metric_relationships"

    id = Column(Integer, primary_key=True, index=True)
    source_metric = Column(String(100), ForeignKey("metrics.name"), nullable=False)
    target_metric = Column(String(100), ForeignKey("metrics.name"), nullable=False)
    relationship_type = Column(String(50), nullable=False)
    direction = Column(String(20), default="positive")
    strength = Column(Float, default=1.0)
    explanation = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())


class TimeSeriesData(Base):
    """
    One row = one metric, one quarter, one segment.
    is_computed=True means the value was derived by the formula engine.
    """
    __tablename__ = "time_series_data"

    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(100), ForeignKey("metrics.name"), nullable=False)
    period = Column(String(20), nullable=False)      # e.g. "Q3 2023"
    segment = Column(String(100), default="Overall") # Food Delivery | Grocery Delivery | Overall
    value = Column(Float, nullable=False)
    is_computed = Column(Boolean, default=False)
    notes = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "metric_name", "period", "segment",
            name="uq_metric_period_segment"
        ),
    )


class CausalEvent(Base):
    """
    Named business events that explain causal spikes in a given period.
    Enriches the inference output with narrative context.
    """
    __tablename__ = "causal_events"

    id = Column(Integer, primary_key=True, index=True)
    period = Column(String(20), nullable=False)
    event_name = Column(String(200), nullable=False)
    segment = Column(String(100), default="Overall")
    affected_metrics = Column(ARRAY(String))
    direction = Column(String(20))      # positive | negative
    magnitude = Column(String(20))      # high | medium | low
    explanation = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())


class QueryLog(Base):
    """Stores every NL query and its result for auditability."""
    __tablename__ = "query_log"

    id = Column(Integer, primary_key=True, index=True)
    query_text = Column(Text, nullable=False)
    parsed_metric = Column(String(100))
    parsed_period = Column(String(20))
    parsed_compare_period = Column(String(20))
    parsed_segment = Column(String(100))
    result = Column(JSON)
    created_at = Column(TIMESTAMP, server_default=func.now())
