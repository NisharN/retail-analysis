"""FastAPI entry point.

Wires CORS, lifespan (which kicks off the initial pipeline load), and
all routers.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS
from .routers import dimensions, gaps, health, summary, upload
from .state import lifespan

app = FastAPI(
    title="Missing Winners API",
    version="1.0.0",
    description=(
        "Identifies high-performing products that are missing or "
        "underperforming in a selected store compared to the rest of "
        "the retail chain."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(CORS_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(summary.router)
app.include_router(dimensions.router)
app.include_router(gaps.router)
app.include_router(upload.router)