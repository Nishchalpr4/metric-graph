"""
Database Seeder

Sequence:
  1. Drop and recreate all tables (idempotent).
  2. Insert metric definitions from METRIC_REGISTRY.
  3. Insert causal/formula relationship edges from RELATIONSHIP_DEFINITIONS.
  
Note: Time-series data should be imported via /api/import-csv endpoint.
"""

import logging
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import Base, engine
from ..models.db_models import (
    Metric, MetricRelationship, TimeSeriesData, CausalEvent
)
from .registry import (
    METRIC_REGISTRY, RELATIONSHIP_DEFINITIONS, COMPUTATION_ORDER, ALL_PERIODS
)

log = logging.getLogger(__name__)

SEGMENTS = ["Food Delivery", "Grocery Delivery"]


def seed_all(db: Session) -> dict:
    """Drop, recreate, and seed the metric definitions and relationships. Returns a summary dict."""
    log.info("Dropping and recreating tables …")
    # Use CASCADE to handle any pre-existing foreign key dependencies from
    # older table schemas that may reside in the same DB.
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO PUBLIC"))
        conn.commit()
    Base.metadata.create_all(bind=engine)

    counts = {
        "metrics": _seed_metrics(db),
        "relationships": _seed_relationships(db),
    }
    db.commit()
    log.info("Seeding complete: %s", counts)
    log.info("To import metric data, use /api/import-csv endpoint with CSV file.")
    return counts


# ─────────────────────────────────────────────────────────────────────────────

def _seed_metrics(db: Session) -> int:
    rows = []
    for name, meta in METRIC_REGISTRY.items():
        rows.append(Metric(
            name=name,
            display_name=meta["display_name"],
            description=meta.get("description", ""),
            formula=meta.get("formula"),
            formula_inputs=meta.get("formula_inputs") or [],
            unit=meta.get("unit", ""),
            category=meta.get("category", ""),
            is_base=meta.get("is_base", False),
        ))
    db.bulk_save_objects(rows)
    db.flush()
    log.info("  Inserted %d metric definitions.", len(rows))
    return len(rows)


def _seed_relationships(db: Session) -> int:
    rows = []
    for rel in RELATIONSHIP_DEFINITIONS:
        rows.append(MetricRelationship(
            source_metric=rel["source"],
            target_metric=rel["target"],
            relationship_type=rel["type"],
            direction=rel.get("direction", "positive"),
            strength=rel.get("strength", 1.0),
            explanation=rel.get("explanation", ""),
        ))
    db.bulk_save_objects(rows)
    db.flush()
    log.info("  Inserted %d relationships.", len(rows))
    return len(rows)
