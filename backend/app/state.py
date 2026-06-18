"""
In-memory application state.

Holds the cached, cleaned DataFrames produced by `pipeline.run_pipeline`
once at backend startup, and provides a thread-safe swap for `/api/upload`.

Why a singleton + threading.Lock and not async Lock?
  - The DataFrames themselves are not async; the only mutations are at
    startup (one daemon thread) and on upload (one request thread). A
    simple `threading.Lock` is sufficient and avoids confusing async/await
    semantics around the long-running pipeline.run_pipeline call.

Why `lifespan` and not `@app.on_event("startup")`?
  - `on_event` is deprecated in modern FastAPI; `lifespan` is the
    documented replacement and integrates cleanly with the rest of the
    ASGI stack.
"""
from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI

from .config import DEFAULT_DATA_PATH
from .pipeline import CleaningReport, PipelineResult, run_pipeline

logger = logging.getLogger(__name__)


@dataclass
class AppState:
    """The single source of truth for cached analysis data."""

    cleaned: Optional[pd.DataFrame] = None
    chain_summary: Optional[pd.DataFrame] = None
    shop_product: Optional[pd.DataFrame] = None
    cleaning_report: Optional[CleaningReport] = None
    ready: bool = False
    load_error: Optional[str] = None
    current_source: Optional[str] = None
    lock: threading.Lock = field(default_factory=threading.Lock)

    def is_ready(self) -> bool:
        return self.ready and self.cleaned is not None


class _StateContainer:
    """Module-level singleton holder."""

    def __init__(self) -> None:
        self._state = AppState()

    def get(self) -> AppState:
        return self._state

    def swap(self, new_state: AppState) -> None:
        """Atomically replace the state object. Used by reload_from_path."""
        with new_state.lock:
            self._state = new_state


_container = _StateContainer()


def get_state() -> AppState:
    """Public accessor used by routers. Do not mutate fields directly."""
    return _container.get()


def _load_into_state(state: AppState, path: Path) -> None:
    """Run the full pipeline and populate the AppState fields under its lock."""
    try:
        logger.info("Loading dataset from %s ...", path)
        result: PipelineResult = run_pipeline(str(path))
        with state.lock:
            state.cleaned = result.cleaned
            state.chain_summary = result.chain_summary
            state.shop_product = result.shop_product
            state.cleaning_report = result.cleaning_report
            state.current_source = str(path)
            state.load_error = None
            state.ready = True
        logger.info(
            "Dataset ready: %d rows, %d products, %d shops, %d departments",
            result.cleaning_report.rows_after,
            result.cleaning_report.unique_articles,
            result.cleaning_report.unique_shops,
            result.cleaning_report.unique_departments,
        )
    except Exception as exc:  # noqa: BLE001 - capture any startup failure
        logger.exception("Pipeline failed during load")
        with state.lock:
            state.load_error = f"{type(exc).__name__}: {exc}"
            state.ready = False


def reload_from_path(path: Path) -> CleaningReport:
    """
    Re-run the pipeline against a new file and atomically swap state.
    Used by /api/upload. Blocks the calling thread; that's fine because
    uploads are user-initiated and the UI shows a loading indicator.

    Unlike the startup lifespan loader (`_load_into_state`, which must
    never raise so a bad default file doesn't crash the whole app at
    boot), this function lets the original exception propagate -- e.g. a
    schema-mismatch `ValueError` from `pipeline._validate_schema` -- so
    `routers/upload.py` can map it to the correct HTTP status (422)
    instead of every failure collapsing into a generic 500.
    """
    result: PipelineResult = run_pipeline(str(path))
    new_state = AppState()
    with new_state.lock:
        new_state.cleaned = result.cleaned
        new_state.chain_summary = result.chain_summary
        new_state.shop_product = result.shop_product
        new_state.cleaning_report = result.cleaning_report
        new_state.current_source = str(path)
        new_state.load_error = None
        new_state.ready = True
    _container.swap(new_state)
    return new_state.cleaning_report  # type: ignore[return-value]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: kick off the initial pipeline load in a daemon thread."""
    state = get_state()
    thread = threading.Thread(
        target=_load_into_state,
        args=(state, DEFAULT_DATA_PATH),
        daemon=True,
        name="pipeline-startup",
    )
    thread.start()
    # Yield immediately; /health reports ready=False until the thread finishes.
    try:
        yield
    finally:
        # Nothing to tear down — DataFrames are released when the process exits.
        pass