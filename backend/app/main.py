"""
FastAPI Application Entry-point
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import APP_NAME, DEBUG
from .database import engine, SessionLocal
from .models.db_models import Base   # noqa: F401  (import triggers table metadata)
from .api.routes import router
from .metrics.loader import load_metrics_from_database

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting %s …", APP_NAME)
    
    # Load metrics from database at startup
    try:
        db = SessionLocal()
        load_metrics_from_database(db)
        db.close()
        log.info("✓ Metrics loaded from database")
    except Exception as e:
        log.warning(f"Could not load metrics from database at startup: {e}. "
                   f"Metrics will be loaded on first use.")
    
    yield
    log.info("Shutting down.")


app = FastAPI(
    title=APP_NAME,
    description=(
        "Causal Financial Knowledge Graph for food-delivery analytics. "
        "Encodes metrics, formula dependencies, and causal business drivers "
        "to answer 'why did X change?' questions."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Allow the frontend (served from any origin during dev) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Serve the frontend as static files at /
import os, pathlib
_frontend = pathlib.Path(__file__).parent.parent.parent / "frontend"
if _frontend.exists():
    app.mount("/", StaticFiles(directory=str(_frontend), html=True), name="frontend")
