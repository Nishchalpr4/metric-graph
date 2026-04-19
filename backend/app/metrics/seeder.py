"""
Database Seeder

Sequence:
  1. Drop and recreate all tables (idempotent).
  2. Insert metric definitions from DEFAULT_METRICS (seed data).
  3. Insert causal/formula relationship edges from DEFAULT_RELATIONSHIPS.
  
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
    DEFAULT_METRICS, DEFAULT_RELATIONSHIPS
)

log = logging.getLogger(__name__)


def seed_all(db: Session) -> dict:
    """Create schema and seed metric definitions and relationships WITHOUT deleting data. Returns a summary dict."""
    log.info("Creating schema and seeding metric definitions …")
    # Create all tables if they don't exist (idempotent, preserves existing data)
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
    """Seed metric definitions (skip if already exist)"""
    count = 0
    for name, meta in DEFAULT_METRICS.items():
        # Check if metric already exists
        existing = db.query(Metric).filter(Metric.name == name).first()
        if existing:
            continue  # Skip, already exists
        
        metric = Metric(
            name=name,
            display_name=meta["display_name"],
            description=meta.get("description", ""),
            formula=meta.get("formula"),
            formula_inputs=meta.get("formula_inputs") or [],
            unit=meta.get("unit", ""),
            category=meta.get("category", ""),
            is_base=meta.get("is_base", False),
        )
        db.add(metric)
        count += 1
    
    db.flush()
    log.info("  Inserted %d metric definitions.", count)
    return count


def _seed_relationships(db: Session) -> int:
    count = 0
    for rel in DEFAULT_RELATIONSHIPS:
        # Check if relationship already exists
        existing = db.query(MetricRelationship).filter(
            MetricRelationship.source_metric == rel["source"],
            MetricRelationship.target_metric == rel["target"]
        ).first()
        if existing:
            continue  # Skip, already exists
        
        relationship = MetricRelationship(
            source_metric=rel["source"],
            target_metric=rel["target"],
            relationship_type=rel["type"],
            direction=rel.get("direction", "positive"),
            strength=rel.get("strength", 1.0),
            explanation=rel.get("explanation", ""),
        )
        db.add(relationship)
        count += 1
    
    db.flush()
    log.info("  Inserted %d relationships.", count)
    return count
