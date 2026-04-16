"""
REST API Routes

Endpoints:
  POST /api/query           ← NL query → full causal analysis
  GET  /api/metrics         ← list all metric definitions
  GET  /api/metric/{name}   ← single metric metadata + all time-series
  GET  /api/graph           ← full graph (nodes + edges) for visualisation
  GET  /api/periods         ← list available periods
  GET  /api/segments        ← list available segments
  POST /api/sync-from-neon  ← sync metric data from Neon PostgreSQL
  POST /api/import-csv      ← import metric data from CSV file
  POST /api/seed            ← (re)seed the database with demo data
  GET  /api/health          ← liveness check
  GET  /api/suggestions     ← sample queries for the UI
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import DATABASE_URL
from ..database import get_db
from ..data.importer import import_metrics_from_csv
from ..data.postgres_source import NeonDataSource
from ..graph.builder import build_graph, graph_to_dict
from ..graph.inference import analyse
from ..metrics.registry import METRIC_REGISTRY, ALL_PERIODS
from ..metrics.seeder import seed_all
from ..models.db_models import Metric, TimeSeriesData
from ..query.handler import handle_query

router = APIRouter(prefix="/api")
log = logging.getLogger(__name__)

# ── Singleton in-memory graph ─────────────────────────────────────────────────
# Rebuilt on /seed and on first use.
_graph_cache: dict = {}   # keyed by "graph"


def _get_graph(db: Session):
    if "graph" not in _graph_cache:
        _graph_cache["graph"] = build_graph(db)
    return _graph_cache["graph"]


def _invalidate_graph():
    _graph_cache.pop("graph", None)


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str


class DirectAnalysisRequest(BaseModel):
    metric: str
    period: str
    compare_period: str
    segment: str = "Food Delivery"


class NeonSyncRequest(BaseModel):
    clear_existing: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/suggestions")
def suggestions():
    """Return curated sample queries shown in the UI."""
    return {
        "suggestions": [
            "Why did revenue increase in Q3 2023?",
            "What drove GMV growth in Q3 2023 vs Q2 2023?",
            "What caused AOV to rise in Q3 2023?",
            "Why did orders surge in Q3 2023?",
            "What drove active user growth in Q3 2023?",
            "Show revenue trends for Food Delivery",
            "Which segment contributed most to orders in Q3 2023?",
            "Why did discounts increase in Q3 2023?",
            "What is the trend for CAC?",
            "Why did take rate improve in Q3 2023?",
        ]
    }


@router.get("/periods")
def get_periods():
    return {"periods": ALL_PERIODS}


@router.get("/segments")
def get_segments():
    return {"segments": ["Food Delivery", "Grocery Delivery"]}


@router.get("/metrics")
def list_metrics(db: Session = Depends(get_db)):
    metrics = db.query(Metric).order_by(Metric.category, Metric.name).all()
    return {
        "metrics": [
            {
                "name": m.name,
                "display_name": m.display_name,
                "description": m.description,
                "formula": m.formula,
                "formula_inputs": m.formula_inputs or [],
                "unit": m.unit,
                "category": m.category,
                "is_base": m.is_base,
            }
            for m in metrics
        ]
    }


@router.get("/metric/{metric_name}")
def get_metric(
    metric_name: str,
    segment: str = "Food Delivery",
    db: Session = Depends(get_db),
):
    m = db.query(Metric).filter(Metric.name == metric_name).first()
    if not m:
        raise HTTPException(status_code=404, detail=f"Metric '{metric_name}' not found.")

    rows = (
        db.query(TimeSeriesData)
        .filter(
            TimeSeriesData.metric_name == metric_name,
            TimeSeriesData.segment == segment,
        )
        .all()
    )
    period_order = {p: i for i, p in enumerate(ALL_PERIODS)}
    sorted_rows = sorted(rows, key=lambda r: period_order.get(r.period, 999))

    return {
        "metric": {
            "name": m.name,
            "display_name": m.display_name,
            "description": m.description,
            "formula": m.formula,
            "formula_inputs": m.formula_inputs or [],
            "unit": m.unit,
            "category": m.category,
            "is_base": m.is_base,
        },
        "time_series": [
            {"period": r.period, "value": round(r.value, 4), "is_computed": r.is_computed}
            for r in sorted_rows
        ],
    }


@router.get("/graph")
def get_graph(db: Session = Depends(get_db)):
    g = _get_graph(db)
    return graph_to_dict(g)


@router.post("/query")
def query_endpoint(req: QueryRequest, db: Session = Depends(get_db)):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    g = _get_graph(db)
    try:
        result = handle_query(req.query, db=db, graph=g)
    except Exception as exc:
        log.exception("Query processing error")
        raise HTTPException(status_code=500, detail=str(exc))
    return result


@router.post("/analyse")
def analyse_direct(req: DirectAnalysisRequest, db: Session = Depends(get_db)):
    """Direct structured analysis without NL parsing (for programmatic use)."""
    if req.metric not in METRIC_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Unknown metric: {req.metric}")
    if req.period not in ALL_PERIODS:
        raise HTTPException(status_code=400, detail=f"Unknown period: {req.period}")
    if req.compare_period not in ALL_PERIODS:
        raise HTTPException(status_code=400, detail=f"Unknown compare_period: {req.compare_period}")

    g = _get_graph(db)
    result = analyse(
        metric_name=req.metric,
        period=req.period,
        compare_period=req.compare_period,
        segment=req.segment,
        db=db,
        graph=g,
    )
    return result


@router.post("/seed")
def seed_database(db: Session = Depends(get_db)):
    """Drop and reseed the database. Invalidates the graph cache."""
    try:
        counts = seed_all(db)
        _invalidate_graph()
        return {"status": "success", "inserted": counts}
    except Exception as exc:
        log.exception("Seed error")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/import-csv")
async def import_csv(file: UploadFile = File(...), clear: bool = False, db: Session = Depends(get_db)):
    """
    Import metric time-series data from CSV file.
    
    CSV Format (comma-separated, with header):
        metric_name,period,segment,value
        orders,Q1 2022,Food Delivery,85.0
        aov,Q1 2022,Food Delivery,295.0
    
    Query Parameters:
        clear: If true, delete existing data before import (default: false)
    """
    try:
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV file (.csv)")
        
        content = await file.read()
        csv_str = content.decode('utf-8')
        
        result = import_metrics_from_csv(csv_str, db, clear_existing=clear)
        
        if result.get("error_count", 0) > 0:
            result["warning"] = f"{result['error_count']} rows had errors"
        
        _invalidate_graph()
        return result
    
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("CSV import error")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/sync-from-neon")
def sync_from_neon(req: NeonSyncRequest, db: Session = Depends(get_db)):
    """
    Sync metric data from Neon PostgreSQL database to local database.
    
    Request body:
        {
            "neon_connection_string": "postgresql://user:password@host/dbname",
            "clear_existing": false
        }
    
    Connection string format:
        postgresql://user:password@ep-xyz.us-east-1.neon.tech/metrics_db
    
    Neon database must have a table named 'time_series_data' with columns:
        - metric_name (VARCHAR)
        - period (VARCHAR)  
        - segment (VARCHAR)
        - value (NUMERIC/FLOAT)
    """
    try:
        log.info(f"[SYNC] Starting sync from Neon with clear_existing={req.clear_existing}")
        
        # Clear existing data if requested
        if req.clear_existing:
            log.info("[SYNC] Clearing existing local data...")
            db.query(TimeSeriesData).delete()
            db.commit()
            log.info("[SYNC] Cleared existing local time-series data")
        
        # Connect to Neon using DATABASE_URL from config
        log.info(f"[SYNC] Connecting to Neon...")
        neon_source = NeonDataSource(DATABASE_URL)
        
        # Test connection
        log.info("[SYNC] Testing Neon connection...")
        if not neon_source.test_connection():
            log.error("[SYNC] Neon connection test failed")
            raise HTTPException(
                status_code=400, 
                detail="Failed to connect to Neon database. Check DATABASE_URL in .env."
            )
        log.info("[SYNC] Neon connection test successful")
        
        # Fetch data from Neon
        log.info("[SYNC] Fetching metrics from Neon...")
        try:
            rows_data = neon_source.fetch_metrics()
            log.info(f"[SYNC] Fetched {len(rows_data)} rows from Neon")
        except Exception as e:
            log.error(f"[SYNC] Error fetching metrics: {type(e).__name__}: {e}")
            raise
        
        if not rows_data:
            log.error("[SYNC] No data returned from fetch_metrics()")
            neon_source.close()
            raise HTTPException(
                status_code=400,
                detail="No data found in Neon database. Ensure time_series_data table exists."
            )
        
        # Insert into local database
        inserted = 0
        updated = 0
        errors = []
        
        for row in rows_data:
            try:
                metric_name = row.get("metric_name", "").strip()
                period = row.get("period", "").strip()
                segment = row.get("segment", "").strip()
                value = float(row.get("value", 0))
                
                if not all([metric_name, period, segment]):
                    errors.append(f"Row missing required fields: {row}")
                    continue
                
                # Check if exists
                existing = db.query(TimeSeriesData).filter(
                    TimeSeriesData.metric_name == metric_name,
                    TimeSeriesData.period == period,
                    TimeSeriesData.segment == segment,
                ).first()
                
                if existing:
                    existing.value = value
                    updated += 1
                else:
                    ts = TimeSeriesData(
                        metric_name=metric_name,
                        period=period,
                        segment=segment,
                        value=value,
                        is_computed=False,
                    )
                    db.add(ts)
                    inserted += 1
            
            except Exception as e:
                errors.append(f"Row error: {str(e)}")
        
        db.commit()
        neon_source.close()
        
        result = {
            "status": "success",
            "rows_inserted": inserted,
            "rows_updated": updated,
            "total_rows_synced": inserted + updated,
            "errors": errors,
            "error_count": len(errors),
        }
        
        log.info(f"Neon sync complete: {inserted} inserted, {updated} updated")
        _invalidate_graph()
        return result
    
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Neon sync error")
        raise HTTPException(status_code=500, detail=str(exc))
