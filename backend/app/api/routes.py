"""
REST API Routes

Endpoints:
  POST /api/query          ← NL query → full causal analysis
  GET  /api/metrics        ← list all metric definitions
  GET  /api/metric/{name}  ← single metric metadata + all time-series
  GET  /api/graph          ← full graph (nodes + edges) for visualisation
  GET  /api/periods        ← list available periods
  GET  /api/segments       ← list available segments
  POST /api/seed           ← (re)seed the database
  GET  /api/health         ← liveness check
  GET  /api/suggestions    ← sample queries for the UI
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
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
