"""
Database Seeder

Sequence:
  1. Drop and recreate all tables (idempotent).
  2. Insert metric definitions from METRIC_REGISTRY.
  3. Insert causal/formula relationship edges from RELATIONSHIP_DEFINITIONS.
  4. Insert raw base-metric time-series data from RAW_DATA.
  5. Compute and insert derived metrics for every (period, segment) pair.
  6. Insert causal events from CAUSAL_EVENTS.
"""

import logging
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import Base, engine
from ..models.db_models import (
    Metric, MetricRelationship, TimeSeriesData, CausalEvent
)
from .registry import (
    METRIC_REGISTRY, RELATIONSHIP_DEFINITIONS,
    RAW_DATA, CAUSAL_EVENTS, COMPUTATION_ORDER, ALL_PERIODS
)
from .engine import compute_all_metrics

log = logging.getLogger(__name__)

SEGMENTS = ["Food Delivery", "Grocery Delivery"]


def seed_all(db: Session) -> dict:
    """Drop, recreate, and seed the entire database. Returns a summary dict."""
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
        "time_series": _seed_time_series(db),
        "causal_events": _seed_causal_events(db),
    }
    db.commit()
    log.info("Seeding complete: %s", counts)
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


def _seed_time_series(db: Session) -> int:
    rows = []
    inserted_keys = set()

    # ── Step 1: insert raw (base) data ────────────────────────────────────────
    for (period, segment, metric_name), value in RAW_DATA.items():
        key = (metric_name, period, segment)
        if key in inserted_keys:
            continue
        rows.append(TimeSeriesData(
            metric_name=metric_name,
            period=period,
            segment=segment,
            value=value,
            is_computed=False,
        ))
        inserted_keys.add(key)

    db.bulk_save_objects(rows)
    db.flush()
    base_count = len(rows)
    rows = []

    # ── Step 2: compute derived metrics for each (period, segment) ─────────────
    for segment in SEGMENTS:
        for period in ALL_PERIODS:
            # Gather all base values available for this (period, segment)
            base_vals = {
                m: v
                for (p, s, m), v in RAW_DATA.items()
                if p == period and s == segment
            }
            if not base_vals:
                continue

            full_vals = compute_all_metrics(base_vals)

            # Insert only derived (non-base) metrics
            for metric_name in COMPUTATION_ORDER:
                meta = METRIC_REGISTRY.get(metric_name, {})
                if meta.get("is_base", True):
                    continue                        # already inserted above
                if metric_name not in full_vals:
                    continue

                key = (metric_name, period, segment)
                if key in inserted_keys:
                    continue

                rows.append(TimeSeriesData(
                    metric_name=metric_name,
                    period=period,
                    segment=segment,
                    value=round(full_vals[metric_name], 6),
                    is_computed=True,
                ))
                inserted_keys.add(key)

    db.bulk_save_objects(rows)
    db.flush()
    derived_count = len(rows)

    total = base_count + derived_count
    log.info("  Inserted %d base + %d derived time-series rows.", base_count, derived_count)
    return total


def _seed_causal_events(db: Session) -> int:
    rows = []
    for ev in CAUSAL_EVENTS:
        rows.append(CausalEvent(
            period=ev["period"],
            event_name=ev["event_name"],
            segment=ev.get("segment", "Overall"),
            affected_metrics=ev.get("affected_metrics", []),
            direction=ev.get("direction", "positive"),
            magnitude=ev.get("magnitude", "medium"),
            explanation=ev.get("explanation", ""),
        ))
    db.bulk_save_objects(rows)
    db.flush()
    log.info("  Inserted %d causal events.", len(rows))
    return len(rows)
